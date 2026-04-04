"""
DailyAI News application entrypoint.
Routes and app wiring are kept here; business logic is split into services/*.
"""

import asyncio
import logging
import os
import re
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
from fastapi import FastAPI, Header, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from services.config import APP_VERSION, COUNTRIES, DEPLOYED_AT, SUPPORTED_LANGUAGES, TOPICS
from services.config import normalize_language, store_key
from services.models import (
    ArticleBriefRequest, CreateProfileRequest, RecordAnalyticsRequest,
    RecordSignalRequest, SubscribeRequest, UpdateProfileRequest,
)
from services.news_core import agent, get_articles_payload, get_news_payload, refresh_all, refresh_news
from services.profiles import create_profile, get_profile, record_analytics, record_signal, update_preferences
from services.security import ensure_csrf_cookie, register_security_middleware
from services.store import NEWS_STORE, get_daily_thought, load_subscribers, save_subscribers

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("dailyai")

EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    from services.database import is_supabase_configured, sync_all_to_supabase

    scheduler.add_job(refresh_all, "interval", hours=1, id="hourly_refresh", replace_existing=True)

    # Supabase cloud sync — every 5 minutes
    if is_supabase_configured():
        scheduler.add_job(
            sync_all_to_supabase, "interval", minutes=5,
            id="supabase_sync", replace_existing=True
        )
        logger.info("Supabase sync scheduled every 5 minutes")

    if os.getenv("RESEND_API_KEY"):

        def run_digest_sync():
            from digest import send_digest

            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(send_digest())
            else:
                loop.run_until_complete(send_digest())

        scheduler.add_job(
            run_digest_sync, "cron", hour=8, minute=0, id="daily_digest", replace_existing=True
        )
        logger.info("Daily digest scheduled for 8:00 AM UTC")

    scheduler.start()
    logger.info("Scheduler started")
    asyncio.create_task(refresh_news("GLOBAL", "en"))

    yield
    scheduler.shutdown()


app = FastAPI(title="DailyAI News", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
register_security_middleware(app)


@app.head("/")
async def health_check():
    return JSONResponse(content={}, status_code=200)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    response = templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "request": request,
            "countries": COUNTRIES,
            "topics": TOPICS,
            "app_version": APP_VERSION,
        },
    )
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    ensure_csrf_cookie(request, response)
    return response


@app.get("/api/version")
async def get_app_version():
    return {"version": APP_VERSION, "deployed_at": DEPLOYED_AT}


@app.get("/api/news/{country_code}")
async def get_news(country_code: str, language: str = "en"):
    status, payload = await get_news_payload(country_code, language)
    if status != 200:
        return JSONResponse(payload, status_code=status)
    return payload


@app.get("/api/thought")
async def get_thought():
    return get_daily_thought()


@app.get("/api/countries")
async def get_countries():
    return {"countries": COUNTRIES}


@app.get("/api/languages")
async def get_languages():
    return {"languages": SUPPORTED_LANGUAGES}


@app.get("/api/articles")
async def get_articles(topic: str = "all", country: str = "GLOBAL",
                       language: str = "en", sync_code: str = "",
                       offset: int = 0, limit: int = 15):
    payload = await get_articles_payload(
        topic=topic,
        country=country,
        language=language,
        sync_code=sync_code,
        offset=max(0, offset),
        limit=max(1, min(limit, 30)),
    )
    payload["language_name"] = SUPPORTED_LANGUAGES.get(payload["language"], "English")
    return payload


@app.post("/api/articles/brief")
async def get_article_brief(req: ArticleBriefRequest):
    language = normalize_language(req.language)
    brief = await agent.generate_topic_brief(
        title=req.title,
        source=req.source,
        link=req.link,
        summary=req.summary,
        why_it_matters=req.why_it_matters,
        topic=req.topic,
        language_code=language,
    )
    return {"brief": brief, "language": language}


