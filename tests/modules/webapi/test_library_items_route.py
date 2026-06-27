from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest
from fastapi.testclient import TestClient
from prometheus_client.parser import text_string_to_metric_families

from modules.library import LibraryConflictError, LibraryError, LibraryNotFoundError
from modules.library.library_sync import LibrarySearchResult
from modules.webapi.application import create_app
from modules.webapi.dependencies import (
    RequestUserContext,
    get_library_sync,
    get_request_user,
)
from modules.webapi.routers import library as library_router

pytestmark = pytest.mark.webapi


@dataclass
class _RecordingLogger:
    messages: list[str] = field(default_factory=list)

    def debug(self, message: str, *args: object, **kwargs: object) -> None:
        self.messages.append(message % args if args else message)

    def info(self, message: str, *args: object, **kwargs: object) -> None:
        self.messages.append(message % args if args else message)


class _StubLibrarySync:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def search(self, **kwargs: Any) -> LibrarySearchResult:
        self.calls.append(kwargs)
        return LibrarySearchResult(
            total=2,
            page=kwargs["page"],
            limit=kwargs["limit"],
            view=kwargs["view"],
            items=[],
            groups=(
                [{"key": "Author", "total": 2}]
                if kwargs["view"] == "by_author"
                else None
            ),
        )

    def serialize_item(
        self,
        entry: object,
    ) -> dict[str, Any]:  # pragma: no cover - no items in this test
        raise AssertionError("serialize_item should not be called for an empty result")


class _StubLibraryMetadataSync:
    def __init__(self) -> None:
        self.refresh_calls: list[str] = []
        self.enrich_calls: list[dict[str, Any]] = []

    def get_item(self, job_id: str) -> None:
        return None

    def refresh_metadata(self, job_id: str) -> str:
        self.refresh_calls.append(job_id)
        return "refreshed"

    def enrich_metadata(self, job_id: str, *, force: bool = False) -> str:
        self.enrich_calls.append({"job_id": job_id, "force": force})
        return "enriched"

    def serialize_item(self, entry: object) -> dict[str, Any]:
        title = "Externally Enriched" if entry == "enriched" else "Source Refreshed"
        return {
            "job_id": "metadata-job",
            "author": "Example Author",
            "book_title": title,
            "item_type": "book",
            "genre": "Reference",
            "language": "English",
            "status": "finished",
            "media_completed": True,
            "created_at": "2026-06-24T00:00:00Z",
            "updated_at": "2026-06-24T00:00:00Z",
            "library_path": "/library/metadata-job",
            "metadata": {},
        }


class _StubLibrarySourceUploadSync:
    def get_item(self, job_id: str) -> None:
        return None

    def reupload_source_from_path(self, job_id: str, source_path: object) -> object:
        raise LibraryError(
            "source upload failed for job secret-library-job from "
            "/Volumes/Data/private/uploads/SecretReplacement.epub"
        )


class _StubLibraryMetadataUpdateSync:
    def __init__(self, *, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[dict[str, Any]] = []

    def get_item(self, job_id: str) -> None:
        return None

    def update_metadata(self, job_id: str, **kwargs: Any) -> object:
        self.calls.append({"job_id": job_id, **kwargs})
        if self.error is not None:
            raise self.error
        return "updated"

    def serialize_item(self, entry: object) -> dict[str, Any]:
        assert entry == "updated"
        return {
            "job_id": "metadata-job",
            "author": "Updated Author",
            "book_title": "Updated Title",
            "item_type": "book",
            "genre": "Reference",
            "language": "English",
            "status": "finished",
            "media_completed": True,
            "created_at": "2026-06-24T00:00:00Z",
            "updated_at": "2026-06-24T00:00:00Z",
            "library_path": "/library/metadata-job",
            "metadata": {},
        }


class _StubLibraryIsbnApplySync:
    def __init__(self, *, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[dict[str, Any]] = []

    def get_item(self, job_id: str) -> None:
        return None

    def apply_isbn_metadata(self, job_id: str, isbn: str) -> object:
        self.calls.append({"job_id": job_id, "isbn": isbn})
        if self.error is not None:
            raise self.error
        return "updated"

    def serialize_item(self, entry: object) -> dict[str, Any]:
        assert entry == "updated"
        return {
            "job_id": "isbn-job",
            "author": "ISBN Author",
            "book_title": "ISBN Title",
            "item_type": "book",
            "genre": "Reference",
            "language": "English",
            "status": "finished",
            "media_completed": True,
            "created_at": "2026-06-24T00:00:00Z",
            "updated_at": "2026-06-24T00:00:00Z",
            "library_path": "/library/isbn-job",
            "metadata": {},
            "isbn": "9780307474278",
        }


def _has_library_metric_count(
    metrics_text: str,
    *,
    operation: str,
    result: str,
) -> bool:
    families = {
        family.name: family
        for family in text_string_to_metric_families(metrics_text)
    }
    metric = families["ebook_tools_library_route_duration_seconds"]
    return any(
        sample.labels.get("operation") == operation
        and sample.labels.get("result") == result
        and sample.name.endswith("_count")
        and sample.value >= 1
        for sample in metric.samples
    )


def test_apply_isbn_metadata_records_token_safe_success_telemetry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    sync = _StubLibraryIsbnApplySync()
    logger = _RecordingLogger()
    monkeypatch.setattr(library_router, "LOGGER", logger)
    app.dependency_overrides[get_library_sync] = lambda: sync
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="office-ipad-user",
        user_role="admin",
    )

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/library/items/isbn-job/isbn",
                json={"isbn": "9780307474278"},
            )
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["isbn"] == "9780307474278"
    assert sync.calls == [{"job_id": "isbn-job", "isbn": "9780307474278"}]
    assert _has_library_metric_count(
        metrics_response.text,
        operation="isbn_apply",
        result="success",
    )
    rendered = metrics_response.text + "\n".join(logger.messages)
    assert "Library ISBN apply result=success" in rendered
    assert "has_isbn=True" in rendered
    assert "office-ipad-user" not in rendered
    assert "isbn-job" not in rendered
    assert "9780307474278" not in rendered


