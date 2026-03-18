"""
DailyAI News — Agentic AI News Aggregator
A mobile-friendly app that fetches, filters, and summarizes AI news every hour
using an LLM agent with tool-calling capabilities.
"""

import os
import json
import asyncio
import logging
import re
from datetime import datetime, timezone, timedelta
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
from pydantic import BaseModel

from agent import NewsAgent

load_dotenv()

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("dailyai")

# ---------------------------------------------------------------------------
# In-memory store  (max 24 tiles, rolling)
# ---------------------------------------------------------------------------
NEWS_STORE: dict[str, list[dict]] = {}   # key = country code
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

# Topic tags for interest filtering
TOPICS = {
    "all": "All Topics",
    "llms": "LLMs & Language Models",
    "big_tech": "Big Tech AI",
    "startups": "AI Startups",
    "research": "Research & Papers",
    "funding": "Funding & Deals",
    "regulation": "Regulation & Policy",
    "open_source": "Open Source AI",
    "ai_safety": "AI Safety & Ethics",
    "robotics": "Robotics",
    "healthcare": "AI in Healthcare",
    "autonomous": "Autonomous Systems",
}

MAX_TILES = 24

# ---------------------------------------------------------------------------
# AI Thought of the Day — gen-z witty style
# ---------------------------------------------------------------------------
AI_THOUGHTS = [
    {"text": "AI doesn't sleep, but it still needs coffee ☕ — because even neural networks need a warm-up.", "emoji": "🧠", "vibe": "chill"},
    {"text": "Humans took millions of years to evolve. GPT-5 took months. No pressure.", "emoji": "🚀", "vibe": "existential"},
    {"text": "The best AI model is the one that makes you forget it's AI. The worst? The one that writes your ex back.", "emoji": "💀", "vibe": "chaotic"},
    {"text": "Every time you say 'AI will replace us,' somewhere a GPU cries. They just wanna help, bro.", "emoji": "🥺", "vibe": "wholesome"},
    {"text": "In 2025, 'I asked ChatGPT' became the new 'I Googled it.' In 2026, even Google asks ChatGPT.", "emoji": "🔮", "vibe": "prediction"},
    {"text": "Training an AI model is basically peer pressure for math equations until they get the right answer.", "emoji": "📐", "vibe": "nerd"},
    {"text": "AI Safety researchers are basically the designated drivers of the tech party. Respect.", "emoji": "🛡️", "vibe": "respect"},
    {"text": "Open source AI is like potluck — everyone brings something, and somehow it's always better than what the big corps serve.", "emoji": "🍕", "vibe": "community"},
    {"text": "The real AI arms race isn't between countries. It's between your 47 open browser tabs.", "emoji": "😤", "vibe": "relatable"},
    {"text": "Plot twist: The AI reading this right now is you. You've been the model all along.", "emoji": "🤯", "vibe": "meta"},
    {"text": "If AI had a dating profile: 'Fluent in 95 languages, great at conversations, terrible at feelings.'", "emoji": "💘", "vibe": "romantic"},
    {"text": "Behind every great AI product is a sleep-deprived engineer who whispered 'please work' before hitting deploy.", "emoji": "🙏", "vibe": "real"},
    {"text": "The future isn't human vs AI. It's human WITH AI vs human WITHOUT AI. Choose your side.", "emoji": "⚡", "vibe": "motivational"},
    {"text": "Transformers used to be robots in disguise. Now they're the architecture running the world. What a glow up.", "emoji": "✨", "vibe": "glow-up"},
]

def get_daily_thought() -> dict:
    """Return a thought based on the day of year (changes daily)."""
    day_of_year = datetime.now(timezone.utc).timetuple().tm_yday
    idx = day_of_year % len(AI_THOUGHTS)
    return AI_THOUGHTS[idx]

# ---------------------------------------------------------------------------
# Subscribers store (simple JSON file)
# ---------------------------------------------------------------------------
SUBSCRIBERS_FILE = Path("subscribers.json")

