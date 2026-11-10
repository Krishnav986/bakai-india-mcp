"""Indian Radio Management and Playback Service for BAKAI Robot.

Supports All India Radio (Akashvani), Vividh Bharati, FM Gold/Rainbow,
Assamese and Northeast stations, regional Indian languages, and verified online FM streams.
Provides stream verification, fallback switching, and Xiaozhi robot action payloads.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import httpx

from core.config import settings
from core.logging import logger
from core.cache import cache, cached


class RadioStateManager:
    """Maintains active radio playback state across tool invocations."""

    def __init__(self) -> None:
        self.current_station: Optional[Dict[str, Any]] = None
        self.is_playing: bool = False
        self.started_at: Optional[float] = None

    def set_playing(self, station: Dict[str, Any]) -> None:
        import time
        self.current_station = station
        self.is_playing = True
        self.started_at = time.time()

    def stop(self) -> Optional[Dict[str, Any]]:
        prev = self.current_station
        self.current_station = None
        self.is_playing = False
        self.started_at = None
        return prev

    def get_state(self) -> Dict[str, Any]:
        return {
            "is_playing": self.is_playing,
            "station": self.current_station,
            "elapsed_seconds": int(time.time() - self.started_at) if self.started_at and self.is_playing else 0,
        }


import time

radio_state = RadioStateManager()


def _load_stations_db() -> List[Dict[str, Any]]:
    """Loads station records from the local curated JSON file."""
    path = settings.RADIO_DB_PATH
    if not path.exists():
        logger.warning(f"Radio database file not found at {path}")
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        logger.error(f"Failed to read radio database: {exc}")
        return []


async def verify_stream_url(url: str, timeout: float = 3.5) -> bool:
    """Checks whether an audio stream endpoint is reachable and responding."""
    cache_key = f"stream_status:{url}"
    cached_status = await cache.get(cache_key)
    if cached_status is not None:
        return cached_status

    try:
        async with httpx.AsyncClient(
            headers={"User-Agent": settings.USER_AGENT, "Range": "bytes=0-512"},
            follow_redirects=True,
            timeout=timeout,
        ) as client:
            # First try HEAD
            try:
                head_resp = await client.head(url)
                if head_resp.status_code in (200, 206, 302):
                    await cache.set(cache_key, True, ttl=600)
                    return True
            except Exception:
                pass

            # Fallback to GET stream
            async with client.stream("GET", url) as resp:
                is_working = resp.status_code in (200, 206)
                await cache.set(cache_key, is_working, ttl=600)
                return is_working
    except Exception as exc:
        logger.debug(f"Stream verification failed for {url}: {exc}")
        await cache.set(cache_key, False, ttl=180)
        return False


async def get_working_stream(station: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    """Verifies primary stream URL, and falls back to alternatives if necessary.

    Returns:
        (working_stream_url, format_type)
    """
    primary = station.get("stream_url")
    if primary and await verify_stream_url(primary):
        return primary, station.get("format", "hls")

    # Check fallbacks
    for fallback in station.get("fallback_urls", []):
        if await verify_stream_url(fallback):
            logger.info(f"Primary stream down for '{station['name']}', using fallback: {fallback}")
            fmt = "hls" if ".m3u8" in fallback else "mp3"
            return fallback, fmt

    return None, None


# ----------------------------------------------------------------------
# Tool Implementations
# ----------------------------------------------------------------------

async def india_radio_list(
    language: Optional[str] = None,
    region: Optional[str] = None,
    category: Optional[str] = None,
) -> Dict[str, Any]:
    """Lists available Indian radio stations filtered by language, region, or category.

    Args:
        language: Filter by language (e.g. 'hindi', 'assamese', 'bengali', 'tamil', 'punjabi', 'english').
        region: Filter by region (e.g. 'National', 'Assam & Northeast', 'West Bengal', 'Delhi').
        category: Filter by category (e.g. 'all_india_radio', 'regional', 'bollywood', 'classical').
    """
    stations = _load_stations_db()
    filtered = []

    for s in stations:
        if language and language.lower() not in s.get("language", "").lower():
            continue
        if region and region.lower() not in s.get("region", "").lower():
            continue
        if category and category.lower() not in s.get("category", "").lower():
            continue
        filtered.append({
            "id": s["id"],
            "name": s["name"],
            "language": s["language"],
            "region": s["region"],
            "city": s["city"],
            "category": s["category"],
            "format": s["format"],
            "description": s["description"],
        })

    count = len(filtered)
    filter_desc = []
    if language:
        filter_desc.append(f"भाषा: {language}")
    if region:
        filter_desc.append(f"क्षेत्र: {region}")
    if category:
        filter_desc.append(f"श्रेणी: {category}")

    desc_str = f" ({', '.join(filter_desc)})" if filter_desc else ""
    speech = (
        f"बॉस, मुझे {count} भारतीय रेडियो स्टेशन मिले हैं{desc_str}। "
        f"प्रमुख स्टेशन हैं: {', '.join([s['name'] for s in filtered[:4]])}।"
        if count > 0 else
        f"माफ़ कीजिए बॉस, दिए गए फ़िल्टर{desc_str} के अनुसार कोई स्टेशन नहीं मिला।"
    )

    return {
        "status": "success",
        "count": count,
        "stations": filtered,
        "speech": speech,
    }


async def radio_search(
    query: str,
    language: Optional[str] = None,
    city: Optional[str] = None,
) -> Dict[str, Any]:
    """Searches for Indian radio stations by name, keyword, city, or language.

    Args:
        query: Search term (e.g. 'vividh bharati', 'guwahati', 'assam', 'fm gold', 'retro').
        language: Optional language filter (e.g. 'hindi', 'assamese', 'tamil').
        city: Optional city filter (e.g. 'Delhi', 'Guwahati', 'Mumbai', 'Kolkata').
    """
    q = query.strip().lower()
    stations = _load_stations_db()
    matches = []

    # 1. Check local curated stations
    for s in stations:
        name_match = q in s["name"].lower()
        alias_match = any(q in alias.lower() for alias in s.get("aliases", []))
        city_match = city is not None and city.lower() in s.get("city", "").lower()
        lang_match = language is not None and language.lower() in s.get("language", "").lower()
        cat_match = q in s.get("category", "").lower() or q in s.get("description", "").lower()

        if (name_match or alias_match or cat_match):
            if (language is None or lang_match) and (city is None or city_match):
                matches.append(s)

    # 2. Dynamic fallback search via Radio Browser if local search yields few results
    if len(matches) == 0:
        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                params = {"country": "India", "name": query, "limit": 5}
                if language:
                    params["language"] = language
                resp = await client.get("https://de1.api.radio-browser.info/json/stations/search", params=params)
                if resp.status_code == 200:
                    for item in resp.json():
                        matches.append({
                            "id": f"rb_{item.get('stationuuid', '')[:8]}",
                            "name": item.get("name", "Unknown Station"),
                            "language": item.get("language", language or "hindi"),
                            "region": item.get("state", "India"),
                            "city": item.get("state", "India"),
                            "category": "online_stream",
                            "stream_url": item.get("url_resolved"),
                            "fallback_urls": [item.get("url")],
                            "format": "mp3" if "mp3" in item.get("codec", "").lower() else "aac",
                            "playable": True,
                            "official_source": "Radio Browser Network",
                            "description": f"Live online stream: {item.get('name')}",
                        })
        except Exception as exc:
            logger.debug(f"Dynamic radio-browser query failed: {exc}")

    count = len(matches)
    if count > 0:
        best = matches[0]
        speech = f"हाँ बॉस, मुझे '{query}' के लिए {best['name']} मिला है। क्या आप इसे सुनना चाहेंगे?"
    else:
        speech = f"माफ़ कीजिए बॉस, '{query}' नाम का कोई रेडियो स्टेशन नहीं मिला। आप विविध भारती या एफएम गोल्ड सुन सकते हैं।"

    return {
        "status": "success" if count > 0 else "not_found",
        "query": query,
        "count": count,
        "results": [
            {
                "id": s["id"],
                "name": s["name"],
                "language": s.get("language"),
                "region": s.get("region"),
                "city": s.get("city"),
                "stream_url": s.get("stream_url"),
                "format": s.get("format"),
                "description": s.get("description"),
            }
            for s in matches
        ],
        "speech": speech,
    }


async def radio_play(station_name: str) -> Dict[str, Any]:
    """Plays an Indian radio station on the BAKAI robot by name or keyword.

    Verifies the stream before launching and returns a Xiaozhi robot action payload.

    Args:
        station_name: Name or alias of the station (e.g. 'vividh bharati', 'assam radio', 'fm gold', 'retro bollywood').
    """
    q = station_name.strip().lower()
    stations = _load_stations_db()

    target_station = None

    # Exact alias/name matching first
    for s in stations:
        if q == s["name"].lower() or any(q == alias.lower() for alias in s.get("aliases", [])):
            target_station = s
            break

    # Partial matching if no exact match
    if not target_station:
        for s in stations:
            if q in s["name"].lower() or any(q in alias.lower() for alias in s.get("aliases", [])):
                target_station = s
                break

    # Search keyword match (e.g. 'assam', 'punjabi', 'tamil')
    if not target_station:
        for s in stations:
            if (
                q in s.get("language", "").lower()
                or q in s.get("region", "").lower()
                or q in s.get("category", "").lower()
            ):
                target_station = s
                break

    if not target_station:
        return {
            "status": "not_found",
            "speech": f"माफ़ कीजिए बॉस, '{station_name}' नहीं मिला। आप 'विविध भारती' या 'एफएम गोल्ड' चला सकते हैं।",
            "robot_action": None,
        }

    # Verify stream health
    working_url, stream_format = await get_working_stream(target_station)
    if not working_url:
        # Suggest alternative station in same language or Vividh Bharati
        alt = stations[0]
        return {
            "status": "stream_unavailable",
            "station": target_station["name"],
            "speech": (
                f"माफ़ कीजिए बॉस, {target_station['name']} का लाइव स्ट्रीम इस समय उपलब्ध नहीं है। "
                f"क्या मैं {alt['name']} चला दूँ?"
            ),
            "alternative_station": alt["name"],
            "robot_action": None,
        }

    # Update active state
    active_record = {
        "id": target_station["id"],
        "name": target_station["name"],
        "url": working_url,
        "format": stream_format,
        "language": target_station.get("language"),
        "city": target_station.get("city"),
    }
    radio_state.set_playing(active_record)

    speech = f"हाँ बॉस, {target_station['name']} शुरू कर रहा हूँ।"

    return {
        "status": "playing",
        "station": target_station["name"],
        "stream_url": working_url,
        "format": stream_format,
        "language": target_station.get("language"),
        "speech": speech,
        "robot_action": {
            "action": "play_audio",
            "url": working_url,
            "format": stream_format,
            "title": target_station["name"],
            "type": "live_stream",
        },
    }


async def radio_stop() -> Dict[str, Any]:
    """Stops the currently playing radio broadcast on BAKAI."""
    prev = radio_state.stop()
    if prev:
        speech = f"रेडियो {prev.get('name', '')} रोक दिया गया है, बॉस।"
    else:
        speech = "इस समय कोई रेडियो स्टेशन नहीं चल रहा है, बॉस।"

    return {
        "status": "stopped",
        "previous_station": prev.get("name") if prev else None,
        "speech": speech,
        "robot_action": {
            "action": "stop_audio",
        },
    }


async def radio_now_playing() -> Dict[str, Any]:
    """Returns details of the currently playing radio station."""
    state = radio_state.get_state()
    if state["is_playing"] and state["station"]:
        st = state["station"]
        elapsed = state["elapsed_seconds"]
        minutes = elapsed // 60
        speech = f"अभी {st['name']} चल रहा है, जो {minutes} मिनट से सक्रिय है।"
        return {
            "status": "active",
            "is_playing": True,
            "station": st,
            "elapsed_seconds": elapsed,
            "speech": speech,
        }
    else:
        return {
            "status": "idle",
            "is_playing": False,
            "station": None,
            "speech": "इस समय कोई रेडियो नहीं चल रहा है।",
        }
