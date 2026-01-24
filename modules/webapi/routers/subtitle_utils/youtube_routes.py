"""YouTube-related route handlers for subtitle operations."""

from __future__ import annotations

import regex
from datetime import datetime
from pathlib import Path
from typing import Mapping, Optional

from fastapi import APIRouter, Depends, HTTPException, status

from modules import logging_manager as log_mgr
from modules.services.job_manager import PipelineJobManager
from modules.services.youtube_subtitles import (
    SubtitleKind,
    download_video as perform_youtube_video_download,
    download_subtitle as perform_youtube_subtitle_download,
    list_available_subtitles,
)
from modules.services.youtube_dubbing import (
    DEFAULT_YOUTUBE_VIDEO_ROOT,
    YoutubeDubbingService,
    delete_nas_subtitle,
    delete_downloaded_video,
    extract_inline_subtitles,
    list_inline_subtitle_streams,
    list_downloaded_videos,
)

from ...dependencies import (
    RequestUserContext,
    get_pipeline_job_manager,
    get_request_user,
    get_subtitle_service,
    get_youtube_dubbing_service,
)
from ...schemas import (
    YoutubeSubtitleDownloadRequest,
    YoutubeSubtitleDownloadResponse,
    YoutubeSubtitleListResponse,
    YoutubeSubtitleTrackPayload,
    YoutubeVideoDownloadRequest,
    YoutubeVideoDownloadResponse,
    YoutubeVideoFormatPayload,
    YoutubeDubRequest,
    YoutubeDubResponse,
    YoutubeNasLibraryResponse,
    YoutubeNasSubtitlePayload,
    YoutubeNasVideoPayload,
    YoutubeInlineSubtitleListResponse,
    YoutubeSubtitleExtractionRequest,
    YoutubeSubtitleExtractionResponse,
    YoutubeSubtitleDeleteRequest,
    YoutubeSubtitleDeleteResponse,
    YoutubeVideoDeleteRequest,
    YoutubeVideoDeleteResponse,
)

from .parsing import parse_timestamp, parse_time_offset, parse_end_time, parse_tempo_value

router = APIRouter()
logger = log_mgr.get_logger().getChild("webapi.subtitles.youtube")
_ALLOWED_ROLES = {"editor", "admin"}


def _ensure_editor(request_user: RequestUserContext) -> None:
    role = (request_user.user_role or "").strip().lower()
    if role not in _ALLOWED_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")


def _serialize_youtube_tracks(listing) -> YoutubeSubtitleListResponse:
    tracks = [
        YoutubeSubtitleTrackPayload(
            language=track.language,
            kind=track.kind,
            name=track.name,
            formats=track.formats,
        )
        for track in listing.tracks
    ]
    video_formats = [
        YoutubeVideoFormatPayload(
            format_id=entry.format_id,
            ext=entry.ext,
            resolution=entry.resolution,
            fps=entry.fps,
            note=entry.note,
            bitrate_kbps=entry.bitrate_kbps,
            filesize=entry.filesize,
        )
        for entry in getattr(listing, "video_formats", []) or []
    ]
    return YoutubeSubtitleListResponse(
        video_id=listing.video_id,
        title=listing.title,
        tracks=tracks,
        video_formats=video_formats,
    )


def _looks_like_youtube_subtitle(path: Path) -> bool:
    """Heuristic to detect YouTube-sourced subtitles from the filename."""

    name = path.name.lower()
    stem = path.stem.lower()
    normalized = name.replace("_", "-")
    if normalized.endswith("-yt.srt"):
        return True
    if stem.endswith("_yt") or stem.endswith("-yt"):
        return True
    # Match YouTube video id enclosed in brackets, e.g., [kZ5Jq2Is888]
    return bool(regex.search(r"\[[a-z0-9_-]{8,15}\]", name, flags=regex.IGNORECASE))


def _normalize_path_token(path: Path) -> Optional[str]:
    try:
        return path.expanduser().resolve().as_posix()
    except Exception:
        try:
            return path.expanduser().as_posix()
        except Exception:
            return None


def _index_youtube_video_jobs(
    job_manager: PipelineJobManager,
    request_user: Optional[RequestUserContext],
) -> dict[str, set[str]]:
    jobs_by_video: dict[str, set[str]] = {}
    try:
        jobs = job_manager.list(
            user_id=request_user.user_id if request_user else None,
            user_role=request_user.user_role if request_user else None,
        ).values()
    except Exception:
        logger.warning("Unable to enumerate jobs while tagging YouTube videos", exc_info=True)
        return jobs_by_video

    for job in jobs:
        if getattr(job, "job_type", "").lower() != "youtube_dub":
            continue
        payload = job.request_payload or job.resume_context or {}
        if not isinstance(payload, Mapping):
            continue
        video_path = payload.get("video_path") or payload.get("input_file")
        if not video_path:
            continue
        token = _normalize_path_token(Path(str(video_path)))
        if not token:
            continue
        jobs_by_video.setdefault(token, set()).add(job.job_id)
    return jobs_by_video


