"""
DailyAI — SQLite Storage Layer
Replaces JSON file persistence with proper async SQLite database.
Zero-config, serverless, handles concurrent reads, and queryable.
"""

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

import aiosqlite

from dailyai.config import DB_PATH

logger = logging.getLogger("dailyai.storage")

_db: aiosqlite.Connection | None = None


async def get_db() -> aiosqlite.Connection:
    """Get or create the database connection."""
    global _db
    if _db is None:
        _db = await aiosqlite.connect(DB_PATH)
        _db.row_factory = aiosqlite.Row
        await _create_tables(_db)
        logger.info(f"SQLite database connected: {DB_PATH}")
    return _db


async def close_db():
    """Close the database connection."""
    global _db
    if _db:
        await _db.close()
        _db = None


async def _create_tables(db: aiosqlite.Connection):
    """Create all tables if they don't exist."""
    await db.executescript("""
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_key TEXT NOT NULL,
            title TEXT NOT NULL,
            summary TEXT DEFAULT '',
            why_it_matters TEXT DEFAULT '',
            category TEXT DEFAULT 'general',
            topic TEXT DEFAULT 'general',
            importance INTEGER DEFAULT 5,
            source TEXT DEFAULT '',
            source_trust TEXT DEFAULT 'low',
            sentiment TEXT DEFAULT 'neutral',
            story_thread TEXT DEFAULT '',
            link TEXT DEFAULT '',
            published TEXT DEFAULT '',
            fetched_at TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_articles_store_key ON articles(store_key);
        CREATE INDEX IF NOT EXISTS idx_articles_importance ON articles(importance DESC);
        CREATE INDEX IF NOT EXISTS idx_articles_topic ON articles(topic);

        CREATE TABLE IF NOT EXISTS profiles (
            sync_code TEXT PRIMARY KEY,
            preferred_topics TEXT DEFAULT '[]',
            country TEXT DEFAULT 'GLOBAL',
            language TEXT DEFAULT 'en',
            signals TEXT DEFAULT '{}',
            bookmarks TEXT DEFAULT '[]',
            analytics TEXT DEFAULT '{}',
            created_at TEXT DEFAULT (datetime('now')),
            last_active TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS subscribers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            topics TEXT DEFAULT '[]',
            country TEXT DEFAULT 'GLOBAL',
            language TEXT DEFAULT 'en',
            subscribed_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            is_active INTEGER DEFAULT 1
        );

        CREATE INDEX IF NOT EXISTS idx_subscribers_email ON subscribers(email);

        CREATE TABLE IF NOT EXISTS api_keys (
            key_hash TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            tier TEXT DEFAULT 'free',
            created_at TEXT DEFAULT (datetime('now')),
            is_active INTEGER DEFAULT 1,
            requests_today INTEGER DEFAULT 0,
            last_request_date TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT DEFAULT ''
        );
    """)
    await db.commit()


# ── Articles ────────────────────────────────────────────────────────

async def save_articles(store_key: str, articles: list[dict]) -> None:
    """Save articles for a given store key (replaces existing)."""
    db = await get_db()

    # Delete old articles for this key
    await db.execute("DELETE FROM articles WHERE store_key = ?", (store_key,))

    # Insert new
    for a in articles:
        await db.execute(
            """INSERT INTO articles
               (store_key, title, summary, why_it_matters, category, topic,
                importance, source, source_trust, sentiment, story_thread,
                link, published, fetched_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                store_key,
                a.get("title", ""),
                a.get("summary", ""),
                a.get("why_it_matters", ""),
                a.get("category", "general"),
                a.get("topic", "general"),
                int(a.get("importance", 5)),
                a.get("source", ""),
                a.get("source_trust", "low"),
                a.get("sentiment", "neutral"),
                a.get("story_thread", ""),
                a.get("link", ""),
                a.get("published", ""),
                a.get("fetched_at", datetime.now(UTC).isoformat()),
            ),
        )
    await db.commit()
    logger.info(f"Saved {len(articles)} articles for key={store_key}")


async def get_articles(store_key: str) -> list[dict]:
    """Get all articles for a given store key."""
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM articles WHERE store_key = ? ORDER BY importance DESC",
        (store_key,),
    )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def get_all_store_keys() -> list[str]:
    """Get all unique store keys."""
    db = await get_db()
    cursor = await db.execute("SELECT DISTINCT store_key FROM articles")
    rows = await cursor.fetchall()
    return [row["store_key"] for row in rows]


async def get_articles_count(store_key: str) -> int:
    """Get count of articles for a key."""
    db = await get_db()
    cursor = await db.execute(
        "SELECT COUNT(*) as cnt FROM articles WHERE store_key = ?", (store_key,)
    )
    row = await cursor.fetchone()
    return row["cnt"] if row else 0


# ── Profiles ────────────────────────────────────────────────────────

async def save_profile(profile: dict) -> None:
    """Upsert a user profile."""
    db = await get_db()
    await db.execute(
        """INSERT OR REPLACE INTO profiles
           (sync_code, preferred_topics, country, language, signals, bookmarks,
            analytics, created_at, last_active)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            profile["sync_code"],
            json.dumps(profile.get("preferred_topics", [])),
            profile.get("country", "GLOBAL"),
            profile.get("language", "en"),
            json.dumps(profile.get("signals", {})),
            json.dumps(profile.get("bookmarks", [])),
            json.dumps(profile.get("analytics", {})),
            profile.get("created_at", datetime.now(UTC).isoformat()),
            profile.get("last_active", datetime.now(UTC).isoformat()),
        ),
    )
    await db.commit()


