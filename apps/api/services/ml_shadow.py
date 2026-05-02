from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np

from services.ml_training import FEATURE_COLUMNS, MODEL_VERSION as ML_CANDIDATE_VERSION

BASE_DIR = Path(__file__).resolve().parents[1]
MODEL_DIR = BASE_DIR / "ml_models"
ARTIFACT_PATH = MODEL_DIR / "latest_candidate.joblib"
METADATA_PATH = MODEL_DIR / "latest_candidate_metadata.json"
LABELS = ["home", "draw", "away"]


def load_candidate_model() -> dict[str, Any] | None:
    if not ARTIFACT_PATH.exists():
        return None

    try:
        artifact = joblib.load(ARTIFACT_PATH)
        metadata = {}
        if METADATA_PATH.exists():
            metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
        if isinstance(artifact, dict):
            return {"model": artifact.get("model"), "metadata": artifact.get("metadata") or metadata}
        return {"model": artifact, "metadata": metadata}
    except Exception:
        return None


def _number(value: Any) -> float:
    try:
        if value is None:
            return 0.0
        number = float(value)
        if np.isnan(number) or np.isinf(number):
            return 0.0
        return number
    except (TypeError, ValueError):
        return 0.0


def build_ml_feature_vector(production_prediction: dict) -> np.ndarray:
    features = production_prediction.get("features") or {}
    goals = production_prediction.get("goals") or {}
    probabilities = production_prediction.get("probabilities") or {}
    values = {
        "elo_delta": features.get("elo_delta"),
        "form_delta": features.get("form_delta"),
        "attack_delta": features.get("attack_delta"),
        "defense_delta": features.get("defense_delta"),
        "draw_risk_score": features.get("draw_risk_score"),
        "data_quality_score": features.get("data_quality_score"),
        "risk_score": production_prediction.get("risk_score"),
        "trap_match_score": production_prediction.get("trap_match_score"),
        "expected_home": goals.get("expected_home"),
        "expected_away": goals.get("expected_away"),
        "over_2_5_probability": goals.get("over_2_5"),
        "btts_probability": goals.get("btts"),
        "home_probability": probabilities.get("home"),
        "draw_probability": probabilities.get("draw"),
        "away_probability": probabilities.get("away"),
    }
    return np.array([[_number(values.get(column)) for column in FEATURE_COLUMNS]], dtype=float)


def _normalize_probabilities(values: list[float]) -> dict[str, int]:
    clipped = [max(0.0, _number(value)) for value in values[:3]]
    total = sum(clipped)
    if total <= 0:
        clipped = [1.0, 1.0, 1.0]
        total = 3.0
    raw = [(value / total) * 100 for value in clipped]
    rounded = [int(round(value)) for value in raw]
    delta = 100 - sum(rounded)
    if delta:
        index = max(range(3), key=lambda item: raw[item] - int(raw[item]))
        rounded[index] += delta
    return {"home": rounded[0], "draw": rounded[1], "away": rounded[2]}


def _pick(probabilities: dict | None) -> str | None:
    if not probabilities:
        return None
    return max(("home", "draw", "away"), key=lambda key: probabilities.get(key, 0))


def generate_shadow_prediction(match: dict, production_prediction: dict) -> dict:
    match_id = (
        production_prediction.get("match_id")
        or production_prediction.get("id")
        or production_prediction.get("slug")
        or match.get("match_id")
        or match.get("id")
    )
    base = {
        "match_id": match_id,
        "model_version": ML_CANDIDATE_VERSION,
        "candidate_is_production": False,
        "available": False,
        "status": "model_missing",
        "predicted_result": None,
        "probabilities": None,
        "confidence": None,
        "source": "candidate_ml_shadow",
        "note": "Prédiction ML calculée en mode shadow. Elle n'est pas utilisée comme prédiction officielle.",
    }
    artifact = load_candidate_model()
    if artifact is None or artifact.get("model") is None:
        return base

    try:
        model = artifact["model"]
        vector = build_ml_feature_vector(production_prediction)
        if hasattr(model, "predict_proba"):
            probabilities = _normalize_probabilities(model.predict_proba(vector)[0].tolist())
        else:
            predicted_label = int(model.predict(vector)[0])
            probabilities = {label: 100 if index == predicted_label else 0 for index, label in enumerate(LABELS)}
        predicted_result = _pick(probabilities)
        return {
            **base,
            "available": True,
            "status": "ok",
            "predicted_result": predicted_result,
            "probabilities": probabilities,
            "confidence": max(probabilities.values()) if probabilities else None,
        }
    except Exception:
        return {**base, "status": "error"}


def compare_shadow_to_production(production_prediction: dict, shadow_prediction: dict) -> dict:
    production_pick = _pick(production_prediction.get("probabilities"))
    shadow_pick = shadow_prediction.get("predicted_result")
    if not shadow_prediction.get("available"):
        return {
            "same_pick": None,
            "production_pick": production_pick,
            "shadow_pick": None,
            "confidence_delta": None,
            "disagreement_level": "unknown",
            "note": "Le modèle shadow n'est pas disponible.",
        }

    production_confidence = max((production_prediction.get("probabilities") or {}).values() or [0])
    shadow_confidence = shadow_prediction.get("confidence") or 0
    confidence_delta = abs(int(shadow_confidence) - int(production_confidence))
    same_pick = production_pick == shadow_pick
    if not same_pick and confidence_delta >= 20:
        level = "high"
    elif not same_pick:
        level = "medium"
    elif confidence_delta >= 15:
        level = "low"
    else:
        level = "none"
    return {
        "same_pick": same_pick,
        "production_pick": production_pick,
        "shadow_pick": shadow_pick,
        "confidence_delta": confidence_delta,
        "disagreement_level": level,
        "note": "Comparaison shadow: le modèle officiel reste Elo/Poisson.",
    }
