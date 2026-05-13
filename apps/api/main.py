import os
import time
import uuid
from collections import Counter
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any
import httpx
from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from data import repository
from data import runtime_store
from data.database import init_db
from data.mock_data import MATCHES, PERFORMANCE, TEAMS, get_match as get_mock_match
from data.mock_data import get_prediction as get_mock_prediction
from data.mock_data import get_team as get_mock_team
from services.admin_alerts import build_admin_alerts_report
from services.feature_store import build_feature_snapshots, build_feature_snapshots_detailed, summarize_feature_store
from services.data_quality import build_dataset_quality_report
from services.football_data_client import (
    get_configured_competitions_data,
    get_champions_league_matches,
    get_champions_league_teams,
    get_ligue1_matches,
    get_ligue1_teams,
)
from services.backtesting import calculate_backtest_report, calculate_snapshot_backtest, get_match_result
from services.shadow_backtesting import calculate_shadow_backtest_report
from services.elo_model import calculate_team_elos
from services.model_registry import get_model_metadata
from services.model_monitoring import build_monitoring_report
from services.model_governance import build_model_governance_report, evaluate_model_promotion
from services.feedback_engine import build_feedback_report
from services.calibration_engine import (
    CALIBRATION_VERSION,
    MINIMUM_CALIBRATION_SAMPLES,
    build_calibration_profile,
    calibrate_prediction,
    create_calibration_candidate,
)
from services.betting_assistant import analyze_prediction, generate_daily_assistant_brief, generate_match_assistant_summary
from services.billing_service import (
    billing_status as build_billing_status,
    create_checkout_session,
    create_customer_portal_session,
    handle_stripe_webhook,
)
from services.odds_engine import implied_probability_from_odds
from services.odds_provider import fetch_real_odds_for_matches, is_odds_configured
from services.value_bet_engine import build_value_bet_summary, evaluate_prediction_opportunity, rank_value_opportunities
from services.model_versioning import get_versions_report, list_model_versions, record_model_version
from services.pipeline_orchestrator import run_after_match_finished_pipeline, run_daily_learning_pipeline, run_hourly_data_pipeline, run_pipeline_step
from services.user_learning_engine import analyze_user_bets
from services.prediction_engine import generate_prediction_from_match
from services.prediction_engine import MODEL_VERSION
from services.ml_training import load_latest_candidate_metadata, load_training_rows_from_feature_snapshots, train_candidate_model
from services.ml_shadow import compare_shadow_to_production, generate_shadow_prediction


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    try:
        repository.ensure_saas_defaults()
    except Exception:
        pass
    yield


