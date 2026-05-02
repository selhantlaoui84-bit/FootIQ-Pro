from __future__ import annotations

from typing import Any

ENGINE_VERSION = "hybrid-engine-v1"
MODE = "official_with_hybrid_advisory"
PRODUCTION_MODEL_VERSION = "elo-poisson-calibrated-v1"
CANDIDATE_MODEL_VERSION = "ml-candidate-v1"


def _num(value: Any, default: float | None = 0) -> float | None:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _pick(probabilities: dict[str, Any] | None) -> str | None:
    if not probabilities:
        return None
    values = {key: _num(probabilities.get(key), 0) or 0 for key in ("home", "draw", "away")}
    if max(values.values()) <= 0:
        return None
    return max(values, key=values.get)


def _status_text(label: str) -> str:
    return {
        "signal_renforce": "Signal renforcé",
        "prudence_confirmee": "Prudence confirmée",
        "desaccord_modele": "Désaccord modèle",
        "eviter": "À éviter",
        "shadow_indisponible": "Shadow indisponible",
    }.get(label, label)


def build_hybrid_engine_decision(
    production_prediction: dict[str, Any],
    shadow_block: dict[str, Any] | None = None,
    shadow_backtesting: dict[str, Any] | None = None,
) -> dict[str, Any]:
    shadow_block = shadow_block or {}
    shadow_backtesting = shadow_backtesting or {}
    shadow_prediction = shadow_block.get("prediction") or {}
    comparison = shadow_block.get("comparison") or {}

    production_confidence = _num((production_prediction.get("confidence") or {}).get("score"), None)
    risk_score = _num(production_prediction.get("risk_score"), 0) or 0
    production_pick = comparison.get("production_pick") or _pick(production_prediction.get("probabilities"))
    shadow_available = bool(shadow_prediction.get("available"))
    shadow_pick = comparison.get("shadow_pick") or shadow_prediction.get("predicted_result") or _pick(shadow_prediction.get("probabilities"))
    shadow_confidence = _num(shadow_prediction.get("confidence"), None)
    confidence_delta = _num(comparison.get("confidence_delta"), None)
    disagreement_level = comparison.get("disagreement_level")
    evaluated_matches = int(_num(shadow_backtesting.get("evaluated_matches"), 0) or 0)
    activation_recommendation = shadow_backtesting.get("activation_recommendation")
    shadow_accuracy = _num(shadow_backtesting.get("shadow_accuracy"), None)
    production_accuracy = _num(shadow_backtesting.get("production_accuracy"), None)

    warnings: list[str] = []
    if evaluated_matches < 50:
        warnings.append("Échantillon shadow encore limité: le signal ML doit rester interprété avec prudence.")
    if activation_recommendation == "do_not_activate":
        warnings.append("Le backtesting shadow ne soutient pas une activation du ML candidat.")

    if not shadow_available or not shadow_pick:
        label = "shadow_indisponible"
        action = "insufficient_shadow_data"
        level = "unknown"
        agreement = "unknown"
        consensus_score = max(20, min(55, round((production_confidence or 50) * 0.65)))
        risk_adjustment = 0
        title = "Signal ML indisponible"
        message = "Le modèle officiel Elo/Poisson reste la référence. Aucun signal ML shadow exploitable n'est disponible pour ce match."
        explanation = [
            "La prédiction officielle reste inchangée.",
            "Le moteur hybride ne remplace jamais le modèle de production.",
            "Générez les prédictions shadow pour obtenir un signal de comparaison.",
        ]
    else:
        agree = production_pick == shadow_pick
        agreement = "agree" if agree else "disagree"
        strong_confidence = (production_confidence or 0) >= 70
        low_confidence = (production_confidence or 0) < 55
        high_risk = risk_score >= 65

        if agree and strong_confidence:
            label = "signal_renforce"
            action = "follow_official_with_confidence"
            level = "strong"
            consensus_score = min(95, round((production_confidence or 70) + 12))
            risk_adjustment = -8
        elif agree:
            label = "prudence_confirmee"
            action = "follow_official_with_caution"
            level = "medium"
            consensus_score = min(82, round((production_confidence or 55) + 8))
            risk_adjustment = -2
        elif low_confidence and high_risk:
            label = "eviter"
            action = "avoid_match"
            level = "avoid"
            consensus_score = max(5, round((production_confidence or 45) - 25))
            risk_adjustment = 25
        else:
            label = "desaccord_modele"
            action = "review_before_decision"
            level = "weak"
            penalty = 22 if disagreement_level == "high" else 14
            consensus_score = max(10, round((production_confidence or 55) - penalty))
            risk_adjustment = 18 if disagreement_level == "high" else 12

        if activation_recommendation == "do_not_activate" and label == "signal_renforce":
            label = "prudence_confirmee"
            action = "follow_official_with_caution"
            level = "medium"
            consensus_score = min(consensus_score, 72)
            warnings.append("Le signal est cohérent, mais le backtesting ML ne permet pas de le renforcer fortement.")

        title = _status_text(label)
        if label == "signal_renforce":
            message = "Le ML shadow confirme le modèle officiel. Le signal Elo/Poisson est renforcé, sans garantie de résultat."
        elif label == "prudence_confirmee":
            message = "Le ML shadow va dans le même sens, mais la confiance impose une lecture prudente."
        elif label == "eviter":
            message = "Faible confiance, risque élevé et désaccord modèle: le match doit être évité dans l'analyse opérationnelle."
        else:
            message = "Le ML shadow contredit le modèle officiel. La prédiction Elo/Poisson reste primaire, mais le match demande une revue manuelle."

        explanation = [
            "La prédiction officielle reste produite par Elo/Poisson.",
            "Le moteur hybride compare ce signal au ML shadow et au backtesting disponible.",
            "Le résultat sert à renforcer, nuancer ou dégrader la lisibilité du match.",
        ]

    return {
        "engine_version": ENGINE_VERSION,
        "mode": MODE,
        "candidate_is_production": False,
        "official_prediction_stays_primary": True,
        "production_model_version": production_prediction.get("model_version") or PRODUCTION_MODEL_VERSION,
        "candidate_model_version": shadow_prediction.get("model_version") if shadow_available else None,
        "production_pick": production_pick,
        "shadow_pick": shadow_pick if shadow_available else None,
        "agreement": agreement,
        "consensus_score": consensus_score,
        "risk_adjustment": risk_adjustment,
        "decision_level": level,
        "decision_label": label,
        "action": action,
        "display_title": title,
        "display_message": message,
        "explanation": explanation,
        "warnings": warnings,
        "evidence": {
            "production_confidence": production_confidence,
            "shadow_confidence": shadow_confidence if shadow_available else None,
            "confidence_delta": confidence_delta,
            "disagreement_level": disagreement_level,
            "shadow_backtesting_status": shadow_backtesting.get("status"),
            "shadow_accuracy": shadow_accuracy,
            "production_accuracy": production_accuracy,
            "activation_recommendation": activation_recommendation,
        },
    }
