from datetime import datetime, timezone

JOB_STALE_SECONDS = 15 * 60

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
_refresh_lock = False
_feature_store_lock = False
_cron_status = {
    "hourly_refresh_last_run": None,
    "match_finished_check_last_run": None,
    "last_finished_match_ids": [],
}


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _parse_iso(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _duration_ms(started_at, finished_at=None):
    started = _parse_iso(started_at)
    finished = _parse_iso(finished_at) or datetime.now(timezone.utc)
    if not started:
        return None
    return round((finished - started).total_seconds() * 1000)


def _normalize_job(job):
    if not job:
        return job

    if job.get("status") == "running":
        age_ms = _duration_ms(job.get("started_at"))
        job["updated_at"] = job.get("updated_at") or job.get("started_at")
        job["duration_ms"] = age_ms

        if age_ms is not None and age_ms > JOB_STALE_SECONDS * 1000:
            job["status"] = "failed_timeout"
            job["finished_at"] = _now_iso()
            job["updated_at"] = job["finished_at"]
            job["duration_ms"] = _duration_ms(job.get("started_at"), job.get("finished_at"))
            job["error"] = "Job probablement bloqué: timeout après 15 minutes."

    return job


def acquire_refresh_lock():
    global _refresh_lock
    latest = get_latest_refresh_job()
    if latest.get("status") != "running":
        _refresh_lock = False
    if _refresh_lock:
        return False
    if latest.get("status") == "running":
        return False
    _refresh_lock = True
    return True


def release_refresh_lock():
    global _refresh_lock
    _refresh_lock = False


def acquire_feature_store_lock():
    global _feature_store_lock
    latest = get_latest_feature_store_job()
    if latest.get("status") != "running":
        _feature_store_lock = False
    if _feature_store_lock:
        return False
    if latest.get("status") == "running":
        return False
    _feature_store_lock = True
    return True


def release_feature_store_lock():
    global _feature_store_lock
    _feature_store_lock = False


def start_refresh_job(job_id):
    global _latest_refresh_job_id
    job = {
        "job_id": job_id,
        "status": "running",
        "started_at": _now_iso(),
        "updated_at": _now_iso(),
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
    fields.setdefault("updated_at", _now_iso())
    job.update(fields)
    return _normalize_job(job)


def finish_refresh_job(job_id, result):
    job = update_refresh_job(job_id)
    if not job:
        return None
    job["status"] = "success"
    job["finished_at"] = _now_iso()
    job["updated_at"] = job["finished_at"]
    job["result"] = result
    job["error"] = None
    job["duration_ms"] = result.get("refresh_duration_ms") if isinstance(result, dict) else _duration_ms(job.get("started_at"), job.get("finished_at"))
    release_refresh_lock()
    return job


def fail_refresh_job(job_id, error):
    job = update_refresh_job(job_id)
    if not job:
        return None
    job["status"] = "error"
    job["finished_at"] = _now_iso()
    job["updated_at"] = job["finished_at"]
    job["error"] = str(error)
    job["duration_ms"] = _duration_ms(job.get("started_at"), job.get("finished_at"))
    release_refresh_lock()
    return job


def get_refresh_job(job_id=None):
    if job_id:
        return _normalize_job(_refresh_jobs.get(job_id)) or {
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
    return _normalize_job(_refresh_jobs.get(_latest_refresh_job_id)) or get_refresh_job(_latest_refresh_job_id)


def get_refresh_job_status(job_id=None):
    return get_refresh_job(job_id)


def start_feature_store_job(job_id):
    global _latest_feature_store_job_id
    job = {
        "job_id": job_id,
        "status": "running",
        "started_at": _now_iso(),
        "updated_at": _now_iso(),
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
    fields.setdefault("updated_at", _now_iso())
    job.update(fields)
    return _normalize_job(job)


def finish_feature_store_job(job_id, result):
    job = update_feature_store_job(job_id)
    if not job:
        return None
    job["status"] = "success"
    job["finished_at"] = _now_iso()
    job["updated_at"] = job["finished_at"]
    job["result"] = result
    job["error"] = None
    job["duration_ms"] = result.get("duration_ms") if isinstance(result, dict) else _duration_ms(job.get("started_at"), job.get("finished_at"))
    release_feature_store_lock()
    return job


def fail_feature_store_job(job_id, error):
    job = update_feature_store_job(job_id)
    if not job:
        return None
    job["status"] = "error"
    job["finished_at"] = _now_iso()
    job["updated_at"] = job["finished_at"]
    job["error"] = str(error)
    job["duration_ms"] = _duration_ms(job.get("started_at"), job.get("finished_at"))
    release_feature_store_lock()
    return job


def get_feature_store_job(job_id=None):
    if job_id:
        return _normalize_job(_feature_store_jobs.get(job_id)) or {
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
    return _normalize_job(_feature_store_jobs.get(_latest_feature_store_job_id)) or get_feature_store_job(_latest_feature_store_job_id)


def get_feature_store_job_status(job_id=None):
    return get_feature_store_job(job_id)


def reset_stale_jobs():
    reset_count = 0
    for job in list(_refresh_jobs.values()) + list(_feature_store_jobs.values()):
        before = job.get("status")
        _normalize_job(job)
        if before == "running" and job.get("status") == "failed_timeout":
            reset_count += 1
    if get_latest_refresh_job().get("status") != "running":
        release_refresh_lock()
    if get_latest_feature_store_job().get("status") != "running":
        release_feature_store_lock()
    return {"status": "ok", "reset_count": reset_count}


def set_cron_run(name, result=None):
    key = f"{name}_last_run"
    _cron_status[key] = {
        "ran_at": _now_iso(),
        "result": result,
    }
    return _cron_status[key]


def get_cron_status():
    return dict(_cron_status)


def get_last_finished_match_ids():
    return set(_cron_status.get("last_finished_match_ids") or [])


def set_last_finished_match_ids(match_ids):
    _cron_status["last_finished_match_ids"] = sorted(match_ids)
