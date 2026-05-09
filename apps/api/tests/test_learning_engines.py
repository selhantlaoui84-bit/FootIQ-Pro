import unittest
from pathlib import Path
from unittest.mock import patch

from services.calibration_engine import build_calibration_profile, calibrate_prediction
from services.feedback_engine import build_feedback_report
from services.ml_training import prepare_training_rows
from services.model_governance import build_model_governance_report
from services.model_versioning import record_model_version, list_model_versions


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


class LearningEngineTests(unittest.TestCase):
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
        self.assertIn("Critères stricts de promotion non satisfaits.", report["promotion_readiness"]["blocking_reasons"])

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
