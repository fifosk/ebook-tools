"""Console-script entry point for ebook-tools."""

from __future__ import annotations

import sys
from typing import Optional, Sequence

from ..progress_tracker import ProgressTracker
from .args import parse_cli_args
from .pipeline_runner import run_pipeline_from_args


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the ebook-tools CLI."""

    args = parse_cli_args(argv)
    command = getattr(args, "command", "run")
    if getattr(args, "interactive", False) or command == "interactive":
        args.interactive = True
        command = "interactive"
    tracker = ProgressTracker()
    response = run_pipeline_from_args(args, progress_tracker=tracker)
    if command == "run" and response is None:
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover - manual execution
    sys.exit(main())
