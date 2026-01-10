from __future__ import annotations

from collections.abc import Iterator
from typing import Tuple

import pytest
from fastapi.testclient import TestClient

from modules.user_management import AuthService, LocalUserStore, SessionManager
from modules.webapi.application import create_app
from modules.webapi.dependencies import get_auth_service


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

    response = client.get("/admin/users")

    assert response.status_code == 401


def test_list_users_requires_admin_role(admin_client) -> None:
    client, _, _, member_token = admin_client

    response = client.get(
        "/admin/users",
        headers={"Authorization": f"Bearer {member_token}"},
    )

    assert response.status_code == 403


def test_list_users_returns_serialized_payload(admin_client) -> None:
    client, _, admin_token, _ = admin_client

    response = client.get(
        "/admin/users",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    usernames = {item["username"] for item in payload["users"]}
    assert {"admin", "member"}.issubset(usernames)


def test_create_user_provisions_account(admin_client) -> None:
    client, service, admin_token, _ = admin_client

    response = client.post(
        "/admin/users",
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


def test_update_user_details_persists_profile_metadata(admin_client) -> None:
    client, service, admin_token, _ = admin_client

    response = client.put(
        "/admin/users/member",
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


def test_suspend_user_updates_metadata_and_clears_sessions(admin_client) -> None:
    client, service, admin_token, member_token = admin_client

    response = client.post(
        "/admin/users/member/suspend",
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
        "/admin/users/member/activate",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    payload = response.json()["user"]
    assert payload["status"] == "active"
    assert payload["is_suspended"] is False


def test_reset_password_invalidates_existing_sessions(admin_client) -> None:
    client, service, admin_token, member_token = admin_client

    response = client.post(
        "/admin/users/member/password",
        json={"password": "new-pass"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 204
    assert service.session_manager.get_session(member_token) is None


def test_delete_user_removes_account(admin_client) -> None:
    client, service, admin_token, _ = admin_client

    response = client.delete(
        "/admin/users/member",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 204
    assert service.user_store.get_user("member") is None


def test_delete_user_rejects_self_deletion(admin_client) -> None:
    client, _, admin_token, _ = admin_client

    response = client.delete(
        "/admin/users/admin",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 400
