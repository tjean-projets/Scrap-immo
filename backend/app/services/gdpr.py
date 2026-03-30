from __future__ import annotations

from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lead import Lead
from app.models.listing import Listing
import structlog

logger = structlog.get_logger()


async def purge_expired_leads(session: AsyncSession) -> int:
    now = datetime.utcnow()

    # Find expired leads (excluding mandat_signe which should be kept)
    stmt = select(Lead).where(
        Lead.auto_purge_at < now,
        Lead.status != "mandat_signe",
    )
    result = await session.execute(stmt)
    expired_leads = result.scalars().all()

    count = 0
    for lead in expired_leads:
        # Anonymize personal data in listing
        await session.execute(
            update(Listing)
            .where(Listing.id == lead.listing_id)
            .values(seller_name=None, seller_phone=None, seller_email=None)
        )
        await session.delete(lead)
        count += 1

    if count > 0:
        await session.commit()
        logger.info("rgpd_purge_complete", purged=count)

    return count
