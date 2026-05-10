import unittest
from unittest.mock import patch

import main
from data.repository import normalize_match_for_storage
from services.feature_store import build_feature_snapshot
from services.football_data_client import normalize_match, normalize_team


def _prediction(match_id="m1"):
    return {
        "match_id": match_id,
        "model_version": "test-model",
        "features": {},
        "goals": {"expected_home": 1.4, "expected_away": 0.9, "over_2_5": 51, "btts": 48},
        "probabilities": {"home": 50, "draw": 25, "away": 25},
        "confidence": {"score": 62},
        "risk_score": 40,
        "trap_match_score": 20,
    }


class FinishedMatchImportTests(unittest.TestCase):
    def test_football_data_match_status_scores_and_winner_are_normalized(self):
        match = normalize_match(
            {
                "homeTeam": {"name": "Paris SG"},
                "awayTeam": {"name": "Lyon"},
                "utcDate": "2026-05-01T19:00:00Z",
                "status": "finished",
                "score": {
                    "winner": None,
                    "fullTime": {"home": 3, "away": 1},
                    "halfTime": {"home": 1, "away": 0},
                },
            },
            "Ligue 1",
        )

        self.assertEqual(match["status"], "FINISHED")
        self.assertEqual(match["raw_status"], "finished")
        self.assertEqual(match["score_full_time_home"], 3)
        self.assertEqual(match["score_full_time_away"], 1)
        self.assertEqual(match["score_half_time_home"], 1)
        self.assertEqual(match["score_half_time_away"], 0)
        self.assertEqual(match["winner"], "HOME_TEAM")
        self.assertIsNone(match["home_team_logo"])

    def test_team_import_preserves_crest_url(self):
        team = normalize_team(
            {
                "name": "Paris Saint-Germain FC",
                "shortName": "Paris SG",
                "tla": "PSG",
                "crest": "https://crests.football-data.org/524.svg",
            },
            "Ligue 1",
        )

        self.assertEqual(team["short_name"], "Paris SG")
        self.assertEqual(team["tla"], "PSG")
        self.assertEqual(team["crest_url"], "https://crests.football-data.org/524.svg")
        self.assertEqual(team["logo_url"], "https://crests.football-data.org/524.svg")

    def test_repository_normalization_maps_nested_score_and_uppercase_status(self):
        match = normalize_match_for_storage(
            {
                "id": "m1",
                "status": "finished",
                "score": {"fullTime": {"home": 0, "away": 0}, "halfTime": {"home": 0, "away": 0}},
            }
        )

        self.assertEqual(match["status"], "FINISHED")
        self.assertEqual(match["score_full_time_home"], 0)
        self.assertEqual(match["score_full_time_away"], 0)
        self.assertEqual(match["winner"], "DRAW")

    def test_finished_match_with_score_creates_training_target(self):
        match = {
            "id": "m1",
            "match_id": "m1",
            "home_team": "Home",
            "away_team": "Away",
            "status": "FINISHED",
            "score_full_time_home": 2,
            "score_full_time_away": 1,
        }

        snapshot = build_feature_snapshot(match, [match], _prediction("m1"))

        self.assertEqual(snapshot["target"]["result"], "home")
        self.assertEqual(snapshot["target"]["home_goals"], 2)
        self.assertEqual(snapshot["target"]["away_goals"], 1)

    def test_feature_store_warning_when_no_finished_match_with_score(self):
        with patch.object(main, "_available_matches", return_value=[{"id": "m1", "status": "TIMED"}]), patch.object(
            main, "_available_predictions", return_value=[_prediction("m1")]
        ), patch.object(main.repository, "get_feature_snapshot_keys", return_value=set()), patch.object(
            main.repository, "save_feature_snapshots", return_value=0
        ), patch.object(main.repository, "get_matches", return_value=[{"id": "m1", "status": "TIMED"}]), patch.object(
            main, "_refresh_status", return_value={"storage": "postgresql"}
        ):
            result = main.run_build_feature_store_job(None)

        self.assertEqual(result["status"], "warning")
        self.assertEqual(result["finished_with_scores"], 0)
        self.assertEqual(result["count_by_status"], {"TIMED": 1})
        self.assertEqual(
            result["reason_if_zero_snapshots"],
            "Aucun match terminé avec score disponible. Importez l’historique ou vérifiez les statuts football-data.org.",
        )

    def test_matches_structure_report_returns_count_by_status(self):
        report = main._matches_structure_report(
            [
                {
                    "id": "m1",
                    "competition": "Ligue 1",
                    "status": "finished",
                    "kickoff": "2026-05-01T19:00:00Z",
                    "score_full_time_home": 1,
                    "score_full_time_away": 1,
                },
                {"id": "m2", "competition": "Ligue 1", "status": "SCHEDULED"},
            ]
        )

        self.assertEqual(report["count_by_status"], {"FINISHED": 1, "SCHEDULED": 1})
        self.assertEqual(report["finished_matches"], 1)
        self.assertEqual(report["finished_with_scores"], 1)


if __name__ == "__main__":
    unittest.main()
