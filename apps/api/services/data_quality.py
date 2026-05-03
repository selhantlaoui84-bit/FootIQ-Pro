from __future__ import annotations

from typing import Any

from services.advanced_features import ADVANCED_FEATURE_COLUMNS, FEATURE_SET_VERSION


LEAKAGE_KEYWORDS = [
    "winner",
    "result",
    "full_time",
    "half_time",
    "home_goals",
    "away_goals",
    "actual",
    "target",
]

SAFE_FEATURE_NAMES = [
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
] + ADVANCED_FEATURE_COLUMNS

BLOCKED_FEATURE_NAMES = [
    "score_full_time_home",
    "score_full_time_away",
    "score_half_time_home",
    "score_half_time_away",
    "winner",
    "actual_result",
    "result",
    "target_result",
    "home_goals",
    "away_goals",
    "final_score",
    "full_time_result",
]

ALLOWED_TARGET_FIELDS = [
    "result",
    "home_goals",
    "away_goals",
    "over_2_5",
    "btts",
]

CORE_FEATURES = [
    "elo_delta",
    "form_delta",
    "attack_delta",
    "defense_delta",
    "draw_risk_score",
    "data_quality_score",
    "home_probability",
    "draw_probability",
    "away_probability",
]


def is_potential_leakage_feature(feature_name: str) -> bool:
    normalized = str(feature_name or "").lower()
    if normalized in SAFE_FEATURE_NAMES:
        return False
    if normalized in BLOCKED_FEATURE_NAMES:
        return True
    if "score" in normalized:
        match_score_context = ("final", "full_time", "half_time", "home", "away", "goals")
        return any(context in normalized for context in match_score_context)
    return any(keyword in normalized for keyword in LEAKAGE_KEYWORDS)


def _quality_score(leakage_features: list[str], missing_core_features: list[str], feature_count: int, has_target: bool) -> int:
    score = 100
    score -= min(len(leakage_features) * 35, 100)
    score -= min(len(missing_core_features) * 6, 45)
    if feature_count <= 0:
        score -= 40
    if not has_target:
        score -= 8
    return max(0, min(100, score))


def inspect_feature_row(row: dict[str, Any]) -> dict[str, Any]:
    try:
        features = row.get("features") or {}
        target = row.get("target") or {}
        if not isinstance(features, dict):
            features = {}
        if not isinstance(target, dict):
            target = {}

        feature_names = [str(name) for name in features.keys()]
        leakage_features = sorted({name for name in feature_names if is_potential_leakage_feature(name)})
        missing_core_features = [name for name in CORE_FEATURES if name not in features]
        target_fields = sorted(str(name) for name in target.keys())
        warnings = []

        if leakage_features:
            warnings.append("Variables suspectes de fuite post-match detectees dans les features.")
        if len(missing_core_features) >= 4:
            warnings.append("Plusieurs variables coeur sont absentes.")
        elif missing_core_features:
            warnings.append("Certaines variables coeur sont absentes.")
        unknown_target_fields = [name for name in target_fields if name not in ALLOWED_TARGET_FIELDS]
        if unknown_target_fields:
            warnings.append("Le target contient des champs non standards.")

        status = "ok"
        if leakage_features:
            status = "blocked"
        elif warnings:
            status = "warning"

        quality_score = _quality_score(leakage_features, missing_core_features, len(feature_names), bool(target))

        return {
            "match_id": row.get("match_id", ""),
            "model_version": row.get("model_version"),
            "feature_set_version": row.get("feature_set_version"),
            "feature_count": len(feature_names),
            "has_target": bool(target),
            "target_fields": target_fields,
            "leakage_features": leakage_features,
            "missing_core_features": missing_core_features,
            "quality_score": quality_score,
            "status": status,
            "warnings": warnings,
        }
    except Exception as exc:
        return {
            "match_id": row.get("match_id", "") if isinstance(row, dict) else "",
            "model_version": row.get("model_version") if isinstance(row, dict) else None,
            "feature_set_version": row.get("feature_set_version") if isinstance(row, dict) else None,
            "feature_count": 0,
            "has_target": False,
            "target_fields": [],
            "leakage_features": [],
            "missing_core_features": CORE_FEATURES,
            "quality_score": 0,
            "status": "warning",
            "warnings": [f"Ligne impossible a inspecter: {exc}"],
        }


