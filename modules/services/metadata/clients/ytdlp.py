"""yt-dlp client for YouTube video metadata."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from modules import logging_manager as log_mgr

from ..types import (
    ConfidenceLevel,
    LookupOptions,
    LookupQuery,
    MediaType,
    MetadataSource,
    SourceIds,
    UnifiedMetadataResult,
)
from .base import BaseMetadataClient

logger = log_mgr.get_logger().getChild("services.metadata.clients.ytdlp")

# Import yt-dlp conditionally to allow graceful degradation
try:
    from yt_dlp import YoutubeDL
    from yt_dlp.utils import DownloadError, ExtractorError

    _YTDLP_AVAILABLE = True
except ImportError:
    _YTDLP_AVAILABLE = False
    YoutubeDL = None
    DownloadError = Exception
    ExtractorError = Exception

# YouTube ID patterns
_YOUTUBE_ID_IN_BRACKETS = re.compile(r"\[(?P<id>[A-Za-z0-9_-]{11})\]")
_YOUTUBE_ID_ONLY = re.compile(r"^(?P<id>[A-Za-z0-9_-]{11})$")
_YOUTUBE_URL = re.compile(
    r"(?ix)"
    r"(?:youtu\.be/|youtube\.com/)"
    r"(?:watch\?v=|shorts/|embed/)?"
    r"(?P<id>[A-Za-z0-9_-]{11})"
)

# Common yt-dlp options
_COMMON_YT_OPTS = {
    "quiet": True,
    "no_warnings": True,
    "extract_flat": False,
    "skip_download": True,
}

_SUMMARY_MAX_CHARS = 520
_DESCRIPTION_MAX_CHARS = 20_000


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


def _truncate_text(value: Optional[str], *, max_chars: int) -> Optional[str]:
    """Truncate text to max characters."""
    if not value:
        return None
    trimmed = value.strip()
    if not trimmed:
        return None
    if len(trimmed) <= max_chars:
        return trimmed
    return trimmed[: max_chars - 1].rstrip() + "…"


def _basename(value: str) -> str:
    """Extract basename from path."""
    normalized = str(value or "").strip()
    if not normalized:
        return ""
    return normalized.split("/")[-1].split("\\")[-1]


def parse_youtube_video_id(source_name: str) -> Optional[tuple[str, str]]:
    """Extract YouTube video ID and pattern from source name.

    Returns tuple of (video_id, pattern) or None if not found.
    """
    normalized = _basename(source_name)
    if not normalized:
        return None

    # Try bracket format first: [VIDEO_ID]
    match = _YOUTUBE_ID_IN_BRACKETS.search(normalized)
    if match:
        return (match.group("id"), "brackets")

    # Try URL format
    match = _YOUTUBE_URL.search(normalized)
    if match:
        return (match.group("id"), "url")

    # Try direct ID match
    match = _YOUTUBE_ID_ONLY.match(normalized.strip())
    if match:
        return (match.group("id"), "direct")

    # Try stem without extension
    stem = Path(normalized).stem
    match = _YOUTUBE_ID_IN_BRACKETS.search(stem)
    if match:
        return (match.group("id"), "brackets")

    return None


def _prune_yt_dlp_payload(payload: Mapping[str, Any]) -> Dict[str, Any]:
    """Remove oversized keys from yt-dlp payload before storage."""
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


def _extract_with_backoff(ydl, url: str, download: bool = False, max_retries: int = 3):
    """Extract info with retry logic."""
    import time

    last_exc = None
    for attempt in range(max_retries):
        try:
            return ydl.extract_info(url, download=download)
        except (DownloadError, ExtractorError) as exc:
            last_exc = exc
            if attempt < max_retries - 1:
                time.sleep(2**attempt)
    raise last_exc


class YtDlpClient(BaseMetadataClient):
    """yt-dlp client for YouTube video metadata.

    Uses yt-dlp (no API key required) to extract metadata from
    YouTube videos.
    """

    name = MetadataSource.YTDLP
    supported_types = (MediaType.YOUTUBE_VIDEO,)
    requires_api_key = False

    def __init__(
        self,
        *,
        session=None,  # Not used, but kept for interface compatibility
        api_key: Optional[str] = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        # Don't call super().__init__ since we don't use requests
        self._api_key = api_key
        self._timeout = timeout_seconds
        self._owns_session = False

    @property
    def is_available(self) -> bool:
        """Return True if yt-dlp is installed."""
        return _YTDLP_AVAILABLE

    def lookup(
        self,
        query: LookupQuery,
        options: LookupOptions,
    ) -> Optional[UnifiedMetadataResult]:
        """Look up YouTube video metadata using yt-dlp."""
        if query.media_type != MediaType.YOUTUBE_VIDEO:
            return None

        if not _YTDLP_AVAILABLE:
            logger.warning("yt-dlp not available")
            return None

        # Get video ID from query
        video_id = query.youtube_video_id
        pattern = "direct"

        if not video_id and query.youtube_url:
            parsed = parse_youtube_video_id(query.youtube_url)
            if parsed:
                video_id, pattern = parsed

        if not video_id and query.source_filename:
            parsed = parse_youtube_video_id(query.source_filename)
            if parsed:
                video_id, pattern = parsed

        if not video_id:
            return UnifiedMetadataResult(
                title="Unknown",
                type=MediaType.YOUTUBE_VIDEO,
                confidence=ConfidenceLevel.LOW,
                primary_source=MetadataSource.YTDLP,
                queried_at=datetime.now(timezone.utc),
                error="Unable to locate a YouTube video ID",
            )

        return self._fetch_video_metadata(video_id, pattern, options)

    def _fetch_video_metadata(
        self,
        video_id: str,
        pattern: str,
        options: LookupOptions,
    ) -> UnifiedMetadataResult:
        """Fetch metadata for a specific video ID."""
        url = f"https://www.youtube.com/watch?v={video_id}"
        logger.info("Looking up YouTube metadata: %s", video_id)

        yt_opts = dict(_COMMON_YT_OPTS)
        yt_opts["socket_timeout"] = options.timeout_seconds

        try:
            with YoutubeDL(yt_opts) as ydl:
                info = _extract_with_backoff(ydl, url, download=False)
        except (DownloadError, ExtractorError) as exc:
            return UnifiedMetadataResult(
                title="Unknown",
                type=MediaType.YOUTUBE_VIDEO,
                confidence=ConfidenceLevel.LOW,
                primary_source=MetadataSource.YTDLP,
                queried_at=datetime.now(timezone.utc),
                source_ids=SourceIds(youtube_video_id=video_id),
                error=f"yt-dlp extraction failed: {exc}",
            )

        info = info if isinstance(info, dict) else {}
        return self._parse_response(info, video_id, options)

    def _parse_response(
        self,
        info: Dict[str, Any],
        video_id: str,
        options: LookupOptions,
    ) -> UnifiedMetadataResult:
        """Parse yt-dlp response into unified result."""
        title = _normalize_text(info.get("title")) or _normalize_text(info.get("fulltitle")) or "Unknown"

        # Extract description/summary
        description = _normalize_text(info.get("description"))
        summary = _truncate_text(description, max_chars=_SUMMARY_MAX_CHARS)

        # Extract upload date and year
        upload_date = _normalize_text(info.get("upload_date"))  # YYYYMMDD format
        year = None
        if upload_date and len(upload_date) >= 4:
            try:
                year = int(upload_date[:4])
            except ValueError:
                pass

        # Extract thumbnail
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

        # Extract categories as genres
        categories = info.get("categories")
        genres: list[str] = []
        if isinstance(categories, list):
            genres = [c.strip() for c in categories if isinstance(c, str) and c.strip()]

        # Extract tags
        tags = info.get("tags")
        if isinstance(tags, list):
            tags = [t.strip() for t in tags if isinstance(t, str) and t.strip()]
        else:
            tags = []

        # Extend genres with first few tags
        for tag in tags[:5]:
            if tag not in genres:
                genres.append(tag)

        # Extract channel info
        channel = _normalize_text(info.get("channel"))
        channel_id = _normalize_text(info.get("channel_id"))
        uploader = _normalize_text(info.get("uploader"))

        # Extract statistics
        view_count = _normalize_int(info.get("view_count"))
        like_count = _normalize_int(info.get("like_count"))
        duration = _normalize_int(info.get("duration"))

        source_ids = SourceIds(
            youtube_video_id=video_id,
            youtube_channel_id=channel_id,
        )

        raw_responses = {}
        if options.include_raw_responses:
            raw_responses["ytdlp"] = _prune_yt_dlp_payload(info)

        return UnifiedMetadataResult(
            title=title,
            type=MediaType.YOUTUBE_VIDEO,
            year=year,
            genres=genres[:10],
            summary=summary,
            cover_url=thumbnail,
            source_ids=source_ids,
            confidence=ConfidenceLevel.HIGH,  # Direct video ID lookup
            primary_source=MetadataSource.YTDLP,
            contributing_sources=[MetadataSource.YTDLP],
            queried_at=datetime.now(timezone.utc),
            author=channel or uploader,
            runtime_minutes=duration // 60 if duration else None,
            channel_name=channel or uploader,
            view_count=view_count,
            like_count=like_count,
            upload_date=upload_date,
            raw_responses=raw_responses,
        )

    def close(self) -> None:
        """Release resources (no-op for yt-dlp)."""
        pass


__all__ = ["YtDlpClient", "parse_youtube_video_id"]
