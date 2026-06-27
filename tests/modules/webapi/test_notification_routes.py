from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from prometheus_client.parser import text_string_to_metric_families

from modules.notifications.notification_service import NotificationResult
from modules.webapi.application import create_app
from modules.webapi.dependencies import (
    RequestUserContext,
    get_notification_service,
    get_request_user,
)
from modules.webapi.routes import notification_routes

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


def _has_notification_metric_count(
    metrics_text: str,
    *,
    operation: str,
    result: str,
) -> bool:
    families = {family.name: family for family in text_string_to_metric_families(metrics_text)}
    metric = families["ebook_tools_notification_route_duration_seconds"]
    return any(
        sample.name.endswith("_count")
        and sample.labels.get("operation") == operation
        and sample.labels.get("result") == result
        and sample.value >= 1
        for sample in metric.samples
    )


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
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, service = notification_client
    capture_logger = _ListLogger()
    monkeypatch.setattr(notification_routes, "logger", capture_logger)
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
    metrics_response = client.get("/metrics")

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
    assert _has_notification_metric_count(
        metrics_response.text,
        operation="register_device",
        result="success",
    )
    assert _has_notification_metric_count(
        metrics_response.text,
        operation="preferences_get",
        result="success",
    )
    assert _has_notification_metric_count(
        metrics_response.text,
        operation="preferences_update",
        result="success",
    )
    assert _has_notification_metric_count(
        metrics_response.text,
        operation="test",
        result="success",
    )
    assert _has_notification_metric_count(
        metrics_response.text,
        operation="rich_test",
        result="success",
    )
    assert _has_notification_metric_count(
        metrics_response.text,
        operation="unregister_device",
        result="success",
    )
    assert _has_notification_metric_count(
        metrics_response.text,
        operation="unregister_device",
        result="not_found",
    )

    logs = "\n".join(capture_logger.messages)
    assert "Notification route operation=register_device result=success" in logs
    assert "Notification route operation=preferences_get result=success" in logs
    assert "Notification route operation=preferences_update result=success" in logs
    assert "Notification route operation=test result=success" in logs
    assert "Notification route operation=rich_test result=success" in logs
    assert "Notification route operation=unregister_device result=success" in logs
    assert "Notification route operation=unregister_device result=not_found" in logs
    assert "alice" not in logs
    assert token not in logs
    assert "Fifo Ipad Pro" not in logs
    assert "Sample Book" not in logs
    assert "Sample Author" not in logs
    assert "/api/jobs/job-1/cover" not in logs


def test_notification_device_routes_normalize_tokens(
    notification_client: tuple[TestClient, _StubNotificationService],
) -> None:
    client, service = notification_client
    token = "0123456789abcdef0123456789abcdef"

    register_response = client.post(
        "/api/notifications/devices",
        json={
            "token": f"  {token}  ",
            "device_name": "Fifo Ipad Pro",
            "bundle_id": "com.example.InteractiveReader",
            "environment": "development",
        },
    )
    unregister_response = client.delete(f"/api/notifications/devices/%20%20{token}%20%20")

    assert register_response.status_code == 200
    assert register_response.json() == {
        "registered": True,
        "device_id": token[:16],
    }
    assert service.register_calls[-1]["token"] == token
    assert unregister_response.status_code == 200
    assert unregister_response.json() == {"unregistered": True}
    assert service.unregister_calls[-1] == {
        "user_id": "alice",
        "token": token,
    }


def test_notification_unregister_rejects_blank_token_without_service_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _StubNotificationService()
    capture_logger = _ListLogger()
    monkeypatch.setattr(notification_routes, "logger", capture_logger)

    def fail_unregister(*args, **kwargs):
        raise AssertionError("unregister_device_token should not be called for blank tokens")

    service.unregister_device_token = fail_unregister
    app = create_app()
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="alice",
        user_role="editor",
    )
    app.dependency_overrides[get_notification_service] = lambda: service

    try:
        with TestClient(app) as client:
            response = client.delete("/api/notifications/devices/%20%20%20")
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json() == {
        "detail": notification_routes.NOTIFICATION_DEVICE_TOKEN_NOT_FOUND_MESSAGE
    }
    assert _has_notification_metric_count(
        metrics_response.text,
        operation="unregister_device",
        result="not_found",
    )
    logs = "\n".join(capture_logger.messages)
    assert "Notification route operation=unregister_device result=not_found" in logs


def test_notification_preferences_response_validation_uses_generic_detail_before_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _StubNotificationService()
    service.preferences["devices"] = [
        {
            "device_name": "Secret Device",
            "bundle_id": "com.example.InteractiveReader",
        }
    ]
    capture_logger = _ListLogger()
    monkeypatch.setattr(notification_routes, "logger", capture_logger)
    app = create_app()
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="alice",
        user_role="editor",
    )
    app.dependency_overrides[get_notification_service] = lambda: service

    try:
        with TestClient(app) as client:
            response = client.get("/api/notifications/preferences")
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json() == {"detail": notification_routes.NOTIFICATION_UNAVAILABLE_MESSAGE}
    assert _has_notification_metric_count(
        metrics_response.text,
        operation="preferences_get",
        result="error",
    )
    logs = "\n".join(capture_logger.messages)
    assert "Notification route operation=preferences_get result=error" in logs
    assert "Notification route operation=preferences_get result=success" not in logs
    rendered = response.text + metrics_response.text + logs
    assert "Secret Device" not in rendered
    assert "alice" not in rendered


