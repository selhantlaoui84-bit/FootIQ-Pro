from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, confusion_matrix, log_loss
from sklearn.model_selection import train_test_split

from data import repository
from services.data_quality import is_potential_leakage_feature
from services.advanced_features import ADVANCED_FEATURE_COLUMNS, FEATURE_SET_VERSION

try:
    from xgboost import XGBClassifier
except Exception:
    XGBClassifier = None


FEATURE_COLUMNS = [
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

LABEL_MAPPING = {"home": 0, "draw": 1, "away": 2}
CLASS_LABELS = {0: "home", 1: "draw", 2: "away"}
MODEL_VERSION = "ml-candidate-v1"
NOTE = "Candidate model is not yet used for production predictions."
BASE_DIR = Path(__file__).resolve().parents[1]
MODEL_DIR = BASE_DIR / "ml_models"
ARTIFACT_PATH = MODEL_DIR / "latest_candidate.joblib"
METADATA_PATH = MODEL_DIR / "latest_candidate_metadata.json"


def _empty_report(status: str, detail: str | None = None) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    report = {
        "status": status,
        "model_type": "random_forest",
        "fallback_used": False,
        "model_version": MODEL_VERSION,
        "rows_loaded": 0,
        "rows_used": 0,
        "invalid_rows": 0,
        "train_rows": 0,
        "test_rows": 0,
        "accuracy": 0,
        "log_loss": None,
        "brier_score_1x2": None,
        "confusion_matrix": {},
        "feature_importance": [],
        "feature_columns": FEATURE_COLUMNS,
        "features_used": FEATURE_COLUMNS,
        "feature_set_version": FEATURE_SET_VERSION,
        "feature_columns_count": len(FEATURE_COLUMNS),
        "rows_after_validation": 0,
        "invalid_feature_rows": 0,
        "invalid_target_rows": 0,
        "sample_feature_keys": [],
        "examples_invalid_features": [],
        "warnings": [],
        "errors": [],
        "target_distribution": {},
        "trained_at": now,
        "artifact_path": "ml_models/latest_candidate.joblib",
        "metadata_path": "ml_models/latest_candidate_metadata.json",
        "note": NOTE,
    }
    if detail:
        report["detail"] = detail
    return report


def validate_feature_columns() -> dict[str, Any]:
    suspicious = [column for column in FEATURE_COLUMNS if is_potential_leakage_feature(column)]
    return {
        "valid": len(suspicious) == 0,
        "suspicious_columns": suspicious,
        "reason": None if not suspicious else "Feature column may leak post-match information",
    }


def _to_float(value: Any) -> float:
    try:
        if value is None:
            return 0.0
        number = float(value)
        if np.isnan(number) or np.isinf(number):
            return 0.0
        return number
    except (TypeError, ValueError):
        return 0.0


def extract_numeric_features(features_json: dict[str, Any] | None, min_features: int = 1) -> dict[str, Any]:
    numeric: dict[str, float] = {}
    invalid_keys: list[str] = []

    if not isinstance(features_json, dict):
        return {
            "valid": False,
            "features": {},
            "feature_names": [],
            "invalid_keys": [],
            "reason": "features_json is not an object",
        }

    for key, value in features_json.items():
        if isinstance(value, bool) or value is None:
            continue
        if isinstance(value, (int, float)):
            number = float(value)
        else:
            try:
                number = float(value)
            except (TypeError, ValueError):
                continue
        if math.isnan(number) or math.isinf(number):
            invalid_keys.append(str(key))
            continue
        numeric[str(key)] = number

    return {
        "valid": len(numeric) >= min_features,
        "features": numeric,
        "feature_names": sorted(numeric.keys()),
        "invalid_keys": invalid_keys,
        "reason": None if len(numeric) >= min_features else "not enough numeric features",
    }


def extract_target_class(target_json: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(target_json, dict):
        return {"valid": False, "target_class": None, "target_label": None, "reason": "target_json is not an object"}

    for key in ("result", "outcome", "winner"):
        value = target_json.get(key)
        if value is None:
            continue
        normalized = str(value).strip().lower()
        if normalized in {"home", "home_win", "home_team", "h", "1", "local"}:
            return {"valid": True, "target_class": 0, "target_label": "home"}
        if normalized in {"draw", "d", "x", "tie", "null", "nul"}:
            return {"valid": True, "target_class": 1, "target_label": "draw"}
        if normalized in {"away", "away_win", "away_team", "a", "2", "visitor"}:
            return {"valid": True, "target_class": 2, "target_label": "away"}

    if target_json.get("home_win") is True:
        return {"valid": True, "target_class": 0, "target_label": "home"}
    if target_json.get("draw") is True:
        return {"valid": True, "target_class": 1, "target_label": "draw"}
    if target_json.get("away_win") is True:
        return {"valid": True, "target_class": 2, "target_label": "away"}

    home_score = target_json.get("home_score", target_json.get("home_goals"))
    away_score = target_json.get("away_score", target_json.get("away_goals"))
    try:
        if home_score is not None and away_score is not None:
            home = float(home_score)
            away = float(away_score)
            if home > away:
                return {"valid": True, "target_class": 0, "target_label": "home"}
            if home == away:
                return {"valid": True, "target_class": 1, "target_label": "draw"}
            return {"valid": True, "target_class": 2, "target_label": "away"}
    except (TypeError, ValueError):
        pass

    return {"valid": False, "target_class": None, "target_label": None, "reason": "target class unavailable"}


def load_training_rows_from_feature_snapshots(limit: int = 5000, model_version: str | None = None) -> dict[str, Any]:
    safe_limit = max(1, min(int(limit or 5000), 10000))
    snapshots = repository.get_feature_snapshots(model_version=model_version, limit=safe_limit)
    rows: list[dict[str, Any]] = []
    invalid_feature_rows = 0
    invalid_target_rows = 0
    rows_with_features = 0
    rows_with_target = 0
    target_distribution: dict[str, int] = {}
    sample_feature_keys: list[str] = []
    examples_invalid_features: list[dict[str, Any]] = []

    for snapshot in snapshots:
        features = snapshot.get("features")
        target = snapshot.get("target")
        if isinstance(features, dict):
            rows_with_features += 1
        if isinstance(target, dict):
            rows_with_target += 1

        numeric = extract_numeric_features(features)
        target_info = extract_target_class(target)
        if not numeric["valid"]:
            invalid_feature_rows += 1
            if len(examples_invalid_features) < 5:
                examples_invalid_features.append({
                    "match_id": snapshot.get("match_id"),
                    "reason": numeric.get("reason"),
                    "feature_keys": sorted((features or {}).keys())[:10] if isinstance(features, dict) else [],
                })
            continue
        if not target_info["valid"]:
            invalid_target_rows += 1
            continue

        if not sample_feature_keys:
            sample_feature_keys = numeric["feature_names"][:15]
        label = str(target_info["target_label"])
        target_distribution[label] = target_distribution.get(label, 0) + 1
        rows.append({
            "match_id": snapshot.get("match_id"),
            "model_version": snapshot.get("model_version"),
            "created_at": snapshot.get("created_at"),
            "features": numeric["features"],
            "target": {
                "result": label,
                "target_class": target_info["target_class"],
            },
        })

    return {
        "status": "ok",
        "storage": "postgresql" if repository.db_available() else "unavailable",
        "rows": rows,
        "rows_loaded": len(snapshots),
        "rows_with_features": rows_with_features,
        "rows_with_target": rows_with_target,
        "rows_after_validation": len(rows),
        "invalid_feature_rows": invalid_feature_rows,
        "invalid_target_rows": invalid_target_rows,
        "sample_feature_keys": sample_feature_keys,
        "examples_invalid_features": examples_invalid_features,
        "target_distribution": target_distribution,
    }


def prepare_training_rows(feature_rows: list[dict]) -> dict[str, Any]:
    prepared_items = []
    invalid_rows = 0
    invalid_feature_rows = 0
    invalid_target_rows = 0
    target_distribution: dict[str, int] = {}
    feature_names_set: set[str] = set()
    examples_invalid_features: list[dict[str, Any]] = []

    for row in feature_rows or []:
        target_info = extract_target_class(row.get("target"))
        if not target_info["valid"]:
            invalid_rows += 1
            invalid_target_rows += 1
            continue

        numeric = extract_numeric_features(row.get("features"))
        if not numeric["valid"]:
            invalid_rows += 1
            invalid_feature_rows += 1
            if len(examples_invalid_features) < 5:
                examples_invalid_features.append({
                    "match_id": row.get("match_id"),
                    "reason": numeric.get("reason"),
                })
            continue

        features = numeric["features"]
        label = str(target_info["target_label"])
        prepared_items.append((features, int(target_info["target_class"])))
        feature_names_set.update(features.keys())
        target_distribution[label] = target_distribution.get(label, 0) + 1

    feature_names = sorted(feature_names_set)
    x_rows = [[_to_float(features.get(column)) for column in feature_names] for features, _ in prepared_items]
    y_rows = [target for _, target in prepared_items]

    return {
        "X": np.array(x_rows, dtype=float),
        "y": np.array(y_rows, dtype=int),
        "rows_loaded": len(feature_rows or []),
        "rows_used": len(y_rows),
        "rows_after_validation": len(y_rows),
        "invalid_rows": invalid_rows,
        "invalid_feature_rows": invalid_feature_rows,
        "invalid_target_rows": invalid_target_rows,
        "feature_columns": feature_names,
        "features_used": feature_names,
        "feature_columns_count": len(feature_names),
        "label_mapping": LABEL_MAPPING,
        "target_distribution": target_distribution,
        "examples_invalid_features": examples_invalid_features,
    }


def _can_stratify(y: np.ndarray) -> bool:
    if len(y) < 6:
        return False
    _, counts = np.unique(y, return_counts=True)
    return bool(len(counts) > 1 and counts.min() >= 2)


def _brier_score_1x2(probabilities: np.ndarray, y_true: np.ndarray) -> float | None:
    if probabilities.size == 0:
        return None
    actual = np.zeros_like(probabilities, dtype=float)
    for index, label in enumerate(y_true):
        if 0 <= label < actual.shape[1]:
            actual[index, label] = 1.0
    return round(float(np.mean(np.sum((probabilities - actual) ** 2, axis=1))), 4)


def _align_probabilities(model: Any, probabilities: np.ndarray) -> np.ndarray:
    aligned = np.zeros((probabilities.shape[0], 3), dtype=float)
    classes = getattr(model, "classes_", [0, 1, 2])
    for index, label in enumerate(classes):
        if int(label) in {0, 1, 2}:
            aligned[:, int(label)] = probabilities[:, index]
    row_sums = aligned.sum(axis=1)
    for index, total in enumerate(row_sums):
        if total > 0:
            aligned[index] = aligned[index] / total
        else:
            aligned[index] = np.array([1 / 3, 1 / 3, 1 / 3])
    return aligned


def _feature_importance(model: Any, feature_columns: list[str]) -> list[dict[str, Any]]:
    importances = getattr(model, "feature_importances_", None)
    if importances is None:
        return []
    rows = [
        {"feature": column, "importance": round(float(importance), 6)}
        for column, importance in zip(feature_columns, importances)
    ]
    return sorted(rows, key=lambda item: item["importance"], reverse=True)


def _candidate_version(model_type: str, trained_at: str) -> str:
    stamp = datetime.fromisoformat(trained_at.replace("Z", "+00:00")).strftime("%Y%m%d-%H%M%S")
    return f"ml-candidate-{model_type}-{stamp}"


def _model_for_type(model_type: str) -> tuple[Any, str, bool]:
    requested = (model_type or "random_forest").lower()
    if requested == "xgboost" and XGBClassifier is not None:
        return (
            XGBClassifier(
                n_estimators=200,
                max_depth=4,
                learning_rate=0.05,
                objective="multi:softprob",
                eval_metric="mlogloss",
                random_state=42,
                n_jobs=1,
            ),
            "xgboost",
            False,
        )

    return (
        RandomForestClassifier(
            n_estimators=200,
            max_depth=6,
            random_state=42,
            class_weight="balanced",
        ),
        "random_forest",
        requested == "xgboost",
    )


def train_candidate_model(feature_rows: list[dict], model_type: str = "random_forest") -> dict[str, Any]:
    column_validation = validate_feature_columns()
    if not column_validation["valid"]:
        report = _empty_report("blocked", column_validation["reason"])
        report["reason"] = column_validation["reason"]
        report["suspicious_columns"] = column_validation["suspicious_columns"]
        return report

    prepared = prepare_training_rows(feature_rows)
    x = prepared["X"]
    y = prepared["y"]
    rows_used = prepared["rows_used"]
    rows_loaded = prepared["rows_loaded"]
    invalid_rows = prepared["invalid_rows"]
    rows_after_validation = prepared["rows_after_validation"]
    feature_columns = prepared["feature_columns"]
    target_distribution = prepared["target_distribution"]
    warnings: list[str] = []

    if rows_used < 50:
        report = _empty_report("error", "At least 50 supervised rows are required to train a candidate model.")
        report["rows_loaded"] = rows_loaded
        report["rows_used"] = rows_used
        report["rows_after_validation"] = rows_after_validation
        report["invalid_rows"] = invalid_rows
        report["invalid_feature_rows"] = prepared["invalid_feature_rows"]
        report["invalid_target_rows"] = prepared["invalid_target_rows"]
        report["target_distribution"] = target_distribution
        report["errors"] = [report["detail"]]
        return report

    if len(np.unique(y)) < 2:
        report = _empty_report("error", "At least 2 target classes are required to train a candidate model.")
        report["rows_loaded"] = rows_loaded
        report["rows_used"] = rows_used
        report["rows_after_validation"] = rows_after_validation
        report["invalid_rows"] = invalid_rows
        report["invalid_feature_rows"] = prepared["invalid_feature_rows"]
        report["invalid_target_rows"] = prepared["invalid_target_rows"]
        report["target_distribution"] = target_distribution
        report["errors"] = [report["detail"]]
        return report

    if len(np.unique(y)) < 3:
        warnings.append("Only 2 target classes available; model trained with partial class coverage.")

    try:
        stratify = y if _can_stratify(y) else None
        x_train, x_test, y_train, y_test = train_test_split(
            x,
            y,
            test_size=0.25,
            random_state=42,
            stratify=stratify,
        )

        model, resolved_type, fallback_used = _model_for_type(model_type)
        model.fit(x_train, y_train)
        predictions = model.predict(x_test)
        probabilities = model.predict_proba(x_test) if hasattr(model, "predict_proba") else None

        loss_value = None
        brier_value = None
        if probabilities is not None:
            probabilities = _align_probabilities(model, probabilities)
            labels = [0, 1, 2]
            loss_value = round(float(log_loss(y_test, probabilities, labels=labels)), 4)
            brier_value = _brier_score_1x2(probabilities, y_test)

        labels = [0, 1, 2]
        matrix = confusion_matrix(y_test, predictions, labels=labels).tolist()
        now = datetime.now(timezone.utc).isoformat()
        model_version = _candidate_version(resolved_type, now)
        MODEL_DIR.mkdir(parents=True, exist_ok=True)

        metadata = {
            "status": "success",
            "storage": "postgresql",
            "model_type": resolved_type,
            "fallback_used": fallback_used,
            "model_version": model_version,
            "rows_loaded": rows_loaded,
            "rows_used": rows_used,
            "rows_after_validation": rows_after_validation,
            "invalid_rows": invalid_rows,
            "invalid_feature_rows": prepared["invalid_feature_rows"],
            "invalid_target_rows": prepared["invalid_target_rows"],
            "train_rows": int(len(y_train)),
            "test_rows": int(len(y_test)),
            "accuracy": round(float(accuracy_score(y_test, predictions)) * 100),
            "accuracy_rate": round(float(accuracy_score(y_test, predictions)), 4),
            "log_loss": loss_value,
            "brier_score_1x2": brier_value,
            "brier_score": brier_value,
            "confusion_matrix": {
                "labels": ["home", "draw", "away"],
                "matrix": matrix,
            },
            "feature_importance": _feature_importance(model, feature_columns),
            "feature_columns": feature_columns,
            "features_used": len(feature_columns),
            "feature_names": feature_columns,
            "feature_set_version": FEATURE_SET_VERSION,
            "feature_columns_count": len(feature_columns),
            "target_distribution": target_distribution,
            "trained_at": now,
            "artifact_path": "ml_models/latest_candidate.joblib",
            "metadata_path": "ml_models/latest_candidate_metadata.json",
            "warnings": warnings,
            "errors": [],
            "detail": None,
            "note": NOTE,
        }

        joblib.dump({"model": model, "metadata": metadata, "feature_columns": feature_columns}, ARTIFACT_PATH)
        METADATA_PATH.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        return metadata
    except Exception as exc:
        report = _empty_report("error", str(exc))
        report["rows_loaded"] = rows_loaded
        report["rows_used"] = rows_used
        report["rows_after_validation"] = rows_after_validation
        report["invalid_rows"] = invalid_rows
        report["invalid_feature_rows"] = prepared["invalid_feature_rows"]
        report["invalid_target_rows"] = prepared["invalid_target_rows"]
        report["target_distribution"] = target_distribution
        report["errors"] = [str(exc)]
        return report


def load_latest_candidate_metadata() -> dict[str, Any]:
    if not METADATA_PATH.exists():
        return {
            "status": "not_trained",
            "model_version": MODEL_VERSION,
            "feature_importance": [],
            "note": NOTE,
        }

    try:
        return json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        report = _empty_report("error", f"Could not load candidate metadata: {exc}")
        report["feature_importance"] = []
        return report


def candidate_model_exists() -> bool:
    return ARTIFACT_PATH.exists()
