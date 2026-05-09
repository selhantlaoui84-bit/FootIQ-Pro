from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _as_bool(value: Any) -> bool:
    return bool(value)


def _num(value: Any, default: int | float = 0):
    try:
        if value is None:
            return default
        return value
    except Exception:
        return default


def _candidate_from_ml_status(ml_status: dict[str, Any] | None) -> dict[str, Any]:
    ml_status = ml_status or {}
    candidate = ml_status.get("latest_candidate") or {}

    return {
        "version": candidate.get("model_version") or "ml-candidate-v1",
        "family": candidate.get("model_type") or "random_forest",
        "status": candidate.get("status") or ml_status.get("status") or "not_trained",
        "candidate_is_production": False,
        "rows_used": candidate.get("rows_used") or 0,
        "accuracy": candidate.get("accuracy"),
        "brier_score_1x2": candidate.get("brier_score_1x2"),
        "trained_at": candidate.get("trained_at"),
    }


def _gate(passed: bool, reason: str) -> dict[str, Any]:
    return {
        "passed": bool(passed),
        "reason": reason,
    }


def build_model_governance_report(
    model_metadata: dict[str, Any] | None,
    ml_status: dict[str, Any] | None,
    dataset_quality: dict[str, Any] | None,
    monitoring_report: dict[str, Any] | None,
    shadow_backtesting: dict[str, Any] | None,
    hybrid_engine_summary: dict[str, Any] | None,
    feedback_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    model_metadata = model_metadata or {}
    dataset_quality = dataset_quality or {}
    monitoring_report = monitoring_report or {}
    shadow_backtesting = shadow_backtesting or {}
    hybrid_engine_summary = hybrid_engine_summary or {}
    feedback_report = feedback_report or {}

    production_version = (
        model_metadata.get("current_model_version")
        or monitoring_report.get("production_model_version")
        or "elo-poisson-calibrated-v1"
    )

    candidate = _candidate_from_ml_status(ml_status)

    blockers: list[str] = []
    warnings: list[str] = []
    next_actions: list[str] = []
    score = 0

    dataset_safe = bool(dataset_quality.get("safe_for_training"))
    dataset_reco = dataset_quality.get("recommendation") or "unknown"
    dataset_reason = dataset_quality.get("recommendation_reason") or "Qualité dataset non vérifiée."

    if dataset_safe:
        score += 25
        dataset_gate = _gate(True, "Dataset compatible avec l'entraînement.")
    else:
        dataset_gate = _gate(False, dataset_reason)
        blockers.append("Qualité dataset non validée.")
        next_actions.append("Vérifier le rapport anti-leakage et reconstruire le Feature Store si nécessaire.")

    candidate_status = str(candidate.get("status") or "not_trained")
    rows_used = int(candidate.get("rows_used") or 0)
    candidate_accuracy = int(candidate.get("accuracy") or 0)
    candidate_brier = candidate.get("brier_score_1x2")
    candidate_log_loss = (ml_status.get("latest_candidate") or {}).get("log_loss") if ml_status else None
    trained = candidate_status in {"ok", "trained", "success"} or rows_used >= 30

    min_rows_ok = rows_used >= 30
    accuracy_ok = candidate_accuracy >= 35
    brier_ok = candidate_brier is not None and float(candidate_brier) <= 0.8

    if trained and min_rows_ok and accuracy_ok and brier_ok:
        score += 20
        training_gate = _gate(True, "Modèle candidat entraîné avec un volume exploitable.")
    else:
        training_gate = _gate(False, "Modèle candidat non entraîné ou métriques insuffisantes.")
        blockers.append("Modèle candidat non promouvable.")
        next_actions.append("Entraîner le modèle candidat après validation dataset.")

    shadow_evaluated = int(shadow_backtesting.get("evaluated_matches") or 0)
    shadow_accuracy = int(shadow_backtesting.get("shadow_accuracy") or 0)
    production_accuracy = int(shadow_backtesting.get("production_accuracy") or 0)

    if shadow_evaluated >= 50:
        score += 20
        if shadow_accuracy >= production_accuracy - 3:
            score += 10
            shadow_gate = _gate(True, "Shadow backtesting suffisant et candidat comparable au modèle officiel.")
        else:
            shadow_gate = _gate(False, "Shadow backtesting suffisant mais candidat inférieur au modèle officiel.")
            warnings.append("Le ML shadow reste inférieur au modèle officiel sur les matchs évalués.")
    else:
        shadow_gate = _gate(False, "Échantillon shadow insuffisant pour une décision robuste.")
        warnings.append("Shadow backtesting insuffisant : moins de 50 matchs évalués.")
        next_actions.append("Générer davantage de prédictions shadow puis attendre plus de matchs terminés.")

    production_log_loss = feedback_report.get("log_loss")
    production_brier = feedback_report.get("brier_score")
    production_roi = feedback_report.get("theoretical_roi")
    enough_tested = shadow_evaluated >= 50
    log_loss_improved = (
        candidate_log_loss is not None
        and production_log_loss is not None
        and float(candidate_log_loss) < float(production_log_loss)
    )
    roi_non_negative = production_roi is not None and float(production_roi) >= 0
    drift_delta = abs(shadow_accuracy - production_accuracy) if shadow_evaluated else None
    drift_ok = drift_delta is not None and drift_delta <= 20

    promotion_rules = {
        "minimum_rows": _gate(min_rows_ok, f"{rows_used} lignes utilisées, minimum 30."),
        "accuracy": _gate(accuracy_ok, f"Accuracy candidat {candidate_accuracy}%, seuil minimum 35%."),
        "log_loss": _gate(log_loss_improved, "Log loss candidat inférieur au modèle production."),
        "brier_score": _gate(brier_ok, f"Brier candidat {candidate_brier}."),
        "roi": _gate(roi_non_negative, "ROI théorique production non négatif sur l'échantillon évalué."),
        "drift": _gate(drift_ok, "Pas de dérive excessive entre shadow et production."),
        "tested_matches": _gate(enough_tested, f"{shadow_evaluated} matchs shadow évalués, minimum 50."),
    }

    if not all(rule["passed"] for rule in promotion_rules.values()):
        blockers.append("Critères stricts de promotion non satisfaits.")

    trend = monitoring_report.get("trend_summary") or {}
    monitoring_status = trend.get("monitoring_status") or "unknown"

    if monitoring_status in {"healthy", "watch"}:
        score += 15
        monitoring_gate = _gate(True, f"Monitoring modèle en statut {monitoring_status}.")
        if monitoring_status == "watch":
            warnings.append("Monitoring à surveiller.")
    else:
        monitoring_gate = _gate(False, f"Monitoring en statut {monitoring_status}.")
        if monitoring_status == "risk":
            blockers.append("Monitoring modèle en état risqué.")
        else:
            warnings.append("Monitoring insuffisant ou inconnu.")
        next_actions.append("Consulter le monitoring modèle.")

    hybrid_reco = hybrid_engine_summary.get("recommendation") or "unknown"

    if hybrid_reco in {"hybrid_advisory_active", "use_hybrid_advisory"}:
        score += 10
        hybrid_gate = _gate(True, "Moteur hybride actif en advisory.")
    else:
        hybrid_gate = _gate(False, "Moteur hybride pas encore suffisamment exploitable.")
        warnings.append("Signal hybride encore limité ou indisponible.")

    if blockers:
        level = "blocked"
    elif score >= 75:
        level = "review_only"
        warnings.append("Le score est bon, mais aucune promotion automatique n'est autorisée.")
    elif score >= 50:
        level = "watch"
    else:
        level = "not_ready"

    if not next_actions:
        next_actions.append("Continuer la surveillance et réaliser une revue manuelle avant toute décision.")

    return {
        "status": "ok",
        "generated_at": _now_iso(),
        "production_model": {
            "version": production_version,
            "family": model_metadata.get("family") or "elo_poisson",
            "status": "production",
            "locked": True,
            "description": model_metadata.get("description") or "Modèle officiel Elo/Poisson calibré.",
        },
        "candidate_model": candidate,
        "governance_gates": {
            "dataset_quality": {
                **dataset_gate,
                "recommendation": dataset_reco,
            },
            "training": training_gate,
            "shadow_backtesting": {
                **shadow_gate,
                "evaluated_matches": shadow_evaluated,
                "shadow_accuracy": shadow_accuracy,
                "production_accuracy": production_accuracy,
            },
            "monitoring": {
                **monitoring_gate,
                "status": monitoring_status,
            },
            "hybrid_review": {
                **hybrid_gate,
                "recommendation": hybrid_reco,
            },
        },
        "promotion_rules": promotion_rules,
        "production_feedback": {
            "evaluated_matches": feedback_report.get("evaluated_matches", 0),
            "accuracy": feedback_report.get("accuracy", 0),
            "log_loss": production_log_loss,
            "brier_score": production_brier,
            "theoretical_roi": production_roi,
        },
        "promotion_readiness": {
            "ready": False,
            "level": level,
            "score": min(100, max(0, score)),
            "blocking_reasons": blockers,
            "warnings": warnings,
            "next_actions": next_actions,
        },
        "version_history": [
            {
                "version": "elo-poisson-v1",
                "family": "elo_poisson",
                "status": "previous",
                "notes": "Modèle initial Elo/Poisson.",
            },
            {
                "version": "elo-poisson-calibrated-v1",
                "family": "elo_poisson",
                "status": "production",
                "notes": "Modèle officiel avec calibration conservatrice.",
            },
            {
                "version": candidate.get("version") or "ml-candidate-v1",
                "family": candidate.get("family") or "random_forest",
                "status": candidate_status,
                "notes": "Candidat ML entraîné sur Feature Store, observation uniquement.",
            },
        ],
        "policy": {
            "automatic_promotion": False,
            "requires_manual_review": True,
            "production_model_locked": True,
            "note": "Le modèle ML ne peut pas remplacer automatiquement le modèle officiel.",
        },
    }