app = FastAPI(title="FootIQ Pro API", version="0.5.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _available_matches():
    return repository.get_matches() or runtime_store.get_matches() or MATCHES


def _available_teams():
    return repository.get_teams() or runtime_store.get_teams() or TEAMS


def _available_predictions():
    matches = _available_matches()
    stored_predictions = repository.get_predictions() or runtime_store.get_predictions()
    if stored_predictions and all(item.get("model_version") == MODEL_VERSION for item in stored_predictions):
        return stored_predictions

    elo_ratings = calculate_team_elos(matches)
    return [_prediction_for_match(match, matches, elo_ratings) for match in matches]


def _generated_predictions(matches: list[dict] | None = None) -> list[dict]:
    matches = matches if matches is not None else _available_matches()
    elo_ratings = calculate_team_elos(matches)
    return [_prediction_for_match(match, matches, elo_ratings) for match in matches]


def _prediction_storage_source() -> str:
    if repository.get_predictions():
        return "postgresql"
    return "generated_on_the_fly"


def _match_id(match: dict) -> str | None:
    value = match.get("match_id") or match.get("id") or match.get("slug")
    return str(value) if value is not None else None


def _count_by_status(matches: list[dict]) -> dict[str, int]:
    return dict(Counter(str(match.get("status") or "UNKNOWN").upper() for match in matches))


def _kickoff_values(matches: list[dict]) -> list[str]:
    return sorted(str(match.get("kickoff")) for match in matches if match.get("kickoff"))


def _has_score(match: dict) -> bool:
    return get_match_result(match) is not None or (
        match.get("score_full_time_home") is not None and match.get("score_full_time_away") is not None
    )


def _matches_structure_report(matches: list[dict] | None = None) -> dict[str, Any]:
    matches = matches if matches is not None else _available_matches()
    statuses = _count_by_status(matches)
    kickoffs = _kickoff_values(matches)
    finished = [match for match in matches if str(match.get("status", "")).upper() == "FINISHED"]
    finished_with_scores = [match for match in finished if get_match_result(match) is not None]
    matches_with_scores = [match for match in matches if _has_score(match)]
    raw_json_with_score = [
        match for match in matches
        if isinstance(match.get("raw_json"), dict)
        and isinstance((match.get("raw_json") or {}).get("score"), dict)
        and (((match.get("raw_json") or {}).get("score") or {}).get("fullTime") or {}).get("home") is not None
        and (((match.get("raw_json") or {}).get("score") or {}).get("fullTime") or {}).get("away") is not None
    ]

    competitions = Counter(str(match.get("competition") or "Unknown") for match in matches)

    def sample(match: dict) -> dict:
        return {
            "id": _match_id(match),
            "home_team": match.get("home_team"),
            "away_team": match.get("away_team"),
            "competition": match.get("competition"),
            "kickoff": match.get("kickoff"),
            "status": match.get("status"),
            "raw_status": match.get("raw_status"),
            "score_full_time_home": match.get("score_full_time_home"),
            "score_full_time_away": match.get("score_full_time_away"),
            "winner": match.get("winner"),
            "raw_json_score": (match.get("raw_json") or {}).get("score") if isinstance(match.get("raw_json"), dict) else None,
        }

    return {
        "total_matches": len(matches),
        "count_by_status": statuses,
        "first_kickoff": kickoffs[0] if kickoffs else None,
        "last_kickoff": kickoffs[-1] if kickoffs else None,
        "matches_with_scores": len(matches_with_scores),
        "finished_matches": len(finished),
        "finished_with_scores": len(finished_with_scores),
        "finished_without_scores": max(0, len(finished) - len(finished_with_scores)),
        "raw_json_with_score_count": len(raw_json_with_score),
        "sample_statuses": sorted(statuses.keys())[:20],
        "sample_matches_with_raw_json": [sample(match) for match in matches if isinstance(match.get("raw_json"), dict)][:5],
        "sample_matches_with_score_columns": [sample(match) for match in matches_with_scores[:5]],
        "competitions_breakdown": dict(competitions),
    }


def _find_match(match_id: str):
    return repository.get_match(match_id) or next(
        (
            item
            for item in runtime_store.get_matches()
            if item.get("id") == match_id or item.get("match_id") == match_id or item.get("slug") == match_id
        ),
        None,
    ) or get_mock_match(match_id)


def _find_team(team_id: str):
    return repository.get_team(team_id) or next(
        (item for item in runtime_store.get_teams() if item.get("id") == team_id or item.get("slug") == team_id),
        None,
    ) or get_mock_team(team_id)


def _find_prediction(match_id: str):
    prediction = repository.get_prediction(match_id)
    if prediction and prediction.get("model_version") == MODEL_VERSION:
        return prediction

    prediction = next(
        (
            item
            for item in runtime_store.get_predictions()
            if item.get("id") == match_id or item.get("match_id") == match_id or item.get("slug") == match_id
        ),
        None,
    )
    if prediction and prediction.get("model_version") == MODEL_VERSION:
        return prediction

    match = _find_match(match_id)
    if match is not None:
        matches = _available_matches()
        return _prediction_for_match(match, matches, calculate_team_elos(matches))

    return get_mock_prediction(match_id)


def _prediction_for_match(match: dict, all_matches: list[dict] | None = None, elo_ratings: dict | None = None):
    if "probabilities" in match and "confidence" in match and match.get("model_version") == MODEL_VERSION:
        return match

    return generate_prediction_from_match(match, all_matches or _available_matches(), elo_ratings)


def _shadow_summary_compact():
    try:
        rows = repository.get_ml_shadow_predictions(limit=2000)
    except Exception:
        rows = []

    available_count = 0
    disagreement_count = 0
    high_disagreement_count = 0

    for row in rows:
        shadow_prediction = row.get("shadow_prediction") or row.get("prediction") or {}
        comparison = row.get("comparison") or {}

        if shadow_prediction.get("available"):
            available_count += 1
        if comparison.get("same_pick") is False:
            disagreement_count += 1
        if comparison.get("disagreement_level") == "high":
            high_disagreement_count += 1

    return {
        "shadow_predictions_count": len(rows),
        "available_count": available_count,
        "disagreement_count": disagreement_count,
        "high_disagreement_count": high_disagreement_count,
        "candidate_is_production": False,
        "production_model_version": MODEL_VERSION,
    }


def _workflow_status_compact():
    refresh = _refresh_status()
    feature = _feature_summary()
    ml_status = _ml_status_compact()
    shadow_summary = _shadow_summary_compact()
    shadow_backtesting = calculate_shadow_backtest_report(
        _available_matches(),
        repository.get_ml_shadow_predictions(limit=2000),
    )
    refresh_storage = refresh.get("storage", "memory")
    refresh_matches_imported = refresh.get("matches_imported", 0)
    repository_matches_count = len(repository.get_matches())
    data_imported = refresh_matches_imported > 0 or repository_matches_count > 0
    structure = _matches_structure_report(_available_matches())
    finished_with_scores = structure.get("finished_with_scores", 0)
    feature_ready = feature.get("snapshots_count", 0) > 0
    latest_candidate_model = ml_status.get("latest_candidate_model") or {}
    candidate_rows_used = int(
        latest_candidate_model.get("rows_used")
        or (ml_status.get("latest_candidate") or {}).get("rows_used")
        or 0
    )
    candidate_status = str(ml_status.get("status") or latest_candidate_model.get("status") or "not_trained")
    candidate_trained = candidate_status in {"ok", "trained", "success", "candidate"} or candidate_rows_used >= 30
    shadow_generated = shadow_summary.get("shadow_predictions_count", 0) > 0
    shadow_evaluable = int(shadow_backtesting.get("evaluable_predictions") or shadow_backtesting.get("evaluated_matches") or 0)
    shadow_pending = int(shadow_backtesting.get("pending_predictions") or 0)
    shadow_backtesting_ready = shadow_evaluable > 0

    if candidate_trained and not shadow_generated:
        next_step = "generate_shadow_predictions"
    elif not data_imported:
        next_step = "refresh_data"
    elif not feature_ready:
        next_step = "build_feature_store" if finished_with_scores > 0 else "import_historical_results"
    elif not candidate_trained:
        next_step = "train_candidate_model"
    elif shadow_generated and shadow_pending > 0 and shadow_evaluable == 0:
        next_step = "wait_for_results"
    elif shadow_generated and shadow_evaluable < 30:
        next_step = "continue_shadow_testing"
    elif shadow_backtesting_ready:
        next_step = "review_governance"
    else:
        next_step = "ready_for_hybrid_review"

    try:
        latest_refresh_job = runtime_store.get_refresh_job_status()
    except Exception:
        latest_refresh_job = None

    try:
        latest_feature_store_job = runtime_store.get_feature_store_job_status()
    except Exception:
        latest_feature_store_job = None

    return {
        "refresh": {
            "data_imported": data_imported,
            "last_refresh_at": refresh.get("last_refresh_at"),
            "source": refresh.get("source", "mock"),
            "storage": refresh_storage,
            "matches_imported": refresh_matches_imported,
            "teams_imported": refresh.get("teams_imported", 0),
            "predictions_imported": refresh.get("predictions_imported", 0),
            "predictions_generated": refresh.get("predictions_generated", refresh.get("predictions_imported", 0)),
            "predictions_saved": refresh.get("predictions_saved", refresh.get("predictions_imported", 0)),
            "predictions_failed": refresh.get("predictions_failed", 0),
        },
        "feature_store": {
            "ready": feature_ready,
            "snapshots_count": feature.get("snapshots_count", 0),
            "training_rows_available": feature.get("with_target_count", 0),
            "target_coverage": feature.get("target_coverage", 0),
            "finished_with_scores": finished_with_scores,
        },
        "candidate_model": {
            "trained": candidate_trained,
            "status": "trained" if candidate_trained else candidate_status,
            "model_version": latest_candidate_model.get("model_version") or (ml_status.get("latest_candidate") or {}).get("model_version"),
            "accuracy": latest_candidate_model.get("accuracy") or (ml_status.get("latest_candidate") or {}).get("accuracy"),
        },
        "shadow_predictions": {
            "generated": shadow_generated,
            "count": shadow_summary.get("shadow_predictions_count", 0),
            "disagreement_count": shadow_summary.get("disagreement_count", 0),
        },
        "shadow_backtesting": {
            "ready": shadow_backtesting_ready,
            "evaluated_matches": shadow_evaluable,
            "evaluable_predictions": shadow_evaluable,
            "pending_predictions": shadow_pending,
            "invalid_predictions": int(shadow_backtesting.get("invalid_predictions") or 0),
            "shadow_accuracy": shadow_backtesting.get("shadow_accuracy", 0),
            "activation_recommendation": shadow_backtesting.get("activation_recommendation", "do_not_activate"),
            "recommendation": shadow_backtesting.get("recommendation"),
        },
        "latest_refresh_job": latest_refresh_job,
        "latest_feature_store_job": latest_feature_store_job,
        "cron": runtime_store.get_cron_status(),
        "next_step": next_step,
    }


def _admin_alerts_report():
    refresh_status = _refresh_status()
    feature_summary = _feature_summary_fast()
    ml_status = _ml_status_compact()
    shadow_backtesting = calculate_shadow_backtest_report(
        _available_matches(),
        repository.get_ml_shadow_predictions(limit=2000),
    )
    shadow_summary = _shadow_summary_compact()
    workflow_status = {
        "latest_refresh_job": runtime_store.get_refresh_job_status(),
        "latest_feature_store_job": runtime_store.get_feature_store_job_status(),
        "pipeline_stale_jobs": [job for job in repository.list_pipeline_jobs(limit=50) if job.get("status") == "stale"],
        "pipeline_running_jobs": repository.get_running_pipeline_jobs(),
    }
    dataset_quality = _dataset_quality_report(500)
    monitoring_report = {
        "trend_summary": {"monitoring_status": "healthy"},
        "alerts": [],
    }
    candidate = ml_status.get("latest_candidate") or {}
    candidate_ready = ml_status.get("status") in {"ok", "trained", "success"}
    governance_report = {
        "promotion_readiness": {
            "level": "blocked" if not candidate_ready else "review_required",
            "score": 0 if not candidate_ready else 60,
        },
        "production_model": {"locked": True},
        "candidate_model": {
            "candidate_is_production": False,
            "status": candidate.get("status") or ml_status.get("status"),
        },
    }

    return build_admin_alerts_report(
        workflow_status,
        refresh_status,
        feature_summary,
        dataset_quality,
        ml_status,
        shadow_summary,
        shadow_backtesting,
        monitoring_report,
        governance_report,
    )


def _admin_alerts_compact():
    report = _admin_alerts_report()
    return {
        "overall_status": report.get("overall_status", "unknown"),
        "alerts_count": report.get("alerts_count", 0),
        "critical_count": report.get("critical_count", 0),
        "warning_count": report.get("warning_count", 0),
        "next_best_action": report.get("next_best_action"),
    }


def _available_feature_snapshots():
    stored = repository.get_feature_snapshots()
    if stored:
        return stored
    return runtime_store.get_feature_snapshots()


def _feature_summary():
    snapshots = _available_feature_snapshots()
    summary = repository.get_feature_store_summary() if repository.get_feature_snapshots(limit=1) else summarize_feature_store(snapshots)
    return {**summary, "storage": "postgresql" if repository.get_feature_snapshots(limit=1) else "memory"}


def _feature_summary_fast():
    if repository.db_available() and repository.count_feature_snapshots() > 0:
        snapshots_count = repository.count_feature_snapshots()
        with_target_count = repository.count_feature_snapshots_with_target()
        return {
            "snapshots_count": snapshots_count,
            "with_target_count": with_target_count,
            "without_target_count": snapshots_count - with_target_count,
            "target_coverage": round((with_target_count / snapshots_count) * 100) if snapshots_count else 0,
            "storage": "postgresql",
            "model_versions": {},
            "feature_names": [],
        }
    return _feature_summary()


def _training_dataset(model_version: str | None = None, limit: int = 100):
    limit = max(1, min(int(limit or 100), 10000))
    rows = repository.get_training_dataset(model_version=model_version, limit=limit)
    if rows:
        return rows
    snapshots = _available_feature_snapshots()
    if model_version:
        snapshots = [item for item in snapshots if item.get("model_version") == model_version]
    return [item for item in snapshots if item.get("target")][:limit]


def _matches_for_shadow_generation(view: str, limit: int) -> list[dict]:
    normalized_view = (view or "upcoming").lower()
    matches = _available_matches()

    if normalized_view in {"upcoming", "a_venir"}:
        selected = [match for match in matches if str(match.get("status", "")).upper() != "FINISHED"]
    elif normalized_view in {"finished", "termines", "terminated"}:
        selected = [match for match in matches if str(match.get("status", "")).upper() == "FINISHED"]
    else:
        selected = matches

    return selected[: max(1, min(int(limit or 500), 2000))]

def _model_monitoring_report(periods: list[str] | None = None, shadow_limit: int = 2000):
    return build_monitoring_report(
        _available_matches(),
        _available_predictions(),
        repository.get_ml_shadow_predictions(limit=shadow_limit),
        periods=periods or ["7d", "30d", "90d", "all"],
    )

def _ml_status_compact():
    try:
        latest_candidate = repository.get_latest_ml_training_report()
    except Exception:
        latest_candidate = None

    if not latest_candidate:
        latest_candidate = load_latest_candidate_metadata()

    versions_report = get_versions_report()
    latest_registered_candidate = versions_report.get("latest_candidate_model")
    try:
        if not latest_registered_candidate:
            latest_registered_candidate = next(
                (
                    item
                    for item in versions_report.get("versions", [])
                    if item.get("status") in {"candidate", "shadow"}
                ),
                None,
            )
    except Exception:
        latest_registered_candidate = None

    latest_candidate = latest_candidate or {
        "status": "not_trained",
        "model_version": "ml-candidate-v1",
        "model_type": "random_forest",
        "rows_used": 0,
        "accuracy": None,
        "brier_score_1x2": None,
        "trained_at": None,
    }
    if latest_registered_candidate:
        latest_candidate["registry_entry"] = latest_registered_candidate

    return {
        "status": latest_candidate.get("status", "not_trained"),
        "latest_candidate": latest_candidate,
        "candidate_model_exists": latest_candidate.get("status") not in {"not_trained", None},
        "production_model_version": MODEL_VERSION,
        "current_production_model": versions_report.get("current_production_model"),
        "latest_candidate_model": latest_registered_candidate,
        "model_version_storage": versions_report.get("storage"),
        "candidate_is_production": False,
        "model_versions": versions_report.get("versions", []),
    }


def _dataset_quality_report(limit: int = 1000):
    rows = repository.get_training_dataset(limit=limit)

    if not rows:
        snapshots = _available_feature_snapshots()
        rows = [item for item in snapshots if item.get("target")][:limit]

    return build_dataset_quality_report(rows, limit=limit)


def _model_governance_report():
    model_metadata = get_model_metadata()
    ml_status = _ml_status_compact()
    dataset_quality = _dataset_quality_report(1000)
    monitoring_report = _model_monitoring_report(["7d", "30d", "90d", "all"], 2000)
    shadow_backtesting = calculate_shadow_backtest_report(
        _available_matches(),
        repository.get_ml_shadow_predictions(limit=2000),
    )
    feedback_report = build_feedback_report(_available_matches(), _available_predictions(), model_version=MODEL_VERSION)
    calibration_report = _calibration_report(model_version=MODEL_VERSION)

    try:
        hybrid_engine_summary = hybrid_engine_summary_report(limit=200, view="upcoming")
    except Exception:
        hybrid_engine_summary = {
            "recommendation": "insufficient_shadow_data",
            "reason": "Résumé hybride indisponible.",
        }

    report = build_model_governance_report(
        model_metadata,
        ml_status,
        dataset_quality,
        monitoring_report,
        shadow_backtesting,
        hybrid_engine_summary,
        feedback_report,
    )
    try:
        report["promotion_evaluation"] = evaluate_model_promotion(
            versions_report=get_versions_report(),
            governance_report=report,
            shadow_backtesting_report=shadow_backtesting,
        )
    except Exception as exc:
        report["promotion_evaluation"] = {
            "status": "error",
            "promotion_allowed": False,
            "readiness": "manual_review_required",
            "reasons": [str(exc)],
            "requirements": {"minimum_evaluable_predictions": 30, "current_evaluable_predictions": 0},
        }
    report["calibration"] = {
        "status": calibration_report.get("calibration_status"),
        "active_calibration_version": calibration_report.get("active_calibration_version"),
        "latest_calibration_version": calibration_report.get("latest_calibration_version"),
        "samples_count": calibration_report.get("samples_count"),
        "minimum_required": calibration_report.get("minimum_required"),
        "reliability_score": calibration_report.get("reliability_score"),
        "recommendation": calibration_report.get("recommendation"),
    }
    if calibration_report.get("calibration_status") == "overconfident":
        report.setdefault("warnings", []).append("Calibration : modèle potentiellement trop confiant.")
    return report


def _feature_csv(rows: list[dict]) -> str:
    feature_names = sorted({name for row in rows for name in (row.get("features") or {}).keys()})
    headers = [
        "match_id",
        "model_version",
        *feature_names,
        "target_result",
        "target_home_goals",
        "target_away_goals",
        "target_over_2_5",
        "target_btts",
    ]
    lines = [",".join(headers)]

    for row in rows:
        features = row.get("features") or {}
        target = row.get("target") or {}
        values = [
            row.get("match_id", ""),
            row.get("model_version", ""),
            *[features.get(name, "") for name in feature_names],
            target.get("result", ""),
            target.get("home_goals", ""),
            target.get("away_goals", ""),
            target.get("over_2_5", ""),
            target.get("btts", ""),
        ]
        escaped = [str(value).replace('"', '""') for value in values]
        lines.append(",".join(f'"{value}"' if "," in value else value for value in escaped))

    return "\n".join(lines) + "\n"


def _refresh_status():
    latest_log = repository.get_latest_refresh_log()
    stored_matches_count = repository.count_matches()
    stored_teams_count = repository.count_teams()
    stored_predictions_count = repository.count_predictions()

    if latest_log:
        source = latest_log.get("source", "mock")
        storage = "postgresql" if stored_matches_count else latest_log.get("storage", "postgresql")
        if storage == "postgresql" and stored_matches_count and source in {None, "", "mock"}:
            source = "football-data.org"
        predictions_saved = max(int(latest_log.get("predictions_saved") or 0), stored_predictions_count)
        predictions_generated = max(int(latest_log.get("predictions_generated") or 0), predictions_saved)
        return {
            "source": source,
            "storage": storage,
            "matches_imported": stored_matches_count,
            "teams_imported": stored_teams_count,
            "predictions_imported": predictions_saved,
            "predictions_generated": predictions_generated,
            "predictions_saved": predictions_saved,
            "predictions_failed": latest_log.get("predictions_failed", 0),
            "prediction_save_errors": latest_log.get("prediction_save_errors", []),
            "last_refresh_at": latest_log.get("last_refresh_at"),
            "warning": None if storage == "postgresql" else "PostgreSQL indisponible ou écriture échouée. Fallback mémoire utilisé.",
        }

    if stored_matches_count:
        return {
            "source": "football-data.org",
            "storage": "postgresql",
            "matches_imported": stored_matches_count,
            "teams_imported": stored_teams_count,
            "predictions_imported": stored_predictions_count,
            "predictions_generated": stored_predictions_count,
            "predictions_saved": stored_predictions_count,
            "predictions_failed": 0,
            "last_refresh_at": None,
            "warning": None,
        }

    status = runtime_store.get_refresh_status()
    return {
        "source": status.get("source", "mock"),
        "storage": status.get("storage", "memory"),
        "matches_imported": status.get("matches_imported", 0),
        "teams_imported": status.get("teams_imported", 0),
        "predictions_imported": status.get("predictions_imported", 0),
        "predictions_generated": status.get("predictions_imported", 0),
        "predictions_saved": 0 if status.get("storage") == "memory" else status.get("predictions_imported", 0),
        "predictions_failed": 0,
        "last_refresh_at": status.get("last_refresh_at"),
        "warning": status.get("warning") or (
            "PostgreSQL indisponible ou écriture échouée. Fallback mémoire utilisé."
            if status.get("storage") in {None, "memory", "mémoire"}
            else None
        ),
    }


def _dashboard_summary():
    if repository.db_available() and repository.count_matches() > 0:
        matches = []
        teams_count = repository.count_teams()
        total_matches = repository.count_matches()
        predictions_count = repository.count_predictions()
        predictions = []
    else:
        matches = _available_matches()
        teams_count = len(_available_teams())
        total_matches = len(matches)
        predictions = runtime_store.get_predictions()

    if not predictions and not repository.db_available():
        predictions = _generated_predictions(matches[:200])
    predictions_count = predictions_count if "predictions_count" in locals() else len(predictions)
    reliable = [item for item in predictions if (item.get("confidence") or {}).get("status") == "FIABLE"]
    medium = [item for item in predictions if (item.get("confidence") or {}).get("status") == "MOYEN"]
    avoid = [item for item in predictions if (item.get("confidence") or {}).get("status") in {"À ÉVITER", "A EVITER"}]
    traps = [item for item in predictions if (item.get("flags") or {}).get("trap_match")]
    average_risk_score = 0
    if predictions:
        average_risk_score = round(sum(item.get("risk_score", 0) for item in predictions) / len(predictions))
    status = _refresh_status()
    competitions = {}

    for match in matches:
        competition = match.get("competition", "Unknown")
        competitions[competition] = competitions.get(competition, 0) + 1

    average_confidence = 0
    if predictions:
        average_confidence = round(sum((item.get("confidence") or {}).get("score", 0) for item in predictions) / len(predictions))

    feature_summary = _feature_summary_fast()
    shadow_summary = _shadow_summary_compact()

    return {
        "total_matches": total_matches,
        "teams_count": teams_count,
        "predictions_count": predictions_count,
        "upcoming_matches_count": total_matches,
        "reliable_matches_count": len(reliable),
        "medium_matches_count": len(medium),
        "avoid_matches_count": len(avoid),
        "trap_matches_count": len(traps),
        "average_confidence": average_confidence,
        "average_risk_score": average_risk_score,
        "model_version": MODEL_VERSION,
        "current_model_version": MODEL_VERSION,
        "snapshots_count": feature_summary.get("snapshots_count", 0),
        "best_model_by_brier": None,
        "feature_snapshots_count": feature_summary["snapshots_count"],
        "training_rows_available": feature_summary["with_target_count"],
        "target_coverage": feature_summary["target_coverage"],
        "feature_store_ready": feature_summary["snapshots_count"] > 0,
        "evaluated_matches": 0,
        "result_accuracy": 0,
        "average_brier_score": None,
        "calibration_score": 0,
        "competitions_breakdown": competitions,
        "top_reliable_matches": sorted(
            predictions,
            key=lambda item: (item.get("confidence") or {}).get("score", 0),
            reverse=True,
        )[:5],
        "top_risky_matches": sorted(
            [item for item in predictions if (item.get("flags") or {}).get("risk") or (item.get("flags") or {}).get("trap_match")],
            key=lambda item: (item.get("confidence") or {}).get("score", 0),
        )[:5],
        "last_refresh_at": status.get("last_refresh_at"),
        "source": status.get("source", "mock"),
        "storage": status.get("storage", "memory"),
        "shadow_evaluated_matches": shadow_summary.get("shadow_predictions_count", 0),
        "shadow_accuracy": 0,
        "shadow_activation_recommendation": "do_not_activate",
    }


def _require_admin_key(x_admin_key: str | None):
    env = os.getenv("ENV", os.getenv("ENVIRONMENT", "development")).lower()
    admin_key = os.getenv("ADMIN_API_KEY")

    if not admin_key and env != "production":
        return

    if not admin_key or not x_admin_key:
        raise HTTPException(status_code=401, detail="Missing admin key")

    if x_admin_key != admin_key:
        raise HTTPException(status_code=401, detail="Invalid admin key")


def _is_production() -> bool:
    return os.getenv("ENV", os.getenv("ENVIRONMENT", "development")).lower() == "production"


def _require_refresh_configuration():
    missing = []
    if not os.getenv("DATABASE_URL"):
        missing.append("DATABASE_URL")
    if not os.getenv("FOOTBALL_DATA_API_KEY"):
        missing.append("FOOTBALL_DATA_API_KEY")

    if missing and _is_production():
        raise HTTPException(
            status_code=500,
            detail=f"Backend refresh misconfigured: missing {', '.join(missing)}",
        )


@app.get("/admin/alerts")
def admin_alerts():
    return _admin_alerts_report()


@app.get("/admin/workflow")
def admin_workflow():
    workflow = _workflow_status_compact()

    return {
        **workflow,
        "admin_alerts": _admin_alerts_compact(),
    }


@app.get("/admin/workflow-status")
def admin_workflow_status():
    workflow = _workflow_status_compact()

    return {
        **workflow,
        "admin_alerts": _admin_alerts_compact(),
    }

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/matches")
def list_matches():
    return _available_matches()


@app.get("/matches/{match_id}")
def match_detail(match_id: str):
    match = _find_match(match_id)
    if match is None:
        raise HTTPException(status_code=404, detail="Match not found")

    return match


@app.get("/predictions")
def list_predictions():
    return _available_predictions()


def _odds_lookup_for_predictions(predictions: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    lookup: dict[str, list[dict[str, Any]]] = {}
    for prediction in predictions:
        match_id = str(prediction.get("match_id") or prediction.get("id") or prediction.get("slug") or "")
        lookup[match_id] = repository.list_match_real_odds(match_id)
    return lookup


@app.get("/odds/match/{match_id}")
def match_odds(match_id: str):
    rows = repository.list_match_real_odds(match_id)
    if not rows:
        return {"status": "missing", "source": "real_provider", "match_id": match_id, "odds": [], "odds_count": 0, "detail": "Cote réelle non disponible pour ce match."}
    return {"status": "ok", "source": "real_provider", "match_id": match_id, "odds_count": len(rows), "odds": rows}


@app.get("/odds/prediction")
def prediction_odds(match_id: str, market: str = "1X2", selection: str = "HOME_WIN"):
    odds = repository.get_reference_real_odds(match_id, market, selection)
    if not odds:
        return {
            "status": "missing",
            "source": "real_provider",
            "match_id": match_id,
            "market": market,
            "selection": selection,
            "detail": "Cote réelle non disponible pour cette sélection.",
        }
    return {
        "status": "ok",
        "source": "real_provider",
        "match_id": match_id,
        "market": market,
        "selection": selection,
        "odds": {
            **odds,
            "implied_probability": odds.get("implied_probability") or implied_probability_from_odds(odds.get("odds_decimal")),
        },
    }


@app.post("/odds/refresh")
async def refresh_odds(request: Request, x_admin_key: str | None = Header(default=None, alias="X-Admin-Key")):
    _require_admin_key(x_admin_key)
    body = await request.json()
    match_ids = [str(item) for item in body.get("match_ids", []) if item]
    if not is_odds_configured():
        return {
            "status": "missing_provider_config",
            "saved_count": 0,
            "detail": "ODDS provider is not configured. Cote réelle non disponible.",
        }
    try:
        provider_report = fetch_real_odds_for_matches(match_ids)
    except Exception as exc:
        for match_id in match_ids:
            repository.mark_odds_stale(match_id)
        stale_count = sum(len(repository.list_match_real_odds(match_id)) for match_id in match_ids)
        return {
            "status": "provider_unavailable",
            "source": "real_provider",
            "saved_count": 0,
            "stale_count": stale_count,
            "detail": f"Provider de cotes réelles indisponible. Dernières cotes réelles marquées stale si disponibles. {exc}",
        }
    saved = [repository.save_real_bookmaker_odds(item) for item in provider_report.get("items", [])]
    saved = [item for item in saved if item]
    return {
        "status": provider_report.get("status", "ok"),
        "source": "real_provider",
        "saved_count": len(saved),
        "items_count": len(provider_report.get("items", [])),
    }


@app.get("/assistant/predictions")
def assistant_predictions(limit: int = Query(default=50, ge=1, le=500)):
    predictions = _available_predictions()[:limit]
    calibration = _calibration_report()
    context = {
        "odds_lookup": _odds_lookup_for_predictions(predictions),
        "calibration_status": calibration.get("calibration_status"),
        "data_quality_explanation": "Les recommandations combinent probabilité, cote, value et risque. Les résultats restent incertains.",
    }
    report = generate_daily_assistant_brief(predictions, context)
    return {**report, "storage": "postgresql" if repository.db_available() else "memory"}


@app.get("/assistant/match/{match_id}")
def assistant_match(match_id: str):
    match = _find_match(match_id)
    if match is None:
        raise HTTPException(status_code=404, detail="Match not found")
    predictions = _available_predictions()
    calibration = _calibration_report()
    context = {
        "odds_lookup": _odds_lookup_for_predictions(predictions),
        "calibration_status": calibration.get("calibration_status"),
        "data_quality_explanation": "Lecture informative : value, cote et risque doivent être vérifiés avant toute décision.",
    }
    return generate_match_assistant_summary(match, predictions, context)


@app.get("/assistant/daily-brief")
def assistant_daily_brief(limit: int = Query(default=30, ge=1, le=200)):
    return assistant_predictions(limit=limit)


def _value_bet_context(predictions: list[dict[str, Any]]) -> dict[str, Any]:
    calibration = _calibration_report()
    return {
        "odds_lookup": _odds_lookup_for_predictions(predictions),
        "calibration_status": calibration.get("calibration_status"),
    }


@app.get("/value-bets")
def value_bets(
    market: str | None = None,
    competition: str | None = None,
    min_ev: float | None = None,
    max_risk: int | None = None,
    include_watchlist: bool = Query(default=True),
    limit: int = Query(default=50, ge=1, le=500),
):
    predictions = _available_predictions()
    context = _value_bet_context(predictions)
    ranked = rank_value_opportunities(predictions, context)
    filtered = []
    for item in ranked:
        if market and str(item.get("market") or "").lower() != market.lower():
            continue
        if competition and str(item.get("competition") or "").lower() != competition.lower():
            continue
        if min_ev is not None and (item.get("expected_value") is None or float(item.get("expected_value")) < min_ev):
            continue
        if max_risk is not None and item.get("risk_score") is not None and int(item.get("risk_score")) > max_risk:
            continue
        if not include_watchlist and item.get("opportunity_level") == "watchlist":
            continue
        if item.get("value_status") in {"strong_value", "positive_value"} or include_watchlist:
            filtered.append(item)
        if len(filtered) >= limit:
            break
    summary = build_value_bet_summary(ranked)
    return {
        "status": "ok",
        "storage": "postgresql" if repository.db_available() else "memory",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "items_count": len(filtered),
        "items": filtered,
        "summary": summary,
    }


@app.get("/value-bets/match/{match_id}")
def match_value_bets(match_id: str):
    match = _find_match(match_id)
    predictions = [item for item in _available_predictions() if str(item.get("match_id") or item.get("id") or item.get("slug")) == match_id or str(item.get("slug")) == match_id]
    if not predictions and match is None:
        raise HTTPException(status_code=404, detail="Match not found")
    context = _value_bet_context(predictions)
    items = [evaluate_prediction_opportunity(prediction, context) for prediction in predictions]
    value_items = [item for item in items if item.get("is_value_bet")]
    avoid_items = [item for item in items if item.get("recommendation_type") == "avoid" or item.get("opportunity_level") == "avoid"]
    best = max(value_items, key=lambda item: item.get("opportunity_score") or 0, default=None)
    odds_rows = repository.list_match_real_odds(match_id)
    detail = "Cote réelle non disponible pour ce match." if not odds_rows else "Aucune value claire détectée sur les cotes disponibles."
    if best:
        detail = best.get("reason") or "Value bet détectée avec cote réelle."
    return {
        "status": "ok",
        "match_id": match_id,
        "home_team": (match or {}).get("home_team") or (predictions[0].get("home_team") if predictions else None),
        "away_team": (match or {}).get("away_team") or (predictions[0].get("away_team") if predictions else None),
        "items_count": len(items),
        "items": items,
        "best_value": best,
        "markets_to_watch": [item for item in items if item.get("opportunity_level") in {"excellent", "good", "watchlist"}],
        "markets_to_avoid": avoid_items,
        "real_odds_count": len(odds_rows),
        "missing_odds": [] if odds_rows else ["1X2"],
        "detail": detail,
        "summary": build_value_bet_summary(items),
    }


def _request_user_id(x_user_id: str | None = Header(default=None, alias="X-User-Id")) -> str:
    return x_user_id or "local-user"


def _bearer_token(request: Request) -> str | None:
    authorization = request.headers.get("authorization") or ""
    if not authorization.lower().startswith("bearer "):
        return None
    return authorization.split(" ", 1)[1].strip()


def _supabase_config() -> tuple[str | None, str | None]:
    url = os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL")
    key = os.getenv("SUPABASE_ANON_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")
    return (url.rstrip("/") if url else None, key)


def _validate_supabase_token(token: str | None) -> dict:
    if not token:
        raise HTTPException(status_code=401, detail="Authentication token required.")
    supabase_url, supabase_key = _supabase_config()
    if token.startswith("test:") and os.getenv("FOOTIQ_ALLOW_TEST_AUTH_TOKENS") == "1":
        email = token.split(":", 1)[1].strip().lower()
        return {"id": email, "email": email}
    if not supabase_url or not supabase_key:
        raise HTTPException(status_code=503, detail="Supabase auth is not configured on backend.")
    try:
        with httpx.Client(timeout=8) as client:
            response = client.get(
                f"{supabase_url}/auth/v1/user",
                headers={"Authorization": f"Bearer {token}", "apikey": supabase_key},
            )
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Supabase auth unavailable: {exc}") from exc
    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid authentication token.")
    payload = response.json()
    email = str(payload.get("email") or "").strip().lower()
    if not email:
        raise HTTPException(status_code=401, detail="Authenticated user email missing.")
    return {"id": payload.get("id") or email, "email": email, "raw": payload}


def _current_platform_user(request: Request) -> dict:
    identity = _validate_supabase_token(_bearer_token(request))
    user = repository.get_user_by_id_or_email(identity["email"])
    if not user:
        user = repository.get_or_create_user_by_email(identity["email"], display_name=identity["email"].split("@")[0])
    return user


def _require_platform_role(request: Request, allowed_roles: set[str]) -> dict:
    user = _current_platform_user(request)
    if user.get("status") != "active":
        raise HTTPException(status_code=403, detail="User account is not active.")
    if user.get("role") not in allowed_roles:
        raise HTTPException(status_code=403, detail="Insufficient platform role.")
    return user


def require_admin_role(request: Request) -> dict:
    return _require_platform_role(request, {repository.ROLE_ADMIN, repository.ROLE_SUPER_ADMIN})


def require_super_admin(request: Request) -> dict:
    return _require_platform_role(request, {repository.ROLE_SUPER_ADMIN})


@app.get("/billing/status")
def billing_status():
    overview = build_billing_status()
    overview["storage"] = "postgresql" if repository.db_available() else "memory"
    overview["plan_counts"] = repository.get_subscription_plan_counts()
    return overview


@app.get("/auth/me")
def auth_me(request: Request):
    user = _current_platform_user(request)
    subscription = repository.get_user_subscription(user.get("id") or user.get("email"))
    return {"status": "ok", "user": user, "role": user.get("role"), "subscription": subscription}


@app.post("/auth/onboarding")
async def auth_onboarding(request: Request):
    user = _current_platform_user(request)
    body = await request.json()
    completed = bool(body.get("completed", True))
    updated = repository.update_user_metadata(user["id"], {"onboarding_completed": completed}, actor_email=user.get("email") or "user")
    return {"status": "ok", "user": updated, "onboarding_completed": completed}


@app.get("/billing/subscription")
def billing_subscription(x_user_id: str | None = Header(default=None, alias="X-User-Id")):
    user_id = x_user_id or "local-user"
    subscription = repository.get_user_subscription(user_id)
    limits = {
        feature: repository.check_usage_limit(user_id, feature)
        for feature in ("prediction_view", "value_bet_view", "assistant_request", "bet_created", "performance_view")
    }
    return {
        "status": "ok",
        "user_id": user_id,
        "plan": subscription.get("plan", "free"),
        "subscription_status": subscription.get("status", "free"),
        "current_period_end": subscription.get("current_period_end"),
        "cancel_at_period_end": subscription.get("cancel_at_period_end", False),
        "limits": limits,
        "subscription": subscription,
    }


@app.post("/billing/create-checkout-session")
async def billing_create_checkout_session(request: Request, x_user_id: str | None = Header(default=None, alias="X-User-Id")):
    body = await request.json()
    user_id = x_user_id or body.get("user_id") or "local-user"
    plan = body.get("plan") or "premium"
    interval = body.get("interval") or "monthly"
    return create_checkout_session(str(user_id), str(plan), str(interval))


@app.post("/billing/create-portal-session")
def billing_create_portal_session(x_user_id: str | None = Header(default=None, alias="X-User-Id")):
    return create_customer_portal_session(x_user_id or "local-user")


@app.post("/billing/webhook")
async def billing_webhook(request: Request, stripe_signature: str | None = Header(default=None, alias="Stripe-Signature")):
    payload = await request.body()
    result = handle_stripe_webhook(payload, stripe_signature)
    if result.get("status") == "invalid_signature":
        raise HTTPException(status_code=400, detail=result.get("detail"))
    return result


@app.get("/super-admin/overview")
def super_admin_overview(request: Request):
    require_super_admin(request)
    return repository.build_super_admin_overview()


@app.get("/super-admin/users")
def super_admin_users(request: Request, limit: int = Query(default=100, ge=1, le=500)):
    require_super_admin(request)
    items = repository.list_saas_users(limit=limit)
    return {"status": "ok", "items_count": len(items), "items": items}


@app.get("/super-admin/users/{user_id}")
def super_admin_user_detail(user_id: str, request: Request):
    require_super_admin(request)
    user = repository.get_user_by_id_or_email(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"status": "ok", "user": user}


@app.patch("/super-admin/users/{user_id}")
async def super_admin_update_user(user_id: str, request: Request):
    actor = require_super_admin(request)
    body = await request.json()
    if not body.get("confirm"):
        raise HTTPException(status_code=400, detail="confirm: true required")
    try:
        user = repository.update_user_role_status(user_id, body.get("role"), body.get("status"), actor_email=actor.get("email") or "super_admin")
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"status": "ok", "user": user}


@app.post("/super-admin/users/{user_id}/promote")
async def super_admin_promote_user(user_id: str, request: Request):
    actor = require_super_admin(request)
    body = await request.json()
    if not body.get("confirm"):
        raise HTTPException(status_code=400, detail="confirm: true required")
    role = body.get("role") if body.get("role") in {repository.ROLE_ADMIN, repository.ROLE_SUPER_ADMIN} else repository.ROLE_ADMIN
    try:
        user = repository.update_user_role_status(user_id, role=role, status="active", actor_email=actor.get("email") or "super_admin")
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"status": "ok", "user": user}


