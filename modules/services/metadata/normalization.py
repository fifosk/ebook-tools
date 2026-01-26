"""Result normalization and merging utilities for metadata lookup."""

from __future__ import annotations

from typing import List, Optional

from .types import ConfidenceLevel, UnifiedMetadataResult


def merge_results(results: List[UnifiedMetadataResult]) -> UnifiedMetadataResult:
    """Merge multiple lookup results into a single result.

    Strategy:
    - Title: Prefer primary (first) source
    - Year: Prefer primary, fallback to others
    - Genres: Union of all, deduplicated
    - Summary: Prefer primary, or longest non-None
    - Cover: Prefer primary source
    - Source IDs: Merge all
    - Confidence: Min of all contributing sources (conservative)

    Args:
        results: List of results to merge (at least one required).

    Returns:
        A merged UnifiedMetadataResult.

    Raises:
        ValueError: If results list is empty.
    """
    if not results:
        raise ValueError("Cannot merge empty results list")

    if len(results) == 1:
        return results[0]

    primary = results[0]

    # Start with a mutable copy of primary
    merged = UnifiedMetadataResult(
        title=primary.title,
        type=primary.type,
        year=primary.year,
        genres=list(primary.genres),
        summary=primary.summary,
        cover_url=primary.cover_url,
        cover_file=primary.cover_file,
        series=primary.series,
        source_ids=primary.source_ids,
        confidence=primary.confidence,
        primary_source=primary.primary_source,
        contributing_sources=list(primary.contributing_sources) if primary.contributing_sources else [],
        queried_at=primary.queried_at,
        author=primary.author,
        language=primary.language,
        runtime_minutes=primary.runtime_minutes,
        rating=primary.rating,
        votes=primary.votes,
        channel_name=primary.channel_name,
        view_count=primary.view_count,
        like_count=primary.like_count,
        upload_date=primary.upload_date,
        raw_responses=dict(primary.raw_responses) if primary.raw_responses else {},
        error=primary.error,
    )

    # Merge from secondary sources
    for secondary in results[1:]:
        # Add to contributing sources
        if secondary.primary_source and secondary.primary_source not in merged.contributing_sources:
            merged.contributing_sources.append(secondary.primary_source)

        # Fill missing year
        if merged.year is None and secondary.year is not None:
            merged.year = secondary.year

        # Merge genres
        for genre in secondary.genres:
            normalized = genre.strip()
            if normalized and not _genre_exists(normalized, merged.genres):
                merged.genres.append(normalized)

        # Fill missing summary or prefer longer
        if merged.summary is None:
            merged.summary = secondary.summary
        elif secondary.summary and len(secondary.summary) > len(merged.summary or ""):
            # Only use secondary if significantly longer
            if len(secondary.summary) > len(merged.summary or "") * 1.2:
                merged.summary = secondary.summary

        # Fill missing cover
        if merged.cover_url is None:
            merged.cover_url = secondary.cover_url
        if merged.cover_file is None:
            merged.cover_file = secondary.cover_file

        # Merge source IDs
        merged.source_ids = merged.source_ids.merge_with(secondary.source_ids)

        # Fill missing author
        if merged.author is None:
            merged.author = secondary.author

        # Fill missing language
        if merged.language is None:
            merged.language = secondary.language

        # Fill missing runtime
        if merged.runtime_minutes is None:
            merged.runtime_minutes = secondary.runtime_minutes

        # Fill missing rating (prefer higher votes for tie-breaking)
        if merged.rating is None:
            merged.rating = secondary.rating
            merged.votes = secondary.votes
        elif secondary.rating is not None and secondary.votes is not None:
            # If secondary has more votes, might be more reliable
            if merged.votes is None or (secondary.votes > merged.votes * 2):
                merged.rating = secondary.rating
                merged.votes = secondary.votes

        # Fill missing series info
        if merged.series is None and secondary.series is not None:
            merged.series = secondary.series

        # Merge raw responses
        if secondary.raw_responses:
            merged.raw_responses.update(secondary.raw_responses)

        # Confidence: use minimum (most conservative)
        confidence_order = [ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM, ConfidenceLevel.LOW]
        secondary_idx = confidence_order.index(secondary.confidence)
        merged_idx = confidence_order.index(merged.confidence)
        if secondary_idx > merged_idx:
            merged.confidence = secondary.confidence

    return merged


def deduplicate_genres(genres: List[str]) -> List[str]:
    """Remove duplicate genres, preserving order.

    Comparison is case-insensitive but original casing is preserved.

    Args:
        genres: List of genre strings.

    Returns:
        Deduplicated list with original casing.
    """
    seen: set[str] = set()
    result: List[str] = []
    for genre in genres:
        normalized = genre.strip().lower()
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(genre.strip())
    return result


def _genre_exists(genre: str, genre_list: List[str]) -> bool:
    """Check if a genre already exists in the list (case-insensitive)."""
    normalized = genre.strip().lower()
    return any(g.strip().lower() == normalized for g in genre_list)


def normalize_genre_name(genre: str) -> str:
    """Normalize a genre name to consistent format.

    Args:
        genre: Raw genre string.

    Returns:
        Normalized genre string.
    """
    # Title case, but preserve some acronyms
    genre = genre.strip()
    if not genre:
        return genre

    # Common genre mappings for consistency
    mappings = {
        "sci-fi": "Science Fiction",
        "scifi": "Science Fiction",
        "science-fiction": "Science Fiction",
        "rom-com": "Romantic Comedy",
        "romcom": "Romantic Comedy",
        "doc": "Documentary",
        "docs": "Documentary",
    }

    lower = genre.lower()
    if lower in mappings:
        return mappings[lower]

    return genre.title()


def compute_confidence(
    *,
    has_title: bool,
    has_year: bool,
    has_summary: bool,
    has_cover: bool,
    has_genres: bool,
    is_exact_match: bool = False,
) -> ConfidenceLevel:
    """Compute confidence level based on field presence.

    Args:
        has_title: Whether title is present.
        has_year: Whether year is present.
        has_summary: Whether summary is present.
        has_cover: Whether cover is present.
        has_genres: Whether genres are present.
        is_exact_match: Whether this was an exact ID match.

    Returns:
        Computed confidence level.
    """
    if is_exact_match:
        return ConfidenceLevel.HIGH

    # Count required fields present
    present_count = sum([has_title, has_year, has_summary, has_cover, has_genres])

    if present_count >= 4:
        return ConfidenceLevel.MEDIUM
    elif present_count >= 2:
        return ConfidenceLevel.LOW
    else:
        return ConfidenceLevel.LOW


def select_best_cover(results: List[UnifiedMetadataResult]) -> Optional[str]:
    """Select the best cover URL from multiple results.

    Prefers covers from primary sources and higher confidence results.

    Args:
        results: List of results with potential covers.

    Returns:
        Best cover URL, or None if no covers found.
    """
    # First pass: high confidence covers
    for result in results:
        if result.confidence == ConfidenceLevel.HIGH and result.cover_url:
            return result.cover_url

    # Second pass: any cover
    for result in results:
        if result.cover_url:
            return result.cover_url

    return None


__all__ = [
    "merge_results",
    "deduplicate_genres",
    "normalize_genre_name",
    "compute_confidence",
    "select_best_cover",
]
