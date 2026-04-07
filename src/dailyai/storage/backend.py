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
