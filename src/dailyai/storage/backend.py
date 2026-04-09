"""Storage backend selector.

SQLite remains the default. Supabase can be enabled with:
- STORAGE_BACKEND=supabase
- SUPABASE_URL
- SUPABASE_KEY
"""

from __future__ import annotations

import logging

from dailyai.config import STORAGE_BACKEND
from dailyai.storage import sqlite, supabase

logger = logging.getLogger("dailyai.storage.backend")


def _select_backend_module():
    if STORAGE_BACKEND == "supabase":
        if supabase.is_configured():
            logger.info("Storage backend: supabase")
            return supabase
        logger.warning(
            "STORAGE_BACKEND=supabase but SUPABASE_URL/SUPABASE_KEY missing; falling back to sqlite"
        )
    return sqlite


_backend = _select_backend_module()


async def get_db():
    return await _backend.get_db()


async def close_db():
    return await _backend.close_db()


async def save_articles(store_key: str, articles: list[dict]) -> None:
    await _backend.save_articles(store_key, articles)


async def get_articles(store_key: str) -> list[dict]:
    return await _backend.get_articles(store_key)


async def get_all_store_keys() -> list[str]:
    return await _backend.get_all_store_keys()


async def get_articles_count(store_key: str) -> int:
    return await _backend.get_articles_count(store_key)


async def save_profile(profile: dict) -> None:
    await _backend.save_profile(profile)


async def get_profile(sync_code: str) -> dict | None:
    return await _backend.get_profile(sync_code)


async def get_all_profiles() -> list[dict]:
    return await _backend.get_all_profiles()


async def save_subscriber(subscriber: dict) -> None:
    await _backend.save_subscriber(subscriber)


async def get_subscriber(email: str) -> dict | None:
    return await _backend.get_subscriber(email)


async def get_all_subscribers() -> list[dict]:
    return await _backend.get_all_subscribers()


async def get_subscriber_count() -> int:
    return await _backend.get_subscriber_count()


async def set_metadata(key: str, value: str) -> None:
    await _backend.set_metadata(key, value)


async def get_metadata(key: str) -> str | None:
    return await _backend.get_metadata(key)


async def get_all_metadata() -> dict[str, str]:
    return await _backend.get_all_metadata()


async def get_cache_health() -> dict:
    return await _backend.get_cache_health()


def backend_name() -> str:
    return "supabase" if _backend is supabase else "sqlite"


# ── Analytics Events ────────────────────────────────────────────────

async def save_events(events: list[dict]) -> None:
    await _backend.save_events(events)


async def get_events(session_id: str, limit: int = 500) -> list[dict]:
    return await _backend.get_events(session_id, limit)


async def get_events_by_sync_code(sync_code: str, limit: int = 1000) -> list[dict]:
    return await _backend.get_events_by_sync_code(sync_code, limit)


async def get_event_counts() -> dict:
    return await _backend.get_event_counts()


# ── Topic Scores ────────────────────────────────────────────────────

async def save_topic_scores(session_id: str, sync_code: str, scores: dict[str, float], event_counts: dict[str, int]) -> None:
    await _backend.save_topic_scores(session_id, sync_code, scores, event_counts)


async def get_topic_scores(session_id: str) -> dict[str, float]:
    return await _backend.get_topic_scores(session_id)


async def get_topic_scores_by_sync_code(sync_code: str) -> dict[str, float]:
    return await _backend.get_topic_scores_by_sync_code(sync_code)


# ── RSS Feeds (Admin) ──────────────────────────────────────────────

async def save_rss_feed(country_code: str, feed_key: str, query: str, is_active: bool = True) -> None:
    await _backend.save_rss_feed(country_code, feed_key, query, is_active)


async def get_rss_feeds(country_code: str | None = None) -> list[dict]:
    feeds = await _backend.get_rss_feeds(country_code)
    
    # Auto-seed from config if no feeds exist for this query
    if not feeds:
        all_feeds = await _backend.get_rss_feeds(None)
        if not all_feeds:
            logger.info("No RSS feeds found in storage. Auto-seeding defaults from config...")
            from dailyai.config import (
                FEED_QUERIES,
                FEED_QUERIES_DE,
                FEED_QUERIES_GB,
                FEED_QUERIES_IN,
            )
            for key, query in FEED_QUERIES.items():
                await save_rss_feed("GLOBAL", key, query, True)
            for key, query in FEED_QUERIES_DE.items():
                await save_rss_feed("DE", key, query, True)
            for key, query in FEED_QUERIES_GB.items():
                await save_rss_feed("GB", key, query, True)
            for key, query in FEED_QUERIES_IN.items():
                await save_rss_feed("IN", key, query, True)
            
            # Fetch again after seeding
            feeds = await _backend.get_rss_feeds(country_code)
            
    return feeds


async def delete_rss_feed(country_code: str, feed_key: str) -> bool:
    return await _backend.delete_rss_feed(country_code, feed_key)
