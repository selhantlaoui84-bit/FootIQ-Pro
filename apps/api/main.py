import os
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from data import repository
from data import runtime_store
from data.database import init_db
from data.mock_data import MATCHES, PERFORMANCE, TEAMS, get_match as get_mock_match
from data.mock_data import get_prediction as get_mock_prediction
from data.mock_data import get_team as get_mock_team
from services.feature_store import build_feature_snapshots, summarize_feature_store
from services.hybrid_decision import build_hybrid_decision
from services.football_data_client import (
    get_champions_league_matches,
    get_champions_league_teams,
    get_ligue1_matches,
    get_ligue1_teams,
)
from services.backtesting import calculate_backtest_report, calculate_snapshot_backtest, get_match_result
from services.elo_model import calculate_team_elos
from services.ml_training import (
    MODEL_VERSION as ML_CANDIDATE_VERSION,
    candidate_model_exists,
    load_latest_candidate_metadata,
    train_candidate_model,
)
from services.ml_shadow import compare_shadow_to_production, generate_shadow_prediction
from services.model_registry import get_model_metadata
from services.prediction_engine import generate_prediction_from_match
from services.prediction_engine import MODEL_VERSION
from services.shadow_backtesting import calculate_shadow_backtest_report


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


def _is_finished(match: dict) -> bool:
    return str(match.get("status", "")).upper() == "FINISHED"


def _kickoff_ts(match: dict) -> float:
    value = match.get("kickoff") or ""
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
    except Exception:
        return 0


def _filter_matches(matches: list[dict], status: str | None = None, q: str | None = None, include_finished: bool = True, view: str = "all"):
    result = list(matches or [])
    normalized_view = (view or "all").lower()
    if normalized_view == "upcoming":
        result = [match for match in result if not _is_finished(match)]
        result.sort(key=_kickoff_ts)
    elif normalized_view == "history":
        result = [match for match in result if _is_finished(match)]
        result.sort(key=_kickoff_ts, reverse=True)
    else:
        if not include_finished:
            result = [match for match in result if not _is_finished(match)]
        result.sort(key=lambda match: (_is_finished(match), _kickoff_ts(match)))

    if status:
        wanted = status.upper()
        if wanted == "UPCOMING":
            result = [match for match in result if not _is_finished(match)]
        elif wanted == "FINISHED":
            result = [match for match in result if _is_finished(match)]
        else:
            result = [match for match in result if str(match.get("status", "")).upper() == wanted]

    if q:
        needle = q.strip().lower()
        result = [
            match
            for match in result
            if needle in " ".join(
                str(match.get(key, ""))
                for key in ("home_team", "away_team", "competition", "slug", "match_id", "id")
            ).lower()
        ]
    return result


def _shadow_memory_rows():
    return runtime_store.get_ml_shadow_predictions()


def _shadow_summary():
    stored = repository.get_ml_shadow_summary()
    if stored.get("shadow_predictions_count"):
        return stored
    rows = _shadow_memory_rows()
    available = [row for row in rows if (row.get("shadow_prediction") or {}).get("available")]
    same = [row for row in rows if (row.get("comparison") or {}).get("same_pick") is True]
    disagreements = [row for row in rows if (row.get("comparison") or {}).get("same_pick") is False]
    high = [row for row in rows if (row.get("comparison") or {}).get("disagreement_level") == "high"]
    return {
        "shadow_predictions_count": len(rows),
        "available_count": len(available),
        "unavailable_count": len(rows) - len(available),
        "same_pick_count": len(same),
        "disagreement_count": len(disagreements),
        "high_disagreement_count": len(high),
        "candidate_model_version": ML_CANDIDATE_VERSION if rows else None,
    }


def _find_shadow(match_id: str):
    stored = repository.get_ml_shadow_prediction(match_id)
    if stored:
        return stored
    return next((row for row in _shadow_memory_rows() if row.get("match_id") == match_id), None)


def _prediction_with_shadow(prediction: dict):
    match_id = prediction.get("match_id") or prediction.get("id") or prediction.get("slug")
    shadow = _find_shadow(match_id)
    enriched = dict(prediction)
    if shadow:
        enriched["shadow"] = {
            "prediction": shadow.get("shadow_prediction"),
            "comparison": shadow.get("comparison"),
        }
    enriched["hybrid"] = build_hybrid_decision(enriched, enriched.get("shadow"))
    return enriched



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


