from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel

from app.schemas.listing import ListingOut


class UrgencyOut(BaseModel):
    score: int | None = None
    level: str | None = None
    factors: list[str] = []


class PriceGapOut(BaseModel):
    gap_pct: float | None = None
    price_m2_market: float | None = None
    comment: str | None = None


class ChronologyOut(BaseModel):
    type: str | None = None
    days_on_market: int | None = None
    previous_price: int | None = None
    comment: str | None = None


class StrategicOut(BaseModel):
    priority: str | None = None
    angle: str | None = None
    sms_script: str | None = None


class LeadOut(BaseModel):
    id: int
    listing_id: int
    status: str
    notes: str | None
    last_contacted_at: datetime | None
    last_interaction_at: datetime
    auto_purge_at: datetime
    created_at: datetime
    is_suspicious: bool | None = False
    commission_amount: int | None = None
    commission_rate: float | None = None
    listing: ListingOut | None = None

    # Analyses premium
    urgency: UrgencyOut | None = None
    price_gap: PriceGapOut | None = None
    chronology: ChronologyOut | None = None
    strategic: StrategicOut | None = None

    model_config = {"from_attributes": True}

    @classmethod
    def from_lead(cls, lead) -> LeadOut:
        import json

        urgency_factors = []
        if lead.urgency_factors:
            try:
                urgency_factors = json.loads(lead.urgency_factors)
            except (json.JSONDecodeError, TypeError):
                pass

        return cls(
            id=lead.id,
            listing_id=lead.listing_id,
            status=lead.status,
            notes=lead.notes,
            last_contacted_at=lead.last_contacted_at,
            last_interaction_at=lead.last_interaction_at,
            auto_purge_at=lead.auto_purge_at,
            created_at=lead.created_at,
            is_suspicious=lead.is_suspicious,
            commission_amount=lead.commission_amount,
            commission_rate=lead.commission_rate,
            listing=ListingOut.model_validate(lead.listing) if lead.listing else None,
            urgency=UrgencyOut(
                score=lead.urgency_score,
                level=lead.urgency_level,
                factors=urgency_factors,
            ),
            price_gap=PriceGapOut(
                gap_pct=lead.price_gap_pct,
                price_m2_market=lead.price_m2_market,
                comment=lead.price_gap_comment,
            ),
            chronology=ChronologyOut(
                type=lead.chronology_type,
                days_on_market=lead.days_on_market,
                previous_price=lead.previous_price,
                comment=lead.chronology_comment,
            ),
            strategic=StrategicOut(
                priority=lead.strategic_priority,
                angle=lead.strategic_angle,
                sms_script=lead.strategic_sms,
            ),
        )


class LeadStatusUpdate(BaseModel):
    status: str


class LeadUpdate(BaseModel):
    notes: str | None = None
    last_contacted_at: datetime | None = None
    strategic_sms: str | None = None


class LeadBulkStatusUpdate(BaseModel):
    ids: list[int]
    status: str
