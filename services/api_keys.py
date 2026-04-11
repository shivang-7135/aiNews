"""
DailyAI Developer API — Key Management & Rate Limiting

API key tiers:
  - free:       100 requests/day,  basic fields
  - pro:        10,000 requests/day, full fields + sentiment + threads
  - enterprise: 50,000 requests/day, full fields + priority support

Keys are stored in api_keys.json (same pattern as profiles.json).
Monetization layer — kept separate from open-source core.
"""

import hashlib
import json
import logging
import secrets
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

logger = logging.getLogger("dailyai.apikeys")

API_KEYS_FILE = Path("api_keys.json")
_lock = threading.Lock()

# ── Tier definitions ────────────────────────────────────────────────
TIERS = {
    "free": {
        "display_name": "Free",
        "daily_limit": 100,
        "fields": "basic",  # headline, summary, source, published
        "price_eur": 0,
    },
    "pro": {
        "display_name": "Pro",
        "daily_limit": 10_000,
        "fields": "full",  # + sentiment, trust, threads, why_it_matters
        "price_eur": 7.99,
    },
    "enterprise": {
        "display_name": "Enterprise",
        "daily_limit": 50_000,
        "fields": "full",
        "price_eur": None,  # custom pricing
    },
}

# Basic fields returned in free tier
BASIC_FIELDS = {
    "id",
    "headline",
    "summary",
    "category",
    "topic",
    "source_name",
    "article_url",
    "published_at",
    "importance",
}

# Full fields returned in pro/enterprise tiers
FULL_FIELDS = BASIC_FIELDS | {
    "why_it_matters",
    "source_trust",
    "sentiment",
    "story_thread",
    "thread_count",
    "updated_at",
}


# ── File I/O ────────────────────────────────────────────────────────
def _load_keys() -> dict[str, dict]:
    if API_KEYS_FILE.exists():
        try:
            data = json.loads(API_KEYS_FILE.read_text())
            if isinstance(data, dict):
                return data
        except (OSError, json.JSONDecodeError):
            pass
    return {}


def _save_keys(keys: dict[str, dict]) -> None:
    with _lock:
        API_KEYS_FILE.write_text(json.dumps(keys, indent=2))


# ── Key generation ──────────────────────────────────────────────────
def _hash_key(raw_key: str) -> str:
    """SHA-256 hash for storage — never store raw keys."""
    return hashlib.sha256(raw_key.encode()).hexdigest()


def create_api_key(
    name: str,
    email: str,
    tier: str = "free",
) -> dict:
    """Create a new API key. Returns the full key (only shown once)."""
    if tier not in TIERS:
        tier = "free"

    raw_key = f"dai_{secrets.token_urlsafe(32)}"
    key_hash = _hash_key(raw_key)
    now = datetime.now(UTC).isoformat()

    key_record = {
        "key_hash": key_hash,
        "key_prefix": raw_key[:12] + "...",
        "name": name[:100],
        "email": email[:200],
        "tier": tier,
        "created_at": now,
        "last_used": now,
        "total_requests": 0,
        "is_active": True,
    }

    keys = _load_keys()
    keys[key_hash] = key_record
    _save_keys(keys)

    logger.info(f"[API Key] Created {tier} key for {email}: {raw_key[:12]}...")

    return {
        "api_key": raw_key,  # Only returned at creation time
        "key_prefix": key_record["key_prefix"],
        "tier": tier,
        "daily_limit": TIERS[tier]["daily_limit"],
        "created_at": now,
    }


def validate_api_key(raw_key: str) -> dict | None:
    """Validate an API key. Returns key record if valid, None if invalid."""
    if not raw_key or not raw_key.startswith("dai_"):
        return None

    key_hash = _hash_key(raw_key)
    keys = _load_keys()
    record = keys.get(key_hash)

    if not record:
        return None
    if not record.get("is_active", True):
        return None

    # Update last used
    record["last_used"] = datetime.now(UTC).isoformat()
    record["total_requests"] = record.get("total_requests", 0) + 1
    keys[key_hash] = record
    _save_keys(keys)

    return record


# ── Rate limiting (in-memory per-process) ───────────────────────────
_rate_buckets: dict[str, list[float]] = {}
_rate_lock = threading.Lock()


def check_rate_limit(key_hash: str, tier: str) -> tuple[bool, int, int]:
    """Check if the key has exceeded its daily rate limit.

    Returns (allowed, remaining, limit).
    """
    limit = cast(int, TIERS.get(tier, TIERS["free"])["daily_limit"])
    now = time.time()
    day_start = now - 86400  # rolling 24h window

    with _rate_lock:
        bucket = _rate_buckets.get(key_hash, [])
        # Prune old entries
        bucket = [t for t in bucket if t > day_start]
        _rate_buckets[key_hash] = bucket

        remaining = max(0, limit - len(bucket))
        if len(bucket) >= limit:
            return False, 0, limit

        bucket.append(now)
        _rate_buckets[key_hash] = bucket
        return True, remaining - 1, limit


def filter_fields_for_tier(article: dict, tier: str) -> dict:
    """Filter article fields based on API tier."""
    allowed = FULL_FIELDS if tier in ("pro", "enterprise") else BASIC_FIELDS
    return {k: v for k, v in article.items() if k in allowed}


def get_api_key_stats(raw_key: str) -> dict | None:
    """Get usage stats for an API key."""
    if not raw_key:
        return None

    key_hash = _hash_key(raw_key)
    keys = _load_keys()
    record = keys.get(key_hash)

    if not record:
        return None

    tier = record.get("tier", "free")
    tier_info = TIERS.get(tier, TIERS["free"])
    daily_limit = cast(int, tier_info["daily_limit"])

    # Get current usage from rate bucket
    now = time.time()
    day_start = now - 86400
    with _rate_lock:
        bucket = _rate_buckets.get(key_hash, [])
        today_count = sum(1 for t in bucket if t > day_start)

    return {
        "key_prefix": record.get("key_prefix", ""),
        "name": record.get("name", ""),
        "tier": tier,
        "tier_display": tier_info["display_name"],
        "daily_limit": daily_limit,
        "requests_today": today_count,
        "remaining_today": max(0, daily_limit - today_count),
        "total_requests": record.get("total_requests", 0),
        "created_at": record.get("created_at", ""),
        "last_used": record.get("last_used", ""),
        "is_active": record.get("is_active", True),
    }
