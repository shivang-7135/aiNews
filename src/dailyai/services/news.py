"""
DailyAI — News Service
Core news management: refresh, retrieve, and format feeds.
Bridges the LangGraph pipeline with the storage and UI layers.
"""

import asyncio
import hashlib
import logging
import time
from asyncio import get_event_loop
from datetime import UTC, datetime

from deep_translator import GoogleTranslator

from dailyai.config import (
    COUNTRIES,
    LANG_MAP,
    MAX_FEED_SIZE,
    MIN_FEED_SIZE,
    REFRESH_COOLDOWN_SECONDS,
    STARTUP_PREFETCH_CONCURRENCY,
    STARTUP_PREFETCH_GLOBAL_LIMIT,
    STARTUP_PREFETCH_OTHER_LIMIT,
    STARTUP_PREFETCH_TIMEOUT,
    SUPPORTED_LANGUAGES,
    UI_FEED_TOPICS,
    normalize_language,
    store_key,
)
from dailyai.graph.pipeline import run_pipeline
from dailyai.llm.prompts import BRIEF_HUMAN, BRIEF_SYSTEM, sanitize_llm_response
from dailyai.storage import backend as db

logger = logging.getLogger("dailyai.services.news")

# Refresh throttling
_last_refresh: dict[str, float] = {}
_refresh_locks: dict[str, asyncio.Lock] = {}
_startup_prefetch_lock = asyncio.Lock()
_startup_prefetch_done = False
_brief_cache: dict[str, str] = {}


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

    # Strip emoji prefix for matching (e.g. "🤖 AI Models" -> "AI Models")
    stripped_request = requested_topic.split(" ", 1)[-1] if requested_topic and requested_topic[0] not in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' else requested_topic
    stripped_ui = ui_topic.split(" ", 1)[-1] if ui_topic and ui_topic[0] not in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' else ui_topic
    if stripped_ui == stripped_request:
        return True

    # Match by core name
    if stripped_request == "AI Models":
        return internal_topic == "llms" or category in {"product", "breakthrough"}
    if stripped_request == "Business":
        return category in {"industry", "funding"} or internal_topic in {"startups", "funding", "big_tech"}
    if stripped_request == "Research":
        return internal_topic in {"research", "robotics", "healthcare", "autonomous"} or category in {"research", "breakthrough"}
    if stripped_request == "Tools":
        return internal_topic in {"open_source", "product"} or category == "product"
    if stripped_request == "Regulation":
        return internal_topic in {"regulation", "ai_safety"} or category == "regulation"
    if stripped_request == "Funding":
        return internal_topic in {"funding", "startups"} or category == "funding"
    return stripped_request == "Top Stories"


def _topic_keyword_score(requested_topic: str, article: dict) -> int:
    text = f"{article.get('headline', '')} {article.get('summary', '')} {article.get('why_it_matters', '')}".lower()
    topic_keywords = {
        "AI Models": ("model", "llm", "gpt", "gemini", "claude", "llama", "mistral", "qwen"),
        "Business": ("funding", "revenue", "startup", "enterprise", "valuation", "acquisition", "market"),
        "Research": ("research", "study", "paper", "benchmark", "arxiv", "lab", "scientist"),
        "Tools": ("tool", "api", "sdk", "framework", "open source", "github", "agent"),
        "Regulation": ("regulation", "policy", "governance", "law", "compliance", "act", "safety"),
        "Funding": ("funding", "raised", "valuation", "seed", "series a", "series b", "investment"),
    }
    keywords = topic_keywords.get(requested_topic, ())
    return sum(1 for k in keywords if k in text)