def _serialize_nas_video(entry, *, linked_jobs: Optional[set[str]] = None) -> YoutubeNasVideoPayload:
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


@router.get("/youtube/subtitles", response_model=YoutubeSubtitleListResponse)
def list_youtube_subtitles(
    url: str,
    request_user: RequestUserContext = Depends(get_request_user),
) -> YoutubeSubtitleListResponse:
    """Return available YouTube subtitle languages for ``url``."""

    _ensure_editor(request_user)
    try:
        listing = list_available_subtitles(url)
    except Exception as exc:
        logger.warning("Unable to list YouTube subtitles for %s", url, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unable to list subtitles: {exc}",
        ) from exc
    return _serialize_youtube_tracks(listing)


@router.post("/youtube/download", response_model=YoutubeSubtitleDownloadResponse)
def download_youtube_subtitle(
    payload: YoutubeSubtitleDownloadRequest,
    service=Depends(get_subtitle_service),
    request_user: RequestUserContext = Depends(get_request_user),
) -> YoutubeSubtitleDownloadResponse:
    """Download a YouTube subtitle track into the subtitle NAS directory."""

    _ensure_editor(request_user)
    language = payload.language.strip()
    if not language:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="language is required",
        )
    kind: SubtitleKind = payload.kind

    mirror_dir = Path(payload.video_output_dir).expanduser() if payload.video_output_dir else None
    timestamp_value = parse_timestamp(payload.timestamp)

    try:
        listing = list_available_subtitles(payload.url)
    except Exception as exc:
        logger.warning("Unable to inspect YouTube subtitles for %s", payload.url, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unable to inspect subtitles: {exc}",
        ) from exc

    selected = next(
        (track for track in listing.tracks if track.language == language and track.kind == kind),
        None,
    )
    if selected is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No {kind} subtitles found for language '{language}'",
        )

    try:
        output_path = perform_youtube_subtitle_download(
            payload.url,
            language=language,
            kind=kind,
            output_dir=service.default_source_dir,
            video_output_dir=mirror_dir,
            timestamp=timestamp_value,
            video_id=listing.video_id,
            video_title=listing.title,
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.warning(
            "Failed to download YouTube subtitles for %s (%s, %s)",
            payload.url,
            language,
            kind,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Subtitle download failed: {exc}",
        ) from exc

    return YoutubeSubtitleDownloadResponse(
        output_path=output_path.as_posix(),
        filename=output_path.name,
    )


@router.post("/youtube/video", response_model=YoutubeVideoDownloadResponse)
def download_youtube_video(
    payload: YoutubeVideoDownloadRequest,
    request_user: RequestUserContext = Depends(get_request_user),
) -> YoutubeVideoDownloadResponse:
    """Download a YouTube video to the NAS directory."""

    _ensure_editor(request_user)
    target_root = Path(payload.output_dir or DEFAULT_YOUTUBE_VIDEO_ROOT).expanduser()
    timestamp_value = parse_timestamp(payload.timestamp)
    try:
        target_root.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unable to create output directory: {exc}",
        ) from exc

    format_id = payload.format_id.strip() if isinstance(payload.format_id, str) else None
    if format_id:
        try:
            listing = list_available_subtitles(payload.url)
        except Exception as exc:
            logger.warning("Unable to inspect YouTube video formats for %s", payload.url, exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unable to inspect video formats: {exc}",
            ) from exc
        known_formats = {entry.format_id for entry in getattr(listing, "video_formats", [])}
        if format_id not in known_formats:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Requested format is not available for this video.",
            )

    try:
        output_path = perform_youtube_video_download(
            payload.url,
            output_root=target_root,
            format_id=format_id,
            timestamp=timestamp_value,
        )
    except Exception as exc:
        logger.warning("YouTube video download failed for %s", payload.url, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Video download failed: {exc}",
        ) from exc

    return YoutubeVideoDownloadResponse(
        output_path=output_path.as_posix(),
        filename=output_path.name,
        folder=output_path.parent.as_posix(),
    )


