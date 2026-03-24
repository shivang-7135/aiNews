import os
from datetime import UTC, datetime

APP_VERSION = (
    os.getenv("APP_VERSION")
    or os.getenv("SOURCE_VERSION")
    or os.getenv("GITHUB_SHA")
    or datetime.now(UTC).strftime("%Y%m%d%H%M%S")
)
DEPLOYED_AT = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")

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

TOPICS = {
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

SECURITY_CSP = (
    "default-src 'self'; "
    "script-src 'self'; "
    "connect-src 'self'; "
    "img-src 'self' https: data:; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src 'self' https://fonts.gstatic.com data:; "
    "object-src 'none'; "
    "base-uri 'self'; "
    "frame-ancestors 'none'; "
    "form-action 'self'"
)

CSRF_COOKIE_NAME = "dailyai_csrf"


def normalize_language(language: str | None) -> str:
    lang = (language or "en").strip().lower()
    return lang if lang in SUPPORTED_LANGUAGES else "en"


def store_key(country_code: str, language: str) -> str:
    return f"{country_code.upper()}::{normalize_language(language)}"
