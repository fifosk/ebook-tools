from __future__ import annotations

from typing import Iterator, Tuple

import pytest
from fastapi.testclient import TestClient

from modules.user_management import AuthService
from modules.user_management.local_user_store import LocalUserStore
from modules.user_management.session_manager import SessionManager
from modules.webapi.application import create_app
from modules.webapi.dependencies import get_auth_service


@pytest.fixture
def media_client(tmp_path) -> Iterator[Tuple[TestClient, str, str]]:
    user_store_path = tmp_path / "users.json"
    session_file = tmp_path / "sessions.json"

    service = AuthService(
        LocalUserStore(storage_path=user_store_path),
        SessionManager(session_file=session_file),
    )

    service.user_store.create_user("viewer", "secret", roles=["viewer"])
    service.user_store.create_user("producer", "secret", roles=["media_producer"])

    viewer_token = service.session_manager.create_session("viewer")
    producer_token = service.session_manager.create_session("producer")

    app = create_app()
    app.dependency_overrides[get_auth_service] = lambda: service

    with TestClient(app) as client:
        yield client, viewer_token, producer_token

    app.dependency_overrides.clear()


def test_media_generation_requires_authentication(media_client) -> None:
    client, *_ = media_client

    response = client.post(
        "/api/media/generate",
        json={"job_id": "job-1", "media_type": "audio"},
    )

    assert response.status_code == 401
    payload = response.json()
    assert payload["error"] == "missing_token"


def test_media_generation_requires_elevated_role(media_client) -> None:
    client, viewer_token, _ = media_client

    response = client.post(
        "/api/media/generate",
        json={"job_id": "job-1", "media_type": "audio"},
        headers={"Authorization": f"Bearer {viewer_token}"},
    )

    assert response.status_code == 403
    payload = response.json()
    assert payload["error"] == "insufficient_permissions"


def test_media_generation_accepts_authorised_user(media_client) -> None:
    client, _, producer_token = media_client

    response = client.post(
        "/api/media/generate",
        json={
            "job_id": "job-123",
            "media_type": "video",
            "parameters": {"quality": "draft"},
            "notes": "Initial render",
        },
        headers={"Authorization": f"Bearer {producer_token}"},
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["status"] == "accepted"
    assert payload["job_id"] == "job-123"
    assert payload["media_type"] == "video"
    assert payload["requested_by"] == "producer"
    assert payload["parameters"] == {"quality": "draft"}
    assert payload["notes"] == "Initial render"
    assert payload["request_id"]
