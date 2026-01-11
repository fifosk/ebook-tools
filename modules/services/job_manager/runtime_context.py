from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional

from modules import config_manager as cfg
from modules import logging_manager as log_mgr
from modules.services.file_locator import FileLocator

logger = log_mgr.get_logger().getChild("services.job_context")


@contextmanager
def job_runtime_context(
    locator: FileLocator,
    job_id: str,
    *,
    output_dir: Optional[Path] = None,
) -> Iterator[Optional[cfg.RuntimeContext]]:
    try:
        base_config = cfg.load_configuration(verbose=False)
    except Exception:
        logger.debug("Unable to load configuration for job %s", job_id, exc_info=True)
        base_config = {}

    resolved_output = output_dir or locator.media_root(job_id)
    try:
        resolved_output.mkdir(parents=True, exist_ok=True)
    except Exception:
        logger.debug(
            "Unable to prepare output directory %s for job %s",
            resolved_output,
            job_id,
            exc_info=True,
        )

    try:
        context = cfg.build_runtime_context(
            dict(base_config),
            {"output_dir": str(resolved_output)},
        )
    except Exception:
        logger.debug("Unable to build runtime context for job %s", job_id, exc_info=True)
        context = None

    if context is None:
        yield None
        return

    previous = cfg.get_runtime_context(None)
    cfg.set_runtime_context(context)
    try:
        yield context
    finally:
        try:
            cfg.cleanup_environment(context)
        finally:
            if previous is not None:
                cfg.set_runtime_context(previous)
            else:
                cfg.clear_runtime_context()
