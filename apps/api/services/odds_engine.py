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


def classify_value_bet(edge: Any, expected_value: Any, risk_score: Any = None) -> str:
    try:
        risk = float(risk_score) if risk_score is not None else None
    except (TypeError, ValueError):
        risk = None
    if edge is None or expected_value is None:
        return "no_odds"
    ev = float(expected_value)
    if risk is not None and risk >= 85:
        return "avoid"
    if ev < -0.08:
        return "avoid"
    if ev < -0.02:
        return "no_value"
    if ev <= 0.02:
        return "fair_price"
    if ev > 0.08:
        return "strong_value"
    return "positive_value"


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
