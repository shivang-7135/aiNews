"""
DailyAI — SQLite Storage Layer
Replaces JSON file persistence with proper async SQLite database.
Zero-config, serverless, handles concurrent reads, and queryable.
"""

import json
import logging
from datetime import UTC, datetime

import aiosqlite

from dailyai.config import CACHE_MAX_ARTICLES, CACHE_MIN_PER_KEY, DB_PATH

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

        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS user_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            sync_code TEXT DEFAULT '',
            event_type TEXT NOT NULL,
            article_id TEXT DEFAULT '',
            topic TEXT DEFAULT '',
            category TEXT DEFAULT '',
            value REAL DEFAULT 0,
            metadata TEXT DEFAULT '{}',
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_user_events_session ON user_events(session_id);
        CREATE INDEX IF NOT EXISTS idx_user_events_sync ON user_events(sync_code);
        CREATE INDEX IF NOT EXISTS idx_user_events_type ON user_events(event_type);
        CREATE INDEX IF NOT EXISTS idx_user_events_created ON user_events(created_at);

        CREATE TABLE IF NOT EXISTS user_topic_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            sync_code TEXT DEFAULT '',
            topic TEXT NOT NULL,
            score REAL DEFAULT 0,
            event_count INTEGER DEFAULT 0,
            updated_at TEXT DEFAULT (datetime('now')),
            UNIQUE(session_id, topic)
        );

        CREATE INDEX IF NOT EXISTS idx_topic_scores_session ON user_topic_scores(session_id);
        CREATE INDEX IF NOT EXISTS idx_topic_scores_sync ON user_topic_scores(sync_code);

        CREATE TABLE IF NOT EXISTS user_session_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            sync_code TEXT DEFAULT '',
            impressions INTEGER DEFAULT 0,
            clicks INTEGER DEFAULT 0,
            detail_opens INTEGER DEFAULT 0,
            saves INTEGER DEFAULT 0,
            unsaves INTEGER DEFAULT 0,
            shares INTEGER DEFAULT 0,
            external_clicks INTEGER DEFAULT 0,
            holds INTEGER DEFAULT 0,
            total_read_time_sec REAL DEFAULT 0,
            avg_read_time_sec REAL DEFAULT 0,
            total_scroll_depth REAL DEFAULT 0,
            avg_scroll_depth REAL DEFAULT 0,
            read_events INTEGER DEFAULT 0,
            scroll_events INTEGER DEFAULT 0,
            top_topics TEXT DEFAULT '{}',
            first_seen TEXT DEFAULT (datetime('now')),
            last_seen TEXT DEFAULT (datetime('now')),
            UNIQUE(session_id)
        );

        CREATE INDEX IF NOT EXISTS idx_session_stats_sync ON user_session_stats(sync_code);
        CREATE INDEX IF NOT EXISTS idx_session_stats_last ON user_session_stats(last_seen);

        CREATE TABLE IF NOT EXISTS rss_feeds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            country_code TEXT NOT NULL,
            feed_key TEXT NOT NULL,
            query TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            UNIQUE(country_code, feed_key)
        );

        CREATE INDEX IF NOT EXISTS idx_rss_feeds_country ON rss_feeds(country_code);
    """)
    # Enable WAL mode for better concurrent read/write performance
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA busy_timeout=5000")
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

    await _prune_articles_cache(db)
    await db.commit()
    logger.info(f"Saved {len(articles)} articles for key={store_key}")


async def _prune_articles_cache(db: aiosqlite.Connection) -> None:
    """Keep the articles table bounded as a rotating cache.

    Preserves a small minimum per store key when possible so one popular
    key does not evict all other country/language caches.
    """
    cursor = await db.execute("SELECT COUNT(*) AS cnt FROM articles")
    row = await cursor.fetchone()
    total = int(row["cnt"] if row else 0)

    if total <= CACHE_MAX_ARTICLES:
        return

    deleted_this_run = 0

    while total > CACHE_MAX_ARTICLES:
        # Prefer deleting from keys that are above the per-key floor.
        cursor = await db.execute(
            """
            SELECT a.id
            FROM articles a
            JOIN (
              SELECT store_key, COUNT(*) AS cnt
              FROM articles
              GROUP BY store_key
            ) c ON c.store_key = a.store_key
            WHERE c.cnt > ?
            ORDER BY
              CASE WHEN a.fetched_at IS NULL OR a.fetched_at = '' THEN a.created_at ELSE a.fetched_at END ASC,
              a.id ASC
            LIMIT 1
            """,
            (CACHE_MIN_PER_KEY,),
        )
        victim = await cursor.fetchone()

        # If every key is already at floor, fall back to oldest overall row.
        if not victim:
            cursor = await db.execute(
                """
                SELECT id
                FROM articles
                ORDER BY
                  CASE WHEN fetched_at IS NULL OR fetched_at = '' THEN created_at ELSE fetched_at END ASC,
                  id ASC
                LIMIT 1
                """
            )
            victim = await cursor.fetchone()

        if not victim:
            break

        await db.execute("DELETE FROM articles WHERE id = ?", (victim["id"],))
        total -= 1
        deleted_this_run += 1

    if deleted_this_run > 0:
        now_iso = datetime.now(UTC).isoformat()

        await db.execute(
            "INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
            ("cache_prune_last_at", now_iso),
        )
        await db.execute(
            "INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
            ("cache_prune_last_deleted", str(deleted_this_run)),
        )

        # Increment cumulative prune counters.
        for counter_key in ("cache_prune_total_deleted", "cache_prune_runs"):
            cursor = await db.execute("SELECT value FROM metadata WHERE key = ?", (counter_key,))
            row = await cursor.fetchone()
            try:
                current = int((row["value"] if row else "0") or "0")
            except ValueError:
                current = 0

            increment = deleted_this_run if counter_key == "cache_prune_total_deleted" else 1
            await db.execute(
                "INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
                (counter_key, str(current + increment)),
            )


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
    cursor = await db.execute("SELECT * FROM profiles WHERE sync_code = ?", (sync_code,))
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
    cursor = await db.execute("SELECT * FROM subscribers WHERE email = ?", (email,))
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


async def get_all_metadata() -> dict[str, str]:
    """Get all metadata key/value pairs."""
    db = await get_db()
    cursor = await db.execute("SELECT key, value FROM metadata")
    rows = await cursor.fetchall()
    return {str(row["key"]): str(row["value"] or "") for row in rows}


async def get_cache_health() -> dict:
    """Return cache health metrics for admin/debug endpoints."""
    db = await get_db()

    cursor = await db.execute("SELECT COUNT(*) AS cnt FROM articles")
    row = await cursor.fetchone()
    total_articles = int(row["cnt"] if row else 0)

    cursor = await db.execute(
        """
        SELECT
          store_key,
          COUNT(*) AS article_count,
          MAX(importance) AS max_importance,
          MAX(CASE WHEN fetched_at IS NULL OR fetched_at = '' THEN created_at ELSE fetched_at END) AS last_cached_at
        FROM articles
        GROUP BY store_key
        ORDER BY store_key
        """
    )
    rows = await cursor.fetchall()

    per_key: list[dict] = []
    per_country: dict[str, int] = {}
    for r in rows:
        key = str(r["store_key"])
        country = key.split("::", 1)[0] if "::" in key else key
        count = int(r["article_count"] or 0)

        per_key.append(
            {
                "store_key": key,
                "article_count": count,
                "max_importance": int(r["max_importance"] or 0),
                "last_cached_at": r["last_cached_at"] or "",
            }
        )

        per_country[country] = per_country.get(country, 0) + count

    cursor = await db.execute(
        "SELECT key, value FROM metadata WHERE key LIKE 'last_updated:%' OR key LIKE 'cache_prune_%'"
    )
    meta_rows = await cursor.fetchall()

    last_refresh_by_key: dict[str, str] = {}
    prune_stats = {
        "last_at": "",
        "last_deleted": 0,
        "total_deleted": 0,
        "runs": 0,
    }

    for m in meta_rows:
        key = str(m["key"])
        value = str(m["value"] or "")

        if key.startswith("last_updated:"):
            last_refresh_by_key[key.replace("last_updated:", "", 1)] = value
            continue

        if key == "cache_prune_last_at":
            prune_stats["last_at"] = value
        elif key == "cache_prune_last_deleted":
            try:
                prune_stats["last_deleted"] = int(value or "0")
            except ValueError:
                prune_stats["last_deleted"] = 0
        elif key == "cache_prune_total_deleted":
            try:
                prune_stats["total_deleted"] = int(value or "0")
            except ValueError:
                prune_stats["total_deleted"] = 0
        elif key == "cache_prune_runs":
            try:
                prune_stats["runs"] = int(value or "0")
            except ValueError:
                prune_stats["runs"] = 0

    return {
        "cache_limit": CACHE_MAX_ARTICLES,
        "total_articles": total_articles,
        "total_store_keys": len(per_key),
        "per_store_key": per_key,
        "per_country": per_country,
        "prune": prune_stats,
        "last_refresh_by_store_key": last_refresh_by_key,
    }


# ── User Events (Analytics) ────────────────────────────────────────


async def save_events(events: list[dict]) -> None:
    """Batch insert analytics events."""
    db = await get_db()
    for e in events:
        await db.execute(
            """INSERT INTO user_events
               (session_id, sync_code, event_type, article_id, topic, category, value, metadata)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                e.get("session_id", ""),
                e.get("sync_code", ""),
                e.get("event_type", ""),
                e.get("article_id", ""),
                e.get("topic", ""),
                e.get("category", ""),
                float(e.get("value", 0)),
                json.dumps(e.get("metadata", {})),
            ),
        )
    await db.commit()


