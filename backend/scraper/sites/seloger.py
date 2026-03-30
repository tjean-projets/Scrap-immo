from __future__ import annotations

import re
import json
import structlog
from playwright.async_api import async_playwright, Page

from scraper.base import BaseScraper
from scraper.models import ScrapedListing
from scraper.anti_bot import AntiBotManager

logger = structlog.get_logger()


class SeLogerScraper(BaseScraper):
    """
    SeLoger.fr - Tres protege (Datadome).
    Utilise Playwright + interception API pour contourner.
    Filtre les pros via idTypeProfessionnel.
    """
    site_key = "seloger"
    site_name = "SeLoger.fr"
    requires_playwright = True
    base_url = "https://www.seloger.com"

    def _build_search_url(self, postal_code: str, page: int = 1) -> str:
        return (
            f"{self.base_url}/list.htm"
            f"?tri=d_dt_crea&idtt=2&cp={postal_code}&page={page}"
        )

    async def scrape(
        self, postal_code: str, transaction_type: str = "vente"
    ) -> list[ScrapedListing]:
        results: list[ScrapedListing] = []
        viewport = self.anti_bot.random_viewport()
        api_cards: list[dict] = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=self.anti_bot.random_ua(),
                viewport={"width": viewport[0], "height": viewport[1]},
                locale="fr-FR",
                timezone_id="Europe/Paris",
            )
            page = await context.new_page()

            # Intercept SeLoger API
            async def handle_response(response):
                url = response.url
                if any(k in url for k in ["api/search", "search-api", "listing/search", "v1/listings"]):
                    try:
                        data = await response.json()
                        items = data.get("items", data.get("cards", data.get("results", [])))
                        if isinstance(items, list):
                            api_cards.extend(items)
                    except Exception:
                        pass

            page.on("response", handle_response)

            try:
                url = self._build_search_url(postal_code)
                logger.info("scraping_page", site="seloger", url=url)

                await self.anti_bot.delay()
                await page.goto(url, wait_until="networkidle", timeout=60000)
                await page.wait_for_timeout(4000)

                if api_cards:
                    for card in api_cards:
                        listing = self._parse_api_card(card, postal_code)
                        if listing:
                            results.append(listing)
                else:
                    results = await self._parse_html(page, postal_code)

            except Exception as e:
                logger.error("scrape_failed", site="seloger", error=str(e))
            finally:
                await browser.close()

        logger.info("scrape_complete", site="seloger", total=len(results))
        return results

    def _parse_api_card(self, card: dict, postal_code: str) -> ScrapedListing | None:
        # Filtrer les pros
        if card.get("idTypeProfessionnel") or card.get("professional"):
            return None
        contact = card.get("contact", {})
        if contact.get("agencyId") or contact.get("type") == "agency":
            return None

        price = card.get("pricing", {}).get("price") or card.get("price")
        surface = card.get("livingArea") or card.get("surface")
        rooms = card.get("rooms") or card.get("nbRooms")
        bedrooms = card.get("bedrooms") or card.get("nbBedrooms")

        prop_type = card.get("propertyType", "").lower()
        property_type = None
        if "appartement" in prop_type or prop_type == "1":
            property_type = "appartement"
        elif "maison" in prop_type or prop_type == "2":
            property_type = "maison"

        city = card.get("city") or card.get("cityLabel")
        cp = card.get("zipCode", postal_code)
        title = card.get("title", f"{property_type or 'Bien'} {city or cp}")

        ad_id = card.get("id", card.get("classifiedId", ""))
        detail_url = card.get("permalink", card.get("classifiedURL", ""))
        if not detail_url:
            detail_url = f"{self.base_url}/annonces/achat/{ad_id}.htm"

        return ScrapedListing(
            source_site="seloger",
            source_url=detail_url,
            source_id=str(ad_id),
            title=title,
            price=price,
            surface_m2=surface,
            nb_rooms=rooms,
            nb_bedrooms=bedrooms,
            property_type=property_type,
            transaction_type="vente",
            description=card.get("description", "")[:2000],
            postal_code=cp,
            city=city,
            department=cp[:2] if cp else postal_code[:2],
        )

    async def _parse_html(self, page: Page, postal_code: str) -> list[ScrapedListing]:
        results: list[ScrapedListing] = []

        cards = await page.query_selector_all(
            "[class*='ListContent'] > div, [class*='classified'], article"
        )

        for card in cards:
            try:
                text = await card.inner_text()
                if not text.strip() or len(text) < 20:
                    continue

                # Skip pro ads
                text_lower = text.lower()
                if any(kw in text_lower for kw in ["agence", "professionnel", "mandat"]):
                    if "particulier" not in text_lower:
                        continue

                link = await card.query_selector("a[href*='annonces']")
                if not link:
                    link = await card.query_selector("a")
                href = await link.get_attribute("href") if link else None
                if not href:
                    continue

                source_url = href if href.startswith("http") else f"{self.base_url}{href}"

                title_el = await card.query_selector("h2, [class*='Title'], [class*='title']")
                title = (await title_el.inner_text()).strip() if title_el else text.split("\n")[0][:80]

                price = None
                price_el = await card.query_selector("[class*='Price'], [class*='price']")
                if price_el:
                    price = self.normalize_price(await price_el.inner_text())

                surface = None
                m = re.search(r"(\d+[\.,]?\d*)\s*m", text)
                if m:
                    surface = float(m.group(1).replace(",", "."))

                rooms = None
                m = re.search(r"(\d+)\s*p\b", text)
                if m:
                    rooms = int(m.group(1))

                if title:
                    results.append(ScrapedListing(
                        source_site="seloger",
                        source_url=source_url,
                        title=title,
                        price=price,
                        surface_m2=surface,
                        nb_rooms=rooms,
                        postal_code=postal_code,
                        department=postal_code[:2],
                        transaction_type="vente",
                    ))
            except Exception as e:
                logger.warning("card_parse_error", error=str(e))

        return results