@router.get("/youtube/library", response_model=YoutubeNasLibraryResponse)
def list_youtube_library(
    base_dir: Optional[str] = None,
    job_manager: PipelineJobManager = Depends(get_pipeline_job_manager),
    request_user: RequestUserContext = Depends(get_request_user),
) -> YoutubeNasLibraryResponse:
    """Return downloaded YouTube videos discovered in the NAS path."""

    _ensure_editor(request_user)
    target_root = Path(base_dir or DEFAULT_YOUTUBE_VIDEO_ROOT).expanduser()
    try:
        videos = list_downloaded_videos(target_root)
    except FileNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    linked_jobs = _index_youtube_video_jobs(job_manager, request_user)
    payload = [
        _serialize_nas_video(
            video,
            linked_jobs=linked_jobs.get(_normalize_path_token(video.path), set()),
        )
        for video in videos
    ]
    return YoutubeNasLibraryResponse(base_dir=target_root.as_posix(), videos=payload)


@router.get("/youtube/subtitle-streams", response_model=YoutubeInlineSubtitleListResponse)
def list_inline_subtitle_streams_from_video(
    video_path: str,
    request_user: RequestUserContext = Depends(get_request_user),
) -> YoutubeInlineSubtitleListResponse:
    """List embedded subtitle streams for a video without extracting them."""

    _ensure_editor(request_user)
    resolved = Path(video_path).expanduser()
    try:
        streams = list_inline_subtitle_streams(resolved)
    except FileNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        logger.warning("Unable to probe subtitle streams for %s", resolved, exc_info=True)
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to inspect subtitle streams: {exc}",
        ) from exc

    return YoutubeInlineSubtitleListResponse(
        video_path=resolved.as_posix(),
        streams=[
            {
                "index": int(stream.get("index")),
                "position": int(stream.get("position", 0)),
                "language": stream.get("language"),
                "codec": stream.get("codec"),
                "title": stream.get("title"),
                "can_extract": bool(stream.get("can_extract", True)),
            }
            for stream in streams
            if stream.get("index") is not None
        ],
    )


@router.post("/youtube/extract-subtitles", response_model=YoutubeSubtitleExtractionResponse)
def extract_inline_subtitles_from_video(
    payload: YoutubeSubtitleExtractionRequest,
    request_user: RequestUserContext = Depends(get_request_user),
) -> YoutubeSubtitleExtractionResponse:
    """Extract embedded subtitle tracks from a NAS video into SRT files."""

    _ensure_editor(request_user)
    video_path = Path(payload.video_path).expanduser()
    try:
        extracted = extract_inline_subtitles(video_path, languages=payload.languages)
    except FileNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        logger.warning("Unable to extract subtitle tracks from %s", video_path, exc_info=True)
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to extract subtitles: {exc}",
        ) from exc

    return YoutubeSubtitleExtractionResponse(
        video_path=video_path.as_posix(),
        extracted=[
            YoutubeNasSubtitlePayload(
                path=sub.path.as_posix(),
                filename=sub.path.name,
                language=sub.language,
                format=sub.format,
            )
            for sub in extracted
        ],
    )


@router.post("/youtube/delete-subtitle", response_model=YoutubeSubtitleDeleteResponse)
def delete_youtube_subtitle(
    payload: YoutubeSubtitleDeleteRequest,
    request_user: RequestUserContext = Depends(get_request_user),
) -> YoutubeSubtitleDeleteResponse:
    """Delete a NAS subtitle and its mirrored companions."""

    _ensure_editor(request_user)
    video_path = Path(payload.video_path).expanduser()
    subtitle_path = Path(payload.subtitle_path).expanduser()

    if not video_path.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Video file not found.")
    if video_path.parent != subtitle_path.parent:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="subtitle_path must be in the same folder as the video file",
        )

    try:
        result = delete_nas_subtitle(subtitle_path)
    except FileNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        logger.warning("Unable to delete subtitle %s", subtitle_path, exc_info=True)
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to delete subtitle: {exc}",
        ) from exc

    return YoutubeSubtitleDeleteResponse(
        video_path=video_path.as_posix(),
        subtitle_path=subtitle_path.as_posix(),
        removed=[path.as_posix() for path in result.removed],
        missing=[path.as_posix() for path in result.missing],
    )


