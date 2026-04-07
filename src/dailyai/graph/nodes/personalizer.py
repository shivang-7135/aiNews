"""
Node: Personalizer
Re-ranks articles based on user profile preferences and interaction signals.
Falls back to default quality ranking when no profile is available.
"""

import logging
import time
from datetime import UTC, datetime

from dailyai.config import MAX_TILES_PER_FETCH

logger = logging.getLogger("dailyai.graph.personalizer")


def _quality_score(article: dict) -> float:
    """Compute a quality score for default ranking."""
    now = datetime.now(UTC)
    base = int(article.get("importance", 5))
    trust_bonus = article.get("_trust_score", 0)

    # Recency bonus
    recency = 0
    published = article.get("published", "")
    if published:
        try:
            dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
            age_hours = max((now - dt).total_seconds() / 3600, 0)
            if age_hours <= 8:
                recency = 2
            elif age_hours <= 24:
                recency = 1
        except Exception:
            pass

    return base * 10.0 + trust_bonus * 3.0 + recency


async def run(state: dict) -> dict:
    """Personalizer node: Rank articles for the user.

    Reads: threaded, user_profile
    Writes: final_feed, node_timings
    """
    start = time.time()
    articles = state.get("threaded", [])
    profile = state.get("user_profile")

    if profile and profile.get("signals"):
        # Personalized ranking
        signals = profile.get("signals", {})
        preferred = set(profile.get("preferred_topics", []))

        def personal_score(article: dict) -> float:
            category = article.get("category", "general")
            topic = article.get("topic", "general")
            pref_score = 0.0

            if category in preferred or topic in preferred:
                pref_score += 10.0
            pref_score += float(signals.get(category, 0)) + float(signals.get(topic, 0))

            return pref_score * 2.0 + _quality_score(article)

        articles.sort(key=personal_score, reverse=True)
        logger.info(f"[Personalizer] Personalized ranking for {profile.get('sync_code', '?')}")
    else:
        # Default quality ranking
        articles.sort(key=_quality_score, reverse=True)
        logger.info("[Personalizer] Default quality ranking")

    # Enforce topic diversity: max 3 of the same topic in top 12
    selected: list[dict] = []
    topic_counts: dict[str, int] = {}

    for article in articles:
        topic = str(article.get("topic", "general"))
        cap = 3 if len(selected) < 12 else 4
        if topic_counts.get(topic, 0) < cap:
            selected.append(article)
            topic_counts[topic] = topic_counts.get(topic, 0) + 1
        if len(selected) >= MAX_TILES_PER_FETCH:
            break

    # Backfill if we have room while still respecting topic diversity caps.
    if len(selected) < min(MAX_TILES_PER_FETCH, len(articles)):
        existing_titles = {a.get("title") for a in selected}
        for article in articles:
            title = article.get("title")
            if title in existing_titles:
                continue

            topic = str(article.get("topic", "general"))
            cap = 3 if len(selected) < 12 else 4
            if topic_counts.get(topic, 0) >= cap:
                continue

            selected.append(article)
            existing_titles.add(title)
            topic_counts[topic] = topic_counts.get(topic, 0) + 1
            if len(selected) >= MAX_TILES_PER_FETCH:
                break

    # Clean up internal fields
    for article in selected:
        article.pop("_trust_score", None)

    elapsed = time.time() - start
    timings = state.get("node_timings", {})
    timings["personalizer"] = round(elapsed, 4)

    return {
        "final_feed": selected,
        "node_timings": timings,
    }
