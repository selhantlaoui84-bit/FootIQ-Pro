from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any

from services.odds_engine import (
    calculate_edge,
    calculate_expected_value,
    classify_value_bet,
    implied_probability_from_odds,
    probability_for_selection,
    select_reference_odds,
    selection_from_prediction,
)

FORBIDDEN_PROMISES = ("pari sûr", "gain garanti", "100% sûr", "100 % sûr", "sans risque", "garanti")


def _match_id(item: dict[str, Any]) -> str:
    return str(item.get("match_id") or item.get("id") or item.get("slug") or "")


def _odds_for_prediction(prediction: dict[str, Any], odds_lookup: dict[str, list[dict[str, Any]]] | None, selection: str) -> dict[str, Any] | None:
    match_id = _match_id(prediction)
    rows = (odds_lookup or {}).get(match_id) or []
    reference = select_reference_odds(
        [
            item for item in rows
            if str(item.get("market") or "").lower() in {"1x2", "1X2".lower()}
            and str(item.get("selection") or "").upper() == selection
        ]
    )
    if reference:
        return reference
    raw_odds = prediction.get("odds") or prediction.get("market_odds") or {}
    if isinstance(raw_odds, dict):
        value = raw_odds.get(selection) or raw_odds.get(selection.lower()) or raw_odds.get(selection.replace("_WIN", "").lower())
        if value:
            return select_reference_odds({"bookmaker": "prediction", "market": "1X2", "selection": selection, "odds_decimal": value})
    return None


def _risk_level(score: int | None) -> str:
    if score is None:
        return "unknown"
    if score >= 80:
        return "very_high"
    if score >= 60:
        return "high"
    if score >= 35:
        return "moderate"
    return "low"


