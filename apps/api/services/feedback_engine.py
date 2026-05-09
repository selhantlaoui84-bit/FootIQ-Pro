from __future__ import annotations

import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any

from services.backtesting import get_match_result

OUTCOMES = ("home", "draw", "away")
CONFIDENCE_BUCKETS = ((0, 49), (50, 59), (60, 69), (70, 79), (80, 89), (90, 100))


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _identity(item: dict[str, Any]) -> list[str]:
    values = []
    for key in ("match_id", "id", "slug"):
        value = item.get(key)
        if value is not None and str(value) not in values:
            values.append(str(value))
    return values


def _index_by_identity(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    indexed = {}
    for item in items or []:
        for value in _identity(item):
            indexed[value] = item
    return indexed


def _probabilities(prediction: dict[str, Any]) -> dict[str, float]:
    raw = prediction.get("probabilities") or {}
    values = {}
    for outcome in OUTCOMES:
        try:
            values[outcome] = max(0.0, float(raw.get(outcome, 0) or 0)) / 100.0
        except Exception:
            values[outcome] = 0.0
    total = sum(values.values())
    if total <= 0:
        return {"home": 1 / 3, "draw": 1 / 3, "away": 1 / 3}
    return {key: value / total for key, value in values.items()}


def _pick(probabilities: dict[str, float]) -> str:
    return max(probabilities, key=probabilities.get)


def _confidence(prediction: dict[str, Any], probabilities: dict[str, float]) -> int:
    confidence = prediction.get("confidence") or {}
    try:
        return max(0, min(100, int(confidence.get("score"))))
    except Exception:
        return round(max(probabilities.values()) * 100)


def _market_rows(prediction: dict[str, Any], actual: dict[str, Any]) -> list[dict[str, Any]]:
    probabilities = _probabilities(prediction)
    goals = prediction.get("goals") or {}
    rows = [
        {
            "market": "1x2",
            "predicted": _pick(probabilities),
            "actual": actual["result"],
            "correct": _pick(probabilities) == actual["result"],
            "probability": probabilities.get(_pick(probabilities), 0.0),
        }
    ]
    for market, actual_key in (("over_2_5", "over_2_5"), ("btts", "btts")):
        if goals.get(market) is None:
            continue
        probability = max(0.0, min(1.0, float(goals.get(market) or 0) / 100.0))
        predicted = probability >= 0.5
        rows.append(
            {
                "market": market,
                "predicted": predicted,
                "actual": bool(actual[actual_key]),
                "correct": predicted == bool(actual[actual_key]),
                "probability": probability,
            }
        )
    return rows


def _brier(probabilities: dict[str, float], actual_result: str) -> float:
    return sum((probabilities[outcome] - (1.0 if outcome == actual_result else 0.0)) ** 2 for outcome in OUTCOMES)


def _log_loss(probabilities: dict[str, float], actual_result: str) -> float:
    probability = max(1e-15, min(1 - 1e-15, probabilities.get(actual_result, 0.0)))
    return -math.log(probability)


def _roi(probability: float, correct: bool) -> float:
    if probability <= 0:
        return -1.0
    decimal_odds = 1 / probability
    return decimal_odds - 1 if correct else -1.0


def _average(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 4)


def _pct(correct: int, total: int) -> int:
    return round((correct / total) * 100) if total else 0


def _bucket_for_confidence(confidence: int) -> str:
    for start, end in CONFIDENCE_BUCKETS:
        if start <= confidence <= end:
            return f"{start}-{end}"
    return "unknown"


def _summarize_group(items: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(items)
    correct = sum(1 for item in items if item["correct"])
    return {
        "count": total,
        "accuracy": _pct(correct, total),
        "log_loss": _average([item["log_loss"] for item in items if item.get("log_loss") is not None]),
        "brier_score": _average([item["brier_score"] for item in items if item.get("brier_score") is not None]),
        "theoretical_roi": _average([item["roi"] for item in items if item.get("roi") is not None]),
    }


def build_feedback_report(
    matches: list[dict[str, Any]],
    predictions: list[dict[str, Any]],
    model_version: str | None = None,
) -> dict[str, Any]:
    predictions_by_id = _index_by_identity(predictions)
    evaluations: list[dict[str, Any]] = []
    market_evaluations: list[dict[str, Any]] = []
    error_counter: Counter[str] = Counter()

    for match in matches or []:
        prediction = None
        for value in _identity(match):
            prediction = predictions_by_id.get(value)
            if prediction:
                break
        if prediction is None:
            continue
        if model_version and prediction.get("model_version") != model_version:
            continue

        actual = get_match_result(match)
        if actual is None:
            continue

        probabilities = _probabilities(prediction)
        predicted_result = _pick(probabilities)
        correct = predicted_result == actual["result"]
        confidence = _confidence(prediction, probabilities)
        brier = _brier(probabilities, actual["result"])
        loss = _log_loss(probabilities, actual["result"])
        roi = _roi(probabilities[predicted_result], correct)
        competition = prediction.get("competition") or match.get("competition") or "Unknown"

        row = {
            "match_id": prediction.get("match_id") or match.get("match_id") or match.get("id"),
            "model_version": prediction.get("model_version"),
            "competition": competition,
            "confidence": confidence,
            "confidence_bucket": _bucket_for_confidence(confidence),
            "predicted_result": predicted_result,
            "actual_result": actual["result"],
            "correct": correct,
            "log_loss": loss,
            "brier_score": brier,
            "roi": roi,
        }
        evaluations.append(row)

        if not correct:
            error_counter[f"{predicted_result}_predicted_{actual['result']}_actual"] += 1

        for market_row in _market_rows(prediction, actual):
            market_evaluations.append(
                {
                    **market_row,
                    "competition": competition,
                    "confidence_bucket": row["confidence_bucket"],
                    "log_loss": loss if market_row["market"] == "1x2" else None,
                    "brier_score": brier if market_row["market"] == "1x2" else None,
                    "roi": _roi(market_row["probability"], market_row["correct"]),
                }
            )

    by_market = defaultdict(list)
    by_competition = defaultdict(list)
    by_confidence = defaultdict(list)
    for item in market_evaluations:
        by_market[item["market"]].append(item)
        by_competition[item["competition"]].append(item)
        by_confidence[item["confidence_bucket"]].append(item)

    summary = _summarize_group(evaluations)
    return {
        "status": "ok" if evaluations else "empty",
        "generated_at": _now_iso(),
        "model_version": model_version or "all",
        "evaluated_matches": len(evaluations),
        "accuracy": summary["accuracy"],
        "log_loss": summary["log_loss"],
        "brier_score": summary["brier_score"],
        "theoretical_roi": summary["theoretical_roi"],
        "performance_by_market": {key: _summarize_group(value) for key, value in sorted(by_market.items())},
        "performance_by_competition": {key: _summarize_group(value) for key, value in sorted(by_competition.items())},
        "performance_by_confidence": {key: _summarize_group(value) for key, value in sorted(by_confidence.items())},
        "frequent_errors": [
            {"error": key, "count": count}
            for key, count in error_counter.most_common(10)
        ],
        "recent_evaluations": evaluations[:25],
        "note": "Feedback report compares stored predictions with finished match results.",
    }
