import json
import logging
import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import text

from data.database import db_available, execute_safe, fetch_all_safe, fetch_one_safe, get_engine, init_db
from services.advanced_features import ADVANCED_FEATURE_COLUMNS, FEATURE_SET_VERSION

logger = logging.getLogger(__name__)
MODEL_VERSION = "elo-poisson-calibrated-v1"
_last_feature_snapshot_save_report = {
    "saved_count": 0,
    "inserted_count": 0,
    "updated_count": 0,
    "skipped_existing_count": 0,
    "failed_count": 0,
    "errors": [],
}


def _json(data) -> str:
    return json.dumps(data, ensure_ascii=False)


def _loads(value: str | None):
    if not value:
        return None

    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return None




def _match_payload_from_row(row: dict | None):
    if not row:
        return None

    match = _loads(row.get("raw_json")) or {}
    if row.get("status") is not None:
        match["status"] = str(row.get("status") or "").upper()

    for key in (
        "score_full_time_home",
        "score_full_time_away",
        "score_half_time_home",
        "score_half_time_away",
        "winner",
    ):
        value = row.get(key)
        if value is not None:
            match[key] = value
    return match or None


def _now() -> datetime:
    return datetime.utcnow()


def _iso(value):
    return value.isoformat() if hasattr(value, "isoformat") else value


def _parse_datetime(value):
    if not value:
        return None
    if hasattr(value, "isoformat"):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


def _num_or_none(value):
    try:
        if value is None or value == "":
            return None
        return float(value)
    except Exception:
        return None


def _int_or_zero(value):
    try:
        return int(value or 0)
    except Exception:
        return 0


def _feature_count(value, metrics: dict | None = None) -> int:
    if isinstance(value, list):
        return len(value)
    if isinstance(value, dict):
        return len(value)
    count = _int_or_zero(value)
    if count:
        return count
    metrics = metrics or {}
    for key in ("features_used", "feature_columns_count"):
        candidate = metrics.get(key)
        if isinstance(candidate, list):
            return len(candidate)
        count = _int_or_zero(candidate)
        if count:
            return count
    return 0


def _winner_from_score(winner, home_score, away_score):
    if winner:
        return winner
    if home_score is None or away_score is None:
        return None
    if home_score > away_score:
        return "HOME_TEAM"
    if away_score > home_score:
        return "AWAY_TEAM"
    return "DRAW"


def normalize_match_for_storage(match: dict) -> dict:
    normalized = dict(match or {})
    raw_status = normalized.get("raw_status", normalized.get("status", "SCHEDULED"))
    normalized["raw_status"] = raw_status
    normalized["status"] = str(raw_status or "SCHEDULED").upper()

    score = normalized.get("score") if isinstance(normalized.get("score"), dict) else {}
    full_time = score.get("fullTime") if isinstance(score.get("fullTime"), dict) else {}
    half_time = score.get("halfTime") if isinstance(score.get("halfTime"), dict) else {}

    normalized["score_full_time_home"] = normalized.get("score_full_time_home", full_time.get("home"))
    normalized["score_full_time_away"] = normalized.get("score_full_time_away", full_time.get("away"))
    normalized["score_half_time_home"] = normalized.get("score_half_time_home", half_time.get("home"))
    normalized["score_half_time_away"] = normalized.get("score_half_time_away", half_time.get("away"))
    normalized["winner"] = _winner_from_score(
        normalized.get("winner") or score.get("winner"),
        normalized.get("score_full_time_home"),
        normalized.get("score_full_time_away"),
    )
    return normalized


def normalize_prediction_for_storage(prediction: dict, fallback_id: str | None = None) -> dict:
    normalized = dict(prediction or {})
    prediction_id = normalized.get("id") or normalized.get("match_id") or normalized.get("slug") or fallback_id
    if not prediction_id:
        raise ValueError("Prediction missing id, match_id and slug")

    prediction_id = str(prediction_id)
    normalized["id"] = str(normalized.get("id") or prediction_id)
    normalized["match_id"] = str(normalized.get("match_id") or prediction_id)
    normalized["slug"] = str(normalized.get("slug") or normalized["match_id"])
    normalized["model_version"] = normalized.get("model_version") or MODEL_VERSION
    return normalized


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


