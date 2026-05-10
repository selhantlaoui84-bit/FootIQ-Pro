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
    candidate = ml_status.get("latest_candidate_model") or ml_status.get("latest_candidate") or {}

    return {
        "version": candidate.get("model_version") or "ml-candidate-v1",
        "family": candidate.get("model_type") or "random_forest",
        "status": candidate.get("status") or ml_status.get("status") or "not_trained",
        "candidate_is_production": False,
        "rows_used": candidate.get("rows_used") or 0,
        "accuracy": candidate.get("accuracy"),
        "log_loss": candidate.get("log_loss"),
        "brier_score_1x2": candidate.get("brier_score_1x2") or candidate.get("brier_score"),
        "trained_at": candidate.get("trained_at"),
    }


def _gate(passed: bool, reason: str) -> dict[str, Any]:
    return {
        "passed": bool(passed),
        "reason": reason,
    }


def _first_number(*values: Any) -> float | None:
    for value in values:
        try:
            if value is None or value == "":
                continue
            return float(value)
        except Exception:
            continue
    return None


def _candidate_from_versions(
    candidate_model_version: str | None,
    versions_report: dict[str, Any] | None,
    governance_report: dict[str, Any] | None,
) -> dict[str, Any] | None:
    versions_report = versions_report or {}
    versions = versions_report.get("versions") or []
    if candidate_model_version:
        for item in versions:
            if item.get("model_version") == candidate_model_version:
                return item
    candidate = versions_report.get("latest_candidate_model")
    if candidate:
        return candidate
    if governance_report:
        governance_candidate = governance_report.get("candidate_model") or {}
        version = governance_candidate.get("version")
        if version:
            return {
                "model_version": version,
                "status": governance_candidate.get("status") or "candidate",
                "rows_used": governance_candidate.get("rows_used") or 0,
                "accuracy": governance_candidate.get("accuracy"),
                "log_loss": governance_candidate.get("log_loss"),
                "brier_score": governance_candidate.get("brier_score_1x2"),
            }
    return None


