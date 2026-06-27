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
    get_pipeline_service,
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
    def __init__(
        self,
        *,
        error: Exception | None = None,
        items: list[object] | None = None,
        serialize_error: Exception | None = None,
    ) -> None:
        self.error = error
        self.items = items or []
        self.serialize_error = serialize_error
        self.calls: list[dict[str, Any]] = []

    def search(self, **kwargs: Any) -> LibrarySearchResult:
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return LibrarySearchResult(
            total=2,
            page=kwargs["page"],
            limit=kwargs["limit"],
            view=kwargs["view"],
            items=self.items,
            groups=(
                [{"key": "Author", "total": 2}]
                if kwargs["view"] == "by_author"
                else None
            ),
        )

    def serialize_item(
        self,
        entry: object,
    ) -> dict[str, Any]:
        if self.serialize_error is not None:
            raise self.serialize_error
        assert entry == "listed"
        return {
            "job_id": "listed-job",
            "author": "Listed Author",
            "book_title": "Listed Title",
            "item_type": "book",
            "genre": "Reference",
            "language": "English",
            "status": "finished",
            "media_completed": True,
            "created_at": "2026-06-24T00:00:00Z",
            "updated_at": "2026-06-24T00:00:00Z",
            "library_path": "/library/listed-job",
            "metadata": {},
        }


class _StubLibraryMetadataSync:
    def __init__(
        self,
        *,
        refresh_error: Exception | None = None,
        enrich_error: Exception | None = None,
    ) -> None:
        self.refresh_error = refresh_error
        self.enrich_error = enrich_error
        self.refresh_calls: list[str] = []
        self.enrich_calls: list[dict[str, Any]] = []

    def get_item(self, job_id: str) -> None:
        return None

    def refresh_metadata(self, job_id: str) -> str:
        self.refresh_calls.append(job_id)
        if self.refresh_error is not None:
            raise self.refresh_error
        return "refreshed"

    def enrich_metadata(self, job_id: str, *, force: bool = False) -> str:
        self.enrich_calls.append({"job_id": job_id, "force": force})
        if self.enrich_error is not None:
            raise self.enrich_error
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