def count_teams() -> int:
    row = fetch_one_safe(text("SELECT COUNT(*) AS count FROM teams"))
    return int(row.get("count", 0)) if row else 0


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
            id, match_id, slug, home_team, away_team, competition, kickoff, status, source,
            score_full_time_home, score_full_time_away, score_half_time_home, score_half_time_away, winner,
            raw_json, updated_at
        )
        VALUES (
            :id, :match_id, :slug, :home_team, :away_team, :competition, :kickoff, :status, :source,
            :score_full_time_home, :score_full_time_away, :score_half_time_home, :score_half_time_away, :winner,
            :raw_json, :updated_at
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
            score_full_time_home = EXCLUDED.score_full_time_home,
            score_full_time_away = EXCLUDED.score_full_time_away,
            score_half_time_home = EXCLUDED.score_half_time_home,
            score_half_time_away = EXCLUDED.score_half_time_away,
            winner = EXCLUDED.winner,
            raw_json = EXCLUDED.raw_json,
            updated_at = EXCLUDED.updated_at
        """
    )
    ok = True

    for match in matches:
        match = normalize_match_for_storage(match)
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
                "score_full_time_home": match.get("score_full_time_home"),
                "score_full_time_away": match.get("score_full_time_away"),
                "score_half_time_home": match.get("score_half_time_home"),
                "score_half_time_away": match.get("score_half_time_away"),
                "winner": match.get("winner"),
                "raw_json": _json(match),
                "updated_at": _now(),
            },
        ) and ok

    return ok


def get_matches() -> list[dict]:
    rows = fetch_all_safe(
        text(
            """
            SELECT raw_json, status, score_full_time_home, score_full_time_away, score_half_time_home,
                   score_half_time_away, winner
            FROM matches
            ORDER BY kickoff
            """
        )
    )
    return [match for match in (_match_payload_from_row(row) for row in rows) if match]


def count_matches() -> int:
    row = fetch_one_safe(text("SELECT COUNT(*) AS count FROM matches"))
    return int(row.get("count", 0)) if row else 0


def get_match(match_id: str) -> dict | None:
    row = fetch_one_safe(
        text(
            """
            SELECT raw_json, status, score_full_time_home, score_full_time_away, score_half_time_home,
                   score_half_time_away, winner
            FROM matches
            WHERE id = :match_id OR match_id = :match_id OR slug = :match_id
            LIMIT 1
            """
        ),
        {"match_id": match_id},
    )
    return _match_payload_from_row(row)


def save_predictions(predictions: list[dict]) -> dict:
    report = {"saved_count": 0, "failed_count": 0, "errors": []}
    if not predictions:
        return report

    engine = get_engine()
    if engine is None:
        report["failed_count"] = len(predictions)
        report["errors"].append("DATABASE_URL missing or PostgreSQL engine unavailable")
        return report

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

    for index, prediction in enumerate(predictions):
        try:
            normalized = normalize_prediction_for_storage(prediction, fallback_id=f"prediction-{index}")
            with engine.begin() as connection:
                connection.execute(
                    statement,
                    {
                        "id": normalized["id"],
                        "match_id": normalized["match_id"],
                        "slug": normalized["slug"],
                        "payload_json": _json(normalized),
                        "model_version": normalized["model_version"],
                        "created_at": _now(),
                    },
                )
            report["saved_count"] += 1
        except Exception as exc:
            report["failed_count"] += 1
            if len(report["errors"]) < 5:
                report["errors"].append(str(exc))
            logger.exception("Prediction insert failed")

    return report


def count_predictions() -> int:
    row = fetch_one_safe(text("SELECT COUNT(*) AS count FROM predictions"))
    return int(row.get("count", 0)) if row else 0


def sample_prediction_db() -> dict | None:
    row = fetch_one_safe(
        text(
            """
            SELECT id, match_id, slug, model_version, payload_json, created_at
            FROM predictions
            ORDER BY created_at DESC
            LIMIT 1
            """
        )
    )
    if not row:
        return None
    payload = _loads(row.get("payload_json")) or {}
    return {
        "id": row.get("id"),
        "match_id": row.get("match_id"),
        "slug": row.get("slug"),
        "model_version": row.get("model_version"),
        "created_at": row.get("created_at").isoformat() if hasattr(row.get("created_at"), "isoformat") else row.get("created_at"),
        "payload": payload,
    }


def _prediction_payload_from_row(row: dict | None):
    if not row:
        return None
    prediction = _loads(row.get("payload_json")) or {}
    prediction["id"] = prediction.get("id") or row.get("id")
    prediction["match_id"] = prediction.get("match_id") or row.get("match_id") or prediction["id"]
    prediction["slug"] = prediction.get("slug") or row.get("slug") or prediction["match_id"]
    prediction["model_version"] = prediction.get("model_version") or row.get("model_version") or MODEL_VERSION
    return prediction if prediction.get("match_id") else None


def get_predictions() -> list[dict]:
    rows = fetch_all_safe(
        text(
            """
            SELECT id, match_id, slug, model_version, payload_json
            FROM predictions
            ORDER BY created_at DESC
            """
        )
    )
    return [prediction for prediction in (_prediction_payload_from_row(row) for row in rows) if prediction]


def get_prediction(match_id: str) -> dict | None:
    row = fetch_one_safe(
        text(
            """
            SELECT id, match_id, slug, model_version, payload_json FROM predictions
            WHERE id = :match_id OR match_id = :match_id OR slug = :match_id
            LIMIT 1
            """
        ),
        {"match_id": match_id},
    )
    return _prediction_payload_from_row(row)


def init_bookmaker_odds_schema() -> bool:
    return init_db()


def _odds_from_row(row: dict | None) -> dict | None:
    if not row:
        return None
    return {
        "id": row.get("id"),
        "match_id": row.get("match_id"),
        "bookmaker": row.get("bookmaker"),
        "market": row.get("market"),
        "selection": row.get("selection"),
        "odds_decimal": _num_or_none(row.get("odds_decimal")),
        "implied_probability": _num_or_none(row.get("implied_probability")),
        "margin": _num_or_none(row.get("margin")),
        "provider": row.get("provider"),
        "provider_event_id": row.get("provider_event_id"),
        "provider_market_id": row.get("provider_market_id"),
        "raw": _loads(row.get("raw_json")) or {},
        "collected_at": _iso(row.get("collected_at")),
        "expires_at": _iso(row.get("expires_at")),
        "stale": bool(row.get("stale")) if row.get("stale") is not None else False,
        "source": row.get("source"),
        "source_type": "manual_user_input" if row.get("source") == "manual_user_input" else "provider",
        "created_at": _iso(row.get("created_at")),
    }


def upsert_bookmaker_odds(odds: dict) -> dict | None:
    if not odds or not db_available():
        return None
    init_bookmaker_odds_schema()
    odds_id = odds.get("id") or str(uuid.uuid4())
    odds_decimal = _num_or_none(odds.get("odds_decimal") or odds.get("odds"))
    implied_probability = _num_or_none(odds.get("implied_probability"))
    if implied_probability is None and odds_decimal and odds_decimal > 1:
        implied_probability = round(1 / odds_decimal, 4)
    row = {
        "id": odds_id,
        "match_id": str(odds.get("match_id") or ""),
        "bookmaker": odds.get("bookmaker") or "reference",
        "market": odds.get("market") or "1X2",
        "selection": odds.get("selection") or "",
        "odds_decimal": odds_decimal,
        "implied_probability": implied_probability,
        "margin": _num_or_none(odds.get("margin")),
        "provider": odds.get("provider") or odds.get("source") or "unknown",
        "provider_event_id": odds.get("provider_event_id"),
        "provider_market_id": odds.get("provider_market_id"),
        "raw_json": _json(odds.get("raw") or odds.get("raw_json") or odds),
        "collected_at": _parse_datetime(odds.get("collected_at")) or _now(),
        "expires_at": _parse_datetime(odds.get("expires_at")),
        "stale": bool(odds.get("stale", False)),
        "source": odds.get("source") or "system",
        "created_at": _parse_datetime(odds.get("created_at")) or _now(),
    }
    if not row["match_id"] or not row["selection"] or odds_decimal is None or odds_decimal <= 1:
        return None
    execute_safe(
        text(
            """
            INSERT INTO bookmaker_odds (
                id, match_id, bookmaker, market, selection, odds_decimal, implied_probability,
                margin, provider, provider_event_id, provider_market_id, raw_json, collected_at,
                expires_at, stale, source, created_at
            )
            VALUES (
                :id, :match_id, :bookmaker, :market, :selection, :odds_decimal, :implied_probability,
                :margin, :provider, :provider_event_id, :provider_market_id, :raw_json, :collected_at,
                :expires_at, :stale, :source, :created_at
            )
            ON CONFLICT (id) DO UPDATE SET
                odds_decimal = EXCLUDED.odds_decimal,
                implied_probability = EXCLUDED.implied_probability,
                margin = EXCLUDED.margin,
                provider = EXCLUDED.provider,
                provider_event_id = EXCLUDED.provider_event_id,
                provider_market_id = EXCLUDED.provider_market_id,
                raw_json = EXCLUDED.raw_json,
                collected_at = EXCLUDED.collected_at,
                expires_at = EXCLUDED.expires_at,
                stale = EXCLUDED.stale,
                source = EXCLUDED.source
            """
        ),
        row,
    )
    return _odds_from_row(fetch_one_safe(text("SELECT * FROM bookmaker_odds WHERE id = :id LIMIT 1"), {"id": odds_id}))


def list_match_odds(match_id: str) -> list[dict]:
    if not match_id or not db_available():
        return []
    rows = fetch_all_safe(
        text(
            """
            SELECT *
            FROM bookmaker_odds
            WHERE match_id = :match_id
            ORDER BY collected_at DESC, created_at DESC
            """
        ),
        {"match_id": str(match_id)},
    )
    return [item for item in (_odds_from_row(row) for row in rows) if item]


def get_latest_odds_for_prediction(match_id: str, market: str, selection: str) -> dict | None:
    if not match_id or not market or not selection or not db_available():
        return None
    row = fetch_one_safe(
        text(
            """
            SELECT *
            FROM bookmaker_odds
            WHERE match_id = :match_id
              AND lower(market) = lower(:market)
              AND lower(selection) = lower(:selection)
            ORDER BY collected_at DESC, created_at DESC
            LIMIT 1
            """
        ),
        {"match_id": str(match_id), "market": market, "selection": selection},
    )
    return _odds_from_row(row)


def get_best_odds_for_prediction(match_id: str, market: str, selection: str) -> dict | None:
    if not match_id or not market or not selection or not db_available():
        return None
    row = fetch_one_safe(
        text(
            """
            SELECT *
            FROM bookmaker_odds
            WHERE match_id = :match_id
              AND lower(market) = lower(:market)
              AND lower(selection) = lower(:selection)
            ORDER BY odds_decimal DESC NULLS LAST, collected_at DESC
            LIMIT 1
            """
        ),
        {"match_id": str(match_id), "market": market, "selection": selection},
    )
    return _odds_from_row(row)


def get_reference_odds_for_prediction(match_id: str, market: str, selection: str) -> dict | None:
    return get_best_odds_for_prediction(match_id, market, selection) or get_latest_odds_for_prediction(match_id, market, selection)


def _is_real_or_manual_odds(odds: dict | None) -> bool:
    if not odds:
        return False
    source = str(odds.get("source") or "").lower()
    provider = str(odds.get("provider") or "").lower()
    return source in {"real_provider", "manual_user_input"} or provider not in {"", "unknown", "system", "prediction", "mock"}


def save_real_bookmaker_odds(odds: dict) -> dict | None:
    source = str((odds or {}).get("source") or "real_provider")
    if source not in {"real_provider", "manual_user_input"}:
        return None
    saved = upsert_bookmaker_odds({**odds, "source": source})
    return saved if _is_real_or_manual_odds(saved) else None


def list_match_real_odds(match_id: str) -> list[dict]:
    return [item for item in list_match_odds(match_id) if _is_real_or_manual_odds(item)]


def get_latest_real_odds(match_id: str, market: str, selection: str) -> dict | None:
    odds = get_latest_odds_for_prediction(match_id, market, selection)
    return odds if _is_real_or_manual_odds(odds) else None


def get_best_real_odds(match_id: str, market: str, selection: str) -> dict | None:
    odds = get_best_odds_for_prediction(match_id, market, selection)
    return odds if _is_real_or_manual_odds(odds) else None


def get_reference_real_odds(match_id: str, market: str, selection: str) -> dict | None:
    return get_best_real_odds(match_id, market, selection) or get_latest_real_odds(match_id, market, selection)


def mark_odds_stale(match_id: str | None = None) -> int:
    if not db_available():
        return 0
    params = {}
    where = ""
    if match_id:
        where = "WHERE match_id = :match_id"
        params["match_id"] = str(match_id)
    rows = fetch_all_safe(text(f"SELECT id FROM bookmaker_odds {where}"), params)
    execute_safe(text(f"UPDATE bookmaker_odds SET stale = true {where}"), params)
    return len(rows)


def list_recent_odds(limit: int = 100) -> list[dict]:
    if not db_available():
        return []
    rows = fetch_all_safe(
        text("SELECT * FROM bookmaker_odds ORDER BY collected_at DESC, created_at DESC LIMIT :limit"),
        {"limit": max(1, min(int(limit or 100), 500))},
    )
    return [item for item in (_odds_from_row(row) for row in rows) if item and _is_real_or_manual_odds(item)]


def has_real_odds_for_match(match_id: str) -> bool:
    return bool(list_match_real_odds(match_id))


def _user_bet_from_row(row: dict | None) -> dict | None:
    if not row:
        return None
    return {
        "id": row.get("id"),
        "user_id": row.get("user_id"),
        "match_id": row.get("match_id"),
        "market": row.get("market"),
        "selection": row.get("selection"),
        "bookmaker": row.get("bookmaker"),
        "odds_decimal": _num_or_none(row.get("odds_decimal")),
        "odds_source": row.get("odds_source"),
        "odds_collected_at": _iso(row.get("odds_collected_at")),
        "stake": _num_or_none(row.get("stake")),
        "implied_probability": _num_or_none(row.get("implied_probability")),
        "model_probability": _num_or_none(row.get("model_probability")),
        "calibrated_probability": _num_or_none(row.get("calibrated_probability")),
        "expected_value": _num_or_none(row.get("expected_value")),
        "edge": _num_or_none(row.get("edge")),
        "risk_level": row.get("risk_level"),
        "recommendation_type": row.get("recommendation_type"),
        "status": row.get("status"),
        "result_profit": _num_or_none(row.get("result_profit")) or 0,
        "placed_at": _iso(row.get("placed_at")),
        "settled_at": _iso(row.get("settled_at")),
        "notes": row.get("notes"),
        "raw_context": _loads(row.get("raw_context_json")) or {},
        "created_at": _iso(row.get("created_at")),
        "updated_at": _iso(row.get("updated_at")),
    }


def create_user_bet(user_id: str, payload: dict) -> dict:
    if not user_id:
        raise ValueError("user_id required")
    odds_decimal = _num_or_none(payload.get("odds_decimal"))
    stake = _num_or_none(payload.get("stake"))
    if odds_decimal is None or odds_decimal <= 1:
        raise ValueError("odds_decimal must be greater than 1")
    if stake is None or stake <= 0:
        raise ValueError("stake must be greater than 0")
    requested_source = str(payload.get("odds_source") or payload.get("source") or (payload.get("raw_context") or {}).get("source") or "")
    source = "real_provider" if requested_source in {"provider", "real_provider"} else requested_source
    if source not in {"real_provider", "manual_user_input"}:
        raise ValueError("real odds source or explicit manual_user_input required")
    stored_odds = None
    if source == "real_provider":
        stored_odds = get_reference_real_odds(str(payload.get("match_id") or ""), str(payload.get("market") or ""), str(payload.get("selection") or ""))
        if not stored_odds:
            raise ValueError("provider odds source requires an existing real bookmaker odd")
        if abs(float(stored_odds.get("odds_decimal") or 0) - odds_decimal) > 0.0001:
            raise ValueError("provider odds_decimal must match stored real bookmaker odds")
    bet_id = str(payload.get("id") or uuid.uuid4())
    now = _now()
    row = {
        "id": bet_id,
        "user_id": str(user_id),
        "match_id": str(payload.get("match_id") or ""),
        "market": str(payload.get("market") or ""),
        "selection": str(payload.get("selection") or ""),
        "bookmaker": payload.get("bookmaker"),
        "odds_decimal": odds_decimal,
        "odds_source": "provider" if source == "real_provider" else "manual_user_input",
        "odds_collected_at": _parse_datetime(payload.get("odds_collected_at") or (stored_odds or {}).get("collected_at")),
        "stake": stake,
        "implied_probability": _num_or_none(payload.get("implied_probability")),
        "model_probability": _num_or_none(payload.get("model_probability")),
        "calibrated_probability": _num_or_none(payload.get("calibrated_probability")),
        "expected_value": _num_or_none(payload.get("expected_value")),
        "edge": _num_or_none(payload.get("edge")),
        "risk_level": payload.get("risk_level"),
        "recommendation_type": payload.get("recommendation_type"),
        "status": payload.get("status") or "pending",
        "result_profit": _num_or_none(payload.get("result_profit")) or 0,
        "placed_at": _parse_datetime(payload.get("placed_at")) or now,
        "settled_at": _parse_datetime(payload.get("settled_at")),
        "notes": payload.get("notes"),
        "raw_context_json": _json({**(payload.get("raw_context") or {}), "source": source}),
        "created_at": now,
        "updated_at": now,
    }
    if not row["match_id"] or not row["market"] or not row["selection"]:
        raise ValueError("match_id, market and selection are required")
    if not db_available():
        return {**row, "raw_context": _loads(row["raw_context_json"]) or {}}
    init_db()
    execute_safe(
        text(
            """
            INSERT INTO user_bets (
                id, user_id, match_id, market, selection, bookmaker, odds_decimal, odds_source,
                odds_collected_at, stake,
                implied_probability, model_probability, calibrated_probability, expected_value,
                edge, risk_level, recommendation_type, status, result_profit, placed_at,
                settled_at, notes, raw_context_json, created_at, updated_at
            )
            VALUES (
                :id, :user_id, :match_id, :market, :selection, :bookmaker, :odds_decimal, :odds_source,
                :odds_collected_at, :stake,
                :implied_probability, :model_probability, :calibrated_probability, :expected_value,
                :edge, :risk_level, :recommendation_type, :status, :result_profit, :placed_at,
                :settled_at, :notes, :raw_context_json, :created_at, :updated_at
            )
            """
        ),
        row,
    )
    return get_user_bet(user_id, bet_id) or _user_bet_from_row(row)


def list_user_bets(user_id: str, limit: int = 100) -> list[dict]:
    if not user_id or not db_available():
        return []
    rows = fetch_all_safe(
        text("SELECT * FROM user_bets WHERE user_id = :user_id ORDER BY placed_at DESC LIMIT :limit"),
        {"user_id": str(user_id), "limit": max(1, min(int(limit or 100), 500))},
    )
    return [item for item in (_user_bet_from_row(row) for row in rows) if item]


def get_user_bet(user_id: str, bet_id: str) -> dict | None:
    if not user_id or not bet_id or not db_available():
        return None
    row = fetch_one_safe(
        text("SELECT * FROM user_bets WHERE user_id = :user_id AND id = :bet_id LIMIT 1"),
        {"user_id": str(user_id), "bet_id": str(bet_id)},
    )
    return _user_bet_from_row(row)


def update_user_bet_status(user_id: str, bet_id: str, status: str, result_profit: float | None = None) -> dict | None:
    if status not in {"pending", "won", "lost", "void", "cancelled"}:
        raise ValueError("invalid bet status")
    if not db_available():
        return None
    params = {
        "user_id": str(user_id),
        "bet_id": str(bet_id),
        "status": status,
        "result_profit": result_profit,
        "settled_at": _now() if status in {"won", "lost", "void", "cancelled"} else None,
        "updated_at": _now(),
    }
    execute_safe(
        text(
            """
            UPDATE user_bets
            SET status = :status,
                result_profit = COALESCE(:result_profit, result_profit),
                settled_at = COALESCE(:settled_at, settled_at),
                updated_at = :updated_at
            WHERE user_id = :user_id AND id = :bet_id
            """
        ),
        params,
    )
    return get_user_bet(user_id, bet_id)


def settle_user_bet(user_id: str, bet_id: str, status: str) -> dict | None:
    bet = get_user_bet(user_id, bet_id)
    if not bet:
        return None
    stake = bet.get("stake") or 0
    odds = bet.get("odds_decimal") or 0
    if status == "won":
        profit = round(stake * (odds - 1), 4)
    elif status == "lost":
        profit = round(-stake, 4)
    elif status == "void":
        profit = 0
    else:
        raise ValueError("settle status must be won, lost or void")
    return update_user_bet_status(user_id, bet_id, status, profit)


def delete_or_cancel_user_bet(user_id: str, bet_id: str) -> dict | None:
    return update_user_bet_status(user_id, bet_id, "cancelled", 0)


def compute_user_betting_summary(user_id: str) -> dict:
    bets = list_user_bets(user_id, limit=500)
    settled = [item for item in bets if item["status"] in {"won", "lost", "void"}]
    total_staked = round(sum(float(item.get("stake") or 0) for item in bets), 4)
    settled_staked = sum(float(item.get("stake") or 0) for item in settled)
    net_profit = round(sum(float(item.get("result_profit") or 0) for item in settled), 4)
    wins = [item for item in settled if item["status"] == "won"]
    average_odds = round(sum(float(item.get("odds_decimal") or 0) for item in bets) / len(bets), 4) if bets else None
    return {
        "status": "ok",
        "total_bets": len(bets),
        "settled_bets": len(settled),
        "pending_bets": len([item for item in bets if item["status"] == "pending"]),
        "total_staked": total_staked,
        "net_profit": net_profit if settled else None,
        "roi": round(net_profit / settled_staked, 4) if settled and settled_staked else None,
        "win_rate": round(len(wins) / len([item for item in settled if item["status"] in {"won", "lost"}]), 4) if any(item["status"] in {"won", "lost"} for item in settled) else None,
        "average_odds": average_odds,
        "by_market": compute_user_market_performance(user_id, bets),
        "by_competition": compute_user_competition_performance(user_id, bets),
        "insights": [],
    }


def compute_user_market_performance(user_id: str, bets: list[dict] | None = None) -> list[dict]:
    rows = bets if bets is not None else list_user_bets(user_id)
    markets = sorted({item.get("market") for item in rows if item.get("market")})
    report = []
    for market in markets:
        subset = [item for item in rows if item.get("market") == market and item.get("status") in {"won", "lost", "void"}]
        staked = sum(float(item.get("stake") or 0) for item in subset)
        profit = sum(float(item.get("result_profit") or 0) for item in subset)
        report.append({"market": market, "settled_bets": len(subset), "net_profit": round(profit, 4), "roi": round(profit / staked, 4) if staked else None})
    return report


def compute_user_competition_performance(user_id: str, bets: list[dict] | None = None) -> list[dict]:
    rows = bets if bets is not None else list_user_bets(user_id)
    by_competition: dict[str, list[dict]] = {}
    for item in rows:
        raw = item.get("raw_context") or {}
        competition = raw.get("competition") or "unknown"
        by_competition.setdefault(str(competition), []).append(item)
    report = []
    for competition, items in sorted(by_competition.items()):
        settled = [item for item in items if item.get("status") in {"won", "lost", "void"}]
        staked = sum(float(item.get("stake") or 0) for item in settled)
        profit = sum(float(item.get("result_profit") or 0) for item in settled)
        report.append({"competition": competition, "settled_bets": len(settled), "net_profit": round(profit, 4), "roi": round(profit / staked, 4) if staked else None})
    return report


PLAN_FREE = "free"
PLAN_PREMIUM = "premium"
PLAN_PRO = "pro"
PLAN_ADMIN = "admin"
PLAN_ENTERPRISE = "enterprise"
ROLE_USER = "user"
ROLE_ADMIN = "admin"
ROLE_SUPER_ADMIN = "super_admin"
SAMIR_SUPER_ADMIN_EMAIL = "samir.elh@outlook.fr"
SUPER_ADMIN_ENTITLEMENTS = [
    "admin.access",
    "super_admin.access",
    "users.manage",
    "subscriptions.manage",
    "payments.manage",
    "plans.manage",
    "roles.manage",
    "platform.monitor",
    "model.governance",
    "odds.manage",
    "bets.monitor",
    "audit.read",
    "product.manage",
    "onboarding.manage",
    "legal.manage",
]
PLAN_ENTITLEMENTS = {
    PLAN_FREE: [
        "predictions.basic",
        "matches.basic",
        "dashboard.basic",
        "limited_predictions_per_day",
    ],
    PLAN_PRO: [
        "predictions.basic",
        "matches.basic",
        "dashboard.basic",
        "predictions.advanced",
        "odds.real",
        "value_bets",
        "bets.track",
        "performance.basic",
        "assistant.basic",
    ],
    PLAN_PREMIUM: [
        "predictions.basic",
        "matches.basic",
        "dashboard.basic",
        "predictions.advanced",
        "odds.real",
        "value_bets",
        "bets.track",
        "performance.basic",
        "assistant.basic",
        "assistant.advanced",
        "performance.advanced",
        "analysis.advanced",
        "alerts.intelligent",
        "bankroll.insights",
        "shadow_insights_read",
    ],
    PLAN_ENTERPRISE: [
        "predictions.basic",
        "matches.basic",
        "dashboard.basic",
        "predictions.advanced",
        "odds.real",
        "value_bets",
        "bets.track",
        "performance.basic",
        "assistant.basic",
        "assistant.advanced",
        "performance.advanced",
        "analysis.advanced",
        "alerts.intelligent",
        "bankroll.insights",
        "shadow_insights_read",
        "multi_user",
        "export.reports",
        "priority_support",
        "custom_limits",
        "team_management",
    ],
    ROLE_SUPER_ADMIN: SUPER_ADMIN_ENTITLEMENTS,
}
DEFAULT_SAAS_PLANS = [
    {
        "code": "free",
        "name": "Free",
        "description": "Découverte FootIQ Pro avec limites d'usage.",
        "price_monthly_cents": 0,
        "price_yearly_cents": 0,
        "features": ["dashboard", "prediction_preview", "limited_bets"],
        "limits": {"prediction_view": 5, "bet_created": 10},
    },
    {
        "code": "pro",
        "name": "Pro",
        "description": "Analyse avancée, value bets et suivi complet.",
        "price_monthly_cents": 2900,
        "price_yearly_cents": 29000,
        "features": ["predictions", "value_bets", "assistant", "performance"],
        "limits": {"prediction_view": 1000, "assistant_request": 200},
    },
    {
        "code": "premium",
        "name": "Premium",
        "description": "Expérience complète pour parieur exigeant.",
        "price_monthly_cents": 1900,
        "price_yearly_cents": 19000,
        "features": ["predictions", "real_odds", "value_bets", "my_bets"],
        "limits": {"prediction_view": 200, "assistant_request": 50},
    },
    {
        "code": "enterprise",
        "name": "Enterprise",
        "description": "Pilotage équipe, supervision et droits étendus.",
        "price_monthly_cents": 9900,
        "price_yearly_cents": 99000,
        "features": ["all", "governance", "exports", "priority_support"],
        "limits": {},
    },
]
VALID_SUBSCRIPTION_PLANS = {PLAN_FREE, PLAN_PREMIUM, PLAN_PRO, PLAN_ENTERPRISE, PLAN_ADMIN}
VALID_SUBSCRIPTION_STATUSES = {"active", "trialing", "past_due", "canceled", "incomplete", "free", "unpaid", "expired"}
FEATURE_LIMITS = {
    PLAN_FREE: {
        "prediction_view": 5,
        "value_bet_view": 2,
        "assistant_request": 3,
        "bet_created": 10,
        "performance_view": 3,
    },
    PLAN_PREMIUM: {
        "prediction_view": 200,
        "value_bet_view": 100,
        "assistant_request": 50,
        "bet_created": 250,
        "performance_view": 100,
    },
    PLAN_PRO: {
        "prediction_view": 1000,
        "value_bet_view": 500,
        "assistant_request": 200,
        "bet_created": 2000,
        "performance_view": 500,
    },
    PLAN_ADMIN: {},
    PLAN_ENTERPRISE: {},
}


def _subscription_from_row(row: dict | None) -> dict | None:
    if not row:
        return None
    return {
        "id": row.get("id"),
        "user_id": row.get("user_id"),
        "plan": row.get("plan") or PLAN_FREE,
        "status": row.get("status") or "free",
        "stripe_customer_id": row.get("stripe_customer_id"),
        "stripe_subscription_id": row.get("stripe_subscription_id"),
        "stripe_price_id": row.get("stripe_price_id"),
        "current_period_start": _iso(row.get("current_period_start")),
        "current_period_end": _iso(row.get("current_period_end")),
        "cancel_at_period_end": bool(row.get("cancel_at_period_end")) if row.get("cancel_at_period_end") is not None else False,
        "created_at": _iso(row.get("created_at")),
        "updated_at": _iso(row.get("updated_at")),
    }


def default_subscription(user_id: str) -> dict:
    return {
        "id": None,
        "user_id": user_id,
        "plan": PLAN_FREE,
        "status": "free",
        "stripe_customer_id": None,
        "stripe_subscription_id": None,
        "stripe_price_id": None,
        "current_period_start": None,
        "current_period_end": None,
        "cancel_at_period_end": False,
        "created_at": None,
        "updated_at": None,
    }


def get_user_subscription(user_id: str) -> dict:
    if not user_id or not db_available():
        return default_subscription(user_id or "local-user")
    init_db()
    row = fetch_one_safe(
        text(
            """
            SELECT *
            FROM user_subscriptions
            WHERE user_id = :user_id
            ORDER BY updated_at DESC, created_at DESC
            LIMIT 1
            """
        ),
        {"user_id": str(user_id)},
    )
    return _subscription_from_row(row) or default_subscription(str(user_id))


def get_subscription_by_customer(stripe_customer_id: str) -> dict | None:
    if not stripe_customer_id or not db_available():
        return None
    row = fetch_one_safe(
        text("SELECT * FROM user_subscriptions WHERE stripe_customer_id = :customer_id ORDER BY updated_at DESC LIMIT 1"),
        {"customer_id": stripe_customer_id},
    )
    return _subscription_from_row(row)


def upsert_user_subscription(
    user_id: str,
    plan: str = PLAN_FREE,
    status: str = "free",
    stripe_customer_id: str | None = None,
    stripe_subscription_id: str | None = None,
    stripe_price_id: str | None = None,
    current_period_start=None,
    current_period_end=None,
    cancel_at_period_end: bool = False,
) -> dict:
    if not user_id:
        raise ValueError("user_id required")
    safe_plan = plan if plan in VALID_SUBSCRIPTION_PLANS else PLAN_FREE
    safe_status = status if status in VALID_SUBSCRIPTION_STATUSES else "free"
    now = _now()
    subscription_id = str(uuid.uuid4())
    row = {
        "id": subscription_id,
        "user_id": str(user_id),
        "plan": safe_plan,
        "status": safe_status,
        "stripe_customer_id": stripe_customer_id,
        "stripe_subscription_id": stripe_subscription_id,
        "stripe_price_id": stripe_price_id,
        "current_period_start": _parse_datetime(current_period_start),
        "current_period_end": _parse_datetime(current_period_end),
        "cancel_at_period_end": bool(cancel_at_period_end),
        "created_at": now,
        "updated_at": now,
    }
    if not db_available():
        return _subscription_from_row(row) or default_subscription(str(user_id))
    init_db()
    existing = fetch_one_safe(
        text("SELECT id FROM user_subscriptions WHERE user_id = :user_id ORDER BY updated_at DESC LIMIT 1"),
        {"user_id": str(user_id)},
    )
    if existing:
        row["id"] = existing["id"]
        execute_safe(
            text(
                """
                UPDATE user_subscriptions
                SET plan = :plan,
                    status = :status,
                    stripe_customer_id = COALESCE(:stripe_customer_id, stripe_customer_id),
                    stripe_subscription_id = COALESCE(:stripe_subscription_id, stripe_subscription_id),
                    stripe_price_id = COALESCE(:stripe_price_id, stripe_price_id),
                    current_period_start = :current_period_start,
                    current_period_end = :current_period_end,
                    cancel_at_period_end = :cancel_at_period_end,
                    updated_at = :updated_at
                WHERE id = :id AND user_id = :user_id
                """
            ),
            row,
        )
    else:
        execute_safe(
            text(
                """
                INSERT INTO user_subscriptions (
                    id, user_id, plan, status, stripe_customer_id, stripe_subscription_id,
                    stripe_price_id, current_period_start, current_period_end,
                    cancel_at_period_end, created_at, updated_at
                )
                VALUES (
                    :id, :user_id, :plan, :status, :stripe_customer_id, :stripe_subscription_id,
                    :stripe_price_id, :current_period_start, :current_period_end,
                    :cancel_at_period_end, :created_at, :updated_at
                )
                """
            ),
            row,
        )
    return get_user_subscription(str(user_id))


def get_user_plan(user_id: str) -> str:
    return (get_user_subscription(user_id).get("plan") or PLAN_FREE) if user_id else PLAN_FREE


def is_user_premium(user_id: str) -> bool:
    return get_user_plan(user_id) in {PLAN_PREMIUM, PLAN_PRO, PLAN_ADMIN}


def record_usage_event(user_id: str, feature: str, event_type: str | None = None, count: int = 1, metadata: dict | None = None) -> dict:
    if not user_id:
        raise ValueError("user_id required")
    now = _now()
    row = {
        "id": str(uuid.uuid4()),
        "user_id": str(user_id),
        "event_type": event_type or feature,
        "feature": str(feature or event_type or "unknown"),
        "count": max(1, _int_or_zero(count)),
        "metadata_json": _json(metadata or {}),
        "created_at": now,
    }
    if db_available():
        init_db()
        execute_safe(
            text(
                """
                INSERT INTO user_usage_events (id, user_id, event_type, feature, count, metadata_json, created_at)
                VALUES (:id, :user_id, :event_type, :feature, :count, :metadata_json, :created_at)
                """
            ),
            row,
        )
    return {**row, "metadata": metadata or {}, "created_at": _iso(now)}


def _period_start(period: str) -> datetime:
    now = _now()
    if period == "month":
        return now - timedelta(days=30)
    if period == "week":
        return now - timedelta(days=7)
    return now - timedelta(days=1)


def get_usage_count(user_id: str, feature: str, period: str = "day") -> int:
    if not user_id or not feature or not db_available():
        return 0
    row = fetch_one_safe(
        text(
            """
            SELECT COALESCE(SUM(count), 0) AS count
            FROM user_usage_events
            WHERE user_id = :user_id
              AND feature = :feature
              AND created_at >= :period_start
            """
        ),
        {"user_id": str(user_id), "feature": str(feature), "period_start": _period_start(period)},
    )
    return _int_or_zero((row or {}).get("count"))


def check_usage_limit(user_id: str, feature: str, period: str = "day") -> dict:
    plan = get_user_plan(user_id)
    limit = FEATURE_LIMITS.get(plan, {}).get(feature)
    used = get_usage_count(user_id, feature, period)
    if limit is None:
        return {"allowed": True, "plan": plan, "feature": feature, "used": used, "limit": None, "remaining": None, "period": period}
    remaining = max(0, limit - used)
    return {
        "allowed": used < limit,
        "plan": plan,
        "feature": feature,
        "used": used,
        "limit": limit,
        "remaining": remaining,
        "period": period,
        "upgrade_required": used >= limit,
    }


def get_subscription_plan_counts() -> dict:
    counts = {plan: 0 for plan in [PLAN_FREE, PLAN_PREMIUM, PLAN_PRO, PLAN_ADMIN]}
    if not db_available():
        return counts
    rows = fetch_all_safe(text("SELECT plan, COUNT(*) AS count FROM user_subscriptions GROUP BY plan"))
    for row in rows:
        plan = row.get("plan")
        if plan in counts:
            counts[plan] = _int_or_zero(row.get("count"))
    return counts


def _user_from_row(row: dict | None) -> dict | None:
    if not row:
        return None
    return {
        "id": row.get("id"),
        "email": row.get("email"),
        "display_name": row.get("display_name"),
        "role": row.get("role") or ROLE_USER,
        "status": row.get("status") or "active",
        "plan_id": row.get("plan_id"),
        "stripe_customer_id": row.get("stripe_customer_id"),
        "created_at": _iso(row.get("created_at")),
        "updated_at": _iso(row.get("updated_at")),
        "last_login_at": _iso(row.get("last_login_at")),
        "metadata": _loads(row.get("metadata_json")) or {},
    }


def _plan_from_row(row: dict | None) -> dict | None:
    if not row:
        return None
    return {
        "id": row.get("id"),
        "code": row.get("code"),
        "name": row.get("name"),
        "description": row.get("description"),
        "price_monthly_cents": _int_or_zero(row.get("price_monthly_cents")),
        "price_yearly_cents": _int_or_zero(row.get("price_yearly_cents")),
        "currency": row.get("currency") or "EUR",
        "is_active": bool(row.get("is_active")) if row.get("is_active") is not None else True,
        "features": _loads(row.get("features_json")) or [],
        "limits": _loads(row.get("limits_json")) or {},
        "created_at": _iso(row.get("created_at")),
        "updated_at": _iso(row.get("updated_at")),
    }


def _subscription_saas_from_row(row: dict | None) -> dict | None:
    if not row:
        return None
    return {
        "id": row.get("id"),
        "user_id": row.get("user_id"),
        "email": row.get("email"),
        "plan_id": row.get("plan_id"),
        "plan_code": row.get("plan_code"),
        "status": row.get("status"),
        "provider": row.get("provider") or "internal",
        "provider_customer_id": row.get("provider_customer_id"),
        "provider_subscription_id": row.get("provider_subscription_id"),
        "current_period_start": _iso(row.get("current_period_start")),
        "current_period_end": _iso(row.get("current_period_end")),
        "cancel_at_period_end": bool(row.get("cancel_at_period_end")) if row.get("cancel_at_period_end") is not None else False,
        "created_at": _iso(row.get("created_at")),
        "updated_at": _iso(row.get("updated_at")),
    }


def _payment_from_row(row: dict | None) -> dict | None:
    if not row:
        return None
    return {
        "id": row.get("id"),
        "user_id": row.get("user_id"),
        "email": row.get("email"),
        "subscription_id": row.get("subscription_id"),
        "provider": row.get("provider") or "internal",
        "provider_payment_id": row.get("provider_payment_id"),
        "amount_cents": _int_or_zero(row.get("amount_cents")),
        "currency": row.get("currency") or "EUR",
        "status": row.get("status"),
        "paid_at": _iso(row.get("paid_at")),
        "created_at": _iso(row.get("created_at")),
        "metadata": _loads(row.get("metadata_json")) or {},
    }


def _entitlement_from_row(row: dict | None) -> dict | None:
    if not row:
        return None
    return {
        "id": row.get("id"),
        "user_id": row.get("user_id"),
        "email": row.get("email"),
        "feature_key": row.get("feature_key"),
        "enabled": bool(row.get("enabled")) if row.get("enabled") is not None else True,
        "source": row.get("source") or "plan",
        "expires_at": _iso(row.get("expires_at")),
        "created_at": _iso(row.get("created_at")),
        "updated_at": _iso(row.get("updated_at")),
    }


def _audit_from_row(row: dict | None) -> dict | None:
    if not row:
        return None
    return {
        "id": row.get("id"),
        "actor_user_id": row.get("actor_user_id"),
        "actor_email": row.get("actor_email"),
        "action": row.get("action"),
        "target_type": row.get("target_type"),
        "target_id": row.get("target_id"),
        "target_email": row.get("target_email"),
        "before": _loads(row.get("before_json")),
        "after": _loads(row.get("after_json")),
        "created_at": _iso(row.get("created_at")),
    }


def ensure_saas_defaults() -> dict:
    if not db_available():
        return {"status": "memory", "plans_seeded": len(DEFAULT_SAAS_PLANS), "super_admin_seeded": True}
    init_db()
    for plan in DEFAULT_SAAS_PLANS:
        upsert_saas_plan(plan, actor_email="system")
    user = promote_samir_super_admin(actor_email="system")
    return {"status": "ok", "plans_seeded": len(DEFAULT_SAAS_PLANS), "super_admin": user}


def get_or_create_user_by_email(email: str, display_name: str | None = None, role: str = ROLE_USER, status: str = "active") -> dict:
    safe_email = str(email or "").strip().lower()
    if not safe_email:
        raise ValueError("email required")
    now = _now()
    if not db_available():
        return {
            "id": safe_email,
            "email": safe_email,
            "display_name": display_name,
            "role": role,
            "status": status,
            "plan_id": None,
            "stripe_customer_id": None,
            "created_at": _iso(now),
            "updated_at": _iso(now),
            "last_login_at": None,
            "metadata": {},
        }
    init_db()
    existing = fetch_one_safe(text("SELECT * FROM users WHERE email = :email LIMIT 1"), {"email": safe_email})
    if existing:
        return _user_from_row(existing)
    user_id = str(uuid.uuid4())
    execute_safe(
        text(
            """
            INSERT INTO users (id, email, display_name, role, status, created_at, updated_at, metadata_json, stripe_customer_id)
            VALUES (:id, :email, :display_name, :role, :status, :created_at, :updated_at, :metadata_json, :stripe_customer_id)
            """
        ),
        {
            "id": user_id,
            "email": safe_email,
            "display_name": display_name,
            "role": role,
            "status": status,
            "created_at": now,
            "updated_at": now,
            "metadata_json": _json({}),
            "stripe_customer_id": None,
        },
    )
    return get_user_by_id_or_email(user_id)


def get_user_by_id_or_email(value: str | None) -> dict | None:
    if not value:
        return None
    if not db_available():
        email = str(value).strip().lower()
        if email == SAMIR_SUPER_ADMIN_EMAIL:
            return get_or_create_user_by_email(email, "Samir", ROLE_SUPER_ADMIN)
        return None
    row = fetch_one_safe(
        text("SELECT * FROM users WHERE id = :value OR email = :email LIMIT 1"),
        {"value": str(value), "email": str(value).strip().lower()},
    )
    return _user_from_row(row)


def set_user_stripe_customer_id(user_id_or_email: str, stripe_customer_id: str) -> dict | None:
    user = get_user_by_id_or_email(user_id_or_email)
    if not user or not stripe_customer_id:
        return user
    if db_available():
        execute_safe(
            text("UPDATE users SET stripe_customer_id = :stripe_customer_id, updated_at = :updated_at WHERE id = :id"),
            {"stripe_customer_id": stripe_customer_id, "updated_at": _now(), "id": user["id"]},
        )
    return get_user_by_id_or_email(user["id"]) or {**user, "stripe_customer_id": stripe_customer_id}


def get_user_by_stripe_customer(stripe_customer_id: str | None) -> dict | None:
    if not stripe_customer_id or not db_available():
        return None
    row = fetch_one_safe(
        text("SELECT * FROM users WHERE stripe_customer_id = :stripe_customer_id LIMIT 1"),
        {"stripe_customer_id": stripe_customer_id},
    )
    return _user_from_row(row)


def update_user_role_status(user_id: str, role: str | None = None, status: str | None = None, actor_email: str = "system") -> dict:
    user = get_user_by_id_or_email(user_id)
    if not user:
        raise ValueError("user not found")
    safe_role = role if role in {ROLE_USER, ROLE_ADMIN, ROLE_SUPER_ADMIN} else user.get("role")
    safe_status = status if status in {"active", "suspended", "deleted"} else user.get("status")
    before = user
    if db_available():
        execute_safe(
            text("UPDATE users SET role = :role, status = :status, updated_at = :updated_at WHERE id = :id"),
            {"role": safe_role, "status": safe_status, "updated_at": _now(), "id": user["id"]},
        )
    updated = get_user_by_id_or_email(user["id"]) or {**user, "role": safe_role, "status": safe_status}
    write_super_admin_audit(actor_email, f"user.{safe_role if role else safe_status}", "user", user["id"], user.get("email"), before, updated)
    return updated


def write_super_admin_audit(
    actor_email: str,
    action: str,
    target_type: str,
    target_id: str | None = None,
    target_email: str | None = None,
    before: dict | None = None,
    after: dict | None = None,
    actor_user_id: str | None = None,
) -> dict:
    row = {
        "id": str(uuid.uuid4()),
        "actor_user_id": actor_user_id,
        "actor_email": str(actor_email or "system").lower(),
        "action": action,
        "target_type": target_type,
        "target_id": target_id,
        "target_email": target_email,
        "before_json": _json(before) if before is not None else None,
        "after_json": _json(after) if after is not None else None,
        "created_at": _now(),
    }
    if db_available():
        execute_safe(
            text(
                """
                INSERT INTO super_admin_audit_log (
                    id, actor_user_id, actor_email, action, target_type, target_id,
                    target_email, before_json, after_json, created_at
                )
                VALUES (
                    :id, :actor_user_id, :actor_email, :action, :target_type, :target_id,
                    :target_email, :before_json, :after_json, :created_at
                )
                """
            ),
            row,
        )
    return {**row, "before": before, "after": after, "created_at": _iso(row["created_at"])}


def grant_entitlement(user_id: str, feature_key: str, source: str = "manual", actor_email: str = "system") -> dict:
    user = get_user_by_id_or_email(user_id)
    if not user:
        raise ValueError("user not found")
    now = _now()
    if db_available():
        existing = fetch_one_safe(
            text("SELECT * FROM access_entitlements WHERE user_id = :user_id AND feature_key = :feature_key LIMIT 1"),
            {"user_id": user["id"], "feature_key": feature_key},
        )
        if existing:
            execute_safe(
                text("UPDATE access_entitlements SET enabled = true, source = :source, updated_at = :updated_at WHERE id = :id"),
                {"source": source, "updated_at": now, "id": existing["id"]},
            )
        else:
            execute_safe(
                text(
                    """
                    INSERT INTO access_entitlements (id, user_id, feature_key, enabled, source, created_at, updated_at)
                    VALUES (:id, :user_id, :feature_key, true, :source, :created_at, :updated_at)
                    """
                ),
                {"id": str(uuid.uuid4()), "user_id": user["id"], "feature_key": feature_key, "source": source, "created_at": now, "updated_at": now},
            )
    entitlement = get_entitlement_for_user(user["id"], feature_key)
    write_super_admin_audit(actor_email, "entitlement.grant", "entitlement", entitlement.get("id") if entitlement else None, user.get("email"), None, entitlement)
    return entitlement or {"user_id": user["id"], "feature_key": feature_key, "enabled": True, "source": source}


def get_entitlement_for_user(user_id: str, feature_key: str) -> dict | None:
    if not db_available():
        return {"id": None, "user_id": user_id, "feature_key": feature_key, "enabled": True, "source": "super_admin"} if user_id else None
    row = fetch_one_safe(
        text(
            """
            SELECT e.*, u.email AS email
            FROM access_entitlements e
            LEFT JOIN users u ON u.id = e.user_id
            WHERE e.user_id = :user_id AND e.feature_key = :feature_key
            LIMIT 1
            """
        ),
        {"user_id": user_id, "feature_key": feature_key},
    )
    return _entitlement_from_row(row)


def is_super_admin(value: str | None) -> bool:
    user = get_user_by_id_or_email(value)
    return bool(user and user.get("role") == ROLE_SUPER_ADMIN and user.get("status") == "active")


def get_user_entitlements(user_id_or_email: str | None) -> list[dict]:
    user = get_user_by_id_or_email(user_id_or_email)
    if not user:
        return []
    if user.get("role") == ROLE_SUPER_ADMIN:
        return [
            {"id": None, "user_id": user["id"], "email": user.get("email"), "feature_key": feature, "enabled": True, "source": "super_admin"}
            for feature in sorted(set(SUPER_ADMIN_ENTITLEMENTS + PLAN_ENTITLEMENTS.get(PLAN_ENTERPRISE, [])))
        ]
    if not db_available():
        return [
            {"id": None, "user_id": user["id"], "email": user.get("email"), "feature_key": feature, "enabled": True, "source": "plan"}
            for feature in PLAN_ENTITLEMENTS.get(get_user_plan(user["id"]), PLAN_ENTITLEMENTS[PLAN_FREE])
        ]
    rows = fetch_all_safe(
        text(
            """
            SELECT e.*, u.email AS email
            FROM access_entitlements e
            LEFT JOIN users u ON u.id = e.user_id
            WHERE e.user_id = :user_id AND e.enabled = true
            ORDER BY e.feature_key ASC
            """
        ),
        {"user_id": user["id"]},
    )
    return [item for item in (_entitlement_from_row(row) for row in rows) if item]


def has_entitlement(user_id_or_email: str | None, feature_key: str) -> bool:
    if not user_id_or_email or not feature_key:
        return False
    user = get_user_by_id_or_email(user_id_or_email)
    if not user or user.get("status") != "active":
        return False
    if user.get("role") == ROLE_SUPER_ADMIN:
        return True
    entitlement = get_entitlement_for_user(user["id"], feature_key)
    return bool(entitlement and entitlement.get("enabled"))


def revoke_plan_entitlements(user_id_or_email: str, actor_email: str = "system") -> int:
    user = get_user_by_id_or_email(user_id_or_email)
    if not user or not db_available():
        return 0
    before = get_user_entitlements(user["id"])
    execute_safe(
        text("UPDATE access_entitlements SET enabled = false, updated_at = :updated_at WHERE user_id = :user_id AND source = 'plan'"),
        {"updated_at": _now(), "user_id": user["id"]},
    )
    after = get_user_entitlements(user["id"])
    write_super_admin_audit(actor_email, "entitlements.plan.revoke", "user", user["id"], user.get("email"), {"entitlements": before}, {"entitlements": after})
    return len(before)


def sync_entitlements_for_subscription(user_id_or_email: str, plan_code: str, source: str = "plan", actor_email: str = "stripe") -> list[dict]:
    user = get_user_by_id_or_email(user_id_or_email)
    if not user:
        return []
    safe_plan = plan_code if plan_code in PLAN_ENTITLEMENTS else PLAN_FREE
    if user.get("role") == ROLE_SUPER_ADMIN:
        safe_plan = ROLE_SUPER_ADMIN
    if source == "plan":
        revoke_plan_entitlements(user["id"], actor_email=actor_email)
    created = []
    for feature in PLAN_ENTITLEMENTS.get(safe_plan, PLAN_ENTITLEMENTS[PLAN_FREE]):
        created.append(grant_entitlement(user["id"], feature, source=source, actor_email=actor_email))
    return created


def promote_samir_super_admin(actor_email: str = "system") -> dict:
    user = get_or_create_user_by_email(SAMIR_SUPER_ADMIN_EMAIL, display_name="Samir", role=ROLE_SUPER_ADMIN, status="active")
    before = dict(user)
    if db_available():
        execute_safe(
            text("UPDATE users SET role = :role, status = 'active', updated_at = :updated_at WHERE id = :id"),
            {"role": ROLE_SUPER_ADMIN, "updated_at": _now(), "id": user["id"]},
        )
    user = get_user_by_id_or_email(user["id"]) or {**user, "role": ROLE_SUPER_ADMIN, "status": "active"}
    for feature in SUPER_ADMIN_ENTITLEMENTS:
        grant_entitlement(user["id"], feature, source="super_admin", actor_email=actor_email)
    write_super_admin_audit(actor_email, "super_admin.seed", "user", user["id"], user.get("email"), before, user)
    return user


def upsert_saas_plan(payload: dict, actor_email: str = "system") -> dict:
    code = str(payload.get("code") or "").strip().lower()
    if code not in {"free", "pro", "premium", "enterprise"}:
        raise ValueError("invalid plan code")
    now = _now()
    existing = get_saas_plan_by_code(code)
    row = {
        "id": existing.get("id") if existing else str(uuid.uuid4()),
        "code": code,
        "name": payload.get("name") or code.title(),
        "description": payload.get("description"),
        "price_monthly_cents": _int_or_zero(payload.get("price_monthly_cents")),
        "price_yearly_cents": _int_or_zero(payload.get("price_yearly_cents")),
        "currency": payload.get("currency") or "EUR",
        "is_active": bool(payload.get("is_active", True)),
        "features_json": _json(payload.get("features") or []),
        "limits_json": _json(payload.get("limits") or {}),
        "created_at": now,
        "updated_at": now,
    }
    if db_available():
        if existing:
            execute_safe(
                text(
                    """
                    UPDATE saas_plans
                    SET name = :name, description = :description, price_monthly_cents = :price_monthly_cents,
                        price_yearly_cents = :price_yearly_cents, currency = :currency, is_active = :is_active,
                        features_json = :features_json, limits_json = :limits_json, updated_at = :updated_at
                    WHERE id = :id
                    """
                ),
                row,
            )
        else:
            execute_safe(
                text(
                    """
                    INSERT INTO saas_plans (
                        id, code, name, description, price_monthly_cents, price_yearly_cents,
                        currency, is_active, features_json, limits_json, created_at, updated_at
                    )
                    VALUES (
                        :id, :code, :name, :description, :price_monthly_cents, :price_yearly_cents,
                        :currency, :is_active, :features_json, :limits_json, :created_at, :updated_at
                    )
                    """
                ),
                row,
            )
    plan = get_saas_plan_by_code(code) or _plan_from_row(row)
    write_super_admin_audit(actor_email, "plan.upsert", "plan", plan.get("id") if plan else row["id"], None, existing, plan)
    return plan


def get_saas_plan_by_code(code: str) -> dict | None:
    if not db_available():
        return _plan_from_row(next((plan for plan in DEFAULT_SAAS_PLANS if plan["code"] == code), None))
    row = fetch_one_safe(text("SELECT * FROM saas_plans WHERE code = :code LIMIT 1"), {"code": code})
    return _plan_from_row(row)


def list_saas_plans() -> list[dict]:
    if not db_available():
        return [_plan_from_row({**plan, "id": plan["code"], "currency": "EUR", "is_active": True, "features_json": _json(plan["features"]), "limits_json": _json(plan["limits"])}) for plan in DEFAULT_SAAS_PLANS]
    rows = fetch_all_safe(text("SELECT * FROM saas_plans ORDER BY price_monthly_cents ASC, code ASC"))
    return [item for item in (_plan_from_row(row) for row in rows) if item]


def list_saas_users(limit: int = 100) -> list[dict]:
    if not db_available():
        return [promote_samir_super_admin()]
    rows = fetch_all_safe(text("SELECT * FROM users ORDER BY created_at DESC LIMIT :limit"), {"limit": max(1, min(int(limit or 100), 500))})
    return [item for item in (_user_from_row(row) for row in rows) if item]


def get_active_saas_subscription(user_id_or_email: str) -> dict | None:
    user = get_user_by_id_or_email(user_id_or_email)
    if not user or not db_available():
        return None
    row = fetch_one_safe(
        text(
            """
            SELECT s.*, u.email AS email, p.code AS plan_code
            FROM subscriptions s
            LEFT JOIN users u ON u.id = s.user_id
            LEFT JOIN saas_plans p ON p.id = s.plan_id
            WHERE s.user_id = :user_id AND s.status IN ('active', 'trialing')
            ORDER BY s.updated_at DESC
            LIMIT 1
            """
        ),
        {"user_id": user["id"]},
    )
    return _subscription_saas_from_row(row)


def get_saas_subscription_by_provider(provider_subscription_id: str | None) -> dict | None:
    if not provider_subscription_id or not db_available():
        return None
    row = fetch_one_safe(
        text(
            """
            SELECT s.*, u.email AS email, p.code AS plan_code
            FROM subscriptions s
            LEFT JOIN users u ON u.id = s.user_id
            LEFT JOIN saas_plans p ON p.id = s.plan_id
            WHERE s.provider_subscription_id = :provider_subscription_id
            ORDER BY s.updated_at DESC
            LIMIT 1
            """
        ),
        {"provider_subscription_id": provider_subscription_id},
    )
    return _subscription_saas_from_row(row)


def get_saas_subscription_by_customer(provider_customer_id: str | None) -> dict | None:
    if not provider_customer_id or not db_available():
        return None
    row = fetch_one_safe(
        text(
            """
            SELECT s.*, u.email AS email, p.code AS plan_code
            FROM subscriptions s
            LEFT JOIN users u ON u.id = s.user_id
            LEFT JOIN saas_plans p ON p.id = s.plan_id
            WHERE s.provider_customer_id = :provider_customer_id
            ORDER BY s.updated_at DESC
            LIMIT 1
            """
        ),
        {"provider_customer_id": provider_customer_id},
    )
    return _subscription_saas_from_row(row)


def upsert_saas_subscription(
    user_id_or_email: str,
    plan_code: str,
    status: str,
    provider: str = "stripe",
    provider_customer_id: str | None = None,
    provider_subscription_id: str | None = None,
    current_period_start=None,
    current_period_end=None,
    cancel_at_period_end: bool = False,
) -> dict:
    user = get_user_by_id_or_email(user_id_or_email)
    if not user and "@" in str(user_id_or_email or ""):
        user = get_or_create_user_by_email(str(user_id_or_email))
    if not user:
        raise ValueError("user not found")
    plan = get_saas_plan_by_code(plan_code) or get_saas_plan_by_code(PLAN_FREE)
    if not plan:
        raise ValueError("plan not found")
    safe_status = status if status in {"trialing", "active", "past_due", "canceled", "unpaid", "expired", "incomplete"} else "incomplete"
    now = _now()
    existing = None
    if provider_subscription_id:
        existing = get_saas_subscription_by_provider(provider_subscription_id)
    if not existing:
        existing = get_active_saas_subscription(user["id"])
    row = {
        "id": (existing or {}).get("id") or str(uuid.uuid4()),
        "user_id": user["id"],
        "plan_id": plan["id"],
        "status": safe_status,
        "provider": provider,
        "provider_customer_id": provider_customer_id,
        "provider_subscription_id": provider_subscription_id,
        "current_period_start": _parse_datetime(current_period_start),
        "current_period_end": _parse_datetime(current_period_end),
        "cancel_at_period_end": bool(cancel_at_period_end),
        "created_at": now,
        "updated_at": now,
    }
    if db_available():
        if existing:
            execute_safe(
                text(
                    """
                    UPDATE subscriptions
                    SET plan_id = :plan_id, status = :status, provider = :provider,
                        provider_customer_id = COALESCE(:provider_customer_id, provider_customer_id),
                        provider_subscription_id = COALESCE(:provider_subscription_id, provider_subscription_id),
                        current_period_start = COALESCE(:current_period_start, current_period_start),
                        current_period_end = COALESCE(:current_period_end, current_period_end),
                        cancel_at_period_end = :cancel_at_period_end,
                        updated_at = :updated_at
                    WHERE id = :id
                    """
                ),
                row,
            )
        else:
            execute_safe(
                text(
                    """
                    INSERT INTO subscriptions (
                        id, user_id, plan_id, status, provider, provider_customer_id,
                        provider_subscription_id, current_period_start, current_period_end,
                        cancel_at_period_end, created_at, updated_at
                    )
                    VALUES (
                        :id, :user_id, :plan_id, :status, :provider, :provider_customer_id,
                        :provider_subscription_id, :current_period_start, :current_period_end,
                        :cancel_at_period_end, :created_at, :updated_at
                    )
                    """
                ),
                row,
            )
        if provider_customer_id:
            set_user_stripe_customer_id(user["id"], provider_customer_id)
    updated = get_saas_subscription_by_provider(provider_subscription_id) if provider_subscription_id else get_active_saas_subscription(user["id"])
    return updated or _subscription_saas_from_row({**row, "email": user.get("email"), "plan_code": plan.get("code")})


def record_saas_payment(
    user_id_or_email: str,
    provider_payment_id: str | None,
    amount_cents: int,
    currency: str = "EUR",
    status: str = "pending",
    subscription_id: str | None = None,
    provider: str = "stripe",
    paid_at=None,
    metadata: dict | None = None,
) -> dict:
    user = get_user_by_id_or_email(user_id_or_email)
    if not user:
        raise ValueError("user not found")
    now = _now()
    existing = None
    if provider_payment_id and db_available():
        existing = fetch_one_safe(text("SELECT * FROM payments WHERE provider_payment_id = :provider_payment_id LIMIT 1"), {"provider_payment_id": provider_payment_id})
    row = {
        "id": (existing or {}).get("id") or str(uuid.uuid4()),
        "user_id": user["id"],
        "subscription_id": subscription_id,
        "provider": provider,
        "provider_payment_id": provider_payment_id,
        "amount_cents": _int_or_zero(amount_cents),
        "currency": str(currency or "EUR").upper(),
        "status": status if status in {"succeeded", "pending", "failed", "refunded"} else "pending",
        "paid_at": _parse_datetime(paid_at),
        "created_at": now,
        "metadata_json": _json(metadata or {}),
    }
    if db_available():
        if existing:
            execute_safe(
                text(
                    """
                    UPDATE payments
                    SET status = :status, amount_cents = :amount_cents, currency = :currency,
                        paid_at = COALESCE(:paid_at, paid_at), metadata_json = :metadata_json
                    WHERE id = :id
                    """
                ),
                row,
            )
        else:
            execute_safe(
                text(
                    """
                    INSERT INTO payments (
                        id, user_id, subscription_id, provider, provider_payment_id,
                        amount_cents, currency, status, paid_at, created_at, metadata_json
                    )
                    VALUES (
                        :id, :user_id, :subscription_id, :provider, :provider_payment_id,
                        :amount_cents, :currency, :status, :paid_at, :created_at, :metadata_json
                    )
                    """
                ),
                row,
            )
    return _payment_from_row({**row, "email": user.get("email")})


def stripe_webhook_event_status(stripe_event_id: str | None) -> dict | None:
    if not stripe_event_id or not db_available():
        return None
    row = fetch_one_safe(text("SELECT * FROM stripe_webhook_events WHERE stripe_event_id = :stripe_event_id LIMIT 1"), {"stripe_event_id": stripe_event_id})
    return dict(row) if row else None


def record_stripe_webhook_event(stripe_event_id: str, event_type: str, status: str, payload: dict | None = None, error: str | None = None) -> dict:
    row = {
        "id": str(uuid.uuid4()),
        "stripe_event_id": stripe_event_id,
        "type": event_type,
        "processed_at": _now(),
        "status": status,
        "error": error,
        "payload_json": _json(payload or {}),
    }
    if db_available():
        execute_safe(
            text(
                """
                INSERT INTO stripe_webhook_events (id, stripe_event_id, type, processed_at, status, error, payload_json)
                VALUES (:id, :stripe_event_id, :type, :processed_at, :status, :error, :payload_json)
                ON CONFLICT (stripe_event_id) DO UPDATE SET
                    processed_at = EXCLUDED.processed_at,
                    status = EXCLUDED.status,
                    error = EXCLUDED.error,
                    payload_json = EXCLUDED.payload_json
                """
            ),
            row,
        )
    return {**row, "processed_at": _iso(row["processed_at"])}


def list_stripe_webhook_events(limit: int = 50) -> list[dict]:
    if not db_available():
        return []
    rows = fetch_all_safe(
        text("SELECT * FROM stripe_webhook_events ORDER BY processed_at DESC LIMIT :limit"),
        {"limit": max(1, min(int(limit or 50), 200))},
    )
    return [
        {
            "stripe_event_id": row.get("stripe_event_id"),
            "type": row.get("type"),
            "processed_at": _iso(row.get("processed_at")),
            "status": row.get("status"),
            "error": row.get("error"),
        }
        for row in rows
    ]


def list_saas_subscriptions(limit: int = 100) -> list[dict]:
    if not db_available():
        return []
    rows = fetch_all_safe(
        text(
            """
            SELECT s.*, u.email AS email, p.code AS plan_code
            FROM subscriptions s
            LEFT JOIN users u ON u.id = s.user_id
            LEFT JOIN saas_plans p ON p.id = s.plan_id
            ORDER BY s.updated_at DESC
            LIMIT :limit
            """
        ),
        {"limit": max(1, min(int(limit or 100), 500))},
    )
    return [item for item in (_subscription_saas_from_row(row) for row in rows) if item]


def list_saas_payments(limit: int = 100) -> list[dict]:
    if not db_available():
        return []
    rows = fetch_all_safe(
        text(
            """
            SELECT p.*, u.email AS email
            FROM payments p
            LEFT JOIN users u ON u.id = p.user_id
            ORDER BY p.created_at DESC
            LIMIT :limit
            """
        ),
        {"limit": max(1, min(int(limit or 100), 500))},
    )
    return [item for item in (_payment_from_row(row) for row in rows) if item]


def list_saas_entitlements(limit: int = 200) -> list[dict]:
    if not db_available():
        user = promote_samir_super_admin()
        return [{"id": None, "user_id": user["id"], "email": user["email"], "feature_key": feature, "enabled": True, "source": "super_admin"} for feature in SUPER_ADMIN_ENTITLEMENTS]
    rows = fetch_all_safe(
        text(
            """
            SELECT e.*, u.email AS email
            FROM access_entitlements e
            LEFT JOIN users u ON u.id = e.user_id
            ORDER BY e.updated_at DESC
            LIMIT :limit
            """
        ),
        {"limit": max(1, min(int(limit or 200), 1000))},
    )
    return [item for item in (_entitlement_from_row(row) for row in rows) if item]


def update_entitlement(entitlement_id: str, payload: dict, actor_email: str = "system") -> dict:
    if not db_available():
        raise ValueError("database required")
    existing = fetch_one_safe(text("SELECT * FROM access_entitlements WHERE id = :id LIMIT 1"), {"id": entitlement_id})
    if not existing:
        raise ValueError("entitlement not found")
    enabled = bool(payload.get("enabled", existing.get("enabled")))
    source = payload.get("source") or existing.get("source") or "manual"
    execute_safe(
        text("UPDATE access_entitlements SET enabled = :enabled, source = :source, updated_at = :updated_at WHERE id = :id"),
        {"enabled": enabled, "source": source, "updated_at": _now(), "id": entitlement_id},
    )
    row = fetch_one_safe(text("SELECT * FROM access_entitlements WHERE id = :id LIMIT 1"), {"id": entitlement_id})
    updated = _entitlement_from_row(row)
    write_super_admin_audit(actor_email, "entitlement.update", "entitlement", entitlement_id, None, _entitlement_from_row(existing), updated)
    return updated


def list_super_admin_audit_log(limit: int = 100) -> list[dict]:
    if not db_available():
        return []
    rows = fetch_all_safe(text("SELECT * FROM super_admin_audit_log ORDER BY created_at DESC LIMIT :limit"), {"limit": max(1, min(int(limit or 100), 500))})
    return [item for item in (_audit_from_row(row) for row in rows) if item]


def build_revenue_summary() -> dict:
    payments = list_saas_payments(limit=500)
    subscriptions = list_saas_subscriptions(limit=500)
    plan_lookup = {plan.get("code"): plan for plan in list_saas_plans()}
    succeeded = [item for item in payments if item.get("status") == "succeeded"]
    failed = [item for item in payments if item.get("status") == "failed"]
    active = [item for item in subscriptions if item.get("status") in {"active", "trialing"}]
    return {
        "status": "ok",
        "currency": "EUR",
        "mrr_cents": sum(_int_or_zero((plan_lookup.get(item.get("plan_code")) or {}).get("price_monthly_cents")) for item in active),
        "revenue_30_days_cents": sum(_int_or_zero(item.get("amount_cents")) for item in succeeded),
        "succeeded_payments": len(succeeded),
        "failed_payments": len(failed),
        "payments_count": len(payments),
        "note": "Aucun paiement réel enregistré." if not payments else None,
    }


def build_super_admin_overview() -> dict:
    ensure_saas_defaults()
    users = list_saas_users(limit=500)
    subscriptions = list_saas_subscriptions(limit=500)
    payments = list_saas_payments(limit=500)
    plans = list_saas_plans()
    webhook_events = list_stripe_webhook_events(limit=10)
    active_users = [item for item in users if item.get("status") == "active"]
    paying = [item for item in subscriptions if item.get("status") in {"trialing", "active"}]
    failed_payments = [item for item in payments if item.get("status") == "failed"]
    plan_lookup = {plan.get("code"): plan for plan in plans}
    mrr = sum(_int_or_zero((plan_lookup.get(item.get("plan_code")) or {}).get("price_monthly_cents")) for item in paying)
    return {
        "status": "ok",
        "storage": "postgresql" if db_available() else "memory",
        "total_users": len(users),
        "active_users": len(active_users),
        "paying_subscribers": len(paying),
        "trial_users": len([item for item in subscriptions if item.get("status") == "trialing"]),
        "monthly_revenue_cents": mrr,
        "failed_payments": len(failed_payments),
        "active_plans": len([item for item in plans if item.get("is_active")]),
        "churn_risk_count": len([item for item in subscriptions if item.get("status") in {"past_due", "unpaid"}]),
        "latest_signups": users[:5],
        "latest_payments": payments[:5],
        "latest_webhook_events": webhook_events,
        "stripe_customers_count": len([item for item in users if item.get("stripe_customer_id")]),
        "active_subscriptions": len([item for item in subscriptions if item.get("status") == "active"]),
        "past_due_subscriptions": len([item for item in subscriptions if item.get("status") in {"past_due", "unpaid"}]),
        "users_without_customer": len([item for item in users if not item.get("stripe_customer_id")]),
        "system_status": {
            "billing": "configured" if payments or subscriptions else "no_real_payments",
            "stripe": "configured" if os.getenv("STRIPE_SECRET_KEY") else "missing",
            "webhooks": "received" if webhook_events else "none",
            "secrets": "server_side",
        },
    }


def update_user_metadata(email_or_id: str, metadata_patch: dict, actor_email: str = "system") -> dict:
    user = get_user_by_id_or_email(email_or_id)
    if not user:
        user = get_or_create_user_by_email(email_or_id)
    before = dict(user)
    metadata = {**(user.get("metadata") or {}), **(metadata_patch or {})}
    if db_available():
        execute_safe(
            text("UPDATE users SET metadata_json = :metadata_json, updated_at = :updated_at WHERE id = :id"),
            {"metadata_json": _json(metadata), "updated_at": _now(), "id": user["id"]},
        )
    updated = get_user_by_id_or_email(user["id"]) or {**user, "metadata": metadata}
    write_super_admin_audit(actor_email, "user.metadata.update", "user", user["id"], user.get("email"), before, updated)
    return updated


def save_refresh_log(
    source: str,
    storage: str,
    matches_imported: int,
    teams_imported: int,
    predictions_generated: int = 0,
    predictions_saved: int = 0,
    predictions_failed: int = 0,
    prediction_save_errors: list[str] | None = None,
) -> dict:
    report = {"saved": False, "error": None}
    engine = get_engine()
    if engine is None:
        report["error"] = "DATABASE_URL missing or PostgreSQL engine unavailable"
        return report

    statement = text(
        """
        INSERT INTO refresh_logs (
            id, source, storage, matches_imported, teams_imported,
            predictions_generated, predictions_saved, predictions_failed, prediction_save_errors_json, created_at
        )
        VALUES (
            :id, :source, :storage, :matches_imported, :teams_imported,
            :predictions_generated, :predictions_saved, :predictions_failed, :prediction_save_errors_json, :created_at
        )
        """
    )
    try:
        with engine.begin() as connection:
            connection.execute(
                statement,
                {
                    "id": str(uuid.uuid4()),
                    "source": source,
                    "storage": storage,
                    "matches_imported": matches_imported,
                    "teams_imported": teams_imported,
                    "predictions_generated": predictions_generated,
                    "predictions_saved": predictions_saved,
                    "predictions_failed": predictions_failed,
                    "prediction_save_errors_json": _json((prediction_save_errors or [])[:5]),
                    "created_at": _now(),
                },
            )
        report["saved"] = True
    except Exception as exc:
        report["error"] = str(exc)
        logger.exception("Refresh log insert failed")
    return report


def get_latest_refresh_log() -> dict | None:
    row = fetch_one_safe(
        text(
            """
            SELECT source, storage, matches_imported, teams_imported,
                   predictions_generated, predictions_saved, predictions_failed,
                   prediction_save_errors_json, created_at
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
        "predictions_generated": row.get("predictions_generated") or 0,
        "predictions_saved": row.get("predictions_saved") or 0,
        "predictions_failed": row.get("predictions_failed") or 0,
        "prediction_save_errors": _loads(row.get("prediction_save_errors_json")) or [],
        "last_refresh_at": created_at.isoformat() if hasattr(created_at, "isoformat") else created_at,
    }






