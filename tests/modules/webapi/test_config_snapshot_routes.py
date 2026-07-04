from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from modules.config_manager.config_repository import SnapshotMetadata
from modules.user_management import AuthService, LocalUserStore, SessionManager
from modules.webapi import config_routes
from modules.webapi.application import create_app
from modules.webapi.dependencies import get_auth_service

pytestmark = pytest.mark.webapi


class _RecordingConfigRepository:
    def __init__(self) -> None:
        self.get_calls: list[str] = []
        self.restore_calls: list[tuple[str, str | None]] = []
        self.delete_calls: list[tuple[str, str | None]] = []
        self.export_calls: list[tuple[str, bool]] = []
        self.metadata = SnapshotMetadata(
            snapshot_id="snap_trimmed",
            label="Trimmed snapshot",
            description="Route helper coverage",
            created_by="admin",
            created_at="2026-07-04T12:00:00+00:00",
            is_active=False,
            source="manual",
            config_hash="abc123",
        )

    def get_snapshot(self, snapshot_id: str) -> tuple[SnapshotMetadata, dict[str, Any]] | None:
        self.get_calls.append(snapshot_id)
        if snapshot_id != "snap_trimmed":
            return None
        return self.metadata, {"pipeline_workers": 2}

    def restore_snapshot(self, snapshot_id: str, *, restored_by: str | None = None) -> None:
        self.restore_calls.append((snapshot_id, restored_by))

    def delete_snapshot(self, snapshot_id: str, *, deleted_by: str | None = None) -> bool:
        self.delete_calls.append((snapshot_id, deleted_by))
        return snapshot_id == "snap_trimmed"

    def export_snapshot(self, snapshot_id: str, *, mask_sensitive: bool = True) -> dict[str, Any]:
        self.export_calls.append((snapshot_id, mask_sensitive))
        if snapshot_id != "snap_trimmed":
            raise AssertionError("unexpected snapshot id")
        return {
            "snapshot_id": snapshot_id,
            "label": self.metadata.label,
            "description": self.metadata.description,
            "created_at": self.metadata.created_at,
            "created_by": self.metadata.created_by,
            "source": self.metadata.source,
            "config": {"pipeline_workers": 2},
        }


@pytest.fixture
def config_snapshot_client(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[tuple[TestClient, _RecordingConfigRepository, str]]:
    auth_service = AuthService(
        LocalUserStore(storage_path=tmp_path / "users.json"),
        SessionManager(session_file=tmp_path / "sessions.json"),
    )
    auth_service.user_store.create_user("admin", "secret", roles=["admin"])
    admin_token = auth_service.session_manager.create_session("admin")
    repository = _RecordingConfigRepository()
    app = create_app()
    app.dependency_overrides[get_auth_service] = lambda: auth_service
    monkeypatch.setattr(config_routes, "_get_config_repository", lambda: repository)
    monkeypatch.setattr(config_routes, "load_configuration", lambda: {"pipeline_workers": 1})
    monkeypatch.setattr(config_routes, "refresh_runtime_config", lambda: None)

    with TestClient(app) as client:
        yield client, repository, admin_token

    app.dependency_overrides.clear()


def test_config_snapshot_routes_use_shared_route_id_normalizer() -> None:
    source = Path(config_routes.__file__).read_text(encoding="utf-8")

    assert "from .route_ids import normalize_route_id" in source
    assert "def _normalize_route_id" not in source
    assert source.count("normalized_snapshot_id = normalize_route_id(snapshot_id)") >= 3
    assert "repo.get_snapshot(normalized_snapshot_id)" in source
    assert "repo.restore_snapshot(normalized_snapshot_id" in source
    assert "repo.delete_snapshot(normalized_snapshot_id" in source
    assert "repo.export_snapshot(normalized_snapshot_id" in source


def test_config_snapshot_routes_normalize_padded_snapshot_id(
    config_snapshot_client: tuple[TestClient, _RecordingConfigRepository, str],
) -> None:
    client, repository, admin_token = config_snapshot_client
    headers = {"Authorization": f"Bearer {admin_token}"}

    restore_response = client.post(
        "/api/admin/config/snapshots/%20%20snap_trimmed%20%20/restore",
        headers=headers,
    )
    export_response = client.get(
        "/api/admin/config/snapshots/%20%20snap_trimmed%20%20/export",
        params={"mask_sensitive": "false"},
        headers=headers,
    )
    delete_response = client.delete(
        "/api/admin/config/snapshots/%20%20snap_trimmed%20%20",
        headers=headers,
    )

    assert restore_response.status_code == 200
    assert restore_response.json()["snapshotId"] == "snap_trimmed"
    assert export_response.status_code == 200
    assert export_response.json()["snapshotId"] == "snap_trimmed"
    assert delete_response.status_code == 204
    assert repository.get_calls == ["snap_trimmed"]
    assert repository.restore_calls == [("snap_trimmed", "admin")]
    assert repository.export_calls == [("snap_trimmed", False)]
    assert repository.delete_calls == [("snap_trimmed", "admin")]


def test_config_snapshot_routes_reject_blank_snapshot_id_before_repository_access(
    config_snapshot_client: tuple[TestClient, _RecordingConfigRepository, str],
) -> None:
    client, repository, admin_token = config_snapshot_client
    headers = {"Authorization": f"Bearer {admin_token}"}

    restore_response = client.post(
        "/api/admin/config/snapshots/%20%20%20/restore",
        headers=headers,
    )
    export_response = client.get(
        "/api/admin/config/snapshots/%20%20%20/export",
        headers=headers,
    )
    delete_response = client.delete(
        "/api/admin/config/snapshots/%20%20%20",
        headers=headers,
    )

    assert restore_response.status_code == 404
    assert restore_response.json() == {"detail": "Snapshot not found"}
    assert export_response.status_code == 404
    assert export_response.json() == {"detail": "Snapshot not found"}
    assert delete_response.status_code == 404
    assert delete_response.json() == {"detail": "Snapshot not found"}
    assert repository.get_calls == []
    assert repository.restore_calls == []
    assert repository.export_calls == []
    assert repository.delete_calls == []
