from __future__ import annotations

import math
import re
from datetime import datetime, timezone
from typing import Any

from services.calibration import normalize_probabilities
from services.feedback_engine import build_feedback_report
from services.backtesting import get_match_result

CALIBRATION_VERSION = "calibration-buckets-v1"
MINIMUM_CALIBRATION_SAMPLES = 30
MINIMUM_BUCKET_SAMPLES = 10
BUCKETS = tuple((start, start + 10) for start in range(0, 100, 10))
OUTCOMES = ("home", "draw", "away")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _bucket_label(value: int) -> str:
    for start, end in BUCKETS:
        if start <= value < end or (end == 100 and value <= 100):
            return f"{start}-{end}%"
    return "unknown"


def _favorite_probability(probabilities: dict[str, Any]) -> int:
    normalized = normalize_probabilities(probabilities)
    return int(max(normalized.values()))


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
        if not isinstance(item, dict):
            continue
        for value in _identity(item):
            indexed[value] = item
    return indexed


def _probabilities_01(prediction: dict[str, Any]) -> dict[str, float]:
    normalized = normalize_probabilities(prediction.get("probabilities") or {})
    return {key: max(0.0, min(1.0, float(normalized.get(key, 0) or 0) / 100.0)) for key in OUTCOMES}


def _pick(probabilities: dict[str, float]) -> str:
    return max(OUTCOMES, key=lambda key: probabilities.get(key, 0.0))


def _prediction_evaluations(
    matches: list[dict[str, Any]],
    predictions: list[dict[str, Any]],
    model_version: str | None = None,
) -> list[dict[str, Any]]:
    predictions_by_id = _index_by_identity(predictions)
    rows: list[dict[str, Any]] = []
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
        probabilities = _probabilities_01(prediction)
        predicted = _pick(probabilities)
        confidence = probabilities[predicted]
        correct = predicted == actual["result"]
        rows.append(
            {
                "match_id": prediction.get("match_id") or match.get("match_id") or match.get("id"),
                "model_version": prediction.get("model_version"),
                "predicted": predicted,
                "actual": actual["result"],
                "confidence": confidence,
                "correct": correct,
                "probabilities": probabilities,
            }
        )
    return rows


def _bucket_status(count: int, gap: float | None) -> str:
    if count < MINIMUM_BUCKET_SAMPLES or gap is None:
        return "insufficient_data"
    if gap <= -0.08:
        return "overconfident"
    if gap >= 0.08:
        return "underconfident"
    return "well_calibrated"


def _average(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 4)


def build_confidence_buckets(predictions: list[dict[str, Any]], bucket_size: int = 10) -> list[dict[str, Any]]:
    safe_size = max(5, min(int(bucket_size or 10), 25))
    bucket_ranges = tuple((start, min(start + safe_size, 100)) for start in range(0, 100, safe_size))
    buckets: list[dict[str, Any]] = []
    for start, end in bucket_ranges:
        items = []
        for item in predictions or []:
            confidence = float(item.get("confidence") or 0)
            if start / 100 <= confidence < end / 100 or (end == 100 and start / 100 <= confidence <= 1):
                items.append(item)
        count = len(items)
        wins = sum(1 for item in items if item.get("correct") is True)
        losses = sum(1 for item in items if item.get("correct") is False)
        predicted_avg = _average([float(item.get("confidence") or 0) for item in items])
        actual_rate = round(wins / count, 4) if count >= MINIMUM_BUCKET_SAMPLES else None
        gap = round(actual_rate - predicted_avg, 4) if actual_rate is not None and predicted_avg is not None else None
        midpoint = round(((start + end) / 2) / 100, 3)
        status = _bucket_status(count, gap)
        buckets.append(
            {
                "bucket_label": f"{start}-{end}%",
                "bucket": f"{start}-{end}",
                "min_confidence": round(start / 100, 2),
                "max_confidence": round(end / 100, 2),
                "predictions_count": count,
                "count": count,
                "wins_count": wins,
                "losses_count": losses,
                "predicted_confidence_avg": predicted_avg if predicted_avg is not None else midpoint,
                "predicted_probability": predicted_avg if predicted_avg is not None else midpoint,
                "actual_success_rate": actual_rate,
                "observed_success_rate": actual_rate,
                "calibration_gap": gap,
                "calibration_factor": 1.0 if gap is None else round(max(0.7, min(1.3, 1 + gap)), 3),
                "status": status,
            }
        )
    return buckets


