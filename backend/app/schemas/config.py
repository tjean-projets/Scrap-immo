from __future__ import annotations

from pydantic import BaseModel


class ScrapingConfigOut(BaseModel):
    postal_codes: list[str]
    schedule_hours: list[int]
    enabled_sites: list[str]
    transaction_types: list[str]


class ScrapingConfigUpdate(BaseModel):
    postal_codes: list[str] | None = None
    schedule_hours: list[int] | None = None
    enabled_sites: list[str] | None = None
    transaction_types: list[str] | None = None
