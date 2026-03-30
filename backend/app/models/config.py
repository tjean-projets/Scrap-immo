from __future__ import annotations

import json

from sqlalchemy import Text, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ScrapingConfig(Base):
    __tablename__ = "scraping_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    _postal_codes: Mapped[str] = mapped_column("postal_codes", Text, default='["75001"]')
    _schedule_hours: Mapped[str] = mapped_column("schedule_hours", Text, default="[8,13,19]")
    _enabled_sites: Mapped[str] = mapped_column("enabled_sites", Text, default='["pap"]')
    _transaction_types: Mapped[str] = mapped_column(
        "transaction_types", Text, default='["vente"]'
    )

    @property
    def postal_codes(self) -> list[str]:
        return json.loads(self._postal_codes)

    @postal_codes.setter
    def postal_codes(self, value: list[str]):
        self._postal_codes = json.dumps(value)

    @property
    def schedule_hours(self) -> list[int]:
        return json.loads(self._schedule_hours)

    @schedule_hours.setter
    def schedule_hours(self, value: list[int]):
        self._schedule_hours = json.dumps(value)

    @property
    def enabled_sites(self) -> list[str]:
        return json.loads(self._enabled_sites)

    @enabled_sites.setter
    def enabled_sites(self, value: list[str]):
        self._enabled_sites = json.dumps(value)

    @property
    def transaction_types(self) -> list[str]:
        return json.loads(self._transaction_types)

    @transaction_types.setter
    def transaction_types(self, value: list[str]):
        self._transaction_types = json.dumps(value)