def build_global_calibration_metrics(buckets: list[dict[str, Any]], samples_count: int) -> dict[str, Any]:
    usable = [bucket for bucket in buckets if bucket.get("calibration_gap") is not None and bucket.get("predictions_count", 0) > 0]
    if samples_count < MINIMUM_CALIBRATION_SAMPLES:
        return {
            "samples_count": samples_count,
            "expected_calibration_error": None,
            "mean_absolute_calibration_error": None,
            "max_calibration_gap": None,
            "overconfidence_score": None,
            "underconfidence_score": None,
            "reliability_score": None,
            "calibration_status": "insufficient_data",
        }
    total_weight = sum(int(bucket.get("predictions_count") or 0) for bucket in usable) or 1
    gaps = [float(bucket.get("calibration_gap") or 0) for bucket in usable]
    expected_error = sum(abs(float(bucket.get("calibration_gap") or 0)) * int(bucket.get("predictions_count") or 0) for bucket in usable) / total_weight
    mean_abs = sum(abs(gap) for gap in gaps) / max(1, len(gaps))
    max_gap = max((abs(gap) for gap in gaps), default=0.0)
    overconfidence = sum(abs(gap) for gap in gaps if gap < 0) / max(1, len([gap for gap in gaps if gap < 0]))
    underconfidence = sum(gap for gap in gaps if gap > 0) / max(1, len([gap for gap in gaps if gap > 0]))
    reliability = max(0.0, min(100.0, 100 - expected_error * 100))
    if overconfidence >= 0.08 and overconfidence > underconfidence:
        status = "overconfident"
    elif underconfidence >= 0.08 and underconfidence > overconfidence:
        status = "underconfident"
    elif max_gap <= 0.06:
        status = "mostly_calibrated"
    else:
        status = "mixed"
    return {
        "samples_count": samples_count,
        "expected_calibration_error": round(expected_error, 4),
        "mean_absolute_calibration_error": round(mean_abs, 4),
        "max_calibration_gap": round(max_gap, 4),
        "overconfidence_score": round(overconfidence, 4),
        "underconfidence_score": round(underconfidence, 4),
        "reliability_score": round(reliability, 1),
        "calibration_status": status,
    }


def generate_calibration_version(model_version: str | None, method: str = "bucket_scaling") -> str:
    safe_model = re.sub(r"[^a-zA-Z0-9_.-]+", "-", model_version or "all").strip("-") or "all"
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"calib-{method}-{safe_model}-{timestamp}"


def build_bucket_scaling_factors(buckets: list[dict[str, Any]], metrics: dict[str, Any]) -> dict[str, Any]:
    samples_count = int(metrics.get("samples_count") or 0)
    if samples_count < MINIMUM_CALIBRATION_SAMPLES:
        return {
            "method": "bucket_scaling",
            "active": False,
            "global_correction": 0.0,
            "bucket_corrections": {},
            "confidence": "insufficient_data",
        }
    usable_gaps = [float(bucket.get("calibration_gap") or 0) for bucket in buckets if bucket.get("calibration_gap") is not None]
    global_correction = max(-0.12, min(0.12, sum(usable_gaps) / max(1, len(usable_gaps))))
    corrections = {}
    for bucket in buckets:
        label = bucket.get("bucket_label") or bucket.get("bucket")
        gap = bucket.get("calibration_gap")
        count = int(bucket.get("predictions_count") or bucket.get("count") or 0)
        corrections[label] = round(max(-0.15, min(0.15, float(gap))), 4) if gap is not None and count >= MINIMUM_BUCKET_SAMPLES else round(global_correction, 4)
    return {
        "method": "bucket_scaling",
        "active": True,
        "global_correction": round(global_correction, 4),
        "bucket_corrections": corrections,
        "confidence": metrics.get("calibration_status"),
    }


def create_calibration_candidate(report: dict[str, Any], *, source: str = "production_feedback", method: str = "bucket_scaling") -> dict[str, Any]:
    samples = int(report.get("samples_count") or report.get("sample_size") or 0)
    status = "candidate" if samples >= MINIMUM_CALIBRATION_SAMPLES else "insufficient_data"
    metrics = {
        "expected_calibration_error": report.get("expected_calibration_error"),
        "mean_absolute_calibration_error": report.get("mean_absolute_calibration_error"),
        "max_calibration_gap": report.get("max_calibration_gap"),
        "overconfidence_score": report.get("overconfidence_score"),
        "underconfidence_score": report.get("underconfidence_score"),
        "reliability_score": report.get("reliability_score"),
        "calibration_status": report.get("calibration_status"),
    }
    return {
        "calibration_version": report.get("calibration_version") or generate_calibration_version(report.get("model_version"), method),
        "model_version": report.get("model_version"),
        "model_type": report.get("model_type"),
        "source": source,
        "method": method,
        "status": status,
        "samples_count": samples,
        "buckets": report.get("buckets") or [],
        "factors": report.get("factors") or {},
        "metrics": metrics,
        "recommendation": report.get("recommendation") or {},
        "created_at": _now_iso(),
    }


