"""Tests for the 20 new live-data and travel MCP tools."""

from __future__ import annotations

from typing import Any, Dict

import httpx
import pytest

from core.config import settings
from utilities import cricket_tools, live_api, live_data_tools, mobility_tools


@pytest.mark.asyncio
async def test_public_data_tools(monkeypatch):
    async def fake_request(url: str, **kwargs: Any) -> Any:
        if "geocoding-api" in url:
            return {
                "results": [
                    {
                        "name": "Delhi",
                        "country": "India",
                        "admin1": "Delhi",
                        "latitude": 28.6,
                        "longitude": 77.2,
                        "timezone": "Asia/Kolkata",
                    }
                ]
            }
        if "air-quality" in url:
            if kwargs.get("params", {}).get("current", "").startswith("us_aqi"):
                return {"current": {"time": "2026-11-04T10:00", "us_aqi": 60, "european_aqi": 45, "pm2_5": 12, "pm10": 20}}
            return {"current": {"time": "2026-11-04T10:00", "uv_index": 3.2, "uv_index_clear_sky": 4.1}}
        if "forecast" in url:
            return {
                "hourly": {
                    "time": ["2026-11-04T11:00", "2026-11-04T12:00"],
                    "precipitation_probability": [30, 70],
                    "precipitation": [0.0, 1.2],
                    "rain": [0.0, 1.2],
                    "showers": [0.0, 0.0],
                }
            }
        if "earthquake.usgs.gov" in url:
            return {
                "features": [
                    {
                        "id": "event-1",
                        "properties": {"mag": 5.1, "place": "Test region", "time": 1, "url": "https://example.test/event"},
                        "geometry": {"coordinates": [90.0, 25.0, 10.0]},
                    }
                ]
            }
        if "frankfurter.dev" in url:
            return [{"date": "2026-11-04", "base": "USD", "quote": "INR", "rate": 88.0}]
        if "calendarific.com" in url:
            return {
                "meta": {"code": 200},
                "response": {
                    "holidays": [
                        {
                            "date": {"iso": "2026-08-15"},
                            "name": "Independence Day",
                        }
                    ]
                },
            }
        if "metals-api.com" in url:
            return {"success": True, "date": "2026-11-04", "rates": {"XAU": 0.0000048}}
        if "api.n2yo.com" in url:
            return {"positions": [{"satlatitude": 10.0, "satlongitude": 20.0, "sataltitude": 420.0, "timestamp": 1}]}
        raise AssertionError(f"Unexpected provider URL: {url}")

    monkeypatch.setattr(live_data_tools, "request_json", fake_request)
    monkeypatch.setattr(settings, "METALS_API_KEY", "test-metals-key")
    monkeypatch.setattr(settings, "N2YO_API_KEY", "test-n2yo-key")
    monkeypatch.setattr(settings, "CALENDARIFIC_API_KEY", "test-calendarific-key")

    assert (await live_data_tools.check_aqi("Delhi"))["us_aqi"] == 60
    rain = await live_data_tools.rain_alert("Delhi", hours_ahead=2)
    assert rain["rain_possible"] is True
    assert rain["forecast_precipitation_mm"] == 1.2
    assert (await live_data_tools.uv_index("Delhi"))["uv_index"] == 3.2
    assert (await live_data_tools.earthquake_alerts())["events"][0]["magnitude"] == 5.1
    assert (await live_data_tools.exchange_rates())["rates"]["INR"] == 88.0
    assert (await live_data_tools.holiday_calendar(2026))["holidays"][0]["name"] == "Independence Day"
    gold = await live_data_tools.gold_price()
    assert gold["status"] == "success"
    assert gold["spot_price_per_gram"] > 0
    assert "excludes Indian taxes" in gold["note"]
    assert (await live_data_tools.fuel_price("Delhi"))["status"] == "provider_access_required"
    iss = await live_data_tools.iss_tracker(28.6, 77.2)
    assert iss["norad_id"] == 25544
    assert iss["latitude"] == 10.0


@pytest.mark.asyncio
async def test_provider_gated_live_data_tools(monkeypatch):
    monkeypatch.setattr(settings, "CRICKET_API_KEY", "test-cricket-key")

    async def fake_cricket_request(url: str, **kwargs: Any) -> Dict[str, Any]:
        assert kwargs["headers"]["x-apisports-key"] == "test-cricket-key"
        return {"response": [{"id": 7, "status": {"long": "In Play"}}]}

    monkeypatch.setattr(cricket_tools, "request_json", fake_cricket_request)
    live = await cricket_tools.cricket_live_score()
    assert live["matches"][0]["id"] == 7
    scheduled = await cricket_tools.cricket_schedule("2026-11-04")
    assert scheduled["match_date"] == "2026-11-04"


