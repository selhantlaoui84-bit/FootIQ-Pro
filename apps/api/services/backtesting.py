from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from services.prediction_engine import MODEL_VERSION


BUCKETS = [(0, 49), (50, 59), (60, 69), (70, 79), (80, 89), (90, 100)]


def _as_number(value: Any) -> int | None:
    try:
        if value is None:
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_raw_json(raw_json: Any) -> dict | None:
    if isinstance(raw_json, dict):
        return raw_json

    if isinstance(raw_json, str):
        try:
            parsed = json.loads(raw_json)
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None

    return None


def _extract_score(match: dict) -> tuple[int | None, int | None]:
    home = _as_number(match.get("score_full_time_home"))
    away = _as_number(match.get("score_full_time_away"))
    if home is not None and away is not None:
        return home, away

    score = match.get("score") or {}
    full_time = score.get("fullTime") if isinstance(score, dict) else None
    if isinstance(full_time, dict):
        home = _as_number(full_time.get("home"))
        away = _as_number(full_time.get("away"))
        if home is not None and away is not None:
            return home, away

    raw_json = _parse_raw_json(match.get("raw_json"))
    if raw_json is not None:
        nested_home, nested_away = _extract_score(raw_json)
        if nested_home is not None and nested_away is not None:
            return nested_home, nested_away

    home = _as_number(match.get("home_score"))
    away = _as_number(match.get("away_score"))
    if home is not None and away is not None:
        return home, away

    return None, None


def get_match_result(match: dict) -> dict | None:
    if str(match.get("status", "")).upper() != "FINISHED":
        return None

    home_goals, away_goals = _extract_score(match)
    if home_goals is None or away_goals is None:
        return None

    if home_goals > away_goals:
        result = "home"
    elif away_goals > home_goals:
        result = "away"
    else:
        result = "draw"

    return {
        "home_goals": home_goals,
        "away_goals": away_goals,
        "result": result,
        "over_2_5": home_goals + away_goals > 2.5,
        "btts": home_goals > 0 and away_goals > 0,
    }


def _predicted_result(probabilities: dict) -> str:
    values = {
        "home": int(probabilities.get("home", 0) or 0),
        "draw": int(probabilities.get("draw", 0) or 0),
        "away": int(probabilities.get("away", 0) or 0),
    }
    return max(values, key=values.get)


def calculate_brier_score_1x2(probabilities: dict, actual_result: str) -> float:
    score = 0.0
    for outcome in ("home", "draw", "away"):
        probability = float(probabilities.get(outcome, 0) or 0) / 100
        expected = 1.0 if outcome == actual_result else 0.0
        score += (probability - expected) ** 2
    return round(score, 4)


def evaluate_prediction(prediction: dict, match: dict) -> dict | None:
    actual = get_match_result(match)
    if actual is None:
        return None

    probabilities = prediction.get("probabilities") or {}
    goals = prediction.get("goals") or {}
    predicted = _predicted_result(probabilities)
    actual_result = actual["result"]
    over_prediction = goals.get("over_2_5")
    btts_prediction = goals.get("btts")

    return {
        "match_id": prediction.get("match_id") or match.get("match_id") or match.get("id"),
        "model_version": prediction.get("model_version", MODEL_VERSION),
        "actual_result": actual_result,
        "predicted_result": predicted,
        "result_correct": predicted == actual_result,
        "over_2_5_correct": None if over_prediction is None else (over_prediction >= 50) == actual["over_2_5"],
        "btts_correct": None if btts_prediction is None else (btts_prediction >= 50) == actual["btts"],
        "confidence_score": int((prediction.get("confidence") or {}).get("score", 0) or 0),
        "brier_score_1x2": calculate_brier_score_1x2(probabilities, actual_result),
        "probability_assigned_to_actual": int(probabilities.get(actual_result, 0) or 0),
        "competition": prediction.get("competition") or match.get("competition", "Unknown"),
    }


def _percentage(correct: int, total: int) -> int:
    if total <= 0:
        return 0
    return round((correct / total) * 100)


def _average(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 4)


def bucket_by_confidence(evaluations: list[dict]) -> list[dict]:
    buckets = []
    for start, end in BUCKETS:
        items = [item for item in evaluations if start <= int(item.get("confidence_score", 0)) <= end]
        buckets.append(
            {
                "bucket": f"{start}-{end}",
                "count": len(items),
                "accuracy": _percentage(sum(1 for item in items if item.get("result_correct")), len(items)),
                "average_brier_score": _average([float(item.get("brier_score_1x2", 0)) for item in items]),
            }
        )
    return buckets


def _accuracy_for_optional(evaluations: list[dict], key: str) -> int:
    items = [item for item in evaluations if item.get(key) is not None]
    return _percentage(sum(1 for item in items if item.get(key)), len(items))


def _calibration_score(evaluations: list[dict]) -> int:
    if not evaluations:
        return 0

    bucket_errors = []
    for bucket in bucket_by_confidence(evaluations):
        if bucket["count"] <= 0:
            continue
        start, end = [int(part) for part in bucket["bucket"].split("-")]
        expected = (start + end) / 2
        bucket_errors.append(abs(expected - bucket["accuracy"]))

    if not bucket_errors:
        return 0

    return max(0, round(100 - (sum(bucket_errors) / len(bucket_errors))))


