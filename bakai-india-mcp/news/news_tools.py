"""Indian and International News Feeds for BAKAI Robot.

Fetches live, authentic headlines and summaries from trustworthy Indian sources
(The Hindu, The Sentinel Assam, NDTV, Times of India) and global sources (BBC World,
TechCrunch, ESPNcricinfo). Includes full RSS parsing, zero-API-key dependable operation,
and smart search.
"""

from __future__ import annotations

import html
import re
from typing import Any, Dict, List, Optional
import feedparser
import httpx

from core.config import settings
from core.logging import logger
from core.cache import cache, cached
from core.security import sanitize_external_text


def _clean_summary(raw_html: str, max_chars: int = 240) -> str:
    """Strips HTML tags, unescapes entities, and cleans whitespace."""
    if not raw_html:
        return ""
    text = re.sub(r"<[^>]+>", " ", raw_html)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > max_chars:
        return text[:max_chars].rstrip() + "..."
    return text


def _extract_entries(parsed_feed, publisher_fallback: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Extracts standardized news items from a parsed RSS feed object."""
    results = []
    if not parsed_feed or not getattr(parsed_feed, "entries", None):
        return results

    for entry in parsed_feed.entries[:limit]:
        title = sanitize_external_text(entry.get("title", "No Title"), max_chars=200)
        summary = _clean_summary(entry.get("summary") or entry.get("description", ""))
        link = entry.get("link", "")
        pub_date = entry.get("published") or entry.get("updated") or "Recently"
        publisher = entry.get("source", {}).get("title") if isinstance(entry.get("source"), dict) else publisher_fallback

        results.append({
            "title": title,
            "summary": summary,
            "publisher": publisher or publisher_fallback,
            "published_at": pub_date,
            "url": link,
        })
    return results


# Primary Verified RSS Sources
_RSS_SOURCES = {
    "india": [
        ("The Hindu", "https://www.thehindu.com/news/national/feeder/default.rss"),
        ("NDTV India", "https://feeds.feedburner.com/ndtvnews-india-news"),
        ("Times of India", "https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms"),
    ],
    "assam": [
        ("The Sentinel Assam", "https://www.sentinelassam.com/north-east-india-news/assam-news/feed"),
        ("The Sentinel", "https://www.sentinelassam.com/feed"),
    ],
    "world": [
        ("BBC News World", "https://feeds.bbci.co.uk/news/world/rss.xml"),
    ],
    "technology": [
        ("TechCrunch", "https://techcrunch.com/feed/"),
        ("NDTV Gadgets 360", "https://feeds.feedburner.com/gadgets360-latest"),
    ],
    "sports": [
        ("ESPNcricinfo", "https://www.espncricinfo.com/rss/content/story/feeds/0.xml"),
        ("The Hindu Sports", "https://www.thehindu.com/sport/feeder/default.rss"),
    ],
}


@cached(ttl=300, key_prefix="rss_fetch")
async def _fetch_rss(url: str, publisher: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Asynchronously fetches and parses an RSS feed."""
    try:
        async with httpx.AsyncClient(
            headers={"User-Agent": settings.USER_AGENT},
            follow_redirects=True,
            timeout=settings.REQUEST_TIMEOUT,
        ) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                parsed = feedparser.parse(resp.text)
                return _extract_entries(parsed, publisher, limit=limit)
    except Exception as exc:
        logger.warning(f"Failed to fetch RSS from {url}: {exc}")
    return []


# ----------------------------------------------------------------------
# News Tools
# ----------------------------------------------------------------------

async def india_news(category: str = "national", limit: int = 5) -> Dict[str, Any]:
    """Fetches real, top national headlines from India.

    Prioritizes trustworthy publications (The Hindu, NDTV, Times of India).

    Args:
        category: News category ('national', 'politics', 'general').
        limit: Number of headlines to return (default 5, max 10).
    """
    limit = min(max(1, limit), 10)
    items = []

    for pub, url in _RSS_SOURCES["india"]:
        batch = await _fetch_rss(url, pub, limit=limit)
        items.extend(batch)
        if len(items) >= limit:
            break

    items = items[:limit]
    if not items:
        # Fallback to news search
        return await news_search("India national news", limit=limit)

    speech_lines = [f"बॉस, आज की मुख्य भारतीय खबरें हैं:"]
    for i, it in enumerate(items[:3], 1):
        speech_lines.append(f"{i}. {it['title']} ({it['publisher']})।")
    speech = " ".join(speech_lines)

    return {
        "status": "success",
        "category": "india_national",
        "count": len(items),
        "articles": items,
        "speech": speech,
    }


async def assam_news(category: str = "general", limit: int = 5) -> Dict[str, Any]:
    """Fetches the latest news and regional updates from Assam and Northeast India.

    Sources from regional publications (The Sentinel Assam, The Assam Tribune, India Today NE).

    Args:
        category: News category ('general', 'assam', 'northeast').
        limit: Number of headlines to return (default 5, max 10).
    """
    limit = min(max(1, limit), 10)
    items = []

    for pub, url in _RSS_SOURCES["assam"]:
        batch = await _fetch_rss(url, pub, limit=limit)
        items.extend(batch)
        if len(items) >= limit:
            break

    # If Sentinel RSS returned fewer items, augment with search
    if len(items) < limit:
        search_res = await news_search("Assam Guwahati news", limit=limit - len(items))
        if search_res.get("status") == "success":
            for extra in search_res.get("articles", []):
                if not any(extra["title"] == x["title"] for x in items):
                    items.append(extra)

    items = items[:limit]

    if items:
        speech_lines = ["बॉस, असम और पूर्वोत्तर की ताज़ा खबरें ये रहीं:"]
        for i, it in enumerate(items[:3], 1):
            speech_lines.append(f"{i}. {it['title']} ({it['publisher']})।")
        speech = " ".join(speech_lines)
    else:
        speech = "माफ़ कीजिए बॉस, इस समय असम की ताज़ा खबरें प्राप्त नहीं हो सकीं।"

    return {
        "status": "success" if items else "unavailable",
        "category": "assam_northeast",
        "count": len(items),
        "articles": items,
        "speech": speech,
    }


async def world_news(category: str = "general", limit: int = 5) -> Dict[str, Any]:
    """Fetches major global headlines and international news.

    Args:
        category: News category ('general', 'world', 'geopolitics').
        limit: Number of headlines to return (default 5, max 10).
    """
    limit = min(max(1, limit), 10)
    items = []

    for pub, url in _RSS_SOURCES["world"]:
        batch = await _fetch_rss(url, pub, limit=limit)
        items.extend(batch)
        if len(items) >= limit:
            break

    items = items[:limit]
    if not items:
        return await news_search("World top news", limit=limit)

    speech_lines = ["बॉस, आज की मुख्य अंतरराष्ट्रीय खबरें:"]
    for i, it in enumerate(items[:3], 1):
        speech_lines.append(f"{i}. {it['title']} ({it['publisher']})।")
    speech = " ".join(speech_lines)

    return {
        "status": "success",
        "category": "world",
        "count": len(items),
        "articles": items,
        "speech": speech,
    }


async def technology_news(limit: int = 5) -> Dict[str, Any]:
    """Fetches current technology and AI headlines from TechCrunch and Gadgets 360.

    Args:
        limit: Number of headlines to return (default 5, max 10).
    """
    limit = min(max(1, limit), 10)
    items = []

    for pub, url in _RSS_SOURCES["technology"]:
        batch = await _fetch_rss(url, pub, limit=limit)
        items.extend(batch)
        if len(items) >= limit:
            break

    items = items[:limit]
    if not items:
        return await news_search("technology artificial intelligence news", limit=limit)

    speech_lines = ["बॉस, आज की प्रमुख टेक्नोलॉजी खबरें ये हैं:"]
    for i, it in enumerate(items[:3], 1):
        speech_lines.append(f"{i}. {it['title']} ({it['publisher']})।")
    speech = " ".join(speech_lines)

    return {
        "status": "success",
        "category": "technology",
        "count": len(items),
        "articles": items,
        "speech": speech,
    }


async def sports_news(limit: int = 5) -> Dict[str, Any]:
    """Fetches latest sports headlines (Cricket, Football, Olympics, etc.).

    Args:
        limit: Number of headlines to return (default 5, max 10).
    """
    limit = min(max(1, limit), 10)
    items = []

    for pub, url in _RSS_SOURCES["sports"]:
        batch = await _fetch_rss(url, pub, limit=limit)
        items.extend(batch)
        if len(items) >= limit:
            break

    items = items[:limit]
    if not items:
        return await news_search("India sports cricket news", limit=limit)

    speech_lines = ["बॉस, खेल जगत की ताज़ा खबरें:"]
    for i, it in enumerate(items[:3], 1):
        speech_lines.append(f"{i}. {it['title']} ({it['publisher']})।")
    speech = " ".join(speech_lines)

    return {
        "status": "success",
        "category": "sports",
        "count": len(items),
        "articles": items,
        "speech": speech,
    }


async def news_search(query: str, limit: int = 5) -> Dict[str, Any]:
    """Searches recent news articles by keyword or topic across Indian and global news.

    Args:
        query: Topic or keyword to search (e.g. 'ISRO Gaganyaan', 'Guwahati flood', 'T20 World Cup').
        limit: Number of results (default 5, max 10).
    """
    limit = min(max(1, limit), 10)
    cache_key = f"news_search:{query}:{limit}"
    cached_val = await cache.get(cache_key)
    if cached_val:
        return cached_val

    results = []
    try:
        from duckduckgo_search import DDGS
        ddgs = DDGS()
        raw = ddgs.news(query, max_results=limit, region="in-en")
        for r in raw:
            results.append({
                "title": sanitize_external_text(r.get("title", "No Title"), max_chars=200),
                "summary": _clean_summary(r.get("body", "")),
                "publisher": r.get("source", "News Provider"),
                "published_at": r.get("date", "Recent"),
                "url": r.get("url", ""),
            })
    except Exception as exc:
        logger.warning(f"News search failed for query '{query}': {exc}")

    count = len(results)
    if count > 0:
        speech = (
            f"बॉस, मुझे '{query}' पर {count} ताज़ा समाचार मिले हैं। "
            f"प्रमुख ख़बर है: {results[0]['title']} ({results[0]['publisher']})।"
        )
    else:
        speech = f"माफ़ कीजिए बॉस, '{query}' से संबंधित कोई ताज़ा समाचार नहीं मिला।"

    resp = {
        "status": "success" if count > 0 else "not_found",
        "query": query,
        "count": count,
        "articles": results,
        "speech": speech,
    }
    await cache.set(cache_key, resp, ttl=300)
    return resp
