from __future__ import annotations

import logging
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from modules.services.file_locator import FileLocator
from modules.user_management import AuthService, LocalUserStore, SessionManager
from modules.webapi.application import create_app
from modules.webapi.dependencies import get_auth_service
from modules.webapi.routers import reading_beds

pytestmark = pytest.mark.webapi


@pytest.fixture
def reading_bed_client(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> Iterator[tuple[TestClient, str, Path]]:
    storage_root = tmp_path / "storage"

    def _locator(*_: object, **__: object) -> FileLocator:
        return FileLocator(storage_dir=storage_root)

    monkeypatch.setattr(reading_beds, "FileLocator", _locator)

    auth_service = AuthService(
        LocalUserStore(storage_path=tmp_path / "users.json"),
        SessionManager(session_file=tmp_path / "sessions.json"),
    )
    auth_service.user_store.create_user("admin", "secret", roles=["admin"])
    admin_token = auth_service.session_manager.create_session("admin")

    app = create_app()
    app.dependency_overrides[get_auth_service] = lambda: auth_service

    with TestClient(app) as client:
        yield client, admin_token, storage_root

    app.dependency_overrides.clear()


def test_reading_bed_routes_manage_uploaded_bed_lifecycle(
    reading_bed_client: tuple[TestClient, str, Path],
) -> None:
    client, admin_token, storage_root = reading_bed_client
    auth_headers = {"Authorization": f"Bearer {admin_token}"}

    initial_response = client.get("/api/reading-beds")

    assert initial_response.status_code == 200
    initial_payload = initial_response.json()
    assert initial_payload["default_id"] == "lost-in-the-pages"
    assert initial_payload["beds"] == [
        {
            "id": "lost-in-the-pages",
            "label": "Lost in the Pages",
            "url": "/assets/reading-beds/lost-in-the-pages.mp3",
            "kind": "bundled",
            "content_type": "audio/mpeg",
            "is_default": True,
        }
    ]

    upload_response = client.post(
        "/api/admin/reading-beds",
        data={"label": "Rain Room"},
        files={"file": ("ambient.mp3", b"fake mp3 bytes", "audio/mpeg")},
        headers=auth_headers,
    )

    assert upload_response.status_code == 201
    uploaded = upload_response.json()
    assert uploaded == {
        "id": "rain-room",
        "label": "Rain Room",
        "url": "/api/reading-beds/rain-room/file",
        "kind": "uploaded",
        "content_type": "audio/mpeg",
        "is_default": False,
    }

    file_response = client.get(uploaded["url"])

    assert file_response.status_code == 200
    assert file_response.content == b"fake mp3 bytes"
    assert file_response.headers["content-type"].startswith("audio/mpeg")

    update_response = client.patch(
        "/api/admin/reading-beds/rain-room",
        json={"label": "Rain Room Focus", "set_default": True},
        headers=auth_headers,
    )

    assert update_response.status_code == 200
    assert update_response.json()["label"] == "Rain Room Focus"
    assert update_response.json()["is_default"] is True

    catalog_response = client.get("/api/reading-beds")
    catalog = catalog_response.json()

    assert catalog_response.status_code == 200
    assert catalog["default_id"] == "rain-room"
    assert [entry["id"] for entry in catalog["beds"]] == [
        "lost-in-the-pages",
        "rain-room",
    ]
    assert {entry["id"]: entry["is_default"] for entry in catalog["beds"]} == {
        "lost-in-the-pages": False,
        "rain-room": True,
    }

    stored_file = storage_root / "reading_beds" / "files" / "rain-room.mp3"
    assert stored_file.exists()

    delete_response = client.delete(
        "/api/admin/reading-beds/rain-room",
        headers=auth_headers,
    )

    assert delete_response.status_code == 200
    assert delete_response.json() == {
        "deleted": True,
        "default_id": "lost-in-the-pages",
    }
    assert not stored_file.exists()

    final_response = client.get("/api/reading-beds")
    assert final_response.status_code == 200
    assert final_response.json()["default_id"] == "lost-in-the-pages"


def test_reading_bed_admin_routes_require_admin(
    reading_bed_client: tuple[TestClient, str, Path],
) -> None:
    client, _, _ = reading_bed_client

    response = client.post(
        "/api/admin/reading-beds",
        data={"label": "No Token"},
        files={"file": ("ambient.mp3", b"fake mp3 bytes", "audio/mpeg")},
    )

    assert response.status_code == 401


def test_reading_bed_missing_file_logs_without_paths_or_ids(
    reading_bed_client: tuple[TestClient, str, Path],
    caplog: pytest.LogCaptureFixture,
) -> None:
    client, admin_token, storage_root = reading_bed_client
    auth_headers = {"Authorization": f"Bearer {admin_token}"}
    caplog.set_level(logging.WARNING, logger="ebook_tools")

    upload_response = client.post(
        "/api/admin/reading-beds",
        data={"label": "Secret Rain Room"},
        files={"file": ("secret-rain.mp3", b"fake mp3 bytes", "audio/mpeg")},
        headers=auth_headers,
    )
    uploaded = upload_response.json()
    stored_file = storage_root / "reading_beds" / "files" / "secret-rain-room.mp3"
    assert stored_file.exists()
    stored_file.unlink()

    response = client.get(uploaded["url"])

    assert response.status_code == 404
    assert response.json()["detail"] == "Reading bed file missing"

    rendered_logs = caplog.text
    assert "Reading bed fetch result=file_not_found" in rendered_logs
    assert "secret-rain-room" not in rendered_logs
    assert "secret-rain.mp3" not in rendered_logs
    assert str(stored_file) not in rendered_logs
