from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Text, Boolean, Float, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    hashed_password: Mapped[str] = mapped_column(Text, nullable=False)
    full_name: Mapped[str] = mapped_column(Text, nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(Text)
    whatsapp_phone: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    # Grille de commission
    commission_type: Mapped[str] = mapped_column(Text, default="fixed")  # fixed, progressive
    commission_rate: Mapped[float] = mapped_column(Float, default=5.0)  # % par défaut
    _commission_tiers: Mapped[Optional[str]] = mapped_column("commission_tiers", Text)  # JSON barème progressif
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Territory(Base):
    """Exclusivité territoriale : 1 code postal = 1 utilisateur max."""
    __tablename__ = "territories"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    postal_code: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    user_id: Mapped[int] = mapped_column(nullable=False, index=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
