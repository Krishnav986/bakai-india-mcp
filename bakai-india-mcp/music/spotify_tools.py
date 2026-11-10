"""Spotify Integration and Music Playback Controls for BAKAI Robot.

Supports official Spotify Web API client credentials search, deep-linking (spotify:track:...),
and Xiaozhi hardware audio player controls (play, pause, next, volume).
Reports playback status honestly and conforms to Spotify Developer Terms.
"""

from __future__ import annotations

import base64
import time
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus
import httpx

from core.config import settings
from core.logging import logger
from core.cache import cache, cached


class MusicPlayerState:
    """Tracks active music playback on the robot."""

    def __init__(self) -> None:
        self.is_playing: bool = False
        self.current_track: Optional[Dict[str, Any]] = None
        self.volume: int = 70  # 0 to 100
        self.source: str = "none"

    def set_track(self, track: Dict[str, Any], source: str = "spotify") -> None:
        self.current_track = track
        self.is_playing = True
        self.source = source

    def control(self, action: str) -> Tuple[bool, str]:
        act = action.strip().lower()
        if act in ("pause", "stop"):
            self.is_playing = False
            return True, "संगीति रोक दी गई है।"
        elif act in ("play", "resume"):
            self.is_playing = True
            if self.current_track:
                return True, f"'{self.current_track.get('title', 'गाना')}' फिर से शुरू किया जा रहा है।"
            return True, "संगीति शुरू की जा रही है।"
        elif act == "next":
            return True, "अगला गाना शुरू किया जा रहा है।"
        elif act == "previous":
            return True, "पिछला गाना शुरू किया जा रहा है।"
        elif act == "volume_up":
            self.volume = min(100, self.volume + 10)
            return True, f"आवाज़ बढ़ाकर {self.volume}% कर दी गई है।"
        elif act == "volume_down":
            self.volume = max(0, self.volume - 10)
            return True, f"आवाज़ घटाकर {self.volume}% कर दी गई है।"
        else:
            return False, f"अमान्य नियंत्रण आदेश: {action}"


music_state = MusicPlayerState()
from typing import Tuple