class _StubLibraryMovePipelineService:
    def __init__(self, *, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[dict[str, Any]] = []

    def get_job(self, job_id: str, **kwargs: Any) -> dict[str, Any]:
        self.calls.append({"job_id": job_id, **kwargs})
        if self.error is not None:
            raise self.error
        return {"job_id": job_id}


class _StubLibraryMoveSync:
    def __init__(
        self,
        *,
        error: Exception | None = None,
        serialize_error: Exception | None = None,
    ) -> None:
        self.error = error
        self.serialize_error = serialize_error
        self.calls: list[dict[str, Any]] = []

    def move_to_library(
        self,
        job_id: str,
        *,
        status_override: str | None = None,
    ) -> object:
        self.calls.append({"job_id": job_id, "status_override": status_override})
        if self.error is not None:
            raise self.error
        return "moved"

    def serialize_item(self, entry: object) -> dict[str, Any]:
        assert entry == "moved"
        if self.serialize_error is not None:
            raise self.serialize_error
        return {
            "job_id": "move-job",
            "author": "Move Author",
            "book_title": "Move Title",
            "item_type": "book",
            "genre": "Reference",
            "language": "English",
            "status": "finished",
            "media_completed": True,
            "created_at": "2026-06-24T00:00:00Z",
            "updated_at": "2026-06-24T00:00:00Z",
            "library_path": "/library/move-job",
            "metadata": {},
        }


class _StubLibraryAccessMetadata:
    data = {"access": {"visibility": "private"}}


class _StubLibraryAccessItem:
    owner_id = "other-user"
    metadata = _StubLibraryAccessMetadata()


class _StubLibraryPublicAccessMetadata:
    data = {
        "access": {
            "visibility": "public",
            "grants": [
                {
                    "subjectType": "user",
                    "subjectId": "shared-user",
                    "permissions": ["view"],
                }
            ],
        }
    }


class _StubLibraryPublicAccessItem:
    owner_id = "office-ipad-user"
    metadata = _StubLibraryPublicAccessMetadata()


class _StubLibraryAccessSync:
    def __init__(
        self,
        *,
        item: object | None = None,
        error: Exception | None = None,
        serialize_error: Exception | None = None,
        get_item_error: Exception | None = None,
    ) -> None:
        self.item = item
        self.error = error
        self.serialize_error = serialize_error
        self.get_item_error = get_item_error
        self.update_calls: list[dict[str, Any]] = []

    def get_item(self, job_id: str) -> object | None:
        if self.get_item_error is not None:
            raise self.get_item_error
        return self.item

    def update_access(
        self,
        job_id: str,
        *,
        visibility: str | None = None,
        grants: list[dict[str, Any]] | None = None,
        actor_id: str | None = None,
    ) -> object:
        self.update_calls.append(
            {
                "job_id": job_id,
                "visibility": visibility,
                "grants": grants,
                "actor_id": actor_id,
            }
        )
        if self.error is not None:
            raise self.error
        return "updated"

    def serialize_item(self, entry: object) -> dict[str, Any]:
        assert entry == "updated"
        if self.serialize_error is not None:
            raise self.serialize_error
        return {
            "job_id": "access-job",
            "author": "Access Author",
            "book_title": "Access Title",
            "item_type": "book",
            "genre": "Reference",
            "language": "English",
            "status": "finished",
            "media_completed": True,
            "created_at": "2026-06-24T00:00:00Z",
            "updated_at": "2026-06-24T00:00:00Z",
            "library_path": "/library/access-job",
            "metadata": {},
            "access": {"visibility": "public", "grants": []},
        }


class _StubLibraryRemoveMediaSync:
    def __init__(
        self,
        *,
        error: Exception | None = None,
        serialize_error: Exception | None = None,
        item: object | None = None,
        updated_item: object | None = None,
        removed: int = 3,
        get_item_error: Exception | None = None,
    ) -> None:
        self.error = error
        self.serialize_error = serialize_error
        self.item = item
        self.updated_item = updated_item
        self.removed = removed
        self.get_item_error = get_item_error
        self.calls: list[str] = []

    def get_item(self, job_id: str) -> object | None:
        if self.get_item_error is not None:
            raise self.get_item_error
        return self.item

    def remove_media(self, job_id: str) -> tuple[object | None, int]:
        self.calls.append(job_id)
        if self.error is not None:
            raise self.error
        return self.updated_item, self.removed

    def serialize_item(self, entry: object) -> dict[str, Any]:
        assert entry == "updated"
        if self.serialize_error is not None:
            raise self.serialize_error
        return {
            "job_id": "media-job",
            "author": "Media Author",
            "book_title": "Media Title",
            "item_type": "book",
            "genre": "Reference",
            "language": "English",
            "status": "paused",
            "media_completed": False,
            "created_at": "2026-06-24T00:00:00Z",
            "updated_at": "2026-06-24T00:00:00Z",
            "library_path": "/library/media-job",
            "metadata": {},
        }


class _StubLibraryRemoveEntrySync:
    def __init__(self, *, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[str] = []

    def get_item(self, job_id: str) -> None:
        return None

    def remove_entry(self, job_id: str) -> None:
        self.calls.append(job_id)
        if self.error is not None:
            raise self.error


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


def test_move_job_to_library_records_token_safe_success_telemetry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    pipeline_service = _StubLibraryMovePipelineService()
    sync = _StubLibraryMoveSync()
    logger = _RecordingLogger()
    monkeypatch.setattr(library_router, "LOGGER", logger)
    app.dependency_overrides[get_pipeline_service] = lambda: pipeline_service
    app.dependency_overrides[get_library_sync] = lambda: sync
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="office-ipad-user",
        user_role="admin",
    )

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/library/move/library-job",
                json={"statusOverride": "finished"},
            )
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["item"]["jobId"] == "move-job"
    assert pipeline_service.calls == [
        {
            "job_id": "library-job",
            "user_id": "office-ipad-user",
            "user_role": "admin",
            "permission": "edit",
        }
    ]
    assert sync.calls == [{"job_id": "library-job", "status_override": "finished"}]
    assert _has_library_metric_count(
        metrics_response.text,
        operation="move_entry",
        result="success",
    )
    rendered = metrics_response.text + "\n".join(logger.messages)
    assert "Library entry move result=success" in rendered
    assert "status_override_present=True" in rendered
    assert "office-ipad-user" not in rendered
    assert "library-job" not in rendered


