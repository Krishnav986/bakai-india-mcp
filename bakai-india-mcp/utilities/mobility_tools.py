"""Flight, rail, bus, and map tools for BAKAI."""

from __future__ import annotations

import datetime as dt
import re
from typing import Any, Dict, Optional
from urllib.parse import urlencode

from core.config import settings
from utilities.live_api import (
    ProviderError,
    invalid_input,
    missing_credential,
    provider_error,
    request_json,
)

_AMADEUS_BASE_URL = "https://api.amadeus.com"
_AVIATIONSTACK_URL = "https://api.aviationstack.com/v1/flights"
_GOOGLE_ROUTES_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"
_IRCTC_TRAIN_SEARCH_URL = "https://www.irctc.co.in/nget/train-search"
_IRCTC_PNR_URL = "https://www.indianrail.gov.in/enquiry/PNR/PnrEnquiry.html?locale=en"
_REDBUS_URL = "https://www.redbus.in/"


def _text_error(value: str, label: str, max_length: int = 120) -> Optional[Dict[str, str]]:
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > max_length:
        return invalid_input(f"{label} must be a non-empty string of at most {max_length} characters.")
    return None


def _maps_link(origin: str, destination: str, mode: str) -> str:
    travel_mode = {"DRIVE": "driving", "WALK": "walking", "BICYCLE": "bicycling", "TRANSIT": "transit"}.get(
        mode, "driving"
    )
    return "https://www.google.com/maps/dir/?" + urlencode(
        {"api": "1", "origin": origin, "destination": destination, "travelmode": travel_mode}
    )


async def _maps_route(origin: str, destination: str, mode: str) -> Dict[str, Any]:
    if not settings.GOOGLE_MAPS_API_KEY:
        return {
            "status": "provider_link_only",
            "error": "Configure GOOGLE_MAPS_API_KEY for structured live route results.",
            "provider_url": _maps_link(origin, destination, mode),
        }

    field_mask = (
        "routes.duration,routes.staticDuration,routes.distanceMeters,"
        "routes.legs.steps.navigationInstruction.instructions,"
        "routes.legs.steps.transitDetails"
    )
    body: Dict[str, Any] = {
        "origin": {"address": origin.strip()},
        "destination": {"address": destination.strip()},
        "travelMode": mode,
        "languageCode": "en",
        "units": "METRIC",
    }
    if mode == "DRIVE":
        body["routingPreference"] = "TRAFFIC_AWARE"
    try:
        payload = await request_json(
            _GOOGLE_ROUTES_URL,
            method="POST",
            headers={
                "X-Goog-Api-Key": settings.GOOGLE_MAPS_API_KEY,
                "X-Goog-FieldMask": field_mask,
            },
            json_body=body,
        )
    except ProviderError as exc:
        return provider_error("Google Maps Routes API", exc)
    if payload.get("error"):
        return provider_error("Google Maps Routes API", ProviderError("The provider rejected the route request."))
    routes = payload.get("routes")
    if not isinstance(routes, list):
        return provider_error("Google Maps Routes API", ProviderError("No route list was returned."))
    if not routes:
        return {"status": "not_found", "provider": "Google Maps Routes API", "routes": []}
    return {
        "status": "success",
        "provider": "Google Maps Routes API",
        "origin": origin.strip(),
        "destination": destination.strip(),
        "routes": routes,
        "provider_url": _maps_link(origin, destination, mode),
    }


