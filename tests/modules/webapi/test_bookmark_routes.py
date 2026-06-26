from __future__ import annotations

from dataclasses import asdict

import pytest
from fastapi.testclient import TestClient
from prometheus_client.parser import text_string_to_metric_families

from modules.services import bookmark_service
from modules.services.bookmark_service import BookmarkEntry, BookmarkService
from modules.services.file_locator import FileLocator
from modules.webapi.application import create_app
from modules.webapi.dependencies import (
    RequestUserContext,
    get_bookmark_service,
    get_request_user,
)
from modules.webapi.routers import bookmarks as bookmarks_router

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


def _has_bookmark_metric_count(
    metrics_text: str,
    *,
    operation: str,
    result: str,
) -> bool:
    families = {family.name: family for family in text_string_to_metric_families(metrics_text)}
    metric = families["ebook_tools_bookmark_route_duration_seconds"]
    return any(
        sample.name.endswith("_count")
        and sample.labels.get("operation") == operation
        and sample.labels.get("result") == result
        and sample.value >= 1
        for sample in metric.samples
    )


class _StubBookmarkService:
    def __init__(self) -> None:
        self.list_calls: list[dict[str, str]] = []
        self.add_calls: list[dict[str, object]] = []
        self.remove_calls: list[dict[str, str]] = []
        self.entry = BookmarkEntry(
            id="bookmark-1",
            job_id="job-1",
            item_type="book",
            kind="sentence",
            created_at=1_800_000_000.0,
            label="Important sentence",
            position=None,
            sentence=42,
            media_type="text",
            media_id="media-1",
            base_id=None,
            segment_id="segment-1",
            chunk_id="chunk-1",
        )

    def list_bookmarks(self, job_id: str, user_id: str) -> list[BookmarkEntry]:
        self.list_calls.append({"job_id": job_id, "user_id": user_id})
        return [self.entry]

    def add_bookmark(
        self,
        job_id: str,
        user_id: str,
        payload: dict[str, object],
    ) -> BookmarkEntry:
        self.add_calls.append({"job_id": job_id, "user_id": user_id, "payload": payload})
        label = str(payload.get("label") or "Bookmark").strip() or "Bookmark"
        return BookmarkEntry(
            **{
                **asdict(self.entry),
                "id": str(payload.get("id") or "created-bookmark"),
                "label": label,
                "kind": str(payload.get("kind") or "time"),
                "sentence": payload.get("sentence"),
                "position": payload.get("position"),
            }
        )

    def remove_bookmark(self, job_id: str, user_id: str, bookmark_id: str) -> bool:
        self.remove_calls.append(
            {"job_id": job_id, "user_id": user_id, "bookmark_id": bookmark_id}
        )
        return bookmark_id == "bookmark-1"


def test_bookmark_routes_scope_calls_to_authenticated_user(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    service = _StubBookmarkService()
    capture_logger = _ListLogger()
    monkeypatch.setattr(bookmarks_router, "logger", capture_logger)
    app.dependency_overrides[get_bookmark_service] = lambda: service
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="alice",
        user_role="editor",
    )

    try:
        with TestClient(app) as client:
            list_response = client.get("/api/bookmarks/job-1")
            add_response = client.post(
                "/api/bookmarks/job-1",
                json={
                    "id": "bookmark-2",
                    "kind": "sentence",
                    "label": "  Saved line  ",
                    "sentence": 7,
                    "media_type": "text",
                    "chunk_id": "chunk-2",
                },
            )
            delete_response = client.delete("/api/bookmarks/job-1/bookmark-1")
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert list_response.status_code == 200
    assert list_response.json() == {
        "job_id": "job-1",
        "bookmarks": [asdict(service.entry)],
    }
    assert add_response.status_code == 200
    assert add_response.json()["id"] == "bookmark-2"
    assert add_response.json()["label"] == "Saved line"
    assert add_response.json()["sentence"] == 7
    assert delete_response.status_code == 200
    assert delete_response.json() == {"deleted": True, "bookmark_id": "bookmark-1"}

    assert service.list_calls == [{"job_id": "job-1", "user_id": "alice"}]
    assert service.add_calls[0]["job_id"] == "job-1"
    assert service.add_calls[0]["user_id"] == "alice"
    assert service.remove_calls == [
        {"job_id": "job-1", "user_id": "alice", "bookmark_id": "bookmark-1"}
    ]
    rendered = "\n".join([list_response.text, add_response.text, delete_response.text])
    assert "alice" not in rendered

    assert metrics_response.status_code == 200
    assert _has_bookmark_metric_count(
        metrics_response.text,
        operation="list",
        result="success",
    )
    assert _has_bookmark_metric_count(
        metrics_response.text,
        operation="add",
        result="success",
    )
    assert _has_bookmark_metric_count(
        metrics_response.text,
        operation="delete",
        result="success",
    )

    logs = "\n".join(capture_logger.messages)
    assert "Bookmark route operation=list result=success" in logs
    assert "Bookmark route operation=add result=success" in logs
    assert "Bookmark route operation=delete result=success" in logs
    assert "bookmarks=1" in logs
    assert "deleted=true" in logs
    assert "alice" not in logs
    assert "job-1" not in logs
    assert "bookmark-1" not in logs
    assert "bookmark-2" not in logs
    assert "Saved line" not in logs


