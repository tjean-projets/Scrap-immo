from __future__ import annotations

import asyncio

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select
import structlog

from app.database import async_session
from app.models.config import ScrapingConfig
from app.services.gdpr import purge_expired_leads
from scraper.runner import ScraperRunner

logger = structlog.get_logger()

scheduler = AsyncIOScheduler()


async def _scrape_job():
    logger.info("scheduled_scrape_started")
    runner = ScraperRunner(async_session)
    await runner.run_all()
    logger.info("scheduled_scrape_finished")


async def _gdpr_purge_job():
    logger.info("gdpr_purge_started")
    async with async_session() as session:
        count = await purge_expired_leads(session)
    logger.info("gdpr_purge_finished", purged=count)


async def setup_scheduler():
    # Load config from DB
    async with async_session() as session:
        result = await session.execute(
            select(ScrapingConfig).where(ScrapingConfig.id == 1)
        )
        config = result.scalar_one_or_none()

    hours = config.schedule_hours if config else [8, 13, 19]

    # Remove existing scrape jobs
    for job in scheduler.get_jobs():
        if job.id.startswith("scrape_"):
            job.remove()

    # Add scrape jobs for each configured hour
    for hour in hours:
        scheduler.add_job(
            _scrape_job,
            CronTrigger(hour=hour, minute=0),
            id=f"scrape_{hour}",
            replace_existing=True,
        )
        logger.info("scheduled_scrape_job", hour=hour)

    # RGPD purge daily at 02:00
    scheduler.add_job(
        _gdpr_purge_job,
        CronTrigger(hour=2, minute=0),
        id="gdpr_purge",
        replace_existing=True,
    )

    if not scheduler.running:
        scheduler.start()
        logger.info("scheduler_started", scrape_hours=hours)


async def reload_scheduler():
    await setup_scheduler()
