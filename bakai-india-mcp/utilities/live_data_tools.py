"""Public and credentialed live-data tools for BAKAI."""

from __future__ import annotations

import datetime as dt
import math
import re
from typing import Any, Dict, Optional

from core.config import settings
from utilities.live_api import (
    ProviderError,
    invalid_input,
    missing_credential,
    provider_error,
    request_json,
)

_GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
_AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


def _valid_text(value: str, label: str, max_length: int = 120) -> Optional[Dict[str, str]]:
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > max_length:
        return invalid_input(f"{label} must be a non-empty string of at most {max_length} characters.")
    return None


async def _geocode(city: str) -> Dict[str, Any]:
    payload = await request_json(
        _GEOCODING_URL,
        params={"name": city.strip(), "count": 1, "language": "en", "format": "json"},
    )
    matches = payload.get("results")
    if not isinstance(matches, list) or not matches:
        raise LookupError(f"No location was found for '{city.strip()}'.")
    location = matches[0]
    if not isinstance(location, dict):
        raise ProviderError("The geocoding provider returned an unexpected location.")
    latitude = location.get("latitude")
    longitude = location.get("longitude")
    if not isinstance(latitude, (int, float)) or not isinstance(longitude, (int, float)):
        raise ProviderError("The geocoding provider returned invalid coordinates.")
    return {
        "name": location.get("name", city.strip()),
        "country": location.get("country"),
        "admin1": location.get("admin1"),
        "latitude": latitude,
        "longitude": longitude,
        "timezone": location.get("timezone", "auto"),
    }


async def check_aqi(city: str) -> Dict[str, Any]:
    """Fetch current modeled US and European AQI and particulate levels for a city."""
    error = _valid_text(city, "city")
    if error:
        return error
    try:
        location = await _geocode(city)
        payload = await request_json(
            _AIR_QUALITY_URL,
            params={
                "latitude": location["latitude"],
                "longitude": location["longitude"],
                "current": "us_aqi,european_aqi,pm2_5,pm10",
                "timezone": location["timezone"],
            },
        )
    except LookupError as exc:
        return {"status": "not_found", "error": str(exc)}
    except ProviderError as exc:
        return provider_error("Open-Meteo", exc)

    current = payload.get("current")
    if not isinstance(current, dict) or not any(
        current.get(key) is not None
        for key in ("us_aqi", "european_aqi", "pm2_5", "pm10")
    ):
        return provider_error("Open-Meteo", ProviderError("No current air-quality data was returned."))
    return {
        "status": "success",
        "provider": "Open-Meteo",
        "location": location,
        "observed_at": current.get("time"),
        "us_aqi": current.get("us_aqi"),
        "european_aqi": current.get("european_aqi"),
        "pm2_5_ug_m3": current.get("pm2_5"),
        "pm10_ug_m3": current.get("pm10"),
        "source_url": "https://open-meteo.com/en/docs/air-quality-api",
    }


