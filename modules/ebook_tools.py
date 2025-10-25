#!/usr/bin/env python3
"""Legacy wrapper around the modern CLI pipeline runner."""

from __future__ import annotations

import sys
import threading
import warnings
from typing import Optional

from .cli.orchestrator import run_legacy_pipeline
from .progress_tracker import ProgressTracker
from .services.pipeline_service import PipelineResponse

__all__ = ["run_pipeline"]


def run_pipeline(
    *,
    progress_tracker: Optional[ProgressTracker] = None,
    stop_event: Optional[threading.Event] = None,
) -> Optional[PipelineResponse]:
    """Entry point for executing the ebook processing pipeline."""

    warnings.warn(
        "modules.ebook_tools is deprecated; import modules.cli.orchestrator instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return run_legacy_pipeline(
        progress_tracker=progress_tracker,
        stop_event=stop_event,
    )


if __name__ == "__main__":  # pragma: no cover - manual execution
    sys.exit(0 if run_pipeline() else 1)
