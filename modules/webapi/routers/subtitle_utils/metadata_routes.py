"""Metadata lookup route handlers for subtitle jobs."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from modules import logging_manager as log_mgr
from modules.services.job_manager import PipelineJobManager
from modules.services.subtitle_metadata_service import SubtitleMetadataService
from modules.services.youtube_video_metadata_service import YoutubeVideoMetadataService

from ...dependencies import (
    RequestUserContext,
    get_pipeline_job_manager,
    get_request_user,
    get_subtitle_metadata_service,
    get_youtube_video_metadata_service,
)
from ...schemas import (
    SubtitleTvMetadataLookupRequest,
    SubtitleTvMetadataPreviewLookupRequest,
    SubtitleTvMetadataPreviewResponse,
    SubtitleTvMetadataResponse,
    YoutubeVideoMetadataLookupRequest,
    YoutubeVideoMetadataPreviewLookupRequest,
    YoutubeVideoMetadataPreviewResponse,
    YoutubeVideoMetadataResponse,
)

router = APIRouter()
logger = log_mgr.get_logger().getChild("webapi.subtitles.metadata")
_ALLOWED_ROLES = {"editor", "admin"}


def _ensure_editor(request_user: RequestUserContext) -> None:
    role = (request_user.user_role or "").strip().lower()
    if role not in _ALLOWED_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")


@router.get("/jobs/{job_id}/metadata/tv", response_model=SubtitleTvMetadataResponse)
def get_subtitle_tv_metadata(
    job_id: str,
    metadata_service: SubtitleMetadataService = Depends(get_subtitle_metadata_service),
    request_user: RequestUserContext = Depends(get_request_user),
) -> SubtitleTvMetadataResponse:
    """Return stored (or inferred) TV metadata for a subtitle job without triggering a lookup."""

    try:
        payload = metadata_service.get_tv_metadata(
            job_id,
            user_id=request_user.user_id,
            user_role=request_user.user_role,
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return SubtitleTvMetadataResponse(**payload)


@router.post(
    "/jobs/{job_id}/metadata/tv/lookup",
    response_model=SubtitleTvMetadataResponse,
)
def lookup_subtitle_tv_metadata(
    job_id: str,
    lookup: SubtitleTvMetadataLookupRequest,
    metadata_service: SubtitleMetadataService = Depends(get_subtitle_metadata_service),
    request_user: RequestUserContext = Depends(get_request_user),
) -> SubtitleTvMetadataResponse:
    """Trigger TVMaze metadata enrichment for the subtitle job and persist the result."""

    try:
        payload = metadata_service.lookup_tv_metadata(
            job_id,
            force=bool(lookup.force),
            user_id=request_user.user_id,
            user_role=request_user.user_role,
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return SubtitleTvMetadataResponse(**payload)


@router.post(
    "/metadata/tv/lookup",
    response_model=SubtitleTvMetadataPreviewResponse,
)
def lookup_subtitle_tv_metadata_preview(
    lookup: SubtitleTvMetadataPreviewLookupRequest,
    metadata_service: SubtitleMetadataService = Depends(get_subtitle_metadata_service),
    request_user: RequestUserContext = Depends(get_request_user),
) -> SubtitleTvMetadataPreviewResponse:
    """Lookup TV metadata for a subtitle filename (used before submitting jobs)."""

    _ensure_editor(request_user)
    try:
        payload = metadata_service.lookup_tv_metadata_for_source(
            lookup.source_name,
            force=bool(lookup.force),
        )
    except Exception as exc:
        logger.warning(
            "Unable to lookup TV metadata for subtitle source %s",
            lookup.source_name,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Unable to lookup TV metadata: {exc}",
        ) from exc

    return SubtitleTvMetadataPreviewResponse(**payload)


@router.get("/jobs/{job_id}/metadata/youtube", response_model=YoutubeVideoMetadataResponse)
def get_youtube_video_metadata(
    job_id: str,
    metadata_service: YoutubeVideoMetadataService = Depends(get_youtube_video_metadata_service),
    request_user: RequestUserContext = Depends(get_request_user),
) -> YoutubeVideoMetadataResponse:
    """Return stored YouTube metadata for a youtube_dub job without triggering a lookup."""

    try:
        payload = metadata_service.get_youtube_metadata(
            job_id,
            user_id=request_user.user_id,
            user_role=request_user.user_role,
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return YoutubeVideoMetadataResponse(**payload)


@router.post(
    "/jobs/{job_id}/metadata/youtube/lookup",
    response_model=YoutubeVideoMetadataResponse,
)
def lookup_youtube_video_metadata(
    job_id: str,
    lookup: YoutubeVideoMetadataLookupRequest,
    metadata_service: YoutubeVideoMetadataService = Depends(get_youtube_video_metadata_service),
    request_user: RequestUserContext = Depends(get_request_user),
) -> YoutubeVideoMetadataResponse:
    """Trigger yt-dlp metadata enrichment for the YouTube dubbing job and persist the result."""

    try:
        payload = metadata_service.lookup_youtube_metadata(
            job_id,
            force=bool(lookup.force),
            user_id=request_user.user_id,
            user_role=request_user.user_role,
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return YoutubeVideoMetadataResponse(**payload)


@router.post(
    "/metadata/youtube/lookup",
    response_model=YoutubeVideoMetadataPreviewResponse,
)
def lookup_youtube_video_metadata_preview(
    lookup: YoutubeVideoMetadataPreviewLookupRequest,
    metadata_service: YoutubeVideoMetadataService = Depends(get_youtube_video_metadata_service),
    request_user: RequestUserContext = Depends(get_request_user),
) -> YoutubeVideoMetadataPreviewResponse:
    """Lookup YouTube metadata for a filename/URL (used before submitting jobs)."""

    _ensure_editor(request_user)
    try:
        payload = metadata_service.lookup_youtube_metadata_for_source(
            lookup.source_name,
            force=bool(lookup.force),
        )
    except Exception as exc:
        logger.warning(
            "Unable to lookup YouTube metadata for source %s",
            lookup.source_name,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Unable to lookup YouTube metadata: {exc}",
        ) from exc

    return YoutubeVideoMetadataPreviewResponse(**payload)


__all__ = ["router"]
