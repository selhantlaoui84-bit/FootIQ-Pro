from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from services.calibration import normalize_probabilities
from services.feedback_engine import build_feedback_report

CALIBRATION_VERSION = "calibration-buckets-v1"
BUCKETS = ((0, 49), (50, 59), (60, 69), (70, 79), (80, 89), (90, 100))


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _bucket_label(value: int) -> str:
    for start, end in BUCKETS:
        if start <= value <= end:
            return f"{start}-{end}"
    return "unknown"


def _favorite_probability(probabilities: dict[str, Any]) -> int:
    normalized = normalize_probabilities(probabilities)
    return int(max(normalized.values()))


def build_calibration_profile(
    matches: list[dict[str, Any]],
    predictions: list[dict[str, Any]],
    model_version: str | None = None,
) -> dict[str, Any]:
    feedback = build_feedback_report(matches, predictions, model_version=model_version)
    bucket_source = feedback.get("performance_by_confidence") or {}
    buckets = []
    weighted_factor = 1.0
    weighted_count = 0

    for start, end in BUCKETS:
        label = f"{start}-{end}"
        item = bucket_source.get(label) or {}
        count = int(item.get("count") or 0)
        predicted_midpoint = (start + end) / 100 / 2
        observed = float(item.get("accuracy") or 0) / 100
        factor = 1.0 if count == 0 or predicted_midpoint <= 0 else max(0.65, min(1.25, observed / predicted_midpoint))
        buckets.append(
            {
                "bucket": label,
                "count": count,
                "predicted_probability": round(predicted_midpoint, 3),
                "observed_success_rate": round(observed, 3),
                "calibration_factor": round(factor, 3),
            }
        )
        weighted_factor += factor * count
        weighted_count += count

    global_factor = round(weighted_factor / max(1, weighted_count), 3)
    return {
        "status": feedback.get("status", "empty"),
        "calibration_version": CALIBRATION_VERSION,
        "model_version": model_version or "all",
        "generated_at": _now_iso(),
        "sample_size": feedback.get("evaluated_matches", 0),
        "global_calibration_factor": global_factor,
        "buckets": buckets,
        "source_metrics": {
            "accuracy": feedback.get("accuracy"),
            "log_loss": feedback.get("log_loss"),
            "brier_score": feedback.get("brier_score"),
        },
    }


def calibrate_prediction(prediction: dict[str, Any], calibration_profile: dict[str, Any] | None = None) -> dict[str, Any]:
    calibrated = dict(prediction or {})
    probabilities = normalize_probabilities(calibrated.get("probabilities"))
    profile = calibration_profile or {}
    bucket_map = {item.get("bucket"): item for item in profile.get("buckets", []) if isinstance(item, dict)}
    favorite = max(probabilities, key=probabilities.get)
    bucket = _bucket_label(_favorite_probability(probabilities))
    factor = float((bucket_map.get(bucket) or {}).get("calibration_factor") or profile.get("global_calibration_factor") or 1.0)

    adjusted = dict(probabilities)
    favorite_probability = adjusted[favorite]
    adjusted[favorite] = round(favorite_probability * factor)
    remaining_delta = favorite_probability - adjusted[favorite]
    others = [key for key in ("home", "draw", "away") if key != favorite]
    for key in others:
        adjusted[key] = adjusted[key] + round(remaining_delta / len(others))

    calibrated["probabilities"] = normalize_probabilities(adjusted)
    calibrated["calibration_version"] = profile.get("calibration_version") or CALIBRATION_VERSION
    calibrated["calibration"] = {
        **(calibrated.get("calibration") or {}),
        "applied": True,
        "method": "confidence_bucket_factor",
        "bucket": bucket,
        "factor": round(factor, 3),
        "calibration_version": calibrated["calibration_version"],
    }
    return calibrated
