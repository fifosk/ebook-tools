"""Metadata lookup helpers for YouTube video IDs (yt-dlp backed)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError, ExtractorError

from modules import logging_manager as log_mgr

from .job_manager import PipelineJob, PipelineJobManager
from .youtube_subtitles import _COMMON_YT_OPTS, _extract_with_backoff
from .metadata.types import LookupOptions, LookupQuery, MediaType, UnifiedMetadataResult
from .metadata.pipeline import create_pipeline

logger = log_mgr.get_logger().getChild("services.youtube_video_metadata")


_YOUTUBE_ID_IN_BRACKETS = re.compile(r"\[(?P<id>[A-Za-z0-9_-]{11})\]")
_YOUTUBE_ID_ONLY = re.compile(r"^(?P<id>[A-Za-z0-9_-]{11})$")
_YOUTUBE_URL = re.compile(
    r"(?ix)"
    r"(?:youtu\.be/|youtube\.com/)"
    r"(?:watch\?v=|shorts/|embed/)?"
    r"(?P<id>[A-Za-z0-9_-]{11})"
)


@dataclass(frozen=True, slots=True)
class YoutubeVideoIdParse:
    video_id: str
    pattern: str


def _basename(value: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        return ""
    return normalized.split("/")[-1].split("\\")[-1]


def parse_youtube_video_id(source_name: str) -> Optional[YoutubeVideoIdParse]:
    """Extract a YouTube video ID from ``source_name`` when possible."""

    normalized = _basename(source_name)
    if not normalized:
        return None

    match = _YOUTUBE_ID_IN_BRACKETS.search(normalized)
    if match:
        return YoutubeVideoIdParse(video_id=match.group("id"), pattern="brackets")

    match = _YOUTUBE_URL.search(normalized)
    if match:
        return YoutubeVideoIdParse(video_id=match.group("id"), pattern="url")

    match = _YOUTUBE_ID_ONLY.match(normalized.strip())
    if match:
        return YoutubeVideoIdParse(video_id=match.group("id"), pattern="direct")

    stem = Path(normalized).stem
    match = _YOUTUBE_ID_IN_BRACKETS.search(stem)
    if match:
        return YoutubeVideoIdParse(video_id=match.group("id"), pattern="brackets")
    return None


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
    return None


def _truncate_text(value: Optional[str], *, max_chars: int) -> Optional[str]:
    if not value:
        return None
    trimmed = value.strip()
    if not trimmed:
        return None
    if len(trimmed) <= max_chars:
        return trimmed
    return trimmed[: max_chars - 1].rstrip() + "…"


def _extract_existing_media_metadata(job: PipelineJob) -> Optional[Mapping[str, Any]]:
    request_payload = job.request_payload
    if isinstance(request_payload, Mapping):
        existing = request_payload.get("media_metadata")
        if isinstance(existing, Mapping):
            return existing
    result_payload = job.result_payload
    if isinstance(result_payload, Mapping):
        dub = result_payload.get("youtube_dub")
        if isinstance(dub, Mapping):
            existing = dub.get("media_metadata")
            if isinstance(existing, Mapping):
                return existing
    return None


def _resolve_source_name(job: PipelineJob) -> Optional[str]:
    request_payload = job.request_payload
    if isinstance(request_payload, Mapping):
        for key in ("original_name", "source_file", "source_path", "submitted_source", "subtitle_path", "video_path"):
            candidate = request_payload.get(key)
            if isinstance(candidate, str) and candidate.strip():
                return _basename(candidate.strip())
    result_payload = job.result_payload
    if isinstance(result_payload, Mapping):
        dub = result_payload.get("youtube_dub")
        if isinstance(dub, Mapping):
            candidate = dub.get("video_path") or dub.get("input_file")
            if isinstance(candidate, str) and candidate.strip():
                return _basename(candidate.strip())
    return None


def _prune_yt_dlp_payload(payload: Mapping[str, Any]) -> Dict[str, Any]:
    """Drop oversized keys from yt-dlp payload before persisting to jobs."""

    blocked = {
        "formats",
        "requested_formats",
        "requested_subtitles",
        "automatic_captions",
        "subtitles",
        "heatmap",
        "thumbnails",
        "chapters",
        "entries",
    }
    pruned: Dict[str, Any] = {}
    for key, value in payload.items():
        if key in blocked:
            continue
        pruned[key] = value
    return pruned


class YoutubeVideoMetadataService:
    """Lazy metadata enrichment for YouTube videos (no API key; yt-dlp scraping)."""

    def __init__(self, *, job_manager: PipelineJobManager) -> None:
        self._job_manager = job_manager

    def get_youtube_metadata(
        self,
        job_id: str,
        *,
        user_id: Optional[str] = None,
        user_role: Optional[str] = None,
    ) -> Dict[str, Any]:
        job = self._job_manager.get(job_id, user_id=user_id, user_role=user_role)
        if job.job_type != "youtube_dub":
            raise KeyError("Job not found")

        source_name = _resolve_source_name(job)
        parsed = parse_youtube_video_id(source_name or "") if source_name else None
        media_metadata = _extract_existing_media_metadata(job)
        existing = None
        if isinstance(media_metadata, Mapping):
            youtube_section = media_metadata.get("youtube")
            if isinstance(youtube_section, Mapping):
                existing = youtube_section
        return {
            "job_id": job.job_id,
            "source_name": source_name,
            "parsed": {
                "video_id": parsed.video_id,
                "pattern": parsed.pattern,
            }
            if parsed
            else None,
            "youtube_metadata": dict(existing) if existing is not None else None,
        }

    def lookup_youtube_metadata_for_source(self, source_name: str, *, force: bool = False) -> Dict[str, Any]:
        """Lookup YouTube metadata for a source name without persisting anything.

        Uses the unified metadata pipeline with caching support.
        """
        normalized_source = _basename(source_name)
        parsed = parse_youtube_video_id(normalized_source) if normalized_source else None

        if parsed is None:
            return {
                "source_name": normalized_source or None,
                "parsed": None,
                "youtube_metadata": {
                    "kind": "youtube_video",
                    "provider": "unified_pipeline",
                    "queried_at": datetime.now(timezone.utc).isoformat(),
                    "source_name": normalized_source,
                    "error": "Unable to locate a YouTube video id (expected `[VIDEO_ID]` in the filename).",
                },
            }

        # Build lookup query for unified pipeline
        lookup_query = LookupQuery(
            media_type=MediaType.YOUTUBE_VIDEO,
            youtube_video_id=parsed.video_id,
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
            # Fall back to legacy direct lookup
            youtube_metadata = self._fetch_youtube_metadata(parsed, source_name=normalized_source)
            return {
                "source_name": normalized_source or None,
                "parsed": {
                    "video_id": parsed.video_id,
                    "pattern": parsed.pattern,
                },
                "youtube_metadata": dict(youtube_metadata) if isinstance(youtube_metadata, Mapping) else None,
            }

        # Convert unified result to legacy format
        youtube_metadata = self._convert_unified_result_to_payload(result, parsed, normalized_source)
        return {
            "source_name": normalized_source or None,
            "parsed": {
                "video_id": parsed.video_id,
                "pattern": parsed.pattern,
            },
            "youtube_metadata": youtube_metadata,
        }

    def _convert_unified_result_to_payload(
        self,
        result: UnifiedMetadataResult,
        parsed: YoutubeVideoIdParse,
        source_name: Optional[str],
    ) -> Dict[str, Any]:
        """Convert unified pipeline result to legacy YouTube metadata format."""
        sources = [s.value for s in result.contributing_sources] if result.contributing_sources else []
        primary = result.primary_source.value if result.primary_source else "unified_pipeline"

        return {
            "kind": "youtube_video",
            "provider": primary,
            "contributing_sources": sources,
            "queried_at": result.queried_at.isoformat() if result.queried_at else datetime.now(timezone.utc).isoformat(),
            "source_name": source_name,
            "video_id": parsed.video_id,
            "title": result.title,
            "webpage_url": f"https://www.youtube.com/watch?v={parsed.video_id}",
            "thumbnail": result.cover_url,
            "channel": result.channel_name,
            "channel_id": result.source_ids.youtube_channel_id,
            "duration_seconds": result.runtime_minutes * 60 if result.runtime_minutes else None,
            "upload_date": result.upload_date,
            "view_count": result.view_count,
            "like_count": result.like_count,
            "categories": result.genres,
            "summary": result.summary,
            "confidence": result.confidence.value if result.confidence else None,
            "error": result.error,
        }

    def lookup_youtube_metadata(
        self,
        job_id: str,
        *,
        force: bool = False,
        user_id: Optional[str] = None,
        user_role: Optional[str] = None,
    ) -> Dict[str, Any]:
        job = self._job_manager.get(job_id, user_id=user_id, user_role=user_role)
        if job.job_type != "youtube_dub":
            raise KeyError("Job not found")

        existing = _extract_existing_media_metadata(job)
        if not force and isinstance(existing, Mapping):
            youtube_section = existing.get("youtube")
            if isinstance(youtube_section, Mapping) and youtube_section.get("title"):
                return self.get_youtube_metadata(job_id, user_id=user_id, user_role=user_role)

        source_name = _resolve_source_name(job)
        parsed = parse_youtube_video_id(source_name or "") if source_name else None
        payload = self._fetch_youtube_metadata(parsed, source_name=source_name, job_id=job_id)
        self._persist_youtube_metadata(job_id, payload, user_id=user_id, user_role=user_role)
        return self.get_youtube_metadata(job_id, user_id=user_id, user_role=user_role)

    def _fetch_youtube_metadata(
        self,
        parsed: Optional[YoutubeVideoIdParse],
        *,
        source_name: Optional[str],
        job_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        timestamp = datetime.now(timezone.utc).isoformat()
        normalized_source = _basename(source_name or "") if source_name else None

        if parsed is None:
            return {
                "kind": "youtube_video",
                "provider": "yt_dlp",
                "queried_at": timestamp,
                "source_name": normalized_source,
                "error": "Unable to locate a YouTube video id (expected `[VIDEO_ID]` in the filename).",
            }

        url = f"https://www.youtube.com/watch?v={parsed.video_id}"
        if job_id:
            logger.info("Looking up YouTube metadata for job %s (%s)", job_id, parsed.video_id)
        else:
            logger.info("Looking up YouTube metadata (%s)", parsed.video_id)

        options = dict(_COMMON_YT_OPTS)
        options.update({"skip_download": True, "extract_flat": False})
        info: Dict[str, Any]
        with YoutubeDL(options) as ydl:
            try:
                extracted = _extract_with_backoff(ydl, url, download=False)
            except (DownloadError, ExtractorError) as exc:
                return {
                    "kind": "youtube_video",
                    "provider": "yt_dlp",
                    "queried_at": timestamp,
                    "source_name": normalized_source,
                    "video_id": parsed.video_id,
                    "error": f"yt-dlp extraction failed: {exc}",
                }

        info = extracted if isinstance(extracted, dict) else {}
        description = _normalize_text(info.get("description"))
        summary = _truncate_text(description, max_chars=520)
        title = _normalize_text(info.get("title")) or _normalize_text(info.get("fulltitle"))

        thumbnail = _normalize_text(info.get("thumbnail"))
        if thumbnail is None:
            thumbs = info.get("thumbnails")
            if isinstance(thumbs, list):
                for entry in reversed(thumbs):
                    if not isinstance(entry, Mapping):
                        continue
                    candidate = _normalize_text(entry.get("url"))
                    if candidate:
                        thumbnail = candidate
                        break

        tags = info.get("tags")
        if isinstance(tags, list):
            tags = [entry.strip() for entry in tags if isinstance(entry, str) and entry.strip()]
        else:
            tags = None

        categories = info.get("categories")
        if isinstance(categories, list):
            categories = [entry.strip() for entry in categories if isinstance(entry, str) and entry.strip()]
        else:
            categories = None

        raw_payload = _prune_yt_dlp_payload(info)

        return {
            "kind": "youtube_video",
            "provider": "yt_dlp",
            "queried_at": timestamp,
            "source_name": normalized_source,
            "video_id": parsed.video_id,
            "title": title,
            "webpage_url": _normalize_text(info.get("webpage_url")) or url,
            "thumbnail": thumbnail,
            "channel": _normalize_text(info.get("channel")),
            "channel_id": _normalize_text(info.get("channel_id")),
            "channel_url": _normalize_text(info.get("channel_url")),
            "uploader": _normalize_text(info.get("uploader")),
            "uploader_id": _normalize_text(info.get("uploader_id")),
            "uploader_url": _normalize_text(info.get("uploader_url")),
            "duration_seconds": _normalize_int(info.get("duration")),
            "upload_date": _normalize_text(info.get("upload_date")),
            "timestamp": _normalize_int(info.get("timestamp")),
            "view_count": _normalize_int(info.get("view_count")),
            "like_count": _normalize_int(info.get("like_count")),
            "comment_count": _normalize_int(info.get("comment_count")),
            "categories": categories,
            "tags": tags,
            "summary": summary,
            "description": _truncate_text(description, max_chars=20_000),
            "raw_payload": raw_payload,
        }

    def _persist_youtube_metadata(
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
            merged_media: Dict[str, Any] = dict(existing_media) if isinstance(existing_media, Mapping) else {}
            merged_media["youtube"] = dict(payload)
            if not merged_media.get("job_label"):
                title = payload.get("title")
                if isinstance(title, str) and title.strip():
                    merged_media["job_label"] = title.strip()
            request_payload["media_metadata"] = merged_media
            job.request_payload = request_payload

            if isinstance(job.result_payload, Mapping):
                result_payload = dict(job.result_payload)
                dub_section = result_payload.get("youtube_dub")
                if isinstance(dub_section, Mapping):
                    dub_payload = dict(dub_section)
                    existing_dub_media = dub_payload.get("media_metadata")
                    merged_dub_media: Dict[str, Any] = (
                        dict(existing_dub_media) if isinstance(existing_dub_media, Mapping) else {}
                    )
                    merged_dub_media["youtube"] = dict(payload)
                    if not merged_dub_media.get("job_label") and merged_media.get("job_label"):
                        merged_dub_media["job_label"] = merged_media.get("job_label")
                    dub_payload["media_metadata"] = merged_dub_media
                    result_payload["youtube_dub"] = dub_payload
                job.result_payload = result_payload

        self._job_manager.mutate_job(job_id, _mutate, user_id=user_id, user_role=user_role)

    def clear_metadata_cache_for_query(self, source_name: str) -> Dict[str, Any]:
        """Clear cached YouTube metadata for a source name.

        This invalidates any cached pipeline results for lookups matching
        the given source name, allowing a fresh lookup to be performed.

        Args:
            source_name: The source filename/URL/video ID to clear cache for.

        Returns:
            Dictionary with cleared cache entry count and query info.
        """
        normalized_source = _basename(source_name)
        parsed = parse_youtube_video_id(normalized_source) if normalized_source else None

        if parsed is None:
            return {
                "cleared": 0,
                "query": {
                    "source_name": normalized_source,
                    "video_id": None,
                },
            }

        # Build the lookup query to find matching cache entries
        lookup_query = LookupQuery(
            media_type=MediaType.YOUTUBE_VIDEO,
            youtube_video_id=parsed.video_id,
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
                "video_id": parsed.video_id,
            },
        }

