from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException
import pytest

from modules.services.file_locator import FileLocator
from modules.webapi.dependencies import RequestUserContext
from modules.webapi.routes.media.common import _resolve_job_root

pytestmark = pytest.mark.webapi


class _RecordingJobManager:
    def __init__(self, *, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[tuple[str, str | None, str | None, str]] = []

    def get(self, job_id: str, *, user_id=None, user_role=None, permission: str = "view") -> None:
        self.calls.append((job_id, user_id, user_role, permission))
        if self.error is not None:
            raise self.error


class _RecordingLibraryRepository:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def get_entry_by_id(self, job_id: str):
        self.calls.append(job_id)
        return None


def test_resolve_job_root_normalizes_route_id_for_pipeline_root(tmp_path: Path) -> None:
    locator = FileLocator(storage_dir=tmp_path)
    job_root = locator.resolve_path("media-job")
    (job_root / "metadata").mkdir(parents=True)
    (job_root / "metadata" / "job.json").write_text("{}", encoding="utf-8")
    manager = _RecordingJobManager()
    repository = _RecordingLibraryRepository()

    resolved = _resolve_job_root(
        job_id="  media-job  ",
        locator=locator,
        library_repository=repository,
        request_user=RequestUserContext(user_id="alice", user_role="editor"),
        job_manager=manager,
    )

    assert resolved == job_root
    assert manager.calls == [("media-job", "alice", "editor", "view")]
    assert repository.calls == []


def test_resolve_job_root_rejects_blank_id_without_lookup(tmp_path: Path) -> None:
    manager = _RecordingJobManager()
    repository = _RecordingLibraryRepository()

    with pytest.raises(HTTPException) as exc_info:
        _resolve_job_root(
            job_id="   ",
            locator=FileLocator(storage_dir=tmp_path),
            library_repository=repository,
            request_user=RequestUserContext(user_id="alice", user_role="editor"),
            job_manager=manager,
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Job not found"
    assert manager.calls == []
    assert repository.calls == []


def test_resolve_job_root_permission_error_uses_generic_detail(tmp_path: Path) -> None:
    manager = _RecordingJobManager(
        error=PermissionError("alice cannot read /Volumes/Data/private/media-job")
    )
    repository = _RecordingLibraryRepository()

    with pytest.raises(HTTPException) as exc_info:
        _resolve_job_root(
            job_id="  media-job  ",
            locator=FileLocator(storage_dir=tmp_path),
            library_repository=repository,
            request_user=RequestUserContext(user_id="alice", user_role="editor"),
            job_manager=manager,
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Not authorized to access media"
    assert "alice cannot read" not in str(exc_info.value.detail)
    assert "/Volumes/Data/private" not in str(exc_info.value.detail)
    assert manager.calls == [("media-job", "alice", "editor", "view")]
    assert repository.calls == []
