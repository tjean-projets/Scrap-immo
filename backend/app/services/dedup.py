from __future__ import annotations

import hashlib


def compute_dedup_hash(
    postal_code: str,
    price: int | None,
    surface_m2: float | None,
    nb_rooms: int | None,
) -> str:
    price_bucket = str(round(price / 5000) * 5000) if price else "0"
    surface_round = str(round(surface_m2)) if surface_m2 else "0"
    rooms = str(nb_rooms) if nb_rooms else "0"
    raw = f"{postal_code}|{price_bucket}|{surface_round}|{rooms}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]
