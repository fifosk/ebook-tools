"""Open Library metadata helpers for acquisition discovery."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import quote

import requests

from .discovery_normalization import normalize_language_code
from .discovery_values import int_value, safe_identifier, string_sequence, string_value
from .models import AcquisitionCandidate
from .tokens import encode_acquisition_token


OPENLIBRARY_SEARCH_URL = "https://openlibrary.org/search.json"


def discover_openlibrary(
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
    normalized_language = normalize_language_code(language)
    if normalized_language:
        params["language"] = normalized_language
    response = client.get(OPENLIBRARY_SEARCH_URL, params=params, timeout=10)
    response.raise_for_status()
    payload = response.json()
    docs = payload.get("docs", []) if isinstance(payload, Mapping) else []
    if not isinstance(docs, Sequence):
        return []

    candidates: list[AcquisitionCandidate] = []
    for item in docs:
        if not isinstance(item, Mapping):
            continue
        title = string_value(item.get("title")) or "Open Library result"
        work_key = openlibrary_path(string_value(item.get("key")), prefix="/works/")
        edition_keys = string_sequence(item.get("edition_key"))
        book_key = openlibrary_book_key(edition_keys)
        authors = string_sequence(item.get("author_name"))
        languages = string_sequence(item.get("language"))
        isbn_values = string_sequence(item.get("isbn"))
        ia_values = string_sequence(item.get("ia"))
        cover_id = int_value(item.get("cover_i"))
        cover_url = openlibrary_cover_url(cover_id)
        source_url = openlibrary_url(work_key or book_key)
        safe_id = safe_identifier(work_key or book_key or title)
        primary_author = authors[0] if authors else None
        primary_language = languages[0] if languages else normalized_language
        year = int_value(item.get("first_publish_year"))
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


def openlibrary_path(value: str | None, *, prefix: str | None = None) -> str | None:
    if not value:
        return None
    path = value if value.startswith("/") else f"/{value}"
    if prefix and not path.startswith(prefix):
        return None
    return path


def openlibrary_book_key(values: Sequence[str]) -> str | None:
    for value in values:
        normalized = openlibrary_path(value)
        if not normalized:
            continue
        if normalized.startswith("/books/"):
            return normalized
        return f"/books/{normalized.lstrip('/')}"
    return None


def openlibrary_url(path: str | None) -> str | None:
    normalized = openlibrary_path(path)
    if not normalized:
        return None
    return f"https://openlibrary.org{quote(normalized, safe='/')}"


def openlibrary_cover_url(cover_id: int | None) -> str | None:
    if cover_id is None:
        return None
    return f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg"


def _candidate_token(payload: Mapping[str, Any]) -> str:
    return encode_acquisition_token(payload)
