from __future__ import annotations

import json
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING

from sqlalchemy import Index, Text, Integer, Float, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.lead import Lead


class Listing(Base):
    __tablename__ = "listings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source_site: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    source_id: Mapped[Optional[str]] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[Optional[int]] = mapped_column(Integer)
    surface_m2: Mapped[Optional[float]] = mapped_column(Float)
    nb_rooms: Mapped[Optional[int]] = mapped_column(Integer)
    nb_bedrooms: Mapped[Optional[int]] = mapped_column(Integer)
    property_type: Mapped[Optional[str]] = mapped_column(Text)
    transaction_type: Mapped[str] = mapped_column(Text, default="vente")
    description: Mapped[Optional[str]] = mapped_column(Text)
    postal_code: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    city: Mapped[Optional[str]] = mapped_column(Text)
    department: Mapped[Optional[str]] = mapped_column(Text)
    seller_name: Mapped[Optional[str]] = mapped_column(Text)
    seller_phone: Mapped[Optional[str]] = mapped_column(Text)
    seller_email: Mapped[Optional[str]] = mapped_column(Text)
    _image_urls: Mapped[Optional[str]] = mapped_column("image_urls", Text)
    publication_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    scraped_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    dedup_hash: Mapped[Optional[str]] = mapped_column(Text, index=True)
    _alternate_urls: Mapped[Optional[str]] = mapped_column("alternate_urls", Text)  # JSON: [{site, url}]
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    lead: Mapped[Optional[Lead]] = relationship(back_populates="listing", uselist=False)

    @property
    def image_urls(self) -> List[str]:
        if self._image_urls:
            return json.loads(self._image_urls)
        return []

    @image_urls.setter
    def image_urls(self, value: List[str]):
        self._image_urls = json.dumps(value)

    @property
    def alternate_urls(self) -> List[dict]:
        if self._alternate_urls:
            return json.loads(self._alternate_urls)
        return []

    @alternate_urls.setter
    def alternate_urls(self, value: List[dict]):
        self._alternate_urls = json.dumps(value, ensure_ascii=False)

    def add_alternate_url(self, site: str, url: str):
        urls = self.alternate_urls
        if not any(u.get("url") == url for u in urls):
            urls.append({"site": site, "url": url})
            self.alternate_urls = urls

    __table_args__ = (
        Index("ix_listings_source_site", "source_site"),
        Index("ix_listings_dedup", "dedup_hash", "postal_code"),
    )
