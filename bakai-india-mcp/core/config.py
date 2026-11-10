"""Configuration management for BAKAI India MCP Server.

Loads environment variables with robust defaults and validation.
Supports zero-key operation with smart public fallbacks for news, weather,
search, and radio.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load .env file from project root if present
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"
if _ENV_FILE.exists():
    load_dotenv(_ENV_FILE)
else:
    load_dotenv()


class Settings:
    """Server and integrations settings."""

    # Server Info
    SERVER_NAME: str = os.getenv("MCP_SERVER_NAME", "bakai-india-mcp")
    SERVER_VERSION: str = os.getenv("MCP_SERVER_VERSION", "1.0.0")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()

    # Network & Timeouts
    REQUEST_TIMEOUT: float = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "8.0"))
    RADIO_STREAM_TIMEOUT: float = float(os.getenv("RADIO_STREAM_TIMEOUT_SECONDS", "4.0"))
    CACHE_DEFAULT_TTL: int = int(os.getenv("CACHE_DEFAULT_TTL_SECONDS", "300"))
    USER_AGENT: str = os.getenv(
        "USER_AGENT",
        "BAKAI-Robot-Assistant/1.0 (Xiaozhi Ecosystem; +https://github.com/bakai-robot)",
    )

    # Robot Spoken Defaults
    DEFAULT_SPEECH_LANGUAGE: str = os.getenv("DEFAULT_SPEECH_LANGUAGE", "hi")
    VOICE_PERSONALITY_NAME: str = os.getenv("VOICE_PERSONALITY_NAME", "BAKAI")

    # News Credentials (Optional - RSS fallback is always active)
    NEWS_API_KEY: Optional[str] = os.getenv("NEWS_API_KEY")
    GNEWS_API_KEY: Optional[str] = os.getenv("GNEWS_API_KEY")

    # Music Credentials (Optional - Public search fallback is active)
    YOUTUBE_API_KEY: Optional[str] = os.getenv("YOUTUBE_API_KEY")
    SPOTIFY_CLIENT_ID: Optional[str] = os.getenv("SPOTIFY_CLIENT_ID")
    SPOTIFY_CLIENT_SECRET: Optional[str] = os.getenv("SPOTIFY_CLIENT_SECRET")

    # Search Credentials (Optional - DuckDuckGo fallback is active)
    TAVILY_API_KEY: Optional[str] = os.getenv("TAVILY_API_KEY")
    SERPAPI_API_KEY: Optional[str] = os.getenv("SERPAPI_API_KEY")

    # Weather Credentials (Optional - Open-Meteo free API is active by default)
    OPENWEATHER_API_KEY: Optional[str] = os.getenv("OPENWEATHER_API_KEY")

    # Live data integrations (all optional)
    CRICKET_API_KEY: Optional[str] = os.getenv("CRICKET_API_KEY")
    AMADEUS_CLIENT_ID: Optional[str] = os.getenv("AMADEUS_CLIENT_ID")
    AMADEUS_CLIENT_SECRET: Optional[str] = os.getenv("AMADEUS_CLIENT_SECRET")
    AVIATIONSTACK_API_KEY: Optional[str] = os.getenv("AVIATIONSTACK_API_KEY")
    GOOGLE_MAPS_API_KEY: Optional[str] = os.getenv("GOOGLE_MAPS_API_KEY")
    CALENDARIFIC_API_KEY: Optional[str] = os.getenv("CALENDARIFIC_API_KEY")
    METALS_API_KEY: Optional[str] = os.getenv("METALS_API_KEY")
    N2YO_API_KEY: Optional[str] = os.getenv("N2YO_API_KEY")

    # Xiaozhi Integration
    XIAOZHI_WS_ENDPOINT: str = os.getenv(
        "XIAOZHI_WS_ENDPOINT", "wss://api.xiaozhi.me/v1/mcp"
    )
    XIAOZHI_TOKEN: Optional[str] = os.getenv("XIAOZHI_TOKEN")
    XIAOZHI_DEVICE_ID: Optional[str] = os.getenv("XIAOZHI_DEVICE_ID")
    # Authenticated Android phone gateway
    PHONE_GATEWAY_TOKEN: Optional[str] = os.getenv("PHONE_GATEWAY_TOKEN")
    PHONE_GATEWAY_HOST: str = os.getenv("PHONE_GATEWAY_HOST", "0.0.0.0")
    PHONE_GATEWAY_PORT: int = int(os.getenv("PHONE_GATEWAY_PORT", "8765"))


    # File paths
    BASE_DIR: Path = _PROJECT_ROOT
    RADIO_DB_PATH: Path = _PROJECT_ROOT / "radio" / "india_stations.json"


settings = Settings()
