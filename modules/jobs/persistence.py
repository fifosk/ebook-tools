"""Filesystem-backed persistence helpers for pipeline job metadata."""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Mapping, TYPE_CHECKING

from .. import config_manager as cfg
from .. import logging_manager

if TYPE_CHECKING:  # pragma: no cover - for static analysis only
    from modules.services.job_manager import PipelineJobMetadata

_LOGGER = logging_manager.get_logger().getChild("jobs.persistence")
_STORAGE_ENV_VAR = "JOB_STORAGE_DIR"
_DEFAULT_STORAGE_RELATIVE = Path("storage")


def _candidate_storage_dirs() -> list[Path]:
    """Return ordered storage root candidates for read operations."""

    candidates: list[Path] = []
    seen: set[Path] = set()

    def _add(value: Path | str | None) -> None:
        if value in {None, ""}:
            return
        try:
            path = Path(value).expanduser()
        except Exception:
            return
        if not path.is_absolute():
            path = (Path.cwd() / path)
        try:
            path = path.resolve()
        except OSError:
            path = path
        if path in seen:
            return
        seen.add(path)
        candidates.append(path)

    override = os.environ.get(_STORAGE_ENV_VAR)
    if override:
        _add(override)
    configured = getattr(cfg.get_settings(), "job_storage_dir", None)
    if isinstance(configured, str) and configured.strip():
        _add(configured.strip())
    _add(_DEFAULT_STORAGE_RELATIVE)
    try:
        _add(cfg.SCRIPT_DIR.parent / "storage")
    except Exception:
        pass
    try:
        _add(cfg.SCRIPT_DIR / "storage")
    except Exception:
        pass

    return candidates


def _resolve_storage_dir() -> Path:
    """Return the directory where job metadata should be stored."""

    candidates = _candidate_storage_dirs()
    if not candidates:
        candidate = Path.cwd() / _DEFAULT_STORAGE_RELATIVE
    else:
        candidate = candidates[0]
    candidate.mkdir(parents=True, exist_ok=True)
    return candidate


def _sanitize_job_id(job_id: str) -> str:
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_")
    return "".join(ch if ch in allowed else "_" for ch in job_id)


def _job_root(job_id: str, root: Path | None = None) -> Path:
    base = root or _resolve_storage_dir()
    return base / _sanitize_job_id(job_id)


def _job_metadata_dir(job_id: str, root: Path | None = None) -> Path:
    metadata_dir = _job_root(job_id, root=root) / "metadata"
    metadata_dir.mkdir(parents=True, exist_ok=True)
    return metadata_dir


def _job_path(job_id: str, root: Path | None = None) -> Path:
    return _job_metadata_dir(job_id, root=root) / "job.json"


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

    payload = None
    for root in _candidate_storage_dirs():
        path = _job_path(job_id, root=root)
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8") as handle:
            payload = handle.read()
        break
    if payload is None:
        raise FileNotFoundError(f"No metadata found for job {job_id}")
    from modules.services.job_manager import PipelineJobMetadata

    return PipelineJobMetadata.from_json(payload)


def list_job_ids() -> list[str]:
    """Return all job identifiers without loading full metadata."""

    job_ids: list[str] = []
    seen: set[str] = set()
    for storage_dir in _candidate_storage_dirs():
        if not storage_dir.exists():
            continue
        for job_dir in sorted(storage_dir.iterdir()):
            if not job_dir.is_dir():
                continue
            job_id = job_dir.name
            if job_id in seen:
                continue
            metadata_file = job_dir / "metadata" / "job.json"
            if not metadata_file.exists():
                continue
            seen.add(job_id)
            job_ids.append(job_id)
    return job_ids


def count_jobs() -> int:
    """Return total number of stored jobs."""

    return len(list_job_ids())


def load_all_jobs(
    *,
    offset: int | None = None,
    limit: int | None = None,
) -> Dict[str, "PipelineJobMetadata"]:
    """Return persisted job metadata keyed by job identifier.

    Args:
        offset: Number of jobs to skip (for pagination).
        limit: Maximum number of jobs to return.

    Returns:
        Dict mapping job_id to metadata.
    """

    job_ids = list_job_ids()

    # Apply pagination to job_ids first (lazy loading)
    if offset is not None or limit is not None:
        start = offset or 0
        end = start + limit if limit is not None else None
        job_ids = job_ids[start:end]

    records: Dict[str, "PipelineJobMetadata"] = {}
    for job_id in job_ids:
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