async def flight_search(
    origin: str,
    destination: str,
    departure_date: str,
    adults: int = 1,
    limit: int = 5,
) -> Dict[str, Any]:
    """Search real flight offers via the production Amadeus Self-Service API."""
    origin = origin.strip().upper() if isinstance(origin, str) else ""
    destination = destination.strip().upper() if isinstance(destination, str) else ""
    if not re.fullmatch(r"[A-Z]{3}", origin) or not re.fullmatch(r"[A-Z]{3}", destination):
        return invalid_input("origin and destination must be three-letter IATA airport codes.")
    try:
        parsed_date = dt.date.fromisoformat(departure_date)
    except (TypeError, ValueError):
        return invalid_input("departure_date must use YYYY-MM-DD format.")
    if parsed_date.isoformat() != departure_date:
        return invalid_input("departure_date must use YYYY-MM-DD format.")
    if not isinstance(adults, int) or isinstance(adults, bool) or not 1 <= adults <= 9:
        return invalid_input("adults must be between 1 and 9.")
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 10:
        return invalid_input("limit must be between 1 and 10.")
    if not settings.AMADEUS_CLIENT_ID or not settings.AMADEUS_CLIENT_SECRET:
        return missing_credential("Amadeus", "AMADEUS_CLIENT_ID and AMADEUS_CLIENT_SECRET")

    try:
        token_payload = await request_json(
            f"{_AMADEUS_BASE_URL}/v1/security/oauth2/token",
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            form_data={
                "grant_type": "client_credentials",
                "client_id": settings.AMADEUS_CLIENT_ID,
                "client_secret": settings.AMADEUS_CLIENT_SECRET,
            },
        )
        access_token = token_payload.get("access_token")
        if not isinstance(access_token, str) or not access_token:
            raise ProviderError("Amadeus did not return an access token.")
        payload = await request_json(
            f"{_AMADEUS_BASE_URL}/v2/shopping/flight-offers",
            params={
                "originLocationCode": origin,
                "destinationLocationCode": destination,
                "departureDate": departure_date,
                "adults": adults,
                "max": limit,
            },
            headers={"Authorization": f"Bearer {access_token}"},
        )
    except ProviderError as exc:
        return provider_error("Amadeus", exc)

    offers = payload.get("data")
    if not isinstance(offers, list):
        return provider_error("Amadeus", ProviderError("No flight-offer list was returned."))
    return {
        "status": "success",
        "provider": "Amadeus",
        "origin": origin,
        "destination": destination,
        "departure_date": departure_date,
        "count": len(offers[:limit]),
        "offers": offers[:limit],
        "note": "Search results only. No ticket has been reserved, booked, or paid for.",
        "source_url": "https://developers.amadeus.com/",
    }


async def flight_status(flight_number: str) -> Dict[str, Any]:
    """Fetch flight status from Aviationstack using an IATA flight number."""
    error = _text_error(flight_number, "flight_number", 12)
    if error:
        return error
    normalized = re.sub(r"\s+", "", flight_number).upper()
    if not re.fullmatch(r"[A-Z0-9]{2,3}\d{1,4}[A-Z]?", normalized):
        return invalid_input("flight_number must look like an airline code followed by a flight number (for example AI123).")
    if not settings.AVIATIONSTACK_API_KEY:
        return missing_credential("Aviationstack", "AVIATIONSTACK_API_KEY")
    try:
        payload = await request_json(
            _AVIATIONSTACK_URL,
            params={"access_key": settings.AVIATIONSTACK_API_KEY, "flight_iata": normalized},
        )
    except ProviderError as exc:
        return provider_error("Aviationstack", exc)
    flights = payload.get("data")
    if not isinstance(flights, list):
        return provider_error("Aviationstack", ProviderError("No flight-status list was returned."))
    if not flights:
        return {"status": "not_found", "provider": "Aviationstack", "flight_number": normalized}
    selected = []
    for flight in flights[:10]:
        if not isinstance(flight, dict):
            continue
        selected.append(
            {
                "flight_number": (flight.get("flight") or {}).get("iata"),
                "status": flight.get("flight_status"),
                "departure": flight.get("departure"),
                "arrival": flight.get("arrival"),
                "airline": flight.get("airline"),
            }
        )
    return {
        "status": "success",
        "provider": "Aviationstack",
        "flight_number": normalized,
        "count": len(selected),
        "flights": selected,
        "source_url": "https://aviationstack.com/documentation",
    }


