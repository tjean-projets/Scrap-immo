from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import structlog
from blinker import signal

from app.models.listing import Listing
from app.models.lead import Lead
from app.models.config import ScrapingConfig
from app.models.scrape_run import ScrapeRun
from app.services.dedup import compute_dedup_hash
from app.services.analysis.pipeline import run_premium_analysis, PremiumAnalysis
from app.services.commission import compute_commission
from scraper.anti_bot import AntiBotManager
from scraper.registry import get_scraper
from scraper.models import ScrapedListing

logger = structlog.get_logger()

# Event signals for v2 hooks (email, WhatsApp)
lead_created = signal("lead.created")


class ScraperRunner:
    def __init__(self, session_factory):
        self.session_factory = session_factory
        self.anti_bot = AntiBotManager()

    async def run_all(self):
        async with self.session_factory() as session:
            config = await self._get_config(session)
            if not config:
                logger.warning("no_config_found")
                return

            for site_key in config.enabled_sites:
                for postal_code in config.postal_codes:
                    for tx_type in config.transaction_types:
                        await self._run_single(
                            session, site_key, postal_code, tx_type
                        )

    async def run_single_site(self, site_key: str, postal_code: str):
        async with self.session_factory() as session:
            await self._run_single(session, site_key, postal_code, "vente")

    async def _run_single(
        self,
        session: AsyncSession,
        site_key: str,
        postal_code: str,
        transaction_type: str,
    ):
        run = ScrapeRun(site=site_key, postal_code=postal_code)
        session.add(run)
        await session.commit()

        try:
            scraper = get_scraper(site_key, self.anti_bot)
            scraped = await scraper.scrape(postal_code, transaction_type)

            # Strict postal code filter — some sites (Leboncoin, Bien'ici…)
            # return geo-radius results from neighbouring communes. We only
            # keep exact matches for the requested code.
            before_filter = len(scraped)
            scraped = [item for item in scraped if item.postal_code == postal_code]
            filtered_out = before_filter - len(scraped)
            if filtered_out:
                logger.info(
                    "postal_code_filter",
                    site=site_key,
                    requested=postal_code,
                    filtered_out=filtered_out,
                )

            run.listings_found = len(scraped)

            new_count = 0
            dedup_count = 0
            rejected_pro = 0

            for item in scraped:
                result = await self._process_listing(session, item)
                if result == "new":
                    new_count += 1
                elif result == "dedup":
                    dedup_count += 1
                elif result == "rejected_pro":
                    rejected_pro += 1

            run.listings_new = new_count
            run.listings_dedup = dedup_count
            run.status = "success"
            run.finished_at = datetime.utcnow()

            await session.commit()
            logger.info(
                "run_complete",
                site=site_key,
                postal_code=postal_code,
                found=run.listings_found,
                new=new_count,
                dedup=dedup_count,
                rejected_pro=rejected_pro,
            )

        except Exception as e:
            run.status = "error"
            run.error_message = str(e)[:500]
            run.finished_at = datetime.utcnow()
            await session.commit()
            logger.error("run_failed", site=site_key, error=str(e))

    async def _process_listing(
        self, session: AsyncSession, item: ScrapedListing
    ) -> str:
        """Returns: 'new', 'dedup', 'existing', 'rejected_pro', 'suspicious'."""

        # Check URL uniqueness
        existing_url = await session.execute(
            select(Listing.id).where(Listing.source_url == item.source_url)
        )
        if existing_url.scalar_one_or_none():
            return "existing"

        # Compute dedup hash
        dedup_hash = compute_dedup_hash(
            item.postal_code, item.price, item.surface_m2, item.nb_rooms
        )

        # Check cross-site dedup — if found, add alternate URL instead of rejecting
        existing_hash = await session.execute(
            select(Listing).where(
                Listing.dedup_hash == dedup_hash,
                Listing.postal_code == item.postal_code,
            )
        )
        existing_listing = existing_hash.scalar_one_or_none()
        if existing_listing:
            # Add the new URL as an alternate source
            existing_listing.add_alternate_url(item.source_site, item.source_url)
            await session.commit()
            logger.info(
                "cross_site_dedup_merged",
                source=item.source_site,
                url=item.source_url,
                merged_into=existing_listing.id,
            )
            return "dedup"

        # === ANALYSE PREMIUM ===
        analysis = await run_premium_analysis(session, item)

        # Rejet si pro confirmé
        if analysis.should_reject:
            logger.info(
                "rejected_pro",
                url=item.source_url,
                reasons=analysis.pro_detection.reasons,
            )
            return "rejected_pro"

        # Insert new listing
        listing = Listing(
            source_site=item.source_site,
            source_url=item.source_url,
            source_id=item.source_id,
            title=item.title,
            price=item.price,
            surface_m2=item.surface_m2,
            nb_rooms=item.nb_rooms,
            nb_bedrooms=item.nb_bedrooms,
            property_type=item.property_type,
            transaction_type=item.transaction_type,
            description=item.description,
            postal_code=item.postal_code,
            city=item.city,
            department=item.department,
            seller_name=item.seller_name,
            seller_phone=item.seller_phone,
            seller_email=item.seller_email,
            publication_date=item.publication_date,
            dedup_hash=dedup_hash,
        )
        listing.image_urls = item.image_urls
        session.add(listing)
        await session.flush()

        # Compute commission (default 5% fixed, overridden per user later)
        commission = compute_commission(item.price)

        # Generate notification JSON
        notification = analysis.to_notification_json(item)
        notification["details"]["commission_estimee"] = commission.commission_amount

        # Auto-create lead with premium analysis data
        lead = Lead(
            listing_id=listing.id,
            # Commission
            commission_amount=commission.commission_amount,
            commission_rate=commission.commission_rate_applied,
            # Urgency
            urgency_score=analysis.urgency.value,
            urgency_level=analysis.urgency.level,
            urgency_factors=json.dumps(analysis.urgency.factors, ensure_ascii=False),
            # Price gap
            price_gap_pct=analysis.price_gap.gap_percentage,
            price_m2_market=analysis.price_gap.estimated_price_m2,
            price_gap_comment=analysis.price_gap.comment,
            # Chronology
            chronology_type=analysis.chronology.type,
            days_on_market=analysis.chronology.days_on_market,
            previous_price=analysis.chronology.previous_price,
            chronology_comment=analysis.chronology.comment,
            # Strategic
            strategic_priority=analysis.strategic_advice.priorite,
            strategic_angle=analysis.strategic_advice.angle_attaque,
            strategic_sms=analysis.strategic_advice.script_accroche_sms,
            # Flags
            is_suspicious=analysis.needs_review,
            notification_json=json.dumps(notification, ensure_ascii=False),
        )
        session.add(lead)
        await session.flush()

        # Fire event for v2 hooks (email, WhatsApp)
        lead_created.send(
            self,
            lead=lead,
            listing=listing,
            analysis=analysis,
            notification=notification,
        )

        return "new"

    async def _get_config(self, session: AsyncSession) -> ScrapingConfig | None:
        result = await session.execute(
            select(ScrapingConfig).where(ScrapingConfig.id == 1)
        )
        return result.scalar_one_or_none()
