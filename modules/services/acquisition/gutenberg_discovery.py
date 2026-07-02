"""Project Gutenberg/Gutendex helpers for acquisition discovery."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import requests

from .discovery_normalization import normalize_language_code
from .discovery_values import int_value, string_sequence
from .models import AcquisitionCandidate
from .tokens import encode_acquisition_token


GUTENDEX_BOOKS_URL = "https://gutendex.com/books"


def discover_gutenberg(
    query: str,
    limit: int,
    *,
    language: str | None,
    session: requests.Session | None,
) -> list[AcquisitionCandidate]:
    if not query:
        return []

    client = session or requests.Session()
    normalized_language = normalize_language_code(language)
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
        gutenberg_id = int_value(item.get("id"))
        if gutenberg_id is None:
            continue
        formats = item.get("formats")
        if not isinstance(formats, Mapping):
            formats = {}
        epub_url = gutenberg_epub_url(formats)
        source_url = gutenberg_source_url(formats, gutenberg_id)
        title = string_value(item.get("title")) or f"Project Gutenberg {gutenberg_id}"
        contributors = gutenberg_person_names(item.get("authors"))
        languages = string_sequence(item.get("languages"))
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
                cover_url=string_value(formats.get("image/jpeg")),
                requires_confirmation=True,
                policy_notes=(
                    "Project Gutenberg/Gutendex result; confirm the work is public-domain or otherwise authorized in your location before acquisition.",
                ),
                metadata={
                    "source_kind": "gutenberg",
                    "gutenberg_id": gutenberg_id,
                    "download_count": int_value(item.get("download_count")),
                    "epub_url": epub_url,
                    "languages": list(languages),
                },
            )
        )
        if len(candidates) >= limit:
            break
    return candidates


def gutendex_search_params(
    query: str,
    limit: int,
    language_code: str | None,
) -> dict[str, str | int]:
    params: dict[str, str | int] = {
        "search": query,
        "page_size": max(1, min(limit, 32)),
    }
    if language_code:
        params["languages"] = language_code
    return params


def gutenberg_epub_url(formats: Mapping[str, Any]) -> str | None:
    preferred = string_value(formats.get("application/epub+zip"))
    if preferred:
        return preferred
    for key, value in formats.items():
        if "epub" not in str(key).casefold():
            continue
        url = string_value(value)
        if url:
            return url
    for value in formats.values():
        url = string_value(value)
        if url and ".epub" in url.casefold():
            return url
    return None


def gutenberg_source_url(
    formats: Mapping[str, Any],
    gutenberg_id: int,
) -> str:
    return (
        string_value(
            formats.get("text/html")
            or formats.get("text/html; charset=utf-8")
            or formats.get("text/html; charset=us-ascii")
        )
        or f"https://www.gutenberg.org/ebooks/{gutenberg_id}"
    )


def gutenberg_person_names(value: Any) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return ()
    names: list[str] = []
    for person in value:
        if not isinstance(person, Mapping):
            continue
        name = string_value(person.get("name"))
        if name:
            names.append(name)
    return tuple(names)


def string_value(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _candidate_token(payload: Mapping[str, Any]) -> str:
    return encode_acquisition_token(payload)