async def train_search(
    origin: str,
    destination: str,
    travel_date: Optional[str] = None,
) -> Dict[str, Any]:
    """Return the official IRCTC search page; no unsupported scraping or seat claims."""
    for value, label in ((origin, "origin"), (destination, "destination")):
        error = _text_error(value, label)
        if error:
            return error
    if travel_date:
        try:
            parsed_date = dt.date.fromisoformat(travel_date)
        except (TypeError, ValueError):
            return invalid_input("travel_date must use YYYY-MM-DD format.")
        if parsed_date.isoformat() != travel_date:
            return invalid_input("travel_date must use YYYY-MM-DD format.")
    return {
        "status": "provider_link_only",
        "provider": "IRCTC",
        "origin": origin.strip(),
        "destination": destination.strip(),
        "travel_date": travel_date,
        "provider_url": _IRCTC_TRAIN_SEARCH_URL,
        "message": "Open IRCTC to check current trains, fares, and availability. No live results or seat availability were queried.",
        "note": "No ticket has been reserved, booked, or paid for.",
    }


async def train_pnr_status(pnr: str) -> Dict[str, str]:
    """Require an authorized railway partner for live PNR status lookups."""
    if not isinstance(pnr, str) or not re.fullmatch(r"\d{10}", pnr.strip()):
        return invalid_input("pnr must be exactly 10 digits.")
    return {
        "status": "provider_access_required",
        "provider_url": _IRCTC_PNR_URL,
        "error": (
            "Live PNR lookup requires an authorized railway data provider. "
            "No public PNR API is configured; use the official Indian Railways enquiry page."
        ),
    }


async def bus_search(origin: str, destination: str, travel_date: Optional[str] = None) -> Dict[str, Any]:
    """Return a real redBus provider link without claiming to have searched inventory."""
    for value, label in ((origin, "origin"), (destination, "destination")):
        error = _text_error(value, label)
        if error:
            return error
    if travel_date:
        try:
            parsed_date = dt.date.fromisoformat(travel_date)
        except (TypeError, ValueError):
            return invalid_input("travel_date must use YYYY-MM-DD format.")
        if parsed_date.isoformat() != travel_date:
            return invalid_input("travel_date must use YYYY-MM-DD format.")
    return {
        "status": "provider_link_only",
        "provider": "redBus",
        "origin": origin.strip(),
        "destination": destination.strip(),
        "travel_date": travel_date,
        "provider_url": _REDBUS_URL,
        "message": "Open redBus to search current operators, fares, and seat availability. No inventory was queried.",
        "note": "No ticket has been reserved, booked, or paid for.",
    }


async def bus_live_tracking(ticket_number: str) -> Dict[str, str]:
    """Require an authorized bus operator or ticketing partner for tracking."""
    error = _text_error(ticket_number, "ticket_number", 64)
    if error:
        return error
    return {
        "status": "provider_access_required",
        "provider_url": _REDBUS_URL,
        "error": (
            "Live bus tracking requires the operator's tracking API or an authorized ticketing-partner integration. "
            "No tracking provider is configured."
        ),
    }


async def metro_routes(origin: str, destination: str) -> Dict[str, Any]:
    """Fetch public-transit routes from Google Maps Routes API."""
    for value, label in ((origin, "origin"), (destination, "destination")):
        error = _text_error(value, label)
        if error:
            return error
    return await _maps_route(origin, destination, "TRANSIT")


async def traffic_status(origin: str, destination: str) -> Dict[str, Any]:
    """Fetch a traffic-aware driving route from Google Maps Routes API."""
    for value, label in ((origin, "origin"), (destination, "destination")):
        error = _text_error(value, label)
        if error:
            return error
    result = await _maps_route(origin, destination, "DRIVE")
    if result.get("status") == "success":
        result["traffic_aware"] = True
        result["note"] = "Travel durations are Google Maps traffic-aware route estimates, not a city-wide traffic incident feed."
    return result


async def map_directions(
    origin: str,
    destination: str,
    mode: str = "DRIVE",
) -> Dict[str, Any]:
    """Fetch a route from Google Maps, or provide a Maps link if no API key is configured."""
    for value, label in ((origin, "origin"), (destination, "destination")):
        error = _text_error(value, label)
        if error:
            return error
    mode = mode.strip().upper() if isinstance(mode, str) else ""
    if mode not in {"DRIVE", "WALK", "BICYCLE", "TRANSIT", "TWO_WHEELER"}:
        return invalid_input("mode must be DRIVE, WALK, BICYCLE, TRANSIT, or TWO_WHEELER.")
    return await _maps_route(origin, destination, mode)
