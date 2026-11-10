from __future__ import annotations

import asyncio
import hmac
import secrets
import time
from typing import Any

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from core.config import settings


_pending: dict[str, dict[str, Any]] = {}
_queue: asyncio.Queue = asyncio.Queue(maxsize=20)
MAX_PENDING = 20
REQUEST_TIMEOUT = 45


def authorized(request: Request) -> bool:
    expected = settings.PHONE_GATEWAY_TOKEN
    supplied = request.headers.get("authorization", "")

    if not expected or not supplied.startswith("Bearer "):
        return False

    return hmac.compare_digest(
        supplied[7:],
        expected
    )


async def health(request: Request):
    if not authorized(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    return JSONResponse({"status": "online"})


async def poll(request: Request):
    if not authorized(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    try:
        request_id = await asyncio.wait_for(
            _queue.get(),
            timeout=20
        )
    except asyncio.TimeoutError:
        return JSONResponse({"request": None})

    item = _pending.get(request_id)

    if not item or item["expires"] < time.monotonic():
        return JSONResponse({"request": None})

    return JSONResponse({
        "request": {
            "id": request_id,
            "query": item["query"]
        }
    })


async def submit_result(request: Request):
    if not authorized(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    try:
        data = await request.json()
        request_id = str(data.get("id", ""))
        name = str(data.get("name", "")).strip()
        number = str(data.get("number", "")).strip()

        if not request_id or not name or not number:
            return JSONResponse({"error": "Invalid data"}, status_code=400)

        if len(name) > 120 or len(number) > 40:
            return JSONResponse({"error": "Data too long"}, status_code=400)

        item = _pending.get(request_id)

        if not item or item["expires"] < time.monotonic():
            return JSONResponse({"error": "Request expired"}, status_code=404)

        if item["result"] is not None:
            return JSONResponse({"error": "Already completed"}, status_code=409)

        item["result"] = {
            "name": name,
            "number": number
        }

        item["event"].set()

        return JSONResponse({"status": "received"})

    except Exception:
        return JSONResponse({"error": "Invalid request"}, status_code=400)


async def find_contact(query: str) -> dict[str, Any]:
    query = str(query).strip()

    if not query or len(query) > 100:
        return {"status": "error", "message": "Enter a valid contact name."}

    if len(_pending) >= MAX_PENDING:
        return {"status": "error", "message": "Phone gateway is busy."}

    request_id = secrets.token_urlsafe(18)
    event = asyncio.Event()

    item = {
        "query": query,
        "event": event,
        "result": None,
        "expires": time.monotonic() + REQUEST_TIMEOUT
    }

    _pending[request_id] = item

    try:
        await _queue.put(request_id)

        try:
            await asyncio.wait_for(event.wait(), timeout=REQUEST_TIMEOUT)
        except asyncio.TimeoutError:
            return {
                "status": "timeout",
                "message": "No contact was selected on the phone."
            }

        return {
            "status": "success",
            "contact": item["result"],
            "message": "Contact selected by the phone user."
        }

    finally:
        _pending.pop(request_id, None)


async def cleanup():
    while True:
        await asyncio.sleep(15)

        now = time.monotonic()

        expired = [
            key for key, value in _pending.items()
            if value["expires"] < now
        ]

        for key in expired:
            _pending.pop(key, None)


routes = [
    Route("/phone/health", health, methods=["GET"]),
    Route("/phone/poll", poll, methods=["GET"]),
    Route("/phone/result", submit_result, methods=["POST"]),
]

app = Starlette(routes=routes)
