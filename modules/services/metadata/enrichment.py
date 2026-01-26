"""Metadata enrichment utilities using the unified lookup pipeline.

This module provides helpers to enrich existing metadata with data from
external sources via the unified metadata lookup pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional

from modules import logging_manager

from .services.unified_service import UnifiedMetadataService
from .types import ConfidenceLevel, MediaType, UnifiedMetadataResult

LOGGER = logging_manager.get_logger().getChild("metadata.enrichment")


@dataclass(slots=True)
class EnrichmentResult:
    """Result of metadata enrichment operation."""

    enriched: bool
    """Whether metadata was successfully enriched."""

    metadata: Dict[str, Any]
    """The enriched metadata dictionary."""

    source_result: Optional[UnifiedMetadataResult]
    """The raw result from the unified lookup pipeline (if successful)."""

    confidence: Optional[str]
    """Confidence level of the enrichment."""


def _is_already_enriched(metadata: Mapping[str, Any]) -> bool:
    """Check if metadata has already been enriched."""
    return bool(metadata.get("_enrichment_source"))


def enrich_book_metadata(
    existing_metadata: Mapping[str, Any],
    *,
    force: bool = False,
    service: Optional[UnifiedMetadataService] = None,
) -> EnrichmentResult:
    """Enrich book metadata using the unified metadata pipeline.

    This function attempts to enrich existing book metadata by looking up
    additional information from external sources (OpenLibrary, Google Books,
    TMDB for adaptations, etc.).

    Args:
        existing_metadata: Current metadata dictionary to enrich.
        force: Force refresh even if we have existing data.
        service: Optional UnifiedMetadataService instance. If None, creates one.

    Returns:
        EnrichmentResult with enriched metadata and lookup details.
    """
    result_metadata = dict(existing_metadata)

    # Skip if already enriched (unless force=True)
    if not force and _is_already_enriched(existing_metadata):
        LOGGER.debug("Skipping enrichment - metadata already enriched")
        return EnrichmentResult(
            enriched=False,
            metadata=result_metadata,
            source_result=None,
            confidence=existing_metadata.get("_enrichment_confidence"),
        )

    # Extract lookup parameters from existing metadata
    title = _extract_title(existing_metadata)
    author = _extract_author(existing_metadata)
    isbn = _extract_isbn(existing_metadata)

    if not title and not isbn:
        LOGGER.debug("No title or ISBN available for book lookup")
        return EnrichmentResult(
            enriched=False,
            metadata=result_metadata,
            source_result=None,
            confidence=None,
        )

    # Create or use provided service
    close_service = False
    if service is None:
        service = UnifiedMetadataService()
        close_service = True

    try:
        lookup_result = service.lookup_book(
            title=title,
            author=author,
            isbn=isbn,
            force=force,
        )

        if lookup_result is None:
            LOGGER.debug(
                "No results from unified book lookup for title=%s, author=%s, isbn=%s",
                title,
                author,
                isbn,
            )
            return EnrichmentResult(
                enriched=False,
                metadata=result_metadata,
                source_result=None,
                confidence=None,
            )

        # Merge the lookup result into existing metadata
        result_metadata = _merge_book_metadata(result_metadata, lookup_result)

        return EnrichmentResult(
            enriched=True,
            metadata=result_metadata,
            source_result=lookup_result,
            confidence=lookup_result.confidence.value,
        )

    except Exception as exc:
        LOGGER.warning(
            "Failed to enrich book metadata: %s",
            exc,
            extra={"event": "metadata.enrichment.failed"},
        )
        return EnrichmentResult(
            enriched=False,
            metadata=result_metadata,
            source_result=None,
            confidence=None,
        )
    finally:
        if close_service:
            service.close()


def enrich_movie_metadata(
    existing_metadata: Mapping[str, Any],
    *,
    force: bool = False,
    service: Optional[UnifiedMetadataService] = None,
) -> EnrichmentResult:
    """Enrich movie/video metadata using the unified metadata pipeline.

    Args:
        existing_metadata: Current metadata dictionary to enrich.
        force: Force refresh even if we have existing data.
        service: Optional UnifiedMetadataService instance.

    Returns:
        EnrichmentResult with enriched metadata.
    """
    result_metadata = dict(existing_metadata)

    # Skip if already enriched (unless force=True)
    if not force and _is_already_enriched(existing_metadata):
        LOGGER.debug("Skipping movie enrichment - metadata already enriched")
        return EnrichmentResult(
            enriched=False,
            metadata=result_metadata,
            source_result=None,
            confidence=existing_metadata.get("_enrichment_confidence"),
        )

    title = _extract_title(existing_metadata)
    year = _extract_year(existing_metadata)
    imdb_id = existing_metadata.get("imdb_id")

    if not title and not imdb_id:
        LOGGER.debug("No title or IMDB ID available for movie lookup")
        return EnrichmentResult(
            enriched=False,
            metadata=result_metadata,
            source_result=None,
            confidence=None,
        )

    close_service = False
    if service is None:
        service = UnifiedMetadataService()
        close_service = True

    try:
        lookup_result = service.lookup_movie(
            title=title,
            year=year,
            imdb_id=imdb_id,
            force=force,
        )

        if lookup_result is None:
            return EnrichmentResult(
                enriched=False,
                metadata=result_metadata,
                source_result=None,
                confidence=None,
            )

        result_metadata = _merge_movie_metadata(result_metadata, lookup_result)

        return EnrichmentResult(
            enriched=True,
            metadata=result_metadata,
            source_result=lookup_result,
            confidence=lookup_result.confidence.value,
        )

    except Exception as exc:
        LOGGER.warning("Failed to enrich movie metadata: %s", exc)
        return EnrichmentResult(
            enriched=False,
            metadata=result_metadata,
            source_result=None,
            confidence=None,
        )
    finally:
        if close_service:
            service.close()


def enrich_tv_metadata(
    existing_metadata: Mapping[str, Any],
    *,
    force: bool = False,
    service: Optional[UnifiedMetadataService] = None,
) -> EnrichmentResult:
    """Enrich TV series/episode metadata using the unified metadata pipeline.

    Args:
        existing_metadata: Current metadata dictionary to enrich.
        force: Force refresh even if we have existing data.
        service: Optional UnifiedMetadataService instance.

    Returns:
        EnrichmentResult with enriched metadata.
    """
    result_metadata = dict(existing_metadata)

    # Skip if already enriched (unless force=True)
    if not force and _is_already_enriched(existing_metadata):
        LOGGER.debug("Skipping TV enrichment - metadata already enriched")
        return EnrichmentResult(
            enriched=False,
            metadata=result_metadata,
            source_result=None,
            confidence=existing_metadata.get("_enrichment_confidence"),
        )

    series_name = existing_metadata.get("series_name") or _extract_title(existing_metadata)
    season = existing_metadata.get("season")
    episode = existing_metadata.get("episode")

    if not series_name:
        LOGGER.debug("No series name available for TV lookup")
        return EnrichmentResult(
            enriched=False,
            metadata=result_metadata,
            source_result=None,
            confidence=None,
        )

    close_service = False
    if service is None:
        service = UnifiedMetadataService()
        close_service = True

    try:
        # Determine if we're looking up a series or episode
        if season is not None and episode is not None:
            lookup_result = service.lookup_tv_episode(
                series_name=series_name,
                season=int(season),
                episode=int(episode),
                force=force,
            )
        else:
            lookup_result = service.lookup_tv_series(
                series_name=series_name,
                force=force,
            )

        if lookup_result is None:
            return EnrichmentResult(
                enriched=False,
                metadata=result_metadata,
                source_result=None,
                confidence=None,
            )

        result_metadata = _merge_tv_metadata(result_metadata, lookup_result)

        return EnrichmentResult(
            enriched=True,
            metadata=result_metadata,
            source_result=lookup_result,
            confidence=lookup_result.confidence.value,
        )

    except Exception as exc:
        LOGGER.warning("Failed to enrich TV metadata: %s", exc)
        return EnrichmentResult(
            enriched=False,
            metadata=result_metadata,
            source_result=None,
            confidence=None,
        )
    finally:
        if close_service:
            service.close()


def detect_media_type(metadata: Mapping[str, Any]) -> MediaType:
    """Detect the media type from existing metadata.

    Args:
        metadata: Metadata dictionary to analyze.

    Returns:
        Detected MediaType.
    """
    # Check explicit type indicators
    job_type = str(metadata.get("job_type") or metadata.get("type") or "").lower()

    if job_type in ("youtube", "youtube_video"):
        return MediaType.YOUTUBE_VIDEO
    if job_type in ("movie", "film"):
        return MediaType.MOVIE
    if job_type in ("tv_series", "tv_show", "series"):
        return MediaType.TV_SERIES
    if job_type in ("tv_episode", "episode"):
        return MediaType.TV_EPISODE

    # Check for YouTube-specific fields
    if metadata.get("youtube_video_id") or metadata.get("youtube_url"):
        return MediaType.YOUTUBE_VIDEO

    # Check for TV-specific fields
    if metadata.get("series_name") and (metadata.get("season") or metadata.get("episode")):
        return MediaType.TV_EPISODE
    if metadata.get("series_name"):
        return MediaType.TV_SERIES

    # Check for book-specific fields (ISBN, author for books)
    if metadata.get("isbn") or metadata.get("isbn_13"):
        return MediaType.BOOK

    # Check for IMDB/TMDB IDs suggesting movie/TV
    if metadata.get("imdb_id") or metadata.get("tmdb_id"):
        # Could be movie or TV; default to movie unless series info present
        return MediaType.MOVIE

    # Default to book for ebook-tools pipeline jobs
    return MediaType.BOOK


def enrich_metadata(
    existing_metadata: Mapping[str, Any],
    *,
    media_type: Optional[MediaType] = None,
    force: bool = False,
    service: Optional[UnifiedMetadataService] = None,
) -> EnrichmentResult:
    """Enrich metadata by auto-detecting type and using appropriate lookup.

    Args:
        existing_metadata: Current metadata to enrich.
        media_type: Optional explicit media type. Auto-detected if None.
        force: Force refresh ignoring cache.
        service: Optional UnifiedMetadataService instance.

    Returns:
        EnrichmentResult with enriched metadata.
    """
    if media_type is None:
        media_type = detect_media_type(existing_metadata)

    LOGGER.debug("Enriching metadata as %s", media_type.value)

    if media_type == MediaType.BOOK:
        return enrich_book_metadata(existing_metadata, force=force, service=service)
    elif media_type == MediaType.MOVIE:
        return enrich_movie_metadata(existing_metadata, force=force, service=service)
    elif media_type in (MediaType.TV_SERIES, MediaType.TV_EPISODE):
        return enrich_tv_metadata(existing_metadata, force=force, service=service)
    else:
        # YouTube - handled separately (no enrichment from external APIs needed)
        return EnrichmentResult(
            enriched=False,
            metadata=dict(existing_metadata),
            source_result=None,
            confidence=None,
        )


# -----------------------------------------------------------------------------
# Helper functions for extracting metadata fields
# -----------------------------------------------------------------------------


def _extract_title(metadata: Mapping[str, Any]) -> Optional[str]:
    """Extract title from various metadata field names."""
    for key in ("book_title", "title", "movie_title", "series_name"):
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _extract_author(metadata: Mapping[str, Any]) -> Optional[str]:
    """Extract author from various metadata field names."""
    for key in ("book_author", "author", "creator", "director"):
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _extract_isbn(metadata: Mapping[str, Any]) -> Optional[str]:
    """Extract ISBN from metadata."""
    for key in ("isbn", "isbn_13", "isbn_10"):
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _extract_year(metadata: Mapping[str, Any]) -> Optional[int]:
    """Extract year from metadata."""
    for key in ("year", "book_year", "release_year", "publish_year"):
        value = metadata.get(key)
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.strip():
            try:
                return int(value.strip())
            except ValueError:
                continue
    return None


# -----------------------------------------------------------------------------
# Helper functions for merging lookup results
# -----------------------------------------------------------------------------


def _merge_book_metadata(
    existing: Dict[str, Any],
    result: UnifiedMetadataResult,
) -> Dict[str, Any]:
    """Merge book lookup result into existing metadata."""
    merged = dict(existing)

    # Map unified result fields to book metadata fields
    if result.title and not existing.get("book_title"):
        merged["book_title"] = result.title

    if result.author and not existing.get("book_author"):
        merged["book_author"] = result.author

    if result.year is not None and not existing.get("book_year"):
        merged["book_year"] = str(result.year)

    if result.summary and not existing.get("book_summary"):
        merged["book_summary"] = result.summary

    if result.genres and not existing.get("book_genre"):
        merged["book_genre"] = ", ".join(result.genres)

    # Cover handling
    cover_url = result.cover_url or result.cover_file
    if cover_url and not existing.get("book_cover_file"):
        merged["book_cover_file"] = cover_url
        merged["book_cover_url"] = cover_url

    # Source IDs
    source_ids = result.source_ids.to_dict()
    for key, value in source_ids.items():
        if value and key not in existing:
            merged[key] = value

    # Store enrichment provenance
    merged["_enrichment_source"] = result.primary_source.value if result.primary_source else None
    merged["_enrichment_confidence"] = result.confidence.value

    return merged


def _merge_movie_metadata(
    existing: Dict[str, Any],
    result: UnifiedMetadataResult,
) -> Dict[str, Any]:
    """Merge movie lookup result into existing metadata."""
    merged = dict(existing)

    if result.title and not existing.get("title"):
        merged["title"] = result.title
        merged["movie_title"] = result.title

    if result.year is not None and not existing.get("year"):
        merged["year"] = result.year

    if result.summary and not existing.get("summary"):
        merged["summary"] = result.summary

    if result.genres and not existing.get("genres"):
        merged["genres"] = result.genres

    if result.runtime_minutes and not existing.get("runtime_minutes"):
        merged["runtime_minutes"] = result.runtime_minutes

    if result.rating and not existing.get("rating"):
        merged["rating"] = result.rating

    cover_url = result.cover_url or result.cover_file
    if cover_url and not existing.get("cover_url"):
        merged["cover_url"] = cover_url

    source_ids = result.source_ids.to_dict()
    for key, value in source_ids.items():
        if value and key not in existing:
            merged[key] = value

    merged["_enrichment_source"] = result.primary_source.value if result.primary_source else None
    merged["_enrichment_confidence"] = result.confidence.value

    return merged


def _merge_tv_metadata(
    existing: Dict[str, Any],
    result: UnifiedMetadataResult,
) -> Dict[str, Any]:
    """Merge TV series/episode lookup result into existing metadata."""
    merged = dict(existing)

    if result.title and not existing.get("title"):
        merged["title"] = result.title

    if result.series:
        if result.series.series_title and not existing.get("series_name"):
            merged["series_name"] = result.series.series_title
        if result.series.season is not None and not existing.get("season"):
            merged["season"] = result.series.season
        if result.series.episode is not None and not existing.get("episode"):
            merged["episode"] = result.series.episode
        if result.series.episode_title and not existing.get("episode_title"):
            merged["episode_title"] = result.series.episode_title

    if result.year is not None and not existing.get("year"):
        merged["year"] = result.year

    if result.summary and not existing.get("summary"):
        merged["summary"] = result.summary

    if result.genres and not existing.get("genres"):
        merged["genres"] = result.genres

    cover_url = result.cover_url or result.cover_file
    if cover_url and not existing.get("cover_url"):
        merged["cover_url"] = cover_url

    source_ids = result.source_ids.to_dict()
    for key, value in source_ids.items():
        if value and key not in existing:
            merged[key] = value

    merged["_enrichment_source"] = result.primary_source.value if result.primary_source else None
    merged["_enrichment_confidence"] = result.confidence.value

    return merged


__all__ = [
    "EnrichmentResult",
    "detect_media_type",
    "enrich_book_metadata",
    "enrich_metadata",
    "enrich_movie_metadata",
    "enrich_tv_metadata",
]