def load_subscribers() -> list[dict]:
    if SUBSCRIBERS_FILE.exists():
        try:
            return json.loads(SUBSCRIBERS_FILE.read_text())
        except (json.JSONDecodeError, IOError):
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
async def refresh_news(country_code: str = "GLOBAL"):
    """Fetch, filter and store AI news for a given country."""
    logger.info(f"🔄 Refreshing news for {country_code} ...")
    try:
        tiles = await agent.run(country_code=country_code, country_name=COUNTRIES.get(country_code, country_code))
        if tiles:
            existing = NEWS_STORE.get(country_code, [])
            # Prepend new tiles, deduplicate by title, cap at MAX_TILES
            seen_titles = set()
            merged: list[dict] = []
            for t in tiles + existing:
                if t["title"] not in seen_titles and len(merged) < MAX_TILES:
                    seen_titles.add(t["title"])
                    merged.append(t)
            NEWS_STORE[country_code] = merged
            LAST_UPDATED[country_code] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            logger.info(f"✅ Stored {len(merged)} tiles for {country_code}")
    except Exception as e:
        logger.error(f"❌ Error refreshing {country_code}: {e}", exc_info=True)


async def refresh_all():
    """Hourly job: refresh news for all countries that have been requested at least once, plus GLOBAL."""
    codes = list(set(NEWS_STORE.keys()) | {"GLOBAL"})
    await asyncio.gather(*(refresh_news(c) for c in codes))


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
        from digest import send_digest
        scheduler.add_job(send_digest, "cron", hour=7, minute=0, id="daily_digest", replace_existing=True)
        logger.info("📧 Daily digest scheduled for 7:00 AM UTC")

    scheduler.start()
    logger.info("⏰ Scheduler started — updates every hour")
    # Fire initial fetch as background task (don't block startup)
    asyncio.create_task(refresh_news("GLOBAL"))
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


# ---------------------------------------------------------------------------
# Page routes
# ---------------------------------------------------------------------------
@app.head("/")
async def health_check():
    """Render uses HEAD / for health checks."""
    return JSONResponse(content={}, status_code=200)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "countries": COUNTRIES,
        "topics": TOPICS,
    })


# ---------------------------------------------------------------------------
# News API
# ---------------------------------------------------------------------------
@app.get("/api/news/{country_code}")
async def get_news(country_code: str):
    country_code = country_code.upper()
    if country_code not in COUNTRIES:
        return JSONResponse({"error": "Unknown country code"}, status_code=400)

    # Lazy-load: if never fetched, fetch now
    if country_code not in NEWS_STORE:
        await refresh_news(country_code)

    tiles = NEWS_STORE.get(country_code, [])

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
        "country_name": COUNTRIES[country_code],
        "last_updated": LAST_UPDATED.get(country_code, "—"),
        "hero_tile": hero_tile,
        "tiles": rest_tiles,
    }


# ---------------------------------------------------------------------------
# AI Thought API
# ---------------------------------------------------------------------------
@app.get("/api/thought")
async def get_thought():
    return get_daily_thought()


@app.post("/api/refresh/{country_code}")
async def force_refresh(country_code: str):
    country_code = country_code.upper()
    if country_code not in COUNTRIES:
        return JSONResponse({"error": "Unknown country code"}, status_code=400)
    await refresh_news(country_code)
    return {"status": "ok", "tiles_count": len(NEWS_STORE.get(country_code, []))}


# ---------------------------------------------------------------------------
# Subscription API
# ---------------------------------------------------------------------------
@app.post("/api/subscribe")
async def subscribe(req: SubscribeRequest):
    email = req.email.strip().lower()
    # Basic email validation
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        return JSONResponse({"error": "Invalid email address"}, status_code=400)

    subs = load_subscribers()

    # Check if already subscribed
    for s in subs:
        if s["email"] == email:
            # Update preferences
            s["topics"] = req.topics
            s["country"] = req.country
            s["updated_at"] = datetime.now(timezone.utc).isoformat()
            save_subscribers(subs)
            return {"status": "updated", "message": "Preferences updated!"}

    # New subscriber
    subs.append({
        "email": email,
        "topics": req.topics,
        "country": req.country,
        "subscribed_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    })
    save_subscribers(subs)
    logger.info(f"📧 New subscriber: {email} (topics: {req.topics})")
    return {"status": "subscribed", "message": "You're in! Daily AI digest coming soon."}


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
    tiles = NEWS_STORE.get("GLOBAL", [])
    if not tiles:
        return HTMLResponse("<p>No news available yet. Check back later.</p>")
    return HTMLResponse(generate_digest_html(tiles[:10]))
