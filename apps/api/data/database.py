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

pipeline_jobs_table = Table(
    "pipeline_jobs",
    metadata,
    Column("id", Text, primary_key=True),
    Column("job_type", Text, nullable=False),
    Column("status", Text, nullable=False),
    Column("started_at", TIMESTAMP(timezone=True), nullable=True),
    Column("finished_at", TIMESTAMP(timezone=True), nullable=True),
    Column("duration_ms", Integer, nullable=True),
    Column("result_json", Text, nullable=True),
    Column("error", Text, nullable=True),
    Column("triggered_by", Text, nullable=True),
    Column("created_at", TIMESTAMP(timezone=True)),
    Column("updated_at", TIMESTAMP(timezone=True)),
)
Index("ix_pipeline_jobs_job_type", pipeline_jobs_table.c.job_type)
Index("ix_pipeline_jobs_status", pipeline_jobs_table.c.status)
Index("ix_pipeline_jobs_started_at", pipeline_jobs_table.c.started_at)
Index("ix_pipeline_jobs_created_at", pipeline_jobs_table.c.created_at)

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

model_promotion_audit_table = Table(
    "model_promotion_audit",
    metadata,
    Column("id", Text, primary_key=True),
    Column("action", Text, nullable=False),
    Column("candidate_model_version", Text, nullable=True),
    Column("previous_production_model_version", Text, nullable=True),
    Column("new_production_model_version", Text, nullable=True),
    Column("requested_by", Text, nullable=True),
    Column("governance_json", Text, nullable=True),
    Column("result", Text, nullable=True),
    Column("detail", Text, nullable=True),
    Column("created_at", TIMESTAMP(timezone=True)),
)
Index("ix_model_promotion_audit_created_at", model_promotion_audit_table.c.created_at)
Index("ix_model_promotion_audit_action", model_promotion_audit_table.c.action)

model_calibrations_table = Table(
    "model_calibrations",
    metadata,
    Column("id", Text, primary_key=True),
    Column("calibration_version", Text, nullable=False),
    Column("model_version", Text, nullable=True),
    Column("model_type", Text, nullable=True),
    Column("source", Text, nullable=False),
    Column("method", Text, nullable=False),
    Column("status", Text, nullable=False),
    Column("samples_count", Integer, default=0),
    Column("buckets_json", Text, nullable=True),
    Column("factors_json", Text, nullable=True),
    Column("metrics_json", Text, nullable=True),
    Column("recommendation_json", Text, nullable=True),
    Column("created_at", TIMESTAMP(timezone=True)),
    Column("activated_at", TIMESTAMP(timezone=True), nullable=True),
)
Index("ux_model_calibrations_version", model_calibrations_table.c.calibration_version, unique=True)
Index("ix_model_calibrations_model_version", model_calibrations_table.c.model_version)
Index("ix_model_calibrations_status", model_calibrations_table.c.status)
Index("ix_model_calibrations_created_at", model_calibrations_table.c.created_at)

bookmaker_odds_table = Table(
    "bookmaker_odds",
    metadata,
    Column("id", Text, primary_key=True),
    Column("match_id", Text, nullable=False),
    Column("bookmaker", Text, nullable=False),
    Column("market", Text, nullable=False),
    Column("selection", Text, nullable=False),
    Column("odds_decimal", Float, nullable=False),
    Column("implied_probability", Float, nullable=True),
    Column("margin", Float, nullable=True),
    Column("provider", Text, nullable=True),
    Column("provider_event_id", Text, nullable=True),
    Column("provider_market_id", Text, nullable=True),
    Column("raw_json", Text, nullable=True),
    Column("collected_at", TIMESTAMP(timezone=True)),
    Column("expires_at", TIMESTAMP(timezone=True), nullable=True),
    Column("stale", Boolean, default=False),
    Column("source", Text, nullable=True),
    Column("created_at", TIMESTAMP(timezone=True)),
)
Index("ix_bookmaker_odds_match_id", bookmaker_odds_table.c.match_id)
Index("ix_bookmaker_odds_market", bookmaker_odds_table.c.market)
Index("ix_bookmaker_odds_selection", bookmaker_odds_table.c.selection)
Index("ix_bookmaker_odds_bookmaker", bookmaker_odds_table.c.bookmaker)
Index("ix_bookmaker_odds_provider", bookmaker_odds_table.c.provider)
Index("ix_bookmaker_odds_collected_at", bookmaker_odds_table.c.collected_at)

