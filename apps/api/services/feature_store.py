from __future__ import annotations

from services.backtesting import get_match_result


FEATURE_SNAPSHOT_COLUMNS = [
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

    return {
        "match_id": match_id,
        "model_version": model_version,
        "features": _sanitize_features(features),
        "target": build_target_from_match(match),
    }


def build_feature_snapshots(matches: list[dict], predictions: list[dict]) -> list[dict]:
    predictions_by_id = {
        prediction.get("match_id") or prediction.get("id") or prediction.get("slug"): prediction
        for prediction in predictions or []
        if prediction.get("match_id") or prediction.get("id") or prediction.get("slug")
    }
    snapshots = []

    for match in matches or []:
        match_id = match.get("match_id") or match.get("id") or match.get("slug")
        prediction = predictions_by_id.get(match_id)
        if prediction is None:
            continue
        try:
            snapshots.append(build_feature_snapshot(match, matches, prediction))
        except Exception:
            continue

    return snapshots


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
        "target_coverage": round((with_target_count / count) * 100) if count else 0,
    }
