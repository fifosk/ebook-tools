"""Filesystem-backed persistence helpers for pipeline job metadata."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Dict, Mapping, TYPE_CHECKING

from .. import logging_manager

if TYPE_CHECKING:  # pragma: no cover - for static analysis only
    from modules.services.job_manager import PipelineJobMetadata

_LOGGER = logging_manager.get_logger().getChild("jobs.persistence")
_STORAGE_ENV_VAR = "JOB_STORAGE_DIR"
_DEFAULT_STORAGE_RELATIVE = Path("storage") / "jobs"


def _resolve_storage_dir() -> Path:
    """Return the directory where job metadata should be stored."""

    override = os.environ.get(_STORAGE_ENV_VAR)
    if override:
        candidate = Path(override)
    else:
        candidate = _DEFAULT_STORAGE_RELATIVE
    if not candidate.is_absolute():
        candidate = Path.cwd() / candidate
    candidate.mkdir(parents=True, exist_ok=True)
    return candidate


def _sanitize_job_id(job_id: str) -> str:
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_")
    return "".join(ch if ch in allowed else "_" for ch in job_id)


def _job_path(job_id: str) -> Path:
    return _resolve_storage_dir() / f"{_sanitize_job_id(job_id)}.json"


def _coerce_metadata(job: "PipelineJobMetadata" | Mapping[str, object]) -> "PipelineJobMetadata":
    from modules.services.job_manager import PipelineJobMetadata

    if isinstance(job, PipelineJobMetadata):
        return job
    if isinstance(job, Mapping):
        return PipelineJobMetadata.from_dict(dict(job))
    raise TypeError(f"Unsupported job payload type: {type(job)!r}")


def save_job(job: "PipelineJobMetadata" | Mapping[str, object]) -> Path:
    """Persist ``job`` metadata to disk using an atomic write."""

    metadata = _coerce_metadata(job)
    path = _job_path(metadata.job_id)
    payload = metadata.to_json()
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=path.parent, delete=False
        ) as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
            temp_path = Path(handle.name)
        if temp_path is None:  # pragma: no cover - defensive safeguard
            raise RuntimeError("Temporary job metadata path was not created")
        os.replace(temp_path, path)
    except Exception:
        if temp_path is not None:
            try:
                temp_path.unlink()
            except OSError:
                pass
        raise
    else:
        _LOGGER.debug("Job %s persisted to %s", metadata.job_id, path)
        return path


def load_job(job_id: str) -> "PipelineJobMetadata":
    """Load metadata for ``job_id`` from disk."""

    path = _job_path(job_id)
    with path.open("r", encoding="utf-8") as handle:
        payload = handle.read()
    from modules.services.job_manager import PipelineJobMetadata

    return PipelineJobMetadata.from_json(payload)


def load_all_jobs() -> Dict[str, "PipelineJobMetadata"]:
    """Return all persisted job metadata keyed by job identifier."""

    storage_dir = _resolve_storage_dir()
    records: Dict[str, "PipelineJobMetadata"] = {}
    for entry in sorted(storage_dir.glob("*.json")):
        job_id = entry.stem
        try:
            records[job_id] = load_job(job_id)
        except Exception as exc:  # pragma: no cover - defensive logging
            _LOGGER.warning(
                "Failed to load job metadata", extra={"job_id": job_id, "error": str(exc)}
            )
    return records


def delete_job(job_id: str) -> None:
    """Remove persisted metadata for ``job_id`` if it exists."""

    path = _job_path(job_id)
    try:
        path.unlink()
    except FileNotFoundError:  # pragma: no cover - idempotent delete
        return
    else:
        _LOGGER.debug("Job %s removed from persistence", job_id)

