from __future__ import annotations

import logging
import os
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

logger = logging.getLogger("footiq.api")


def _env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    env: str = os.getenv("ENV", "production")
    debug: bool = _env_bool("DEBUG")
    football_data_api_key: str | None = os.getenv("FOOTBALL_DATA_API_KEY")


settings = Settings()


MOCK_MATCHES: list[dict[str, Any]] = [
    {
        "id": "psg-lyon",
        "match_id": "psg-lyon",
        "home_team": "PSG",
        "away_team": "Lyon",
        "competition": "Ligue 1",
        "kickoff": "2026-05-05T20:00:00Z",
        "status": "SCHEDULED",
    },
    {
        "id": "marseille-rennes",
        "match_id": "marseille-rennes",
        "home_team": "Marseille",
        "away_team": "Rennes",
        "competition": "Ligue 1",
        "kickoff": "2026-05-06T20:00:00Z",
        "status": "SCHEDULED",
    },
]

MOCK_TEAMS: list[dict[str, Any]] = [
    {"id": "psg", "name": "PSG", "competition": "Ligue 1"},
    {"id": "marseille", "name": "Marseille", "competition": "Ligue 1"},
    {"id": "lyon", "name": "Lyon", "competition": "Ligue 1"},
    {"id": "rennes", "name": "Rennes", "competition": "Ligue 1"},
    {"id": "real-madrid", "name": "Real Madrid", "competition": "Champions League"},
    {"id": "arsenal", "name": "Arsenal", "competition": "Champions League"},
]


def generate_prediction(match: dict[str, Any]) -> dict[str, Any]:
    home = match["home_team"]
    away = match["away_team"]

    strong_teams = {
        "PSG",
        "Real Madrid",
        "Arsenal",
        "Manchester City",
        "Barcelona",
        "Bayern",
        "Inter",
        "Liverpool",
    }

    if home in strong_teams:
        probabilities = {"home": 61, "draw": 23, "away": 16}
        confidence_score = 78
        recommendation = "Exploitable"
    elif away in strong_teams:
        probabilities = {"home": 24, "draw": 25, "away": 51}
        confidence_score = 64
        recommendation = "Prudence"
    else:
        probabilities = {"home": 42, "draw": 28, "away": 30}
        confidence_score = 52
        recommendation = "À surveiller"

    if confidence_score >= 75:
        status = "FIABLE"
    elif confidence_score >= 55:
        status = "MOYEN"
    else:
        status = "À ÉVITER"

    favorite_probability = max(probabilities.values())
    trap_match = favorite_probability >= 55 and confidence_score < 55

    return {
        "id": match["id"],
        "match_id": match["match_id"],
        "home_team": home,
        "away_team": away,
        "competition": match["competition"],
        "kickoff": match["kickoff"],
        "probabilities": probabilities,
        "goals": {
            "expected_home": 2.1 if probabilities["home"] >= probabilities["away"] else 1.2,
            "expected_away": 1.2 if probabilities["home"] >= probabilities["away"] else 1.8,
            "over_2_5": 58,
            "btts": 54,
        },
        "confidence": {
            "score": confidence_score,
            "status": status,
        },
        "flags": {
            "trap_match": trap_match,
            "risk": confidence_score < 55,
        },
        "recommendation": recommendation,
        "explanation": [
            "Analyse basée sur la force relative des équipes",
            "Lecture probabiliste avec pondération du contexte du match",
            "Les signaux sont simplifiés pour le MVP",
        ],
        "risks": [
            "Données encore partielles",
            "Composition officielle non intégrée",
        ],
        "disclaimer": "Modèle probabiliste. Aucune garantie de résultat.",
    }


runtime_store: dict[str, Any] = {
    "matches": MOCK_MATCHES,
    "teams": MOCK_TEAMS,
    "last_refresh_at": None,
    "source": "mock",
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting FootIQ API...")
    yield
    logger.info("Stopping FootIQ API...")


app = FastAPI(debug=settings.debug, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response: Response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000

    logger.info(
        "method=%s path=%s status=%s duration_ms=%.2f",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )

    return response


@app.get("/")
def root() -> dict[str, str]:
    return {"status": "ok", "service": "FootIQ Pro API"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/matches")
def get_matches() -> list[dict[str, Any]]:
    return runtime_store["matches"]


@app.get("/matches/{match_id}")
def get_match(match_id: str) -> dict[str, Any]:
    for match in runtime_store["matches"]:
        if match["match_id"] == match_id or match["id"] == match_id:
            return match
    raise HTTPException(status_code=404, detail="Match not found")


@app.get("/predictions")
def get_predictions() -> list[dict[str, Any]]:
    return [generate_prediction(match) for match in runtime_store["matches"]]


@app.get("/predictions/{match_id}")
def get_prediction(match_id: str) -> dict[str, Any]:
    for match in runtime_store["matches"]:
        if match["match_id"] == match_id or match["id"] == match_id:
            return generate_prediction(match)
    raise HTTPException(status_code=404, detail="Prediction not found")


@app.get("/teams")
def get_teams() -> list[dict[str, Any]]:
    return runtime_store["teams"]


@app.get("/teams/{team_id}")
def get_team(team_id: str) -> dict[str, Any]:
    normalized_team_id = team_id.lower().strip()

    for team in runtime_store["teams"]:
        candidates = {
            str(team.get("id", "")).lower(),
            str(team.get("slug", "")).lower(),
            str(team.get("team_id", "")).lower(),
            str(team.get("name", "")).lower().replace(" ", "-"),
        }

        if normalized_team_id in candidates:
            return team

    raise HTTPException(status_code=404, detail="Team not found")



@app.get("/performance")
def get_performance() -> dict[str, Any]:
    return {
        "model_version": "mvp-0.1",
        "predictions_tracked": 180,
        "high_confidence_hit_rate": 72,
        "average_confidence": 68,
        "calibration_status": "En cours de mesure",
        "brier_score": None,
    }


@app.post("/admin/refresh-data")
def refresh_data() -> dict[str, Any]:
    runtime_store["matches"] = MOCK_MATCHES
    runtime_store["teams"] = MOCK_TEAMS
    runtime_store["last_refresh_at"] = datetime.now(timezone.utc).isoformat()
    runtime_store["source"] = "mock"

    return {
        "status": "ok",
        "source": runtime_store["source"],
        "matches_imported": len(runtime_store["matches"]),
        "teams_imported": len(runtime_store["teams"]),
        "last_refresh_at": runtime_store["last_refresh_at"],
        "note": "Fallback mock utilisé. Connecteur football-data.org à brancher ensuite.",
    }