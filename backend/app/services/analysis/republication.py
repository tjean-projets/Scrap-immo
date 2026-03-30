from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.listing import Listing
from app.services.dedup import compute_dedup_hash
import structlog

logger = structlog.get_logger()


@dataclass
class ChronologyAnalysis:
    type: str = "NOUVELLE"  # NOUVELLE, REPUBLICATION, BAISSE_PRIX, HAUSSE_PRIX
    previous_listing_id: int | None = None
    previous_price: int | None = None
    previous_date: datetime | None = None
    days_on_market: int | None = None
    price_change_pct: float | None = None
    comment: str = ""


async def analyze_chronology(
    session: AsyncSession,
    postal_code: str,
    price: int | None,
    surface_m2: float | None,
    nb_rooms: int | None,
    source_url: str,
    title: str | None = None,
) -> ChronologyAnalysis:
    """
    Détecte si une annonce est nouvelle ou une republication.
    Compare avec l'historique des listings déjà scrapés.
    """
    result = ChronologyAnalysis()

    # 1. Chercher par dedup_hash (même bien, possiblement un autre site)
    dedup_hash = compute_dedup_hash(postal_code, price, surface_m2, nb_rooms)

    previous = await session.execute(
        select(Listing)
        .where(
            and_(
                Listing.dedup_hash == dedup_hash,
                Listing.postal_code == postal_code,
                Listing.source_url != source_url,
            )
        )
        .order_by(Listing.created_at.desc())
        .limit(1)
    )
    prev_listing = previous.scalar_one_or_none()

    # 2. Chercher aussi par hash voisin (prix différent mais même bien)
    if not prev_listing and price and surface_m2 and nb_rooms:
        # Chercher des biens similaires dans la même zone
        candidates = await session.execute(
            select(Listing)
            .where(
                and_(
                    Listing.postal_code == postal_code,
                    Listing.nb_rooms == nb_rooms,
                    Listing.surface_m2.between(
                        (surface_m2 or 0) * 0.95, (surface_m2 or 0) * 1.05
                    ),
                    Listing.source_url != source_url,
                )
            )
            .order_by(Listing.created_at.desc())
            .limit(5)
        )
        for candidate in candidates.scalars():
            # Même surface ±5% et même nb pièces = probablement le même bien
            if candidate.price and price:
                result.previous_listing_id = candidate.id
                result.previous_price = candidate.price
                result.previous_date = candidate.created_at

                days = (datetime.utcnow() - candidate.created_at).days
                result.days_on_market = days

                price_change = ((price - candidate.price) / candidate.price) * 100
                result.price_change_pct = round(price_change, 1)

                if price < candidate.price:
                    result.type = "BAISSE_PRIX"
                    result.comment = (
                        f"Republication avec baisse de {abs(result.price_change_pct)}%. "
                        f"Vu il y a {days} jours à {candidate.price:,}€. "
                        f"Vendeur qui commence à baisser — bon moment pour appeler."
                    )
                elif price > candidate.price:
                    result.type = "HAUSSE_PRIX"
                    result.comment = (
                        f"Republication avec hausse de {result.price_change_pct}%. "
                        f"Vu il y a {days} jours à {candidate.price:,}€. "
                        f"Vendeur qui tente sa chance à la hausse."
                    )
                else:
                    result.type = "REPUBLICATION"
                    result.comment = (
                        f"Annonce republiée au même prix. "
                        f"Bien en vente depuis au moins {days} jours. "
                        f"Vendeur potentiellement fatigué."
                    )
                break

    if not prev_listing and result.type == "NOUVELLE":
        result.comment = "Annonce fraîche — première apparition dans notre base."

    elif prev_listing and result.type == "NOUVELLE":
        # Trouvé par dedup_hash avec même prix
        days = (datetime.utcnow() - prev_listing.created_at).days
        result.days_on_market = days
        result.previous_listing_id = prev_listing.id
        result.previous_price = prev_listing.price
        result.previous_date = prev_listing.created_at

        if days > 60:
            result.type = "REPUBLICATION"
            result.comment = (
                f"Bien 'brûlé' — en vente depuis {days} jours sur plusieurs sites. "
                f"Le vendeur a besoin d'aide professionnelle."
            )
        elif days > 30:
            result.type = "REPUBLICATION"
            result.comment = (
                f"Bien en vente depuis {days} jours. "
                f"Début de lassitude probable chez le vendeur."
            )

    return result
