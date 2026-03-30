from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.listing import Listing
from app.schemas.listing import ListingOut

router = APIRouter(prefix="/api/listings", tags=["listings"])


@router.get("", response_model=dict)
async def list_listings(
    source_site: str | None = None,
    postal_code: str | None = None,
    min_price: int | None = None,
    max_price: int | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = select(Listing)
    count_q = select(func.count(Listing.id))

    if source_site:
        query = query.where(Listing.source_site == source_site)
        count_q = count_q.where(Listing.source_site == source_site)
    if postal_code:
        query = query.where(Listing.postal_code == postal_code)
        count_q = count_q.where(Listing.postal_code == postal_code)
    if min_price is not None:
        query = query.where(Listing.price >= min_price)
        count_q = count_q.where(Listing.price >= min_price)
    if max_price is not None:
        query = query.where(Listing.price <= max_price)
        count_q = count_q.where(Listing.price <= max_price)

    total = (await db.execute(count_q)).scalar() or 0

    query = query.order_by(Listing.created_at.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    listings = result.scalars().all()

    return {
        "items": [ListingOut.model_validate(l) for l in listings],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/{listing_id}", response_model=ListingOut)
async def read_listing(listing_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Listing).where(Listing.id == listing_id))
    listing = result.scalar_one_or_none()
    if not listing:
        raise HTTPException(404, "Listing not found")
    return ListingOut.model_validate(listing)
