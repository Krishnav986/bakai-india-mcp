"""Cricket live score and schedule tools via API-Sports Cricket."""

from __future__ import annotations

import datetime as dt
from typing import Any, Dict, Optional

from core.config import settings
from utilities.live_api import ProviderError, invalid_input, missing_credential, provider_error, request_json

_CRICKET_API_URL = "https://v1.cricket.api-sports.io/games"


async def _games(params: Dict[str, Any]) -> Dict[str, Any]:
    try:
        payload = await request_json(
            _CRICKET_API_URL,
            params=params,
            headers={"x-apisports-key": settings.CRICKET_API_KEY or ""},
        )
    except ProviderError as exc:
        return provider_error("API-Sports Cricket", exc)
    if payload.get("errors"):
        return provider_error("API-Sports Cricket", ProviderError("The cricket provider rejected the request."))
    games = payload.get("response")
    if not isinstance(games, list):
        return provider_error("API-Sports Cricket", ProviderError("No cricket match list was returned."))
    return {
        "status": "success",
        "provider": "API-Sports Cricket",
        "count": len(games),
        "matches": games,
        "source_url": "https://api-sports.io/documentation/cricket/v1",
    }


async def cricket_live_score() -> Dict[str, Any]:
    """Fetch currently live cricket games from the documented API-Sports Cricket API."""
    if not settings.CRICKET_API_KEY:
        return missing_credential("API-Sports Cricket", "CRICKET_API_KEY")
    return await _games({"live": "all"})


async def cricket_schedule(match_date: Optional[str] = None) -> Dict[str, Any]:
    """Fetch the cricket fixtures scheduled on a date (today by default)."""
    if match_date is None:
        match_date = dt.date.today().isoformat()
    try:
        parsed_date = dt.date.fromisoformat(match_date)
    except (TypeError, ValueError):
        return invalid_input("match_date must use YYYY-MM-DD format.")
    if parsed_date.isoformat() != match_date:
        return invalid_input("match_date must use YYYY-MM-DD format.")
    if not settings.CRICKET_API_KEY:
        return missing_credential("API-Sports Cricket", "CRICKET_API_KEY")
    result = await _games({"date": match_date})
    if result.get("status") == "success":
        result["match_date"] = match_date
    return result
