from __future__ import annotations

import logging
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from prometheus_client.parser import text_string_to_metric_families

from modules.services.file_locator import FileLocator
from modules.user_management import AuthService, LocalUserStore, SessionManager
from modules.webapi.application import create_app
from modules.webapi.dependencies import get_auth_service
from modules.webapi.routers import reading_beds

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


def _has_reading_bed_metric_count(
    metrics_text: str,
    *,
    operation: str,
    result: str,
) -> bool:
    families = {family.name: family for family in text_string_to_metric_families(metrics_text)}
    metric = families["ebook_tools_reading_bed_route_duration_seconds"]
    return any(
        sample.name.endswith("_count")
        and sample.labels.get("operation") == operation
        and sample.labels.get("result") == result
        and sample.value >= 1
        for sample in metric.samples
    )


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
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, admin_token, storage_root = reading_bed_client
    auth_headers = {"Authorization": f"Bearer {admin_token}"}
    capture_logger = _ListLogger()
    monkeypatch.setattr(reading_beds, "logger", capture_logger)

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

    metrics_response = client.get("/metrics")
    assert metrics_response.status_code == 200
    for operation in ["list", "upload", "fetch", "update", "delete"]:
        assert _has_reading_bed_metric_count(
            metrics_response.text,
            operation=operation,
            result="success",
        )

    logs = "\n".join(capture_logger.messages)
    assert "Reading bed route operation=list result=success" in logs
    assert "Reading bed route operation=upload result=success" in logs
    assert "Reading bed route operation=fetch result=success" in logs
    assert "Reading bed route operation=update result=success" in logs
    assert "Reading bed route operation=delete result=success" in logs
    assert "beds=2" in logs
    assert "bytes=14" in logs
    assert "default_changed=true" in logs
    assert "deleted=true" in logs
    assert "rain-room" not in logs
    assert "Rain Room" not in logs
    assert "ambient.mp3" not in logs
    assert str(stored_file) not in logs


def test_reading_bed_admin_routes_require_admin(
    reading_bed_client: tuple[TestClient, str, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _, _ = reading_bed_client
    capture_logger = _ListLogger()
    monkeypatch.setattr(reading_beds, "logger", capture_logger)

    response = client.post(
        "/api/admin/reading-beds",
        data={"label": "No Token"},
        files={"file": ("ambient.mp3", b"fake mp3 bytes", "audio/mpeg")},
    )

    assert response.status_code == 401
    metrics_response = client.get("/metrics")
    assert metrics_response.status_code == 200
    assert _has_reading_bed_metric_count(
        metrics_response.text,
        operation="upload",
        result="unauthorized",
    )
    logs = "\n".join(capture_logger.messages)
    assert "Reading bed route operation=upload result=unauthorized" in logs
    assert "No Token" not in logs
    assert "ambient.mp3" not in logs


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


@pytest.mark.parametrize(
    ("operation", "method", "path"),
    [
        ("list", "get", "/api/reading-beds"),
        ("fetch", "get", "/api/reading-beds/secret-bed-id/file"),
        ("upload", "post", "/api/admin/reading-beds"),
        ("update", "patch", "/api/admin/reading-beds/secret-bed-id"),
        ("delete", "delete", "/api/admin/reading-beds/secret-bed-id"),
    ],
)
def test_reading_bed_storage_errors_use_token_safe_response(
    reading_bed_client: tuple[TestClient, str, Path],
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
    method: str,
    path: str,
) -> None:
    client, admin_token, _ = reading_bed_client
    capture_logger = _ListLogger()
    monkeypatch.setattr(reading_beds, "logger", capture_logger)

    def fail_manifest(*args, **kwargs):
        raise RuntimeError(
            "reading bed manifest failed for secret-bed-id admin at "
            "/Volumes/Data/private/reading_beds/manifest.json"
        )

    monkeypatch.setattr(reading_beds, "_ensure_manifest", fail_manifest)
    auth_headers = {"Authorization": f"Bearer {admin_token}"}

    if operation == "upload":
        response = client.post(
            path,
            data={"label": "Secret Rain Room"},
            files={"file": ("secret-rain.mp3", b"fake mp3 bytes", "audio/mpeg")},
            headers=auth_headers,
        )
    elif operation == "update":
        response = client.patch(
            path,
            json={"label": "Secret Rain Room", "set_default": True},
            headers=auth_headers,
        )
    elif operation == "delete":
        response = client.delete(path, headers=auth_headers)
    else:
        response = getattr(client, method)(path)

    metrics_response = client.get("/metrics")

    assert response.status_code == 503
    assert response.json() == {"detail": reading_beds.READING_BED_UNAVAILABLE_MESSAGE}
    assert "secret-bed-id" not in response.text
    assert "admin" not in response.text
    assert "/Volumes/Data" not in response.text
    assert "Secret Rain Room" not in response.text
    assert "secret-rain.mp3" not in response.text
    assert _has_reading_bed_metric_count(
        metrics_response.text,
        operation=operation,
        result="error",
    )

    logs = "\n".join(capture_logger.messages)
    assert f"Reading bed route operation={operation} result=error" in logs
    assert "secret-bed-id" not in logs
    assert "admin" not in logs
    assert "/Volumes/Data" not in logs
    assert "Secret Rain Room" not in logs
    assert "secret-rain.mp3" not in logs
