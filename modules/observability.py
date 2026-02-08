"""Observability utilities for structured logging and optional telemetry."""

from __future__ import annotations

import contextlib
import time
from typing import Dict, Iterator, Mapping, Optional

from . import logging_manager as log_mgr

logger = log_mgr.get_logger()

try:  # pragma: no cover - optional dependency
    from opentelemetry import metrics, trace
except Exception:  # pragma: no cover - defensive import guard
    metrics = None  # type: ignore
    trace = None  # type: ignore


_tracer = trace.get_tracer("ebook_tools.pipeline") if trace else None
_meter = metrics.get_meter("ebook_tools.pipeline") if metrics else None
_histograms: Dict[str, object] = {}

# Prometheus bridge — maps OTEL-style metric names to Prometheus Histogram objects.
# Lazily initialised on first use; safe no-op when prometheus-client is absent.
_prometheus_bridge: Optional[Dict[str, object]] = None


def _init_prometheus_bridge() -> Dict[str, object]:
    """Build the mapping once on first call."""
    global _prometheus_bridge
    if _prometheus_bridge is not None:
        return _prometheus_bridge
    try:
        from modules.webapi.metrics import PIPELINE_STAGE_DURATION
        _prometheus_bridge = {
            "pipeline.stage.duration": PIPELINE_STAGE_DURATION,
            "pipeline.operation.duration": PIPELINE_STAGE_DURATION,
        }
    except Exception:
        _prometheus_bridge = {}
    return _prometheus_bridge


def _bridge_to_prometheus(
    name: str,
    value: float,
    attributes: Mapping[str, object],
) -> None:
    """Forward a metric observation to the corresponding Prometheus histogram."""
    bridge = _init_prometheus_bridge()
    prom_hist = bridge.get(name)
    if prom_hist is None:
        return
    try:
        # Extract a single label value; pipeline stage/operation both use "stage"
        label_key = "stage" if "stage" in attributes else "operation"
        label_val = str(attributes.get(label_key, "unknown"))
        prom_hist.labels(stage=label_val).observe(value / 1000.0)  # ms → seconds
    except Exception:
        pass


def _get_histogram(name: str):  # pragma: no cover - simple helper
    if _meter is None:
        return None
    histogram = _histograms.get(name)
    if histogram is None:
        histogram = _meter.create_histogram(name)
        _histograms[name] = histogram
    return histogram


def record_metric(
    name: str,
    value: float,
    attributes: Optional[Mapping[str, object]] = None,
) -> None:
    """Record a numeric observation, using OpenTelemetry when available."""

    histogram = _get_histogram(name)
    attributes = dict(attributes or {})
    if histogram is not None:
        try:  # pragma: no cover - dependent on optional OTEL runtime
            histogram.record(value, attributes=attributes)
            return
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.debug(
                "Failed to export metric via OpenTelemetry",
                extra={
                    "event": "observability.metric_export_error",
                    "metric": name,
                    "error": str(exc),
                    "console_suppress": True,
                },
            )

    # Bridge to Prometheus histograms when available
    _bridge_to_prometheus(name, value, attributes)

    logger.debug(
        "Metric recorded",
        extra={
            "event": "observability.metric_recorded",
            "metric": name,
            "value": value,
            "attributes": attributes,
            "console_suppress": True,
        },
    )


@contextlib.contextmanager
def _maybe_span(name: str, attributes: Mapping[str, object]):  # pragma: no cover - thin wrapper
    if _tracer is None:
        yield None
        return
    with _tracer.start_as_current_span(name, attributes=dict(attributes)) as span:
        yield span


@contextlib.contextmanager
def pipeline_operation(
    name: str,
    *,
    attributes: Optional[Mapping[str, object]] = None,
) -> Iterator[None]:
    """Context manager that instruments a pipeline operation."""

    attrs = dict(attributes or {})
    log_mgr.ensure_correlation_context(
        correlation_id=attrs.get("correlation_id"), job_id=attrs.get("job_id")
    )

    with log_mgr.log_context(stage=name):
        start = time.perf_counter()
        logger.info(
            "Operation started",
            extra={
                "event": "pipeline.operation.start",
                "stage": name,
                "attributes": attrs,
                "console_suppress": True,
            },
        )
        with _maybe_span(f"pipeline.operation.{name}", attrs):
            yield
        duration_ms = (time.perf_counter() - start) * 1000.0
        record_metric(
            "pipeline.operation.duration", duration_ms, {**attrs, "operation": name}
        )
        logger.info(
            "Operation completed",
            extra={
                "event": "pipeline.operation.complete",
                "stage": name,
                "duration_ms": round(duration_ms, 2),
                "attributes": attrs,
                "console_suppress": True,
            },
        )


@contextlib.contextmanager
def pipeline_stage(stage: str, attributes: Optional[Mapping[str, object]] = None) -> Iterator[None]:
    """Instrument a pipeline stage with structured logging and optional telemetry."""

    attrs = dict(attributes or {})
    log_mgr.ensure_correlation_context(
        correlation_id=attrs.get("correlation_id"), job_id=attrs.get("job_id")
    )

    with log_mgr.log_context(stage=stage):
        start = time.perf_counter()
        logger.info(
            "Stage started",
            extra={
                "event": "pipeline.stage.start",
                "stage": stage,
                "attributes": attrs,
                "console_suppress": True,
            },
        )
        with _maybe_span(f"pipeline.stage.{stage}", attrs):
            yield
        duration_ms = (time.perf_counter() - start) * 1000.0
        record_metric(
            "pipeline.stage.duration", duration_ms, {**attrs, "stage": stage}
        )
        logger.info(
            "Stage completed",
            extra={
                "event": "pipeline.stage.complete",
                "stage": stage,
                "duration_ms": round(duration_ms, 2),
                "attributes": attrs,
                "console_suppress": True,
            },
        )


def worker_pool_event(
    action: str,
    *,
    mode: str,
    max_workers: int,
    attributes: Optional[Mapping[str, object]] = None,
) -> None:
    """Emit a structured log for worker pool lifecycle transitions."""

    attrs = {"mode": mode, "max_workers": max_workers}
    if attributes:
        attrs.update(dict(attributes))
    logger.info(
        "Worker pool event",
        extra={
            "event": "worker_pool.%s" % action,
            "stage": "worker_pool",
            "attributes": attrs,
            "console_suppress": True,
        },
    )
    record_metric(
        f"worker_pool.{action}",
        float(max_workers),
        {**attrs, "action": action},
    )
