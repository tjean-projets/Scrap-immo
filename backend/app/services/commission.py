from __future__ import annotations

import json
from dataclasses import dataclass


# Barème progressif par défaut (tranches)
DEFAULT_PROGRESSIVE_TIERS = [
    {"min": 0, "max": 100000, "rate": 7.0},
    {"min": 100000, "max": 300000, "rate": 5.0},
    {"min": 300000, "max": 500000, "rate": 4.0},
    {"min": 500000, "max": None, "rate": 3.0},
]


@dataclass
class CommissionResult:
    commission_amount: int  # Montant en euros
    commission_rate_applied: float  # Taux effectif appliqué
    commission_type: str  # "fixed" ou "progressive"


def compute_commission(
    price: int | None,
    commission_type: str = "fixed",
    commission_rate: float = 5.0,
    commission_tiers_json: str | None = None,
) -> CommissionResult:
    """
    Calcule la commission estimée sur un bien.

    - fixed : prix * taux fixe
    - progressive : barème par tranches
    """
    if not price or price <= 0:
        return CommissionResult(
            commission_amount=0,
            commission_rate_applied=0,
            commission_type=commission_type,
        )

    if commission_type == "fixed":
        amount = int(price * commission_rate / 100)
        return CommissionResult(
            commission_amount=amount,
            commission_rate_applied=commission_rate,
            commission_type="fixed",
        )

    # Progressive
    tiers = DEFAULT_PROGRESSIVE_TIERS
    if commission_tiers_json:
        try:
            tiers = json.loads(commission_tiers_json)
        except (json.JSONDecodeError, TypeError):
            pass

    amount = 0
    remaining = price

    for tier in tiers:
        tier_min = tier.get("min", 0)
        tier_max = tier.get("max")
        rate = tier.get("rate", 5.0)

        if tier_max is None:
            # Dernière tranche, tout le reste
            tranche = remaining
        else:
            tranche = min(remaining, tier_max - tier_min)

        if tranche <= 0:
            break

        amount += int(tranche * rate / 100)
        remaining -= tranche

        if remaining <= 0:
            break

    effective_rate = round((amount / price) * 100, 2) if price > 0 else 0

    return CommissionResult(
        commission_amount=amount,
        commission_rate_applied=effective_rate,
        commission_type="progressive",
    )


def compute_pipeline_value(
    leads_with_prices: list[tuple[str, int | None]],
    commission_type: str = "fixed",
    commission_rate: float = 5.0,
    commission_tiers_json: str | None = None,
) -> dict[str, dict]:
    """
    Calcule la valeur du pipeline par colonne Kanban.

    leads_with_prices: list de (status, price)

    Retourne: {
        "nouveau": {"count": 5, "total_value": 850000, "total_commission": 42500},
        ...
    }
    """
    pipeline: dict[str, dict] = {}

    for status, price in leads_with_prices:
        if status not in pipeline:
            pipeline[status] = {
                "count": 0,
                "total_value": 0,
                "total_commission": 0,
            }

        pipeline[status]["count"] += 1
        pipeline[status]["total_value"] += price or 0

        if price:
            result = compute_commission(
                price, commission_type, commission_rate, commission_tiers_json
            )
            pipeline[status]["total_commission"] += result.commission_amount

    return pipeline
