from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from prometheus_client.parser import text_string_to_metric_families

from modules.user_management import AuthService, LocalUserStore, SessionManager
from modules.webapi.application import create_app
from modules.webapi.dependencies import get_auth_service

pytestmark = pytest.mark.webapi


@pytest.fixture
def auth_client(tmp_path) -> Iterator[tuple[TestClient, AuthService, str]]:
    service = AuthService(
        LocalUserStore(storage_path=tmp_path / "users.json"),
        SessionManager(session_file=tmp_path / "sessions.json"),
    )
    service.user_store.create_user(
        "reader",
        "secret",
        roles=["viewer"],
        metadata={
            "email": "reader@example.test",
            "first_name": "Test",
            "last_name": "Reader",
            "last_login": "2026-06-21T12:00:00+00:00",
        },
    )
    token = service.session_manager.create_session("reader")

    app = create_app()
    app.dependency_overrides[get_auth_service] = lambda: service
    with TestClient(app) as client:
        yield client, service, token
    app.dependency_overrides.clear()


def test_login_session_logout_cycle_matches_device_contract(auth_client) -> None:
    client, _, _ = auth_client

    login_response = client.post(
        "/api/auth/login",
        json={"username": "reader", "password": "secret"},
    )

    assert login_response.status_code == 200
    login_payload = login_response.json()
    issued_token = login_payload["token"]
    assert isinstance(issued_token, str)
    assert issued_token
    assert login_payload["user"]["username"] == "reader"
    assert login_payload["user"]["role"] == "viewer"
    assert login_payload["user"]["email"] == "reader@example.test"
    assert login_payload["user"]["first_name"] == "Test"
    assert login_payload["user"]["last_name"] == "Reader"
    assert login_payload["user"]["last_login"] != "2026-06-21T12:00:00+00:00"
    datetime.fromisoformat(login_payload["user"]["last_login"])
    assert "secret" not in login_response.text

    session_response = client.get(
        "/api/auth/session",
        headers={"Authorization": f"Bearer {issued_token}"},
    )

    assert session_response.status_code == 200
    assert session_response.json() == login_payload

    logout_response = client.post(
        "/api/auth/logout",
        headers={"Authorization": f"Bearer {issued_token}"},
    )
    assert logout_response.status_code == 204

    restored_response = client.get(
        "/api/auth/session",
        headers={"Authorization": f"Bearer {issued_token}"},
    )
    assert restored_response.status_code == 401


def test_session_status_returns_compact_user_payload(auth_client) -> None:
    client, _, token = auth_client

    response = client.get(
        "/api/auth/session",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "token": token,
        "user": {
            "username": "reader",
            "role": "viewer",
            "email": "reader@example.test",
            "first_name": "Test",
            "last_name": "Reader",
            "last_login": "2026-06-21T12:00:00+00:00",
        },
    }


@pytest.mark.parametrize(
    "authorization",
    [
        None,
        "Basic invalid",
        "Bearer invalid",
    ],
)
def test_session_status_rejects_missing_or_invalid_tokens(auth_client, authorization: str | None) -> None:
    client, _, _ = auth_client

    headers = {"Authorization": authorization} if authorization is not None else {}
    response = client.get("/api/auth/session", headers=headers)

    assert response.status_code == 401


def test_auth_duration_metric_records_session_result(auth_client) -> None:
    client, _, token = auth_client

    response = client.get(
        "/api/auth/session",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200

    metrics = client.get("/metrics")
    families = {f.name: f for f in text_string_to_metric_families(metrics.text)}
    auth_duration = families.get("ebook_tools_auth_duration_seconds")
    assert auth_duration is not None

    count_samples = [
        sample
        for sample in auth_duration.samples
        if sample.name == "ebook_tools_auth_duration_seconds_count"
        and sample.labels.get("operation") == "session"
        and sample.labels.get("result") == "success"
    ]
    assert count_samples
    assert any(sample.value >= 1.0 for sample in count_samples)