def save_prediction_snapshot(prediction: dict) -> str | None:
    if not prediction or not db_available():
        return None

    snapshot_id = str(uuid.uuid4())
    prediction_id = prediction.get("match_id") or prediction.get("id") or prediction.get("slug")
    ok = execute_safe(
        text(
            """
            INSERT INTO prediction_snapshots (id, match_id, model_version, prediction_json, created_at)
            VALUES (:id, :match_id, :model_version, :prediction_json, :created_at)
            """
        ),
        {
            "id": snapshot_id,
            "match_id": prediction_id,
            "model_version": prediction.get("model_version", MODEL_VERSION),
            "prediction_json": _json(prediction),
            "created_at": _now(),
        },
    )
    return snapshot_id if ok else None


def save_prediction_snapshots(predictions: list[dict]) -> int:
    if not predictions or not db_available():
        return 0

    saved = 0
    for prediction in predictions:
        if save_prediction_snapshot(prediction):
            saved += 1
    return saved


def _snapshot_from_row(row: dict) -> dict:
    created_at = row.get("created_at")
    evaluated_at = row.get("evaluated_at")
    return {
        "id": row.get("id"),
        "match_id": row.get("match_id"),
        "model_version": row.get("model_version"),
        "prediction": _loads(row.get("prediction_json")),
        "prediction_json": row.get("prediction_json"),
        "created_at": created_at.isoformat() if hasattr(created_at, "isoformat") else created_at,
        "evaluated_at": evaluated_at.isoformat() if hasattr(evaluated_at, "isoformat") else evaluated_at,
        "actual_result": row.get("actual_result"),
        "result_correct": row.get("result_correct"),
        "brier_score_1x2": row.get("brier_score_1x2"),
    }


