from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.analysis.urgency import UrgencyScore, compute_urgency_score
from app.services.analysis.price_gap import PriceGapAnalysis, analyze_price_gap
from app.services.analysis.republication import ChronologyAnalysis, analyze_chronology
from app.services.analysis.pro_detector import ProDetectionResult, detect_pro
from app.services.analysis.strategic_advisor import StrategicAdvice, generate_strategic_advice
from scraper.models import ScrapedListing

import structlog

logger = structlog.get_logger()


@dataclass
class PremiumAnalysis:
    urgency: UrgencyScore = field(default_factory=UrgencyScore)
    price_gap: PriceGapAnalysis = field(default_factory=PriceGapAnalysis)
    chronology: ChronologyAnalysis = field(default_factory=ChronologyAnalysis)
    pro_detection: ProDetectionResult = field(default_factory=ProDetectionResult)
    strategic_advice: StrategicAdvice = field(default_factory=StrategicAdvice)

    @property
    def should_reject(self) -> bool:
        """L'annonce doit être rejetée (pro confirmé)."""
        return self.pro_detection.is_likely_pro

    @property
    def needs_review(self) -> bool:
        """L'annonce nécessite une vérification manuelle."""
        return self.pro_detection.is_suspicious

    def to_notification_json(
        self,
        listing: ScrapedListing,
        territory: str | None = None,
    ) -> dict:
        """Génère la notification premium au format JSON."""
        price_m2 = None
        if listing.price and listing.surface_m2 and listing.surface_m2 > 0:
            price_m2 = round(listing.price / listing.surface_m2)

        return {
            "lead_id": f"{listing.source_site.upper()}-{listing.source_id or '000'}",
            "status": "NOUVEAU",
            "secteur": territory or listing.postal_code,
            "details": {
                "titre": listing.title,
                "prix_annonce": listing.price,
                "prix_m2": price_m2,
                "commission_estimee": 0,  # Rempli par le runner
                "surface": f"{listing.surface_m2}m2" if listing.surface_m2 else None,
                "nb_pieces": listing.nb_rooms,
                "type_bien": listing.property_type,
                "ville": listing.city,
                "lien_source": listing.source_url,
                "site_source": listing.source_site,
                "photos": listing.image_urls[:5],
                "score_urgence": self.urgency.value,
                "mots_cles_detectes": [
                    f.replace("Mot-clé détecté: '", "").rstrip("'")
                    for f in self.urgency.factors
                    if f.startswith("Mot-clé")
                ],
            },
            "analyse_premium": {
                "score_urgence": {
                    "valeur": self.urgency.value,
                    "niveau": self.urgency.level,
                    "facteurs": self.urgency.factors,
                },
                "ecart_prix": {
                    "pourcentage": self.price_gap.gap_percentage,
                    "prix_m2_annonce": self.price_gap.listing_price_m2,
                    "prix_m2_marche": self.price_gap.estimated_price_m2,
                    "commentaire": self.price_gap.comment,
                    "source_donnees": self.price_gap.data_source,
                    "confiance": self.price_gap.confidence,
                },
                "chronologie": {
                    "type": self.chronology.type,
                    "jours_en_vente": self.chronology.days_on_market,
                    "ancien_prix": self.chronology.previous_price,
                    "variation_prix_pct": self.chronology.price_change_pct,
                    "commentaire": self.chronology.comment,
                },
                "detection_pro": {
                    "est_pro": self.pro_detection.is_likely_pro,
                    "suspect": self.pro_detection.is_suspicious,
                    "score_pro": self.pro_detection.pro_score,
                    "raisons": self.pro_detection.reasons,
                },
            },
            "strategie": {
                "priorite": self.strategic_advice.priorite,
                "angle_attaque": self.strategic_advice.angle_attaque,
                "accroche_sms": self.strategic_advice.script_accroche_sms,
                "points_forts": self.price_gap.comment or "",
            },
            "vendeur": {
                "nom": listing.seller_name,
                "telephone": listing.seller_phone,
                "email": listing.seller_email,
            },
        }


async def run_premium_analysis(
    session: AsyncSession,
    listing: ScrapedListing,
) -> PremiumAnalysis:
    """Exécute l'ensemble du pipeline d'analyse premium sur une annonce."""
    analysis = PremiumAnalysis()

    # 1. Détection pro/particulier (rapide, pas d'IO)
    analysis.pro_detection = detect_pro(
        listing.title,
        listing.description,
        listing.seller_name,
    )

    if analysis.should_reject:
        logger.info(
            "listing_rejected_pro",
            url=listing.source_url,
            reasons=analysis.pro_detection.reasons,
        )
        return analysis

    # 2. Score d'urgence (rapide, pas d'IO)
    analysis.urgency = compute_urgency_score(
        listing.title,
        listing.description,
        listing.price,
    )

    # 3. Écart de prix (appel API DVF)
    analysis.price_gap = await analyze_price_gap(
        listing.postal_code,
        listing.price,
        listing.surface_m2,
        listing.property_type,
    )

    # 4. Détection republication (requête DB)
    analysis.chronology = await analyze_chronology(
        session,
        listing.postal_code,
        listing.price,
        listing.surface_m2,
        listing.nb_rooms,
        listing.source_url,
        listing.title,
    )

    # 5. Conseil stratégique (synthèse de tout)
    analysis.strategic_advice = generate_strategic_advice(
        title=listing.title,
        price=listing.price,
        surface_m2=listing.surface_m2,
        city=listing.city,
        postal_code=listing.postal_code,
        urgency=analysis.urgency,
        price_gap=analysis.price_gap,
        chronology=analysis.chronology,
        seller_name=listing.seller_name,
    )

    logger.info(
        "premium_analysis_complete",
        url=listing.source_url,
        urgency=analysis.urgency.value,
        price_gap=analysis.price_gap.gap_percentage,
        chrono=analysis.chronology.type,
        priority=analysis.strategic_advice.priorite,
    )

    return analysis
