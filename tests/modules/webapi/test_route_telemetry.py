from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from modules.webapi import metrics, route_telemetry

pytestmark = pytest.mark.webapi


@dataclass
class _DummyChild:
    observations: list[float] = field(default_factory=list)

    def observe(self, value: float) -> None:
        self.observations.append(value)


@dataclass
class _DummyMetric:
    labels_seen: list[dict[str, str]] = field(default_factory=list)
    child: _DummyChild = field(default_factory=_DummyChild)

    def labels(self, **labels: str) -> _DummyChild:
        self.labels_seen.append(labels)
        return self.child


class _ListLogger:
    def __init__(self) -> None:
        self.debug_messages: list[str] = []
        self.info_messages: list[str] = []

    def debug(self, message: str, **_kwargs) -> None:
        self.debug_messages.append(message)

    def info(self, message: str, **_kwargs) -> None:
        self.info_messages.append(message)


def test_route_duration_sanitizes_metric_labels(monkeypatch) -> None:
    metric = _DummyMetric()
    monkeypatch.setattr(metrics, "TEST_ROUTE_DURATION", metric, raising=False)

    route_telemetry.record_labeled_route_duration(
        "TEST_ROUTE_DURATION",
        0.25,
        operation="lookup /api?token=secret",
        result="failed:user@example.test",
    )

    assert metric.labels_seen == [
        {
            "operation": "lookup_api_token_secret",
            "result": "failed:user_example.test",
        }
    ]
    assert metric.child.observations == [0.25]


def test_started_route_log_uses_sanitized_operation_and_result(monkeypatch) -> None:
    metric = _DummyMetric()
    logger = _ListLogger()
    monkeypatch.setattr(metrics, "TEST_LOG_ROUTE_DURATION", metric, raising=False)
    monkeypatch.setattr(route_telemetry.time, "perf_counter", lambda: 10.5)

    route_telemetry.log_started_route_result(
        logger,
        metric_name="TEST_LOG_ROUTE_DURATION",
        message="Route",
        operation="media /Users/fifo/book.epub",
        result="success?auth=secret",
        started_at=10.0,
        success_results={"success_auth_secret"},
        count=3,
    )

    assert metric.labels_seen == [
        {
            "operation": "media_Users_fifo_book.epub",
            "result": "success_auth_secret",
        }
    ]
    assert logger.info_messages == [
        "Route operation=media_Users_fifo_book.epub result=success_auth_secret "
        "duration_ms=500.0 count=3"
    ]
    assert logger.debug_messages == []


def test_labeled_route_log_sanitizes_extra_metric_labels(monkeypatch) -> None:
    metric = _DummyMetric()
    logger = _ListLogger()
    monkeypatch.setattr(metrics, "TEST_LABELED_ROUTE_DURATION", metric, raising=False)
    monkeypatch.setattr(route_telemetry.time, "perf_counter", lambda: 20.249)

    route_telemetry.log_labeled_route_result(
        logger,
        metric_name="TEST_LABELED_ROUTE_DURATION",
        message="Media stream",
        labels={
            "operation": "file stream",
            "result": "partial",
            "media_kind": "video/private?token=secret",
        },
        started_at=20.0,
        success_results={"partial"},
        duration_first=False,
        status=206,
        bytes=12,
    )

    assert metric.labels_seen == [
        {
            "operation": "file_stream",
            "result": "partial",
            "media_kind": "video_private_token_secret",
        }
    ]
    assert logger.debug_messages == [
        "Media stream operation=file_stream result=partial "
        "media_kind=video_private_token_secret status=206 bytes=12 duration_ms=249.0"
    ]
    assert logger.info_messages == []


def test_metric_label_sanitizer_bounds_empty_and_long_values() -> None:
    assert route_telemetry._sanitize_metric_label(" ? ") == "unknown"
    assert route_telemetry._sanitize_metric_label("a" * 100) == "a" * 80
