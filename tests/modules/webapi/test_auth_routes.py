from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

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
