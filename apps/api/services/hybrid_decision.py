from __future__ import annotations

from typing import Any

MODE = "official_with_shadow_advisory"
OFFICIAL_MODEL_VERSION = "elo-poisson-calibrated-v1"
CANDIDATE_MODEL_VERSION = "ml-candidate-v1"


def _pick_from_probabilities(probabilities: dict[str, Any] | None) -> str | None:
    if not probabilities:
        return None
    values: dict[str, float] = {}
    for key in ("home", "draw", "away"):
        try:
            values[key] = float(probabilities.get(key, 0))
        except Exception:
            values[key] = 0
    if not values or max(values.values()) <= 0:
        return None
    return max(values, key=values.get)


def _safe_number(value: Any, default: float = 0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def build_hybrid_decision(production_prediction: dict[str, Any], shadow_block: dict[str, Any] | None = None) -> dict[str, Any]:
    probabilities = production_prediction.get("probabilities") or {}
    production_pick = _pick_from_probabilities(probabilities)
    production_confidence = _safe_number((production_prediction.get("confidence") or {}).get("score"), 50)

    shadow_prediction = (shadow_block or {}).get("prediction") or {}
    comparison = (shadow_block or {}).get("comparison") or {}
    shadow_available = bool(shadow_prediction.get("available"))
    shadow_pick = comparison.get("shadow_pick") or shadow_prediction.get("predicted_result")
    candidate_model_version = shadow_prediction.get("model_version") if shadow_available else None
    disagreement_level = comparison.get("disagreement_level", "unknown")

    if not shadow_available:
        return {
            "mode": MODE,
            "official_model_version": production_prediction.get("model_version") or OFFICIAL_MODEL_VERSION,
            "candidate_model_version": candidate_model_version,
            "candidate_is_production": False,
            "production_pick": production_pick,
            "shadow_pick": None,
            "agreement": "unknown",
            "consensus_score": max(20, min(70, round(production_confidence * 0.75))),
            "decision_label": "shadow_indisponible",
            "risk_adjustment": 0,
            "display_message": "Signal ML shadow indisponible. La lecture officielle reste Elo/Poisson.",
            "explanation": [
                "Le modèle officiel Elo/Poisson reste la seule prédiction utilisée.",
                "Le candidat ML n'est pas disponible pour ce match ou n'a pas encore été généré.",
                "La décision reste prudente et probabiliste.",
            ],
        }

    same_pick = comparison.get("same_pick")
    if same_pick is None and production_pick and shadow_pick:
        same_pick = production_pick == shadow_pick

    confidence_delta = abs(_safe_number(comparison.get("confidence_delta"), 0))

    if same_pick is True:
        consensus_score = min(95, round(production_confidence + 12 - min(confidence_delta, 10) * 0.2))
        risk_adjustment = -5
        label = "signal_renforce"
        agreement = "agree"
        message = "Le candidat ML confirme le signal officiel. Le modèle officiel reste prioritaire."
        explanation = [
            "Elo/Poisson et ML shadow pointent vers la même issue principale.",
            "Ce consensus renforce la lisibilité statistique, sans garantir le résultat.",
            "Le ML reste un signal d'observation, pas un moteur de production.",
        ]
    else:
        penalty = 18 if disagreement_level == "high" else 10
        consensus_score = max(5, round(production_confidence - penalty - min(confidence_delta, 20) * 0.3))
        risk_adjustment = 18 if disagreement_level == "high" else 10
        label = "desaccord_modele"
        agreement = "disagree"
        message = "Le ML shadow contredit le signal officiel. La recommandation reste Elo/Poisson avec prudence accrue."
        explanation = [
            "Le modèle officiel et le candidat ML ne choisissent pas la même issue.",
            "Ce désaccord augmente le risque de lecture du match.",
            "Aucune activation ML n'est effectuée: le signal reste consultatif.",
        ]

    if label == "desaccord_modele" and disagreement_level in {"low", "unknown"}:
        label = "prudence_shadow"
        message = "Le signal ML invite à une prudence modérée, sans remettre en cause le modèle officiel."

    return {
        "mode": MODE,
        "official_model_version": production_prediction.get("model_version") or OFFICIAL_MODEL_VERSION,
        "candidate_model_version": candidate_model_version or CANDIDATE_MODEL_VERSION,
        "candidate_is_production": False,
        "production_pick": production_pick,
        "shadow_pick": shadow_pick,
        "agreement": agreement,
        "consensus_score": consensus_score,
        "decision_label": label,
        "risk_adjustment": risk_adjustment,
        "display_message": message,
        "explanation": explanation,
    }
