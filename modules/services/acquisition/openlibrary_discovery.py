"""Open Library metadata helpers for acquisition discovery."""

from __future__ import annotations

from collections.abc import Sequence
from urllib.parse import quote


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
