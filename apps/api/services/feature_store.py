from __future__ import annotations

from collections import Counter
from typing import Callable

from services.advanced_features import ADVANCED_FEATURE_COLUMNS, FEATURE_SET_VERSION, build_advanced_pre_match_features
from services.backtesting import get_match_result


BASE_FEATURE_COLUMNS = [
    "elo_delta",
    "form_delta",
    "attack_delta",
    "defense_delta",
    "draw_risk_score",
    "data_quality_score",
    "risk_score",
    "trap_match_score",
    "expected_home",
    "expected_away",
    "over_2_5_probability",
    "btts_probability",
    "home_probability",
    "draw_probability",
    "away_probability",
]
FEATURE_SNAPSHOT_COLUMNS = BASE_FEATURE_COLUMNS + ADVANCED_FEATURE_COLUMNS


def build_target_from_match(match: dict) -> dict | None:
    result = get_match_result(match)
    if result is None:
        return None

    return {
        "result": result["result"],
        "home_goals": result["home_goals"],
        "away_goals": result["away_goals"],
        "over_2_5": result["over_2_5"],
        "btts": result["btts"],
    }


def _identity_values(item: dict) -> list[str]:
    values = []
    for key in ("match_id", "id", "slug"):
        value = item.get(key)
        if value is not None and str(value) not in values:
            values.append(str(value))
    return values


def _prediction_indexes(predictions: list[dict]) -> dict[str, dict[str, dict]]:
    indexes = {"match_id": {}, "id": {}, "slug": {}, "any": {}}
    for prediction in predictions or []:
        for key in ("match_id", "id", "slug"):
            value = prediction.get(key)
            if value is not None:
                indexes[key][str(value)] = prediction
                indexes["any"][str(value)] = prediction
    return indexes


def find_prediction_for_match(match: dict, predictions: list[dict]) -> tuple[dict | None, str | None]:
    indexes = _prediction_indexes(predictions)
    for key in ("match_id", "id", "slug"):
        value = match.get(key)
        if value is not None and str(value) in indexes[key]:
            return indexes[key][str(value)], key
    for value in _identity_values(match):
        if value in indexes["any"]:
            return indexes["any"][value], "any"
    return None, None


def _number(value, default=0):
    try:
        if value is None:
            return default
        return value
    except (TypeError, ValueError):
        return default


def _sanitize_features(features: dict) -> dict:
    return {name: (features or {}).get(name, 0) for name in FEATURE_SNAPSHOT_COLUMNS}


def build_feature_snapshot(match: dict, all_matches: list[dict], prediction: dict) -> dict:
    match_id = match.get("match_id") or match.get("id") or match.get("slug") or prediction.get("match_id")
    model_version = prediction.get("model_version", "unknown")
    prediction_features = prediction.get("features") or {}
    goals = prediction.get("goals") or {}
    probabilities = prediction.get("probabilities") or {}

    features = {
        "elo_delta": _number(prediction_features.get("elo_delta")),
        "form_delta": _number(prediction_features.get("form_delta")),
        "attack_delta": _number(prediction_features.get("attack_delta")),
        "defense_delta": _number(prediction_features.get("defense_delta")),
        "draw_risk_score": _number(prediction_features.get("draw_risk_score")),
        "data_quality_score": _number(prediction_features.get("data_quality_score")),
        "risk_score": _number(prediction.get("risk_score")),
        "trap_match_score": _number(prediction.get("trap_match_score")),
        "expected_home": _number(goals.get("expected_home")),
        "expected_away": _number(goals.get("expected_away")),
        "over_2_5_probability": _number(goals.get("over_2_5")),
        "btts_probability": _number(goals.get("btts")),
        "home_probability": _number(probabilities.get("home")),
        "draw_probability": _number(probabilities.get("draw")),
        "away_probability": _number(probabilities.get("away")),
    }
    features.update(build_advanced_pre_match_features(match, all_matches))

    return {
        "match_id": match_id,
        "model_version": model_version,
        "feature_set_version": FEATURE_SET_VERSION,
        "features": _sanitize_features(features),
        "target": build_target_from_match(match),
    }