async def get_profile(sync_code: str) -> dict | None:
    """Get a profile by sync code."""
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM profiles WHERE sync_code = ?", (sync_code,)
    )
    row = await cursor.fetchone()
    if not row:
        return None
    profile = dict(row)
    # Parse JSON fields
    profile["preferred_topics"] = json.loads(profile.get("preferred_topics", "[]"))
    profile["signals"] = json.loads(profile.get("signals", "{}"))
    profile["bookmarks"] = json.loads(profile.get("bookmarks", "[]"))
    profile["analytics"] = json.loads(profile.get("analytics", "{}"))
    return profile


async def get_all_profiles() -> list[dict]:
    """Get all profiles."""
    db = await get_db()
    cursor = await db.execute("SELECT * FROM profiles")
    rows = await cursor.fetchall()
    profiles = []
    for row in rows:
        p = dict(row)
        p["preferred_topics"] = json.loads(p.get("preferred_topics", "[]"))
        p["signals"] = json.loads(p.get("signals", "{}"))
        p["bookmarks"] = json.loads(p.get("bookmarks", "[]"))
        p["analytics"] = json.loads(p.get("analytics", "{}"))
        profiles.append(p)
    return profiles


# ── Subscribers ─────────────────────────────────────────────────────

async def save_subscriber(subscriber: dict) -> None:
    """Upsert a subscriber."""
    db = await get_db()
    await db.execute(
        """INSERT OR REPLACE INTO subscribers
           (email, topics, country, language, subscribed_at, updated_at, is_active)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            subscriber["email"],
            json.dumps(subscriber.get("topics", [])),
            subscriber.get("country", "GLOBAL"),
            subscriber.get("language", "en"),
            subscriber.get("subscribed_at", datetime.now(UTC).isoformat()),
            subscriber.get("updated_at", datetime.now(UTC).isoformat()),
            1 if subscriber.get("is_active", True) else 0,
        ),
    )
    await db.commit()


async def get_subscriber(email: str) -> dict | None:
    """Get a subscriber by email."""
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM subscribers WHERE email = ?", (email,)
    )
    row = await cursor.fetchone()
    if not row:
        return None
    sub = dict(row)
    sub["topics"] = json.loads(sub.get("topics", "[]"))
    sub["is_active"] = bool(sub.get("is_active", 1))
    return sub


async def get_all_subscribers() -> list[dict]:
    """Get all active subscribers."""
    db = await get_db()
    cursor = await db.execute("SELECT * FROM subscribers WHERE is_active = 1")
    rows = await cursor.fetchall()
    subs = []
    for row in rows:
        s = dict(row)
        s["topics"] = json.loads(s.get("topics", "[]"))
        s["is_active"] = bool(s.get("is_active", 1))
        subs.append(s)
    return subs


async def get_subscriber_count() -> int:
    """Get total subscriber count."""
    db = await get_db()
    cursor = await db.execute("SELECT COUNT(*) as cnt FROM subscribers WHERE is_active = 1")
    row = await cursor.fetchone()
    return row["cnt"] if row else 0


# ── Metadata ────────────────────────────────────────────────────────

async def set_metadata(key: str, value: str) -> None:
    """Set a metadata value."""
    db = await get_db()
    await db.execute(
        "INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
        (key, value),
    )
    await db.commit()


async def get_metadata(key: str) -> str | None:
    """Get a metadata value."""
    db = await get_db()
    cursor = await db.execute("SELECT value FROM metadata WHERE key = ?", (key,))
    row = await cursor.fetchone()
    return row["value"] if row else None
