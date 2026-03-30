from __future__ import annotations

from dataclasses import dataclass
from app.services.analysis.urgency import UrgencyScore
from app.services.analysis.price_gap import PriceGapAnalysis
from app.services.analysis.republication import ChronologyAnalysis


@dataclass
class StrategicAdvice:
    angle_attaque: str = ""
    script_accroche_sms: str = ""
    priorite: str = "normale"  # basse, normale, haute, critique


def generate_strategic_advice(
    title: str | None,
    price: int | None,
    surface_m2: float | None,
    city: str | None,
    postal_code: str,
    urgency: UrgencyScore,
    price_gap: PriceGapAnalysis,
    chronology: ChronologyAnalysis,
    seller_name: str | None = None,
) -> StrategicAdvice:
    """
    Génère un conseil stratégique et un script d'accroche SMS
    basé sur l'ensemble des analyses.
    """
    advice = StrategicAdvice()

    # Déterminer la priorité globale
    priority_score = urgency.value
    if chronology.type == "REPUBLICATION" and chronology.days_on_market and chronology.days_on_market > 60:
        priority_score += 20
    if chronology.type == "BAISSE_PRIX":
        priority_score += 15
    if price_gap.gap_percentage and price_gap.gap_percentage > 15:
        priority_score += 15

    if priority_score >= 80:
        advice.priorite = "critique"
    elif priority_score >= 50:
        advice.priorite = "haute"
    elif priority_score >= 25:
        advice.priorite = "normale"
    else:
        advice.priorite = "basse"

    # Construire les éléments de contexte
    bien_desc = _build_bien_description(title, surface_m2, city, postal_code)
    salutation = f"Bonjour{f' {seller_name}' if seller_name else ''}"
    location = city or postal_code

    # Générer l'angle d'attaque selon le profil
    angles = []

    # Cas 1: Vendeur pressé + bien surestimé
    if urgency.value >= 60 and price_gap.gap_percentage and price_gap.gap_percentage > 10:
        angles.append(
            f"Ce vendeur est pressé ({_summarize_urgency_factors(urgency)}) "
            f"mais s'entête sur un prix trop élevé ({price_gap.gap_percentage:+.0f}% vs marché). "
            f"Son bien risque d'être 'brûlé' sur le marché. "
            f"Appelle pour proposer ton expertise sur l'estimation réelle et un plan de vente rapide."
        )
        advice.script_accroche_sms = (
            f"{salutation}, je suis mandataire immobilier dans le {location}. "
            f"J'ai vu votre {bien_desc}. "
            f"Connaissant bien votre secteur, je pense que votre estimation est ambitieuse "
            f"et risque de vous faire perdre du temps"
            f"{' si vous devez partir vite' if urgency.value >= 80 else ''}. "
            f"Quand êtes-vous disponible pour une vraie estimation gratuite et sans engagement ? "
            f"Cordialement."
        )

    # Cas 2: Republication / bien brûlé
    elif chronology.type in ("REPUBLICATION", "BAISSE_PRIX") and chronology.days_on_market and chronology.days_on_market > 30:
        days = chronology.days_on_market
        angles.append(
            f"Ce bien est en vente depuis {days} jours"
            f"{f' avec déjà une baisse de {abs(chronology.price_change_pct or 0):.0f}%' if chronology.type == 'BAISSE_PRIX' else ''}. "
            f"Le vendeur s'épuise. C'est le moment idéal pour proposer "
            f"une stratégie de vente professionnelle avec une nouvelle approche."
        )
        advice.script_accroche_sms = (
            f"{salutation}, je suis mandataire immobilier spécialisé sur {location}. "
            f"J'ai remarqué que votre {bien_desc} est en vente depuis un moment. "
            f"C'est souvent un problème de positionnement prix ou de visibilité. "
            f"Je peux vous proposer une nouvelle stratégie de mise en marché — "
            f"souhaitez-vous qu'on en discute 15 minutes ? Cordialement."
        )

    # Cas 3: Vendeur très pressé
    elif urgency.value >= 70:
        angles.append(
            f"Ce vendeur montre des signaux d'urgence forts ({_summarize_urgency_factors(urgency)}). "
            f"Il a besoin d'un professionnel réactif qui peut vendre vite. "
            f"Appelle rapidement en mettant en avant ta réactivité et ton réseau d'acquéreurs."
        )
        advice.script_accroche_sms = (
            f"{salutation}, je suis mandataire immobilier sur {location} "
            f"et j'ai un réseau d'acquéreurs qualifiés en recherche active dans votre secteur. "
            f"Pour votre {bien_desc}, je peux organiser des visites dès cette semaine. "
            f"Avez-vous un créneau pour en discuter ? Cordialement."
        )

    # Cas 4: Bien sous-évalué
    elif price_gap.gap_percentage and price_gap.gap_percentage < -10:
        angles.append(
            f"Ce bien est en dessous du marché de {abs(price_gap.gap_percentage):.0f}%. "
            f"Le vendeur ne connaît peut-être pas la vraie valeur de son bien, "
            f"ou il a besoin de vendre rapidement. "
            f"Positionne-toi comme l'expert qui peut valoriser au mieux son patrimoine."
        )
        advice.script_accroche_sms = (
            f"{salutation}, je suis mandataire immobilier expert du secteur {location}. "
            f"En analysant votre {bien_desc}, je pense que vous pourriez en obtenir davantage "
            f"avec un accompagnement professionnel. "
            f"Accepteriez-vous une estimation gratuite et sans engagement ? Cordialement."
        )

    # Cas 5: Bien surestimé sans urgence
    elif price_gap.gap_percentage and price_gap.gap_percentage > 15:
        angles.append(
            f"Ce bien est surestimé de {price_gap.gap_percentage:.0f}% par rapport au marché. "
            f"Sans urgence apparente, ce vendeur va mettre du temps à vendre. "
            f"Reviens dans 2-3 semaines s'il n'a pas vendu — il sera plus réceptif."
        )
        advice.script_accroche_sms = (
            f"{salutation}, je suis mandataire immobilier sur {location}. "
            f"J'ai vu votre {bien_desc} et je me permets de vous contacter car "
            f"je connais très bien les prix de votre quartier. "
            f"Seriez-vous ouvert à un avis de valeur gratuit et confidentiel ? Cordialement."
        )

    # Cas par défaut
    else:
        angles.append(
            f"Annonce standard sans signal fort. "
            f"Approche classique : proposer une estimation gratuite "
            f"en mettant en avant ta connaissance du quartier."
        )
        advice.script_accroche_sms = (
            f"{salutation}, je suis mandataire immobilier spécialisé sur {location}. "
            f"J'ai vu votre {bien_desc} et je dispose d'acquéreurs en recherche active "
            f"dans votre secteur. Souhaitez-vous qu'on échange sur votre projet de vente ? "
            f"Cordialement."
        )

    advice.angle_attaque = " ".join(angles)
    return advice


def _build_bien_description(
    title: str | None,
    surface_m2: float | None,
    city: str | None,
    postal_code: str,
) -> str:
    parts = []
    if title:
        # Simplifier le titre
        t = title.lower()
        if "appartement" in t:
            parts.append("appartement")
        elif "maison" in t:
            parts.append("maison")
        elif "terrain" in t:
            parts.append("terrain")
        else:
            parts.append("bien")
    else:
        parts.append("bien")

    if surface_m2:
        parts.append(f"de {int(surface_m2)}m²")

    if city:
        parts.append(f"à {city}")

    return " ".join(parts)


def _summarize_urgency_factors(urgency: UrgencyScore) -> str:
    # Prendre les 2 facteurs les plus importants
    real_factors = [
        f for f in urgency.factors
        if f != "Aucun signal d'urgence détecté"
    ]
    if not real_factors:
        return "signaux d'urgence détectés"
    return ", ".join(real_factors[:2]).lower()