@pytest.mark.parametrize(
    ("error", "expected_status", "expected_detail", "expected_result"),
    [
        (
            KeyError("missing secret-move-job under /Volumes/Data/private/jobs"),
            404,
            "Job not found.",
            "job_not_found",
        ),
        (
            PermissionError(
                "user office-ipad-user cannot edit secret-move-job from "
                "/Volumes/Data/private/jobs"
            ),
            403,
            "Not authorized to modify job.",
            "forbidden",
        ),
        (
            RuntimeError(
                "queue database failed for secret-move-job at "
                "/Volumes/Data/private/jobs"
            ),
            502,
            "Unable to move job to library.",
            "error",
        ),
    ],
)
def test_move_job_to_library_pipeline_errors_use_generic_detail_and_token_safe_telemetry(
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
    expected_status: int,
    expected_detail: str,
    expected_result: str,
) -> None:
    app = create_app()
    sync = _StubLibraryMoveSync()
    logger = _RecordingLogger()
    monkeypatch.setattr(library_router, "LOGGER", logger)
    app.dependency_overrides[get_pipeline_service] = (
        lambda: _StubLibraryMovePipelineService(error=error)
    )
    app.dependency_overrides[get_library_sync] = lambda: sync
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="office-ipad-user",
        user_role="admin",
    )

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/library/move/secret-move-job",
                json={"statusOverride": "finished"},
            )
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == expected_status
    assert response.json() == {"detail": expected_detail}
    assert sync.calls == []
    assert _has_library_metric_count(
        metrics_response.text,
        operation="move_entry",
        result=expected_result,
    )
    rendered = response.text + metrics_response.text + "\n".join(logger.messages)
    assert f"Library entry move result={expected_result}" in rendered
    assert "status_override_present=True" in rendered
    assert "office-ipad-user" not in rendered
    assert "secret-move-job" not in rendered
    assert "/Volumes/Data/private" not in rendered


@pytest.mark.parametrize(
    ("error", "expected_status", "expected_detail", "expected_result"),
    [
        (
            LibraryNotFoundError(
                "missing secret-move-job under /Volumes/Data/private/jobs"
            ),
            404,
            "Job not found.",
            "not_found",
        ),
        (
            LibraryConflictError(
                "secret-move-job already exists at /Volumes/Data/private/library"
            ),
            409,
            "Library item already exists.",
            "conflict",
        ),
        (
            LibraryError(
                "move failed for secret-move-job at "
                "/Volumes/Data/private/library"
            ),
            400,
            "Unable to move job to library.",
            "bad_request",
        ),
        (
            RuntimeError(
                "serializer failed for secret-move-job at "
                "/Volumes/Data/private/library"
            ),
            502,
            "Unable to move job to library.",
            "error",
        ),
    ],
)
def test_move_job_to_library_sync_errors_use_generic_detail_and_token_safe_telemetry(
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
    expected_status: int,
    expected_detail: str,
    expected_result: str,
) -> None:
    app = create_app()
    logger = _RecordingLogger()
    monkeypatch.setattr(library_router, "LOGGER", logger)
    serialize_error = error if isinstance(error, RuntimeError) else None
    move_error = None if serialize_error is not None else error
    sync = _StubLibraryMoveSync(error=move_error, serialize_error=serialize_error)
    app.dependency_overrides[get_pipeline_service] = (
        lambda: _StubLibraryMovePipelineService()
    )
    app.dependency_overrides[get_library_sync] = lambda: sync
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="office-ipad-user",
        user_role="admin",
    )

    try:
        with TestClient(app) as client:
            response = client.post("/api/library/move/secret-move-job")
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == expected_status
    assert response.json() == {"detail": expected_detail}
    assert sync.calls == [{"job_id": "secret-move-job", "status_override": None}]
    assert _has_library_metric_count(
        metrics_response.text,
        operation="move_entry",
        result=expected_result,
    )
    rendered = response.text + metrics_response.text + "\n".join(logger.messages)
    assert f"Library entry move result={expected_result}" in rendered
    assert "status_override_present=False" in rendered
    assert "office-ipad-user" not in rendered
    assert "secret-move-job" not in rendered
    assert "/Volumes/Data/private" not in rendered