@app.post("/api/refresh/{country_code}")
async def force_refresh(country_code: str, language: str = "en"):
    country_code = country_code.upper()
    language = normalize_language(language)
    if country_code not in COUNTRIES:
        return JSONResponse({"error": "Unknown country code"}, status_code=400)
    await refresh_news(country_code, language)
    key = store_key(country_code, language)
    return {"status": "ok", "tiles_count": len(NEWS_STORE.get(key, []))}


@app.post("/api/subscribe")
async def subscribe(req: SubscribeRequest):
    from services.database import is_supabase_configured, sync_subscriber_to_supabase

    email = req.email.strip().lower()
    language = normalize_language(req.language)
    country = (req.country or "GLOBAL").upper()
    if country not in COUNTRIES:
        country = "GLOBAL"

    if not EMAIL_RE.match(email):
        return JSONResponse({"error": "Invalid email address"}, status_code=400)

    subs = load_subscribers()
    now_iso = datetime.now(UTC).isoformat()

    for subscriber in subs:
        if subscriber["email"] == email:
            subscriber["topics"] = req.topics
            subscriber["country"] = country
            subscriber["language"] = language
            subscriber["updated_at"] = now_iso
            save_subscribers(subs)
            if is_supabase_configured():
                asyncio.create_task(sync_subscriber_to_supabase(subscriber))
            return {"status": "updated", "message": "Preferences updated!"}

    subs.append(
        {
            "email": email,
            "topics": req.topics,
            "country": country,
            "language": language,
            "subscribed_at": now_iso,
            "updated_at": now_iso,
        }
    )
    save_subscribers(subs)
    if is_supabase_configured():
        asyncio.create_task(sync_subscriber_to_supabase(subs[-1]))
    logger.info(f"New subscriber: {email} (topics: {req.topics})")

    preferred_key = store_key(country, language)
    global_key = store_key("GLOBAL", language)
    fallback_key = store_key("GLOBAL", "en")

    tiles = NEWS_STORE.get(preferred_key, [])
    if not tiles:
        await refresh_news(country, language)
        tiles = NEWS_STORE.get(preferred_key, [])
    if not tiles:
        await refresh_news("GLOBAL", language)
        tiles = NEWS_STORE.get(global_key, [])
    if not tiles and language != "en":
        await refresh_news("GLOBAL", "en")
        tiles = NEWS_STORE.get(fallback_key, [])

    if tiles:
        from digest import send_welcome_email

        asyncio.create_task(send_welcome_email(email, tiles[:10]))

    return {
        "status": "subscribed",
        "message": "You're in! Check your inbox for today's top AI stories.",
    }


@app.get("/api/subscribers/count")
async def subscriber_count():
    return {"count": len(load_subscribers())}


# ── Profile (anonymous recommendation) routes ──────────────────────
@app.post("/api/profile/new")
async def create_new_profile(req: CreateProfileRequest):
    from services.database import is_supabase_configured, sync_profile_to_supabase

    profile = create_profile(
        preferred_topics=req.preferred_topics,
        country=req.country,
        language=req.language,
    )
    if is_supabase_configured():
        asyncio.create_task(sync_profile_to_supabase(profile))
    return {"status": "created", "profile": profile}


@app.get("/api/profile/{sync_code}")
async def fetch_profile(sync_code: str):
    profile = get_profile(sync_code)
    if not profile:
        return JSONResponse({"error": "Profile not found"}, status_code=404)
    return {"profile": profile}


@app.put("/api/profile/{sync_code}")
async def update_profile(sync_code: str, req: UpdateProfileRequest):
    from services.database import is_supabase_configured, sync_profile_to_supabase

    profile = update_preferences(
        sync_code=sync_code,
        preferred_topics=req.preferred_topics,
        country=req.country,
        language=req.language,
        bookmarks=req.bookmarks,
    )
    if not profile:
        return JSONResponse({"error": "Profile not found"}, status_code=404)
    if is_supabase_configured():
        asyncio.create_task(sync_profile_to_supabase(profile))
    return {"status": "updated", "profile": profile}


