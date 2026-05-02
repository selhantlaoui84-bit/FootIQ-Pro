from __future__ import annotations

import json
from typing import Any

from services.backtesting import calculate_brier_score_1x2, get_match_result


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


def _accuracy(correct: int, total: int) -> int:
    if total <= 0:
        return 0

    return round((correct / total) * 100)


def _average(values: list[float]) -> float | None:
    if not values:
        return None

    return round(sum(values) / len(values), 4)


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
            production_brier = calculate_brier_score_1x2(production_probabilities, actual_result)
    except Exception:
        production_brier = None

    try:
        if shadow_probabilities:
            shadow_brier = calculate_brier_score_1x2(shadow_probabilities, actual_result)
    except Exception:
        shadow_brier = None

    return {
        "match_id": shadow_record.get("match_id") or match.get("match_id") or match.get("id"),
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
            "do_not_activate",
            "Aucune prédiction shadow évaluable pour le moment.",
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

    for record in shadow_records:
        match_id = record.get("match_id")
        match = match_by_id.get(str(match_id))

        if not match:
            continue

        evaluation = evaluate_shadow_prediction(match, record)

        if evaluation:
            evaluations.append(evaluation)

    evaluated_matches = len(evaluations)

    if evaluated_matches == 0:
        return {
            "status": "empty",
            "evaluated_matches": 0,
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
            "activation_recommendation": "do_not_activate",
            "recommendation_reason": "Aucune prédiction shadow évaluable pour le moment.",
            "competition_breakdown": {},
            "recent_evaluations": [],
            "candidate_is_production": False,
            "note": "Le backtesting shadow mesure le modèle ML candidat sans l'activer en production.",
        }

    production_correct_count = sum(1 for item in evaluations if item["production_correct"] is True)
    shadow_correct_count = sum(1 for item in evaluations if item["shadow_correct"] is True)

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

    production_accuracy = _accuracy(production_correct_count, evaluated_matches)
    shadow_accuracy = _accuracy(shadow_correct_count, evaluated_matches)

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

    for item in evaluations:
        competition = item.get("competition") or "Inconnue"

        if competition not in competition_breakdown:
            competition_breakdown[competition] = {
                "evaluated_matches": 0,
                "production_correct": 0,
                "shadow_correct": 0,
                "disagreements": 0,
            }

        bucket = competition_breakdown[competition]
        bucket["evaluated_matches"] += 1

        if item["production_correct"] is True:
            bucket["production_correct"] += 1

        if item["shadow_correct"] is True:
            bucket["shadow_correct"] += 1

        if item["same_pick"] is False:
            bucket["disagreements"] += 1

    for bucket in competition_breakdown.values():
        total = bucket["evaluated_matches"]
        bucket["production_accuracy"] = _accuracy(bucket["production_correct"], total)
        bucket["shadow_accuracy"] = _accuracy(bucket["shadow_correct"], total)

    recent_evaluations = sorted(
        evaluations,
        key=lambda item: str(item.get("kickoff") or ""),
        reverse=True,
    )[:10]

    return {
        "status": "ok",
        "evaluated_matches": evaluated_matches,
        "production_accuracy": production_accuracy,
        "shadow_accuracy": shadow_accuracy,
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
