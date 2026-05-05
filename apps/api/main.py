import os
import time
import uuid
from collections import Counter
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any
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
from services.model_governance import build_model_governance_report
from services.prediction_engine import generate_prediction_from_match
from services.prediction_engine import MODEL_VERSION


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
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
    candidate_trained = ml_status.get("status") in {"ok", "trained", "success"}
    shadow_generated = shadow_summary.get("shadow_predictions_count", 0) > 0
    shadow_backtesting_ready = shadow_backtesting.get("evaluated_matches", 0) > 0

    if not data_imported:
        next_step = "refresh_data"
    elif not feature_ready:
        next_step = "build_feature_store" if finished_with_scores > 0 else "import_historical_results"
    elif not candidate_trained:
        next_step = "train_candidate_model"
    elif not shadow_generated:
        next_step = "generate_shadow_predictions"
    elif not shadow_backtesting_ready:
        next_step = "review_shadow_backtesting"
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
            "status": ml_status.get("status", "not_trained"),
            "model_version": (ml_status.get("latest_candidate") or {}).get("model_version"),
            "accuracy": (ml_status.get("latest_candidate") or {}).get("accuracy"),
        },
        "shadow_predictions": {
            "generated": shadow_generated,
            "count": shadow_summary.get("shadow_predictions_count", 0),
            "disagreement_count": shadow_summary.get("disagreement_count", 0),
        },
        "shadow_backtesting": {
            "ready": shadow_backtesting_ready,
            "evaluated_matches": shadow_backtesting.get("evaluated_matches", 0),
            "shadow_accuracy": shadow_backtesting.get("shadow_accuracy", 0),
            "activation_recommendation": shadow_backtesting.get("activation_recommendation", "do_not_activate"),
        },
        "latest_refresh_job": latest_refresh_job,
        "latest_feature_store_job": latest_feature_store_job,
        "cron": runtime_store.get_cron_status(),
        "next_step": next_step,
    }


def _admin_alerts_report():
    workflow_status = _workflow_status_compact()
    refresh_status = _refresh_status()
    feature_summary = _feature_summary()
    dataset_quality = _dataset_quality_report(1000)
    ml_status = _ml_status_compact()
    shadow_summary = _shadow_summary_compact()
    shadow_backtesting = calculate_shadow_backtest_report(
        _available_matches(),
        repository.get_ml_shadow_predictions(limit=2000),
    )
    monitoring_report = _model_monitoring_report(["30d", "all"], 2000)
    governance_report = _model_governance_report()

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