async def get_events(session_id: str, limit: int = 500) -> list[dict]:
    """Get events for a session."""
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM user_events WHERE session_id = ? ORDER BY created_at DESC LIMIT ?",
        (session_id, limit),
    )
    rows = await cursor.fetchall()
    result = []
    for row in rows:
        r = dict(row)
        try:
            r["metadata"] = json.loads(r.get("metadata", "{}"))
        except (json.JSONDecodeError, TypeError):
            r["metadata"] = {}
        result.append(r)
    return result


async def get_events_by_sync_code(sync_code: str, limit: int = 1000) -> list[dict]:
    """Get events for a sync code (across sessions/devices)."""
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM user_events WHERE sync_code = ? ORDER BY created_at DESC LIMIT ?",
        (sync_code, limit),
    )
    rows = await cursor.fetchall()
    result = []
    for row in rows:
        r = dict(row)
        try:
            r["metadata"] = json.loads(r.get("metadata", "{}"))
        except (json.JSONDecodeError, TypeError):
            r["metadata"] = {}
        result.append(r)
    return result


async def get_event_counts() -> dict:
    """Get aggregate event counts for admin dashboard."""
    db = await get_db()
    cursor = await db.execute(
        """SELECT event_type, COUNT(*) as cnt
           FROM user_events
           GROUP BY event_type
           ORDER BY cnt DESC"""
    )
    rows = await cursor.fetchall()
    return {row["event_type"]: row["cnt"] for row in rows}


