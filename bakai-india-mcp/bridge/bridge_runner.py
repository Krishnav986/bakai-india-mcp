
"""BAKAI MCP WebSocket Bridge for XiaoZhi.

Connects the local FastMCP tools to XiaoZhi and runs
the authenticated Android phone gateway.
"""

from __future__ import annotations

import asyncio
import inspect
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import websockets

# Add MCP project root to Python path.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.config import settings
from core.logging import logger
from server import mcp


def get_registered_tools():
    """Get tools registered with the local FastMCP server."""
    manager = getattr(mcp, "_tool_manager", None)
    return getattr(manager, "_tools", {})


class XiaozhiWebSocketBridge:
    """Expose local MCP tools through XiaoZhi WebSocket."""

    def __init__(
        self,
        ws_url: str,
        token: Optional[str] = None,
    ) -> None:
        self.ws_url = ws_url
        self.token = token or settings.XIAOZHI_TOKEN
        self.device_id = (
            settings.XIAOZHI_DEVICE_ID or "bakai_robot_01"
        )
        self._running = False

    def build_tool_manifest(self) -> List[Dict[str, Any]]:
        """Build the MCP tools/list response."""
        manifest = []

        for name, tool in get_registered_tools().items():
            fn = getattr(tool, "fn", None)

            description = (
                getattr(tool, "description", None)
                or getattr(fn, "__doc__", "")
                or ""
            )

            schema = getattr(tool, "parameters", None)

            if not isinstance(schema, dict):
                schema = {
                    "type": "object",
                    "properties": {},
                }

            manifest.append({
                "name": name,
                "description": description.strip(),
                "inputSchema": schema,
            })

        return manifest

    async def execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> Any:
        """Execute one registered MCP tool."""
        tool = get_registered_tools().get(tool_name)

        if tool is None:
            raise ValueError(
                f"Tool '{tool_name}' was not found."
            )

        fn = getattr(tool, "fn", None)

        if fn is None:
            raise RuntimeError(
                f"Tool '{tool_name}' has no callable function."
            )

        logger.info(f"Executing MCP tool: {tool_name}")

        if inspect.iscoroutinefunction(fn):
            return await fn(**arguments)

        result = fn(**arguments)

        if inspect.isawaitable(result):
            result = await result

        return result

    async def send_response(
        self,
        ws,
        message_id: Any,
        result: Any,
    ) -> None:
        """Send a JSON-RPC success response."""
        response = {
            "jsonrpc": "2.0",
            "id": message_id,
            "result": result,
        }

        await ws.send(json.dumps(response, ensure_ascii=False))

    async def send_error(
        self,
        ws,
        message_id: Any,
        code: int,
        message: str,
    ) -> None:
        """Send a JSON-RPC error response."""
        response = {
            "jsonrpc": "2.0",
            "id": message_id,
            "error": {
                "code": code,
                "message": message,
            },
        }

        await ws.send(json.dumps(response, ensure_ascii=False))

    async def handle_message(
        self,
        ws,
        message_text: str,
    ) -> None:
        """Handle incoming XiaoZhi JSON-RPC messages."""

        try:
            message = json.loads(message_text)
        except (json.JSONDecodeError, TypeError):
            logger.warning("Received invalid JSON-RPC message.")
            return

        message_id = message.get("id")
        method = message.get("method")
        params = message.get("params") or {}

        if not isinstance(params, dict):
            params = {}

        # MCP initialization.
        if method == "initialize":
            requested_version = params.get(
                "protocolVersion",
                "2024-11-05",
            )

            await self.send_response(
                ws,
                message_id,
                {
                    "protocolVersion": requested_version,
                    "capabilities": {
                        "tools": {
                            "listChanged": False
                        }
                    },
                    "serverInfo": {
                        "name": "BAKAI MCP",
                        "version": "1.0.0",
                    },
                },
            )

            logger.info("MCP initialization completed.")
            return

        # Notifications do not receive JSON-RPC responses.
        if method == "notifications/initialized":
            logger.info("XiaoZhi initialized the MCP session.")
            return

        if method == "notifications/cancelled":
            return

        # Tool discovery.
        if method == "tools/list":
            tools = self.build_tool_manifest()

            await self.send_response(
                ws,
                message_id,
                {
                    "tools": tools,
                },
            )

            logger.info(
                f"Provided {len(tools)} MCP tools to XiaoZhi."
            )
            return

        # Tool execution.
        if method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments") or {}

            if not isinstance(tool_name, str):
                await self.send_error(
                    ws,
                    message_id,
                    -32602,
                    "Invalid tool name.",
                )
                return

            if not isinstance(arguments, dict):
                await self.send_error(
                    ws,
                    message_id,
                    -32602,
                    "Tool arguments must be an object.",
                )
                return

            try:
                result = await self.execute_tool(
                    tool_name,
                    arguments,
                )

                response_text = (
                    result
                    if isinstance(result, str)
                    else json.dumps(
                        result,
                        ensure_ascii=False,
                        default=str,
                    )
                )

                await self.send_response(
                    ws,
                    message_id,
                    {
                        "content": [
                            {
                                "type": "text",
                                "text": response_text,
                            }
                        ],
                        "isError": False,
                    },
                )

            except Exception as exc:
                logger.error(
                    f"MCP tool execution failed: {tool_name}: {exc}"
                )

                await self.send_response(
                    ws,
                    message_id,
                    {
                        "content": [
                            {
                                "type": "text",
                                "text": str(exc),
                            }
                        ],
                        "isError": True,
                    },
                )

            return

        # MCP ping.
        if method == "ping":
            await self.send_response(
                ws,
                message_id,
                {},
            )
            return

        # Unknown request.
        if method and message_id is not None:
            await self.send_error(
                ws,
                message_id,
                -32601,
                f"Method not found: {method}",
            )

    def build_connection_url(self) -> str:
        """Add the token once, without duplicating query parameters."""
        parts = urlsplit(self.ws_url)
        query = parse_qsl(
            parts.query,
            keep_blank_values=True,
        )

        if self.token and not any(
            key == "token" for key, _ in query
        ):
            query.append(("token", self.token))

        return urlunsplit((
            parts.scheme,
            parts.netloc,
            parts.path,
            urlencode(query),
            parts.fragment,
        ))

    async def start(self) -> None:
        """Connect and reconnect to XiaoZhi."""
        self._running = True
        reconnect_delay = 3

        headers = {
            "X-Device-Id": self.device_id,
            "User-Agent": settings.USER_AGENT,
        }

        connect_url = self.build_connection_url()

        logger.info(
            "Starting BAKAI XiaoZhi MCP WebSocket connection."
        )

        while self._running:
            try:
                async with websockets.connect(
                    connect_url,
                    additional_headers=headers,
                    ping_interval=20,
                    ping_timeout=20,
                    close_timeout=10,
                ) as ws:

                    logger.info(
                        "Connected to XiaoZhi MCP endpoint."
                    )

                    reconnect_delay = 3

                    async for message in ws:
                        if isinstance(message, str):
                            await self.handle_message(
                                ws,
                                message,
                            )

            except asyncio.CancelledError:
                raise

            except Exception as exc:
                logger.warning(
                    f"XiaoZhi connection ended: {exc}. "
                    f"Retrying in {reconnect_delay:.1f} seconds."
                )

                await asyncio.sleep(reconnect_delay)

                reconnect_delay = min(
                    30,
                    reconnect_delay * 1.5,
                )

    def stop(self) -> None:
        self._running = False


