"""Helpers for YouTube NAS library route payloads and job links."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping, Optional

import regex

from modules.services.job_manager import PipelineJobManager
from modules.services.job_manager.metadata import PipelineJobMetadata

from ...dependencies import RequestUserContext
from ...schemas import (
    YoutubeNasSubtitlePayload,
    YoutubeNasVideoPayload,
)


def looks_like_youtube_subtitle(path: Path) -> bool:
    """Heuristic to detect YouTube-sourced subtitles from the filename."""

    name = path.name.lower()
    stem = path.stem.lower()
    normalized = name.replace("_", "-")
    if normalized.endswith("-yt.srt"):
        return True
    if stem.endswith("_yt") or stem.endswith("-yt"):
        return True
    return bool(regex.search(r"\[[a-z0-9_-]{8,15}\]", name, flags=regex.IGNORECASE))


def normalize_path_token(path: Path) -> Optional[str]:
    try:
        return path.expanduser().resolve().as_posix()
    except Exception:
        try:
            return path.expanduser().as_posix()
        except Exception:
            return None


def index_youtube_video_job_metadata(
    job_metadata: Mapping[str, PipelineJobMetadata],
    *,
    allowed_tokens: Optional[set[str]] = None,
) -> dict[str, set[str]]:
    jobs_by_video: dict[str, set[str]] = {}
    allowed_names = {Path(token).name for token in allowed_tokens or set()}
    for job in job_metadata.values():
        payload = job.request_payload or job.resume_context or {}
        if not isinstance(payload, Mapping):
            continue
        video_path = payload.get("video_path") or payload.get("input_file")
        if not video_path:
            continue
        candidate_path = Path(str(video_path))
        if allowed_names and candidate_path.name not in allowed_names:
            continue
        token = normalize_path_token(candidate_path)
        if not token:
            continue
        if allowed_tokens is not None and token not in allowed_tokens:
            continue
        jobs_by_video.setdefault(token, set()).add(job.job_id)
    return jobs_by_video


def index_youtube_video_jobs(
    job_manager: PipelineJobManager,
    request_user: Optional[RequestUserContext],
    *,
    allowed_tokens: Optional[set[str]] = None,
    logger=None,
) -> dict[str, set[str]]:
    if allowed_tokens is not None and not allowed_tokens:
        return {}
    try:
        job_metadata = job_manager.list_metadata(
            user_id=request_user.user_id if request_user else None,
            user_role=request_user.user_role if request_user else None,
            job_type="youtube_dub",
        )
    except Exception:
        if logger is not None:
            logger.warning("Unable to enumerate jobs while tagging YouTube videos")
        return {}
    return index_youtube_video_job_metadata(job_metadata, allowed_tokens=allowed_tokens)


def serialize_nas_video(entry, *, linked_jobs: Optional[set[str]] = None) -> YoutubeNasVideoPayload:
    subtitles = [
        YoutubeNasSubtitlePayload(
            path=sub.path.as_posix(),
            filename=sub.path.name,
            language=sub.language,
            format=sub.format,
        )
        for sub in getattr(entry, "subtitles", []) or []
    ]
    job_ids = sorted(linked_jobs) if linked_jobs else []
    return YoutubeNasVideoPayload(
        path=entry.path.as_posix(),
        filename=entry.path.name,
        folder=entry.path.parent.as_posix(),
        size_bytes=entry.size_bytes,
        modified_at=entry.modified_at,
        subtitles=subtitles,
        source=getattr(entry, "source", None) or "youtube",
        linked_job_ids=job_ids,
    )


def serialize_nas_video_library(
    videos,
    *,
    job_manager: PipelineJobManager,
    request_user: Optional[RequestUserContext],
    logger=None,
) -> list[YoutubeNasVideoPayload]:
    video_entries = [(video, normalize_path_token(video.path)) for video in videos]
    video_tokens = {token for _, token in video_entries if token}
    linked_jobs = index_youtube_video_jobs(
        job_manager,
        request_user,
        allowed_tokens=video_tokens,
        logger=logger,
    )
    return [
        serialize_nas_video(
            video,
            linked_jobs=linked_jobs.get(token, set()) if token else set(),
        )
        for video, token in video_entries
    ]
