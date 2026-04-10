"""
DailyAI — Centralized Configuration
All settings, constants, and env-driven configuration in one place.
"""

import os
from datetime import UTC, datetime

from dotenv import load_dotenv

load_dotenv()

# ── App Metadata ────────────────────────────────────────────────────
APP_NAME = "DailyAI"
APP_VERSION = (
    os.getenv("APP_VERSION")
    or os.getenv("SOURCE_VERSION")
    or os.getenv("GITHUB_SHA")
    or "2.0.0"
)
DEPLOYED_AT = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
APP_URL = os.getenv("APP_URL", "http://localhost:8000")

# ── Server ──────────────────────────────────────────────────────────
PORT = int(os.getenv("PORT", "8000"))
HOST = os.getenv("HOST", "0.0.0.0")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# ── Database ────────────────────────────────────────────────────────
DB_PATH = os.getenv("DB_PATH", "dailyai.db")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "sqlite").strip().lower()
if STORAGE_BACKEND not in {"sqlite", "supabase"}:
    STORAGE_BACKEND = "sqlite"
SUPABASE_TIMEOUT_SECONDS = float(os.getenv("SUPABASE_TIMEOUT_SECONDS", "10"))

# ── Countries & Languages ──────────────────────────────────────────
COUNTRIES: dict[str, str] = {
    "US": "United States",
    "GB": "United Kingdom",
    "DE": "Germany",
    "IN": "India",
    "GLOBAL": "Global / Worldwide",
}

SUPPORTED_LANGUAGES: dict[str, str] = {
    "en": "English",
    "de": "German",
    "hi": "Hindi",
}

# Current product launch language set for UI and public API language picker.
UI_LANGUAGES: dict[str, str] = {
    "en": "English",
    "de": "German",
}

LANG_MAP: dict[str, tuple[str, str]] = {
    "US": ("en", "US"),
    "GB": ("en", "GB"),
    "IN": ("en", "IN"),
    "DE": ("de", "DE"),
    "FR": ("fr", "FR"),
    "CA": ("en", "CA"),
    "AU": ("en", "AU"),
    "GLOBAL": ("en", "US"),
}

# ── Topics ──────────────────────────────────────────────────────────
TOPICS: dict[str, str] = {
    "all": "All Topics",
    "llms": "LLMs",
    "big_tech": "Big Tech",
    "startups": "Startups",
    "research": "Research",
    "funding": "Funding",
    "regulation": "Regulation",
    "open_source": "Open Source",
    "ai_safety": "AI Safety",
    "robotics": "Robotics",
    "healthcare": "Healthcare",
    "autonomous": "Autonomous",
}

UI_TOPIC_MAP: dict[str, str] = {
    "llms": "🤖 AI Models",
    "big_tech": "🔥 Top Stories",
    "startups": "💼 Business",
    "research": "🔬 Research",
    "funding": "💰 Funding",
    "regulation": "⚖️ Regulation",
    "open_source": "🛠 Tools",
    "ai_safety": "⚖️ Regulation",
    "robotics": "🔬 Research",
    "healthcare": "🔬 Research",
    "autonomous": "🔬 Research",
    "breakthrough": "🔥 Top Stories",
    "product": "🛠 Tools",
    "industry": "💼 Business",
    "general": "🔥 Top Stories",
}

# UI topic rail order for feed/category metadata.
UI_FEED_TOPICS: list[str] = [
    "For You",
    "🔥 Top Stories",
    "🤖 AI Models",
    "💼 Business",
    "🔬 Research",
    "🛠 Tools",
    "⚖️ Regulation",
    "💰 Funding",
]

# ── RSS Feed Queries ────────────────────────────────────────────────
GOOGLE_NEWS_RSS = (
    "https://news.google.com/rss/search?q={query}&hl={hl}&gl={gl}&ceid={gl}:{hl}"
)

FEED_QUERIES: dict[str, str] = {
    "ai_core": "artificial+intelligence+OR+AI+OR+machine+learning+OR+deep+learning+OR+LLM+OR+generative+AI",
    "ai_industry": "OpenAI+OR+Google+AI+OR+Meta+AI+OR+Anthropic+OR+Mistral+OR+DeepMind+OR+Hugging+Face",
    "ai_breakthroughs": "AI+breakthrough+OR+AI+launch+OR+AI+regulation+OR+AI+startup",
    "ai_research": "AI+research+paper+OR+arXiv+AI+OR+foundation+model+benchmark",
    "ai_infra": "NVIDIA+AI+chips+OR+AI+inference+OR+datacenter+AI+OR+GPU+cluster",
    "ai_policy": "AI+Act+OR+AI+policy+OR+AI+governance+OR+AI+safety+institute",
}

FEED_QUERIES_DE: dict[str, str] = {
    "ki_allgemein": "Künstliche+Intelligenz+OR+KI+OR+maschinelles+Lernen+OR+generative+KI",
    "ki_industrie": "OpenAI+OR+Google+KI+OR+Meta+KI+OR+Anthropic+OR+Mistral+OR+DeepMind+OR+Aleph+Alpha",
    "ki_regulierung": "AI+Act+OR+KI+Regulierung+OR+KI+Gesetz+OR+Datenschutz+KI+OR+EU+KI+Verordnung",
    "ki_startups": "KI+Startup+Deutschland+OR+AI+Startup+Germany+OR+Aleph+Alpha+OR+DeepL",
}

