"""
DailyAI — Analytics Service
Processes behavioral events into personalization signals.
Uses weighted scoring to rank topics by user interest.

Tracks per-session granular metrics: clicks, read time, saves,
scroll depth, impressions, and more. Aggregated scores drive
the personalized feed ranking.
"""

import logging
from datetime import UTC, datetime

from dailyai.storage import backend as db

logger = logging.getLogger("dailyai.services.analytics")

# ── Event weights for topic scoring ─────────────────────────────────
EVENT_WEIGHTS: dict[str, float] = {
    "impression": 0.1,
    "click": 1.0,
    "hold": 1.5,
    "detail_open": 2.0,
    "read_time": 3.0,  # value = seconds; weight applied if >= 15s
    "scroll_depth": 2.5,  # value = percentage; weight applied if >= 70%
    "share": 4.0,
    "save": 5.0,
    "unsave": -2.0,
    "external_click": 3.0,
    "skip": -0.5,
}

# Minimum thresholds for time/scroll events to count
READ_TIME_THRESHOLD_SECONDS = 15
SCROLL_DEPTH_THRESHOLD_PCT = 70

# Read-time brackets for graduated scoring
READ_TIME_BRACKETS = [
    (60, 5.0),   # 60s+ = very engaged
    (30, 3.0),   # 30-60s = engaged
    (15, 2.0),   # 15-30s = interested
    (5, 0.5),    # 5-15s = glanced
    (0, 0.1),    # <5s = barely looked
]


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

    # Enrich events with session/sync info and timestamp
    enriched = []
    for e in events:
        enriched.append(
            {
                "session_id": session_id,
                "sync_code": sync_code,
                "event_type": e.get("event_type", ""),
                "article_id": e.get("article_id", ""),
                "topic": e.get("topic", ""),
                "category": e.get("category", ""),
                "value": float(e.get("value", 0)),
                "metadata": e.get("metadata", {}),
            }
        )

    await db.save_events(enriched)

    # Recompute topic scores after new events
    try:
        await _recompute_scores(session_id, sync_code)
    except Exception as e:
        logger.error(f"Score recomputation failed: {e}")

    # Aggregate into compact session stats (lightweight alternative to raw events)
    try:
        await _aggregate_session_stats(session_id, sync_code)
    except Exception as e:
        logger.error(f"Session stats aggregation failed: {e}")

    # Update per-session summary stats in profile (if sync_code present)
    if sync_code:
        try:
            await _update_profile_analytics(sync_code, enriched)
        except Exception as e:
            logger.error(f"Profile analytics update failed: {e}")

    # Auto-prune old raw events every ~100 batches (probabilistic to avoid overhead)
    import random
    if random.random() < 0.01:  # ~1% chance per batch
        try:
            pruned = await db.prune_old_events(days=7)
            if pruned > 0:
                logger.info(f"Auto-pruned {pruned} old raw events")
        except Exception as e:
            logger.error(f"Event auto-prune failed: {e}")

    return len(enriched)


async def _aggregate_session_stats(session_id: str, sync_code: str) -> None:
    """Aggregate raw events into compact session stats row."""
    events = await db.get_events(session_id, limit=2000)
    if not events:
        return

    stats = {
        "session_id": session_id,
        "sync_code": sync_code,
        "impressions": 0,
        "clicks": 0,
        "detail_opens": 0,
        "saves": 0,
        "unsaves": 0,
        "shares": 0,
        "external_clicks": 0,
        "holds": 0,
        "total_read_time_sec": 0.0,
        "total_scroll_depth": 0.0,
        "read_events": 0,
        "scroll_events": 0,
    }

    topic_counts: dict[str, int] = {}

    for e in events:
        et = e.get("event_type", "")
        val = float(e.get("value", 0))
        topic = e.get("topic", "")

        if et == "impression":
            stats["impressions"] += 1
        elif et == "click":
            stats["clicks"] += 1
        elif et == "detail_open":
            stats["detail_opens"] += 1
        elif et == "save":
            stats["saves"] += 1
        elif et == "unsave":
            stats["unsaves"] += 1
        elif et == "share":
            stats["shares"] += 1
        elif et == "external_click":
            stats["external_clicks"] += 1
        elif et == "hold":
            stats["holds"] += 1
        elif et == "read_time":
            stats["total_read_time_sec"] += val
            stats["read_events"] += 1
        elif et == "scroll_depth":
            stats["total_scroll_depth"] += val
            stats["scroll_events"] += 1

        if topic:
            topic_counts[topic] = topic_counts.get(topic, 0) + 1

    # Compute averages
    if stats["read_events"] > 0:
        stats["avg_read_time_sec"] = round(stats["total_read_time_sec"] / stats["read_events"], 1)
    if stats["scroll_events"] > 0:
        stats["avg_scroll_depth"] = round(stats["total_scroll_depth"] / stats["scroll_events"], 1)

    # Top 5 topics
    sorted_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    stats["top_topics"] = dict(sorted_topics)

    await db.save_session_stats(stats)


