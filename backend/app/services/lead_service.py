from __future__ import annotations

from datetime import datetime

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.lead import Lead, LEAD_STATUSES
from app.models.listing import Listing


async def get_leads(
    session: AsyncSession,
    status: str | None = None,
    postal_code: str | None = None,
    page: int = 1,
    per_page: int = 50,
) -> tuple[list[Lead], int]:
    query = select(Lead).options(joinedload(Lead.listing))

    if status:
        query = query.where(Lead.status == status)
    if postal_code:
        query = query.join(Listing).where(Listing.postal_code == postal_code)

    # Count
    count_q = select(func.count(Lead.id))
    if status:
        count_q = count_q.where(Lead.status == status)
    if postal_code:
        count_q = count_q.join(Listing).where(Listing.postal_code == postal_code)
    total = (await session.execute(count_q)).scalar() or 0

    # Paginate
    query = query.order_by(Lead.created_at.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)

    result = await session.execute(query)
    leads = result.scalars().unique().all()

    return list(leads), total


async def get_lead(session: AsyncSession, lead_id: int) -> Lead | None:
    result = await session.execute(
        select(Lead).options(joinedload(Lead.listing)).where(Lead.id == lead_id)
    )
    return result.scalar_one_or_none()


async def update_lead_status(
    session: AsyncSession, lead_id: int, status: str
) -> Lead | None:
    if status not in LEAD_STATUSES:
        raise ValueError(f"Invalid status: {status}")

    lead = await get_lead(session, lead_id)
    if not lead:
        return None

    lead.status = status
    lead.touch()
    await session.commit()
    return lead


async def update_lead(
    session: AsyncSession,
    lead_id: int,
    notes: str | None = None,
    last_contacted_at: datetime | None = None,
) -> Lead | None:
    lead = await get_lead(session, lead_id)
    if not lead:
        return None

    if notes is not None:
        lead.notes = notes
    if last_contacted_at is not None:
        lead.last_contacted_at = last_contacted_at

    lead.touch()
    await session.commit()
    return lead


async def delete_lead(session: AsyncSession, lead_id: int) -> bool:
    lead = await get_lead(session, lead_id)
    if not lead:
        return False

    # Anonymize listing personal data (RGPD)
    if lead.listing:
        lead.listing.seller_name = None
        lead.listing.seller_phone = None
        lead.listing.seller_email = None

    await session.delete(lead)
    await session.commit()
    return True


async def get_dashboard_stats(session: AsyncSession) -> dict:
    # Count by status
    status_counts = {}
    for status in LEAD_STATUSES:
        count = (
            await session.execute(
                select(func.count(Lead.id)).where(Lead.status == status)
            )
        ).scalar() or 0
        status_counts[status] = count

    total = sum(status_counts.values())

    # Count by source site
    site_counts_result = await session.execute(
        select(Listing.source_site, func.count(Lead.id))
        .join(Listing)
        .group_by(Listing.source_site)
    )
    site_counts = {row[0]: row[1] for row in site_counts_result.all()}

    return {
        "total_leads": total,
        "by_status": status_counts,
        "by_site": site_counts,
    }
