#!/usr/bin/env python3
"""Legacy wrapper around the modern CLI pipeline runner."""

from __future__ import annotations

import sys
import threading
from typing import Optional

from .cli import args as cli_args
from .cli import pipeline_runner as cli_pipeline_runner
from .progress_tracker import ProgressTracker
from .services.pipeline_service import PipelineResponse

__all__ = ["run_pipeline"]


def run_pipeline(
    *,
    progress_tracker: Optional[ProgressTracker] = None,
    stop_event: Optional[threading.Event] = None,
) -> Optional[PipelineResponse]:
    """Entry point for executing the ebook processing pipeline."""

    args = cli_args.parse_legacy_args()
    response = cli_pipeline_runner.run_pipeline_from_args(
        args,
        progress_tracker=progress_tracker,
        stop_event=stop_event,
    )
    return response


if __name__ == "__main__":  # pragma: no cover - manual execution
    sys.exit(0 if run_pipeline() else 1)
