from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog

from app.database import engine, Base, async_session
from app.models import Listing, Lead, ScrapingConfig, ScrapeRun
from app.api.router import api_router
from scraper.scheduler import setup_scheduler, scheduler

structlog.configure(
    processors=[
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(0),
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables + seed config + start scheduler
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        from sqlalchemy import select
        from app.config import settings
        from app.models.user import User
        from app.models.config import ScrapingConfig as Cfg
        from app.services.auth import hash_password

        # Seed default scraping config
        result = await session.execute(select(Cfg).where(Cfg.id == 1))
        if not result.scalar_one_or_none():
            session.add(Cfg(id=1))
            await session.commit()
            logger.info("config_seeded")

        # Seed admin user
        result = await session.execute(select(User).where(User.email == settings.admin_email))
        if not result.scalar_one_or_none():
            admin = User(
                email=settings.admin_email,
                hashed_password=hash_password(settings.admin_password),
                full_name="Admin",
                is_admin=True,
            )
            session.add(admin)
            await session.commit()
            logger.info("admin_created", email=settings.admin_email)

    await setup_scheduler()
    logger.info("app_started")

    yield

    # Shutdown
    scheduler.shutdown(wait=False)
    await engine.dispose()
    logger.info("app_stopped")


app = FastAPI(
    title="Scrap Immo",
    description="CRM de pige immobilière automatisée",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
