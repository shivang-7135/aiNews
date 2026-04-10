"""
DailyAI — Analytics Service
Processes behavioral events into personalization signals.
Uses weighted scoring to rank topics by user interest.
"""

import logging

from dailyai.storage import backend as db

logger = logging.getLogger("dailyai.services.analytics")

# ── Event weights for topic scoring ─────────────────────────────────
EVENT_WEIGHTS: dict[str, float] = {
    "impression": 0.1,
    "click": 1.0,
    "hold": 1.5,
    "detail_open": 2.0,
    "read_time": 3.0,       # value = seconds; weight applied if >= 15s
    "scroll_depth": 2.5,    # value = percentage; weight applied if >= 70%
    "share": 4.0,
    "save": 5.0,
    "unsave": -2.0,
    "external_click": 3.0,
    "skip": -0.5,
}

# Minimum thresholds for time/scroll events to count
READ_TIME_THRESHOLD_SECONDS = 15
SCROLL_DEPTH_THRESHOLD_PCT = 70


async def record_events(
    session_id: str,
    sync_code: str,
    events: list[dict],
) -> int:
    """Record a batch of analytics events and update topic scores.

    Args:
        session_id: Browser session identifier
        sync_code: User sync code for cross-device personalization
        events: List of event dicts with event_type, article_id, topic, category, value, metadata

    Returns:
        Number of events recorded
    """
    if not events:
        return 0

    # Enrich events with session/sync info
    enriched = []
    for e in events:
        enriched.append({
            "session_id": session_id,
            "sync_code": sync_code,
            "event_type": e.get("event_type", ""),
            "article_id": e.get("article_id", ""),
            "topic": e.get("topic", ""),
            "category": e.get("category", ""),
            "value": float(e.get("value", 0)),
            "metadata": e.get("metadata", {}),
        })

    await db.save_events(enriched)

    # Recompute topic scores after new events
    try:
        await _recompute_scores(session_id, sync_code)
    except Exception as e:
        logger.error(f"Score recomputation failed: {e}")

    return len(enriched)


async def _recompute_scores(session_id: str, sync_code: str) -> None:
    """Recompute topic scores from all events for this session."""
    # Get recent events (last 1000)
    if sync_code:
        events = await db.get_events_by_sync_code(sync_code, limit=1000)
    else:
        events = await db.get_events(session_id, limit=1000)

    scores: dict[str, float] = {}
    event_counts: dict[str, int] = {}

    for e in events:
        topic = e.get("topic", "")
        if not topic:
            continue

        event_type = e.get("event_type", "")
        value = float(e.get("value", 0))
        weight = EVENT_WEIGHTS.get(event_type, 0)

        # Apply threshold filters for time/scroll events
        if event_type == "read_time" and value < READ_TIME_THRESHOLD_SECONDS:
            weight = weight * 0.2  # Partial credit for short reads
        elif event_type == "scroll_depth" and value < SCROLL_DEPTH_THRESHOLD_PCT:
            weight = weight * 0.3  # Partial credit for shallow scrolls

        if weight != 0:
            scores[topic] = scores.get(topic, 0) + weight
            event_counts[topic] = event_counts.get(topic, 0) + 1

    if scores:
        await db.save_topic_scores(session_id, sync_code, scores, event_counts)


async def get_personalized_scores(
    session_id: str = "",
    sync_code: str = "",
) -> dict[str, float]:
    """Get topic preference scores for personalized ranking.

    Prefers sync_code (cross-device) over session_id (single browser).
    """
    if sync_code:
        scores = await db.get_topic_scores_by_sync_code(sync_code)
        if scores:
            return scores

    if session_id:
        return await db.get_topic_scores(session_id)

    return {}


def rank_articles_by_scores(
    articles: list[dict],
    scores: dict[str, float],
) -> list[dict]:
    """Re-rank articles using personalization scores.

    Keeps top 5 articles in their original order (editorial picks),
    then re-ranks the rest by user's topic preferences + importance.
    """
    if not scores or len(articles) <= 5:
        return articles

    # Keep top 5 untouched (editorial/breaking news)
    top = articles[:5]
    rest = articles[5:]

    def rank_score(article: dict) -> float:
        topic = article.get("topic", "")
        category = article.get("category", "")
        # Check both the UI topic label and the internal category
        topic_score = scores.get(topic, 0) + scores.get(category, 0)
        importance = float(article.get("importance", 5))
        return topic_score * 2.0 + importance

    rest.sort(key=rank_score, reverse=True)
    return top + rest


async def get_analytics_summary() -> dict:
    """Get analytics summary for admin dashboard."""
    event_counts = await db.get_event_counts()
    total_events = sum(event_counts.values())

    return {
        "total_events": total_events,
        "event_breakdown": event_counts,
    }