FEED_QUERIES_IN: dict[str, str] = {
    "ai_india": "artificial+intelligence+India+OR+AI+India+OR+machine+learning+India",
    "ai_india_companies": "Infosys+AI+OR+TCS+artificial+intelligence+OR+Wipro+AI+OR+Reliance+Jio+AI",
    "ai_india_research": "IIT+AI+OR+IISC+AI+OR+ISRO+AI+OR+India+AI+research+OR+NASSCOM+AI",
    "ai_india_govt": "India+AI+policy+OR+MeitY+AI+OR+India+digital+transformation",
}

FEED_QUERIES_GB: dict[str, str] = {
    "ai_uk": "artificial+intelligence+UK+OR+AI+United+Kingdom+OR+machine+learning+UK",
    "ai_uk_companies": "DeepMind+OR+ARM+AI+OR+BT+artificial+intelligence+OR+UK+AI+startup",
    "ai_uk_policy": "UK+AI+Safety+Institute+OR+UK+AI+regulation+OR+Bletchley+Park+AI+summit",
    "ai_uk_research": "Alan+Turing+Institute+AI+OR+Oxford+AI+OR+Cambridge+AI+research",
}

# ── Source Trust ────────────────────────────────────────────────────
HIGH_TRUST_SOURCES: set[str] = {
    "reuters", "associated press", "ap news", "financial times",
    "bloomberg", "wsj", "the economist", "nature", "science",
    "mit technology review", "arxiv", "the verge", "techcrunch",
    "wired", "bbc", "the guardian", "cnbc",
    # German high-trust (DACH)
    "heise", "golem", "t3n", "handelsblatt", "faz",
    "frankfurter allgemeine", "spiegel", "der spiegel",
    "süddeutsche zeitung", "die zeit", "tagesschau", "nzz", "der standard",
    # India high-trust
    "the hindu", "times of india", "economic times", "livemint",
    "ndtv", "india today", "business standard", "the indian express",
    # UK high-trust
    "the times", "the telegraph", "sky news",
}

MEDIUM_TRUST_SOURCES: set[str] = {
    "venturebeat", "zdnet", "ars technica", "the information",
    "the register", "engadget", "mashable", "nikkei",
    "south china morning post", "business insider", "fortune",
    "fast company", "cnet", "tom's hardware", "9to5mac", "9to5google",
    "chip.de", "computerbild",
    # India medium-trust
    "moneycontrol", "firstpost", "inc42", "yourstory",
    # UK medium-trust
    "techradar",
}

# ── Pipeline Limits ─────────────────────────────────────────────────
MAX_TILES_PER_FETCH = 30
MAX_FEED_SIZE = 30
MIN_FEED_SIZE = 3  # Lowered from 10 to avoid premature fallback for regional feeds
RSS_MAX_ITEMS_PER_FEED = 20
RSS_TIMEOUT_SECONDS = 15
LLM_TIMEOUT_SECONDS = 45
LLM_FAST_TIMEOUT_SECONDS = 20
STARTUP_PREFETCH_TIMEOUT = 300  # 5 min max for full startup prefetch
REFRESH_INTERVAL_HOURS = int(os.getenv("REFRESH_INTERVAL_HOURS", "1"))
REFRESH_INTERVAL_MINUTES = int(os.getenv("REFRESH_INTERVAL_MINUTES", "15"))
REFRESH_COOLDOWN_SECONDS = 120

# Cache / prefetch behavior
CACHE_MAX_ARTICLES = int(os.getenv("CACHE_MAX_ARTICLES", "150"))
CACHE_MIN_PER_KEY = int(os.getenv("CACHE_MIN_PER_KEY", "8"))
STARTUP_PREFETCH_GLOBAL_LIMIT = int(os.getenv("STARTUP_PREFETCH_GLOBAL_LIMIT", "30"))
STARTUP_PREFETCH_OTHER_LIMIT = int(os.getenv("STARTUP_PREFETCH_OTHER_LIMIT", "30"))
STARTUP_PREFETCH_CONCURRENCY = int(os.getenv("STARTUP_PREFETCH_CONCURRENCY", "2"))
DAILY_REFRESH_HOUR_UTC = int(os.getenv("DAILY_REFRESH_HOUR_UTC", "6"))
DAILY_REFRESH_MINUTE_UTC = int(os.getenv("DAILY_REFRESH_MINUTE_UTC", "0"))

# ── Email ───────────────────────────────────────────────────────────
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
RESEND_FROM_EMAIL = os.getenv("RESEND_FROM_EMAIL", "DailyAI <onboarding@resend.dev>")
RESEND_REPLY_TO = os.getenv("RESEND_REPLY_TO", "")

# ── Security ────────────────────────────────────────────────────────
CSRF_COOKIE_NAME = "dailyai_csrf"

# ── Helpers ─────────────────────────────────────────────────────────

def normalize_language(language: str | None) -> str:
    lang = (language or "en").strip().lower()
    return lang if lang in SUPPORTED_LANGUAGES else "en"


def store_key(country_code: str, language: str) -> str:
    return f"{country_code.upper()}::{normalize_language(language)}"
