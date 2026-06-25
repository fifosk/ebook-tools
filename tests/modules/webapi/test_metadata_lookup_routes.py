from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from prometheus_client.parser import text_string_to_metric_families

from modules.services.metadata import (
    ConfidenceLevel,
    MediaType,
    MetadataSource,
    SourceIds,
    UnifiedMetadataResult,
)
from modules.webapi.application import create_app
from modules.webapi.routes import metadata_routes

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


class _FakeMetadataPipeline:
    def __init__(self, result: UnifiedMetadataResult | None) -> None:
        self.result = result
        self.calls: list[dict[str, object]] = []

    def __enter__(self) -> "_FakeMetadataPipeline":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def lookup(self, query, options) -> UnifiedMetadataResult | None:
        self.calls.append({"query": query, "options": options})
        return self.result


def _has_metadata_metric_count(
    metrics_text: str,
    *,
    operation: str,
    result: str,
) -> bool:
    families = {family.name: family for family in text_string_to_metric_families(metrics_text)}
    metric = families["ebook_tools_metadata_lookup_route_duration_seconds"]
    return any(
        sample.name.endswith("_count")
        and sample.labels.get("operation") == operation
        and sample.labels.get("result") == result
        and sample.value >= 1
        for sample in metric.samples
    )


def test_unified_metadata_lookup_records_token_safe_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    capture_logger = _ListLogger()
    result = UnifiedMetadataResult(
        title="Displayed Metadata Title",
        type=MediaType.BOOK,
        author="Displayed Author",
        language="en",
        confidence=ConfidenceLevel.HIGH,
        primary_source=MetadataSource.OPENLIBRARY,
        contributing_sources=[MetadataSource.OPENLIBRARY, MetadataSource.WIKIPEDIA],
        source_ids=SourceIds(isbn="9780307474278", openlibrary_work_key="OL_SECRET_W"),
    )
    pipeline = _FakeMetadataPipeline(result)
    monkeypatch.setattr(metadata_routes, "logger", capture_logger)
    monkeypatch.setattr(metadata_routes, "create_pipeline", lambda: pipeline)

    with TestClient(app) as client:
        response = client.post(
            "/api/pipelines/metadata/lookup",
            json={
                "type": "book",
                "title": "Secret Dan Brown Continuation",
                "author": "Hidden Author",
                "isbn": "9780307474278",
                "source_filename": "Secret Dan Brown.epub",
                "youtube_url": "https://youtube.example.invalid/watch?v=secret",
                "imdb_id": "tt-secret",
                "tmdb_id": 12345,
                "force": True,
                "include_raw": True,
            },
        )
        metrics_response = client.get("/metrics")

    assert response.status_code == 200
    assert response.json()["title"] == "Displayed Metadata Title"
    assert response.json()["primary_source"] == "openlibrary"
    assert response.json()["contributing_sources"] == ["openlibrary", "wikipedia"]
    assert pipeline.calls
    assert pipeline.calls[0]["query"].media_type == MediaType.BOOK
    assert pipeline.calls[0]["options"].force_refresh is True
    assert pipeline.calls[0]["options"].include_raw_responses is True

    assert metrics_response.status_code == 200
    assert _has_metadata_metric_count(
        metrics_response.text,
        operation="lookup",
        result="success",
    )

    logs = "\n".join(capture_logger.messages)
    assert "Unified metadata lookup result=success" in logs
    assert "type=book" in logs
    assert "force=true" in logs
    assert "include_raw=true" in logs
    assert "sources=2" in logs
    assert "source_ids=2" in logs
    assert "Secret Dan Brown" not in logs
    assert "Hidden Author" not in logs
    assert "9780307474278" not in logs
    assert "Secret Dan Brown.epub" not in logs
    assert "youtube.example.invalid" not in logs
    assert "tt-secret" not in logs
    assert "12345" not in logs
    assert "Displayed Metadata Title" not in logs
    assert "Displayed Author" not in logs
    assert "OL_SECRET_W" not in logs


def test_unified_metadata_lookup_records_invalid_type(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    capture_logger = _ListLogger()
    monkeypatch.setattr(metadata_routes, "logger", capture_logger)

    with TestClient(app) as client:
        response = client.post(
            "/api/pipelines/metadata/lookup",
            json={
                "type": "unknown_kind",
                "title": "Do not log this title",
                "source_filename": "private-source.mkv",
            },
        )
        metrics_response = client.get("/metrics")

    assert response.status_code == 400
    assert _has_metadata_metric_count(
        metrics_response.text,
        operation="lookup",
        result="invalid_type",
    )
    logs = "\n".join(capture_logger.messages)
    assert "Unified metadata lookup result=invalid_type" in logs
    assert "type=unknown_kind" in logs
    assert "Do not log this title" not in logs
    assert "private-source.mkv" not in logs


def test_unified_metadata_lookup_records_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    capture_logger = _ListLogger()
    pipeline = _FakeMetadataPipeline(None)
    monkeypatch.setattr(metadata_routes, "logger", capture_logger)
    monkeypatch.setattr(metadata_routes, "create_pipeline", lambda: pipeline)

    with TestClient(app) as client:
        response = client.post(
            "/api/pipelines/metadata/lookup",
            json={
                "type": "youtube_video",
                "youtube_url": "https://youtube.example.invalid/watch?v=secret",
                "source_filename": "private-video.mp4",
            },
        )
        metrics_response = client.get("/metrics")

    assert response.status_code == 404
    assert _has_metadata_metric_count(
        metrics_response.text,
        operation="lookup",
        result="not_found",
    )
    logs = "\n".join(capture_logger.messages)
    assert "Unified metadata lookup result=not_found" in logs
    assert "type=youtube_video" in logs
    assert "youtube.example.invalid" not in logs
    assert "private-video.mp4" not in logs
