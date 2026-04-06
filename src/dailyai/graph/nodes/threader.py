"""
Node: Story Threader
Groups related articles by story_thread labels and computes thread counts.
"""

import logging
import time

logger = logging.getLogger("dailyai.graph.threader")


async def run(state: dict) -> dict:
    """Threader node: Compute story thread counts.

    Reads: sentiment_tagged
    Writes: threaded, node_timings
    """
    start = time.time()
    articles = state.get("sentiment_tagged", [])

    # Count articles per thread
    thread_counts: dict[str, int] = {}
    for article in articles:
        thread = str(article.get("story_thread", "")).strip().lower()
        if thread:
            thread_counts[thread] = thread_counts.get(thread, 0) + 1

    # Annotate each article with its thread count
    for article in articles:
        thread = str(article.get("story_thread", "")).strip().lower()
        article["thread_count"] = thread_counts.get(thread, 0) if thread else 0

    elapsed = time.time() - start
    timings = state.get("node_timings", {})
    timings["threader"] = round(elapsed, 4)

    thread_groups = len([k for k, v in thread_counts.items() if v > 1])
    logger.info(f"[Threader] {thread_groups} multi-article threads found")

    return {
        "threaded": articles,
        "node_timings": timings,
    }
