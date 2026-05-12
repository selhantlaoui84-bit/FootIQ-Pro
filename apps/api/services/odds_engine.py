from __future__ import annotations

from typing import Any


def normalize_decimal_odds(value: Any) -> float | None:
    try:
        odds = float(value)
    except (TypeError, ValueError):
        return None
    if not odds or odds <= 1 or odds > 1000:
        return None
    return round(odds, 4)


def implied_probability_from_odds(odds: Any) -> float | None:
    normalized = normalize_decimal_odds(odds)
    if normalized is None:
        return None
    return round(1 / normalized, 4)


def fair_odds_from_probability(probability: Any) -> float | None:
    normalized = _probability_01(probability)
    if normalized is None or normalized <= 0:
        return None
    return round(1 / normalized, 4)


def minimum_value_odds(probability: Any, margin: float = 0.02) -> float | None:
    fair_odds = fair_odds_from_probability(probability)
    if fair_odds is None:
        return None
    try:
        safe_margin = max(0, float(margin))
    except (TypeError, ValueError):
        safe_margin = 0.02
    return round(fair_odds * (1 + safe_margin), 4)


def calculate_bookmaker_margin(odds_list: list[Any]) -> float | None:
    probabilities = [implied_probability_from_odds(item) for item in odds_list]
    clean = [item for item in probabilities if item is not None]
    if not clean:
        return None
    return round(sum(clean) - 1, 4)


def select_reference_odds(odds: list[dict[str, Any]] | dict[str, Any] | None) -> dict[str, Any] | None:
    if not odds:
        return None
    rows = [odds] if isinstance(odds, dict) else [item for item in odds if isinstance(item, dict)]
    clean = [item for item in rows if normalize_decimal_odds(item.get("odds_decimal") or item.get("odds")) is not None]
    if not clean:
        return None
    selected = max(clean, key=lambda item: normalize_decimal_odds(item.get("odds_decimal") or item.get("odds")) or 0)
    decimal = normalize_decimal_odds(selected.get("odds_decimal") or selected.get("odds"))
    return {
        **selected,
        "odds_decimal": decimal,
        "implied_probability": selected.get("implied_probability") or implied_probability_from_odds(decimal),
    }


def _probability_01(value: Any) -> float | None:
    try:
        probability = float(value)
    except (TypeError, ValueError):
        return None
    if probability > 1:
        probability = probability / 100
    if probability < 0 or probability > 1:
        return None
    return probability


def calculate_edge(model_probability: Any, odds: Any) -> float | None:
    probability = _probability_01(model_probability)
    implied = implied_probability_from_odds(odds)
    if probability is None or implied is None:
        return None
    return round(probability - implied, 4)


def calculate_expected_value(model_probability: Any, odds: Any) -> float | None:
    probability = _probability_01(model_probability)
    decimal = normalize_decimal_odds(odds)
    if probability is None or decimal is None:
        return None
    return round(probability * (decimal - 1) - (1 - probability), 4)


def calculate_risk_adjusted_value(expected_value: Any, risk_score: Any) -> float | None:
    try:
        ev = float(expected_value)
    except (TypeError, ValueError):
        return None
    try:
        risk = max(0, min(100, float(risk_score if risk_score is not None else 50)))
    except (TypeError, ValueError):
        risk = 50
    return round(ev * (1 - risk / 100), 4)


def calculate_value_score(probability: Any, odds_decimal: Any, risk_score: Any = None, reliability_score: Any = None) -> int | None:
    edge = calculate_edge(probability, odds_decimal)
    expected_value = calculate_expected_value(probability, odds_decimal)
    if edge is None or expected_value is None:
        return None
    try:
        risk = max(0, min(100, float(risk_score if risk_score is not None else 50)))
    except (TypeError, ValueError):
        risk = 50
    try:
        reliability = max(0, min(100, float(reliability_score if reliability_score is not None else 55)))
    except (TypeError, ValueError):
        reliability = 55
    raw = (max(0, expected_value) * 240) + (max(0, edge) * 180) + (reliability * 0.2) - (risk * 0.25)
    return int(max(0, min(100, round(raw))))


