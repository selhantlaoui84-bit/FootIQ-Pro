from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any

from services.odds_engine import (
    calculate_edge,
    calculate_expected_value,
    calculate_risk_adjusted_value,
    calculate_value_score,
    classify_value_opportunity,
    explain_value_opportunity,
    fair_odds_from_probability,
    implied_probability_from_odds,
    minimum_value_odds,
    normalize_decimal_odds,
    probability_for_selection,
    select_reference_odds,
    selection_from_prediction,
)


def _match_id(item: dict[str, Any]) -> str:
    return str(item.get("match_id") or item.get("id") or item.get("slug") or "")


def _risk_level(score: int | float | None) -> str:
    if score is None:
        return "unknown"
    if score >= 80:
        return "very_high"
    if score >= 60:
        return "high"
    if score >= 35:
        return "moderate"
    return "low"


def _as_score(value: Any, fallback: float = 55) -> float:
    try:
        return max(0, min(100, float(value)))
    except (TypeError, ValueError):
        return fallback


def _reliability_score(prediction: dict[str, Any], context: dict[str, Any]) -> float:
    market = str(context.get("market") or "1X2")
    competition = str(prediction.get("competition") or context.get("competition") or "unknown")
    market_scores = context.get("market_reliability") or {}
    competition_scores = context.get("competition_reliability") or {}
    feature_quality = (prediction.get("features") or {}).get("data_quality_score")
    base = _as_score(feature_quality, 55)
    if isinstance(market_scores, dict) and market in market_scores:
        base = (base + _as_score(market_scores[market], base)) / 2
    if isinstance(competition_scores, dict) and competition in competition_scores:
        base = (base + _as_score(competition_scores[competition], base)) / 2
    calibration_status = str(context.get("calibration_status") or "")
    if calibration_status in {"overconfident", "insufficient_data"}:
        base -= 10
    return max(0, min(100, round(base, 2)))


def _user_fit_score(prediction: dict[str, Any], context: dict[str, Any]) -> float | None:
    profile = context.get("user_profile") or {}
    if not isinstance(profile, dict):
        return None
    preferred = profile.get("preferred_markets") or []
    market = context.get("market") or "1X2"
    roi = profile.get("user_roi")
    score = 50
    if market in preferred:
        score += 20
    try:
        if roi is not None:
            score += max(-20, min(20, float(roi) * 100))
    except (TypeError, ValueError):
        pass
    return max(0, min(100, round(score, 2)))


def detect_high_odds_trap(item: dict[str, Any]) -> bool:
    odds = normalize_decimal_odds(item.get("odds_decimal"))
    probability = item.get("used_probability")
    try:
        probability_value = float(probability)
    except (TypeError, ValueError):
        probability_value = 0
    return bool(odds and odds >= 3 and probability_value < 0.38)


def detect_overpriced_favorite(item: dict[str, Any]) -> bool:
    odds = normalize_decimal_odds(item.get("odds_decimal"))
    probability = item.get("used_probability")
    try:
        probability_value = float(probability)
    except (TypeError, ValueError):
        probability_value = 0
    return bool(odds and odds <= 1.45 and probability_value >= 0.6 and (item.get("expected_value") or 0) <= 0.02)


def detect_false_value(item: dict[str, Any]) -> bool:
    return bool(
        item.get("value_status") in {"strong_value", "positive_value"}
        and (
            item.get("risk_score", 0) >= 80
            or item.get("is_stale_odds")
            or item.get("is_high_odds_trap")
            or item.get("reliability_score", 100) < 35
        )
    )


def _opportunity_level(score: int | None, value_status: str, risk_score: int | float | None, has_odds: bool, is_data_limited: bool) -> str:
    if not has_odds:
        return "unavailable"
    if value_status in {"no_real_odds", "insufficient_data"}:
        return "unavailable" if is_data_limited else "watchlist"
    if value_status == "avoid" or (risk_score is not None and risk_score >= 85):
        return "avoid"
    if score is None:
        return "weak"
    if score >= 80:
        return "excellent"
    if score >= 65:
        return "good"
    if score >= 45:
        return "watchlist"
    if score >= 25:
        return "weak"
    return "avoid"


