from __future__ import annotations

from typing import Optional

from sqlalchemy import Text, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

# Default columns seeded at first launch
DEFAULT_COLUMNS = [
    {"name": "Nouveau Lead", "color": "#3b82f6", "position": 0},
    {"name": "Tentative Appel", "color": "#f59e0b", "position": 1},
    {"name": "RDV Estimation", "color": "#8b5cf6", "position": 2},
    {"name": "Mandat Signe", "color": "#10b981", "position": 3},
    {"name": "Archive", "color": "#6b7280", "position": 4},
]


class KanbanColumn(Base):
    __tablename__ = "kanban_columns"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    color: Mapped[str] = mapped_column(Text, default="#3b82f6")
    position: Mapped[int] = mapped_column(Integer, default=0)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    is_archive: Mapped[bool] = mapped_column(Boolean, default=False)
