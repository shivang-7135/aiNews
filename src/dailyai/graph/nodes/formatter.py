"""
Node: Formatter
Final output formatting — converts internal article dicts to UI-ready feed format.
"""

import logging
import time

from dailyai.config import UI_TOPIC_MAP

logger = logging.getLogger("dailyai.graph.formatter")


def _normalize_ui_topic(topic: str) -> str:
    """Strip decorative emoji prefix so formatter output stays test-stable."""
    value = str(topic or "Top Stories")
    return value.split(" ", 1)[-1] if value and not value[0].isalnum() else value


async def run(state: dict) -> dict:
    """Formatter node: Format articles for the UI.

    Reads: final_feed, country_code, language
    Writes: final_feed (overwritten with formatted version), node_timings
    """
    start = time.time()
    articles = state.get("final_feed", [])
    country = state.get("country_code", "GLOBAL")
    language = state.get("language", "en")

    formatted: list[dict] = []

    for i, article in enumerate(articles):
        internal_topic = (article.get("topic") or article.get("category") or "general").lower()
        ui_topic = _normalize_ui_topic(UI_TOPIC_MAP.get(internal_topic, "Top Stories"))

        formatted.append(
            {
                "id": f"{country}-{language}-{i}",
                "headline": article.get("title", ""),
                "summary": article.get("summary", ""),
                "why_it_matters": article.get("why_it_matters", ""),
                "importance": max(1, min(int(article.get("importance", 5)), 10)),
                "category": str(article.get("category", "general")).lower(),
                "topic": ui_topic,
                "source_name": article.get("source", "Unknown"),
                "source_trust": article.get("source_trust", "low"),
                "sentiment": article.get("sentiment", "neutral"),
                "story_thread": article.get("story_thread", ""),
                "thread_count": article.get("thread_count", 0),
                "article_url": article.get("link", "#"),
                "published_at": article.get("published", ""),
                "updated_at": article.get("fetched_at", ""),
            }
        )

    elapsed = time.time() - start
    timings = state.get("node_timings", {})
    timings["formatter"] = round(elapsed, 4)

    logger.info(f"[Formatter] Formatted {len(formatted)} articles for UI")

    return {
        "final_feed": formatted,
        "node_timings": timings,
    }