async def rain_alert(
    city: str,
    hours_ahead: int = 24,
    probability_threshold: int = 50,
) -> Dict[str, Any]:
    """Check Open-Meteo precipitation forecasts for the next 1–72 hours."""
    error = _valid_text(city, "city")
    if error:
        return error
    if not isinstance(hours_ahead, int) or isinstance(hours_ahead, bool) or not 1 <= hours_ahead <= 72:
        return invalid_input("hours_ahead must be between 1 and 72.")
    if (
        not isinstance(probability_threshold, int)
        or isinstance(probability_threshold, bool)
        or not 0 <= probability_threshold <= 100
    ):
        return invalid_input("probability_threshold must be between 0 and 100.")
    try:
        location = await _geocode(city)
        payload = await request_json(
            _FORECAST_URL,
            params={
                "latitude": location["latitude"],
                "longitude": location["longitude"],
                "hourly": "precipitation_probability,precipitation,rain,showers",
                "forecast_days": 3,
                "timezone": location["timezone"],
            },
        )
    except LookupError as exc:
        return {"status": "not_found", "error": str(exc)}
    except ProviderError as exc:
        return provider_error("Open-Meteo", exc)

    hourly = payload.get("hourly")
    if not isinstance(hourly, dict) or not isinstance(hourly.get("time"), list):
        return provider_error("Open-Meteo", ProviderError("No hourly precipitation forecast was returned."))
    times = hourly["time"][:hours_ahead]
    probabilities = (hourly.get("precipitation_probability") or [])[:hours_ahead]
    precipitation = (hourly.get("precipitation") or [])[:hours_ahead]
    rain = (hourly.get("rain") or [])[:hours_ahead]
    showers = (hourly.get("showers") or [])[:hours_ahead]
    valid_probabilities = [value for value in probabilities if isinstance(value, (int, float))]
    maximum_probability = max(valid_probabilities, default=None)
    total_precipitation = sum(
        value for value in precipitation if isinstance(value, (int, float))
    )
    may_rain = (
        None
        if maximum_probability is None
        else maximum_probability >= probability_threshold
    )
    return {
        "status": "success",
        "provider": "Open-Meteo",
        "location": location,
        "hours_checked": len(times),
        "rain_possible": may_rain,
        "probability_threshold_percent": probability_threshold,
        "maximum_precipitation_probability_percent": maximum_probability,
        "forecast_precipitation_mm": round(total_precipitation, 2),
        "hourly": [
            {
                "time": times[index],
                "precipitation_probability_percent": probabilities[index] if index < len(probabilities) else None,
                "precipitation_mm": precipitation[index] if index < len(precipitation) else None,
                "rain_mm": rain[index] if index < len(rain) else None,
                "showers_mm": showers[index] if index < len(showers) else None,
            }
            for index in range(len(times))
        ],
        "source_url": "https://open-meteo.com/en/docs",
    }


async def uv_index(city: str) -> Dict[str, Any]:
    """Fetch the current modeled UV index for a city from Open-Meteo."""
    error = _valid_text(city, "city")
    if error:
        return error
    try:
        location = await _geocode(city)
        payload = await request_json(
            _AIR_QUALITY_URL,
            params={
                "latitude": location["latitude"],
                "longitude": location["longitude"],
                "current": "uv_index,uv_index_clear_sky",
                "timezone": location["timezone"],
            },
        )
    except LookupError as exc:
        return {"status": "not_found", "error": str(exc)}
    except ProviderError as exc:
        return provider_error("Open-Meteo", exc)

    current = payload.get("current")
    if not isinstance(current, dict) or current.get("uv_index") is None:
        return provider_error("Open-Meteo", ProviderError("No current UV-index data was returned."))
    return {
        "status": "success",
        "provider": "Open-Meteo",
        "location": location,
        "observed_at": current.get("time"),
        "uv_index": current["uv_index"],
        "uv_index_clear_sky": current.get("uv_index_clear_sky"),
        "source_url": "https://open-meteo.com/en/docs/air-quality-api",
    }


