import json
import logging
import uuid
from datetime import datetime

from sqlalchemy import text

from data.database import db_available, execute_safe, fetch_all_safe, fetch_one_safe, get_engine
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
