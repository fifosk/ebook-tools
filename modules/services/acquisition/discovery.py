"""Normalized source discovery for acquisition-backed Create flows."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import quote

import requests

from .provider_registry import (
    default_discovery_provider_ids,
    discovery_media_kinds_for,
)
from .tokens import encode_acquisition_token
from .discovery_values import (
    int_value as _int_value,
    safe_identifier as _safe_identifier,
    string_sequence as _string_sequence,
    string_value as _string_value,
)
from .discovery_planning import (
    order_default_discovery_candidates,
    provider_query_limit,
)
from .discovery_normalization import (
    normalize_language_code as _normalize_language_code,
    normalize_limit as _normalize_limit,
    normalize_media_kind as _normalize_media_kind,
    normalize_provider as _normalize_provider,
    normalize_query as _normalize_query,
)
from .file_sources import (
    append_bounded_newest_candidate as _append_bounded_newest_candidate,
    discover_local_epubs as _discover_local_epubs,
    discover_manual_downloads as _discover_manual_downloads,
    discover_nas_videos as _discover_nas_videos,
)
from .indexer_discovery import (
    discover_newznab_torznab as _discover_newznab_torznab,
)
from .gutenberg_discovery import (
    GUTENDEX_BOOKS_URL,
    gutenberg_epub_url,
    gutenberg_person_names,
    gutenberg_source_url,
    gutendex_search_params,
)
from .internet_archive_discovery import (
    fetch_internet_archive_metadata,
    internet_archive_download_url,
    internet_archive_epub_file,
    internet_archive_query,
    internet_archive_rights,
    mapping_value,
    normalize_internet_archive_source_ids as _normalize_source_ids,
)
from .openlibrary_discovery import (
    openlibrary_book_key,
    openlibrary_cover_url,
    openlibrary_path,
    openlibrary_url,
)
from .models import (
    AcquisitionCandidate,
    AcquisitionDiscoveryResult,
    AcquisitionProviderDiscoveryError,
)
from .youtube_discovery import (
    discover_youtube_search as _discover_youtube_search,
    discover_youtube_url as _discover_youtube_url,
)


_OPENLIBRARY_SEARCH_URL = "https://openlibrary.org/search.json"
_INTERNET_ARCHIVE_ADVANCED_SEARCH_URL = "https://archive.org/advancedsearch.php"
_INTERNET_ARCHIVE_METADATA_URL = "https://archive.org/metadata"


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
    raw_query = (query or "").strip()
    normalized_query = _normalize_query(query)
    normalized_provider = _normalize_provider(provider)
    effective_limit = _normalize_limit(limit)
    providers = _providers_for(normalized_kind, normalized_provider, config)
    is_default_provider_fanout = normalized_provider is None
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
        try:
            if not is_default_provider_fanout and len(candidates) >= effective_limit:
                break
            remaining = provider_query_limit(
                provider_id,
                candidates=candidates,
                effective_limit=effective_limit,
                is_default_provider_fanout=is_default_provider_fanout,
            )
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
            elif provider_id == "youtube_url":
                queried.append(provider_id)
                candidates.extend(_discover_youtube_url(raw_query, remaining))
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
        except AcquisitionProviderDiscoveryError as exc:
            if not is_default_provider_fanout:
                raise
            if provider_id not in queried:
                queried.append(provider_id)
            policy_notes.append(_default_provider_failure_note(exc))
            continue

    ordered_candidates = (
        order_default_discovery_candidates(candidates, providers)
        if is_default_provider_fanout
        else candidates
    )
    return AcquisitionDiscoveryResult(
        candidates=tuple(ordered_candidates[:effective_limit]),
        policy_notes=tuple(policy_notes),
        providers_queried=tuple(queried),
    )


def _default_provider_failure_note(error: AcquisitionProviderDiscoveryError) -> str:
    return f"{error.provider} unavailable during Default sources: {error.public_message}"


def _providers_for(
    media_kind: str,
    provider: str | None,
    config: Mapping[str, Any],
) -> tuple[str, ...]:
    if provider:
        media_kinds = discovery_media_kinds_for(provider)
        if not media_kinds:
            raise ValueError(f"provider {provider} does not support discovery")
        if media_kind not in media_kinds:
            raise ValueError(
                f"provider {provider} does not support {media_kind} discovery"
            )
        return (provider,)
    return default_discovery_provider_ids(media_kind, config)


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
    normalized_language = _normalize_language_code(language)
    response = client.get(
        GUTENDEX_BOOKS_URL,
        params=gutendex_search_params(query, limit, normalized_language),
        timeout=10,
    )
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
        epub_url = gutenberg_epub_url(formats)
        source_url = gutenberg_source_url(formats, gutenberg_id)
        title = _string_value(item.get("title")) or f"Project Gutenberg {gutenberg_id}"
        contributors = gutenberg_person_names(item.get("authors"))
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
    normalized_language = _normalize_language_code(language)
    params: dict[str, Any] = {
        "q": internet_archive_query(query, normalized_language),
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
        metadata = fetch_internet_archive_metadata(
            client,
            _INTERNET_ARCHIVE_METADATA_URL,
            identifier,
        )
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
        metadata = fetch_internet_archive_metadata(
            client,
            _INTERNET_ARCHIVE_METADATA_URL,
            identifier,
        )
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
    metadata_object = mapping_value(metadata.get("metadata"))
    epub_file = internet_archive_epub_file(metadata)
    if not epub_file:
        return None
    epub_name = _string_value(epub_file.get("name"))
    if not epub_name:
        return None
    epub_url = internet_archive_download_url(identifier, epub_name)
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
    rights = internet_archive_rights(search_item, metadata)
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
        work_key = openlibrary_path(_string_value(item.get("key")), prefix="/works/")
        edition_keys = _string_sequence(item.get("edition_key"))
        book_key = openlibrary_book_key(edition_keys)
        authors = _string_sequence(item.get("author_name"))
        languages = _string_sequence(item.get("language"))
        isbn_values = _string_sequence(item.get("isbn"))
        ia_values = _string_sequence(item.get("ia"))
        cover_id = _int_value(item.get("cover_i"))
        cover_url = openlibrary_cover_url(cover_id)
        source_url = openlibrary_url(work_key or book_key)
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
            "openlibrary_work_url": openlibrary_url(work_key),
            "openlibrary_book_key": book_key,
            "openlibrary_book_url": openlibrary_url(book_key),
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
                    "openlibrary_work_url": openlibrary_url(work_key),
                    "openlibrary_book_key": book_key,
                    "openlibrary_book_url": openlibrary_url(book_key),
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


def _candidate_token(payload: Mapping[str, Any]) -> str:
    return encode_acquisition_token(payload)
