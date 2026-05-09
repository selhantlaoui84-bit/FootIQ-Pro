import logging
import os
from datetime import datetime

from sqlalchemy import Boolean, Column, Float, Index, Integer, MetaData, Table, Text, TIMESTAMP, create_engine, text
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
    Column("payload_json", Text, nullable=True),
    Column("created_at", TIMESTAMP(timezone=True)),
)
Index("ux_feature_snapshots_match_model", feature_snapshots_table.c.match_id, feature_snapshots_table.c.model_version, unique=True)

ml_shadow_predictions_table = Table(
    "ml_shadow_predictions",
    metadata,
    Column("id", Text, primary_key=True),
    Column("match_id", Text),
    Column("production_model_version", Text),
    Column("candidate_model_version", Text),
    Column("production_prediction_json", Text),
    Column("shadow_prediction_json", Text),
    Column("comparison_json", Text),
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
    Column("predictions_generated", Integer),
    Column("predictions_saved", Integer),
    Column("predictions_failed", Integer),
    Column("prediction_save_errors_json", Text, nullable=True),
    Column("created_at", TIMESTAMP(timezone=True)),
)

model_versions_table = Table(
    "model_versions",
    metadata,
    Column("id", Text, primary_key=True),
    Column("model_version", Text, nullable=False),
    Column("model_type", Text, nullable=True),
    Column("status", Text, nullable=False),
    Column("feature_set_version", Text, nullable=True),
    Column("calibration_version", Text, nullable=True),
    Column("trained_at", TIMESTAMP(timezone=True), nullable=True),
    Column("promoted_at", TIMESTAMP(timezone=True), nullable=True),
    Column("created_at", TIMESTAMP(timezone=True)),
    Column("updated_at", TIMESTAMP(timezone=True)),
    Column("rows_used", Integer, default=0),
    Column("features_used", Integer, default=0),
    Column("accuracy", Float, nullable=True),
    Column("log_loss", Float, nullable=True),
    Column("brier_score", Float, nullable=True),
    Column("roi_theoretical", Float, nullable=True),
    Column("target_distribution_json", Text, nullable=True),
    Column("metrics_json", Text, nullable=True),
    Column("governance_json", Text, nullable=True),
    Column("notes", Text, nullable=True),
    Column("source", Text, default="postgresql"),
)
Index("ux_model_versions_model_version", model_versions_table.c.model_version, unique=True)
Index("ix_model_versions_status", model_versions_table.c.status)
Index("ix_model_versions_created_at", model_versions_table.c.created_at)
Index("ix_model_versions_model_type", model_versions_table.c.model_type)
Index("ix_model_versions_trained_at", model_versions_table.c.trained_at)


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




def _ensure_runtime_columns_and_indexes(engine: Engine) -> None:
    if engine.dialect.name == "postgresql":
        statements = [
            "ALTER TABLE matches ADD COLUMN IF NOT EXISTS score_full_time_home INTEGER",
            "ALTER TABLE matches ADD COLUMN IF NOT EXISTS score_full_time_away INTEGER",
            "ALTER TABLE matches ADD COLUMN IF NOT EXISTS score_half_time_home INTEGER",
            "ALTER TABLE matches ADD COLUMN IF NOT EXISTS score_half_time_away INTEGER",
            "ALTER TABLE matches ADD COLUMN IF NOT EXISTS winner TEXT",
            "ALTER TABLE matches ADD COLUMN IF NOT EXISTS raw_json TEXT",
            "ALTER TABLE refresh_logs ADD COLUMN IF NOT EXISTS predictions_generated INTEGER DEFAULT 0",
            "ALTER TABLE refresh_logs ADD COLUMN IF NOT EXISTS predictions_saved INTEGER DEFAULT 0",
            "ALTER TABLE refresh_logs ADD COLUMN IF NOT EXISTS predictions_failed INTEGER DEFAULT 0",
            "ALTER TABLE refresh_logs ADD COLUMN IF NOT EXISTS prediction_save_errors_json TEXT",
            "ALTER TABLE feature_snapshots ADD COLUMN IF NOT EXISTS payload_json TEXT",
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_feature_snapshots_match_model ON feature_snapshots(match_id, model_version)",
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_model_versions_model_version ON model_versions(model_version)",
            "CREATE INDEX IF NOT EXISTS ix_model_versions_status ON model_versions(status)",
            "CREATE INDEX IF NOT EXISTS ix_model_versions_created_at ON model_versions(created_at)",
            "CREATE INDEX IF NOT EXISTS ix_model_versions_model_type ON model_versions(model_type)",
            "CREATE INDEX IF NOT EXISTS ix_model_versions_trained_at ON model_versions(trained_at)",
        ]
    elif engine.dialect.name == "sqlite":
        statements = [
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_feature_snapshots_match_model ON feature_snapshots(match_id, model_version)",
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_model_versions_model_version ON model_versions(model_version)",
            "CREATE INDEX IF NOT EXISTS ix_model_versions_status ON model_versions(status)",
            "CREATE INDEX IF NOT EXISTS ix_model_versions_created_at ON model_versions(created_at)",
            "CREATE INDEX IF NOT EXISTS ix_model_versions_model_type ON model_versions(model_type)",
            "CREATE INDEX IF NOT EXISTS ix_model_versions_trained_at ON model_versions(trained_at)",
        ]
        with engine.connect() as connection:
            columns = {row._mapping["name"] for row in connection.execute(text("PRAGMA table_info(feature_snapshots)"))}
        if "payload_json" not in columns:
            statements.insert(0, "ALTER TABLE feature_snapshots ADD COLUMN payload_json TEXT")
    else:
        statements = []

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
        _ensure_runtime_columns_and_indexes(engine)
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
