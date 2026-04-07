"""
DailyAI — Main Entry Point
Managed entirely by `uv run dailyai`.
"""

import asyncio
import logging
import os
import sys

import uvicorn
from dotenv import load_dotenv

from dailyai.services.scheduler import start_scheduler, stop_scheduler
from dailyai.storage.backend import close_db, get_db
from dailyai.ui.app import create_app

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("dailyai.main")

# Load environment before anything else
load_dotenv()


def main():
    """Application entry point."""
    logger.info("Initializing DailyAI v2 (LangGraph Edition)")

    # Ensure DB path directory exists
    db_path = os.getenv("DB_PATH", "dailyai.db")
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    # Initialize app
    app = create_app()

    # Lifecycle events
    @app.on_event("startup")
    async def on_startup():
        logger.info("Starting background services...")
        await get_db()
        start_scheduler()

        # Pre-warm HuggingFace model to avoid cold start on first request
        from dailyai.llm.provider import warmup_hf_model
        from dailyai.services.media_cache import ensure_category_images_cached
        from dailyai.services.news import prefetch_cache_on_startup
        asyncio.create_task(warmup_hf_model())
        asyncio.create_task(ensure_category_images_cached())

        # Warm the DB cache at startup to reduce per-user LLM latency.
        asyncio.create_task(prefetch_cache_on_startup(force=True))

    @app.on_event("shutdown")
    async def on_shutdown():
        logger.info("Shutting down services...")
        stop_scheduler()
        await close_db()

    # Run server
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")

    logger.info(f"Starting Uvicorn server on http://{host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
