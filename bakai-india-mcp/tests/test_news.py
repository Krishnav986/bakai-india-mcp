"""Unit and integration tests for Indian and International News module."""

import pytest
from news.news_tools import (
    india_news,
    assam_news,
    world_news,
    technology_news,
    sports_news,
    news_search,
)


@pytest.mark.asyncio
async def test_india_news_fetch():
    """Verifies that national Indian news returns valid real articles with dates and publishers."""
    res = await india_news(limit=3)
    assert res["status"] == "success"
    assert res["count"] > 0
    assert len(res["articles"]) <= 3

    top = res["articles"][0]
    assert "title" in top and top["title"]
    assert "url" in top and top["url"].startswith("http")
    assert "publisher" in top and top["publisher"]
    assert "published_at" in top and top["published_at"]
    assert res["speech"].startswith("बॉस")


@pytest.mark.asyncio
async def test_assam_news_fetch():
    """Verifies Assam and Northeast regional news fetching."""
    res = await assam_news(limit=3)
    assert res["status"] in ("success", "unavailable")
    if res["status"] == "success":
        assert res["count"] > 0
        article = res["articles"][0]
        assert "title" in article
        assert "url" in article


@pytest.mark.asyncio
async def test_world_news_fetch():
    """Verifies international news feeds."""
    res = await world_news(limit=3)
    assert res["status"] == "success"
    assert res["count"] > 0
    assert "articles" in res
    assert len(res["articles"]) <= 3


@pytest.mark.asyncio
async def test_technology_news_fetch():
    """Verifies tech news feeds."""
    res = await technology_news(limit=3)
    assert res["status"] == "success"
    assert res["count"] > 0
    top = res["articles"][0]
    assert "title" in top


@pytest.mark.asyncio
async def test_sports_news_fetch():
    """Verifies sports news feeds."""
    res = await sports_news(limit=3)
    assert res["status"] == "success"
    assert res["count"] > 0
    top = res["articles"][0]
    assert "title" in top


@pytest.mark.asyncio
async def test_news_search():
    """Verifies keyword search across news."""
    res = await news_search("ISRO", limit=2)
    assert res["status"] in ("success", "not_found")
    if res["status"] == "success":
        assert res["count"] > 0
        assert "ISRO" in res["query"]
