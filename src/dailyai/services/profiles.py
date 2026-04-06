"""
DailyAI — User Profiles Service
Anonymous user profiles with memorable Sync Codes.
Now backed by SQLite instead of JSON files.
"""

import logging
import random
from datetime import UTC, datetime

from dailyai.storage import sqlite as db

logger = logging.getLogger("dailyai.services.profiles")

# ── Sync Code word lists ─────────────────────────────────────────────
ADJECTIVES = [
    "Clever", "Neon", "Swift", "Bright", "Cosmic", "Calm", "Bold", "Lucky",
    "Quiet", "Vivid", "Warm", "Cool", "Sharp", "Fuzzy", "Rapid", "Wild",
    "Gentle", "Epic", "Silky", "Turbo", "Nova", "Pixel", "Zen", "Hyper",
    "Solar", "Lunar", "Cyber", "Iron", "Golden", "Silver", "Crystal", "Amber",
    "Coral", "Azure", "Sage", "Ruby", "Jade", "Onyx", "Pearl", "Maple",
    "Storm", "Blaze", "Frost", "Drift", "Cloud", "Flash", "Spark", "Orbit",
    "Prism", "Pulse",
]

NOUNS = [
    "Panda", "Coffee", "Falcon", "Tiger", "Pixel", "Lotus", "Phoenix",
    "Raven", "Comet", "Orbit", "Prism", "Quasar", "Nebula", "Spark",
    "Thunder", "Breeze", "Canyon", "Summit", "River", "Maple", "Cedar",
    "Glacier", "Horizon", "Echo", "Ripple", "Compass", "Lantern", "Rocket",
    "Arrow", "Shield", "Beacon", "Anchor", "Voyager", "Pioneer", "Cosmos",
    "Atlas", "Nova", "Zenith", "Vertex", "Ember", "Flame", "Willow",
    "Birch", "Otter", "Wolf", "Fox", "Hawk", "Crane", "Lynx", "Coral",
]


def _generate_sync_code() -> str:
    """Generate a unique Adjective-Noun-Number sync code."""
    adj = random.choice(ADJECTIVES)
    noun = random.choice(NOUNS)
    num = random.randint(10, 99)
    return f"{adj}-{noun}-{num}"


async def create_profile(
    preferred_topics: list[str],
    country: str = "GLOBAL",
    language: str = "en",
) -> dict:
    """Create a new anonymous profile."""
    # Generate unique sync code
    for _ in range(500):
        code = _generate_sync_code()
        existing = await db.get_profile(code)
        if not existing:
            break
    else:
        code = f"{random.choice(ADJECTIVES)}-{random.choice(NOUNS)}-{random.randint(100, 999)}"

    now = datetime.now(UTC).isoformat()
    profile = {
        "sync_code": code,
        "preferred_topics": preferred_topics[:8],
        "country": country,
        "language": language,
        "signals": {},
        "bookmarks": [],
        "analytics": {},
        "created_at": now,
        "last_active": now,
    }

    await db.save_profile(profile)
    logger.info(f"Created profile: {code} (topics: {preferred_topics})")
    return profile


async def get_profile(sync_code: str) -> dict | None:
    """Get a profile by sync code."""
    return await db.get_profile(sync_code)


async def update_preferences(
    sync_code: str,
    preferred_topics: list[str] | None = None,
    country: str | None = None,
    language: str | None = None,
    bookmarks: list[str] | None = None,
) -> dict | None:
    """Update profile preferences."""
    profile = await db.get_profile(sync_code)
    if not profile:
        return None

    if preferred_topics is not None:
        profile["preferred_topics"] = preferred_topics[:8]
    if country is not None:
        profile["country"] = country
    if language is not None:
        profile["language"] = language
    if bookmarks is not None:
        profile["bookmarks"] = bookmarks[:200]

    profile["last_active"] = datetime.now(UTC).isoformat()
    await db.save_profile(profile)
    return profile


async def record_signal(sync_code: str, topic: str, action: str) -> dict | None:
    """Record an implicit interaction signal.

    Actions & weights: tap=+1, save=+3, skip=-1, unsave=-1
    """
    WEIGHTS = {"tap": 1, "save": 3, "skip": -1, "unsave": -1}
    weight = WEIGHTS.get(action, 0)
    if weight == 0 or not topic:
        return None

    profile = await db.get_profile(sync_code)
    if not profile:
        return None

    signals = profile.get("signals", {})
    signals[topic] = signals.get(topic, 0) + weight
    profile["signals"] = signals
    profile["last_active"] = datetime.now(UTC).isoformat()
    await db.save_profile(profile)
    return profile


async def get_topic_scores(sync_code: str) -> dict[str, float]:
    """Get combined preference scores for feed ranking."""
    profile = await db.get_profile(sync_code)
    if not profile:
        return {}

    scores: dict[str, float] = {}
    for topic in profile.get("preferred_topics", []):
        scores[topic] = scores.get(topic, 0) + 10.0
    for topic, signal_score in profile.get("signals", {}).items():
        scores[topic] = scores.get(topic, 0) + float(signal_score)

    return dict(sorted(scores.items(), key=lambda x: x[1], reverse=True))


async def record_analytics(sync_code: str, stats: dict) -> dict | None:
    """Merge session-level analytics into the profile."""
    profile = await db.get_profile(sync_code)
    if not profile:
        return None

    analytics = profile.get("analytics", {})
    FIELD_MAP = {
        "taps": "total_taps", "saves": "total_saves", "reads": "total_reads",
        "skips": "total_skips", "briefs_opened": "total_briefs_opened",
        "time_spent_seconds": "total_time_spent_seconds", "session_count": "session_count",
    }
    for src_key, dest_key in FIELD_MAP.items():
        try:
            analytics[dest_key] = analytics.get(dest_key, 0) + int(stats.get(src_key, 0))
        except (TypeError, ValueError):
            pass

    profile["analytics"] = analytics
    profile["last_active"] = datetime.now(UTC).isoformat()
    await db.save_profile(profile)
    return analytics
