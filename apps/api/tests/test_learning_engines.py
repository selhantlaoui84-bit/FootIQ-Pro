import unittest
import asyncio
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import create_engine, text

import main
from data import database, repository
from services.calibration_engine import (
    apply_bucket_calibration_binary,
    apply_bucket_calibration_multiclass,
    build_confidence_buckets,
    build_calibration_profile,
    build_global_calibration_metrics,
    calibrate_prediction,
    create_calibration_candidate,
    generate_calibration_version,
)
from services.feedback_engine import build_feedback_report
from services.ml_training import (
    extract_numeric_features,
    extract_target_class,
    load_training_rows_from_feature_snapshots,
    prepare_training_rows,
    train_candidate_model,
)
from services.model_governance import build_model_governance_report, evaluate_model_promotion
from services.model_versioning import get_versions_report, record_model_version, list_model_versions
from services.odds_engine import (
    calculate_expected_value,
    calculate_risk_adjusted_value,
    classify_value_bet,
    classify_value_opportunity,
    fair_odds_from_probability,
    implied_probability_from_odds,
    minimum_value_odds,
    select_reference_odds,
)
from services.odds_provider import fetch_real_odds_for_matches, is_odds_configured
from services.betting_assistant import analyze_prediction
from services.billing_service import create_checkout_session, map_price_to_plan, sync_subscription_from_stripe
from services.user_learning_engine import detect_risky_patterns, detect_user_strengths
from services.value_bet_engine import evaluate_value_bet
from services.pipeline_orchestrator import run_hourly_data_pipeline, run_pipeline_step
from services.shadow_backtesting import calculate_shadow_backtest_report


def finished_match(match_id, result="home", competition="Ligue 1"):
    scores = {
        "home": (2, 1),
        "draw": (1, 1),
        "away": (0, 2),
    }[result]
    return {
        "id": match_id,
        "match_id": match_id,
        "status": "FINISHED",
        "competition": competition,
        "score_full_time_home": scores[0],
        "score_full_time_away": scores[1],
    }


def prediction(match_id, home=70, draw=20, away=10, competition="Ligue 1"):
    return {
        "id": match_id,
        "match_id": match_id,
        "competition": competition,
        "model_version": "elo-poisson-calibrated-v1",
        "probabilities": {"home": home, "draw": draw, "away": away},
        "goals": {"over_2_5": 60, "btts": 55},
        "confidence": {"score": max(home, draw, away), "status": "FIABLE"},
    }


def shadow_record(
    match_id,
    shadow_pick="home",
    production_pick="home",
    shadow_probs=None,
    production_probs=None,
    confidence=70,
    odds=1.8,
):
    shadow_probs = shadow_probs or {"home": 70, "draw": 20, "away": 10}
    production_probs = production_probs or {"home": 60, "draw": 25, "away": 15}
    return {
        "id": f"shadow-{match_id}",
        "match_id": match_id,
        "candidate_model_version": "ml-shadow-v1",
        "production_model_version": "elo-poisson-calibrated-v1",
        "production_prediction": {
            "match_id": match_id,
            "model_version": "elo-poisson-calibrated-v1",
            "probabilities": production_probs,
            "confidence": {"score": max(production_probs.values())},
            "odds": {production_pick: odds},
            "market": "1x2",
        },
        "shadow_prediction": {
            "match_id": match_id,
            "model_version": "ml-shadow-v1",
            "available": True,
            "predicted_result": shadow_pick,
            "probabilities": shadow_probs,
            "confidence": confidence,
            "odds": {shadow_pick: odds},
            "market": "1x2",
        },
        "comparison": {
            "production_pick": production_pick,
            "shadow_pick": shadow_pick,
            "same_pick": production_pick == shadow_pick,
            "disagreement_level": "none" if production_pick == shadow_pick else "medium",
        },
        "created_at": "2026-05-10T10:00:00+00:00",
    }


class FakeRequest:
    def __init__(self, body):
        self.body = body

    async def json(self):
        return self.body


def feature_snapshot_row(index: int) -> dict:
    labels = ["home", "draw", "away"]
    label = labels[index % 3]
    scores = {
        "home": (2, 1),
        "draw": (1, 1),
        "away": (0, 2),
    }[label]
    return {
        "match_id": f"train-{index}",
        "model_version": main.MODEL_VERSION,
        "features": {
            "elo_delta": float(index % 11),
            "form_delta": float((index % 7) - 3),
            "attack_delta": float(index % 5),
            "defense_delta": float((index % 4) - 2),
            "home_probability": 40 + (index % 20),
            "draw_probability": 20 + (index % 10),
            "away_probability": 30 + (index % 15),
            "ignored_text": "not numeric",
        },
        "target": {
            "home_score": scores[0],
            "away_score": scores[1],
        },
    }


