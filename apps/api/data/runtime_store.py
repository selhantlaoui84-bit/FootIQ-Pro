from datetime import datetime, timezone

_matches = []
_teams = []
_predictions = []
_feature_snapshots = []
_ml_shadow_predictions = []
_last_refresh_at = None
_source = "mock"
_storage = "memory"


def get_matches():
    return _matches


def set_matches(matches):
    global _last_refresh_at, _matches
    _matches = matches
    _last_refresh_at = datetime.now(timezone.utc).isoformat()


def get_teams():
    return _teams


def set_teams(teams):
    global _last_refresh_at, _teams
    _teams = teams
    _last_refresh_at = datetime.now(timezone.utc).isoformat()


def get_predictions():
    return _predictions


def set_predictions(predictions):
    global _last_refresh_at, _predictions
    _predictions = predictions
    _last_refresh_at = datetime.now(timezone.utc).isoformat()


def set_source(source: str):
    global _source
    _source = source


def set_storage(storage: str):
    global _storage
    _storage = storage


def get_refresh_status():
    return {
        "source": _source,
        "storage": _storage,
        "matches_imported": len(_matches),
        "teams_imported": len(_teams),
        "predictions_imported": len(_predictions),
        "last_refresh_at": _last_refresh_at,
    }



def get_feature_snapshots():
    return _feature_snapshots


def set_feature_snapshots(feature_snapshots):
    global _feature_snapshots, _last_refresh_at
    _feature_snapshots = feature_snapshots
    _last_refresh_at = datetime.now(timezone.utc).isoformat()


def get_ml_shadow_predictions():
    return _ml_shadow_predictions


def set_ml_shadow_predictions(predictions):
    global _ml_shadow_predictions, _last_refresh_at
    _ml_shadow_predictions = predictions
    _last_refresh_at = datetime.now(timezone.utc).isoformat()


_refresh_jobs = {}
_latest_refresh_job_id = None
_feature_store_jobs = {}
_latest_feature_store_job_id = None


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def start_refresh_job(job_id):
    global _latest_refresh_job_id
    job = {
        "job_id": job_id,
        "status": "running",
        "started_at": _now_iso(),
        "finished_at": None,
        "duration_ms": None,
        "result": None,
        "error": None,
    }
    _refresh_jobs[job_id] = job
    _latest_refresh_job_id = job_id
    return job


def update_refresh_job(job_id, **fields):
    if not job_id:
        return get_latest_refresh_job()
    job = _refresh_jobs.get(job_id) or start_refresh_job(job_id)
    job.update(fields)
    return job


def finish_refresh_job(job_id, result):
    job = update_refresh_job(job_id)
    if not job:
        return None
    job["status"] = "success"
    job["finished_at"] = _now_iso()
    job["result"] = result
    job["error"] = None
    job["duration_ms"] = result.get("refresh_duration_ms") if isinstance(result, dict) else None
    return job


def fail_refresh_job(job_id, error):
    job = update_refresh_job(job_id)
    if not job:
        return None
    job["status"] = "error"
    job["finished_at"] = _now_iso()
    job["error"] = str(error)
    return job


def get_refresh_job(job_id=None):
    if job_id:
        return _refresh_jobs.get(job_id) or {
            "job_id": job_id,
            "status": "idle",
            "started_at": None,
            "finished_at": None,
            "duration_ms": None,
            "result": None,
            "error": None,
        }
    return get_latest_refresh_job()


def get_latest_refresh_job():
    if not _latest_refresh_job_id:
        return {
            "job_id": None,
            "status": "idle",
            "started_at": None,
            "finished_at": None,
            "duration_ms": None,
            "result": None,
            "error": None,
        }
    return _refresh_jobs.get(_latest_refresh_job_id) or get_refresh_job(_latest_refresh_job_id)


def start_feature_store_job(job_id):
    global _latest_feature_store_job_id
    job = {
        "job_id": job_id,
        "status": "running",
        "started_at": _now_iso(),
        "finished_at": None,
        "duration_ms": None,
        "result": None,
        "error": None,
    }
    _feature_store_jobs[job_id] = job
    _latest_feature_store_job_id = job_id
    return job


def update_feature_store_job(job_id, **fields):
    if not job_id:
        return get_latest_feature_store_job()
    job = _feature_store_jobs.get(job_id) or start_feature_store_job(job_id)
    job.update(fields)
    return job


def finish_feature_store_job(job_id, result):
    job = update_feature_store_job(job_id)
    if not job:
        return None
    job["status"] = "success"
    job["finished_at"] = _now_iso()
    job["result"] = result
    job["error"] = None
    job["duration_ms"] = result.get("duration_ms") if isinstance(result, dict) else None
    return job


def fail_feature_store_job(job_id, error):
    job = update_feature_store_job(job_id)
    if not job:
        return None
    job["status"] = "error"
    job["finished_at"] = _now_iso()
    job["error"] = str(error)
    return job


def get_feature_store_job(job_id=None):
    if job_id:
        return _feature_store_jobs.get(job_id) or {
            "job_id": job_id,
            "status": "idle",
            "started_at": None,
            "finished_at": None,
            "duration_ms": None,
            "result": None,
            "error": None,
        }
    return get_latest_feature_store_job()


def get_latest_feature_store_job():
    if not _latest_feature_store_job_id:
        return {
            "job_id": None,
            "status": "idle",
            "started_at": None,
            "finished_at": None,
            "duration_ms": None,
            "result": None,
            "error": None,
        }
    return _feature_store_jobs.get(_latest_feature_store_job_id) or get_feature_store_job(_latest_feature_store_job_id)
