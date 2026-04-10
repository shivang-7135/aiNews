"""
DailyAI — REST API Routes
Developer API v1 endpoints + internal API for the NiceGUI frontend.
"""

import hashlib
import logging
import re
from datetime import UTC, datetime

from fastapi import APIRouter, Header, Response
from fastapi.responses import JSONResponse, StreamingResponse

from dailyai.config import (
    APP_VERSION,
    COUNTRIES,
    DEPLOYED_AT,
    UI_FEED_TOPICS,
    UI_LANGUAGES,
    normalize_language,
)
from dailyai.services.news import get_feed, refresh_news, stream_article_brief
from dailyai.storage.backend import backend_name
from dailyai.storage.models import (
    AdminDeleteRSSFeedRequest,
    AdminRSSFeedRequest,
    ArticleBriefRequest,
    BatchEventsRequest,
    CreateProfileRequest,
    RecordAnalyticsRequest,
    RecordSignalRequest,
    SubscribeRequest,
    UpdateProfileRequest,
)

logger = logging.getLogger("dailyai.api")
router = APIRouter()

EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


def _feed_etag(payload: dict, topic: str) -> str:
    signature = "|".join([
        str(payload.get("country", "GLOBAL")),
        str(payload.get("language", "en")),
        str(topic),
        str(payload.get("offset", 0)),
        str(payload.get("limit", 0)),
        str(payload.get("total", 0)),
        str(payload.get("last_updated", "")),
    ])
    return hashlib.sha1(signature.encode("utf-8", errors="ignore")).hexdigest()


# ── Internal API (used by NiceGUI frontend) ─────────────────────────

@router.get("/api/version")
async def get_version():
    return {
        "version": APP_VERSION,
        "deployed_at": DEPLOYED_AT,
        "storage_backend": backend_name(),
    }


@router.get("/api/news/{country_code}")
async def get_news(country_code: str, language: str = "en"):
    feed = await get_feed(country=country_code, language=language)
    return feed


@router.get("/api/articles")
async def get_articles(
    response: Response,
    topic: str = "all", country: str = "GLOBAL", language: str = "en",
    sync_code: str = "", offset: int = 0, limit: int = 15,
):
    payload = await get_feed(
        country=country, language=language, topic=topic,
        sync_code=sync_code, offset=max(0, offset), limit=max(1, min(limit, 30)),
    )
    response.headers["Cache-Control"] = "public, max-age=120"
    response.headers["ETag"] = _feed_etag(payload, topic)
    return payload


@router.get("/api/articles/categories")
async def get_article_categories(
    country: str = "GLOBAL", language: str = "en", sync_code: str = "",
):
    payload = await get_feed(
        topic="all",
        country=country,
        language=language,
        sync_code=sync_code,
        offset=0,
        limit=1,
    )
    categories = payload.get("categories") or [{"name": t, "count": 0} for t in UI_FEED_TOPICS]
    return {
        "categories": categories,
        "country": payload.get("country", country.upper()),
        "language": payload.get("language", normalize_language(language)),
        "total": int(payload.get("total", 0)),
        "last_updated": payload.get("last_updated", "-"),
    }


@router.post("/api/articles/brief")
async def article_brief(req: ArticleBriefRequest):
    return StreamingResponse(
        stream_article_brief(
            article={
                "title": req.title,
                "source": req.source,
                "link": req.link,
                "summary": req.summary,
                "why_it_matters": req.why_it_matters,
                "topic": req.topic,
            },
            language=normalize_language(req.language)
        ),
        media_type="text/plain",
    )


@router.post("/api/refresh/{country_code}")
async def force_refresh(country_code: str, language: str = "en"):
    country_code = country_code.upper()
    if country_code not in COUNTRIES:
        return JSONResponse({"error": "Unknown country code"}, status_code=400)
    await refresh_news(country_code, normalize_language(language))
    return {"status": "ok"}


@router.get("/api/countries")
async def countries():
    return {"countries": COUNTRIES}


@router.get("/api/languages")
async def languages():
    return {"languages": UI_LANGUAGES}

# ── Subscribe ───────────────────────────────────────────────────────

