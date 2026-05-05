from datetime import datetime, timedelta, timezone
import unittest

from data import runtime_store


class RuntimeStoreJobTests(unittest.TestCase):
    def test_running_refresh_job_over_15_minutes_becomes_failed_timeout(self):
        job_id = "stale-refresh-test"
        job = runtime_store.start_refresh_job(job_id)
        job["started_at"] = (datetime.now(timezone.utc) - timedelta(minutes=16)).isoformat()

        status = runtime_store.get_refresh_job(job_id)

        self.assertEqual(status["status"], "failed_timeout")
        self.assertIn("timeout", status["error"])

    def test_running_feature_store_job_over_15_minutes_becomes_failed_timeout(self):
        job_id = "stale-feature-test"
        job = runtime_store.start_feature_store_job(job_id)
        job["started_at"] = (datetime.now(timezone.utc) - timedelta(minutes=16)).isoformat()

        status = runtime_store.get_feature_store_job(job_id)

        self.assertEqual(status["status"], "failed_timeout")
        self.assertIn("timeout", status["error"])


if __name__ == "__main__":
    unittest.main()
