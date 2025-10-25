"""Compatibility bootstrap that forwards to the unified CLI orchestrator."""

from __future__ import annotations

import sys
from typing import Sequence

from modules.cli.orchestrator import run_cli


def main(argv: Sequence[str] | None = None) -> int:
    """Execute the CLI with the supplied ``argv`` sequence."""

    return run_cli(argv)


if __name__ == "__main__":  # pragma: no cover - manual execution
    sys.exit(main())