def _recommendation_type(value_status: str, opportunity_level: str, warnings: list[str]) -> str:
    if value_status in {"no_real_odds", "insufficient_data"}:
        return "wait"
    if opportunity_level == "avoid" or value_status in {"avoid", "no_value"}:
        return "avoid"
    if opportunity_level in {"excellent", "good"} and not warnings:
        return "recommended"
    if value_status in {"strong_value", "positive_value"}:
        return "cautious"
    return "informational"


def evaluate_value_bet(prediction: dict[str, Any], odds: dict[str, Any] | None, context: dict[str, Any] | None = None) -> dict[str, Any]:
    context = context or {}
    selection = str(context.get("selection") or selection_from_prediction(prediction))
    market = str(context.get("market") or "1X2")
    model_probability = probability_for_selection({**prediction, "calibrated_probabilities_json": None}, selection)
    calibrated_probability = probability_for_selection(prediction, selection)
    used_probability = calibrated_probability if calibrated_probability is not None else model_probability
    risk_score = int(_as_score(prediction.get("risk_score"), 45))
    reliability_score = _reliability_score(prediction, {**context, "market": market})
    user_fit = _user_fit_score(prediction, {**context, "market": market})
    has_probability = used_probability is not None
    has_odds = odds is not None and normalize_decimal_odds((odds or {}).get("odds_decimal")) is not None

    base = {
        "match_id": _match_id(prediction),
        "home_team": prediction.get("home_team"),
        "away_team": prediction.get("away_team"),
        "competition": prediction.get("competition"),
        "market": market,
        "selection": selection,
        "model_probability": model_probability,
        "calibrated_probability": calibrated_probability if calibrated_probability != model_probability else None,
        "used_probability": used_probability,
        "risk_score": risk_score,
        "risk_level": _risk_level(risk_score),
        "reliability_score": reliability_score,
        "user_fit_score": user_fit,
    }
    if not has_probability:
        return {
            **base,
            "value_status": "insufficient_data",
            "opportunity_score": None,
            "opportunity_level": "unavailable",
            "recommendation_type": "wait",
            "reason": "Données insuffisantes pour qualifier cette opportunité.",
            "warnings": ["Données insuffisantes"],
            "is_value_bet": False,
            "is_data_limited": True,
            "odds_source": None,
        }
    if not has_odds:
        return {
            **base,
            "bookmaker": None,
            "odds_decimal": None,
            "odds_source": None,
            "odds_collected_at": None,
            "odds_stale": False,
            "implied_probability": None,
            "fair_odds": fair_odds_from_probability(used_probability),
            "minimum_value_odds": minimum_value_odds(used_probability),
            "edge": None,
            "expected_value": None,
            "risk_adjusted_value": None,
            "value_score": None,
            "value_status": "no_real_odds",
            "opportunity_score": None,
            "opportunity_level": "unavailable",
            "recommendation_type": "wait",
            "reason": "Cote réelle non disponible : impossible de calculer la value.",
            "warnings": ["Cote réelle non disponible"],
            "is_value_bet": False,
            "is_false_value_risk": False,
            "is_overpriced_favorite": False,
            "is_high_odds_trap": False,
            "is_data_limited": False,
            "is_stale_odds": False,
        }

    decimal = normalize_decimal_odds(odds.get("odds_decimal"))
    edge = calculate_edge(used_probability, decimal)
    expected_value = calculate_expected_value(used_probability, decimal)
    risk_adjusted = calculate_risk_adjusted_value(expected_value, risk_score)
    value_status = classify_value_opportunity(edge, expected_value, risk_score, reliability_score)
    value_score = calculate_value_score(used_probability, decimal, risk_score, reliability_score)
    confidence_score = _as_score((prediction.get("confidence") or {}).get("score"), 50)
    odds_quality_score = 4 if odds.get("stale") else 10
    user_component = ((user_fit or 50) / 100) * 10 if user_fit is not None else 5
    raw_score = (
        ((value_score or 0) / 100) * 40
        + (confidence_score / 100) * 20
        + (reliability_score / 100) * 20
        + odds_quality_score
        + user_component
    )
    if risk_score >= 75:
        raw_score -= 15
    if odds.get("stale"):
        raw_score -= 10
    if reliability_score < 35:
        raw_score -= 12
    opportunity_score = int(max(0, min(100, round(raw_score))))
    item = {
        **base,
        "bookmaker": odds.get("bookmaker"),
        "odds_decimal": decimal,
        "odds_source": odds.get("source_type") or ("manual_user_input" if odds.get("source") == "manual_user_input" else "provider"),
        "odds_collected_at": odds.get("collected_at"),
        "odds_stale": bool(odds.get("stale")),
        "provider": odds.get("provider"),
        "implied_probability": implied_probability_from_odds(decimal),
        "fair_odds": fair_odds_from_probability(used_probability),
        "minimum_value_odds": minimum_value_odds(used_probability),
        "edge": edge,
        "expected_value": expected_value,
        "risk_adjusted_value": risk_adjusted,
        "value_score": value_score,
        "value_status": value_status,
        "opportunity_score": opportunity_score,
        "is_data_limited": reliability_score < 35,
        "is_stale_odds": bool(odds.get("stale")),
    }
    item["is_high_odds_trap"] = detect_high_odds_trap(item)
    item["is_overpriced_favorite"] = detect_overpriced_favorite(item)
    item["is_false_value_risk"] = detect_false_value(item)
    item["is_value_bet"] = value_status in {"strong_value", "positive_value"} and not item["is_false_value_risk"]
    level = _opportunity_level(opportunity_score, value_status, risk_score, True, item["is_data_limited"])
    if item["is_false_value_risk"] and level in {"excellent", "good"}:
        level = "watchlist"
    item["opportunity_level"] = level
    explanation = explain_value_opportunity(value_status, used_probability, decimal, edge, expected_value, risk_score, bool(odds.get("stale")))
    warnings = list(explanation["warnings"])
    if item["is_high_odds_trap"]:
        warnings.append("Cote élevée avec probabilité faible : risque de piège.")
    if item["is_overpriced_favorite"]:
        warnings.append("Favori trop bas : value limitée.")
    if item["is_false_value_risk"]:
        warnings.append("Signal de fausse value possible.")
    item["warnings"] = warnings
    item["reason"] = explanation["reason"]
    item["recommendation_type"] = _recommendation_type(value_status, level, warnings)
    return item