@pytest.mark.parametrize(
    ("error", "expected_status", "expected_detail", "expected_result"),
    [
        (
            LibraryError(
                "invalid ISBN 9780307474278 for secret-isbn-job at "
                "/Volumes/Data/private/isbn-cache.json"
            ),
            400,
            "Unable to apply ISBN metadata.",
            "bad_request",
        ),
        (
            LibraryNotFoundError(
                "missing secret-isbn-job under /Volumes/Data/private/library"
            ),
            404,
            "Library item not found.",
            "not_found",
        ),
    ],
)
def test_apply_isbn_metadata_errors_use_generic_detail_and_token_safe_telemetry(
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
    expected_status: int,
    expected_detail: str,
    expected_result: str,
) -> None:
    app = create_app()
    logger = _RecordingLogger()
    monkeypatch.setattr(library_router, "LOGGER", logger)
    app.dependency_overrides[get_library_sync] = lambda: _StubLibraryIsbnApplySync(
        error=error
    )
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="office-ipad-user",
        user_role="admin",
    )

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/library/items/secret-isbn-job/isbn",
                json={"isbn": "9780307474278"},
            )
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == expected_status
    assert response.json() == {"detail": expected_detail}
    assert _has_library_metric_count(
        metrics_response.text,
        operation="isbn_apply",
        result=expected_result,
    )
    rendered = response.text + metrics_response.text + "\n".join(logger.messages)
    assert f"Library ISBN apply result={expected_result}" in rendered
    assert "has_isbn=True" in rendered
    assert "office-ipad-user" not in rendered
    assert "secret-isbn-job" not in rendered
    assert "9780307474278" not in rendered
    assert "/Volumes/Data/private" not in rendered


def test_update_library_metadata_records_token_safe_success_telemetry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    sync = _StubLibraryMetadataUpdateSync()
    logger = _RecordingLogger()
    monkeypatch.setattr(library_router, "LOGGER", logger)
    app.dependency_overrides[get_library_sync] = lambda: sync
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="office-ipad-user",
        user_role="admin",
    )

    try:
        with TestClient(app) as client:
            response = client.patch(
                "/api/library/items/metadata-job",
                json={
                    "title": "Updated Title",
                    "author": "Updated Author",
                    "isbn": None,
                },
            )
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["bookTitle"] == "Updated Title"
    assert sync.calls == [
        {
            "job_id": "metadata-job",
            "title": "Updated Title",
            "author": "Updated Author",
            "genre": None,
            "language": None,
            "isbn": None,
        }
    ]
    assert _has_library_metric_count(
        metrics_response.text,
        operation="metadata_update",
        result="success",
    )
    rendered = metrics_response.text + "\n".join(logger.messages)
    assert "Library metadata update result=success" in rendered
    assert "edited_fields=2" in rendered
    assert "office-ipad-user" not in rendered
    assert "metadata-job" not in rendered
    assert "Updated Title" not in rendered
    assert "Updated Author" not in rendered


