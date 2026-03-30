from __future__ import annotations

import re
import json
import structlog
from playwright.async_api import async_playwright, Page

from scraper.base import BaseScraper
from scraper.models import ScrapedListing
from scraper.anti_bot import AntiBotManager

logger = structlog.get_logger()


class LeboncoinScraper(BaseScraper):
    """
    Leboncoin.fr - Le plus gros site d'annonces en France.
    Protege par Datadome - utilise Playwright + interception API.
    Filtre les annonces pro via owner_type et badges.
    """
    site_key = "leboncoin"
    site_name = "Leboncoin.fr"
    requires_playwright = True
    base_url = "https://www.leboncoin.fr"

    def _build_search_url(self, postal_code: str, page: int = 1) -> str:
        return (
            f"{self.base_url}/recherche?category=9&locations={postal_code}"
            f"&real_estate_type=1,2&owner_type=private&page={page}"
        )

    async def scrape(
        self, postal_code: str, transaction_type: str = "vente"
    ) -> list[ScrapedListing]:
        results: list[ScrapedListing] = []
        viewport = self.anti_bot.random_viewport()
        api_data: list[dict] = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=self.anti_bot.random_ua(),
                viewport={"width": viewport[0], "height": viewport[1]},
                locale="fr-FR",
                timezone_id="Europe/Paris",
            )
            page = await context.new_page()

            # Intercept API responses to get structured JSON
            async def handle_response(response):
                url = response.url
                if "api.leboncoin.fr/finder/search" in url or "api/adfinder" in url:
                    try:
                        data = await response.json()
                        if "ads" in data:
                            api_data.extend(data["ads"])
                    except Exception:
                        pass

            page.on("response", handle_response)

            try:
                page_num = 1
                max_pages = 3

                while page_num <= max_pages:
                    url = self._build_search_url(postal_code, page_num)
                    logger.info("scraping_page", site="leboncoin", url=url, page=page_num)

                    await self.anti_bot.delay()
                    response = await page.goto(url, wait_until="networkidle", timeout=45000)

                    if not response or response.status != 200:
                        logger.warning("page_failed", url=url, status=response.status if response else None)
                        break

                    await page.wait_for_timeout(3000)

                    # If API interception worked, use structured data
                    if api_data:
                        for ad in api_data:
                            listing = self._parse_api_ad(ad, postal_code)
                            if listing:
                                results.append(listing)
                        api_data.clear()
                    else:
                        # Fallback to HTML parsing
                        listings = await self._parse_html(page, postal_code)
                        results.extend(listings)

                    if not results:
                        break

                    logger.info("page_scraped", page=page_num, count=len(results))
                    page_num += 1

            except Exception as e:
                logger.error("scrape_failed", site="leboncoin", error=str(e))
            finally:
                await browser.close()

        logger.info("scrape_complete", site="leboncoin", total=len(results))
        return results

    def _parse_api_ad(self, ad: dict, postal_code: str) -> ScrapedListing | None:
        """Parse une annonce depuis l'API JSON Leboncoin."""
        # Filtrer les pros
        owner = ad.get("owner", {})
        if owner.get("type") == "pro":
            return None
        if ad.get("owner_type") == "pro":
            return None

        # Extraire les attributs
        attrs = {}
        for attr in ad.get("attributes", []):
            attrs[attr.get("key", "")] = attr.get("value", "")

        price_list = ad.get("price", [])
        price = price_list[0] if price_list else None

        surface = None
        if "square" in attrs:
            try:
                surface = float(attrs["square"])
            except (ValueError, TypeError):
                pass

        rooms = None
        if "rooms" in attrs:
            try:
                rooms = int(attrs["rooms"])
            except (ValueError, TypeError):
                pass

        # Location
        location = ad.get("location", {})
        city = location.get("city")
        cp = location.get("zipcode", postal_code)

        # Type de bien
        property_type = None
        re_type = attrs.get("real_estate_type", "").lower()
        if "appartement" in re_type or re_type == "1":
            property_type = "appartement"
        elif "maison" in re_type or re_type == "2":
            property_type = "maison"
        elif "terrain" in re_type:
            property_type = "terrain"

        ad_url = ad.get("url", "")
        if not ad_url.startswith("http"):
            ad_url = f"{self.base_url}{ad_url}"

        return ScrapedListing(
            source_site="leboncoin",
            source_url=ad_url,
            source_id=str(ad.get("list_id", "")),
            title=ad.get("subject", ""),
            price=price,
            surface_m2=surface,
            nb_rooms=rooms,
            property_type=property_type,
            transaction_type="vente",
            description=ad.get("body", "")[:2000],
            postal_code=cp,
            city=city,
            department=cp[:2],
            seller_name=owner.get("name"),
            image_urls=[img.get("urls", {}).get("default", "") for img in ad.get("images", {}).get("urls_large", [])[:5]],
        )

    async def _parse_html(self, page: Page, postal_code: str) -> list[ScrapedListing]:
        """Fallback HTML parsing si l'interception API echoue."""
        results: list[ScrapedListing] = []

        card_selectors = [
            "a[data-qa-id='aditem_container']",
            "article[data-qa-id='aditem_container']",
            "[class*='adCard']",
            "[data-test-id='ad']",
        ]

        cards = []
        for selector in card_selectors:
            cards = await page.query_selector_all(selector)
            if cards:
                break

        for card in cards:
            try:
                text = await card.inner_text()
                text_lower = text.lower()

                # Filtrer les pros
                if "pro" in text_lower and "particulier" not in text_lower:
                    continue

                href = await card.get_attribute("href")
                if not href:
                    link = await card.query_selector("a")
                    href = await link.get_attribute("href") if link else None
                if not href:
                    continue

                source_url = href if href.startswith("http") else f"{self.base_url}{href}"

                # Parse text content
                lines = [l.strip() for l in text.split("\n") if l.strip()]
                title = lines[0] if lines else ""
                price = None
                for line in lines:
                    p = self.normalize_price(line)
                    if p and p > 10000:
                        price = p
                        break

                surface = self._extract_val(text, r"(\d+)\s*m[²2]")
                rooms = self._extract_val(text, r"(\d+)\s*pi[eè]ce")

                if title:
                    results.append(ScrapedListing(
                        source_site="leboncoin",
                        source_url=source_url,
                        title=title,
                        price=price,
                        surface_m2=float(surface) if surface else None,
                        nb_rooms=surface,
                        postal_code=postal_code,
                        department=postal_code[:2],
                        transaction_type="vente",
                    ))
            except Exception as e:
                logger.warning("card_parse_error", error=str(e))

        return results

    @staticmethod
    def _extract_val(text: str, pattern: str) -> int | None:
        m = re.search(pattern, text, re.IGNORECASE)
        return int(m.group(1)) if m else None
