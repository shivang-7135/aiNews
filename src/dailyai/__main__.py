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
from dailyai.storage.sqlite import close_db, get_db
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

        # Fire off an initial background refresh if the DB is empty
        asyncio.create_task(_initial_refresh_if_needed())

    @app.on_event("shutdown")
    async def on_shutdown():
        logger.info("Shutting down services...")
        stop_scheduler()
        await close_db()

    async def _initial_refresh_if_needed():
        """Fetch feed on first boot if DB is totally empty."""
        try:
            from dailyai.storage.sqlite import get_all_store_keys
            from dailyai.services.news import refresh_news
            keys = await get_all_store_keys()
            if not keys:
                logger.info("Database empty, triggering initial feed fetch...")
                await refresh_news("GLOBAL", "en")
        except Exception as e:
            logger.error(f"Initial refresh failed: {e}")

    # Run server
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")

    logger.info(f"Starting Uvicorn server on http://{host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
