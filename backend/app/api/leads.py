from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.lead import LeadOut, LeadStatusUpdate, LeadUpdate, LeadBulkStatusUpdate
from app.services.lead_service import (
    get_leads,
    get_lead,
    update_lead_status,
    update_lead,
    delete_lead,
)

router = APIRouter(prefix="/api/leads", tags=["leads"])


@router.get("", response_model=dict)
async def list_leads(
    status: str | None = None,
    postal_code: str | None = None,
    priority: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    leads, total = await get_leads(db, status, postal_code, page, per_page)
    items = [LeadOut.from_lead(l) for l in leads]

    # Filtrage par priorité côté serveur
    if priority:
        items = [i for i in items if i.strategic and i.strategic.priority == priority]

    return {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/{lead_id}", response_model=LeadOut)
async def read_lead(lead_id: int, db: AsyncSession = Depends(get_db)):
    lead = await get_lead(db, lead_id)
    if not lead:
        raise HTTPException(404, "Lead not found")
    return LeadOut.from_lead(lead)


@router.get("/{lead_id}/notification")
async def get_notification(lead_id: int, db: AsyncSession = Depends(get_db)):
    """Retourne la notification premium JSON complète."""
    lead = await get_lead(db, lead_id)
    if not lead:
        raise HTTPException(404, "Lead not found")
    if lead.notification_json:
        return json.loads(lead.notification_json)
    return {"error": "Pas de notification disponible pour ce lead"}


@router.patch("/{lead_id}", response_model=LeadOut)
async def patch_lead(
    lead_id: int, body: LeadUpdate, db: AsyncSession = Depends(get_db)
):
    lead = await update_lead(db, lead_id, body.notes, body.last_contacted_at)
    if not lead:
        raise HTTPException(404, "Lead not found")
    return LeadOut.from_lead(lead)


@router.patch("/{lead_id}/status", response_model=LeadOut)
async def change_status(
    lead_id: int, body: LeadStatusUpdate, db: AsyncSession = Depends(get_db)
):
    try:
        lead = await update_lead_status(db, lead_id, body.status)
    except ValueError as e:
        raise HTTPException(400, str(e))
    if not lead:
        raise HTTPException(404, "Lead not found")
    return LeadOut.from_lead(lead)


@router.post("/bulk-status")
async def bulk_status(body: LeadBulkStatusUpdate, db: AsyncSession = Depends(get_db)):
    updated = 0
    for lead_id in body.ids:
        try:
            result = await update_lead_status(db, lead_id, body.status)
            if result:
                updated += 1
        except ValueError:
            pass
    return {"updated": updated}


@router.delete("/{lead_id}")
async def remove_lead(lead_id: int, db: AsyncSession = Depends(get_db)):
    deleted = await delete_lead(db, lead_id)
    if not deleted:
        raise HTTPException(404, "Lead not found")
    return {"deleted": True}
