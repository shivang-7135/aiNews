"""
DailyAI — APScheduler Jobs
Manages periodic tasks: news refresh, Supabase sync, email digest.
"""

import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from dailyai.config import REFRESH_INTERVAL_MINUTES

logger = logging.getLogger("dailyai.services.scheduler")

scheduler = AsyncIOScheduler()


async def _refresh_all_feeds():
    """Refresh news for all active country/language combinations."""
    from dailyai.services.news import refresh_news

    # Always refresh global English
    await refresh_news("GLOBAL", "en")

    # Also refresh any other stored keys
    from dailyai.storage.sqlite import get_all_store_keys

    keys = await get_all_store_keys()
    for key in keys:
        if "::" in key:
            country, lang = key.split("::", 1)
            if country != "GLOBAL" or lang != "en":
                await refresh_news(country, lang)


def start_scheduler():
    """Start the background scheduler with all jobs."""
    # Frequent refresh so users do not wait an hour for new feed updates.
    scheduler.add_job(
        _refresh_all_feeds,
        "interval",
        minutes=max(1, REFRESH_INTERVAL_MINUTES),
        id="feed_refresh",
        replace_existing=True,
    )
    logger.info(f"Scheduled news refresh every {max(1, REFRESH_INTERVAL_MINUTES)} minute(s)")

    # Email digest at 8 AM UTC
    from dailyai.config import RESEND_API_KEY
    if RESEND_API_KEY:
        scheduler.add_job(
            _send_digest_wrapper,
            "cron",
            hour=8,
            minute=0,
            id="daily_digest",
            replace_existing=True,
        )
        logger.info("Scheduled daily digest for 8:00 AM UTC")

    scheduler.start()
    logger.info("Scheduler started")


async def _send_digest_wrapper():
    """Wrapper to call digest sender."""
    try:
        from dailyai.services.digest import send_digest
        await send_digest()
    except Exception as e:
        logger.error(f"Digest job failed: {e}")


def stop_scheduler():
    """Shutdown the scheduler."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler stopped")
