import unittest
from unittest.mock import patch

import main
from services.feature_store import build_feature_snapshots_detailed


def _match(**overrides):
    base = {
        "id": "m1-id",
        "match_id": "m1",
        "slug": "home-away",
        "home_team": "Home",
        "away_team": "Away",
        "status": "FINISHED",
        "score_full_time_home": 2,
        "score_full_time_away": 1,
    }
    base.update(overrides)
    return base


def _prediction(**overrides):
    base = {
        "id": "p1",
        "match_id": "m1",
        "slug": "home-away",
        "model_version": main.MODEL_VERSION,
        "features": {},
        "goals": {"expected_home": 1.5, "expected_away": 0.8, "over_2_5": 54, "btts": 45},
        "probabilities": {"home": 55, "draw": 25, "away": 20},
        "confidence": {"score": 64},
        "risk_score": 35,
        "trap_match_score": 20,
    }
    base.update(overrides)
    return base


class FeatureStoreDiagnosticsTests(unittest.TestCase):
    def test_feature_store_snapshot_with_matching_match_id(self):
        match = _match()
        result = build_feature_snapshots_detailed([match], [_prediction(match_id="m1")])

        self.assertEqual(len(result["snapshots"]), 1)
        self.assertEqual(result["snapshots"][0]["target"]["result"], "home")
        self.assertEqual(result["first_trainable_candidate_sample"]["join_key"], "match_id")

    def test_feature_store_snapshot_with_matching_slug(self):
        match = _match(match_id="match-from-provider", id="provider-id", slug="home-away")
        prediction = _prediction(id="different-id", match_id="different-match", slug="home-away")

        result = build_feature_snapshots_detailed([match], [prediction])

        self.assertEqual(len(result["snapshots"]), 1)
        self.assertEqual(result["first_trainable_candidate_sample"]["join_key"], "slug")

    def test_feature_store_snapshot_with_generated_prediction_when_table_empty(self):
        match = _match()
        result = build_feature_snapshots_detailed(
            [match],
            [],
            prediction_factory=lambda item: _prediction(match_id=item["match_id"], slug=item["slug"]),
        )

        self.assertEqual(len(result["snapshots"]), 1)
        self.assertEqual(result["snapshots"][0]["prediction_source"], "generated_on_the_fly")

    def test_debug_feature_store_diagnostics_returns_counters(self):
        match = _match()
        prediction = _prediction()

        with patch.object(main, "_available_matches", return_value=[match]), patch.object(
            main.repository, "get_predictions", return_value=[prediction]
        ), patch.object(main.repository, "get_matches", return_value=[match]), patch.object(
            main, "_available_feature_snapshots", return_value=[]
        ):
            report = main.debug_feature_store_diagnostics()

        self.assertEqual(report["matches_total"], 1)
        self.assertEqual(report["finished_with_scores"], 1)
        self.assertEqual(report["join_on_match_id_count"], 1)
        self.assertEqual(report["trainable_candidates_count"], 1)
        self.assertIn("rejection_reasons_count", report)

    def test_finished_with_scores_and_zero_snapshots_returns_explicit_warning(self):
        match = _match()

        with patch.object(main, "_available_matches", return_value=[match]), patch.object(
            main.repository, "get_predictions", return_value=[_prediction()]
        ), patch.object(main.repository, "get_feature_snapshot_keys", return_value=set()), patch.object(
            main, "build_feature_snapshots_detailed", return_value={
                "snapshots": [],
                "rejection_reasons_count": {"missing_prediction": 1},
                "sample_rejected_matches": [{"match_id": "m1", "reason": "missing_prediction"}],
                "first_trainable_candidate_sample": None,
            }
        ), patch.object(main.repository, "save_feature_snapshots", return_value={"saved_count": 0, "failed_count": 0, "errors": []}), patch.object(
            main.repository, "get_matches", return_value=[match]
        ), patch.object(main, "_refresh_status", return_value={"storage": "postgresql"}):
            result = main.run_build_feature_store_job(None)

        self.assertEqual(result["status"], "warning")
        self.assertEqual(
            result["reason_if_zero_snapshots"],
            "Matchs terminés avec score disponibles mais aucun snapshot créé. Vérifiez la jointure match/prédiction ou la génération à la volée.",
        )
        self.assertEqual(result["rejection_reasons_count"]["missing_prediction"], 1)


if __name__ == "__main__":
    unittest.main()