@pytest.mark.asyncio
async def test_flight_and_provider_link_tools(monkeypatch):
    monkeypatch.setattr(settings, "AMADEUS_CLIENT_ID", "test-client")
    monkeypatch.setattr(settings, "AMADEUS_CLIENT_SECRET", "test-secret")
    monkeypatch.setattr(settings, "AVIATIONSTACK_API_KEY", "test-flight-key")
    monkeypatch.setattr(settings, "GOOGLE_MAPS_API_KEY", "test-maps-key")

    async def fake_mobility_request(url: str, **kwargs: Any) -> Dict[str, Any]:
        if "oauth2/token" in url:
            assert kwargs["form_data"]["client_id"] == "test-client"
            return {"access_token": "temporary-test-token"}
        if "flight-offers" in url:
            assert kwargs["headers"]["Authorization"] == "Bearer temporary-test-token"
            return {"data": [{"id": "offer-1", "price": {"currency": "INR", "total": "5000"}}]}
        if "aviationstack" in url:
            return {
                "data": [
                    {
                        "flight": {"iata": "AI123"},
                        "flight_status": "active",
                        "departure": {"airport": "DEL"},
                        "arrival": {"airport": "BOM"},
                        "airline": {"name": "Air India"},
                    }
                ]
            }
        if "routes.googleapis.com" in url:
            assert kwargs["headers"]["X-Goog-Api-Key"] == "test-maps-key"
            return {
                "routes": [
                    {
                        "duration": "3600s",
                        "staticDuration": "3000s",
                        "distanceMeters": 12000,
                        "legs": [{"steps": [{"navigationInstruction": {"instructions": "Continue"}}]}],
                    }
                ]
            }
        raise AssertionError(f"Unexpected provider URL: {url}")

    monkeypatch.setattr(mobility_tools, "request_json", fake_mobility_request)
    offers = await mobility_tools.flight_search("DEL", "BOM", "2026-12-01")
    assert offers["offers"][0]["price"]["total"] == "5000"
    assert "No ticket has been reserved" in offers["note"]
    status = await mobility_tools.flight_status("AI 123")
    assert status["flights"][0]["status"] == "active"

    train = await mobility_tools.train_search("New Delhi", "Mumbai", "2026-12-01")
    assert train["status"] == "provider_link_only"
    assert "irctc.co.in" in train["provider_url"]
    assert "No live results" in train["message"]
    assert (await mobility_tools.train_pnr_status("1234567890"))["status"] == "provider_access_required"

    bus = await mobility_tools.bus_search("Delhi", "Jaipur", "2026-12-01")
    assert bus["status"] == "provider_link_only"
    assert bus["provider_url"] == "https://www.redbus.in/"
    assert (await mobility_tools.bus_live_tracking("ticket-1"))["status"] == "provider_access_required"

    metro = await mobility_tools.metro_routes("Rajiv Chowk, Delhi", "Kashmere Gate, Delhi")
    assert metro["routes"][0]["distanceMeters"] == 12000
    traffic = await mobility_tools.traffic_status("Delhi", "Gurugram")
    assert traffic["traffic_aware"] is True
    directions = await mobility_tools.map_directions("Delhi", "Agra", "DRIVE")
    assert directions["routes"][0]["duration"] == "3600s"


@pytest.mark.asyncio
async def test_new_tool_input_and_missing_configuration(monkeypatch):
    monkeypatch.setattr(settings, "CRICKET_API_KEY", None)
    monkeypatch.setattr(settings, "AMADEUS_CLIENT_ID", None)
    monkeypatch.setattr(settings, "AMADEUS_CLIENT_SECRET", None)
    monkeypatch.setattr(settings, "AVIATIONSTACK_API_KEY", None)
    monkeypatch.setattr(settings, "GOOGLE_MAPS_API_KEY", None)
    monkeypatch.setattr(settings, "METALS_API_KEY", None)
    monkeypatch.setattr(settings, "N2YO_API_KEY", None)
    monkeypatch.setattr(settings, "CALENDARIFIC_API_KEY", None)

    assert (await cricket_tools.cricket_live_score())["status"] == "not_configured"
    assert (await cricket_tools.cricket_schedule("not-a-date"))["status"] == "invalid_input"
    assert (await mobility_tools.flight_search("DEL", "BOM", "2026-12-01"))["status"] == "not_configured"
    assert (await mobility_tools.flight_status("AI123"))["status"] == "not_configured"
    assert (await live_data_tools.gold_price())["status"] == "not_configured"
    assert (await live_data_tools.iss_tracker(0, 0))["status"] == "not_configured"
    assert (await mobility_tools.metro_routes("Delhi", "Noida"))["status"] == "provider_link_only"
    assert (await mobility_tools.traffic_status("Delhi", "Noida"))["status"] == "provider_link_only"
    assert (await mobility_tools.map_directions("Delhi", "Noida"))["status"] == "provider_link_only"
    assert (await live_data_tools.check_aqi(""))["status"] == "invalid_input"
    assert (await live_data_tools.rain_alert("Delhi", hours_ahead=0))["status"] == "invalid_input"
    assert (await live_data_tools.exchange_rates(base="US"))["status"] == "invalid_input"
    assert (await live_data_tools.holiday_calendar(2026, "IND"))["status"] == "invalid_input"
    assert (await live_data_tools.holiday_calendar(2026))["status"] == "not_configured"
    assert (await mobility_tools.flight_status("bad"))["status"] == "invalid_input"
    assert (await mobility_tools.train_pnr_status("123"))["status"] == "invalid_input"
    assert (await mobility_tools.map_directions("Delhi", "Noida", "FLY"))["status"] == "invalid_input"


@pytest.mark.asyncio
async def test_live_request_timeout_is_safe(monkeypatch):
    class TimeoutClient:
        def __init__(self, **kwargs: Any) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args: Any) -> None:
            return None

        async def request(self, *args: Any, **kwargs: Any):
            raise httpx.TimeoutException("credential=must-not-be-returned")

    monkeypatch.setattr(live_api.httpx, "AsyncClient", TimeoutClient)
    with pytest.raises(live_api.ProviderError, match="timed out") as exc:
        await live_api.request_json("https://provider.example/test")
    assert "must-not-be-returned" not in str(exc.value)