async def earthquake_alerts(
    hours: int = 24,
    minimum_magnitude: float = 4.5,
    limit: int = 20,
) -> Dict[str, Any]:
    """List recent earthquakes from the USGS FDSN GeoJSON event service."""
    if not isinstance(hours, int) or isinstance(hours, bool) or not 1 <= hours <= 168:
        return invalid_input("hours must be between 1 and 168.")
    if (
        not isinstance(minimum_magnitude, (int, float))
        or isinstance(minimum_magnitude, bool)
        or not math.isfinite(minimum_magnitude)
        or not 0 <= minimum_magnitude <= 10
    ):
        return invalid_input("minimum_magnitude must be between 0 and 10.")
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 100:
        return invalid_input("limit must be between 1 and 100.")
    end = dt.datetime.now(dt.timezone.utc)
    start = end - dt.timedelta(hours=hours)
    try:
        payload = await request_json(
            "https://earthquake.usgs.gov/fdsnws/event/1/query",
            params={
                "format": "geojson",
                "starttime": start.isoformat(timespec="seconds"),
                "endtime": end.isoformat(timespec="seconds"),
                "minmagnitude": minimum_magnitude,
                "limit": limit,
                "orderby": "time",
            },
        )
    except ProviderError as exc:
        return provider_error("USGS", exc)

    features = payload.get("features")
    if not isinstance(features, list):
        return provider_error("USGS", ProviderError("No earthquake event list was returned."))
    events = []
    for feature in features[:limit]:
        if not isinstance(feature, dict):
            continue
        properties = feature.get("properties") or {}
        geometry = feature.get("geometry") or {}
        events.append(
            {
                "id": feature.get("id"),
                "magnitude": properties.get("mag"),
                "place": properties.get("place"),
                "time_ms": properties.get("time"),
                "url": properties.get("url"),
                "coordinates": geometry.get("coordinates"),
            }
        )
    return {
        "status": "success",
        "provider": "USGS",
        "count": len(events),
        "events": events,
        "source_url": "https://earthquake.usgs.gov/fdsnws/event/1/",
    }


async def exchange_rates(base: str = "USD", targets: str = "INR") -> Dict[str, Any]:
    """Fetch daily reference exchange rates without an API key."""
    base = base.strip().upper() if isinstance(base, str) else ""
    targets = targets.strip().upper() if isinstance(targets, str) else ""
    if not re.fullmatch(r"[A-Z]{3}", base):
        return invalid_input("base must be a three-letter currency code.")
    target_codes = [item.strip() for item in targets.split(",") if item.strip()]
    if not target_codes or len(target_codes) > 20 or any(
        not re.fullmatch(r"[A-Z]{3}", item) for item in target_codes
    ):
        return invalid_input("targets must be a comma-separated list of 1–20 three-letter currency codes.")
    if base in target_codes:
        target_codes = [code for code in target_codes if code != base]
    if not target_codes:
        return {"status": "success", "provider": "Frankfurter", "base": base, "rates": {base: 1.0}}
    try:
        payload = await request_json(
            "https://api.frankfurter.dev/v2/rates",
            params={"base": base, "quotes": ",".join(target_codes)},
        )
    except ProviderError as exc:
        return provider_error("Frankfurter", exc)
    if not isinstance(payload, list):
        return provider_error("Frankfurter", ProviderError("No exchange-rate list was returned."))
    rates = {
        row["quote"]: row["rate"]
        for row in payload
        if isinstance(row, dict)
        and row.get("quote") in target_codes
        and isinstance(row.get("rate"), (int, float))
    }
    if not rates:
        return provider_error("Frankfurter", ProviderError("No requested exchange rates were returned."))
    return {
        "status": "success",
        "provider": "Frankfurter",
        "base": base,
        "date": payload[0].get("date") if payload and isinstance(payload[0], dict) else None,
        "rates": rates,
        "source_url": "https://frankfurter.dev/",
    }


async def holiday_calendar(year: int, country_code: str = "IN") -> Dict[str, Any]:
    """Fetch the public holiday calendar for a country and calendar year."""
    if not isinstance(year, int) or isinstance(year, bool) or not 1 <= year <= 9999:
        return invalid_input("year must be between 1 and 9999.")
    country_code = country_code.strip().upper() if isinstance(country_code, str) else ""
    if not re.fullmatch(r"[A-Z]{2}", country_code):
        return invalid_input("country_code must be a two-letter ISO country code.")
    if not settings.CALENDARIFIC_API_KEY:
        return missing_credential("Calendarific", "CALENDARIFIC_API_KEY")
    try:
        payload = await request_json(
            "https://calendarific.com/api/v2/holidays",
            params={
                "api_key": settings.CALENDARIFIC_API_KEY,
                "country": country_code,
                "year": year,
            },
        )
    except ProviderError as exc:
        return provider_error("Calendarific", exc)
    response = payload.get("response")
    holidays = response.get("holidays") if isinstance(response, dict) else None
    meta = payload.get("meta")
    if not isinstance(holidays, list) or not isinstance(meta, dict) or meta.get("code") != 200:
        return provider_error("Calendarific", ProviderError("No holiday list was returned."))
    return {
        "status": "success",
        "provider": "Calendarific",
        "year": year,
        "country_code": country_code,
        "count": len(holidays),
        "holidays": holidays,
        "source_url": "https://calendarific.com/api-documentation",
    }


