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
    LANG_MAP,
    MAX_FEED_SIZE,
    MIN_FEED_SIZE,
    STARTUP_PREFETCH_GLOBAL_LIMIT,
    STARTUP_PREFETCH_OTHER_LIMIT,
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
_startup_prefetch_lock = asyncio.Lock()
_startup_prefetch_done = False


def _infer_topic_category(title: str, summary: str = "", source: str = "") -> tuple[str, str]:
    """Infer internal topic/category to avoid overuse of generic buckets."""
    text = f"{title} {summary} {source}".lower()

    model_keywords = (
        "gpt", "llm", "foundation model", "gemini", "claude", "llama", "mistral", "qwen", "model release",
    )
    research_keywords = (
        "research", "paper", "benchmark", "arxiv", "study", "peer review", "evaluation", "dataset",
    )
    tools_keywords = (
        "sdk", "framework", "developer tool", "open source", "github", "api", "copilot", "plugin", "agent", "tool", "library",
    )
    business_keywords = (
        "funding", "raised", "valuation", "revenue", "enterprise", "partnership", "acquisition", "earnings", "market", "startup", "company",
    )
    regulation_keywords = (
        "regulation", "policy", "act", "compliance", "governance", "law", "eu ai", "safety institute",
    )

    if any(k in text for k in model_keywords):
        return "llms", "product"
    if any(k in text for k in research_keywords):
        return "research", "research"
    if any(k in text for k in tools_keywords):
        return "open_source", "product"
    if any(k in text for k in business_keywords):
        return "startups", "industry"
    if any(k in text for k in regulation_keywords):
        return "regulation", "regulation"
    return "general", "general"


def _match_ui_topic(requested_topic: str, ui_topic: str, category: str, internal_topic: str) -> bool:
    """Flexible topic matching so mobile tabs are rarely empty."""
    if requested_topic in ("all", "For You"):
        return True
    if ui_topic == requested_topic:
        return True

    category = category.lower()
    internal_topic = internal_topic.lower()

    if requested_topic == "AI Models":
        return internal_topic == "llms" or category in {"product", "breakthrough"}
    if requested_topic == "Business":
        return category in {"industry", "funding"} or internal_topic in {"startups", "funding", "big_tech"}
    if requested_topic == "Research":
        return internal_topic in {"research", "robotics", "healthcare", "autonomous"} or category in {"research", "breakthrough"}
    if requested_topic == "Tools":
        return internal_topic in {"open_source", "product"} or category == "product"

    return False


def _topic_keyword_score(requested_topic: str, article: dict) -> int:
    text = f"{article.get('headline', '')} {article.get('summary', '')} {article.get('why_it_matters', '')}".lower()
    topic_keywords = {
        "AI Models": ("model", "llm", "gpt", "gemini", "claude", "llama", "mistral", "qwen"),
        "Business": ("funding", "revenue", "startup", "enterprise", "valuation", "acquisition", "market"),
        "Research": ("research", "study", "paper", "benchmark", "arxiv", "lab", "scientist"),
        "Tools": ("tool", "api", "sdk", "framework", "open source", "github", "agent"),
    }
    keywords = topic_keywords.get(requested_topic, ())
    return sum(1 for k in keywords if k in text)


def get_prefetch_pairs() -> list[tuple[str, str]]:
    """Country/language pairs to hydrate at startup and daily refresh.

    Global English is always first to keep first-screen load snappy.
    """
    pairs: list[tuple[str, str]] = [("GLOBAL", "en")]
    for country in COUNTRIES:
        lang = normalize_language(LANG_MAP.get(country, ("en", country))[0])
        pair = (country, lang)
        if pair not in pairs:
            pairs.append(pair)
    return pairs


async def prefetch_cache_on_startup(force: bool = True) -> None:
    """Warm DB cache for all country/language slices on server startup."""
    global _startup_prefetch_done

    async with _startup_prefetch_lock:
        if _startup_prefetch_done and not force:
            return

        pairs = get_prefetch_pairs()
        logger.info(f"Startup prefetch started for {len(pairs)} country/language keys")

        for country, language in pairs:
            target = STARTUP_PREFETCH_GLOBAL_LIMIT if country == "GLOBAL" else STARTUP_PREFETCH_OTHER_LIMIT
            await refresh_news(country, language, force=force, target_size=target)

        _startup_prefetch_done = True
        logger.info("Startup prefetch completed")