user_bets_table = Table(
    "user_bets",
    metadata,
    Column("id", Text, primary_key=True),
    Column("user_id", Text, nullable=False),
    Column("match_id", Text, nullable=False),
    Column("market", Text, nullable=False),
    Column("selection", Text, nullable=False),
    Column("bookmaker", Text, nullable=True),
    Column("odds_decimal", Float, nullable=False),
    Column("odds_source", Text, nullable=False),
    Column("odds_collected_at", TIMESTAMP(timezone=True), nullable=True),
    Column("stake", Float, nullable=False),
    Column("implied_probability", Float, nullable=True),
    Column("model_probability", Float, nullable=True),
    Column("calibrated_probability", Float, nullable=True),
    Column("expected_value", Float, nullable=True),
    Column("edge", Float, nullable=True),
    Column("risk_level", Text, nullable=True),
    Column("recommendation_type", Text, nullable=True),
    Column("status", Text, nullable=False),
    Column("result_profit", Float, default=0),
    Column("placed_at", TIMESTAMP(timezone=True)),
    Column("settled_at", TIMESTAMP(timezone=True), nullable=True),
    Column("notes", Text, nullable=True),
    Column("raw_context_json", Text, nullable=True),
    Column("created_at", TIMESTAMP(timezone=True)),
    Column("updated_at", TIMESTAMP(timezone=True)),
)
Index("ix_user_bets_user_id", user_bets_table.c.user_id)
Index("ix_user_bets_match_id", user_bets_table.c.match_id)
Index("ix_user_bets_status", user_bets_table.c.status)
Index("ix_user_bets_placed_at", user_bets_table.c.placed_at)
Index("ix_user_bets_market", user_bets_table.c.market)
Index("ix_user_bets_selection", user_bets_table.c.selection)

user_subscriptions_table = Table(
    "user_subscriptions",
    metadata,
    Column("id", Text, primary_key=True),
    Column("user_id", Text, nullable=False),
    Column("plan", Text, nullable=False),
    Column("status", Text, nullable=False),
    Column("stripe_customer_id", Text, nullable=True),
    Column("stripe_subscription_id", Text, nullable=True),
    Column("stripe_price_id", Text, nullable=True),
    Column("current_period_start", TIMESTAMP(timezone=True), nullable=True),
    Column("current_period_end", TIMESTAMP(timezone=True), nullable=True),
    Column("cancel_at_period_end", Boolean, default=False),
    Column("created_at", TIMESTAMP(timezone=True)),
    Column("updated_at", TIMESTAMP(timezone=True)),
)
Index("ix_user_subscriptions_user_id", user_subscriptions_table.c.user_id)
Index("ix_user_subscriptions_stripe_customer_id", user_subscriptions_table.c.stripe_customer_id)
Index("ix_user_subscriptions_stripe_subscription_id", user_subscriptions_table.c.stripe_subscription_id)
Index("ix_user_subscriptions_plan", user_subscriptions_table.c.plan)
Index("ix_user_subscriptions_status", user_subscriptions_table.c.status)

user_usage_events_table = Table(
    "user_usage_events",
    metadata,
    Column("id", Text, primary_key=True),
    Column("user_id", Text, nullable=False),
    Column("event_type", Text, nullable=False),
    Column("feature", Text, nullable=False),
    Column("count", Integer, default=1),
    Column("metadata_json", Text, nullable=True),
    Column("created_at", TIMESTAMP(timezone=True)),
)
Index("ix_user_usage_events_user_id", user_usage_events_table.c.user_id)
Index("ix_user_usage_events_event_type", user_usage_events_table.c.event_type)
Index("ix_user_usage_events_feature", user_usage_events_table.c.feature)
Index("ix_user_usage_events_created_at", user_usage_events_table.c.created_at)

