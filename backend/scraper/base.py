from __future__ import annotations

from abc import ABC, abstractmethod
import re

from scraper.models import ScrapedListing
from scraper.anti_bot import AntiBotManager


class BaseScraper(ABC):
    site_key: str = ""
    site_name: str = ""
    requires_playwright: bool = False

    def __init__(self, anti_bot: AntiBotManager):
        self.anti_bot = anti_bot

    @abstractmethod
    async def scrape(
        self, postal_code: str, transaction_type: str = "vente"
    ) -> list[ScrapedListing]:
        ...

    def is_private_seller(self, raw_data: dict) -> bool:
        return True

    @staticmethod
    def normalize_price(raw: str) -> int | None:
        if not raw:
            return None
        digits = re.sub(r"[^\d]", "", raw)
        return int(digits) if digits else None

    @staticmethod
    def normalize_surface(raw: str) -> float | None:
        if not raw:
            return None
        match = re.search(r"([\d.,]+)", raw.replace(",", "."))
        return float(match.group(1)) if match else None

    @staticmethod
    def has_siren(text: str) -> bool:
        siren_pattern = re.compile(r"\b\d{3}\s?\d{3}\s?\d{3}\b")
        return bool(siren_pattern.search(text))
