from __future__ import annotations

import re
import json
import structlog
from playwright.async_api import async_playwright, Page

from scraper.base import BaseScraper
from scraper.models import ScrapedListing
from scraper.anti_bot import AntiBotManager

logger = structlog.get_logger()


class BienIciScraper(BaseScraper):
    """
    Bien'ici - Agregateur immobilier.
    Utilise Playwright + interception de l'API interne pour les donnees structurees.
    Filtre par owner.type == "private".
    """
    site_key = "bienici"
    site_name = "Bien'ici"
    requires_playwright = True
    base_url = "https://www.bienici.com"

    def _build_search_url(self, postal_code: str, page: int = 1) -> str:
        offset = (page - 1) * 24
        return (
            f"{self.base_url}/recherche/achat/{postal_code}"
            f"?page={page}&sortBy=publicationDate-desc"
        )

    async def scrape(
        self, postal_code: str, transaction_type: str = "vente"
    ) -> list[ScrapedListing]:
        results: list[ScrapedListing] = []
        viewport = self.anti_bot.random_viewport()
        api_ads: list[dict] = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=self.anti_bot.random_ua(),
                viewport={"width": viewport[0], "height": viewport[1]},
                locale="fr-FR",
                timezone_id="Europe/Paris",
            )
            page = await context.new_page()

            # Intercept Bien'ici API
            async def handle_response(response):
                url = response.url
                if "realEstateAds" in url or "search/results" in url:
                    try:
                        data = await response.json()
                        ads = data.get("realEstateAds", data.get("ads", []))
                        if isinstance(ads, list):
                            api_ads.extend(ads)
                    except Exception:
                        pass

            page.on("response", handle_response)

            try:
                page_num = 1
                max_pages = 3

                while page_num <= max_pages:
                    url = self._build_search_url(postal_code, page_num)
                    logger.info("scraping_page", site="bienici", url=url, page=page_num)

                    await self.anti_bot.delay()
                    await page.goto(url, wait_until="networkidle", timeout=45000)
                    await page.wait_for_timeout(3000)

                    if api_ads:
                        for ad in api_ads:
                            listing = self._parse_api_ad(ad, postal_code)
                            if listing:
                                results.append(listing)
                        api_ads.clear()
                    else:
                        listings = await self._parse_html(page, postal_code)
                        results.extend(listings)

                    if not results and page_num == 1:
                        break

                    logger.info("page_scraped", page=page_num, count=len(results))
                    page_num += 1

            except Exception as e:
                logger.error("scrape_failed", site="bienici", error=str(e))
            finally:
                await browser.close()

        logger.info("scrape_complete", site="bienici", total=len(results))
        return results

    def _parse_api_ad(self, ad: dict, postal_code: str) -> ScrapedListing | None:
        # Filtrer les pros
        if ad.get("adType") == "professional":
            return None
        if ad.get("accountType") == "agency":
            return None

        ad_id = ad.get("id", "")
        price = ad.get("price")
        surface = ad.get("surfaceArea")
        rooms = ad.get("roomsQuantity")
        bedrooms = ad.get("bedroomsQuantity")

        # Type de bien
        prop_type_raw = ad.get("propertyType", "").lower()
        property_type = None
        if "flat" in prop_type_raw or "appartement" in prop_type_raw:
            property_type = "appartement"
        elif "house" in prop_type_raw or "maison" in prop_type_raw:
            property_type = "maison"
        elif "land" in prop_type_raw or "terrain" in prop_type_raw:
            property_type = "terrain"

        city = ad.get("city")
        cp = ad.get("postalCode", postal_code)
        title = ad.get("title", f"{property_type or 'Bien'} {rooms or ''}p {city or ''}")

        photos = []
        for photo in ad.get("photos", [])[:5]:
            if isinstance(photo, str):
                photos.append(photo)
            elif isinstance(photo, dict):
                photos.append(photo.get("url", photo.get("url_photo", "")))

        return ScrapedListing(
            source_site="bienici",
            source_url=f"{self.base_url}/annonce/{ad_id}",
            source_id=str(ad_id),
            title=title,
            price=price,
            surface_m2=surface,
            nb_rooms=rooms,
            nb_bedrooms=bedrooms,
            property_type=property_type,
            transaction_type="vente",
            description=ad.get("description", "")[:2000],
            postal_code=cp,
            city=city,
            department=cp[:2] if cp else postal_code[:2],
            image_urls=photos,
        )

    async def _parse_html(self, page: Page, postal_code: str) -> list[ScrapedListing]:
        results: list[ScrapedListing] = []

        cards = await page.query_selector_all("article, [class*='RealEstateAd'], [class*='ad-card']")

        for card in cards:
            try:
                text = await card.inner_text()
                if not text.strip():
                    continue

                link = await card.query_selector("a[href*='/annonce/']")
                href = await link.get_attribute("href") if link else None
                if not href:
                    continue

                source_url = href if href.startswith("http") else f"{self.base_url}{href}"

                title_el = await card.query_selector("h2, [class*='title'], [class*='Title']")
                title = (await title_el.inner_text()).strip() if title_el else ""

                price = None
                price_el = await card.query_selector("[class*='price'], [class*='Price']")
                if price_el:
                    price = self.normalize_price(await price_el.inner_text())

                surface = None
                m = re.search(r"(\d+[\.,]?\d*)\s*m", text)
                if m:
                    surface = float(m.group(1).replace(",", "."))

                rooms = None
                m = re.search(r"(\d+)\s*pi", text, re.IGNORECASE)
                if m:
                    rooms = int(m.group(1))

                if title:
                    results.append(ScrapedListing(
                        source_site="bienici",
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
