from __future__ import annotations

from scraper.base import BaseScraper
from scraper.anti_bot import AntiBotManager
from scraper.sites.pap import PapScraper
from scraper.sites.entreparticuliers import EntreparticuliersScraper
from scraper.sites.paruvendu import ParuVenduScraper
from scraper.sites.leboncoin import LeboncoinScraper
from scraper.sites.bienici import BienIciScraper
from scraper.sites.seloger import SeLogerScraper
from scraper.sites.avendrealouer import AVendreALouerScraper
from scraper.sites.logicimmo import LogicImmoScraper

SCRAPERS: dict[str, type[BaseScraper]] = {
    "pap": PapScraper,
    "entreparticuliers": EntreparticuliersScraper,
    "paruvendu": ParuVenduScraper,
    "leboncoin": LeboncoinScraper,
    "bienici": BienIciScraper,
    "seloger": SeLogerScraper,
    "avendrealouer": AVendreALouerScraper,
    "logicimmo": LogicImmoScraper,
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
