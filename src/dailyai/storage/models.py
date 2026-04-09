"""
DailyAI — Pydantic Models
Structured data models for the entire application.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── News Article ────────────────────────────────────────────────────

class NewsArticle(BaseModel):
    """A curated news article after full pipeline processing."""

    title: str = Field(max_length=200)
    summary: str = Field(default="", max_length=500)
    why_it_matters: str = Field(default="", max_length=300)
    category: str = Field(default="general")
    topic: str = Field(default="general")
    importance: int = Field(default=5, ge=1, le=10)
    source: str = Field(default="")
    source_trust: str = Field(default="low")  # high | medium | low
    sentiment: str = Field(default="neutral")  # bullish | bearish | neutral
    story_thread: str = Field(default="", max_length=80)
    link: str = Field(default="")
    published: str = Field(default="")
    fetched_at: str = Field(default="")


class RawArticle(BaseModel):
    """An article as fetched from RSS before any processing."""

    title: str
    link: str = ""
    source: str = ""
    published: str = ""


# ── User Profile ───────────────────────────────────────────────────

class UserProfile(BaseModel):
    """Anonymous user profile with preferences and interaction signals."""

    sync_code: str
    preferred_topics: list[str] = Field(default_factory=list, max_length=8)
    country: str = "GLOBAL"
    language: str = "en"
    signals: dict[str, float] = Field(default_factory=dict)
    bookmarks: list[str] = Field(default_factory=list)
    analytics: dict[str, int] = Field(default_factory=dict)
    created_at: str = ""
    last_active: str = ""


# ── Subscriber ──────────────────────────────────────────────────────

class Subscriber(BaseModel):
    """Email digest subscriber."""

    email: str
    topics: list[str] = Field(default_factory=list)
    country: str = "GLOBAL"
    language: str = "en"
    subscribed_at: str = ""
    updated_at: str = ""
    is_active: bool = True


# ── API Key ─────────────────────────────────────────────────────────

class APIKeyRecord(BaseModel):
    """Developer API key record."""

    key_hash: str
    name: str
    email: str
    tier: str = "free"  # free | pro | enterprise
    created_at: str = ""
    is_active: bool = True
    requests_today: int = 0


# ── API Request / Response Models ───────────────────────────────────

class SubscribeRequest(BaseModel):
    email: str
    topics: list[str] = Field(default_factory=list)
    country: str = "GLOBAL"
    language: str = "en"


class CreateProfileRequest(BaseModel):
    preferred_topics: list[str] = Field(default_factory=list)
    country: str = "GLOBAL"
    language: str = "en"


class UpdateProfileRequest(BaseModel):
    preferred_topics: Optional[list[str]] = None
    country: Optional[str] = None
    language: Optional[str] = None
    bookmarks: Optional[list[str]] = None


class RecordSignalRequest(BaseModel):
    topic: str
    action: str  # tap | save | skip | unsave


class RecordAnalyticsRequest(BaseModel):
    taps: int = 0
    saves: int = 0
    reads: int = 0
    skips: int = 0
    briefs_opened: int = 0
    time_spent_seconds: int = 0
    session_count: int = 0


class ArticleBriefRequest(BaseModel):
    title: str
    source: str = ""
    link: str = ""
    summary: str = ""
    why_it_matters: str = ""
    topic: str = "general"
    language: str = "en"


# ── Feed Response ───────────────────────────────────────────────────

class FeedArticle(BaseModel):
    """Article formatted for the UI feed."""

    id: str
    headline: str
    summary: str = ""
    why_it_matters: str = ""
    importance: int = 5
    category: str = "general"
    topic: str = "Top Stories"
    source_name: str = "Unknown"
    source_trust: str = "low"
    sentiment: str = "neutral"
    story_thread: str = ""
    thread_count: int = 0
    article_url: str = "#"
    published_at: str = ""
    updated_at: str = ""


# ── Analytics ──────────────────────────────────────────────────────

class AnalyticsEvent(BaseModel):
    """A single user interaction event."""
    event_type: str  # impression | click | hold | detail_open | read_time | scroll_depth | share | save | unsave | external_click | skip
    article_id: str = ""
    topic: str = ""
    category: str = ""
    value: float = 0  # seconds for read_time, percentage for scroll_depth
    metadata: dict = Field(default_factory=dict)


class BatchEventsRequest(BaseModel):
    """Batch of analytics events from the client."""
    session_id: str
    sync_code: str = ""
    events: list[AnalyticsEvent] = Field(default_factory=list, max_length=100)


# ── Admin ──────────────────────────────────────────────────────────

class AdminRSSFeedRequest(BaseModel):
    """Create or update an RSS feed configuration."""
    country_code: str
    feed_key: str
    query: str
    is_active: bool = True


class AdminDeleteRSSFeedRequest(BaseModel):
    """Delete an RSS feed configuration."""
    country_code: str
    feed_key: str
