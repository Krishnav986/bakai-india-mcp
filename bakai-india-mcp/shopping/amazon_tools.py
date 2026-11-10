"""Amazon India Search, Product Inspection, and Safe Website Launchers.

Provides safe searching on Amazon India (amazon.in), product URL validation,
ASIN extraction, and safe website opening using strict allowlists.
Guarantees no automatic purchases or account modifications.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus, urlparse

from core.logging import logger
from core.security import is_domain_allowed, validate_safe_url, SAFE_WEBSITE_DOMAINS


# Common trusted Indian and Global portals directory
SERVICE_DIRECTORY: Dict[str, Dict[str, str]] = {
    "amazon": {
        "name": "Amazon India",
        "url": "https://www.amazon.in",
        "category": "shopping",
        "description": "India's online marketplace for electronics, books, essentials.",
    },
    "flipkart": {
        "name": "Flipkart",
        "url": "https://www.flipkart.com",
        "category": "shopping",
        "description": "Indian e-commerce platform.",
    },
    "spotify": {
        "name": "Spotify Web Player",
        "url": "https://open.spotify.com",
        "category": "music",
        "description": "Music and podcast streaming service.",
    },
    "youtube": {
        "name": "YouTube",
        "url": "https://www.youtube.com",
        "category": "video",
        "description": "Video sharing and streaming platform.",
    },
    "google": {
        "name": "Google India",
        "url": "https://www.google.co.in",
        "category": "search",
        "description": "Web search engine.",
    },
    "gmail": {
        "name": "Google Gmail",
        "url": "https://mail.google.com",
        "category": "email",
        "description": "Google email service.",
    },
    "maps": {
        "name": "Google Maps",
        "url": "https://maps.google.com",
        "category": "navigation",
        "description": "Maps, satellite imagery, and navigation.",
    },
    "wikipedia": {
        "name": "Wikipedia",
        "url": "https://en.wikipedia.org",
        "category": "knowledge",
        "description": "Free open encyclopedia.",
    },
    "irctc": {
        "name": "IRCTC Official Train Booking",
        "url": "https://www.irctc.co.in/nget/",
        "category": "travel",
        "description": "Indian Railways catering and ticket booking portal.",
    },
    "digilocker": {
        "name": "DigiLocker India",
        "url": "https://www.digilocker.gov.in",
        "category": "government",
        "description": "National Digital Wallet for government documents (Aadhaar, Driving License, Marks sheets).",
    },
    "indiagov": {
        "name": "National Portal of India",
        "url": "https://www.india.gov.in",
        "category": "government",
        "description": "Single window access to Indian Government information and services.",
    },
    "swiggy": {
        "name": "Swiggy",
        "url": "https://www.swiggy.com",
        "category": "food",
        "description": "Online food ordering and quick commerce.",
    },
    "zomato": {
        "name": "Zomato",
        "url": "https://www.zomato.com",
        "category": "food",
        "description": "Restaurant search and food delivery platform.",
    },
}


def _extract_asin(url: str) -> Optional[str]:
    """Extracts Amazon 10-character ASIN from product URLs."""
    patterns = [
        r"/dp/([A-Z0-9]{10})",
        r"/gp/product/([A-Z0-9]{10})",
        r"/ASIN/([A-Z0-9]{10})",
        r"/product/([A-Z0-9]{10})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url, re.IGNORECASE)
        if match:
            return match.group(1).upper()
    return None


# ----------------------------------------------------------------------
# Shopping & Launcher Tools
# ----------------------------------------------------------------------

async def amazon_search(query: str) -> Dict[str, Any]:
    """Searches Amazon India (amazon.in) for products and returns verified search and category URLs.

    Args:
        query: Product to search (e.g. 'ESP32 development board', 'I2S DAC MAX98357A', 'boAt headphones').
    """
    clean_q = query.strip()
    encoded = quote_plus(clean_q)
    search_url = f"https://www.amazon.in/s?k={encoded}&ref=nb_sb_noss"

    speech = (
        f"बॉस, Amazon India पर '{clean_q}' खोजने के लिए लिंक तैयार है: "
        f"आप इसे अपने ब्राउज़र या मोबाइल ऐप पर देख सकते हैं।"
    )

    return {
        "status": "success",
        "platform": "Amazon India",
        "query": clean_q,
        "search_url": search_url,
        "region": "IN",
        "currency": "INR",
        "speech": speech,
        "robot_action": {
            "action": "open_url",
            "url": search_url,
            "title": f"Amazon India - {clean_q}",
            "app": "browser",
        },
    }


async def amazon_product_info(product_url: str) -> Dict[str, Any]:
    """Inspects and validates an Amazon product URL, extracting its verified ASIN and canonical product link.

    Guarantees safe URL parameters without tracker bloat and protects against SSRF.

    Args:
        product_url: Amazon product URL (e.g. 'https://www.amazon.in/dp/B08N5WRWNW').
    """
    is_safe, canonical = validate_safe_url(product_url)
    if not is_safe:
        return {
            "status": "error",
            "speech": f"अमान्य या असुरक्षित लिंक है, बॉस: {canonical}",
            "error": canonical,
        }

    parsed = urlparse(canonical)
    host = (parsed.hostname or "").lower()

    if "amazon." not in host:
        return {
            "status": "invalid_domain",
            "speech": "यह लिंक Amazon का नहीं है, कृपया Amazon India का मान्य लिंक दें।",
            "domain": host,
        }

    asin = _extract_asin(canonical)
    if not asin:
        return {
            "status": "asin_not_found",
            "speech": "इस लिंक में उत्पाद की ASIN पहचान संख्या नहीं मिली।",
            "original_url": canonical,
        }

    clean_product_url = f"https://www.amazon.in/dp/{asin}"
    speech = f"बॉस, Amazon उत्पाद की पहचान संख्या (ASIN) {asin} है। इसका सुरक्षित लिंक तैयार है।"

    return {
        "status": "success",
        "asin": asin,
        "clean_url": clean_product_url,
        "original_url": canonical,
        "speech": speech,
        "robot_action": {
            "action": "open_url",
            "url": clean_product_url,
            "title": f"Amazon Product {asin}",
        },
    }


async def open_website(service: str) -> Dict[str, Any]:
    """Launches an approved Indian or international website/service from the secure allowlist.

    Supported services include: amazon, flipkart, spotify, youtube, google, gmail,
    maps, wikipedia, irctc, digilocker, indiagov, swiggy, zomato.

    Args:
        service: Name or shortcut of service (e.g. 'amazon', 'irctc', 'digilocker', 'spotify', 'maps').
    """
    key = service.strip().lower().replace(" ", "").replace("_", "")

    # Match in service directory
    entry = None
    for k, v in SERVICE_DIRECTORY.items():
        if key == k or key in k:
            entry = v
            break

    if not entry:
        # Check if the input is a valid URL directly
        if service.startswith("http://") or service.startswith("https://"):
            is_safe, checked_url = validate_safe_url(service)
            if is_safe and is_domain_allowed(checked_url):
                parsed = urlparse(checked_url)
                entry = {
                    "name": parsed.hostname or service,
                    "url": checked_url,
                    "category": "custom",
                    "description": "Approved allowlisted destination",
                }

    if not entry:
        return {
            "status": "unauthorized_or_unknown",
            "speech": (
                f"माफ़ कीजिए बॉस, '{service}' सुरक्षित सूची में नहीं है। "
                f"आप Amazon, Spotify, YouTube, IRCTC, DigiLocker या Google खोल सकते हैं।"
            ),
            "allowed_services": list(SERVICE_DIRECTORY.keys()),
            "robot_action": None,
        }

    speech = f"हाँ बॉस, {entry['name']} खोल रहा हूँ।"

    return {
        "status": "success",
        "service": entry["name"],
        "url": entry["url"],
        "category": entry.get("category"),
        "speech": speech,
        "robot_action": {
            "action": "open_url",
            "url": entry["url"],
            "title": entry["name"],
        },
    }


async def website_search(query: str) -> Dict[str, Any]:
    """Finds official websites and safe links for Indian and global organizations or services.

    Args:
        query: Entity or service to locate (e.g. 'IRCTC', 'Assam University official', 'Prasar Bharati').
    """
    from duckduckgo_search import DDGS
    clean_q = f"official website {query.strip()}"
    results = []

    try:
        ddgs = DDGS()
        raw = ddgs.text(clean_q, max_results=4, region="in-en")
        for r in raw:
            url = r.get("href", "")
            is_safe, checked = validate_safe_url(url)
            if is_safe:
                results.append({
                    "title": r.get("title", ""),
                    "url": checked,
                    "snippet": r.get("body", "")[:180],
                })
    except Exception as exc:
        logger.warning(f"Website search failed: {exc}")

    count = len(results)
    if count > 0:
        top = results[0]
        speech = f"बॉस, मुझे '{query}' की आधिकारिक वेबसाइट '{top['title']}' मिली है: {top['url']}।"
    else:
        speech = f"माफ़ कीजिए बॉस, '{query}' की आधिकारिक वेबसाइट नहीं मिल सकी।"

    return {
        "status": "success" if count > 0 else "not_found",
        "query": query,
        "count": count,
        "results": results,
        "speech": speech,
    }
