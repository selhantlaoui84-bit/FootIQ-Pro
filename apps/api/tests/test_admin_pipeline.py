import unittest
from datetime import datetime, timezone
from unittest.mock import patch

import main
from data import runtime_store


class AdminPipelineTests(unittest.TestCase):
    def test_refresh_status_prefers_postgresql_when_repository_has_matches_and_log(self):
        with patch.object(main.repository, "get_latest_refresh_log", return_value={
            "source": "football-data.org",
            "storage": "postgresql",
            "last_refresh_at": datetime.now(timezone.utc).isoformat(),
        }), patch.object(main.repository, "get_matches", return_value=[{"id": "m1"}]), patch.object(
            main.repository, "get_teams", return_value=[{"id": "t1"}]
        ), patch.object(main.repository, "get_predictions", return_value=[{"id": "p1"}]):
            status = main._refresh_status()

        self.assertEqual(status["storage"], "postgresql")
        self.assertEqual(status["matches_imported"], 1)

    def test_workflow_imported_data_never_returns_refresh_data_next_step(self):
        with patch.object(main, "_refresh_status", return_value={
            "source": "football-data.org",
            "storage": "postgresql",
            "matches_imported": 1935,
            "teams_imported": 106,
            "predictions_imported": 1935,
            "last_refresh_at": "2026-05-05T10:00:00Z",
        }), patch.object(main.repository, "get_matches", return_value=[{
            "id": "m1",
            "status": "FINISHED",
            "score_full_time_home": 2,
            "score_full_time_away": 1,
        }]), patch.object(
            main, "_feature_summary", return_value={"snapshots_count": 0, "with_target_count": 0, "target_coverage": 0}
        ), patch.object(main, "_ml_status_compact", return_value={"status": "not_trained", "latest_candidate": {}}), patch.object(
            main, "_shadow_summary_compact", return_value={"shadow_predictions_count": 0, "disagreement_count": 0}
        ), patch.object(main, "calculate_shadow_backtest_report", return_value={"evaluated_matches": 0}):
            workflow = main._workflow_status_compact()

        self.assertTrue(workflow["refresh"]["data_imported"])
        self.assertEqual(workflow["next_step"], "build_feature_store")
        self.assertNotEqual(workflow["next_step"], "refresh_data")

    def test_workflow_imported_data_without_finished_scores_requests_history(self):
        with patch.object(main, "_refresh_status", return_value={
            "source": "football-data.org",
            "storage": "postgresql",
            "matches_imported": 1935,
            "teams_imported": 106,
            "predictions_imported": 1935,
            "last_refresh_at": "2026-05-05T10:00:00Z",
        }), patch.object(main.repository, "get_matches", return_value=[{"id": "m1", "status": "TIMED"}]), patch.object(
            main, "_feature_summary", return_value={"snapshots_count": 0, "with_target_count": 0, "target_coverage": 0}
        ), patch.object(main, "_ml_status_compact", return_value={"status": "not_trained", "latest_candidate": {}}), patch.object(
            main, "_shadow_summary_compact", return_value={"shadow_predictions_count": 0, "disagreement_count": 0}
        ), patch.object(main, "calculate_shadow_backtest_report", return_value={"evaluated_matches": 0}):
            workflow = main._workflow_status_compact()

        self.assertTrue(workflow["refresh"]["data_imported"])
        self.assertEqual(workflow["next_step"], "import_historical_results")
        self.assertNotEqual(workflow["next_step"], "refresh_data")

    def test_feature_store_zero_snapshots_returns_warning_and_postgresql_storage(self):
        with patch.object(main, "_available_matches", return_value=[{"id": "m1", "status": "SCHEDULED"}]), patch.object(
            main, "_available_predictions", return_value=[{"id": "p1", "match_id": "m1"}]
        ), patch.object(main.repository, "get_feature_snapshot_keys", return_value=set()), patch.object(
            main, "build_feature_snapshots", return_value=[]
        ), patch.object(main.repository, "save_feature_snapshots", return_value=0), patch.object(
            main.repository, "get_matches", return_value=[{"id": "m1"}]
        ), patch.object(main, "_refresh_status", return_value={"storage": "postgresql"}):
            result = main.run_build_feature_store_job(None)

        self.assertEqual(result["status"], "warning")
        self.assertEqual(result["storage"], "postgresql")
        self.assertEqual(result["feature_snapshots_built"], 0)
        self.assertTrue(result["reason_if_zero_snapshots"])

    def test_refresh_running_job_does_not_replace_stable_refresh_status(self):
        job = runtime_store.start_refresh_job("stable-refresh-test")
        job["status"] = "running"

        with patch.object(main, "_refresh_status", return_value={
            "source": "football-data.org",
            "storage": "postgresql",
            "matches_imported": 1935,
            "teams_imported": 106,
            "predictions_imported": 1935,
            "last_refresh_at": "2026-05-05T10:00:00Z",
        }):
            response = main.refresh_status()

        self.assertEqual(response["stable_refresh_status"]["storage"], "postgresql")
        self.assertEqual(response["current_job"]["status"], "running")


if __name__ == "__main__":
    unittest.main()
