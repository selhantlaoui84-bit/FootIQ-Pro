import logging
import os
from datetime import datetime

from sqlalchemy import Boolean, Column, Float, Integer, MetaData, Table, Text, TIMESTAMP, create_engine, text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

metadata = MetaData()
_engine: Engine | None = None

teams_table = Table(
    "teams",
    metadata,
    Column("id", Text, primary_key=True),
    Column("slug", Text),
    Column("name", Text),
    Column("competition", Text),
    Column("source", Text),
    Column("raw_json", Text, nullable=True),
    Column("updated_at", TIMESTAMP(timezone=True)),
)

matches_table = Table(
    "matches",
    metadata,
    Column("id", Text, primary_key=True),
    Column("match_id", Text),
    Column("slug", Text),
    Column("home_team", Text),
    Column("away_team", Text),
    Column("competition", Text),
    Column("kickoff", Text),
    Column("status", Text),
    Column("source", Text),
    Column("score_full_time_home", Integer, nullable=True),
    Column("score_full_time_away", Integer, nullable=True),
    Column("score_half_time_home", Integer, nullable=True),
    Column("score_half_time_away", Integer, nullable=True),
    Column("winner", Text, nullable=True),
    Column("raw_json", Text, nullable=True),
    Column("updated_at", TIMESTAMP(timezone=True)),
)

predictions_table = Table(
    "predictions",
    metadata,
    Column("id", Text, primary_key=True),
    Column("match_id", Text),
    Column("slug", Text),
    Column("payload_json", Text),
    Column("model_version", Text),
    Column("created_at", TIMESTAMP(timezone=True)),
)


prediction_snapshots_table = Table(
    "prediction_snapshots",
    metadata,
    Column("id", Text, primary_key=True),
    Column("match_id", Text),
    Column("model_version", Text),
    Column("prediction_json", Text),
    Column("created_at", TIMESTAMP(timezone=True)),
    Column("evaluated_at", TIMESTAMP(timezone=True), nullable=True),
    Column("actual_result", Text, nullable=True),
    Column("result_correct", Boolean, nullable=True),
    Column("brier_score_1x2", Float, nullable=True),
)


feature_snapshots_table = Table(
    "feature_snapshots",
    metadata,
    Column("id", Text, primary_key=True),
    Column("match_id", Text),
    Column("model_version", Text),
    Column("features_json", Text),
    Column("target_json", Text, nullable=True),
    Column("created_at", TIMESTAMP(timezone=True)),
)

refresh_logs_table = Table(
    "refresh_logs",
    metadata,
    Column("id", Text, primary_key=True),
    Column("source", Text),
    Column("storage", Text),
    Column("matches_imported", Integer),
    Column("teams_imported", Integer),
    Column("created_at", TIMESTAMP(timezone=True)),
)


def get_database_url() -> str | None:
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        return None

    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql://", 1)

    return database_url


def get_engine() -> Engine | None:
    global _engine

    database_url = get_database_url()
    if not database_url:
        return None

    if _engine is None:
        try:
            _engine = create_engine(database_url, pool_pre_ping=True, future=True)
        except Exception as exc:
            logger.warning("PostgreSQL engine unavailable: %s", exc)
            return None

    return _engine


def db_available() -> bool:
    engine = get_engine()

    if engine is None:
        return False

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.warning("PostgreSQL unavailable: %s", exc)
        return False




def _ensure_match_score_columns(engine: Engine) -> None:
    if engine.dialect.name != "postgresql":
        return

    statements = [
        "ALTER TABLE matches ADD COLUMN IF NOT EXISTS score_full_time_home INTEGER",
        "ALTER TABLE matches ADD COLUMN IF NOT EXISTS score_full_time_away INTEGER",
        "ALTER TABLE matches ADD COLUMN IF NOT EXISTS score_half_time_home INTEGER",
        "ALTER TABLE matches ADD COLUMN IF NOT EXISTS score_half_time_away INTEGER",
        "ALTER TABLE matches ADD COLUMN IF NOT EXISTS winner TEXT",
        "ALTER TABLE matches ADD COLUMN IF NOT EXISTS raw_json TEXT",
    ]

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))


def init_db() -> bool:
    engine = get_engine()

    if engine is None:
        logger.warning("DATABASE_URL missing; using memory storage fallback.")
        return False

    try:
        metadata.create_all(engine)
        _ensure_match_score_columns(engine)
        return True
    except Exception as exc:
        logger.warning("PostgreSQL schema init failed: %s", exc)
        return False


def execute_safe(statement, params=None) -> bool:
    engine = get_engine()

    if engine is None:
        return False

    try:
        with engine.begin() as connection:
            connection.execute(statement, params or {})
        return True
    except Exception as exc:
        logger.warning("PostgreSQL execute failed: %s", exc)
        return False


def fetch_all_safe(statement, params=None) -> list[dict]:
    engine = get_engine()

    if engine is None:
        return []

    try:
        with engine.connect() as connection:
            rows = connection.execute(statement, params or {}).fetchall()
        return [dict(row._mapping) for row in rows]
    except Exception as exc:
        logger.warning("PostgreSQL fetch all failed: %s", exc)
        return []


def fetch_one_safe(statement, params=None) -> dict | None:
    engine = get_engine()

    if engine is None:
        return None

    try:
        with engine.connect() as connection:
            row = connection.execute(statement, params or {}).fetchone()
        return dict(row._mapping) if row else None
    except Exception as exc:
        logger.warning("PostgreSQL fetch one failed: %s", exc)
        return None


def utcnow() -> datetime:
    return datetime.utcnow()