@pytest.mark.parametrize(
    ("error", "expected_status", "expected_detail", "expected_result"),
    [
        (
            LibraryError(
                "metadata update failed for secret-library-job title=Private Draft "
                "at /Volumes/Data/Library/private"
            ),
            400,
            "Unable to update library metadata.",
            "bad_request",
        ),
        (
            LibraryConflictError(
                "destination already exists for /Volumes/Data/Library/private/Private Draft"
            ),
            409,
            "Library metadata update conflicts with an existing item.",
            "conflict",
        ),
    ],
)
def test_update_library_metadata_errors_use_generic_detail_and_token_safe_telemetry(
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
    expected_status: int,
    expected_detail: str,
    expected_result: str,
) -> None:
    app = create_app()
    logger = _RecordingLogger()
    monkeypatch.setattr(library_router, "LOGGER", logger)
    app.dependency_overrides[get_library_sync] = lambda: _StubLibraryMetadataUpdateSync(
        error=error
    )
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="office-ipad-user",
        user_role="admin",
    )

    try:
        with TestClient(app) as client:
            response = client.patch(
                "/api/library/items/secret-library-job",
                json={
                    "title": "Private Draft",
                    "author": "Hidden Author",
                    "genre": "Secret Genre",
                },
            )
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == expected_status
    assert response.json() == {"detail": expected_detail}
    assert _has_library_metric_count(
        metrics_response.text,
        operation="metadata_update",
        result=expected_result,
    )
    rendered = response.text + metrics_response.text + "\n".join(logger.messages)
    assert f"Library metadata update result={expected_result}" in rendered
    assert "edited_fields=3" in rendered
    assert "office-ipad-user" not in rendered
    assert "secret-library-job" not in rendered
    assert "Private Draft" not in rendered
    assert "Hidden Author" not in rendered
    assert "Secret Genre" not in rendered
    assert "/Volumes/Data/Library/private" not in rendered


def test_list_library_items_records_safe_timing(monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_app()
    sync = _StubLibrarySync()
    logger = _RecordingLogger()
    secret_query = "SecretSearchNeedle"

    monkeypatch.setattr(library_router, "LOGGER", logger)
    app.dependency_overrides[get_library_sync] = lambda: sync
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="test-user",
        user_role="admin",
    )

    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/library/items",
                params={
                    "q": secret_query,
                    "author": "Hidden Author",
                    "view": "by_author",
                    "page": 2,
                    "limit": 7,
                },
            )
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "total": 2,
        "page": 2,
        "limit": 7,
        "view": "by_author",
        "items": [],
        "groups": [{"key": "Author", "total": 2}],
    }
    assert sync.calls == [
        {
            "query": secret_query,
            "author": "Hidden Author",
            "book_title": None,
            "genre": None,
            "language": None,
            "status": None,
            "view": "by_author",
            "page": 2,
            "limit": 7,
            "sort": "updated_at_desc",
            "user_id": "test-user",
            "user_role": "admin",
        }
    ]

    rendered_logs = "\n".join(logger.messages)
    assert "query_present=True" in rendered_logs
    assert "filters=1" in rendered_logs
    assert "total=2" in rendered_logs
    assert secret_query not in rendered_logs
    assert "Hidden Author" not in rendered_logs
    assert "test-user" not in rendered_logs

    assert _has_library_metric_count(
        metrics_response.text,
        operation="list_items",
        result="success",
    )


def test_upload_library_source_error_uses_generic_detail_and_token_safe_telemetry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    logger = _RecordingLogger()
    monkeypatch.setattr(library_router, "LOGGER", logger)
    app.dependency_overrides[get_library_sync] = lambda: _StubLibrarySourceUploadSync()
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="office-ipad-user",
        user_role="admin",
    )

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/library/items/secret-library-job/upload-source",
                files={
                    "file": (
                        "SecretReplacement.epub",
                        b"replacement epub",
                        "application/epub+zip",
                    )
                },
            )
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400
    assert response.json() == {"detail": "Unable to replace library source file."}
    assert _has_library_metric_count(
        metrics_response.text,
        operation="source_upload",
        result="bad_request",
    )
    rendered = response.text + metrics_response.text + "\n".join(logger.messages)
    assert "Library source upload result=bad_request" in rendered
    assert "has_filename=True" in rendered
    assert "office-ipad-user" not in rendered
    assert "secret-library-job" not in rendered
    assert "SecretReplacement.epub" not in rendered
    assert "/Volumes/Data/private/uploads" not in rendered


def test_refresh_library_metadata_defaults_to_source_refresh_only() -> None:
    app = create_app()
    sync = _StubLibraryMetadataSync()
    app.dependency_overrides[get_library_sync] = lambda: sync
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="test-user",
        user_role="admin",
    )

    try:
        with TestClient(app) as client:
            response = client.post("/api/library/items/metadata-job/refresh")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["item"]["bookTitle"] == "Source Refreshed"
    assert sync.refresh_calls == ["metadata-job"]
    assert sync.enrich_calls == []


def test_refresh_library_metadata_can_chain_external_enrichment() -> None:
    app = create_app()
    sync = _StubLibraryMetadataSync()
    app.dependency_overrides[get_library_sync] = lambda: sync
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="test-user",
        user_role="admin",
    )

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/library/items/metadata-job/refresh",
                json={"enrichFromExternal": True},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["item"]["bookTitle"] == "Externally Enriched"
    assert sync.refresh_calls == ["metadata-job"]
    assert sync.enrich_calls == [{"job_id": "metadata-job", "force": True}]
