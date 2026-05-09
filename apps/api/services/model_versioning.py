from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from data import repository

BASE_DIR = Path(__file__).resolve().parents[1]
MODEL_DIR = BASE_DIR / "ml_models"
REGISTRY_PATH = MODEL_DIR / "model_versions.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_registry() -> list[dict[str, Any]]:
    if not REGISTRY_PATH.exists():
        return []
    try:
        payload = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        return payload if isinstance(payload, list) else []
    except Exception:
        return []


def list_model_versions() -> list[dict[str, Any]]:
    try:
        repository.init_model_versions_schema()
        repository.import_model_versions_from_file_if_needed(REGISTRY_PATH)
        versions = repository.list_model_versions()
        if versions or repository.db_available():
            return versions
    except Exception:
        pass

    return sorted(_load_registry(), key=lambda item: str(item.get("trained_at") or item.get("created_at") or ""), reverse=True)


def record_model_version(
    *,
    model_version: str,
    feature_set_version: str | None,
    calibration_version: str | None,
    trained_at: str | None,
    rows_used: int,
    metrics: dict[str, Any] | None,
    status: str,
    family: str | None = None,
    artifact_path: str | None = None,
    features_used: int | list[str] | None = None,
    target_distribution: dict[str, Any] | None = None,
    governance: dict[str, Any] | None = None,
    roi_theoretical: float | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    row = {
        "id": f"{model_version}:{trained_at or _now_iso()}",
        "model_version": model_version,
        "model_type": family,
        "feature_set_version": feature_set_version,
        "calibration_version": calibration_version,
        "trained_at": trained_at or _now_iso(),
        "created_at": _now_iso(),
        "rows_used": int(rows_used or 0),
        "features_used": features_used or 0,
        "accuracy": (metrics or {}).get("accuracy"),
        "log_loss": (metrics or {}).get("log_loss"),
        "brier_score": (metrics or {}).get("brier_score") or (metrics or {}).get("brier_score_1x2"),
        "roi_theoretical": roi_theoretical or (metrics or {}).get("theoretical_roi"),
        "target_distribution": target_distribution or (metrics or {}).get("target_distribution") or {},
        "metrics": metrics or {},
        "governance": governance or {},
        "status": status,
        "family": family,
        "artifact_path": artifact_path,
        "notes": notes,
        "source": "postgresql",
    }
    try:
        repository.init_model_versions_schema()
        saved = repository.save_model_version(row)
        if saved:
            saved["storage"] = "postgresql"
            return saved
    except Exception:
        pass

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    registry = _load_registry()
    fallback_row = {**row, "storage": "file_fallback", "source": "file_fallback"}
    registry.append(fallback_row)
    REGISTRY_PATH.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")
    return fallback_row


def latest_model_version(status: str | None = None) -> dict[str, Any] | None:
    versions = list_model_versions()
    if status:
        versions = [item for item in versions if item.get("status") == status]
    return versions[0] if versions else None


def get_versions_report(limit: int = 100) -> dict[str, Any]:
    try:
        repository.init_model_versions_schema()
        import_report = repository.import_model_versions_from_file_if_needed(REGISTRY_PATH)
        versions = repository.list_model_versions(limit=limit)
        if versions or repository.db_available():
            return {
                "status": "ok",
                "storage": "postgresql",
                "versions_count": len(versions),
                "current_production_model": repository.get_current_production_model(),
                "latest_candidate_model": repository.get_latest_candidate_model(),
                "versions": versions,
                "import_report": import_report,
                "note": "Model versions are stored in PostgreSQL with read-only file import fallback.",
            }
    except Exception as exc:
        versions = sorted(_load_registry(), key=lambda item: str(item.get("trained_at") or item.get("created_at") or ""), reverse=True)
        return {
            "status": "error" if not versions else "ok",
            "storage": "file_fallback",
            "detail": str(exc),
            "fallback_used": True,
            "versions_count": len(versions),
            "current_production_model": next((item for item in versions if item.get("status") == "production"), None),
            "latest_candidate_model": next((item for item in versions if item.get("status") in {"candidate", "shadow"}), None),
            "versions": versions[:limit],
        }

    versions = sorted(_load_registry(), key=lambda item: str(item.get("trained_at") or item.get("created_at") or ""), reverse=True)
    return {
        "status": "ok",
        "storage": "file_fallback",
        "fallback_used": True,
        "versions_count": len(versions),
        "current_production_model": next((item for item in versions if item.get("status") == "production"), None),
        "latest_candidate_model": next((item for item in versions if item.get("status") in {"candidate", "shadow"}), None),
        "versions": versions[:limit],
        "note": "PostgreSQL unavailable; using read-only file fallback for model versions.",
    }


def import_model_versions_from_file_if_needed() -> dict[str, Any]:
    try:
        return repository.import_model_versions_from_file_if_needed(REGISTRY_PATH)
    except Exception as exc:
        return {"status": "error", "storage": "file_fallback", "detail": str(exc)}


def list_versions(limit: int = 100) -> list[dict[str, Any]]:
    return get_versions_report(limit=limit).get("versions", [])


def get_active_model() -> dict[str, Any] | None:
    return get_versions_report().get("current_production_model")


def get_candidate_models() -> list[dict[str, Any]]:
    return [item for item in list_model_versions() if item.get("status") in {"candidate", "shadow"}]


register_model_version = record_model_version