@router.post("/api/subscribe")
async def subscribe(req: SubscribeRequest):
    from dailyai.storage.backend import get_subscriber, save_subscriber

    email = req.email.strip().lower()
    if not EMAIL_RE.match(email):
        return JSONResponse({"error": "Invalid email address"}, status_code=400)

    existing = await get_subscriber(email)
    now = datetime.now(UTC).isoformat()

    if existing:
        existing["topics"] = req.topics
        existing["country"] = (req.country or "GLOBAL").upper()
        existing["language"] = normalize_language(req.language)
        existing["updated_at"] = now
        await save_subscriber(existing)
        return {"status": "updated", "message": "Preferences updated!"}

    await save_subscriber({
        "email": email, "topics": req.topics,
        "country": (req.country or "GLOBAL").upper(),
        "language": normalize_language(req.language),
        "subscribed_at": now, "updated_at": now, "is_active": True,
    })
    logger.info(f"New subscriber: {email}")
    return {"status": "subscribed", "message": "You're in! Check your inbox for today's top AI stories."}


@router.get("/api/subscribers/count")
async def subscriber_count():
    from dailyai.storage.backend import get_subscriber_count
    return {"count": await get_subscriber_count()}


# ── Profiles ────────────────────────────────────────────────────────

@router.post("/api/profile/new")
async def create_new_profile(req: CreateProfileRequest):
    from dailyai.services.profiles import create_profile
    profile = await create_profile(
        preferred_topics=req.preferred_topics,
        country=req.country, language=req.language,
    )
    return {"status": "created", "profile": profile}


@router.get("/api/profile/{sync_code}")
async def fetch_profile(sync_code: str):
    from dailyai.services.profiles import get_profile
    profile = await get_profile(sync_code)
    if not profile:
        return JSONResponse({"error": "Profile not found"}, status_code=404)
    return {"profile": profile}


@router.put("/api/profile/{sync_code}")
async def update_profile(sync_code: str, req: UpdateProfileRequest):
    from dailyai.services.profiles import update_preferences
    profile = await update_preferences(
        sync_code=sync_code, preferred_topics=req.preferred_topics,
        country=req.country, language=req.language, bookmarks=req.bookmarks,
    )
    if not profile:
        return JSONResponse({"error": "Profile not found"}, status_code=404)
    return {"status": "updated", "profile": profile}


@router.post("/api/profile/{sync_code}/signal")
async def profile_signal(sync_code: str, req: RecordSignalRequest):
    from dailyai.services.profiles import record_signal
    profile = await record_signal(sync_code=sync_code, topic=req.topic, action=req.action)
    if not profile:
        return JSONResponse({"error": "Profile not found or invalid signal"}, status_code=400)
    return {"status": "recorded"}


@router.post("/api/profile/{sync_code}/analytics")
async def profile_analytics(sync_code: str, req: RecordAnalyticsRequest):
    from dailyai.services.profiles import record_analytics
    result = await record_analytics(sync_code=sync_code, stats=req.model_dump())
    if not result:
        return JSONResponse({"error": "Profile not found"}, status_code=404)
    return {"status": "recorded", "analytics": result}


# ── Developer API v1 ────────────────────────────────────────────────

@router.get("/api/v1/feed")
async def api_v1_feed(
    response: Response,
    topic: str = "all", country: str = "GLOBAL", language: str = "en",
    offset: int = 0, limit: int = 15, x_api_key: str = Header(None),
):
    """Public Developer API — Get curated AI news feed."""
    # For now, open access. API key validation can be added later.
    payload = await get_feed(
        topic=topic, country=country.upper(),
        language=normalize_language(language),
        offset=max(0, offset), limit=max(1, min(limit, 30)),
    )
    payload["api_version"] = "v1"
    response.headers["Cache-Control"] = "public, max-age=120"
    response.headers["ETag"] = _feed_etag(payload, topic)
    return payload


@router.get("/api/v1/categories")
async def api_v1_categories(
    country: str = "GLOBAL",
    language: str = "en",
    x_api_key: str = Header(None),
):
    payload = await get_feed(
        topic="all",
        country=country.upper(),
        language=normalize_language(language),
        offset=0,
        limit=1,
    )
    return {
        "categories": payload.get("categories", [{"name": t, "count": 0} for t in UI_FEED_TOPICS]),
        "country": payload.get("country", country.upper()),
        "language": payload.get("language", normalize_language(language)),
        "last_updated": payload.get("last_updated", "-"),
        "api_version": "v1",
    }


