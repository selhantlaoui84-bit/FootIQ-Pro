from __future__ import annotations

from collections import Counter
from typing import Any

VERSION = "explainability-v1"
DISCLAIMER = "Modèle probabiliste. Aucune garantie de résultat."

FACTOR_LABELS = {
    "elo_delta": "Écart Elo",
    "form_delta": "Forme récente",
    "attack_delta": "Différentiel offensif",
    "defense_delta": "Solidité défensive",
    "draw_risk_score": "Risque de match nul",
    "data_quality_score": "Qualité des données",
    "risk_score": "Score de risque",
    "trap_match_score": "Risque de piège",
    "expected_home": "Buts attendus domicile",
    "expected_away": "Buts attendus extérieur",
    "home_recent_points_per_match": "Forme récente domicile",
    "away_recent_points_per_match": "Forme récente extérieur",
    "rest_days_delta": "Écart de récupération",
    "schedule_density_delta_14d": "Charge calendrier",
    "home_win_streak": "Série de victoires domicile",
    "away_win_streak": "Série de victoires extérieur",
}


def _num(value: Any, default: float | None = 0) -> float | None:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _round_value(value: Any) -> int | float | str | None:
    numeric = _num(value, None)
    if numeric is None:
        return value if isinstance(value, str) else None
    if abs(numeric - round(numeric)) < 0.001:
        return int(round(numeric))
    return round(numeric, 2)


def _pick(probabilities: dict[str, Any] | None) -> str | None:
    values = {key: _num((probabilities or {}).get(key), 0) or 0 for key in ("home", "draw", "away")}
    if max(values.values()) <= 0:
        return None
    return max(values, key=values.get)


def _pick_label(pick: str | None) -> str:
    return {"home": "domicile", "draw": "nul", "away": "extérieur"}.get(pick or "", "le signal principal")


def _impact(feature: str, value: Any, pick: str | None) -> tuple[str, int, str]:
    numeric = _num(value, None)
    if numeric is None:
        return "neutral", 0, "Signal indisponible ou non numérique."

    abs_value = abs(numeric)
    label_pick = _pick_label(pick)

    if feature in {"risk_score", "trap_match_score"}:
        if numeric >= 70:
            return "negative", min(100, round(numeric)), "Risque élevé: la lecture du match doit rester prudente."
        if numeric >= 55:
            return "negative", round(numeric * 0.75), "Risque modéré qui réduit la lisibilité du signal."
        return "positive", max(15, round(55 - numeric)), "Risque contenu, ce qui rend le signal plus lisible."

    if feature == "draw_risk_score":
        if numeric >= 65 and pick != "draw":
            return "negative", min(90, round(numeric)), "Le risque de nul affaiblit la lecture du favori."
        if pick == "draw" and numeric >= 50:
            return "positive", min(80, round(numeric)), "Le profil du match soutient une lecture orientée nul."
        return "neutral", round(min(50, numeric)), "Le risque de nul reste surveillé sans dominer l'analyse."

    if feature == "data_quality_score":
        if numeric >= 75:
            return "positive", min(100, round(numeric)), "La qualité des données renforce la lisibilité statistique."
        if numeric < 50:
            return "negative", round(70 - numeric), "Qualité de données limitée: interprétation plus prudente."
        return "neutral", round(numeric * 0.5), "Qualité de données correcte mais perfectible."

    if feature in {"elo_delta", "form_delta", "attack_delta", "home_recent_points_per_match", "home_recent_win_rate", "home_win_streak"}:
        if numeric > 0:
            aligned = pick == "home"
            return ("positive" if aligned else "negative"), min(95, round(abs_value * 1.2)), f"Ce signal penche vers le domicile et {'soutient' if aligned else 'nuance'} le choix {label_pick}."
        if numeric < 0:
            aligned = pick == "away"
            return ("positive" if aligned else "negative"), min(95, round(abs_value * 1.2)), f"Ce signal penche vers l'extérieur et {'soutient' if aligned else 'nuance'} le choix {label_pick}."

    if feature in {"defense_delta", "away_recent_points_per_match", "away_recent_win_rate", "away_win_streak"}:
        if numeric > 0:
            aligned = pick == "away"
            return ("positive" if aligned else "negative"), min(95, round(abs_value * 1.2)), f"Ce signal avantage l'extérieur et {'confirme' if aligned else 'fragilise'} le choix {label_pick}."
        if numeric < 0:
            aligned = pick == "home"
            return ("positive" if aligned else "negative"), min(95, round(abs_value * 1.2)), f"Ce signal avantage le domicile et {'confirme' if aligned else 'fragilise'} le choix {label_pick}."

    if feature == "rest_days_delta":
        if numeric > 0:
            aligned = pick == "home"
            return ("positive" if aligned else "negative"), min(80, round(abs_value * 12)), "Le domicile semble disposer d'un meilleur temps de récupération."
        if numeric < 0:
            aligned = pick == "away"
            return ("positive" if aligned else "negative"), min(80, round(abs_value * 12)), "L'extérieur semble disposer d'un meilleur temps de récupération."

    if feature == "schedule_density_delta_14d":
        if numeric > 0:
            aligned = pick == "away"
            return ("positive" if aligned else "negative"), min(80, round(abs_value * 18)), "Le domicile a eu une charge calendrier plus lourde."
        if numeric < 0:
            aligned = pick == "home"
            return ("positive" if aligned else "negative"), min(80, round(abs_value * 18)), "L'extérieur a eu une charge calendrier plus lourde."

    if feature == "expected_home":
        aligned = pick == "home"
        return ("positive" if aligned and numeric >= 1.5 else "neutral"), min(75, round(numeric * 28)), "Les buts attendus du domicile donnent un repère offensif."

    if feature == "expected_away":
        aligned = pick == "away"
        return ("positive" if aligned and numeric >= 1.5 else "neutral"), min(75, round(numeric * 28)), "Les buts attendus de l'extérieur donnent un repère offensif."

    if abs_value >= 20:
        return "positive", min(70, round(abs_value)), "Signal notable dans la lecture du match."
    if abs_value >= 8:
        return "neutral", min(45, round(abs_value)), "Signal secondaire, utile mais non dominant."
    return "neutral", 10, "Signal faible ou équilibré."


