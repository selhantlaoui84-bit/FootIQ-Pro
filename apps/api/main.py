import os
import time
import uuid
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
from services.feature_store import build_feature_snapshots, summarize_feature_store
from services.data_quality import build_dataset_quality_report
from services.football_data_client import (
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
    if latest_log:
        return {
            "source": latest_log.get("source", "mock"),
            "storage": latest_log.get("storage", "postgresql"),
            "matches_imported": len(repository.get_matches()),
            "teams_imported": len(repository.get_teams()),
            "predictions_imported": len(repository.get_predictions()),
            "last_refresh_at": latest_log.get("last_refresh_at"),
        }

    return runtime_store.get_refresh_status()


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
    env = os.getenv("ENV", "development").lower()
    admin_key = os.getenv("ADMIN_API_KEY")

    if not admin_key and env != "production":
        return

    if not admin_key or not x_admin_key:
        raise HTTPException(status_code=401, detail="Missing admin key")

    if x_admin_key != admin_key:
        raise HTTPException(status_code=401, detail="Invalid admin key")


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
    return {**metadata, "available_model_versions": available_versions}


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
    }

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
    }


@app.get("/dashboard/summary")
def dashboard_summary():
    summary = _dashboard_summary()

    monitoring_report = _model_monitoring_report(["30d"], 2000)
    monitoring_30d = monitoring_report.get("periods", {}).get("30d", {})
    monitoring_official_30d = monitoring_30d.get("official", {})
    monitoring_trend = monitoring_report.get("trend_summary", {})

    return {
        **summary,
        "monitoring_status": monitoring_trend.get("monitoring_status", "unknown"),
        "monitoring_accuracy_30d": monitoring_official_30d.get("result_accuracy", 0),
        "monitoring_brier_30d": monitoring_official_30d.get("average_brier_score"),
        "monitoring_shadow_edge": monitoring_trend.get("shadow_edge", "unknown"),
        "monitoring_alerts_count": len(monitoring_report.get("alerts", [])),
    }


@app.get("/admin/refresh-status")
def refresh_status():
    return {"status": "ok", **_refresh_status()}

def run_refresh_data_job(job_id: str | None = None) -> dict:
    started = time.perf_counter()

    try:
        source = "mock"
        matches = MATCHES
        teams = TEAMS

        if os.getenv("FOOTBALL_DATA_API_KEY"):
            external_matches = get_ligue1_matches() + get_champions_league_matches()
            external_teams = get_ligue1_teams() + get_champions_league_teams()

            if external_matches or external_teams:
                source = "football-data.org"
                matches = external_matches or MATCHES
                teams = external_teams or TEAMS

        elo_ratings = calculate_team_elos(matches)
        predictions = [_prediction_for_match(match, matches, elo_ratings) for match in matches]

        storage = "memory"
        snapshots_saved = 0
        warning = None

        saved_core = repository.save_matches(matches) and repository.save_teams(teams) and repository.save_predictions(predictions)

        if saved_core:
            storage = "postgresql"
            repository.save_refresh_log(source, storage, len(matches), len(teams))

            try:
                snapshots_saved = repository.save_prediction_snapshots(predictions)
            except Exception as exc:
                warning = f"Refresh réussi, mais sauvegarde des snapshots échouée: {exc}"
        else:
            warning = "PostgreSQL indisponible ou écriture échouée. Fallback mémoire utilisé."

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
            "predictions_imported": len(predictions),
            "snapshots_saved": snapshots_saved,
            "refresh_duration_ms": duration_ms,
            "next_recommended_actions": [
                "build_feature_store",
                "train_candidate_model",
                "generate_shadow_predictions",
            ],
            "last_refresh_at": status.get("last_refresh_at"),
            "warning": warning,
        }

        if job_id:
            runtime_store.finish_refresh_job(job_id, result)

        return result

    except Exception as exc:
        if job_id:
            runtime_store.fail_refresh_job(job_id, str(exc))
        raise


@app.post("/admin/refresh-data")
def refresh_data(
    background_tasks: BackgroundTasks,
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
):
    _require_admin_key(x_admin_key)

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
        predictions = _available_predictions()

        limit = max(1, min(int(limit or 500), 2000))

        existing_keys = set()
        if not force:
            try:
                existing_keys = repository.get_feature_snapshot_keys(model_version=MODEL_VERSION)
            except Exception:
                existing_keys = set()

        target_matches = []
        skipped_count = 0

        for match in matches:
            match_id = match.get("match_id") or match.get("id") or match.get("slug")
            key = f"{match_id}:{MODEL_VERSION}"

            if not force and key in existing_keys:
                skipped_count += 1
                continue

            target_matches.append(match)

            if len(target_matches) >= limit:
                break

        try:
            feature_items = build_feature_snapshots(matches, predictions, target_matches=target_matches)
        except TypeError:
            all_items = build_feature_snapshots(matches, predictions)
            target_ids = {
                item.get("match_id") or item.get("id") or item.get("slug")
                for item in target_matches
            }
            feature_items = [
                item for item in all_items
                if item.get("match_id") in target_ids
            ][:limit]

        saved_count = repository.save_feature_snapshots(feature_items)

        storage = "postgresql" if saved_count > 0 else "memory"

        if storage == "memory" and feature_items:
            runtime_store.set_feature_snapshots(feature_items)

        training_rows_available = sum(1 for item in feature_items if item.get("target") is not None)

        target_coverage = (
            round((training_rows_available / len(feature_items)) * 100)
            if feature_items
            else 0
        )

        duration_ms = round((time.perf_counter() - started) * 1000)

        result = {
            "status": "ok",
            "storage": storage,
            "feature_snapshots_built": len(feature_items),
            "feature_snapshots_saved": saved_count,
            "feature_snapshots_skipped": skipped_count,
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
        raise


@app.post("/admin/build-feature-store")
def build_feature_store(
    background_tasks: BackgroundTasks,
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
    limit: int = Query(default=500, ge=1, le=2000),
    force: bool = Query(default=False),
) -> dict[str, Any]:
    _require_admin_key(x_admin_key)

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
    return run_build_feature_store_job(None, limit, force)


@app.get("/admin/feature-store-job-status")
def feature_store_job_status(job_id: str | None = None):
    return runtime_store.get_feature_store_job(job_id)