@router.get("/api/v1/trending")
async def api_v1_trending(
    country: str = "GLOBAL", language: str = "en",
    x_api_key: str = Header(None),
):
    """Public Developer API — Get trending story threads."""
    feed_data = await get_feed(country=country.upper(), language=normalize_language(language), limit=30)
    articles = feed_data.get("articles", [])

    threads: dict[str, dict] = {}
    for a in articles:
        thread_name = str(a.get("story_thread", "")).strip()
        if not thread_name:
            continue
        tkey = thread_name.lower()
        if tkey not in threads:
            threads[tkey] = {
                "thread": thread_name, "articles_count": 0, "sources": [],
                "top_headline": a.get("headline", ""), "sentiment": a.get("sentiment", "neutral"),
                "max_importance": 0,
            }
        entry = threads[tkey]
        entry["articles_count"] += 1
        src = a.get("source_name", "")
        if src and src not in entry["sources"]:
            entry["sources"].append(src)
        imp = int(a.get("importance", 5))
        if imp > entry["max_importance"]:
            entry["max_importance"] = imp
            entry["top_headline"] = a.get("headline", "")

    sorted_threads = sorted(
        threads.values(),
        key=lambda x: x["articles_count"] * x["max_importance"],
        reverse=True,
    )
    return {"threads": sorted_threads[:20], "total": len(sorted_threads), "api_version": "v1"}


# ── Analytics Events API ────────────────────────────────────────────

@router.post("/api/analytics/events")
async def ingest_analytics_events(req: BatchEventsRequest):
    """Batch ingest user interaction events for personalization."""
    from dailyai.services.analytics import record_events

    if not req.session_id:
        return JSONResponse({"error": "session_id required"}, status_code=400)
    if not req.events:
        return {"recorded": 0}

    events = [e.model_dump() for e in req.events]
    count = await record_events(req.session_id, req.sync_code, events)
    return {"recorded": count}


@router.get("/api/analytics/scores/{identifier}")
async def get_personalization_scores(identifier: str):
    """Get topic preference scores for a session or sync code."""
    from dailyai.services.analytics import get_personalized_scores

    # Try as sync_code first, then session_id
    scores = await get_personalized_scores(session_id=identifier, sync_code=identifier)
    return {"identifier": identifier, "scores": scores}


# ── Admin API (Password Protected) ──────────────────────────────────

_ADMIN_PASSWORD = None

def _get_admin_password() -> str:
    global _ADMIN_PASSWORD
    if _ADMIN_PASSWORD is None:
        import os
        _ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "dailyai-admin-2026")
    return _ADMIN_PASSWORD


def _check_admin_auth(authorization: str | None) -> bool:
    if not authorization:
        return False
    expected = _get_admin_password()
    # Support both "Bearer <password>" and plain password
    token = authorization.replace("Bearer ", "").strip()
    return token == expected


@router.get("/api/admin/rss-feeds")
async def admin_get_rss_feeds(
    country_code: str | None = None,
    authorization: str | None = Header(None),
):
    if not _check_admin_auth(authorization):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    from dailyai.storage.backend import get_rss_feeds
    feeds = await get_rss_feeds(country_code)
    return {"feeds": feeds, "total": len(feeds)}


@router.post("/api/admin/rss-feeds")
async def admin_save_rss_feed(
    req: AdminRSSFeedRequest,
    authorization: str | None = Header(None),
):
    if not _check_admin_auth(authorization):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    from dailyai.storage.backend import save_rss_feed
    await save_rss_feed(req.country_code, req.feed_key, req.query, req.is_active)
    return {"status": "saved", "country_code": req.country_code, "feed_key": req.feed_key}


@router.delete("/api/admin/rss-feeds")
async def admin_delete_rss_feed(
    req: AdminDeleteRSSFeedRequest,
    authorization: str | None = Header(None),
):
    if not _check_admin_auth(authorization):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    from dailyai.storage.backend import delete_rss_feed
    deleted = await delete_rss_feed(req.country_code, req.feed_key)
    return {"status": "deleted" if deleted else "not_found"}


@router.get("/api/admin/analytics")
async def admin_analytics_overview(
    authorization: str | None = Header(None),
):
    if not _check_admin_auth(authorization):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    from dailyai.services.analytics import get_analytics_summary
    return await get_analytics_summary()


@router.get("/api/admin/cache-health")
async def admin_cache_health(
    authorization: str | None = Header(None),
):
    if not _check_admin_auth(authorization):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    from dailyai.storage.backend import get_cache_health
    return await get_cache_health()


@router.post("/api/admin/auth")
async def admin_auth(password: str = ""):
    """Simple admin auth check."""
    if password == _get_admin_password():
        return {"authenticated": True}
    return JSONResponse({"error": "Invalid password"}, status_code=401)

