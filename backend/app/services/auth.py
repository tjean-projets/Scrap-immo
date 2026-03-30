from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User, Territory
from app.config import settings

security = HTTPBearer()


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    hashed = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
    return f"{salt}:{hashed}"


def verify_password(password: str, hashed: str) -> bool:
    parts = hashed.split(":")
    if len(parts) != 2:
        return False
    salt, hash_val = parts
    return hashlib.sha256(f"{salt}{password}".encode()).hexdigest() == hash_val


def create_token(user_id: int) -> str:
    exp = datetime.now(timezone.utc) + timedelta(days=settings.jwt_expiration_days)
    payload = {"sub": str(user_id), "exp": exp}
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        user_id = int(payload["sub"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expiré, veuillez vous reconnecter")
    except (jwt.InvalidTokenError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Token invalide")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Utilisateur inactif")
    return user


async def get_user_territories(
    db: AsyncSession, user_id: int
) -> list[str]:
    """Retourne les codes postaux exclusifs d'un utilisateur."""
    result = await db.execute(
        select(Territory.postal_code).where(
            Territory.user_id == user_id,
            Territory.is_active == True,
        )
    )
    return [row[0] for row in result.all()]


async def check_territory_available(
    db: AsyncSession, postal_code: str
) -> bool:
    """Vérifie si un code postal est disponible."""
    result = await db.execute(
        select(Territory).where(
            Territory.postal_code == postal_code,
            Territory.is_active == True,
        )
    )
    return result.scalar_one_or_none() is None


async def assign_territory(
    db: AsyncSession, user_id: int, postal_code: str
) -> Territory:
    """Assigne un code postal exclusif à un utilisateur."""
    if not await check_territory_available(db, postal_code):
        raise ValueError(f"Le code postal {postal_code} est déjà attribué")

    territory = Territory(postal_code=postal_code, user_id=user_id)
    db.add(territory)
    await db.commit()
    return territory
