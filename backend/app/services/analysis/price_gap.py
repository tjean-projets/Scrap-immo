from __future__ import annotations

import httpx
import structlog
from dataclasses import dataclass
from typing import Optional

logger = structlog.get_logger()

# Cache en mémoire des prix/m² par code postal
_price_cache: dict[str, Optional[float]] = {}

# API DVF (Demandes de Valeurs Foncières) - données open data officielles
DVF_API_URL = "https://api.cquest.org/dvf"

# Fallback: API data.gouv pour les stats DVF agrégées
DVF_STATS_URL = "https://apidf-preprod.cerema.fr/indicateurs/dv3f/departement/prix"


@dataclass
class PriceGapAnalysis:
    estimated_price_m2: float | None = None
    listing_price_m2: float | None = None
    gap_percentage: float | None = None  # Positif = trop cher, Négatif = bonne affaire
    comment: str = ""
    data_source: str = ""
    confidence: str = "low"  # low, medium, high


async def get_average_price_m2(
    postal_code: str,
    property_type: str | None = None,
) -> float | None:
    """Récupère le prix moyen au m² pour un code postal via l'API DVF."""
    cache_key = f"{postal_code}_{property_type or 'all'}"
    if cache_key in _price_cache:
        return _price_cache[cache_key]

    price = await _fetch_dvf_price(postal_code, property_type)
    _price_cache[cache_key] = price
    return price


async def _fetch_dvf_price(
    postal_code: str,
    property_type: str | None = None,
) -> float | None:
    """Interroge l'API DVF pour les transactions récentes."""
    try:
        # Construire le type de bien pour l'API
        code_type = None
        if property_type:
            type_map = {
                "appartement": "Appartement",
                "maison": "Maison",
            }
            code_type = type_map.get(property_type.lower())

        params = {
            "code_postal": postal_code,
        }
        if code_type:
            params["type_local"] = code_type

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(DVF_API_URL, params=params)

            if response.status_code != 200:
                logger.warning("dvf_api_error", status=response.status_code, cp=postal_code)
                return None

            data = response.json()
            resultats = data.get("resultats", [])

            if not resultats:
                logger.info("dvf_no_results", cp=postal_code)
                return None

            # Calculer le prix moyen au m² des transactions récentes
            prices_m2 = []
            for tx in resultats:
                valeur = tx.get("valeur_fonciere")
                surface = tx.get("surface_reelle_bati") or tx.get("surface_terrain")
                if valeur and surface and surface > 0:
                    pm2 = valeur / surface
                    # Filtrer les valeurs aberrantes
                    if 500 < pm2 < 30000:
                        prices_m2.append(pm2)

            if not prices_m2:
                return None

            # Médiane pour éviter les outliers
            prices_m2.sort()
            mid = len(prices_m2) // 2
            if len(prices_m2) % 2 == 0:
                median = (prices_m2[mid - 1] + prices_m2[mid]) / 2
            else:
                median = prices_m2[mid]

            logger.info(
                "dvf_price_computed",
                cp=postal_code,
                median_m2=round(median),
                sample_size=len(prices_m2),
            )
            return round(median, 2)

    except Exception as e:
        logger.error("dvf_fetch_error", error=str(e), cp=postal_code)
        return None


# Prix moyens de secours par département (données 2024 approximatives)
FALLBACK_PRICES_M2: dict[str, float] = {
    "75": 10500,  # Paris
    "92": 6500,   # Hauts-de-Seine
    "93": 4200,   # Seine-Saint-Denis
    "94": 5500,   # Val-de-Marne
    "69": 4200,   # Rhône
    "13": 3200,   # Bouches-du-Rhône
    "06": 4800,   # Alpes-Maritimes
    "33": 3800,   # Gironde
    "31": 3400,   # Haute-Garonne
    "44": 3600,   # Loire-Atlantique
    "67": 3000,   # Bas-Rhin
    "59": 2800,   # Nord
    "34": 3200,   # Hérault
    "35": 3200,   # Ille-et-Vilaine
    "76": 2500,   # Seine-Maritime
}


async def analyze_price_gap(
    postal_code: str,
    price: int | None,
    surface_m2: float | None,
    property_type: str | None = None,
) -> PriceGapAnalysis:
    """Analyse l'écart entre le prix demandé et le prix de marché."""
    result = PriceGapAnalysis()

    if not price or not surface_m2 or surface_m2 <= 0:
        result.comment = "Données insuffisantes pour l'analyse de prix"
        return result

    listing_pm2 = price / surface_m2
    result.listing_price_m2 = round(listing_pm2)

    # Tenter l'API DVF
    market_pm2 = await get_average_price_m2(postal_code, property_type)

    if market_pm2:
        result.estimated_price_m2 = round(market_pm2)
        result.data_source = "DVF (transactions réelles)"
        result.confidence = "high"
    else:
        # Fallback sur les moyennes départementales
        dept = postal_code[:2]
        fallback = FALLBACK_PRICES_M2.get(dept)
        if fallback:
            result.estimated_price_m2 = fallback
            result.data_source = "Moyenne départementale (approximation)"
            result.confidence = "low"
        else:
            result.comment = f"Pas de données de référence pour le département {dept}"
            return result

    # Calculer l'écart
    gap = ((listing_pm2 - result.estimated_price_m2) / result.estimated_price_m2) * 100
    result.gap_percentage = round(gap, 1)

    # Générer le commentaire
    if gap > 20:
        result.comment = (
            f"Surestimé de {result.gap_percentage}% par rapport au marché "
            f"({result.listing_price_m2}€/m² vs {result.estimated_price_m2}€/m² secteur). "
            f"Vendeur qui va galérer — besoin d'une estimation pro."
        )
    elif gap > 10:
        result.comment = (
            f"Au-dessus du marché de {result.gap_percentage}%. "
            f"Marge de négociation probable."
        )
    elif gap > -5:
        result.comment = (
            f"Prix cohérent avec le marché ({result.gap_percentage:+.1f}%). "
            f"Vendeur bien informé."
        )
    elif gap > -15:
        result.comment = (
            f"En dessous du marché de {abs(result.gap_percentage)}%. "
            f"Bonne affaire potentielle — agir vite."
        )
    else:
        result.comment = (
            f"Très en dessous du marché ({result.gap_percentage:+.1f}%). "
            f"À vérifier : possible vice caché ou vente pressée."
        )

    return result