def assess_bet_risk(prediction: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []
    base = int(prediction.get("risk_score") or 45)
    calibration_status = str(context.get("calibration_status") or "insufficient_data")
    if context.get("odds") is None:
        base += 15
        reasons.append("Cote non disponible : impossible de valider la value.")
    if calibration_status in {"insufficient_data", "overconfident"}:
        base += 12
        reasons.append("Calibration encore limitée ou modèle potentiellement trop confiant.")
    if context.get("expected_value") is not None and float(context["expected_value"]) < 0:
        base += 18
        reasons.append("Expected value négative.")
    confidence = (prediction.get("confidence") or {}).get("score")
    if confidence is None or float(confidence) < 60:
        base += 10
        reasons.append("Confiance modèle limitée.")
    score = max(0, min(100, base))
    return {"risk_score": score, "risk_level": _risk_level(score), "risk_reasons": reasons}


def generate_assistant_recommendation(prediction: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    value_status = context.get("value_status")
    risk_level = context.get("risk_level")
    if value_status == "no_odds":
        recommendation_type = "wait"
        label = "Cote non disponible"
        reason = "Cote non disponible : impossible de calculer la value."
    elif value_status == "insufficient_data":
        recommendation_type = "insufficient_data"
        label = "Données insuffisantes"
        reason = "Données insuffisantes pour formuler une recommandation de pari."
    elif value_status in {"avoid", "no_value"}:
        recommendation_type = "avoid"
        label = "À éviter"
        reason = "La cote ne compense pas le risque estimé par le modèle."
    elif value_status in {"strong_value", "positive_value"} and risk_level in {"low", "moderate"}:
        recommendation_type = "recommended"
        label = "Value détectée"
        reason = "Probabilité modèle supérieure à la probabilité implicite bookmaker, avec risque contenu."
    elif value_status in {"strong_value", "positive_value"}:
        recommendation_type = "cautious"
        label = "Prudence"
        reason = "Value positive détectée, mais le risque ou le volume de données impose de rester prudent."
    else:
        recommendation_type = "informational"
        label = "Prix juste"
        reason = "La cote semble proche de la probabilité estimée : pas de value claire."
    return {
        "recommendation_type": recommendation_type,
        "recommendation_label": label,
        "recommendation_reason": reason,
        "confidence_explanation": f"Confiance modèle : {(prediction.get('confidence') or {}).get('score', 'Non disponible')}.",
        "value_explanation": "La value compare la probabilité modèle à la probabilité implicite de la cote.",
        "risk_explanation": "Le risque reste affiché car chaque prédiction conserve une incertitude.",
        "data_quality_explanation": context.get("data_quality_explanation") or "Les données insuffisantes limitent la force de recommandation.",
        "suggested_action": "Surveiller et ajuster la mise au risque." if recommendation_type in {"recommended", "cautious"} else "Ne pas forcer le pari.",
    }


def analyze_prediction(prediction: dict[str, Any], context: dict[str, Any] | None = None) -> dict[str, Any]:
    context = context or {}
    selection = context.get("selection") or selection_from_prediction(prediction)
    model_probability = probability_for_selection(prediction, selection)
    raw_probability = probability_for_selection({**prediction, "calibrated_probabilities_json": None}, selection)
    odds = _odds_for_prediction(prediction, context.get("odds_lookup"), selection)
    decimal = (odds or {}).get("odds_decimal")
    implied = implied_probability_from_odds(decimal)
    edge = calculate_edge(model_probability, decimal)
    expected_value = calculate_expected_value(model_probability, decimal)
    value_status = classify_value_bet(edge, expected_value, prediction.get("risk_score")) if decimal else "no_odds"
    risk = assess_bet_risk(
        prediction,
        {
            **context,
            "odds": odds,
            "expected_value": expected_value,
            "calibration_status": context.get("calibration_status"),
        },
    )
    recommendation = generate_assistant_recommendation(prediction, {**context, **risk, "value_status": value_status})
    result = {
        "match_id": _match_id(prediction),
        "home_team": prediction.get("home_team"),
        "away_team": prediction.get("away_team"),
        "competition": prediction.get("competition"),
        "market": "1X2",
        "selection": selection,
        "model_probability": raw_probability,
        "calibrated_probability": model_probability if prediction.get("calibration", {}).get("applied") or prediction.get("calibration_version") else None,
        "used_probability": model_probability,
        "odds": decimal,
        "bookmaker": (odds or {}).get("bookmaker"),
        "implied_probability": implied,
        "edge": edge,
        "expected_value": expected_value,
        "value_status": value_status,
        **risk,
        **recommendation,
    }
    text = " ".join(str(value).lower() for value in result.values() if isinstance(value, str))
    result["promise_check"] = "ok" if not any(item in text for item in FORBIDDEN_PROMISES) else "blocked"
    return result


def generate_daily_assistant_brief(predictions: list[dict[str, Any]], context: dict[str, Any] | None = None) -> dict[str, Any]:
    items = [analyze_prediction(item, context) for item in predictions]
    counts = Counter(item["recommendation_type"] for item in items)
    return {
        "status": "ok",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "items_count": len(items),
        "items": items,
        "summary": {
            "recommended_count": counts.get("recommended", 0),
            "cautious_count": counts.get("cautious", 0),
            "avoid_count": counts.get("avoid", 0),
            "no_odds_count": sum(1 for item in items if item["value_status"] == "no_odds"),
            "insufficient_data_count": counts.get("insufficient_data", 0),
        },
    }


def generate_match_assistant_summary(match: dict[str, Any], predictions: list[dict[str, Any]], context: dict[str, Any] | None = None) -> dict[str, Any]:
    match_id = _match_id(match)
    related = [item for item in predictions if _match_id(item) == match_id or str(item.get("slug")) == match_id]
    analyzed = [analyze_prediction(item, context) for item in related]
    primary = analyzed[0] if analyzed else None
    return {
        "status": "ok" if primary else "missing",
        "match_id": match_id,
        "home_team": match.get("home_team"),
        "away_team": match.get("away_team"),
        "summary": (
            f"Assistant FootIQ : {primary['recommendation_reason']}"
            if primary else "Données insuffisantes pour générer une recommandation de pari."
        ),
        "primary_recommendation": primary,
        "markets_to_watch": [item for item in analyzed if item["recommendation_type"] in {"recommended", "cautious"}],
        "markets_to_avoid": [item for item in analyzed if item["recommendation_type"] == "avoid"],
        "missing_data": [] if analyzed else ["prediction"],
    }