@pytest.mark.parametrize(
    ("updated_item", "expected_location", "expected_item_job_id"),
    [
        (None, "queue", None),
        ("updated", "library", "media-job"),
    ],
)
def test_remove_library_media_records_token_safe_success_telemetry(
    monkeypatch: pytest.MonkeyPatch,
    updated_item: object | None,
    expected_location: str,
    expected_item_job_id: str | None,
) -> None:
    app = create_app()
    sync = _StubLibraryRemoveMediaSync(updated_item=updated_item, removed=5)
    logger = _RecordingLogger()
    monkeypatch.setattr(library_router, "LOGGER", logger)
    app.dependency_overrides[get_library_sync] = lambda: sync
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="office-ipad-user",
        user_role="admin",
    )

    try:
        with TestClient(app) as client:
            response = client.post("/api/library/remove-media/library-job")
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["jobId"] == "library-job"
    assert payload["location"] == expected_location
    assert payload["removed"] == 5
    if expected_item_job_id is None:
        assert payload["item"] is None
    else:
        assert payload["item"]["jobId"] == expected_item_job_id
    assert sync.calls == ["library-job"]
    assert _has_library_metric_count(
        metrics_response.text,
        operation="remove_media",
        result="success",
    )
    rendered = metrics_response.text + "\n".join(logger.messages)
    assert "Library media remove result=success" in rendered
    assert f"location={expected_location}" in rendered
    assert "removed_count=5" in rendered
    assert "office-ipad-user" not in rendered
    assert "library-job" not in rendered


@pytest.mark.parametrize(
    ("error", "expected_status", "expected_detail", "expected_result"),
    [
        (
            LibraryNotFoundError(
                "missing secret-media-job under /Volumes/Data/private/library"
            ),
            404,
            "Library media not found.",
            "not_found",
        ),
        (
            LibraryError(
                "remove media failed for secret-media-job at "
                "/Volumes/Data/private/library/secret-media-job/media"
            ),
            400,
            "Unable to remove library media.",
            "bad_request",
        ),
        (
            RuntimeError(
                "sqlite failure for secret-media-job at "
                "/Volumes/Data/private/library/secret-media-job"
            ),
            502,
            "Unable to remove library media.",
            "error",
        ),
    ],
)
def test_remove_library_media_errors_use_generic_detail_and_token_safe_telemetry(
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
    expected_status: int,
    expected_detail: str,
    expected_result: str,
) -> None:
    app = create_app()
    logger = _RecordingLogger()
    monkeypatch.setattr(library_router, "LOGGER", logger)
    app.dependency_overrides[get_library_sync] = lambda: _StubLibraryRemoveMediaSync(
        error=error
    )
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="office-ipad-user",
        user_role="admin",
    )

    try:
        with TestClient(app) as client:
            response = client.post("/api/library/remove-media/secret-media-job")
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == expected_status
    assert response.json() == {"detail": expected_detail}
    assert _has_library_metric_count(
        metrics_response.text,
        operation="remove_media",
        result=expected_result,
    )
    rendered = response.text + metrics_response.text + "\n".join(logger.messages)
    assert f"Library media remove result={expected_result}" in rendered
    assert "office-ipad-user" not in rendered
    assert "secret-media-job" not in rendered
    assert "/Volumes/Data/private/library" not in rendered


def test_remove_library_media_serialization_errors_use_generic_detail_and_token_safe_telemetry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    logger = _RecordingLogger()
    monkeypatch.setattr(library_router, "LOGGER", logger)
    app.dependency_overrides[get_library_sync] = lambda: _StubLibraryRemoveMediaSync(
        updated_item="updated",
        serialize_error=RuntimeError(
            "serialize failed for secret-media-job at /Volumes/Data/private/library"
        ),
    )
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="office-ipad-user",
        user_role="admin",
    )

    try:
        with TestClient(app) as client:
            response = client.post("/api/library/remove-media/secret-media-job")
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 502
    assert response.json() == {"detail": "Unable to remove library media."}
    assert _has_library_metric_count(
        metrics_response.text,
        operation="remove_media",
        result="error",
    )
    rendered = response.text + metrics_response.text + "\n".join(logger.messages)
    assert "Library media remove result=error" in rendered
    assert "secret-media-job" not in rendered
    assert "/Volumes/Data/private/library" not in rendered


def test_remove_library_media_forbidden_records_token_safe_telemetry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    logger = _RecordingLogger()
    monkeypatch.setattr(library_router, "LOGGER", logger)
    sync = _StubLibraryRemoveMediaSync(item=_StubLibraryAccessItem())
    app.dependency_overrides[get_library_sync] = lambda: sync
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="office-ipad-user",
        user_role="viewer",
    )

    try:
        with TestClient(app) as client:
            response = client.post("/api/library/remove-media/secret-media-job")
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json() == {"detail": "Not authorized to modify library item"}
    assert sync.calls == []
    assert _has_library_metric_count(
        metrics_response.text,
        operation="remove_media",
        result="forbidden",
    )
    rendered = response.text + metrics_response.text + "\n".join(logger.messages)
    assert "Library media remove result=forbidden" in rendered
    assert "office-ipad-user" not in rendered
    assert "secret-media-job" not in rendered


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


