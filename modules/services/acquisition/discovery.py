"""Normalized source discovery for acquisition-backed Create flows."""

from __future__ import annotations

import base64
import json
import os
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

from modules.language_constants import LANGUAGE_CODES
from modules.services.source_discovery import walk_visible_source_files
from modules.services.youtube_dubbing import list_downloaded_videos

from .provider_registry import resolve_books_root, resolve_video_root


_LANGUAGE_NAME_TO_CODE = {name.casefold(): code for name, code in LANGUAGE_CODES.items()}
_YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
_YOUTUBE_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"
_GUTENDEX_BOOKS_URL = "https://gutendex.com/books"
_DEFAULT_DISCOVERY_LIMIT = 20
_MAX_DISCOVERY_LIMIT = 50
_DISCOVERY_PROVIDER_MEDIA_KINDS = {
    "gutenberg": {"book"},
    "local_epub": {"book"},
    "nas_video": {"video"},
    "youtube_search": {"video"},
}
_ISO8601_DURATION_PATTERN = re.compile(
    r"^P(?:(?P<days>\d+)D)?(?:T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?)?$"
)


@dataclass(frozen=True)
class AcquisitionSubtitleHint:
    """Subtitle companion available for a discovered video."""

    path: str
    filename: str
    language: str | None = None
    format: str | None = None


@dataclass(frozen=True)
class AcquisitionCandidate:
    """Provider-neutral candidate returned by discovery endpoints."""

    candidate_id: str
    provider: str
    media_kind: str
    title: str
    rights: str
    capabilities: tuple[str, ...]
    candidate_token: str
    subtitle: str | None = None
    contributors: tuple[str, ...] = ()
    language: str | None = None
    year: int | None = None
    published_at: str | None = None
    source_url: str | None = None
    thumbnail_url: str | None = None
    cover_url: str | None = None
    local_path: str | None = None
    size_bytes: int | None = None
    modified_at: datetime | None = None
    duration_seconds: int | None = None
    subtitles: tuple[AcquisitionSubtitleHint, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)
    requires_confirmation: bool = False
    policy_notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class AcquisitionDiscoveryResult:
    """Result from a discovery query."""

    candidates: tuple[AcquisitionCandidate, ...]
    policy_notes: tuple[str, ...] = ()
    providers_queried: tuple[str, ...] = ()


def discover_acquisition_candidates(
    *,
    media_kind: str,
    query: str,
    provider: str | None = None,
    language: str | None = None,
    limit: int = 20,
    config: Mapping[str, Any] | None = None,
    session: requests.Session | None = None,
) -> AcquisitionDiscoveryResult:
    """Search configured lawful source providers and normalize candidates."""

    config = config or {}
    normalized_kind = _normalize_media_kind(media_kind)
    normalized_query = _normalize_query(query)
    normalized_provider = _normalize_provider(provider)
    effective_limit = _normalize_limit(limit)
    providers = _providers_for(normalized_kind, normalized_provider, config)

    candidates: list[AcquisitionCandidate] = []
    queried: list[str] = []
    policy_notes = [
        "Discovery results are candidates only; downloader handoff requires a reviewed acquisition step.",
        "Do not use acquisition providers for works you are not authorized to download or process.",
    ]
    if effective_limit <= 0:
        return AcquisitionDiscoveryResult(
            candidates=(),
            policy_notes=tuple(policy_notes),
            providers_queried=(),
        )
    for provider_id in providers:
        if len(candidates) >= effective_limit:
            break
        remaining = effective_limit - len(candidates)
        if provider_id == "local_epub":
            queried.append(provider_id)
            candidates.extend(_discover_local_epubs(config, normalized_query, remaining))
        elif provider_id == "gutenberg":
            queried.append(provider_id)
            candidates.extend(
                _discover_gutenberg(
                    normalized_query,
                    remaining,
                    language=language,
                    session=session,
                )
            )
        elif provider_id == "nas_video":
            queried.append(provider_id)
            candidates.extend(_discover_nas_videos(config, normalized_query, remaining))
        elif provider_id == "youtube_search":
            queried.append(provider_id)
            candidates.extend(
                _discover_youtube_search(
                    config,
                    normalized_query,
                    remaining,
                    language=language,
                    session=session,
                )
            )

    return AcquisitionDiscoveryResult(
        candidates=tuple(candidates[:effective_limit]),
        policy_notes=tuple(policy_notes),
        providers_queried=tuple(queried),
    )


