from __future__ import annotations

import re
import structlog
from playwright.async_api import async_playwright, Page

from scraper.base import BaseScraper
from scraper.models import ScrapedListing
from scraper.anti_bot import AntiBotManager

logger = structlog.get_logger()


class AVendreALouerScraper(BaseScraper):
    """AVendreALouer.fr - Annonces immobilieres, filtre particulier."""
    site_key = "avendrealouer"
    site_name = "AVendreALouer.fr"
    requires_playwright = True
    base_url = "https://www.avendrealouer.fr"

    def _build_search_url(self, postal_code: str, page: int = 1) -> str:
        url = f"{self.base_url}/recherche.html?pageIndex={page}&typeTransaction=acheter&localisation={postal_code}"
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
                max_pages = 3

                while page_num <= max_pages:
                    url = self._build_search_url(postal_code, page_num)
                    logger.info("scraping_page", site="avendrealouer", url=url, page=page_num)

                    await self.anti_bot.delay()
                    response = await page.goto(url, wait_until="domcontentloaded", timeout=30000)

                    if not response or response.status != 200:
                        break

                    await page.wait_for_timeout(2000)

                    listings = await self._parse_page(page, postal_code)
                    if not listings:
                        break

                    results.extend(listings)
                    logger.info("page_scraped", page=page_num, count=len(listings))

                    has_next = await page.query_selector("a[rel='next'], [class*='next'], .pagination .next")
                    if not has_next:
                        break
                    page_num += 1

            except Exception as e:
                logger.error("scrape_failed", site="avendrealouer", error=str(e))
            finally:
                await browser.close()

        logger.info("scrape_complete", site="avendrealouer", total=len(results))
        return results

    async def _parse_page(self, page: Page, postal_code: str) -> list[ScrapedListing]:
        results: list[ScrapedListing] = []

        cards = await page.query_selector_all(
            "[class*='adListItem'], [class*='listing-item'], article[class*='ad'], .resultList > div"
        )

        for card in cards:
            try:
                text = await card.inner_text()
                text_lower = text.lower()

                # Filtrage pro
                if any(kw in text_lower for kw in ["agence", "professionnel", "mandataire", "honoraires"]):
                    if "particulier" not in text_lower:
                        continue
                if self.has_siren(text):
                    continue

                link = await card.query_selector("a[href*='annonce'], a[href*='detail']")
                if not link:
                    link = await card.query_selector("a")
                href = await link.get_attribute("href") if link else None
                if not href:
                    continue

                source_url = href if href.startswith("http") else f"{self.base_url}{href}"

                title_el = await card.query_selector("h2, h3, [class*='title']")
                title = (await title_el.inner_text()).strip() if title_el else ""

                price = None
                price_el = await card.query_selector("[class*='price'], [class*='prix']")
                if price_el:
                    price = self.normalize_price(await price_el.inner_text())

                surface = None
                m = re.search(r"(\d+[\.,]?\d*)\s*m", text)
                if m:
                    surface = float(m.group(1).replace(",", "."))

                rooms = None
                m = re.search(r"(\d+)\s*pi[eè]ce", text, re.IGNORECASE)
                if m:
                    rooms = int(m.group(1))

                property_type = None
                if "appartement" in text_lower:
                    property_type = "appartement"
                elif "maison" in text_lower:
                    property_type = "maison"

                if title:
                    results.append(ScrapedListing(
                        source_site="avendrealouer",
                        source_url=source_url,
                        title=title,
                        price=price,
                        surface_m2=surface,
                        nb_rooms=rooms,
                        property_type=property_type,
                        postal_code=postal_code,
                        department=postal_code[:2],
                        transaction_type="vente",
                    ))
            except Exception as e:
                logger.warning("card_parse_error", error=str(e))

        return results
