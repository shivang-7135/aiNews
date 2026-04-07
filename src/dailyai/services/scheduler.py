"""
DailyAI — APScheduler Jobs
Manages periodic tasks: news refresh, Supabase sync, email digest.
"""

import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from dailyai.config import DAILY_REFRESH_HOUR_UTC, DAILY_REFRESH_MINUTE_UTC

logger = logging.getLogger("dailyai.services.scheduler")

scheduler = AsyncIOScheduler()


async def _refresh_all_feeds():
    """Refresh news for all active country/language combinations."""
    from dailyai.services.news import get_prefetch_pairs, refresh_news

    for country, lang in get_prefetch_pairs():
        await refresh_news(country, lang, force=True)


def start_scheduler():
    """Start the background scheduler with all jobs."""
    if scheduler.running:
        logger.info("Scheduler already running; skipping re-start")
        return

    # Daily full-cache refresh.
    scheduler.add_job(
        _refresh_all_feeds,
        "cron",
        hour=max(0, min(23, DAILY_REFRESH_HOUR_UTC)),
        minute=max(0, min(59, DAILY_REFRESH_MINUTE_UTC)),
        id="feed_refresh",
        replace_existing=True,
    )
    logger.info(
        "Scheduled daily cache refresh at %02d:%02d UTC",
        max(0, min(23, DAILY_REFRESH_HOUR_UTC)),
        max(0, min(59, DAILY_REFRESH_MINUTE_UTC)),
    )

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
