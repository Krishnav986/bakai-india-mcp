"""Optional Dashboard API and Management Web Console for BAKAI MCP Ecosystem.

Runs independently of the Netlify frontend on port 8088.
Provides health diagnostics, station management, and real-time stream status.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict
from starlette.applications import Starlette
from starlette.responses import JSONResponse, HTMLResponse
from starlette.routing import Route
import uvicorn

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.config import settings
from radio.radio_tools import _load_stations_db, verify_stream_url, radio_state
from server import mcp

_START_TIME = time.time()


async def api_status(request):
    """Returns server diagnostics and active state."""
    tools_count = len(getattr(mcp._tool_manager, "_tools", {}))
    state = radio_state.get_state()
    return JSONResponse({
        "server": settings.SERVER_NAME,
        "version": settings.SERVER_VERSION,
        "uptime_seconds": int(time.time() - _START_TIME),
        "tools_registered": tools_count,
        "active_radio": state,
    })


async def api_stations(request):
    """Lists all configured radio stations."""
    stations = _load_stations_db()
    return JSONResponse({"count": len(stations), "stations": stations})


async def api_verify_stream(request):
    """Verifies any live stream URL on demand."""
    try:
        body = await request.json()
        url = body.get("url", "")
    except Exception:
        url = request.query_params.get("url", "")

    if not url:
        return JSONResponse({"status": "error", "message": "Missing 'url' parameter"}, status_code=400)

    is_alive = await verify_stream_url(url, timeout=4.0)
    return JSONResponse({"url": url, "is_alive": is_alive})


async def dashboard_view(request):
    """Renders a responsive web console for BAKAI MCP."""
    stations = _load_stations_db()
    tools = sorted(list(getattr(mcp._tool_manager, "_tools", {}).keys()))
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>BAKAI India MCP Ecosystem Dashboard</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    :root {{ --primary: #ff9933; --secondary: #138808; --dark: #121820; --card: #1e2632; --text: #e6edf3; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: var(--dark); color: var(--text); margin: 0; padding: 24px; }}
    .header {{ display: flex; align-items: center; justify-content: space-between; border-bottom: 2px solid #2a3442; padding-bottom: 16px; margin-bottom: 24px; }}
    .badge {{ background: #238636; color: #fff; padding: 4px 10px; border-radius: 12px; font-size: 13px; font-weight: 600; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 16px; }}
    .card {{ background: var(--card); border: 1px solid #2f3b4c; border-radius: 8px; padding: 18px; }}
    .card h3 {{ margin-top: 0; color: var(--primary); font-size: 18px; }}
    .station-item {{ border-bottom: 1px solid #283342; padding: 8px 0; display: flex; justify-content: space-between; align-items: center; }}
    .btn {{ background: #238636; border: none; color: white; padding: 6px 12px; border-radius: 4px; cursor: pointer; text-decoration: none; font-size: 12px; }}
    .btn:hover {{ background: #2ea043; }}
    .tool-pill {{ display: inline-block; background: #273344; color: #58a6ff; font-family: monospace; font-size: 12px; padding: 4px 8px; border-radius: 4px; margin: 3px; }}
  </style>
</head>
<body>
  <div class="header">
    <div>
      <h1 style="margin: 0; font-size: 24px;">🤖 BAKAI INDIA MCP SERVER</h1>
      <p style="margin: 4px 0 0; color: #8b949e;">Xiaozhi Robot Services Ecosystem • All India Radio • News • Music • Utilities</p>
    </div>
    <div>
      <span class="badge">● Server Active</span>
    </div>
  </div>

  <div class="grid">
    <div class="card">
      <h3>Active Capabilities ({len(tools)} MCP Tools)</h3>
      <p style="color: #8b949e; font-size: 13px;">Registered on Model Context Protocol protocol for robot BAKAI:</p>
      <div>
        {''.join(f'<span class="tool-pill">{t}</span>' for t in tools)}
      </div>
    </div>

    <div class="card">
      <h3>Indian Radio Directory ({len(stations)} Stations)</h3>
      <div style="max-height: 380px; overflow-y: auto;">
        {''.join(f'<div class="station-item"><div><strong>{s["name"]}</strong><br><small style="color: #8b949e;">{s.get("language", "").title()} • {s.get("city", "")}</small></div><a href="{s["stream_url"]}" target="_blank" class="btn">Stream</a></div>' for s in stations)}
      </div>
    </div>
  </div>
</body>
</html>
"""
    return HTMLResponse(html_content)


app = Starlette(
    routes=[
        Route("/", dashboard_view),
        Route("/api/status", api_status),
        Route("/api/stations", api_stations),
        Route("/api/verify-stream", api_verify_stream, methods=["GET", "POST"]),
    ]
)


def start_dashboard(host: str = "0.0.0.0", port: int = 8088):
    """Starts the dashboard server."""
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    start_dashboard()
