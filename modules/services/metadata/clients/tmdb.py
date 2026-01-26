"""TMDB (The Movie Database) API client for movie and TV metadata."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional

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

logger = log_mgr.get_logger().getChild("services.metadata.clients.tmdb")

_TMDB_BASE_URL = "https://api.themoviedb.org/3"
_TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/original"


def _normalize_text(value: Any) -> Optional[str]:
    """Normalize a string value."""
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def _normalize_int(value: Any) -> Optional[int]:
    """Normalize an integer value."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return None


def _normalize_float(value: Any) -> Optional[float]:
    """Normalize a float value."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _format_episode_code(season: int, episode: int) -> str:
    """Format season/episode as SxxEyy code."""
    return f"S{season:02d}E{episode:02d}"


class TMDBClient(BaseMetadataClient):
    """TMDB API client for movie and TV metadata.

    Requires a TMDB API key (v3 auth). Get one at:
    https://www.themoviedb.org/settings/api
    """

    name = MetadataSource.TMDB
    supported_types = (MediaType.MOVIE, MediaType.TV_SERIES, MediaType.TV_EPISODE)
    requires_api_key = True

    def __init__(
        self,
        *,
        session: Optional[requests.Session] = None,
        api_key: Optional[str] = None,
        timeout_seconds: float = 10.0,
        base_url: str = _TMDB_BASE_URL,
    ) -> None:
        super().__init__(session=session, api_key=api_key, timeout_seconds=timeout_seconds)
        self._base_url = base_url.rstrip("/")

    def _get_with_auth(
        self,
        endpoint: str,
        *,
        params: Optional[dict] = None,
        timeout: Optional[float] = None,
    ) -> Optional[dict]:
        """Make authenticated GET request to TMDB API."""
        if not self._api_key:
            return None

        url = f"{self._base_url}{endpoint}"
        query_params = {"api_key": self._api_key}
        if params:
            query_params.update(params)

        return self._get(url, params=query_params, timeout=timeout)

    def lookup(
        self,
        query: LookupQuery,
        options: LookupOptions,
    ) -> Optional[UnifiedMetadataResult]:
        """Look up movie or TV metadata from TMDB."""
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
        title = query.movie_title or query.title
        if not title:
            return None

        # If we have a TMDB ID, use direct lookup
        if query.tmdb_id:
            return self._get_movie_details(query.tmdb_id, query, options)

        logger.info("Searching TMDB for movie: %s (year=%s)", title, query.year)

        params: Dict[str, Any] = {"query": title}
        if query.year:
            params["year"] = query.year

        payload = self._get_with_auth("/search/movie", params=params, timeout=options.timeout_seconds)
        if not payload:
            return None

        results = payload.get("results", [])
        if not isinstance(results, list) or not results:
            return None

        # Take the first result
        movie = results[0]
        movie_id = _normalize_int(movie.get("id"))
        if movie_id is None:
            return None

        return self._get_movie_details(movie_id, query, options)

    def _get_movie_details(
        self,
        movie_id: int,
        query: LookupQuery,
        options: LookupOptions,
    ) -> Optional[UnifiedMetadataResult]:
        """Get detailed movie information."""
        payload = self._get_with_auth(
            f"/movie/{movie_id}",
            params={"append_to_response": "external_ids"},
            timeout=options.timeout_seconds,
        )
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
        title = _normalize_text(data.get("title")) or query.title or "Unknown"

        # Extract year from release_date
        release_date = _normalize_text(data.get("release_date"))
        year = None
        if release_date:
            match = re.match(r"(\d{4})", release_date)
            if match:
                year = int(match.group(1))

        # Extract genres
        genres_data = data.get("genres", [])
        genres: List[str] = []
        if isinstance(genres_data, list):
            for g in genres_data:
                if isinstance(g, Mapping):
                    name = _normalize_text(g.get("name"))
                    if name:
                        genres.append(name)

        # Extract summary
        summary = _normalize_text(data.get("overview"))

        # Extract poster
        poster_path = _normalize_text(data.get("poster_path"))
        cover_url = f"{_TMDB_IMAGE_BASE}{poster_path}" if poster_path else None

        # Extract runtime
        runtime = _normalize_int(data.get("runtime"))

        # Extract rating
        rating = _normalize_float(data.get("vote_average"))
        votes = _normalize_int(data.get("vote_count"))

        # Extract language
        language = _normalize_text(data.get("original_language"))

        # Extract external IDs
        external_ids = data.get("external_ids", {})
        imdb_id = _normalize_text(external_ids.get("imdb_id")) if isinstance(external_ids, Mapping) else None

        movie_id = _normalize_int(data.get("id"))
        source_ids = SourceIds(
            tmdb_id=movie_id,
            imdb_id=imdb_id,
        )

        return UnifiedMetadataResult(
            title=title,
            type=MediaType.MOVIE,
            year=year,
            genres=genres[:10],
            summary=summary,
            cover_url=cover_url,
            source_ids=source_ids,
            confidence=ConfidenceLevel.HIGH if query.tmdb_id else ConfidenceLevel.MEDIUM,
            primary_source=MetadataSource.TMDB,
            contributing_sources=[MetadataSource.TMDB],
            queried_at=datetime.now(timezone.utc),
            language=language,
            runtime_minutes=runtime,
            rating=rating,
            votes=votes,
            raw_responses={"tmdb_movie": dict(data)} if options.include_raw_responses else {},
        )

    def _lookup_tv_series(
        self,
        query: LookupQuery,
        options: LookupOptions,
    ) -> Optional[UnifiedMetadataResult]:
        """Look up TV series by name."""
        series_name = query.series_name or query.title
        if not series_name:
            return None

        # If we have a TMDB ID, use direct lookup
        if query.tmdb_id:
            return self._get_tv_details(query.tmdb_id, query, options)

        logger.info("Searching TMDB for TV series: %s", series_name)

        payload = self._get_with_auth(
            "/search/tv",
            params={"query": series_name},
            timeout=options.timeout_seconds,
        )
        if not payload:
            return None

        results = payload.get("results", [])
        if not isinstance(results, list) or not results:
            return None

        tv = results[0]
        tv_id = _normalize_int(tv.get("id"))
        if tv_id is None:
            return None

        return self._get_tv_details(tv_id, query, options)

    def _get_tv_details(
        self,
        tv_id: int,
        query: LookupQuery,
        options: LookupOptions,
    ) -> Optional[UnifiedMetadataResult]:
        """Get detailed TV series information."""
        payload = self._get_with_auth(
            f"/tv/{tv_id}",
            params={"append_to_response": "external_ids"},
            timeout=options.timeout_seconds,
        )
        if not payload:
            return None

        return self._parse_tv_response(payload, query, options)

    def _parse_tv_response(
        self,
        data: Mapping[str, Any],
        query: LookupQuery,
        options: LookupOptions,
    ) -> UnifiedMetadataResult:
        """Parse TV series response into unified result."""
        title = _normalize_text(data.get("name")) or query.series_name or "Unknown"

        # Extract year from first_air_date
        first_air_date = _normalize_text(data.get("first_air_date"))
        year = None
        if first_air_date:
            match = re.match(r"(\d{4})", first_air_date)
            if match:
                year = int(match.group(1))

        # Extract genres
        genres_data = data.get("genres", [])
        genres: List[str] = []
        if isinstance(genres_data, list):
            for g in genres_data:
                if isinstance(g, Mapping):
                    name = _normalize_text(g.get("name"))
                    if name:
                        genres.append(name)

        # Extract summary
        summary = _normalize_text(data.get("overview"))

        # Extract poster
        poster_path = _normalize_text(data.get("poster_path"))
        cover_url = f"{_TMDB_IMAGE_BASE}{poster_path}" if poster_path else None

        # Extract rating
        rating = _normalize_float(data.get("vote_average"))
        votes = _normalize_int(data.get("vote_count"))

        # Extract language
        language = _normalize_text(data.get("original_language"))

        # Extract episode runtime
        runtimes = data.get("episode_run_time", [])
        runtime = runtimes[0] if isinstance(runtimes, list) and runtimes else None

        # Extract external IDs
        external_ids = data.get("external_ids", {})
        imdb_id = _normalize_text(external_ids.get("imdb_id")) if isinstance(external_ids, Mapping) else None

        tv_id = _normalize_int(data.get("id"))
        source_ids = SourceIds(
            tmdb_id=tv_id,
            imdb_id=imdb_id,
        )

        return UnifiedMetadataResult(
            title=title,
            type=MediaType.TV_SERIES,
            year=year,
            genres=genres[:10],
            summary=summary,
            cover_url=cover_url,
            source_ids=source_ids,
            confidence=ConfidenceLevel.HIGH if query.tmdb_id else ConfidenceLevel.MEDIUM,
            primary_source=MetadataSource.TMDB,
            contributing_sources=[MetadataSource.TMDB],
            queried_at=datetime.now(timezone.utc),
            language=language,
            runtime_minutes=runtime,
            rating=rating,
            votes=votes,
            raw_responses={"tmdb_tv": dict(data)} if options.include_raw_responses else {},
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
            "Looking up TMDB episode: %s %s",
            series_name,
            _format_episode_code(query.season, query.episode),
        )

        # First, find the TV series
        tv_id = query.tmdb_id
        if not tv_id:
            payload = self._get_with_auth(
                "/search/tv",
                params={"query": series_name},
                timeout=options.timeout_seconds,
            )
            if not payload:
                return None

            results = payload.get("results", [])
            if not isinstance(results, list) or not results:
                return None

            tv_id = _normalize_int(results[0].get("id"))
            if tv_id is None:
                return None

        # Get episode details
        episode_data = self._get_with_auth(
            f"/tv/{tv_id}/season/{query.season}/episode/{query.episode}",
            timeout=options.timeout_seconds,
        )
        if not episode_data:
            # Fall back to series info
            return self._get_tv_details(tv_id, query, options)

        # Get series details for additional info
        tv_data = self._get_with_auth(
            f"/tv/{tv_id}",
            params={"append_to_response": "external_ids"},
            timeout=options.timeout_seconds,
        )
        tv_data = tv_data or {}

        return self._parse_episode_response(tv_data, episode_data, query, options)

    def _parse_episode_response(
        self,
        tv_data: Mapping[str, Any],
        episode_data: Mapping[str, Any],
        query: LookupQuery,
        options: LookupOptions,
    ) -> UnifiedMetadataResult:
        """Parse episode response into unified result."""
        show_name = _normalize_text(tv_data.get("name")) or query.series_name or "Unknown"
        episode_name = _normalize_text(episode_data.get("name"))

        season = _normalize_int(episode_data.get("season_number")) or query.season or 0
        episode_num = _normalize_int(episode_data.get("episode_number")) or query.episode or 0

        # Format title
        ep_code = _format_episode_code(season, episode_num)
        if episode_name:
            title = f"{show_name} {ep_code} - {episode_name}"
        else:
            title = f"{show_name} {ep_code}"

        # Extract year from air_date
        air_date = _normalize_text(episode_data.get("air_date"))
        year = None
        if air_date:
            match = re.match(r"(\d{4})", air_date)
            if match:
                year = int(match.group(1))

        # Fall back to series first_air_date
        if not year:
            first_air = _normalize_text(tv_data.get("first_air_date"))
            if first_air:
                match = re.match(r"(\d{4})", first_air)
                if match:
                    year = int(match.group(1))

        # Extract genres from series
        genres_data = tv_data.get("genres", [])
        genres: List[str] = []
        if isinstance(genres_data, list):
            for g in genres_data:
                if isinstance(g, Mapping):
                    name = _normalize_text(g.get("name"))
                    if name:
                        genres.append(name)

        # Extract summary (prefer episode, fall back to series)
        summary = _normalize_text(episode_data.get("overview"))
        if not summary:
            summary = _normalize_text(tv_data.get("overview"))

        # Extract still image for episode
        still_path = _normalize_text(episode_data.get("still_path"))
        poster_path = _normalize_text(tv_data.get("poster_path"))
        cover_url = None
        if still_path:
            cover_url = f"{_TMDB_IMAGE_BASE}{still_path}"
        elif poster_path:
            cover_url = f"{_TMDB_IMAGE_BASE}{poster_path}"

        # Extract runtime
        runtime = _normalize_int(episode_data.get("runtime"))

        # Extract rating
        rating = _normalize_float(episode_data.get("vote_average"))
        votes = _normalize_int(episode_data.get("vote_count"))

        # Extract language
        language = _normalize_text(tv_data.get("original_language"))

        # Extract external IDs
        external_ids = tv_data.get("external_ids", {})
        imdb_id = _normalize_text(external_ids.get("imdb_id")) if isinstance(external_ids, Mapping) else None

        tv_id = _normalize_int(tv_data.get("id"))
        episode_id = _normalize_int(episode_data.get("id"))

        source_ids = SourceIds(
            tmdb_id=tv_id,
            imdb_id=imdb_id,
        )

        series_info = SeriesInfo(
            series_id=str(tv_id) if tv_id else None,
            series_title=show_name,
            season=season,
            episode=episode_num,
            episode_id=str(episode_id) if episode_id else None,
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
            confidence=ConfidenceLevel.HIGH if query.tmdb_id else ConfidenceLevel.MEDIUM,
            primary_source=MetadataSource.TMDB,
            contributing_sources=[MetadataSource.TMDB],
            queried_at=datetime.now(timezone.utc),
            author=show_name,
            language=language,
            runtime_minutes=runtime,
            rating=rating,
            votes=votes,
            raw_responses={
                "tmdb_tv": dict(tv_data),
                "tmdb_episode": dict(episode_data),
            }
            if options.include_raw_responses
            else {},
        )


__all__ = ["TMDBClient"]
