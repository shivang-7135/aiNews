"""
Supabase cloud database integration.
Uses httpx to call Supabase PostgREST API — no extra dependencies needed.

Requires SUPABASE_URL and SUPABASE_KEY in .env.
Falls back to JSON files if not configured.
"""

import json
import logging
import os
from typing import Any

import httpx

logger = logging.getLogger("dailyai.database")

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")


def is_supabase_configured() -> bool:
    """Check if Supabase credentials are set."""
    return bool(SUPABASE_URL and SUPABASE_KEY)


def _headers() -> dict[str, str]:
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def _url(table: str) -> str:
    return f"{SUPABASE_URL}/rest/v1/{table}"


# ── Generic CRUD ─────────────────────────────────────────────────────

async def db_select(table: str, params: dict | None = None) -> list[dict]:
    """SELECT rows from a Supabase table."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(_url(table), headers=_headers(), params=params or {})
            if resp.status_code == 200:
                return resp.json()
            logger.warning(f"[DB] SELECT {table} → {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        logger.warning(f"[DB] SELECT {table} failed: {e}")
    return []


async def db_insert(table: str, data: dict | list[dict]) -> list[dict]:
    """INSERT row(s) into a Supabase table."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(_url(table), headers=_headers(), json=data)
            if resp.status_code in (200, 201):
                return resp.json()
            logger.warning(f"[DB] INSERT {table} → {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        logger.warning(f"[DB] INSERT {table} failed: {e}")
    return []


async def db_upsert(table: str, data: dict) -> list[dict]:
    """UPSERT (insert or update) a row in a Supabase table."""
    try:
        headers = _headers()
        headers["Prefer"] = "return=representation,resolution=merge-duplicates"
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(_url(table), headers=headers, json=data)
            if resp.status_code in (200, 201):
                return resp.json()
            logger.warning(f"[DB] UPSERT {table} → {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        logger.warning(f"[DB] UPSERT {table} failed: {e}")
    return []


async def db_update(table: str, match_params: dict, data: dict) -> list[dict]:
    """UPDATE rows matching filter in a Supabase table."""
    try:
        params = {f"{k}": f"eq.{v}" for k, v in match_params.items()}
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.patch(
                _url(table), headers=_headers(), json=data, params=params
            )
            if resp.status_code == 200:
                return resp.json()
            logger.warning(f"[DB] UPDATE {table} → {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        logger.warning(f"[DB] UPDATE {table} failed: {e}")
    return []


async def db_delete(table: str, match_params: dict) -> bool:
    """DELETE rows matching filter in a Supabase table."""
    try:
        params = {f"{k}": f"eq.{v}" for k, v in match_params.items()}
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.delete(_url(table), headers=_headers(), params=params)
            if resp.status_code in (200, 204):
                return True
            logger.warning(f"[DB] DELETE {table} → {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        logger.warning(f"[DB] DELETE {table} failed: {e}")
    return False


# ── Profiles ─────────────────────────────────────────────────────────

async def db_get_profile(sync_code: str) -> dict | None:
    """Get profile by sync_code from Supabase."""
    rows = await db_select("profiles", {"sync_code": f"eq.{sync_code}", "select": "*"})
    return rows[0] if rows else None


async def db_create_profile(profile: dict) -> dict | None:
    """Create a new profile in Supabase."""
    result = await db_insert("profiles", profile)
    return result[0] if result else None


async def db_update_profile(sync_code: str, updates: dict) -> dict | None:
    """Update a profile in Supabase."""
    result = await db_update("profiles", {"sync_code": sync_code}, updates)
    return result[0] if result else None


# ── Analytics Events ─────────────────────────────────────────────────

async def db_record_analytics_event(event: dict) -> dict | None:
    """Insert an analytics event."""
    result = await db_insert("analytics_events", event)
    return result[0] if result else None


async def db_record_analytics_batch(events: list[dict]) -> list[dict]:
    """Insert multiple analytics events."""
    return await db_insert("analytics_events", events)


# ── Subscribers ──────────────────────────────────────────────────────

async def db_get_subscribers() -> list[dict]:
    """Get all active subscribers."""
    return await db_select("subscribers", {"is_active": "eq.true", "select": "*"})


async def db_add_subscriber(subscriber: dict) -> dict | None:
    """Add a new subscriber."""
    result = await db_upsert("subscribers", subscriber)
    return result[0] if result else None


# ── SQL Schema for Supabase Dashboard ────────────────────────────────

SCHEMA_SQL = """
-- Run this in Supabase SQL Editor (Dashboard → SQL Editor → New Query)

-- Profiles table (replaces profiles.json)
CREATE TABLE IF NOT EXISTS profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sync_code VARCHAR(30) UNIQUE NOT NULL,
    preferred_topics JSONB DEFAULT '[]',
    country VARCHAR(10) DEFAULT 'GLOBAL',
    language VARCHAR(5) DEFAULT 'en',
    signals JSONB DEFAULT '{}',
    bookmarks JSONB DEFAULT '[]',
    analytics JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now(),
    last_active TIMESTAMPTZ DEFAULT now()
);

-- Analytics events table (granular tracking)
CREATE TABLE IF NOT EXISTS analytics_events (
    id BIGSERIAL PRIMARY KEY,
    sync_code VARCHAR(30) REFERENCES profiles(sync_code),
    event_type VARCHAR(30) NOT NULL,
    article_id VARCHAR(255),
    topic VARCHAR(50),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Subscribers table (replaces subscribers.json)
CREATE TABLE IF NOT EXISTS subscribers (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    topics JSONB DEFAULT '[]',
    country VARCHAR(10) DEFAULT 'GLOBAL',
    language VARCHAR(5) DEFAULT 'en',
    subscribed_at TIMESTAMPTZ DEFAULT now(),
    is_active BOOLEAN DEFAULT true
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_profiles_sync_code ON profiles(sync_code);
CREATE INDEX IF NOT EXISTS idx_events_sync_code ON analytics_events(sync_code);
CREATE INDEX IF NOT EXISTS idx_events_type ON analytics_events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_created ON analytics_events(created_at);
CREATE INDEX IF NOT EXISTS idx_subscribers_email ON subscribers(email);

-- Enable Row Level Security (RLS)
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE analytics_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscribers ENABLE ROW LEVEL SECURITY;

-- Allow all operations via service key (anon key for now)
CREATE POLICY "Allow all for anon" ON profiles FOR ALL USING (true);
CREATE POLICY "Allow all for anon" ON analytics_events FOR ALL USING (true);
CREATE POLICY "Allow all for anon" ON subscribers FOR ALL USING (true);
"""
