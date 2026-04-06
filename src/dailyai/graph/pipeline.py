"""
DailyAI — LangGraph News Pipeline
Compiles all nodes into a single invocable graph.

Usage:
    pipeline = build_pipeline()
    result = await pipeline.ainvoke({
        "country_code": "US",
        "country_name": "United States",
        "language": "en",
    })
    feed = result["final_feed"]
"""

import logging

from langgraph.graph import END, StateGraph

from dailyai.graph.nodes import (
    collector,
    curator,
    deduplicator,
    formatter,
    personalizer,
    sentiment,
    threader,
    trust,
)
from dailyai.graph.state import PipelineState

logger = logging.getLogger("dailyai.graph.pipeline")

# Module-level compiled graph (singleton)
_pipeline = None


def build_pipeline() -> StateGraph:
    """Build and compile the LangGraph news pipeline.

    Pipeline flow:
        collect → deduplicate → curate → score_trust →
        tag_sentiment → thread_stories → personalize → format → END
    """
    graph = StateGraph(PipelineState)

    # Register nodes
    graph.add_node("collect", collector.run)
    graph.add_node("deduplicate", deduplicator.run)
    graph.add_node("curate", curator.run)
    graph.add_node("score_trust", trust.run)
    graph.add_node("tag_sentiment", sentiment.run)
    graph.add_node("thread_stories", threader.run)
    graph.add_node("personalize", personalizer.run)
    graph.add_node("format", formatter.run)

    # Define edges (linear pipeline)
    graph.set_entry_point("collect")
    graph.add_edge("collect", "deduplicate")
    graph.add_edge("deduplicate", "curate")
    graph.add_edge("curate", "score_trust")
    graph.add_edge("score_trust", "tag_sentiment")
    graph.add_edge("tag_sentiment", "thread_stories")
    graph.add_edge("thread_stories", "personalize")
    graph.add_edge("personalize", "format")
    graph.add_edge("format", END)

    compiled = graph.compile()
    logger.info("[Pipeline] LangGraph news pipeline compiled successfully")
    return compiled


def get_pipeline():
    """Get or create the singleton pipeline instance."""
    global _pipeline
    if _pipeline is None:
        _pipeline = build_pipeline()
    return _pipeline


async def run_pipeline(
    country_code: str = "GLOBAL",
    country_name: str = "Global / Worldwide",
    language: str = "en",
    user_profile: dict | None = None,
) -> list[dict]:
    """Run the full news pipeline and return the final feed.

    Args:
        country_code: ISO country code or "GLOBAL"
        country_name: Human-readable country name
        language: Output language code
        user_profile: Optional user profile for personalization

    Returns:
        List of formatted article dicts ready for the UI
    """
    pipeline = get_pipeline()

    initial_state = {
        "country_code": country_code,
        "country_name": country_name,
        "language": language,
        "raw_articles": [],
        "deduplicated": [],
        "curated": [],
        "trust_scored": [],
        "sentiment_tagged": [],
        "threaded": [],
        "user_sync_code": user_profile.get("sync_code", "") if user_profile else "",
        "user_profile": user_profile,
        "final_feed": [],
        "errors": [],
        "node_timings": {},
    }

    result = await pipeline.ainvoke(initial_state)

    # Log pipeline performance
    timings = result.get("node_timings", {})
    total = sum(timings.values())
    timing_str = " → ".join(f"{k}:{v:.1f}s" for k, v in timings.items())
    logger.info(f"[Pipeline] Completed in {total:.1f}s | {timing_str}")

    errors = result.get("errors", [])
    if errors:
        logger.warning(f"[Pipeline] Errors: {errors}")

    return result.get("final_feed", [])