def _build_topic_counts(all_formatted: list[dict]) -> list[dict]:
    """Build stable topic counts so all feed categories are always available in the UI."""
    counts: dict[str, int] = {topic: 0 for topic in UI_FEED_TOPICS if topic != "For You"}

    for article in all_formatted:
        ui_topic = str(article.get("topic", "🔥 Top Stories") or "🔥 Top Stories")
        if ui_topic not in counts:
            counts[ui_topic] = 0
        counts[ui_topic] += 1

    counts["For You"] = len(all_formatted)

    return [{"name": topic, "count": int(counts.get(topic, 0))} for topic in UI_FEED_TOPICS]


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
        
        concurrency = max(1, min(5, int(STARTUP_PREFETCH_CONCURRENCY)))
        sem = asyncio.Semaphore(concurrency)  # Avoid overwhelming LLM/API providers during startup.
        
        async def fetch_pair(i: int, country: str, language: str):
            target = STARTUP_PREFETCH_GLOBAL_LIMIT if country == "GLOBAL" else STARTUP_PREFETCH_OTHER_LIMIT
            async with sem:
                try:
                    logger.info(f"Prefetching [{i}/{len(pairs)}] {country}/{language} (target={target})...")
                    await asyncio.wait_for(
                        refresh_news(country, language, force=force, target_size=target),
                        timeout=STARTUP_PREFETCH_TIMEOUT,
                    )
                    logger.info(f"  ✅ Prefetch [{i}/{len(pairs)}] {country}/{language} complete")
                except TimeoutError:
                    logger.warning(f"  ⚠ Prefetch [{i}/{len(pairs)}] {country}/{language} timed out, skipping")
                except Exception as e:
                    logger.error(f"  ❌ Prefetch [{i}/{len(pairs)}] {country}/{language} failed: {e}")

        # Run all fetches concurrently
        tasks = [fetch_pair(i, country_code, lang) for i, (country_code, lang) in enumerate(pairs, 1)]
        await asyncio.gather(*tasks, return_exceptions=True)

        _startup_prefetch_done = True
        logger.info("Startup prefetch completed")


async def pregenerate_top_briefs(articles: list[dict], language: str) -> None:
    """Pre-generate and cache LLM briefs for top articles in the background."""
    logger.info(f"Starting background brief pre-generation for {len(articles)} articles ({language}).")
    
    # Throttle pre-generation to respect LLM API limits
    sem = asyncio.Semaphore(2)

    async def _cache_brief(article: dict):
        async with sem:
            try:
                # Check if it exists or use stream_article_brief generator
                # We can just iterate it but not yield
                async for _ in stream_article_brief(article, language=language):
                    pass
            except Exception as e:
                logger.debug(f"Pre-generation failed for '{article.get('title')}': {e}")
            await asyncio.sleep(1.0) # Small cooldown between briefs

    tasks = [_cache_brief(a) for a in articles]
    await asyncio.gather(*tasks, return_exceptions=True)
    logger.info(f"Finished background brief pre-generation ({language}).")


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

            # Pre-generate LLM briefs for top articles to avoid rate limits
            if merged:
                asyncio.create_task(pregenerate_top_briefs(merged[:15], language))

        except Exception as e:
            logger.error(f"Error refreshing {key}: {e}", exc_info=True)