async def _get_spotify_access_token() -> Optional[str]:
    """Obtains a client credentials OAuth token from Spotify Accounts service."""
    if not settings.SPOTIFY_CLIENT_ID or not settings.SPOTIFY_CLIENT_SECRET:
        return None

    cache_key = "spotify_oauth_token"
    token = await cache.get(cache_key)
    if token:
        return token

    auth_header = base64.b64encode(
        f"{settings.SPOTIFY_CLIENT_ID}:{settings.SPOTIFY_CLIENT_SECRET}".encode("utf-8")
    ).decode("utf-8")

    try:
        async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT) as client:
            resp = await client.post(
                "https://accounts.spotify.com/api/token",
                headers={
                    "Authorization": f"Basic {auth_header}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={"grant_type": "client_credentials"},
            )
            if resp.status_code == 200:
                data = resp.json()
                access_token = data.get("access_token")
                expires_in = data.get("expires_in", 3600) - 60
                await cache.set(cache_key, access_token, ttl=expires_in)
                return access_token
            else:
                logger.warning(f"Spotify token request rejected ({resp.status_code}): {resp.text}")
    except Exception as exc:
        logger.error(f"Failed to obtain Spotify token: {exc}")
    return None


# ----------------------------------------------------------------------
# Spotify Tools
# ----------------------------------------------------------------------

async def spotify_search(query: str, limit: int = 5) -> Dict[str, Any]:
    """Searches Spotify's official music catalog for tracks, artists, and albums.

    Args:
        query: Song or artist query (e.g. 'Arijit Singh Tum Hi Ho', 'Bhupen Hazarika Dil Hoom Hoom Kare').
        limit: Max results (default 5, max 10).
    """
    limit = min(max(1, limit), 10)
    token = await _get_spotify_access_token()

    if token:
        try:
            async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT) as client:
                resp = await client.get(
                    "https://api.spotify.com/v1/search",
                    headers={"Authorization": f"Bearer {token}"},
                    params={"q": query, "type": "track", "market": "IN", "limit": limit},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    tracks = []
                    for t in data.get("tracks", {}).get("items", []):
                        artists = ", ".join(a["name"] for a in t.get("artists", []))
                        tracks.append({
                            "title": t.get("name"),
                            "artist": artists,
                            "album": t.get("album", {}).get("name"),
                            "duration_ms": t.get("duration_ms"),
                            "duration_seconds": round(t.get("duration_ms", 0) / 1000),
                            "spotify_uri": t.get("uri"),
                            "spotify_url": t.get("external_urls", {}).get("spotify"),
                            "popularity": t.get("popularity"),
                        })

                    count = len(tracks)
                    if count > 0:
                        top = tracks[0]
                        speech = (
                            f"बॉस, Spotify पर '{top['title']}' ({top['artist']}) मिला है। "
                            f"क्या आप इसे Spotify पर खोलना चाहते हैं?"
                        )
                    else:
                        speech = f"माफ़ कीजिए बॉस, Spotify पर '{query}' के लिए कोई गाना नहीं मिला।"

                    return {
                        "status": "success" if count > 0 else "not_found",
                        "query": query,
                        "source": "spotify_api",
                        "count": count,
                        "tracks": tracks,
                        "speech": speech,
                    }
        except Exception as exc:
            logger.error(f"Spotify API search failed: {exc}")

    # Fallback when Spotify credentials are not configured in .env
    encoded = quote_plus(query)
    web_url = f"https://open.spotify.com/search/{encoded}"
    app_uri = f"spotify:search:{encoded}"
    speech = (
        f"बॉस, Spotify पर '{query}' खोजने के लिए लिंक तैयार है। "
        f"पूर्ण आधिकारिक सूची के लिए .env में SPOTIFY_CLIENT_ID जोड़ें।"
    )

    return {
        "status": "configured_link",
        "query": query,
        "source": "spotify_search_link",
        "search_url": web_url,
        "spotify_uri": app_uri,
        "tracks": [
            {
                "title": query,
                "artist": "Search Query",
                "spotify_url": web_url,
                "spotify_uri": app_uri,
            }
        ],
        "speech": speech,
        "note": "Configure SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET in .env for full metadata search.",
    }


async def spotify_open(query: str) -> Dict[str, Any]:
    """Generates an action to open the requested song, artist, or playlist on Spotify app or browser.

    Args:
        query: Track name, artist, or Spotify URL/URI (e.g. 'Dil Hoom Hoom Kare', 'spotify:track:...').
    """
    if query.startswith("spotify:"):
        uri = query
        url = f"https://open.spotify.com/{query.split(':')[1]}/{query.split(':')[2]}" if len(query.split(':')) >= 3 else "https://open.spotify.com"
        title = "Spotify Item"
    elif "open.spotify.com" in query:
        url = query
        uri = f"spotify:{query.split('/')[-2]}:{query.split('/')[-1].split('?')[0]}"
        title = "Spotify Item"
    else:
        # Search for track details first
        search_res = await spotify_search(query, limit=1)
        tracks = search_res.get("tracks", [])
        if tracks:
            top = tracks[0]
            url = top.get("spotify_url", f"https://open.spotify.com/search/{quote_plus(query)}")
            uri = top.get("spotify_uri", f"spotify:search:{quote_plus(query)}")
            title = f"{top.get('title')} - {top.get('artist')}"
        else:
            url = f"https://open.spotify.com/search/{quote_plus(query)}"
            uri = f"spotify:search:{quote_plus(query)}"
            title = query

    speech = f"हाँ बॉस, Spotify पर '{title}' खोल रहा हूँ।"

    return {
        "status": "success",
        "title": title,
        "url": url,
        "spotify_uri": uri,
        "speech": speech,
        "robot_action": {
            "action": "open_app",
            "app": "spotify",
            "uri": uri,
            "url": url,
            "title": title,
        },
    }


async def music_control(action: str) -> Dict[str, Any]:
    """Controls music playback on BAKAI (play, pause, stop, resume, next, previous, volume_up, volume_down).

    Args:
        action: Control command ('play', 'pause', 'stop', 'resume', 'next', 'previous', 'volume_up', 'volume_down').
    """
    valid_actions = {
        "play", "pause", "stop", "resume", "next", "previous",
        "volume_up", "volume_down", "mute"
    }
    normalized = action.strip().lower()

    if normalized not in valid_actions:
        return {
            "status": "invalid_action",
            "speech": f"माफ़ कीजिए बॉस, '{action}' अमान्य आदेश है। आप play, pause, next या volume_up कह सकते हैं।",
            "robot_action": None,
        }

    success, speech = music_state.control(normalized)

    return {
        "status": "success" if success else "failed",
        "action": normalized,
        "volume": music_state.volume,
        "is_playing": music_state.is_playing,
        "speech": speech,
        "robot_action": {
            "action": f"player_{normalized}",
            "volume": music_state.volume,
        },
    }


async def music_now_playing() -> Dict[str, Any]:
    """Checks what music track is currently active or playing on the robot."""
    if music_state.is_playing and music_state.current_track:
        track = music_state.current_track
        title = track.get("title", "Unknown")
        artist = track.get("artist", "")
        speech = f"अभी '{title}' {f'({artist})' if artist else ''} बज रहा है, आवाज़ {music_state.volume}% है।"
        return {
            "status": "playing",
            "is_playing": True,
            "source": music_state.source,
            "track": track,
            "volume": music_state.volume,
            "speech": speech,
        }
    else:
        return {
            "status": "idle",
            "is_playing": False,
            "source": "none",
            "track": None,
            "volume": music_state.volume,
            "speech": "इस समय कोई संगीत नहीं बज रहा है, बॉस।",
        }