def test_bookmark_routes_normalize_route_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_app()
    service = _StubBookmarkService()
    app.dependency_overrides[get_bookmark_service] = lambda: service
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="alice",
        user_role="editor",
    )

    try:
        with TestClient(app) as client:
            list_response = client.get("/api/bookmarks/%20%20job-1%20%20")
            add_response = client.post(
                "/api/bookmarks/%20%20job-1%20%20",
                json={
                    "id": "bookmark-2",
                    "kind": "sentence",
                    "label": "Saved line",
                    "sentence": 7,
                },
            )
            delete_response = client.delete(
                "/api/bookmarks/%20%20job-1%20%20/%20%20bookmark-1%20%20"
            )
    finally:
        app.dependency_overrides.clear()

    assert list_response.status_code == 200
    assert list_response.json()["job_id"] == "job-1"
    assert add_response.status_code == 200
    assert delete_response.status_code == 200
    assert delete_response.json() == {"deleted": True, "bookmark_id": "bookmark-1"}
    assert service.list_calls == [{"job_id": "job-1", "user_id": "alice"}]
    assert service.add_calls[0]["job_id"] == "job-1"
    assert service.remove_calls == [
        {"job_id": "job-1", "user_id": "alice", "bookmark_id": "bookmark-1"}
    ]


def test_bookmark_routes_reject_blank_job_id_without_service_lookup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    service = _StubBookmarkService()
    app.dependency_overrides[get_bookmark_service] = lambda: service
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="alice",
        user_role="editor",
    )

    try:
        with TestClient(app) as client:
            response = client.get("/api/bookmarks/%20%20%20")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json() == {"detail": "Job not found"}
    assert service.list_calls == []
    assert service.add_calls == []
    assert service.remove_calls == []


def test_bookmark_delete_skips_blank_bookmark_id_without_service_lookup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    service = _StubBookmarkService()
    app.dependency_overrides[get_bookmark_service] = lambda: service
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="alice",
        user_role="editor",
    )

    try:
        with TestClient(app) as client:
            response = client.delete("/api/bookmarks/job-1/%20%20%20")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"deleted": False, "bookmark_id": ""}
    assert service.list_calls == []
    assert service.add_calls == []
    assert service.remove_calls == []


def test_bookmark_routes_require_authenticated_user(monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_app()
    capture_logger = _ListLogger()
    monkeypatch.setattr(bookmarks_router, "logger", capture_logger)
    app.dependency_overrides[get_bookmark_service] = lambda: _StubBookmarkService()
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id=None,
        user_role="anonymous",
    )

    try:
        with TestClient(app) as client:
            response = client.get("/api/bookmarks/job-1")
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 401
    assert metrics_response.status_code == 200
    assert _has_bookmark_metric_count(
        metrics_response.text,
        operation="list",
        result="unauthorized",
    )
    logs = "\n".join(capture_logger.messages)
    assert "Bookmark route operation=list result=unauthorized" in logs
    assert "job-1" not in logs
    assert "anonymous" not in logs


def test_bookmark_corrupt_storage_logs_token_safe_recovery(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    service = BookmarkService(file_locator=FileLocator(storage_dir=tmp_path))
    capture_logger = _ListLogger()
    user_id = "alice.secret@example.test"
    job_id = "secret-job-1"
    storage_path = service._job_path(job_id, user_id)  # noqa: SLF001 - pins recovery behavior.
    storage_path.parent.mkdir(parents=True, exist_ok=True)
    storage_path.write_text("{bad-json: /nas/private/book.epub", encoding="utf-8")
    app.dependency_overrides[get_bookmark_service] = lambda: service
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id=user_id,
        user_role="editor",
    )
    monkeypatch.setattr(bookmark_service, "logger", capture_logger)

    try:
        with TestClient(app) as client:
            response = client.get(f"/api/bookmarks/{job_id}")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"job_id": job_id, "bookmarks": []}
    logs = "\n".join(capture_logger.messages)
    assert "Bookmark storage could not be loaded" in logs
    assert user_id not in logs
    assert "alice_secret_example_test" not in logs
    assert job_id not in logs
    assert str(storage_path) not in logs
    assert "/nas/private/book.epub" not in logs
    assert "bad-json" not in logs
