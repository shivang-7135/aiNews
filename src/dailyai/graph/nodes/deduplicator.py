"""
Node: Deduplicator
Removes duplicate and near-duplicate articles by normalized title.
"""

import logging
import re
import time

logger = logging.getLogger("dailyai.graph.deduplicator")


def _normalize_title(title: str) -> str:
    """Normalize a headline for dedup comparison."""
    normalized = title.lower().strip()
    # Remove common headline suffixes like "- Reuters"
    normalized = re.sub(
        r"\s*[-|:|]\s*(reuters|associated press|ap news|techcrunch|the verge|"
        r"wired|forbes|bloomberg|bbc|cnn|cnbc).*$",
        "",
        normalized,
    )
    normalized = re.sub(r"[^a-z0-9\s]", "", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


async def run(state: dict) -> dict:
    """Deduplicator node: Remove duplicate articles.

    Reads: raw_articles
    Writes: deduplicated, node_timings
    """
    start = time.time()
    raw = state.get("raw_articles", [])

    seen: set[str] = set()
    unique: list[dict] = []

    for article in raw:
        key = _normalize_title(article.get("title", ""))
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(article)

    elapsed = time.time() - start
    timings = state.get("node_timings", {})
    timings["deduplicator"] = round(elapsed, 4)

    removed = len(raw) - len(unique)
    logger.info(
        f"[Deduplicator] {len(raw)} → {len(unique)} articles ({removed} duplicates removed)"
    )

    return {
        "deduplicated": unique,
        "node_timings": timings,
    }
