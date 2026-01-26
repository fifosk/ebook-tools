"""TVMaze API client for TV series and episode metadata."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, Mapping, Optional, Sequence

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

logger = log_mgr.get_logger().getChild("services.metadata.clients.tvmaze")

_TVMAZE_BASE_URL = "https://api.tvmaze.com"


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
    if isinstance(value, str):
        trimmed = value.strip()
        if not trimmed:
            return None
        try:
            return int(float(trimmed))
        except ValueError:
            return None
    return None


def _strip_html(value: str) -> str:
    """Strip HTML tags from a string."""
    return re.sub(r"<[^>]+>", "", value or "").strip()


def _format_episode_code(season: int, episode: int) -> str:
    """Format season/episode as SxxEyy code."""
    return f"S{season:02d}E{episode:02d}"


class TVMazeClient(BaseMetadataClient):
    """TVMaze API client for TV series and episode metadata.

    Uses the public TVMaze API (no authentication required) to
    search for TV shows and look up episode details.
    """

    name = MetadataSource.TVMAZE
    supported_types = (MediaType.TV_SERIES, MediaType.TV_EPISODE)
    requires_api_key = False

    def __init__(
        self,
        *,
        session: Optional[requests.Session] = None,
        api_key: Optional[str] = None,
        timeout_seconds: float = 10.0,
        base_url: str = _TVMAZE_BASE_URL,
    ) -> None:
        super().__init__(session=session, api_key=api_key, timeout_seconds=timeout_seconds)
        self._base_url = base_url.rstrip("/")

    def lookup(
        self,
        query: LookupQuery,
        options: LookupOptions,
    ) -> Optional[UnifiedMetadataResult]:
        """Look up TV metadata from TVMaze.

        Supports TV series lookup and episode lookup with season/episode.
        """
        if query.media_type == MediaType.TV_EPISODE:
            return self._lookup_episode(query, options)
        elif query.media_type == MediaType.TV_SERIES:
            return self._lookup_series(query, options)
        return None

    def _lookup_series(
        self,
        query: LookupQuery,
        options: LookupOptions,
    ) -> Optional[UnifiedMetadataResult]:
        """Look up TV series by name."""
        series_name = query.series_name or query.title
        if not series_name:
            return None

        logger.info("Searching TVMaze for series: %s", series_name)

        candidates = self._search_shows(series_name, timeout=options.timeout_seconds)
        if not candidates:
            return None

        # Take the first (best) match
        first = candidates[0]
        show = first.get("show") if isinstance(first, Mapping) else None
        if not isinstance(show, Mapping):
            return None

        return self._parse_show_response(show, query, options)

    def _lookup_episode(
        self,
        query: LookupQuery,
        options: LookupOptions,
    ) -> Optional[UnifiedMetadataResult]:
        """Look up TV episode by series name, season, and episode number."""
        series_name = query.series_name or query.title
        if not series_name or query.season is None or query.episode is None:
            return None

        logger.info(
            "Looking up TVMaze episode: %s %s",
            series_name,
            _format_episode_code(query.season, query.episode),
        )

        # First, search for the show
        candidates = self._search_shows(series_name, timeout=options.timeout_seconds)
        if not candidates:
            return None

        first = candidates[0]
        show = first.get("show") if isinstance(first, Mapping) else None
        if not isinstance(show, Mapping):
            return None

        show_id = _normalize_int(show.get("id"))
        if show_id is None:
            return None

        # Then get the specific episode
        episode_data = self._get_episode_by_number(
            show_id,
            season=query.season,
            episode=query.episode,
            timeout=options.timeout_seconds,
        )
        if not episode_data:
            # Return series info without episode
            return self._parse_show_response(show, query, options, error="Episode not found")

        return self._parse_episode_response(show, episode_data, query, options)

    def _search_shows(
        self,
        query: str,
        *,
        timeout: Optional[float] = None,
    ) -> Sequence[Mapping[str, Any]]:
        """Search for TV shows."""
        payload = self._get(
            f"{self._base_url}/search/shows",
            params={"q": query},
            timeout=timeout,
        )
        return payload if isinstance(payload, list) else []

    def _get_episode_by_number(
        self,
        show_id: int,
        *,
        season: int,
        episode: int,
        timeout: Optional[float] = None,
    ) -> Optional[Mapping[str, Any]]:
        """Get a specific episode by season and episode number."""
        try:
            response = self._session.get(
                f"{self._base_url}/shows/{int(show_id)}/episodebynumber",
                params={"season": int(season), "number": int(episode)},
                headers={"Accept": "application/json"},
                timeout=timeout or self._timeout,
            )
            if response.status_code == 404:
                return None
            response.raise_for_status()
            payload = response.json()
            return payload if isinstance(payload, Mapping) else None
        except Exception:
            return None

    def _parse_show_response(
        self,
        show: Mapping[str, Any],
        query: LookupQuery,
        options: LookupOptions,
        error: Optional[str] = None,
    ) -> UnifiedMetadataResult:
        """Parse show response into unified result."""
        name = _normalize_text(show.get("name")) or query.series_name or "Unknown"

        # Extract year from premiered date
        premiered = _normalize_text(show.get("premiered"))
        year = None
        if premiered:
            match = re.match(r"(\d{4})", premiered)
            if match:
                year = int(match.group(1))

        # Extract genres
        genres = show.get("genres", [])
        if not isinstance(genres, list):
            genres = []
        genres = [g for g in genres if isinstance(g, str) and g.strip()]

        # Extract cover image
        image = show.get("image")
        cover_url = None
        if isinstance(image, Mapping):
            cover_url = _normalize_text(image.get("original") or image.get("medium"))

        # Extract summary
        summary = _normalize_text(show.get("summary"))
        if summary:
            summary = _strip_html(summary)

        # Extract network/language
        network = show.get("network") or show.get("webChannel")
        language = _normalize_text(show.get("language"))

        # Extract external IDs
        externals = show.get("externals")
        imdb_id = None
        if isinstance(externals, Mapping):
            imdb = externals.get("imdb")
            if isinstance(imdb, str) and imdb.startswith("tt"):
                imdb_id = imdb

        show_id = _normalize_int(show.get("id"))
        source_ids = SourceIds(
            tvmaze_show_id=show_id,
            imdb_id=imdb_id,
        )

        result = UnifiedMetadataResult(
            title=name,
            type=MediaType.TV_SERIES,
            year=year,
            genres=genres[:10],
            summary=summary,
            cover_url=cover_url,
            source_ids=source_ids,
            confidence=ConfidenceLevel.MEDIUM,
            primary_source=MetadataSource.TVMAZE,
            contributing_sources=[MetadataSource.TVMAZE],
            queried_at=datetime.now(timezone.utc),
            language=language,
            raw_responses={"tvmaze_show": dict(show)} if options.include_raw_responses else {},
            error=error,
        )

        return result

    def _parse_episode_response(
        self,
        show: Mapping[str, Any],
        episode: Mapping[str, Any],
        query: LookupQuery,
        options: LookupOptions,
    ) -> UnifiedMetadataResult:
        """Parse episode response into unified result."""
        show_name = _normalize_text(show.get("name")) or query.series_name or "Unknown"
        episode_name = _normalize_text(episode.get("name"))

        season = _normalize_int(episode.get("season")) or query.season or 0
        episode_num = _normalize_int(episode.get("number")) or query.episode or 0

        # Format title as "Show SxxEyy - Episode Name"
        ep_code = _format_episode_code(season, episode_num)
        if episode_name:
            title = f"{show_name} {ep_code} - {episode_name}"
        else:
            title = f"{show_name} {ep_code}"

        # Extract year from airdate
        airdate = _normalize_text(episode.get("airdate"))
        year = None
        if airdate:
            match = re.match(r"(\d{4})", airdate)
            if match:
                year = int(match.group(1))

        # Fall back to show premiered year
        if not year:
            premiered = _normalize_text(show.get("premiered"))
            if premiered:
                match = re.match(r"(\d{4})", premiered)
                if match:
                    year = int(match.group(1))

        # Extract genres from show
        genres = show.get("genres", [])
        if not isinstance(genres, list):
            genres = []
        genres = [g for g in genres if isinstance(g, str) and g.strip()]

        # Extract cover image (prefer episode, fall back to show)
        ep_image = episode.get("image")
        show_image = show.get("image")
        cover_url = None
        if isinstance(ep_image, Mapping):
            cover_url = _normalize_text(ep_image.get("original") or ep_image.get("medium"))
        if not cover_url and isinstance(show_image, Mapping):
            cover_url = _normalize_text(show_image.get("original") or show_image.get("medium"))

        # Extract summary (prefer episode, fall back to show)
        ep_summary = _normalize_text(episode.get("summary"))
        show_summary = _normalize_text(show.get("summary"))
        summary = _strip_html(ep_summary) if ep_summary else (_strip_html(show_summary) if show_summary else None)

        # Extract runtime
        runtime = _normalize_int(episode.get("runtime"))

        # Extract language
        language = _normalize_text(show.get("language"))

        # Extract external IDs
        externals = show.get("externals")
        imdb_id = None
        if isinstance(externals, Mapping):
            imdb = externals.get("imdb")
            if isinstance(imdb, str) and imdb.startswith("tt"):
                imdb_id = imdb

        show_id = _normalize_int(show.get("id"))
        episode_id = _normalize_int(episode.get("id"))

        source_ids = SourceIds(
            tvmaze_show_id=show_id,
            tvmaze_episode_id=episode_id,
            imdb_id=imdb_id,
        )

        series_info = SeriesInfo(
            series_id=str(show_id) if show_id else None,
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
            confidence=ConfidenceLevel.MEDIUM,
            primary_source=MetadataSource.TVMAZE,
            contributing_sources=[MetadataSource.TVMAZE],
            queried_at=datetime.now(timezone.utc),
            author=show_name,  # Use show name as "author" for TV
            language=language,
            runtime_minutes=runtime,
            raw_responses={
                "tvmaze_show": dict(show),
                "tvmaze_episode": dict(episode),
            }
            if options.include_raw_responses
            else {},
        )

    # Legacy API methods for backwards compatibility

    def search_shows(self, query: str) -> Sequence[Mapping[str, Any]]:
        """Search for TV shows (legacy API)."""
        return self._search_shows(query)

    def episode_by_number(
        self,
        show_id: int,
        *,
        season: int,
        episode: int,
    ) -> Optional[Mapping[str, Any]]:
        """Get episode by number (legacy API)."""
        return self._get_episode_by_number(show_id, season=season, episode=episode)


__all__ = ["TVMazeClient"]