def test_remove_library_entry_records_token_safe_success_telemetry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    sync = _StubLibraryRemoveEntrySync()
    logger = _RecordingLogger()
    monkeypatch.setattr(library_router, "LOGGER", logger)
    app.dependency_overrides[get_library_sync] = lambda: sync
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="office-ipad-user",
        user_role="admin",
    )

    try:
        with TestClient(app) as client:
            response = client.delete("/api/library/remove/library-job")
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 204
    assert sync.calls == ["library-job"]
    assert _has_library_metric_count(
        metrics_response.text,
        operation="remove_entry",
        result="success",
    )
    rendered = metrics_response.text + "\n".join(logger.messages)
    assert "Library entry remove result=success" in rendered
    assert "office-ipad-user" not in rendered
    assert "library-job" not in rendered


@pytest.mark.parametrize(
    ("error", "expected_status", "expected_detail", "expected_result"),
    [
        (
            LibraryError(
                "remove failed for secret-remove-job at "
                "/Volumes/Data/private/library/secret-remove-job"
            ),
            400,
            "Unable to remove library item.",
            "bad_request",
        ),
        (
            LibraryNotFoundError(
                "missing secret-remove-job under /Volumes/Data/private/library"
            ),
            404,
            "Library item not found.",
            "not_found",
        ),
        (
            RuntimeError(
                "sqlite failure for secret-remove-job at "
                "/Volumes/Data/private/library/secret-remove-job"
            ),
            502,
            "Unable to remove library item.",
            "error",
        ),
    ],
)
def test_remove_library_entry_errors_use_generic_detail_and_token_safe_telemetry(
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
    expected_status: int,
    expected_detail: str,
    expected_result: str,
) -> None:
    app = create_app()
    logger = _RecordingLogger()
    monkeypatch.setattr(library_router, "LOGGER", logger)
    app.dependency_overrides[get_library_sync] = lambda: _StubLibraryRemoveEntrySync(
        error=error
    )
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="office-ipad-user",
        user_role="admin",
    )

    try:
        with TestClient(app) as client:
            response = client.delete("/api/library/remove/secret-remove-job")
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == expected_status
    assert response.json() == {"detail": expected_detail}
    assert _has_library_metric_count(
        metrics_response.text,
        operation="remove_entry",
        result=expected_result,
    )
    rendered = response.text + metrics_response.text + "\n".join(logger.messages)
    assert f"Library entry remove result={expected_result}" in rendered
    assert "office-ipad-user" not in rendered
    assert "secret-remove-job" not in rendered
    assert "/Volumes/Data/private/library" not in rendered


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


@pytest.mark.parametrize(
    ("sync", "expected_status", "expected_result"),
    [
        (
            _StubLibrarySync(
                error=LibraryError(
                    "list failed for SecretSearchNeedle at "
                    "/Volumes/Data/private/library/index.sqlite"
                )
            ),
            400,
            "bad_request",
        ),
        (
            _StubLibrarySync(
                items=["listed"],
                serialize_error=RuntimeError(
                    "serialize failed for SecretSearchNeedle at "
                    "/Volumes/Data/private/library/listed-job"
                ),
            ),
            502,
            "error",
        ),
    ],
)
def test_list_library_items_errors_use_generic_detail_and_token_safe_telemetry(
    monkeypatch: pytest.MonkeyPatch,
    sync: _StubLibrarySync,
    expected_status: int,
    expected_result: str,
) -> None:
    app = create_app()
    logger = _RecordingLogger()
    secret_query = "SecretSearchNeedle"

    monkeypatch.setattr(library_router, "LOGGER", logger)
    app.dependency_overrides[get_library_sync] = lambda: sync
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="office-ipad-user",
        user_role="admin",
    )

    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/library/items",
                params={
                    "q": secret_query,
                    "author": "Hidden Author",
                    "genre": "Secret Genre",
                    "view": "by_author",
                    "page": 2,
                    "limit": 7,
                },
            )
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == expected_status
    assert response.json() == {"detail": "Unable to list library items."}
    assert _has_library_metric_count(
        metrics_response.text,
        operation="list_items",
        result=expected_result,
    )
    rendered = response.text + metrics_response.text + "\n".join(logger.messages)
    assert f"Library item list failed result={expected_result}" in rendered
    assert "query_present=True" in rendered
    assert "filters=2" in rendered
    assert "office-ipad-user" not in rendered
    assert secret_query not in rendered
    assert "Hidden Author" not in rendered
    assert "Secret Genre" not in rendered
    assert "/Volumes/Data/private/library" not in rendered


