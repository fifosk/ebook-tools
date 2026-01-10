"""Shared helpers for media route handlers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import HTTPException, status

from ....services.file_locator import FileLocator
from ....library import LibraryRepository
from ....permissions import can_access, resolve_access_policy
from ...dependencies import RequestUserContext


def _resolve_job_path(job_root: Path, relative_path: str) -> Path:
    normalized = relative_path.replace("\\", "/").strip()
    if not normalized:
        raise ValueError("Empty path")
    candidate = Path(normalized)
    if candidate.is_absolute():
        resolved = candidate.resolve()
    else:
        resolved = (job_root / candidate).resolve()
    try:
        resolved.relative_to(job_root)
    except ValueError as exc:
        raise ValueError("Path escapes job root") from exc
    return resolved


def _resolve_job_root(
    *,
    job_id: str,
    locator: FileLocator,
    library_repository: LibraryRepository,
    request_user: RequestUserContext,
    job_manager: Any,
    permission: str = "view",
) -> Path:
    try:
        job_manager.get(
            job_id,
            user_id=request_user.user_id,
            user_role=request_user.user_role,
            permission=permission,
        )
    except KeyError:
        entry = library_repository.get_entry_by_id(job_id)
        if entry is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
        metadata_payload = entry.metadata.data if hasattr(entry.metadata, "data") else {}
        owner_id = entry.owner_id or metadata_payload.get("user_id") or metadata_payload.get("owner_id")
        if isinstance(owner_id, str):
            owner_id = owner_id.strip() or None
        policy = resolve_access_policy(metadata_payload.get("access"), default_visibility="public")
        if not can_access(
            policy,
            owner_id=owner_id,
            user_id=request_user.user_id,
            user_role=request_user.user_role,
            permission=permission,
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access media")
        job_root = Path(entry.library_path)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    else:
        pipeline_root = locator.resolve_path(job_id)
        probe = pipeline_root / "metadata" / "job.json"
        if probe.exists():
            job_root = pipeline_root
        else:
            entry = library_repository.get_entry_by_id(job_id)
            if entry is not None:
                candidate_root = Path(entry.library_path)
                if candidate_root.exists():
                    job_root = candidate_root
                else:
                    job_root = pipeline_root
            else:
                job_root = pipeline_root

    if not job_root.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job_root
