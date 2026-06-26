from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

import pytest

from modules.services.job_manager.job import PipelineJob, PipelineJobStatus
from modules.services.subtitle_metadata_service import SubtitleMetadataService
from modules.services.youtube_video_metadata_service import YoutubeVideoMetadataService

pytestmark = pytest.mark.services


class _MutatingJobManager:
    def __init__(self, job: PipelineJob) -> None:
        self.job = job
        self.calls: list[tuple[str, str | None, str | None]] = []

    def mutate_job(
        self,
        job_id: str,
        mutator: Callable[[PipelineJob], None],
        *,
        user_id: str | None = None,
        user_role: str | None = None,
    ) -> None:
        self.calls.append((job_id, user_id, user_role))
        mutator(self.job)


def test_subtitle_tv_metadata_persistence_normalizes_discovery_identifiers() -> None:
    job = PipelineJob(
        job_id="tv-job",
        status=PipelineJobStatus.COMPLETED,
        created_at=datetime.now(timezone.utc),
        job_type="youtube_dub",
        request_payload={
            "media_metadata": {
                "title": "Existing",
                "source_kind": " NAS_Video ",
                "youtube": {"provider": " YouTube_Search ", "title": "Existing video"},
            }
        },
        result_payload={
            "media_metadata": {"source_provider": " Newznab_Torznab "},
            "youtube_dub": {
                "media_metadata": {
                    "source_kind": " NAS_Video ",
                    "youtube": {"provider": " YouTube_Search ", "title": "Existing video"},
                }
            },
        },
    )
    manager = _MutatingJobManager(job)

    SubtitleMetadataService(job_manager=manager)._persist_media_metadata(
        "tv-job",
        {
            "kind": "tv_episode",
            "provider": " TVMaze ",
            "source_kind": " Manual_Downloads ",
            "source_provider": " Newznab_Torznab ",
            "acquisition_provider": " Youtube_Search ",
            "acquisition_candidate_id": "Youtube_Search:DemoVideo",
            "job_label": "Demo S01E02",
            "show": {"name": "Demo Show"},
            "episode": {"name": "Pilot", "season": 1, "number": 2},
            "tvmaze": {"show_id": 10, "episode_id": 20},
        },
        user_id="editor",
        user_role="editor",
    )

    assert manager.calls == [("tv-job", "editor", "editor")]
    assert job.request_payload is not None
    assert job.request_payload["media_metadata"]["provider"] == "tvmaze"
    assert job.request_payload["media_metadata"]["source_kind"] == "manual_downloads"
    assert job.request_payload["media_metadata"]["source_provider"] == "newznab_torznab"
    assert job.request_payload["media_metadata"]["acquisition_provider"] == "youtube_search"
    assert job.request_payload["media_metadata"]["acquisition_candidate_id"] == "Youtube_Search:DemoVideo"
    assert job.request_payload["media_metadata"]["youtube"]["provider"] == "youtube_search"
    assert job.result_payload is not None
    assert job.result_payload["youtube_dub"]["media_metadata"]["provider"] == "tvmaze"
    assert job.result_payload["youtube_dub"]["media_metadata"]["youtube"]["provider"] == "youtube_search"
    assert job.result_payload["media_metadata"]["source_provider"] == "newznab_torznab"
    assert job.result_payload["media_metadata"]["job_label"] == "Demo S01E02"


def test_youtube_metadata_persistence_normalizes_discovery_identifiers() -> None:
    job = PipelineJob(
        job_id="youtube-job",
        status=PipelineJobStatus.COMPLETED,
        created_at=datetime.now(timezone.utc),
        job_type="youtube_dub",
        request_payload={
            "media_metadata": {
                "source_kind": " NAS_Video ",
                "source_provider": " Newznab_Torznab ",
            }
        },
        result_payload={
            "youtube_dub": {
                "media_metadata": {
                    "source_kind": " NAS_Video ",
                    "source_provider": " Newznab_Torznab ",
                }
            }
        },
    )
    manager = _MutatingJobManager(job)

    YoutubeVideoMetadataService(job_manager=manager)._persist_youtube_metadata(
        "youtube-job",
        {
            "kind": "youtube_video",
            "provider": " YouTube_Search ",
            "title": "Demo Video",
        },
        user_id="editor",
        user_role="editor",
    )

    assert manager.calls == [("youtube-job", "editor", "editor")]
    assert job.request_payload is not None
    assert job.request_payload["media_metadata"]["source_kind"] == "nas_video"
    assert job.request_payload["media_metadata"]["source_provider"] == "newznab_torznab"
    assert job.request_payload["media_metadata"]["youtube"]["provider"] == "youtube_search"
    assert job.request_payload["media_metadata"]["job_label"] == "Demo Video"
    assert job.result_payload is not None
    assert job.result_payload["youtube_dub"]["media_metadata"]["source_kind"] == "nas_video"
    assert job.result_payload["youtube_dub"]["media_metadata"]["source_provider"] == "newznab_torznab"
    assert job.result_payload["youtube_dub"]["media_metadata"]["youtube"]["provider"] == "youtube_search"
    assert job.result_payload["youtube_dub"]["media_metadata"]["job_label"] == "Demo Video"
