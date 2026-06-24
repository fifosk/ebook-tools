from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from prometheus_client.parser import text_string_to_metric_families

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


class _RecordingLogger:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def debug(self, message: str, *args: object, **kwargs: object) -> None:
        self.messages.append(message % args if args else message)

    def info(self, message: str, *args: object, **kwargs: object) -> None:
        self.messages.append(message % args if args else message)

    def warning(self, message: str, *args: object, **kwargs: object) -> None:
        self.messages.append(message % args if args else message)


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
                request_payload={"video_path": "/nas/Secret Show/video-a.mp4"},
                user_id=user_id,
                user_role=user_role,
            ),
            "other-dub-job": PipelineJobMetadata(
                job_id="other-dub-job",
                job_type="youtube_dub",
                status=PipelineJobStatus.COMPLETED,
                created_at=datetime(2026, 6, 24, 12, 5, tzinfo=timezone.utc),
                request_payload={"video_path": "/nas/Other Show/video-b.mp4"},
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
    logger = _RecordingLogger()
    secret_base_dir = "/nas/Secret Show"
    video = YoutubeNasVideo(
        path=Path(f"{secret_base_dir}/video-a.mp4"),
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
    monkeypatch.setattr(youtube_routes, "logger", logger)

    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/subtitles/youtube/library",
                params={"base_dir": secret_base_dir},
            )
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["base_dir"] == secret_base_dir
    assert payload["videos"][0]["linked_job_ids"] == ["dub-job"]
    assert "other-dub-job" not in payload["videos"][0]["linked_job_ids"]
    assert manager.list_metadata_calls == [
        {
            "user_id": "alice",
            "user_role": "editor",
            "job_type": "youtube_dub",
        }
    ]
    assert manager.list_calls == 0

    rendered_logs = "\n".join(logger.messages)
    assert "YouTube library route result=success videos=1 subtitles=0 linked_jobs=1" in rendered_logs
    assert secret_base_dir not in rendered_logs
    assert "/nas/Secret Show/video-a.mp4" not in rendered_logs
    assert "alice" not in rendered_logs
    assert "dub-job" not in rendered_logs
    assert "other-dub-job" not in rendered_logs

    families = {
        family.name: family
        for family in text_string_to_metric_families(metrics_response.text)
    }
    metric = families["ebook_tools_youtube_library_route_duration_seconds"]
    assert any(
        sample.labels.get("operation") == "list"
        and sample.labels.get("result") == "success"
        and sample.name.endswith("_count")
        and sample.value >= 1
        for sample in metric.samples
    )


def test_youtube_library_skips_job_metadata_when_no_videos(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    manager = _MetadataOnlyJobManager()
    monkeypatch.setattr(youtube_routes, "list_downloaded_videos", lambda root: [])
    app.dependency_overrides[get_pipeline_job_manager] = lambda: manager
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="alice",
        user_role="editor",
    )

    try:
        with TestClient(app) as client:
            response = client.get("/api/subtitles/youtube/library")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["videos"] == []
    assert manager.list_metadata_calls == []
    assert manager.list_calls == 0


def test_delete_youtube_subtitle_reports_missing_stale_sidecar(tmp_path: Path) -> None:
    app = create_app()
    video_path = tmp_path / "episode_yt.mp4"
    subtitle_path = tmp_path / "episode_yt.en.srt"
    video_path.write_bytes(b"\x00")
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="alice",
        user_role="editor",
    )

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/subtitles/youtube/delete-subtitle",
                json={
                    "video_path": video_path.as_posix(),
                    "subtitle_path": subtitle_path.as_posix(),
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["removed"] == []
    assert payload["missing"] == [subtitle_path.resolve().as_posix()]


def test_delete_youtube_subtitle_rejects_stale_non_subtitle_sidecar(tmp_path: Path) -> None:
    app = create_app()
    video_path = tmp_path / "episode_yt.mp4"
    subtitle_path = tmp_path / "episode_yt.txt"
    video_path.write_bytes(b"\x00")
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="alice",
        user_role="editor",
    )

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/subtitles/youtube/delete-subtitle",
                json={
                    "video_path": video_path.as_posix(),
                    "subtitle_path": subtitle_path.as_posix(),
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400
    assert "subtitle file" in response.json()["detail"]


def test_delete_youtube_video_reports_missing_stale_video(tmp_path: Path) -> None:
    app = create_app()
    manager = _MetadataOnlyJobManager()
    video_path = tmp_path / "episode_yt.mp4"
    app.dependency_overrides[get_pipeline_job_manager] = lambda: manager
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="alice",
        user_role="editor",
    )

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/subtitles/youtube/delete-video",
                json={"video_path": video_path.as_posix()},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["removed"] == []
    assert payload["missing"] == [video_path.resolve().as_posix()]
    assert manager.list_calls == 0


def test_delete_youtube_video_rejects_stale_non_video_path(tmp_path: Path) -> None:
    app = create_app()
    manager = _MetadataOnlyJobManager()
    video_path = tmp_path / "episode_yt.txt"
    app.dependency_overrides[get_pipeline_job_manager] = lambda: manager
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="alice",
        user_role="editor",
    )

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/subtitles/youtube/delete-video",
                json={"video_path": video_path.as_posix()},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400
    assert "supported video file" in response.json()["detail"]
    assert manager.list_calls == 0
