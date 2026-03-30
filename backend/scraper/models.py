from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ScrapedListing:
    source_site: str
    source_url: str
    title: str
    postal_code: str
    source_id: str | None = None
    price: int | None = None
    surface_m2: float | None = None
    nb_rooms: int | None = None
    nb_bedrooms: int | None = None
    property_type: str | None = None
    transaction_type: str = "vente"
    description: str | None = None
    city: str | None = None
    department: str | None = None
    seller_name: str | None = None
    seller_phone: str | None = None
    seller_email: str | None = None
    image_urls: list[str] = field(default_factory=list)
    publication_date: datetime | None = None
