from __future__ import annotations

from fastapi import APIRouter

from app.api.leads import router as leads_router
from app.api.listings import router as listings_router
from app.api.settings import router as settings_router
from app.api.dashboard import router as dashboard_router
from app.api.scraper_ctrl import router as scraper_router
from app.api.kanban import router as kanban_router
from app.api.auth import router as auth_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(leads_router)
api_router.include_router(listings_router)
api_router.include_router(settings_router)
api_router.include_router(dashboard_router)
api_router.include_router(scraper_router)
api_router.include_router(kanban_router)