def test_get_library_access_records_token_safe_success_telemetry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    logger = _RecordingLogger()
    sync = _StubLibraryAccessSync(item=_StubLibraryPublicAccessItem())
    monkeypatch.setattr(library_router, "LOGGER", logger)
    app.dependency_overrides[get_library_sync] = lambda: sync
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="office-ipad-user",
        user_role="editor",
    )

    try:
        with TestClient(app) as client:
            response = client.get("/api/library/items/access-job/access")
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["visibility"] == "public"
    assert _has_library_metric_count(
        metrics_response.text,
        operation="access_get",
        result="success",
    )
    rendered = metrics_response.text + "\n".join(logger.messages)
    assert "Library access policy operation=access_get result=success" in rendered
    assert "visibility_present=True" in rendered
    assert "grant_count=1" in rendered
    assert "office-ipad-user" not in rendered
    assert "access-job" not in rendered
    assert "shared-user" not in rendered


@pytest.mark.parametrize(
    ("sync", "expected_status", "expected_detail", "expected_result"),
    [
        (
            _StubLibraryAccessSync(),
            404,
            "Library item not found.",
            "not_found",
        ),
        (
            _StubLibraryAccessSync(
                item=_StubLibraryAccessItem(),
            ),
            403,
            "Not authorized to access library item",
            "forbidden",
        ),
        (
            _StubLibraryAccessSync(
                get_item_error=RuntimeError(
                    "access lookup failed for secret-access-job at "
                    "/Volumes/Data/private/library"
                )
            ),
            502,
            "Unable to load library access policy.",
            "error",
        ),
    ],
)
def test_get_library_access_errors_use_generic_detail_and_token_safe_telemetry(
    monkeypatch: pytest.MonkeyPatch,
    sync: _StubLibraryAccessSync,
    expected_status: int,
    expected_detail: str,
    expected_result: str,
) -> None:
    app = create_app()
    logger = _RecordingLogger()
    monkeypatch.setattr(library_router, "LOGGER", logger)
    app.dependency_overrides[get_library_sync] = lambda: sync
    user_role = "viewer" if expected_result == "forbidden" else "editor"
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="office-ipad-user",
        user_role=user_role,
    )

    try:
        with TestClient(app) as client:
            response = client.get("/api/library/items/secret-access-job/access")
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == expected_status
    assert response.json() == {"detail": expected_detail}
    assert _has_library_metric_count(
        metrics_response.text,
        operation="access_get",
        result=expected_result,
    )
    rendered = response.text + metrics_response.text + "\n".join(logger.messages)
    assert f"Library access policy operation=access_get result={expected_result}" in rendered
    assert "office-ipad-user" not in rendered
    assert "secret-access-job" not in rendered
    assert "/Volumes/Data/private/library" not in rendered


def test_update_library_access_records_token_safe_success_telemetry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    logger = _RecordingLogger()
    sync = _StubLibraryAccessSync(item=_StubLibraryPublicAccessItem())
    monkeypatch.setattr(library_router, "LOGGER", logger)
    app.dependency_overrides[get_library_sync] = lambda: sync
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="office-ipad-user",
        user_role="editor",
    )

    try:
        with TestClient(app) as client:
            response = client.patch(
                "/api/library/items/access-job/access",
                json={
                    "visibility": "public",
                    "grants": [
                        {
                            "subjectType": "user",
                            "subjectId": "secret-shared-user",
                            "permissions": ["view"],
                        }
                    ],
                },
            )
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["jobId"] == "access-job"
    assert sync.update_calls == [
        {
            "job_id": "access-job",
            "visibility": "public",
            "grants": [
                {
                    "subjectType": "user",
                    "subjectId": "secret-shared-user",
                    "permissions": ["view"],
                    "grantedBy": None,
                    "grantedAt": None,
                }
            ],
            "actor_id": "office-ipad-user",
        }
    ]
    assert _has_library_metric_count(
        metrics_response.text,
        operation="access_update",
        result="success",
    )
    rendered = metrics_response.text + "\n".join(logger.messages)
    assert "Library access policy operation=access_update result=success" in rendered
    assert "visibility_present=True" in rendered
    assert "grant_count=1" in rendered
    assert "office-ipad-user" not in rendered
    assert "access-job" not in rendered
    assert "secret-shared-user" not in rendered