def _providers_for(
    media_kind: str,
    provider: str | None,
    config: Mapping[str, Any],
) -> tuple[str, ...]:
    if provider:
        media_kinds = _DISCOVERY_PROVIDER_MEDIA_KINDS.get(provider)
        if media_kinds is None:
            raise ValueError(f"provider {provider} does not support discovery")
        if media_kind not in media_kinds:
            raise ValueError(
                f"provider {provider} does not support {media_kind} discovery"
            )
        return (provider,)
    if media_kind == "book":
        return ("local_epub",)
    providers = ["nas_video"]
    if _youtube_api_key(config):
        providers.append("youtube_search")
    return tuple(providers)


def _discover_local_epubs(
    config: Mapping[str, Any],
    query: str,
    limit: int,
) -> list[AcquisitionCandidate]:
    root = resolve_books_root(config=config, context=None)
    matches: list[AcquisitionCandidate] = []
    for entry in walk_visible_source_files(root, suffixes={".epub"}):
        relative_path = _relative_path(entry.path, root)
        if query and query not in _search_blob(entry.path.name, relative_path):
            continue
        token = _candidate_token(
            {
                "provider": "local_epub",
                "media_kind": "book",
                "path": relative_path,
            }
        )
        matches.append(
            AcquisitionCandidate(
                candidate_id=f"local_epub:{relative_path}",
                provider="local_epub",
                media_kind="book",
                title=_title_from_filename(entry.path),
                rights="user_provided",
                capabilities=("import_local", "metadata"),
                candidate_token=token,
                local_path=relative_path,
                size_bytes=entry.stat.st_size,
                modified_at=datetime.fromtimestamp(entry.stat.st_mtime),
                requires_confirmation=False,
                policy_notes=(
                    "Backend-visible EPUB under the configured books root.",
                ),
                metadata={
                    "source_kind": "local_epub",
                    "source_path": relative_path,
                },
            )
        )
    ordered = sorted(
        matches,
        key=lambda candidate: (
            -candidate.modified_at.timestamp() if candidate.modified_at else 0,
            candidate.title.casefold(),
        ),
    )
    return ordered[:limit]


def _discover_gutenberg(
    query: str,
    limit: int,
    *,
    language: str | None,
    session: requests.Session | None,
) -> list[AcquisitionCandidate]:
    if not query:
        return []

    client = session or requests.Session()
    params: dict[str, str | int] = {
        "search": query,
        "page_size": max(1, min(limit, 32)),
    }
    normalized_language = _normalize_language_code(language)
    if normalized_language:
        params["languages"] = normalized_language
    response = client.get(_GUTENDEX_BOOKS_URL, params=params, timeout=10)
    response.raise_for_status()
    payload = response.json()
    results = payload.get("results", [])
    if not isinstance(results, Sequence):
        return []

    candidates: list[AcquisitionCandidate] = []
    for item in results:
        if not isinstance(item, Mapping):
            continue
        gutenberg_id = _int_value(item.get("id"))
        if gutenberg_id is None:
            continue
        formats = item.get("formats")
        if not isinstance(formats, Mapping):
            formats = {}
        epub_url = _gutenberg_epub_url(formats)
        source_url = _string_value(
            formats.get("text/html")
            or formats.get("text/html; charset=utf-8")
            or formats.get("text/html; charset=us-ascii")
        ) or f"https://www.gutenberg.org/ebooks/{gutenberg_id}"
        title = _string_value(item.get("title")) or f"Project Gutenberg {gutenberg_id}"
        contributors = _gutenberg_person_names(item.get("authors"))
        languages = _string_sequence(item.get("languages"))
        copyright_value = item.get("copyright")
        rights = "public_domain" if copyright_value is False else "unknown"
        token = _candidate_token(
            {
                "provider": "gutenberg",
                "media_kind": "book",
                "gutenberg_id": gutenberg_id,
                "epub_url": epub_url,
            }
        )
        candidates.append(
            AcquisitionCandidate(
                candidate_id=f"gutenberg:{gutenberg_id}",
                provider="gutenberg",
                media_kind="book",
                title=title,
                rights=rights,
                capabilities=("search", "metadata", "acquire"),
                candidate_token=token,
                contributors=contributors,
                language=languages[0] if languages else None,
                source_url=source_url,
                cover_url=_string_value(formats.get("image/jpeg")),
                requires_confirmation=True,
                policy_notes=(
                    "Project Gutenberg/Gutendex result; confirm the work is public-domain or otherwise authorized in your location before acquisition.",
                ),
                metadata={
                    "source_kind": "gutenberg",
                    "gutenberg_id": gutenberg_id,
                    "download_count": _int_value(item.get("download_count")),
                    "epub_url": epub_url,
                    "languages": list(languages),
                },
            )
        )
        if len(candidates) >= limit:
            break
    return candidates


