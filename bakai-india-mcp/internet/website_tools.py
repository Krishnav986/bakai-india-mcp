"""Website Inspection and Connectivity Tools for BAKAI Robot."""

from __future__ import annotations

from typing import Any, Dict
from urllib.parse import urlparse
import httpx

from core.config import settings
from core.logging import logger
from core.security import validate_safe_url, is_domain_allowed


async def check_website_status(url: str) -> Dict[str, Any]:
    """Checks whether an approved website is online and responsive.

    Args:
        url: URL to inspect (must be on safe allowlist).
    """
    is_safe, checked = validate_safe_url(url)
    if not is_safe:
        return {
            "status": "blocked",
            "url": url,
            "error": checked,
            "speech": f"यह वेबसाइट सुरक्षा कारणों से जाँची नहीं जा सकती, बॉस: {checked}",
        }

    try:
        async with httpx.AsyncClient(headers={"User-Agent": settings.USER_AGENT}, timeout=5.0) as client:
            resp = await client.head(checked, follow_redirects=True)
            status_code = resp.status_code
            is_up = 200 <= status_code < 400
            domain = urlparse(checked).hostname

            speech = (
                f"हाँ बॉस, {domain} सक्रिय है और इसका स्टेटस कोड {status_code} है।"
                if is_up else
                f"बॉस, {domain} इस समय अनुत्तरदायी लग रहा है (कोड {status_code})।"
            )

            return {
                "status": "online" if is_up else "error",
                "http_code": status_code,
                "url": checked,
                "domain": domain,
                "speech": speech,
            }
    except Exception as exc:
        return {
            "status": "unreachable",
            "url": url,
            "error": str(exc),
            "speech": f"माफ़ कीजिए बॉस, {url} तक पहुँचा नहीं जा सका: {exc}",
        }
