import asyncio
import logging
import os
from datetime import UTC, datetime

from agent import NewsAgent
from services.config import COUNTRIES, MAX_TILES, UI_TOPIC_MAP, normalize_language, store_key
from services.store import LAST_UPDATED, NEWS_STORE

logger = logging.getLogger("dailyai.news")
agent = NewsAgent(hf_token=os.getenv("HF_API_TOKEN", ""))


async def refresh_news(country_code: str = "GLOBAL", language: str = "en") -> None:
    language = normalize_language(language)
    key = store_key(country_code, language)
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


async def get_articles_payload(topic: str, country: str, language: str,
                                sync_code: str = "") -> dict:
    country = country.upper()
    language = normalize_language(language)
    if country not in COUNTRIES:
        country = "GLOBAL"

    key = store_key(country, language)
    global_key = store_key("GLOBAL", language)

    if key not in NEWS_STORE:
        await refresh_news(country, language)

    tiles = list(NEWS_STORE.get(key, []))

    if len(tiles) < 10 and country != "GLOBAL":
        if global_key not in NEWS_STORE:
            await refresh_news("GLOBAL", language)
        global_tiles = NEWS_STORE.get(global_key, [])
        existing_titles = {t.get("title", "").lower() for t in tiles}
        for gt in global_tiles:
            title = gt.get("title", "").lower()
            if title and title not in existing_titles:
                tiles.append(gt)
            if len(tiles) >= 20:
                break

    tiles = tiles[:20]
    articles = []
    for i, t in enumerate(tiles):
        internal_topic = (t.get("topic") or t.get("category") or "general").lower()
        ui_topic = UI_TOPIC_MAP.get(internal_topic, "Top Stories")

        if topic not in ("all", "For You") and ui_topic != topic:
            continue

        importance = int(t.get("importance", 5) or 5)
        category = str(t.get("category", "general") or "general").lower()
        confidence_key = "high" if importance >= 8 else "medium" if importance >= 6 else "low"
        impact_key = "immediate" if importance >= 7 or category in {"regulation", "product", "funding"} else "watchlist"

        articles.append(
            {
                "id": f"{country}-{language}-{i}",
                "headline": t.get("title", ""),
                "summary": (t.get("summary", "") or "")[:1400],
                "why_it_matters": (t.get("why_it_matters", "") or "")[:130],
                "importance": max(1, min(importance, 10)),
                "category": category,
                "confidence": confidence_key,
                "impact": impact_key,
                "topic": ui_topic,
                "source_name": t.get("source", "Unknown"),
                "source_avatar_url": None,
                "image_url": None,
                "article_url": t.get("link", "#"),
                "published_at": t.get("published", t.get("fetched_at", "")),
                "updated_at": t.get("fetched_at", t.get("published", "")),
            }
        )

    # ── Personalized re-ranking ──────────────────────────────────
    if sync_code:
        try:
            from services.profiles import get_topic_scores
            scores = get_topic_scores(sync_code)
            if scores:
                def rank_score(article: dict) -> float:
                    cat = article.get("category", "general")
                    pref_score = scores.get(cat, 0)
                    imp_score = article.get("importance", 5)
                    return pref_score * 2 + imp_score

                articles.sort(key=rank_score, reverse=True)
                logger.info(f"[Feed] Personalized for {sync_code} ({len(scores)} topic scores)")
        except Exception as e:
            logger.warning(f"[Feed] Personalization failed for {sync_code}: {e}")

    return {
        "articles": articles,
        "country": country,
        "country_name": COUNTRIES.get(country, country),
        "language": language,
    }