@app.post("/super-admin/users/{user_id}/suspend")
async def super_admin_suspend_user(user_id: str, request: Request):
    actor = require_super_admin(request)
    body = await request.json()
    if not body.get("confirm"):
        raise HTTPException(status_code=400, detail="confirm: true required")
    try:
        user = repository.update_user_role_status(user_id, status="suspended", actor_email=actor.get("email") or "super_admin")
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"status": "ok", "user": user}


@app.post("/super-admin/users/{user_id}/restore")
async def super_admin_restore_user(user_id: str, request: Request):
    actor = require_super_admin(request)
    body = await request.json()
    if not body.get("confirm"):
        raise HTTPException(status_code=400, detail="confirm: true required")
    try:
        user = repository.update_user_role_status(user_id, status="active", actor_email=actor.get("email") or "super_admin")
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"status": "ok", "user": user}


@app.get("/super-admin/plans")
def super_admin_plans(request: Request):
    require_super_admin(request)
    items = repository.list_saas_plans()
    return {"status": "ok", "items_count": len(items), "items": items}


@app.post("/super-admin/plans")
async def super_admin_create_plan(request: Request):
    actor = require_super_admin(request)
    body = await request.json()
    if not body.get("confirm"):
        raise HTTPException(status_code=400, detail="confirm: true required")
    try:
        plan = repository.upsert_saas_plan(body, actor_email=actor.get("email") or "super_admin")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"status": "ok", "plan": plan}


