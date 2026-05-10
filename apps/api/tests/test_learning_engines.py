import unittest
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
from services.model_governance import build_model_governance_report
from services.model_versioning import get_versions_report, record_model_version, list_model_versions


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


if __name__ == "__main__":
    unittest.main()
