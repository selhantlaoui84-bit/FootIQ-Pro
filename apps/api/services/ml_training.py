from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, confusion_matrix, log_loss
from sklearn.model_selection import train_test_split

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


def prepare_training_rows(feature_rows: list[dict]) -> dict[str, Any]:
    x_rows = []
    y_rows = []
    invalid_rows = 0
    target_distribution: dict[str, int] = {}

    for row in feature_rows or []:
        target = row.get("target") or {}
        result = target.get("result")
        if result not in LABEL_MAPPING:
            invalid_rows += 1
            continue

        features = row.get("features") or {}
        try:
            x_rows.append([_to_float(features.get(column)) for column in FEATURE_COLUMNS])
            y_rows.append(LABEL_MAPPING[result])
            target_distribution[result] = target_distribution.get(result, 0) + 1
        except Exception:
            invalid_rows += 1
            continue

    return {
        "X": np.array(x_rows, dtype=float),
        "y": np.array(y_rows, dtype=int),
        "rows_loaded": len(feature_rows or []),
        "rows_used": len(y_rows),
        "invalid_rows": invalid_rows,
        "feature_columns": FEATURE_COLUMNS,
        "features_used": FEATURE_COLUMNS,
        "label_mapping": LABEL_MAPPING,
        "target_distribution": target_distribution,
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


def _feature_importance(model: Any) -> list[dict[str, Any]]:
    importances = getattr(model, "feature_importances_", None)
    if importances is None:
        return []
    rows = [
        {"feature": column, "importance": round(float(importance), 6)}
        for column, importance in zip(FEATURE_COLUMNS, importances)
    ]
    return sorted(rows, key=lambda item: item["importance"], reverse=True)


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
    target_distribution = prepared["target_distribution"]

    if rows_used < 30:
        report = _empty_report("insufficient_data", "At least 30 supervised rows are required to train a candidate model.")
        report["rows_loaded"] = rows_loaded
        report["rows_used"] = rows_used
        report["invalid_rows"] = invalid_rows
        report["target_distribution"] = target_distribution
        return report

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
            labels = [0, 1, 2]
            loss_value = round(float(log_loss(y_test, probabilities, labels=labels)), 4)
            brier_value = _brier_score_1x2(probabilities, y_test)

        labels = [0, 1, 2]
        matrix = confusion_matrix(y_test, predictions, labels=labels).tolist()
        now = datetime.now(timezone.utc).isoformat()
        MODEL_DIR.mkdir(parents=True, exist_ok=True)

        metadata = {
            "status": "ok",
            "model_type": resolved_type,
            "fallback_used": fallback_used,
            "model_version": MODEL_VERSION,
            "rows_loaded": rows_loaded,
            "rows_used": rows_used,
            "invalid_rows": invalid_rows,
            "train_rows": int(len(y_train)),
            "test_rows": int(len(y_test)),
            "accuracy": round(float(accuracy_score(y_test, predictions)) * 100),
            "log_loss": loss_value,
            "brier_score_1x2": brier_value,
            "confusion_matrix": {
                "labels": ["home", "draw", "away"],
                "matrix": matrix,
            },
            "feature_importance": _feature_importance(model),
            "feature_columns": FEATURE_COLUMNS,
            "features_used": FEATURE_COLUMNS,
            "feature_set_version": FEATURE_SET_VERSION,
            "feature_columns_count": len(FEATURE_COLUMNS),
            "target_distribution": target_distribution,
            "trained_at": now,
            "artifact_path": "ml_models/latest_candidate.joblib",
            "metadata_path": "ml_models/latest_candidate_metadata.json",
            "note": NOTE,
        }

        joblib.dump({"model": model, "metadata": metadata, "feature_columns": FEATURE_COLUMNS}, ARTIFACT_PATH)
        METADATA_PATH.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        return metadata
    except Exception as exc:
        return _empty_report("error", str(exc))


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
