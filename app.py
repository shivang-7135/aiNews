"""
DailyAI News — Agentic AI News Aggregator
A mobile-friendly app that fetches, filters, and summarizes AI news every hour
using an LLM agent with tool-calling capabilities.
"""

import asyncio
import json
import logging
import os
import re
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from agent import NewsAgent

load_dotenv()

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("dailyai")

APP_VERSION = (
    os.getenv("APP_VERSION")
    or os.getenv("SOURCE_VERSION")
    or os.getenv("GITHUB_SHA")
    or datetime.now(UTC).strftime("%Y%m%d%H%M%S")
)
DEPLOYED_AT = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")

# ---------------------------------------------------------------------------
# In-memory store  (max 24 tiles, rolling)
# ---------------------------------------------------------------------------
# key format: {COUNTRY}::{LANG}
NEWS_STORE: dict[str, list[dict]] = {}
LAST_UPDATED: dict[str, str] = {}

# Country config
COUNTRIES = {
    "US": "United States",
    "GB": "United Kingdom",
    "IN": "India",
    "DE": "Germany",
    "FR": "France",
    "CA": "Canada",
    "AU": "Australia",
    "JP": "Japan",
    "KR": "South Korea",
    "CN": "China",
    "BR": "Brazil",
    "SG": "Singapore",
    "AE": "UAE",
    "IL": "Israel",
    "GLOBAL": "Global / Worldwide",
}

SUPPORTED_LANGUAGES = {
    "en": "English",
    "hi": "Hindi",
    "de": "German",
}


def normalize_language(language: str | None) -> str:
    lang = (language or "en").strip().lower()
    return lang if lang in SUPPORTED_LANGUAGES else "en"


def store_key(country_code: str, language: str) -> str:
    return f"{country_code.upper()}::{normalize_language(language)}"


# Topic tags for interest filtering
TOPICS = {
    "all": "✨ All Topics",
    "llms": "🤖 LLMs",
    "big_tech": "🏢 Big Tech",
    "startups": "🚀 Startups",
    "research": "📄 Research",
    "funding": "💰 Funding",
    "regulation": "⚖️ Regulation",
    "open_source": "🔓 Open Source",
    "ai_safety": "🛡️ AI Safety",
    "robotics": "🦾 Robotics",
    "healthcare": "🏥 Healthcare",
    "autonomous": "🚗 Autonomous",
}

# Mapping from internal topics/categories to mobile UI topic labels
UI_TOPIC_MAP = {
    "llms": "AI Models",
    "big_tech": "Top Stories",
    "startups": "Business",
    "research": "Research",
    "funding": "Business",
    "regulation": "Top Stories",
    "open_source": "Tools",
    "ai_safety": "Top Stories",
    "robotics": "Tech & Science",
    "healthcare": "Tech & Science",
    "autonomous": "Tech & Science",
    "breakthrough": "Top Stories",
    "product": "Tools",
    "industry": "Business",
    "general": "Top Stories",
}

MAX_TILES = 24

