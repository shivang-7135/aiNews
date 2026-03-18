"""
DailyAI News — Agentic AI News Aggregator
A mobile-friendly app that fetches, filters, and summarizes AI news every hour
using an LLM agent with tool-calling capabilities.
"""

import os
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv

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

MAX_TILES = 24

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


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "countries": COUNTRIES,
    })


@app.get("/api/news/{country_code}")
async def get_news(country_code: str):
    country_code = country_code.upper()
    if country_code not in COUNTRIES:
        return JSONResponse({"error": "Unknown country code"}, status_code=400)

    # Lazy-load: if never fetched, fetch now
    if country_code not in NEWS_STORE:
        await refresh_news(country_code)

    return {
        "country": country_code,
        "country_name": COUNTRIES[country_code],
        "last_updated": LAST_UPDATED.get(country_code, "—"),
        "tiles": NEWS_STORE.get(country_code, []),
    }


@app.post("/api/refresh/{country_code}")
async def force_refresh(country_code: str):
    country_code = country_code.upper()
    if country_code not in COUNTRIES:
        return JSONResponse({"error": "Unknown country code"}, status_code=400)
    await refresh_news(country_code)
    return {"status": "ok", "tiles_count": len(NEWS_STORE.get(country_code, []))}
