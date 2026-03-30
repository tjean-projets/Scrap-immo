from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User, Territory
from app.services.auth import (
    hash_password,
    verify_password,
    create_token,
    get_current_user,
    get_user_territories,
    check_territory_available,
    assign_territory,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str
    phone: str | None = None
    whatsapp_phone: str | None = None


class LoginRequest(BaseModel):
    email: str
    password: str


class TerritoryRequest(BaseModel):
    postal_code: str


class CommissionConfigRequest(BaseModel):
    commission_type: str = "fixed"  # "fixed" ou "progressive"
    commission_rate: float = 5.0
    commission_tiers: list[dict] | None = None  # Barème progressif


@router.post("/register")
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(400, "Email déjà utilisé")

    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        phone=body.phone,
        whatsapp_phone=body.whatsapp_phone,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_token(user.id)
    return {"token": token, "user_id": user.id, "full_name": user.full_name}


@router.post("/login")
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(401, "Email ou mot de passe incorrect")

    token = create_token(user.id)
    return {"token": token, "user_id": user.id, "full_name": user.full_name}


@router.get("/me")
async def me(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    territories = await get_user_territories(db, user.id)
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "phone": user.phone,
        "whatsapp_phone": user.whatsapp_phone,
        "territories": territories,
    }


@router.post("/territories")
async def add_territory(
    body: TerritoryRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        territory = await assign_territory(db, user.id, body.postal_code)
        return {
            "postal_code": territory.postal_code,
            "message": f"Exclusivité sur {body.postal_code} activée",
        }
    except ValueError as e:
        raise HTTPException(409, str(e))


@router.get("/territories")
async def list_territories(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return {"territories": await get_user_territories(db, user.id)}


@router.get("/territories/check/{postal_code}")
async def check_territory(
    postal_code: str,
    db: AsyncSession = Depends(get_db),
):
    available = await check_territory_available(db, postal_code)
    return {"postal_code": postal_code, "available": available}


@router.get("/commission")
async def get_commission_config(
    user: User = Depends(get_current_user),
):
    import json
    tiers = None
    if user._commission_tiers:
        try:
            tiers = json.loads(user._commission_tiers)
        except (json.JSONDecodeError, TypeError):
            pass
    return {
        "commission_type": user.commission_type,
        "commission_rate": user.commission_rate,
        "commission_tiers": tiers,
    }


@router.put("/commission")
async def update_commission_config(
    body: CommissionConfigRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    import json
    user.commission_type = body.commission_type
    user.commission_rate = body.commission_rate
    if body.commission_tiers:
        user._commission_tiers = json.dumps(body.commission_tiers)
    await db.commit()
    return {
        "commission_type": user.commission_type,
        "commission_rate": user.commission_rate,
        "message": "Configuration commission mise à jour",
    }
