"""Metadata lookup helpers for subtitle jobs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence

import requests

from modules import logging_manager as log_mgr

from .job_manager import PipelineJob, PipelineJobManager
from .metadata.types import LookupOptions, LookupQuery, MediaType, UnifiedMetadataResult
from .metadata.pipeline import create_pipeline

logger = log_mgr.get_logger().getChild("services.subtitle_metadata")


_SXXEYY_PATTERN = re.compile(
    r"(?ix)"
    r"(?P<prefix>^|[^a-z0-9])"
    r"s(?P<season>\d{1,2})"
    r"[\s._-]*"
    r"e(?P<episode>\d{1,3})"
    r"(?P<suffix>[^0-9]|$)"
)
_NXXN_PATTERN = re.compile(
    r"(?ix)"
    r"(?P<prefix>^|[^0-9])"
    r"(?P<season>\d{1,2})"
    r"x"
    r"(?P<episode>\d{1,3})"
    r"(?P<suffix>[^0-9]|$)"
)


@dataclass(frozen=True, slots=True)
class TvEpisodeQuery:
    """Parsed TV episode query extracted from a subtitle filename."""

    series: str
    season: int
    episode: int
    pattern: str
    source_name: str


def _basename(value: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        return ""
    return normalized.split("/")[-1].split("\\")[-1]


def _clean_series_title(value: str) -> str:
    candidate = value.strip()
    if not candidate:
        return ""
    candidate = re.sub(r"[\[\(].*?[\]\)]", " ", candidate)
    candidate = re.sub(r"[._-]+", " ", candidate)
    candidate = re.sub(r"\s+", " ", candidate)
    return candidate.strip()


def parse_tv_episode_query(source_name: str) -> Optional[TvEpisodeQuery]:
    """Parse ``source_name`` into a :class:`TvEpisodeQuery` when possible."""

    basename = _basename(source_name)
    if not basename:
        return None
    stem = Path(basename).stem
    match = _SXXEYY_PATTERN.search(stem)
    pattern = "SxxEyy"
    if match is None:
        match = _NXXN_PATTERN.search(stem)
        pattern = "NxxN"
    if match is None:
        return None

    prefix = stem[: match.start()].strip()
    series = _clean_series_title(prefix)
    if not series:
        return None

    try:
        season = int(match.group("season"))
        episode = int(match.group("episode"))
    except (TypeError, ValueError):
        return None
    if season <= 0 or episode <= 0:
        return None

    return TvEpisodeQuery(
        series=series,
        season=season,
        episode=episode,
        pattern=pattern,
        source_name=basename,
    )


def _normalize_text(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def _normalize_int(value: Any) -> Optional[int]:
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


def _extract_mapping(value: Any) -> Optional[Mapping[str, Any]]:
    return value if isinstance(value, Mapping) else None


def _strip_html(value: str) -> str:
    return re.sub(r"<[^>]+>", "", value or "").strip()


def _format_episode_code(season: int, episode: int) -> str:
    return f"S{season:02d}E{episode:02d}"


def _build_job_label(*, show_name: str, season: int, episode: int, episode_name: Optional[str]) -> str:
    code = _format_episode_code(season, episode)
    if episode_name:
        return f"{show_name} {code} - {episode_name}"
    return f"{show_name} {code}"


class TvMazeClient:
    """Small wrapper around the public TVMaze API (no auth required)."""

    def __init__(
        self,
        *,
        session: Optional[requests.Session] = None,
        base_url: str = "https://api.tvmaze.com",
        timeout_seconds: float = 10.0,
    ) -> None:
        self._session = session or requests.Session()
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds

    def search_shows(self, query: str) -> Sequence[Mapping[str, Any]]:
        response = self._session.get(
            f"{self._base_url}/search/shows",
            params={"q": query},
            headers={"Accept": "application/json"},
            timeout=self._timeout,
        )
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, list) else []

    def episode_by_number(self, show_id: int, *, season: int, episode: int) -> Optional[Mapping[str, Any]]:
        response = self._session.get(
            f"{self._base_url}/shows/{int(show_id)}/episodebynumber",
            params={"season": int(season), "number": int(episode)},
            headers={"Accept": "application/json"},
            timeout=self._timeout,
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, Mapping) else None


def _normalize_show_payload(show: Mapping[str, Any]) -> Dict[str, Any]:
    network = _extract_mapping(show.get("network")) or _extract_mapping(show.get("webChannel"))
    image = _extract_mapping(show.get("image"))
    externals = _extract_mapping(show.get("externals"))
    rating = _extract_mapping(show.get("rating"))
    return {
        "id": _normalize_int(show.get("id")),
        "name": _normalize_text(show.get("name")),
        "type": _normalize_text(show.get("type")),
        "language": _normalize_text(show.get("language")),
        "genres": [genre for genre in show.get("genres", []) if isinstance(genre, str) and genre.strip()],
        "status": _normalize_text(show.get("status")),
        "premiered": _normalize_text(show.get("premiered")),
        "official_site": _normalize_text(show.get("officialSite")),
        "url": _normalize_text(show.get("url")),
        "network": {
            "id": _normalize_int(network.get("id")) if network else None,
            "name": _normalize_text(network.get("name")) if network else None,
        }
        if network
        else None,
        "image": {
            "medium": _normalize_text(image.get("medium")) if image else None,
            "original": _normalize_text(image.get("original")) if image else None,
        }
        if image
        else None,
        "externals": dict(externals) if externals else None,
        "rating": {
            "average": rating.get("average") if rating and rating.get("average") is not None else None,
        }
        if rating
        else None,
        "summary": _strip_html(show.get("summary")) if isinstance(show.get("summary"), str) else None,
    }


def _normalize_episode_payload(episode: Mapping[str, Any]) -> Dict[str, Any]:
    image = _extract_mapping(episode.get("image"))
    return {
        "id": _normalize_int(episode.get("id")),
        "name": _normalize_text(episode.get("name")),
        "season": _normalize_int(episode.get("season")),
        "number": _normalize_int(episode.get("number")),
        "airdate": _normalize_text(episode.get("airdate")),
        "airtime": _normalize_text(episode.get("airtime")),
        "runtime": _normalize_int(episode.get("runtime")),
        "url": _normalize_text(episode.get("url")),
        "image": {
            "medium": _normalize_text(image.get("medium")) if image else None,
            "original": _normalize_text(image.get("original")) if image else None,
        }
        if image
        else None,
        "summary": _strip_html(episode.get("summary")) if isinstance(episode.get("summary"), str) else None,
    }


def _extract_existing_media_metadata(job: PipelineJob) -> Optional[Mapping[str, Any]]:
    request_payload = job.request_payload
    if isinstance(request_payload, Mapping):
        existing = request_payload.get("media_metadata")
        if isinstance(existing, Mapping):
            return existing
    result_payload = job.result_payload
    if isinstance(result_payload, Mapping):
        subtitle = result_payload.get("subtitle")
        if isinstance(subtitle, Mapping):
            metadata = subtitle.get("metadata")
            if isinstance(metadata, Mapping):
                existing = metadata.get("media_metadata")
                if isinstance(existing, Mapping):
                    return existing
    return None


def _resolve_source_name(job: PipelineJob) -> Optional[str]:
    request_payload = job.request_payload
    if isinstance(request_payload, Mapping):
        for key in (
            "original_name",
            "source_file",
            "source_path",
            "submitted_source",
            "subtitle_path",
            "video_path",
        ):
            candidate = request_payload.get(key)
            if isinstance(candidate, str) and candidate.strip():
                return _basename(candidate.strip())

    result_payload = job.result_payload
    if isinstance(result_payload, Mapping):
        subtitle = result_payload.get("subtitle")
        if isinstance(subtitle, Mapping):
            metadata = subtitle.get("metadata")
            if isinstance(metadata, Mapping):
                input_file = metadata.get("input_file")
                if isinstance(input_file, str) and input_file.strip():
                    return _basename(input_file.strip())
    return None


class SubtitleMetadataService:
    """Lazy metadata enrichment for subtitle jobs."""

    def __init__(
        self,
        *,
        job_manager: PipelineJobManager,
        tvmaze_client: Optional[TvMazeClient] = None,
    ) -> None:
        self._job_manager = job_manager
        self._tvmaze = tvmaze_client or TvMazeClient()

    def get_tv_metadata(
        self,
        job_id: str,
        *,
        user_id: Optional[str] = None,
        user_role: Optional[str] = None,
    ) -> Dict[str, Any]:
        job = self._job_manager.get(job_id, user_id=user_id, user_role=user_role)
        if job.job_type not in {"subtitle", "youtube_dub"}:
            raise KeyError("Job not found")

        source_name = _resolve_source_name(job)
        parsed = parse_tv_episode_query(source_name or "") if source_name else None
        existing = _extract_existing_media_metadata(job)
        return {
            "job_id": job.job_id,
            "source_name": source_name,
            "parsed": {
                "series": parsed.series,
                "season": parsed.season,
                "episode": parsed.episode,
                "pattern": parsed.pattern,
            }
            if parsed
            else None,
            "media_metadata": dict(existing) if existing is not None else None,
        }

    def lookup_tv_metadata_for_source(self, source_name: str, *, force: bool = False) -> Dict[str, Any]:
        """Lookup TV metadata for a subtitle filename without persisting anything.

        Uses the unified metadata pipeline with caching support.
        """
        normalized_source = _basename(source_name)
        parsed = parse_tv_episode_query(normalized_source) if normalized_source else None

        if parsed is None:
            # Can't parse episode info, return basic response
            job_label: Optional[str] = None
            if normalized_source:
                try:
                    job_label = Path(normalized_source).stem or normalized_source
                except Exception:
                    job_label = normalized_source
            return {
                "source_name": normalized_source or None,
                "parsed": None,
                "media_metadata": {
                    "kind": "tv_episode",
                    "provider": "unified_pipeline",
                    "queried_at": datetime.now(timezone.utc).isoformat(),
                    "source_name": normalized_source,
                    "job_label": job_label,
                    "error": "Unable to parse season/episode from subtitle filename.",
                },
            }

        # Build lookup query for unified pipeline
        lookup_query = LookupQuery(
            media_type=MediaType.TV_EPISODE,
            series_name=parsed.series,
            season=parsed.season,
            episode=parsed.episode,
            source_filename=normalized_source,
        )

        options = LookupOptions(
            skip_cache=force,
            force_refresh=force,
            include_raw_responses=True,
        )

        # Use unified pipeline with caching
        try:
            with create_pipeline(cache_enabled=True) as pipeline:
                result = pipeline.lookup(lookup_query, options)
        except Exception as exc:
            logger.warning("Pipeline lookup failed for %s: %s", normalized_source, exc)
            result = None

        if result is None:
            # Fall back to legacy TVMaze direct lookup
            media_metadata = self._build_tv_episode_metadata_payload(parsed, source_name=normalized_source)
            return {
                "source_name": normalized_source or None,
                "parsed": {
                    "series": parsed.series,
                    "season": parsed.season,
                    "episode": parsed.episode,
                    "pattern": parsed.pattern,
                },
                "media_metadata": dict(media_metadata) if isinstance(media_metadata, Mapping) else None,
            }

        # Convert unified result to legacy format
        media_metadata = self._convert_unified_result_to_payload(result, parsed, normalized_source)
        return {
            "source_name": normalized_source or None,
            "parsed": {
                "series": parsed.series,
                "season": parsed.season,
                "episode": parsed.episode,
                "pattern": parsed.pattern,
            },
            "media_metadata": media_metadata,
        }

    def _convert_unified_result_to_payload(
        self,
        result: UnifiedMetadataResult,
        parsed: TvEpisodeQuery,
        source_name: Optional[str],
    ) -> Dict[str, Any]:
        """Convert unified pipeline result to legacy media metadata format."""
        series_info = result.series
        show_name = result.author or (series_info.series_title if series_info else None) or parsed.series
        episode_name = series_info.episode_title if series_info else None
        season = (series_info.season if series_info else None) or parsed.season
        episode = (series_info.episode if series_info else None) or parsed.episode

        # Build legacy show structure
        show = {
            "id": result.source_ids.tvmaze_show_id,
            "name": show_name,
            "genres": result.genres,
            "language": result.language,
            "summary": result.summary,
            "image": {"original": result.cover_url, "medium": result.cover_url} if result.cover_url else None,
            "externals": {"imdb": result.source_ids.imdb_id} if result.source_ids.imdb_id else None,
            "tmdb_id": result.source_ids.tmdb_id,
        }

        # Build legacy episode structure
        episode_data = {
            "id": result.source_ids.tvmaze_episode_id,
            "name": episode_name,
            "season": season,
            "number": episode,
            "airdate": None,
            "runtime": result.runtime_minutes,
            "summary": result.summary if episode_name else None,
        }

        job_label = _build_job_label(
            show_name=show_name,
            season=season,
            episode=episode,
            episode_name=episode_name,
        )

        sources = [s.value for s in result.contributing_sources] if result.contributing_sources else []
        primary = result.primary_source.value if result.primary_source else "unified_pipeline"

        return {
            "kind": "tv_episode",
            "provider": primary,
            "contributing_sources": sources,
            "queried_at": result.queried_at.isoformat() if result.queried_at else datetime.now(timezone.utc).isoformat(),
            "source_name": source_name,
            "parsed": {
                "series": parsed.series,
                "season": parsed.season,
                "episode": parsed.episode,
                "pattern": parsed.pattern,
            },
            "job_label": job_label,
            "show": show,
            "episode": episode_data,
            "genres": result.genres,
            "confidence": result.confidence.value if result.confidence else None,
            "tvmaze": {
                "show_id": result.source_ids.tvmaze_show_id,
                "episode_id": result.source_ids.tvmaze_episode_id,
            } if result.source_ids.tvmaze_show_id else None,
            "tmdb_id": result.source_ids.tmdb_id,
            "imdb_id": result.source_ids.imdb_id,
            "error": result.error,
        }

    def lookup_tv_metadata(
        self,
        job_id: str,
        *,
        force: bool = False,
        user_id: Optional[str] = None,
        user_role: Optional[str] = None,
    ) -> Dict[str, Any]:
        job = self._job_manager.get(job_id, user_id=user_id, user_role=user_role)
        if job.job_type not in {"subtitle", "youtube_dub"}:
            raise KeyError("Job not found")

        existing = _extract_existing_media_metadata(job)
        if existing is not None and not force:
            return self.get_tv_metadata(job_id, user_id=user_id, user_role=user_role)

        source_name = _resolve_source_name(job)
        parsed = parse_tv_episode_query(source_name or "") if source_name else None
        payload = self._build_tv_episode_metadata_payload(parsed, source_name=source_name, job_id=job_id)
        self._persist_media_metadata(job_id, payload, user_id=user_id, user_role=user_role)
        return self.get_tv_metadata(job_id, user_id=user_id, user_role=user_role)

    def _build_tv_episode_metadata_payload(
        self,
        parsed: Optional[TvEpisodeQuery],
        *,
        source_name: Optional[str],
        job_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        timestamp = datetime.now(timezone.utc).isoformat()
        normalized_source = _basename(source_name or "") if source_name else None

        if parsed is None:
            job_label: Optional[str] = None
            if normalized_source:
                try:
                    job_label = Path(normalized_source).stem or normalized_source
                except Exception:
                    job_label = normalized_source
            return {
                "kind": "tv_episode",
                "provider": "tvmaze",
                "queried_at": timestamp,
                "source_name": normalized_source,
                "job_label": job_label,
                "error": "Unable to parse season/episode from subtitle filename.",
            }

        if job_id:
            logger.info(
                "Looking up TV metadata for subtitle job %s (%s %s)",
                job_id,
                parsed.series,
                _format_episode_code(parsed.season, parsed.episode),
            )
        else:
            logger.info(
                "Looking up TV metadata (%s %s)",
                parsed.series,
                _format_episode_code(parsed.season, parsed.episode),
            )

        def _error_payload(message: str, *, show: Mapping[str, Any] | None = None) -> Dict[str, Any]:
            normalized_show = _normalize_show_payload(show) if show is not None else {"name": parsed.series}
            normalized_episode: Dict[str, Any] = {
                "season": parsed.season,
                "number": parsed.episode,
            }
            job_label = _build_job_label(
                show_name=normalized_show.get("name") or parsed.series,
                season=parsed.season,
                episode=parsed.episode,
                episode_name=None,
            )
            payload: Dict[str, Any] = {
                "kind": "tv_episode",
                "provider": "tvmaze",
                "queried_at": timestamp,
                "source_name": parsed.source_name,
                "parsed": {
                    "series": parsed.series,
                    "season": parsed.season,
                    "episode": parsed.episode,
                    "pattern": parsed.pattern,
                },
                "job_label": job_label,
                "show": normalized_show,
                "episode": normalized_episode,
                "error": message,
            }
            return payload

        try:
            candidates = self._tvmaze.search_shows(parsed.series)
        except Exception as exc:
            return _error_payload(f"TVMaze show search failed: {exc}")

        show_match: Optional[Mapping[str, Any]] = None
        if candidates:
            first = candidates[0]
            show = first.get("show") if isinstance(first, Mapping) else None
            if isinstance(show, Mapping):
                show_match = show

        if show_match is None:
            return _error_payload("TVMaze returned no matching shows.")

        show_id = _normalize_int(show_match.get("id"))
        if show_id is None:
            return _error_payload("TVMaze show response missing id.")

        try:
            episode_payload = self._tvmaze.episode_by_number(
                int(show_id),
                season=parsed.season,
                episode=parsed.episode,
            )
        except Exception as exc:
            return _error_payload(f"TVMaze episode lookup failed: {exc}", show=show_match)

        if episode_payload is None:
            return _error_payload(
                "TVMaze did not find an episode for the parsed season/episode.",
                show=show_match,
            )

        normalized_show = _normalize_show_payload(show_match)
        normalized_episode = _normalize_episode_payload(episode_payload)
        job_label = _build_job_label(
            show_name=normalized_show.get("name") or parsed.series,
            season=parsed.season,
            episode=parsed.episode,
            episode_name=normalized_episode.get("name"),
        )

        return {
            "kind": "tv_episode",
            "provider": "tvmaze",
            "queried_at": timestamp,
            "source_name": parsed.source_name,
            "parsed": {
                "series": parsed.series,
                "season": parsed.season,
                "episode": parsed.episode,
                "pattern": parsed.pattern,
            },
            "job_label": job_label,
            "show": normalized_show,
            "episode": normalized_episode,
            "tvmaze": {
                "show_id": normalized_show.get("id"),
                "episode_id": normalized_episode.get("id"),
            },
        }

    def _persist_media_metadata(
        self,
        job_id: str,
        payload: Mapping[str, Any],
        *,
        user_id: Optional[str],
        user_role: Optional[str],
    ) -> None:
        def _mutate(job: PipelineJob) -> None:
            request_payload = dict(job.request_payload) if isinstance(job.request_payload, Mapping) else {}
            existing_media = request_payload.get("media_metadata")
            existing_youtube = None
            if isinstance(existing_media, Mapping):
                existing_youtube = existing_media.get("youtube")

            merged_payload = dict(payload)
            if existing_youtube is not None and "youtube" not in merged_payload:
                merged_payload["youtube"] = (
                    dict(existing_youtube) if isinstance(existing_youtube, Mapping) else existing_youtube
                )

            request_payload["media_metadata"] = merged_payload
            job.request_payload = request_payload

            if isinstance(job.result_payload, Mapping):
                result_payload = dict(job.result_payload)
                if job.job_type == "subtitle":
                    subtitle_section = result_payload.get("subtitle")
                    if not isinstance(subtitle_section, Mapping):
                        subtitle_section = {}
                    subtitle_section = dict(subtitle_section)
                    metadata = subtitle_section.get("metadata")
                    if not isinstance(metadata, Mapping):
                        metadata = {}
                    metadata = dict(metadata)
                    metadata["media_metadata"] = dict(merged_payload)
                    if isinstance(payload.get("job_label"), str) and payload.get("job_label"):
                        metadata["job_label"] = str(payload["job_label"])
                    subtitle_section["metadata"] = metadata
                    result_payload["subtitle"] = subtitle_section
                elif job.job_type == "youtube_dub":
                    dub_section = result_payload.get("youtube_dub")
                    if isinstance(dub_section, Mapping):
                        dub_payload = dict(dub_section)
                        existing_dub_media = dub_payload.get("media_metadata")
                        existing_dub_youtube = None
                        if isinstance(existing_dub_media, Mapping):
                            existing_dub_youtube = existing_dub_media.get("youtube")
                        merged_dub_media = dict(payload)
                        if existing_dub_youtube is not None and "youtube" not in merged_dub_media:
                            merged_dub_media["youtube"] = (
                                dict(existing_dub_youtube)
                                if isinstance(existing_dub_youtube, Mapping)
                                else existing_dub_youtube
                            )
                        dub_payload["media_metadata"] = merged_dub_media
                        result_payload["youtube_dub"] = dub_payload

                media_metadata = result_payload.get("media_metadata")
                if isinstance(media_metadata, Mapping):
                    merged_book = dict(media_metadata)
                    job_label = payload.get("job_label")
                    if isinstance(job_label, str) and job_label.strip():
                        merged_book["job_label"] = job_label.strip()
                    show = payload.get("show")
                    episode = payload.get("episode")
                    show_name = show.get("name") if isinstance(show, Mapping) else None
                    episode_name = episode.get("name") if isinstance(episode, Mapping) else None
                    season_number = episode.get("season") if isinstance(episode, Mapping) else None
                    episode_number = episode.get("number") if isinstance(episode, Mapping) else None
                    airdate = episode.get("airdate") if isinstance(episode, Mapping) else None

                    if isinstance(show_name, str) and show_name.strip():
                        merged_book["book_author"] = show_name.strip()
                        merged_book["series_title"] = show_name.strip()
                    if isinstance(season_number, int) and isinstance(episode_number, int) and season_number > 0 and episode_number > 0:
                        merged_book["season_number"] = season_number
                        merged_book["episode_number"] = episode_number
                        merged_book["episode_code"] = _format_episode_code(season_number, episode_number)
                    if isinstance(episode_name, str) and episode_name.strip():
                        merged_book["episode_title"] = episode_name.strip()
                    if isinstance(airdate, str) and airdate.strip():
                        merged_book["airdate"] = airdate.strip()

                    code = merged_book.get("episode_code")
                    if isinstance(code, str) and code.strip() and isinstance(episode_name, str) and episode_name.strip():
                        merged_book["book_title"] = f"{code.strip()} - {episode_name.strip()}"
                    elif isinstance(code, str) and code.strip():
                        merged_book["book_title"] = code.strip()

                    tvmaze = payload.get("tvmaze")
                    if isinstance(tvmaze, Mapping):
                        show_id = tvmaze.get("show_id")
                        episode_id = tvmaze.get("episode_id")
                        if isinstance(show_id, int):
                            merged_book["tvmaze_show_id"] = show_id
                        if isinstance(episode_id, int):
                            merged_book["tvmaze_episode_id"] = episode_id
                    result_payload["media_metadata"] = merged_book
                job.result_payload = result_payload

        self._job_manager.mutate_job(job_id, _mutate, user_id=user_id, user_role=user_role)

    def clear_metadata_cache_for_query(self, source_name: str) -> Dict[str, Any]:
        """Clear cached TV metadata for a source name.

        This invalidates any cached pipeline results for lookups matching
        the given source name, allowing a fresh lookup to be performed.

        Args:
            source_name: The source filename to clear cache for.

        Returns:
            Dictionary with cleared cache entry count and query info.
        """
        normalized_source = _basename(source_name)
        parsed = parse_tv_episode_query(normalized_source) if normalized_source else None

        if parsed is None:
            return {
                "cleared": 0,
                "query": {
                    "source_name": normalized_source,
                    "series": None,
                    "season": None,
                    "episode": None,
                },
            }

        # Build the lookup query to find matching cache entries
        lookup_query = LookupQuery(
            media_type=MediaType.TV_EPISODE,
            series_name=parsed.series,
            season=parsed.season,
            episode=parsed.episode,
            source_filename=normalized_source,
        )

        cleared_count = 0
        try:
            with create_pipeline(cache_enabled=True) as pipeline:
                if pipeline.invalidate_cache(lookup_query):
                    cleared_count += 1
        except Exception as exc:
            logger.warning("Failed to clear metadata cache for %s: %s", source_name, exc)

        return {
            "cleared": cleared_count,
            "query": {
                "source_name": normalized_source,
                "series": parsed.series,
                "season": parsed.season,
                "episode": parsed.episode,
            },
        }
