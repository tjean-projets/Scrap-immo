#!/usr/bin/env python3
"""Script pour lancer un scraping manuellement."""
import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.database import engine, Base, async_session
from app.models import Listing, Lead, ScrapingConfig, ScrapeRun
from scraper.runner import ScraperRunner


async def main():
    postal_code = sys.argv[1] if len(sys.argv) > 1 else "75001"
    site = sys.argv[2] if len(sys.argv) > 2 else "pap"

    print(f"Initialisation de la base de données...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Ensure config exists
    async with async_session() as session:
        from sqlalchemy import select
        result = await session.execute(
            select(ScrapingConfig).where(ScrapingConfig.id == 1)
        )
        if not result.scalar_one_or_none():
            session.add(ScrapingConfig(id=1))
            await session.commit()

    print(f"Lancement du scraping {site} pour le code postal {postal_code}...")
    runner = ScraperRunner(async_session)
    await runner.run_single_site(site, postal_code)

    # Show results
    async with async_session() as session:
        from sqlalchemy import select, func
        total = (await session.execute(select(func.count(Listing.id)))).scalar()
        leads = (await session.execute(select(func.count(Lead.id)))).scalar()
        print(f"\nRésultats: {total} annonces, {leads} leads créés")

        result = await session.execute(
            select(Listing).order_by(Listing.created_at.desc()).limit(5)
        )
        for listing in result.scalars():
            print(f"  - {listing.title} | {listing.price}€ | {listing.city} | {listing.source_url}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
