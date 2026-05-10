import unittest
import asyncio
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import create_engine, text

import main
from data import database, repository
from services.calibration_engine import build_calibration_profile, calibrate_prediction
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

        self.assertEqual(profile["calibration_version"], "calibration-buckets-v1")
        self.assertEqual(sum(calibrated["probabilities"].values()), 100)
        self.assertEqual(calibrated["calibration_version"], "calibration-buckets-v1")
        self.assertTrue(calibrated["calibration"]["applied"])

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


if __name__ == "__main__":
    unittest.main()
