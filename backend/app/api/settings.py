from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.config import ScrapingConfig
from app.schemas.config import ScrapingConfigOut, ScrapingConfigUpdate
from scraper.registry import get_available_sites

router = APIRouter(prefix="/api/settings", tags=["settings"])


async def _get_or_create_config(db: AsyncSession) -> ScrapingConfig:
    result = await db.execute(select(ScrapingConfig).where(ScrapingConfig.id == 1))
    config = result.scalar_one_or_none()
    if not config:
        config = ScrapingConfig(id=1)
        db.add(config)
        await db.commit()
        await db.refresh(config)
    return config


@router.get("", response_model=ScrapingConfigOut)
async def get_settings(db: AsyncSession = Depends(get_db)):
    config = await _get_or_create_config(db)
    return ScrapingConfigOut(
        postal_codes=config.postal_codes,
        schedule_hours=config.schedule_hours,
        enabled_sites=config.enabled_sites,
        transaction_types=config.transaction_types,
    )


@router.put("", response_model=ScrapingConfigOut)
async def update_settings(
    body: ScrapingConfigUpdate, db: AsyncSession = Depends(get_db)
):
    config = await _get_or_create_config(db)

    if body.postal_codes is not None:
        config.postal_codes = body.postal_codes
    if body.schedule_hours is not None:
        config.schedule_hours = body.schedule_hours
    if body.enabled_sites is not None:
        config.enabled_sites = body.enabled_sites
    if body.transaction_types is not None:
        config.transaction_types = body.transaction_types

    await db.commit()

    return ScrapingConfigOut(
        postal_codes=config.postal_codes,
        schedule_hours=config.schedule_hours,
        enabled_sites=config.enabled_sites,
        transaction_types=config.transaction_types,
    )


@router.get("/available-sites")
async def available_sites():
    return get_available_sites()
