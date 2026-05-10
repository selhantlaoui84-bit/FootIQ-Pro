from __future__ import annotations

import json
import math
from typing import Any

from services.backtesting import calculate_brier_score_1x2, get_match_result

MINIMUM_EVALUABLE_PREDICTIONS = 30
OUTCOMES = ("home", "draw", "away")


def _safe_json(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value

    if not value:
        return {}

    try:
        return json.loads(value)
    except Exception:
        return {}


def _pick_from_probabilities(probabilities: dict[str, Any] | None) -> str | None:
    if not probabilities:
        return None

    valid_keys = ["home", "draw", "away"]
    clean = {}

    for key in valid_keys:
        try:
            clean[key] = float(probabilities.get(key, 0))
        except Exception:
            clean[key] = 0

    if not clean:
        return None

    return max(clean, key=clean.get)


def _probabilities(prediction: dict[str, Any]) -> dict[str, float]:
    raw = prediction.get("probabilities") or prediction.get("probabilities_json") or {}
    if not isinstance(raw, dict):
        return {}

    clean: dict[str, float] = {}
    for outcome in OUTCOMES:
        try:
            value = float(raw.get(outcome, 0) or 0)
        except (TypeError, ValueError):
            value = 0.0
        if value > 1:
            value = value / 100
        clean[outcome] = max(0.0, min(1.0, value))

    total = sum(clean.values())
    if total <= 0:
        return {}
    return {key: value / total for key, value in clean.items()}


def _probability_percent(probabilities: dict[str, Any]) -> dict[str, float]:
    normalized = _probabilities({"probabilities": probabilities})
    return {key: value * 100 for key, value in normalized.items()}


def _log_loss(probabilities: dict[str, Any], actual_result: str) -> float | None:
    normalized = _probabilities({"probabilities": probabilities})
    if actual_result not in normalized:
        return None
    probability = max(1e-15, min(1 - 1e-15, normalized.get(actual_result, 0)))
    return round(-math.log(probability), 4)


def _confidence_value(value: Any) -> float | None:
    if isinstance(value, dict):
        value = value.get("score") or value.get("value")
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _confidence_bucket(confidence: float | None) -> str:
    if confidence is None:
        return "unknown"
    lower = int(confidence // 10) * 10
    upper = min(100, lower + 9)
    if confidence >= 100:
        return "100"
    return f"{lower}-{upper}"


def _odds_for_pick(prediction: dict[str, Any], pick: str | None) -> float | None:
    if not pick:
        return None
    raw_odds = prediction.get("odds") or prediction.get("odds_json") or prediction.get("market_odds") or {}
    if not isinstance(raw_odds, dict):
        return None
    aliases = {
        "home": ("home", "1", "home_win"),
        "draw": ("draw", "x"),
        "away": ("away", "2", "away_win"),
    }
    for key in aliases.get(pick, (pick,)):
        try:
            value = raw_odds.get(key)
            if value is not None:
                odds = float(value)
                return odds if odds > 1 else None
        except (TypeError, ValueError):
            continue
    return None


def _profit_for_pick(prediction: dict[str, Any], pick: str | None, correct: bool | None) -> float | None:
    odds = _odds_for_pick(prediction, pick)
    if odds is None or correct is None:
        return None
    return round(odds - 1, 4) if correct else -1.0


def _market_from(record: dict[str, Any], shadow_prediction: dict[str, Any], production_prediction: dict[str, Any]) -> str:
    return str(
        record.get("market")
        or shadow_prediction.get("market")
        or production_prediction.get("market")
        or "1x2"
    )


def _accuracy(correct: int, total: int) -> int:
    if total <= 0:
        return 0

    return round((correct / total) * 100)


def _accuracy_or_none(correct: int, total: int) -> int | None:
    if total <= 0:
        return None
    return _accuracy(correct, total)


def _average(values: list[float]) -> float | None:
    if not values:
        return None

    return round(sum(values) / len(values), 4)


def _roi(profits: list[float]) -> float | None:
    if not profits:
        return None
    return round(sum(profits) / len(profits), 4)


def _round_delta(value: float | None) -> float | None:
    return None if value is None else round(value, 4)


def evaluate_shadow_prediction(match: dict[str, Any], shadow_record: dict[str, Any]) -> dict[str, Any] | None:
    result = get_match_result(match)

    if not result:
        return None

    actual_result = result["result"]

    production_prediction = _safe_json(
        shadow_record.get("production_prediction_json")
        or shadow_record.get("production_prediction")
    )
    shadow_prediction = _safe_json(
        shadow_record.get("shadow_prediction_json")
        or shadow_record.get("shadow_prediction")
    )
    comparison = _safe_json(
        shadow_record.get("comparison_json")
        or shadow_record.get("comparison")
    )

    production_probabilities = production_prediction.get("probabilities") or {}
    shadow_probabilities = shadow_prediction.get("probabilities") or {}

    production_pick = comparison.get("production_pick") or _pick_from_probabilities(production_probabilities)
    shadow_pick = comparison.get("shadow_pick") or shadow_prediction.get("predicted_result") or _pick_from_probabilities(shadow_probabilities)

    production_correct = production_pick == actual_result if production_pick else None
    shadow_correct = shadow_pick == actual_result if shadow_pick else None

    same_pick = None
    if production_pick and shadow_pick:
        same_pick = production_pick == shadow_pick

    winner = "unknown"

    if production_correct is True and shadow_correct is True:
        winner = "both"
    elif production_correct is True and shadow_correct is False:
        winner = "production"
    elif production_correct is False and shadow_correct is True:
        winner = "shadow"
    elif production_correct is False and shadow_correct is False:
        winner = "none"

    production_brier = None
    shadow_brier = None

    try:
        if production_probabilities:
            production_brier = calculate_brier_score_1x2(_probability_percent(production_probabilities), actual_result)
    except Exception:
        production_brier = None

    try:
        if shadow_probabilities:
            shadow_brier = calculate_brier_score_1x2(_probability_percent(shadow_probabilities), actual_result)
    except Exception:
        shadow_brier = None

    production_log_loss = _log_loss(production_probabilities, actual_result)
    shadow_log_loss = _log_loss(shadow_probabilities, actual_result)
    production_profit = _profit_for_pick(production_prediction, production_pick, production_correct)
    shadow_profit = _profit_for_pick(shadow_prediction, shadow_pick, shadow_correct)
    shadow_confidence = _confidence_value(shadow_prediction.get("confidence"))
    production_confidence = _confidence_value(production_prediction.get("confidence"))
    market = _market_from(shadow_record, shadow_prediction, production_prediction)

    return {
        "match_id": shadow_record.get("match_id") or match.get("match_id") or match.get("id"),
        "model_version": shadow_prediction.get("model_version") or shadow_record.get("candidate_model_version"),
        "production_model_version": production_prediction.get("model_version") or shadow_record.get("production_model_version"),
        "actual_result": actual_result,
        "production_pick": production_pick,
        "shadow_pick": shadow_pick,
        "production_correct": production_correct,
        "shadow_correct": shadow_correct,
        "same_pick": same_pick,
        "winner": winner,
        "disagreement_level": comparison.get("disagreement_level", "unknown"),
        "production_brier_score": production_brier,
        "shadow_brier_score": shadow_brier,
        "production_log_loss": production_log_loss,
        "shadow_log_loss": shadow_log_loss,
        "production_profit": production_profit,
        "shadow_profit": shadow_profit,
        "market": market,
        "confidence": shadow_confidence,
        "production_confidence": production_confidence,
        "confidence_bucket": _confidence_bucket(shadow_confidence),
        "competition": match.get("competition", "Inconnue"),
        "home_team": match.get("home_team"),
        "away_team": match.get("away_team"),
        "kickoff": match.get("kickoff"),
    }


def _activation_recommendation(
    evaluated_matches: int,
    production_accuracy: int,
    shadow_accuracy: int,
    production_average_brier: float | None,
    shadow_average_brier: float | None,
    shadow_wins_on_disagreement: int,
    production_wins_on_disagreement: int,
) -> tuple[int, str, str]:
    if evaluated_matches == 0:
        return (
            0,
            "collect_more_data",
            "Pas assez de prédictions shadow évaluables.",
        )

    accuracy_delta = shadow_accuracy - production_accuracy

    brier_ok = False
    if production_average_brier is not None and shadow_average_brier is not None:
        brier_ok = shadow_average_brier <= production_average_brier

    disagreement_edge = shadow_wins_on_disagreement - production_wins_on_disagreement

    activation_score = 50 + accuracy_delta

    if brier_ok:
        activation_score += 10
    else:
        activation_score -= 10

    activation_score += max(-15, min(15, disagreement_edge * 2))
    activation_score = max(0, min(100, round(activation_score)))

    if evaluated_matches < 50:
        return (
            activation_score,
            "keep_shadow",
            "Échantillon encore trop faible. Le candidat ML doit rester en observation.",
        )

    if (
        evaluated_matches >= 100
        and shadow_accuracy >= production_accuracy + 3
        and brier_ok
    ):
        return (
            activation_score,
            "candidate_ready_for_limited_rollout",
            "Le candidat ML bat le modèle officiel sur l'échantillon évalué avec un Brier score compétitif. Un test limité peut être envisagé.",
        )

    if accuracy_delta >= -1 and brier_ok:
        return (
            activation_score,
            "consider_hybrid",
            "Le candidat ML est proche du modèle officiel. Un mode hybride peut être étudié, sans activation complète.",
        )

    if disagreement_edge > 0:
        return (
            activation_score,
            "consider_hybrid",
            "Le candidat ML gagne davantage de désaccords que le modèle officiel, mais le signal reste à confirmer.",
        )

    return (
        activation_score,
        "keep_shadow",
        "Le modèle ML candidat ne justifie pas encore une activation. Il doit rester en mode shadow.",
    )


def calculate_shadow_backtest_report(
    matches: list[dict[str, Any]],
    shadow_records: list[dict[str, Any]],
) -> dict[str, Any]:
    match_by_id: dict[str, dict[str, Any]] = {}

    for match in matches:
        for key in [
            match.get("match_id"),
            match.get("id"),
            match.get("slug"),
        ]:
            if key:
                match_by_id[str(key)] = match

    evaluations = []
    pending_matches = []
    invalid_matches = []
    candidate_versions = []
    production_versions = []

    for record in shadow_records:
        match_id = record.get("match_id")
        shadow_prediction = _safe_json(record.get("shadow_prediction_json") or record.get("shadow_prediction"))
        production_prediction = _safe_json(record.get("production_prediction_json") or record.get("production_prediction"))
        candidate_version = shadow_prediction.get("model_version") or record.get("candidate_model_version")
        production_version = production_prediction.get("model_version") or record.get("production_model_version")
        if candidate_version:
            candidate_versions.append(str(candidate_version))
        if production_version:
            production_versions.append(str(production_version))
        match = match_by_id.get(str(match_id))

        if not match:
            invalid_matches.append({
                "match_id": match_id,
                "model_version": candidate_version,
                "reason": "match_not_found",
            })
            continue

        evaluation = evaluate_shadow_prediction(match, record)

        if evaluation and evaluation.get("shadow_pick"):
            evaluations.append(evaluation)
        elif get_match_result(match):
            invalid_matches.append({
                "match_id": match_id,
                "model_version": candidate_version,
                "home_team": match.get("home_team"),
                "away_team": match.get("away_team"),
                "competition": match.get("competition"),
                "kickoff": match.get("kickoff"),
                "reason": "missing_shadow_selection",
            })
        else:
            pending_matches.append({
                "match_id": match_id,
                "model_version": candidate_version,
                "home_team": match.get("home_team"),
                "away_team": match.get("away_team"),
                "competition": match.get("competition"),
                "kickoff": match.get("kickoff"),
                "reason": "result_pending",
            })

    evaluated_matches = len(evaluations)
    shadow_predictions_total = len(shadow_records or [])
    pending_predictions = len(pending_matches)
    invalid_predictions = len(invalid_matches)
    candidate_model_version = candidate_versions[0] if candidate_versions else None
    production_model_version = production_versions[0] if production_versions else None

    if evaluated_matches == 0:
        return {
            "status": "ok",
            "storage": "postgresql",
            "backtesting_status": "pending" if shadow_predictions_total else "empty",
            "candidate_model_version": candidate_model_version,
            "production_model_version": production_model_version,
            "shadow_predictions_total": shadow_predictions_total,
            "evaluable_predictions": 0,
            "pending_predictions": pending_predictions,
            "invalid_predictions": invalid_predictions,
            "metrics": {
                "accuracy": None,
                "log_loss": None,
                "brier_score": None,
                "roi_theoretical": None,
                "profit_theoretical": None,
                "average_confidence": None,
                "calibration_gap": None,
            },
            "production_metrics": {
                "accuracy": None,
                "log_loss": None,
                "brier_score": None,
                "roi_theoretical": None,
            },
            "comparison": {
                "candidate_vs_production": "insufficient_data",
                "comparison_status": "insufficient_data" if shadow_predictions_total else "no_shadow_predictions",
                "delta_accuracy": None,
                "delta_log_loss": None,
                "delta_brier_score": None,
                "delta_roi": None,
                "candidate_better_than_production": None,
            },
            "by_market": [],
            "by_competition": [],
            "by_confidence": [],
            "evaluated_matches": 0,
            "evaluated_match_rows": [],
            "pending_matches": pending_matches[:20],
            "invalid_matches": invalid_matches[:20],
            "recommendation": {
                "status": "collect_more_data",
                "reason": "Pas assez de prédictions shadow évaluables.",
                "minimum_required": MINIMUM_EVALUABLE_PREDICTIONS,
                "current": 0,
            },
            "production_accuracy": 0,
            "shadow_accuracy": 0,
            "production_average_brier": None,
            "shadow_average_brier": None,
            "same_pick_count": 0,
            "disagreement_count": 0,
            "high_disagreement_count": 0,
            "shadow_wins_on_disagreement": 0,
            "production_wins_on_disagreement": 0,
            "both_wrong_on_disagreement": 0,
            "activation_score": 0,
            "activation_recommendation": "collect_more_data",
            "recommendation_reason": "Pas assez de prédictions shadow évaluables.",
            "competition_breakdown": {},
            "recent_evaluations": [],
            "candidate_is_production": False,
            "note": "Le backtesting shadow mesure le modèle ML candidat sans l'activer en production.",
        }

    production_correct_count = sum(1 for item in evaluations if item["production_correct"] is True)
    shadow_correct_count = sum(1 for item in evaluations if item["shadow_correct"] is True)
    production_evaluable_count = sum(1 for item in evaluations if item.get("production_correct") is not None)

    same_pick_count = sum(1 for item in evaluations if item["same_pick"] is True)
    disagreement_items = [item for item in evaluations if item["same_pick"] is False]
    disagreement_count = len(disagreement_items)

    high_disagreement_count = sum(
        1 for item in disagreement_items if item.get("disagreement_level") == "high"
    )

    shadow_wins_on_disagreement = sum(
        1 for item in disagreement_items if item["winner"] == "shadow"
    )
    production_wins_on_disagreement = sum(
        1 for item in disagreement_items if item["winner"] == "production"
    )
    both_wrong_on_disagreement = sum(
        1 for item in disagreement_items if item["winner"] == "none"
    )

    production_briers = [
        item["production_brier_score"]
        for item in evaluations
        if item.get("production_brier_score") is not None
    ]
    shadow_briers = [
        item["shadow_brier_score"]
        for item in evaluations
        if item.get("shadow_brier_score") is not None
    ]

    production_average_brier = _average(production_briers)
    shadow_average_brier = _average(shadow_briers)
    production_log_losses = [item["production_log_loss"] for item in evaluations if item.get("production_log_loss") is not None]
    shadow_log_losses = [item["shadow_log_loss"] for item in evaluations if item.get("shadow_log_loss") is not None]
    production_profits = [item["production_profit"] for item in evaluations if item.get("production_profit") is not None]
    shadow_profits = [item["shadow_profit"] for item in evaluations if item.get("shadow_profit") is not None]
    shadow_confidences = [item["confidence"] for item in evaluations if item.get("confidence") is not None]

    production_average_log_loss = _average(production_log_losses)
    shadow_average_log_loss = _average(shadow_log_losses)
    production_roi = _roi(production_profits)
    shadow_roi = _roi(shadow_profits)
    shadow_profit_total = round(sum(shadow_profits), 4) if shadow_profits else None
    average_confidence = _average(shadow_confidences)

    production_accuracy = _accuracy(production_correct_count, production_evaluable_count)
    production_accuracy_metric = _accuracy_or_none(production_correct_count, production_evaluable_count)
    shadow_accuracy = _accuracy(shadow_correct_count, evaluated_matches)
    calibration_gap = None
    if average_confidence is not None:
        calibration_gap = round((average_confidence / 100) - (shadow_accuracy / 100), 4)

    activation_score, recommendation, reason = _activation_recommendation(
        evaluated_matches=evaluated_matches,
        production_accuracy=production_accuracy,
        shadow_accuracy=shadow_accuracy,
        production_average_brier=production_average_brier,
        shadow_average_brier=shadow_average_brier,
        shadow_wins_on_disagreement=shadow_wins_on_disagreement,
        production_wins_on_disagreement=production_wins_on_disagreement,
    )

    competition_breakdown: dict[str, dict[str, Any]] = {}
    market_breakdown: dict[str, dict[str, Any]] = {}
    confidence_breakdown: dict[str, dict[str, Any]] = {}

    def ensure_bucket(store: dict[str, dict[str, Any]], key: str) -> dict[str, Any]:
        if key not in store:
            store[key] = {
                "count": 0,
                "evaluated_matches": 0,
                "production_evaluable": 0,
                "production_correct": 0,
                "shadow_correct": 0,
                "disagreements": 0,
                "shadow_log_losses": [],
                "shadow_briers": [],
                "shadow_profits": [],
            }
        return store[key]

    for item in evaluations:
        for store, key_name in [
            (competition_breakdown, item.get("competition") or "Inconnue"),
            (market_breakdown, item.get("market") or "1x2"),
            (confidence_breakdown, item.get("confidence_bucket") or "unknown"),
        ]:
            bucket = ensure_bucket(store, str(key_name))
            bucket["count"] += 1
            bucket["evaluated_matches"] += 1
            if item.get("production_correct") is not None:
                bucket["production_evaluable"] += 1

            if item["production_correct"] is True:
                bucket["production_correct"] += 1

            if item["shadow_correct"] is True:
                bucket["shadow_correct"] += 1

            if item["same_pick"] is False:
                bucket["disagreements"] += 1

            if item.get("shadow_log_loss") is not None:
                bucket["shadow_log_losses"].append(item["shadow_log_loss"])
            if item.get("shadow_brier_score") is not None:
                bucket["shadow_briers"].append(item["shadow_brier_score"])
            if item.get("shadow_profit") is not None:
                bucket["shadow_profits"].append(item["shadow_profit"])

    def finalize_group(store: dict[str, dict[str, Any]], label: str) -> list[dict[str, Any]]:
        rows = []
        for key, bucket in store.items():
            total = bucket["evaluated_matches"]
            production_total = bucket["production_evaluable"]
            row = {
                label: key,
                "count": bucket["count"],
                "evaluable_count": total,
                "evaluated_matches": total,
                "accuracy": _accuracy(bucket["shadow_correct"], total) if total else None,
                "production_accuracy": _accuracy_or_none(bucket["production_correct"], production_total),
                "shadow_accuracy": _accuracy(bucket["shadow_correct"], total),
                "disagreements": bucket["disagreements"],
                "log_loss": _average(bucket.pop("shadow_log_losses")),
                "brier_score": _average(bucket.pop("shadow_briers")),
                "roi_theoretical": _roi(bucket.pop("shadow_profits")),
                "status": "ok" if total else "insufficient_data",
            }
            bucket.update(row)
            rows.append(row)
        return sorted(rows, key=lambda item: item["evaluated_matches"], reverse=True)

    by_competition = finalize_group(competition_breakdown, "competition")
    by_market = finalize_group(market_breakdown, "market")
    by_confidence = finalize_group(confidence_breakdown, "confidence_bucket")

    recent_evaluations = sorted(
        evaluations,
        key=lambda item: str(item.get("kickoff") or ""),
        reverse=True,
    )[:10]

    delta_accuracy = None if production_accuracy_metric is None else shadow_accuracy - production_accuracy_metric
    delta_log_loss = (
        None if shadow_average_log_loss is None or production_average_log_loss is None
        else round(shadow_average_log_loss - production_average_log_loss, 4)
    )
    delta_brier = (
        None if shadow_average_brier is None or production_average_brier is None
        else round(shadow_average_brier - production_average_brier, 4)
    )
    delta_roi = (
        None if shadow_roi is None or production_roi is None
        else round(shadow_roi - production_roi, 4)
    )

    if production_accuracy_metric is None:
        comparison_status = "no_production_reference"
        candidate_better_than_production = None
    elif evaluated_matches < MINIMUM_EVALUABLE_PREDICTIONS:
        comparison_status = "insufficient_data"
        candidate_better_than_production = None
    elif delta_accuracy is not None and delta_accuracy > 1 and (delta_log_loss is None or delta_log_loss <= 0) and (delta_brier is None or delta_brier <= 0):
        comparison_status = "candidate_better"
        candidate_better_than_production = True
    elif delta_accuracy is not None and delta_accuracy < -1:
        comparison_status = "candidate_worse"
        candidate_better_than_production = False
    else:
        comparison_status = "candidate_equivalent"
        candidate_better_than_production = None

    if evaluated_matches < MINIMUM_EVALUABLE_PREDICTIONS:
        governance_status = "collect_more_data"
        governance_reason = "Pas assez de prédictions shadow évaluables."
    elif production_accuracy_metric is None:
        governance_status = "candidate_promising"
        governance_reason = "Référence production non disponible sur les mêmes matchs, revue manuelle requise après plus de shadow testing."
    elif delta_accuracy is not None and delta_accuracy >= 0 and (delta_log_loss is None or delta_log_loss <= 0) and (delta_brier is None or delta_brier <= 0):
        governance_status = "promotion_ready_manual_review" if shadow_roi is None or shadow_roi >= 0 else "candidate_promising"
        governance_reason = "Le candidat est compétitif, revue manuelle requise avant toute promotion."
    elif (delta_accuracy is not None and delta_accuracy >= 0) or (delta_log_loss is not None and delta_log_loss <= 0):
        governance_status = "candidate_promising"
        governance_reason = "Le candidat montre un signal positif mais pas assez complet pour une promotion."
    else:
        governance_status = "blocked_worse_than_production"
        governance_reason = "Le candidat ne bat pas la production sur les métriques shadow disponibles."

    return {
        "status": "ok",
        "storage": "postgresql",
        "backtesting_status": "evaluated",
        "candidate_model_version": candidate_model_version,
        "production_model_version": production_model_version,
        "shadow_predictions_total": shadow_predictions_total,
        "evaluable_predictions": evaluated_matches,
        "pending_predictions": pending_predictions,
        "invalid_predictions": invalid_predictions,
        "metrics": {
            "accuracy": shadow_accuracy,
            "log_loss": shadow_average_log_loss,
            "brier_score": shadow_average_brier,
            "roi_theoretical": shadow_roi,
            "profit_theoretical": shadow_profit_total,
            "average_confidence": average_confidence,
            "calibration_gap": calibration_gap,
        },
        "production_metrics": {
            "accuracy": production_accuracy_metric,
            "log_loss": production_average_log_loss,
            "brier_score": production_average_brier,
            "roi_theoretical": production_roi,
        },
        "comparison": {
            "candidate_vs_production": governance_status,
            "comparison_status": comparison_status,
            "delta_accuracy": delta_accuracy,
            "delta_log_loss": delta_log_loss,
            "delta_brier_score": delta_brier,
            "delta_roi": delta_roi,
            "candidate_better_than_production": candidate_better_than_production,
            "production_accuracy": production_accuracy,
            "production_log_loss": production_average_log_loss,
            "production_brier_score": production_average_brier,
            "production_roi": production_roi,
        },
        "by_market": by_market,
        "by_competition": by_competition,
        "by_confidence": by_confidence,
        "evaluated_matches": evaluated_matches,
        "evaluated_match_rows": recent_evaluations,
        "pending_matches": pending_matches[:20],
        "invalid_matches": invalid_matches[:20],
        "recommendation": {
            "status": governance_status,
            "reason": governance_reason,
            "minimum_required": MINIMUM_EVALUABLE_PREDICTIONS,
            "current": evaluated_matches,
        },
        "evaluated_count": evaluated_matches,
        "production_accuracy": production_accuracy,
        "shadow_accuracy": shadow_accuracy,
        "production_average_log_loss": production_average_log_loss,
        "shadow_average_log_loss": shadow_average_log_loss,
        "production_average_brier": production_average_brier,
        "shadow_average_brier": shadow_average_brier,
        "same_pick_count": same_pick_count,
        "disagreement_count": disagreement_count,
        "high_disagreement_count": high_disagreement_count,
        "shadow_wins_on_disagreement": shadow_wins_on_disagreement,
        "production_wins_on_disagreement": production_wins_on_disagreement,
        "both_wrong_on_disagreement": both_wrong_on_disagreement,
        "activation_score": activation_score,
        "activation_recommendation": recommendation,
        "recommendation_reason": reason,
        "competition_breakdown": competition_breakdown,
        "recent_evaluations": recent_evaluations,
        "candidate_is_production": False,
        "note": "Le backtesting shadow mesure le modèle ML candidat sans l'activer en production.",
    }
