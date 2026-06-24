from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from modules.services.job_manager.metadata import PipelineJobMetadata
from modules.services.job_manager.job import PipelineJobStatus
from modules.services.youtube_dubbing.common import YoutubeNasVideo
from modules.webapi.application import create_app
from modules.webapi.dependencies import (
    RequestUserContext,
    get_pipeline_job_manager,
    get_request_user,
)
from modules.webapi.routers.subtitle_utils import youtube_routes

pytestmark = pytest.mark.webapi


class _MetadataOnlyJobManager:
    def __init__(self) -> None:
        self.list_metadata_calls: list[dict[str, str | None]] = []
        self.list_calls = 0

    def list_metadata(
        self,
        *,
        user_id: str | None = None,
        user_role: str | None = None,
        job_type: str | None = None,
    ) -> dict[str, PipelineJobMetadata]:
        self.list_metadata_calls.append(
            {
                "user_id": user_id,
                "user_role": user_role,
                "job_type": job_type,
            }
        )
        return {
            "dub-job": PipelineJobMetadata(
                job_id="dub-job",
                job_type="youtube_dub",
                status=PipelineJobStatus.COMPLETED,
                created_at=datetime(2026, 6, 24, 12, 0, tzinfo=timezone.utc),
                request_payload={"video_path": "/nas/video-a.mp4"},
                user_id=user_id,
                user_role=user_role,
            )
        }

    def list(self, **kwargs):  # pragma: no cover - should not be used
        self.list_calls += 1
        raise AssertionError("YouTube library route should not hydrate full jobs")


def test_youtube_library_links_jobs_from_metadata_without_full_job_hydration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    manager = _MetadataOnlyJobManager()
    video = YoutubeNasVideo(
        path=Path("/nas/video-a.mp4"),
        size_bytes=123,
        modified_at=datetime(2026, 6, 24, 12, 30, tzinfo=timezone.utc),
        subtitles=[],
    )
    monkeypatch.setattr(youtube_routes, "list_downloaded_videos", lambda root: [video])
    app.dependency_overrides[get_pipeline_job_manager] = lambda: manager
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="alice",
        user_role="editor",
    )

    try:
        with TestClient(app) as client:
            response = client.get("/api/subtitles/youtube/library", params={"base_dir": "/nas"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["base_dir"] == "/nas"
    assert payload["videos"][0]["linked_job_ids"] == ["dub-job"]
    assert manager.list_metadata_calls == [
        {
            "user_id": "alice",
            "user_role": "editor",
            "job_type": "youtube_dub",
        }
    ]
    assert manager.list_calls == 0
