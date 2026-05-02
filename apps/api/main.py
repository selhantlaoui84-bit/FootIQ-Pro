import os

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from data import runtime_store
from data.mock_data import MATCHES, PERFORMANCE, TEAMS, get_match as get_mock_match
from data.mock_data import get_prediction as get_mock_prediction
from data.mock_data import get_team as get_mock_team
from services.football_data_client import (
    get_champions_league_matches,
    get_champions_league_teams,
    get_ligue1_matches,
    get_ligue1_teams,
)
from services.prediction_engine import generate_prediction_from_match

app = FastAPI(title="FootIQ Pro API", version="0.4.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _available_matches():
    return runtime_store.get_matches() or MATCHES


def _available_teams():
    return runtime_store.get_teams() or TEAMS


def _find_match(match_id: str):
    return next(
        (
            item
            for item in runtime_store.get_matches()
            if item.get("id") == match_id or item.get("match_id") == match_id or item.get("slug") == match_id
        ),
        None,
    ) or get_mock_match(match_id)


def _find_team(team_id: str):
    return next(
        (item for item in runtime_store.get_teams() if item.get("id") == team_id or item.get("slug") == team_id),
        None,
    ) or get_mock_team(team_id)


def _prediction_for_match(match: dict):
    if "probabilities" in match and "confidence" in match:
        return match

    return generate_prediction_from_match(match)


def _dashboard_summary():
    matches = _available_matches()
    predictions = [_prediction_for_match(match) for match in matches]
    total_matches = len(matches)
    reliable = [item for item in predictions if item["confidence"]["status"] == "FIABLE"]
    medium = [item for item in predictions if item["confidence"]["status"] == "MOYEN"]
    avoid = [item for item in predictions if item["confidence"]["status"] in {"À ÉVITER", "A EVITER"}]
    traps = [item for item in predictions if item["flags"]["trap_match"]]
    status = runtime_store.get_refresh_status()
    competitions = {}

    for match in matches:
        competition = match.get("competition", "Unknown")
        competitions[competition] = competitions.get(competition, 0) + 1

    average_confidence = 0
    if predictions:
        average_confidence = round(sum(item["confidence"]["score"] for item in predictions) / len(predictions))

    return {
        "total_matches": total_matches,
        "upcoming_matches_count": total_matches,
        "reliable_matches_count": len(reliable),
        "medium_matches_count": len(medium),
        "avoid_matches_count": len(avoid),
        "trap_matches_count": len(traps),
        "average_confidence": average_confidence,
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
        "last_refresh_at": status["last_refresh_at"],
        "source": status["source"],
    }


def _require_admin_key(x_admin_key: str | None):
    env = os.getenv("ENV", "development").lower()
    admin_key = os.getenv("ADMIN_API_KEY")

    if not admin_key and env != "production":
        return

    if not admin_key or x_admin_key != admin_key:
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
    return [_prediction_for_match(match) for match in _available_matches()]


@app.get("/predictions/{match_id}")
def prediction_detail(match_id: str):
    match = _find_match(match_id)
    if match is not None:
        return _prediction_for_match(match)

    prediction = get_mock_prediction(match_id)
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


@app.get("/performance")
def model_performance():
    return {**PERFORMANCE, "latest_refresh": runtime_store.get_refresh_status()}


@app.get("/dashboard/summary")
def dashboard_summary():
    return _dashboard_summary()


@app.get("/admin/refresh-status")
def refresh_status():
    return {"status": "ok", **runtime_store.get_refresh_status()}


@app.post("/admin/refresh-data")
def refresh_data(x_admin_key: str | None = Header(default=None, alias="X-Admin-Key")):
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

    runtime_store.set_matches(matches)
    runtime_store.set_teams(teams)
    runtime_store.set_source(source)
    status = runtime_store.get_refresh_status()

    return {
        "status": "ok",
        "source": source,
        "storage": status.get("storage", "memory"),
        "matches_imported": status["matches_imported"],
        "teams_imported": status["teams_imported"],
        "last_refresh_at": status["last_refresh_at"],
    }