@pytest.mark.parametrize(
    ("sync", "expected_status", "expected_detail", "expected_result"),
    [
        (
            _StubLibraryAccessSync(),
            404,
            "Library item not found.",
            "not_found",
        ),
        (
            _StubLibraryAccessSync(item=_StubLibraryAccessItem()),
            403,
            "Not authorized to modify library item",
            "forbidden",
        ),
        (
            _StubLibraryAccessSync(
                item=_StubLibraryPublicAccessItem(),
                error=LibraryNotFoundError(
                    "missing secret-access-job under /Volumes/Data/private/library"
                ),
            ),
            404,
            "Library item not found.",
            "not_found",
        ),
        (
            _StubLibraryAccessSync(
                item=_StubLibraryPublicAccessItem(),
                error=LibraryError(
                    "invalid access policy for secret-access-job at "
                    "/Volumes/Data/private/library"
                ),
            ),
            400,
            "Unable to update library access policy.",
            "bad_request",
        ),
        (
            _StubLibraryAccessSync(
                item=_StubLibraryPublicAccessItem(),
                serialize_error=RuntimeError(
                    "serialize failed for secret-access-job at "
                    "/Volumes/Data/private/library"
                ),
            ),
            502,
            "Unable to update library access policy.",
            "error",
        ),
    ],
)
def test_update_library_access_errors_use_generic_detail_and_token_safe_telemetry(
    monkeypatch: pytest.MonkeyPatch,
    sync: _StubLibraryAccessSync,
    expected_status: int,
    expected_detail: str,
    expected_result: str,
) -> None:
    app = create_app()
    logger = _RecordingLogger()
    monkeypatch.setattr(library_router, "LOGGER", logger)
    app.dependency_overrides[get_library_sync] = lambda: sync
    user_role = "viewer" if expected_result == "forbidden" else "editor"
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="office-ipad-user",
        user_role=user_role,
    )

    try:
        with TestClient(app) as client:
            response = client.patch(
                "/api/library/items/secret-access-job/access",
                json={
                    "visibility": "public",
                    "grants": [
                        {
                            "subjectType": "user",
                            "subjectId": "secret-shared-user",
                            "permissions": ["view"],
                        }
                    ],
                },
            )
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == expected_status
    assert response.json() == {"detail": expected_detail}
    assert _has_library_metric_count(
        metrics_response.text,
        operation="access_update",
        result=expected_result,
    )
    rendered = response.text + metrics_response.text + "\n".join(logger.messages)
    assert f"Library access policy operation=access_update result={expected_result}" in rendered
    assert "visibility_present=True" in rendered
    assert "grant_count=1" in rendered
    assert "office-ipad-user" not in rendered
    assert "secret-access-job" not in rendered
    assert "secret-shared-user" not in rendered
    assert "/Volumes/Data/private/library" not in rendered


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


def test_refresh_library_metadata_defaults_to_source_refresh_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    sync = _StubLibraryMetadataSync()
    logger = _RecordingLogger()
    monkeypatch.setattr(library_router, "LOGGER", logger)
    app.dependency_overrides[get_library_sync] = lambda: sync
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="office-ipad-user",
        user_role="admin",
    )

    try:
        with TestClient(app) as client:
            response = client.post("/api/library/items/metadata-job/refresh")
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["item"]["bookTitle"] == "Source Refreshed"
    assert sync.refresh_calls == ["metadata-job"]
    assert sync.enrich_calls == []
    assert _has_library_metric_count(
        metrics_response.text,
        operation="metadata_refresh",
        result="success",
    )
    rendered = metrics_response.text + "\n".join(logger.messages)
    assert "Library metadata refresh result=success" in rendered
    assert "enrich_requested=False" in rendered
    assert "office-ipad-user" not in rendered
    assert "metadata-job" not in rendered
    assert "Source Refreshed" not in rendered


def test_refresh_library_metadata_can_chain_external_enrichment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    sync = _StubLibraryMetadataSync()
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
                "/api/library/items/metadata-job/refresh",
                json={"enrichFromExternal": True},
            )
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["item"]["bookTitle"] == "Externally Enriched"
    assert sync.refresh_calls == ["metadata-job"]
    assert sync.enrich_calls == [{"job_id": "metadata-job", "force": True}]
    assert _has_library_metric_count(
        metrics_response.text,
        operation="metadata_refresh",
        result="success",
    )
    rendered = metrics_response.text + "\n".join(logger.messages)
    assert "Library metadata refresh result=success" in rendered
    assert "enrich_requested=True" in rendered
    assert "office-ipad-user" not in rendered
    assert "metadata-job" not in rendered
    assert "Externally Enriched" not in rendered


