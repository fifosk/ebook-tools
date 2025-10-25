"""Compatibility bootstrap that forwards to the unified CLI orchestrator."""

from __future__ import annotations

import sys
import warnings
from typing import Sequence

from modules.cli.orchestrator import run_cli


def main(argv: Sequence[str] | None = None) -> int:
    """Execute the CLI with the supplied ``argv`` sequence."""

    return run_cli(argv)


def run_pipeline(argv: Sequence[str] | None = None) -> int:
    """Backward compatible alias for :func:`main`.

    Historically :mod:`ebook-tools` exposed a ``run_pipeline`` helper from the
    ``main`` module.  Retain that public API so legacy invocations such as the
    ``ebook-tools.py`` shim continue to operate after the CLI refactor.
    """

    warnings.warn(
        "main.run_pipeline() is deprecated; call main.main() or use the CLI entry "
        "point instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return main(argv)


if __name__ == "__main__":  # pragma: no cover - manual execution
    sys.exit(main())
