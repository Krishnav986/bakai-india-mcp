"""Weather Services for Indian and Global Cities for BAKAI Robot.

Uses the Open-Meteo API for zero-key, high-accuracy live meteorological data,
with optional OpenWeatherMap adapter. Provides conversational spoken descriptions
in Hindi and English for robot voice interaction.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import httpx

from core.config import settings
from core.logging import logger
from core.cache import cached

# WMO Weather interpretation codes
_WMO_DESCRIPTIONS: Dict[int, Tuple[str, str]] = {
    0: ("Clear sky", "आसमान बिल्कुल साफ़ है"),
    1: ("Mainly clear", "मुख्य रूप से साफ़ मौसम"),
    2: ("Partly cloudy", "हल्के बादल छाए हुए हैं"),
    3: ("Overcast", "घने बादल छाए हुए हैं"),
    45: ("Foggy", "कोहरा छाया हुआ है"),
    48: ("Depositing rime fog", "घना कोहरा है"),
    51: ("Light drizzle", "हल्की बूंदाबांदी हो रही है"),
    53: ("Moderate drizzle", "बूंदाबांदी हो रही है"),
    55: ("Dense drizzle", "तेज़ बूंदाबांदी"),
    61: ("Slight rain", "हल्की बारिश हो रही है"),
    63: ("Moderate rain", "मध्यम बारिश हो रही है"),
    65: ("Heavy rain", "तेज़ मूसलाधार बारिश हो रही है"),
    71: ("Slight snowfall", "हल्की बर्फबारी"),
    73: ("Moderate snowfall", "बर्फबारी"),
    75: ("Heavy snowfall", "भारी बर्फबारी"),
    80: ("Slight rain showers", "हल्की फुहारें पड़ रही हैं"),
    81: ("Moderate rain showers", "बारिश की फुहारें"),
    82: ("Violent rain showers", "तेज़ बारिश की बौछारें"),
    95: ("Thunderstorm", "बिजली कड़कने के साथ आंधी-तूफ़ान की संभावना है"),
    96: ("Thunderstorm with slight hail", "तूफ़ान और ओले पड़ने की संभावना"),
    99: ("Thunderstorm with heavy hail", "भारी ओलावृष्टि और तूफ़ान"),
}


def _describe_wmo(code: int) -> Tuple[str, str]:
    return _WMO_DESCRIPTIONS.get(code, ("Variable conditions", "मौसम सामान्य है"))


@cached(ttl=1800, key_prefix="geocode")
async def _geocode_city(city: str) -> Optional[Dict[str, Any]]:
    """Geocodes a city name to coordinates using Open-Meteo geocoding."""
    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {"name": city.strip(), "count": 1, "language": "en", "format": "json"}

    try:
        async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT) as client:
            resp = await client.get(url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])
                if results:
                    top = results[0]
                    return {
                        "name": top.get("name"),
                        "latitude": top.get("latitude"),
                        "longitude": top.get("longitude"),
                        "country": top.get("country", "India"),
                        "admin1": top.get("admin1", ""),  # State/Region
                        "timezone": top.get("timezone", "Asia/Kolkata"),
                    }
    except Exception as exc:
        logger.error(f"Geocoding failed for '{city}': {exc}")
    return None


# ----------------------------------------------------------------------
# Weather Tools
# ----------------------------------------------------------------------

async def get_weather(city: str) -> Dict[str, Any]:
    """Gets current live weather conditions (temperature, humidity, condition, wind) for any Indian or global city.

    Args:
        city: City or district name (e.g. 'Guwahati', 'Delhi', 'Dibrugarh', 'Mumbai', 'Shillong').
    """
    geo = await _geocode_city(city)
    if not geo:
        return {
            "status": "not_found",
            "city": city,
            "speech": f"माफ़ कीजिए बॉस, '{city}' का स्थान नहीं मिल पाया। कृपया शहर का सही नाम बताएं।",
        }

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": geo["latitude"],
        "longitude": geo["longitude"],
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m",
        "timezone": geo["timezone"],
    }

    try:
        async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT) as client:
            resp = await client.get(url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                curr = data.get("current", {})
                temp = curr.get("temperature_2m")
                feels_like = curr.get("apparent_temperature")
                humidity = curr.get("relative_humidity_2m")
                wind = curr.get("wind_speed_10m")
                wmo_code = curr.get("weather_code", 0)
                en_desc, hi_desc = _describe_wmo(wmo_code)

                location_str = f"{geo['name']}, {geo['admin1']}" if geo['admin1'] else geo['name']
                speech = (
                    f"बॉस, {location_str} में अभी तापमान {temp}°C है। "
                    f"{hi_desc}, और नमी {humidity}% है।"
                )

                return {
                    "status": "success",
                    "city": geo["name"],
                    "state": geo["admin1"],
                    "country": geo["country"],
                    "temperature_celsius": temp,
                    "feels_like_celsius": feels_like,
                    "humidity_percent": humidity,
                    "wind_speed_kmh": wind,
                    "condition": en_desc,
                    "condition_hindi": hi_desc,
                    "speech": speech,
                }
    except Exception as exc:
        logger.error(f"Weather fetch failed for '{city}': {exc}")

    return {
        "status": "error",
        "city": city,
        "speech": f"माफ़ कीजिए बॉस, {city} का मौसम प्राप्त करने में समस्या आई।",
    }


async def weather_forecast(city: str) -> Dict[str, Any]:
    """Gets a multi-day weather forecast (upcoming 3 days) for a city.

    Args:
        city: City or district name (e.g. 'Guwahati', 'Delhi', 'Kolkata', 'London').
    """
    geo = await _geocode_city(city)
    if not geo:
        return {
            "status": "not_found",
            "city": city,
            "speech": f"माफ़ कीजिए बॉस, '{city}' का स्थान नहीं मिल पाया।",
        }

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": geo["latitude"],
        "longitude": geo["longitude"],
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
        "timezone": geo["timezone"],
        "forecast_days": 3,
    }

    try:
        async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT) as client:
            resp = await client.get(url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                daily = data.get("daily", {})
                dates = daily.get("time", [])
                max_temps = daily.get("temperature_2m_max", [])
                min_temps = daily.get("temperature_2m_min", [])
                precip = daily.get("precipitation_probability_max", [])
                codes = daily.get("weather_code", [])

                forecast_items = []
                for i in range(len(dates)):
                    en_cond, hi_cond = _describe_wmo(codes[i] if i < len(codes) else 0)
                    forecast_items.append({
                        "date": dates[i],
                        "temp_max_c": max_temps[i] if i < len(max_temps) else None,
                        "temp_min_c": min_temps[i] if i < len(min_temps) else None,
                        "precipitation_chance_percent": precip[i] if i < len(precip) else 0,
                        "condition": en_cond,
                        "condition_hindi": hi_cond,
                    })

                loc_str = f"{geo['name']}, {geo['admin1']}" if geo['admin1'] else geo['name']
                speech_parts = [f"बॉस, {loc_str} का 3 दिन का पूर्वानुमान ये रहा:"]
                for item in forecast_items:
                    speech_parts.append(
                        f"{item['date']}: अधिकतम {item['temp_max_c']}°C, न्यूनतम {item['temp_min_c']}°C ({item['condition_hindi']})।"
                    )
                speech = " ".join(speech_parts)

                return {
                    "status": "success",
                    "city": geo["name"],
                    "state": geo["admin1"],
                    "country": geo["country"],
                    "forecast": forecast_items,
                    "speech": speech,
                }
    except Exception as exc:
        logger.error(f"Weather forecast failed for '{city}': {exc}")

    return {
        "status": "error",
        "city": city,
        "speech": f"माफ़ कीजिए बॉस, {city} का पूर्वानुमान प्राप्त नहीं हो सका।",
    }
