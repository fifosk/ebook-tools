"""OpenLibrary API client for book metadata."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence

import requests

from modules import config_manager as cfg
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

logger = log_mgr.get_logger().getChild("services.metadata.clients.openlibrary")

_OPENLIBRARY_BASE_URL = "https://openlibrary.org"
_OPENLIBRARY_SEARCH_URL = f"{_OPENLIBRARY_BASE_URL}/search.json"
_OPENLIBRARY_COVER_TEMPLATE = "https://covers.openlibrary.org/b/id/{cover_id}-L.jpg"

_FILENAME_YEAR_PATTERN = re.compile(r"(18|19|20|21)\d{2}")

_SUMMARY_MAX_SENTENCES = 4
_SUMMARY_MAX_CHARACTERS = 600


def _normalize_text(value: Any) -> Optional[str]:
    """Normalize a string value."""
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def _normalize_isbn(value: Any) -> Optional[str]:
    """Normalize and validate an ISBN."""
    if not isinstance(value, str):
        return None
    cleaned = re.sub(r"[^0-9Xx]", "", value)
    if len(cleaned) in {10, 13}:
        return cleaned.upper()
    return None


def _normalize_for_matching(value: Any) -> Optional[str]:
    """Normalize text for fuzzy matching."""
    if not isinstance(value, str):
        return None
    cleaned = re.sub(r"\s+", " ", value).strip().lower()
    return cleaned or None


def _limit_summary_length(summary: str) -> str:
    """Truncate summary to reasonable length."""
    cleaned = summary.strip()
    if not cleaned:
        return cleaned

    primary_paragraph = cleaned.split("\n\n", 1)[0].strip()
    sentences = re.split(r"(?<=[.!?])\s+", primary_paragraph)

    limited_sentences: list[str] = []
    for sentence in sentences:
        stripped = sentence.strip()
        if not stripped:
            continue
        limited_sentences.append(stripped)
        if len(limited_sentences) >= _SUMMARY_MAX_SENTENCES:
            break

    short_summary = " ".join(limited_sentences) if limited_sentences else primary_paragraph
    if len(short_summary) <= _SUMMARY_MAX_CHARACTERS:
        return short_summary

    truncated = short_summary[: _SUMMARY_MAX_CHARACTERS - 1].rsplit(" ", 1)[0]
    return truncated + "…"


def _cover_destination(query_key: str) -> Path:
    """Generate a unique local path for cover downloads."""
    root = cfg.resolve_directory(None, cfg.DEFAULT_COVERS_RELATIVE)
    safe_base = re.sub(r"[^A-Za-z0-9_.-]", "_", query_key) or "book"
    safe_base = safe_base[:40]
    digest = hashlib.sha1(query_key.encode("utf-8")).hexdigest()[:8]
    return root / f"openlibrary_{safe_base}_{digest}.jpg"


def _download_cover(url: str, destination: Path, timeout: float = 10.0) -> bool:
    """Download a cover image."""
    try:
        response = requests.get(url, timeout=timeout)
        if response.status_code != 200:
            return False
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(response.content)
        return True
    except Exception:
        logger.debug("Failed to download cover image from %s", url, exc_info=True)
        return False


def _select_best_doc(
    docs: Sequence[Mapping[str, Any]],
    title: str,
    author: Optional[str],
) -> Optional[Mapping[str, Any]]:
    """Select the best matching document from search results."""
    if not docs:
        return None

    normalized_title = _normalize_for_matching(title)
    normalized_author = _normalize_for_matching(author)

    best_doc: Optional[Mapping[str, Any]] = None
    best_score = -1

    for doc in docs:
        doc_title = _normalize_for_matching(doc.get("title"))
        if not doc_title:
            continue

        score = 0
        if doc_title == normalized_title:
            score += 3
        elif normalized_title and normalized_title in doc_title:
            score += 1

        author_names = [_normalize_for_matching(name) for name in doc.get("author_name", []) if name]
        if normalized_author and author_names:
            if normalized_author in author_names:
                score += 3
            else:
                for candidate in author_names:
                    if candidate and normalized_author.split()[0] in candidate:
                        score += 1
                        break

        if best_doc is None or score > best_score:
            best_doc = doc
            best_score = score

    return best_doc


class OpenLibraryClient(BaseMetadataClient):
    """OpenLibrary API client for book metadata.

    Uses the public OpenLibrary API (no authentication required) to
    search for books by title/author or look up by ISBN.
    """

    name = MetadataSource.OPENLIBRARY
    supported_types = (MediaType.BOOK,)
    requires_api_key = False

    def __init__(
        self,
        *,
        session: Optional[requests.Session] = None,
        api_key: Optional[str] = None,
        timeout_seconds: float = 10.0,
        base_url: str = _OPENLIBRARY_BASE_URL,
    ) -> None:
        super().__init__(session=session, api_key=api_key, timeout_seconds=timeout_seconds)
        self._base_url = base_url.rstrip("/")

    def lookup(
        self,
        query: LookupQuery,
        options: LookupOptions,
    ) -> Optional[UnifiedMetadataResult]:
        """Look up book metadata from OpenLibrary.

        Supports lookup by ISBN (preferred) or title/author search.
        """
        if query.media_type != MediaType.BOOK:
            return None

        # Try ISBN lookup first (higher confidence)
        if query.isbn:
            result = self._lookup_by_isbn(query, options)
            if result:
                return result

        # Fall back to title/author search
        if query.title:
            return self._lookup_by_title(query, options)

        return None

    def _lookup_by_isbn(
        self,
        query: LookupQuery,
        options: LookupOptions,
    ) -> Optional[UnifiedMetadataResult]:
        """Look up book by ISBN."""
        isbn = _normalize_isbn(query.isbn)
        if not isbn:
            return None

        logger.info("Looking up OpenLibrary by ISBN: %s", isbn)

        payload = self._get(
            f"{self._base_url}/api/books",
            params={"bibkeys": f"ISBN:{isbn}", "format": "json", "jscmd": "data"},
            timeout=options.timeout_seconds,
        )

        if not payload:
            return None

        book_data = payload.get(f"ISBN:{isbn}")
        if not isinstance(book_data, Mapping):
            return None

        return self._parse_isbn_response(book_data, query, options)

    def _lookup_by_title(
        self,
        query: LookupQuery,
        options: LookupOptions,
    ) -> Optional[UnifiedMetadataResult]:
        """Look up book by title and optional author."""
        title = query.title
        if not title:
            return None

        logger.info("Searching OpenLibrary: title=%s, author=%s", title, query.author)

        params: Dict[str, str] = {"title": title}
        if query.author:
            params["author"] = query.author

        payload = self._get(
            _OPENLIBRARY_SEARCH_URL,
            params=params,
            timeout=options.timeout_seconds,
        )

        if not payload:
            return None

        docs = payload.get("docs", [])
        if not isinstance(docs, list) or not docs:
            return None

        best_doc = _select_best_doc(docs, title, query.author)
        if not best_doc:
            return None

        return self._parse_search_response(best_doc, query, options)

    def _parse_isbn_response(
        self,
        data: Mapping[str, Any],
        query: LookupQuery,
        options: LookupOptions,
    ) -> UnifiedMetadataResult:
        """Parse ISBN lookup response into unified result."""
        title = _normalize_text(data.get("title")) or query.title or "Unknown"

        # Extract authors
        authors_raw = data.get("authors")
        authors: list[str] = []
        if isinstance(authors_raw, list):
            for entry in authors_raw:
                if isinstance(entry, Mapping):
                    name = _normalize_text(entry.get("name"))
                    if name:
                        authors.append(name)
        author = ", ".join(authors) if authors else query.author

        # Extract year
        publish_date = _normalize_text(data.get("publish_date"))
        year = None
        if publish_date:
            match = _FILENAME_YEAR_PATTERN.search(publish_date)
            if match:
                year = int(match.group(0))

        # Extract summary
        description = data.get("description")
        if isinstance(description, Mapping):
            description = description.get("value")
        summary = _normalize_text(description)
        if summary:
            summary = _limit_summary_length(summary)

        # Extract cover
        cover_info = data.get("cover")
        cover_url = None
        if isinstance(cover_info, Mapping):
            cover_url = _normalize_text(cover_info.get("large") or cover_info.get("medium") or cover_info.get("small"))
        elif isinstance(cover_info, str):
            cover_url = _normalize_text(cover_info)

        cover_file = None
        if cover_url and options.download_cover:
            destination = _cover_destination(f"isbn_{query.isbn}")
            if _download_cover(cover_url, destination, timeout=options.timeout_seconds):
                cover_file = str(destination)

        # Extract subjects/genres
        subjects = data.get("subjects")
        genres: list[str] = []
        if isinstance(subjects, list):
            for subj in subjects:
                if isinstance(subj, Mapping):
                    name = _normalize_text(subj.get("name"))
                    if name:
                        genres.append(name)
                elif isinstance(subj, str) and subj.strip():
                    genres.append(subj.strip())

        # Extract identifiers
        book_url = _normalize_text(data.get("url"))
        book_key = _normalize_text(data.get("key"))

        source_ids = SourceIds(
            isbn=_normalize_isbn(query.isbn),
            openlibrary_book_key=book_key,
        )

        return UnifiedMetadataResult(
            title=title,
            type=MediaType.BOOK,
            year=year,
            genres=genres[:10],  # Limit genres
            summary=summary,
            cover_url=cover_url,
            cover_file=cover_file,
            source_ids=source_ids,
            confidence=ConfidenceLevel.HIGH,  # ISBN is exact match
            primary_source=MetadataSource.OPENLIBRARY,
            contributing_sources=[MetadataSource.OPENLIBRARY],
            queried_at=datetime.now(timezone.utc),
            author=author,
            raw_responses={"openlibrary_isbn": dict(data)} if options.include_raw_responses else {},
        )

    def _parse_search_response(
        self,
        doc: Mapping[str, Any],
        query: LookupQuery,
        options: LookupOptions,
    ) -> UnifiedMetadataResult:
        """Parse search result document into unified result."""
        title = _normalize_text(doc.get("title")) or query.title or "Unknown"

        # Extract authors
        authors_raw = doc.get("author_name")
        author = None
        if isinstance(authors_raw, list):
            names = [name.strip() for name in authors_raw if isinstance(name, str) and name.strip()]
            if names:
                author = ", ".join(names)
        author = author or query.author

        # Extract year
        year_value = doc.get("first_publish_year")
        if not year_value:
            publish_years = doc.get("publish_year", [])
            if isinstance(publish_years, list) and publish_years:
                year_value = publish_years[0]
        year = int(year_value) if isinstance(year_value, (int, str)) and str(year_value).strip() else None

        # Extract cover
        cover_url = None
        cover_file = None
        cover_id = doc.get("cover_i")
        if isinstance(cover_id, int):
            cover_url = _OPENLIBRARY_COVER_TEMPLATE.format(cover_id=cover_id)
            if options.download_cover:
                destination = _cover_destination(f"cover_{cover_id}")
                if _download_cover(cover_url, destination, timeout=options.timeout_seconds):
                    cover_file = str(destination)

        # Extract summary (from first_sentence or work description)
        summary = None
        first_sentence = doc.get("first_sentence")
        if isinstance(first_sentence, Mapping):
            summary = _normalize_text(first_sentence.get("value"))
        elif isinstance(first_sentence, str):
            summary = _normalize_text(first_sentence)

        # Try to get full description from work
        work_key = _normalize_text(doc.get("key"))
        if work_key:
            work = self._get(
                f"{self._base_url}{work_key}.json",
                timeout=options.timeout_seconds,
            )
            if work:
                description = work.get("description")
                if isinstance(description, Mapping):
                    description = description.get("value")
                if isinstance(description, str):
                    summary = _normalize_text(description) or summary

        if summary:
            summary = _limit_summary_length(summary)

        # Extract subjects/genres
        subjects = doc.get("subject", [])
        genres: list[str] = []
        if isinstance(subjects, list):
            for subj in subjects:
                if isinstance(subj, str) and subj.strip():
                    genres.append(subj.strip())

        # Extract ISBN from results
        isbn = None
        isbn_raw = doc.get("isbn")
        if isinstance(isbn_raw, list):
            for candidate in isbn_raw:
                normalized = _normalize_isbn(candidate) if isinstance(candidate, str) else None
                if normalized:
                    isbn = normalized
                    break

        work_url = f"{_OPENLIBRARY_BASE_URL}{work_key}" if work_key else None

        source_ids = SourceIds(
            isbn=isbn,
            openlibrary_work_key=work_key,
        )

        return UnifiedMetadataResult(
            title=title,
            type=MediaType.BOOK,
            year=year,
            genres=genres[:10],
            summary=summary,
            cover_url=cover_url,
            cover_file=cover_file,
            source_ids=source_ids,
            confidence=ConfidenceLevel.MEDIUM,  # Title search is fuzzy match
            primary_source=MetadataSource.OPENLIBRARY,
            contributing_sources=[MetadataSource.OPENLIBRARY],
            queried_at=datetime.now(timezone.utc),
            author=author,
            raw_responses={"openlibrary_search": dict(doc)} if options.include_raw_responses else {},
        )

    def search(self, *, title: str, author: Optional[str] = None) -> Sequence[Mapping[str, Any]]:
        """Search OpenLibrary by title/author.

        This is the legacy API for backwards compatibility.
        """
        params: Dict[str, str] = {"title": title}
        if author:
            params["author"] = author

        payload = self._get(_OPENLIBRARY_SEARCH_URL, params=params)
        if not payload:
            return []

        docs = payload.get("docs", [])
        return docs if isinstance(docs, list) else []

    def fetch_work(self, work_key: str) -> Optional[Mapping[str, Any]]:
        """Fetch work details by key.

        This is the legacy API for backwards compatibility.
        """
        if not work_key or not work_key.startswith("/"):
            return None
        return self._get(f"{self._base_url}{work_key}.json")

    def lookup_isbn(self, isbn: str) -> Optional[Mapping[str, Any]]:
        """Look up book by ISBN.

        This is the legacy API for backwards compatibility.
        """
        normalized = _normalize_isbn(isbn)
        if not normalized:
            return None

        payload = self._get(
            f"{self._base_url}/api/books",
            params={"bibkeys": f"ISBN:{normalized}", "format": "json", "jscmd": "data"},
        )

        if not payload:
            return None

        book_data = payload.get(f"ISBN:{normalized}")
        return book_data if isinstance(book_data, Mapping) else None


__all__ = ["OpenLibraryClient"]