def get_prediction_snapshots(model_version: str | None = None, limit: int = 500) -> list[dict]:
    if not db_available():
        return []

    if model_version:
        rows = fetch_all_safe(
            text(
                """
                SELECT id, match_id, model_version, prediction_json, created_at, evaluated_at,
                       actual_result, result_correct, brier_score_1x2
                FROM prediction_snapshots
                WHERE model_version = :model_version
                ORDER BY created_at DESC
                LIMIT :limit
                """
            ),
            {"model_version": model_version, "limit": limit},
        )
    else:
        rows = fetch_all_safe(
            text(
                """
                SELECT id, match_id, model_version, prediction_json, created_at, evaluated_at,
                       actual_result, result_correct, brier_score_1x2
                FROM prediction_snapshots
                ORDER BY created_at DESC
                LIMIT :limit
                """
            ),
            {"limit": limit},
        )

    return [_snapshot_from_row(row) for row in rows]


def get_latest_prediction_snapshots(limit: int = 100) -> list[dict]:
    return get_prediction_snapshots(limit=limit)


def update_snapshot_evaluation(snapshot_id: str, evaluation: dict) -> bool:
    if not snapshot_id or not evaluation or not db_available():
        return False

    return execute_safe(
        text(
            """
            UPDATE prediction_snapshots
            SET evaluated_at = :evaluated_at,
                actual_result = :actual_result,
                result_correct = :result_correct,
                brier_score_1x2 = :brier_score_1x2
            WHERE id = :id
            """
        ),
        {
            "id": snapshot_id,
            "evaluated_at": _now(),
            "actual_result": evaluation.get("actual_result"),
            "result_correct": evaluation.get("result_correct"),
            "brier_score_1x2": evaluation.get("brier_score_1x2"),
        },
    )


