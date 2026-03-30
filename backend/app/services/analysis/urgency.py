from __future__ import annotations

import re
from dataclasses import dataclass, field


# Marqueurs et leurs poids pour le score d'urgence
VERY_HOT_KEYWORDS = {
    "mutation": 25,
    "muté": 25,
    "succession": 25,
    "héritage": 25,
    "héritier": 20,
    "urgent": 30,
    "urgence": 30,
    "vente urgente": 35,
    "libre de suite": 20,
    "libre immédiatement": 25,
    "baisse de prix": 25,
    "prix baissé": 25,
    "prix réduit": 20,
    "prix révisé": 20,
    "nouveau prix": 20,
    "divorce": 25,
    "séparation": 20,
    "liquidation": 25,
    "saisie": 25,
    "départ étranger": 20,
    "départ à l'étranger": 20,
    "expatriation": 20,
    "demenagement": 15,
    "déménagement": 15,
    "doit vendre": 25,
    "vente rapide": 25,
    "cause départ": 20,
    "cause mutation": 25,
    "cause divorce": 25,
    "cause décès": 25,
}

WARM_KEYWORDS = {
    "prix à débattre": 15,
    "a débattre": 15,
    "à débattre": 15,
    "faire offre": 15,
    "négociable": 12,
    "ouvert aux offres": 15,
    "toute offre étudiée": 18,
    "offre sérieuse": 12,
    "disponible rapidement": 10,
    "disponible immédiatement": 12,
    "visite possible": 8,
    "visite immédiate": 10,
    "première offre": 10,
    "à saisir": 12,
    "affaire à saisir": 15,
    "bonne affaire": 10,
    "rare": 8,
    "opportunité": 10,
    "idéal investisseur": 8,
    "rentabilité": 8,
    "travaux à prévoir": 10,
    "à rénover": 8,
    "vendu en l'état": 10,
}

COLD_KEYWORDS = {
    "pas pressé": -15,
    "curieux s'abstenir": -10,
    "agence s'abstenir": -5,
    "prix ferme": -10,
    "prix non négociable": -12,
    "ne pas déranger": -10,
    "sans intermédiaire": -5,
    "uniquement particulier": -5,
}


@dataclass
class UrgencyScore:
    value: int = 0
    factors: list[str] = field(default_factory=list)
    level: str = "froid"  # froid, tiede, chaud, tres_chaud


def compute_urgency_score(
    title: str | None,
    description: str | None,
    price: int | None = None,
    previous_price: int | None = None,
) -> UrgencyScore:
    result = UrgencyScore()
    text = f"{title or ''} {description or ''}".lower()

    # Nettoyer accents partiels
    text_normalized = text

    # Scanner les mots-clés très chauds
    for keyword, weight in VERY_HOT_KEYWORDS.items():
        if keyword.lower() in text_normalized:
            result.value += weight
            result.factors.append(f"Mot-clé détecté: '{keyword}'")

    # Scanner les mots-clés tièdes
    for keyword, weight in WARM_KEYWORDS.items():
        if keyword.lower() in text_normalized:
            result.value += weight
            result.factors.append(f"Signal: '{keyword}'")

    # Scanner les mots-clés froids (réduisent le score)
    for keyword, weight in COLD_KEYWORDS.items():
        if keyword.lower() in text_normalized:
            result.value += weight  # weight is negative
            result.factors.append(f"Signal froid: '{keyword}'")

    # Bonus si baisse de prix détectée
    if previous_price and price and previous_price > price:
        drop_pct = round((previous_price - price) / previous_price * 100)
        result.value += min(20, drop_pct * 2)
        result.factors.append(
            f"Baisse de prix de {drop_pct}% ({previous_price}€ → {price}€)"
        )

    # Détecter les montants barrés ou "ancien prix" dans le texte
    ancien_prix_match = re.search(
        r"(?:ancien prix|prix initial|avant|était à)\s*:?\s*([\d\s.]+)\s*€",
        text_normalized,
    )
    if ancien_prix_match and price:
        try:
            old = int(re.sub(r"[^\d]", "", ancien_prix_match.group(1)))
            if old > price:
                drop_pct = round((old - price) / old * 100)
                result.value += min(15, drop_pct * 2)
                result.factors.append(
                    f"Ancien prix détecté dans l'annonce: {old}€ → {price}€ (-{drop_pct}%)"
                )
        except ValueError:
            pass

    # Détecter les délais courts mentionnés
    delai_patterns = [
        (r"avant\s+(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)", 10),
        (r"d'ici\s+\d+\s+(semaine|mois|jour)", 12),
        (r"avant\s+fin\s+(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)", 15),
    ]
    for pattern, bonus in delai_patterns:
        if re.search(pattern, text_normalized):
            result.value += bonus
            result.factors.append("Délai de vente mentionné")
            break

    # Clamp 0-100
    result.value = max(0, min(100, result.value))

    # Déterminer le niveau
    if result.value >= 80:
        result.level = "tres_chaud"
    elif result.value >= 40:
        result.level = "chaud"
    elif result.value >= 20:
        result.level = "tiede"
    else:
        result.level = "froid"

    if not result.factors:
        result.factors.append("Aucun signal d'urgence détecté")

    return result
