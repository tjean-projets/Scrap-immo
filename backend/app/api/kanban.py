from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.kanban_column import KanbanColumn, DEFAULT_COLUMNS

router = APIRouter(prefix="/api/kanban", tags=["kanban"])


class ColumnCreate(BaseModel):
    name: str
    color: str = "#3b82f6"


class ColumnUpdate(BaseModel):
    name: str | None = None
    color: str | None = None
    position: int | None = None


class ColumnReorder(BaseModel):
    column_ids: list[int]


async def _ensure_columns(db: AsyncSession):
    """Seed default columns if none exist."""
    result = await db.execute(select(KanbanColumn))
    if not result.scalars().first():
        for col in DEFAULT_COLUMNS:
            db.add(KanbanColumn(
                name=col["name"],
                color=col["color"],
                position=col["position"],
                is_default=(col["position"] == 0),
                is_archive=(col["name"] == "Archive"),
            ))
        await db.commit()


@router.get("/columns")
async def list_columns(db: AsyncSession = Depends(get_db)):
    await _ensure_columns(db)
    result = await db.execute(
        select(KanbanColumn).order_by(KanbanColumn.position)
    )
    cols = result.scalars().all()
    return [
        {
            "id": c.id,
            "name": c.name,
            "color": c.color,
            "position": c.position,
            "is_default": c.is_default,
            "is_archive": c.is_archive,
        }
        for c in cols
    ]


@router.post("/columns")
async def create_column(body: ColumnCreate, db: AsyncSession = Depends(get_db)):
    await _ensure_columns(db)
    # Get max position
    result = await db.execute(select(KanbanColumn).order_by(KanbanColumn.position.desc()).limit(1))
    last = result.scalar_one_or_none()
    max_pos = last.position if last else 0

    col = KanbanColumn(name=body.name, color=body.color, position=max_pos + 1)
    db.add(col)
    await db.commit()
    await db.refresh(col)
    return {"id": col.id, "name": col.name, "color": col.color, "position": col.position}


@router.patch("/columns/{column_id}")
async def update_column(column_id: int, body: ColumnUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(KanbanColumn).where(KanbanColumn.id == column_id))
    col = result.scalar_one_or_none()
    if not col:
        raise HTTPException(404, "Colonne introuvable")

    if body.name is not None:
        col.name = body.name
    if body.color is not None:
        col.color = body.color
    if body.position is not None:
        col.position = body.position

    await db.commit()
    return {"id": col.id, "name": col.name, "color": col.color, "position": col.position}


@router.delete("/columns/{column_id}")
async def delete_column(column_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(KanbanColumn).where(KanbanColumn.id == column_id))
    col = result.scalar_one_or_none()
    if not col:
        raise HTTPException(404, "Colonne introuvable")
    if col.is_default:
        raise HTTPException(400, "Impossible de supprimer la colonne par defaut")

    await db.delete(col)
    await db.commit()
    return {"deleted": True}


@router.put("/columns/reorder")
async def reorder_columns(body: ColumnReorder, db: AsyncSession = Depends(get_db)):
    for idx, col_id in enumerate(body.column_ids):
        result = await db.execute(select(KanbanColumn).where(KanbanColumn.id == col_id))
        col = result.scalar_one_or_none()
        if col:
            col.position = idx
    await db.commit()
    return {"reordered": True}
