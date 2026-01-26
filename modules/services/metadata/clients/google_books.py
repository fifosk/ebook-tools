"""Google Books API client for book metadata."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional

import requests

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

logger = log_mgr.get_logger().getChild("services.metadata.clients.google_books")

_GOOGLE_BOOKS_BASE_URL = "https://www.googleapis.com/books/v1"

_SUMMARY_MAX_CHARS = 600


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


def _strip_html(text: str) -> str:
    """Strip HTML tags from text."""
    return re.sub(r"<[^>]+>", "", text).strip()


def _limit_summary_length(summary: str) -> str:
    """Truncate summary to reasonable length."""
    cleaned = summary.strip()
    if len(cleaned) <= _SUMMARY_MAX_CHARS:
        return cleaned
    truncated = cleaned[: _SUMMARY_MAX_CHARS - 1].rsplit(" ", 1)[0]
    return truncated + "…"


class GoogleBooksClient(BaseMetadataClient):
    """Google Books API client for book metadata.

    Requires a Google Books API key. Get one at:
    https://console.developers.google.com/
    """

    name = MetadataSource.GOOGLE_BOOKS
    supported_types = (MediaType.BOOK,)
    requires_api_key = True

    def __init__(
        self,
        *,
        session: Optional[requests.Session] = None,
        api_key: Optional[str] = None,
        timeout_seconds: float = 10.0,
        base_url: str = _GOOGLE_BOOKS_BASE_URL,
    ) -> None:
        super().__init__(session=session, api_key=api_key, timeout_seconds=timeout_seconds)
        self._base_url = base_url.rstrip("/")

    def _get_with_auth(
        self,
        endpoint: str,
        *,
        params: Optional[dict] = None,
        timeout: Optional[float] = None,
    ) -> Optional[dict]:
        """Make authenticated GET request to Google Books API."""
        if not self._api_key:
            return None

        url = f"{self._base_url}{endpoint}"
        query_params = {"key": self._api_key}
        if params:
            query_params.update(params)

        return self._get(url, params=query_params, timeout=timeout)

    def lookup(
        self,
        query: LookupQuery,
        options: LookupOptions,
    ) -> Optional[UnifiedMetadataResult]:
        """Look up book metadata from Google Books."""
        if not self.is_available:
            return None

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

        logger.info("Looking up Google Books by ISBN: %s", isbn)

        payload = self._get_with_auth(
            "/volumes",
            params={"q": f"isbn:{isbn}"},
            timeout=options.timeout_seconds,
        )

        if not payload:
            return None

        items = payload.get("items", [])
        if not isinstance(items, list) or not items:
            return None

        return self._parse_volume(items[0], query, options, is_isbn_match=True)

    def _lookup_by_title(
        self,
        query: LookupQuery,
        options: LookupOptions,
    ) -> Optional[UnifiedMetadataResult]:
        """Look up book by title and optional author."""
        title = query.title
        if not title:
            return None

        # Build query string
        q_parts = [f'intitle:"{title}"']
        if query.author:
            q_parts.append(f'inauthor:"{query.author}"')

        q = "+".join(q_parts)

        logger.info("Searching Google Books: %s", q)

        payload = self._get_with_auth(
            "/volumes",
            params={"q": q, "maxResults": 10},
            timeout=options.timeout_seconds,
        )

        if not payload:
            return None

        items = payload.get("items", [])
        if not isinstance(items, list) or not items:
            return None

        # Find best match
        best_item = self._select_best_item(items, query)
        if not best_item:
            return None

        return self._parse_volume(best_item, query, options, is_isbn_match=False)

    def _select_best_item(
        self,
        items: List[Mapping[str, Any]],
        query: LookupQuery,
    ) -> Optional[Mapping[str, Any]]:
        """Select the best matching volume from results."""
        if not items:
            return None

        query_title = (query.title or "").lower().strip()
        query_author = (query.author or "").lower().strip()

        best_item = None
        best_score = -1

        for item in items:
            volume_info = item.get("volumeInfo", {})
            if not isinstance(volume_info, Mapping):
                continue

            title = (volume_info.get("title") or "").lower().strip()
            authors = volume_info.get("authors", [])
            if not isinstance(authors, list):
                authors = []

            score = 0

            # Score title match
            if title == query_title:
                score += 3
            elif query_title and query_title in title:
                score += 1

            # Score author match
            if query_author:
                for author in authors:
                    author_lower = (author or "").lower()
                    if query_author == author_lower:
                        score += 3
                        break
                    elif query_author in author_lower or query_author.split()[0] in author_lower:
                        score += 1
                        break

            if score > best_score:
                best_score = score
                best_item = item

        return best_item

    def _parse_volume(
        self,
        item: Mapping[str, Any],
        query: LookupQuery,
        options: LookupOptions,
        is_isbn_match: bool,
    ) -> UnifiedMetadataResult:
        """Parse volume response into unified result."""
        volume_info = item.get("volumeInfo", {})
        if not isinstance(volume_info, Mapping):
            volume_info = {}

        title = _normalize_text(volume_info.get("title")) or query.title or "Unknown"

        # Extract authors
        authors_list = volume_info.get("authors", [])
        author = None
        if isinstance(authors_list, list):
            names = [a.strip() for a in authors_list if isinstance(a, str) and a.strip()]
            if names:
                author = ", ".join(names)
        author = author or query.author

        # Extract year from publishedDate
        published = _normalize_text(volume_info.get("publishedDate"))
        year = None
        if published:
            match = re.match(r"(\d{4})", published)
            if match:
                year = int(match.group(1))

        # Extract categories as genres
        categories = volume_info.get("categories", [])
        genres: List[str] = []
        if isinstance(categories, list):
            for cat in categories:
                if isinstance(cat, str) and cat.strip():
                    # Categories may include parent/child like "Fiction / Mystery"
                    for part in cat.split("/"):
                        part = part.strip()
                        if part and part not in genres:
                            genres.append(part)

        # Extract description
        description = volume_info.get("description")
        summary = None
        if isinstance(description, str) and description.strip():
            summary = _strip_html(description)
            summary = _limit_summary_length(summary)

        # Extract cover image
        image_links = volume_info.get("imageLinks", {})
        cover_url = None
        if isinstance(image_links, Mapping):
            # Prefer larger images
            for key in ["extraLarge", "large", "medium", "small", "thumbnail"]:
                url = _normalize_text(image_links.get(key))
                if url:
                    # Google Books URLs use http, upgrade to https
                    cover_url = url.replace("http://", "https://")
                    break

        # Extract ISBNs
        industry_ids = volume_info.get("industryIdentifiers", [])
        isbn_10 = None
        isbn_13 = None
        if isinstance(industry_ids, list):
            for id_info in industry_ids:
                if not isinstance(id_info, Mapping):
                    continue
                id_type = id_info.get("type")
                id_value = _normalize_isbn(id_info.get("identifier"))
                if id_type == "ISBN_10" and id_value:
                    isbn_10 = id_value
                elif id_type == "ISBN_13" and id_value:
                    isbn_13 = id_value

        # Extract Google Books ID
        google_id = _normalize_text(item.get("id"))

        # Extract language
        language = _normalize_text(volume_info.get("language"))

        # Extract page count as rough "runtime"
        page_count = volume_info.get("pageCount")
        if isinstance(page_count, int):
            # Estimate reading time: ~2 min per page
            runtime_minutes = page_count * 2
        else:
            runtime_minutes = None

        # Extract rating
        rating = volume_info.get("averageRating")
        if isinstance(rating, (int, float)):
            rating = float(rating)
        else:
            rating = None

        votes = volume_info.get("ratingsCount")
        if not isinstance(votes, int):
            votes = None

        source_ids = SourceIds(
            isbn=isbn_10,
            isbn_13=isbn_13,
            google_books_id=google_id,
        )

        return UnifiedMetadataResult(
            title=title,
            type=MediaType.BOOK,
            year=year,
            genres=genres[:10],
            summary=summary,
            cover_url=cover_url,
            source_ids=source_ids,
            confidence=ConfidenceLevel.HIGH if is_isbn_match else ConfidenceLevel.MEDIUM,
            primary_source=MetadataSource.GOOGLE_BOOKS,
            contributing_sources=[MetadataSource.GOOGLE_BOOKS],
            queried_at=datetime.now(timezone.utc),
            author=author,
            language=language,
            runtime_minutes=runtime_minutes,
            rating=rating,
            votes=votes,
            raw_responses={"google_books": dict(item)} if options.include_raw_responses else {},
        )


__all__ = ["GoogleBooksClient"]
