from __future__ import annotations

from scraper.base import BaseScraper
from scraper.anti_bot import AntiBotManager
from scraper.sites.pap import PapScraper

SCRAPERS: dict[str, type[BaseScraper]] = {
    "pap": PapScraper,
}


def get_scraper(site_key: str, anti_bot: AntiBotManager) -> BaseScraper:
    cls = SCRAPERS.get(site_key)
    if not cls:
        raise ValueError(f"Unknown scraper: {site_key}")
    return cls(anti_bot)


def get_available_sites() -> list[dict[str, str]]:
    return [
        {"key": key, "name": cls.site_name}
        for key, cls in SCRAPERS.items()
    ]
