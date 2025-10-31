"""Filesystem-backed persistence helpers for pipeline job metadata."""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Mapping, TYPE_CHECKING

from .. import logging_manager

if TYPE_CHECKING:  # pragma: no cover - for static analysis only
    from modules.services.job_manager import PipelineJobMetadata

_LOGGER = logging_manager.get_logger().getChild("jobs.persistence")
_STORAGE_ENV_VAR = "JOB_STORAGE_DIR"
_DEFAULT_STORAGE_RELATIVE = Path("storage")


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


def _job_root(job_id: str) -> Path:
    return _resolve_storage_dir() / _sanitize_job_id(job_id)


def _job_metadata_dir(job_id: str) -> Path:
    metadata_dir = _job_root(job_id) / "metadata"
    metadata_dir.mkdir(parents=True, exist_ok=True)
    return metadata_dir


def _job_path(job_id: str) -> Path:
    return _job_metadata_dir(job_id) / "job.json"


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
    for job_dir in sorted(storage_dir.iterdir()):
        if not job_dir.is_dir():
            continue
        job_id = job_dir.name
        metadata_file = job_dir / "metadata" / "job.json"
        if not metadata_file.exists():
            continue
        try:
            records[job_id] = load_job(job_id)
        except Exception as exc:  # pragma: no cover - defensive logging
            _LOGGER.warning(
                "Failed to load job metadata",
                extra={"job_id": job_id, "error": str(exc)},
            )
    return records


def delete_job(job_id: str) -> None:
    """Remove persisted metadata and any stored artifacts for ``job_id``."""

    metadata_path = _job_path(job_id)
    job_root = _job_root(job_id)

    try:
        metadata_path.unlink()
    except FileNotFoundError:
        pass
    else:
        _LOGGER.debug("Job %s metadata removed from %s", job_id, metadata_path)

    try:
        shutil.rmtree(job_root)
    except FileNotFoundError:
        return
    except OSError:
        _LOGGER.debug("Unable to remove job directory %s", job_root, exc_info=True)
    else:
        _LOGGER.debug("Job %s directory %s removed", job_id, job_root)
