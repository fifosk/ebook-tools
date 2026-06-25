from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient
from prometheus_client.parser import text_string_to_metric_families

from modules.webapi.dependencies import RequestUserContext
from modules.webapi.application import create_app
from modules.webapi.dependencies import (
    get_file_locator,
    get_library_repository,
    get_pipeline_service,
    get_request_user,
)
from modules.webapi.routes.media import lookup_cache

pytestmark = pytest.mark.webapi


class _ListLogger:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def debug(self, message: str, *args, **kwargs) -> None:
        self.messages.append(message % args if args else message)

    def info(self, message: str, *args, **kwargs) -> None:
        self.messages.append(message % args if args else message)

    def warning(self, message: str, *args, **kwargs) -> None:
        self.messages.append(message % args if args else message)

    def error(self, message: str, *args, **kwargs) -> None:
        self.messages.append(message % args if args else message)


class _AudioRef:
    def to_dict(self) -> dict[str, object]:
        return {"path": "/private/audio/secretword.mp3", "t0": 1.25, "t1": 1.55}


class _CacheEntry:
    word = "secretword"
    word_normalized = "secretword"
    lookup_result = {"definition": "Sensitive definition payload"}
    audio_references = [_AudioRef()]


class _Cache:
    input_language = "English"
    definition_language = "Slovak"
    stats = SimpleNamespace(
        total_words=1,
        llm_calls=7,
        skipped_stopwords=3,
        build_time_seconds=4.5,
    )
    entries = {"secretword": _CacheEntry()}

    def get(self, word: str) -> _CacheEntry | None:
        if word == "secretword":
            return _CacheEntry()
        return None


def _has_lookup_cache_metric_count(
    metrics_text: str,
    *,
    operation: str,
    result: str,
) -> bool:
    families = {family.name: family for family in text_string_to_metric_families(metrics_text)}
    metric = families["ebook_tools_lookup_cache_route_duration_seconds"]
    return any(
        sample.name.endswith("_count")
        and sample.labels.get("operation") == operation
        and sample.labels.get("result") == result
        and sample.value >= 1
        for sample in metric.samples
    )


def _build_client(monkeypatch: pytest.MonkeyPatch, capture_logger: _ListLogger) -> TestClient:
    app = create_app()
    monkeypatch.setattr(lookup_cache, "logger", capture_logger)
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="alice",
        user_role="viewer",
    )
    app.dependency_overrides[get_pipeline_service] = lambda: SimpleNamespace(_job_manager=object())
    app.dependency_overrides[get_file_locator] = lambda: object()
    app.dependency_overrides[get_library_repository] = lambda: object()
    return TestClient(app)


def test_lookup_cache_resolution_preserves_forbidden(monkeypatch) -> None:
    def _raise_forbidden(**_kwargs: object) -> Path:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="not allowed")

    monkeypatch.setattr(lookup_cache, "_resolve_job_root", _raise_forbidden)

    with pytest.raises(HTTPException) as exc_info:
        lookup_cache._load_cache_for_job(
            "job-private",
            locator=object(),
            library_repository=object(),
            request_user=RequestUserContext(user_id="reader", user_role="viewer"),
            job_manager=object(),
        )

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN


def test_lookup_cache_resolution_keeps_missing_as_cache_miss(monkeypatch) -> None:
    def _raise_not_found(**_kwargs: object) -> Path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="missing")

    monkeypatch.setattr(lookup_cache, "_resolve_job_root", _raise_not_found)

    assert (
        lookup_cache._load_cache_for_job(
            "job-missing",
            locator=object(),
            library_repository=object(),
            request_user=RequestUserContext(user_id="reader", user_role="viewer"),
            job_manager=object(),
        )
        is None
    )


