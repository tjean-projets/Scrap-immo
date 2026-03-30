from __future__ import annotations

import re
from dataclasses import dataclass, field


# Mots-clés qui indiquent un professionnel
PRO_KEYWORDS = [
    # Identité pro
    "agence", "cabinet", "mandataire", "conseiller immobilier",
    "négociateur", "agent immobilier", "réseau", "franchise",
    "groupe immobilier", "société", "sarl", "sas", "eurl", "sci",
    # Carte professionnelle
    "carte professionnelle", "carte t", "carte transaction",
    # Honoraires / barèmes (REJET RADICAL)
    "honoraires à la charge de l'acquéreur", "honoraires charge acquéreur",
    "barème d'honoraires", "barème honoraires", "barème d'agence",
    "honoraires à la charge", "honoraires acquéreur",
    "honoraires vendeur", "frais d'agence", "commission d'agence",
    "honoraires ttc", "honoraires ht",
    # Mandats / conformité
    "mandat exclusif", "mandat simple", "mandat de vente",
    "diagnostics réalisés", "diagnostic réalisé",
    "loi alur", "loi carrez certifié",
    # Langage commercial pro
    "estimation gratuite", "nous contacter pour plus",
    "notre équipe", "nos conseillers", "nos agents",
    "retrouvez nos annonces", "toutes nos annonces",
    "référence annonce", "réf :", "ref:",
    "n'hésitez pas à contacter notre",
    "votre conseiller", "votre agent",
    # Liens vers barèmes
    "consultez nos honoraires", "tarifs disponibles",
    "voir nos honoraires", "grille tarifaire",
]

# Patterns de numéro SIREN/SIRET
SIREN_PATTERN = re.compile(r"\b\d{3}[\s.-]?\d{3}[\s.-]?\d{3}\b")
SIRET_PATTERN = re.compile(r"\b\d{3}[\s.-]?\d{3}[\s.-]?\d{3}[\s.-]?\d{5}\b")
RCS_PATTERN = re.compile(r"rcs\s+\w+\s*\d{3}[\s.]?\d{3}[\s.]?\d{3}", re.IGNORECASE)

# Indicateurs de langage "trop pro" pour un particulier
SUSPICIOUS_PATTERNS = [
    # CGV / mentions légales
    (r"(?:conditions générales|mentions légales|cgv)", 30, "CGV/Mentions légales détectées"),
    # Référence structurée type agence
    (r"(?:réf(?:érence)?[\s.:]+[A-Z0-9-]{4,})", 15, "Référence structurée d'agence"),
    # Honoraires
    (r"(?:honoraires|commission|frais).{0,20}(?:\d+[\s,.]?\d*\s*[%€])", 25, "Mention d'honoraires"),
    # DPE trop formel
    (r"(?:classe énergie\s*:\s*[A-G].*classe climat\s*:\s*[A-G])", 10, "DPE formaté comme une agence"),
    # Multiples points de contact pro
    (r"(?:(?:www\.|http).+\.(?:com|fr|immo))", 15, "Site web professionnel"),
    # Signature structurée
    (r"(?:votre (?:conseiller|agent|interlocuteur))", 20, "Signature pro"),
    # Loi Alur mentions détaillées
    (r"(?:loi alur.{0,50}honoraires)", 20, "Mention Loi Alur + honoraires"),
]

# Indicateurs de langage naturel de particulier
PARTICULIER_MARKERS = [
    "je vends", "nous vendons", "notre appartement", "notre maison",
    "mon appartement", "ma maison", "mon bien",
    "suite à", "cause déménagement", "cause mutation",
    "n'hésitez pas à me contacter", "me contacter",
    "contactez-moi", "appelez-moi",
    "je suis disponible", "je reste disponible",
    "photos supplémentaires sur demande",
]


@dataclass
class ProDetectionResult:
    is_likely_pro: bool = False
    is_suspicious: bool = False  # Besoin de vérification manuelle
    confidence: float = 0.0  # 0-1
    pro_score: int = 0  # 0-100
    reasons: list[str] = field(default_factory=list)
    particulier_signals: list[str] = field(default_factory=list)


def detect_pro(
    title: str | None,
    description: str | None,
    seller_name: str | None = None,
) -> ProDetectionResult:
    """
    Analyse une annonce pour déterminer si elle provient d'un pro ou d'un particulier.
    Retourne un résultat avec score et raisons.
    """
    result = ProDetectionResult()
    text = f"{title or ''} {description or ''} {seller_name or ''}".lower()

    # Règle 1: SIREN/SIRET
    if SIREN_PATTERN.search(text) or SIRET_PATTERN.search(text):
        result.is_likely_pro = True
        result.pro_score = 100
        result.confidence = 0.99
        result.reasons.append("Numéro SIREN/SIRET détecté")
        return result

    if RCS_PATTERN.search(text):
        result.is_likely_pro = True
        result.pro_score = 100
        result.confidence = 0.99
        result.reasons.append("Numéro RCS détecté")
        return result

    # Règle 2: Mots-clés pro directs
    pro_keyword_score = 0
    for keyword in PRO_KEYWORDS:
        if keyword in text:
            pro_keyword_score += 15
            result.reasons.append(f"Mot-clé pro: '{keyword}'")

    result.pro_score += min(60, pro_keyword_score)

    # Règle 3: Patterns suspects (analyse du langage)
    for pattern, weight, reason in SUSPICIOUS_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            result.pro_score += weight
            result.reasons.append(reason)

    # Signaux de particulier (réduisent le score)
    for marker in PARTICULIER_MARKERS:
        if marker in text:
            result.pro_score -= 10
            result.particulier_signals.append(f"Signal particulier: '{marker}'")

    # Analyse de la longueur et structure du texte
    if description:
        # Les pros ont tendance à avoir des descriptions très longues et structurées
        lines = description.strip().split("\n")
        if len(lines) > 20:
            result.pro_score += 10
            result.reasons.append("Description très longue et structurée (>20 lignes)")

        # Détecter les listes à puces formatées (typique agence)
        bullet_count = len(re.findall(r"^[\s]*[•\-✓✔→►]\s", description, re.MULTILINE))
        if bullet_count > 5:
            result.pro_score += 10
            result.reasons.append(f"{bullet_count} listes à puces (format agence)")

    # Analyse du nom du vendeur
    if seller_name:
        name_lower = seller_name.lower()
        pro_name_keywords = [
            "immobilier", "immo", "agence", "cabinet", "groupe",
            "réseau", "conseil", "patrimoine", "gestion",
        ]
        for kw in pro_name_keywords:
            if kw in name_lower:
                result.pro_score += 25
                result.reasons.append(f"Nom vendeur contient '{kw}'")

    # Clamp
    result.pro_score = max(0, min(100, result.pro_score))

    # Décision finale
    if result.pro_score >= 70:
        result.is_likely_pro = True
        result.confidence = min(0.95, result.pro_score / 100)
    elif result.pro_score >= 40:
        result.is_suspicious = True
        result.confidence = result.pro_score / 100
    else:
        result.confidence = 1.0 - (result.pro_score / 100)

    if not result.reasons:
        result.reasons.append("Aucun indicateur professionnel détecté")

    return result
