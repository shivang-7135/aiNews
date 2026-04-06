"""
Node: Trust Scorer
Assigns source trust tiers based on curated source registry.
"""

import logging
import time

from dailyai.config import HIGH_TRUST_SOURCES, MEDIUM_TRUST_SOURCES

logger = logging.getLogger("dailyai.graph.trust")


def _score_source(source: str) -> tuple[str, int]:
    """Score a source and return (tier, numeric_score)."""
    src = (source or "").strip().lower()
    if not src:
        return "low", 0
    if any(trusted in src for trusted in HIGH_TRUST_SOURCES):
        return "high", 2
    if any(med in src for med in MEDIUM_TRUST_SOURCES):
        return "medium", 1
    if any(kw in src for kw in ("news", "times", "post", "journal")):
        return "medium", 1
    return "low", 0


async def run(state: dict) -> dict:
    """Trust scorer node: Assign source trust tiers.

    Reads: curated
    Writes: trust_scored, node_timings
    """
    start = time.time()
    articles = state.get("curated", [])

    for article in articles:
        tier, score = _score_source(article.get("source", ""))
        article["source_trust"] = tier
        article["_trust_score"] = score  # Internal, used for ranking

    elapsed = time.time() - start
    timings = state.get("node_timings", {})
    timings["trust"] = round(elapsed, 4)

    logger.info(f"[Trust] Scored {len(articles)} articles")

    return {
        "trust_scored": articles,
        "node_timings": timings,
    }