def get_model_versions() -> list[str]:
    if not db_available():
        return []

    rows = fetch_all_safe(
        text(
            """
            SELECT DISTINCT model_version
            FROM prediction_snapshots
            WHERE model_version IS NOT NULL
            ORDER BY model_version
            """
        )
    )
    return [row.get("model_version") for row in rows if row.get("model_version")]


def init_model_versions_schema() -> bool:
    return init_db()


def _model_version_from_row(row: dict | None) -> dict | None:
    if not row:
        return None

    metrics = _loads(row.get("metrics_json")) or {}
    governance = _loads(row.get("governance_json")) or {}
    target_distribution = _loads(row.get("target_distribution_json")) or metrics.get("target_distribution") or {}

    return {
        "id": row.get("id"),
        "model_version": row.get("model_version"),
        "model_type": row.get("model_type"),
        "family": row.get("model_type"),
        "status": row.get("status"),
        "feature_set_version": row.get("feature_set_version"),
        "calibration_version": row.get("calibration_version"),
        "trained_at": _iso(row.get("trained_at")),
        "promoted_at": _iso(row.get("promoted_at")),
        "created_at": _iso(row.get("created_at")),
        "updated_at": _iso(row.get("updated_at")),
        "rows_used": row.get("rows_used") or 0,
        "features_used": row.get("features_used") or 0,
        "accuracy": row.get("accuracy"),
        "log_loss": row.get("log_loss"),
        "brier_score": row.get("brier_score"),
        "brier_score_1x2": row.get("brier_score"),
        "roi_theoretical": row.get("roi_theoretical"),
        "theoretical_roi": row.get("roi_theoretical"),
        "target_distribution": target_distribution,
        "metrics": metrics,
        "governance": governance,
        "notes": row.get("notes"),
        "source": row.get("source") or "postgresql",
        "artifact_path": metrics.get("artifact_path"),
    }


