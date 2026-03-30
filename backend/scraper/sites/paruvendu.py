from __future__ import annotations

import re
import structlog
from playwright.async_api import async_playwright, Page

from scraper.base import BaseScraper
from scraper.models import ScrapedListing
from scraper.anti_bot import AntiBotManager

logger = structlog.get_logger()


class ParuVenduScraper(BaseScraper):
    site_key = "paruvendu"
    site_name = "ParuVendu.fr"
    requires_playwright = True
    base_url = "https://www.paruvendu.fr"

    def _build_search_url(self, postal_code: str, page: int = 1) -> str:
        url = (
            f"{self.base_url}/immobilier/vente/maison-appartement/"
            f"?lo={postal_code}&tt=1&tbApp=1&tbMai=1"
        )
        if page > 1:
            url += f"&p={page}"
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
                    logger.info("scraping_page", site="paruvendu", url=url, page=page_num)

                    await self.anti_bot.delay()
                    response = await page.goto(url, wait_until="domcontentloaded", timeout=30000)

                    if not response or response.status != 200:
                        logger.warning("page_failed", url=url, status=response.status if response else None)
                        break

                    await page.wait_for_timeout(2000)

                    # Handle cookie banner
                    try:
                        cookie_btn = await page.query_selector(
                            "button[id*='accept'], button[class*='accept'], #didomi-notice-agree-button"
                        )
                        if cookie_btn:
                            await cookie_btn.click()
                            await page.wait_for_timeout(500)
                    except Exception:
                        pass

                    listings = await self._parse_search_page(page, postal_code)
                    if not listings:
                        break

                    results.extend(listings)
                    logger.info("page_scraped", page=page_num, count=len(listings))

                    has_next = await page.query_selector(
                        "a[class*='next'], a[title*='Suivant'], .pagination a:last-child"
                    )
                    if not has_next:
                        break

                    page_num += 1

            except Exception as e:
                logger.error("scrape_failed", site="paruvendu", error=str(e))
            finally:
                await browser.close()

        logger.info("scrape_complete", site="paruvendu", total=len(results))
        return results

    async def _parse_search_page(
        self, page: Page, postal_code: str
    ) -> list[ScrapedListing]:
        results: list[ScrapedListing] = []

        card_selectors = [
            "div[class*='ergov3-annonce']",
            "div[class*='annonce']",
            "li[class*='annonce']",
            "article[class*='annonce']",
            "div.lazyload",
        ]

        cards = []
        for selector in card_selectors:
            cards = await page.query_selector_all(selector)
            if cards:
                logger.info("found_cards", selector=selector, count=len(cards))
                break

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
        # Check if this is a "particulier" listing
        full_text = await card.inner_text()
        text_lower = full_text.lower()

        # ParuVendu marks pro listings - reject them
        if any(kw in text_lower for kw in ["professionnel", "agence", "négociateur", "mandat"]):
            if "particulier" not in text_lower:
                return None

        # Extract link
        link_el = await card.query_selector("a[href*='/immobilier/']")
        if not link_el:
            link_el = await card.query_selector("a")
        href = await link_el.get_attribute("href") if link_el else None
        if not href:
            return None

        source_url = href if href.startswith("http") else f"{self.base_url}{href}"

        # ID from URL
        source_id = None
        id_match = re.search(r"[-/](\d{6,})", href)
        if id_match:
            source_id = id_match.group(1)

        # Title
        title = ""
        for sel in ["h3", "h2", "[class*='title']", "[class*='titre']", "a[class*='title']"]:
            el = await card.query_selector(sel)
            if el:
                title = (await el.inner_text()).strip()
                if title and len(title) > 3:
                    break

        # Price
        price = None
        for sel in ["[class*='price']", "[class*='prix']", "span.price", "strong"]:
            el = await card.query_selector(sel)
            if el:
                price = self.normalize_price(await el.inner_text())
                if price:
                    break

        # Location
        city = None
        for sel in ["[class*='location']", "[class*='localisation']", "[class*='ville']"]:
            el = await card.query_selector(sel)
            if el:
                city = (await el.inner_text()).strip()
                if city:
                    break

        # Surface / rooms from text
        surface = self._extract_surface(full_text)
        nb_rooms = self._extract_rooms(full_text)
        property_type = self._extract_property_type(full_text)

        if not title:
            return None

        return ScrapedListing(
            source_site="paruvendu",
            source_url=source_url,
            source_id=source_id,
            title=title,
            price=price,
            surface_m2=surface,
            nb_rooms=nb_rooms,
            property_type=property_type,
            transaction_type="vente",
            postal_code=postal_code,
            city=city,
            department=postal_code[:2],
        )

    @staticmethod
    def _extract_surface(text: str) -> float | None:
        match = re.search(r"(\d+[\.,]?\d*)\s*m[²2]", text, re.IGNORECASE)
        return float(match.group(1).replace(",", ".")) if match else None

    @staticmethod
    def _extract_rooms(text: str) -> int | None:
        if "studio" in text.lower():
            return 1
        match = re.search(r"(\d+)\s*pi[èe]ce", text, re.IGNORECASE)
        return int(match.group(1)) if match else None

    @staticmethod
    def _extract_property_type(text: str) -> str | None:
        t = text.lower()
        if "appartement" in t:
            return "appartement"
        if "maison" in t:
            return "maison"
        if "terrain" in t:
            return "terrain"
        if "studio" in t:
            return "appartement"
        return None