def test_notification_test_route_reports_disabled_server(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _StubNotificationService(enabled=False)
    capture_logger = _ListLogger()
    monkeypatch.setattr(notification_routes, "logger", capture_logger)
    app = create_app()
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="alice",
        user_role="editor",
    )
    app.dependency_overrides[get_notification_service] = lambda: service

    try:
        with TestClient(app) as client:
            response = client.post("/api/notifications/test")
            rich_response = client.post("/api/notifications/test/rich")
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "sent": 0,
        "failed": 0,
        "message": "Push notifications are not configured on the server",
    }
    assert rich_response.status_code == 200
    assert service.test_calls == []
    assert service.rich_test_calls == []
    assert _has_notification_metric_count(metrics_response.text, operation="test", result="disabled")
    assert _has_notification_metric_count(metrics_response.text, operation="rich_test", result="disabled")
    logs = "\n".join(capture_logger.messages)
    assert "Notification route operation=test result=disabled" in logs
    assert "Notification route operation=rich_test result=disabled" in logs


def test_notification_routes_require_authenticated_user(monkeypatch: pytest.MonkeyPatch) -> None:
    capture_logger = _ListLogger()
    monkeypatch.setattr(notification_routes, "logger", capture_logger)
    app = create_app()
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id=None,
        user_role=None,
    )
    app.dependency_overrides[get_notification_service] = lambda: _StubNotificationService()

    try:
        with TestClient(app) as client:
            response = client.get("/api/notifications/preferences")
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 401
    assert _has_notification_metric_count(
        metrics_response.text,
        operation="preferences_get",
        result="unauthorized",
    )
    logs = "\n".join(capture_logger.messages)
    assert "Notification route operation=preferences_get result=unauthorized" in logs


@pytest.mark.parametrize(
    ("operation", "method", "path"),
    [
        ("register_device", "post", "/api/notifications/devices"),
        ("unregister_device", "delete", "/api/notifications/devices/0123456789abcdef0123456789abcdef"),
        ("test", "post", "/api/notifications/test"),
        ("rich_test", "post", "/api/notifications/test/rich"),
        ("preferences_get", "get", "/api/notifications/preferences"),
        ("preferences_update", "put", "/api/notifications/preferences"),
    ],
)
def test_notification_route_storage_errors_use_token_safe_response(
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
    method: str,
    path: str,
) -> None:
    service = _StubNotificationService()
    capture_logger = _ListLogger()
    monkeypatch.setattr(notification_routes, "logger", capture_logger)

    def fail(*args, **kwargs):
        raise RuntimeError(
            "notification store failed for alice token 0123456789abcdef0123456789abcdef "
            "device Fifo Ipad Pro at /Volumes/Data/private/users.json"
        )

    if operation == "register_device":
        service.register_device_token = fail
    elif operation == "unregister_device":
        service.unregister_device_token = fail
    elif operation == "test":
        service.send_test_notification = fail
    elif operation == "rich_test":
        service.send_rich_test_notification = fail
    elif operation == "preferences_get":
        service.get_preferences = fail
    else:
        service.update_preferences = fail

    app = create_app()
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="alice",
        user_role="editor",
    )
    app.dependency_overrides[get_notification_service] = lambda: service

    token = "0123456789abcdef0123456789abcdef"
    try:
        with TestClient(app) as client:
            if operation == "register_device":
                response = client.post(
                    path,
                    json={
                        "token": token,
                        "device_name": "Fifo Ipad Pro",
                        "bundle_id": "com.example.InteractiveReader",
                        "environment": "development",
                    },
                )
            elif operation == "preferences_update":
                response = client.put(
                    path,
                    json={"job_completed": False, "job_failed": True},
                )
            elif operation == "rich_test":
                response = client.post(
                    path,
                    params={
                        "title": "Secret Book",
                        "subtitle": "Secret Author",
                        "cover_url": "/api/jobs/secret-job/cover",
                    },
                )
            else:
                response = getattr(client, method)(path)
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json() == {"detail": notification_routes.NOTIFICATION_UNAVAILABLE_MESSAGE}
    assert "alice" not in response.text
    assert token not in response.text
    assert "Fifo Ipad Pro" not in response.text
    assert "/Volumes/Data" not in response.text
    assert "Secret Book" not in response.text
    assert _has_notification_metric_count(
        metrics_response.text,
        operation=operation,
        result="error",
    )

    logs = "\n".join(capture_logger.messages)
    assert f"Notification route operation={operation} result=error" in logs
    assert "alice" not in logs
    assert token not in logs
    assert "Fifo Ipad Pro" not in logs
    assert "/Volumes/Data" not in logs
    assert "Secret Book" not in logs
