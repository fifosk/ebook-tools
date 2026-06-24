from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Any

import pytest

from modules.notifications import apns_service as apns_module
from modules.notifications.apns_service import APNsConfig, APNsResponse, NotificationRequest
from modules.notifications.notification_service import NotificationService
from modules.user_management.local_user_store import LocalUserStore


class _ListLogger:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def debug(self, message: str, *args: object, **_: object) -> None:
        self.messages.append(message % args if args else message)

    def info(self, message: str, *args: object, **_: object) -> None:
        self.messages.append(message % args if args else message)

    def warning(self, message: str, *args: object, **_: object) -> None:
        self.messages.append(message % args if args else message)

    def error(self, message: str, *args: object, **_: object) -> None:
        self.messages.append(message % args if args else message)


class _FakeAPNs:
    async def send_batch(self, requests: list[NotificationRequest]) -> list[APNsResponse]:
        return [
            APNsResponse(success=True, device_token=request.device_token, status_code=200)
            for request in requests
        ]


class _FakeAPNsHTTPResponse:
    status_code = 200
    headers = {"apns-id": "apns-response-id"}

    def json(self) -> dict[str, Any]:
        return {}


class _FakeAsyncClient:
    def __init__(self, **_: Any) -> None:
        pass

    async def __aenter__(self) -> _FakeAsyncClient:
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    async def post(self, *_: object, **__: object) -> _FakeAPNsHTTPResponse:
        return _FakeAPNsHTTPResponse()


class _FakeHTTPX:
    AsyncClient = _FakeAsyncClient


def test_notification_service_logs_omit_user_job_device_and_token(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    logger = _ListLogger()
    monkeypatch.setattr("modules.notifications.notification_service.logger", logger)

    user_id = "secret-office-ipad-user"
    device_name = "Secret iPad Pro"
    token = "0123456789abcdef0123456789abcdef"
    job_id = "secret-dan-brown-continuation-job"
    store = LocalUserStore(tmp_path / "users.json")
    store.create_user(user_id, "password", metadata={})
    service = NotificationService(_FakeAPNs(), store, api_base_url="http://api.local")

    assert service.register_device_token(
        user_id=user_id,
        token=token,
        device_name=device_name,
        bundle_id="com.example.InteractiveReader",
        environment="development",
    )
    assert service.update_preferences(user_id=user_id, job_completed=False, job_failed=True)
    disabled = asyncio.run(
        service.notify_job_completed(
            user_id=user_id,
            job_id=job_id,
            job_label="Secret Dan Brown Continuation",
            status="completed",
        )
    )
    assert service.update_preferences(user_id=user_id, job_completed=True, job_failed=True)
    delivered = asyncio.run(
        service.notify_job_completed(
            user_id=user_id,
            job_id=job_id,
            job_label="Secret Dan Brown Continuation",
            status="completed",
            cover_url="/api/jobs/secret-dan-brown-continuation-job/cover",
        )
    )
    assert service.unregister_device_token(user_id=user_id, token=token)

    assert disabled.reason == "disabled_by_preference"
    assert delivered.sent == 1
    rendered_logs = "\n".join(logger.messages)
    assert "Notification device registration result=success action=created devices=1" in rendered_logs
    assert "Notification preferences update result=success job_completed=False job_failed=True" in rendered_logs
    assert "Notification send skipped result=job_completed_disabled" in rendered_logs
    assert "Notification send result=success sent=1 total=1 failed=0 invalid_tokens=0 rich=True status=completed" in rendered_logs
    assert "Notification device unregister result=success remaining_devices=0" in rendered_logs
    assert user_id not in rendered_logs
    assert device_name not in rendered_logs
    assert token not in rendered_logs
    assert token[:16] not in rendered_logs
    assert job_id not in rendered_logs
    assert job_id[:8] not in rendered_logs
    assert "Secret Dan Brown Continuation" not in rendered_logs


def test_apns_success_log_omits_device_token(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    logger = _ListLogger()
    token = "abcdef0123456789abcdef0123456789"
    key_path = tmp_path / "AuthKey_TEST.p8"
    key_path.write_text("private key", encoding="utf-8")
    service = apns_module.APNsService(
        APNsConfig(
            key_id="KEYID",
            team_id="TEAMID",
            bundle_id="com.example.InteractiveReader",
            key_path=key_path,
        )
    )
    service._jwt_token = "jwt-token"
    service._jwt_expires_at = time.time() + 60

    monkeypatch.setattr(apns_module, "logger", logger)
    monkeypatch.setattr(apns_module, "httpx", _FakeHTTPX)

    response = asyncio.run(
        service.send_notification(
            NotificationRequest(
                device_token=token,
                title="Test",
                body="Body",
            )
        )
    )

    assert response.success is True
    rendered_logs = "\n".join(logger.messages)
    assert "APNs notification send result=success status=200" in rendered_logs
    assert token not in rendered_logs
    assert token[:16] not in rendered_logs
