"""Shared route telemetry helpers for token-safe backend observability."""

from __future__ import annotations

import time
from typing import Any


def record_labeled_route_duration(
    metric_name: str,
    elapsed_seconds: float,
    **labels: str,
) -> None:
    """Record a token-safe route duration metric with caller-supplied labels."""

    try:
        from . import metrics as webapi_metrics

        metric = getattr(webapi_metrics, metric_name)
    except Exception:
        return
    metric.labels(**labels).observe(elapsed_seconds)


def record_route_duration(
    metric_name: str,
    operation: str,
    result: str,
    elapsed_seconds: float,
) -> None:
    """Record a token-safe route duration metric if metrics are available."""

    record_labeled_route_duration(
        metric_name,
        elapsed_seconds,
        operation=operation,
        result=result,
    )


def record_started_route_duration(
    metric_name: str,
    operation: str,
    result: str,
    started_at: float,
) -> None:
    """Record a token-safe route duration metric from a perf-counter start."""

    record_route_duration(metric_name, operation, result, time.perf_counter() - started_at)


def log_started_route_result(
    logger: Any,
    *,
    metric_name: str,
    message: str,
    operation: str,
    result: str,
    started_at: float,
    success_results: set[str] | frozenset[str] = frozenset({"success"}),
    duration_precision: int = 1,
    log_extra: dict[str, Any] | None = None,
    **fields: str | int | bool | None,
) -> None:
    """Record and log aggregate route timing without identifiers or payload values."""

    elapsed_seconds = time.perf_counter() - started_at
    duration_ms = elapsed_seconds * 1000.0
    record_route_duration(metric_name, operation, result, elapsed_seconds)
    details = (
        f"{message} operation={operation} result={result} "
        f"duration_ms={duration_ms:.{duration_precision}f}"
    )
    for name, value in fields.items():
        if value is None:
            continue
        rendered = str(value).lower() if isinstance(value, bool) else str(value)
        details += f" {name}={rendered}"
    log_method = logger.info if result not in success_results or duration_ms >= 250 else logger.debug
    if log_extra is None:
        log_method(details)
    else:
        log_method(details, extra=log_extra)


def record_media_stream_route_duration(
    result: str,
    media_kind: str,
    elapsed_seconds: float,
) -> None:
    """Record token-safe local media streaming setup timing."""

    record_labeled_route_duration(
        "MEDIA_STREAM_DURATION",
        elapsed_seconds,
        operation="file_stream",
        result=result,
        media_kind=media_kind,
    )


def record_started_media_stream_route_duration(
    result: str,
    media_kind: str,
    started_at: float,
) -> None:
    """Record token-safe local media streaming setup timing from a perf-counter start."""

    record_media_stream_route_duration(result, media_kind, time.perf_counter() - started_at)


def record_source_picker_route_duration(
    operation: str,
    result: str,
    elapsed_seconds: float,
) -> None:
    """Record token-safe source picker route timing if metrics are available."""

    record_route_duration(
        "SOURCE_PICKER_ROUTE_DURATION",
        operation,
        result,
        elapsed_seconds,
    )


def record_create_submission_route_duration(
    operation: str,
    result: str,
    elapsed_seconds: float,
) -> None:
    """Record token-safe Create submission route timing if metrics are available."""

    record_route_duration(
        "CREATE_SUBMISSION_ROUTE_DURATION",
        operation,
        result,
        elapsed_seconds,
    )


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
