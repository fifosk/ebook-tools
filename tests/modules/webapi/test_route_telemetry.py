from __future__ import annotations

from dataclasses import dataclass, field

from modules.webapi import metrics, route_telemetry


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


def test_metric_label_sanitizer_bounds_empty_and_long_values() -> None:
    assert route_telemetry._sanitize_metric_label(" ? ") == "unknown"
    assert route_telemetry._sanitize_metric_label("a" * 100) == "a" * 80