async def refresh_news(
    country_code: str = "GLOBAL",
    language: str = "en",
    *,
    force: bool = False,
    target_size: int | None = None,
) -> None:
    """Refresh news for a country/language combination using the LangGraph pipeline."""
    language = normalize_language(language)
    key = store_key(country_code, language)

    lock = _refresh_locks.setdefault(key, asyncio.Lock())
    now = time.monotonic()
    last = _last_refresh.get(key, 0.0)

    # Cooldown check
    existing_count = await db.get_articles_count(key)
    if not force and existing_count > 0 and now - last < REFRESH_COOLDOWN_SECONDS:
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

            max_items = max(1, min(int(target_size or MAX_FEED_SIZE), MAX_FEED_SIZE))

            for article in feed + existing:
                title = article.get("headline", article.get("title", ""))
                if title not in seen_titles and len(merged) < max_items:
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

                    # Reduce empty category tabs by inferring topic/category for generic rows.
                    inferred_topic, inferred_category = _infer_topic_category(
                        merged[-1]["title"],
                        merged[-1]["summary"],
                        merged[-1]["source"],
                    )
                    if str(merged[-1].get("topic", "general")).lower() in ("", "general"):
                        merged[-1]["topic"] = inferred_topic
                    if str(merged[-1].get("category", "general")).lower() in ("", "general"):
                        merged[-1]["category"] = inferred_category

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
    _allow_topic_refetch: bool = True,
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
    all_formatted: list[dict] = []
    for a in articles:
        internal_topic = (a.get("topic", "general") or "general").lower()
        category = str(a.get("category", "general") or "general").lower()

        if internal_topic in ("", "general"):
            category_to_topic = {
                "product": "open_source",
                "research": "research",
                "industry": "startups",
                "funding": "funding",
                "regulation": "regulation",
                "breakthrough": "llms",
            }
            internal_topic = category_to_topic.get(category, internal_topic)

        if internal_topic in ("", "general") or category in ("", "general"):
            inferred_topic, inferred_category = _infer_topic_category(
                str(a.get("title", "")),
                str(a.get("summary", "")),
                str(a.get("source", "")),
            )
            if internal_topic in ("", "general"):
                internal_topic = inferred_topic
            if category in ("", "general"):
                category = inferred_category

        ui_topic = UI_TOPIC_MAP.get(internal_topic, "Top Stories")

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

        formatted = {
            "id": f"{country}-{language}-{stable_id}",
            "headline": a.get("title", ""),
            "summary": a.get("summary", ""),
            "why_it_matters": a.get("why_it_matters", ""),
            "importance": max(1, min(int(a.get("importance", 5)), 10)),
            "category": category,
            "topic": ui_topic,
            "source_name": a.get("source", "Unknown"),
            "source_trust": a.get("source_trust", "low"),
            "sentiment": a.get("sentiment", "neutral"),
            "story_thread": story_thread,
            "thread_count": thread_count,
            "article_url": a.get("link", "#"),
            "published_at": a.get("published", ""),
            "updated_at": a.get("fetched_at", ""),
        }
        all_formatted.append(formatted)

        if _match_ui_topic(topic, ui_topic, category, internal_topic):
            feed_articles.append(formatted)

    # Sort by importance
    feed_articles.sort(
        key=lambda x: (int(x.get("importance", 0)), x.get("published_at", "")),
        reverse=True,
    )
    all_formatted.sort(
        key=lambda x: (int(x.get("importance", 0)), x.get("published_at", "")),
        reverse=True,
    )

    # If a specific topic has no cached rows, force-refresh once and retry.
    if topic not in ("all", "For You") and not feed_articles and _allow_topic_refetch:
        logger.info(f"Topic cache miss for {key} topic={topic}; forcing one refresh")
        await refresh_news(country, language, force=True)
        return await get_feed(
            country=country,
            language=language,
            topic=topic,
            sync_code=sync_code,
            offset=offset,
            limit=limit,
            _allow_topic_refetch=False,
        )

    # Final non-empty fallback for category tabs after one forced refresh attempt.
    if topic not in ("all", "For You") and not feed_articles and all_formatted:
        scored = sorted(
            all_formatted,
            key=lambda a: (_topic_keyword_score(topic, a), int(a.get("importance", 0))),
            reverse=True,
        )
        best_score = _topic_keyword_score(topic, scored[0]) if scored else 0
        if best_score > 0:
            feed_articles = [a for a in scored if _topic_keyword_score(topic, a) > 0][:20]
        else:
            feed_articles = scored[:10]

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


# ── Brief cache (prevents repeated LLM calls for same article) ──
_brief_cache: dict[str, str] = {}
_BRIEF_CACHE_MAX = 200


async def get_article_brief(
    title: str,
    source: str = "",
    link: str = "",
    summary: str = "",
    why_it_matters: str = "",
    topic: str = "general",
    language: str = "en",
) -> str:
    """Generate a detailed brief for one article using the fast LLM.

    Uses an in-memory cache to avoid repeated LLM calls for the same article.
    Falls back to existing summary/why_it_matters if LLM is slow or fails.
    """
    # Cache key based on title (same article = same brief)
    cache_key = hashlib.md5(title.encode("utf-8", errors="ignore")).hexdigest()[:16]

    if cache_key in _brief_cache:
        logger.debug(f"Brief cache hit: {title[:40]}")
        return _brief_cache[cache_key]

    # If we already have a good summary + why_it_matters, use them directly
    # instead of waiting for the LLM (speed optimization for mobile)
    has_good_content = (
        summary
        and len(summary) > 60
        and "Reported by" not in summary
        and why_it_matters
        and "Stay informed" not in why_it_matters
    )

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

    try:
        # 30-second timeout — allows the fallback chain to cascade
        # through multiple providers (8-25s per-provider timeout each)
        response = await asyncio.wait_for(
            invoke_llm(system_msg, human_msg, fast=True),
            timeout=30.0,
        )
        cleaned = (response or "").strip()
    except asyncio.TimeoutError:
        logger.warning(f"Brief LLM timed out for: {title[:40]}")
        cleaned = ""
    except Exception as e:
        logger.error(f"Brief LLM error: {e}")
        cleaned = ""

    if not cleaned:
        fallback = summary or why_it_matters or "No additional details available yet."
        _brief_cache[cache_key] = fallback
        return fallback

    sanitized = sanitize_llm_response(cleaned)
    if not sanitized:
        fallback = summary or why_it_matters or "No additional details available yet."
        _brief_cache[cache_key] = fallback
        return fallback

    result = sanitized[:1200]

    # Store in cache (evict oldest if full)
    if len(_brief_cache) >= _BRIEF_CACHE_MAX:
        oldest = next(iter(_brief_cache))
        del _brief_cache[oldest]
    _brief_cache[cache_key] = result

    return result
