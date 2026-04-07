"""DailyAI media cache helpers.

Downloads category cover images once and reuses local files afterward.
"""

from __future__ import annotations

import logging
from pathlib import Path
from urllib.parse import quote

import httpx

logger = logging.getLogger("dailyai.services.media")

PROJECT_ROOT = Path(__file__).resolve().parents[3]
TOPIC_COVERS_DIR = PROJECT_ROOT / "static" / "topic-covers"

# Topic-aware keyword queries (3 variants/category) for non-generic visuals.
CATEGORY_IMAGE_QUERIES: dict[str, tuple[str, str, str]] = {
    "breakthrough": (
        "artificial intelligence robotics laboratory",
        "ai semiconductor datacenter",
        "advanced machine learning innovation",
    ),
    "product": (
        "ai software product launch",
        "developer coding ai assistant",
        "saas dashboard artificial intelligence",
    ),
    "regulation": (
        "government technology policy meeting",
        "law regulation digital governance",
        "europe parliament technology law",
    ),
    "funding": (
        "startup funding venture capital technology",
        "business deal handshake tech",
        "finance investment ai startup",
    ),
    "research": (
        "scientist ai research paper",
        "data science lab experiment",
        "university machine learning study",
    ),
    "industry": (
        "technology business office ai",
        "enterprise digital transformation",
        "industry conference artificial intelligence",
    ),
    "general": (
        "artificial intelligence technology news",
        "modern technology abstract network",
        "global technology innovation",
    ),
}


def _cover_path(category: str, idx: int) -> Path:
    return TOPIC_COVERS_DIR / f"{category}-{idx}.jpg"


def _stable_lock(seed: str, idx: int) -> int:
    return (sum(ord(c) for c in seed) + idx * 97) % 100000


def _cover_url(query: str, seed: str, idx: int) -> str:
    # Topic-aware image source with deterministic lock for stable caching.
    tags = quote(query.replace(" ", ","), safe=",")
    lock = _stable_lock(seed, idx)
    return f"https://loremflickr.com/1080/720/{tags}?lock={lock}"


def _fallback_cover_url(seed: str) -> str:
    return f"https://picsum.photos/seed/{seed}/1080/720"


async def ensure_category_images_cached() -> None:
    """Download category cover images if they do not exist locally.

    This is best-effort and never raises: the app can continue with existing
    local cover images when network fetch fails.
    """
    TOPIC_COVERS_DIR.mkdir(parents=True, exist_ok=True)

    async with httpx.AsyncClient(timeout=25, follow_redirects=True) as client:
        for category, queries in CATEGORY_IMAGE_QUERIES.items():
            for idx, query in enumerate(queries, start=1):
                seed = f"{category}-{idx}"
                path = _cover_path(category, idx)
                if path.exists() and path.stat().st_size > 1024:
                    continue

                try:
                    resp = await client.get(_cover_url(query, seed, idx))
                    if resp.status_code != 200 or not resp.content:
                        resp = await client.get(_fallback_cover_url(seed))

                    if resp.status_code == 200 and resp.content:
                        path.write_bytes(resp.content)
                        logger.info("Cached category cover: %s", path.name)
                    else:
                        logger.warning(
                            "Cover download failed (%s): %s",
                            resp.status_code,
                            path.name,
                        )
                except Exception as exc:
                    logger.warning("Cover download error for %s: %s", path.name, exc)