def evaluate_model_promotion(
    candidate_model_version: str | None = None,
    *,
    versions_report: dict[str, Any] | None = None,
    governance_report: dict[str, Any] | None = None,
    shadow_backtesting_report: dict[str, Any] | None = None,
    minimum_evaluable_predictions: int = 30,
) -> dict[str, Any]:
    """Return a strict manual-promotion decision. It never promotes by itself."""
    versions_report = versions_report or {}
    governance_report = governance_report or {}
    shadow_backtesting_report = shadow_backtesting_report or {}

    candidate = _candidate_from_versions(candidate_model_version, versions_report, governance_report)
    production = versions_report.get("current_production_model") or {}
    production_from_governance = governance_report.get("production_model") or {}
    production_locked = bool(
        production.get("locked")
        or production_from_governance.get("locked")
        or (governance_report.get("policy") or {}).get("production_model_locked")
    )

    reasons: list[str] = []
    warnings: list[str] = []
    readiness = "promotion_ready"
    promotion_allowed = True

    if not candidate:
        reasons.append("Aucun modèle candidat disponible.")
        readiness = "blocked_no_candidate"
        promotion_allowed = False
    else:
        candidate_status = str(candidate.get("status") or "").lower()
        if candidate_status != "candidate":
            reasons.append(f"Le modèle {candidate.get('model_version')} n'est pas en status candidate.")
            readiness = "blocked_no_candidate"
            promotion_allowed = False
        if int(candidate.get("rows_used") or 0) <= 0:
            reasons.append("Le modèle candidat n'a aucune ligne d'entraînement validée.")
            readiness = "blocked_no_candidate"
            promotion_allowed = False
        if _first_number(candidate.get("accuracy"), (candidate.get("metrics") or {}).get("accuracy")) is None:
            reasons.append("Le modèle candidat n'a pas de métrique accuracy.")
            readiness = "manual_review_required"
            promotion_allowed = False

    shadow_total = int(shadow_backtesting_report.get("shadow_predictions_total") or 0)
    current_evaluable = int(
        shadow_backtesting_report.get("evaluable_predictions")
        or shadow_backtesting_report.get("evaluated_matches")
        or 0
    )
    metrics = shadow_backtesting_report.get("metrics") or {}
    comparison = shadow_backtesting_report.get("comparison") or {}

    if shadow_total <= 0:
        reasons.append("Aucune prédiction shadow disponible.")
        readiness = "blocked_no_shadow_backtesting"
        promotion_allowed = False
    elif current_evaluable < minimum_evaluable_predictions:
        reasons.append(
            f"Promotion bloquée : {current_evaluable} prédiction évaluable sur {minimum_evaluable_predictions} requises."
        )
        readiness = "blocked_insufficient_data"
        promotion_allowed = False

    delta_accuracy = _first_number(comparison.get("delta_accuracy"))
    delta_log_loss = _first_number(comparison.get("delta_log_loss"))
    delta_brier = _first_number(comparison.get("delta_brier_score"), comparison.get("delta_brier"))
    delta_roi = _first_number(comparison.get("delta_roi"))
    candidate_brier = _first_number(metrics.get("brier_score"), candidate.get("brier_score") if candidate else None)
    candidate_log_loss = _first_number(metrics.get("log_loss"), candidate.get("log_loss") if candidate else None)
    candidate_roi = _first_number(metrics.get("roi_theoretical"), candidate.get("roi_theoretical") if candidate else None)

    worse_accuracy = delta_accuracy is not None and delta_accuracy < 0
    worse_log_loss = delta_log_loss is not None and delta_log_loss > 0
    worse_brier = delta_brier is not None and delta_brier > 0
    worse_roi = delta_roi is not None and delta_roi < 0
    if current_evaluable >= minimum_evaluable_predictions and (worse_accuracy or worse_log_loss or worse_brier or worse_roi):
        reasons.append("Le candidat est inférieur à la production sur au moins une métrique clé.")
        readiness = "blocked_worse_than_production"
        promotion_allowed = False

    if candidate_brier is not None and candidate_brier > 0.8:
        reasons.append(f"Brier score candidat trop élevé ({candidate_brier}).")
        readiness = "blocked_worse_than_production"
        promotion_allowed = False
    if candidate_log_loss is not None and candidate_log_loss > 1.5:
        reasons.append(f"Log loss candidat trop élevé ({candidate_log_loss}).")
        readiness = "blocked_worse_than_production"
        promotion_allowed = False
    if candidate_roi is not None and candidate_roi < 0:
        reasons.append(f"ROI théorique candidat négatif ({candidate_roi}).")
        readiness = "blocked_worse_than_production"
        promotion_allowed = False

    governance_readiness = governance_report.get("promotion_readiness") or {}
    governance_level = str(governance_readiness.get("level") or "")
    if governance_level.startswith("blocked") or governance_level == "blocked":
        warnings.extend(governance_readiness.get("blocking_reasons") or [])
        if promotion_allowed:
            reasons.append("La gouvernance courante bloque la promotion.")
            readiness = governance_level
            promotion_allowed = False

    if production_locked:
        reasons.append("Le modèle production est verrouillé.")
        readiness = "blocked_production_locked"
        promotion_allowed = False

    if not reasons and not production:
        warnings.append("Aucune entrée production PostgreSQL n'existe encore; revue manuelle recommandée.")
        readiness = "manual_review_required"
        promotion_allowed = False

    if not reasons and promotion_allowed:
        readiness = "promotion_ready"

    return {
        "status": "ok",
        "promotion_allowed": promotion_allowed,
        "readiness": readiness,
        "candidate_model_version": (candidate or {}).get("model_version"),
        "production_model_version": production.get("model_version") or production_from_governance.get("version"),
        "reasons": reasons,
        "warnings": warnings,
        "requirements": {
            "minimum_evaluable_predictions": minimum_evaluable_predictions,
            "current_evaluable_predictions": current_evaluable,
            "shadow_predictions_total": shadow_total,
        },
        "metrics": {
            "delta_accuracy": delta_accuracy,
            "delta_log_loss": delta_log_loss,
            "delta_brier_score": delta_brier,
            "delta_roi": delta_roi,
            "candidate_log_loss": candidate_log_loss,
            "candidate_brier_score": candidate_brier,
            "candidate_roi_theoretical": candidate_roi,
        },
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
        ((ml_status or {}).get("current_production_model") or {}).get("model_version")
        or
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
    candidate_log_loss = candidate.get("log_loss") or ((ml_status.get("latest_candidate") or {}).get("log_loss") if ml_status else None)
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

    shadow_evaluated = int(shadow_backtesting.get("evaluable_predictions") or shadow_backtesting.get("evaluated_matches") or 0)
    shadow_accuracy = int(shadow_backtesting.get("shadow_accuracy") or (shadow_backtesting.get("metrics") or {}).get("accuracy") or 0)
    production_accuracy = int(shadow_backtesting.get("production_accuracy") or (shadow_backtesting.get("comparison") or {}).get("production_accuracy") or 0)
    shadow_recommendation = shadow_backtesting.get("recommendation") or {}
    comparison = shadow_backtesting.get("comparison") or {}

    if shadow_evaluated >= 30:
        score += 20
        if shadow_accuracy >= production_accuracy - 3:
            score += 10
            shadow_gate = _gate(True, "Shadow backtesting suffisant et candidat comparable au modèle officiel.")
        else:
            shadow_gate = _gate(False, "Shadow backtesting suffisant mais candidat inférieur au modèle officiel.")
            warnings.append("Le ML shadow reste inférieur au modèle officiel sur les matchs évalués.")
    else:
        shadow_gate = _gate(False, "Échantillon shadow insuffisant pour une décision robuste.")
        warnings.append("Shadow backtesting insuffisant : moins de 30 matchs évalués.")
        next_actions.append("Générer davantage de prédictions shadow puis attendre plus de matchs terminés.")

    production_log_loss = feedback_report.get("log_loss")
    production_brier = feedback_report.get("brier_score")
    production_roi = comparison.get("production_roi", feedback_report.get("theoretical_roi"))
    candidate_roi = (shadow_backtesting.get("metrics") or {}).get("roi_theoretical")
    enough_tested = shadow_evaluated >= 30
    log_loss_improved = (
        comparison.get("delta_log_loss") is not None
        and float(comparison.get("delta_log_loss")) <= 0
    )
    roi_non_negative = candidate_roi is not None and float(candidate_roi) >= 0
    drift_delta = abs(shadow_accuracy - production_accuracy) if shadow_evaluated else None
    drift_ok = drift_delta is not None and drift_delta <= 20

    promotion_rules = {
        "minimum_rows": _gate(min_rows_ok, f"{rows_used} lignes utilisées, minimum 30."),
        "accuracy": _gate(accuracy_ok, f"Accuracy candidat {candidate_accuracy}%, seuil minimum 35%."),
        "log_loss": _gate(log_loss_improved, "Log loss candidat inférieur au modèle production."),
        "brier_score": _gate(brier_ok, f"Brier candidat {candidate_brier}."),
        "roi": _gate(roi_non_negative, "ROI théorique production non négatif sur l'échantillon évalué."),
        "drift": _gate(drift_ok, "Pas de dérive excessive entre shadow et production."),
        "tested_matches": _gate(enough_tested, f"{shadow_evaluated} matchs shadow évalués, minimum 30."),
    }

    if not all(rule["passed"] for rule in promotion_rules.values()):
        if trained:
            warnings.append("Critères stricts de promotion non satisfaits : garder le candidat en shadow.")
            next_actions.append("Générer des prédictions shadow et accumuler au moins 30 matchs testés.")
        else:
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

    promotion_label = shadow_recommendation.get("status")
    if model_metadata.get("locked") is True or model_metadata.get("production_locked") is True:
        level = "production_locked"
        blockers.append("Modèle production verrouillé.")
    elif shadow_evaluated < 30:
        level = "blocked_insufficient_data"
    elif promotion_label in {"blocked_worse_than_production", "candidate_promising", "promotion_ready_manual_review"}:
        level = promotion_label
    elif blockers:
        level = "blocked"
    elif score >= 75:
        level = "promotion_ready_manual_review"
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
                "evaluable_predictions": shadow_evaluated,
                "pending_predictions": shadow_backtesting.get("pending_predictions", 0),
                "shadow_accuracy": shadow_accuracy,
                "production_accuracy": production_accuracy,
                "recommendation": shadow_recommendation,
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
        "shadow_backtesting": {
            "metrics": shadow_backtesting.get("metrics", {}),
            "comparison": comparison,
            "recommendation": shadow_recommendation,
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