@router.post("/youtube/delete-video", response_model=YoutubeVideoDeleteResponse)
def delete_youtube_video(
    payload: YoutubeVideoDeleteRequest,
    job_manager: PipelineJobManager = Depends(get_pipeline_job_manager),
    request_user: RequestUserContext = Depends(get_request_user),
) -> YoutubeVideoDeleteResponse:
    """Delete a downloaded YouTube video when no linked jobs reference it."""

    _ensure_editor(request_user)
    video_path = Path(payload.video_path).expanduser()
    linked_jobs = _index_youtube_video_jobs(job_manager, request_user)
    token = _normalize_path_token(video_path)
    if token and linked_jobs.get(token):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Video is referenced by existing dubbing jobs and cannot be removed.",
        )

    try:
        result = delete_downloaded_video(video_path)
    except FileNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.warning("Unable to delete YouTube video %s", video_path, exc_info=True)
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to delete YouTube video.",
        ) from exc

    return YoutubeVideoDeleteResponse(
        video_path=video_path.as_posix(),
        removed=[path.as_posix() for path in result.removed],
        missing=[path.as_posix() for path in result.missing],
    )


@router.post("/youtube/dub", response_model=YoutubeDubResponse, status_code=status.HTTP_202_ACCEPTED)
def generate_youtube_dub(
    payload: YoutubeDubRequest,
    youtube_dubbing_service: YoutubeDubbingService = Depends(get_youtube_dubbing_service),
    request_user: RequestUserContext = Depends(get_request_user),
) -> YoutubeDubResponse:
    """Generate a dubbed audio track from an ASS subtitle and mux it into the video."""

    _ensure_editor(request_user)
    video_path = Path(payload.video_path).expanduser()
    subtitle_path = Path(payload.subtitle_path).expanduser()

    tempo = parse_tempo_value(payload.tempo)
    macos_speed = payload.macos_reading_speed if payload.macos_reading_speed is not None else 100
    if macos_speed <= 0:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="macos_reading_speed must be greater than zero",
        )
    mix_percent = payload.original_mix_percent
    if mix_percent is not None and (mix_percent < 0 or mix_percent > 100):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="original_mix_percent must be between 0 and 100",
        )
    target_height = int(payload.target_height) if payload.target_height is not None else 480
    allowed_heights = {320, 480, 720}
    if target_height not in allowed_heights:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="target_height must be one of 320, 480, or 720",
        )
    preserve_aspect_ratio = True if payload.preserve_aspect_ratio is None else bool(payload.preserve_aspect_ratio)
    flush_sentences = payload.flush_sentences
    if flush_sentences is not None and flush_sentences <= 0:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="flush_sentences must be greater than zero",
        )
    llm_model = (payload.llm_model or "").strip() or None
    include_transliteration = True if payload.include_transliteration is None else bool(payload.include_transliteration)
    split_batches = bool(payload.split_batches) if payload.split_batches is not None else False
    stitch_batches = True if payload.stitch_batches is None else bool(payload.stitch_batches)
    start_offset = parse_time_offset(payload.start_time_offset)
    end_offset = parse_end_time(payload.end_time_offset, start_offset)
    voice = (payload.voice or "gTTS").strip() or "gTTS"
    target_language = (payload.target_language or "").strip() or None
    output_dir = Path(payload.output_dir).expanduser() if payload.output_dir else None

    try:
        job = youtube_dubbing_service.enqueue(
            video_path=video_path,
            subtitle_path=subtitle_path,
            source_language=payload.source_language,
            target_language=target_language,
            voice=voice,
            tempo=tempo,
            macos_reading_speed=macos_speed,
            output_dir=output_dir,
            user_id=request_user.user_id,
            user_role=request_user.user_role,
            media_metadata=payload.media_metadata,
            start_time_offset=start_offset,
            end_time_offset=end_offset,
            original_mix_percent=mix_percent,
            flush_sentences=flush_sentences,
            llm_model=llm_model,
            translation_provider=payload.translation_provider,
            translation_batch_size=payload.translation_batch_size,
            transliteration_mode=payload.transliteration_mode,
            transliteration_model=payload.transliteration_model,
            split_batches=split_batches,
            stitch_batches=stitch_batches,
            include_transliteration=include_transliteration,
            target_height=target_height,
            preserve_aspect_ratio=preserve_aspect_ratio,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        logger.warning(
            "Unable to generate dubbed YouTube video",
            exc_info=True,
        )
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to generate dubbed video: {exc}",
        ) from exc

    return YoutubeDubResponse(
        job_id=job.job_id,
        status=job.status,
        created_at=job.created_at,
        job_type=job.job_type,
    )


# Export helper functions for use by other modules
__all__ = [
    "router",
    "_looks_like_youtube_subtitle",
    "_normalize_path_token",
    "_index_youtube_video_jobs",
    "_serialize_nas_video",
    "_serialize_youtube_tracks",
]
