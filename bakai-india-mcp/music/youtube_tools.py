"""YouTube Search and Launcher Tools for BAKAI Robot.

Supports official YouTube Data API v3 integration with a resilient public video
metadata search fallback. Adheres to terms of service: does not extract protected streams,
bypass ads, or download copyrighted media. Generates Xiaozhi-compatible client actions.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus
import httpx

from core.config import settings
from core.logging import logger
from core.cache import cached
from core.security import sanitize_external_text


@cached(ttl=600, key_prefix="yt_search")
async def _search_official_api(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Searches YouTube using the official Google Data API v3 if API key is provided."""
    if not settings.YOUTUBE_API_KEY:
        return []

    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": limit,
        "key": settings.YOUTUBE_API_KEY,
        "regionCode": "IN",
    }
    try:
        async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT) as client:
            resp = await client.get(url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                items = []
                for item in data.get("items", []):
                    vid_id = item["id"].get("videoId")
                    snippet = item.get("snippet", {})
                    items.append({
                        "title": snippet.get("title", ""),
                        "channel": snippet.get("channelTitle", ""),
                        "video_id": vid_id,
                        "url": f"https://www.youtube.com/watch?v={vid_id}",
                        "published_at": snippet.get("publishedAt", ""),
                        "description": snippet.get("description", ""),
                    })
                return items
            else:
                logger.warning(f"YouTube API returned status {resp.status_code}: {resp.text}")
    except Exception as exc:
        logger.error(f"Error querying YouTube API: {exc}")
    return []


@cached(ttl=600, key_prefix="yt_fallback")
async def _search_public_fallback(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Resilient fallback search using DDGS video index."""
    items = []
    try:
        from duckduckgo_search import DDGS
        ddgs = DDGS()
        raw = ddgs.videos(query, max_results=limit)
        for r in raw:
            title = sanitize_external_text(r.get("title", ""))
            content_url = r.get("content", "")
            # Extract video ID if it's a youtube watch URL
            vid_match = re.search(r"v=([a-zA-Z0-9_-]{11})", content_url)
            vid_id = vid_match.group(1) if vid_match else None
            watch_url = f"https://www.youtube.com/watch?v={vid_id}" if vid_id else content_url

            items.append({
                "title": title,
                "channel": r.get("uploader", "YouTube Creator"),
                "video_id": vid_id or "",
                "url": watch_url,
                "published_at": r.get("published", ""),
                "description": r.get("description", ""),
            })
    except Exception as exc:
        logger.warning(f"Public YouTube search fallback failed: {exc}")
    return items


# ----------------------------------------------------------------------
# YouTube Tools
# ----------------------------------------------------------------------

async def youtube_search(query: str, limit: int = 5) -> Dict[str, Any]:
    """Searches YouTube for videos, songs, or channels.

    Returns verified titles, channels, and video links.

    Args:
        query: Search term (e.g. 'Arijit Singh Kesariya', 'ESP32 tutorial hindi', 'Bihu folk dance').
        limit: Max results (default 5, max 10).
    """
    limit = min(max(1, limit), 10)
    items = await _search_official_api(query, limit=limit)
    if not items:
        items = await _search_public_fallback(query, limit=limit)

    count = len(items)
    if count > 0:
        top = items[0]
        speech = (
            f"बॉस, मुझे YouTube पर '{top['title']}' मिला है, जिसे {top['channel']} ने प्रकाशित किया है। "
            f"क्या आप इसे चलाना चाहते हैं?"
        )
    else:
        speech = f"माफ़ कीजिए बॉस, YouTube पर '{query}' के लिए कोई परिणाम नहीं मिला।"

    return {
        "status": "success" if count > 0 else "not_found",
        "query": query,
        "count": count,
        "videos": items[:limit],
        "speech": speech,
    }


async def youtube_open(query: str) -> Dict[str, Any]:
    """Generates an official YouTube playback action to open the requested video or search query on the user's connected screen or app.

    Args:
        query: Song or video to open (e.g. 'Arijit Singh songs', 'https://www.youtube.com/watch?v=...').
    """
    # Check if query is already a YouTube URL
    url_match = re.search(r"(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})", query)
    if url_match:
        vid_id = url_match.group(1)
        watch_url = f"https://www.youtube.com/watch?v={vid_id}"
        title = "YouTube Video"
    else:
        # Search for best match
        search_res = await youtube_search(query, limit=1)
        videos = search_res.get("videos", [])
        if videos:
            top = videos[0]
            watch_url = top["url"]
            title = top["title"]
        else:
            # Fallback search URL
            watch_url = f"https://www.youtube.com/results?search_query={quote_plus(query)}"
            title = query

    speech = f"बॉस, YouTube पर '{title}' खोल रहा हूँ।"

    return {
        "status": "success",
        "target": title,
        "url": watch_url,
        "speech": speech,
        "robot_action": {
            "action": "open_url",
            "url": watch_url,
            "app": "youtube",
            "title": title,
        },
    }