def build_dataset_quality_report(rows: list[dict[str, Any]], limit: int = 1000) -> dict[str, Any]:
    checked_rows = list(rows or [])[: max(1, int(limit or 1000))]
    inspections = [inspect_feature_row(row) for row in checked_rows]
    rows_checked = len(inspections)

    if rows_checked == 0:
        return {
            "status": "empty",
            "rows_checked": 0,
            "rows_with_target": 0,
            "rows_without_target": 0,
            "blocked_rows": 0,
            "warning_rows": 0,
            "ok_rows": 0,
            "average_quality_score": 0,
            "leakage_features_detected": [],
            "missing_core_features": {},
            "target_field_coverage": {},
            "safe_for_training": False,
            "recommendation": "insufficient_data",
            "recommendation_reason": "Aucune ligne de Feature Store disponible pour le controle qualite.",
            "safe_feature_names": SAFE_FEATURE_NAMES,
            "blocked_feature_names": BLOCKED_FEATURE_NAMES,
            "observed_feature_names": [],
            "leakage_detection_mode": "strict_feature_only",
            "sample_checked_rows": [],
            "feature_set_version": None,
            "feature_set_version_coverage": {},
            "advanced_feature_coverage": {
                "advanced_features_present": 0,
                "advanced_features_expected": len(ADVANCED_FEATURE_COLUMNS),
                "coverage_percent": 0,
            },
            "sample_issues": [],
        }

    rows_with_target = sum(1 for item in inspections if item["has_target"])
    blocked_rows = sum(1 for item in inspections if item["status"] == "blocked")
    warning_rows = sum(1 for item in inspections if item["status"] == "warning")
    ok_rows = sum(1 for item in inspections if item["status"] == "ok")
    average_quality_score = round(sum(item["quality_score"] for item in inspections) / rows_checked)

    leakage_features = sorted({name for item in inspections for name in item["leakage_features"]})
    observed_feature_names = sorted({name for row in checked_rows for name in (row.get("features") or {}).keys()})
    advanced_present = len([name for name in ADVANCED_FEATURE_COLUMNS if name in observed_feature_names])
    feature_set_versions: dict[str, int] = {}
    missing_core_features: dict[str, int] = {}
    target_field_coverage: dict[str, int] = {field: 0 for field in ALLOWED_TARGET_FIELDS}

    for item in inspections:
        for name in item["missing_core_features"]:
            missing_core_features[name] = missing_core_features.get(name, 0) + 1
        for name in item["target_fields"]:
            target_field_coverage[name] = target_field_coverage.get(name, 0) + 1
        version = item.get("feature_set_version") or (
            FEATURE_SET_VERSION if any(name in observed_feature_names for name in ADVANCED_FEATURE_COLUMNS) else "base"
        )
        feature_set_versions[version] = feature_set_versions.get(version, 0) + 1

    sample_issues = [
        item
        for item in inspections
        if item["status"] in {"warning", "blocked"}
    ][:20]
    sample_checked_rows = [
        {
            "match_id": item["match_id"],
            "feature_set_version": item.get("feature_set_version"),
            "feature_names": sorted((checked_rows[index].get("features") or {}).keys()),
            "target_fields": item["target_fields"],
            "leakage_features": item["leakage_features"],
            "status": item["status"],
        }
        for index, item in enumerate(inspections[:5])
    ]

    status = "ok"
    recommendation = "safe_to_train"
    reason = "Le dataset ne presente pas de fuite evidente et contient assez de targets pour entrainer."
    safe_for_training = True

    if blocked_rows > 0:
        status = "blocked"
        recommendation = "blocked_leakage_detected"
        reason = "Des features semblent contenir des informations post-match. Entrainement bloque."
        safe_for_training = False
    elif rows_with_target < 30:
        recommendation = "insufficient_data"
        reason = "Moins de 30 lignes supervisees sont disponibles pour l'entrainement."
        safe_for_training = False
    elif warning_rows > 0:
        recommendation = "review_warnings"
        reason = "Aucune fuite bloquante detectee, mais certaines lignes ont des variables coeur manquantes."
        safe_for_training = True

    return {
        "status": status,
        "rows_checked": rows_checked,
        "rows_with_target": rows_with_target,
        "rows_without_target": rows_checked - rows_with_target,
        "blocked_rows": blocked_rows,
        "warning_rows": warning_rows,
        "ok_rows": ok_rows,
        "average_quality_score": average_quality_score,
        "leakage_features_detected": leakage_features,
        "missing_core_features": missing_core_features,
        "target_field_coverage": target_field_coverage,
        "safe_feature_names": SAFE_FEATURE_NAMES,
        "blocked_feature_names": BLOCKED_FEATURE_NAMES,
        "observed_feature_names": observed_feature_names,
        "leakage_detection_mode": "strict_feature_only",
        "feature_set_version": FEATURE_SET_VERSION if advanced_present else None,
        "feature_set_version_coverage": feature_set_versions,
        "advanced_feature_coverage": {
            "advanced_features_present": advanced_present,
            "advanced_features_expected": len(ADVANCED_FEATURE_COLUMNS),
            "coverage_percent": round((advanced_present / len(ADVANCED_FEATURE_COLUMNS)) * 100) if ADVANCED_FEATURE_COLUMNS else 0,
        },
        "safe_for_training": safe_for_training,
        "recommendation": recommendation,
        "recommendation_reason": reason,
        "sample_checked_rows": sample_checked_rows,
        "sample_issues": sample_issues,
    }
