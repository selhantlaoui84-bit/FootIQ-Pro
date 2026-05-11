from __future__ import annotations

from typing import Any, Callable

from data import repository


PIPELINE_STEPS = (
    "refresh_data",
    "build_feature_store",
    "train_candidate_model",
    "generate_shadow_predictions",
    "shadow_backtesting",
    "feedback",
    "calibration",
    "monitoring",
)


HandlerMap = dict[str, Callable[[], dict[str, Any]]]


def _status(value: dict[str, Any] | None) -> str:
    return str((value or {}).get("status") or "ok").lower()


def _job_payload(job: dict | None, result: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "job": job,
        "result": result or {},
    }


def run_pipeline_step(step: str, options: dict[str, Any] | None = None) -> dict[str, Any]:
    options = options or {}
    handlers: HandlerMap = options.get("handlers") or {}
    triggered_by = str(options.get("triggered_by") or "system")
    safe_step = str(step or "").strip()

    repository.init_pipeline_jobs_schema()
    job = repository.create_pipeline_job(safe_step, triggered_by=triggered_by)
    job_id = (job or {}).get("id")

    if safe_step not in PIPELINE_STEPS:
        result = {"status": "skipped", "detail": f"Unsupported pipeline step: {safe_step}"}
        if job_id:
            job = repository.mark_pipeline_job_skipped(job_id, result["detail"], result)
        return {"status": "skipped", "step": safe_step, **_job_payload(job, result)}

    handler = handlers.get(safe_step)
    if handler is None:
        result = {"status": "skipped", "detail": f"No handler configured for {safe_step}."}
        if job_id:
            job = repository.mark_pipeline_job_skipped(job_id, result["detail"], result)
        return {"status": "skipped", "step": safe_step, **_job_payload(job, result)}

    try:
        if job_id:
            repository.mark_pipeline_job_running(job_id)
        result = handler() or {"status": "ok"}
        if _status(result) in {"error", "failed"}:
            if job_id:
                job = repository.mark_pipeline_job_error(job_id, str(result.get("detail") or result.get("error") or "Pipeline step failed."), result)
            return {"status": "error", "step": safe_step, **_job_payload(job, result)}
        if _status(result) in {"skipped", "noop"}:
            if job_id:
                job = repository.mark_pipeline_job_skipped(job_id, str(result.get("detail") or result.get("reason") or "Pipeline step skipped."), result)
            return {"status": "skipped", "step": safe_step, **_job_payload(job, result)}
        if job_id:
            job = repository.mark_pipeline_job_success(job_id, result)
        return {"status": "success", "step": safe_step, **_job_payload(job, result)}
    except Exception as exc:
        result = {"status": "error", "detail": str(exc)}
        if job_id:
            job = repository.mark_pipeline_job_error(job_id, str(exc), result)
        return {"status": "error", "step": safe_step, **_job_payload(job, result)}


def run_steps(steps: list[str], handlers: HandlerMap, triggered_by: str = "system") -> dict[str, Any]:
    results = []
    for step in steps:
        outcome = run_pipeline_step(step, {"handlers": handlers, "triggered_by": triggered_by})
        results.append(outcome)
        if outcome.get("status") == "error":
            break
    return {
        "status": "error" if any(item.get("status") == "error" for item in results) else "ok",
        "steps": results,
    }


def run_hourly_data_pipeline(handlers: HandlerMap, triggered_by: str = "cron") -> dict[str, Any]:
    return run_steps(
        ["refresh_data", "build_feature_store", "generate_shadow_predictions", "shadow_backtesting", "monitoring"],
        handlers,
        triggered_by=triggered_by,
    )


def run_daily_learning_pipeline(handlers: HandlerMap, triggered_by: str = "cron") -> dict[str, Any]:
    return run_steps(["feedback", "calibration", "monitoring"], handlers, triggered_by=triggered_by)


def run_after_match_finished_pipeline(handlers: HandlerMap, triggered_by: str = "cron") -> dict[str, Any]:
    return run_steps(["refresh_data", "build_feature_store", "shadow_backtesting", "monitoring"], handlers, triggered_by=triggered_by)
