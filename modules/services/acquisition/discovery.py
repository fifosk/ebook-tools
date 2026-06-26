"""Normalized source discovery for acquisition-backed Create flows."""

from __future__ import annotations

import os
import re
import xml.etree.ElementTree as ET
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit

import requests

from modules.language_constants import LANGUAGE_CODES
from modules.services.source_discovery import walk_visible_source_files
from modules.services.youtube_dubbing import list_downloaded_videos

from .provider_registry import (
    resolve_books_root,
    resolve_manual_download_roots,
    resolve_video_root,
)
from .references import store_acquisition_reference
from .tokens import encode_acquisition_token


_LANGUAGE_NAME_TO_CODE = {name.casefold(): code for name, code in LANGUAGE_CODES.items()}
_YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
_YOUTUBE_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"
_GUTENDEX_BOOKS_URL = "https://gutendex.com/books"
_OPENLIBRARY_SEARCH_URL = "https://openlibrary.org/search.json"
_INTERNET_ARCHIVE_ADVANCED_SEARCH_URL = "https://archive.org/advancedsearch.php"
_INTERNET_ARCHIVE_METADATA_URL = "https://archive.org/metadata"
_DEFAULT_DISCOVERY_LIMIT = 20
_MAX_DISCOVERY_LIMIT = 50
_INTERNET_ARCHIVE_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,99}$")
_DISCOVERY_PROVIDER_MEDIA_KINDS = {
    "gutenberg": {"book"},
    "internet_archive": {"book"},
    "local_epub": {"book"},
    "manual_downloads": {"book", "video"},
    "nas_video": {"video"},
    "newznab_torznab": {"video"},
    "openlibrary": {"book"},
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


class AcquisitionProviderDiscoveryError(RuntimeError):
    """Token-safe error raised when a configured discovery provider fails."""

    def __init__(self, *, provider: str, reason: str, message: str) -> None:
        super().__init__(message)
        self.provider = provider
        self.reason = reason
        self.public_message = message


def discover_acquisition_candidates(
    *,
    media_kind: str,
    query: str,
    provider: str | None = None,
    language: str | None = None,
    limit: int = 20,
    source_ids: Sequence[str] | None = None,
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
    normalized_source_ids = (
        _normalize_source_ids(source_ids) if "internet_archive" in providers else ()
    )

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
        elif provider_id == "manual_downloads":
            queried.append(provider_id)
            candidates.extend(
                _discover_manual_downloads(
                    config,
                    normalized_kind,
                    normalized_query,
                    remaining,
                )
            )
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
        elif provider_id == "internet_archive":
            queried.append(provider_id)
            candidates.extend(
                _discover_internet_archive(
                    normalized_query,
                    remaining,
                    language=language,
                    source_ids=normalized_source_ids,
                    session=session,
                )
            )
        elif provider_id == "openlibrary":
            queried.append(provider_id)
            candidates.extend(
                _discover_openlibrary(
                    normalized_query,
                    remaining,
                    language=language,
                    session=session,
                )
            )
        elif provider_id == "nas_video":
            queried.append(provider_id)
            candidates.extend(_discover_nas_videos(config, normalized_query, remaining))
        elif provider_id == "newznab_torznab":
            queried.append(provider_id)
            candidates.extend(
                _discover_newznab_torznab(
                    config,
                    normalized_query,
                    remaining,
                    session=session,
                )
            )
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


def _discover_internet_archive(
    query: str,
    limit: int,
    *,
    language: str | None,
    source_ids: Sequence[str] = (),
    session: requests.Session | None,
) -> list[AcquisitionCandidate]:
    if source_ids:
        return _discover_internet_archive_source_ids(source_ids, limit, session=session)
    if not query:
        return []

    client = session or requests.Session()
    params: dict[str, Any] = {
        "q": _internet_archive_query(query, language),
        "output": "json",
        "rows": max(1, min(limit, 25)),
        "page": 1,
        "fl[]": [
            "identifier",
            "title",
            "creator",
            "date",
            "language",
            "licenseurl",
            "rights",
            "downloads",
        ],
    }
    response = client.get(_INTERNET_ARCHIVE_ADVANCED_SEARCH_URL, params=params, timeout=10)
    response.raise_for_status()
    payload = response.json()
    docs = ((payload.get("response") or {}).get("docs")) if isinstance(payload, Mapping) else None
    if not isinstance(docs, Sequence):
        return []

    candidates: list[AcquisitionCandidate] = []
    for item in docs:
        if not isinstance(item, Mapping):
            continue
        identifier = _string_value(item.get("identifier"))
        if not identifier:
            continue
        metadata = _fetch_internet_archive_metadata(client, identifier)
        candidate = _internet_archive_candidate_from_metadata(
            identifier=identifier,
            metadata=metadata,
            search_item=item,
        )
        if not candidate:
            continue
        candidates.append(candidate)
        if len(candidates) >= limit:
            break
    return candidates


def _discover_internet_archive_source_ids(
    source_ids: Sequence[str],
    limit: int,
    *,
    session: requests.Session | None,
) -> list[AcquisitionCandidate]:
    client = session or requests.Session()
    candidates: list[AcquisitionCandidate] = []
    for identifier in source_ids:
        metadata = _fetch_internet_archive_metadata(client, identifier)
        candidate = _internet_archive_candidate_from_metadata(
            identifier=identifier,
            metadata=metadata,
            search_item={},
        )
        if not candidate:
            continue
        candidates.append(candidate)
        if len(candidates) >= limit:
            break
    return candidates


def _internet_archive_candidate_from_metadata(
    *,
    identifier: str,
    metadata: Mapping[str, Any],
    search_item: Mapping[str, Any],
) -> AcquisitionCandidate | None:
    metadata_object = _mapping_value(metadata.get("metadata"))
    epub_file = _internet_archive_epub_file(metadata)
    if not epub_file:
        return None
    epub_name = _string_value(epub_file.get("name"))
    if not epub_name:
        return None
    epub_url = _internet_archive_download_url(identifier, epub_name)
    title = (
        _string_value(search_item.get("title"))
        or _string_value(metadata_object.get("title"))
        or identifier
    )
    creators = _string_sequence(search_item.get("creator")) or _string_sequence(
        metadata_object.get("creator")
    )
    languages = _string_sequence(search_item.get("language")) or _string_sequence(
        metadata_object.get("language")
    )
    date_value = _string_value(search_item.get("date")) or _string_value(
        metadata_object.get("date")
    )
    year = _int_value(date_value[:4]) if date_value else None
    rights = _internet_archive_rights(search_item, metadata)
    token = _candidate_token(
        {
            "provider": "internet_archive",
            "media_kind": "book",
            "identifier": identifier,
            "epub_url": epub_url,
        }
    )
    return AcquisitionCandidate(
        candidate_id=f"internet_archive:{identifier}",
        provider="internet_archive",
        media_kind="book",
        title=title,
        rights=rights,
        capabilities=("search", "metadata", "acquire"),
        candidate_token=token,
        contributors=creators,
        language=languages[0] if languages else None,
        year=year,
        source_url=f"https://archive.org/details/{quote(identifier, safe='')}",
        cover_url=f"https://archive.org/services/img/{quote(identifier, safe='')}",
        size_bytes=_int_value(epub_file.get("size")),
        requires_confirmation=True,
        policy_notes=(
            "Internet Archive result; confirm public, open, or otherwise authorized access before acquisition.",
        ),
        metadata={
            "source_kind": "internet_archive",
            "identifier": identifier,
            "epub_file": epub_name,
            "epub_url": epub_url,
            "downloads": _int_value(search_item.get("downloads")),
            "licenseurl": _string_value(search_item.get("licenseurl"))
            or _string_value(metadata_object.get("licenseurl")),
            "rights": _string_value(search_item.get("rights"))
            or _string_value(metadata_object.get("rights")),
            "languages": list(languages),
        },
    )


def _discover_openlibrary(
    query: str,
    limit: int,
    *,
    language: str | None,
    session: requests.Session | None,
) -> list[AcquisitionCandidate]:
    if not query:
        return []

    client = session or requests.Session()
    fields = (
        "key,title,author_name,first_publish_year,language,cover_i,isbn,"
        "edition_key,ia,has_fulltext,availability"
    )
    params: dict[str, str | int] = {
        "q": query,
        "limit": max(1, min(limit, 25)),
        "fields": fields,
    }
    normalized_language = _normalize_language_code(language)
    if normalized_language:
        params["language"] = normalized_language
    response = client.get(_OPENLIBRARY_SEARCH_URL, params=params, timeout=10)
    response.raise_for_status()
    payload = response.json()
    docs = payload.get("docs", []) if isinstance(payload, Mapping) else []
    if not isinstance(docs, Sequence):
        return []

    candidates: list[AcquisitionCandidate] = []
    for item in docs:
        if not isinstance(item, Mapping):
            continue
        title = _string_value(item.get("title")) or "Open Library result"
        work_key = _openlibrary_path(_string_value(item.get("key")), prefix="/works/")
        edition_keys = _string_sequence(item.get("edition_key"))
        book_key = _openlibrary_book_key(edition_keys)
        authors = _string_sequence(item.get("author_name"))
        languages = _string_sequence(item.get("language"))
        isbn_values = _string_sequence(item.get("isbn"))
        ia_values = _string_sequence(item.get("ia"))
        cover_id = _int_value(item.get("cover_i"))
        cover_url = _openlibrary_cover_url(cover_id)
        source_url = _openlibrary_url(work_key or book_key)
        safe_id = _safe_identifier(work_key or book_key or title)
        primary_author = authors[0] if authors else None
        primary_language = languages[0] if languages else normalized_language
        year = _int_value(item.get("first_publish_year"))
        first_isbn = isbn_values[0] if isbn_values else None
        book_lookup = {
            "title": title,
            "author": primary_author,
            "year": str(year) if year is not None else None,
            "language": primary_language,
            "isbn": first_isbn,
            "cover_url": cover_url,
            "openlibrary_work_key": work_key,
            "openlibrary_work_url": _openlibrary_url(work_key),
            "openlibrary_book_key": book_key,
            "openlibrary_book_url": _openlibrary_url(book_key),
        }
        token = _candidate_token(
            {
                "provider": "openlibrary",
                "media_kind": "book",
                "work_key": work_key,
                "book_key": book_key,
                "title": title,
            }
        )
        candidates.append(
            AcquisitionCandidate(
                candidate_id=f"openlibrary:{safe_id}",
                provider="openlibrary",
                media_kind="book",
                title=title,
                rights="unknown",
                capabilities=("search", "metadata"),
                candidate_token=token,
                contributors=authors,
                language=primary_language,
                year=year,
                source_url=source_url,
                cover_url=cover_url,
                requires_confirmation=False,
                policy_notes=(
                    "Open Library result is metadata only; choose a local, public, or manually downloaded EPUB source before creating a narration job.",
                ),
                metadata={
                    "source_kind": "openlibrary",
                    "title": title,
                    "book_title": title,
                    "author": primary_author,
                    "book_author": primary_author,
                    "book_year": str(year) if year is not None else None,
                    "language": primary_language,
                    "book_language": primary_language,
                    "cover_url": cover_url,
                    "openlibrary_work_key": work_key,
                    "openlibrary_work_url": _openlibrary_url(work_key),
                    "openlibrary_book_key": book_key,
                    "openlibrary_book_url": _openlibrary_url(book_key),
                    "isbn": first_isbn,
                    "book_isbn": first_isbn,
                    "isbns": list(isbn_values),
                    "languages": list(languages),
                    "internet_archive_ids": list(ia_values),
                    "media_metadata_lookup": {
                        "kind": "book",
                        "provider": "openlibrary",
                        "book": book_lookup,
                    },
                    "has_fulltext": item.get("has_fulltext")
                    if isinstance(item.get("has_fulltext"), bool)
                    else None,
                    "availability": item.get("availability")
                    if isinstance(item.get("availability"), Mapping)
                    else None,
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


def _discover_manual_downloads(
    config: Mapping[str, Any],
    media_kind: str,
    query: str,
    limit: int,
) -> list[AcquisitionCandidate]:
    roots = resolve_manual_download_roots(config)
    if not roots:
        return []
    if media_kind == "book":
        return _discover_manual_download_epubs(roots, query, limit)
    if media_kind == "video":
        return _discover_manual_download_videos(roots, query, limit)
    return []


def _discover_manual_download_epubs(
    roots: Sequence[Path],
    query: str,
    limit: int,
) -> list[AcquisitionCandidate]:
    matches: list[AcquisitionCandidate] = []
    seen_paths: set[str] = set()
    for root in roots:
        for entry in walk_visible_source_files(root, suffixes={".epub"}, resolve_paths=True):
            absolute_path = entry.path.as_posix()
            if absolute_path in seen_paths:
                continue
            seen_paths.add(absolute_path)
            relative_path = _relative_path(entry.path, root)
            if query and query not in _search_blob(entry.path.name, relative_path, absolute_path):
                continue
            token = _candidate_token(
                {
                    "provider": "manual_downloads",
                    "media_kind": "book",
                    "path": absolute_path,
                }
            )
            matches.append(
                AcquisitionCandidate(
                    candidate_id=f"manual_downloads:book:{absolute_path}",
                    provider="manual_downloads",
                    media_kind="book",
                    title=_title_from_filename(entry.path),
                    rights="user_provided",
                    capabilities=("import_local", "metadata"),
                    candidate_token=token,
                    local_path=absolute_path,
                    size_bytes=entry.stat.st_size,
                    modified_at=datetime.fromtimestamp(entry.stat.st_mtime),
                    requires_confirmation=False,
                    policy_notes=(
                        "Backend-visible EPUB found in a configured manual download folder.",
                    ),
                    metadata={
                        "source_kind": "manual_download",
                        "source_path": absolute_path,
                        "source_root": root.as_posix(),
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


def _discover_manual_download_videos(
    roots: Sequence[Path],
    query: str,
    limit: int,
) -> list[AcquisitionCandidate]:
    matches: list[AcquisitionCandidate] = []
    seen_paths: set[str] = set()
    for root in roots:
        try:
            videos = list_downloaded_videos(root)
        except FileNotFoundError:
            continue
        for video in videos:
            absolute_path = video.path.as_posix()
            if absolute_path in seen_paths:
                continue
            seen_paths.add(absolute_path)
            relative_path = _relative_path(video.path, root)
            if query and query not in _search_blob(video.path.name, relative_path, absolute_path):
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
                    "provider": "manual_downloads",
                    "media_kind": "video",
                    "path": absolute_path,
                }
            )
            matches.append(
                AcquisitionCandidate(
                    candidate_id=f"manual_downloads:video:{absolute_path}",
                    provider="manual_downloads",
                    media_kind="video",
                    title=_title_from_filename(video.path),
                    rights="user_provided",
                    capabilities=("import_local", "extract_subtitles", "metadata"),
                    candidate_token=token,
                    local_path=absolute_path,
                    size_bytes=video.size_bytes,
                    modified_at=video.modified_at,
                    subtitles=subtitles,
                    requires_confirmation=False,
                    policy_notes=(
                        "Backend-visible video found in a configured manual download folder.",
                    ),
                    metadata={
                        "source_kind": "manual_download",
                        "source_path": absolute_path,
                        "source_root": root.as_posix(),
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
    _raise_for_youtube_status(response, operation="search")
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


def _discover_newznab_torznab(
    config: Mapping[str, Any],
    query: str,
    limit: int,
    *,
    session: requests.Session | None,
) -> list[AcquisitionCandidate]:
    endpoint = _indexer_endpoint(config)
    if not endpoint or not query:
        return []

    client = session or requests.Session()
    params: dict[str, str | int] = {
        "t": "search",
        "q": query,
        "limit": max(1, min(limit, 100)),
    }
    api_key = _indexer_api_key(config)
    if api_key:
        params["apikey"] = api_key
    category = _indexer_category(config)
    if category:
        params["cat"] = category

    response = client.get(_newznab_api_url(endpoint), params=params, timeout=15)
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        raise _indexer_provider_error(exc) from exc

    try:
        root = ET.fromstring(response.text)
    except ET.ParseError as exc:
        raise AcquisitionProviderDiscoveryError(
            provider="newznab_torznab",
            reason="invalid_xml",
            message="Indexer search returned an unreadable feed. Check the configured Newznab/Torznab endpoint.",
        ) from exc

    candidates: list[AcquisitionCandidate] = []
    for item in root.findall(".//item"):
        title = _xml_child_text(item, "title") or "Indexer result"
        guid = _xml_child_text(item, "guid") or _xml_child_text(item, "link") or title
        attrs = _torznab_attrs(item)
        size_bytes = _int_value(attrs.get("size")) or _enclosure_length(item)
        published_at = _xml_child_text(item, "pubDate")
        published_dt = _parse_rfc2822_datetime(published_at)
        indexer = _xml_child_text(item, "author") or _string_value(config.get("indexer_label"))
        categories = tuple(
            category
            for category in (
                _xml_child_text(element, None)
                for element in item.findall("./category")
            )
            if category
        )
        safe_guid = _safe_identifier(guid)
        source_uri = _xml_child_text(item, "link") or _enclosure_url(item)
        source_ref = (
            store_acquisition_reference(
                provider="newznab_torznab",
                media_kind="video",
                source_uri=source_uri,
                config=config,
                metadata={"guid": safe_guid, "title": title},
            )
            if source_uri
            else None
        )
        handoff_provider = "download_station" if source_ref else None
        token = _candidate_token(
            {
                "provider": "newznab_torznab",
                "media_kind": "video",
                "guid": safe_guid,
                "source_ref": source_ref,
                "title": title,
            }
        )
        seeders = _int_value(attrs.get("seeders"))
        peers = _int_value(attrs.get("peers"))
        candidates.append(
            AcquisitionCandidate(
                candidate_id=f"newznab_torznab:{safe_guid}",
                provider="newznab_torznab",
                media_kind="video",
                title=title,
                rights="unknown",
                capabilities=(
                    ("search", "metadata", "acquire")
                    if handoff_provider
                    else ("search", "metadata")
                ),
                candidate_token=token,
                contributors=tuple(value for value in (indexer,) if value),
                published_at=published_dt.isoformat() if published_dt else published_at,
                size_bytes=size_bytes,
                requires_confirmation=True,
                policy_notes=(
                    "Indexer result is metadata only; confirm lawful access before any downloader handoff.",
                    "Raw NZB, torrent, magnet, and API-key URLs stay server-side and are not returned to clients.",
                ),
                metadata={
                    "source_kind": "newznab_torznab",
                    "indexer": indexer,
                    "guid": safe_guid,
                    "categories": list(categories),
                    "seeders": seeders,
                    "peers": peers,
                    "grabs": _int_value(attrs.get("grabs")),
                    "has_download_url": bool(source_ref),
                    "handoff_provider": handoff_provider,
                    "handoff_action": "confirm_acquisition" if handoff_provider else None,
                },
            )
        )
        if len(candidates) >= limit:
            break
    return candidates


def _indexer_provider_error(exc: requests.HTTPError) -> AcquisitionProviderDiscoveryError:
    response = exc.response
    status_code = response.status_code if response is not None else None
    if status_code in {401, 403}:
        message = "Indexer search is not authorized. Check the backend Newznab/Torznab API key."
        reason = "unauthorized"
    elif status_code == 429:
        message = "Indexer search is rate limited. Wait and try again later."
        reason = "rate_limited"
    else:
        suffix = f" HTTP {status_code}" if status_code else ""
        message = f"Indexer search failed{suffix}. Try again later."
        reason = f"http_{status_code or 'unknown'}"
    return AcquisitionProviderDiscoveryError(
        provider="newznab_torznab",
        reason=reason,
        message=message,
    )


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
    _raise_for_youtube_status(response, operation="details")
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


def _raise_for_youtube_status(response: requests.Response, *, operation: str) -> None:
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        raise _youtube_provider_error(exc, operation=operation) from exc


def _youtube_provider_error(
    exc: requests.HTTPError,
    *,
    operation: str,
) -> AcquisitionProviderDiscoveryError:
    response = exc.response
    status_code = response.status_code if response is not None else None
    reason = _youtube_error_reason(response)
    normalized_reason = reason.casefold()
    if normalized_reason in {
        "quotaexceeded",
        "dailylimitexceeded",
        "ratelimitexceeded",
        "userratelimitexceeded",
    }:
        message = (
            "YouTube search quota or rate limit was exceeded. "
            "Check the backend YouTube Data API quota, then try again."
        )
    elif normalized_reason in {
        "keyinvalid",
        "accessnotconfigured",
        "forbidden",
        "insufficientpermissions",
        "iprefererblocked",
    } or status_code in {401, 403}:
        message = (
            "YouTube search is not authorized. "
            "Check the backend YouTube Data API key and API enablement."
        )
    elif status_code == 429:
        message = (
            "YouTube search is rate limited. Wait for quota to recover, then try again."
        )
    else:
        suffix = f" HTTP {status_code}" if status_code else ""
        message = f"YouTube search {operation} failed{suffix}. Try again later."
    return AcquisitionProviderDiscoveryError(
        provider="youtube_search",
        reason=reason or f"http_{status_code or 'unknown'}",
        message=message,
    )


def _youtube_error_reason(response: requests.Response | None) -> str:
    if response is None:
        return ""
    try:
        payload = response.json()
    except ValueError:
        return ""
    if not isinstance(payload, Mapping):
        return ""
    error = payload.get("error")
    if not isinstance(error, Mapping):
        return ""
    errors = error.get("errors")
    if isinstance(errors, Sequence):
        for item in errors:
            if not isinstance(item, Mapping):
                continue
            reason = _string_value(item.get("reason"))
            if reason:
                return reason
    status_reason = _string_value(error.get("status"))
    return status_reason or _string_value(error.get("reason")) or ""


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


def _indexer_endpoint(config: Mapping[str, Any]) -> str | None:
    for key in ("prowlarr_url", "torznab_url", "newznab_url", "indexer_url"):
        value = config.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    for key in ("PROWLARR_URL", "TORZNAB_URL", "NEWZNAB_URL", "EBOOK_PROWLARR_URL"):
        value = os.environ.get(key, "").strip()
        if value:
            return value
    return None


def _indexer_api_key(config: Mapping[str, Any]) -> str | None:
    for key in (
        "prowlarr_api_key",
        "torznab_api_key",
        "newznab_api_key",
        "indexer_api_key",
    ):
        value = config.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    for key in (
        "PROWLARR_API_KEY",
        "TORZNAB_API_KEY",
        "NEWZNAB_API_KEY",
        "EBOOK_PROWLARR_API_KEY",
    ):
        value = os.environ.get(key, "").strip()
        if value:
            return value
    return None


def _indexer_category(config: Mapping[str, Any]) -> str | None:
    value = config.get("indexer_video_category") or config.get("torznab_video_category")
    if isinstance(value, str) and value.strip():
        return value.strip()
    if isinstance(value, int):
        return str(value)
    env_value = os.environ.get("TORZNAB_VIDEO_CATEGORY", "").strip()
    return env_value or None


def _newznab_api_url(endpoint: str) -> str:
    parts = urlsplit(endpoint)
    query = urlencode(
        [
            (key, value)
            for key, value in parse_qsl(parts.query, keep_blank_values=True)
            if key.casefold() != "apikey"
        ],
        doseq=True,
    )
    path = parts.path.rstrip("/")
    if not path.endswith("/api") and path.rsplit("/", 1)[-1] != "api":
        path = f"{path}/api" if path else "/api"
    return urlunsplit((parts.scheme, parts.netloc, path, query, ""))


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


def _normalize_source_ids(source_ids: Sequence[str] | None) -> tuple[str, ...]:
    if not source_ids:
        return ()
    normalized: list[str] = []
    seen: set[str] = set()
    for source_id in source_ids:
        value = (source_id or "").strip()
        if not value:
            continue
        if not _INTERNET_ARCHIVE_IDENTIFIER_PATTERN.fullmatch(value):
            raise ValueError("source_id must be a valid Internet Archive identifier")
        key = value.casefold()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(value)
    return tuple(normalized[:_MAX_DISCOVERY_LIMIT])


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
    return encode_acquisition_token(payload)


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


def _internet_archive_query(query: str, language: str | None) -> str:
    terms = " ".join(re.findall(r"[A-Za-z0-9._'-]+", query)).strip() or query
    clauses = [f"({terms})", "mediatype:texts", "-access-restricted-item:true"]
    normalized_language = _normalize_language_code(language)
    if normalized_language:
        clauses.append(f"language:{normalized_language}")
    return " AND ".join(clauses)


def _fetch_internet_archive_metadata(
    client: requests.Session,
    identifier: str,
) -> Mapping[str, Any]:
    response = client.get(
        f"{_INTERNET_ARCHIVE_METADATA_URL}/{quote(identifier, safe='')}",
        timeout=10,
    )
    response.raise_for_status()
    payload = response.json()
    return payload if isinstance(payload, Mapping) else {}


def _internet_archive_epub_file(metadata: Mapping[str, Any]) -> Mapping[str, Any] | None:
    metadata_object = _mapping_value(metadata.get("metadata"))
    if _truthy_value(metadata_object.get("access-restricted-item")):
        return None
    files = metadata.get("files")
    if not isinstance(files, Sequence) or isinstance(files, (str, bytes)):
        return None
    for item in files:
        if not isinstance(item, Mapping):
            continue
        name = _string_value(item.get("name"))
        if not name:
            continue
        normalized_name = name.casefold()
        if not normalized_name.endswith(".epub"):
            continue
        if "encrypted" in normalized_name or "daisy" in normalized_name:
            continue
        if _truthy_value(item.get("private")) or _truthy_value(item.get("noindex")):
            continue
        return item
    return None


def _internet_archive_download_url(identifier: str, filename: str) -> str:
    return (
        f"https://archive.org/download/{quote(identifier, safe='')}/"
        f"{quote(filename, safe='/')}"
    )


def _internet_archive_rights(
    item: Mapping[str, Any],
    metadata: Mapping[str, Any],
) -> str:
    metadata_object = _mapping_value(metadata.get("metadata"))
    license_url = (
        _string_value(item.get("licenseurl"))
        or _string_value(metadata_object.get("licenseurl"))
        or ""
    ).casefold()
    rights = (
        _string_value(item.get("rights"))
        or _string_value(metadata_object.get("rights"))
        or ""
    ).casefold()
    if "publicdomain" in license_url or "public domain" in rights:
        return "public_domain"
    if "creativecommons.org" in license_url or "creative commons" in rights:
        return "open_license"
    return "unknown"


def _openlibrary_path(value: str | None, *, prefix: str | None = None) -> str | None:
    if not value:
        return None
    path = value if value.startswith("/") else f"/{value}"
    if prefix and not path.startswith(prefix):
        return None
    return path


def _openlibrary_book_key(values: Sequence[str]) -> str | None:
    for value in values:
        normalized = _openlibrary_path(value)
        if not normalized:
            continue
        if normalized.startswith("/books/"):
            return normalized
        return f"/books/{normalized.lstrip('/')}"
    return None


def _openlibrary_url(path: str | None) -> str | None:
    normalized = _openlibrary_path(path)
    if not normalized:
        return None
    return f"https://openlibrary.org{quote(normalized, safe='/')}"


def _openlibrary_cover_url(cover_id: int | None) -> str | None:
    if cover_id is None:
        return None
    return f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg"


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
    if isinstance(value, str):
        string_value = _string_value(value)
        return (string_value,) if string_value else ()
    if not isinstance(value, Sequence) or isinstance(value, bytes):
        return ()
    entries: list[str] = []
    for item in value:
        string_value = _string_value(item)
        if string_value:
            entries.append(string_value)
    return tuple(entries)


def _mapping_value(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _truthy_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().casefold() in {"1", "true", "yes", "y"}
    return False


def _xml_child_text(element: ET.Element, tag: str | None) -> str | None:
    if tag is None:
        return _string_value(element.text)
    child = element.find(tag)
    if child is None:
        return None
    return _string_value(child.text)


def _torznab_attrs(item: ET.Element) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for element in item.iter():
        if not element.tag.endswith("attr"):
            continue
        name = _string_value(element.attrib.get("name"))
        value = _string_value(element.attrib.get("value"))
        if name and value:
            attrs[name.casefold()] = value
    return attrs


def _enclosure_length(item: ET.Element) -> int | None:
    enclosure = item.find("enclosure")
    if enclosure is None:
        return None
    return _int_value(enclosure.attrib.get("length"))


def _enclosure_url(item: ET.Element) -> str | None:
    enclosure = item.find("enclosure")
    if enclosure is None:
        return None
    return _string_value(enclosure.attrib.get("url"))


def _parse_rfc2822_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError, AttributeError):
        return None


def _safe_identifier(value: str) -> str:
    raw_value = value.strip()
    parsed = urlsplit(raw_value)
    if parsed.scheme and parsed.netloc:
        raw_value = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))
    sanitized = re.sub(r"[^A-Za-z0-9_.:-]+", "-", raw_value)
    return sanitized.strip("-")[:160] or "result"


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