@app.post("/api/profile/{sync_code}/signal")
async def profile_signal(sync_code: str, req: RecordSignalRequest):
    from services.database import is_supabase_configured, sync_profile_to_supabase

    profile = record_signal(sync_code=sync_code, topic=req.topic, action=req.action)
    if not profile:
        return JSONResponse({"error": "Profile not found or invalid signal"}, status_code=400)
    if is_supabase_configured():
        asyncio.create_task(sync_profile_to_supabase(profile))
    return {"status": "recorded"}


@app.post("/api/profile/{sync_code}/analytics")
async def profile_analytics(sync_code: str, req: RecordAnalyticsRequest):
    from services.database import is_supabase_configured, sync_profile_to_supabase

    result = record_analytics(
        sync_code=sync_code,
        stats=req.dict() if hasattr(req, 'dict') else req.model_dump(),
    )
    if not result:
        return JSONResponse({"error": "Profile not found"}, status_code=404)
    if is_supabase_configured():
        profile = get_profile(sync_code)
        if profile:
            asyncio.create_task(sync_profile_to_supabase(profile))
    return {"status": "recorded", "analytics": result}


@app.get("/api/digest/preview", response_class=HTMLResponse)
async def digest_preview():
    from digest import generate_digest_html

    tiles = NEWS_STORE.get(store_key("GLOBAL", "en"), [])
    if not tiles:
        return HTMLResponse("<p>No news available yet. Check back later.</p>")
    return HTMLResponse(generate_digest_html(tiles[:10]))


# ── Legal pages (required for German market) ───────────────────────
@app.get("/impressum", response_class=HTMLResponse)
async def impressum(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="impressum.html",
        context={"request": request, "app_version": APP_VERSION},
    )


@app.get("/datenschutz", response_class=HTMLResponse)
async def datenschutz(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="datenschutz.html",
        context={"request": request, "app_version": APP_VERSION},
    )


@app.get("/terms", response_class=HTMLResponse)
async def terms(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="terms.html",
        context={"request": request, "app_version": APP_VERSION},
    )


# ══════════════════════════════════════════════════════════════════════
# Developer API v1 — Public REST API with API key authentication
# ══════════════════════════════════════════════════════════════════════

@app.post("/api/v1/keys")
async def create_key(request: Request):
    """Create a new API key (free tier by default)."""
    from services.api_keys import create_api_key

    body = await request.json()
    name = str(body.get("name", "My App"))[:100]
    email = str(body.get("email", ""))[:200]

    if not email or "@" not in email:
        return JSONResponse({"error": "Valid email required"}, status_code=400)

    result = create_api_key(name=name, email=email, tier="free")
    return result


@app.get("/api/v1/keys/stats")
async def key_stats(x_api_key: str = Header(None)):
    """Get usage stats for your API key."""
    from services.api_keys import get_api_key_stats

    if not x_api_key:
        return JSONResponse({"error": "X-API-Key header required"}, status_code=401)

    stats = get_api_key_stats(x_api_key)
    if not stats:
        return JSONResponse({"error": "Invalid API key"}, status_code=401)
    return stats


def _validate_v1_key(api_key: str | None) -> tuple[dict | None, JSONResponse | None]:
    """Validate API key and check rate limit. Returns (record, error_response)."""
    from services.api_keys import check_rate_limit, validate_api_key

    if not api_key:
        return None, JSONResponse(
            {"error": "Missing X-API-Key header. Get a free key at https://www.dailyai.site/api/docs"},
            status_code=401,
        )

    record = validate_api_key(api_key)
    if not record:
        return None, JSONResponse({"error": "Invalid or deactivated API key"}, status_code=401)

    tier = record.get("tier", "free")
    key_hash = record.get("key_hash", "")
    allowed, remaining, limit = check_rate_limit(key_hash, tier)

    if not allowed:
        resp = JSONResponse(
            {"error": "Rate limit exceeded", "limit": limit, "reset": "rolling 24h"},
            status_code=429,
        )
        resp.headers["X-RateLimit-Limit"] = str(limit)
        resp.headers["X-RateLimit-Remaining"] = "0"
        resp.headers["Retry-After"] = "3600"
        return None, resp

    return record, None


