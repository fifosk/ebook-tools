"""Project Gutenberg/Gutendex helpers for acquisition discovery."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


GUTENDEX_BOOKS_URL = "https://gutendex.com/books"


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
