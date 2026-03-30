from __future__ import annotations

import re
import structlog
from playwright.async_api import async_playwright, Page

from scraper.base import BaseScraper
from scraper.models import ScrapedListing
from scraper.anti_bot import AntiBotManager

logger = structlog.get_logger()

# Mapping arrondissements Paris
PARIS_ARRONDISSEMENTS = {
    "75001": "paris-1er",
    "75002": "paris-2e",
    "75003": "paris-3e",
    "75004": "paris-4e",
    "75005": "paris-5e",
    "75006": "paris-6e",
    "75007": "paris-7e",
    "75008": "paris-8e",
    "75009": "paris-9e",
    "75010": "paris-10e",
    "75011": "paris-11e",
    "75012": "paris-12e",
    "75013": "paris-13e",
    "75014": "paris-14e",
    "75015": "paris-15e",
    "75016": "paris-16e",
    "75017": "paris-17e",
    "75018": "paris-18e",
    "75019": "paris-19e",
    "75020": "paris-20e",
}


class PapScraper(BaseScraper):
    site_key = "pap"
    site_name = "PAP.fr"
    requires_playwright = True
    base_url = "https://www.pap.fr"

    def _build_search_url(self, postal_code: str, page: int = 1) -> str:
        slug = PARIS_ARRONDISSEMENTS.get(postal_code, postal_code)
        url = f"{self.base_url}/annonce/vente-immobiliere-{slug}-{postal_code}"
        if page > 1:
            url += f"-{page}"
        return url

    async def scrape(
        self, postal_code: str, transaction_type: str = "vente"
    ) -> list[ScrapedListing]:
        results: list[ScrapedListing] = []
        viewport = self.anti_bot.random_viewport()

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=self.anti_bot.random_ua(),
                viewport={"width": viewport[0], "height": viewport[1]},
                locale="fr-FR",
                timezone_id="Europe/Paris",
            )
            page = await context.new_page()

            try:
                page_num = 1
                max_pages = 5

                while page_num <= max_pages:
                    url = self._build_search_url(postal_code, page_num)
                    logger.info("scraping_page", site="pap", url=url, page=page_num)

                    await self.anti_bot.delay()
                    response = await page.goto(url, wait_until="domcontentloaded", timeout=30000)

                    if not response or response.status != 200:
                        logger.warning("page_failed", url=url, status=response.status if response else None)
                        break

                    # Wait for listings to load
                    await page.wait_for_timeout(2000)

                    listings = await self._parse_search_page(page, postal_code)
                    if not listings:
                        logger.info("no_more_listings", page=page_num)
                        break

                    results.extend(listings)
                    logger.info("page_scraped", page=page_num, count=len(listings))

                    # Check if there's a next page
                    has_next = await page.query_selector("a.next, a[rel='next'], .pagination a:last-child")
                    if not has_next:
                        break

                    page_num += 1

            except Exception as e:
                logger.error("scrape_failed", site="pap", error=str(e))
            finally:
                await browser.close()

        logger.info("scrape_complete", site="pap", total=len(results))
        return results

    async def _parse_search_page(
        self, page: Page, postal_code: str
    ) -> list[ScrapedListing]:
        results: list[ScrapedListing] = []

        # Try multiple selectors for listing cards (PAP updates their HTML)
        card_selectors = [
            "div.search-results-item",
            "div[class*='search-list-item']",
            "article[class*='annonce']",
            "li.detail",
        ]

        cards = []
        for selector in card_selectors:
            cards = await page.query_selector_all(selector)
            if cards:
                logger.info("found_cards", selector=selector, count=len(cards))
                break

        if not cards:
            # Fallback: try to find any listing-like links
            logger.warning("no_cards_found", selectors=card_selectors)
            return results

        for card in cards:
            try:
                listing = await self._parse_card(card, page, postal_code)
                if listing:
                    results.append(listing)
            except Exception as e:
                logger.warning("card_parse_error", error=str(e))
                continue

        return results

    async def _parse_card(
        self, card, page: Page, postal_code: str
    ) -> ScrapedListing | None:
        # Extract link to detail page
        link_el = await card.query_selector("a[href*='/annonces/']")
        if not link_el:
            link_el = await card.query_selector("a[href*='/annonce/']")
        if not link_el:
            link_el = await card.query_selector("a")

        href = await link_el.get_attribute("href") if link_el else None
        if not href:
            return None

        source_url = href if href.startswith("http") else f"{self.base_url}{href}"

        # Extract listing ID from URL
        source_id = None
        id_match = re.search(r"-r(\d+)", href)
        if id_match:
            source_id = id_match.group(1)

        # Extract title
        title = ""
        for sel in ["span.h1", "h2", "a[class*='title']", "a"]:
            title_el = await card.query_selector(sel)
            if title_el:
                title = (await title_el.inner_text()).strip()
                if title:
                    break

        # Extract price
        price = None
        for sel in ["span.price strong", "span.price", "[class*='price']", "strong"]:
            price_el = await card.query_selector(sel)
            if price_el:
                price_text = await price_el.inner_text()
                price = self.normalize_price(price_text)
                if price:
                    break

        # Extract description / location
        city = None
        desc_el = await card.query_selector("p.item-description, [class*='description']")
        description = ""
        if desc_el:
            description = (await desc_el.inner_text()).strip()
            # Try to extract city from description
            city_el = await desc_el.query_selector("strong")
            if city_el:
                city = (await city_el.inner_text()).strip()

        # Extract surface and rooms from title/description
        combined_text = f"{title} {description}"
        surface = self._extract_surface(combined_text)
        nb_rooms = self._extract_rooms(combined_text)
        property_type = self._extract_property_type(combined_text)

        if not title:
            return None

        return ScrapedListing(
            source_site="pap",
            source_url=source_url,
            source_id=source_id,
            title=title,
            price=price,
            surface_m2=surface,
            nb_rooms=nb_rooms,
            property_type=property_type,
            transaction_type="vente",
            description=description[:2000] if description else None,
            postal_code=postal_code,
            city=city,
            department=postal_code[:2],
        )

    @staticmethod
    def _extract_surface(text: str) -> float | None:
        match = re.search(r"(\d+[\.,]?\d*)\s*m[²2]", text, re.IGNORECASE)
        if match:
            return float(match.group(1).replace(",", "."))
        return None

    @staticmethod
    def _extract_rooms(text: str) -> int | None:
        if "studio" in text.lower():
            return 1
        match = re.search(r"(\d+)\s*pi[èe]ce", text, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return None

    @staticmethod
    def _extract_property_type(text: str) -> str | None:
        text_lower = text.lower()
        if "appartement" in text_lower:
            return "appartement"
        if "maison" in text_lower:
            return "maison"
        if "terrain" in text_lower:
            return "terrain"
        if "studio" in text_lower:
            return "appartement"
        if "loft" in text_lower:
            return "appartement"
        return None
