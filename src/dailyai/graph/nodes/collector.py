"""
Node: Collector
Fetches raw news articles from Google News RSS feeds.
"""

import asyncio
import logging
import time
from datetime import UTC, datetime, timedelta

import feedparser
import httpx

from dailyai.config import (
    GOOGLE_NEWS_RSS,
    LANG_MAP,
    RSS_MAX_ITEMS_PER_FEED,
    RSS_TIMEOUT_SECONDS,
)

logger = logging.getLogger("dailyai.graph.collector")


async def _fetch_rss_feed(
    query: str,
    gl: str = "US",
    hl: str = "en",
    max_items: int = RSS_MAX_ITEMS_PER_FEED,
) -> list[dict]:
    """Fetch items from a single Google News RSS feed."""
    url = GOOGLE_NEWS_RSS.format(query=query, hl=hl, gl=gl)
    try:
        async with httpx.AsyncClient(timeout=RSS_TIMEOUT_SECONDS, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0 DailyAI/2.0"})
            resp.raise_for_status()
    except Exception as e:
        logger.warning(f"[Collector] RSS fetch failed for query={query[:30]}: {e}")
        return []

    feed = feedparser.parse(resp.text)
    cutoff = datetime.now(UTC) - timedelta(hours=26)
    items: list[dict] = []

    for entry in feed.entries[:max_items]:
        published = None
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            from time import mktime

            published = datetime.fromtimestamp(mktime(entry.published_parsed), tz=UTC)

        if published and published < cutoff:
            continue

        items.append(
            {
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "source": (
                    entry.get("source", {}).get("title", "") if hasattr(entry, "source") else ""
                ),
                "summary": entry.get("summary", entry.get("description", "")),
                "published": published.isoformat() if published else "",
            }
        )

    return items


async def run(state: dict) -> dict:
    """Collector node: Fetch raw news from multiple RSS feeds.

    Reads: country_code
    Writes: raw_articles, node_timings
    """
    from dailyai.storage.backend import get_rss_feeds

    start = time.time()
    country_code = state.get("country_code", "GLOBAL")
    hl = state.get("language", "en")
    gl = LANG_MAP.get(country_code, ("en", "US"))[1]

    # Fetch global queries as baseline
    global_feeds = await get_rss_feeds("GLOBAL")
    queries = {f["feed_key"]: f["query"] for f in global_feeds if f.get("is_active")}

    # Merge country-specific queries if applicable
    if country_code != "GLOBAL":
        country_feeds = await get_rss_feeds(country_code)
        country_queries = {f["feed_key"]: f["query"] for f in country_feeds if f.get("is_active")}
        queries.update(country_queries)

    if not queries:
        logger.warning(f"No active RSS feeds found for country '{country_code}' or GLOBAL")

    # Fetch all feeds concurrently
    tasks = [_fetch_rss_feed(q, gl=gl, hl=hl) for q in queries.values()]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Collect results, track failures
    all_items: list[dict] = []
    fail_count = 0
    for r in results:
        if isinstance(r, Exception):
            fail_count += 1
        elif isinstance(r, list):
            all_items.extend(r)

    errors = state.get("errors", [])
    if fail_count >= 3:
        errors.append(f"Collector: {fail_count}/{len(results)} RSS feeds failed")

    elapsed = time.time() - start
    timings = state.get("node_timings", {})
    timings["collector"] = round(elapsed, 2)

    logger.info(f"[Collector] Fetched {len(all_items)} raw articles in {elapsed:.1f}s")

    return {
        "raw_articles": all_items,
        "errors": errors,
        "node_timings": timings,
    }
