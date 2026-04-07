"""
Node: Sentiment Tagger
Validates and normalizes sentiment values from LLM output.
Future: can be enhanced with a dedicated sentiment model.
"""

import logging
import time

logger = logging.getLogger("dailyai.graph.sentiment")

VALID_SENTIMENTS = {"bullish", "bearish", "neutral"}


async def run(state: dict) -> dict:
    """Sentiment node: Validate and normalize sentiment tags.

    Reads: trust_scored
    Writes: sentiment_tagged, node_timings
    """
    start = time.time()
    articles = state.get("trust_scored", [])

    for article in articles:
        sentiment = str(article.get("sentiment", "neutral")).lower().strip()
        if sentiment not in VALID_SENTIMENTS:
            sentiment = "neutral"
        article["sentiment"] = sentiment

    elapsed = time.time() - start
    timings = state.get("node_timings", {})
    timings["sentiment"] = round(elapsed, 4)

    logger.info(f"[Sentiment] Tagged {len(articles)} articles")

    return {
        "sentiment_tagged": articles,
        "node_timings": timings,
    }