def _shadow_backtesting_report(limit: int = 2000):
    return calculate_shadow_backtest_report(
        _available_matches(),
        repository.get_ml_shadow_predictions(limit=limit) or _shadow_memory_rows(),
    )


def _hybrid_summary():
    shadow_backtesting = _shadow_backtesting_report()
    recommendation = "insufficient_data"
    reason = "Donn?es shadow insuffisantes pour recommander un usage hybride."
    activation_recommendation = shadow_backtesting.get("activation_recommendation")

    if shadow_backtesting.get("evaluated_matches", 0) <= 0:
        recommendation = "insufficient_data"
        reason = "Aucun backtesting shadow exploitable pour le moment."
    elif activation_recommendation in {"consider_hybrid", "candidate_ready_for_limited_rollout"}:
        recommendation = "use_hybrid_advisory"
        reason = "Le candidat ML peut ?tre utilis? comme signal consultatif, sans remplacer Elo/Poisson."
    else:
        recommendation = "keep_official"
        reason = "Le mod?le officiel Elo/Poisson reste prioritaire; le ML reste en observation."

    return {
        "mode": "official_with_shadow_advisory",
        "candidate_is_production": False,
        "production_model_version": MODEL_VERSION,
        "shadow_summary": _shadow_summary(),
        "shadow_backtesting": shadow_backtesting,
        "recommendation": recommendation,
        "reason": reason,
    }