def _discover_nas_videos(
    config: Mapping[str, Any],
    query: str,
    limit: int,
) -> list[AcquisitionCandidate]:
    root = resolve_video_root(config)
    try:
        videos = list_downloaded_videos(root)
    except FileNotFoundError:
        return []

    matches: list[AcquisitionCandidate] = []
    for video in videos:
        relative_path = _relative_path(video.path, root)
        if query and query not in _search_blob(video.path.name, relative_path):
            continue
        subtitles = tuple(
            AcquisitionSubtitleHint(
                path=subtitle.path.as_posix(),
                filename=subtitle.path.name,
                language=subtitle.language,
                format=subtitle.format,
            )
            for subtitle in video.subtitles
        )
        token = _candidate_token(
            {
                "provider": "nas_video",
                "media_kind": "video",
                "path": video.path.as_posix(),
            }
        )
        matches.append(
            AcquisitionCandidate(
                candidate_id=f"nas_video:{video.path.as_posix()}",
                provider="nas_video",
                media_kind="video",
                title=_title_from_filename(video.path),
                rights="user_provided",
                capabilities=("import_local", "extract_subtitles", "metadata"),
                candidate_token=token,
                local_path=video.path.as_posix(),
                size_bytes=video.size_bytes,
                modified_at=video.modified_at,
                subtitles=subtitles,
                requires_confirmation=False,
                policy_notes=(
                    "Backend-visible NAS video under the configured video root.",
                ),
                metadata={
                    "source_kind": getattr(video, "source", "nas_video") or "nas_video",
                    "source_path": video.path.as_posix(),
                },
            )
        )
        if len(matches) >= limit:
            break
    return matches


def _discover_youtube_search(
    config: Mapping[str, Any],
    query: str,
    limit: int,
    *,
    language: str | None,
    session: requests.Session | None,
) -> list[AcquisitionCandidate]:
    api_key = _youtube_api_key(config)
    if not api_key or not query:
        return []

    client = session or requests.Session()
    params: dict[str, str | int] = {
        "part": "snippet",
        "type": "video",
        "maxResults": max(1, min(limit, 25)),
        "q": query,
        "key": api_key,
        "safeSearch": "moderate",
    }
    if language:
        params["relevanceLanguage"] = language
    response = client.get(_YOUTUBE_SEARCH_URL, params=params, timeout=10)
    response.raise_for_status()
    payload = response.json()
    items = payload.get("items", [])
    if not isinstance(items, Sequence):
        return []

    search_items = [item for item in items if isinstance(item, Mapping)]
    video_ids = [_youtube_video_id(item) for item in search_items]
    details_by_id = _fetch_youtube_video_details(client, api_key, video_ids)
    candidates: list[AcquisitionCandidate] = []
    for item in search_items:
        video_id = _youtube_video_id(item)
        if not video_id:
            continue
        snippet = item.get("snippet")
        if not isinstance(snippet, Mapping):
            continue
        details = details_by_id.get(video_id, {})
        url = f"https://www.youtube.com/watch?v={video_id}"
        token = _candidate_token(
            {
                "provider": "youtube_search",
                "media_kind": "video",
                "video_id": video_id,
            }
        )
        candidates.append(
            AcquisitionCandidate(
                candidate_id=f"youtube_search:{video_id}",
                provider="youtube_search",
                media_kind="video",
                title=_string_value(snippet.get("title")) or video_id,
                rights="unknown",
                capabilities=("metadata", "extract_subtitles"),
                candidate_token=token,
                contributors=tuple(
                    value
                    for value in [_string_value(snippet.get("channelTitle"))]
                    if value
                ),
                published_at=_string_value(snippet.get("publishedAt")),
                source_url=url,
                thumbnail_url=_youtube_thumbnail(snippet),
                duration_seconds=_parse_iso8601_duration(
                    _string_value(details.get("duration"))
                ),
                requires_confirmation=True,
                policy_notes=(
                    "YouTube search uses metadata only; video/subtitle acquisition is a separate reviewed step.",
                ),
                metadata={
                    "source_kind": "youtube",
                    "youtube_video_id": video_id,
                    "youtube_url": url,
                    "channel": _string_value(snippet.get("channelTitle")),
                },
            )
        )
        if len(candidates) >= limit:
            break
    return candidates


