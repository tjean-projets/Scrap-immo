from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.lead import Lead
from app.models.listing import Listing
from app.models.scrape_run import ScrapeRun
from app.models.user import Territory
from app.services.lead_service import get_dashboard_stats, get_leads
from app.services.commission import compute_pipeline_value
from app.schemas.lead import LeadOut

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats")
async def stats(db: AsyncSession = Depends(get_db)):
    return await get_dashboard_stats(db)


@router.get("/recent")
async def recent_leads(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    leads, _ = await get_leads(db, page=1, per_page=limit)
    return [LeadOut.from_lead(l) for l in leads]


@router.get("/scrape-runs")
async def scrape_runs(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ScrapeRun).order_by(ScrapeRun.started_at.desc()).limit(limit)
    )
    runs = result.scalars().all()
    return [
        {
            "id": r.id,
            "site": r.site,
            "postal_code": r.postal_code,
            "status": r.status,
            "listings_found": r.listings_found,
            "listings_new": r.listings_new,
            "listings_dedup": r.listings_dedup,
            "error_message": r.error_message,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
        }
        for r in runs
    ]


@router.get("/pipeline-value")
async def pipeline_value(
    commission_rate: float = Query(5.0, ge=0, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    Calcule la valeur du pipeline par colonne Kanban.
    Retourne le CA potentiel cumulé par statut.
    """
    result = await db.execute(
        select(Lead.status, Listing.price)
        .join(Listing)
        .where(Lead.status != "archive")
    )
    leads_data = [(row[0], row[1]) for row in result.all()]

    pipeline = compute_pipeline_value(
        leads_data,
        commission_type="fixed",
        commission_rate=commission_rate,
    )

    total_commission = sum(col["total_commission"] for col in pipeline.values())
    total_value = sum(col["total_value"] for col in pipeline.values())

    return {
        "pipeline": pipeline,
        "totaux": {
            "leads_actifs": sum(col["count"] for col in pipeline.values()),
            "valeur_biens": total_value,
            "ca_potentiel": total_commission,
            "taux_applique": commission_rate,
        },
    }


@router.get("/territoire")
async def territoire_dashboard(
    db: AsyncSession = Depends(get_db),
):
    """
    Dashboard territoire : leads 24h, zones exclusives, activité par zone.
    """
    now = datetime.utcnow()
    h24 = now - timedelta(hours=24)

    # Leads créés dans les 24h
    result_24h = await db.execute(
        select(func.count(Lead.id)).where(Lead.created_at >= h24)
    )
    leads_24h = result_24h.scalar() or 0

    # Leads par code postal (dernières 24h)
    result_by_cp = await db.execute(
        select(Listing.postal_code, func.count(Lead.id))
        .join(Listing)
        .where(Lead.created_at >= h24)
        .group_by(Listing.postal_code)
    )
    leads_by_cp = {row[0]: row[1] for row in result_by_cp.all()}

    # Zones exclusives attribuées
    result_territories = await db.execute(
        select(Territory).where(Territory.is_active == True)
    )
    territories = [
        {
            "postal_code": t.postal_code,
            "user_id": t.user_id,
            "assigned_at": t.assigned_at.isoformat() if t.assigned_at else None,
        }
        for t in result_territories.scalars()
    ]

    # Zones les plus actives (par nombre total de leads)
    result_top = await db.execute(
        select(Listing.postal_code, func.count(Lead.id).label("count"))
        .join(Listing)
        .group_by(Listing.postal_code)
        .order_by(func.count(Lead.id).desc())
        .limit(10)
    )
    top_zones = [{"postal_code": row[0], "total_leads": row[1]} for row in result_top.all()]

    return {
        "leads_24h": leads_24h,
        "leads_par_zone_24h": leads_by_cp,
        "zones_exclusives": territories,
        "top_zones": top_zones,
    }