def _admin_workflow_status():
    refresh = _refresh_status()
    feature = _feature_summary()
    candidate = load_latest_candidate_metadata()
    shadow = _shadow_summary()
    shadow_backtesting = _shadow_backtesting_report()
    hybrid = _hybrid_summary()

    if not refresh.get("last_refresh_at"):
        next_step = "refresh_data"
    elif feature.get("snapshots_count", 0) <= 0:
        next_step = "build_feature_store"
    elif candidate.get("status", "not_trained") in {"not_trained", "insufficient_data", "error"}:
        next_step = "train_candidate_model"
    elif shadow.get("shadow_predictions_count", 0) <= 0:
        next_step = "generate_shadow_predictions"
    elif shadow_backtesting.get("evaluated_matches", 0) <= 0:
        next_step = "review_shadow_backtesting"
    else:
        next_step = "ready_for_hybrid_review"

    return {
        "refresh": {
            "last_refresh_at": refresh.get("last_refresh_at"),
            "storage": refresh.get("storage", "memory"),
            "matches_imported": refresh.get("matches_imported", 0),
            "predictions_imported": refresh.get("predictions_imported", 0),
        },
        "feature_store": {
            "ready": feature.get("snapshots_count", 0) > 0,
            "snapshots_count": feature.get("snapshots_count", 0),
            "training_rows_available": feature.get("with_target_count", 0),
            "target_coverage": feature.get("target_coverage", 0),
        },
        "candidate_model": {
            "trained": candidate.get("status") == "ok",
            "status": candidate.get("status", "not_trained"),
            "model_version": candidate.get("model_version"),
            "accuracy": candidate.get("accuracy"),
        },
        "shadow_predictions": {
            "generated": shadow.get("shadow_predictions_count", 0) > 0,
            "count": shadow.get("shadow_predictions_count", 0),
            "disagreement_count": shadow.get("disagreement_count", 0),
        },
        "shadow_backtesting": {
            "ready": shadow_backtesting.get("evaluated_matches", 0) > 0,
            "evaluated_matches": shadow_backtesting.get("evaluated_matches", 0),
            "shadow_accuracy": shadow_backtesting.get("shadow_accuracy", 0),
            "activation_recommendation": shadow_backtesting.get("activation_recommendation", "do_not_activate"),
        },
        "hybrid": {
            "mode": hybrid.get("mode"),
            "recommendation": hybrid.get("recommendation"),
        },
        "next_step": next_step,
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
    finished_matches_count = len([item for item in matches if _is_finished(item)])
    upcoming_matches_count = len(matches) - finished_matches_count
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
    shadow_backtesting = _shadow_backtesting_report()
    hybrid_summary = _hybrid_summary()
    candidate_metadata = load_latest_candidate_metadata()

    return {
        "total_matches": total_matches,
        "teams_count": len(teams),
        "predictions_count": len(predictions),
        "upcoming_matches_count": upcoming_matches_count,
        "historical_matches_count": finished_matches_count,
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
        "ml_candidate_status": candidate_metadata.get("status", "not_trained"),
        "ml_candidate_accuracy": candidate_metadata.get("accuracy"),
        "ml_candidate_model_version": candidate_metadata.get("model_version", "ml-candidate-v1"),
        "ml_shadow_summary": _shadow_summary(),
        "shadow_disagreement_count": _shadow_summary().get("disagreement_count", 0),
        "shadow_high_disagreement_count": _shadow_summary().get("high_disagreement_count", 0),
        "shadow_evaluated_matches": shadow_backtesting.get("evaluated_matches", 0),
        "shadow_accuracy": shadow_backtesting.get("shadow_accuracy", 0),
        "shadow_activation_recommendation": shadow_backtesting.get("activation_recommendation", "do_not_activate"),
        "hybrid_recommendation": hybrid_summary.get("recommendation"),
        "hybrid_mode": hybrid_summary.get("mode"),
        "hybrid_candidate_is_production": hybrid_summary.get("candidate_is_production", False),
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
def list_matches(
    status: str | None = None,
    q: str | None = None,
    include_finished: bool = True,
    view: str = Query(default="all", pattern="^(all|upcoming|history)$"),
):
    return _filter_matches(_available_matches(), status=status, q=q, include_finished=include_finished, view=view)


@app.get("/matches/{match_id}")
def match_detail(match_id: str):
    match = _find_match(match_id)
    if match is None:
        raise HTTPException(status_code=404, detail="Match not found")

    return match


@app.get("/predictions")
def list_predictions(include_hybrid: bool = False):
    predictions = _available_predictions()
    if not include_hybrid:
        return predictions
    return [_prediction_with_shadow(prediction) for prediction in predictions]




@app.get("/predictions/snapshots")
def prediction_snapshots():
    return repository.get_latest_prediction_snapshots(limit=100)

@app.get("/predictions/{match_id}")
def prediction_detail(match_id: str):
    prediction = _find_prediction(match_id)
    if prediction is None:
        raise HTTPException(status_code=404, detail="Prediction not found")

    return _prediction_with_shadow(prediction)


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


@app.get("/ml/status")
def ml_status():
    metadata = load_latest_candidate_metadata()
    return {
        "status": metadata.get("status", "not_trained"),
        "latest_candidate": metadata,
        "feature_store": _feature_summary(),
        "candidate_model_exists": candidate_model_exists(),
        "production_model_version": MODEL_VERSION,
        "candidate_is_production": False,
    }


def _ml_comparison():
    production_report = calculate_backtest_report(_available_matches(), _available_predictions())
    candidate = load_latest_candidate_metadata()
    candidate_status = candidate.get("status", "not_trained")
    candidate_accuracy = candidate.get("accuracy")
    candidate_brier = candidate.get("brier_score_1x2")
    production_accuracy = production_report.get("result_accuracy")
    production_brier = production_report.get("average_brier_score")

    winner_by_accuracy = None
    if candidate_status == "ok" and candidate_accuracy is not None and production_accuracy is not None:
        if candidate_accuracy > production_accuracy:
            winner_by_accuracy = "candidate"
        elif production_accuracy > candidate_accuracy:
            winner_by_accuracy = "production"

    winner_by_brier = None
    if candidate_status == "ok" and candidate_brier is not None and production_brier is not None:
        if candidate_brier < production_brier:
            winner_by_brier = "candidate"
        elif production_brier < candidate_brier:
            winner_by_brier = "production"

    return {
        "production_model_version": MODEL_VERSION,
        "candidate_model_version": ML_CANDIDATE_VERSION,
        "candidate_is_production": False,
        "production": {
            "evaluated_matches": production_report.get("evaluated_matches", 0),
            "result_accuracy": production_accuracy or 0,
            "average_brier_score": production_brier or 0,
            "calibration_score": production_report.get("calibration_score", 0),
        },
        "candidate": {
            "status": candidate_status,
            "rows_used": candidate.get("rows_used", 0),
            "accuracy": candidate_accuracy,
            "log_loss": candidate.get("log_loss"),
            "brier_score_1x2": candidate_brier,
            "trained_at": candidate.get("trained_at"),
        },
        "winner_by_accuracy": winner_by_accuracy,
        "winner_by_brier": winner_by_brier,
        "note": "Le modèle ML candidat est évalué mais n'est pas encore utilisé en production.",
    }


@app.get("/ml/feature-importance")
def ml_feature_importance():
    metadata = load_latest_candidate_metadata()
    return metadata.get("feature_importance") or []


@app.get("/ml/shadow-summary")
def ml_shadow_summary():
    return {
        **_shadow_summary(),
        "candidate_is_production": False,
        "production_model_version": MODEL_VERSION,
    }


@app.get("/ml/shadow-predictions")
def ml_shadow_predictions(limit: int = Query(default=100, ge=1, le=500), view: str = Query(default="all", pattern="^(all|upcoming|history)$")):
    rows = repository.get_ml_shadow_predictions(limit=limit) or _shadow_memory_rows()
    match_ids = {
        match.get("match_id") or match.get("id") or match.get("slug")
        for match in _filter_matches(_available_matches(), view=view)
    }
    if view != "all":
        rows = [row for row in rows if row.get("match_id") in match_ids]
    return rows[:limit]


@app.get("/ml/shadow-backtesting")
def ml_shadow_backtesting(limit: int = Query(default=500, ge=1, le=2000)):
    shadow_records = repository.get_ml_shadow_predictions(limit=limit) or _shadow_memory_rows()
    return calculate_shadow_backtest_report(_available_matches(), shadow_records)


@app.get("/ml/comparison")
def ml_comparison():
    return _ml_comparison()


@app.get("/hybrid/summary")
def hybrid_summary():
    return _hybrid_summary()


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
    shadow_backtesting = _shadow_backtesting_report()

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
        "ml_candidate": load_latest_candidate_metadata(),
        "ml_comparison": _ml_comparison(),
        "ml_shadow_summary": _shadow_summary(),
        "ml_shadow_backtesting": shadow_backtesting,
        "hybrid_summary": _hybrid_summary(),
        "candidate_is_production": False,
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
    }


@app.get("/dashboard/summary")
def dashboard_summary():
    return _dashboard_summary()


@app.get("/admin/refresh-status")
def refresh_status():
    return {"status": "ok", **_refresh_status()}


@app.get("/admin/workflow-status")
def admin_workflow_status():
    return _admin_workflow_status()


@app.post("/admin/refresh-data")
def refresh_data(x_admin_key: str | None = Header(default=None, alias="X-Admin-Key")):
    started_at = time.perf_counter()
    _require_admin_key(x_admin_key)

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

    data_saved = repository.save_matches(matches) and repository.save_teams(teams) and repository.save_predictions(predictions)
    if data_saved:
        storage = "postgresql"
        repository.save_refresh_log(source, storage, len(matches), len(teams))
        try:
            snapshots_saved = repository.save_prediction_snapshots(predictions)
        except Exception:
            snapshots_saved = 0
            warning = "Les donn?es et pr?dictions ont ?t? actualis?es, mais la sauvegarde des snapshots a ?chou?."

    runtime_store.set_matches(matches)
    runtime_store.set_teams(teams)
    runtime_store.set_predictions(predictions)
    runtime_store.set_source(source)
    runtime_store.set_storage(storage)
    status = runtime_store.get_refresh_status()
    duration_ms = round((time.perf_counter() - started_at) * 1000)

    response = {
        "status": "ok",
        "source": source,
        "storage": storage,
        "matches_imported": status["matches_imported"],
        "teams_imported": status["teams_imported"],
        "predictions_imported": status["predictions_imported"],
        "snapshots_saved": snapshots_saved,
        "refresh_duration_ms": duration_ms,
        "next_recommended_actions": [
            "build_feature_store",
            "train_candidate_model",
            "generate_shadow_predictions",
        ],
        "last_refresh_at": status["last_refresh_at"],
    }
    if warning:
        response["warning"] = warning
    return response

@app.post("/admin/build-feature-store")
def build_feature_store(
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
    limit: int = Query(default=500, ge=1, le=2000),
    force: bool = Query(default=False),
) -> dict[str, Any]:
    _require_admin_key(x_admin_key)

    now = datetime.now(timezone.utc).isoformat()

    matches = _available_matches()
    predictions = _available_predictions()

    existing_keys = set()
    if not force:
        try:
            existing_keys = repository.get_feature_snapshot_keys(model_version=MODEL_VERSION)
        except Exception:
            existing_keys = set()

    all_feature_items = build_feature_snapshots(matches, predictions)

    selected_items = []
    skipped_count = 0

    for item in all_feature_items:
        match_id = item.get("match_id")
        model_version = item.get("model_version") or MODEL_VERSION
        key = f"{match_id}:{model_version}"

        if not force and key in existing_keys:
            skipped_count += 1
            continue

        selected_items.append(item)

        if len(selected_items) >= limit:
            break

    saved_count = repository.save_feature_snapshots(selected_items)

    if saved_count > 0:
        storage = "postgresql"
    else:
        storage = "memory"

    if storage == "memory" and selected_items:
        runtime_store.set_feature_snapshots(selected_items)

    training_rows_available = sum(
        1 for item in selected_items if item.get("target") is not None
    )

    target_coverage = (
        round((training_rows_available / len(selected_items)) * 100)
        if selected_items
        else 0
    )

    return {
        "status": "ok",
        "storage": storage,
        "feature_snapshots_built": len(selected_items),
        "feature_snapshots_saved": saved_count,
        "feature_snapshots_skipped": skipped_count,
        "training_rows_available": training_rows_available,
        "target_coverage": target_coverage,
        "model_version": MODEL_VERSION,
        "limit": limit,
        "force": force,
        "created_at": now,
        "note": "Use force=true to rebuild existing snapshots.",
    }


@app.post("/admin/generate-shadow-predictions")
def generate_shadow_predictions_endpoint(
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
    limit: int = Query(default=500, ge=1, le=2000),
    force: bool = Query(default=False),
    view: str = Query(default="upcoming", pattern="^(all|upcoming|history)$"),
) -> dict[str, Any]:
    _require_admin_key(x_admin_key)

    now = datetime.now(timezone.utc).isoformat()
    all_matches = _available_matches()
    target_matches = _filter_matches(all_matches, view=view)
    predictions = _available_predictions()
    predictions_by_id = {
        item.get("match_id") or item.get("id") or item.get("slug"): item
        for item in predictions
    }

    existing_ids = set()
    if not force:
        existing_rows = repository.get_ml_shadow_predictions(limit=2000) or _shadow_memory_rows()
        existing_ids = {row.get("match_id") for row in existing_rows if row.get("match_id")}

    items = []
    elo_ratings = calculate_team_elos(all_matches)

    for match in target_matches:
        match_id = match.get("match_id") or match.get("id") or match.get("slug")
        if not match_id or (not force and match_id in existing_ids):
            continue

        production_prediction = predictions_by_id.get(match_id) or _prediction_for_match(match, all_matches, elo_ratings)
        shadow_prediction = generate_shadow_prediction(match, production_prediction)
        comparison = compare_shadow_to_production(production_prediction, shadow_prediction)
        items.append(
            {
                "match_id": match_id,
                "production_prediction": production_prediction,
                "shadow_prediction": shadow_prediction,
                "comparison": comparison,
                "created_at": now,
            }
        )

        if len(items) >= limit:
            break

    saved_count = repository.save_ml_shadow_predictions(items)
    storage = "postgresql" if saved_count > 0 else "memory"
    if storage == "memory" and items:
        previous_rows = [] if force else _shadow_memory_rows()
        runtime_store.set_ml_shadow_predictions(items + previous_rows)

    available_count = sum(1 for item in items if item["shadow_prediction"].get("available"))
    same_pick_count = sum(1 for item in items if item["comparison"].get("same_pick") is True)
    disagreement_count = sum(1 for item in items if item["comparison"].get("same_pick") is False)
    high_disagreement_count = sum(1 for item in items if item["comparison"].get("disagreement_level") == "high")

    return {
        "status": "ok",
        "storage": storage,
        "view": view,
        "shadow_predictions_generated": len(items),
        "shadow_predictions_saved": saved_count if storage == "postgresql" else len(items),
        "available_count": available_count,
        "unavailable_count": len(items) - available_count,
        "same_pick_count": same_pick_count,
        "disagreement_count": disagreement_count,
        "high_disagreement_count": high_disagreement_count,
        "candidate_is_production": False,
        "created_at": now,
        "note": "Les pr?dictions ML shadow sont calcul?es en parall?le et ne remplacent pas le mod?le officiel.",
    }


@app.post("/admin/train-candidate-model")
def train_candidate_model_endpoint(
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
    model_type: str = Query(default="random_forest"),
    limit: int = Query(default=5000, ge=1, le=10000),
) -> dict[str, Any]:
    _require_admin_key(x_admin_key)

    feature_rows = repository.get_training_dataset(limit=limit)
    if not feature_rows:
        feature_rows = _training_dataset(limit=limit)

    return train_candidate_model(feature_rows, model_type=model_type)
