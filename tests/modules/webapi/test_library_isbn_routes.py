from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient
from prometheus_client.parser import text_string_to_metric_families

from modules.library import LibraryError
from modules.webapi.application import create_app
from modules.webapi.dependencies import get_library_sync
from modules.webapi.routers import library as library_router

pytestmark = pytest.mark.webapi


class _StubLibrarySync:
    def __init__(
        self,
        *,
        metadata: dict[str, Any] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.metadata = metadata or {
            "title": "Demo Book",
            "author": "Demo Author",
            "isbn": "9780307474278",
        }
        self.error = error

    def lookup_isbn_metadata(self, isbn: str) -> dict[str, Any]:
        if self.error is not None:
            raise self.error
        return dict(self.metadata)


class _RecordingLogger:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def _record(self, message: str, *args, **kwargs) -> None:
        if args:
            message = message % args
        self.messages.append(message)

    def debug(self, message: str, *args, **kwargs) -> None:
        self._record(message, *args, **kwargs)

    def info(self, message: str, *args, **kwargs) -> None:
        self._record(message, *args, **kwargs)

    def warning(self, message: str, *args, **kwargs) -> None:
        self._record(message, *args, **kwargs)

    @property
    def rendered(self) -> str:
        return "\n".join(self.messages)


def _has_library_metric_count(
    metrics_text: str,
    *,
    operation: str,
    result: str,
) -> bool:
    families = {family.name: family for family in text_string_to_metric_families(metrics_text)}
    metric = families["ebook_tools_library_route_duration_seconds"]
    return any(
        sample.name.endswith("_count")
        and sample.labels.get("operation") == operation
        and sample.labels.get("result") == result
        and sample.value >= 1
        for sample in metric.samples
    )


def _build_client(sync: _StubLibrarySync) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_library_sync] = lambda: sync
    return TestClient(app)


def test_library_isbn_lookup_records_success_metric() -> None:
    with _build_client(_StubLibrarySync()) as client:
        response = client.get("/api/library/isbn/lookup", params={"isbn": "9780307474278"})
        metrics_response = client.get("/metrics")

    assert response.status_code == 200
    assert response.json()["metadata"]["title"] == "Demo Book"
    assert _has_library_metric_count(
        metrics_response.text,
        operation="isbn_lookup",
        result="success",
    )


def test_library_isbn_lookup_library_error_uses_generic_detail_and_token_safe_telemetry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    logger = _RecordingLogger()
    secret_error = LibraryError(
        "OpenLibrary failed for ISBN 9780307474278 at "
        "/Volumes/Data/private/isbn-cache.json api_key=secret-key"
    )
    monkeypatch.setattr(library_router, "LOGGER", logger)

    with _build_client(_StubLibrarySync(error=secret_error)) as client:
        response = client.get("/api/library/isbn/lookup", params={"isbn": "9780307474278"})
        metrics_response = client.get("/metrics")

    assert response.status_code == 400
    assert response.json() == {"detail": "Unable to lookup ISBN metadata."}
    assert _has_library_metric_count(
        metrics_response.text,
        operation="isbn_lookup",
        result="bad_request",
    )
    assert "response detail suppressed" in logger.rendered
    rendered = response.text + metrics_response.text + logger.rendered
    assert "9780307474278" not in rendered
    assert "/Volumes/Data/private/isbn-cache.json" not in rendered
    assert "secret-key" not in rendered
    assert "OpenLibrary failed" not in rendered


def test_library_isbn_lookup_unexpected_error_uses_generic_detail_and_token_safe_telemetry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    logger = _RecordingLogger()
    secret_error = RuntimeError(
        "metadata provider crashed for ISBN 9780307474278 at "
        "/Volumes/Data/private/provider.log token=secret-token"
    )
    monkeypatch.setattr(library_router, "LOGGER", logger)

    with _build_client(_StubLibrarySync(error=secret_error)) as client:
        response = client.get("/api/library/isbn/lookup", params={"isbn": "9780307474278"})
        metrics_response = client.get("/metrics")

    assert response.status_code == 502
    assert response.json() == {"detail": "Unable to lookup ISBN metadata."}
    assert _has_library_metric_count(
        metrics_response.text,
        operation="isbn_lookup",
        result="error",
    )
    assert "response detail suppressed" in logger.rendered
    rendered = response.text + metrics_response.text + logger.rendered
    assert "9780307474278" not in rendered
    assert "/Volumes/Data/private/provider.log" not in rendered
    assert "secret-token" not in rendered
    assert "metadata provider crashed" not in rendered
