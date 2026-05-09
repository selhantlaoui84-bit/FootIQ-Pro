from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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
) -> dict[str, Any]:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    registry = _load_registry()
    row = {
        "id": f"{model_version}:{trained_at or _now_iso()}",
        "model_version": model_version,
        "feature_set_version": feature_set_version,
        "calibration_version": calibration_version,
        "trained_at": trained_at or _now_iso(),
        "created_at": _now_iso(),
        "rows_used": int(rows_used or 0),
        "metrics": metrics or {},
        "status": status,
        "family": family,
        "artifact_path": artifact_path,
    }
    registry.append(row)
    REGISTRY_PATH.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")
    return row


def latest_model_version(status: str | None = None) -> dict[str, Any] | None:
    versions = list_model_versions()
    if status:
        versions = [item for item in versions if item.get("status") == status]
    return versions[0] if versions else None