def _competition_breakdown(evaluations: list[dict]) -> dict:
    breakdown: dict[str, dict] = {}
    for item in evaluations:
        competition = item.get("competition") or "Unknown"
        entry = breakdown.setdefault(
            competition,
            {"count": 0, "correct": 0, "brier_scores": []},
        )
        entry["count"] += 1
        if item.get("result_correct"):
            entry["correct"] += 1
        entry["brier_scores"].append(float(item.get("brier_score_1x2", 0)))

    return {
        competition: {
            "count": entry["count"],
            "accuracy": _percentage(entry["correct"], entry["count"]),
            "average_brier_score": _average(entry["brier_scores"]),
        }
        for competition, entry in breakdown.items()
    }


def calculate_backtest_report(matches: list[dict], predictions: list[dict]) -> dict:
    predictions_by_id = {
        item.get("match_id") or item.get("id") or item.get("slug"): item
        for item in predictions
        if item.get("match_id") or item.get("id") or item.get("slug")
    }
    evaluations = []

    for match in matches:
        match_id = match.get("match_id") or match.get("id") or match.get("slug")
        prediction = predictions_by_id.get(match_id)
        if prediction is None:
            continue
        evaluation = evaluate_prediction(prediction, match)
        if evaluation is not None:
            evaluations.append(evaluation)

    count = len(evaluations)
    correct = sum(1 for item in evaluations if item.get("result_correct"))
    confidence_values = [int(item.get("confidence_score", 0)) for item in evaluations]
    brier_scores = [float(item.get("brier_score_1x2", 0)) for item in evaluations]

    return {
        "model_version": MODEL_VERSION,
        "previous_model_version": "elo-poisson-v1",
        "comparison_note": "Historical model comparison requires stored prediction snapshots.",
        "calibration_applied": MODEL_VERSION == "elo-poisson-calibrated-v1",
        "evaluated_matches": count,
        "result_accuracy": _percentage(correct, count),
        "over_2_5_accuracy": _accuracy_for_optional(evaluations, "over_2_5_correct"),
        "btts_accuracy": _accuracy_for_optional(evaluations, "btts_correct"),
        "average_brier_score": _average(brier_scores),
        "average_confidence": round(sum(confidence_values) / count) if count else 0,
        "calibration_score": _calibration_score(evaluations),
        "confidence_buckets": bucket_by_confidence(evaluations),
        "competition_breakdown": _competition_breakdown(evaluations),
        "last_backtest_at": datetime.now(timezone.utc).isoformat(),
        "note": "Backtesting is computed on finished matches with available scores.",
    }





def calculate_snapshot_backtest(matches: list[dict], snapshots: list[dict]) -> dict:
    matches_by_id = {
        match.get("match_id") or match.get("id") or match.get("slug"): match
        for match in matches
        if match.get("match_id") or match.get("id") or match.get("slug")
    }
    grouped: dict[str, dict] = {}

    for snapshot in snapshots or []:
        prediction = snapshot.get("prediction")
        if not isinstance(prediction, dict):
            prediction = _parse_raw_json(snapshot.get("prediction_json"))
        if not isinstance(prediction, dict):
            continue

        model_version = snapshot.get("model_version") or prediction.get("model_version") or "unknown"
        entry = grouped.setdefault(
            model_version,
            {"snapshots": 0, "evaluations": []},
        )
        entry["snapshots"] += 1
        match_id = snapshot.get("match_id") or prediction.get("match_id") or prediction.get("id") or prediction.get("slug")
        match = matches_by_id.get(match_id)
        if match is None:
            continue
        evaluation = evaluate_prediction(prediction, match)
        if evaluation is not None:
            entry["evaluations"].append(evaluation)

    model_versions = {}
    for model_version, entry in grouped.items():
        evaluations = entry["evaluations"]
        count = len(evaluations)
        correct = sum(1 for item in evaluations if item.get("result_correct"))
        brier_scores = [float(item.get("brier_score_1x2", 0)) for item in evaluations]
        confidence_values = [int(item.get("confidence_score", 0)) for item in evaluations]
        model_versions[model_version] = {
            "snapshots": entry["snapshots"],
            "evaluated_matches": count,
            "result_accuracy": _percentage(correct, count),
            "average_brier_score": _average(brier_scores),
            "average_confidence": round(sum(confidence_values) / count) if count else 0,
        }

    evaluated_items = {key: value for key, value in model_versions.items() if value["evaluated_matches"] > 0}
    best_model_by_brier = None
    best_model_by_accuracy = None
    if evaluated_items:
        best_model_by_brier = min(evaluated_items, key=lambda key: evaluated_items[key]["average_brier_score"])
        best_model_by_accuracy = max(evaluated_items, key=lambda key: evaluated_items[key]["result_accuracy"])

    return {
        "model_versions": model_versions,
        "best_model_by_brier": best_model_by_brier,
        "best_model_by_accuracy": best_model_by_accuracy,
        "note": "Model comparison is based on stored prediction snapshots.",
    }
