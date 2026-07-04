from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Tuple

import pytest
from fastapi.testclient import TestClient

from modules.user_management import AuthService, LocalUserStore, SessionManager
from modules.webapi import admin_routes
from modules.webapi.application import create_app
from modules.webapi.dependencies import get_auth_service

pytestmark = pytest.mark.webapi


def _build_auth_service(tmp_path) -> Tuple[AuthService, str, str]:
    store_path = tmp_path / "users.json"
    sessions_path = tmp_path / "sessions.json"
    service = AuthService(
        LocalUserStore(storage_path=store_path),
        SessionManager(session_file=sessions_path),
    )

    service.user_store.create_user("admin", "secret", roles=["admin"])
    service.user_store.create_user("member", "secret", roles=["viewer"])

    admin_token = service.session_manager.create_session("admin")
    member_token = service.session_manager.create_session("member")

    return service, admin_token, member_token


@pytest.fixture
def admin_client(tmp_path) -> Iterator[Tuple[TestClient, AuthService, str, str]]:
    service, admin_token, member_token = _build_auth_service(tmp_path)
    app = create_app()
    app.dependency_overrides[get_auth_service] = lambda: service

    with TestClient(app) as client:
        yield client, service, admin_token, member_token

    app.dependency_overrides.clear()


def test_list_users_requires_authentication(admin_client) -> None:
    client, *_ = admin_client

    response = client.get("/api/admin/users")

    assert response.status_code == 401


def test_list_users_requires_admin_role(admin_client) -> None:
    client, _, _, member_token = admin_client

    response = client.get(
        "/api/admin/users",
        headers={"Authorization": f"Bearer {member_token}"},
    )

    assert response.status_code == 403


def test_list_users_returns_serialized_payload(admin_client) -> None:
    client, _, admin_token, _ = admin_client

    response = client.get(
        "/api/admin/users",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    usernames = {item["username"] for item in payload["users"]}
    assert {"admin", "member"}.issubset(usernames)


def test_create_user_provisions_account(admin_client) -> None:
    client, service, admin_token, _ = admin_client

    response = client.post(
        "/api/admin/users",
        json={
            "username": "newbie",
            "password": "hunter2",
            "roles": ["viewer"],
            "email": "newbie@example.com",
            "first_name": "New",
            "last_name": "User",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["user"]["username"] == "newbie"
    assert body["user"]["status"] == "active"
    assert body["user"]["email"] == "newbie@example.com"
    assert body["user"]["first_name"] == "New"
    assert body["user"]["last_name"] == "User"
    assert service.user_store.get_user("newbie") is not None


def test_admin_user_routes_use_shared_route_id_normalizer() -> None:
    source = Path(admin_routes.__file__).read_text(encoding="utf-8")

    assert "from .route_ids import normalize_route_id" in source
    assert "def _normalize_route_id" not in source
    assert "normalized_username = normalize_route_id(username)" in source
    assert "auth_service.user_store.get_user(normalized_username)" in source
    assert "auth_service.user_store.update_user(normalized_username" in source
    assert "auth_service.user_store.delete_user(normalized_username)" in source
    assert "clear_sessions_for_user(normalized_username)" in source


def test_update_user_details_persists_profile_metadata(admin_client) -> None:
    client, service, admin_token, _ = admin_client

    response = client.put(
        "/api/admin/users/member",
        json={
            "email": "member@example.com",
            "first_name": "Member",
            "last_name": "User",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    payload = response.json()["user"]
    assert payload["email"] == "member@example.com"
    assert payload["first_name"] == "Member"
    assert payload["last_name"] == "User"

    record = service.user_store.get_user("member")
    assert record is not None
    assert record.metadata.get("email") == "member@example.com"
    assert record.metadata.get("first_name") == "Member"
    assert record.metadata.get("last_name") == "User"


def test_admin_user_routes_normalize_padded_username(admin_client) -> None:
    client, service, admin_token, member_token = admin_client
    headers = {"Authorization": f"Bearer {admin_token}"}

    update_response = client.put(
        "/api/admin/users/%20%20member%20%20",
        json={"email": "trimmed@example.com"},
        headers=headers,
    )
    suspend_response = client.post(
        "/api/admin/users/%20%20member%20%20/suspend",
        headers=headers,
    )
    activate_response = client.post(
        "/api/admin/users/%20%20member%20%20/activate",
        headers=headers,
    )
    password_response = client.post(
        "/api/admin/users/%20%20member%20%20/password",
        json={"password": "new-pass"},
        headers=headers,
    )
    delete_response = client.delete(
        "/api/admin/users/%20%20member%20%20",
        headers=headers,
    )

    assert update_response.status_code == 200
    assert update_response.json()["user"]["username"] == "member"
    assert update_response.json()["user"]["email"] == "trimmed@example.com"
    assert suspend_response.status_code == 200
    assert suspend_response.json()["user"]["status"] == "suspended"
    assert service.session_manager.get_session(member_token) is None
    assert activate_response.status_code == 200
    assert activate_response.json()["user"]["status"] == "active"
    assert password_response.status_code == 204
    assert delete_response.status_code == 204
    assert service.user_store.get_user("member") is None


def test_admin_user_routes_reject_blank_username(admin_client) -> None:
    client, service, admin_token, _ = admin_client
    headers = {"Authorization": f"Bearer {admin_token}"}

    update_response = client.put(
        "/api/admin/users/%20%20%20",
        json={"email": "nobody@example.com"},
        headers=headers,
    )
    delete_response = client.delete(
        "/api/admin/users/%20%20%20",
        headers=headers,
    )

    assert update_response.status_code == 404
    assert update_response.json() == {"detail": "User not found"}
    assert delete_response.status_code == 404
    assert delete_response.json() == {"detail": "User not found"}
    assert service.user_store.get_user("member") is not None


def test_suspend_user_updates_metadata_and_clears_sessions(admin_client) -> None:
    client, service, admin_token, member_token = admin_client

    response = client.post(
        "/api/admin/users/member/suspend",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    payload = response.json()["user"]
    assert payload["status"] == "suspended"
    assert payload["is_suspended"] is True

    assert service.session_manager.get_session(member_token) is None


def test_activate_user_clears_suspension_flag(admin_client) -> None:
    client, service, admin_token, _ = admin_client
    service.user_store.update_user(
        "member",
        metadata={"suspended": True, "is_suspended": True},
    )

    response = client.post(
        "/api/admin/users/member/activate",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    payload = response.json()["user"]
    assert payload["status"] == "active"
    assert payload["is_suspended"] is False


def test_reset_password_invalidates_existing_sessions(admin_client) -> None:
    client, service, admin_token, member_token = admin_client

    response = client.post(
        "/api/admin/users/member/password",
        json={"password": "new-pass"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 204
    assert service.session_manager.get_session(member_token) is None


def test_delete_user_removes_account(admin_client) -> None:
    client, service, admin_token, _ = admin_client

    response = client.delete(
        "/api/admin/users/member",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 204
    assert service.user_store.get_user("member") is None


def test_delete_user_rejects_self_deletion(admin_client) -> None:
    client, _, admin_token, _ = admin_client

    response = client.delete(
        "/api/admin/users/admin",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 400


def test_delete_user_rejects_padded_self_deletion(admin_client) -> None:
    client, _, admin_token, _ = admin_client

    response = client.delete(
        "/api/admin/users/%20%20admin%20%20",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 400
