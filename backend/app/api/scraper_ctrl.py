from __future__ import annotations

import asyncio

from fastapi import APIRouter, BackgroundTasks

from app.database import async_session
from scraper.runner import ScraperRunner

router = APIRouter(prefix="/api/scraper", tags=["scraper"])


async def _run_scraper():
    runner = ScraperRunner(async_session)
    await runner.run_all()


@router.post("/run")
async def trigger_scrape(background_tasks: BackgroundTasks):
    background_tasks.add_task(_run_scraper)
    return {"status": "started", "message": "Scraping lancé en arrière-plan"}


@router.post("/run/{site_key}/{postal_code}")
async def trigger_single(
    site_key: str, postal_code: str, background_tasks: BackgroundTasks
):
    async def _run():
        runner = ScraperRunner(async_session)
        await runner.run_single_site(site_key, postal_code)

    background_tasks.add_task(_run)
    return {
        "status": "started",
        "message": f"Scraping {site_key} pour {postal_code} lancé",
    }