# ── Session Stats (compact aggregated analytics) ───────────────────


async def save_session_stats(stats: dict) -> None:
    """Upsert aggregated session statistics."""
    db = await get_db()
    await db.execute(
        """INSERT INTO user_session_stats
           (session_id, sync_code, impressions, clicks, detail_opens,
            saves, unsaves, shares, external_clicks, holds,
            total_read_time_sec, avg_read_time_sec,
            total_scroll_depth, avg_scroll_depth,
            read_events, scroll_events, top_topics, last_seen)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
           ON CONFLICT(session_id) DO UPDATE SET
             sync_code = CASE WHEN ? != '' THEN ? ELSE sync_code END,
             impressions = ?, clicks = ?, detail_opens = ?,
             saves = ?, unsaves = ?, shares = ?, external_clicks = ?, holds = ?,
             total_read_time_sec = ?, avg_read_time_sec = ?,
             total_scroll_depth = ?, avg_scroll_depth = ?,
             read_events = ?, scroll_events = ?,
             top_topics = ?, last_seen = datetime('now')""",
        (
            stats["session_id"], stats.get("sync_code", ""),
            stats.get("impressions", 0), stats.get("clicks", 0), stats.get("detail_opens", 0),
            stats.get("saves", 0), stats.get("unsaves", 0), stats.get("shares", 0),
            stats.get("external_clicks", 0), stats.get("holds", 0),
            stats.get("total_read_time_sec", 0), stats.get("avg_read_time_sec", 0),
            stats.get("total_scroll_depth", 0), stats.get("avg_scroll_depth", 0),
            stats.get("read_events", 0), stats.get("scroll_events", 0),
            json.dumps(stats.get("top_topics", {})),
            # ON CONFLICT params:
            stats.get("sync_code", ""), stats.get("sync_code", ""),
            stats.get("impressions", 0), stats.get("clicks", 0), stats.get("detail_opens", 0),
            stats.get("saves", 0), stats.get("unsaves", 0), stats.get("shares", 0),
            stats.get("external_clicks", 0), stats.get("holds", 0),
            stats.get("total_read_time_sec", 0), stats.get("avg_read_time_sec", 0),
            stats.get("total_scroll_depth", 0), stats.get("avg_scroll_depth", 0),
            stats.get("read_events", 0), stats.get("scroll_events", 0),
            json.dumps(stats.get("top_topics", {})),
        ),
    )
    await db.commit()