def build_feature_snapshots_detailed(
    matches: list[dict],
    predictions: list[dict],
    target_matches: list[dict] | None = None,
    prediction_factory: Callable[[dict], dict | None] | None = None,
) -> dict:
    snapshots = []
    rejection_reasons = Counter({
        "not_finished": 0,
        "missing_score": 0,
        "missing_prediction": 0,
        "prediction_generation_failed": 0,
        "invalid_target": 0,
        "invalid_features": 0,
        "save_failed": 0,
    })
    sample_rejected = []
    first_candidate = None

    selected_matches = target_matches if target_matches is not None else matches
    for match in selected_matches or []:
        match_sample = {
            "id": match.get("id"),
            "match_id": match.get("match_id"),
            "slug": match.get("slug"),
            "status": match.get("status"),
            "score_full_time_home": match.get("score_full_time_home"),
            "score_full_time_away": match.get("score_full_time_away"),
        }

        if str(match.get("status") or "").upper() != "FINISHED":
            rejection_reasons["not_finished"] += 1
            if len(sample_rejected) < 5:
                sample_rejected.append({**match_sample, "reason": "not_finished"})
            continue

        target = build_target_from_match(match)
        if target is None:
            rejection_reasons["missing_score"] += 1
            if len(sample_rejected) < 5:
                sample_rejected.append({**match_sample, "reason": "missing_score"})
            continue

        prediction, join_key = find_prediction_for_match(match, predictions)
        if prediction is None and prediction_factory is not None:
            try:
                prediction = prediction_factory(match)
                join_key = "generated_on_the_fly" if prediction else None
            except Exception:
                rejection_reasons["prediction_generation_failed"] += 1
                if len(sample_rejected) < 5:
                    sample_rejected.append({**match_sample, "reason": "prediction_generation_failed"})
                continue

        if prediction is None:
            rejection_reasons["missing_prediction"] += 1
            if len(sample_rejected) < 5:
                sample_rejected.append({**match_sample, "reason": "missing_prediction"})
            continue

        try:
            snapshot = build_feature_snapshot(match, matches, prediction)
        except Exception:
            rejection_reasons["invalid_features"] += 1
            if len(sample_rejected) < 5:
                sample_rejected.append({**match_sample, "reason": "invalid_features"})
            continue

        if snapshot.get("target") is None:
            rejection_reasons["invalid_target"] += 1
            if len(sample_rejected) < 5:
                sample_rejected.append({**match_sample, "reason": "invalid_target"})
            continue
        if not snapshot.get("features"):
            rejection_reasons["invalid_features"] += 1
            if len(sample_rejected) < 5:
                sample_rejected.append({**match_sample, "reason": "invalid_features"})
            continue

        snapshot["prediction_source"] = join_key or "unknown"
        snapshots.append(snapshot)
        if first_candidate is None:
            first_candidate = {
                "match": match_sample,
                "prediction_id": prediction.get("id"),
                "prediction_match_id": prediction.get("match_id"),
                "prediction_slug": prediction.get("slug"),
                "join_key": join_key,
                "target": snapshot.get("target"),
            }

    return {
        "snapshots": snapshots,
        "rejection_reasons_count": dict(rejection_reasons),
        "sample_rejected_matches": sample_rejected,
        "first_trainable_candidate_sample": first_candidate,
    }


def build_feature_snapshots(matches: list[dict], predictions: list[dict], target_matches: list[dict] | None = None) -> list[dict]:
    return build_feature_snapshots_detailed(matches, predictions, target_matches=target_matches)["snapshots"]


def summarize_feature_store(feature_snapshots: list[dict]) -> dict:
    snapshots = feature_snapshots or []
    with_target = [item for item in snapshots if item.get("target")]
    model_versions = {}
    feature_names = set()

    for item in snapshots:
        model_version = item.get("model_version", "unknown")
        model_versions[model_version] = model_versions.get(model_version, 0) + 1
        features = item.get("features") or {}
        feature_names.update(features.keys())

    count = len(snapshots)
    with_target_count = len(with_target)

    return {
        "snapshots_count": count,
        "with_target_count": with_target_count,
        "without_target_count": count - with_target_count,
        "model_versions": model_versions,
        "feature_names": sorted(feature_names),
        "feature_set_version": FEATURE_SET_VERSION if any(name in feature_names for name in ADVANCED_FEATURE_COLUMNS) else None,
        "advanced_feature_coverage": _advanced_feature_coverage(feature_names),
        "target_coverage": round((with_target_count / count) * 100) if count else 0,
    }


def _advanced_feature_coverage(feature_names: set[str]) -> dict:
    present = len([name for name in ADVANCED_FEATURE_COLUMNS if name in feature_names])
    expected = len(ADVANCED_FEATURE_COLUMNS)
    return {
        "advanced_features_present": present,
        "advanced_features_expected": expected,
        "coverage_percent": round((present / expected) * 100) if expected else 0,
    }