async def _background_translate_and_cache(
    articles: list[dict], target_language: str, store_key_str: str
) -> None:
    """Translate English articles → target language in the background and
    persist the translated versions to the DB so future page loads are instant."""
    try:
        loop = get_event_loop()

        def _do_translate():
            try:
                t = GoogleTranslator(source='en', target=target_language)
                titles = [a.get("title", "") or "" for a in articles]
                summaries = [a.get("summary", "") or "" for a in articles]
                whys = [a.get("why_it_matters", "") or "" for a in articles]
                if any(titles):
                    t_titles = t.translate_batch(titles)
                    for a, trans in zip(articles, t_titles, strict=False):
                        if trans:
                            a["title"] = trans
                if any(summaries):
                    t_sums = t.translate_batch(summaries)
                    for a, trans in zip(articles, t_sums, strict=False):
                        if trans:
                            a["summary"] = trans
                if any(whys):
                    t_whys = t.translate_batch(whys)
                    for a, trans in zip(articles, t_whys, strict=False):
                        if trans:
                            a["why_it_matters"] = trans
            except Exception as e:
                logger.error(f"Background translation error: {e}")

        await asyncio.wait_for(
            loop.run_in_executor(None, _do_translate),
            timeout=30.0,
        )

        # Save translated articles back to DB so next load is instant
        existing = await db.get_articles(store_key_str)
        existing_titles = {a.get("title", "") for a in existing}
        merged = list(existing)
        for a in articles:
            if a.get("title", "") not in existing_titles:
                merged.append(a)
        await db.save_articles(store_key_str, merged)
        logger.info(
            f"Background translation complete: {len(articles)} articles → {target_language}, saved to {store_key_str}"
        )
    except TimeoutError:
        logger.warning(f"Background translation timed out for {target_language}")
    except Exception as e:
        logger.error(f"Background translation failed: {e}")


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

    # Frontend NEVER triggers pipeline — only reads from DB.
    # If cache is empty, the startup prefetch hasn't finished yet.
    articles = await db.get_articles(key)

    # Fallback chain if insufficient articles (try global, then english global)
    if len(articles) < MIN_FEED_SIZE:
        global_key = store_key("GLOBAL", language)
        if global_key != key:
            global_articles = await db.get_articles(global_key)
            existing_titles = {a.get("title", "") for a in articles}
            for a in global_articles:
                if a.get("title", "") not in existing_titles:
                    articles.append(a)
                if len(articles) >= MAX_FEED_SIZE:
                    break

    if len(articles) < MIN_FEED_SIZE and language != "en":
        en_key = store_key("GLOBAL", "en")
        en_articles = await db.get_articles(en_key)
        existing_titles = {a.get("title", "") for a in articles}

        new_arts = []
        for a in en_articles:
            if a.get("title", "") not in existing_titles:
                new_arts.append(dict(a))
            if len(articles) + len(new_arts) >= MAX_FEED_SIZE:
                break

        # Return English articles immediately (non-blocking) and schedule
        # background translation that caches results for future page loads.
        # This avoids the 15-30s synchronous GoogleTranslator bottleneck.
        if new_arts:
            articles.extend(new_arts)
            asyncio.create_task(
                _background_translate_and_cache(new_arts, language, key)
            )

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

        ui_topic = UI_TOPIC_MAP.get(internal_topic, "🔥 Top Stories")

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
            "country": country,
            "language": language,
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

    # If a specific topic has no cached rows, try keyword scoring as fallback.
    # DO NOT trigger refresh_news here — that's the server's startup job.
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
    synthesis = ""
    custom_hooks = {}
    if sync_code:
        try:
            from dailyai.services.analytics import get_personalized_scores, rank_articles_by_scores
            scores = await get_personalized_scores(sync_code=sync_code)
            if scores:
                feed_articles = rank_articles_by_scores(feed_articles, scores)
                
            if topic == "For You":
                from dailyai.services.personalizer_llm import generate_daily_bespoke_digest
                digest = await generate_daily_bespoke_digest(sync_code, feed_articles)
                if digest:
                    synthesis = digest.get("synthesis", "")
                    custom_hooks = digest.get("custom_hooks", {})
                    # Inject custom hooks directly into the returned page
                    for _idx, a in enumerate(feed_articles):
                        aid = str(a.get("id"))
                        if custom_hooks and aid in custom_hooks:
                            a["why_it_matters"] = custom_hooks[aid]
        except Exception as e:
            logger.warning(f"Personalization failed: {e}")

    # Pagination
    total = len(feed_articles)
    has_more = offset + limit < total
    page = feed_articles[offset:offset + limit]
    topic_counts = _build_topic_counts(all_formatted)

    last_updated = await db.get_metadata(f"last_updated:{key}") or "-"

    return {
        "articles": page,
        "total": total,
        "offset": offset,
        "limit": limit,
        "has_more": has_more,
        "next_offset": (offset + len(page)) if has_more else None,
        "page_count": len(page),
        "visible_start": (offset + 1) if page else 0,
        "visible_end": offset + len(page),
        "country": country,
        "country_name": COUNTRIES.get(country, country),
        "language": language,
        "last_updated": last_updated,
        "categories": topic_counts,
        "synthesis": synthesis,
    }


