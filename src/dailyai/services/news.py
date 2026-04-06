"""
DailyAI — News Service
Core news management: refresh, retrieve, and format feeds.
Bridges the LangGraph pipeline with the storage and UI layers.
"""

import asyncio
import hashlib
import logging
import time
from datetime import UTC, datetime

from dailyai.config import (
    COUNTRIES,
    MAX_FEED_SIZE,
    MIN_FEED_SIZE,
    REFRESH_COOLDOWN_SECONDS,
    normalize_language,
    store_key,
)
from dailyai.graph.pipeline import run_pipeline
from dailyai.llm.prompts import BRIEF_PROMPT, sanitize_llm_response
from dailyai.storage import sqlite as db

logger = logging.getLogger("dailyai.services.news")

# Refresh throttling
_last_refresh: dict[str, float] = {}
_refresh_locks: dict[str, asyncio.Lock] = {}


async def refresh_news(country_code: str = "GLOBAL", language: str = "en") -> None:
    """Refresh news for a country/language combination using the LangGraph pipeline."""
    language = normalize_language(language)
    key = store_key(country_code, language)

    lock = _refresh_locks.setdefault(key, asyncio.Lock())
    now = time.monotonic()
    last = _last_refresh.get(key, 0.0)

    # Cooldown check
    existing_count = await db.get_articles_count(key)
    if existing_count > 0 and now - last < REFRESH_COOLDOWN_SECONDS:
        logger.info(f"Skipping refresh for {key} (cooldown)")
        return

    if lock.locked():
        logger.info(f"Refresh already running for {key}")
        return

    async with lock:
        _last_refresh[key] = time.monotonic()
        logger.info(f"Refreshing news for {country_code} ({language})")

        try:
            # Run the LangGraph pipeline
            country_name = COUNTRIES.get(country_code, country_code)
            feed = await run_pipeline(
                country_code=country_code,
                country_name=country_name,
                language=language,
            )

            if not feed:
                logger.warning(f"Pipeline returned empty feed for {key}")
                return

            # Merge with existing articles (keep unique by title)
            existing = await db.get_articles(key)
            seen_titles: set[str] = set()
            merged: list[dict] = []

            for article in feed + existing:
                title = article.get("headline", article.get("title", ""))
                if title not in seen_titles and len(merged) < MAX_FEED_SIZE:
                    seen_titles.add(title)
                    # Normalize to storage format
                    merged.append({
                        "title": article.get("headline", article.get("title", "")),
                        "summary": article.get("summary", ""),
                        "why_it_matters": article.get("why_it_matters", ""),
                        "category": article.get("category", "general"),
                        "topic": article.get("topic", "general"),
                        "importance": int(article.get("importance", 5)),
                        "source": article.get("source_name", article.get("source", "")),
                        "source_trust": article.get("source_trust", "low"),
                        "sentiment": article.get("sentiment", "neutral"),
                        "story_thread": article.get("story_thread", ""),
                        "link": article.get("article_url", article.get("link", "")),
                        "published": article.get("published_at", article.get("published", "")),
                        "fetched_at": article.get("updated_at", article.get("fetched_at", "")),
                    })

            await db.save_articles(key, merged)
            await db.set_metadata(
                f"last_updated:{key}",
                datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
            )
            logger.info(f"Saved {len(merged)} articles for {key}")

        except Exception as e:
            logger.error(f"Error refreshing {key}: {e}", exc_info=True)