def classify_value_opportunity(edge: Any, expected_value: Any, risk_score: Any = None, data_quality: Any = None) -> str:
    try:
        risk = float(risk_score) if risk_score is not None else None
    except (TypeError, ValueError):
        risk = None
    if edge is None or expected_value is None:
        return "no_real_odds"
    try:
        quality = float(data_quality) if data_quality is not None else None
    except (TypeError, ValueError):
        quality = None
    if quality is not None and quality < 20:
        return "insufficient_data"
    ev = float(expected_value)
    edge_value = float(edge)
    if risk is not None and risk >= 85:
        return "avoid"
    if ev < -0.08:
        return "avoid"
    if ev < -0.02:
        return "no_value"
    if ev <= 0.02:
        return "fair_price"
    if ev >= 0.08 and edge_value >= 0.05 and (risk is None or risk <= 60):
        return "strong_value"
    if ev >= 0.02 and edge_value >= 0.02 and (risk is None or risk <= 75):
        return "positive_value"
    if risk is not None and risk > 75:
        return "avoid"
    if ev > 0.02:
        return "fair_price"
    return "no_value"


def classify_value_bet(edge: Any, expected_value: Any, risk_score: Any = None) -> str:
    return classify_value_opportunity(edge, expected_value, risk_score)


def explain_value_opportunity(
    value_status: str,
    probability: Any = None,
    odds_decimal: Any = None,
    edge: Any = None,
    expected_value: Any = None,
    risk_score: Any = None,
    stale: bool = False,
) -> dict[str, Any]:
    warnings: list[str] = []
    if stale:
        warnings.append("Cote ancienne : surveiller avant de décider.")
    if value_status == "no_real_odds":
        reason = "Cote réelle non disponible : impossible de calculer la value."
    elif value_status == "insufficient_data":
        reason = "Données insuffisantes pour qualifier cette opportunité."
    elif value_status == "strong_value":
        reason = "La cote est nettement supérieure à la cote juste estimée, avec un risque contenu."
    elif value_status == "positive_value":
        reason = "La cote est supérieure à notre cote juste estimée."
    elif value_status == "fair_price":
        reason = "La cote semble proche de la probabilité estimée."
    elif value_status == "no_value":
        reason = "Le modèle est confiant, mais la cote est trop basse pour créer une value."
    else:
        reason = "Le rapport value/risque invite à éviter cette opportunité."
    if risk_score is not None:
        try:
            if float(risk_score) >= 75:
                warnings.append("Risque élevé : prudence recommandée.")
        except (TypeError, ValueError):
            pass
    return {
        "reason": reason,
        "warnings": warnings,
        "fair_odds": fair_odds_from_probability(probability),
        "minimum_value_odds": minimum_value_odds(probability),
        "implied_probability": implied_probability_from_odds(odds_decimal),
        "edge": edge,
        "expected_value": expected_value,
    }


def enrich_prediction_with_real_odds(prediction: dict[str, Any], odds: dict[str, Any] | None) -> dict[str, Any]:
    selection = selection_from_prediction(prediction)
    probability = probability_for_selection(prediction, selection)
    if not odds:
        return {
            **prediction,
            "selection": selection,
            "real_odds": None,
            "value_status": "no_real_odds",
            "edge": None,
            "expected_value": None,
            "implied_probability": None,
        }
    decimal = odds.get("odds_decimal")
    edge = calculate_edge(probability, decimal)
    expected_value = calculate_expected_value(probability, decimal)
    return {
        **prediction,
        "selection": selection,
        "real_odds": odds,
        "value_status": classify_value_bet(edge, expected_value, prediction.get("risk_score")),
        "edge": edge,
        "expected_value": expected_value,
        "implied_probability": implied_probability_from_odds(decimal),
    }


def selection_from_prediction(prediction: dict[str, Any]) -> str:
    probabilities = prediction.get("probabilities") or {}
    mapping = {"home": "HOME_WIN", "draw": "DRAW", "away": "AWAY_WIN"}
    if not isinstance(probabilities, dict) or not probabilities:
        return "HOME_WIN"
    favorite = max(("home", "draw", "away"), key=lambda key: float(probabilities.get(key, 0) or 0))
    return mapping[favorite]


def probability_for_selection(prediction: dict[str, Any], selection: str) -> float | None:
    calibrated = prediction.get("calibrated_probabilities_json") or prediction.get("calibrated_probabilities")
    probabilities = calibrated if isinstance(calibrated, dict) else prediction.get("probabilities")
    key = {"HOME_WIN": "home", "DRAW": "draw", "AWAY_WIN": "away"}.get(selection, "home")
    return _probability_01((probabilities or {}).get(key))
