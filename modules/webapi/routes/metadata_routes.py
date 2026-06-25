"""Routes for unified metadata lookup."""

from __future__ import annotations

import time

from fastapi import APIRouter, HTTPException, status

from modules import logging_manager as log_mgr
from modules.services.metadata import (
    LookupOptions,
    LookupQuery,
    MediaType,
    create_pipeline,
)
from ..schemas.metadata_lookup import (
    UnifiedMetadataLookupRequest,
    UnifiedMetadataResponse,
    SeriesInfoResponse,
)
from ..route_telemetry import record_started_route_duration

logger = log_mgr.get_logger().getChild("webapi.routes.metadata")

router = APIRouter(prefix="/metadata", tags=["metadata"])


def _media_type_from_str(type_str: str) -> MediaType:
    """Convert string to MediaType enum."""
    mapping = {
        "book": MediaType.BOOK,
        "movie": MediaType.MOVIE,
        "tv_series": MediaType.TV_SERIES,
        "tv": MediaType.TV_SERIES,
        "tv_episode": MediaType.TV_EPISODE,
        "episode": MediaType.TV_EPISODE,
        "youtube_video": MediaType.YOUTUBE_VIDEO,
        "youtube": MediaType.YOUTUBE_VIDEO,
    }
    result = mapping.get(type_str.lower())
    if result is None:
        raise ValueError(f"Unknown media type: {type_str}")
    return result


def _record_metadata_lookup_route_duration(result: str, started_at: float) -> None:
    """Record token-safe unified metadata lookup route timing if metrics are available."""

    record_started_route_duration(
        "METADATA_LOOKUP_ROUTE_DURATION",
        "lookup",
        result,
        started_at,
    )


def _log_metadata_lookup_route_result(
    *,
    result: str,
    media_type: str,
    started_at: float,
    force: bool,
    include_raw: bool,
    contributing_sources: int | None = None,
    source_ids: int | None = None,
) -> None:
    duration_ms = (time.perf_counter() - started_at) * 1000.0
    details = (
        "Unified metadata lookup result="
        f"{result} type={media_type} force={str(force).lower()} "
        f"include_raw={str(include_raw).lower()} duration_ms={duration_ms:.1f}"
    )
    if contributing_sources is not None:
        details += f" sources={contributing_sources}"
    if source_ids is not None:
        details += f" source_ids={source_ids}"
    log_method = logger.info if result != "success" or duration_ms >= 250 else logger.debug
    log_method(details)


@router.post("/lookup", response_model=UnifiedMetadataResponse)
async def unified_metadata_lookup(
    request: UnifiedMetadataLookupRequest,
) -> UnifiedMetadataResponse:
    """Look up metadata for a book, movie, TV series/episode, or YouTube video.

    This endpoint uses multiple data sources with automatic fallback:
    - Books: OpenLibrary → Google Books → Wikipedia
    - Movies: TMDB → OMDb → Wikipedia
    - TV Series: TMDB → OMDb → Wikipedia
    - TV Episodes: TMDB → OMDb → TVMaze
    - YouTube: yt-dlp

    Returns unified metadata in a consistent format.
    """
    started_at = time.perf_counter()
    request_type = request.type.strip().lower()
    try:
        media_type = _media_type_from_str(request.type)
    except ValueError as exc:
        _record_metadata_lookup_route_duration("invalid_type", started_at)
        _log_metadata_lookup_route_result(
            result="invalid_type",
            media_type=request_type or "unknown",
            started_at=started_at,
            force=request.force,
            include_raw=request.include_raw,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    # Build query based on media type
    query = LookupQuery(
        media_type=media_type,
        title=request.title,
        author=request.author,
        isbn=request.isbn,
        movie_title=request.movie_title,
        series_name=request.series_name,
        season=request.season,
        episode=request.episode,
        year=request.year,
        youtube_video_id=request.youtube_video_id,
        youtube_url=request.youtube_url,
        source_filename=request.source_filename,
        tmdb_id=request.tmdb_id,
        imdb_id=request.imdb_id,
    )

    options = LookupOptions(
        force_refresh=request.force,
        include_raw_responses=request.include_raw,
    )

    # Execute lookup
    try:
        with create_pipeline() as pipeline:
            result = pipeline.lookup(query, options)
    except Exception:
        _record_metadata_lookup_route_duration("error", started_at)
        _log_metadata_lookup_route_result(
            result="error",
            media_type=media_type.value,
            started_at=started_at,
            force=request.force,
            include_raw=request.include_raw,
        )
        raise

    if result is None:
        _record_metadata_lookup_route_duration("not_found", started_at)
        _log_metadata_lookup_route_result(
            result="not_found",
            media_type=media_type.value,
            started_at=started_at,
            force=request.force,
            include_raw=request.include_raw,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No metadata found",
        )

    # Convert to response
    series_response = None
    if result.series:
        series_response = SeriesInfoResponse(
            series_id=result.series.series_id,
            series_title=result.series.series_title,
            season=result.series.season,
            episode=result.series.episode,
            episode_id=result.series.episode_id,
            episode_title=result.series.episode_title,
        )

    source_id_count = len(result.source_ids.to_dict())
    contributing_source_count = len(result.contributing_sources or [])
    _record_metadata_lookup_route_duration("success", started_at)
    _log_metadata_lookup_route_result(
        result="success",
        media_type=media_type.value,
        started_at=started_at,
        force=request.force,
        include_raw=request.include_raw,
        contributing_sources=contributing_source_count,
        source_ids=source_id_count,
    )

    return UnifiedMetadataResponse(
        title=result.title,
        type=result.type.value,
        year=result.year,
        genres=result.genres,
        summary=result.summary,
        cover=result.cover_url or result.cover_file,
        cover_url=result.cover_url,
        cover_file=result.cover_file,
        author=result.author,
        language=result.language,
        runtime_minutes=result.runtime_minutes,
        rating=result.rating,
        votes=result.votes,
        series=series_response,
        confidence=result.confidence.value,
        primary_source=result.primary_source.value if result.primary_source else None,
        contributing_sources=[s.value for s in result.contributing_sources] if result.contributing_sources else [],
        source_ids=result.source_ids.to_dict(),
        queried_at=result.queried_at.isoformat() if result.queried_at else None,
        error=result.error,
        raw_responses=result.raw_responses if request.include_raw else None,
    )


__all__ = ["router"]
