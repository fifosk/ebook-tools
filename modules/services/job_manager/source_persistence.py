"""Utilities for persisting source files for pipeline jobs."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from ... import config_manager as cfg
from ... import logging_manager as log_mgr
from ..file_locator import FileLocator

if TYPE_CHECKING:
    from ..pipeline_service import PipelineRequest

logger = log_mgr.logger


def persist_source_file(
    job_id: str,
    request: "PipelineRequest",
    file_locator: FileLocator,
) -> Optional[str]:
    """Mirror the pipeline input file into the job's dedicated data directory.

    Returns the relative path from job_root if successful, None otherwise.
    """

    input_file = getattr(request.inputs, "input_file", "")
    if not input_file:
        return None

    resolved_path: Optional[Path] = None
    candidate = Path(str(input_file)).expanduser()
    try:
        if candidate.is_file():
            resolved_path = candidate
    except OSError:
        resolved_path = None

    if resolved_path is None:
        base_dir = None
        context = request.context
        if context is not None:
            base_dir = getattr(context, "books_dir", None)
        resolved = cfg.resolve_file_path(input_file, base_dir)
        if resolved is not None:
            resolved_path = Path(resolved)

    if resolved_path is None or not resolved_path.exists():
        return None

    data_root = file_locator.data_root(job_id)
    data_root.mkdir(parents=True, exist_ok=True)

    destination = data_root / resolved_path.name
    job_root = file_locator.job_root(job_id)

    try:
        if destination.exists() and destination.resolve() == resolved_path.resolve():
            return destination.relative_to(job_root).as_posix()
    except OSError:
        pass

    try:
        shutil.copy2(resolved_path, destination)
    except Exception:  # pragma: no cover - defensive logging
        logger.debug(
            "Unable to mirror source file %s for job %s",
            resolved_path,
            job_id,
            exc_info=True,
        )
        return None

    return destination.relative_to(job_root).as_posix()


__all__ = [
    "persist_source_file",
]
