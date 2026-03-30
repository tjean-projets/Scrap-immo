from __future__ import annotations

from fastapi import APIRouter, Depends

from app.services.auth import get_current_user
from app.api.leads import router as leads_router
from app.api.listings import router as listings_router
from app.api.settings import router as settings_router
from app.api.dashboard import router as dashboard_router
from app.api.scraper_ctrl import router as scraper_router
from app.api.kanban import router as kanban_router
from app.api.auth import router as auth_router

# Routes publiques (login, register)
api_router = APIRouter()
api_router.include_router(auth_router)

# Routes protégées par JWT
protected = APIRouter(dependencies=[Depends(get_current_user)])
protected.include_router(leads_router)
protected.include_router(listings_router)
protected.include_router(settings_router)
protected.include_router(dashboard_router)
protected.include_router(scraper_router)
protected.include_router(kanban_router)

api_router.include_router(protected)
