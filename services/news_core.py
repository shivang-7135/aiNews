import asyncio
import json
import logging
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from agent import NewsAgent
from services.config import COUNTRIES, MAX_TILES, UI_TOPIC_MAP, normalize_language, store_key
from services.store import LAST_UPDATED, NEWS_STORE

logger = logging.getLogger("dailyai.news")
agent = NewsAgent(hf_token=os.getenv("HF_API_TOKEN", ""))

ARTICLES_CACHE_FILE = Path("articles_cache.json")
MIN_FEED_SIZE = 15
MAX_FEED_SIZE = 30
REFRESH_MIN_INTERVAL_SECONDS = 45
_LAST_REFRESH_ATTEMPT: dict[str, float] = {}
_REFRESH_LOCKS: dict[str, asyncio.Lock] = {}


def _load_articles_cache() -> dict:
    """Load persisted articles from disk."""
    if ARTICLES_CACHE_FILE.exists():
        try:
            return cast(dict, json.loads(ARTICLES_CACHE_FILE.read_text()))
        except (OSError, json.JSONDecodeError):
            pass
    return {}


def _save_articles_cache() -> None:
    """Persist current NEWS_STORE to disk."""
    try:
        snapshot = {k: v for k, v in NEWS_STORE.items() if v}
        ARTICLES_CACHE_FILE.write_text(json.dumps(snapshot, indent=2, default=str))
    except Exception as e:
        logger.warning(f"Failed to save articles cache: {e}")


def restore_from_cache() -> None:
    """On startup, load cached articles into memory."""
    cached = _load_articles_cache()
    for key, tiles in cached.items():
        if key not in NEWS_STORE or not NEWS_STORE[key]:
            NEWS_STORE[key] = tiles
            logger.info(f"Restored {len(tiles)} articles from cache for {key}")


# Restore on module load
restore_from_cache()


async def refresh_news(country_code: str = "GLOBAL", language: str = "en") -> None:
    language = normalize_language(language)
    key = store_key(country_code, language)

    lock = _REFRESH_LOCKS.setdefault(key, asyncio.Lock())
    now = time.monotonic()
    last_attempt = _LAST_REFRESH_ATTEMPT.get(key, 0.0)

    # Skip duplicate rapid refreshes when we already have content.
    if NEWS_STORE.get(key) and now - last_attempt < REFRESH_MIN_INTERVAL_SECONDS:
        logger.info(
            f"Skipping refresh for {country_code} ({language}) due to cooldown "
            f"({REFRESH_MIN_INTERVAL_SECONDS}s)"
        )
        return

    # Avoid concurrent refreshes for the same feed key.
    if lock.locked():
        logger.info(f"Refresh already in progress for {country_code} ({language}), skipping")
        return

    async with lock:
        _LAST_REFRESH_ATTEMPT[key] = time.monotonic()
        logger.info(f"Refreshing news for {country_code} ({language})")
        try:
            tiles = await agent.run(
                country_code=country_code,
                country_name=COUNTRIES.get(country_code, country_code),
                language_code=language,
            )
            if not tiles:
                return

            existing = NEWS_STORE.get(key, [])
            seen_titles = set()
            merged: list[dict] = []
            for t in tiles + existing:
                title = t.get("title", "")
                if title not in seen_titles and len(merged) < MAX_TILES:
                    seen_titles.add(title)
                    merged.append(t)

            NEWS_STORE[key] = merged
            LAST_UPDATED[key] = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
            _save_articles_cache()
        except Exception as exc:
            logger.error(f"Error refreshing {country_code} ({language}): {exc}", exc_info=True)


async def refresh_all() -> None:
    keys = list(set(NEWS_STORE.keys()) | {store_key("GLOBAL", "en")})
    tasks = []
    for key in keys:
        if "::" in key:
            country_code, language = key.split("::", 1)
        else:
            country_code, language = key, "en"
        tasks.append(refresh_news(country_code, language))
    await asyncio.gather(*tasks)


async def get_news_payload(country_code: str, language: str) -> tuple[int, dict]:
    country_code = country_code.upper()
    language = normalize_language(language)
    key = store_key(country_code, language)

    if country_code not in COUNTRIES:
        return 400, {"error": "Unknown country code"}

    if key not in NEWS_STORE:
        await refresh_news(country_code, language)

    tiles = list(NEWS_STORE.get(key, []))
    hero_tile = None
    rest_tiles = tiles
    if tiles:
        sorted_by_imp = sorted(tiles, key=lambda t: t.get("importance", 0), reverse=True)
        hero_tile = sorted_by_imp[0] if sorted_by_imp[0].get("importance", 0) >= 7 else None
        if hero_tile:
            rest_tiles = [t for t in tiles if t.get("title") != hero_tile.get("title")]

    return 200, {
        "country": country_code,
        "language": language,
        "country_name": COUNTRIES[country_code],
        "last_updated": LAST_UPDATED.get(key, "-"),
        "hero_tile": hero_tile,
        "tiles": rest_tiles,
    }