async def get_all_session_stats() -> list[dict]:
    """Get all session stats, ordered by most recent."""
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM user_session_stats ORDER BY last_seen DESC"
    )
    rows = await cursor.fetchall()
    result = []
    for row in rows:
        r = dict(row)
        try:
            r["top_topics"] = json.loads(r.get("top_topics", "{}"))
        except (json.JSONDecodeError, TypeError):
            r["top_topics"] = {}
        result.append(r)
    return result


async def get_session_stats_by_sync_code(sync_code: str) -> list[dict]:
    """Get session stats for a specific sync code."""
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM user_session_stats WHERE sync_code = ? ORDER BY last_seen DESC",
        (sync_code,),
    )
    rows = await cursor.fetchall()
    result = []
    for row in rows:
        r = dict(row)
        try:
            r["top_topics"] = json.loads(r.get("top_topics", "{}"))
        except (json.JSONDecodeError, TypeError):
            r["top_topics"] = {}
        result.append(r)
    return result


async def get_analytics_overview() -> dict:
    """Get a full analytics overview for the admin dashboard."""
    db = await get_db()

    # Total events
    c = await db.execute("SELECT COUNT(*) as cnt FROM user_events")
    r = await c.fetchone()
    total_events = r["cnt"] if r else 0

    # Event type breakdown
    c = await db.execute(
        "SELECT event_type, COUNT(*) as cnt FROM user_events GROUP BY event_type ORDER BY cnt DESC"
    )
    event_breakdown = {row["event_type"]: row["cnt"] for row in await c.fetchall()}

    # Unique sessions
    c = await db.execute("SELECT COUNT(DISTINCT session_id) as cnt FROM user_events")
    r = await c.fetchone()
    unique_sessions = r["cnt"] if r else 0

    # Unique sync codes
    c = await db.execute(
        "SELECT COUNT(DISTINCT sync_code) as cnt FROM user_events WHERE sync_code != ''"
    )
    r = await c.fetchone()
    unique_sync_codes = r["cnt"] if r else 0

    # Total profiles
    c = await db.execute("SELECT COUNT(*) as cnt FROM profiles")
    r = await c.fetchone()
    total_profiles = r["cnt"] if r else 0

    # Top topics by event count
    c = await db.execute(
        """SELECT topic, COUNT(*) as cnt FROM user_events
           WHERE topic != '' GROUP BY topic ORDER BY cnt DESC LIMIT 10"""
    )
    top_topics = {row["topic"]: row["cnt"] for row in await c.fetchall()}

    # Session stats summary
    c = await db.execute("SELECT COUNT(*) as cnt FROM user_session_stats")
    r = await c.fetchone()
    total_session_stats = r["cnt"] if r else 0

    # Events per day (last 7 days)
    c = await db.execute(
        """SELECT DATE(created_at) as day, COUNT(*) as cnt
           FROM user_events
           WHERE created_at >= datetime('now', '-7 days')
           GROUP BY DATE(created_at)
           ORDER BY day DESC"""
    )
    daily_events = {row["day"]: row["cnt"] for row in await c.fetchall()}

    # User Retention
    c = await db.execute(
        "SELECT sync_code, COUNT(*) as sessions, MAX(last_seen) as last_seen, SUM(total_read_time_sec) as total_read_time FROM user_session_stats WHERE sync_code != '' GROUP BY sync_code ORDER BY sessions DESC"
    )
    user_retention = [dict(row) for row in await c.fetchall()]

    return {
        "total_events": total_events,
        "event_breakdown": event_breakdown,
        "unique_sessions": unique_sessions,
        "unique_sync_codes": unique_sync_codes,
        "total_profiles": total_profiles,
        "top_topics": top_topics,
        "total_session_stats": total_session_stats,
        "daily_events": daily_events,
        "user_retention": user_retention,
    }


async def get_daily_leaderboard(limit: int = 3) -> list[dict]:
    """Get top readers for the current day (UTC) based on total read time."""
    db = await get_db()
    cursor = await db.execute(
        """SELECT sync_code, SUM(total_read_time_sec) as read_time_sec, COUNT(*) as sessions 
           FROM user_session_stats 
           WHERE DATE(last_seen) = DATE('now')
             AND sync_code != ''
           GROUP BY sync_code 
           ORDER BY read_time_sec DESC 
           LIMIT ?""",
        (limit,)
    )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def prune_old_events(days: int = 7) -> int:
    """Delete raw events older than N days. Returns count of deleted rows."""
    db = await get_db()
    cursor = await db.execute(
        "DELETE FROM user_events WHERE created_at < datetime('now', ?)",
        (f"-{days} days",),
    )
    await db.commit()
    deleted = cursor.rowcount
    if deleted > 0:
        logger.info(f"Pruned {deleted} raw events older than {days} days")
    return deleted