users_table = Table(
    "users",
    metadata,
    Column("id", Text, primary_key=True),
    Column("email", Text, nullable=False),
    Column("display_name", Text, nullable=True),
    Column("role", Text, nullable=False, default="user"),
    Column("status", Text, nullable=False, default="active"),
    Column("plan_id", Text, nullable=True),
    Column("stripe_customer_id", Text, nullable=True),
    Column("created_at", TIMESTAMP(timezone=True)),
    Column("updated_at", TIMESTAMP(timezone=True)),
    Column("last_login_at", TIMESTAMP(timezone=True), nullable=True),
    Column("metadata_json", Text, nullable=True),
)
Index("ux_users_email", users_table.c.email, unique=True)
Index("ix_users_role", users_table.c.role)
Index("ix_users_status", users_table.c.status)
Index("ix_users_stripe_customer_id", users_table.c.stripe_customer_id)

saas_plans_table = Table(
    "saas_plans",
    metadata,
    Column("id", Text, primary_key=True),
    Column("code", Text, nullable=False),
    Column("name", Text, nullable=False),
    Column("description", Text, nullable=True),
    Column("price_monthly_cents", Integer, default=0),
    Column("price_yearly_cents", Integer, default=0),
    Column("currency", Text, nullable=False, default="EUR"),
    Column("is_active", Boolean, default=True),
    Column("features_json", Text, nullable=True),
    Column("limits_json", Text, nullable=True),
    Column("created_at", TIMESTAMP(timezone=True)),
    Column("updated_at", TIMESTAMP(timezone=True)),
)
Index("ux_saas_plans_code", saas_plans_table.c.code, unique=True)
Index("ix_saas_plans_is_active", saas_plans_table.c.is_active)

subscriptions_table = Table(
    "subscriptions",
    metadata,
    Column("id", Text, primary_key=True),
    Column("user_id", Text, nullable=False),
    Column("plan_id", Text, nullable=False),
    Column("status", Text, nullable=False),
    Column("provider", Text, nullable=False, default="internal"),
    Column("provider_customer_id", Text, nullable=True),
    Column("provider_subscription_id", Text, nullable=True),
    Column("current_period_start", TIMESTAMP(timezone=True), nullable=True),
    Column("current_period_end", TIMESTAMP(timezone=True), nullable=True),
    Column("cancel_at_period_end", Boolean, default=False),
    Column("created_at", TIMESTAMP(timezone=True)),
    Column("updated_at", TIMESTAMP(timezone=True)),
)
Index("ix_subscriptions_user_id", subscriptions_table.c.user_id)
Index("ix_subscriptions_status", subscriptions_table.c.status)

payments_table = Table(
    "payments",
    metadata,
    Column("id", Text, primary_key=True),
    Column("user_id", Text, nullable=False),
    Column("subscription_id", Text, nullable=True),
    Column("provider", Text, nullable=False, default="internal"),
    Column("provider_payment_id", Text, nullable=True),
    Column("amount_cents", Integer, nullable=False, default=0),
    Column("currency", Text, nullable=False, default="EUR"),
    Column("status", Text, nullable=False),
    Column("paid_at", TIMESTAMP(timezone=True), nullable=True),
    Column("created_at", TIMESTAMP(timezone=True)),
    Column("metadata_json", Text, nullable=True),
)
Index("ix_payments_user_id", payments_table.c.user_id)
Index("ix_payments_status", payments_table.c.status)

access_entitlements_table = Table(
    "access_entitlements",
    metadata,
    Column("id", Text, primary_key=True),
    Column("user_id", Text, nullable=False),
    Column("feature_key", Text, nullable=False),
    Column("enabled", Boolean, default=True),
    Column("source", Text, nullable=False, default="plan"),
    Column("expires_at", TIMESTAMP(timezone=True), nullable=True),
    Column("created_at", TIMESTAMP(timezone=True)),
    Column("updated_at", TIMESTAMP(timezone=True)),
)
Index("ix_access_entitlements_user_id", access_entitlements_table.c.user_id)
Index("ix_access_entitlements_feature_key", access_entitlements_table.c.feature_key)