@pytest.mark.parametrize(
    ("refresh_error", "enrich_error", "enrich_requested", "expected_status", "expected_detail", "expected_result"),
    [
        (
            LibraryError(
                "refresh failed for secret-refresh-job at "
                "/Volumes/Data/private/source.epub"
            ),
            None,
            False,
            400,
            "Unable to refresh library metadata.",
            "bad_request",
        ),
        (
            LibraryNotFoundError(
                "missing secret-refresh-job under /Volumes/Data/private/library"
            ),
            None,
            False,
            404,
            "Library item not found.",
            "not_found",
        ),
        (
            None,
            LibraryError(
                "OpenLibrary refresh enrichment failed for secret-refresh-job "
                "token=secret-token at /Volumes/Data/private/openlibrary-cache.json"
            ),
            True,
            400,
            "Unable to refresh library metadata.",
            "bad_request",
        ),
    ],
)
def test_refresh_library_metadata_errors_use_generic_detail_and_token_safe_telemetry(
    monkeypatch: pytest.MonkeyPatch,
    refresh_error: Exception | None,
    enrich_error: Exception | None,
    enrich_requested: bool,
    expected_status: int,
    expected_detail: str,
    expected_result: str,
) -> None:
    app = create_app()
    sync = _StubLibraryMetadataSync(
        refresh_error=refresh_error,
        enrich_error=enrich_error,
    )
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
                "/api/library/items/secret-refresh-job/refresh",
                json={"enrichFromExternal": enrich_requested},
            )
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == expected_status
    assert response.json() == {"detail": expected_detail}
    assert _has_library_metric_count(
        metrics_response.text,
        operation="metadata_refresh",
        result=expected_result,
    )
    rendered = response.text + metrics_response.text + "\n".join(logger.messages)
    assert f"Library metadata refresh result={expected_result}" in rendered
    assert f"enrich_requested={enrich_requested}" in rendered
    assert "office-ipad-user" not in rendered
    assert "secret-refresh-job" not in rendered
    assert "/Volumes/Data/private" not in rendered
    assert "secret-token" not in rendered
    assert "OpenLibrary refresh enrichment failed" not in rendered


def test_enrich_library_metadata_records_token_safe_success_telemetry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    sync = _StubLibraryMetadataSync()
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
                "/api/library/items/metadata-job/enrich",
                json={"force": True},
            )
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["item"]["bookTitle"] == "Externally Enriched"
    assert sync.enrich_calls == [{"job_id": "metadata-job", "force": True}]
    assert _has_library_metric_count(
        metrics_response.text,
        operation="metadata_enrich",
        result="success",
    )
    rendered = metrics_response.text + "\n".join(logger.messages)
    assert "Library metadata enrich result=success" in rendered
    assert "force=True" in rendered
    assert "office-ipad-user" not in rendered
    assert "metadata-job" not in rendered
    assert "Externally Enriched" not in rendered


@pytest.mark.parametrize(
    ("error", "expected_status", "expected_detail", "expected_result"),
    [
        (
            LibraryError(
                "OpenLibrary enrich failed for secret-enrich-job at "
                "/Volumes/Data/private/openlibrary-cache.json token=secret-token"
            ),
            400,
            "Unable to enrich library metadata.",
            "bad_request",
        ),
        (
            LibraryNotFoundError(
                "missing secret-enrich-job under /Volumes/Data/private/library"
            ),
            404,
            "Library item not found.",
            "not_found",
        ),
    ],
)
def test_enrich_library_metadata_errors_use_generic_detail_and_token_safe_telemetry(
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
    expected_status: int,
    expected_detail: str,
    expected_result: str,
) -> None:
    app = create_app()
    sync = _StubLibraryMetadataSync(enrich_error=error)
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
                "/api/library/items/secret-enrich-job/enrich",
                json={"force": True},
            )
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == expected_status
    assert response.json() == {"detail": expected_detail}
    assert _has_library_metric_count(
        metrics_response.text,
        operation="metadata_enrich",
        result=expected_result,
    )
    rendered = response.text + metrics_response.text + "\n".join(logger.messages)
    assert f"Library metadata enrich result={expected_result}" in rendered
    assert "force=True" in rendered
    assert "office-ipad-user" not in rendered
    assert "secret-enrich-job" not in rendered
    assert "/Volumes/Data/private" not in rendered
    assert "secret-token" not in rendered
    assert "OpenLibrary enrich failed" not in rendered
