import unittest
from unittest.mock import patch

from sqlalchemy import create_engine

import main
from data import database, repository


def _prediction(match_id="m1"):
    return {
        "id": match_id,
        "match_id": match_id,
        "slug": match_id,
        "model_version": main.MODEL_VERSION,
        "home_team": "Home",
        "away_team": "Away",
        "probabilities": {"home": 50, "draw": 25, "away": 25},
        "goals": {"expected_home": 1.4, "expected_away": 0.8, "over_2_5": 52, "btts": 47},
        "confidence": {"score": 60, "status": "MOYEN"},
        "features": {},
        "flags": {"risk": False, "trap_match": False},
    }


class PredictionPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", future=True)
        database.metadata.create_all(self.engine)
        self.patches = [
            patch.object(database, "get_engine", return_value=self.engine),
            patch.object(repository, "get_engine", return_value=self.engine),
        ]
        for item in self.patches:
            item.start()

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        self.engine.dispose()

    def test_save_predictions_inserts_valid_prediction(self):
        report = repository.save_predictions([_prediction("m1")])

        self.assertEqual(report["saved_count"], 1)
        self.assertEqual(report["failed_count"], 0)
        self.assertEqual(repository.count_predictions(), 1)

    def test_get_predictions_reads_saved_prediction(self):
        repository.save_predictions([_prediction("m1")])

        rows = repository.get_predictions()

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["id"], "m1")
        self.assertEqual(rows[0]["match_id"], "m1")
        self.assertEqual(rows[0]["slug"], "m1")
        self.assertEqual(rows[0]["model_version"], main.MODEL_VERSION)

    def test_save_refresh_log_writes_line(self):
        report = repository.save_refresh_log(
            "football-data.org",
            "postgresql",
            10,
            2,
            predictions_generated=10,
            predictions_saved=10,
            predictions_failed=0,
        )

        self.assertTrue(report["saved"])
        latest = repository.get_latest_refresh_log()
        self.assertEqual(latest["predictions_generated"], 10)
        self.assertEqual(latest["predictions_saved"], 10)

    def test_refresh_reports_predictions_saved_when_postgresql_available(self):
        with patch.object(main, "_require_refresh_configuration", return_value=None), patch.object(
            main.repository, "save_matches", return_value=True
        ), patch.object(main.repository, "save_teams", return_value=True), patch.object(
            main.repository, "save_predictions", return_value={"saved_count": 2, "failed_count": 0, "errors": []}
        ), patch.object(main.repository, "save_refresh_log", return_value={"saved": True, "error": None}), patch.object(
            main.repository, "save_prediction_snapshots", return_value=2
        ):
            result = main.run_refresh_data_job(None)

        self.assertGreater(result["predictions_generated"], 0)
        self.assertEqual(result["predictions_saved"], 2)
        self.assertEqual(result["predictions_failed"], 0)

    def test_feature_store_generates_predictions_when_table_empty(self):
        match = {
            "id": "m1",
            "match_id": "m1",
            "slug": "m1",
            "home_team": "Home",
            "away_team": "Away",
            "status": "FINISHED",
            "score_full_time_home": 2,
            "score_full_time_away": 1,
        }

        with patch.object(main, "_available_matches", return_value=[match]), patch.object(
            main.repository, "get_predictions", return_value=[]
        ), patch.object(main.repository, "get_feature_snapshot_keys", return_value=set()), patch.object(
            main.repository, "save_feature_snapshots", side_effect=lambda items: len(items)
        ), patch.object(main.repository, "get_matches", return_value=[match]), patch.object(
            main, "_refresh_status", return_value={"storage": "postgresql"}
        ):
            result = main.run_build_feature_store_job(None)

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["predictions_source"], "generated_on_the_fly")
        self.assertEqual(result["feature_snapshots_built"], 1)
        self.assertEqual(result["feature_snapshots_saved"], 1)

    def test_debug_predictions_structure_detects_empty_table_with_generatable_predictions(self):
        match = {
            "id": "m1",
            "match_id": "m1",
            "slug": "m1",
            "home_team": "Home",
            "away_team": "Away",
            "status": "FINISHED",
            "score_full_time_home": 1,
            "score_full_time_away": 0,
        }

        with patch.object(main.repository, "get_predictions", return_value=[]), patch.object(
            main.repository, "count_predictions", return_value=0
        ), patch.object(main.repository, "sample_prediction_db", return_value=None), patch.object(
            main.repository, "get_latest_refresh_log", return_value=None
        ), patch.object(main, "_available_matches", return_value=[match]):
            report = main.debug_predictions_structure()

        self.assertEqual(report["predictions_table_count"], 0)
        self.assertEqual(report["generated_predictions_count"], 1)
        self.assertTrue(report["warning"])


if __name__ == "__main__":
    unittest.main()
