"""
Anonymous user profiles with memorable Sync Codes.
Profiles are stored in profiles.json (same pattern as subscribers.json).
When Supabase is configured, profiles are synced to cloud DB every 5 min.
"""

import json
import logging
import random
import threading
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger("dailyai.profiles")

PROFILES_FILE = Path("profiles.json")
_lock = threading.Lock()

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


# ── File I/O ────────────────────────────────────────────────────────
def _load_profiles() -> dict[str, dict]:
    """Load all profiles as {sync_code: profile_dict}."""
    if PROFILES_FILE.exists():
        try:
            data = json.loads(PROFILES_FILE.read_text())
            if isinstance(data, dict):
                return data
        except (OSError, json.JSONDecodeError):
            pass
    return {}


def _save_profiles(profiles: dict[str, dict]) -> None:
    """Persist profiles dict to disk."""
    with _lock:
        PROFILES_FILE.write_text(json.dumps(profiles, indent=2))


# ── Sync Code generation ────────────────────────────────────────────
def generate_sync_code(existing_codes: set[str] | None = None) -> str:
    """Generate a unique Adjective-Noun-Number sync code."""
    if existing_codes is None:
        existing_codes = set(_load_profiles().keys())

    for _ in range(500):  # generous retry budget
        adj = random.choice(ADJECTIVES)
        noun = random.choice(NOUNS)
        num = random.randint(10, 99)
        code = f"{adj}-{noun}-{num}"
        if code not in existing_codes:
            return code

    # Extremely unlikely fallback — extend with 3-digit number
    return f"{random.choice(ADJECTIVES)}-{random.choice(NOUNS)}-{random.randint(100, 999)}"


# ── Profile CRUD ────────────────────────────────────────────────────
def create_profile(preferred_topics: list[str], country: str = "GLOBAL",
                   language: str = "en") -> dict:
    """Create a new anonymous profile and return it."""
    profiles = _load_profiles()
    sync_code = generate_sync_code(set(profiles.keys()))
    now = datetime.now(UTC).isoformat()

    profile = {
        "sync_code": sync_code,
        "preferred_topics": preferred_topics[:8],  # cap at 8
        "country": country,
        "language": language,
        "signals": {},        # topic -> score
        "bookmarks": [],      # article IDs
        "created_at": now,
        "last_active": now,
    }

    profiles[sync_code] = profile
    _save_profiles(profiles)
    logger.info(f"Created profile: {sync_code} (topics: {preferred_topics})")
    return profile


def get_profile(sync_code: str) -> dict | None:
    """Retrieve a profile by sync code (case-sensitive)."""
    profiles = _load_profiles()
    return profiles.get(sync_code)


def update_preferences(sync_code: str, preferred_topics: list[str] | None = None,
                       country: str | None = None, language: str | None = None,
                       bookmarks: list[str] | None = None) -> dict | None:
    """Update an existing profile's preferences."""
    profiles = _load_profiles()
    profile = profiles.get(sync_code)
    if not profile:
        return None

    if preferred_topics is not None:
        profile["preferred_topics"] = preferred_topics[:8]
    if country is not None:
        profile["country"] = country
    if language is not None:
        profile["language"] = language
    if bookmarks is not None:
        profile["bookmarks"] = bookmarks[:200]  # cap stored bookmarks

    profile["last_active"] = datetime.now(UTC).isoformat()
    profiles[sync_code] = profile
    _save_profiles(profiles)
    return profile


def record_signal(sync_code: str, topic: str, action: str) -> dict | None:
    """Record an implicit interaction signal for a topic.

    Actions & weights:
        tap    → +1
        save   → +3
        skip   → -1
        unsave → -1
    """
    SIGNAL_WEIGHTS = {
        "tap": 1,
        "save": 3,
        "skip": -1,
        "unsave": -1,
    }

    weight = SIGNAL_WEIGHTS.get(action, 0)
    if weight == 0 or not topic:
        return None

    profiles = _load_profiles()
    profile = profiles.get(sync_code)
    if not profile:
        return None

    signals = profile.get("signals", {})
    signals[topic] = signals.get(topic, 0) + weight
    profile["signals"] = signals
    profile["last_active"] = datetime.now(UTC).isoformat()

    profiles[sync_code] = profile
    _save_profiles(profiles)
    return profile


def get_topic_scores(sync_code: str) -> dict[str, float]:
    """Get combined preference scores for feed ranking.

    Merges explicit preferences (each = +10 base score) with implicit signals.
    Returns {topic: score} sorted descending.
    """
    profile = get_profile(sync_code)
    if not profile:
        return {}

    scores: dict[str, float] = {}

    # Explicit preferences get a strong base score
    for topic in profile.get("preferred_topics", []):
        scores[topic] = scores.get(topic, 0) + 10.0

    # Layer in implicit signals
    for topic, signal_score in profile.get("signals", {}).items():
        scores[topic] = scores.get(topic, 0) + float(signal_score)

    # Sort descending
    return dict(sorted(scores.items(), key=lambda x: x[1], reverse=True))


def record_analytics(sync_code: str, stats: dict) -> dict | None:
    """Merge session-level analytics into the profile.

    Expected stats keys:
        taps, saves, reads, skips, briefs_opened, time_spent_seconds, session_count
    Each value is an increment from the current session.
    """
    profiles = _load_profiles()
    profile = profiles.get(sync_code)
    if not profile:
        return None

    analytics = profile.get("analytics", {
        "total_taps": 0,
        "total_saves": 0,
        "total_reads": 0,
        "total_skips": 0,
        "total_briefs_opened": 0,
        "total_time_spent_seconds": 0,
        "session_count": 0,
    })

    FIELD_MAP = {
        "taps": "total_taps",
        "saves": "total_saves",
        "reads": "total_reads",
        "skips": "total_skips",
        "briefs_opened": "total_briefs_opened",
        "time_spent_seconds": "total_time_spent_seconds",
        "session_count": "session_count",
    }
    for src_key, dest_key in FIELD_MAP.items():
        val = stats.get(src_key, 0)
        with suppress(TypeError, ValueError):
            analytics[dest_key] = analytics.get(dest_key, 0) + int(val)

    profile["analytics"] = analytics
    profile["last_active"] = datetime.now(UTC).isoformat()
    profiles[sync_code] = profile
    _save_profiles(profiles)
    logger.info(f"Analytics updated for {sync_code}: {analytics}")
    return analytics