# ---------------------------------------------------------------------------
# AI Thought of the Day — gen-z witty style
# ---------------------------------------------------------------------------
AI_THOUGHTS = [
    {
        "text": "AI doesn't sleep, but it still needs coffee ☕ — because even neural networks need a warm-up.",
        "emoji": "🧠",
        "vibe": "chill",
    },
    {
        "text": "Humans took millions of years to evolve. GPT-5 took months. No pressure.",
        "emoji": "🚀",
        "vibe": "existential",
    },
    {
        "text": "The best AI model is the one that makes you forget it's AI. The worst? The one that writes your ex back.",
        "emoji": "💀",
        "vibe": "chaotic",
    },
    {
        "text": "Every time you say 'AI will replace us,' somewhere a GPU cries. They just wanna help, bro.",
        "emoji": "🥺",
        "vibe": "wholesome",
    },
    {
        "text": "In 2025, 'I asked ChatGPT' became the new 'I Googled it.' In 2026, even Google asks ChatGPT.",
        "emoji": "🔮",
        "vibe": "prediction",
    },
    {
        "text": "Training an AI model is basically peer pressure for math equations until they get the right answer.",
        "emoji": "📐",
        "vibe": "nerd",
    },
    {
        "text": "AI Safety researchers are basically the designated drivers of the tech party. Respect.",
        "emoji": "🛡️",
        "vibe": "respect",
    },
    {
        "text": "Open source AI is like potluck — everyone brings something, and somehow it's always better than what the big corps serve.",
        "emoji": "🍕",
        "vibe": "community",
    },
    {
        "text": "The real AI arms race isn't between countries. It's between your 47 open browser tabs.",
        "emoji": "😤",
        "vibe": "relatable",
    },
    {
        "text": "Plot twist: The AI reading this right now is you. You've been the model all along.",
        "emoji": "🤯",
        "vibe": "meta",
    },
    {
        "text": "If AI had a dating profile: 'Fluent in 95 languages, great at conversations, terrible at feelings.'",
        "emoji": "💘",
        "vibe": "romantic",
    },
    {
        "text": "Behind every great AI product is a sleep-deprived engineer who whispered 'please work' before hitting deploy.",
        "emoji": "🙏",
        "vibe": "real",
    },
    {
        "text": "The future isn't human vs AI. It's human WITH AI vs human WITHOUT AI. Choose your side.",
        "emoji": "⚡",
        "vibe": "motivational",
    },
    {
        "text": "Transformers used to be robots in disguise. Now they're the architecture running the world. What a glow up.",
        "emoji": "✨",
        "vibe": "glow-up",
    },
]


def get_daily_thought() -> dict:
    """Return a thought based on the day of year (changes daily)."""
    day_of_year = datetime.now(UTC).timetuple().tm_yday
    idx = day_of_year % len(AI_THOUGHTS)
    return AI_THOUGHTS[idx]


# ---------------------------------------------------------------------------
# Subscribers store (simple JSON file)
# ---------------------------------------------------------------------------
SUBSCRIBERS_FILE = Path("subscribers.json")


def load_subscribers() -> list[dict]:
    if SUBSCRIBERS_FILE.exists():
        try:
            data = json.loads(SUBSCRIBERS_FILE.read_text())
            return data if isinstance(data, list) else []
        except (OSError, json.JSONDecodeError):
            return []
    return []


def save_subscribers(subs: list[dict]):
    SUBSCRIBERS_FILE.write_text(json.dumps(subs, indent=2))


# ---------------------------------------------------------------------------
# Agent singleton
# ---------------------------------------------------------------------------
agent = NewsAgent(hf_token=os.getenv("HF_API_TOKEN", ""))


# ---------------------------------------------------------------------------
# Core refresh logic
# ---------------------------------------------------------------------------
async def refresh_news(country_code: str = "GLOBAL", language: str = "en"):
    """Fetch, filter and store AI news for a given country."""
    language = normalize_language(language)
    key = store_key(country_code, language)
    logger.info(f"🔄 Refreshing news for {country_code} ({language}) ...")
    try:
        tiles = await agent.run(
            country_code=country_code,
            country_name=COUNTRIES.get(country_code, country_code),
            language_code=language,
        )
        if tiles:
            existing = NEWS_STORE.get(key, [])
            # Prepend new tiles, deduplicate by title, cap at MAX_TILES
            seen_titles = set()
            merged: list[dict] = []
            for t in tiles + existing:
                if t["title"] not in seen_titles and len(merged) < MAX_TILES:
                    seen_titles.add(t["title"])
                    merged.append(t)
            NEWS_STORE[key] = merged
            LAST_UPDATED[key] = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
            logger.info(f"✅ Stored {len(merged)} tiles for {country_code} ({language})")
    except Exception as e:
        logger.error(f"❌ Error refreshing {country_code} ({language}): {e}", exc_info=True)