@app.get("/api/v1/feed")
async def api_v1_feed(
    topic: str = "all",
    country: str = "GLOBAL",
    language: str = "en",
    offset: int = 0,
    limit: int = 15,
    x_api_key: str = Header(None),
):
    """Public Developer API — Get curated AI news feed.

    Requires X-API-Key header. Get a free key at https://www.dailyai.site
    """
    from services.api_keys import filter_fields_for_tier

    record, error = _validate_v1_key(x_api_key)
    if error:
        return error

    tier = record.get("tier", "free")
    payload = await get_articles_payload(
        topic=topic,
        country=country.upper(),
        language=normalize_language(language),
        offset=max(0, offset),
        limit=max(1, min(limit, 30)),
    )

    # Filter fields based on tier
    filtered_articles = [
        filter_fields_for_tier(a, tier) for a in payload.get("articles", [])
    ]

    return {
        "articles": filtered_articles,
        "total": payload.get("total", 0),
        "offset": payload.get("offset", 0),
        "limit": payload.get("limit", 15),
        "has_more": payload.get("has_more", False),
        "country": payload.get("country", "GLOBAL"),
        "language": payload.get("language", "en"),
        "api_version": "v1",
        "tier": tier,
    }


@app.get("/api/v1/trending")
async def api_v1_trending(
    country: str = "GLOBAL",
    language: str = "en",
    x_api_key: str = Header(None),
):
    """Public Developer API — Get trending story threads.

    Groups articles by story thread and returns top threads by coverage.
    """
    record, error = _validate_v1_key(x_api_key)
    if error:
        return error

    language = normalize_language(language)
    country = country.upper()
    key = store_key(country, language)

    if key not in NEWS_STORE:
        await refresh_news(country, language)

    tiles = list(NEWS_STORE.get(key, []))

    # Group by story_thread
    threads: dict[str, dict] = {}
    for t in tiles:
        thread_name = str(t.get("story_thread", "")).strip()
        if not thread_name:
            continue
        thread_key = thread_name.lower()
        if thread_key not in threads:
            threads[thread_key] = {
                "thread": thread_name,
                "articles_count": 0,
                "sources": [],
                "top_headline": t.get("title", ""),
                "sentiment": t.get("sentiment", "neutral"),
                "max_importance": 0,
                "latest_published": "",
            }
        entry = threads[thread_key]
        entry["articles_count"] += 1
        src = t.get("source", "")
        if src and src not in entry["sources"]:
            entry["sources"].append(src)
        imp = int(t.get("importance", 5) or 5)
        if imp > entry["max_importance"]:
            entry["max_importance"] = imp
            entry["top_headline"] = t.get("title", "")
        pub = str(t.get("published", ""))
        if pub > entry["latest_published"]:
            entry["latest_published"] = pub

    # Sort by coverage (article count * max importance)
    sorted_threads = sorted(
        threads.values(),
        key=lambda x: x["articles_count"] * x["max_importance"],
        reverse=True,
    )

    return {
        "threads": sorted_threads[:20],
        "total": len(sorted_threads),
        "country": country,
        "language": language,
        "api_version": "v1",
    }


@app.get("/api/v1/sources")
async def api_v1_sources(x_api_key: str = Header(None)):
    """Public Developer API — Get source trust database."""
    record, error = _validate_v1_key(x_api_key)
    if error:
        return error

    # Build source trust database from agent's source lists
    from services.news_core import agent as news_agent

    sources = []
    for src in sorted(news_agent.high_trust_sources):
        sources.append({"name": src.title(), "trust_tier": "high"})
    for src in sorted(news_agent.medium_trust_sources):
        sources.append({"name": src.title(), "trust_tier": "medium"})

    return {
        "sources": sources,
        "total": len(sources),
        "api_version": "v1",
    }


# ── API Documentation page ─────────────────────────────────────────
@app.get("/api/docs/guide", response_class=HTMLResponse)
async def api_docs_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="api_docs.html",
        context={"request": request, "app_version": APP_VERSION},
    )
