from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

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
    get_youtube_dubbing_service,
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


def test_youtube_video_job_index_prefilters_by_discovered_filename(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    metadata = {
        "match": PipelineJobMetadata(
            job_id="match",
            job_type="youtube_dub",
            status=PipelineJobStatus.COMPLETED,
            created_at=datetime(2026, 6, 24, 12, 0, tzinfo=timezone.utc),
            request_payload={"video_path": "/nas/Show/video-a.mp4"},
        ),
        "unrelated": PipelineJobMetadata(
            job_id="unrelated",
            job_type="youtube_dub",
            status=PipelineJobStatus.COMPLETED,
            created_at=datetime(2026, 6, 24, 12, 5, tzinfo=timezone.utc),
            request_payload={"video_path": "/nas/Other/another-video.mp4"},
        ),
    }
    normalized_calls: list[str] = []

    def fake_normalize(path: Path) -> str:
        normalized_calls.append(path.as_posix())
        return path.as_posix()

    monkeypatch.setattr(youtube_routes, "_normalize_path_token", fake_normalize)

    indexed = youtube_routes._index_youtube_video_job_metadata(
        metadata,
        allowed_tokens={"/nas/Show/video-a.mp4"},
    )

    assert indexed == {"/nas/Show/video-a.mp4": {"match"}}
    assert normalized_calls == ["/nas/Show/video-a.mp4"]


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


def test_youtube_library_normalizes_discovered_video_paths_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _EmptyMetadataJobManager(_MetadataOnlyJobManager):
        def list_metadata(self, **kwargs) -> dict[str, PipelineJobMetadata]:
            self.list_metadata_calls.append(dict(kwargs))
            return {}

    app = create_app()
    manager = _EmptyMetadataJobManager()
    video = YoutubeNasVideo(
        path=Path("/nas/Secret Show/video-a.mp4"),
        size_bytes=123,
        modified_at=datetime(2026, 6, 24, 12, 30, tzinfo=timezone.utc),
        subtitles=[],
    )
    normalize_calls: list[str] = []
    real_normalize = youtube_routes._normalize_path_token

    def recording_normalize(path: Path) -> str | None:
        normalize_calls.append(path.as_posix())
        return real_normalize(path)

    monkeypatch.setattr(youtube_routes, "list_downloaded_videos", lambda root: [video])
    monkeypatch.setattr(youtube_routes, "_normalize_path_token", recording_normalize)
    app.dependency_overrides[get_pipeline_job_manager] = lambda: manager
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="alice",
        user_role="editor",
    )

    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/subtitles/youtube/library",
                params={"base_dir": "/nas/Secret Show"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert normalize_calls.count("/nas/Secret Show/video-a.mp4") == 1
    assert manager.list_metadata_calls == [
        {
            "user_id": "alice",
            "user_role": "editor",
            "job_type": "youtube_dub",
        }
    ]


def test_youtube_dub_submission_records_safe_timing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    logger = _RecordingLogger()
    secret_dir = tmp_path / "Secret Show"
    secret_dir.mkdir()
    video_path = secret_dir / "episode.mp4"
    subtitle_path = secret_dir / "episode.ass"
    output_dir = secret_dir / "dubbed"
    video_path.write_bytes(b"\x00")
    subtitle_path.write_text("[Script Info]\n", encoding="utf-8")

    class _Service:
        def __init__(self) -> None:
            self.calls: list[dict[str, object]] = []

        def enqueue(self, **kwargs):
            self.calls.append(kwargs)
            return SimpleNamespace(
                job_id="youtube-dub-1",
                status="pending",
                created_at=datetime(2026, 6, 24, 12, 0, tzinfo=timezone.utc),
                job_type="youtube_dub",
                output_path=None,
            )

    service = _Service()
    app.dependency_overrides[get_youtube_dubbing_service] = lambda: service
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="office-ipad-user",
        user_role="editor",
    )
    monkeypatch.setattr(youtube_routes, "logger", logger)

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/subtitles/youtube/dub",
                json={
                    "video_path": video_path.as_posix(),
                    "subtitle_path": subtitle_path.as_posix(),
                    "target_language": "Spanish",
                    "voice": "Diego",
                    "media_metadata": {"title": "Private Title"},
                    "output_dir": output_dir.as_posix(),
                },
            )
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 202
    assert response.json()["job_id"] == "youtube-dub-1"
    assert service.calls[0]["video_path"] == video_path
    assert service.calls[0]["subtitle_path"] == subtitle_path

    rendered_logs = "\n".join(logger.messages)
    assert "Create submission operation=youtube_dub result=success" in rendered_logs
    assert "output_dir_present=true metadata_present=true" in rendered_logs
    assert "Secret Show" not in rendered_logs
    assert "episode.mp4" not in rendered_logs
    assert "episode.ass" not in rendered_logs
    assert "office-ipad-user" not in rendered_logs
    assert "Spanish" not in rendered_logs
    assert "Diego" not in rendered_logs
    assert "Private Title" not in rendered_logs
    assert "youtube-dub-1" not in rendered_logs

    families = {
        family.name: family
        for family in text_string_to_metric_families(metrics_response.text)
    }
    metric = families["ebook_tools_create_submission_route_duration_seconds"]
    assert any(
        sample.labels.get("operation") == "youtube_dub"
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


def test_youtube_source_action_errors_do_not_log_or_return_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    logger = _RecordingLogger()
    manager = _MetadataOnlyJobManager()
    secret_dir = tmp_path / "Secret Show"
    secret_dir.mkdir()
    video_path = secret_dir / "episode_yt.mp4"
    subtitle_path = secret_dir / "episode_yt.en.srt"
    video_path.write_bytes(b"\x00")
    subtitle_path.write_text("1\n00:00:00,000 --> 00:00:01,000\nHi\n", encoding="utf-8")

    def fail_with_path(path: Path, *args: object, **kwargs: object):
        raise RuntimeError(f"cannot process {path}")

    monkeypatch.setattr(youtube_routes, "logger", logger)
    monkeypatch.setattr(youtube_routes, "list_inline_subtitle_streams", fail_with_path)
    monkeypatch.setattr(youtube_routes, "extract_inline_subtitles", fail_with_path)
    monkeypatch.setattr(youtube_routes, "delete_nas_subtitle", fail_with_path)
    monkeypatch.setattr(youtube_routes, "delete_downloaded_video", fail_with_path)
    app.dependency_overrides[get_pipeline_job_manager] = lambda: manager
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="office-ipad-user",
        user_role="editor",
    )

    try:
        with TestClient(app) as client:
            responses = [
                client.get(
                    "/api/subtitles/youtube/subtitle-streams",
                    params={"video_path": video_path.as_posix()},
                ),
                client.post(
                    "/api/subtitles/youtube/extract-subtitles",
                    json={"video_path": video_path.as_posix()},
                ),
                client.post(
                    "/api/subtitles/youtube/delete-subtitle",
                    json={
                        "video_path": video_path.as_posix(),
                        "subtitle_path": subtitle_path.as_posix(),
                    },
                ),
                client.post(
                    "/api/subtitles/youtube/delete-video",
                    json={"video_path": video_path.as_posix()},
                ),
            ]
    finally:
        app.dependency_overrides.clear()

    assert [response.status_code for response in responses] == [500, 500, 500, 500]
    assert [response.json()["detail"] for response in responses] == [
        "Unable to inspect subtitle streams.",
        "Unable to extract subtitles.",
        "Unable to delete subtitle.",
        "Unable to delete YouTube video.",
    ]
    rendered_logs = "\n".join(logger.messages)
    rendered_details = "\n".join(response.text for response in responses)
    for rendered in (rendered_logs, rendered_details):
        assert "Secret Show" not in rendered
        assert "episode_yt.mp4" not in rendered
        assert "episode_yt.en.srt" not in rendered
        assert "office-ipad-user" not in rendered
    assert "Unable to probe subtitle streams" in rendered_logs
    assert "Unable to extract subtitle tracks" in rendered_logs
    assert "Unable to delete YouTube subtitle" in rendered_logs
    assert "Unable to delete YouTube video" in rendered_logs


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