async def gold_price() -> Dict[str, Any]:
    """Fetch the INR spot gold price per gram; local taxes and premiums are excluded."""
    if not settings.METALS_API_KEY:
        return missing_credential("Metals-API", "METALS_API_KEY")
    try:
        payload = await request_json(
            "https://metals-api.com/api/latest",
            params={
                "access_key": settings.METALS_API_KEY,
                "base": "INR",
                "symbols": "XAU",
            },
        )
    except ProviderError as exc:
        return provider_error("Metals-API", exc)
    rates = payload.get("rates")
    rate = rates.get("XAU") if isinstance(rates, dict) else None
    if payload.get("success") is False or not isinstance(rate, (int, float)) or rate <= 0:
        return provider_error("Metals-API", ProviderError("A valid INR/XAU quote was not returned."))
    return {
        "status": "success",
        "provider": "Metals-API",
        "currency": "INR",
        "unit": "gram",
        "spot_price_per_gram": round((1 / rate) / 31.1034768, 2),
        "quote_date": payload.get("date"),
        "note": "Spot reference only; excludes Indian taxes, making charges, and local premiums.",
        "source_url": "https://metals-api.com/documentation",
    }


async def fuel_price(city: str, fuel_type: str = "petrol") -> Dict[str, str]:
    """Report when an authorized live fuel-price provider has not been configured."""
    error = _valid_text(city, "city")
    if error:
        return error
    if not isinstance(fuel_type, str) or fuel_type.strip().lower() not in {"petrol", "diesel"}:
        return invalid_input("fuel_type must be 'petrol' or 'diesel'.")
    return {
        "status": "provider_access_required",
        "error": (
            "No stable, documented public India-wide fuel-price API is configured. "
            "Connect a licensed provider before requesting live prices."
        ),
        "city": city.strip(),
        "fuel_type": fuel_type.strip().lower(),
    }


async def iss_tracker(latitude: float, longitude: float, altitude_km: float = 0) -> Dict[str, Any]:
    """Fetch the ISS position above the supplied observer coordinates from N2YO."""
    coordinates = (latitude, longitude, altitude_km)
    if any(
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(value)
        for value in coordinates
    ):
        return invalid_input("latitude, longitude, and altitude_km must be finite numbers.")
    if not -90 <= latitude <= 90:
        return invalid_input("latitude must be between -90 and 90.")
    if not -180 <= longitude <= 180:
        return invalid_input("longitude must be between -180 and 180.")
    if not 0 <= altitude_km <= 10:
        return invalid_input("altitude_km must be between 0 and 10.")
    if not settings.N2YO_API_KEY:
        return missing_credential("N2YO", "N2YO_API_KEY")
    url = (
        "https://api.n2yo.com/rest/v1/satellite/positions/"
        f"25544/{latitude}/{longitude}/{altitude_km}/1"
    )
    try:
        payload = await request_json(url, params={"apiKey": settings.N2YO_API_KEY})
    except ProviderError as exc:
        return provider_error("N2YO", exc)
    positions = payload.get("positions")
    if not isinstance(positions, list) or not positions or not isinstance(positions[0], dict):
        return provider_error("N2YO", ProviderError("No ISS position was returned."))
    position = positions[0]
    return {
        "status": "success",
        "provider": "N2YO",
        "satellite": "ISS",
        "norad_id": 25544,
        "latitude": position.get("satlatitude"),
        "longitude": position.get("satlongitude"),
        "altitude_km": position.get("sataltitude"),
        "timestamp": position.get("timestamp"),
        "source_url": "https://www.n2yo.com/api/",
    }