def _training_dataset(model_version: str | None = None, limit: int = 100):
    limit = max(1, min(int(limit or 100), 500))
    rows = repository.get_training_dataset(model_version=model_version, limit=limit)
    if rows:
        return rows
    snapshots = _available_feature_snapshots()
    if model_version:
        snapshots = [item for item in snapshots if item.get("model_version") == model_version]
    return [item for item in snapshots if item.get("target")][:limit]

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

    latest_candidate = latest_candidate or {
        "status": "not_trained",
        "model_version": "ml-candidate-v1",
        "model_type": "random_forest",
        "rows_used": 0,
        "accuracy": None,
        "brier_score_1x2": None,
        "trained_at": None,
    }

    return {
        "status": latest_candidate.get("status", "not_trained"),
        "latest_candidate": latest_candidate,
        "candidate_model_exists": latest_candidate.get("status") not in {"not_trained", None},
        "production_model_version": MODEL_VERSION,
        "candidate_is_production": False,
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

    try:
        hybrid_engine_summary = hybrid_engine_summary_report(limit=200, view="upcoming")
    except Exception:
        hybrid_engine_summary = {
            "recommendation": "insufficient_shadow_data",
            "reason": "Résumé hybride indisponible.",
        }

    return build_model_governance_report(
        model_metadata,
        ml_status,
        dataset_quality,
        monitoring_report,
        shadow_backtesting,
        hybrid_engine_summary,
    )


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
    stored_matches = repository.get_matches()
    stored_teams = repository.get_teams()
    stored_predictions = repository.get_predictions()

    if latest_log:
        source = latest_log.get("source", "mock")
        storage = "postgresql" if stored_matches else latest_log.get("storage", "postgresql")
        predictions_saved = latest_log.get("predictions_saved", len(stored_predictions))
        predictions_generated = latest_log.get("predictions_generated", predictions_saved)
        return {
            "source": source,
            "storage": storage,
            "matches_imported": len(stored_matches),
            "teams_imported": len(stored_teams),
            "predictions_imported": predictions_saved,
            "predictions_generated": predictions_generated,
            "predictions_saved": predictions_saved,
            "predictions_failed": latest_log.get("predictions_failed", 0),
            "prediction_save_errors": latest_log.get("prediction_save_errors", []),
            "last_refresh_at": latest_log.get("last_refresh_at"),
            "warning": None if storage == "postgresql" else "PostgreSQL indisponible ou écriture échouée. Fallback mémoire utilisé.",
        }

    if stored_matches:
        source = stored_matches[0].get("source") or "football-data.org"
        return {
            "source": source,
            "storage": "postgresql",
            "matches_imported": len(stored_matches),
            "teams_imported": len(stored_teams),
            "predictions_imported": len(stored_predictions),
            "predictions_generated": len(stored_predictions),
            "predictions_saved": len(stored_predictions),
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
    matches = _available_matches()
    teams = _available_teams()
    predictions = _available_predictions()
    backtest = calculate_backtest_report(matches, predictions)
    total_matches = len(matches)
    reliable = [item for item in predictions if item["confidence"]["status"] == "FIABLE"]
    medium = [item for item in predictions if item["confidence"]["status"] == "MOYEN"]
    avoid = [item for item in predictions if item["confidence"]["status"] in {"Ã€ Ã‰VITER", "A EVITER"}]
    traps = [item for item in predictions if item["flags"]["trap_match"]]
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
        average_confidence = round(sum(item["confidence"]["score"] for item in predictions) / len(predictions))

    comparison = calculate_snapshot_backtest(matches, repository.get_prediction_snapshots())
    feature_summary = _feature_summary()
    shadow_backtesting = calculate_shadow_backtest_report(
        matches,
        repository.get_ml_shadow_predictions(limit=2000),
    )

    return {
        "total_matches": total_matches,
        "teams_count": len(teams),
        "predictions_count": len(predictions),
        "upcoming_matches_count": total_matches,
        "reliable_matches_count": len(reliable),
        "medium_matches_count": len(medium),
        "avoid_matches_count": len(avoid),
        "trap_matches_count": len(traps),
        "average_confidence": average_confidence,
        "average_risk_score": average_risk_score,
        "model_version": MODEL_VERSION,
        "current_model_version": MODEL_VERSION,
        "snapshots_count": sum(item.get("snapshots", 0) for item in comparison["model_versions"].values()),
        "best_model_by_brier": comparison.get("best_model_by_brier"),
        "feature_snapshots_count": feature_summary["snapshots_count"],
        "training_rows_available": feature_summary["with_target_count"],
        "target_coverage": feature_summary["target_coverage"],
        "feature_store_ready": feature_summary["snapshots_count"] > 0,
        "evaluated_matches": backtest["evaluated_matches"],
        "result_accuracy": backtest["result_accuracy"],
        "average_brier_score": backtest["average_brier_score"],
        "calibration_score": backtest["calibration_score"],
        "competitions_breakdown": competitions,
        "top_reliable_matches": sorted(
            predictions,
            key=lambda item: item["confidence"]["score"],
            reverse=True,
        )[:5],
        "top_risky_matches": sorted(
            [item for item in predictions if item["flags"]["risk"] or item["flags"]["trap_match"]],
            key=lambda item: item["confidence"]["score"],
        )[:5],
        "last_refresh_at": status.get("last_refresh_at"),
        "source": status.get("source", "mock"),
        "storage": status.get("storage", "memory"),
        "shadow_evaluated_matches": shadow_backtesting.get("evaluated_matches", 0),
        "shadow_accuracy": shadow_backtesting.get("shadow_accuracy", 0),
        "shadow_activation_recommendation": shadow_backtesting.get("activation_recommendation", "do_not_activate"),
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


@app.get("/models/comparison")
def model_comparison():
    return calculate_snapshot_backtest(_available_matches(), repository.get_prediction_snapshots())


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
    avoid = [item for item in predictions if item["confidence"]["status"] in {"Ã€ Ã‰VITER", "A EVITER"}]
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
        "admin_alerts": admin_alerts,
    }


@app.get("/dashboard/summary")
def dashboard_summary():
    summary = _dashboard_summary()

    monitoring_report = _model_monitoring_report(["30d"], 2000)
    monitoring_30d = monitoring_report.get("periods", {}).get("30d", {})
    monitoring_official_30d = monitoring_30d.get("official", {})
    monitoring_trend = monitoring_report.get("trend_summary", {})
    alerts = _admin_alerts_compact()
    governance = _model_governance_report()
    readiness = governance.get("promotion_readiness", {})

    return {
        **summary,
        "monitoring_status": monitoring_trend.get("monitoring_status", "unknown"),
        "monitoring_accuracy_30d": monitoring_official_30d.get("result_accuracy", 0),
        "monitoring_brier_30d": monitoring_official_30d.get("average_brier_score"),
        "monitoring_shadow_edge": monitoring_trend.get("shadow_edge", "unknown"),
        "monitoring_alerts_count": len(monitoring_report.get("alerts", [])),
        "model_governance_level": readiness.get("level", "not_ready"),
        "model_governance_score": readiness.get("score", 0),
        "model_governance_blockers_count": len(readiness.get("blocking_reasons", [])),
        "model_promotion_ready": False,
        "admin_alerts_status": alerts.get("overall_status"),
        "admin_alerts_count": alerts.get("alerts_count"),
        "admin_critical_alerts_count": alerts.get("critical_count"),
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
    return runtime_store.reset_stale_jobs(force=force, stale_seconds=5 * 60 if force else runtime_store.JOB_STALE_SECONDS)


def _cron_next_step() -> str:
    return _workflow_status_compact().get("next_step", "refresh_data")


@app.post("/admin/cron/hourly-refresh")
def cron_hourly_refresh(x_admin_key: str | None = Header(default=None, alias="X-Admin-Key")):
    _require_admin_key(x_admin_key)

    refresh_result = refresh_data_sync(x_admin_key)
    feature_result: dict[str, Any]

    if refresh_result.get("status") == "ok":
        try:
            feature_result = build_feature_store_sync(x_admin_key, limit=2000, force=False)
        except HTTPException as exc:
            feature_result = {"status": "error", "detail": exc.detail}
        except Exception as exc:
            feature_result = {"status": "error", "detail": str(exc)}
    else:
        feature_result = {"status": "skipped", "detail": "Refresh did not complete successfully."}

    result = {
        "status": "ok",
        "refresh": {"status": refresh_result.get("status"), **refresh_result},
        "feature_store": {"status": feature_result.get("status"), **feature_result},
        "source": refresh_result.get("source"),
        "storage": refresh_result.get("storage"),
        "matches_imported": refresh_result.get("matches_imported", 0),
        "feature_snapshots_saved": feature_result.get("feature_snapshots_saved", 0),
        "next_step": _cron_next_step(),
    }
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
    refresh_result = refresh_data_sync(x_admin_key)
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

    feature_result: dict[str, Any]

    try:
        feature_result = build_feature_store_sync(x_admin_key, limit=2000, force=False)
    except HTTPException as exc:
        feature_result = {"status": "error", "detail": exc.detail}
    except Exception as exc:
        feature_result = {"status": "error", "detail": str(exc)}

    try:
        backtesting = calculate_backtest_report(_available_matches(), _available_predictions())
        backtesting_status = "ok"
    except Exception as exc:
        backtesting = {"detail": str(exc)}
        backtesting_status = "error"

    runtime_store.set_last_finished_match_ids(_finished_match_ids())
    result = {
        "status": "ok",
        "finished_matches_detected": len(detected),
        "finished_match_ids": detected,
        "refresh_status": refresh_result.get("status"),
        "feature_store_status": feature_result.get("status"),
        "backtesting_status": backtesting_status,
        "backtesting": backtesting,
        "next_step": _cron_next_step(),
    }
    runtime_store.set_cron_run("match_finished_check", result)
    return result
