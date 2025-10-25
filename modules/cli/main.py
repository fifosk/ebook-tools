"""Console-script entry point for ebook-tools."""

from __future__ import annotations

import sys
from typing import Optional, Sequence

from .orchestrator import run_cli


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the ebook-tools CLI."""

    return run_cli(argv)


if __name__ == "__main__":  # pragma: no cover - manual execution
    sys.exit(main())