def build_calibration_profile(
    matches: list[dict[str, Any]],
    predictions: list[dict[str, Any]],
    model_version: str | None = None,
) -> dict[str, Any]:
    feedback = build_feedback_report(matches, predictions, model_version=model_version)
    evaluations = _prediction_evaluations(matches, predictions, model_version=model_version)
    buckets = build_confidence_buckets(evaluations)
    metrics = build_global_calibration_metrics(buckets, len(evaluations))
    factors = build_bucket_scaling_factors(buckets, metrics)
    status = metrics["calibration_status"]
    if status == "insufficient_data":
        recommendation = {
            "status": "collect_more_data",
            "reason": "Données insuffisantes pour activer une calibration fiable.",
            "next_action": "Continuer le shadow testing.",
        }
    elif status == "overconfident":
        recommendation = {
            "status": "review_overconfidence",
            "reason": "Le modèle semble trop confiant sur les observations disponibles.",
            "next_action": "Créer une calibration candidate et la revoir manuellement.",
        }
    elif status == "underconfident":
        recommendation = {
            "status": "review_underconfidence",
            "reason": "Le modèle semble prudent par rapport aux résultats observés.",
            "next_action": "Créer une calibration candidate et la revoir manuellement.",
        }
    else:
        recommendation = {
            "status": "mostly_calibrated",
            "reason": "La calibration observée est globalement stable.",
            "next_action": "Continuer la surveillance.",
        }
    calibration_version = generate_calibration_version(model_version or "all", "bucket_scaling") if len(evaluations) else CALIBRATION_VERSION
    return {
        "status": "ok" if evaluations else "empty",
        "storage": "postgresql",
        "calibration_status": status,
        "active_calibration_version": None,
        "latest_calibration_version": calibration_version,
        "calibration_version": calibration_version,
        "model_version": model_version or "all",
        "generated_at": _now_iso(),
        "samples_count": len(evaluations),
        "sample_size": len(evaluations),
        "minimum_required": MINIMUM_CALIBRATION_SAMPLES,
        "global_calibration_factor": round(1 + float(factors.get("global_correction") or 0), 3),
        "expected_calibration_error": metrics["expected_calibration_error"],
        "mean_absolute_calibration_error": metrics["mean_absolute_calibration_error"],
        "max_calibration_gap": metrics["max_calibration_gap"],
        "overconfidence_score": metrics["overconfidence_score"],
        "underconfidence_score": metrics["underconfidence_score"],
        "reliability_score": metrics["reliability_score"],
        "buckets": buckets,
        "factors": factors,
        "recommendation": recommendation,
        "source_metrics": {
            "accuracy": feedback.get("accuracy"),
            "log_loss": feedback.get("log_loss"),
            "brier_score": feedback.get("brier_score"),
        },
    }


def _correction_for_probability(probability: float, calibration_profile: dict[str, Any] | None) -> float:
    profile = calibration_profile or {}
    factors = profile.get("factors") or {}
    bucket_corrections = factors.get("bucket_corrections") or {}
    bucket = _bucket_label(int(round(probability * 100)))
    try:
        return float(bucket_corrections.get(bucket, factors.get("global_correction", 0.0)) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def apply_bucket_calibration_binary(probability: float, calibration_profile: dict[str, Any] | None = None) -> float:
    try:
        original = max(0.01, min(0.99, float(probability)))
    except (TypeError, ValueError):
        original = 0.5
    factors = (calibration_profile or {}).get("factors") or {}
    if not factors.get("active"):
        return round(original, 4)
    correction = _correction_for_probability(original, calibration_profile)
    return round(max(0.01, min(0.99, original + correction)), 4)


def apply_bucket_calibration_multiclass(probabilities: dict[str, Any], calibration_profile: dict[str, Any] | None = None) -> dict[str, int]:
    normalized = normalize_probabilities(probabilities)
    factors = (calibration_profile or {}).get("factors") or {}
    if not factors.get("active"):
        return normalized
    favorite = max(OUTCOMES, key=lambda key: normalized.get(key, 0))
    original_favorite = max(0.01, min(0.99, normalized[favorite] / 100))
    calibrated_favorite = apply_bucket_calibration_binary(original_favorite, calibration_profile)
    original_others = [key for key in OUTCOMES if key != favorite]
    other_total = sum(normalized[key] for key in original_others) or 1
    remaining = max(1.0, (1 - calibrated_favorite) * 100)
    adjusted = {favorite: calibrated_favorite * 100}
    for key in original_others:
        adjusted[key] = remaining * (normalized[key] / other_total)
    return normalize_probabilities(adjusted)


def calibrate_prediction(prediction: dict[str, Any], calibration_profile: dict[str, Any] | None = None) -> dict[str, Any]:
    calibrated = dict(prediction or {})
    probabilities = normalize_probabilities(calibrated.get("probabilities"))
    profile = calibration_profile or {}
    bucket = _bucket_label(_favorite_probability(probabilities))
    adjusted = apply_bucket_calibration_multiclass(probabilities, profile)
    calibrated["original_probabilities"] = probabilities
    calibrated["original_probabilities_json"] = probabilities
    calibrated["probabilities"] = adjusted
    calibrated["calibrated_probabilities_json"] = adjusted
    calibrated["calibration_version"] = profile.get("calibration_version") or CALIBRATION_VERSION
    applied = bool((profile.get("factors") or {}).get("active"))
    calibrated["calibration"] = {
        **(calibrated.get("calibration") or {}),
        "applied": applied,
        "method": profile.get("method") or "bucket_scaling",
        "bucket": bucket,
        "factor": profile.get("global_calibration_factor"),
        "calibration_version": calibrated["calibration_version"],
    }
    return calibrated