super_admin_audit_log_table = Table(
    "super_admin_audit_log",
    metadata,
    Column("id", Text, primary_key=True),
    Column("actor_user_id", Text, nullable=True),
    Column("actor_email", Text, nullable=False),
    Column("action", Text, nullable=False),
    Column("target_type", Text, nullable=False),
    Column("target_id", Text, nullable=True),
    Column("target_email", Text, nullable=True),
    Column("before_json", Text, nullable=True),
    Column("after_json", Text, nullable=True),
    Column("created_at", TIMESTAMP(timezone=True)),
)
Index("ix_super_admin_audit_actor_email", super_admin_audit_log_table.c.actor_email)
Index("ix_super_admin_audit_created_at", super_admin_audit_log_table.c.created_at)

stripe_webhook_events_table = Table(
    "stripe_webhook_events",
    metadata,
    Column("id", Text, primary_key=True),
    Column("stripe_event_id", Text, nullable=False),
    Column("type", Text, nullable=True),
    Column("processed_at", TIMESTAMP(timezone=True), nullable=True),
    Column("status", Text, nullable=False, default="processing"),
    Column("error", Text, nullable=True),
    Column("payload_json", Text, nullable=True),
)
Index("ux_stripe_webhook_events_event_id", stripe_webhook_events_table.c.stripe_event_id, unique=True)
Index("ix_stripe_webhook_events_type", stripe_webhook_events_table.c.type)
Index("ix_stripe_webhook_events_processed_at", stripe_webhook_events_table.c.processed_at)


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
            "CREATE INDEX IF NOT EXISTS ix_model_promotion_audit_created_at ON model_promotion_audit(created_at)",
            "CREATE INDEX IF NOT EXISTS ix_model_promotion_audit_action ON model_promotion_audit(action)",
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_model_calibrations_version ON model_calibrations(calibration_version)",
            "CREATE INDEX IF NOT EXISTS ix_model_calibrations_model_version ON model_calibrations(model_version)",
            "CREATE INDEX IF NOT EXISTS ix_model_calibrations_status ON model_calibrations(status)",
            "CREATE INDEX IF NOT EXISTS ix_model_calibrations_created_at ON model_calibrations(created_at)",
            "ALTER TABLE bookmaker_odds ADD COLUMN IF NOT EXISTS provider TEXT",
            "ALTER TABLE bookmaker_odds ADD COLUMN IF NOT EXISTS provider_event_id TEXT",
            "ALTER TABLE bookmaker_odds ADD COLUMN IF NOT EXISTS provider_market_id TEXT",
            "ALTER TABLE bookmaker_odds ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ",
            "ALTER TABLE bookmaker_odds ADD COLUMN IF NOT EXISTS stale BOOLEAN DEFAULT false",
            "ALTER TABLE bookmaker_odds ADD COLUMN IF NOT EXISTS source TEXT",
            "ALTER TABLE user_bets ADD COLUMN IF NOT EXISTS odds_source TEXT DEFAULT 'manual_user_input'",
            "ALTER TABLE user_bets ADD COLUMN IF NOT EXISTS odds_collected_at TIMESTAMPTZ",
            "CREATE INDEX IF NOT EXISTS ix_bookmaker_odds_match_id ON bookmaker_odds(match_id)",
            "CREATE INDEX IF NOT EXISTS ix_bookmaker_odds_market ON bookmaker_odds(market)",
            "CREATE INDEX IF NOT EXISTS ix_bookmaker_odds_selection ON bookmaker_odds(selection)",
            "CREATE INDEX IF NOT EXISTS ix_bookmaker_odds_bookmaker ON bookmaker_odds(bookmaker)",
            "CREATE INDEX IF NOT EXISTS ix_bookmaker_odds_provider ON bookmaker_odds(provider)",
            "CREATE INDEX IF NOT EXISTS ix_bookmaker_odds_collected_at ON bookmaker_odds(collected_at)",
            "CREATE INDEX IF NOT EXISTS ix_user_bets_user_id ON user_bets(user_id)",
            "CREATE INDEX IF NOT EXISTS ix_user_bets_match_id ON user_bets(match_id)",
            "CREATE INDEX IF NOT EXISTS ix_user_bets_status ON user_bets(status)",
            "CREATE INDEX IF NOT EXISTS ix_user_bets_placed_at ON user_bets(placed_at)",
            "CREATE INDEX IF NOT EXISTS ix_user_bets_market ON user_bets(market)",
            "CREATE INDEX IF NOT EXISTS ix_user_bets_selection ON user_bets(selection)",
            "CREATE INDEX IF NOT EXISTS ix_pipeline_jobs_job_type ON pipeline_jobs(job_type)",
            "CREATE INDEX IF NOT EXISTS ix_pipeline_jobs_status ON pipeline_jobs(status)",
            "CREATE INDEX IF NOT EXISTS ix_pipeline_jobs_started_at ON pipeline_jobs(started_at)",
            "CREATE INDEX IF NOT EXISTS ix_pipeline_jobs_created_at ON pipeline_jobs(created_at)",
            "CREATE INDEX IF NOT EXISTS ix_user_subscriptions_user_id ON user_subscriptions(user_id)",
            "CREATE INDEX IF NOT EXISTS ix_user_subscriptions_stripe_customer_id ON user_subscriptions(stripe_customer_id)",
            "CREATE INDEX IF NOT EXISTS ix_user_subscriptions_stripe_subscription_id ON user_subscriptions(stripe_subscription_id)",
            "CREATE INDEX IF NOT EXISTS ix_user_subscriptions_plan ON user_subscriptions(plan)",
            "CREATE INDEX IF NOT EXISTS ix_user_subscriptions_status ON user_subscriptions(status)",
            "CREATE INDEX IF NOT EXISTS ix_user_usage_events_user_id ON user_usage_events(user_id)",
            "CREATE INDEX IF NOT EXISTS ix_user_usage_events_event_type ON user_usage_events(event_type)",
            "CREATE INDEX IF NOT EXISTS ix_user_usage_events_feature ON user_usage_events(feature)",
            "CREATE INDEX IF NOT EXISTS ix_user_usage_events_created_at ON user_usage_events(created_at)",
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_users_email ON users(email)",
            "CREATE INDEX IF NOT EXISTS ix_users_role ON users(role)",
            "CREATE INDEX IF NOT EXISTS ix_users_status ON users(status)",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS stripe_customer_id TEXT",
            "CREATE INDEX IF NOT EXISTS ix_users_stripe_customer_id ON users(stripe_customer_id)",
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_saas_plans_code ON saas_plans(code)",
            "CREATE INDEX IF NOT EXISTS ix_saas_plans_is_active ON saas_plans(is_active)",
            "CREATE INDEX IF NOT EXISTS ix_subscriptions_user_id ON subscriptions(user_id)",
            "CREATE INDEX IF NOT EXISTS ix_subscriptions_status ON subscriptions(status)",
            "CREATE INDEX IF NOT EXISTS ix_payments_user_id ON payments(user_id)",
            "CREATE INDEX IF NOT EXISTS ix_payments_status ON payments(status)",
            "CREATE INDEX IF NOT EXISTS ix_access_entitlements_user_id ON access_entitlements(user_id)",
            "CREATE INDEX IF NOT EXISTS ix_access_entitlements_feature_key ON access_entitlements(feature_key)",
            "CREATE INDEX IF NOT EXISTS ix_super_admin_audit_actor_email ON super_admin_audit_log(actor_email)",
            "CREATE INDEX IF NOT EXISTS ix_super_admin_audit_created_at ON super_admin_audit_log(created_at)",
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_stripe_webhook_events_event_id ON stripe_webhook_events(stripe_event_id)",
            "CREATE INDEX IF NOT EXISTS ix_stripe_webhook_events_type ON stripe_webhook_events(type)",
            "CREATE INDEX IF NOT EXISTS ix_stripe_webhook_events_processed_at ON stripe_webhook_events(processed_at)",
        ]
    elif engine.dialect.name == "sqlite":
        statements = [
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_feature_snapshots_match_model ON feature_snapshots(match_id, model_version)",
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_model_versions_model_version ON model_versions(model_version)",
            "CREATE INDEX IF NOT EXISTS ix_model_versions_status ON model_versions(status)",
            "CREATE INDEX IF NOT EXISTS ix_model_versions_created_at ON model_versions(created_at)",
            "CREATE INDEX IF NOT EXISTS ix_model_versions_model_type ON model_versions(model_type)",
            "CREATE INDEX IF NOT EXISTS ix_model_versions_trained_at ON model_versions(trained_at)",
            "CREATE INDEX IF NOT EXISTS ix_model_promotion_audit_created_at ON model_promotion_audit(created_at)",
            "CREATE INDEX IF NOT EXISTS ix_model_promotion_audit_action ON model_promotion_audit(action)",
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_model_calibrations_version ON model_calibrations(calibration_version)",
            "CREATE INDEX IF NOT EXISTS ix_model_calibrations_model_version ON model_calibrations(model_version)",
            "CREATE INDEX IF NOT EXISTS ix_model_calibrations_status ON model_calibrations(status)",
            "CREATE INDEX IF NOT EXISTS ix_model_calibrations_created_at ON model_calibrations(created_at)",
            "CREATE INDEX IF NOT EXISTS ix_bookmaker_odds_match_id ON bookmaker_odds(match_id)",
            "CREATE INDEX IF NOT EXISTS ix_bookmaker_odds_market ON bookmaker_odds(market)",
            "CREATE INDEX IF NOT EXISTS ix_bookmaker_odds_selection ON bookmaker_odds(selection)",
            "CREATE INDEX IF NOT EXISTS ix_bookmaker_odds_bookmaker ON bookmaker_odds(bookmaker)",
            "CREATE INDEX IF NOT EXISTS ix_bookmaker_odds_provider ON bookmaker_odds(provider)",
            "CREATE INDEX IF NOT EXISTS ix_bookmaker_odds_collected_at ON bookmaker_odds(collected_at)",
            "CREATE INDEX IF NOT EXISTS ix_user_bets_user_id ON user_bets(user_id)",
            "CREATE INDEX IF NOT EXISTS ix_user_bets_match_id ON user_bets(match_id)",
            "CREATE INDEX IF NOT EXISTS ix_user_bets_status ON user_bets(status)",
            "CREATE INDEX IF NOT EXISTS ix_user_bets_placed_at ON user_bets(placed_at)",
            "CREATE INDEX IF NOT EXISTS ix_user_bets_market ON user_bets(market)",
            "CREATE INDEX IF NOT EXISTS ix_user_bets_selection ON user_bets(selection)",
            "CREATE INDEX IF NOT EXISTS ix_pipeline_jobs_job_type ON pipeline_jobs(job_type)",
            "CREATE INDEX IF NOT EXISTS ix_pipeline_jobs_status ON pipeline_jobs(status)",
            "CREATE INDEX IF NOT EXISTS ix_pipeline_jobs_started_at ON pipeline_jobs(started_at)",
            "CREATE INDEX IF NOT EXISTS ix_pipeline_jobs_created_at ON pipeline_jobs(created_at)",
            "CREATE INDEX IF NOT EXISTS ix_user_subscriptions_user_id ON user_subscriptions(user_id)",
            "CREATE INDEX IF NOT EXISTS ix_user_subscriptions_stripe_customer_id ON user_subscriptions(stripe_customer_id)",
            "CREATE INDEX IF NOT EXISTS ix_user_subscriptions_stripe_subscription_id ON user_subscriptions(stripe_subscription_id)",
            "CREATE INDEX IF NOT EXISTS ix_user_subscriptions_plan ON user_subscriptions(plan)",
            "CREATE INDEX IF NOT EXISTS ix_user_subscriptions_status ON user_subscriptions(status)",
            "CREATE INDEX IF NOT EXISTS ix_user_usage_events_user_id ON user_usage_events(user_id)",
            "CREATE INDEX IF NOT EXISTS ix_user_usage_events_event_type ON user_usage_events(event_type)",
            "CREATE INDEX IF NOT EXISTS ix_user_usage_events_feature ON user_usage_events(feature)",
            "CREATE INDEX IF NOT EXISTS ix_user_usage_events_created_at ON user_usage_events(created_at)",
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_users_email ON users(email)",
            "CREATE INDEX IF NOT EXISTS ix_users_role ON users(role)",
            "CREATE INDEX IF NOT EXISTS ix_users_status ON users(status)",
            "CREATE INDEX IF NOT EXISTS ix_users_stripe_customer_id ON users(stripe_customer_id)",
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_saas_plans_code ON saas_plans(code)",
            "CREATE INDEX IF NOT EXISTS ix_saas_plans_is_active ON saas_plans(is_active)",
            "CREATE INDEX IF NOT EXISTS ix_subscriptions_user_id ON subscriptions(user_id)",
            "CREATE INDEX IF NOT EXISTS ix_subscriptions_status ON subscriptions(status)",
            "CREATE INDEX IF NOT EXISTS ix_payments_user_id ON payments(user_id)",
            "CREATE INDEX IF NOT EXISTS ix_payments_status ON payments(status)",
            "CREATE INDEX IF NOT EXISTS ix_access_entitlements_user_id ON access_entitlements(user_id)",
            "CREATE INDEX IF NOT EXISTS ix_access_entitlements_feature_key ON access_entitlements(feature_key)",
            "CREATE INDEX IF NOT EXISTS ix_super_admin_audit_actor_email ON super_admin_audit_log(actor_email)",
            "CREATE INDEX IF NOT EXISTS ix_super_admin_audit_created_at ON super_admin_audit_log(created_at)",
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_stripe_webhook_events_event_id ON stripe_webhook_events(stripe_event_id)",
            "CREATE INDEX IF NOT EXISTS ix_stripe_webhook_events_type ON stripe_webhook_events(type)",
            "CREATE INDEX IF NOT EXISTS ix_stripe_webhook_events_processed_at ON stripe_webhook_events(processed_at)",
        ]
        with engine.connect() as connection:
            columns = {row._mapping["name"] for row in connection.execute(text("PRAGMA table_info(feature_snapshots)"))}
        if "payload_json" not in columns:
            statements.insert(0, "ALTER TABLE feature_snapshots ADD COLUMN payload_json TEXT")
        with engine.connect() as connection:
            odds_columns = {row._mapping["name"] for row in connection.execute(text("PRAGMA table_info(bookmaker_odds)"))}
        sqlite_odds_columns = {
            "provider": "ALTER TABLE bookmaker_odds ADD COLUMN provider TEXT",
            "provider_event_id": "ALTER TABLE bookmaker_odds ADD COLUMN provider_event_id TEXT",
            "provider_market_id": "ALTER TABLE bookmaker_odds ADD COLUMN provider_market_id TEXT",
            "expires_at": "ALTER TABLE bookmaker_odds ADD COLUMN expires_at TIMESTAMP",
            "stale": "ALTER TABLE bookmaker_odds ADD COLUMN stale BOOLEAN DEFAULT false",
            "source": "ALTER TABLE bookmaker_odds ADD COLUMN source TEXT",
        }
        for column_name, alter_statement in sqlite_odds_columns.items():
            if column_name not in odds_columns:
                statements.insert(0, alter_statement)
        with engine.connect() as connection:
            user_bet_columns = {row._mapping["name"] for row in connection.execute(text("PRAGMA table_info(user_bets)"))}
        sqlite_user_bet_columns = {
            "odds_source": "ALTER TABLE user_bets ADD COLUMN odds_source TEXT DEFAULT 'manual_user_input'",
            "odds_collected_at": "ALTER TABLE user_bets ADD COLUMN odds_collected_at TIMESTAMP",
        }
        for column_name, alter_statement in sqlite_user_bet_columns.items():
            if column_name not in user_bet_columns:
                statements.insert(0, alter_statement)
        with engine.connect() as connection:
            user_columns = {row._mapping["name"] for row in connection.execute(text("PRAGMA table_info(users)"))}
        if "stripe_customer_id" not in user_columns:
            statements.insert(0, "ALTER TABLE users ADD COLUMN stripe_customer_id TEXT")
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
