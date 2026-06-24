"""Shared route telemetry helpers for token-safe backend observability."""

from __future__ import annotations

import time
from typing import Any


def record_create_submission_route_duration(
    operation: str,
    result: str,
    elapsed_seconds: float,
) -> None:
    """Record token-safe Create submission route timing if metrics are available."""

    try:
        from .metrics import CREATE_SUBMISSION_ROUTE_DURATION
    except Exception:
        return
    CREATE_SUBMISSION_ROUTE_DURATION.labels(operation=operation, result=result).observe(elapsed_seconds)


def log_create_submission_route(
    logger: Any,
    operation: str,
    result: str,
    started_at: float,
    **flags: bool | None,
) -> None:
    """Log aggregate Create submission timing without identifiers, paths, or payload values."""

    elapsed_seconds = time.perf_counter() - started_at
    duration_ms = elapsed_seconds * 1000.0
    record_create_submission_route_duration(operation, result, elapsed_seconds)
    details = (
        f"Create submission operation={operation} result={result} "
        f"duration_ms={duration_ms:.1f}"
    )
    for name, value in flags.items():
        if value is not None:
            details += f" {name}={str(value).lower()}"
    log_method = logger.info if result != "success" or duration_ms >= 250 else logger.debug
    log_method(details)
