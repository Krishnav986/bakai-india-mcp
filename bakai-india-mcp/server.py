"""BAKAI India MCP Server – Ultimate AI Services Ecosystem for Robot BAKAI.

Integrates Indian radio, news, music, shopping, web research, weather, and utilities
over the Model Context Protocol (MCP) with support for the Xiaozhi AI Ecosystem.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from typing import Any, Dict, List, Optional

# Core MCP server factory supporting both MCP 2.x (MCPServer) and 1.x (FastMCP)
try:
    from mcp.server.mcpserver import MCPServer as FastMCP
except ImportError:
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError:
        from mcp.server import Server as FastMCP

from core.config import settings
from core.logging import logger

# Import tool handlers from dedicated domain packages
from radio.radio_tools import (
    india_radio_list as _india_radio_list,
    radio_search as _radio_search,
    radio_play as _radio_play,
    radio_stop as _radio_stop,
    radio_now_playing as _radio_now_playing,
)
from news.news_tools import (
    india_news as _india_news,
    assam_news as _assam_news,
    world_news as _world_news,
    technology_news as _technology_news,
    sports_news as _sports_news,
    news_search as _news_search,
)
from music.youtube_tools import (
    youtube_search as _youtube_search,
    youtube_open as _youtube_open,
)
from music.spotify_tools import (
    spotify_search as _spotify_search,
    spotify_open as _spotify_open,
    music_control as _music_control,
    music_now_playing as _music_now_playing,
)
from shopping.amazon_tools import (
    amazon_search as _amazon_search,
    amazon_product_info as _amazon_product_info,
    open_website as _open_website,
    website_search as _website_search,
)
from internet.search_tools import (
    web_search as _web_search,
    deep_research as _deep_research,
    fact_check as _fact_check,
    general_knowledge as _general_knowledge,
)
from utilities.weather_tools import (
    get_weather as _get_weather,
    weather_forecast as _weather_forecast,
)
from utilities.daily_tools import (
    get_india_time as _get_india_time,
    calculator as _calculator,
    unit_converter as _unit_converter,
)
from utilities.live_data_tools import (
    check_aqi as _check_aqi,
    earthquake_alerts as _earthquake_alerts,
    exchange_rates as _exchange_rates,
    fuel_price as _fuel_price,
    gold_price as _gold_price,
    holiday_calendar as _holiday_calendar,
    iss_tracker as _iss_tracker,
    rain_alert as _rain_alert,
    uv_index as _uv_index,
)
from utilities.mobility_tools import (
    bus_live_tracking as _bus_live_tracking,
    bus_search as _bus_search,
    flight_search as _flight_search,
    flight_status as _flight_status,
    map_directions as _map_directions,
    metro_routes as _metro_routes,
    traffic_status as _traffic_status,
    train_pnr_status as _train_pnr_status,
    train_search as _train_search,
)
from utilities.cricket_tools import (
    cricket_live_score as _cricket_live_score,
    cricket_schedule as _cricket_schedule,
)

# Initialize MCP Server instance
mcp = FastMCP(
    name=settings.SERVER_NAME,
    instructions=(
        "BAKAI India MCP Server provides comprehensive tools for Indian radio, "
        "regional and national news, music search and playback controls, Amazon India shopping, "
        "advanced internet research, live weather, and Indian daily utilities. "
        "All responses contain both structured data and conversational speech phrasing for the robot's voice."
    ),
)


# ======================================================================
# 1. INDIAN RADIO TOOLS
# ======================================================================

@mcp.tool()
async def india_radio_list(
    language: Optional[str] = None,
    region: Optional[str] = None,
    category: Optional[str] = None,
) -> Dict[str, Any]:
    """Lists available Indian radio stations filtered by language, region, or category.

    Use when the user asks what radio stations are available, or asks for stations in a specific language (e.g. Assamese, Hindi, Bengali, Tamil).

    Args:
        language: Optional language filter (e.g. 'hindi', 'assamese', 'bengali', 'tamil', 'punjabi', 'kannada', 'marathi', 'english').
        region: Optional geographic region filter (e.g. 'National', 'Assam & Northeast', 'West Bengal', 'Delhi', 'Maharashtra').
        category: Optional category filter (e.g. 'all_india_radio', 'regional', 'bollywood', 'classical', 'community').
    """
    return await _india_radio_list(language=language, region=region, category=category)


@mcp.tool()
async def radio_search(
    query: str,
    language: Optional[str] = None,
    city: Optional[str] = None,
) -> Dict[str, Any]:
    """Searches for Indian radio stations by name, keyword, city, or language.

    Use when the user searches for a specific station (e.g. 'vividh bharati', 'fm gold', 'guwahati radio', 'retro bollywood').

    Args:
        query: Station name or search query (e.g. 'vividh bharati', 'fm gold', 'assam', 'retro', 'nagaon').
        language: Optional language constraint (e.g. 'hindi', 'assamese').
        city: Optional city constraint (e.g. 'Delhi', 'Guwahati', 'Mumbai', 'Kolkata').
    """
    return await _radio_search(query=query, language=language, city=city)


@mcp.tool()
async def radio_play(station_name: str) -> Dict[str, Any]:
    """Starts playing an Indian radio station on the robot by name or keyword.

    Verifies stream health, selects active fallback streams if needed, and returns a Xiaozhi robot action payload with the live audio stream URL.

    Args:
        station_name: Station to play (e.g. 'vividh bharati', 'fm gold', 'assam radio', 'air maitree', 'retro bollywood', 'delhi rainbow').
    """
    return await _radio_play(station_name=station_name)


@mcp.tool()
async def radio_stop() -> Dict[str, Any]:
    """Stops the currently playing radio broadcast on BAKAI.

    Use when the user says 'रेडियो बंद करो', 'stop radio', 'turn off radio'.
    """
    return await _radio_stop()


@mcp.tool()
async def radio_now_playing() -> Dict[str, Any]:
    """Checks what radio station is currently playing on the robot and how long it has been streaming.

    Use when the user asks 'कौन सा रेडियो चल रहा है?' or 'what radio station is playing?'.
    """
    return await _radio_now_playing()


# ======================================================================
# 2. INDIAN AND INTERNATIONAL NEWS TOOLS
# ======================================================================

@mcp.tool()
async def india_news(category: str = "national", limit: int = 5) -> Dict[str, Any]:
    """Fetches real, top national headlines from India across politics, governance, and national affairs.

    Use when the user asks for Indian news (e.g. 'आज की भारतीय खबरें सुनाओ', 'India news today').

    Args:
        category: News category ('national', 'politics', 'general').
        limit: Number of headlines to return (1 to 10, default 5).
    """
    return await _india_news(category=category, limit=limit)


@mcp.tool()
async def assam_news(category: str = "general", limit: int = 5) -> Dict[str, Any]:
    """Fetches the latest regional news and updates from Assam and Northeast India.

    Use when the user asks for Assam or Northeast news (e.g. 'असम की खबरें बताओ', 'Assam news', 'Guwahati updates').

    Args:
        category: News category ('general', 'assam', 'northeast').
        limit: Number of headlines to return (1 to 10, default 5).
    """
    return await _assam_news(category=category, limit=limit)


@mcp.tool()
async def world_news(category: str = "general", limit: int = 5) -> Dict[str, Any]:
    """Fetches major global headlines and international geopolitical developments.

    Use when the user asks for international or world news ('दुनिया की खबरें', 'world news').

    Args:
        category: News category ('general', 'world', 'geopolitics').
        limit: Number of headlines (1 to 10, default 5).
    """
    return await _world_news(category=category, limit=limit)


@mcp.tool()
async def technology_news(limit: int = 5) -> Dict[str, Any]:
    """Fetches recent technology, artificial intelligence, gadget, and startup headlines.

    Use when the user asks for tech news ('आज की टेक्नोलॉजी न्यूज़ क्या है?', 'tech news').

    Args:
        limit: Number of headlines (1 to 10, default 5).
    """
    return await _technology_news(limit=limit)


@mcp.tool()
async def sports_news(limit: int = 5) -> Dict[str, Any]:
    """Fetches latest sports headlines (Cricket, Football, Olympics, Badminton).

    Use when the user asks for sports or cricket news ('खेल समाचार सुनाओ', 'cricket score updates').

    Args:
        limit: Number of headlines (1 to 10, default 5).
    """
    return await _sports_news(limit=limit)


@mcp.tool()
async def news_search(query: str, limit: int = 5) -> Dict[str, Any]:
    """Searches recent news articles by keyword or topic across Indian and global publications.

    Use when the user asks for news about a specific person, place, or event (e.g. 'ISRO Gaganyaan news', 'Guwahati news').

    Args:
        query: Topic to search (e.g. 'ISRO', 'Guwahati', 'T20 World Cup').
        limit: Number of articles (1 to 10, default 5).
    """
    return await _news_search(query=query, limit=limit)


# ======================================================================
# 3. MUSIC AND AUDIO SERVICES TOOLS
# ======================================================================

@mcp.tool()
async def youtube_search(query: str, limit: int = 5) -> Dict[str, Any]:
    """Searches YouTube for videos, songs, tutorials, or creators.

    Returns verified titles, channels, and video links.

    Args:
        query: Search term (e.g. 'Arijit Singh Kesariya', 'ESP32 robot tutorial', 'Assamese Bihu folk').
        limit: Number of results (1 to 10, default 5).
    """
    return await _youtube_search(query=query, limit=limit)


@mcp.tool()
async def youtube_open(query: str) -> Dict[str, Any]:
    """Opens a requested YouTube video, song, or search query on the user's connected display or app.

    Args:
        query: Song name or video title or URL (e.g. 'Kesariya song', 'https://www.youtube.com/watch?v=...').
    """
    return await _youtube_open(query=query)


@mcp.tool()
async def spotify_search(query: str, limit: int = 5) -> Dict[str, Any]:
    """Searches Spotify's catalog for tracks, artists, and albums.

    Use when the user wants to find songs on Spotify ('Spotify par gaana khojo', 'search song on Spotify').

    Args:
        query: Track or artist name (e.g. 'Tum Hi Ho Arijit Singh', 'Bhupen Hazarika').
        limit: Number of results (1 to 10, default 5).
    """
    return await _spotify_search(query=query, limit=limit)


@mcp.tool()
async def spotify_open(query: str) -> Dict[str, Any]:
    """Opens Spotify app or web player for a song, artist, playlist, or search query.

    Use when the user says 'Spotify खोलो', 'open Spotify', 'play song on Spotify'.

    Args:
        query: Track title, artist, playlist, or URI (e.g. 'Dil Hoom Hoom Kare', 'spotify:track:...').
    """
    return await _spotify_open(query=query)


@mcp.tool()
async def music_control(action: str) -> Dict[str, Any]:
    """Controls music playback on BAKAI (play, pause, stop, resume, next, previous, volume_up, volume_down).

    Use when the user gives playback commands ('गाना रोको', 'pause music', 'next song', 'volume badhao').

    Args:
        action: Command ('play', 'pause', 'stop', 'resume', 'next', 'previous', 'volume_up', 'volume_down').
    """
    return await _music_control(action=action)


@mcp.tool()
async def music_now_playing() -> Dict[str, Any]:
    """Checks what music track is currently active or playing on the robot.

    Use when the user asks 'कौन सा गाना बज रहा है?' or 'what song is playing?'.
    """
    return await _music_now_playing()


# ======================================================================
# 4. AMAZON INDIA AND WEBSITE LAUNCHER TOOLS
# ======================================================================

@mcp.tool()
async def amazon_search(query: str) -> Dict[str, Any]:
    """Searches Amazon India (amazon.in) for products, electronics, parts, and daily essentials.

    Use when the user asks to search for products to buy or view on Amazon ('Amazon पर ESP32 खोजो', 'search headphones on Amazon').

    Args:
        query: Product to search (e.g. 'ESP32 development board', 'MAX98357A I2S DAC', 'Sony headphones').
    """
    return await _amazon_search(query=query)


@mcp.tool()
async def amazon_product_info(product_url: str) -> Dict[str, Any]:
    """Inspects and validates an Amazon product URL, extracting its clean ASIN and tracker-free link.

    Guarantees no automatic purchases or modifications.

    Args:
        product_url: Amazon product URL (e.g. 'https://www.amazon.in/dp/B08N5WRWNW').
    """
    return await _amazon_product_info(product_url=product_url)


@mcp.tool()
async def open_website(service: str) -> Dict[str, Any]:
    """Opens an approved Indian or global web service from the secure allowlist.

    Supported services: amazon, flipkart, spotify, youtube, google, gmail, maps, wikipedia, irctc, digilocker, indiagov, swiggy, zomato.

    Args:
        service: Service name (e.g. 'irctc', 'digilocker', 'amazon', 'youtube', 'maps', 'wikipedia').
    """
    return await _open_website(service=service)


@mcp.tool()
async def website_search(query: str) -> Dict[str, Any]:
    """Locates official websites and safe links for Indian institutions, government portals, or companies.

    Args:
        query: Entity to locate (e.g. 'IRCTC', 'Prasar Bharati', 'Assam University').
    """
    return await _website_search(query=query)


# ======================================================================
# 5. ADVANCED INTERNET RESEARCH TOOLS
# ======================================================================

@mcp.tool()
async def web_search(query: str, limit: int = 5) -> Dict[str, Any]:
    """Searches the web for factual information, technical documentation, and encyclopedic knowledge.

    Treats retrieved data as untrusted and protects against prompt injection.

    Args:
        query: Query string (e.g. 'Kaziranga National Park Assam facts', 'ISRO Gaganyaan mission objectives').
        limit: Max results (1 to 10, default 5).
    """
    return await _web_search(query=query, limit=limit)


@mcp.tool()
async def deep_research(topic: str) -> Dict[str, Any]:
    """Performs deep factual research on a topic, providing comprehensive background, historical context, and citations.

    Use when the user asks for an in-depth explanation or research ('tell me in detail about...', 'deep research on...').

    Args:
        topic: Subject or entity to research (e.g. 'Brahmaputra River hydrology', 'Ahom Kingdom Lachit Borphukan', 'ESP32 architecture').
    """
    return await _deep_research(topic=topic)


@mcp.tool()
async def fact_check(claim: str) -> Dict[str, Any]:
    """Verifies a claim or statement against reputable sources, evaluating consensus and providing citations.

    Use when the user asks if a claim is true ('is it true that...', 'क्या यह सच है कि...').

    Args:
        claim: Statement to verify (e.g. 'Guwahati is the capital of Assam', 'India won the 1983 World Cup').
    """
    return await _fact_check(claim=claim)


@mcp.tool()
async def general_knowledge(question: str) -> Dict[str, Any]:
    """Answers factual questions across geography, history, science, Indian affairs, and world knowledge.

    Use for general knowledge queries ('भारत की राजधानी क्या है?', 'who invented the telephone?').

    Args:
        question: Question to answer (e.g. 'What is the capital of Assam?', 'Who was the first President of India?').
    """
    return await _general_knowledge(question=question)


# ======================================================================
# 6. WEATHER AND DAILY UTILITIES TOOLS
# ======================================================================

@mcp.tool()
async def get_weather(city: str) -> Dict[str, Any]:
    """Gets current live weather conditions (temperature, humidity, weather condition, wind) for any Indian or global city.

    Use when the user asks about the weather ('आज गुवाहाटी का मौसम बताओ', 'weather in Delhi').

    Args:
        city: City or district name (e.g. 'Guwahati', 'Delhi', 'Dibrugarh', 'Mumbai', 'Kolkata', 'London').
    """
    return await _get_weather(city=city)


@mcp.tool()
async def weather_forecast(city: str) -> Dict[str, Any]:
    """Gets a 3-day weather forecast with expected temperatures and precipitation chances for a city.

    Use when the user asks for upcoming weather ('कल गुवाहाटी में बारिश होगी क्या?', 'forecast for Delhi').

    Args:
        city: City or district name (e.g. 'Guwahati', 'Delhi', 'Bengaluru').
    """
    return await _weather_forecast(city=city)


@mcp.tool()
async def get_india_time() -> Dict[str, Any]:
    """Returns the current Indian Standard Time (IST, UTC+05:30), date, and day of the week.

    Use when the user asks what time or date it is in India ('समय क्या हुआ है?', 'what is the time in India?').
    """
    return _get_india_time()


@mcp.tool()
async def calculator(expression: str) -> Dict[str, Any]:
    """Evaluates mathematical calculations securely using AST parsing without dangerous eval.

    Supports arithmetic (+, -, *, /, //, %, ^), trigonometry (sin, cos, tan), roots (sqrt), and constants (pi, e).

    Use when the user asks to calculate math ('25 * 40 कितना होगा?', 'calculate sqrt(144) + 50').

    Args:
        expression: Mathematical expression (e.g. '1250 * 18 / 100', 'sqrt(256) + 45', '2^10').
    """
    return _calculator(expression=expression)


@mcp.tool()
async def unit_converter(value: float, from_unit: str, to_unit: str) -> Dict[str, Any]:
    """Converts values between metric, imperial, and traditional Indian units.

    Supports:
    - Temperature (c, f, k)
    - Length (km, m, cm, mm, mile, foot, inch)
    - Weight (kg, g, mg, lb, tola, seer, maund)
    - Area (sqm, sqft, acre, hectare, bigha, katha)
    - Data (b, kb, mb, gb, tb)
    - Indian numbers (lakh, crore, million, billion)

    Args:
        value: Number to convert (e.g. 5.0).
        from_unit: Source unit (e.g. 'c', 'tola', 'bigha', 'crore', 'km').
        to_unit: Target unit (e.g. 'f', 'gram', 'sqft', 'million', 'mile').
    """
    return _unit_converter(value=value, from_unit=from_unit, to_unit=to_unit)


# ======================================================================
# 7. LIVE DATA, TRAVEL, AND TRANSPORT TOOLS
# ======================================================================

@mcp.tool()
async def check_aqi(city: str) -> Dict[str, Any]:
    """Fetch current modeled AQI and particulate readings from Open-Meteo."""
    return await _check_aqi(city=city)


@mcp.tool()
async def cricket_live_score() -> Dict[str, Any]:
    """Fetch live cricket match scores from API-Sports Cricket (requires CRICKET_API_KEY)."""
    return await _cricket_live_score()


@mcp.tool()
async def cricket_schedule(match_date: Optional[str] = None) -> Dict[str, Any]:
    """Fetch scheduled cricket fixtures for a date from API-Sports Cricket."""
    return await _cricket_schedule(match_date=match_date)


@mcp.tool()
async def flight_search(
    origin: str,
    destination: str,
    departure_date: str,
    adults: int = 1,
    limit: int = 5,
) -> Dict[str, Any]:
    """Search real flight offers via Amadeus; requires production API credentials and never books."""
    return await _flight_search(
        origin=origin,
        destination=destination,
        departure_date=departure_date,
        adults=adults,
        limit=limit,
    )


@mcp.tool()
async def flight_status(flight_number: str) -> Dict[str, Any]:
    """Fetch flight status from Aviationstack (requires AVIATIONSTACK_API_KEY)."""
    return await _flight_status(flight_number=flight_number)


@mcp.tool()
async def train_search(
    origin: str,
    destination: str,
    travel_date: Optional[str] = None,
) -> Dict[str, Any]:
    """Open the official IRCTC train search page; does not claim live inventory or seat availability."""
    return await _train_search(origin=origin, destination=destination, travel_date=travel_date)


@mcp.tool()
async def train_pnr_status(pnr: str) -> Dict[str, Any]:
    """Provide the official PNR enquiry link; live lookup requires authorized railway-provider access."""
    return await _train_pnr_status(pnr=pnr)


@mcp.tool()
async def bus_search(
    origin: str,
    destination: str,
    travel_date: Optional[str] = None,
) -> Dict[str, Any]:
    """Open redBus to search live bus inventory; no seats or booking are claimed by this tool."""
    return await _bus_search(origin=origin, destination=destination, travel_date=travel_date)


@mcp.tool()
async def bus_live_tracking(ticket_number: str) -> Dict[str, Any]:
    """Explain that live tracking requires an authorized bus operator or ticketing partner."""
    return await _bus_live_tracking(ticket_number=ticket_number)


@mcp.tool()
async def metro_routes(origin: str, destination: str) -> Dict[str, Any]:
    """Fetch public-transit routes from Google Maps (requires GOOGLE_MAPS_API_KEY)."""
    return await _metro_routes(origin=origin, destination=destination)


@mcp.tool()
async def traffic_status(origin: str, destination: str) -> Dict[str, Any]:
    """Fetch traffic-aware driving route duration from Google Maps (requires GOOGLE_MAPS_API_KEY)."""
    return await _traffic_status(origin=origin, destination=destination)


@mcp.tool()
async def map_directions(
    origin: str,
    destination: str,
    mode: str = "DRIVE",
) -> Dict[str, Any]:
    """Fetch a Google Maps route or return a provider link if the API key is not configured."""
    return await _map_directions(origin=origin, destination=destination, mode=mode)


@mcp.tool()
async def fuel_price(city: str, fuel_type: str = "petrol") -> Dict[str, Any]:
    """Report when a licensed live Indian fuel-price data provider is not configured."""
    return await _fuel_price(city=city, fuel_type=fuel_type)


@mcp.tool()
async def gold_price() -> Dict[str, Any]:
    """Fetch INR gold spot price per gram from Metals-API (requires METALS_API_KEY)."""
    return await _gold_price()


@mcp.tool()
async def earthquake_alerts(
    hours: int = 24,
    minimum_magnitude: float = 4.5,
    limit: int = 20,
) -> Dict[str, Any]:
    """List recent earthquake events from the USGS GeoJSON service."""
    return await _earthquake_alerts(
        hours=hours,
        minimum_magnitude=minimum_magnitude,
        limit=limit,
    )


@mcp.tool()
async def rain_alert(
    city: str,
    hours_ahead: int = 24,
    probability_threshold: int = 50,
) -> Dict[str, Any]:
    """Check Open-Meteo hourly precipitation forecasts for a city."""
    return await _rain_alert(
        city=city,
        hours_ahead=hours_ahead,
        probability_threshold=probability_threshold,
    )


@mcp.tool()
async def uv_index(city: str) -> Dict[str, Any]:
    """Fetch current modeled UV index from Open-Meteo."""
    return await _uv_index(city=city)


@mcp.tool()
async def exchange_rates(base: str = "USD", targets: str = "INR") -> Dict[str, Any]:
    """Fetch daily reference exchange rates from Frankfurter without an API key."""
    return await _exchange_rates(base=base, targets=targets)


@mcp.tool()
async def holiday_calendar(year: int, country_code: str = "IN") -> Dict[str, Any]:
    """Fetch public holidays from Calendarific (requires CALENDARIFIC_API_KEY)."""
    return await _holiday_calendar(year=year, country_code=country_code)


@mcp.tool()
async def iss_tracker(latitude: float, longitude: float, altitude_km: float = 0) -> Dict[str, Any]:
    """Fetch the ISS position above observer coordinates from N2YO (requires N2YO_API_KEY)."""
    return await _iss_tracker(latitude=latitude, longitude=longitude, altitude_km=altitude_km)


# ======================================================================
# CLI ENTRY POINT & DIAGNOSTICS
# ======================================================================

def list_registered_tools() -> None:
    """Prints all registered MCP tools and their descriptions."""
    tools = []
    if hasattr(mcp, "_tool_manager"):
        # MCP 2.x
        mgr = mcp._tool_manager
        tool_dict = getattr(mgr, "_tools", {})
        for name, tool in tool_dict.items():
            doc = (getattr(tool, "description", None) or getattr(tool.fn, "__doc__", "")).strip().split("\n")[0]
            tools.append((name, doc))
    sys.stderr.write(f"\nRegistered {len(tools)} MCP Tools for {settings.SERVER_NAME}:\n")
    sys.stderr.write("-" * 75 + "\n")
    for name, desc in sorted(tools):
        sys.stderr.write(f"  * {name:<24} : {desc}\n")
    sys.stderr.write("-" * 75 + "\n\n")


def run_server() -> None:
    """Parses command-line arguments and launches the MCP server."""
    parser = argparse.ArgumentParser(description=f"{settings.SERVER_NAME} - Model Context Protocol Server for BAKAI Robot")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable-http"],
        default="stdio",
        help="MCP transport mode (default: stdio for Xiaozhi bridge & desktop clients)",
    )
    parser.add_argument("--port", type=int, default=8080, help="Port for SSE transport mode (default: 8080)")
    parser.add_argument("--host", default="127.0.0.1", help="Host address for SSE transport (default: 127.0.0.1)")
    parser.add_argument("--list-tools", action="store_true", help="Print all registered tools and exit")

    args = parser.parse_args()

    if args.list_tools:
        list_registered_tools()
        sys.exit(0)

    logger.info(f"Starting {settings.SERVER_NAME} v{settings.SERVER_VERSION} using transport='{args.transport}'")
    list_registered_tools()

    if args.transport == "stdio":
        # Standard input/output transport for mcp2xiaozhi bridge
        mcp.run(transport="stdio")
    elif args.transport == "sse":
        # Server-Sent Events HTTP transport
        logger.info(f"SSE Server listening on http://{args.host}:{args.port}/sse")
        mcp.run(transport="sse", host=args.host, port=args.port)
    else:
        mcp.run(transport=args.transport)

from bridge.phone_gateway import find_contact

@mcp.tool()
async def phone_find_contact(query: str) -> Dict[str, Any]:
    """Search contacts on the connected Android phone. The user selects a contact."""
    return await find_contact(query)
if __name__ == "__main__":
    run_server()
