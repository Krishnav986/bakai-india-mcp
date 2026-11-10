"""Shared async HTTP helpers for live data integrations."""

from __future__ import annotations

from typing import Any, Dict, Optional

import httpx

from core.config import settings


class ProviderError(Exception):
    """A safe, user-facing provider failure without request credentials."""


async def request_json(
    url: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    method: str = "GET",
    form_data: Optional[Dict[str, str]] = None,
    json_body: Optional[Dict[str, Any]] = None,
    allow_list: bool = False,
) -> Any:
    """Make a bounded HTTP request and require a JSON object response."""
    try:
        async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT) as client:
            response = await client.request(
                method,
                url,
                params=params,
                headers=headers,
                data=form_data,
                json=json_body,
            )
    except httpx.TimeoutException as exc:
        raise ProviderError("The provider request timed out.") from exc
    except httpx.RequestError as exc:
        raise ProviderError("The provider could not be reached.") from exc

    if not response.is_success:
        raise ProviderError(f"The provider returned HTTP {response.status_code}.")

    try:
        payload = response.json()
    except ValueError as exc:
        raise ProviderError("The provider returned invalid JSON.") from exc

    if not isinstance(payload, dict) and not (allow_list and isinstance(payload, list)):
        raise ProviderError("The provider returned an unexpected response.")
    return payload


def provider_error(provider: str, exc: ProviderError) -> Dict[str, str]:
    """Create a consistent error response without leaking request URLs."""
    return {"status": "error", "provider": provider, "error": str(exc)}


def missing_credential(provider: str, variable: str) -> Dict[str, str]:
    """Explain which optional credential enables a provider integration."""
    return {
        "status": "not_configured",
        "provider": provider,
        "error": f"Configure {variable} to enable this live-data provider.",
    }


def invalid_input(message: str) -> Dict[str, str]:
    """Return a consistent validation error for tool callers."""
    return {"status": "invalid_input", "error": message}
