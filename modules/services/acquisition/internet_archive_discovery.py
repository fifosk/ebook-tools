"""Internet Archive metadata helpers for acquisition discovery."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import quote

import requests

from .discovery_normalization import MAX_DISCOVERY_LIMIT, normalize_language_code
from .discovery_values import int_value, string_sequence, string_value
from .models import AcquisitionCandidate
from .tokens import encode_acquisition_token

_INTERNET_ARCHIVE_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,99}$")
_INTERNET_ARCHIVE_ADVANCED_SEARCH_URL = "https://archive.org/advancedsearch.php"
_INTERNET_ARCHIVE_METADATA_URL = "https://archive.org/metadata"


def discover_internet_archive(
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
    normalized_language = normalize_language_code(language)
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
    response = client.get(
        _INTERNET_ARCHIVE_ADVANCED_SEARCH_URL,
        params=params,
        timeout=10,
    )
    response.raise_for_status()
    payload = response.json()
    docs = (
        ((payload.get("response") or {}).get("docs"))
        if isinstance(payload, Mapping)
        else None
    )
    if not isinstance(docs, Sequence):
        return []

    candidates: list[AcquisitionCandidate] = []
    for item in docs:
        if not isinstance(item, Mapping):
            continue
        identifier = string_value(item.get("identifier"))
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
    epub_name = string_value(epub_file.get("name"))
    if not epub_name:
        return None
    epub_url = internet_archive_download_url(identifier, epub_name)
    title = (
        string_value(search_item.get("title"))
        or string_value(metadata_object.get("title"))
        or identifier
    )
    creators = string_sequence(search_item.get("creator")) or string_sequence(
        metadata_object.get("creator")
    )
    languages = string_sequence(search_item.get("language")) or string_sequence(
        metadata_object.get("language")
    )
    date_value = string_value(search_item.get("date")) or string_value(
        metadata_object.get("date")
    )
    year = int_value(date_value[:4]) if date_value else None
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
        size_bytes=int_value(epub_file.get("size")),
        requires_confirmation=True,
        policy_notes=(
            "Internet Archive result; confirm public, open, or otherwise authorized access before acquisition.",
        ),
        metadata={
            "source_kind": "internet_archive",
            "identifier": identifier,
            "epub_file": epub_name,
            "epub_url": epub_url,
            "downloads": int_value(search_item.get("downloads")),
            "licenseurl": string_value(search_item.get("licenseurl"))
            or string_value(metadata_object.get("licenseurl")),
            "rights": string_value(search_item.get("rights"))
            or string_value(metadata_object.get("rights")),
            "languages": list(languages),
        },
    )


def internet_archive_query(query: str, language_code: str | None) -> str:
    terms = " ".join(re.findall(r"[A-Za-z0-9._'-]+", query)).strip() or query
    clauses = [f"({terms})", "mediatype:texts", "-access-restricted-item:true"]
    if language_code:
        clauses.append(f"language:{language_code}")
    return " AND ".join(clauses)


def normalize_internet_archive_source_ids(
    source_ids: Sequence[str] | None,
    *,
    max_limit: int = MAX_DISCOVERY_LIMIT,
) -> tuple[str, ...]:
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
    return tuple(normalized[:max_limit])


def fetch_internet_archive_metadata(
    client: requests.Session,
    metadata_base_url: str,
    identifier: str,
) -> Mapping[str, Any]:
    response = client.get(
        f"{metadata_base_url}/{quote(identifier, safe='')}",
        timeout=10,
    )
    response.raise_for_status()
    payload = response.json()
    return payload if isinstance(payload, Mapping) else {}


def internet_archive_epub_file(metadata: Mapping[str, Any]) -> Mapping[str, Any] | None:
    metadata_object = mapping_value(metadata.get("metadata"))
    if truthy_value(metadata_object.get("access-restricted-item")):
        return None
    files = metadata.get("files")
    if not isinstance(files, Sequence) or isinstance(files, (str, bytes)):
        return None
    for item in files:
        if not isinstance(item, Mapping):
            continue
        name = string_value(item.get("name"))
        if not name:
            continue
        normalized_name = name.casefold()
        if not normalized_name.endswith(".epub"):
            continue
        if "encrypted" in normalized_name or "daisy" in normalized_name:
            continue
        if truthy_value(item.get("private")) or truthy_value(item.get("noindex")):
            continue
        return item
    return None


def internet_archive_download_url(identifier: str, filename: str) -> str:
    return (
        f"https://archive.org/download/{quote(identifier, safe='')}/"
        f"{quote(filename, safe='/')}"
    )


def internet_archive_rights(
    item: Mapping[str, Any],
    metadata: Mapping[str, Any],
) -> str:
    metadata_object = mapping_value(metadata.get("metadata"))
    license_url = (
        string_value(item.get("licenseurl"))
        or string_value(metadata_object.get("licenseurl"))
        or ""
    ).casefold()
    rights = (
        string_value(item.get("rights"))
        or string_value(metadata_object.get("rights"))
        or ""
    ).casefold()
    if "publicdomain" in license_url or "public domain" in rights:
        return "public_domain"
    if "creativecommons.org" in license_url or "creative commons" in rights:
        return "open_license"
    return "unknown"


def mapping_value(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def truthy_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().casefold() in {"1", "true", "yes", "y"}
    return False


def string_value(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _candidate_token(payload: Mapping[str, Any]) -> str:
    return encode_acquisition_token(payload)
