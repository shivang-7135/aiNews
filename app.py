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
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from services.config import APP_VERSION, COUNTRIES, DEPLOYED_AT, SUPPORTED_LANGUAGES, TOPICS
from services.config import normalize_language, store_key
from services.models import ArticleBriefRequest, SubscribeRequest
from services.news_core import agent, get_articles_payload, get_news_payload, refresh_all, refresh_news
from services.security import ensure_csrf_cookie, register_security_middleware
from services.store import NEWS_STORE, get_daily_thought, load_subscribers, save_subscribers

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("dailyai")

EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.add_job(refresh_all, "interval", hours=1, id="hourly_refresh", replace_existing=True)

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
async def get_articles(topic: str = "all", country: str = "GLOBAL", language: str = "en"):
    payload = await get_articles_payload(topic=topic, country=country, language=language)
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


@app.get("/api/digest/preview", response_class=HTMLResponse)
async def digest_preview():
    from digest import generate_digest_html

    tiles = NEWS_STORE.get(store_key("GLOBAL", "en"), [])
    if not tiles:
        return HTMLResponse("<p>No news available yet. Check back later.</p>")
    return HTMLResponse(generate_digest_html(tiles[:10]))
