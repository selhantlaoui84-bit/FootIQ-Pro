from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except Exception:
        return default


def _add_alert(
    alerts: list[dict[str, Any]],
    seen: set[str],
    alert_id: str,
    level: str,
    title: str,
    message: str,
    area: str,
    recommended_action: str,
    action_href: str = "/admin",
    blocking: bool = False,
) -> None:
    if alert_id in seen:
        return

    seen.add(alert_id)
    alerts.append(
        {
            "id": alert_id,
            "level": level,
            "title": title,
            "message": message,
            "area": area,
            "recommended_action": recommended_action,
            "action_href": action_href,
            "blocking": blocking,
            "created_at": _now_iso(),
        }
    )


def build_admin_alerts_report(
    workflow_status: dict[str, Any] | None,
    refresh_status: dict[str, Any] | None,
    feature_summary: dict[str, Any] | None,
    dataset_quality: dict[str, Any] | None,
    ml_status: dict[str, Any] | None,
    shadow_summary: dict[str, Any] | None,
    shadow_backtesting: dict[str, Any] | None,
    monitoring_report: dict[str, Any] | None,
    governance_report: dict[str, Any] | None,
) -> dict[str, Any]:
    workflow_status = workflow_status or {}
    refresh_status = refresh_status or {}
    feature_summary = feature_summary or {}
    dataset_quality = dataset_quality or {}
    ml_status = ml_status or {}
    shadow_summary = shadow_summary or {}
    shadow_backtesting = shadow_backtesting or {}
    monitoring_report = monitoring_report or {}
    governance_report = governance_report or {}

    alerts: list[dict[str, Any]] = []
    seen: set[str] = set()

    latest_refresh_job = workflow_status.get("latest_refresh_job") or {}
    latest_feature_job = workflow_status.get("latest_feature_store_job") or {}

    if not refresh_status.get("last_refresh_at"):
        _add_alert(
            alerts,
            seen,
            "refresh_missing",
            "warning",
            "Actualisation non confirmée",
            "Aucune actualisation récente des données n'est disponible.",
            "refresh",
            "Lancer une actualisation des données depuis l'admin.",
            "/admin",
        )

    if latest_refresh_job.get("status") == "error":
        _add_alert(
            alerts,
            seen,
            "refresh_job_failed",
            "critical",
            "Actualisation échouée",
            latest_refresh_job.get("error") or "Le dernier job d'actualisation est en erreur.",
            "refresh",
            "Consulter l'erreur du job puis relancer l'actualisation.",
            "/admin",
            True,
        )

    if latest_feature_job.get("status") == "error":
        _add_alert(
            alerts,
            seen,
            "feature_store_job_failed",
            "critical",
            "Construction Feature Store échouée",
            latest_feature_job.get("error") or "Le dernier job Feature Store est en erreur.",
            "feature_store",
            "Consulter l'erreur puis relancer la construction du Feature Store.",
            "/admin",
            True,
        )

    snapshots_count = _int(feature_summary.get("snapshots_count"))
    with_target_count = _int(feature_summary.get("with_target_count"))

    if snapshots_count == 0:
        _add_alert(
            alerts,
            seen,
            "feature_store_empty",
            "critical",
            "Feature Store vide",
            "Aucun snapshot de variables n'est disponible pour préparer l'entraînement.",
            "feature_store",
            "Construire le Feature Store après actualisation des données.",
            "/admin",
            True,
        )

    if snapshots_count > 0 and with_target_count == 0:
        _add_alert(
            alerts,
            seen,
            "feature_store_no_training_rows",
            "warning",
            "Aucune ligne entraînable",
            "Le Feature Store existe mais ne contient pas de cible exploitable.",
            "feature_store",
            "Vérifier les matchs terminés et reconstruire le Feature Store.",
            "/admin",
        )

    safe_for_training = bool(dataset_quality.get("safe_for_training"))
    quality_reco = str(dataset_quality.get("recommendation") or "unknown")

    if not safe_for_training:
        level = "critical" if quality_reco in {"blocked_leakage_detected", "insufficient_data"} else "warning"
        _add_alert(
            alerts,
            seen,
            "dataset_quality_blocked",
            level,
            "Qualité dataset non validée",
            dataset_quality.get("recommendation_reason") or "Le dataset n'est pas encore jugé sûr pour l'entraînement.",
            "dataset",
            "Consulter le rapport qualité et reconstruire le Feature Store si nécessaire.",
            "/admin",
            level == "critical",
        )

    candidate = ml_status.get("latest_candidate") or {}
    candidate_status = str(candidate.get("status") or ml_status.get("status") or "not_trained")

    if candidate_status == "blocked":
        _add_alert(
            alerts,
            seen,
            "ml_training_blocked",
            "critical",
            "Entraînement ML bloqué",
            candidate.get("reason") or candidate.get("quality_recommendation_reason") or "Le quality gate bloque l'entraînement.",
            "ml",
            "Corriger la qualité dataset avant de relancer l'entraînement.",
            "/admin",
            True,
        )
    elif candidate_status not in {"ok", "trained", "success"}:
        _add_alert(
            alerts,
            seen,
            "ml_not_trained",
            "warning",
            "Modèle candidat non entraîné",
            "Le modèle ML candidat n'est pas encore exploitable.",
            "ml",
            "Valider le dataset puis entraîner le modèle candidat.",
            "/admin",
        )

    shadow_count = _int(shadow_summary.get("shadow_predictions_count"))
    if shadow_count < 50:
        _add_alert(
            alerts,
            seen,
            "shadow_low_volume",
            "warning",
            "Volume shadow insuffisant",
            f"Seulement {shadow_count} prédictions shadow sont disponibles.",
            "shadow",
            "Générer davantage de prédictions shadow.",
            "/admin",
        )

    shadow_eval = _int(shadow_backtesting.get("evaluated_matches"))
    if shadow_eval < 50:
        _add_alert(
            alerts,
            seen,
            "shadow_backtesting_low_sample",
            "warning",
            "Backtesting shadow insuffisant",
            f"Seulement {shadow_eval} matchs shadow sont évaluables.",
            "shadow",
            "Attendre plus de matchs terminés et relancer le backtesting shadow.",
            "/performance#backtesting",
        )

    trend = monitoring_report.get("trend_summary") or {}
    monitoring_status = str(trend.get("monitoring_status") or "unknown")

    if monitoring_status == "risk":
        _add_alert(
            alerts,
            seen,
            "monitoring_risk",
            "critical",
            "Monitoring modèle en risque",
            "Les indicateurs récents signalent une dégradation à surveiller immédiatement.",
            "monitoring",
            "Consulter le monitoring modèle et vérifier les performances récentes.",
            "/performance",
            True,
        )
    elif monitoring_status in {"insufficient_data", "watch", "unknown"}:
        _add_alert(
            alerts,
            seen,
            "monitoring_insufficient",
            "warning",
            "Monitoring à surveiller",
            f"Le statut monitoring est {monitoring_status}.",
            "monitoring",
            "Lire les métriques de suivi avant toute décision.",
            "/performance",
        )

    readiness = governance_report.get("promotion_readiness") or {}
    governance_level = str(readiness.get("level") or "unknown")

    if governance_level == "blocked":
        _add_alert(
            alerts,
            seen,
            "governance_blocked",
            "critical",
            "Gouvernance modèle bloquée",
            "La gouvernance empêche toute promotion du modèle candidat.",
            "governance",
            "Consulter les raisons de blocage dans la gouvernance modèle.",
            "/performance#model-governance",
            True,
        )

    production = governance_report.get("production_model") or {}
    candidate_model = governance_report.get("candidate_model") or {}
    if production.get("locked") and not candidate_model.get("candidate_is_production", False):
        _add_alert(
            alerts,
            seen,
            "production_locked_info",
            "info",
            "Production verrouillée",
            "Le modèle officiel reste verrouillé. Le candidat ML reste hors production.",
            "governance",
            "Aucune action requise : cette protection est volontaire.",
            "/admin",
            False,
        )

    level_order = {"critical": 0, "warning": 1, "info": 2}
    alerts.sort(key=lambda item: (level_order.get(item["level"], 9), item["area"], item["id"]))

    critical_count = sum(1 for item in alerts if item["level"] == "critical")
    warning_count = sum(1 for item in alerts if item["level"] == "warning")
    info_count = sum(1 for item in alerts if item["level"] == "info")

    if critical_count > 0:
        overall_status = "critical"
    elif warning_count > 0:
        overall_status = "warning"
    else:
        overall_status = "healthy"

    first_alert = alerts[0] if alerts else None
    next_best_action = {
        "label": first_alert["recommended_action"] if first_alert else "Aucune action prioritaire",
        "href": first_alert["action_href"] if first_alert else "/admin",
        "priority": first_alert["level"] if first_alert else "info",
    }

    return {
        "status": "ok",
        "generated_at": _now_iso(),
        "overall_status": overall_status,
        "alerts_count": len(alerts),
        "critical_count": critical_count,
        "warning_count": warning_count,
        "info_count": info_count,
        "alerts": alerts,
        "next_best_action": next_best_action,
        "policy": {
            "external_notifications_enabled": False,
            "automatic_model_promotion": False,
            "note": "Les alertes sont affichées dans l'admin sans notification externe.",
        },
    }
