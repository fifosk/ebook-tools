from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest
from fastapi.testclient import TestClient
from prometheus_client.parser import text_string_to_metric_families

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

    families = {
        family.name: family
        for family in text_string_to_metric_families(metrics_response.text)
    }
    metric = families["ebook_tools_library_route_duration_seconds"]
    assert any(
        sample.labels.get("operation") == "list_items"
        and sample.labels.get("result") == "success"
        and sample.name.endswith("_count")
        and sample.value >= 1
        for sample in metric.samples
    )