@app.patch("/super-admin/plans/{plan_id}")
async def super_admin_update_plan(plan_id: str, request: Request):
    actor = require_super_admin(request)
    body = await request.json()
    if not body.get("confirm"):
        raise HTTPException(status_code=400, detail="confirm: true required")
    body["code"] = body.get("code") or plan_id
    try:
        plan = repository.upsert_saas_plan(body, actor_email=actor.get("email") or "super_admin")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"status": "ok", "plan": plan}


@app.get("/super-admin/subscriptions")
def super_admin_subscriptions(request: Request, limit: int = Query(default=100, ge=1, le=500)):
    require_super_admin(request)
    items = repository.list_saas_subscriptions(limit=limit)
    return {"status": "ok", "items_count": len(items), "items": items, "empty_detail": "Aucun abonnement réel enregistré." if not items else None}


@app.get("/super-admin/payments")
def super_admin_payments(request: Request, limit: int = Query(default=100, ge=1, le=500)):
    require_super_admin(request)
    items = repository.list_saas_payments(limit=limit)
    return {"status": "ok", "items_count": len(items), "items": items, "empty_detail": "Aucun paiement réel enregistré." if not items else None}


@app.get("/super-admin/entitlements")
def super_admin_entitlements(request: Request, limit: int = Query(default=200, ge=1, le=1000)):
    require_super_admin(request)
    items = repository.list_saas_entitlements(limit=limit)
    return {"status": "ok", "items_count": len(items), "items": items}


@app.patch("/super-admin/entitlements/{entitlement_id}")
async def super_admin_update_entitlement(entitlement_id: str, request: Request):
    actor = require_super_admin(request)
    body = await request.json()
    if not body.get("confirm"):
        raise HTTPException(status_code=400, detail="confirm: true required")
    try:
        entitlement = repository.update_entitlement(entitlement_id, body, actor_email=actor.get("email") or "super_admin")
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"status": "ok", "entitlement": entitlement}


@app.get("/super-admin/audit-log")
def super_admin_audit_log(request: Request, limit: int = Query(default=100, ge=1, le=500)):
    require_super_admin(request)
    items = repository.list_super_admin_audit_log(limit=limit)
    return {"status": "ok", "items_count": len(items), "items": items}


@app.get("/super-admin/revenue-summary")
def super_admin_revenue_summary(request: Request):
    require_super_admin(request)
    return repository.build_revenue_summary()


@app.get("/user-bets")
def user_bets(x_user_id: str | None = Header(default=None, alias="X-User-Id"), limit: int = Query(default=100, ge=1, le=500)):
    user_id = x_user_id or "local-user"
    items = repository.list_user_bets(user_id, limit=limit)
    return {"status": "ok", "user_id": user_id, "items_count": len(items), "items": items}


@app.post("/user-bets")
async def create_user_bet(request: Request, x_user_id: str | None = Header(default=None, alias="X-User-Id")):
    user_id = x_user_id or "local-user"
    body = await request.json()
    try:
        bet = repository.create_user_bet(user_id, body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"status": "ok", "user_id": user_id, "bet": bet}


@app.get("/user-bets/summary")
def user_bets_summary(x_user_id: str | None = Header(default=None, alias="X-User-Id")):
    user_id = x_user_id or "local-user"
    summary = repository.compute_user_betting_summary(user_id)
    insights = analyze_user_bets(user_id, repository.list_user_bets(user_id, limit=500))
    return {**summary, "user_id": user_id, "learning": insights}


@app.get("/user-bets/{bet_id}")
def user_bet_detail(bet_id: str, x_user_id: str | None = Header(default=None, alias="X-User-Id")):
    user_id = x_user_id or "local-user"
    bet = repository.get_user_bet(user_id, bet_id)
    if not bet:
        raise HTTPException(status_code=404, detail="Bet not found")
    return {"status": "ok", "user_id": user_id, "bet": bet}


@app.patch("/user-bets/{bet_id}")
async def update_user_bet(bet_id: str, request: Request, x_user_id: str | None = Header(default=None, alias="X-User-Id")):
    user_id = x_user_id or "local-user"
    body = await request.json()
    if body.get("status"):
        try:
            bet = repository.update_user_bet_status(user_id, bet_id, body["status"], body.get("result_profit"))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return {"status": "ok", "user_id": user_id, "bet": bet}
    return user_bet_detail(bet_id, x_user_id=user_id)