def evaluate_prediction_opportunity(prediction: dict[str, Any], context: dict[str, Any] | None = None) -> dict[str, Any]:
    context = context or {}
    selection = str(context.get("selection") or selection_from_prediction(prediction))
    market = str(context.get("market") or "1X2")
    match_id = _match_id(prediction)
    odds_lookup = context.get("odds_lookup") or {}
    rows = odds_lookup.get(match_id) if isinstance(odds_lookup, dict) else []
    odds = select_reference_odds(
        [
            item for item in (rows or [])
            if str(item.get("market") or "").lower() == market.lower()
            and str(item.get("selection") or "").upper() == selection.upper()
        ]
    )
    return evaluate_value_bet(prediction, odds, {**context, "selection": selection, "market": market})


def rank_value_opportunities(predictions: list[dict[str, Any]], context: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    items = [evaluate_prediction_opportunity(prediction, context or {}) for prediction in predictions]
    return sorted(
        items,
        key=lambda item: (
            item.get("opportunity_score") if item.get("opportunity_score") is not None else -1,
            item.get("expected_value") if item.get("expected_value") is not None else -999,
        ),
        reverse=True,
    )


def build_value_bet_summary(items: list[dict[str, Any]]) -> dict[str, Any]:
    statuses = Counter(item.get("value_status") for item in items)
    levels = Counter(item.get("opportunity_level") for item in items)
    ev_values = [float(item["expected_value"]) for item in items if item.get("expected_value") is not None]
    return {
        "strong_value_count": statuses.get("strong_value", 0),
        "positive_value_count": statuses.get("positive_value", 0),
        "watchlist_count": levels.get("watchlist", 0),
        "avoid_count": statuses.get("avoid", 0) + levels.get("avoid", 0),
        "no_real_odds_count": statuses.get("no_real_odds", 0),
        "insufficient_data_count": statuses.get("insufficient_data", 0),
        "average_ev": round(sum(ev_values) / len(ev_values), 4) if ev_values else None,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
