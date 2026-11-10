"""Unit and integration tests for Indian Radio module."""

import pytest
import asyncio
from radio.radio_tools import (
    _load_stations_db,
    india_radio_list,
    radio_search,
    radio_play,
    radio_stop,
    radio_now_playing,
    radio_state,
)


def test_station_database_integrity():
    """Verifies that the station database loads and contains essential fields."""
    stations = _load_stations_db()
    assert len(stations) >= 15, "Expected at least 15 curated Indian stations"

    station_ids = set()
    for s in stations:
        assert "id" in s and s["id"], "Station missing id"
        assert s["id"] not in station_ids, f"Duplicate station id: {s['id']}"
        station_ids.add(s["id"])

        assert "name" in s and s["name"], "Station missing name"
        assert "stream_url" in s and s["stream_url"].startswith("http"), f"Invalid stream url in {s['name']}"
        assert "language" in s, "Station missing language"
        assert "category" in s, "Station missing category"
        assert "format" in s and s["format"] in ("hls", "aac", "mp3"), f"Unsupported format in {s['name']}"


@pytest.mark.asyncio
async def test_india_radio_list_filters():
    """Tests station filtering by language and region."""
    # Hindi filter
    hindi_res = await india_radio_list(language="hindi")
    assert hindi_res["status"] == "success"
    assert hindi_res["count"] > 0
    assert any("Vividh" in s["name"] for s in hindi_res["stations"])

    # Assamese filter
    assam_res = await india_radio_list(language="assamese")
    assert assam_res["status"] == "success"
    assert assam_res["count"] > 0
    assert any("Nagaon" in s["name"] or "Assam" in s["name"] for s in assam_res["stations"])

    # Non-existent filter
    none_res = await india_radio_list(language="klingon")
    assert none_res["status"] == "success"
    assert none_res["count"] == 0


@pytest.mark.asyncio
async def test_radio_search():
    """Tests searching stations by name and keyword."""
    # Search Vividh Bharati
    res = await radio_search("vividh")
    assert res["status"] == "success"
    assert res["count"] >= 1
    assert "Vividh" in res["results"][0]["name"]

    # Search Assam
    res_assam = await radio_search("assam")
    assert res_assam["status"] == "success"
    assert res_assam["count"] >= 1


@pytest.mark.asyncio
async def test_radio_playback_lifecycle():
    """Tests radio play, now_playing tracking, and stop."""
    # Play Vividh Bharati
    play_res = await radio_play("vividh bharati")
    assert play_res["status"] == "playing"
    assert "Vividh" in play_res["station"]
    assert play_res["robot_action"]["action"] == "play_audio"
    assert play_res["robot_action"]["url"].startswith("http")

    # Check now playing
    now_res = await radio_now_playing()
    assert now_res["status"] == "active"
    assert now_res["is_playing"] is True
    assert "Vividh" in now_res["station"]["name"]

    # Stop playback
    stop_res = await radio_stop()
    assert stop_res["status"] == "stopped"
    assert stop_res["robot_action"]["action"] == "stop_audio"

    # Verify state is idle
    after_stop = await radio_now_playing()
    assert after_stop["status"] == "idle"
    assert after_stop["is_playing"] is False


@pytest.mark.asyncio
async def test_radio_play_unknown():
    """Verifies graceful handling of non-existent stations."""
    res = await radio_play("NonExistentStationXYZ123")
    assert res["status"] == "not_found"
    assert res["robot_action"] is None
    assert "नहीं मिला" in res["speech"]
