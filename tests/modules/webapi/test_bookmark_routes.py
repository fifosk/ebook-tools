from __future__ import annotations

from dataclasses import asdict

import pytest
from fastapi.testclient import TestClient

from modules.services.bookmark_service import BookmarkEntry
from modules.webapi.application import create_app
from modules.webapi.dependencies import (
    RequestUserContext,
    get_bookmark_service,
    get_request_user,
)

pytestmark = pytest.mark.webapi


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


def test_bookmark_routes_scope_calls_to_authenticated_user() -> None:
    app = create_app()
    service = _StubBookmarkService()
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


def test_bookmark_routes_require_authenticated_user() -> None:
    app = create_app()
    app.dependency_overrides[get_bookmark_service] = lambda: _StubBookmarkService()
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id=None,
        user_role="anonymous",
    )

    try:
        with TestClient(app) as client:
            response = client.get("/api/bookmarks/job-1")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 401
