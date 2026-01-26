"""Unified metadata lookup service."""

from __future__ import annotations

from typing import Any, Dict, Optional

from ..types import LookupOptions, LookupQuery, MediaType, UnifiedMetadataResult
from ..pipeline import MetadataLookupPipeline, create_pipeline


class UnifiedMetadataService:
    """Unified service for metadata lookups across all media types.

    Provides a simple interface for metadata lookups with automatic
    source selection and fallback.
    """

    def __init__(
        self,
        pipeline: Optional[MetadataLookupPipeline] = None,
    ) -> None:
        """Initialize the service.

        Args:
            pipeline: Pipeline to use. If None, creates from config.
        """
        self._pipeline = pipeline or create_pipeline()

    def lookup_book(
        self,
        *,
        title: Optional[str] = None,
        author: Optional[str] = None,
        isbn: Optional[str] = None,
        force: bool = False,
    ) -> Optional[UnifiedMetadataResult]:
        """Look up book metadata.

        Args:
            title: Book title.
            author: Book author.
            isbn: ISBN-10 or ISBN-13.
            force: Force refresh, ignoring cache.

        Returns:
            UnifiedMetadataResult if found.
        """
        query = LookupQuery(
            media_type=MediaType.BOOK,
            title=title,
            author=author,
            isbn=isbn,
        )
        options = LookupOptions(force_refresh=force)
        return self._pipeline.lookup(query, options)

    def lookup_movie(
        self,
        *,
        title: Optional[str] = None,
        year: Optional[int] = None,
        imdb_id: Optional[str] = None,
        tmdb_id: Optional[int] = None,
        force: bool = False,
    ) -> Optional[UnifiedMetadataResult]:
        """Look up movie metadata.

        Args:
            title: Movie title.
            year: Release year.
            imdb_id: IMDB ID for direct lookup.
            tmdb_id: TMDB ID for direct lookup.
            force: Force refresh, ignoring cache.

        Returns:
            UnifiedMetadataResult if found.
        """
        query = LookupQuery(
            media_type=MediaType.MOVIE,
            movie_title=title,
            year=year,
            imdb_id=imdb_id,
            tmdb_id=tmdb_id,
        )
        options = LookupOptions(force_refresh=force)
        return self._pipeline.lookup(query, options)

    def lookup_tv_series(
        self,
        *,
        series_name: Optional[str] = None,
        imdb_id: Optional[str] = None,
        tmdb_id: Optional[int] = None,
        force: bool = False,
    ) -> Optional[UnifiedMetadataResult]:
        """Look up TV series metadata.

        Args:
            series_name: Series name.
            imdb_id: IMDB ID for direct lookup.
            tmdb_id: TMDB ID for direct lookup.
            force: Force refresh, ignoring cache.

        Returns:
            UnifiedMetadataResult if found.
        """
        query = LookupQuery(
            media_type=MediaType.TV_SERIES,
            series_name=series_name,
            imdb_id=imdb_id,
            tmdb_id=tmdb_id,
        )
        options = LookupOptions(force_refresh=force)
        return self._pipeline.lookup(query, options)

    def lookup_tv_episode(
        self,
        *,
        series_name: Optional[str] = None,
        season: Optional[int] = None,
        episode: Optional[int] = None,
        tmdb_id: Optional[int] = None,
        force: bool = False,
    ) -> Optional[UnifiedMetadataResult]:
        """Look up TV episode metadata.

        Args:
            series_name: Series name.
            season: Season number.
            episode: Episode number.
            tmdb_id: TMDB series ID for direct lookup.
            force: Force refresh, ignoring cache.

        Returns:
            UnifiedMetadataResult if found.
        """
        query = LookupQuery(
            media_type=MediaType.TV_EPISODE,
            series_name=series_name,
            season=season,
            episode=episode,
            tmdb_id=tmdb_id,
        )
        options = LookupOptions(force_refresh=force)
        return self._pipeline.lookup(query, options)

    def lookup_youtube(
        self,
        *,
        video_id: Optional[str] = None,
        url: Optional[str] = None,
        source_filename: Optional[str] = None,
        force: bool = False,
    ) -> Optional[UnifiedMetadataResult]:
        """Look up YouTube video metadata.

        Args:
            video_id: YouTube video ID.
            url: YouTube URL.
            source_filename: Filename that may contain video ID.
            force: Force refresh, ignoring cache.

        Returns:
            UnifiedMetadataResult if found.
        """
        query = LookupQuery(
            media_type=MediaType.YOUTUBE_VIDEO,
            youtube_video_id=video_id,
            youtube_url=url,
            source_filename=source_filename,
        )
        options = LookupOptions(force_refresh=force)
        return self._pipeline.lookup(query, options)

    def lookup(
        self,
        query: LookupQuery,
        options: Optional[LookupOptions] = None,
    ) -> Optional[UnifiedMetadataResult]:
        """Execute a custom lookup query.

        Args:
            query: The lookup query.
            options: Lookup options.

        Returns:
            UnifiedMetadataResult if found.
        """
        return self._pipeline.lookup(query, options)

    def close(self) -> None:
        """Release resources."""
        self._pipeline.close()

    def __enter__(self) -> "UnifiedMetadataService":
        return self

    def __exit__(self, *args) -> None:
        self.close()


__all__ = ["UnifiedMetadataService"]