def _normalize_model_version(version: dict) -> dict:
    metrics = dict(version.get("metrics") or {})
    if version.get("artifact_path") and not metrics.get("artifact_path"):
        metrics["artifact_path"] = version.get("artifact_path")
    if version.get("feature_columns") and not metrics.get("feature_columns"):
        metrics["feature_columns"] = version.get("feature_columns")

    target_distribution = (
        version.get("target_distribution")
        or version.get("target_distribution_json")
        or metrics.get("target_distribution")
        or {}
    )
    governance = version.get("governance") or version.get("governance_json") or {}
    created_at = _parse_datetime(version.get("created_at")) or _now()
    updated_at = _now()

    return {
        "id": version.get("id") or str(uuid.uuid4()),
        "model_version": version.get("model_version"),
        "model_type": version.get("model_type") or version.get("family"),
        "status": version.get("status") or "candidate",
        "feature_set_version": version.get("feature_set_version"),
        "calibration_version": version.get("calibration_version"),
        "trained_at": _parse_datetime(version.get("trained_at")),
        "promoted_at": _parse_datetime(version.get("promoted_at")),
        "created_at": created_at,
        "updated_at": updated_at,
        "rows_used": _int_or_zero(version.get("rows_used")),
        "features_used": _feature_count(version.get("features_used"), metrics),
        "accuracy": _num_or_none(version.get("accuracy", metrics.get("accuracy"))),
        "log_loss": _num_or_none(version.get("log_loss", metrics.get("log_loss"))),
        "brier_score": _num_or_none(version.get("brier_score", metrics.get("brier_score") or metrics.get("brier_score_1x2"))),
        "roi_theoretical": _num_or_none(version.get("roi_theoretical", version.get("theoretical_roi", metrics.get("theoretical_roi")))),
        "target_distribution_json": _json(target_distribution),
        "metrics_json": _json(metrics),
        "governance_json": _json(governance),
        "notes": version.get("notes"),
        "source": version.get("source") or "postgresql",
    }


def save_model_version(version: dict) -> dict | None:
    if not version or not version.get("model_version") or not db_available():
        return None

    row = _normalize_model_version(version)
    existing = get_model_version(row["model_version"])
    if existing:
        merged_metrics = {**(existing.get("metrics") or {}), **(_loads(row["metrics_json"]) or {})}
        merged_governance = {**(existing.get("governance") or {}), **(_loads(row["governance_json"]) or {})}
        incoming_status = row["status"]
        current_status = existing.get("status") or "candidate"
        next_status = current_status
        if current_status != "production" and incoming_status not in {"shadow"}:
            next_status = incoming_status
        if incoming_status == "shadow":
            merged_metrics["shadow_registry_update"] = True

        execute_safe(
            text(
                """
                UPDATE model_versions
                SET model_type = COALESCE(:model_type, model_type),
                    status = :status,
                    feature_set_version = COALESCE(:feature_set_version, feature_set_version),
                    calibration_version = COALESCE(:calibration_version, calibration_version),
                    trained_at = COALESCE(:trained_at, trained_at),
                    promoted_at = COALESCE(:promoted_at, promoted_at),
                    updated_at = :updated_at,
                    rows_used = CASE WHEN :rows_used > rows_used THEN :rows_used ELSE rows_used END,
                    features_used = CASE WHEN :features_used > features_used THEN :features_used ELSE features_used END,
                    accuracy = COALESCE(:accuracy, accuracy),
                    log_loss = COALESCE(:log_loss, log_loss),
                    brier_score = COALESCE(:brier_score, brier_score),
                    roi_theoretical = COALESCE(:roi_theoretical, roi_theoretical),
                    target_distribution_json = COALESCE(:target_distribution_json, target_distribution_json),
                    metrics_json = :metrics_json,
                    governance_json = :governance_json,
                    notes = COALESCE(:notes, notes),
                    source = CASE WHEN source = 'postgresql' THEN source ELSE :source END
                WHERE model_version = :model_version
                """
            ),
            {
                **row,
                "status": next_status,
                "metrics_json": _json(merged_metrics),
                "governance_json": _json(merged_governance),
            },
        )
        return get_model_version(row["model_version"])

    ok = execute_safe(
        text(
            """
            INSERT INTO model_versions (
                id, model_version, model_type, status, feature_set_version, calibration_version,
                trained_at, promoted_at, created_at, updated_at, rows_used, features_used,
                accuracy, log_loss, brier_score, roi_theoretical, target_distribution_json,
                metrics_json, governance_json, notes, source
            )
            VALUES (
                :id, :model_version, :model_type, :status, :feature_set_version, :calibration_version,
                :trained_at, :promoted_at, :created_at, :updated_at, :rows_used, :features_used,
                :accuracy, :log_loss, :brier_score, :roi_theoretical, :target_distribution_json,
                :metrics_json, :governance_json, :notes, :source
            )
            """
        ),
        row,
    )
    return get_model_version(row["model_version"]) if ok else None


def list_model_versions(limit: int = 100) -> list[dict]:
    if not db_available():
        return []
    safe_limit = max(1, min(int(limit or 100), 500))
    rows = fetch_all_safe(
        text(
            """
            SELECT *
            FROM model_versions
            ORDER BY COALESCE(trained_at, created_at) DESC, created_at DESC
            LIMIT :limit
            """
        ),
        {"limit": safe_limit},
    )
    return [item for item in (_model_version_from_row(row) for row in rows) if item]


def get_model_version(model_version: str) -> dict | None:
    if not model_version or not db_available():
        return None
    row = fetch_one_safe(text("SELECT * FROM model_versions WHERE model_version = :model_version LIMIT 1"), {"model_version": model_version})
    return _model_version_from_row(row)


def get_current_production_model() -> dict | None:
    row = fetch_one_safe(
        text(
            """
            SELECT *
            FROM model_versions
            WHERE status = 'production'
            ORDER BY COALESCE(promoted_at, trained_at, created_at) DESC
            LIMIT 1
            """
        )
    )
    return _model_version_from_row(row)