async def stream_article_brief(article: dict, language: str = "en"):
    """
    Generate an article brief dynamically and yield text chunks in real-time.
    Caches the final output to SQLite metadata to avoid re-summarizing.
    """
    article_hash = hashlib.md5((article.get('source', '') + article.get('title', '')).encode()).hexdigest()
    cache_key = f"{article_hash}_{language}"

    from dailyai.llm.provider import SUMMARY_FALLBACK_MESSAGE, stream_llm

    # Return cached brief sequentially if it exists
    cached = await db.get_metadata(f"brief:{cache_key}")
    if cached:
        cached_text = str(cached).strip()
        if SUMMARY_FALLBACK_MESSAGE.lower() not in cached_text.lower():
            # Simulate quick streaming for the cached content
            chunk_size = max(5, len(cached_text) // 10)
            for i in range(0, len(cached_text), chunk_size):
                yield cached_text[i:i+chunk_size]
                await asyncio.sleep(0.01)
            return
        logger.info(f"Skipping stale fallback brief cache for key={cache_key}")

    language = normalize_language(language)
    output_language = SUPPORTED_LANGUAGES.get(language, "English")

    # Fallback structure logic...
    raw_summary = str(article.get("summary", "") or "").strip()
    headline = str(article.get("title", "") or "").strip()
    why = str(article.get("why_it_matters", "") or "").strip()
    source = str(article.get("source", "") or "").strip()
    topic = str(article.get("topic", "general") or "general").strip()
    link = str(article.get("link", "") or "").strip()

    system_msg = BRIEF_SYSTEM.format(output_language=output_language)
    human_msg = BRIEF_HUMAN.format(
        title=headline or "Untitled",
        source=source or "Unknown",
        topic=topic,
        link=link,
        summary=raw_summary or "Not available",
        why_it_matters=why or "Not available",
    )

    full_output = ""
    try:
        async for chunk in stream_llm(system_msg, human_msg):
            full_output += chunk
            yield chunk
            
        # Background cache the finalized response
        if full_output:
            try:
                cleaned_output = sanitize_llm_response(full_output).strip()
                if SUMMARY_FALLBACK_MESSAGE.lower() in cleaned_output.lower():
                    logger.info(f"Not caching fallback brief for key={cache_key}")
                    return
                # Store in SQLite key-value metadata store
                await db.set_metadata(f"brief:{cache_key}", cleaned_output)
            except Exception as e:
                logger.error(f"Failed to cache generated brief: {e}")

    except Exception as e:
        logger.error(f"Streaming brief failed: {e}", exc_info=True)
        yield SUMMARY_FALLBACK_MESSAGE


async def get_article_brief(
    title: str,
    source: str = "",
    summary: str = "",
    why_it_matters: str = "",
    topic: str = "general",
    link: str = "",
    language: str = "en",
) -> str:
    """Compatibility helper returning a single brief string with in-memory caching."""
    cache_key = hashlib.md5(str(title or "").encode("utf-8")).hexdigest()[:16]
    cached = _brief_cache.get(cache_key)
    if cached:
        return cached

    article = {
        "title": title,
        "source": source,
        "summary": summary,
        "why_it_matters": why_it_matters,
        "topic": topic,
        "link": link,
    }
    chunks: list[str] = []
    async for chunk in stream_article_brief(article, language=language):
        chunks.append(chunk)

    brief = "".join(chunks).strip()
    if brief:
        _brief_cache[cache_key] = brief
    return brief