async def run_services(bridge):
    """Run the XiaoZhi bridge and phone gateway together."""
    import uvicorn

    from bridge.phone_gateway import app

    bridge_task = asyncio.create_task(bridge.start())

    gateway_config = uvicorn.Config(
        app,
        host=settings.PHONE_GATEWAY_HOST,
        port=settings.PHONE_GATEWAY_PORT,
        log_level="warning",
        access_log=False,
    )

    gateway_server = uvicorn.Server(gateway_config)
    gateway_task = asyncio.create_task(
        gateway_server.serve()
    )

    logger.info(
        "BAKAI phone gateway starting on port "
        f"{settings.PHONE_GATEWAY_PORT}"
    )

    try:
        await asyncio.gather(
            bridge_task,
            gateway_task,
        )

    finally:
        bridge.stop()
        gateway_server.should_exit = True

        for task in (bridge_task, gateway_task):
            task.cancel()

        await asyncio.gather(
            bridge_task,
            gateway_task,
            return_exceptions=True,
        )


if __name__ == "__main__":
    endpoint = (
        sys.argv[1]
        if len(sys.argv) > 1
        else settings.XIAOZHI_WS_ENDPOINT
    )

    if not endpoint:
        raise SystemExit(
            "XIAOZHI_WS_ENDPOINT is missing from configuration."
        )

    bridge = XiaozhiWebSocketBridge(
        ws_url=endpoint,
    )

    try:
        asyncio.run(run_services(bridge))

    except KeyboardInterrupt:
        logger.info("BAKAI services stopped by user.")
