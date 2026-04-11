"""
Node: Curator
Uses LLM to filter, rank, and summarize articles into structured tiles.
This is the brain of the pipeline — the most important node.
"""

import json
import logging
import re
import time
from datetime import UTC, datetime

from dailyai.config import LLM_TIMEOUT_SECONDS, MAX_TILES_PER_FETCH, SUPPORTED_LANGUAGES
from dailyai.llm.prompts import CURATION_PROMPT, sanitize_llm_response
from dailyai.llm.provider import get_llm

logger = logging.getLogger("dailyai.graph.curator")

# Template values the LLM may echo from the prompt
_TEMPLATE_VALUES = {
    "short headline",
    "source name",
    "url",
    "iso date",
    "category_name",
    "topic_tag",
    "1-2 sentence summary",
    "one punchy sentence",
}


def _is_template(tile: dict) -> bool:
    """Return True if a tile contains placeholder text from the prompt."""
    for field in ("title", "source", "link", "published"):
        val = str(tile.get(field, "")).strip().lower()
        if val in _TEMPLATE_VALUES:
            return True
    title_lower = str(tile.get("title", "")).strip().lower()
    return title_lower.startswith("short headline") or title_lower == ""


def _extract_json_array(response: str) -> list[dict] | None:
    """Extract a JSON array from an LLM response, handling various formats."""
    if not response:
        return None

    # Method 1: Strip markdown code fences
    cleaned = response.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```\s*$", "", cleaned)
        cleaned = cleaned.strip()

    # Method 2: Direct parse
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, list):
            return parsed
    except json.JSONDecodeError:
        pass

    # Method 3: Bracket matching
    start_idx = response.find("[")
    if start_idx != -1:
        depth = 0
        for i in range(start_idx, len(response)):
            if response[i] == "[":
                depth += 1
            elif response[i] == "]":
                depth -= 1
                if depth == 0:
                    candidate = response[start_idx : i + 1]
                    try:
                        parsed = json.loads(candidate)
                        if isinstance(parsed, list):
                            return parsed
                    except json.JSONDecodeError:
                        pass
                    break

        # Method 4: Truncated JSON recovery
        partial = response[start_idx:]
        last_complete = partial.rfind("},")
        if last_complete == -1:
            last_complete = partial.rfind("}")
        if last_complete != -1:
            candidate = partial[: last_complete + 1].rstrip(",") + "]"
            try:
                parsed = json.loads(candidate)
                if isinstance(parsed, list) and len(parsed) > 0:
                    logger.info(f"[Curator] Recovered {len(parsed)} items from truncated JSON")
                    return parsed
            except json.JSONDecodeError:
                pass

    return None


async def run(state: dict) -> dict:
    """Curator node: Use LLM to filter and summarize articles.

    Reads: deduplicated, country_name, language
    Writes: curated, errors, node_timings
    """
    start = time.time()
    articles = state.get("deduplicated", [])
    country_name = state.get("country_name", "Global")
    language = state.get("language", "en")
    output_language = SUPPORTED_LANGUAGES.get(language, "English")
    errors = state.get("errors", [])

    if not articles:
        logger.warning("[Curator] No articles to curate")
        timings = state.get("node_timings", {})
        timings["curator"] = 0.0
        return {"curated": [], "errors": errors, "node_timings": timings}

    # Keep curator prompts compact to reduce timeout/rate-limit pressure.
    capped = articles[:30]
    articles_text = "\n".join(
        f"- [{i + 1}] {a['title']} (Source: {a.get('source', 'Unknown')}, Link: {a.get('link', '')})"
        for i, a in enumerate(capped)
    )

    # Format the prompt
    prompt = CURATION_PROMPT.format_messages(
        country_name=country_name,
        output_language=output_language,
        articles_text=articles_text,
    )

    # Call LLM with a strict timeout (prevents SDK infinite retries on rate limits)
    try:
        import asyncio

        llm = get_llm()
        timeout_s = max(15.0, min(float(LLM_TIMEOUT_SECONDS), 35.0))
        response = await asyncio.wait_for(llm.ainvoke(prompt), timeout=timeout_s)
        response_text = response.content if hasattr(response, "content") else str(response)
    except TimeoutError:
        logger.info("[Curator] LLM call timed out; using deterministic fallback")
        errors.append("Curator: LLM timeout")
        timings = state.get("node_timings", {})
        timings["curator"] = round(time.time() - start, 2)
        return {
            "curated": _fallback_curate(articles, language),
            "errors": errors,
            "node_timings": timings,
        }
    except Exception as e:
        error_text = str(e).lower()
        if (
            "timed out" in error_text
            or "timeout" in error_text
            or "429" in error_text
            or "rate limit" in error_text
        ):
            logger.info(f"[Curator] Provider timeout/rate-limit; using fallback: {e}")
        else:
            logger.error(f"[Curator] LLM call failed: {e}")
            errors.append(f"Curator LLM failed: {e}")
        # Use fallback processing
        timings = state.get("node_timings", {})
        timings["curator"] = round(time.time() - start, 2)
        return {
            "curated": _fallback_curate(articles, language),
            "errors": errors,
            "node_timings": timings,
        }

    # Parse response
    tiles_raw = _extract_json_array(response_text)
    if tiles_raw is None:
        logger.warning("[Curator] Could not parse LLM response as JSON")
        errors.append("Curator: JSON parse failed")
        timings = state.get("node_timings", {})
        timings["curator"] = round(time.time() - start, 2)
        return {
            "curated": _fallback_curate(articles, language),
            "errors": errors,
            "node_timings": timings,
        }

    # Validate and clean tiles
    clean_tiles: list[dict] = []
    seen_titles: set[str] = set()

    for t in tiles_raw:
        if not isinstance(t, dict) or "title" not in t:
            continue
        if _is_template(t):
            continue

        normalized = re.sub(r"\W+", " ", str(t.get("title", "")).lower()).strip()
        if normalized in seen_titles:
            continue
        seen_titles.add(normalized)

        # Parse importance
        try:
            importance = int(t.get("importance", 5))
        except (TypeError, ValueError):
            importance = 5

        # Sanitize text fields
        raw_summary = str(t.get("summary", ""))[:300]
        raw_why = str(t.get("why_it_matters", ""))[:200]
        summary_clean = sanitize_llm_response(raw_summary) or ""
        why_clean = sanitize_llm_response(raw_why) or ""

        # Validate sentiment
        sentiment = str(t.get("sentiment", "neutral")).lower().strip()
        if sentiment not in ("bullish", "bearish", "neutral"):
            sentiment = "neutral"

        clean_tiles.append(
            {
                "title": str(t.get("title", ""))[:150],
                "summary": summary_clean or "Tap to read the full story.",
                "why_it_matters": why_clean,
                "category": str(t.get("category", "general")).lower(),
                "topic": str(t.get("topic", "general")).lower(),
                "importance": min(max(importance, 1), 10),
                "source": str(t.get("source", "")),
                "sentiment": sentiment,
                "story_thread": str(t.get("story_thread", "")).strip()[:60],
                "link": str(t.get("link", "")),
                "published": str(t.get("published", "")),
                "fetched_at": datetime.now(UTC).isoformat(),
            }
        )

    # Sort by importance
    clean_tiles.sort(key=lambda x: x.get("importance", 0), reverse=True)
    clean_tiles = clean_tiles[:MAX_TILES_PER_FETCH]

    elapsed = time.time() - start
    timings = state.get("node_timings", {})
    timings["curator"] = round(elapsed, 2)

    logger.info(f"[Curator] Produced {len(clean_tiles)} curated tiles in {elapsed:.1f}s")

    return {
        "curated": clean_tiles,
        "errors": errors,
        "node_timings": timings,
    }


def _fallback_curate(articles: list[dict], language: str = "en") -> list[dict]:
    """Smart fallback when LLM fails — keyword-based topic assignment."""
    KEYWORD_TOPICS = {
        "openai": ("big_tech", "industry"),
        "google": ("big_tech", "industry"),
        "meta ": ("big_tech", "industry"),
        "anthropic": ("big_tech", "industry"),
        "mistral": ("big_tech", "industry"),
        "deepmind": ("big_tech", "research"),
        "llm": ("llms", "product"),
        "gpt": ("llms", "product"),
        "chatgpt": ("llms", "product"),
        "gemini": ("llms", "product"),
        "claude": ("llms", "product"),
        "robot": ("robotics", "product"),
        "regulat": ("regulation", "regulation"),
        "safety": ("ai_safety", "regulation"),
        "funding": ("funding", "funding"),
        "startup": ("startups", "funding"),
        "open source": ("open_source", "product"),
        "research": ("research", "research"),
    }

    fallback_why = {
        "en": "Stay informed — this story is trending in the AI community right now.",
        "de": "Bleiben Sie informiert — diese Story ist gerade in der KI-Community im Trend.",
        "hi": "जानकारी में रहें — यह स्टोरी अभी AI समुदाय में तेजी से ट्रेंड कर रही है.",
    }

    tiles: list[dict] = []
    lang = language if language in fallback_why else "en"

    for i, a in enumerate(articles[:30]):
        title_lower = a.get("title", "").lower()
        topic, category = "general", "general"
        importance = max(8 - i, 2)  # Top articles get 8, then 7, 6, 5... down to 2

        for kw, (t, c) in KEYWORD_TOPICS.items():
            if kw in title_lower:
                topic, category = t, c
                break

        source = a.get("source", "")
        raw_feed_summary = str(a.get("summary", "")).strip()[:500]
        # Clean HTML completely for the fallback summary
        import re as regex

        raw_feed_summary = regex.sub(r"<[^>]+>", "", raw_feed_summary).strip()

        summary = (
            raw_feed_summary
            if raw_feed_summary and len(raw_feed_summary) > 20
            else (
                f"Reported by {source}. Tap to read the full story."
                if source
                else "Tap to read the full story."
            )
        )

        tiles.append(
            {
                "title": a.get("title", "")[:150],
                "summary": summary,
                "why_it_matters": fallback_why.get(lang, fallback_why["en"]),
                "category": category,
                "topic": topic,
                "importance": importance,
                "source": source,
                "sentiment": "neutral",
                "story_thread": "",
                "link": a.get("link", ""),
                "published": a.get("published", ""),
                "fetched_at": datetime.now(UTC).isoformat(),
            }
        )

    return tiles