async def get_feed(
    country: str = "GLOBAL",
    language: str = "en",
    topic: str = "all",
    sync_code: str = "",
    offset: int = 0,
    limit: int = 15,
) -> dict:
    """Get the formatted news feed with pagination and optional personalization."""
    country = country.upper()
    language = normalize_language(language)
    if country not in COUNTRIES:
        country = "GLOBAL"

    key = store_key(country, language)

    # Ensure we have articles
    count = await db.get_articles_count(key)
    if count == 0:
        await refresh_news(country, language)

    articles = await db.get_articles(key)

    # Fallback chain if insufficient articles
    if len(articles) < MIN_FEED_SIZE:
        global_key = store_key("GLOBAL", language)
        if global_key != key:
            global_count = await db.get_articles_count(global_key)
            if global_count == 0:
                await refresh_news("GLOBAL", language)
            global_articles = await db.get_articles(global_key)
            existing_titles = {a.get("title", "") for a in articles}
            for a in global_articles:
                if a.get("title", "") not in existing_titles:
                    articles.append(a)
                if len(articles) >= MAX_FEED_SIZE:
                    break

    if len(articles) < MIN_FEED_SIZE and language != "en":
        en_key = store_key("GLOBAL", "en")
        en_count = await db.get_articles_count(en_key)
        if en_count == 0:
            await refresh_news("GLOBAL", "en")
        en_articles = await db.get_articles(en_key)
        existing_titles = {a.get("title", "") for a in articles}
        for a in en_articles:
            if a.get("title", "") not in existing_titles:
                articles.append(a)
            if len(articles) >= MAX_FEED_SIZE:
                break

    # Format for UI
    from dailyai.config import UI_TOPIC_MAP

    feed_articles: list[dict] = []
    for a in articles:
        internal_topic = (a.get("topic", "general") or "general").lower()
        ui_topic = UI_TOPIC_MAP.get(internal_topic, "Top Stories")

        # Topic filter
        if topic not in ("all", "For You") and ui_topic != topic:
            continue

        # Thread count
        story_thread = str(a.get("story_thread", "")).strip()
        thread_count = 0
        if story_thread:
            thread_count = sum(
                1 for other in articles
                if str(other.get("story_thread", "")).strip().lower() == story_thread.lower()
            )

        # Stable ID across refreshes/page sizes to keep article links resilient.
        identity = "|".join([
            str(a.get("title", "") or ""),
            str(a.get("source", "") or ""),
            str(a.get("published", "") or ""),
            str(a.get("link", "") or ""),
        ])
        stable_id = hashlib.sha1(identity.encode("utf-8", errors="ignore")).hexdigest()[:12]

        feed_articles.append({
            "id": f"{country}-{language}-{stable_id}",
            "headline": a.get("title", ""),
            "summary": a.get("summary", ""),
            "why_it_matters": a.get("why_it_matters", ""),
            "importance": max(1, min(int(a.get("importance", 5)), 10)),
            "category": str(a.get("category", "general")).lower(),
            "topic": ui_topic,
            "source_name": a.get("source", "Unknown"),
            "source_trust": a.get("source_trust", "low"),
            "sentiment": a.get("sentiment", "neutral"),
            "story_thread": story_thread,
            "thread_count": thread_count,
            "article_url": a.get("link", "#"),
            "published_at": a.get("published", ""),
            "updated_at": a.get("fetched_at", ""),
        })

    # Sort by importance
    feed_articles.sort(
        key=lambda x: (int(x.get("importance", 0)), x.get("published_at", "")),
        reverse=True,
    )

    # Personalization
    if sync_code:
        try:
            from dailyai.services.profiles import get_topic_scores
            scores = await get_topic_scores(sync_code)
            if scores:
                # Split into common (top 5) + personalized
                common = feed_articles[:5]
                rest = feed_articles[5:]

                def rank(a: dict) -> float:
                    cat = a.get("category", "general")
                    t = a.get("topic", "Top Stories")
                    s = float(scores.get(cat, 0)) + float(scores.get(t, 0))
                    return s * 2.0 + float(a.get("importance", 5))

                rest.sort(key=rank, reverse=True)
                feed_articles = common + rest
        except Exception as e:
            logger.warning(f"Personalization failed: {e}")

    # Pagination
    total = len(feed_articles)
    has_more = offset + limit < total
    page = feed_articles[offset:offset + limit]

    last_updated = await db.get_metadata(f"last_updated:{key}") or "-"

    return {
        "articles": page,
        "total": total,
        "offset": offset,
        "limit": limit,
        "has_more": has_more,
        "country": country,
        "country_name": COUNTRIES.get(country, country),
        "language": language,
        "last_updated": last_updated,
    }


async def get_article_brief(
    title: str,
    source: str = "",
    link: str = "",
    summary: str = "",
    why_it_matters: str = "",
    topic: str = "general",
    language: str = "en",
) -> str:
    """Generate a detailed brief for one article using the fast LLM."""
    from dailyai.config import SUPPORTED_LANGUAGES
    from dailyai.llm.provider import invoke_llm

    output_language = SUPPORTED_LANGUAGES.get(language, "English")

    prompt = BRIEF_PROMPT.format_messages(
        output_language=output_language,
        title=title,
        source=source,
        topic=topic,
        link=link,
        summary=summary,
        why_it_matters=why_it_matters,
    )

    system_msg = prompt[0].content
    human_msg = prompt[1].content

    response = await invoke_llm(system_msg, human_msg, fast=True)
    cleaned = (response or "").strip()

    if not cleaned:
        return summary or why_it_matters or "No additional details available yet."

    sanitized = sanitize_llm_response(cleaned)
    if not sanitized:
        return summary or why_it_matters or "No additional details available yet."

    return sanitized[:1200]