def format_factor_label(feature_name: str) -> str:
    if feature_name in FACTOR_LABELS:
        return FACTOR_LABELS[feature_name]
    return str(feature_name or "").replace("_", " ").strip().capitalize() or "Facteur"


def score_feature_impact(feature_name: str, value: Any, production_prediction: dict[str, Any]) -> dict[str, Any]:
    probabilities = production_prediction.get("probabilities") or {}
    pick = _pick(probabilities)
    impact, strength, message = _impact(feature_name, value, pick)
    return {
        "feature": feature_name,
        "label": format_factor_label(feature_name),
        "value": _round_value(value),
        "impact": impact,
        "strength": max(0, min(100, int(strength or 0))),
        "message": message,
    }


def build_prediction_explanation(
    production_prediction: dict[str, Any],
    hybrid_engine: dict[str, Any] | None = None,
) -> dict[str, Any]:
    features = dict(production_prediction.get("features") or {})
    goals = production_prediction.get("goals") or {}
    probabilities = production_prediction.get("probabilities") or {}
    confidence = production_prediction.get("confidence") or {}

    features.setdefault("risk_score", production_prediction.get("risk_score"))
    features.setdefault("trap_match_score", production_prediction.get("trap_match_score"))
    features.setdefault("expected_home", goals.get("expected_home"))
    features.setdefault("expected_away", goals.get("expected_away"))

    impacts = [
        score_feature_impact(name, value, production_prediction)
        for name, value in features.items()
        if value is not None
    ]
    positives = sorted([item for item in impacts if item["impact"] == "positive"], key=lambda item: item["strength"], reverse=True)[:5]
    negatives = sorted([item for item in impacts if item["impact"] == "negative"], key=lambda item: item["strength"], reverse=True)[:5]
    neutral = sorted([item for item in impacts if item["impact"] == "neutral"], key=lambda item: item["strength"], reverse=True)[:5]

    pick = _pick(probabilities)
    pick_text = _pick_label(pick)
    confidence_score = int(_num(confidence.get("score"), 0) or 0)
    max_probability = max((_num(probabilities.get(key), 0) or 0 for key in ("home", "draw", "away")), default=0)

    if confidence_score >= 75:
        confidence_reading = "Signal lisible: plusieurs indicateurs convergent, sans certitude de résultat."
    elif confidence_score >= 55:
        confidence_reading = "Signal modéré: la tendance existe, mais elle demande une lecture prudente."
    else:
        confidence_reading = "Lisibilité faible: le match contient trop d'incertitudes pour un signal fort."

    risk_notes: list[str] = []
    if (production_prediction.get("risk_score") or 0) >= 60:
        risk_notes.append("Le score de risque invite à réduire la confiance opérationnelle.")
    if (production_prediction.get("trap_match_score") or 0) >= 60:
        risk_notes.append("Le risque de piège indique un favori moins confortable qu'il n'y paraît.")
    if (features.get("draw_risk_score") or 0) >= 65:
        risk_notes.append("Le risque de nul peut brouiller la lecture du vainqueur.")

    data_quality_notes: list[str] = []
    data_quality = _num(features.get("data_quality_score"), None)
    if data_quality is None:
        data_quality_notes.append("La qualité des données n'est pas renseignée pour ce match.")
    elif data_quality < 55:
        data_quality_notes.append("La qualité des données est limitée: le modèle doit être lu avec prudence.")
    else:
        data_quality_notes.append("La qualité des données est suffisante pour une lecture probabiliste.")

    hybrid_notes: list[str] = []
    if hybrid_engine:
        agreement = hybrid_engine.get("agreement")
        if agreement == "disagree":
            hybrid_notes.append("Le ML shadow contredit le signal officiel: une revue manuelle est préférable.")
        elif agreement == "agree":
            hybrid_notes.append("Le ML shadow va dans le même sens que le modèle officiel.")
        if hybrid_engine.get("decision_label") == "eviter":
            hybrid_notes.append("Le moteur hybride classe ce match dans une zone à éviter.")

    summary = f"Le modèle officiel oriente la lecture vers {pick_text} avec une probabilité principale de {round(max_probability)}%."
    official_signal = f"Signal officiel: {pick_text}, porté par {len(positives)} facteur(s) favorable(s) et {len(negatives)} point(s) de prudence."
    plain_language = (
        "Cette explication traduit les signaux statistiques disponibles avant le match. "
        "Elle aide à comprendre la prédiction, sans prouver la cause du résultat futur."
    )

    return {
        "version": VERSION,
        "summary": summary,
        "official_signal": official_signal,
        "confidence_reading": confidence_reading,
        "top_positive_factors": positives,
        "top_negative_factors": negatives,
        "neutral_factors": neutral,
        "risk_notes": risk_notes,
        "data_quality_notes": data_quality_notes,
        "hybrid_notes": hybrid_notes,
        "plain_language": plain_language,
        "disclaimer": DISCLAIMER,
    }