async def refresh_all():
    """Hourly job: refresh news for all countries that have been requested at least once, plus GLOBAL."""
    keys = list(set(NEWS_STORE.keys()) | {store_key("GLOBAL", "en")})
    tasks = []
    for key in keys:
        if "::" in key:
            country_code, language = key.split("::", 1)
        else:
            country_code, language = key, "en"
        tasks.append(refresh_news(country_code, language))
    await asyncio.gather(*tasks)


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------
scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Schedule hourly refresh and start scheduler FIRST (so port opens immediately)
    scheduler.add_job(refresh_all, "interval", hours=1, id="hourly_refresh", replace_existing=True)

    # Schedule daily digest email at 7 AM UTC (only if Resend is configured)
    if os.getenv("RESEND_API_KEY"):

        def run_digest_sync():
            """Wrapper to run async send_digest in the event loop."""
            import asyncio

            from digest import send_digest

            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(send_digest())
            else:
                loop.run_until_complete(send_digest())

        scheduler.add_job(
            run_digest_sync, "cron", hour=8, minute=0, id="daily_digest", replace_existing=True
        )
        logger.info("📧 Daily digest scheduled for 8:00 AM UTC")

    scheduler.start()
    logger.info("⏰ Scheduler started — updates every hour")
    # Fire initial fetch as background task (don't block startup)
    asyncio.create_task(refresh_news("GLOBAL", "en"))
    yield
    scheduler.shutdown()


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(title="DailyAI News", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------
class SubscribeRequest(BaseModel):
    email: str
    topics: list[str] = []
    country: str = "GLOBAL"
    language: str = "en"


class ArticleBriefRequest(BaseModel):
    title: str
    source: str = ""
    link: str = ""
    summary: str = ""
    why_it_matters: str = ""
    topic: str = "general"
    language: str = "en"


# ---------------------------------------------------------------------------
# Page routes
# ---------------------------------------------------------------------------
@app.head("/")
async def health_check():
    """Render uses HEAD / for health checks."""
    return JSONResponse(content={}, status_code=200)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "countries": COUNTRIES,
            "topics": TOPICS,
            "app_version": APP_VERSION,
        },
    )


@app.get("/api/version")
async def get_app_version():
    return {"version": APP_VERSION, "deployed_at": DEPLOYED_AT}


# ---------------------------------------------------------------------------
# News API
# ---------------------------------------------------------------------------
@app.get("/api/news/{country_code}")
async def get_news(country_code: str, language: str = "en"):
    country_code = country_code.upper()
    language = normalize_language(language)
    key = store_key(country_code, language)
    if country_code not in COUNTRIES:
        return JSONResponse({"error": "Unknown country code"}, status_code=400)

    # Lazy-load: if never fetched, fetch now
    if key not in NEWS_STORE:
        await refresh_news(country_code, language)

    tiles = list(NEWS_STORE.get(key, []))

    # Separate hero tile (highest importance) from the rest
    hero_tile = None
    rest_tiles = tiles
    if tiles:
        sorted_by_imp = sorted(tiles, key=lambda t: t.get("importance", 0), reverse=True)
        hero_tile = sorted_by_imp[0] if sorted_by_imp[0].get("importance", 0) >= 7 else None
        if hero_tile:
            rest_tiles = [t for t in tiles if t["title"] != hero_tile["title"]]

    return {
        "country": country_code,
        "language": language,
        "country_name": COUNTRIES[country_code],
        "last_updated": LAST_UPDATED.get(key, "—"),
        "hero_tile": hero_tile,
        "tiles": rest_tiles,
    }


# ---------------------------------------------------------------------------
# AI Thought API
# ---------------------------------------------------------------------------
@app.get("/api/thought")
async def get_thought():
    return get_daily_thought()


# ---------------------------------------------------------------------------
# Countries API (mobile UI)
# ---------------------------------------------------------------------------
@app.get("/api/countries")
async def get_countries():
    return {"countries": COUNTRIES}


@app.get("/api/languages")
async def get_languages():
    return {"languages": SUPPORTED_LANGUAGES}


