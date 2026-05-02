import json
import logging
import uuid
from datetime import datetime

from sqlalchemy import text

from data.database import db_available, execute_safe, fetch_all_safe, fetch_one_safe

logger = logging.getLogger(__name__)
MODEL_VERSION = "FootIQ-Pro v0.5"


def _json(data) -> str:
    return json.dumps(data, ensure_ascii=False)


def _loads(value: str | None):
    if not value:
        return None

    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return None


def _now() -> datetime:
    return datetime.utcnow()


def save_teams(teams: list[dict]) -> bool:
    if not teams or not db_available():
        return False

    statement = text(
        """
        INSERT INTO teams (id, slug, name, competition, source, raw_json, updated_at)
        VALUES (:id, :slug, :name, :competition, :source, :raw_json, :updated_at)
        ON CONFLICT (id) DO UPDATE SET
            slug = EXCLUDED.slug,
            name = EXCLUDED.name,
            competition = EXCLUDED.competition,
            source = EXCLUDED.source,
            raw_json = EXCLUDED.raw_json,
            updated_at = EXCLUDED.updated_at
        """
    )
    ok = True

    for team in teams:
        ok = execute_safe(
            statement,
            {
                "id": team.get("id") or team.get("slug"),
                "slug": team.get("slug") or team.get("id"),
                "name": team.get("name"),
                "competition": team.get("competition"),
                "source": team.get("source", "unknown"),
                "raw_json": _json(team),
                "updated_at": _now(),
            },
        ) and ok

    return ok


def get_teams() -> list[dict]:
    rows = fetch_all_safe(text("SELECT raw_json FROM teams ORDER BY competition, name"))
    return [team for team in (_loads(row.get("raw_json")) for row in rows) if team]


def get_team(team_id: str) -> dict | None:
    row = fetch_one_safe(
        text("SELECT raw_json FROM teams WHERE id = :team_id OR slug = :team_id LIMIT 1"),
        {"team_id": team_id},
    )
    return _loads(row.get("raw_json")) if row else None


def save_matches(matches: list[dict]) -> bool:
    if not matches or not db_available():
        return False

    statement = text(
        """
        INSERT INTO matches (
            id, match_id, slug, home_team, away_team, competition, kickoff, status, source, raw_json, updated_at
        )
        VALUES (
            :id, :match_id, :slug, :home_team, :away_team, :competition, :kickoff, :status, :source, :raw_json, :updated_at
        )
        ON CONFLICT (id) DO UPDATE SET
            match_id = EXCLUDED.match_id,
            slug = EXCLUDED.slug,
            home_team = EXCLUDED.home_team,
            away_team = EXCLUDED.away_team,
            competition = EXCLUDED.competition,
            kickoff = EXCLUDED.kickoff,
            status = EXCLUDED.status,
            source = EXCLUDED.source,
            raw_json = EXCLUDED.raw_json,
            updated_at = EXCLUDED.updated_at
        """
    )
    ok = True

    for match in matches:
        match_id = match.get("match_id") or match.get("id") or match.get("slug")
        ok = execute_safe(
            statement,
            {
                "id": match.get("id") or match_id,
                "match_id": match_id,
                "slug": match.get("slug") or match_id,
                "home_team": match.get("home_team"),
                "away_team": match.get("away_team"),
                "competition": match.get("competition"),
                "kickoff": match.get("kickoff"),
                "status": match.get("status"),
                "source": match.get("source", "unknown"),
                "raw_json": _json(match),
                "updated_at": _now(),
            },
        ) and ok

    return ok


def get_matches() -> list[dict]:
    rows = fetch_all_safe(text("SELECT raw_json FROM matches ORDER BY kickoff"))
    return [match for match in (_loads(row.get("raw_json")) for row in rows) if match]


def get_match(match_id: str) -> dict | None:
    row = fetch_one_safe(
        text("SELECT raw_json FROM matches WHERE id = :match_id OR match_id = :match_id OR slug = :match_id LIMIT 1"),
        {"match_id": match_id},
    )
    return _loads(row.get("raw_json")) if row else None


def save_predictions(predictions: list[dict]) -> bool:
    if not predictions or not db_available():
        return False

    statement = text(
        """
        INSERT INTO predictions (id, match_id, slug, payload_json, model_version, created_at)
        VALUES (:id, :match_id, :slug, :payload_json, :model_version, :created_at)
        ON CONFLICT (id) DO UPDATE SET
            match_id = EXCLUDED.match_id,
            slug = EXCLUDED.slug,
            payload_json = EXCLUDED.payload_json,
            model_version = EXCLUDED.model_version,
            created_at = EXCLUDED.created_at
        """
    )
    ok = True

    for prediction in predictions:
        prediction_id = prediction.get("id") or prediction.get("match_id") or prediction.get("slug")
        ok = execute_safe(
            statement,
            {
                "id": prediction_id,
                "match_id": prediction.get("match_id") or prediction_id,
                "slug": prediction.get("slug") or prediction_id,
                "payload_json": _json(prediction),
                "model_version": MODEL_VERSION,
                "created_at": _now(),
            },
        ) and ok

    return ok


def get_predictions() -> list[dict]:
    rows = fetch_all_safe(text("SELECT payload_json FROM predictions ORDER BY created_at DESC"))
    return [prediction for prediction in (_loads(row.get("payload_json")) for row in rows) if prediction]


def get_prediction(match_id: str) -> dict | None:
    row = fetch_one_safe(
        text(
            """
            SELECT payload_json FROM predictions
            WHERE id = :match_id OR match_id = :match_id OR slug = :match_id
            LIMIT 1
            """
        ),
        {"match_id": match_id},
    )
    return _loads(row.get("payload_json")) if row else None


def save_refresh_log(source: str, storage: str, matches_imported: int, teams_imported: int) -> bool:
    if not db_available():
        return False

    return execute_safe(
        text(
            """
            INSERT INTO refresh_logs (id, source, storage, matches_imported, teams_imported, created_at)
            VALUES (:id, :source, :storage, :matches_imported, :teams_imported, :created_at)
            """
        ),
        {
            "id": str(uuid.uuid4()),
            "source": source,
            "storage": storage,
            "matches_imported": matches_imported,
            "teams_imported": teams_imported,
            "created_at": _now(),
        },
    )


def get_latest_refresh_log() -> dict | None:
    row = fetch_one_safe(
        text(
            """
            SELECT source, storage, matches_imported, teams_imported, created_at
            FROM refresh_logs
            ORDER BY created_at DESC
            LIMIT 1
            """
        )
    )

    if not row:
        return None

    created_at = row.get("created_at")
    return {
        "source": row.get("source"),
        "storage": row.get("storage"),
        "matches_imported": row.get("matches_imported"),
        "teams_imported": row.get("teams_imported"),
        "last_refresh_at": created_at.isoformat() if hasattr(created_at, "isoformat") else created_at,
    }
