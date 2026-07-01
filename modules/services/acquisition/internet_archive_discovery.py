"""Internet Archive metadata helpers for acquisition discovery."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import quote

import requests

from .discovery_normalization import MAX_DISCOVERY_LIMIT

_INTERNET_ARCHIVE_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,99}$")


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
