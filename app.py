"""Compatibility ASGI entrypoint.

This shim keeps `uvicorn app:app` working by booting the v2 app from `src/dailyai`.
Preferred command remains: `uv run dailyai`.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Ensure src-layout imports work when launched as `uvicorn app:app`
ROOT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Load .env for `uvicorn app:app` workflows.
load_dotenv(ROOT_DIR / ".env")

from dailyai.ui.app import create_app

app = create_app()


@app.on_event("startup")
async def _startup_services_for_uvicorn_app_entry() -> None:
    """Run startup cache warmup for `uvicorn app:app` compatibility path."""
    from dailyai.llm.provider import warmup_hf_model
    from dailyai.services.media_cache import ensure_category_images_cached
    from dailyai.services.news import prefetch_cache_on_startup
    from dailyai.services.scheduler import start_scheduler
    from dailyai.storage.sqlite import get_db

    await get_db()
    start_scheduler()

    import asyncio

    asyncio.create_task(warmup_hf_model())
    asyncio.create_task(ensure_category_images_cached())
    asyncio.create_task(prefetch_cache_on_startup(force=True))


@app.on_event("shutdown")
async def _shutdown_services_for_uvicorn_app_entry() -> None:
    """Shutdown background services for `uvicorn app:app` compatibility path."""
    from dailyai.services.scheduler import stop_scheduler
    from dailyai.storage.sqlite import close_db

    stop_scheduler()
    await close_db()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("RELOAD", "true").lower() == "true",
    )