def test_lookup_cache_routes_record_token_safe_metrics_and_logs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    capture_logger = _ListLogger()
    monkeypatch.setattr(lookup_cache, "_load_cache_for_job", lambda *_, **__: _Cache())

    with _build_client(monkeypatch, capture_logger) as client:
        full_response = client.get("/api/pipelines/jobs/private-job/lookup-cache")
        summary_response = client.get("/api/pipelines/jobs/private-job/lookup-cache/summary")
        hit_response = client.get("/api/pipelines/jobs/private-job/lookup-cache/secretword")
        miss_response = client.get("/api/pipelines/jobs/private-job/lookup-cache/missingword")
        bulk_response = client.post(
            "/api/pipelines/jobs/private-job/lookup-cache/bulk",
            json={"words": ["secretword", "missingword"]},
        )
        metrics_response = client.get("/metrics")

    assert full_response.status_code == 200
    assert full_response.json()["entries"]["secretword"]["cached"] is True
    assert summary_response.status_code == 200
    assert summary_response.json()["available"] is True
    assert hit_response.status_code == 200
    assert hit_response.json()["cached"] is True
    assert miss_response.status_code == 200
    assert miss_response.json()["cached"] is False
    assert bulk_response.status_code == 200
    assert bulk_response.json()["cache_hits"] == 1
    assert bulk_response.json()["cache_misses"] == 1

    assert metrics_response.status_code == 200
    assert _has_lookup_cache_metric_count(
        metrics_response.text,
        operation="full",
        result="success",
    )
    assert _has_lookup_cache_metric_count(
        metrics_response.text,
        operation="summary",
        result="success",
    )
    assert _has_lookup_cache_metric_count(
        metrics_response.text,
        operation="word",
        result="cache_hit",
    )
    assert _has_lookup_cache_metric_count(
        metrics_response.text,
        operation="word",
        result="cache_miss",
    )
    assert _has_lookup_cache_metric_count(
        metrics_response.text,
        operation="bulk",
        result="success",
    )

    logs = "\n".join(capture_logger.messages)
    assert "Lookup cache route operation=full result=success" in logs
    assert "Lookup cache route operation=summary result=success" in logs
    assert "Lookup cache route operation=word result=cache_hit" in logs
    assert "Lookup cache route operation=word result=cache_miss" in logs
    assert "Lookup cache route operation=bulk result=success" in logs
    assert "entries=1" in logs
    assert "hits=1" in logs
    assert "misses=1" in logs
    for secret in [
        "alice",
        "private-job",
        "secretword",
        "missingword",
        "Sensitive definition",
        "/private/audio",
        "English",
        "Slovak",
    ]:
        assert secret not in logs


def test_lookup_cache_routes_record_unavailable_not_found_and_forbidden(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    capture_logger = _ListLogger()
    monkeypatch.setattr(lookup_cache, "_load_cache_for_job", lambda *_, **__: None)

    with _build_client(monkeypatch, capture_logger) as client:
        full_missing = client.get("/api/pipelines/jobs/private-job/lookup-cache")
        summary_missing = client.get("/api/pipelines/jobs/private-job/lookup-cache/summary")
        word_missing = client.get("/api/pipelines/jobs/private-job/lookup-cache/secretword")
        bulk_missing = client.post(
            "/api/pipelines/jobs/private-job/lookup-cache/bulk",
            json={"words": ["secretword", "missingword"]},
        )
        metrics_response = client.get("/metrics")

    assert full_missing.status_code == 404
    assert summary_missing.status_code == 200
    assert summary_missing.json()["available"] is False
    assert word_missing.status_code == 200
    assert word_missing.json()["cached"] is False
    assert bulk_missing.status_code == 200
    assert bulk_missing.json()["cache_hits"] == 0
    assert bulk_missing.json()["cache_misses"] == 2
    assert _has_lookup_cache_metric_count(
        metrics_response.text,
        operation="full",
        result="not_found",
    )
    assert _has_lookup_cache_metric_count(
        metrics_response.text,
        operation="summary",
        result="unavailable",
    )
    assert _has_lookup_cache_metric_count(
        metrics_response.text,
        operation="bulk",
        result="unavailable",
    )

    def _raise_forbidden(*_args: Any, **_kwargs: Any) -> None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="not allowed")

    forbidden_logger = _ListLogger()
    monkeypatch.setattr(lookup_cache, "_load_cache_for_job", _raise_forbidden)
    with _build_client(monkeypatch, forbidden_logger) as client:
        forbidden_response = client.get("/api/pipelines/jobs/private-job/lookup-cache/summary")
        forbidden_metrics = client.get("/metrics")

    assert forbidden_response.status_code == 403
    assert _has_lookup_cache_metric_count(
        forbidden_metrics.text,
        operation="summary",
        result="forbidden",
    )
    logs = "\n".join(capture_logger.messages + forbidden_logger.messages)
    assert "Lookup cache route operation=full result=not_found" in logs
    assert "Lookup cache route operation=summary result=unavailable" in logs
    assert "Lookup cache route operation=summary result=forbidden" in logs
    assert "private-job" not in logs
    assert "secretword" not in logs
    assert "missingword" not in logs