def _fetch_youtube_video_details(
    client: requests.Session,
    api_key: str,
    video_ids: Sequence[str | None],
) -> dict[str, Mapping[str, Any]]:
    ids = [video_id for video_id in video_ids if video_id]
    if not ids:
        return {}
    response = client.get(
        _YOUTUBE_VIDEOS_URL,
        params={
            "part": "contentDetails,snippet",
            "id": ",".join(ids[:50]),
            "key": api_key,
        },
        timeout=10,
    )
    response.raise_for_status()
    payload = response.json()
    items = payload.get("items", [])
    details: dict[str, Mapping[str, Any]] = {}
    if not isinstance(items, Sequence):
        return details
    for item in items:
        if not isinstance(item, Mapping):
            continue
        video_id = _string_value(item.get("id"))
        content_details = item.get("contentDetails")
        if video_id and isinstance(content_details, Mapping):
            details[video_id] = {
                "duration": content_details.get("duration"),
            }
    return details


def _youtube_api_key(config: Mapping[str, Any]) -> str | None:
    for key in ("youtube_api_key", "youtube_data_api_key"):
        value = config.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    for key in ("YOUTUBE_API_KEY", "EBOOK_YOUTUBE_API_KEY"):
        value = os.environ.get(key, "").strip()
        if value:
            return value
    return None


def _normalize_media_kind(media_kind: str) -> str:
    value = (media_kind or "").strip().lower()
    if value not in {"book", "video"}:
        raise ValueError("media_kind must be book or video")
    return value


def _normalize_provider(provider: str | None) -> str | None:
    value = (provider or "").strip().lower()
    return value or None


def _normalize_query(query: str) -> str:
    return re.sub(r"\s+", " ", (query or "").strip().casefold())


def _normalize_limit(limit: int) -> int:
    try:
        value = int(limit)
    except (TypeError, ValueError):
        value = _DEFAULT_DISCOVERY_LIMIT
    return max(0, min(value, _MAX_DISCOVERY_LIMIT))


def _search_blob(*values: str) -> str:
    return " ".join(values).casefold()


def _relative_path(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _title_from_filename(path: Path) -> str:
    title = re.sub(r"[_\s]+", " ", path.stem).strip()
    return title or path.name


def _candidate_token(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(encoded).decode("ascii").rstrip("=")


def _youtube_video_id(item: Mapping[str, Any]) -> str | None:
    item_id = item.get("id")
    if isinstance(item_id, Mapping):
        return _string_value(item_id.get("videoId"))
    return None


def _youtube_thumbnail(snippet: Mapping[str, Any]) -> str | None:
    thumbnails = snippet.get("thumbnails")
    if not isinstance(thumbnails, Mapping):
        return None
    for key in ("high", "medium", "default"):
        entry = thumbnails.get(key)
        if isinstance(entry, Mapping):
            value = _string_value(entry.get("url"))
            if value:
                return value
    return None


def _gutenberg_epub_url(formats: Mapping[str, Any]) -> str | None:
    preferred = _string_value(formats.get("application/epub+zip"))
    if preferred:
        return preferred
    for key, value in formats.items():
        if "epub" not in str(key).casefold():
            continue
        url = _string_value(value)
        if url:
            return url
    for value in formats.values():
        url = _string_value(value)
        if url and ".epub" in url.casefold():
            return url
    return None


def _gutenberg_person_names(value: Any) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return ()
    names: list[str] = []
    for person in value:
        if not isinstance(person, Mapping):
            continue
        name = _string_value(person.get("name"))
        if name:
            names.append(name)
    return tuple(names)


def _parse_iso8601_duration(value: str | None) -> int | None:
    if not value:
        return None
    match = _ISO8601_DURATION_PATTERN.match(value)
    if not match:
        return None
    days = int(match.group("days") or 0)
    hours = int(match.group("hours") or 0)
    minutes = int(match.group("minutes") or 0)
    seconds = int(match.group("seconds") or 0)
    return days * 86400 + hours * 3600 + minutes * 60 + seconds


def _normalize_language_code(value: str | None) -> str | None:
    raw_value = (value or "").strip()
    if not raw_value:
        return None
    mapped = _LANGUAGE_NAME_TO_CODE.get(raw_value.casefold())
    normalized = (mapped or raw_value).replace("_", "-").strip().casefold()
    if re.fullmatch(r"[a-z]{2,3}(?:-[a-z]{2})?", normalized):
        return normalized.split("-", 1)[0]
    return None


def _string_sequence(value: Any) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return ()
    entries: list[str] = []
    for item in value:
        string_value = _string_value(item)
        if string_value:
            entries.append(string_value)
    return tuple(entries)


def _int_value(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def _string_value(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None