async def get_articles_payload(
    topic: str, country: str, language: str, sync_code: str = "", offset: int = 0, limit: int = 15
) -> dict:
    country = country.upper()
    language = normalize_language(language)
    if country not in COUNTRIES:
        country = "GLOBAL"

    key = store_key(country, language)
    global_key = store_key("GLOBAL", language)
    country_en_key = store_key(country, "en")
    global_en_key = store_key("GLOBAL", "en")

    if key not in NEWS_STORE:
        await refresh_news(country, language)

    tiles = list(NEWS_STORE.get(key, []))

    def _story_fingerprint(tile: dict) -> str:
        title = str(tile.get("title", "") or "").strip().lower()
        link = str(tile.get("link", "") or "").strip().lower()
        return f"{title}::{link}"

    def _merge_unique(base: list[dict], incoming: list[dict]) -> list[dict]:
        seen = {_story_fingerprint(t) for t in base if _story_fingerprint(t) != "::"}
        merged = list(base)
        for tile in incoming:
            fp = _story_fingerprint(tile)
            if fp == "::" or fp in seen:
                continue
            merged.append(tile)
            seen.add(fp)
            if len(merged) >= MAX_FEED_SIZE:
                break
        return merged

    # Ensure we have enough articles for pagination and UX consistency.
    if len(tiles) < MIN_FEED_SIZE:
        # 1) Same-language global pool.
        if global_key not in NEWS_STORE:
            await refresh_news("GLOBAL", language)
        tiles = _merge_unique(tiles, NEWS_STORE.get(global_key, []))

    if len(tiles) < MIN_FEED_SIZE and language != "en":
        # 2) English regional pool, then English global pool.
        if country_en_key not in NEWS_STORE:
            await refresh_news(country, "en")
        tiles = _merge_unique(tiles, NEWS_STORE.get(country_en_key, []))

        if global_en_key not in NEWS_STORE:
            await refresh_news("GLOBAL", "en")
        tiles = _merge_unique(tiles, NEWS_STORE.get(global_en_key, []))

    if len(tiles) < MIN_FEED_SIZE:
        # 3) Last-resort merge from any in-memory stores (same language first, then EN).
        same_lang_keys = [
            k for k in NEWS_STORE if k.endswith(f"::{language}") and k not in {key, global_key}
        ]
        en_keys = [
            k for k in NEWS_STORE if k.endswith("::en") and k not in {country_en_key, global_en_key}
        ]
        for fallback_key in same_lang_keys + en_keys:
            tiles = _merge_unique(tiles, NEWS_STORE.get(fallback_key, []))
            if len(tiles) >= MIN_FEED_SIZE:
                break

    tiles = tiles[:MAX_FEED_SIZE]
    articles = []
    for i, t in enumerate(tiles):
        internal_topic = (t.get("topic") or t.get("category") or "general").lower()
        ui_topic = UI_TOPIC_MAP.get(internal_topic, "Top Stories")

        if topic not in ("all", "For You") and ui_topic != topic:
            continue

        importance = int(t.get("importance", 5) or 5)
        category = str(t.get("category", "general") or "general").lower()

        clean_summary = ""
        clean_why = ""

        # Compute thread count for this story
        story_thread = str(t.get("story_thread", "")).strip()
        thread_count = 0
        if story_thread:
            thread_count = sum(
                1
                for other in tiles
                if str(other.get("story_thread", "")).strip().lower() == story_thread.lower()
            )

        articles.append(
            {
                "id": f"{country}-{language}-{i}",
                "headline": t.get("title", ""),
                "summary": clean_summary,
                "why_it_matters": clean_why,
                "importance": max(1, min(importance, 10)),
                "category": category,
                "topic": ui_topic,
                "source_name": t.get("source", "Unknown"),
                "source_trust": t.get("source_trust", "low"),
                "sentiment": t.get("sentiment", "neutral"),
                "story_thread": story_thread,
                "thread_count": thread_count,
                "source_avatar_url": None,
                "image_url": None,
                "article_url": t.get("link", "#"),
                "published_at": t.get("published", t.get("fetched_at", "")),
                "updated_at": t.get("fetched_at", t.get("published", "")),
            }
        )

    def importance_sort_key(article: dict) -> tuple:
        return (
            int(article.get("importance", 0) or 0),
            str(article.get("published_at", "") or ""),
        )

    common_count = 5
    common_articles = sorted(articles, key=importance_sort_key, reverse=True)[:common_count]
    common_ids = {article.get("id") for article in common_articles}
    personalized_pool = [article for article in articles if article.get("id") not in common_ids]

    if sync_code:
        try:
            from services.profiles import get_topic_scores

            scores = get_topic_scores(sync_code)
            if scores:

                def personalized_rank(article: dict) -> float:
                    category = article.get("category", "general")
                    topic = article.get("topic", "Top Stories")
                    pref_score = float(scores.get(category, 0)) + float(scores.get(topic, 0))
                    imp_score = float(article.get("importance", 5))
                    return pref_score * 2.0 + imp_score

                personalized_pool.sort(key=personalized_rank, reverse=True)
                logger.info(f"[Feed] Personalized for {sync_code} ({len(scores)} topic scores)")
            else:
                personalized_pool.sort(key=importance_sort_key, reverse=True)
        except Exception as e:
            logger.warning(f"[Feed] Personalization failed for {sync_code}: {e}")
            personalized_pool.sort(key=importance_sort_key, reverse=True)
    else:
        personalized_pool.sort(key=importance_sort_key, reverse=True)

    curated_articles = common_articles + personalized_pool
    has_more = offset + limit < len(curated_articles)
    page = curated_articles[offset : offset + limit]

    return {
        "articles": page,
        "common_count": min(common_count, len(common_articles)),
        "total": len(curated_articles),
        "offset": offset,
        "limit": limit,
        "has_more": has_more,
        "country": country,
        "country_name": COUNTRIES.get(country, country),
        "language": language,
    }