def build_explainability_summary(predictions: list[dict[str, Any]], limit: int = 200) -> dict[str, Any]:
    selected = list(predictions or [])[: max(1, min(int(limit or 200), 1000))]
    positive_counter: Counter[str] = Counter()
    negative_counter: Counter[str] = Counter()
    high_confidence = 0
    low_confidence = 0
    high_risk = 0
    trap_risk = 0

    for prediction in selected:
        confidence = int(_num((prediction.get("confidence") or {}).get("score"), 0) or 0)
        high_confidence += int(confidence >= 75)
        low_confidence += int(confidence < 55)
        high_risk += int((_num(prediction.get("risk_score"), 0) or 0) >= 65)
        trap_risk += int((_num(prediction.get("trap_match_score"), 0) or 0) >= 60 or bool((prediction.get("flags") or {}).get("trap_match")))
        explanation = build_prediction_explanation(prediction)
        positive_counter.update(item["label"] for item in explanation["top_positive_factors"])
        negative_counter.update(item["label"] for item in explanation["top_negative_factors"])

    return {
        "version": VERSION,
        "processed_predictions": len(selected),
        "high_confidence_count": high_confidence,
        "low_confidence_count": low_confidence,
        "high_risk_count": high_risk,
        "trap_risk_count": trap_risk,
        "most_common_positive_factors": dict(positive_counter.most_common(8)),
        "most_common_negative_factors": dict(negative_counter.most_common(8)),
        "note": "L'explicabilité décrit les signaux du modèle sans garantir le résultat.",
    }