async def _update_profile_analytics(sync_code: str, events: list[dict]) -> None:
    """Update the profile's aggregated analytics counters from new events."""
    profile = await db.get_profile(sync_code)
    if not profile:
        return

    analytics = profile.get("analytics", {})

    # Count events by type
    for e in events:
        event_type = e.get("event_type", "")
        value = float(e.get("value", 0))

        if event_type == "click":
            analytics["total_clicks"] = analytics.get("total_clicks", 0) + 1
        elif event_type == "detail_open":
            analytics["total_detail_opens"] = analytics.get("total_detail_opens", 0) + 1
        elif event_type == "read_time":
            analytics["total_read_time_seconds"] = analytics.get("total_read_time_seconds", 0) + value
            analytics["total_reads"] = analytics.get("total_reads", 0) + 1
            # Track average read time
            total_reads = analytics.get("total_reads", 1)
            total_time = analytics.get("total_read_time_seconds", 0)
            analytics["avg_read_time_seconds"] = round(total_time / max(1, total_reads), 1)
        elif event_type == "scroll_depth":
            depth_sum = analytics.get("total_scroll_depth_sum", 0) + value
            depth_count = analytics.get("total_scroll_events", 0) + 1
            analytics["total_scroll_depth_sum"] = depth_sum
            analytics["total_scroll_events"] = depth_count
            analytics["avg_scroll_depth_pct"] = round(depth_sum / max(1, depth_count), 1)
        elif event_type == "save":
            analytics["total_saves"] = analytics.get("total_saves", 0) + 1
        elif event_type == "unsave":
            analytics["total_unsaves"] = analytics.get("total_unsaves", 0) + 1
        elif event_type == "share":
            analytics["total_shares"] = analytics.get("total_shares", 0) + 1
        elif event_type == "external_click":
            analytics["total_external_clicks"] = analytics.get("total_external_clicks", 0) + 1
        elif event_type == "impression":
            analytics["total_impressions"] = analytics.get("total_impressions", 0) + 1
        elif event_type == "hold":
            analytics["total_holds"] = analytics.get("total_holds", 0) + 1

    # Track unique sessions
    session_id = events[0].get("session_id", "") if events else ""
    seen_sessions = analytics.get("seen_sessions", [])
    if session_id and session_id not in seen_sessions:
        seen_sessions.append(session_id)
        # Keep only last 100 session IDs to bound storage
        if len(seen_sessions) > 100:
            seen_sessions = seen_sessions[-100:]
        analytics["seen_sessions"] = seen_sessions
        analytics["session_count"] = len(seen_sessions)

    analytics["last_event_at"] = datetime.now(UTC).isoformat()

    profile["analytics"] = analytics
    profile["last_active"] = datetime.now(UTC).isoformat()
    await db.save_profile(profile)


async def _recompute_scores(session_id: str, sync_code: str) -> None:
    """Recompute topic scores from all events for this session."""
    # Get recent events (last 1000)
    if sync_code:
        events = await db.get_events_by_sync_code(sync_code, limit=1000)
    else:
        events = await db.get_events(session_id, limit=1000)

    scores: dict[str, float] = {}
    event_counts: dict[str, int] = {}

    # Track per-article engagement to avoid double-counting
    article_engagement: dict[str, dict] = {}

    for e in events:
        topic = e.get("topic", "")
        if not topic:
            continue

        event_type = e.get("event_type", "")
        value = float(e.get("value", 0))
        article_id = e.get("article_id", "")
        weight = EVENT_WEIGHTS.get(event_type, 0)

        # Apply graduated scoring for read_time
        if event_type == "read_time":
            for threshold, bracket_weight in READ_TIME_BRACKETS:
                if value >= threshold:
                    weight = bracket_weight
                    break

        # Apply threshold filters for scroll events
        elif event_type == "scroll_depth":
            if value >= 90:
                weight = weight * 1.5  # Bonus for reading almost everything
            elif value >= SCROLL_DEPTH_THRESHOLD_PCT:
                weight = weight * 1.0  # Full credit
            elif value >= 40:
                weight = weight * 0.5  # Partial credit
            else:
                weight = weight * 0.15  # Minimal credit for shallow scrolls

        # Track compound engagement per article
        if article_id and event_type in ("click", "detail_open", "read_time", "scroll_depth", "save", "external_click"):
            if article_id not in article_engagement:
                article_engagement[article_id] = {"topic": topic, "actions": set(), "read_time": 0, "scroll": 0}
            article_engagement[article_id]["actions"].add(event_type)
            if event_type == "read_time":
                article_engagement[article_id]["read_time"] = max(article_engagement[article_id]["read_time"], value)
            if event_type == "scroll_depth":
                article_engagement[article_id]["scroll"] = max(article_engagement[article_id]["scroll"], value)

        if weight != 0:
            scores[topic] = scores.get(topic, 0) + weight
            event_counts[topic] = event_counts.get(topic, 0) + 1

    # Bonus for deep engagement: if a user clicked, read 15s+, AND scrolled 70%+ on the same article
    for _article_id, data in article_engagement.items():
        topic = data["topic"]
        actions = data["actions"]
        if (
            len(actions) >= 3
            and "click" in actions
            and data["read_time"] >= READ_TIME_THRESHOLD_SECONDS
            and data["scroll"] >= SCROLL_DEPTH_THRESHOLD_PCT
        ):
            # Deep engagement bonus
            scores[topic] = scores.get(topic, 0) + 3.0
            if "save" in actions:
                scores[topic] = scores.get(topic, 0) + 2.0  # Extra bonus for save + deep read
            if "external_click" in actions:
                scores[topic] = scores.get(topic, 0) + 1.5  # Went to original source = high interest

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

    # Normalize scores to 0-1 range for balanced blending
    max_score = max(abs(v) for v in scores.values()) if scores else 1.0
    if max_score == 0:
        max_score = 1.0

    def rank_score(article: dict) -> float:
        topic = article.get("topic", "")
        category = article.get("category", "")
        # Check both the UI topic label and the internal category
        topic_score = (scores.get(topic, 0) + scores.get(category, 0)) / max_score
        importance = float(article.get("importance", 5))
        # Blend: personalization (60%) + editorial importance (40%)
        return topic_score * 6.0 + importance * 0.4

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