class LearningEngineTests(unittest.TestCase):
    def setUp(self):
        self.engine = None
        self.patches = []

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        if self.engine is not None:
            self.engine.dispose()

    def use_sqlite_registry(self):
        self.engine = create_engine("sqlite:///:memory:", future=True)
        database.metadata.create_all(self.engine)
        self.patches.extend(
            [
                patch.object(database, "get_engine", return_value=self.engine),
                patch.object(repository, "get_engine", return_value=self.engine),
            ]
        )
        for item in self.patches:
            item.start()
        return self.engine

    def test_feedback_metrics_group_by_market_competition_and_confidence(self):
        report = build_feedback_report(
            [
                finished_match("m1", "home", "Ligue 1"),
                finished_match("m2", "away", "Champions League"),
            ],
            [
                prediction("m1", 70, 20, 10, "Ligue 1"),
                prediction("m2", 65, 20, 15, "Champions League"),
            ],
        )

        self.assertEqual(report["evaluated_matches"], 2)
        self.assertEqual(report["accuracy"], 50)
        self.assertIsNotNone(report["log_loss"])
        self.assertIsNotNone(report["brier_score"])
        self.assertIn("1x2", report["performance_by_market"])
        self.assertIn("Champions League", report["performance_by_competition"])
        self.assertGreaterEqual(len(report["frequent_errors"]), 1)

    def test_calibration_profile_and_prediction_bucket_factor(self):
        profile = build_calibration_profile(
            [finished_match("m1", "home"), finished_match("m2", "away")],
            [prediction("m1", 70, 20, 10), prediction("m2", 70, 20, 10)],
        )
        calibrated = calibrate_prediction(prediction("future", 70, 20, 10), profile)

        self.assertTrue(profile["calibration_version"].startswith("calib-bucket_scaling-all-"))
        self.assertEqual(sum(calibrated["probabilities"].values()), 100)
        self.assertEqual(calibrated["calibration_version"], profile["calibration_version"])
        self.assertFalse(calibrated["calibration"]["applied"])
        self.assertEqual(profile["calibration_status"], "insufficient_data")

    def test_build_confidence_buckets_empty(self):
        buckets = build_confidence_buckets([])
        self.assertEqual(len(buckets), 10)
        self.assertTrue(all(bucket["status"] == "insufficient_data" for bucket in buckets))
        self.assertTrue(all(bucket["actual_success_rate"] is None for bucket in buckets))

    def test_build_confidence_buckets_insufficient_data(self):
        buckets = build_confidence_buckets([{"confidence": 0.64, "correct": True}])
        target = next(bucket for bucket in buckets if bucket["bucket_label"] == "60-70%")
        self.assertEqual(target["predictions_count"], 1)
        self.assertEqual(target["status"], "insufficient_data")
        self.assertIsNone(target["calibration_gap"])

    def test_build_confidence_buckets_overconfident(self):
        rows = [{"confidence": 0.82, "correct": index < 3} for index in range(10)]
        bucket = next(item for item in build_confidence_buckets(rows) if item["bucket_label"] == "80-90%")
        self.assertEqual(bucket["status"], "overconfident")
        self.assertLess(bucket["calibration_gap"], 0)

    def test_build_confidence_buckets_underconfident(self):
        rows = [{"confidence": 0.52, "correct": index < 8} for index in range(10)]
        bucket = next(item for item in build_confidence_buckets(rows) if item["bucket_label"] == "50-60%")
        self.assertEqual(bucket["status"], "underconfident")
        self.assertGreater(bucket["calibration_gap"], 0)

    def test_global_calibration_metrics(self):
        rows = [{"confidence": 0.62, "correct": index < 18} for index in range(30)]
        buckets = build_confidence_buckets(rows)
        metrics = build_global_calibration_metrics(buckets, 30)
        self.assertGreaterEqual(metrics["samples_count"], 30)
        self.assertIsNotNone(metrics["expected_calibration_error"])
        self.assertIn(metrics["calibration_status"], {"mostly_calibrated", "mixed", "overconfident", "underconfident"})

    def test_generate_calibration_version(self):
        version = generate_calibration_version("ml candidate/v1", "bucket_scaling")
        self.assertTrue(version.startswith("calib-bucket_scaling-ml-candidate-v1-"))

    def test_create_calibration_candidate(self):
        profile = build_calibration_profile(
            [finished_match(f"c{i}", "home") for i in range(30)],
            [prediction(f"c{i}", 60, 25, 15) for i in range(30)],
            model_version="elo-poisson-calibrated-v1",
        )
        candidate = create_calibration_candidate(profile)
        self.assertEqual(candidate["status"], "candidate")
        self.assertEqual(candidate["samples_count"], 30)
        self.assertIn("expected_calibration_error", candidate["metrics"])

    def test_calibration_insufficient_data_not_activated(self):
        self.use_sqlite_registry()
        profile = build_calibration_profile([finished_match("i1", "home")], [prediction("i1", 60, 25, 15)])
        saved = repository.create_model_calibration(create_calibration_candidate(profile))
        self.assertIsNotNone(saved)
        activated = repository.activate_calibration_version(saved["calibration_version"])
        self.assertIsNone(activated)

    def test_apply_bucket_calibration_binary(self):
        profile = {"factors": {"active": True, "global_correction": -0.1, "bucket_corrections": {"70-80%": -0.1}}}
        self.assertEqual(apply_bucket_calibration_binary(0.72, profile), 0.62)

    def test_apply_bucket_calibration_multiclass_renormalizes(self):
        profile = {"factors": {"active": True, "global_correction": -0.1, "bucket_corrections": {"70-80%": -0.1}}}
        calibrated = apply_bucket_calibration_multiclass({"home": 72, "draw": 18, "away": 10}, profile)
        self.assertEqual(sum(calibrated.values()), 100)
        self.assertLess(calibrated["home"], 72)

    def test_model_versioning_appends_entries(self):
        registry_path = Path(__file__).with_name("_tmp_model_versions.json")
        if registry_path.exists():
            registry_path.unlink()
        try:
            with patch("services.model_versioning.REGISTRY_PATH", registry_path), patch(
                "services.model_versioning.MODEL_DIR", registry_path.parent
            ):
                record_model_version(
                    model_version="ml-candidate-v1",
                    feature_set_version="pre-match-advanced-v1",
                    calibration_version="calibration-buckets-v1",
                    trained_at="2026-05-09T20:00:00Z",
                    rows_used=120,
                    metrics={"accuracy": 44},
                    status="candidate",
                )
                record_model_version(
                    model_version="ml-candidate-v1",
                    feature_set_version="pre-match-advanced-v1",
                    calibration_version="calibration-buckets-v1",
                    trained_at="2026-05-09T21:00:00Z",
                    rows_used=130,
                    metrics={"accuracy": 46},
                    status="shadow",
                )

                versions = list_model_versions()
        finally:
            if registry_path.exists():
                registry_path.unlink()

        self.assertEqual(len(versions), 2)
        self.assertEqual({item["status"] for item in versions}, {"candidate", "shadow"})

    def test_model_versions_schema_created(self):
        engine = self.use_sqlite_registry()
        repository.init_model_versions_schema()

        with engine.connect() as connection:
            columns = {row._mapping["name"] for row in connection.execute(text("PRAGMA table_info(model_versions)"))}

        self.assertIn("model_version", columns)
        self.assertIn("metrics_json", columns)
        self.assertIn("governance_json", columns)

    def test_save_and_list_model_version_postgresql(self):
        self.use_sqlite_registry()

        saved = repository.save_model_version(
            {
                "model_version": "ml-candidate-v2",
                "model_type": "random_forest",
                "status": "candidate",
                "rows_used": 64,
                "features_used": 12,
                "accuracy": 48,
                "log_loss": 0.92,
                "brier_score": 0.42,
                "metrics": {"accuracy": 48},
                "governance": {"ready": False},
            }
        )
        versions = repository.list_model_versions()

        self.assertEqual(saved["model_version"], "ml-candidate-v2")
        self.assertEqual(len(versions), 1)
        self.assertEqual(versions[0]["source"], "postgresql")

    def test_unique_model_version_upsert_controlled(self):
        self.use_sqlite_registry()

        repository.save_model_version({"model_version": "ml-candidate-v3", "status": "candidate", "rows_used": 40, "metrics": {"accuracy": 41}})
        repository.save_model_version(
            {
                "model_version": "ml-candidate-v3",
                "status": "shadow",
                "rows_used": 45,
                "metrics": {"shadow_predictions_saved": 9},
            }
        )
        versions = repository.list_model_versions()

        self.assertEqual(len(versions), 1)
        self.assertEqual(versions[0]["status"], "candidate")
        self.assertEqual(versions[0]["metrics"]["shadow_predictions_saved"], 9)

    def test_import_model_versions_from_file_if_needed(self):
        self.use_sqlite_registry()
        registry_path = Path(__file__).with_name("_tmp_model_versions_import.json")
        registry_path.write_text(
            '[{"model_version":"ml-imported-v1","status":"candidate","rows_used":50,"metrics":{"accuracy":45}}]',
            encoding="utf-8",
        )
        try:
            report = repository.import_model_versions_from_file_if_needed(registry_path)
            versions = repository.list_model_versions()
        finally:
            registry_path.unlink(missing_ok=True)

        self.assertEqual(report["status"], "ok")
        self.assertEqual(report["imported_count"], 1)
        self.assertEqual(versions[0]["source"], "file")

    def test_models_versions_endpoint_uses_postgresql(self):
        self.use_sqlite_registry()
        repository.save_model_version({"model_version": "ml-endpoint-v1", "status": "candidate", "rows_used": 55, "metrics": {"accuracy": 46}})

        report = main.model_versions()

        self.assertEqual(report["storage"], "postgresql")
        self.assertEqual(report["versions_count"], 1)
        self.assertEqual(report["latest_candidate_model"]["model_version"], "ml-endpoint-v1")

    def test_model_governance_uses_postgresql_versions(self):
        self.use_sqlite_registry()
        repository.save_model_version(
            {
                "model_version": "ml-governance-v1",
                "status": "candidate",
                "rows_used": 60,
                "accuracy": 46,
                "brier_score": 0.4,
                "log_loss": 0.85,
                "metrics": {"accuracy": 46, "brier_score": 0.4, "log_loss": 0.85},
            }
        )

        report = main._model_governance_report()

        self.assertEqual(report["candidate_model"]["version"], "ml-governance-v1")

    def test_training_registers_candidate_model_version(self):
        self.use_sqlite_registry()
        training_report = {
            "status": "ok",
            "model_type": "random_forest",
            "model_version": "ml-trained-v1",
            "feature_set_version": "pre-match-advanced-v1",
            "trained_at": "2026-05-10T10:00:00Z",
            "rows_used": 80,
            "features_used": ["elo_delta", "form_delta"],
            "accuracy": 49,
            "log_loss": 0.82,
            "brier_score_1x2": 0.39,
            "target_distribution": {"home": 40, "draw": 20, "away": 20},
        }
        with patch.object(main, "_require_admin_key", return_value=None), patch.object(main, "_training_dataset", return_value=[{"features": {}, "target": {}}] * 80), patch.object(
            main,
            "build_dataset_quality_report",
            return_value={"safe_for_training": True, "recommendation": "safe_to_train"},
        ), patch.object(main, "train_candidate_model", return_value=training_report):
            result = main.train_candidate_model_admin(x_admin_key="test")

        saved = repository.get_latest_candidate_model()
        self.assertEqual(result["registry_entry"]["storage"], "postgresql")
        self.assertEqual(saved["model_version"], "ml-trained-v1")
        self.assertEqual(saved["features_used"], 2)

    def test_load_training_rows_from_feature_snapshots_postgresql(self):
        self.use_sqlite_registry()
        repository.save_feature_snapshots([feature_snapshot_row(index) for index in range(9)])

        report = load_training_rows_from_feature_snapshots(limit=20)

        self.assertEqual(report["storage"], "postgresql")
        self.assertEqual(report["rows_loaded"], 9)
        self.assertEqual(report["rows_after_validation"], 9)
        self.assertEqual(report["invalid_feature_rows"], 0)
        self.assertEqual(report["invalid_target_rows"], 0)
        self.assertIn("elo_delta", report["sample_feature_keys"])

    def test_extract_numeric_features(self):
        report = extract_numeric_features({"a": 1, "b": "2.5", "c": None, "d": "text", "e": float("inf")})

        self.assertTrue(report["valid"])
        self.assertEqual(report["features"], {"a": 1.0, "b": 2.5})
        self.assertIn("e", report["invalid_keys"])

    def test_extract_target_class_from_scores(self):
        self.assertEqual(extract_target_class({"home_score": 2, "away_score": 1})["target_class"], 0)
        self.assertEqual(extract_target_class({"home_score": 1, "away_score": 1})["target_class"], 1)
        self.assertEqual(extract_target_class({"home_score": 0, "away_score": 2})["target_class"], 2)
        self.assertEqual(extract_target_class({"winner": "AWAY_TEAM"})["target_label"], "away")

    def test_train_candidate_model_success(self):
        artifact_path = Path(__file__).with_name("_tmp_candidate.joblib")
        metadata_path = Path(__file__).with_name("_tmp_candidate_metadata.json")
        rows = [feature_snapshot_row(index) for index in range(90)]
        try:
            with patch("services.ml_training.ARTIFACT_PATH", artifact_path), patch("services.ml_training.METADATA_PATH", metadata_path):
                report = train_candidate_model(rows, model_type="random_forest")
        finally:
            artifact_path.unlink(missing_ok=True)
            metadata_path.unlink(missing_ok=True)

        self.assertEqual(report["status"], "success")
        self.assertGreater(report["rows_used"], 0)
        self.assertGreater(report["features_used"], 0)
        self.assertIsNotNone(report["log_loss"])
        self.assertIsNotNone(report["brier_score"])
        self.assertTrue(report["model_version"].startswith("ml-candidate-random_forest-"))

    def test_train_candidate_model_returns_error_without_valid_rows(self):
        report = train_candidate_model([{"features": {"a": "text"}, "target": {"result": "bad"}}], model_type="random_forest")

        self.assertEqual(report["status"], "error")
        self.assertEqual(report["rows_used"], 0)
        self.assertGreaterEqual(report["invalid_rows"], 1)

    def test_train_candidate_model_registers_candidate_model_version(self):
        self.use_sqlite_registry()
        repository.save_feature_snapshots([feature_snapshot_row(index) for index in range(90)])
        artifact_path = Path(__file__).with_name("_tmp_endpoint_candidate.joblib")
        metadata_path = Path(__file__).with_name("_tmp_endpoint_candidate_metadata.json")
        try:
            with patch.object(main, "_require_admin_key", return_value=None), patch(
                "services.ml_training.ARTIFACT_PATH",
                artifact_path,
            ), patch("services.ml_training.METADATA_PATH", metadata_path):
                result = main.train_candidate_model_admin(x_admin_key="test", limit=120, bypass_quality_gate=True)
        finally:
            artifact_path.unlink(missing_ok=True)
            metadata_path.unlink(missing_ok=True)

        saved = repository.get_latest_candidate_model()
        self.assertEqual(result["status"], "success")
        self.assertEqual(saved["status"], "candidate")
        self.assertEqual(saved["model_version"], result["model_version"])
        self.assertGreater(saved["rows_used"], 0)

    def test_workflow_status_detects_candidate_from_postgres(self):
        self.use_sqlite_registry()
        repository.save_model_version({"model_version": "ml-workflow-v1", "status": "candidate", "rows_used": 80, "metrics": {"accuracy": 51}})

        workflow = main._workflow_status_compact()

        self.assertTrue(workflow["candidate_model"]["trained"])
        self.assertEqual(workflow["candidate_model"]["model_version"], "ml-workflow-v1")
        self.assertEqual(workflow["next_step"], "generate_shadow_predictions")

    def test_learning_monitoring_after_candidate_training(self):
        self.use_sqlite_registry()
        repository.save_model_version({"model_version": "ml-monitor-trained-v1", "status": "candidate", "rows_used": 80, "metrics": {"accuracy": 51}})

        report = main.learning_monitoring()

        self.assertEqual(report["latest_candidate_model_version"], "ml-monitor-trained-v1")
        self.assertEqual(report["next_best_action"]["label"], "Générer les prédictions shadow")

    def test_model_versions_contains_candidate_after_training(self):
        self.use_sqlite_registry()
        repository.save_model_version({"model_version": "ml-versions-trained-v1", "status": "candidate", "rows_used": 80, "metrics": {"accuracy": 51}})

        report = main.model_versions()

        self.assertEqual(report["latest_candidate_model"]["model_version"], "ml-versions-trained-v1")

    def test_learning_monitoring_endpoint(self):
        self.use_sqlite_registry()
        repository.save_model_version({"model_version": "ml-monitor-v1", "status": "candidate", "rows_used": 55, "metrics": {"accuracy": 46}})

        report = main.learning_monitoring()

        self.assertIn(report["status"], {"ok", "warning"})
        self.assertEqual(report["storage"], "postgresql")
        self.assertEqual(report["latest_candidate_model_version"], "ml-monitor-v1")
        self.assertIn("next_best_action", report)

    def test_shadow_backtesting_no_predictions(self):
        report = calculate_shadow_backtest_report([], [])

        self.assertEqual(report["shadow_predictions_total"], 0)
        self.assertEqual(report["evaluable_predictions"], 0)
        self.assertEqual(report["recommendation"]["status"], "collect_more_data")

    def test_shadow_backtesting_pending_predictions(self):
        report = calculate_shadow_backtest_report(
            [{"id": "m1", "match_id": "m1", "status": "SCHEDULED"}],
            [shadow_record("m1")],
        )

        self.assertEqual(report["shadow_predictions_total"], 1)
        self.assertEqual(report["pending_predictions"], 1)
        self.assertEqual(report["invalid_predictions"], 0)
        self.assertEqual(report["metrics"]["accuracy"], None)

    def test_shadow_backtesting_does_not_count_pending_as_wrong(self):
        report = calculate_shadow_backtest_report(
            [{"id": "m1", "match_id": "m1", "status": "SCHEDULED"}],
            [shadow_record("m1", shadow_pick="away", production_pick="home")],
        )

        self.assertEqual(report["evaluable_predictions"], 0)
        self.assertEqual(report["pending_predictions"], 1)
        self.assertIsNone(report["metrics"]["accuracy"])
        self.assertIsNone(report["comparison"]["delta_accuracy"])

    def test_shadow_backtesting_invalid_prediction_is_not_evaluable(self):
        record = shadow_record("m1", shadow_pick="home", production_pick="home")
        record["shadow_prediction"]["predicted_result"] = None
        record["shadow_prediction"]["probabilities"] = {}
        record["comparison"]["shadow_pick"] = None

        report = calculate_shadow_backtest_report([finished_match("m1", "home")], [record])

        self.assertEqual(report["evaluable_predictions"], 0)
        self.assertEqual(report["pending_predictions"], 0)
        self.assertEqual(report["invalid_predictions"], 1)
        self.assertEqual(report["invalid_matches"][0]["reason"], "missing_shadow_selection")

    def test_shadow_backtesting_evaluable_metrics_and_roi(self):
        report = calculate_shadow_backtest_report(
            [finished_match("m1", "home"), finished_match("m2", "away", competition="Serie A")],
            [
                shadow_record("m1", shadow_pick="home", production_pick="draw", odds=2.0),
                shadow_record(
                    "m2",
                    shadow_pick="home",
                    production_pick="away",
                    shadow_probs={"home": 55, "draw": 25, "away": 20},
                    production_probs={"home": 20, "draw": 20, "away": 60},
                    odds=1.9,
                ),
            ],
        )

        self.assertEqual(report["evaluable_predictions"], 2)
        self.assertEqual(report["metrics"]["accuracy"], 50)
        self.assertIsNotNone(report["metrics"]["log_loss"])
        self.assertIsNotNone(report["metrics"]["brier_score"])
        self.assertEqual(report["metrics"]["roi_theoretical"], 0.0)
        self.assertEqual(report["comparison"]["delta_accuracy"], 0)
        self.assertEqual(report["comparison"]["comparison_status"], "insufficient_data")
        self.assertIsNone(report["comparison"]["candidate_better_than_production"])
        self.assertEqual(report["production_metrics"]["accuracy"], 50)
        self.assertEqual(report["by_market"][0]["market"], "1x2")
        self.assertEqual(report["by_market"][0]["evaluable_count"], 2)
        self.assertGreaterEqual(len(report["by_competition"]), 1)
        self.assertGreaterEqual(len(report["by_confidence"]), 1)

    def test_shadow_backtesting_endpoint(self):
        records = [shadow_record("m1")]
        with patch.object(main, "_available_matches", return_value=[finished_match("m1", "home")]), patch.object(
            main.repository,
            "get_ml_shadow_predictions",
            return_value=records,
        ):
            report = main.shadow_backtesting_report()

        self.assertEqual(report["status"], "ok")
        self.assertEqual(report["candidate_model_version"], "ml-shadow-v1")
        self.assertEqual(report["evaluable_predictions"], 1)

    def test_workflow_status_after_shadow_predictions_pending(self):
        with patch.object(main, "_feature_summary", return_value={"snapshots_count": 10, "with_target_count": 8, "target_coverage": 80, "storage": "postgresql"}), patch.object(
            main,
            "_refresh_status",
            return_value={"storage": "postgresql", "matches_imported": 10},
        ), patch.object(main, "_ml_status_compact", return_value={"latest_candidate_model": {"model_version": "ml-v1", "status": "candidate", "rows_used": 50}}), patch.object(
            main,
            "_shadow_summary_compact",
            return_value={"shadow_predictions_count": 1, "disagreement_count": 0},
        ), patch.object(main, "calculate_shadow_backtest_report", return_value={"evaluable_predictions": 0, "pending_predictions": 1, "shadow_accuracy": 0, "recommendation": {"status": "collect_more_data"}}):
            workflow = main._workflow_status_compact()

        self.assertFalse(workflow["shadow_backtesting"]["ready"])
        self.assertEqual(workflow["shadow_backtesting"]["pending_predictions"], 1)
        self.assertEqual(workflow["next_step"], "wait_for_results")

    def test_workflow_status_after_shadow_predictions_evaluable(self):
        with patch.object(main, "_feature_summary", return_value={"snapshots_count": 10, "with_target_count": 8, "target_coverage": 80, "storage": "postgresql"}), patch.object(
            main,
            "_refresh_status",
            return_value={"storage": "postgresql", "matches_imported": 10},
        ), patch.object(main, "_ml_status_compact", return_value={"latest_candidate_model": {"model_version": "ml-v1", "status": "candidate", "rows_used": 50}}), patch.object(
            main,
            "_shadow_summary_compact",
            return_value={"shadow_predictions_count": 35, "disagreement_count": 3},
        ), patch.object(main, "calculate_shadow_backtest_report", return_value={"evaluable_predictions": 35, "pending_predictions": 0, "shadow_accuracy": 55, "recommendation": {"status": "promotion_ready_manual_review"}}):
            workflow = main._workflow_status_compact()

        self.assertTrue(workflow["shadow_backtesting"]["ready"])
        self.assertEqual(workflow["next_step"], "review_governance")

    def test_governance_blocks_insufficient_shadow_data(self):
        report = build_model_governance_report(
            {"current_model_version": "elo-poisson-calibrated-v1"},
            {"latest_candidate": {"status": "candidate", "model_version": "ml-v1", "rows_used": 60, "accuracy": 58, "brier_score": 0.5, "log_loss": 0.9}},
            {"safe_for_training": True, "recommendation": "safe_to_train"},
            {"trend_summary": {"monitoring_status": "healthy"}},
            {"evaluable_predictions": 1, "metrics": {"accuracy": 100}, "recommendation": {"status": "collect_more_data"}},
            {"recommendation": "insufficient_shadow_data"},
            {"evaluated_matches": 20, "accuracy": 50, "log_loss": 1.0, "brier_score": 0.6, "theoretical_roi": 0.1},
        )

        self.assertEqual(report["promotion_readiness"]["level"], "blocked_insufficient_data")
        self.assertFalse(report["promotion_rules"]["tested_matches"]["passed"])

    def test_learning_monitoring_includes_shadow_backtesting(self):
        self.use_sqlite_registry()
        repository.save_model_version({"model_version": "ml-monitor-shadow-v1", "status": "candidate", "rows_used": 80, "metrics": {"accuracy": 51}})
        with patch.object(main, "calculate_shadow_backtest_report", return_value={"shadow_predictions_total": 1, "evaluable_predictions": 0, "pending_predictions": 1, "backtesting_status": "pending", "recommendation": {"status": "collect_more_data"}}):
            report = main.learning_monitoring()

        self.assertEqual(report["shadow_predictions_total"], 1)
        self.assertEqual(report["shadow_evaluable_predictions"], 0)
        self.assertEqual(report["next_best_action"]["label"], "Attendre les résultats des matchs")

    def test_governance_blocks_promotion_when_strict_rules_fail(self):
        report = build_model_governance_report(
            {"current_model_version": "elo-poisson-calibrated-v1"},
            {
                "latest_candidate": {
                    "status": "ok",
                    "model_version": "ml-candidate-v1",
                    "rows_used": 40,
                    "accuracy": 40,
                    "brier_score_1x2": 0.7,
                    "log_loss": 1.1,
                }
            },
            {"safe_for_training": True, "recommendation": "safe_to_train"},
            {"trend_summary": {"monitoring_status": "healthy"}},
            {"evaluated_matches": 20, "shadow_accuracy": 45, "production_accuracy": 50},
            {"recommendation": "insufficient_shadow_data"},
            {"evaluated_matches": 20, "accuracy": 50, "log_loss": 1.0, "brier_score": 0.6, "theoretical_roi": -0.1},
        )

        self.assertFalse(report["promotion_readiness"]["ready"])
        self.assertFalse(report["promotion_rules"]["tested_matches"]["passed"])
        self.assertFalse(report["promotion_rules"]["roi"]["passed"])
        self.assertNotIn("Critères stricts de promotion non satisfaits.", report["promotion_readiness"]["blocking_reasons"])
        self.assertIn(
            "Critères stricts de promotion non satisfaits : garder le candidat en shadow.",
            report["promotion_readiness"]["warnings"],
        )

    def test_training_diagnostics_counts_invalid_rows_and_targets(self):
        rows = [
            {"features": {"elo_delta": 1}, "target": {"result": "home"}},
            {"features": {"elo_delta": 1}, "target": {"result": "draw"}},
            {"features": {"elo_delta": 1}, "target": {"result": "bad"}},
            {"features": {"elo_delta": 1}, "target": None},
        ]

        prepared = prepare_training_rows(rows)

        self.assertEqual(prepared["rows_loaded"], 4)
        self.assertEqual(prepared["rows_used"], 2)
        self.assertEqual(prepared["invalid_rows"], 2)
        self.assertEqual(prepared["target_distribution"], {"home": 1, "draw": 1})
        self.assertIn("elo_delta", prepared["features_used"])

    def test_promotion_blocked_without_candidate(self):
        report = evaluate_model_promotion(
            versions_report={"versions": [], "latest_candidate_model": None},
            governance_report={"production_model": {"locked": False}, "policy": {"production_model_locked": False}},
            shadow_backtesting_report={"shadow_predictions_total": 0, "evaluable_predictions": 0},
        )

        self.assertFalse(report["promotion_allowed"])
        self.assertEqual(report["readiness"], "blocked_no_shadow_backtesting")
        self.assertIn("Aucun modèle candidat disponible.", report["reasons"])

    def test_promotion_blocked_insufficient_shadow_data(self):
        report = evaluate_model_promotion(
            versions_report={
                "latest_candidate_model": {"model_version": "ml-v1", "status": "candidate", "rows_used": 80, "accuracy": 55},
                "current_production_model": {"model_version": "prod-v1"},
                "versions": [],
            },
            governance_report={"production_model": {"locked": False}, "policy": {"production_model_locked": False}},
            shadow_backtesting_report={"shadow_predictions_total": 10, "evaluable_predictions": 1, "metrics": {"accuracy": 60}},
        )

        self.assertFalse(report["promotion_allowed"])
        self.assertEqual(report["readiness"], "blocked_insufficient_data")

    def test_promotion_blocked_if_production_locked(self):
        report = evaluate_model_promotion(
            versions_report={
                "latest_candidate_model": {"model_version": "ml-v1", "status": "candidate", "rows_used": 80, "accuracy": 55},
                "current_production_model": {"model_version": "prod-v1", "locked": True},
                "versions": [],
            },
            governance_report={"production_model": {"locked": True}, "policy": {"production_model_locked": True}},
            shadow_backtesting_report={"shadow_predictions_total": 40, "evaluable_predictions": 35, "metrics": {"accuracy": 60}},
        )

        self.assertFalse(report["promotion_allowed"])
        self.assertEqual(report["readiness"], "blocked_production_locked")

    def test_promotion_allowed_when_governance_ready(self):
        report = evaluate_model_promotion(
            versions_report={
                "latest_candidate_model": {
                    "model_version": "ml-ready-v1",
                    "status": "candidate",
                    "rows_used": 100,
                    "accuracy": 60,
                    "log_loss": 0.8,
                    "brier_score": 0.4,
                },
                "current_production_model": {"model_version": "prod-v1"},
                "versions": [],
            },
            governance_report={"production_model": {"locked": False}, "policy": {"production_model_locked": False}},
            shadow_backtesting_report={
                "shadow_predictions_total": 40,
                "evaluable_predictions": 35,
                "metrics": {"accuracy": 60, "log_loss": 0.8, "brier_score": 0.4, "roi_theoretical": 0.1},
                "comparison": {"delta_accuracy": 3, "delta_log_loss": -0.1, "delta_brier_score": -0.02, "delta_roi": 0.1},
            },
        )

        self.assertTrue(report["promotion_allowed"])
        self.assertEqual(report["readiness"], "promotion_ready")

    def test_promote_candidate_archives_previous_production_and_logs(self):
        self.use_sqlite_registry()
        repository.save_model_version({"model_version": "prod-v1", "status": "production", "rows_used": 100})
        repository.save_model_version({"model_version": "ml-promote-v1", "status": "candidate", "rows_used": 120, "accuracy": 60})
        allowed = {
            "status": "ok",
            "promotion_allowed": True,
            "readiness": "promotion_ready",
            "reasons": [],
            "requirements": {"minimum_evaluable_predictions": 30, "current_evaluable_predictions": 35},
        }
        with patch.object(main, "_require_admin_key", return_value=None), patch.object(main, "evaluate_model_promotion", return_value=allowed), patch.object(
            main,
            "calculate_shadow_backtest_report",
            return_value={"shadow_predictions_total": 40, "evaluable_predictions": 35},
        ):
            request = FakeRequest({"model_version": "ml-promote-v1", "confirm": True})
            result = asyncio.run(main.promote_candidate_model(request, x_admin_key="test"))

        self.assertEqual(result["status"], "success")
        self.assertEqual(repository.get_model_version("prod-v1")["status"], "archived")
        self.assertEqual(repository.get_model_version("ml-promote-v1")["status"], "production")
        self.assertEqual(repository.list_model_promotion_audit()[0]["action"], "promote")

    def test_promote_candidate_requires_confirm_true(self):
        self.use_sqlite_registry()
        with patch.object(main, "_require_admin_key", return_value=None):
            request = FakeRequest({"model_version": "ml-v1", "confirm": False})
            result = asyncio.run(main.promote_candidate_model(request, x_admin_key="test"))

        self.assertEqual(result["status"], "blocked")

    def test_rollback_requires_confirm_true(self):
        self.use_sqlite_registry()
        with patch.object(main, "_require_admin_key", return_value=None):
            request = FakeRequest({"target_model_version": "prod-v1", "confirm": False})
            result = asyncio.run(main.rollback_production_model(request, x_admin_key="test"))

        self.assertEqual(result["status"], "blocked")

    def test_rollback_restores_previous_production(self):
        self.use_sqlite_registry()
        repository.save_model_version({"model_version": "prod-current", "status": "production", "rows_used": 100})
        repository.save_model_version({"model_version": "prod-previous", "status": "archived", "rows_used": 100})
        with patch.object(main, "_require_admin_key", return_value=None):
            request = FakeRequest({"target_model_version": "prod-previous", "confirm": True})
            result = asyncio.run(main.rollback_production_model(request, x_admin_key="test"))

        self.assertEqual(result["status"], "success")
        self.assertEqual(repository.get_model_version("prod-previous")["status"], "production")
        self.assertEqual(repository.get_model_version("prod-current")["status"], "archived")

    def test_promotion_audit_endpoint(self):
        self.use_sqlite_registry()
        repository.log_model_promotion_event(action="blocked", candidate_model_version="ml-v1", result="blocked", detail="no")
        with patch.object(main, "_require_admin_key", return_value=None):
            report = main.model_promotion_audit(x_admin_key="test")

        self.assertEqual(report["status"], "ok")
        self.assertEqual(report["events_count"], 1)

    def test_learning_monitoring_includes_promotion_readiness(self):
        self.use_sqlite_registry()
        repository.save_model_version({"model_version": "ml-monitor-promotion-v1", "status": "candidate", "rows_used": 80, "metrics": {"accuracy": 51}})
        with patch.object(main, "calculate_shadow_backtest_report", return_value={"shadow_predictions_total": 1, "evaluable_predictions": 0, "pending_predictions": 1}):
            report = main.learning_monitoring()

        self.assertIn("promotion_readiness", report)
        self.assertFalse(report["promotion_allowed"])

    def test_learning_calibration_endpoint(self):
        self.use_sqlite_registry()
        with patch.object(main, "_available_matches", return_value=[finished_match("cal-endpoint", "home")]), patch.object(main, "_available_predictions", return_value=[prediction("cal-endpoint", 65, 20, 15)]):
            report = main.learning_calibration()

        self.assertEqual(report["storage"], "postgresql")
        self.assertEqual(report["calibration_status"], "insufficient_data")
        self.assertIn("buckets", report)

    def test_recompute_calibration_endpoint(self):
        self.use_sqlite_registry()
        matches = [finished_match(f"recompute-{index}", "home") for index in range(30)]
        preds = [prediction(f"recompute-{index}", 60, 25, 15) for index in range(30)]
        with patch.object(main, "_available_matches", return_value=matches), patch.object(main, "_available_predictions", return_value=preds):
            report = asyncio.run(main.recompute_learning_calibration(FakeRequest({"method": "bucket_scaling"}), x_admin_key=None))

        self.assertEqual(report["status"], "ok")
        self.assertIsNotNone(report["calibration_record"])
        self.assertEqual(report["calibration_record"]["status"], "candidate")

    def test_activate_calibration_requires_confirm(self):
        self.use_sqlite_registry()
        result = asyncio.run(main.activate_learning_calibration(FakeRequest({"calibration_version": "missing"}), x_admin_key=None))
        self.assertEqual(result["status"], "blocked")

    def test_learning_monitoring_includes_calibration(self):
        self.use_sqlite_registry()
        report = main.learning_monitoring()
        self.assertIn("calibration_samples_count", report)
        self.assertIn("calibration_minimum_required", report)

    def test_pipeline_job_lifecycle_success(self):
        self.use_sqlite_registry()
        job = repository.create_pipeline_job("refresh_data", triggered_by="test")
        repository.mark_pipeline_job_running(job["id"])
        done = repository.mark_pipeline_job_success(job["id"], {"status": "ok"})

        self.assertEqual(done["status"], "success")
        self.assertEqual(done["result_json"]["status"], "ok")
        self.assertEqual(repository.get_latest_pipeline_job("refresh_data")["id"], job["id"])

    def test_pipeline_job_lifecycle_error(self):
        self.use_sqlite_registry()
        job = repository.create_pipeline_job("build_feature_store", triggered_by="test")
        repository.mark_pipeline_job_running(job["id"])
        done = repository.mark_pipeline_job_error(job["id"], "boom", {"status": "error"})

        self.assertEqual(done["status"], "error")
        self.assertEqual(done["error"], "boom")

    def test_reset_stale_pipeline_jobs(self):
        self.use_sqlite_registry()
        job = repository.create_pipeline_job("shadow_backtesting", triggered_by="test")
        repository.mark_pipeline_job_running(job["id"])
        with self.engine.begin() as connection:
            connection.execute(text("UPDATE pipeline_jobs SET started_at = '2020-01-01 00:00:00' WHERE id = :id"), {"id": job["id"]})

        report = repository.reset_stale_pipeline_jobs(max_age_minutes=1)

        self.assertEqual(report["reset_count"], 1)
        self.assertEqual(report["jobs"][0]["status"], "stale")

    def test_run_hourly_pipeline_skips_when_no_new_data(self):
        self.use_sqlite_registry()
        report = run_hourly_data_pipeline(
            {
                "refresh_data": lambda: {"status": "skipped", "detail": "No new data."},
                "build_feature_store": lambda: {"status": "ok"},
            },
            triggered_by="test",
        )

        self.assertEqual(report["status"], "ok")
        self.assertEqual(report["steps"][0]["status"], "skipped")

    def test_run_hourly_pipeline_does_not_promote_model(self):
        self.use_sqlite_registry()
        report = run_hourly_data_pipeline(
            {
                "refresh_data": lambda: {"status": "ok"},
                "build_feature_store": lambda: {"status": "ok"},
                "generate_shadow_predictions": lambda: {"status": "skipped", "detail": "No candidate."},
                "shadow_backtesting": lambda: {"status": "ok"},
                "monitoring": lambda: {"status": "ok"},
            },
            triggered_by="test",
        )

        self.assertEqual(report["status"], "ok")
        self.assertEqual(repository.list_model_versions(), [])

    def test_pipeline_status_returns_latest_jobs(self):
        self.use_sqlite_registry()
        repository.create_pipeline_job("refresh_data", triggered_by="test")
        with patch.object(main, "_workflow_status_compact", return_value={"refresh": {"data_imported": False}, "feature_store": {}, "candidate_model": {}, "shadow_predictions": {}, "shadow_backtesting": {}, "next_step": "refresh_data"}), patch.object(
            main, "learning_monitoring", return_value={"status": "ok"}
        ):
            report = main.pipeline_status(x_admin_key="test")

        self.assertIn("refresh_data", report["latest_jobs"])
        self.assertEqual(report["next_best_action"]["action"], "refresh_data")

    def test_run_daily_pipeline_updates_monitoring(self):
        self.use_sqlite_registry()
        report = main.pipeline_run_daily(x_admin_key="test")

        self.assertIn(report["status"], {"ok", "error"})
        self.assertTrue(repository.list_pipeline_jobs(limit=10))

    def test_pipeline_status_includes_next_best_action(self):
        self.use_sqlite_registry()
        with patch.object(main, "_workflow_status_compact", return_value={"refresh": {"data_imported": True}, "feature_store": {"ready": True}, "candidate_model": {"trained": False}, "shadow_predictions": {}, "shadow_backtesting": {}, "next_step": "train_candidate_model"}), patch.object(
            main, "learning_monitoring", return_value={"status": "ok"}
        ):
            report = main.pipeline_status(x_admin_key="test")

        self.assertEqual(report["next_best_action"]["action"], "train_candidate_model")

    def test_admin_alerts_include_stale_jobs(self):
        self.use_sqlite_registry()
        job = repository.create_pipeline_job("refresh_data", triggered_by="test")
        repository.mark_pipeline_job_running(job["id"])
        with self.engine.begin() as connection:
            connection.execute(text("UPDATE pipeline_jobs SET started_at = '2020-01-01 00:00:00' WHERE id = :id"), {"id": job["id"]})
        repository.reset_stale_pipeline_jobs(max_age_minutes=1)

        with patch.object(main, "_refresh_status", return_value={"last_refresh_at": "2026-05-10T00:00:00Z"}), patch.object(main, "_feature_summary_fast", return_value={"snapshots_count": 1, "with_target_count": 1}), patch.object(main, "_ml_status_compact", return_value={"status": "ok", "latest_candidate": {"status": "ok"}}), patch.object(main, "_dataset_quality_report", return_value={"safe_for_training": True, "recommendation": "safe_to_train"}):
            report = main._admin_alerts_report()

        self.assertTrue(any(item["id"] == "pipeline_jobs_stale" for item in report["alerts"]))

    def test_implied_probability_from_decimal_odds(self):
        self.assertEqual(implied_probability_from_odds(2.1), 0.4762)

    def test_expected_value_positive(self):
        self.assertEqual(calculate_expected_value(0.60, 2.10), 0.26)
        self.assertEqual(classify_value_bet(0.124, 0.26), "strong_value")

    def test_expected_value_negative(self):
        self.assertLess(calculate_expected_value(0.40, 1.80), 0)
        self.assertEqual(classify_value_bet(-0.1556, -0.28), "avoid")

    def test_value_status_no_odds(self):
        self.assertEqual(classify_value_bet(None, None), "no_real_odds")

    def test_value_status_insufficient_data(self):
        result = analyze_prediction({"match_id": "no-probability", "probabilities": {}, "confidence": {"score": 40}}, {})
        self.assertIn(result["value_status"], {"no_real_odds", "insufficient_data"})
        self.assertIn(result["recommendation_type"], {"wait", "insufficient_data"})

    def test_real_odds_missing_provider_does_not_simulate(self):
        with patch.dict("os.environ", {"ODDS_PROVIDER": "", "ODDS_API_KEY": "", "ODDS_BASE_URL": ""}, clear=False):
            self.assertFalse(is_odds_configured())
            report = fetch_real_odds_for_matches(["m1"])
        self.assertEqual(report["status"], "missing_provider_config")
        self.assertEqual(report["items"], [])

    def test_save_real_bookmaker_odds_and_latest(self):
        self.use_sqlite_registry()
        saved = repository.save_real_bookmaker_odds(
            {
                "match_id": "odds-match",
                "bookmaker": "RealBook",
                "market": "1X2",
                "selection": "HOME_WIN",
                "odds_decimal": 2.1,
                "provider": "real-provider",
                "source": "real_provider",
            }
        )
        self.assertIsNotNone(saved)
        latest = repository.get_latest_real_odds("odds-match", "1X2", "HOME_WIN")
        self.assertEqual(latest["bookmaker"], "RealBook")
        self.assertEqual(latest["source_type"], "provider")

    def test_expected_value_requires_real_odds(self):
        self.assertIsNone(calculate_expected_value(0.58, None))
        self.assertEqual(classify_value_bet(None, None), "no_real_odds")

    def test_fair_odds_from_probability(self):
        self.assertEqual(fair_odds_from_probability(0.5), 2.0)

    def test_minimum_value_odds(self):
        self.assertEqual(minimum_value_odds(0.5, margin=0.02), 2.04)

    def test_calculate_risk_adjusted_value(self):
        self.assertEqual(calculate_risk_adjusted_value(0.2, 40), 0.12)

    def test_classify_strong_value(self):
        self.assertEqual(classify_value_opportunity(0.08, 0.14, 40, 70), "strong_value")

    def test_classify_positive_value(self):
        self.assertEqual(classify_value_opportunity(0.03, 0.04, 65, 70), "positive_value")

    def test_classify_no_value(self):
        self.assertEqual(classify_value_opportunity(-0.04, -0.05, 40, 70), "no_value")

    def test_classify_no_real_odds(self):
        self.assertEqual(classify_value_opportunity(None, None, 40, 70), "no_real_odds")

    def test_classify_insufficient_data(self):
        self.assertEqual(classify_value_opportunity(0.03, 0.04, 40, 10), "insufficient_data")

    def test_value_bet_engine_uses_calibrated_probability_first(self):
        item = prediction("value-calib", 70, 20, 10)
        item["calibrated_probabilities_json"] = {"home": 60, "draw": 25, "away": 15}
        result = evaluate_value_bet(item, {"market": "1X2", "selection": "HOME_WIN", "odds_decimal": 2.0, "source_type": "provider"})
        self.assertEqual(result["used_probability"], 0.6)
        self.assertEqual(result["fair_odds"], 1.6667)

    def test_value_bet_engine_flags_stale_odds(self):
        result = evaluate_value_bet(
            prediction("value-stale", 65, 20, 15),
            {"market": "1X2", "selection": "HOME_WIN", "odds_decimal": 2.1, "source_type": "provider", "stale": True},
        )
        self.assertTrue(result["is_stale_odds"])
        self.assertTrue(result["warnings"])

    def test_value_bet_engine_does_not_use_simulated_odds(self):
        result = evaluate_value_bet(prediction("value-no-odds", 65, 20, 15), None)
        self.assertEqual(result["value_status"], "no_real_odds")
        self.assertIsNone(result["expected_value"])

    def test_no_false_value_when_risk_high(self):
        item = prediction("value-risk", 70, 20, 10)
        item["risk_score"] = 90
        result = evaluate_value_bet(item, {"market": "1X2", "selection": "HOME_WIN", "odds_decimal": 2.2, "source_type": "provider"})
        self.assertEqual(result["opportunity_level"], "avoid")

    def test_no_random_odds_generation(self):
        odds_source = Path(__file__).parents[1] / "services" / "odds_provider.py"
        source = odds_source.read_text(encoding="utf-8")
        self.assertNotIn("random" + ".uniform", source)
        self.assertNotIn("random" + ".random", source)
        self.assertNotIn("Math" + ".random", source)

    def test_manual_user_input_odds_is_marked_manual(self):
        self.use_sqlite_registry()
        saved = repository.save_real_bookmaker_odds(
            {
                "match_id": "manual-match",
                "bookmaker": "Saisie utilisateur",
                "market": "1X2",
                "selection": "DRAW",
                "odds_decimal": 3.1,
                "provider": "manual_user_input",
                "source": "manual_user_input",
            }
        )
        self.assertEqual(saved["source_type"], "manual_user_input")

    def test_reference_odds_selection(self):
        selected = select_reference_odds(
            [
                {"bookmaker": "a", "odds_decimal": 1.9},
                {"bookmaker": "b", "odds_decimal": 2.1},
            ]
        )
        self.assertEqual(selected["bookmaker"], "b")
        self.assertEqual(selected["implied_probability"], 0.4762)

    def test_assistant_recommendation_recommended(self):
        result = analyze_prediction(
            prediction("assistant-rec", 65, 20, 15),
            {"odds_lookup": {"assistant-rec": [{"market": "1X2", "selection": "HOME_WIN", "odds_decimal": 2.2}]}, "calibration_status": "mostly_calibrated"},
        )
        self.assertEqual(result["value_status"], "strong_value")
        self.assertIn(result["recommendation_type"], {"recommended", "cautious"})

    def test_assistant_recommendation_cautious(self):
        item = prediction("assistant-cautious", 62, 23, 15)
        item["risk_score"] = 75
        result = analyze_prediction(
            item,
            {"odds_lookup": {"assistant-cautious": [{"market": "1X2", "selection": "HOME_WIN", "odds_decimal": 2.15}]}, "calibration_status": "overconfident"},
        )
        self.assertEqual(result["recommendation_type"], "cautious")
        self.assertIn(result["risk_level"], {"high", "very_high"})

    def test_assistant_recommendation_avoid(self):
        result = analyze_prediction(
            prediction("assistant-avoid", 45, 30, 25),
            {"odds_lookup": {"assistant-avoid": [{"market": "1X2", "selection": "HOME_WIN", "odds_decimal": 1.5}]}, "calibration_status": "mostly_calibrated"},
        )
        self.assertEqual(result["recommendation_type"], "avoid")

    def test_assistant_handles_missing_odds(self):
        result = analyze_prediction(prediction("assistant-no-odds", 70, 20, 10), {})
        self.assertEqual(result["value_status"], "no_real_odds")
        self.assertEqual(result["recommendation_label"], "Cote réelle non disponible")

    def test_assistant_handles_missing_calibration(self):
        result = analyze_prediction(
            prediction("assistant-no-calib", 60, 25, 15),
            {"odds_lookup": {"assistant-no-calib": [{"market": "1X2", "selection": "HOME_WIN", "odds_decimal": 2.0}]}}
        )
        self.assertIsNone(result["calibrated_probability"])
        self.assertIsNotNone(result["expected_value"])

    def test_assistant_predictions_endpoint(self):
        with patch.object(main, "_available_predictions", return_value=[prediction("assistant-endpoint", 65, 20, 15)]), patch.object(main, "_odds_lookup_for_predictions", return_value={"assistant-endpoint": [{"market": "1X2", "selection": "HOME_WIN", "odds_decimal": 2.1}]}):
            report = main.assistant_predictions(limit=10)

        self.assertEqual(report["status"], "ok")
        self.assertEqual(report["items_count"], 1)
        self.assertIn("expected_value", report["items"][0])

    def test_betting_assistant_includes_opportunity_score(self):
        result = analyze_prediction(
            prediction("assistant-opportunity", 65, 20, 15),
            {"odds_lookup": {"assistant-opportunity": [{"market": "1X2", "selection": "HOME_WIN", "odds_decimal": 2.1, "source_type": "provider"}]}},
        )
        self.assertIn("opportunity_score", result)
        self.assertIn("fair_odds", result)

    def test_value_bets_endpoint(self):
        with patch.object(main, "_available_predictions", return_value=[prediction("value-endpoint", 65, 20, 15)]), patch.object(main, "_odds_lookup_for_predictions", return_value={"value-endpoint": [{"market": "1X2", "selection": "HOME_WIN", "odds_decimal": 2.1, "source_type": "provider"}]}):
            report = main.value_bets(limit=10)
        self.assertEqual(report["status"], "ok")
        self.assertIn("summary", report)

    def test_match_value_bets_endpoint(self):
        match = {"id": "value-match", "match_id": "value-match", "home_team": "PSG", "away_team": "Lyon"}
        with patch.object(main, "_find_match", return_value=match), patch.object(main, "_available_predictions", return_value=[prediction("value-match", 65, 20, 15)]), patch.object(main, "_odds_lookup_for_predictions", return_value={"value-match": [{"market": "1X2", "selection": "HOME_WIN", "odds_decimal": 2.1, "source_type": "provider"}]}), patch.object(main.repository, "list_match_real_odds", return_value=[{"odds_decimal": 2.1}]):
            report = main.match_value_bets("value-match")
        self.assertEqual(report["status"], "ok")
        self.assertIn("best_value", report)

    def test_assistant_match_endpoint(self):
        match = {"id": "assistant-match", "match_id": "assistant-match", "home_team": "PSG", "away_team": "Lyon"}
        with patch.object(main, "_find_match", return_value=match), patch.object(main, "_available_predictions", return_value=[prediction("assistant-match", 65, 20, 15)]), patch.object(main, "_odds_lookup_for_predictions", return_value={"assistant-match": [{"market": "1X2", "selection": "HOME_WIN", "odds_decimal": 2.0}]}):
            report = main.assistant_match("assistant-match")

        self.assertEqual(report["status"], "ok")
        self.assertEqual(report["match_id"], "assistant-match")
        self.assertIsNotNone(report["primary_recommendation"])

    def test_assistant_daily_brief_endpoint(self):
        with patch.object(main, "_available_predictions", return_value=[prediction("assistant-brief", 65, 20, 15)]), patch.object(main, "_odds_lookup_for_predictions", return_value={"assistant-brief": [{"market": "1X2", "selection": "HOME_WIN", "odds_decimal": 2.0}]}):
            report = main.assistant_daily_brief(limit=10)

        self.assertEqual(report["status"], "ok")
        self.assertIn("summary", report)

    def test_assistant_never_promises_gain(self):
        result = analyze_prediction(
            prediction("assistant-safe", 65, 20, 15),
            {"odds_lookup": {"assistant-safe": [{"market": "1X2", "selection": "HOME_WIN", "odds_decimal": 2.0}]}, "calibration_status": "mostly_calibrated"},
        )
        rendered_text = " ".join(str(value).lower() for value in result.values() if isinstance(value, str))
        for forbidden in ["pari " + "sûr", "gain " + "gar" + "anti", "100% " + "sûr", "100 % " + "sûr", "sans " + "risque"]:
            self.assertNotIn(forbidden, rendered_text)
        self.assertEqual(result["promise_check"], "ok")

    def test_create_user_bet(self):
        self.use_sqlite_registry()
        repository.save_real_bookmaker_odds(
            {"match_id": "bet-match", "bookmaker": "RealBook", "market": "1X2", "selection": "HOME_WIN", "odds_decimal": 2.0, "provider": "real-provider", "source": "real_provider"}
        )
        bet = repository.create_user_bet(
            "u1",
            {"match_id": "bet-match", "market": "1X2", "selection": "HOME_WIN", "odds_decimal": 2.0, "odds_source": "provider", "stake": 10},
        )
        self.assertEqual(bet["odds_source"], "provider")
        self.assertEqual(bet["status"], "pending")

    def test_create_user_bet_requires_valid_odds(self):
        self.use_sqlite_registry()
        with self.assertRaises(ValueError):
            repository.create_user_bet("u1", {"match_id": "missing", "market": "1X2", "selection": "HOME_WIN", "odds_decimal": 2.0, "odds_source": "provider", "stake": 10})

    def test_create_user_bet_requires_positive_stake(self):
        self.use_sqlite_registry()
        with self.assertRaises(ValueError):
            repository.create_user_bet("u1", {"match_id": "m1", "market": "1X2", "selection": "HOME_WIN", "odds_decimal": 2.0, "odds_source": "manual_user_input", "stake": 0})

    def test_user_bets_are_user_scoped(self):
        self.use_sqlite_registry()
        bet = repository.create_user_bet("u1", {"match_id": "m1", "market": "1X2", "selection": "HOME_WIN", "odds_decimal": 2.0, "odds_source": "manual_user_input", "stake": 10})
        self.assertIsNone(repository.get_user_bet("u2", bet["id"]))

    def test_settle_user_bet_won_and_lost(self):
        self.use_sqlite_registry()
        won = repository.create_user_bet("u1", {"match_id": "m1", "market": "1X2", "selection": "HOME_WIN", "odds_decimal": 2.5, "odds_source": "manual_user_input", "stake": 10})
        lost = repository.create_user_bet("u1", {"match_id": "m2", "market": "1X2", "selection": "AWAY_WIN", "odds_decimal": 2.0, "odds_source": "manual_user_input", "stake": 8})
        self.assertEqual(repository.settle_user_bet("u1", won["id"], "won")["result_profit"], 15)
        self.assertEqual(repository.settle_user_bet("u1", lost["id"], "lost")["result_profit"], -8)

    def test_user_bet_summary_roi_and_no_false_zero(self):
        self.use_sqlite_registry()
        pending = repository.create_user_bet("u1", {"match_id": "m0", "market": "1X2", "selection": "DRAW", "odds_decimal": 3.0, "odds_source": "manual_user_input", "stake": 5})
        self.assertIsNone(repository.compute_user_betting_summary("u1")["roi"])
        repository.settle_user_bet("u1", pending["id"], "won")
        self.assertGreater(repository.compute_user_betting_summary("u1")["roi"], 0)

    def test_user_learning_detects_market_strength_and_risky_patterns(self):
        bets = [
            {"market": "1X2", "status": "won", "stake": 10, "result_profit": 12, "odds_decimal": 2.2, "expected_value": 0.1},
            {"market": "1X2", "status": "won", "stake": 10, "result_profit": 8, "odds_decimal": 1.8, "expected_value": 0.05},
            {"market": "Longshot", "status": "lost", "stake": 10, "result_profit": -10, "odds_decimal": 4.0, "expected_value": -0.1},
            {"market": "Longshot", "status": "lost", "stake": 10, "result_profit": -10, "odds_decimal": 3.5, "expected_value": -0.2},
            {"market": "Longshot", "status": "lost", "stake": 10, "result_profit": -10, "odds_decimal": 3.2, "expected_value": -0.05},
        ]
        self.assertTrue(detect_user_strengths("u1", bets))
        self.assertTrue(detect_risky_patterns("u1", bets))

    def test_default_user_plan_is_free(self):
        self.use_sqlite_registry()

        subscription = repository.get_user_subscription("billing-u1")

        self.assertEqual(subscription["plan"], "free")
        self.assertEqual(subscription["status"], "free")

    def test_upsert_user_subscription_and_get_user_plan(self):
        self.use_sqlite_registry()

        subscription = repository.upsert_user_subscription("billing-u1", plan="premium", status="active", stripe_customer_id="cus_123")

        self.assertEqual(subscription["plan"], "premium")
        self.assertEqual(repository.get_user_plan("billing-u1"), "premium")
        self.assertTrue(repository.is_user_premium("billing-u1"))

    def test_usage_limit_free_predictions(self):
        self.use_sqlite_registry()

        for _ in range(5):
            repository.record_usage_event("usage-u1", "prediction_view")

        limit = repository.check_usage_limit("usage-u1", "prediction_view")
        self.assertFalse(limit["allowed"])
        self.assertEqual(limit["plan"], "free")
        self.assertEqual(limit["limit"], 5)

    def test_record_usage_event(self):
        self.use_sqlite_registry()

        repository.record_usage_event("usage-u2", "assistant_request", metadata={"source": "test"})

        self.assertEqual(repository.get_usage_count("usage-u2", "assistant_request"), 1)

    def test_billing_status_without_stripe_config(self):
        with patch.dict("os.environ", {"STRIPE_SECRET_KEY": "", "APP_BASE_URL": ""}, clear=False):
            report = main.billing_status()

        self.assertEqual(report["status"], "ok")
        self.assertFalse(report["billing_configured"])

    def test_create_checkout_session_requires_stripe_config(self):
        with patch.dict("os.environ", {"STRIPE_SECRET_KEY": "", "APP_BASE_URL": ""}, clear=False):
            report = create_checkout_session("billing-u1", "premium", "monthly")

        self.assertEqual(report["status"], "billing_not_configured")

    def test_map_price_to_plan(self):
        with patch.dict("os.environ", {"STRIPE_PRICE_PREMIUM_MONTHLY": "price_premium", "STRIPE_PRICE_PRO_MONTHLY": "price_pro"}, clear=False):
            self.assertEqual(map_price_to_plan("price_premium"), "premium")
            self.assertEqual(map_price_to_plan("price_pro"), "pro")

    def test_webhook_subscription_updated_and_deleted(self):
        self.use_sqlite_registry()
        event = {
            "type": "customer.subscription.updated",
            "data": {
                "object": {
                    "id": "sub_123",
                    "customer": "cus_123",
                    "status": "active",
                    "metadata": {"user_id": "billing-u3", "plan": "pro"},
                    "items": {"data": [{"price": {"id": "price_pro"}}]},
                    "current_period_start": 1760000000,
                    "current_period_end": 1762600000,
                }
            },
        }

        updated = sync_subscription_from_stripe(event)
        deleted = sync_subscription_from_stripe({**event, "type": "customer.subscription.deleted"})

        self.assertEqual(updated["subscription"]["plan"], "pro")
        self.assertEqual(deleted["subscription"]["plan"], "free")

    def test_subscription_user_scoping(self):
        self.use_sqlite_registry()
        repository.upsert_user_subscription("billing-u4", plan="premium", status="active")

        self.assertEqual(repository.get_user_plan("billing-u4"), "premium")
        self.assertEqual(repository.get_user_plan("billing-u5"), "free")


if __name__ == "__main__":
    unittest.main()
