"""OMDb (Open Movie Database) API client for movie and TV metadata."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, List, Mapping, Optional

import requests

from modules import logging_manager as log_mgr

from ..types import (
    ConfidenceLevel,
    LookupOptions,
    LookupQuery,
    MediaType,
    MetadataSource,
    SeriesInfo,
    SourceIds,
    UnifiedMetadataResult,
)
from .base import BaseMetadataClient

logger = log_mgr.get_logger().getChild("services.metadata.clients.omdb")

_OMDB_BASE_URL = "https://www.omdbapi.com"


def _normalize_text(value: Any) -> Optional[str]:
    """Normalize a string value."""
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    # OMDb uses "N/A" for missing values
    if cleaned.upper() == "N/A":
        return None
    return cleaned or None


def _normalize_int(value: Any) -> Optional[int]:
    """Normalize an integer value."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        # Remove commas from numbers like "1,234"
        cleaned = value.replace(",", "").strip()
        if cleaned.upper() == "N/A":
            return None
        try:
            return int(cleaned)
        except ValueError:
            return None
    return None


def _normalize_float(value: Any) -> Optional[float]:
    """Normalize a float value."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.strip()
        if cleaned.upper() == "N/A":
            return None
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def _parse_runtime(value: Any) -> Optional[int]:
    """Parse runtime string like '120 min' to integer minutes."""
    text = _normalize_text(value)
    if not text:
        return None
    match = re.search(r"(\d+)", text)
    if match:
        return int(match.group(1))
    return None


def _format_episode_code(season: int, episode: int) -> str:
    """Format season/episode as SxxEyy code."""
    return f"S{season:02d}E{episode:02d}"


class OMDbClient(BaseMetadataClient):
    """OMDb API client for movie and TV metadata.

    Requires an OMDb API key. Get one at:
    http://www.omdbapi.com/apikey.aspx
    """

    name = MetadataSource.OMDB
    supported_types = (MediaType.MOVIE, MediaType.TV_SERIES, MediaType.TV_EPISODE)
    requires_api_key = True

    def __init__(
        self,
        *,
        session: Optional[requests.Session] = None,
        api_key: Optional[str] = None,
        timeout_seconds: float = 10.0,
        base_url: str = _OMDB_BASE_URL,
    ) -> None:
        super().__init__(session=session, api_key=api_key, timeout_seconds=timeout_seconds)
        self._base_url = base_url.rstrip("/")

    def _get_with_auth(
        self,
        *,
        params: Optional[dict] = None,
        timeout: Optional[float] = None,
    ) -> Optional[dict]:
        """Make authenticated GET request to OMDb API."""
        if not self._api_key:
            return None

        query_params = {"apikey": self._api_key}
        if params:
            query_params.update(params)

        result = self._get(self._base_url, params=query_params, timeout=timeout)

        # Check for OMDb error response
        if result and result.get("Response") == "False":
            error = result.get("Error", "Unknown error")
            logger.debug("OMDb API error: %s", error)
            return None

        return result

    def lookup(
        self,
        query: LookupQuery,
        options: LookupOptions,
    ) -> Optional[UnifiedMetadataResult]:
        """Look up movie or TV metadata from OMDb."""
        if not self.is_available:
            return None

        if query.media_type == MediaType.MOVIE:
            return self._lookup_movie(query, options)
        elif query.media_type == MediaType.TV_EPISODE:
            return self._lookup_tv_episode(query, options)
        elif query.media_type == MediaType.TV_SERIES:
            return self._lookup_tv_series(query, options)
        return None

    def _lookup_movie(
        self,
        query: LookupQuery,
        options: LookupOptions,
    ) -> Optional[UnifiedMetadataResult]:
        """Look up movie by title and optional year."""
        # Prefer IMDB ID if available
        if query.imdb_id:
            logger.info("Looking up OMDb movie by IMDB ID: %s", query.imdb_id)
            payload = self._get_with_auth(
                params={"i": query.imdb_id, "type": "movie", "plot": "full"},
                timeout=options.timeout_seconds,
            )
        else:
            title = query.movie_title or query.title
            if not title:
                return None

            logger.info("Searching OMDb for movie: %s (year=%s)", title, query.year)

            params = {"t": title, "type": "movie", "plot": "full"}
            if query.year:
                params["y"] = str(query.year)

            payload = self._get_with_auth(params=params, timeout=options.timeout_seconds)

        if not payload:
            return None

        return self._parse_movie_response(payload, query, options)

    def _parse_movie_response(
        self,
        data: Mapping[str, Any],
        query: LookupQuery,
        options: LookupOptions,
    ) -> UnifiedMetadataResult:
        """Parse movie response into unified result."""
        title = _normalize_text(data.get("Title")) or query.title or "Unknown"

        # Extract year
        year_str = _normalize_text(data.get("Year"))
        year = None
        if year_str:
            match = re.match(r"(\d{4})", year_str)
            if match:
                year = int(match.group(1))

        # Extract genres (comma-separated)
        genres_str = _normalize_text(data.get("Genre"))
        genres: List[str] = []
        if genres_str:
            genres = [g.strip() for g in genres_str.split(",") if g.strip()]

        # Extract summary
        summary = _normalize_text(data.get("Plot"))

        # Extract poster
        cover_url = _normalize_text(data.get("Poster"))

        # Extract runtime
        runtime = _parse_runtime(data.get("Runtime"))

        # Extract rating (IMDB rating)
        rating = _normalize_float(data.get("imdbRating"))
        votes_str = data.get("imdbVotes")
        votes = _normalize_int(votes_str)

        # Extract language
        language = _normalize_text(data.get("Language"))
        if language:
            # Take first language if comma-separated
            language = language.split(",")[0].strip()

        # Extract director as "author"
        director = _normalize_text(data.get("Director"))

        # Extract IMDB ID
        imdb_id = _normalize_text(data.get("imdbID"))

        source_ids = SourceIds(imdb_id=imdb_id)

        return UnifiedMetadataResult(
            title=title,
            type=MediaType.MOVIE,
            year=year,
            genres=genres[:10],
            summary=summary,
            cover_url=cover_url,
            source_ids=source_ids,
            confidence=ConfidenceLevel.HIGH if query.imdb_id else ConfidenceLevel.MEDIUM,
            primary_source=MetadataSource.OMDB,
            contributing_sources=[MetadataSource.OMDB],
            queried_at=datetime.now(timezone.utc),
            author=director,
            language=language,
            runtime_minutes=runtime,
            rating=rating,
            votes=votes,
            raw_responses={"omdb": dict(data)} if options.include_raw_responses else {},
        )

    def _lookup_tv_series(
        self,
        query: LookupQuery,
        options: LookupOptions,
    ) -> Optional[UnifiedMetadataResult]:
        """Look up TV series by name."""
        # Prefer IMDB ID if available
        if query.imdb_id:
            logger.info("Looking up OMDb series by IMDB ID: %s", query.imdb_id)
            payload = self._get_with_auth(
                params={"i": query.imdb_id, "type": "series", "plot": "full"},
                timeout=options.timeout_seconds,
            )
        else:
            series_name = query.series_name or query.title
            if not series_name:
                return None

            logger.info("Searching OMDb for series: %s", series_name)

            payload = self._get_with_auth(
                params={"t": series_name, "type": "series", "plot": "full"},
                timeout=options.timeout_seconds,
            )

        if not payload:
            return None

        return self._parse_series_response(payload, query, options)

    def _parse_series_response(
        self,
        data: Mapping[str, Any],
        query: LookupQuery,
        options: LookupOptions,
    ) -> UnifiedMetadataResult:
        """Parse series response into unified result."""
        title = _normalize_text(data.get("Title")) or query.series_name or "Unknown"

        # Extract year (may be "2010–2013" or "2010–")
        year_str = _normalize_text(data.get("Year"))
        year = None
        if year_str:
            match = re.match(r"(\d{4})", year_str)
            if match:
                year = int(match.group(1))

        # Extract genres
        genres_str = _normalize_text(data.get("Genre"))
        genres: List[str] = []
        if genres_str:
            genres = [g.strip() for g in genres_str.split(",") if g.strip()]

        # Extract summary
        summary = _normalize_text(data.get("Plot"))

        # Extract poster
        cover_url = _normalize_text(data.get("Poster"))

        # Extract runtime
        runtime = _parse_runtime(data.get("Runtime"))

        # Extract rating
        rating = _normalize_float(data.get("imdbRating"))
        votes = _normalize_int(data.get("imdbVotes"))

        # Extract language
        language = _normalize_text(data.get("Language"))
        if language:
            language = language.split(",")[0].strip()

        # Extract IMDB ID
        imdb_id = _normalize_text(data.get("imdbID"))

        source_ids = SourceIds(imdb_id=imdb_id)

        return UnifiedMetadataResult(
            title=title,
            type=MediaType.TV_SERIES,
            year=year,
            genres=genres[:10],
            summary=summary,
            cover_url=cover_url,
            source_ids=source_ids,
            confidence=ConfidenceLevel.HIGH if query.imdb_id else ConfidenceLevel.MEDIUM,
            primary_source=MetadataSource.OMDB,
            contributing_sources=[MetadataSource.OMDB],
            queried_at=datetime.now(timezone.utc),
            language=language,
            runtime_minutes=runtime,
            rating=rating,
            votes=votes,
            raw_responses={"omdb": dict(data)} if options.include_raw_responses else {},
        )

    def _lookup_tv_episode(
        self,
        query: LookupQuery,
        options: LookupOptions,
    ) -> Optional[UnifiedMetadataResult]:
        """Look up TV episode by series name, season, and episode number."""
        series_name = query.series_name or query.title
        if not series_name or query.season is None or query.episode is None:
            return None

        logger.info(
            "Looking up OMDb episode: %s %s",
            series_name,
            _format_episode_code(query.season, query.episode),
        )

        params = {
            "t": series_name,
            "type": "episode",
            "Season": str(query.season),
            "Episode": str(query.episode),
            "plot": "full",
        }

        payload = self._get_with_auth(params=params, timeout=options.timeout_seconds)
        if not payload:
            return None

        return self._parse_episode_response(payload, query, options)

    def _parse_episode_response(
        self,
        data: Mapping[str, Any],
        query: LookupQuery,
        options: LookupOptions,
    ) -> UnifiedMetadataResult:
        """Parse episode response into unified result."""
        show_name = _normalize_text(data.get("seriesID"))  # OMDb gives seriesID, not name
        # Fall back to query series name
        if not show_name:
            show_name = query.series_name or "Unknown"

        episode_name = _normalize_text(data.get("Title"))
        season = _normalize_int(data.get("Season")) or query.season or 0
        episode_num = _normalize_int(data.get("Episode")) or query.episode or 0

        # Format title
        ep_code = _format_episode_code(season, episode_num)
        if episode_name:
            title = f"{query.series_name or 'Unknown'} {ep_code} - {episode_name}"
        else:
            title = f"{query.series_name or 'Unknown'} {ep_code}"

        # Extract year from Released date
        released = _normalize_text(data.get("Released"))
        year = None
        if released:
            match = re.search(r"(\d{4})", released)
            if match:
                year = int(match.group(1))

        # Extract genres
        genres_str = _normalize_text(data.get("Genre"))
        genres: List[str] = []
        if genres_str:
            genres = [g.strip() for g in genres_str.split(",") if g.strip()]

        # Extract summary
        summary = _normalize_text(data.get("Plot"))

        # Extract poster
        cover_url = _normalize_text(data.get("Poster"))

        # Extract runtime
        runtime = _parse_runtime(data.get("Runtime"))

        # Extract rating
        rating = _normalize_float(data.get("imdbRating"))
        votes = _normalize_int(data.get("imdbVotes"))

        # Extract language
        language = _normalize_text(data.get("Language"))
        if language:
            language = language.split(",")[0].strip()

        # Extract IMDB IDs
        imdb_id = _normalize_text(data.get("imdbID"))
        series_imdb = _normalize_text(data.get("seriesID"))

        source_ids = SourceIds(imdb_id=series_imdb or imdb_id)

        series_info = SeriesInfo(
            series_id=series_imdb,
            series_title=query.series_name,
            season=season,
            episode=episode_num,
            episode_id=imdb_id,
            episode_title=episode_name,
        )

        return UnifiedMetadataResult(
            title=title,
            type=MediaType.TV_EPISODE,
            year=year,
            genres=genres[:10],
            summary=summary,
            cover_url=cover_url,
            series=series_info,
            source_ids=source_ids,
            confidence=ConfidenceLevel.MEDIUM,
            primary_source=MetadataSource.OMDB,
            contributing_sources=[MetadataSource.OMDB],
            queried_at=datetime.now(timezone.utc),
            author=query.series_name,
            language=language,
            runtime_minutes=runtime,
            rating=rating,
            votes=votes,
            raw_responses={"omdb": dict(data)} if options.include_raw_responses else {},
        )


__all__ = ["OMDbClient"]
