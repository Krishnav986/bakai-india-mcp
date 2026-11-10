"""Tests for MCP server instance, tool manifest, and Xiaozhi bridge execution."""

import pytest
from server import mcp
from bridge.bridge_runner import XiaozhiWebSocketBridge


def test_mcp_server_initialization():
    """Verifies that the MCP server initializes with all required tools."""
    tools_dict = getattr(mcp._tool_manager, "_tools", {})
    assert len(tools_dict) == 51, f"Expected 51 tools, found {len(tools_dict)}"

    required_tools = [
        "india_radio_list",
        "radio_search",
        "radio_play",
        "radio_stop",
        "radio_now_playing",
        "india_news",
        "assam_news",
        "world_news",
        "technology_news",
        "sports_news",
        "news_search",
        "youtube_search",
        "youtube_open",
        "spotify_search",
        "spotify_open",
        "music_control",
        "music_now_playing",
        "amazon_search",
        "amazon_product_info",
        "open_website",
        "website_search",
        "web_search",
        "deep_research",
        "fact_check",
        "general_knowledge",
        "get_weather",
        "weather_forecast",
        "get_india_time",
        "calculator",
        "unit_converter",
        "phone_find_contact",
        "check_aqi",
        "cricket_live_score",
        "cricket_schedule",
        "flight_search",
        "flight_status",
        "train_search",
        "train_pnr_status",
        "bus_search",
        "bus_live_tracking",
        "metro_routes",
        "traffic_status",
        "map_directions",
        "fuel_price",
        "gold_price",
        "earthquake_alerts",
        "rain_alert",
        "uv_index",
        "exchange_rates",
        "holiday_calendar",
        "iss_tracker",
    ]

    for tool_name in required_tools:
        assert tool_name in tools_dict, f"Missing required tool: {tool_name}"


def test_xiaozhi_bridge_tool_manifest():
    """Verifies that the Xiaozhi bridge properly generates tools/list manifest."""
    bridge = XiaozhiWebSocketBridge(ws_url="wss://mock.xiaozhi.me/v1/mcp")
    manifest = bridge.build_tool_manifest()
    assert len(manifest) == 51

    names = [t["name"] for t in manifest]
    assert "radio_play" in names
    assert "assam_news" in names
    assert "calculator" in names
    for tool_name in (
        "check_aqi",
        "cricket_live_score",
        "cricket_schedule",
        "flight_search",
        "flight_status",
        "train_search",
        "train_pnr_status",
        "bus_search",
        "bus_live_tracking",
        "metro_routes",
        "traffic_status",
        "map_directions",
        "fuel_price",
        "gold_price",
        "earthquake_alerts",
        "rain_alert",
        "uv_index",
        "exchange_rates",
        "holiday_calendar",
        "iss_tracker",
    ):
        assert tool_name in names


@pytest.mark.asyncio
async def test_xiaozhi_bridge_tool_execution():
    """Tests executing tools through the bridge dispatcher."""
    bridge = XiaozhiWebSocketBridge(ws_url="wss://mock.xiaozhi.me/v1/mcp")

    # 1. Execute calculator
    calc_res = await bridge.execute_tool("calculator", {"expression": "50 * 2"})
    assert calc_res["status"] == "success"
    assert calc_res["result"] == 100

    # 2. Execute get_india_time
    time_res = await bridge.execute_tool("get_india_time", {})
    assert time_res["status"] == "success"
    assert time_res["utc_offset"] == "+05:30"

    # 3. Non-existent tool call
    err_res = await bridge.execute_tool("invalid_unknown_tool", {})
    assert err_res["status"] == "error"
    assert "not found" in err_res["error"]