def get_latest_candidate_model() -> dict | None:
    row = fetch_one_safe(
        text(
            """
            SELECT *
            FROM model_versions
            WHERE status = 'candidate'
            ORDER BY COALESCE(trained_at, created_at) DESC
            LIMIT 1
            """
        )
    )
    if not row:
        row = fetch_one_safe(
            text(
                """
                SELECT *
                FROM model_versions
                WHERE status = 'shadow'
                ORDER BY COALESCE(trained_at, created_at) DESC
                LIMIT 1
                """
            )
        )
    return _model_version_from_row(row)


def update_model_version_status(model_version: str, status: str) -> dict | None:
    allowed = {"candidate", "production", "shadow", "archived", "rejected"}
    if not model_version or status not in allowed or not db_available():
        return None
    execute_safe(
        text(
            """
            UPDATE model_versions
            SET status = :status, updated_at = :updated_at
            WHERE model_version = :model_version
            """
        ),
        {"model_version": model_version, "status": status, "updated_at": _now()},
    )
    return get_model_version(model_version)


def promote_model_version(model_version: str) -> dict | None:
    if not model_version or not db_available():
        return None
    execute_safe(
        text(
            """
            UPDATE model_versions
            SET status = 'archived', updated_at = :updated_at
            WHERE status = 'production' AND model_version <> :model_version
            """
        ),
        {"model_version": model_version, "updated_at": _now()},
    )
    execute_safe(
        text(
            """
            UPDATE model_versions
            SET status = 'production', promoted_at = :promoted_at, updated_at = :updated_at
            WHERE model_version = :model_version
            """
        ),
        {"model_version": model_version, "promoted_at": _now(), "updated_at": _now()},
    )
    return get_model_version(model_version)


def archive_model_version(model_version: str) -> dict | None:
    return update_model_version_status(model_version, "archived")


def init_model_promotion_audit_schema() -> bool:
    return init_db()


def _promotion_audit_from_row(row: dict | None) -> dict | None:
    if not row:
        return None
    created_at = row.get("created_at")
    return {
        "id": row.get("id"),
        "action": row.get("action"),
        "candidate_model_version": row.get("candidate_model_version"),
        "previous_production_model_version": row.get("previous_production_model_version"),
        "new_production_model_version": row.get("new_production_model_version"),
        "requested_by": row.get("requested_by"),
        "governance": _loads(row.get("governance_json")) or {},
        "result": row.get("result"),
        "detail": row.get("detail"),
        "created_at": created_at.isoformat() if hasattr(created_at, "isoformat") else created_at,
    }


def log_model_promotion_event(
    *,
    action: str,
    candidate_model_version: str | None = None,
    previous_production_model_version: str | None = None,
    new_production_model_version: str | None = None,
    requested_by: str | None = None,
    governance: dict | None = None,
    result: str | None = None,
    detail: str | None = None,
) -> dict | None:
    if not action or not db_available():
        return None

    audit_id = str(uuid.uuid4())
    ok = execute_safe(
        text(
            """
            INSERT INTO model_promotion_audit (
                id, action, candidate_model_version, previous_production_model_version,
                new_production_model_version, requested_by, governance_json, result, detail, created_at
            )
            VALUES (
                :id, :action, :candidate_model_version, :previous_production_model_version,
                :new_production_model_version, :requested_by, :governance_json, :result, :detail, :created_at
            )
            """
        ),
        {
            "id": audit_id,
            "action": action,
            "candidate_model_version": candidate_model_version,
            "previous_production_model_version": previous_production_model_version,
            "new_production_model_version": new_production_model_version,
            "requested_by": requested_by,
            "governance_json": _json(governance or {}),
            "result": result,
            "detail": detail,
            "created_at": _now(),
        },
    )
    if not ok:
        return None
    row = fetch_one_safe(text("SELECT * FROM model_promotion_audit WHERE id = :id LIMIT 1"), {"id": audit_id})
    return _promotion_audit_from_row(row)


def list_model_promotion_audit(limit: int = 50) -> list[dict]:
    if not db_available():
        return []
    try:
        parsed_limit = int(limit or 50)
    except (TypeError, ValueError):
        parsed_limit = 50
    safe_limit = max(1, min(parsed_limit, 200))
    rows = fetch_all_safe(
        text(
            """
            SELECT *
            FROM model_promotion_audit
            ORDER BY created_at DESC
            LIMIT :limit
            """
        ),
        {"limit": safe_limit},
    )
    return [item for item in (_promotion_audit_from_row(row) for row in rows) if item]


def get_latest_model_promotion_event(action: str) -> dict | None:
    if not action or not db_available():
        return None
    row = fetch_one_safe(
        text(
            """
            SELECT *
            FROM model_promotion_audit
            WHERE action = :action AND result = 'success'
            ORDER BY created_at DESC
            LIMIT 1
            """
        ),
        {"action": action},
    )
    return _promotion_audit_from_row(row)


def init_model_calibrations_schema() -> bool:
    return init_db()


def _model_calibration_from_row(row: dict | None) -> dict | None:
    if not row:
        return None
    return {
        "id": row.get("id"),
        "calibration_version": row.get("calibration_version"),
        "model_version": row.get("model_version"),
        "model_type": row.get("model_type"),
        "source": row.get("source"),
        "method": row.get("method"),
        "status": row.get("status"),
        "samples_count": row.get("samples_count") or 0,
        "buckets": _loads(row.get("buckets_json")) or [],
        "factors": _loads(row.get("factors_json")) or {},
        "metrics": _loads(row.get("metrics_json")) or {},
        "recommendation": _loads(row.get("recommendation_json")) or {},
        "created_at": _iso(row.get("created_at")),
        "activated_at": _iso(row.get("activated_at")),
    }


def create_model_calibration(calibration: dict) -> dict | None:
    if not calibration or not calibration.get("calibration_version") or not db_available():
        return None

    init_model_calibrations_schema()
    calibration_version = calibration.get("calibration_version")
    existing = fetch_one_safe(
        text("SELECT * FROM model_calibrations WHERE calibration_version = :calibration_version LIMIT 1"),
        {"calibration_version": calibration_version},
    )
    row = {
        "id": calibration.get("id") or str(uuid.uuid4()),
        "calibration_version": calibration_version,
        "model_version": calibration.get("model_version"),
        "model_type": calibration.get("model_type"),
        "source": calibration.get("source") or "system",
        "method": calibration.get("method") or "bucket_scaling",
        "status": calibration.get("status") or "candidate",
        "samples_count": _int_or_zero(calibration.get("samples_count") or calibration.get("sample_size")),
        "buckets_json": _json(calibration.get("buckets") or []),
        "factors_json": _json(calibration.get("factors") or calibration.get("factors_json") or {}),
        "metrics_json": _json(calibration.get("metrics") or {}),
        "recommendation_json": _json(calibration.get("recommendation") or {}),
        "created_at": _parse_datetime(calibration.get("created_at")) or _now(),
        "activated_at": _parse_datetime(calibration.get("activated_at")),
    }
    if existing:
        execute_safe(
            text(
                """
                UPDATE model_calibrations
                SET model_version = COALESCE(:model_version, model_version),
                    model_type = COALESCE(:model_type, model_type),
                    source = :source,
                    method = :method,
                    status = :status,
                    samples_count = :samples_count,
                    buckets_json = :buckets_json,
                    factors_json = :factors_json,
                    metrics_json = :metrics_json,
                    recommendation_json = :recommendation_json,
                    activated_at = COALESCE(:activated_at, activated_at)
                WHERE calibration_version = :calibration_version
                """
            ),
            row,
        )
    else:
        execute_safe(
            text(
                """
                INSERT INTO model_calibrations (
                    id, calibration_version, model_version, model_type, source, method, status,
                    samples_count, buckets_json, factors_json, metrics_json, recommendation_json,
                    created_at, activated_at
                )
                VALUES (
                    :id, :calibration_version, :model_version, :model_type, :source, :method, :status,
                    :samples_count, :buckets_json, :factors_json, :metrics_json, :recommendation_json,
                    :created_at, :activated_at
                )
                """
            ),
            row,
        )

    return get_model_calibration(calibration_version)


def get_model_calibration(calibration_version: str | None) -> dict | None:
    if not calibration_version or not db_available():
        return None
    row = fetch_one_safe(
        text("SELECT * FROM model_calibrations WHERE calibration_version = :calibration_version LIMIT 1"),
        {"calibration_version": calibration_version},
    )
    return _model_calibration_from_row(row)


def list_model_calibrations(limit: int = 50) -> list[dict]:
    if not db_available():
        return []
    safe_limit = max(1, min(int(limit or 50), 200))
    rows = fetch_all_safe(
        text(
            """
            SELECT *
            FROM model_calibrations
            ORDER BY COALESCE(activated_at, created_at) DESC, created_at DESC
            LIMIT :limit
            """
        ),
        {"limit": safe_limit},
    )
    return [item for item in (_model_calibration_from_row(row) for row in rows) if item]


def get_latest_calibration() -> dict | None:
    rows = list_model_calibrations(limit=1)
    return rows[0] if rows else None


def get_active_calibration() -> dict | None:
    if not db_available():
        return None
    row = fetch_one_safe(
        text(
            """
            SELECT *
            FROM model_calibrations
            WHERE status = 'active'
            ORDER BY COALESCE(activated_at, created_at) DESC
            LIMIT 1
            """
        )
    )
    return _model_calibration_from_row(row)


def archive_old_calibrations(except_version: str | None = None) -> int:
    if not db_available():
        return 0
    params = {"except_version": except_version}
    statement = "UPDATE model_calibrations SET status = 'archived' WHERE status = 'active'"
    if except_version:
        statement += " AND calibration_version <> :except_version"
    execute_safe(text(statement), params)
    rows = fetch_all_safe(text("SELECT id FROM model_calibrations WHERE status = 'archived'"))
    return len(rows)


def activate_calibration_version(calibration_version: str | None) -> dict | None:
    if not calibration_version or not db_available():
        return None
    calibration = get_model_calibration(calibration_version)
    if not calibration or calibration.get("status") == "insufficient_data":
        return None
    archive_old_calibrations(except_version=calibration_version)
    execute_safe(
        text(
            """
            UPDATE model_calibrations
            SET status = 'active', activated_at = :activated_at
            WHERE calibration_version = :calibration_version
            """
        ),
        {"calibration_version": calibration_version, "activated_at": _now()},
    )
    return get_model_calibration(calibration_version)


def import_model_versions_from_file_if_needed(file_path: str | Path | None = None) -> dict:
    if not db_available():
        return {"status": "skipped", "storage": "file_fallback", "imported_count": 0, "reason": "database_unavailable"}
    if list_model_versions(limit=1):
        return {"status": "skipped", "storage": "postgresql", "imported_count": 0, "reason": "postgresql_already_seeded"}

    registry_path = Path(file_path) if file_path else Path(__file__).resolve().parents[1] / "ml_models" / "model_versions.json"
    if not registry_path.exists():
        return {"status": "skipped", "storage": "postgresql", "imported_count": 0, "reason": "file_missing"}

    try:
        payload = json.loads(registry_path.read_text(encoding="utf-8"))
        rows = payload if isinstance(payload, list) else []
    except Exception as exc:
        return {"status": "error", "storage": "postgresql", "imported_count": 0, "detail": str(exc)}

    imported = 0
    for item in rows:
        if not isinstance(item, dict) or not item.get("model_version"):
            continue
        imported_item = dict(item)
        metrics = dict(imported_item.get("metrics") or {})
        metrics["source_imported_from"] = "file"
        imported_item["metrics"] = metrics
        imported_item["source"] = "file"
        if save_model_version(imported_item):
            imported += 1

    return {"status": "ok", "storage": "postgresql", "imported_count": imported, "source_file": str(registry_path)}



def _feature_row_to_snapshot(row: dict) -> dict:
    created_at = row.get("created_at")
    payload = _loads(row.get("payload_json")) or {}
    features = _loads(row.get("features_json")) or payload.get("features") or {}
    return {
        "id": row.get("id"),
        "match_id": row.get("match_id"),
        "model_version": row.get("model_version"),
        "feature_set_version": FEATURE_SET_VERSION if any(name in features for name in ADVANCED_FEATURE_COLUMNS) else None,
        "features": features,
        "target": _loads(row.get("target_json")) if row.get("target_json") else payload.get("target"),
        "payload": payload,
        "created_at": created_at.isoformat() if hasattr(created_at, "isoformat") else created_at,
    }


def save_feature_snapshot(match_id: str, model_version: str, features: dict, target: dict | None = None) -> str | None:
    if not match_id or not features or not db_available():
        return None

    snapshot_id = str(uuid.uuid4())
    ok = execute_safe(
        text(
            """
            INSERT INTO feature_snapshots (id, match_id, model_version, features_json, target_json, created_at)
            VALUES (:id, :match_id, :model_version, :features_json, :target_json, :created_at)
            """
        ),
        {
            "id": snapshot_id,
            "match_id": match_id,
            "model_version": model_version,
            "features_json": _json(features),
            "target_json": _json(target) if target is not None else None,
            "created_at": _now(),
        },
    )
    return snapshot_id if ok else None


def save_feature_snapshots(items: list[dict]) -> dict:
    global _last_feature_snapshot_save_report

    report = {
        "saved_count": 0,
        "inserted_count": 0,
        "updated_count": 0,
        "skipped_existing_count": 0,
        "failed_count": 0,
        "errors": [],
    }
    if not items:
        _last_feature_snapshot_save_report = dict(report)
        return report

    engine = get_engine()
    if engine is None:
        report["failed_count"] = len(items)
        report["errors"].append("DATABASE_URL missing or PostgreSQL engine unavailable")
        _last_feature_snapshot_save_report = dict(report)
        return report

    statement = text(
        """
        INSERT INTO feature_snapshots (id, match_id, model_version, features_json, target_json, payload_json, created_at)
        VALUES (:id, :match_id, :model_version, :features_json, :target_json, :payload_json, :created_at)
        ON CONFLICT(match_id, model_version) DO UPDATE SET
            features_json = EXCLUDED.features_json,
            target_json = EXCLUDED.target_json,
            payload_json = EXCLUDED.payload_json,
            created_at = EXCLUDED.created_at
        """
    )

    for item in items:
        try:
            match_id = item.get("match_id")
            model_version = item.get("model_version", MODEL_VERSION)
            features = item.get("features") or {}
            if not match_id:
                raise ValueError("Feature snapshot missing match_id")
            if not features:
                raise ValueError("Feature snapshot missing features")
            existed = fetch_one_safe(
                text("SELECT id FROM feature_snapshots WHERE match_id = :match_id AND model_version = :model_version LIMIT 1"),
                {"match_id": match_id, "model_version": model_version},
            ) is not None
            with engine.begin() as connection:
                connection.execute(
                    statement,
                    {
                        "id": str(uuid.uuid4()),
                        "match_id": match_id,
                        "model_version": model_version,
                        "features_json": _json(features),
                        "target_json": _json(item.get("target")) if item.get("target") is not None else None,
                        "payload_json": _json(item),
                        "created_at": _now(),
                    },
                )
            report["saved_count"] += 1
            if existed:
                report["updated_count"] += 1
            else:
                report["inserted_count"] += 1
        except Exception as exc:
            report["failed_count"] += 1
            if len(report["errors"]) < 5:
                report["errors"].append(str(exc))
            logger.exception("Feature snapshot insert failed")

    _last_feature_snapshot_save_report = dict(report)
    return report


