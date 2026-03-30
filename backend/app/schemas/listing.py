from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel


class ListingOut(BaseModel):
    id: int
    source_site: str
    source_url: str
    title: str
    price: int | None
    surface_m2: float | None
    nb_rooms: int | None
    nb_bedrooms: int | None
    property_type: str | None
    transaction_type: str
    description: str | None
    postal_code: str
    city: str | None
    department: str | None
    seller_name: str | None
    seller_phone: str | None
    seller_email: str | None
    image_urls: list[str]
    publication_date: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
