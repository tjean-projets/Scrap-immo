from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional, TYPE_CHECKING

from sqlalchemy import Text, Integer, Float, DateTime, ForeignKey, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.config import settings

if TYPE_CHECKING:
    from app.models.listing import Listing

LEAD_STATUSES = [
    "nouveau",
    "tentative_appel",
    "rdv_estimation",
    "mandat_signe",
    "archive",
]


def _default_purge_at():
    return datetime.utcnow() + timedelta(days=settings.rgpd_retention_days)


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    listing_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("listings.id", ondelete="CASCADE"), unique=True
    )
    status: Mapped[str] = mapped_column(Text, default="nouveau", index=True)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    last_contacted_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    last_interaction_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    auto_purge_at: Mapped[datetime] = mapped_column(DateTime, default=_default_purge_at)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Analyses premium
    urgency_score: Mapped[Optional[int]] = mapped_column(Integer)
    urgency_level: Mapped[Optional[str]] = mapped_column(Text)
    urgency_factors: Mapped[Optional[str]] = mapped_column(Text)  # JSON
    price_gap_pct: Mapped[Optional[float]] = mapped_column(Float)
    price_m2_market: Mapped[Optional[float]] = mapped_column(Float)
    price_gap_comment: Mapped[Optional[str]] = mapped_column(Text)
    chronology_type: Mapped[Optional[str]] = mapped_column(Text)
    days_on_market: Mapped[Optional[int]] = mapped_column(Integer)
    previous_price: Mapped[Optional[int]] = mapped_column(Integer)
    chronology_comment: Mapped[Optional[str]] = mapped_column(Text)
    strategic_priority: Mapped[Optional[str]] = mapped_column(Text)
    strategic_angle: Mapped[Optional[str]] = mapped_column(Text)
    strategic_sms: Mapped[Optional[str]] = mapped_column(Text)
    is_suspicious: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    notification_json: Mapped[Optional[str]] = mapped_column(Text)  # Full JSON

    # Commission / Business
    commission_amount: Mapped[Optional[int]] = mapped_column(Integer)  # CA potentiel en €
    commission_rate: Mapped[Optional[float]] = mapped_column(Float)

    # Territoire
    territory_user_id: Mapped[Optional[int]] = mapped_column(Integer)

    listing: Mapped[Listing] = relationship(back_populates="lead")

    def touch(self):
        now = datetime.utcnow()
        self.last_interaction_at = now
        self.auto_purge_at = now + timedelta(days=settings.rgpd_retention_days)