def get_last_feature_snapshot_save_report() -> dict:
    return dict(_last_feature_snapshot_save_report)


def count_feature_snapshots() -> int:
    row = fetch_one_safe(text("SELECT COUNT(*) AS count FROM feature_snapshots"))
    return int(row.get("count", 0)) if row else 0


def count_feature_snapshots_with_target() -> int:
    row = fetch_one_safe(
        text(
            """
            SELECT COUNT(*) AS count
            FROM feature_snapshots
            WHERE target_json IS NOT NULL
              AND target_json <> ''
              AND target_json <> '{}'
              AND target_json <> 'null'
            """
        )
    )
    return int(row.get("count", 0)) if row else 0


def feature_snapshots_schema_ok() -> bool:
    engine = get_engine()
    if engine is None:
        return False
    required = {"id", "match_id", "model_version", "features_json", "target_json", "created_at"}
    try:
        if engine.dialect.name == "postgresql":
            rows = fetch_all_safe(
                text(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = 'feature_snapshots'
                    """
                )
            )
            columns = {row.get("column_name") for row in rows}
        elif engine.dialect.name == "sqlite":
            with engine.connect() as connection:
                rows = connection.execute(text("PRAGMA table_info(feature_snapshots)")).fetchall()
            columns = {row._mapping["name"] for row in rows}
        else:
            return False
        return required.issubset(columns) and ("features_json" in columns or "payload_json" in columns)
    except Exception as exc:
        logger.warning("Feature snapshot schema inspection failed: %s", exc)
        return False


def get_feature_snapshots(model_version: str | None = None, limit: int = 5000) -> list[dict]:
    if not db_available():
        return []

    limit = max(1, min(int(limit or 5000), 5000))
    if model_version:
        rows = fetch_all_safe(
            text(
                """
                SELECT id, match_id, model_version, features_json, target_json, payload_json, created_at
                FROM feature_snapshots
                WHERE model_version = :model_version
                ORDER BY created_at DESC
                LIMIT :limit
                """
            ),
            {"model_version": model_version, "limit": limit},
        )
    else:
        rows = fetch_all_safe(
            text(
                """
                SELECT id, match_id, model_version, features_json, target_json, payload_json, created_at
                FROM feature_snapshots
                ORDER BY created_at DESC
                LIMIT :limit
                """
            ),
            {"limit": limit},
        )
    return [_feature_row_to_snapshot(row) for row in rows]


def get_training_dataset(model_version: str | None = None, limit: int = 500) -> list[dict]:
    snapshots = get_feature_snapshots(model_version=model_version, limit=limit)
    return [item for item in snapshots if item.get("target")]


def get_feature_store_summary() -> dict:
    snapshots = get_feature_snapshots(limit=5000)
    snapshots_count = len(snapshots)
    with_target_count = sum(1 for item in snapshots if item.get("target"))
    feature_names = set()
    model_versions: dict[str, int] = {}

    for item in snapshots:
        model_version = item.get("model_version") or "unknown"
        model_versions[model_version] = model_versions.get(model_version, 0) + 1
        feature_names.update((item.get("features") or {}).keys())

    return {
        "snapshots_count": snapshots_count,
        "with_target_count": with_target_count,
        "without_target_count": snapshots_count - with_target_count,
        "model_versions": model_versions,
        "feature_names": sorted(feature_names),
        "feature_set_version": FEATURE_SET_VERSION if any(name in feature_names for name in ADVANCED_FEATURE_COLUMNS) else None,
        "advanced_feature_coverage": _advanced_feature_coverage(feature_names),
        "target_coverage": round((with_target_count / snapshots_count) * 100) if snapshots_count else 0,
    }


def _advanced_feature_coverage(feature_names: set[str]) -> dict:
    present = len([name for name in ADVANCED_FEATURE_COLUMNS if name in feature_names])
    expected = len(ADVANCED_FEATURE_COLUMNS)
    return {
        "advanced_features_present": present,
        "advanced_features_expected": expected,
        "coverage_percent": round((present / expected) * 100) if expected else 0,
    }
def get_feature_snapshot_keys(model_version: str | None = None) -> set[str]:
    try:
        rows = get_feature_snapshots(model_version=model_version)

        keys: set[str] = set()

        for row in rows:
            match_id = row.get("match_id")
            version = row.get("model_version")

            if match_id and version:
                keys.add(f"{match_id}:{version}")

        return keys
    except Exception:
        return set()


def _shadow_from_row(row: dict) -> dict:
    created_at = row.get("created_at")
    return {
        "id": row.get("id"),
        "match_id": row.get("match_id"),
        "production_model_version": row.get("production_model_version"),
        "candidate_model_version": row.get("candidate_model_version"),
        "production_prediction": _loads(row.get("production_prediction_json")) or {},
        "shadow_prediction": _loads(row.get("shadow_prediction_json")) or {},
        "comparison": _loads(row.get("comparison_json")) or {},
        "created_at": created_at.isoformat() if hasattr(created_at, "isoformat") else created_at,
    }


def save_ml_shadow_prediction(match_id: str, production_prediction: dict, shadow_prediction: dict, comparison: dict) -> str | None:
    if not match_id or not db_available():
        return None

    row_id = str(uuid.uuid4())
    ok = execute_safe(
        text(
            """
            INSERT INTO ml_shadow_predictions (
                id, match_id, production_model_version, candidate_model_version,
                production_prediction_json, shadow_prediction_json, comparison_json, created_at
            )
            VALUES (
                :id, :match_id, :production_model_version, :candidate_model_version,
                :production_prediction_json, :shadow_prediction_json, :comparison_json, :created_at
            )
            """
        ),
        {
            "id": row_id,
            "match_id": match_id,
            "production_model_version": production_prediction.get("model_version", MODEL_VERSION),
            "candidate_model_version": shadow_prediction.get("model_version"),
            "production_prediction_json": _json(production_prediction),
            "shadow_prediction_json": _json(shadow_prediction),
            "comparison_json": _json(comparison),
            "created_at": _now(),
        },
    )
    return row_id if ok else None


def save_ml_shadow_predictions(items: list[dict]) -> int:
    saved = 0
    for item in items or []:
        if save_ml_shadow_prediction(
            item.get("match_id"),
            item.get("production_prediction") or {},
            item.get("shadow_prediction") or {},
            item.get("comparison") or {},
        ):
            saved += 1
    return saved


def get_ml_shadow_predictions(limit: int = 100) -> list[dict]:
    if not db_available():
        return []
    rows = fetch_all_safe(
        text(
            """
            SELECT id, match_id, production_model_version, candidate_model_version,
                   production_prediction_json, shadow_prediction_json, comparison_json, created_at
            FROM ml_shadow_predictions
            ORDER BY created_at DESC
            LIMIT :limit
            """
        ),
        {"limit": max(1, min(int(limit or 100), 500))},
    )
    return [_shadow_from_row(row) for row in rows]


def get_ml_shadow_prediction(match_id: str) -> dict | None:
    if not match_id or not db_available():
        return None
    row = fetch_one_safe(
        text(
            """
            SELECT id, match_id, production_model_version, candidate_model_version,
                   production_prediction_json, shadow_prediction_json, comparison_json, created_at
            FROM ml_shadow_predictions
            WHERE match_id = :match_id
            ORDER BY created_at DESC
            LIMIT 1
            """
        ),
        {"match_id": match_id},
    )
    return _shadow_from_row(row) if row else None


def get_ml_shadow_summary() -> dict:
    rows = get_ml_shadow_predictions(limit=500)
    available = [row for row in rows if (row.get("shadow_prediction") or {}).get("available")]
    disagreements = [row for row in rows if (row.get("comparison") or {}).get("same_pick") is False]
    high = [row for row in rows if (row.get("comparison") or {}).get("disagreement_level") == "high"]
    same = [row for row in rows if (row.get("comparison") or {}).get("same_pick") is True]
    candidate_versions = [
        (row.get("shadow_prediction") or {}).get("model_version") or row.get("candidate_model_version")
        for row in rows
        if (row.get("shadow_prediction") or {}).get("model_version") or row.get("candidate_model_version")
    ]
    return {
        "shadow_predictions_count": len(rows),
        "available_count": len(available),
        "unavailable_count": len(rows) - len(available),
        "same_pick_count": len(same),
        "disagreement_count": len(disagreements),
        "high_disagreement_count": len(high),
        "candidate_model_version": candidate_versions[0] if candidate_versions else None,
    }


PIPELINE_JOB_TYPES = {
    "refresh_data",
    "build_feature_store",
    "train_candidate_model",
    "generate_shadow_predictions",
    "shadow_backtesting",
    "learning_monitoring",
    "match_finished_check",
    "calibration",
    "feedback",
}


def init_pipeline_jobs_schema() -> bool:
    return init_db()


def _pipeline_job_from_row(row: dict | None):
    if not row:
        return None
    item = dict(row)
    item["result_json"] = _loads(item.get("result_json")) or {}
    for key in ("started_at", "finished_at", "created_at", "updated_at"):
        item[key] = _iso(item.get(key))
    return item


def create_pipeline_job(job_type: str, triggered_by: str = "system", status: str = "queued", job_id: str | None = None) -> dict | None:
    if not db_available():
        return None
    now = _now()
    job_id = job_id or str(uuid.uuid4())
    execute_safe(
        text(
            """
            INSERT INTO pipeline_jobs (id, job_type, status, started_at, finished_at, duration_ms, result_json, error, triggered_by, created_at, updated_at)
            VALUES (:id, :job_type, :status, NULL, NULL, NULL, :result_json, NULL, :triggered_by, :created_at, :updated_at)
            """
        ),
        {
            "id": job_id,
            "job_type": str(job_type or "unknown"),
            "status": status,
            "result_json": _json({}),
            "triggered_by": triggered_by,
            "created_at": now,
            "updated_at": now,
        },
    )
    return _pipeline_job_from_row(fetch_one_safe(text("SELECT * FROM pipeline_jobs WHERE id = :id"), {"id": job_id}))


def mark_pipeline_job_running(job_id: str) -> dict | None:
    if not job_id or not db_available():
        return None
    now = _now()
    execute_safe(
        text("UPDATE pipeline_jobs SET status = 'running', started_at = COALESCE(started_at, :now), updated_at = :now WHERE id = :id"),
        {"id": job_id, "now": now},
    )
    return _pipeline_job_from_row(fetch_one_safe(text("SELECT * FROM pipeline_jobs WHERE id = :id"), {"id": job_id}))


def _finish_pipeline_job(job_id: str, status: str, result: dict | None = None, error: str | None = None) -> dict | None:
    if not job_id or not db_available():
        return None
    now = _now()
    row = fetch_one_safe(text("SELECT started_at FROM pipeline_jobs WHERE id = :id"), {"id": job_id})
    started_at = _parse_datetime((row or {}).get("started_at"))
    duration_ms = None
    if started_at:
        duration_ms = max(0, round((now - started_at.replace(tzinfo=None)).total_seconds() * 1000))
    execute_safe(
        text(
            """
            UPDATE pipeline_jobs
            SET status = :status,
                finished_at = :finished_at,
                duration_ms = :duration_ms,
                result_json = :result_json,
                error = :error,
                updated_at = :updated_at
            WHERE id = :id
            """
        ),
        {
            "id": job_id,
            "status": status,
            "finished_at": now,
            "duration_ms": duration_ms,
            "result_json": _json(result or {}),
            "error": error,
            "updated_at": now,
        },
    )
    return _pipeline_job_from_row(fetch_one_safe(text("SELECT * FROM pipeline_jobs WHERE id = :id"), {"id": job_id}))


def mark_pipeline_job_success(job_id: str, result: dict | None = None) -> dict | None:
    return _finish_pipeline_job(job_id, "success", result=result)


def mark_pipeline_job_error(job_id: str, error: str, result: dict | None = None) -> dict | None:
    return _finish_pipeline_job(job_id, "error", result=result, error=error)


def mark_pipeline_job_skipped(job_id: str, reason: str, result: dict | None = None) -> dict | None:
    return _finish_pipeline_job(job_id, "skipped", result={"reason": reason, **(result or {})})


def list_pipeline_jobs(limit: int = 100, job_type: str | None = None) -> list[dict]:
    if not db_available():
        return []
    safe_limit = max(1, min(_int_or_zero(limit) or 100, 500))
    if job_type:
        rows = fetch_all_safe(
            text("SELECT * FROM pipeline_jobs WHERE job_type = :job_type ORDER BY created_at DESC LIMIT :limit"),
            {"job_type": job_type, "limit": safe_limit},
        )
    else:
        rows = fetch_all_safe(text("SELECT * FROM pipeline_jobs ORDER BY created_at DESC LIMIT :limit"), {"limit": safe_limit})
    return [item for item in (_pipeline_job_from_row(row) for row in rows) if item]


def get_latest_pipeline_job(job_type: str) -> dict | None:
    if not job_type or not db_available():
        return None
    row = fetch_one_safe(
        text("SELECT * FROM pipeline_jobs WHERE job_type = :job_type ORDER BY created_at DESC LIMIT 1"),
        {"job_type": job_type},
    )
    return _pipeline_job_from_row(row)


def get_running_pipeline_jobs() -> list[dict]:
    if not db_available():
        return []
    rows = fetch_all_safe(text("SELECT * FROM pipeline_jobs WHERE status = 'running' ORDER BY started_at ASC LIMIT 100"), {})
    return [item for item in (_pipeline_job_from_row(row) for row in rows) if item]


def reset_stale_pipeline_jobs(max_age_minutes: int = 15) -> dict:
    if not db_available():
        return {"status": "unavailable", "storage": "memory", "reset_count": 0, "jobs": []}
    now = _now()
    reset = []
    max_age_seconds = max(1, int(max_age_minutes or 15)) * 60
    for job in get_running_pipeline_jobs():
        started_at = _parse_datetime(job.get("started_at"))
        if not started_at:
            continue
        age_seconds = (now - started_at.replace(tzinfo=None)).total_seconds()
        if age_seconds >= max_age_seconds:
            updated = _finish_pipeline_job(
                job["id"],
                "stale",
                result={"reason": f"Job running for more than {max_age_minutes} minutes.", "stale_after_minutes": max_age_minutes},
                error="stale_pipeline_job",
            )
            if updated:
                reset.append(updated)
    return {"status": "ok", "storage": "postgresql", "reset_count": len(reset), "jobs": reset}