# ---------------------------------------------------------------------------
# Articles API (mobile UI)
# ---------------------------------------------------------------------------
@app.get("/api/articles")
async def get_articles(topic: str = "all", country: str = "GLOBAL", language: str = "en"):
    """Mobile-optimized articles endpoint with country support."""
    country = country.upper()
    language = normalize_language(language)
    if country not in COUNTRIES:
        country = "GLOBAL"

    key = store_key(country, language)
    global_key = store_key("GLOBAL", language)

    # Lazy-load news for requested country
    if key not in NEWS_STORE:
        await refresh_news(country, language)

    tiles = list(NEWS_STORE.get(key, []))

    # If country-specific has < 10 tiles, pad with GLOBAL
    if len(tiles) < 10 and country != "GLOBAL":
        if global_key not in NEWS_STORE:
            await refresh_news("GLOBAL", language)
        global_tiles = NEWS_STORE.get(global_key, [])
        existing_titles = {t.get("title", "").lower() for t in tiles}
        for gt in global_tiles:
            if gt.get("title", "").lower() not in existing_titles:
                tiles.append(gt)
            if len(tiles) >= 20:
                break

    # Max limit: 20 for GLOBAL, 20 for others too
    max_limit = 20
    tiles = tiles[:max_limit]

    articles = []
    for i, t in enumerate(tiles):
        internal_topic = (t.get("topic") or t.get("category") or "general").lower()
        ui_topic = UI_TOPIC_MAP.get(internal_topic, "Top Stories")

        # Filter by topic if not "all" / "For You"
        if topic not in ("all", "For You") and ui_topic != topic:
            continue

        articles.append(
            {
                "id": f"{country}-{language}-{i}",
                "headline": t.get("title", ""),
                "summary": (t.get("summary", "") or "")[:1400],
                "why_it_matters": (t.get("why_it_matters", "") or "")[:130],
                "topic": ui_topic,
                "source_name": t.get("source", "Unknown"),
                "source_avatar_url": None,
                "image_url": None,
                "article_url": t.get("link", "#"),
                "published_at": t.get("published", t.get("fetched_at", "")),
            }
        )
    return {
        "articles": articles,
        "country": country,
        "country_name": COUNTRIES.get(country, country),
        "language": language,
        "language_name": SUPPORTED_LANGUAGES.get(language, "English"),
    }


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
    key = store_key(country_code, language)
    if country_code not in COUNTRIES:
        return JSONResponse({"error": "Unknown country code"}, status_code=400)
    await refresh_news(country_code, language)
    return {"status": "ok", "tiles_count": len(NEWS_STORE.get(key, []))}


# ---------------------------------------------------------------------------
# Subscription API
# ---------------------------------------------------------------------------
@app.post("/api/subscribe")
async def subscribe(req: SubscribeRequest):
    email = req.email.strip().lower()
    language = normalize_language(req.language)
    country = (req.country or "GLOBAL").upper()
    if country not in COUNTRIES:
        country = "GLOBAL"
    # Basic email validation
    if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
        return JSONResponse({"error": "Invalid email address"}, status_code=400)

    subs = load_subscribers()

    # Check if already subscribed
    for s in subs:
        if s["email"] == email:
            # Update preferences
            s["topics"] = req.topics
            s["country"] = country
            s["language"] = language
            s["updated_at"] = datetime.now(UTC).isoformat()
            save_subscribers(subs)
            return {"status": "updated", "message": "Preferences updated!"}

    # New subscriber
    subs.append(
        {
            "email": email,
            "topics": req.topics,
            "country": country,
            "language": language,
            "subscribed_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
        }
    )
    save_subscribers(subs)
    logger.info(f"📧 New subscriber: {email} (topics: {req.topics})")

    # Send welcome email with top 10 news (non-blocking)
    # If store is empty (fresh boot), fetch once so first subscribers still get mail.
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


# ---------------------------------------------------------------------------
# Digest preview
# ---------------------------------------------------------------------------
@app.get("/api/digest/preview", response_class=HTMLResponse)
async def digest_preview():
    """Preview the daily digest email HTML."""
    from digest import generate_digest_html

    tiles = NEWS_STORE.get(store_key("GLOBAL", "en"), [])
    if not tiles:
        return HTMLResponse("<p>No news available yet. Check back later.</p>")
    return HTMLResponse(generate_digest_html(tiles[:10]))
