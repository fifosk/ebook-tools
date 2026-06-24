from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from modules.notifications.notification_service import NotificationResult
from modules.webapi.application import create_app
from modules.webapi.dependencies import (
    RequestUserContext,
    get_notification_service,
    get_request_user,
)

pytestmark = pytest.mark.webapi


class _StubNotificationService:
    def __init__(self, *, enabled: bool = True) -> None:
        self.is_enabled = enabled
        self.register_calls: list[dict[str, str]] = []
        self.unregister_calls: list[dict[str, str]] = []
        self.preference_updates: list[dict[str, bool]] = []
        self.test_calls: list[str] = []
        self.rich_test_calls: list[dict[str, str | None]] = []
        self.tokens: set[str] = set()
        self.preferences: dict[str, Any] = {
            "job_completed": True,
            "job_failed": True,
            "devices": [],
        }

    def register_device_token(
        self,
        *,
        user_id: str,
        token: str,
        device_name: str,
        bundle_id: str,
        environment: str,
    ) -> bool:
        self.register_calls.append(
            {
                "user_id": user_id,
                "token": token,
                "device_name": device_name,
                "bundle_id": bundle_id,
                "environment": environment,
            }
        )
        self.tokens.add(token)
        self.preferences["devices"] = [
            {
                "device_name": device_name,
                "bundle_id": bundle_id,
                "environment": environment,
                "registered_at": "2026-06-24T12:00:00+00:00",
                "last_used_at": "2026-06-24T12:01:00+00:00",
            }
        ]
        return True

    def unregister_device_token(self, *, user_id: str, token: str) -> bool:
        self.unregister_calls.append({"user_id": user_id, "token": token})
        if token not in self.tokens:
            return False
        self.tokens.remove(token)
        self.preferences["devices"] = []
        return True

    async def send_test_notification(self, user_id: str) -> NotificationResult:
        self.test_calls.append(user_id)
        if not self.tokens:
            return NotificationResult(sent=0, failed=0, reason="no_devices")
        return NotificationResult(sent=len(self.tokens), failed=0)

    async def send_rich_test_notification(
        self,
        user_id: str,
        *,
        title: str | None = None,
        subtitle: str | None = None,
        cover_url: str | None = None,
    ) -> NotificationResult:
        self.rich_test_calls.append(
            {
                "user_id": user_id,
                "title": title,
                "subtitle": subtitle,
                "cover_url": cover_url,
            }
        )
        if not self.tokens:
            return NotificationResult(sent=0, failed=0, reason="no_devices")
        return NotificationResult(sent=len(self.tokens), failed=0)

    def get_preferences(self, user_id: str) -> dict[str, Any]:
        assert user_id == "alice"
        return dict(self.preferences)

    def update_preferences(
        self,
        *,
        user_id: str,
        job_completed: bool,
        job_failed: bool,
    ) -> bool:
        self.preference_updates.append(
            {
                "user_id": user_id,
                "job_completed": job_completed,
                "job_failed": job_failed,
            }
        )
        self.preferences["job_completed"] = job_completed
        self.preferences["job_failed"] = job_failed
        return True


@pytest.fixture
def notification_client() -> Iterator[tuple[TestClient, _StubNotificationService]]:
    service = _StubNotificationService()
    app = create_app()
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="alice",
        user_role="editor",
    )
    app.dependency_overrides[get_notification_service] = lambda: service

    with TestClient(app) as client:
        yield client, service

    app.dependency_overrides.clear()


def test_notification_routes_cover_device_preferences_and_test_sends(
    notification_client: tuple[TestClient, _StubNotificationService],
) -> None:
    client, service = notification_client
    token = "0123456789abcdef0123456789abcdef"

    register_response = client.post(
        "/api/notifications/devices",
        json={
            "token": token,
            "device_name": "Fifo Ipad Pro",
            "bundle_id": "com.example.InteractiveReader",
            "environment": "development",
        },
    )
    preferences_response = client.get("/api/notifications/preferences")
    update_response = client.put(
        "/api/notifications/preferences",
        json={"job_completed": False, "job_failed": True},
    )
    test_response = client.post("/api/notifications/test")
    rich_response = client.post(
        "/api/notifications/test/rich",
        params={
            "title": "Sample Book",
            "subtitle": "Sample Author",
            "cover_url": "/api/jobs/job-1/cover",
        },
    )
    unregister_response = client.delete(f"/api/notifications/devices/{token}")
    missing_unregister_response = client.delete(f"/api/notifications/devices/{token}")

    assert register_response.status_code == 200
    assert register_response.json() == {
        "registered": True,
        "device_id": token[:16],
    }
    assert service.register_calls == [
        {
            "user_id": "alice",
            "token": token,
            "device_name": "Fifo Ipad Pro",
            "bundle_id": "com.example.InteractiveReader",
            "environment": "development",
        }
    ]

    assert preferences_response.status_code == 200
    assert preferences_response.json() == {
        "job_completed": True,
        "job_failed": True,
        "devices": [
            {
                "device_name": "Fifo Ipad Pro",
                "bundle_id": "com.example.InteractiveReader",
                "environment": "development",
                "registered_at": "2026-06-24T12:00:00+00:00",
                "last_used_at": "2026-06-24T12:01:00+00:00",
            }
        ],
    }
    assert token not in preferences_response.text

    assert update_response.status_code == 200
    assert update_response.json() == {"updated": True}
    assert service.preference_updates == [
        {
            "user_id": "alice",
            "job_completed": False,
            "job_failed": True,
        }
    ]

    assert test_response.status_code == 200
    assert test_response.json() == {
        "sent": 1,
        "failed": 0,
        "message": "Sent to 1 device(s)",
    }
    assert service.test_calls == ["alice"]

    assert rich_response.status_code == 200
    assert rich_response.json() == {
        "sent": 1,
        "failed": 0,
        "message": "Rich notification sent to 1 device(s)",
    }
    assert service.rich_test_calls == [
        {
            "user_id": "alice",
            "title": "Sample Book",
            "subtitle": "Sample Author",
            "cover_url": "/api/jobs/job-1/cover",
        }
    ]

    assert unregister_response.status_code == 200
    assert unregister_response.json() == {"unregistered": True}
    assert missing_unregister_response.status_code == 404


def test_notification_test_route_reports_disabled_server() -> None:
    service = _StubNotificationService(enabled=False)
    app = create_app()
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="alice",
        user_role="editor",
    )
    app.dependency_overrides[get_notification_service] = lambda: service

    try:
        with TestClient(app) as client:
            response = client.post("/api/notifications/test")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "sent": 0,
        "failed": 0,
        "message": "Push notifications are not configured on the server",
    }
    assert service.test_calls == []


def test_notification_routes_require_authenticated_user() -> None:
    app = create_app()
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id=None,
        user_role=None,
    )
    app.dependency_overrides[get_notification_service] = lambda: _StubNotificationService()

    try:
        with TestClient(app) as client:
            response = client.get("/api/notifications/preferences")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 401