# ── User Topic Scores ──────────────────────────────────────────────


async def save_topic_scores(
    session_id: str, sync_code: str, scores: dict[str, float], event_counts: dict[str, int]
) -> None:
    """Upsert topic scores for a session."""
    db = await get_db()
    for topic, score in scores.items():
        count = event_counts.get(topic, 0)
        await db.execute(
            """INSERT INTO user_topic_scores (session_id, sync_code, topic, score, event_count, updated_at)
               VALUES (?, ?, ?, ?, ?, datetime('now'))
               ON CONFLICT(session_id, topic) DO UPDATE SET
                 score = ?, event_count = ?, sync_code = ?, updated_at = datetime('now')""",
            (session_id, sync_code, topic, score, count, score, count, sync_code),
        )
    await db.commit()


async def get_topic_scores(session_id: str) -> dict[str, float]:
    """Get topic scores for a session."""
    db = await get_db()
    cursor = await db.execute(
        "SELECT topic, score FROM user_topic_scores WHERE session_id = ? ORDER BY score DESC",
        (session_id,),
    )
    rows = await cursor.fetchall()
    return {row["topic"]: float(row["score"]) for row in rows}


async def get_topic_scores_by_sync_code(sync_code: str) -> dict[str, float]:
    """Get aggregated topic scores across all sessions for a sync code."""
    db = await get_db()
    cursor = await db.execute(
        """SELECT topic, SUM(score) as total_score
           FROM user_topic_scores
           WHERE sync_code = ?
           GROUP BY topic
           ORDER BY total_score DESC""",
        (sync_code,),
    )
    rows = await cursor.fetchall()
    return {row["topic"]: float(row["total_score"]) for row in rows}


async def get_all_events() -> list[dict]:
    db = await get_db()
    cursor = await db.execute("SELECT * FROM user_events ORDER BY created_at ASC")
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def get_all_topic_scores() -> list[dict]:
    db = await get_db()
    cursor = await db.execute("SELECT * FROM user_topic_scores")
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


# ── RSS Feeds (Admin) ──────────────────────────────────────────────


async def save_rss_feed(
    country_code: str, feed_key: str, query: str, is_active: bool = True
) -> None:
    """Upsert an RSS feed configuration."""
    db = await get_db()
    await db.execute(
        """INSERT INTO rss_feeds (country_code, feed_key, query, is_active, updated_at)
           VALUES (?, ?, ?, ?, datetime('now'))
           ON CONFLICT(country_code, feed_key) DO UPDATE SET
             query = ?, is_active = ?, updated_at = datetime('now')""",
        (country_code, feed_key, query, 1 if is_active else 0, query, 1 if is_active else 0),
    )
    await db.commit()


async def get_rss_feeds(country_code: str | None = None) -> list[dict]:
    """Get RSS feed configurations, optionally filtered by country."""
    db = await get_db()
    if country_code:
        cursor = await db.execute(
            "SELECT * FROM rss_feeds WHERE country_code = ? ORDER BY feed_key",
            (country_code,),
        )
    else:
        cursor = await db.execute("SELECT * FROM rss_feeds ORDER BY country_code, feed_key")
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def delete_rss_feed(country_code: str, feed_key: str) -> bool:
    """Delete an RSS feed configuration."""
    db = await get_db()
    cursor = await db.execute(
        "DELETE FROM rss_feeds WHERE country_code = ? AND feed_key = ?",
        (country_code, feed_key),
    )
    await db.commit()
    return cursor.rowcount > 0


async def store_user_daily_digest(
    sync_code: str, target_date: str, synthesis: str, custom_hooks: dict
) -> None:
    """Store a personalized daily digest payload."""
    import json

    db = await get_db()
    # Replace existing or insert new
    await db.execute(
        """INSERT OR REPLACE INTO user_daily_digests 
           (sync_code, target_date, synthesis, custom_hooks, created_at) 
           VALUES (?, ?, ?, ?, datetime('now'))""",
        (sync_code, target_date, synthesis, json.dumps(custom_hooks)),
    )
    await db.commit()


async def get_user_daily_digest(sync_code: str, target_date: str) -> dict | None:
    """Retrieve a personalized daily digest payload."""
    import json

    db = await get_db()
    cursor = await db.execute(
        "SELECT synthesis, custom_hooks FROM user_daily_digests WHERE sync_code = ? AND target_date = ?",
        (sync_code, target_date),
    )
    row = await cursor.fetchone()
    if row:
        return {"synthesis": row["synthesis"], "custom_hooks": json.loads(row["custom_hooks"])}
    return None