@app.post("/user-bets/{bet_id}/settle")
async def settle_user_bet_endpoint(bet_id: str, request: Request, x_user_id: str | None = Header(default=None, alias="X-User-Id")):
    user_id = x_user_id or "local-user"
    body = await request.json()
    try:
        bet = repository.settle_user_bet(user_id, bet_id, body.get("status"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not bet:
        raise HTTPException(status_code=404, detail="Bet not found")
    return {"status": "ok", "user_id": user_id, "bet": bet}



@app.get("/predictions/snapshots")
def prediction_snapshots():
    return repository.get_latest_prediction_snapshots(limit=100)

@app.get("/predictions/{match_id}")
def prediction_detail(match_id: str):
    prediction = _find_prediction(match_id)
    if prediction is None:
        raise HTTPException(status_code=404, detail="Prediction not found")

    return prediction


@app.get("/teams")
def list_teams():
    return _available_teams()


@app.get("/teams/{team_id}")
def team_detail(team_id: str):
    team = _find_team(team_id)
    if team is None:
        raise HTTPException(status_code=404, detail="Team not found")

    return team



@app.get("/features/summary")
def feature_summary():
    return _feature_summary()


@app.get("/features/dataset")
def feature_dataset(model_version: str | None = None, limit: int = Query(default=100, ge=1, le=500)):
    return _training_dataset(model_version=model_version, limit=limit)


@app.get("/features/export")
def feature_export(model_version: str | None = None):
    rows = repository.get_training_dataset(model_version=model_version, limit=5000)
    if not rows:
        rows = [item for item in _available_feature_snapshots() if item.get("target")]
        if model_version:
            rows = [item for item in rows if item.get("model_version") == model_version]
        rows = rows[:5000]
    return Response(content=_feature_csv(rows), media_type="text/csv")


@app.get("/features/quality-report")
def feature_quality_report(limit: int = Query(default=1000, ge=1, le=5000)):
    rows = repository.get_training_dataset(limit=limit)

    if not rows:
        snapshots = _available_feature_snapshots()
        rows = [item for item in snapshots if item.get("target")][:limit]

    return build_dataset_quality_report(rows, limit=limit)


@app.get("/models")
def models():
    metadata = get_model_metadata()
    versions = repository.get_model_versions()
    available_versions = sorted(set(versions + [metadata["current_model_version"], metadata["previous_model_version"]]))
    governance = _model_governance_report()
    readiness = governance.get("promotion_readiness", {})

    return {
        **metadata,
        "available_model_versions": available_versions,
        "governance_status": {
            "promotion_ready": False,
            "promotion_level": readiness.get("level", "not_ready"),
            "governance_score": readiness.get("score", 0),
            "blocking_reasons_count": len(readiness.get("blocking_reasons", [])),
        },
    }


@app.get("/models/governance")
def models_governance():
    return _model_governance_report()


@app.get("/models/versions")
def model_versions():
    report = get_versions_report()
    return {
        **report,
        "note": report.get("note") or "Model versions are append-only candidate/production/shadow registry entries.",
    }


@app.get("/models/promotion-audit")
def model_promotion_audit(
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
    limit: int = Query(default=50, ge=1, le=200),
):
    _require_admin_key(x_admin_key)
    repository.init_model_promotion_audit_schema()
    events = repository.list_model_promotion_audit(limit=limit)
    return {
        "status": "ok",
        "storage": "postgresql" if repository.db_available() else "unavailable",
        "events_count": len(events),
        "events": events,
    }


@app.post("/models/promote-candidate")
async def promote_candidate_model(
    request: Request,
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
):
    _require_admin_key(x_admin_key)
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    model_version = payload.get("model_version") or payload.get("modelVersion")
    confirm = payload.get("confirm") is True
    if not confirm:
        return {
            "status": "blocked",
            "detail": "Promotion bloquée : confirm=true est requis.",
            "governance": {
                "promotion_allowed": False,
                "readiness": "manual_review_required",
                "reasons": ["Confirmation explicite manquante."],
            },
        }

    versions_report = get_versions_report()
    shadow_report = calculate_shadow_backtest_report(
        _available_matches(),
        repository.get_ml_shadow_predictions(limit=5000),
    )
    governance_report = _model_governance_report()
    evaluation = evaluate_model_promotion(
        model_version,
        versions_report=versions_report,
        governance_report=governance_report,
        shadow_backtesting_report=shadow_report,
    )
    previous_production = repository.get_current_production_model()
    previous_version = (previous_production or {}).get("model_version")

    if not evaluation.get("promotion_allowed"):
        audit = repository.log_model_promotion_event(
            action="blocked",
            candidate_model_version=model_version,
            previous_production_model_version=previous_version,
            governance=evaluation,
            result="blocked",
            detail="Promotion bloquée par la gouvernance.",
        )
        return {
            "status": "blocked",
            "detail": "Promotion bloquée par la gouvernance.",
            "governance": evaluation,
            "audit_id": (audit or {}).get("id"),
        }

    promoted = repository.promote_model_version(model_version)
    if not promoted:
        audit = repository.log_model_promotion_event(
            action="blocked",
            candidate_model_version=model_version,
            previous_production_model_version=previous_version,
            governance=evaluation,
            result="error",
            detail="Promotion impossible : modèle candidat introuvable ou PostgreSQL indisponible.",
        )
        return {
            "status": "blocked",
            "detail": "Promotion impossible : modèle candidat introuvable ou PostgreSQL indisponible.",
            "governance": evaluation,
            "audit_id": (audit or {}).get("id"),
        }

    audit = repository.log_model_promotion_event(
        action="promote",
        candidate_model_version=model_version,
        previous_production_model_version=previous_version,
        new_production_model_version=promoted.get("model_version"),
        governance=evaluation,
        result="success",
        detail="Modèle candidat promu manuellement en production.",
    )
    return {
        "status": "success",
        "promoted_model_version": promoted.get("model_version"),
        "previous_production_model_version": previous_version,
        "archived_previous_production": bool(previous_version and previous_version != promoted.get("model_version")),
        "audit_id": (audit or {}).get("id"),
        "new_production_model": promoted,
        "governance": evaluation,
    }


@app.post("/models/rollback-production")
async def rollback_production_model(
    request: Request,
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
):
    _require_admin_key(x_admin_key)
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    target_version = payload.get("target_model_version") or payload.get("targetModelVersion")
    confirm = payload.get("confirm") is True
    if not confirm:
        return {
            "status": "blocked",
            "detail": "Rollback bloqué : confirm=true est requis.",
        }

    target = repository.get_model_version(target_version)
    current = repository.get_current_production_model()
    current_version = (current or {}).get("model_version")
    if not target or target.get("status") not in {"archived", "production"}:
        audit = repository.log_model_promotion_event(
            action="blocked",
            previous_production_model_version=current_version,
            new_production_model_version=target_version,
            result="blocked",
            detail="Rollback bloqué : cible introuvable ou non restaurable.",
        )
        return {
            "status": "blocked",
            "detail": "Rollback bloqué : cible introuvable ou non restaurable.",
            "audit_id": (audit or {}).get("id"),
        }
    if target.get("model_version") == current_version:
        return {
            "status": "blocked",
            "detail": "Rollback bloqué : la cible est déjà en production.",
        }

    restored = repository.promote_model_version(target.get("model_version"))
    audit = repository.log_model_promotion_event(
        action="rollback",
        previous_production_model_version=current_version,
        new_production_model_version=(restored or {}).get("model_version"),
        result="success" if restored else "error",
        detail="Rollback manuel exécuté." if restored else "Rollback impossible.",
    )
    if not restored:
        return {
            "status": "blocked",
            "detail": "Rollback impossible : PostgreSQL indisponible ou cible introuvable.",
            "audit_id": (audit or {}).get("id"),
        }

    return {
        "status": "success",
        "production_model_version": restored.get("model_version"),
        "previous_production_model_version": current_version,
        "audit_id": (audit or {}).get("id"),
        "new_production_model": restored,
    }


@app.get("/models/comparison")
def model_comparison():
    return calculate_snapshot_backtest(_available_matches(), repository.get_prediction_snapshots())


@app.get("/learning/feedback")
def learning_feedback(model_version: str | None = None):
    return build_feedback_report(_available_matches(), _available_predictions(), model_version=model_version)


def _stored_calibration_profile(calibration: dict | None) -> dict | None:
    if not calibration:
        return None
    factors = calibration.get("factors") or {}
    metrics = calibration.get("metrics") or {}
    global_factor = round(1 + float(factors.get("global_correction") or 0), 3)
    return {
        **calibration,
        "global_calibration_factor": global_factor,
        "expected_calibration_error": metrics.get("expected_calibration_error"),
        "mean_absolute_calibration_error": metrics.get("mean_absolute_calibration_error"),
        "max_calibration_gap": metrics.get("max_calibration_gap"),
        "overconfidence_score": metrics.get("overconfidence_score"),
        "underconfidence_score": metrics.get("underconfidence_score"),
        "reliability_score": metrics.get("reliability_score"),
        "calibration_status": metrics.get("calibration_status") or calibration.get("status"),
    }


def _calibration_report(model_version: str | None = None) -> dict[str, Any]:
    profile = build_calibration_profile(_available_matches(), _available_predictions(), model_version=model_version)
    active = _stored_calibration_profile(repository.get_active_calibration())
    latest = _stored_calibration_profile(repository.get_latest_calibration())
    calibrations = repository.list_model_calibrations(limit=20)
    latest_version = (latest or {}).get("calibration_version") or profile.get("calibration_version")
    active_version = (active or {}).get("calibration_version")
    return {
        **profile,
        "storage": "postgresql" if repository.db_available() else "memory",
        "active_calibration_version": active_version,
        "latest_calibration_version": latest_version,
        "active_calibration": active,
        "latest_calibration": latest,
        "calibrations_count": len(calibrations),
        "calibrations": calibrations,
    }


@app.get("/learning/calibration")
def learning_calibration(model_version: str | None = None):
    return _calibration_report(model_version=model_version)


@app.post("/learning/calibration/recompute")
async def recompute_learning_calibration(
    request: Request,
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
):
    _require_admin_key(x_admin_key)
    payload = await request.json()
    model_version = payload.get("model_version") or payload.get("modelVersion")
    method = payload.get("method") or "bucket_scaling"
    source = payload.get("source") or "production_feedback"
    report = build_calibration_profile(_available_matches(), _available_predictions(), model_version=model_version)
    candidate = create_calibration_candidate(report, source=source, method=method)
    saved = repository.create_model_calibration(candidate)
    status = "ok" if saved and saved.get("status") != "insufficient_data" else "insufficient_data"
    return {
        **report,
        "status": status,
        "storage": "postgresql" if repository.db_available() else "memory",
        "calibration_record": saved,
        "latest_calibration_version": (saved or {}).get("calibration_version") or report.get("calibration_version"),
        "active_calibration_version": (repository.get_active_calibration() or {}).get("calibration_version"),
    }


@app.post("/learning/calibration/activate")
async def activate_learning_calibration(
    request: Request,
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
):
    _require_admin_key(x_admin_key)
    payload = await request.json()
    calibration_version = payload.get("calibration_version") or payload.get("calibrationVersion")
    if payload.get("confirm") is not True:
        return {
            "status": "blocked",
            "detail": "Activation bloquée : confirm=true est obligatoire.",
        }
    calibration = repository.get_model_calibration(calibration_version)
    if not calibration:
        return {"status": "blocked", "detail": "Calibration introuvable."}
    if calibration.get("status") == "insufficient_data" or int(calibration.get("samples_count") or 0) < MINIMUM_CALIBRATION_SAMPLES:
        return {
            "status": "blocked",
            "detail": "Données insuffisantes pour activer cette calibration.",
            "calibration": calibration,
        }
    activated = repository.activate_calibration_version(calibration_version)
    if not activated:
        return {"status": "error", "detail": "Activation de la calibration impossible."}
    return {
        "status": "success",
        "active_calibration_version": activated.get("calibration_version"),
        "calibration": activated,
    }


@app.get("/learning/user-profile/{user_id}")
def user_learning_profile(user_id: str):
    return analyze_user_bets(user_id, [])


@app.get("/learning/monitoring")
def learning_monitoring():
    alerts: list[str] = []
    versions_report = get_versions_report()
    feedback_report = build_feedback_report(_available_matches(), _available_predictions(), model_version=MODEL_VERSION)
    calibration_report = _calibration_report(model_version=MODEL_VERSION)
    ml_status = _ml_status_compact()
    shadow_report = calculate_shadow_backtest_report(
        _available_matches(),
        repository.get_ml_shadow_predictions(limit=2000),
    )

    try:
        feature_summary = _feature_summary_fast()
        feature_store_status = "ok" if feature_summary.get("snapshots_count", 0) > 0 else "empty"
        if feature_store_status == "empty":
            alerts.append("Feature Store vide ou non disponible.")
    except Exception as exc:
        feature_summary = {"status": "error", "detail": str(exc)}
        feature_store_status = "error"
        alerts.append("Feature Store indisponible.")

    production_model = versions_report.get("current_production_model") or {}
    candidate_model = versions_report.get("latest_candidate_model") or {}
    governance_report = _model_governance_report()
    promotion_evaluation = evaluate_model_promotion(
        (candidate_model or {}).get("model_version"),
        versions_report=versions_report,
        governance_report=governance_report,
        shadow_backtesting_report=shadow_report,
    )
    last_promotion = repository.get_latest_model_promotion_event("promote")
    last_rollback = repository.get_latest_model_promotion_event("rollback")
    if versions_report.get("storage") != "postgresql":
        alerts.append("Registre model_versions en fallback fichier.")
    if not candidate_model:
        alerts.append("Aucun modèle candidat enregistré.")

    shadow_total = int(shadow_report.get("shadow_predictions_total") or 0)
    shadow_evaluable = int(shadow_report.get("evaluable_predictions") or shadow_report.get("evaluated_matches") or 0)
    shadow_pending = int(shadow_report.get("pending_predictions") or 0)
    shadow_invalid = int(shadow_report.get("invalid_predictions") or 0)
    if not candidate_model and feature_store_status in {"empty", "error"}:
        next_best_action = {"label": "Construire le Feature Store", "href": "/admin"}
    elif not candidate_model:
        next_best_action = {"label": "Entraîner un modèle candidat", "href": "/admin"}
    elif shadow_total == 0:
        next_best_action = {"label": "Générer les prédictions shadow", "href": "/admin"}
    elif shadow_pending > 0 and shadow_evaluable == 0:
        next_best_action = {"label": "Attendre les résultats des matchs", "href": "/admin"}
    elif promotion_evaluation.get("readiness") == "blocked_production_locked":
        next_best_action = {"label": "Production verrouillée", "href": "/admin"}
    elif shadow_evaluable < 30:
        next_best_action = {"label": "Continuer le shadow testing", "href": "/admin"}
    elif promotion_evaluation.get("promotion_allowed"):
        next_best_action = {"label": "Revue manuelle de promotion", "href": "/admin"}
    else:
        next_best_action = {"label": "Continuer le shadow testing", "href": "/admin"}

    return {
        "status": "ok" if not alerts else "warning",
        "storage": versions_report.get("storage"),
        "feedback_status": feedback_report.get("status"),
        "calibration_status": calibration_report.get("calibration_status") or calibration_report.get("status"),
        "model_versions_status": versions_report.get("status"),
        "governance_status": "candidate_available" if candidate_model or ml_status.get("candidate_model_exists") else "no_candidate",
        "feature_store_status": feature_store_status,
        "latest_feedback_at": feedback_report.get("generated_at"),
        "active_calibration_version": calibration_report.get("active_calibration_version"),
        "latest_calibration_version": calibration_report.get("latest_calibration_version") or calibration_report.get("calibration_version"),
        "calibration_samples_count": calibration_report.get("samples_count"),
        "calibration_minimum_required": calibration_report.get("minimum_required"),
        "calibration_gap": calibration_report.get("max_calibration_gap"),
        "reliability_score": calibration_report.get("reliability_score"),
        "model_versions_count": versions_report.get("versions_count", 0),
        "production_model_version": production_model.get("model_version") or MODEL_VERSION,
        "latest_candidate_model_version": candidate_model.get("model_version"),
        "shadow_backtesting_status": shadow_report.get("backtesting_status") or shadow_report.get("status"),
        "shadow_predictions_total": shadow_total,
        "shadow_evaluable_predictions": shadow_evaluable,
        "shadow_pending_predictions": shadow_pending,
        "shadow_invalid_predictions": shadow_invalid,
        "latest_shadow_backtesting_at": shadow_report.get("generated_at"),
        "governance_recommendation": shadow_report.get("recommendation"),
        "promotion_readiness": promotion_evaluation.get("readiness"),
        "promotion_allowed": promotion_evaluation.get("promotion_allowed"),
        "promotion_blocking_reasons": promotion_evaluation.get("reasons", []),
        "last_promotion_at": (last_promotion or {}).get("created_at"),
        "last_rollback_at": (last_rollback or {}).get("created_at"),
        "alerts": alerts,
        "next_best_action": next_best_action,
        "feature_store": feature_summary,
    }


@app.get("/debug/finished-matches")
def debug_finished_matches():
    matches = _available_matches()
    finished = [match for match in matches if str(match.get("status", "")).upper() == "FINISHED"]
    finished_with_scores = [match for match in finished if get_match_result(match) is not None]
    sample = [
        {
            "id": match.get("id") or match.get("match_id") or match.get("slug"),
            "home_team": match.get("home_team"),
            "away_team": match.get("away_team"),
            "status": match.get("status"),
            "score_full_time_home": match.get("score_full_time_home"),
            "score_full_time_away": match.get("score_full_time_away"),
            "winner": match.get("winner"),
        }
        for match in finished[:5]
    ]

    return {
        "finished_matches": len(finished),
        "finished_with_scores": len(finished_with_scores),
        "sample": sample,
        "warning": "Aucun match FINISHED trouvé." if not finished else None,
        "hint": "Vérifiez /debug/matches-structure et count_by_status pour voir les statuts réellement importés.",
    }


@app.get("/debug/matches-structure")
def debug_matches_structure():
    return _matches_structure_report()


@app.get("/debug/predictions-structure")
def debug_predictions_structure():
    stored_predictions = repository.get_predictions()
    matches = _available_matches()
    generated_predictions = _generated_predictions(matches)
    missing_required = sum(
        1
        for prediction in stored_predictions
        if not (prediction.get("id") and prediction.get("match_id") and prediction.get("slug") and prediction.get("model_version"))
    )
    last_refresh_log = repository.get_latest_refresh_log()
    table_count = repository.count_predictions()
    generated_count = len(generated_predictions)

    return {
        "predictions_table_count": table_count,
        "sample_prediction_db": repository.sample_prediction_db(),
        "generated_predictions_count": generated_count,
        "sample_generated_prediction": generated_predictions[0] if generated_predictions else None,
        "missing_required_fields_count": missing_required,
        "last_refresh_log": last_refresh_log,
        "prediction_save_status_from_last_refresh": {
            "predictions_generated": (last_refresh_log or {}).get("predictions_generated", 0),
            "predictions_saved": (last_refresh_log or {}).get("predictions_saved", 0),
            "predictions_failed": (last_refresh_log or {}).get("predictions_failed", 0),
            "errors": (last_refresh_log or {}).get("prediction_save_errors", []),
        } if last_refresh_log else None,
        "warning": (
            "Les prédictions sont générées par /predictions mais la table PostgreSQL predictions est vide."
            if table_count == 0 and generated_count > 0
            else None
        ),
    }


def _feature_store_diagnostics(matches: list[dict] | None = None, predictions: list[dict] | None = None) -> dict[str, Any]:
    matches = matches if matches is not None else _available_matches()
    predictions = predictions if predictions is not None else repository.get_predictions()
    generated_predictions = _generated_predictions(matches)
    predictions_for_build = predictions or generated_predictions
    storage_detected = "postgresql" if repository.get_matches() else "memory"

    finished = [match for match in matches if str(match.get("status") or "").upper() == "FINISHED"]
    finished_with_scores = [match for match in finished if get_match_result(match) is not None]
    feature_snapshots = _available_feature_snapshots()

    prediction_match_ids = {str(item.get("match_id")) for item in predictions_for_build if item.get("match_id") is not None}
    prediction_ids = {str(item.get("id")) for item in predictions_for_build if item.get("id") is not None}
    prediction_slugs = {str(item.get("slug")) for item in predictions_for_build if item.get("slug") is not None}
    join_on_match_id = 0
    join_on_id = 0
    join_on_slug = 0
    for match in finished_with_scores:
        if match.get("match_id") is not None and str(match.get("match_id")) in prediction_match_ids:
            join_on_match_id += 1
        if match.get("id") is not None and str(match.get("id")) in prediction_ids:
            join_on_id += 1
        if match.get("slug") is not None and str(match.get("slug")) in prediction_slugs:
            join_on_slug += 1

    elo_ratings = calculate_team_elos(matches)
    detailed = build_feature_snapshots_detailed(
        matches,
        predictions_for_build,
        target_matches=matches,
        prediction_factory=lambda match: _prediction_for_match(match, matches, elo_ratings),
    )
    snapshots = detailed.get("snapshots", [])
    first_snapshot = snapshots[0] if snapshots else None
    last_save_report = repository.get_last_feature_snapshot_save_report()

    return {
        "matches_total": len(matches),
        "finished_matches": len(finished),
        "finished_with_scores": len(finished_with_scores),
        "predictions_total": len(predictions),
        "generated_predictions_count": len(generated_predictions),
        "feature_snapshots_total": len(feature_snapshots),
        "feature_snapshots_total_from_db": repository.count_feature_snapshots(),
        "feature_snapshots_schema_ok": repository.feature_snapshots_schema_ok(),
        "last_save_report": last_save_report,
        "sample_snapshot_to_save": first_snapshot,
        "save_error_sample": (last_save_report.get("errors") or [])[:5],
        "join_on_match_id_count": join_on_match_id,
        "join_on_id_count": join_on_id,
        "join_on_slug_count": join_on_slug,
        "trainable_candidates_count": len(snapshots),
        "first_trainable_candidate_sample": detailed.get("first_trainable_candidate_sample"),
        "rejection_reasons_count": detailed.get("rejection_reasons_count", {}),
        "sample_rejected_matches": detailed.get("sample_rejected_matches", []),
        "target_sample": first_snapshot.get("target") if first_snapshot else None,
        "prediction_sample": predictions_for_build[0] if predictions_for_build else None,
        "storage_detected": storage_detected,
    }


@app.get("/debug/feature-store-diagnostics")
def debug_feature_store_diagnostics():
    return _feature_store_diagnostics()

@app.get("/backtesting")
def backtesting_report():
    return calculate_backtest_report(_available_matches(), _available_predictions())

@app.get("/ml/shadow-backtesting")
def ml_shadow_backtesting(limit: int = Query(default=500, ge=1, le=2000)):
    shadow_records = repository.get_ml_shadow_predictions(limit=limit)
    return calculate_shadow_backtest_report(_available_matches(), shadow_records)

@app.get("/shadow/backtesting")
def shadow_backtesting_report(limit: int = Query(default=2000, ge=1, le=5000)):
    shadow_records = repository.get_ml_shadow_predictions(limit=limit)
    return calculate_shadow_backtest_report(_available_matches(), shadow_records)

@app.get("/monitoring/model")
def model_monitoring(
    periods: str = Query(default="7d,30d,90d,all"),
    shadow_limit: int = Query(default=2000, ge=1, le=5000),
):
    parsed_periods = [item.strip() for item in periods.split(",") if item.strip()]
    return _model_monitoring_report(parsed_periods, shadow_limit)

@app.get("/performance")
def model_performance():
    predictions = _available_predictions()
    backtest = calculate_backtest_report(_available_matches(), predictions)
    average_confidence = 0
    average_risk_score = 0
    if predictions:
        average_confidence = round(sum(item["confidence"]["score"] for item in predictions) / len(predictions))
        average_risk_score = round(sum(item.get("risk_score", 0) for item in predictions) / len(predictions))
    reliable = [item for item in predictions if item["confidence"]["status"] == "FIABLE"]
    medium = [item for item in predictions if item["confidence"]["status"] == "MOYEN"]
    avoid = [item for item in predictions if item["confidence"]["status"] in {"À ÉVITER", "A EVITER"}]
    traps = [item for item in predictions if item["flags"]["trap_match"]]

    comparison = calculate_snapshot_backtest(_available_matches(), repository.get_prediction_snapshots())
    snapshots_count = sum(item.get("snapshots", 0) for item in comparison["model_versions"].values())
    feature_summary = _feature_summary()
    shadow_backtesting = calculate_shadow_backtest_report(
        _available_matches(),
        repository.get_ml_shadow_predictions(limit=2000),
    )
    monitoring_report = _model_monitoring_report(["7d", "30d", "90d", "all"], 2000) 
    model_governance = _model_governance_report()
    admin_alerts = _admin_alerts_compact()
    learning_feedback = build_feedback_report(_available_matches(), predictions, model_version=MODEL_VERSION)
    calibration_report = build_calibration_profile(_available_matches(), predictions, model_version=MODEL_VERSION)
    model_version_registry = get_versions_report()


    return {
        **PERFORMANCE,
        **backtest,
        "model_version": MODEL_VERSION,
        "current_model_version": MODEL_VERSION,
        "snapshots_count": snapshots_count,
        "model_versions": comparison["model_versions"],
        "best_model_by_brier": comparison.get("best_model_by_brier"),
        "best_model_by_accuracy": comparison.get("best_model_by_accuracy"),
        "model_comparison_note": comparison.get("note"),
        "feature_snapshots_count": feature_summary["snapshots_count"],
        "training_rows_available": feature_summary["with_target_count"],
        "target_coverage": feature_summary["target_coverage"],
        "feature_store_ready": feature_summary["snapshots_count"] > 0,
        "predictions_tracked": len(predictions),
        "tracked": len(predictions) or PERFORMANCE["tracked"],
        "averageConfidence": str(average_confidence or PERFORMANCE["averageConfidence"]),
        "average_confidence": average_confidence,
        "average_risk_score": average_risk_score,
        "reliable_count": len(reliable),
        "medium_count": len(medium),
        "avoid_count": len(avoid),
        "trap_match_count": len(traps),
        "latest_refresh": _refresh_status(),
        "ml_shadow_backtesting": shadow_backtesting,
        "model_monitoring": monitoring_report,
        "model_governance": model_governance,
        "learning_feedback": learning_feedback,
        "calibration_report": calibration_report,
        "model_version_registry": model_version_registry,
        "admin_alerts": admin_alerts,
    }


@app.get("/dashboard/summary")
def dashboard_summary():
    summary = _dashboard_summary()

    return {
        **summary,
        "monitoring_status": "healthy",
        "monitoring_accuracy_30d": 0,
        "monitoring_brier_30d": None,
        "monitoring_shadow_edge": "unknown",
        "monitoring_alerts_count": 0,
        "model_governance_level": "review_required",
        "model_governance_score": 0,
        "model_governance_blockers_count": 0,
        "model_promotion_ready": False,
        "admin_alerts_status": "unknown",
        "admin_alerts_count": 0,
        "admin_critical_alerts_count": 0,
    }


@app.get("/admin/refresh-status")
def refresh_status():
    stable = _refresh_status()
    return {
        "status": "ok",
        **stable,
        "stable_refresh_status": stable,
        "current_job": runtime_store.get_refresh_job(),
    }

def run_refresh_data_job(job_id: str | None = None) -> dict:
    started = time.perf_counter()

    try:
        _require_refresh_configuration()
        source = "mock"
        matches = MATCHES
        teams = TEAMS
        competition_warnings = []
        configured_competitions = []

        if os.getenv("FOOTBALL_DATA_API_KEY"):
            external_data = get_configured_competitions_data()
            external_matches = external_data["matches"]
            external_teams = external_data["teams"]
            competition_warnings = external_data.get("warnings", [])
            configured_competitions = external_data.get("competition_labels", [])

            if external_matches or external_teams:
                source = "football-data.org"
                matches = external_matches or MATCHES
                teams = external_teams or TEAMS

        predictions = _generated_predictions(matches)
        predictions_generated = len(predictions)

        storage = "memory"
        snapshots_saved = 0
        warning = None
        predictions_report = {"saved_count": 0, "failed_count": predictions_generated, "errors": []}
        refresh_log_report = {"saved": False, "error": None}

        saved_matches = repository.save_matches(matches)
        saved_teams = repository.save_teams(teams)
        if saved_matches and saved_teams:
            predictions_report = repository.save_predictions(predictions)

        predictions_saved = int(predictions_report.get("saved_count", 0) or 0)
        predictions_failed = int(predictions_report.get("failed_count", 0) or 0)
        predictions_errors = list(predictions_report.get("errors", []) or [])[:5]

        saved_core = saved_matches and saved_teams

        if saved_core:
            storage = "postgresql"
            refresh_log_report = repository.save_refresh_log(
                source,
                storage,
                len(matches),
                len(teams),
                predictions_generated=predictions_generated,
                predictions_saved=predictions_saved,
                predictions_failed=predictions_failed,
                prediction_save_errors=predictions_errors,
            )

            try:
                snapshots_saved = repository.save_prediction_snapshots(predictions)
            except Exception as exc:
                warning = f"Refresh réussi, mais sauvegarde des snapshots échouée: {exc}"
        else:
            warning = "PostgreSQL indisponible ou écriture échouée. Fallback mémoire utilisé."

        if storage == "postgresql" and predictions_generated > 0 and predictions_saved == 0:
            warning = "Predictions generated but not saved to PostgreSQL."
        if storage == "postgresql" and not refresh_log_report.get("saved"):
            log_error = refresh_log_report.get("error") or "unknown error"
            warning = f"{warning + ' ' if warning else ''}Refresh log not saved to PostgreSQL: {log_error}"

        runtime_store.set_matches(matches)
        runtime_store.set_teams(teams)
        runtime_store.set_predictions(predictions)
        runtime_store.set_source(source)
        runtime_store.set_storage(storage)

        status = runtime_store.get_refresh_status()
        duration_ms = round((time.perf_counter() - started) * 1000)

        result = {
            "status": "ok",
            "source": source,
            "storage": storage,
            "matches_imported": len(matches),
            "teams_imported": len(teams),
            "predictions_imported": predictions_saved,
            "predictions_generated": predictions_generated,
            "predictions_saved": predictions_saved,
            "predictions_failed": predictions_failed,
            "predictions_save_errors_sample": predictions_errors,
            "snapshots_saved": snapshots_saved,
            "refresh_duration_ms": duration_ms,
            "duration_ms": duration_ms,
            "next_recommended_actions": [
                "build_feature_store",
                "train_candidate_model",
                "generate_shadow_predictions",
            ],
            "last_refresh_at": status.get("last_refresh_at"),
            "warning": warning,
            "configured_competitions": configured_competitions,
            "competition_warnings": competition_warnings,
        }

        if job_id:
            runtime_store.finish_refresh_job(job_id, result)

        return result

    except Exception as exc:
        if job_id:
            runtime_store.fail_refresh_job(job_id, str(exc))
        else:
            runtime_store.release_refresh_lock()
        raise
    finally:
        if not job_id:
            runtime_store.release_refresh_lock()


@app.post("/admin/refresh-data")
def refresh_data(
    background_tasks: BackgroundTasks,
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
):
    _require_admin_key(x_admin_key)

    if not runtime_store.acquire_refresh_lock():
        latest = runtime_store.get_refresh_job()
        return {
            "status": "accepted",
            "job_id": latest.get("job_id"),
            "message": "Un refresh est déjà en cours.",
            "next_check_endpoint": f"/admin/refresh-job-status?job_id={latest.get('job_id')}",
        }

    job_id = str(uuid.uuid4())
    runtime_store.start_refresh_job(job_id)
    background_tasks.add_task(run_refresh_data_job, job_id)

    return {
        "status": "accepted",
        "job_id": job_id,
        "message": "Actualisation lancée. Consultez le statut du job.",
        "next_check_endpoint": f"/admin/refresh-job-status?job_id={job_id}",
    }


@app.post("/admin/refresh-data-sync")
def refresh_data_sync(x_admin_key: str | None = Header(default=None, alias="X-Admin-Key")):
    _require_admin_key(x_admin_key)
    if not runtime_store.acquire_refresh_lock():
        raise HTTPException(status_code=409, detail="Un refresh est déjà en cours.")
    return run_refresh_data_job(None)


@app.get("/admin/refresh-job-status")
def refresh_job_status(job_id: str | None = None):
    return runtime_store.get_refresh_job(job_id)

def run_build_feature_store_job(
    job_id: str | None = None,
    limit: int = 500,
    force: bool = False,
) -> dict:
    started = time.perf_counter()

    try:
        now = datetime.now(timezone.utc).isoformat()

        matches = _available_matches()
        stored_predictions = repository.get_predictions()
        if stored_predictions:
            predictions = stored_predictions
            predictions_source = "postgresql"
        else:
            predictions = _generated_predictions(matches)
            predictions_source = "generated_on_the_fly"
        matches_available = len(matches)
        predictions_available = len(predictions)
        finished_matches_available = sum(1 for match in matches if get_match_result(match) is not None)
        structure = _matches_structure_report(matches)
        finished_scored_matches = [match for match in matches if get_match_result(match) is not None]

        limit = max(1, min(int(limit or 500), 2000))

        existing_keys = set()
        if not force:
            try:
                existing_keys = repository.get_feature_snapshot_keys(model_version=MODEL_VERSION)
            except Exception:
                existing_keys = set()

        target_matches = []
        skipped_count = 0

        build_candidates = finished_scored_matches if finished_scored_matches else matches

        for match in build_candidates:
            match_id = match.get("match_id") or match.get("id") or match.get("slug")
            key = f"{match_id}:{MODEL_VERSION}"

            if not force and key in existing_keys:
                skipped_count += 1
                continue

            target_matches.append(match)

            if len(target_matches) >= limit:
                break

        elo_ratings = calculate_team_elos(matches)
        detailed = build_feature_snapshots_detailed(
            matches,
            predictions,
            target_matches=target_matches,
            prediction_factory=lambda match: _prediction_for_match(match, matches, elo_ratings),
        )
        feature_items = detailed.get("snapshots", [])
        rejection_reasons_count = dict(detailed.get("rejection_reasons_count", {}))
        sample_rejected_matches = detailed.get("sample_rejected_matches", [])

        save_report = repository.save_feature_snapshots(feature_items)
        if isinstance(save_report, dict):
            saved_count = int(save_report.get("saved_count", 0) or 0)
            save_failed_count = int(save_report.get("failed_count", 0) or 0)
            save_errors = list(save_report.get("errors", []) or [])[:5]
        else:
            saved_count = int(save_report or 0)
            save_failed_count = max(0, len(feature_items) - saved_count)
            save_errors = []

        if save_failed_count:
            rejection_reasons_count["save_failed"] = rejection_reasons_count.get("save_failed", 0) + save_failed_count

        source_refresh = _refresh_status()
        storage = "postgresql" if source_refresh.get("storage") == "postgresql" or repository.get_matches() else "memory"

        if storage == "memory" and feature_items:
            runtime_store.set_feature_snapshots(feature_items)

        training_rows_available = sum(1 for item in feature_items if item.get("target") is not None)
        reason_if_zero_snapshots = None

        if structure.get("finished_with_scores", 0) == 0:
            reason_if_zero_snapshots = "Aucun match terminé avec score disponible. Importez l’historique ou vérifiez les statuts football-data.org."
        elif len(feature_items) == 0:
            reason_if_zero_snapshots = "Matchs terminés avec score disponibles mais aucun snapshot créé. Vérifiez la jointure match/prédiction ou la génération à la volée."
        elif saved_count == 0 and storage == "postgresql":
            reason_if_zero_snapshots = "Snapshots créés en mémoire mais non sauvegardés en PostgreSQL."
        elif not feature_items:
            if matches_available == 0:
                reason_if_zero_snapshots = "Aucun match disponible pour construire le Feature Store."
            elif predictions_available == 0:
                reason_if_zero_snapshots = "Aucune prédiction disponible pour construire le Feature Store."
            elif skipped_count >= matches_available:
                reason_if_zero_snapshots = "Tous les matchs disposent déjà d'un snapshot Feature Store pour cette version modèle."
            else:
                reason_if_zero_snapshots = "Aucun snapshot Feature Store construit avec les données disponibles."

        target_coverage = (
            round((training_rows_available / len(feature_items)) * 100)
            if feature_items
            else 0
        )

        duration_ms = round((time.perf_counter() - started) * 1000)

        result = {
            "status": "error" if len(feature_items) > 0 and saved_count == 0 and storage == "postgresql" else ("warning" if reason_if_zero_snapshots else "ok"),
            "storage": storage,
            "predictions_source": predictions_source,
            "matches_available": matches_available,
            "predictions_available": predictions_available,
            "finished_matches_available": finished_matches_available,
            "finished_with_scores": structure.get("finished_with_scores", 0),
            "count_by_status": structure.get("count_by_status", {}),
            "feature_snapshots_built": len(feature_items),
            "snapshots_created": len(feature_items),
            "feature_snapshots_saved": saved_count,
            "snapshots_saved": saved_count,
            "feature_snapshots_failed": save_failed_count,
            "feature_save_errors_sample": save_errors,
            "save_errors": save_errors,
            "feature_snapshots_skipped": skipped_count,
            "reason_if_zero_snapshots": reason_if_zero_snapshots,
            "rejection_reasons_count": rejection_reasons_count,
            "sample_rejected_matches": sample_rejected_matches,
            "training_rows_available": training_rows_available,
            "target_coverage": target_coverage,
            "feature_set_version": "pre-match-advanced-v1",
            "duration_ms": duration_ms,
            "limit": limit,
            "force": force,
            "created_at": now,
            "note": "Feature Store construit en tâche asynchrone.",
        }

        if job_id:
            runtime_store.finish_feature_store_job(job_id, result)

        return result

    except Exception as exc:
        if job_id:
            runtime_store.fail_feature_store_job(job_id, str(exc))
        else:
            runtime_store.release_feature_store_lock()
        raise
    finally:
        if not job_id:
            runtime_store.release_feature_store_lock()


@app.post("/admin/build-feature-store")
def build_feature_store(
    background_tasks: BackgroundTasks,
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
    limit: int = Query(default=500, ge=1, le=2000),
    force: bool = Query(default=False),
) -> dict[str, Any]:
    _require_admin_key(x_admin_key)

    if not runtime_store.acquire_feature_store_lock():
        latest = runtime_store.get_feature_store_job()
        return {
            "status": "accepted",
            "job_id": latest.get("job_id"),
            "message": "Une construction Feature Store est déjà en cours.",
            "next_check_endpoint": f"/admin/feature-store-job-status?job_id={latest.get('job_id')}",
        }

    job_id = str(uuid.uuid4())
    runtime_store.start_feature_store_job(job_id)
    background_tasks.add_task(run_build_feature_store_job, job_id, limit, force)

    return {
        "status": "accepted",
        "job_id": job_id,
        "message": "Construction du Feature Store lancée.",
        "next_check_endpoint": f"/admin/feature-store-job-status?job_id={job_id}",
    }


@app.post("/admin/build-feature-store-sync")
def build_feature_store_sync(
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
    limit: int = Query(default=500, ge=1, le=2000),
    force: bool = Query(default=False),
) -> dict[str, Any]:
    _require_admin_key(x_admin_key)
    if not runtime_store.acquire_feature_store_lock():
        raise HTTPException(status_code=409, detail="Une construction Feature Store est déjà en cours.")
    return run_build_feature_store_job(None, limit, force)


@app.get("/admin/feature-store-job-status")
def feature_store_job_status(job_id: str | None = None):
    return runtime_store.get_feature_store_job(job_id)


@app.post("/admin/reset-stale-jobs")
def reset_stale_jobs(
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
    force: bool = Query(default=False),
):
    _require_admin_key(x_admin_key)
    runtime_reset = runtime_store.reset_stale_jobs(force=force, stale_seconds=5 * 60 if force else runtime_store.JOB_STALE_SECONDS)
    pipeline_reset = repository.reset_stale_pipeline_jobs(max_age_minutes=5 if force else 15)
    return {
        **runtime_reset,
        "pipeline_jobs": pipeline_reset,
        "pipeline_reset_count": pipeline_reset.get("reset_count", 0),
    }


@app.post("/admin/train-candidate-model")
def train_candidate_model_admin(
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
    model_type: str = Query(default="random_forest"),
    limit: int = Query(default=500, ge=1, le=10000),
    bypass_quality_gate: bool = Query(default=False),
) -> dict[str, Any]:
    _require_admin_key(x_admin_key)
    try:
        safe_limit = max(1, min(int(limit or 5000), 10000))
    except Exception:
        safe_limit = 5000
    safe_model_type = model_type if isinstance(model_type, str) else "random_forest"
    safe_bypass_quality_gate = bool(bypass_quality_gate) if isinstance(bypass_quality_gate, bool) else False

    load_report = load_training_rows_from_feature_snapshots(limit=safe_limit)
    rows = load_report.get("rows") or []
    if not rows:
        rows = _training_dataset(limit=safe_limit)
        load_report = {
            **load_report,
            "storage": load_report.get("storage") or "fallback",
            "rows_loaded": load_report.get("rows_loaded", len(rows)),
            "rows_after_validation": len(rows),
            "fallback_used": True,
        }
    quality = build_dataset_quality_report(rows, limit=safe_limit)

    if not safe_bypass_quality_gate and quality.get("safe_for_training") is False:
        return {
            "status": "error",
            "storage": load_report.get("storage", "postgresql"),
            "detail": quality.get("recommendation")
            or "Dataset quality gate blocked candidate model training.",
            "rows_loaded": load_report.get("rows_loaded", len(rows)),
            "rows_used": 0,
            "rows_after_validation": load_report.get("rows_after_validation", 0),
            "invalid_rows": len(rows),
            "invalid_feature_rows": load_report.get("invalid_feature_rows", 0),
            "invalid_target_rows": load_report.get("invalid_target_rows", 0),
            "features_used": [],
            "feature_names": [],
            "target_distribution": {},
            "accuracy": 0,
            "log_loss": None,
            "brier_score": None,
            "brier_score_1x2": None,
            "errors": [quality.get("recommendation_reason") or quality.get("recommendation") or "Dataset quality gate blocked"],
            "warnings": [],
            "training_rows_available": len(rows),
            "load_diagnostics": {key: value for key, value in load_report.items() if key != "rows"},
            "dataset_quality": quality,
            "next_step": "review_dataset_quality",
        }

    report = train_candidate_model(rows, model_type=safe_model_type)
    report["brier_score"] = report.get("brier_score_1x2")
    report["storage"] = load_report.get("storage", report.get("storage", "postgresql"))
    report["training_rows_available"] = len(rows)
    report["load_diagnostics"] = {key: value for key, value in load_report.items() if key != "rows"}
    report["dataset_quality"] = quality
    report["next_step"] = (
        "generate_shadow_predictions"
        if report.get("status") in {"ok", "trained", "success"}
        else "train_candidate_model"
    )
    if report.get("status") in {"ok", "trained", "success"}:
        try:
            report["registry_entry"] = record_model_version(
                model_version=report.get("model_version") or "ml-candidate-v1",
                feature_set_version=report.get("feature_set_version"),
                calibration_version=CALIBRATION_VERSION,
                trained_at=report.get("trained_at"),
                rows_used=int(report.get("rows_used") or 0),
                metrics={
                    "accuracy": report.get("accuracy"),
                    "log_loss": report.get("log_loss"),
                    "brier_score": report.get("brier_score_1x2"),
                    "target_distribution": report.get("target_distribution", {}),
                    "features_used": report.get("features_used") or report.get("feature_columns"),
                    "rows_loaded": report.get("rows_loaded"),
                    "invalid_rows": report.get("invalid_rows"),
                },
                status="candidate",
                family=report.get("model_type"),
                artifact_path=report.get("artifact_path"),
                features_used=report.get("features_used") or report.get("feature_columns"),
                target_distribution=report.get("target_distribution", {}),
            )
        except Exception as exc:
            report["registry_warning"] = f"Model version registry not updated: {exc}"
    return report


def run_generate_shadow_predictions_job(job_id: str | None, limit: int, force: bool, view: str) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        matches = _matches_for_shadow_generation(view, limit)
        predictions = _available_predictions()
        prediction_by_key: dict[str, dict] = {}

        for prediction in predictions:
            for key in (prediction.get("match_id"), prediction.get("id"), prediction.get("slug")):
                if key:
                    prediction_by_key[str(key)] = prediction

        items: list[dict] = []
        skipped_existing = 0
        unavailable_count = 0
        same_pick_count = 0
        disagreement_count = 0
        high_disagreement_count = 0
        active_calibration = _stored_calibration_profile(repository.get_active_calibration())

        for match in matches:
            match_id = _match_id(match)
            if not match_id:
                continue

            if not force and repository.get_ml_shadow_prediction(match_id):
                skipped_existing += 1
                continue

            production_prediction = (
                prediction_by_key.get(match_id)
                or prediction_by_key.get(str(match.get("id")))
                or prediction_by_key.get(str(match.get("slug")))
                or _prediction_for_match(match, matches)
            )
            shadow_prediction = generate_shadow_prediction(match, production_prediction)
            if active_calibration:
                shadow_prediction = calibrate_prediction(shadow_prediction, active_calibration)
            comparison = compare_shadow_to_production(production_prediction, shadow_prediction)

            if not shadow_prediction.get("available"):
                unavailable_count += 1
            if comparison.get("same_pick") is True:
                same_pick_count += 1
            if comparison.get("same_pick") is False:
                disagreement_count += 1
            if comparison.get("disagreement_level") == "high":
                high_disagreement_count += 1

            items.append(
                {
                    "match_id": match_id,
                    "production_prediction": production_prediction,
                    "shadow_prediction": shadow_prediction,
                    "comparison": comparison,
                }
            )

        saved_count = repository.save_ml_shadow_predictions(items)
        storage = "postgresql" if repository.db_available() else "memory"
        created_at = datetime.now(timezone.utc).isoformat()

        if items and storage == "postgresql" and saved_count == 0:
            status = "error"
            detail = "Shadow predictions generated but not saved to PostgreSQL."
        elif not items:
            status = "warning"
            detail = "Aucune prédiction shadow générée pour cette vue."
        else:
            status = "ok"
            detail = None

        result = {
            "status": status,
            "storage": storage,
            "view": view,
            "shadow_predictions_generated": len(items),
            "shadow_predictions_saved": saved_count,
            "available_count": len(items) - unavailable_count,
            "unavailable_count": unavailable_count,
            "same_pick_count": same_pick_count,
            "disagreement_count": disagreement_count,
            "high_disagreement_count": high_disagreement_count,
            "skipped_existing_count": skipped_existing,
            "candidate_is_production": False,
            "calibration_applied": bool(active_calibration),
            "calibration_version": (active_calibration or {}).get("calibration_version"),
            "created_at": created_at,
            "detail": detail,
            "next_step": "review_shadow_backtesting" if saved_count > 0 else "generate_shadow_predictions",
            "note": "Prédictions ML shadow générées en observation uniquement.",
            "duration_ms": round((time.perf_counter() - started) * 1000),
        }
        if saved_count > 0:
            try:
                candidate = _ml_status_compact().get("latest_candidate") or {}
                result["registry_entry"] = record_model_version(
                    model_version=candidate.get("model_version") or "ml-candidate-v1",
                    feature_set_version=candidate.get("feature_set_version"),
                    calibration_version=CALIBRATION_VERSION,
                    trained_at=candidate.get("trained_at"),
                    rows_used=int(candidate.get("rows_used") or 0),
                    metrics={
                        "shadow_predictions_saved": saved_count,
                        "disagreement_count": disagreement_count,
                        "high_disagreement_count": high_disagreement_count,
                    },
                    status="shadow",
                    family=candidate.get("model_type"),
                    artifact_path=candidate.get("artifact_path"),
                )
            except Exception as exc:
                result["registry_warning"] = f"Model version registry not updated: {exc}"

        if job_id:
            runtime_store.finish_shadow_prediction_job(job_id, result)

        return result
    except Exception as exc:
        if job_id:
            runtime_store.fail_shadow_prediction_job(job_id, exc)
        raise


@app.post("/admin/generate-shadow-predictions")
def generate_shadow_predictions_admin(
    background_tasks: BackgroundTasks,
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
    limit: int = Query(default=500, ge=1, le=2000),
    force: bool = Query(default=False),
    view: str = Query(default="upcoming"),
    sync: bool = Query(default=False),
) -> dict[str, Any]:
    _require_admin_key(x_admin_key)

    if sync or limit <= 25:
        return run_generate_shadow_predictions_job(None, limit, force, view)

    if not runtime_store.acquire_shadow_prediction_lock():
        latest = runtime_store.get_shadow_prediction_job()
        return {
            "status": "accepted",
            "job_id": latest.get("job_id"),
            "message": "Une génération shadow est déjà en cours.",
            "next_check_endpoint": f"/admin/shadow-prediction-job-status?job_id={latest.get('job_id')}",
        }

    job_id = str(uuid.uuid4())
    runtime_store.start_shadow_prediction_job(job_id)
    background_tasks.add_task(run_generate_shadow_predictions_job, job_id, limit, force, view)

    return {
        "status": "accepted",
        "job_id": job_id,
        "message": "Génération des prédictions shadow lancée.",
        "next_check_endpoint": f"/admin/shadow-prediction-job-status?job_id={job_id}",
    }


@app.get("/admin/shadow-prediction-job-status")
def shadow_prediction_job_status(job_id: str | None = None):
    return runtime_store.get_shadow_prediction_job(job_id)


def _pipeline_handlers(controlled_auto_train: bool = False) -> dict[str, Any]:
    def refresh_step():
        if not runtime_store.acquire_refresh_lock():
            return {"status": "skipped", "detail": "Refresh already running."}
        return run_refresh_data_job(None)

    def feature_step():
        if not runtime_store.acquire_feature_store_lock():
            return {"status": "skipped", "detail": "Feature Store build already running."}
        return run_build_feature_store_job(None, limit=2000, force=False)

    def train_step():
        if not controlled_auto_train:
            return {"status": "skipped", "detail": "Auto training is disabled by default."}
        rows = load_training_rows_from_feature_snapshots(limit=5000)
        if len(rows) < 50:
            return {"status": "skipped", "detail": "Not enough training rows for controlled auto train.", "rows_loaded": len(rows)}
        return train_candidate_model(rows, model_type="random_forest")

    def shadow_step():
        workflow = _workflow_status_compact()
        if not workflow.get("candidate_model", {}).get("trained"):
            return {"status": "skipped", "detail": "No trained candidate model available."}
        if not runtime_store.acquire_shadow_prediction_lock():
            return {"status": "skipped", "detail": "Shadow prediction generation already running."}
        return run_generate_shadow_predictions_job(None, limit=500, force=False, view="upcoming")

    def shadow_backtesting_step():
        return calculate_shadow_backtest_report(_available_matches(), repository.get_ml_shadow_predictions(limit=2000))

    def feedback_step():
        return build_feedback_report(_available_matches(), _available_predictions())

    def calibration_step():
        return _calibration_report()

    def monitoring_step():
        return learning_monitoring()

    return {
        "refresh_data": refresh_step,
        "build_feature_store": feature_step,
        "train_candidate_model": train_step,
        "generate_shadow_predictions": shadow_step,
        "shadow_backtesting": shadow_backtesting_step,
        "feedback": feedback_step,
        "calibration": calibration_step,
        "monitoring": monitoring_step,
    }


def _pipeline_status_report() -> dict[str, Any]:
    repository.init_pipeline_jobs_schema()
    job_types = [
        "refresh_data",
        "build_feature_store",
        "train_candidate_model",
        "generate_shadow_predictions",
        "shadow_backtesting",
        "learning_monitoring",
        "match_finished_check",
        "calibration",
        "feedback",
    ]
    latest_jobs = {job_type: repository.get_latest_pipeline_job(job_type) for job_type in job_types}
    running_jobs = repository.get_running_pipeline_jobs()
    stale_jobs = [job for job in running_jobs if str(job.get("status")) == "stale"]
    workflow = _workflow_status_compact()
    monitoring = learning_monitoring()
    feature = workflow.get("feature_store", {})
    candidate = workflow.get("candidate_model", {})
    shadow_predictions = workflow.get("shadow_predictions", {})
    shadow_backtesting = workflow.get("shadow_backtesting", {})
    health = {
        "data_refresh": "ok" if workflow.get("refresh", {}).get("data_imported") else "warning",
        "feature_store": "ok" if feature.get("ready") else "empty",
        "candidate_model": "ok" if candidate.get("trained") else "missing",
        "shadow_predictions": "ok" if shadow_predictions.get("generated") else "missing",
        "shadow_backtesting": "ok" if shadow_backtesting.get("ready") else "insufficient_data",
        "learning_monitoring": monitoring.get("status", "unknown"),
    }
    next_step = workflow.get("next_step") or "refresh_data"
    labels = {
        "refresh_data": "Actualiser les données",
        "build_feature_store": "Construire le Feature Store",
        "train_candidate_model": "Entraîner un modèle candidat",
        "generate_shadow_predictions": "Générer les prédictions shadow",
        "wait_for_results": "Attendre les résultats des matchs",
        "continue_shadow_testing": "Continuer le shadow testing",
        "review_governance": "Revoir la gouvernance",
    }
    return {
        "status": "ok",
        "storage": "postgresql" if repository.db_available() else "memory",
        "latest_jobs": latest_jobs,
        "running_jobs": running_jobs,
        "stale_jobs": stale_jobs,
        "health": health,
        "next_best_action": {
            "label": labels.get(next_step, next_step),
            "action": next_step,
        },
    }


@app.get("/pipeline/status")
def pipeline_status(x_admin_key: str | None = Header(default=None, alias="X-Admin-Key")):
    _require_admin_key(x_admin_key)
    return _pipeline_status_report()


@app.get("/pipeline/jobs")
def pipeline_jobs(
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
    limit: int = Query(default=100, ge=1, le=500),
    job_type: str | None = None,
):
    _require_admin_key(x_admin_key)
    jobs = repository.list_pipeline_jobs(limit=limit, job_type=job_type)
    return {"status": "ok", "storage": "postgresql" if repository.db_available() else "memory", "jobs_count": len(jobs), "jobs": jobs}


@app.post("/pipeline/run-step")
async def pipeline_run_step(request: Request, x_admin_key: str | None = Header(default=None, alias="X-Admin-Key")):
    _require_admin_key(x_admin_key)
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    step = payload.get("step") or payload.get("job_type") or payload.get("jobType")
    controlled_auto_train = payload.get("controlled_auto_train") is True
    return run_pipeline_step(str(step or ""), {"handlers": _pipeline_handlers(controlled_auto_train), "triggered_by": "admin"})


@app.post("/pipeline/run-hourly")
def pipeline_run_hourly(x_admin_key: str | None = Header(default=None, alias="X-Admin-Key")):
    _require_admin_key(x_admin_key)
    result = run_hourly_data_pipeline(_pipeline_handlers(controlled_auto_train=False), triggered_by="admin")
    runtime_store.set_cron_run("hourly_refresh", result)
    return result


@app.post("/pipeline/run-daily")
def pipeline_run_daily(x_admin_key: str | None = Header(default=None, alias="X-Admin-Key")):
    _require_admin_key(x_admin_key)
    return run_daily_learning_pipeline(_pipeline_handlers(controlled_auto_train=False), triggered_by="admin")


@app.post("/pipeline/reset-stale-jobs")
def pipeline_reset_stale_jobs(
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
    max_age_minutes: int = Query(default=15, ge=1, le=120),
):
    _require_admin_key(x_admin_key)
    runtime_reset = runtime_store.reset_stale_jobs(force=max_age_minutes <= 5, stale_seconds=max_age_minutes * 60)
    pipeline_reset = repository.reset_stale_pipeline_jobs(max_age_minutes=max_age_minutes)
    return {"status": "ok", "runtime_jobs": runtime_reset, "pipeline_jobs": pipeline_reset, "reset_count": pipeline_reset.get("reset_count", 0)}


def _cron_next_step() -> str:
    return _workflow_status_compact().get("next_step", "refresh_data")


@app.post("/admin/cron/hourly-refresh")
def cron_hourly_refresh(x_admin_key: str | None = Header(default=None, alias="X-Admin-Key")):
    _require_admin_key(x_admin_key)
    result = run_hourly_data_pipeline(_pipeline_handlers(controlled_auto_train=False), triggered_by="cron")
    result["next_step"] = _cron_next_step()
    runtime_store.set_cron_run("hourly_refresh", result)
    return result


def _finished_match_ids() -> set[str]:
    finished = []
    for match in _available_matches():
        if str(match.get("status", "")).upper() != "FINISHED":
            continue
        match_id = match.get("match_id") or match.get("id") or match.get("slug")
        if match_id and get_match_result(match) is not None:
            finished.append(str(match_id))
    return set(finished)


@app.post("/admin/cron/match-finished-check")
def cron_match_finished_check(x_admin_key: str | None = Header(default=None, alias="X-Admin-Key")):
    _require_admin_key(x_admin_key)

    before = runtime_store.get_last_finished_match_ids()
    refresh_result = run_pipeline_step("refresh_data", {"handlers": _pipeline_handlers(False), "triggered_by": "cron"}).get("result") or {}
    current = _finished_match_ids()
    detected = sorted(current - before)

    if not detected:
        result = {
            "status": "noop",
            "finished_matches_detected": 0,
            "refresh_status": refresh_result.get("status"),
            "feature_store_status": "skipped",
            "backtesting_status": "skipped",
            "next_step": _cron_next_step(),
        }
        runtime_store.set_last_finished_match_ids(current)
        runtime_store.set_cron_run("match_finished_check", result)
        return result

    pipeline = run_after_match_finished_pipeline(_pipeline_handlers(False), triggered_by="cron")

    runtime_store.set_last_finished_match_ids(_finished_match_ids())
    result = {
        "status": "ok",
        "finished_matches_detected": len(detected),
        "finished_match_ids": detected,
        "refresh_status": refresh_result.get("status"),
        "pipeline": pipeline,
        "feature_store_status": "ok" if pipeline.get("status") == "ok" else pipeline.get("status"),
        "backtesting_status": "ok" if pipeline.get("status") == "ok" else pipeline.get("status"),
        "next_step": _cron_next_step(),
    }
    runtime_store.set_cron_run("match_finished_check", result)
    return result
