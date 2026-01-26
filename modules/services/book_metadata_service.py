"""Metadata lookup helpers for book-like jobs."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import re
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence

import requests

from modules import config_manager as cfg
from modules import logging_manager as log_mgr

from .job_manager import PipelineJob, PipelineJobManager
from .pipeline_types import PipelineMetadata
from .metadata.types import LookupOptions, LookupQuery, MediaType
from .metadata.clients.google_books import GoogleBooksClient

logger = log_mgr.get_logger().getChild("services.book_metadata")


_OPENLIBRARY_BASE_URL = "https://openlibrary.org"
_OPENLIBRARY_SEARCH_URL = f"{_OPENLIBRARY_BASE_URL}/search.json"
_OPENLIBRARY_COVER_TEMPLATE = "https://covers.openlibrary.org/b/id/{cover_id}-L.jpg"

_FILENAME_YEAR_PATTERN = re.compile(r"(18|19|20|21)\d{2}")

# Patterns that indicate series numbering (e.g., "Housemaid 1: The Housemaid")
# These should be stripped when searching to improve match quality
_SERIES_PREFIX_PATTERNS = [
    re.compile(r"^[^:]+\s+\d+\s*:\s*", re.IGNORECASE),  # "Series Name 1: " -> ""
    re.compile(r"^\d+\s*[-–—]\s*", re.IGNORECASE),  # "1 - Title" -> "Title"
    re.compile(r"^(?:book|volume|vol\.?|part|episode|ep\.?)\s*\d+\s*[-–—:]\s*", re.IGNORECASE),  # "Book 1: " -> ""
    re.compile(r"^#\d+\s*[-–—:]\s*", re.IGNORECASE),  # "#1: Title" -> "Title"
]
_SERIES_COLON_PATTERN = re.compile(r"^.+?\d+\s*:\s*(.+)$")

_ISBN_CANDIDATE_PATTERN = re.compile(
    r"(?ix)"
    r"(?:isbn(?:-1[03])?[\s:#-]*)?"
    r"(?P<raw>[0-9Xx][0-9Xx\\s._-]{8,24}[0-9Xx])"
)

_SUMMARY_MAX_SENTENCES = 4
_SUMMARY_MAX_CHARACTERS = 600


@dataclass(frozen=True, slots=True)
class BookLookupQuery:
    """Query extracted from a filename and/or existing job metadata."""

    title: Optional[str]
    author: Optional[str]
    isbn: Optional[str]
    source_name: Optional[str]


def _basename(value: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        return ""
    return normalized.split("/")[-1].split("\\")[-1]


def _normalize_text(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def _normalize_isbn(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    cleaned = re.sub(r"[^0-9Xx]", "", value)
    if len(cleaned) in {10, 13}:
        return cleaned.upper()
    return None


def _normalize_title(value: str) -> Optional[str]:
    cleaned = value.strip()
    if not cleaned:
        return None
    cleaned = re.sub(r"[\[\(].*?[\]\)]", " ", cleaned)
    cleaned = re.sub(r"[._-]+", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = cleaned.strip()
    return cleaned or None


def _normalize_title_for_search(title: str) -> str:
    """Normalize a book title for better search results.

    Strips common series numbering patterns like:
    - "Housemaid 1: The Housemaid" -> "The Housemaid"
    - "Book 3: The Final Chapter" -> "The Final Chapter"
    - "#1 - First Story" -> "First Story"
    - "The Housemaid Housemaid 1" -> "The Housemaid" (duplicate title with series num)

    Also handles parenthetical series info like "(Book 1)" suffix.
    """
    cleaned = title.strip()

    # Try to extract title after "Series N:" pattern
    match = _SERIES_COLON_PATTERN.match(cleaned)
    if match:
        extracted = match.group(1).strip()
        if len(extracted) >= 3:  # Ensure we have a meaningful title
            return extracted

    # Try other prefix patterns
    for pattern in _SERIES_PREFIX_PATTERNS:
        result = pattern.sub("", cleaned)
        if result != cleaned and len(result) >= 3:
            return result.strip()

    # Remove trailing parenthetical series info like "(Book 1)" or "(Series Name #2)"
    result = re.sub(r"\s*\([^)]*(?:book|volume|vol\.?|part|#)\s*\d+[^)]*\)\s*$", "", cleaned, flags=re.IGNORECASE)
    if result != cleaned and len(result) >= 3:
        return result.strip()

    # Handle "Title Series N" pattern - remove trailing series info
    # e.g., "The Housemaid Housemaid 1" -> "The Housemaid"
    # Pattern: look for a word/phrase that repeats followed by a number
    series_suffix_match = re.search(r"(\b\w+(?:\s+\w+)?)\s+\1\s+\d+\s*$", cleaned, re.IGNORECASE)
    if series_suffix_match:
        # Remove the duplicate series name and number, keep just the title
        result = cleaned[: series_suffix_match.start()].strip() + " " + series_suffix_match.group(1)
        result = result.strip()
        if len(result) >= 3:
            return result

    # Handle "Title - SeriesName N" pattern (trailing dash with series info)
    # e.g., "The Housemaid - Housemaid 1" -> "The Housemaid"
    # This must come before duplicate word check to handle dashes properly
    dash_series_match = re.search(r"(.+?)\s*[-–—]\s*\S+\s+\d+\s*$", cleaned)
    if dash_series_match:
        result = dash_series_match.group(1).strip()
        if len(result) >= 3:
            return result

    # Also try: remove trailing "SeriesName N" where SeriesName is part of the title
    # e.g., "The Housemaid Housemaid 1" - detect that "Housemaid" appears twice
    words = cleaned.split()
    if len(words) >= 3:
        last_word = words[-1]
        if last_word.isdigit():
            # Check if second-to-last word appears earlier in the title
            second_last = words[-2].lower()
            title_words_lower = [w.lower() for w in words[:-2]]
            if second_last in title_words_lower:
                # Remove the duplicate series info
                result = " ".join(words[:-2])
                # Strip trailing dashes/punctuation
                result = re.sub(r"[\s\-–—]+$", "", result).strip()
                if len(result) >= 3:
                    return result

    return cleaned


_SOURCE_TAG_PATTERNS = re.compile(
    r"^(z-?library|libgen|lib\.?gen|epub|mobi|pdf|calibre|"
    r"ebook|e-?book|kindle|retail|scan|ocr|fixed|converted|"
    r"original|repack|proper|www\..+|\.com|\.org|\.net)$",
    re.IGNORECASE,
)


def _parse_filename_title_author(source_name: str) -> Dict[str, Optional[str]]:
    """Best-effort title/author extraction from a filename.

    Handles common formats:
    - "Title - Author.epub"
    - "Title (Author).epub"
    - "Title by Author.epub"
    - "Series Name 1: Title (Author).epub"
    - "Title (Author) (Z-Library).epub" - skips source tags like Z-Library
    """

    basename = _basename(source_name)
    if not basename:
        return {}
    stem = Path(basename).stem

    # First, try to extract author from trailing parentheses BEFORE normalizing
    # Pattern: "Title (Author)" or "Title - Subtitle (Author)"
    # Skip common source/library tags like "(Z-Library)", "(libgen)", "(epub)", etc.
    author_from_parens = None
    title_without_author_parens = stem

    # Find all parenthetical groups and check from right to left
    paren_matches = list(re.finditer(r"\(([^()]+)\)", stem))
    for match in reversed(paren_matches):
        candidate = match.group(1).strip()
        # Skip if it looks like a source/library tag
        if _SOURCE_TAG_PATTERNS.match(candidate):
            # Remove the source tag from the title
            title_without_author_parens = (
                stem[: match.start()].strip() + stem[match.end() :].strip()
            ).strip()
            continue
        # Skip if it looks like series info (e.g., "Book 1")
        if re.match(r"^(book|vol|volume|part|#)?\s*\d+", candidate, re.IGNORECASE):
            continue
        # This looks like an author name
        if candidate and len(candidate) >= 2:
            author_from_parens = candidate
            title_without_author_parens = stem[: match.start()].strip()
            # Remove any source tags that might follow
            title_without_author_parens = re.sub(
                r"\s*\([^)]*(?:z-?library|libgen|epub|mobi|pdf)[^)]*\)\s*$",
                "",
                title_without_author_parens,
                flags=re.IGNORECASE,
            ).strip()
            break

    # Try delimiter-based extraction BEFORE normalizing (since normalize converts dashes to spaces)
    # Only do this if we don't already have an author from parentheses
    if not author_from_parens:
        for delimiter in (" - ", " by ", " : "):
            if delimiter in title_without_author_parens:
                left, right = (part.strip() for part in title_without_author_parens.split(delimiter, 1))
                if len(left) > 2 and len(right) > 2:
                    # Normalize the title part
                    normalized_left = _normalize_title(left) or left.strip()
                    return {
                        "book_title": normalized_left,
                        "book_author": right,
                    }
                break

    # Now normalize the title (this removes any remaining brackets/parens)
    cleaned = _normalize_title(title_without_author_parens) or title_without_author_parens.strip()

    # Only remove year if it's not the entire title (e.g., "1984" is a valid book title)
    year_match = _FILENAME_YEAR_PATTERN.search(cleaned)
    if year_match:
        candidate_cleaned = cleaned.replace(year_match.group(0), " ")
        candidate_cleaned = re.sub(r"\s+", " ", candidate_cleaned).strip()
        # Only use the year-stripped version if we still have meaningful content
        if candidate_cleaned and len(candidate_cleaned) >= 2:
            cleaned = candidate_cleaned

    # If we have author from parens, return with the cleaned title
    if author_from_parens:
        return {
            "book_title": cleaned or None,
            "book_author": author_from_parens,
        }

    return {"book_title": cleaned or None}


def _extract_isbn_candidates(source_name: str) -> Sequence[str]:
    basename = _basename(source_name)
    if not basename:
        return []
    stem = Path(basename).stem
    candidates: list[str] = []
    for match in _ISBN_CANDIDATE_PATTERN.finditer(stem):
        raw = match.group("raw")
        normalized = _normalize_isbn(raw)
        if normalized:
            candidates.append(normalized)
    return candidates


def _limit_summary_length(summary: str) -> str:
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
    root = cfg.resolve_directory(None, cfg.DEFAULT_COVERS_RELATIVE)
    safe_base = re.sub(r"[^A-Za-z0-9_.-]", "_", query_key) or "book"
    safe_base = safe_base[:40]
    digest = hashlib.sha1(query_key.encode("utf-8")).hexdigest()[:8]
    return root / f"openlibrary_{safe_base}_{digest}.jpg"


def _download_cover(url: str, destination: Path) -> bool:
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return False
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(response.content)
        return True
    except Exception:  # pragma: no cover - network errors
        logger.debug("Failed to download cover image from %s", url, exc_info=True)
        return False


def _normalize(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    cleaned = re.sub(r"\s+", " ", value).strip().lower()
    return cleaned or None


def _select_best_doc(
    docs: Sequence[Mapping[str, Any]],
    title: str,
    author: Optional[str],
) -> Optional[Mapping[str, Any]]:
    if not docs:
        return None
    normalized_title = _normalize(title)
    normalized_author = _normalize(author)

    best_doc: Optional[Mapping[str, Any]] = None
    best_score = -1
    for doc in docs:
        doc_title = _normalize(doc.get("title"))
        if not doc_title:
            continue
        score = 0
        if doc_title == normalized_title:
            score += 3
        elif normalized_title and normalized_title in doc_title:
            score += 1

        author_names = [_normalize(name) for name in doc.get("author_name", []) if name]
        if normalized_author and author_names:
            if normalized_author in author_names:
                score += 3
            else:
                for candidate in author_names:
                    if normalized_author.split()[0] in candidate:
                        score += 1
                        break

        if best_doc is None or score > best_score:
            best_doc = doc
            best_score = score
    return best_doc


class OpenLibraryClient:
    """Small wrapper around the public Open Library API (no auth required)."""

    def __init__(
        self,
        *,
        session: Optional[requests.Session] = None,
        base_url: str = _OPENLIBRARY_BASE_URL,
        timeout_seconds: float = 10.0,
    ) -> None:
        self._session = session or requests.Session()
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds

    def search(self, *, title: str, author: Optional[str] = None) -> Sequence[Mapping[str, Any]]:
        params: Dict[str, str] = {"title": title}
        if author:
            params["author"] = author
        response = self._session.get(
            _OPENLIBRARY_SEARCH_URL,
            params=params,
            headers={"Accept": "application/json"},
            timeout=self._timeout,
        )
        response.raise_for_status()
        payload = response.json()
        docs = payload.get("docs", []) if isinstance(payload, dict) else []
        return docs if isinstance(docs, list) else []

    def fetch_work(self, work_key: str) -> Optional[Mapping[str, Any]]:
        if not work_key or not work_key.startswith("/"):
            return None
        response = self._session.get(
            f"{self._base_url}{work_key}.json",
            headers={"Accept": "application/json"},
            timeout=self._timeout,
        )
        if response.status_code != 200:
            return None
        payload = response.json()
        return payload if isinstance(payload, Mapping) else None

    def lookup_isbn(self, isbn: str) -> Optional[Mapping[str, Any]]:
        normalized = _normalize_isbn(isbn)
        if not normalized:
            return None
        response = self._session.get(
            f"{self._base_url}/api/books",
            params={"bibkeys": f"ISBN:{normalized}", "format": "json", "jscmd": "data"},
            headers={"Accept": "application/json"},
            timeout=self._timeout,
        )
        if response.status_code != 200:
            return None
        payload = response.json()
        if not isinstance(payload, Mapping):
            return None
        book_data = payload.get(f"ISBN:{normalized}")
        return book_data if isinstance(book_data, Mapping) else None


def _extract_existing_book_metadata(job: PipelineJob) -> Dict[str, Any]:
    if job.request is not None:
        try:
            return job.request.inputs.book_metadata.as_dict()
        except Exception:
            return {}
    request_payload = job.request_payload
    if isinstance(request_payload, Mapping):
        inputs = request_payload.get("inputs")
        if isinstance(inputs, Mapping):
            book_metadata = inputs.get("book_metadata")
            if isinstance(book_metadata, Mapping):
                return dict(book_metadata)
    result_payload = job.result_payload
    if isinstance(result_payload, Mapping):
        book_metadata = result_payload.get("book_metadata")
        if isinstance(book_metadata, Mapping):
            return dict(book_metadata)
    return {}


def _resolve_input_file(job: PipelineJob) -> Optional[str]:
    if job.request is not None:
        candidate = getattr(job.request.inputs, "input_file", None)
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    request_payload = job.request_payload
    if isinstance(request_payload, Mapping):
        inputs = request_payload.get("inputs")
        if isinstance(inputs, Mapping):
            candidate = inputs.get("input_file")
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
    return None


_VALID_BOOK_PROVIDERS = {"openlibrary", "google_books"}


def _extract_existing_lookup(job: PipelineJob) -> Optional[Mapping[str, Any]]:
    for payload in (job.request_payload, job.result_payload):
        if not isinstance(payload, Mapping):
            continue
        lookup = payload.get("book_metadata_lookup")
        if isinstance(lookup, Mapping):
            provider = lookup.get("provider")
            if isinstance(provider, str) and provider.strip().lower() in _VALID_BOOK_PROVIDERS:
                return lookup
    book_metadata = _extract_existing_book_metadata(job)
    lookup = book_metadata.get("book_metadata_lookup")
    if isinstance(lookup, Mapping):
        provider = lookup.get("provider")
        if isinstance(provider, str) and provider.strip().lower() in _VALID_BOOK_PROVIDERS:
            return lookup
    return None


def _infer_lookup_query(source_name: Optional[str], metadata: Mapping[str, Any]) -> BookLookupQuery:
    isbn_candidate = None
    for key in ("isbn", "book_isbn", "isbn_13", "isbn13", "isbn10", "isbn_10"):
        normalized = _normalize_isbn(metadata.get(key))
        if normalized:
            isbn_candidate = normalized
            break

    parsed_title = _normalize_text(metadata.get("book_title")) or _normalize_text(metadata.get("title"))
    parsed_author = _normalize_text(metadata.get("book_author")) or _normalize_text(metadata.get("author"))

    if (not parsed_title or not parsed_author) and source_name:
        filename_bits = _parse_filename_title_author(source_name)
        parsed_title = parsed_title or filename_bits.get("book_title")
        parsed_author = parsed_author or filename_bits.get("book_author")

    if not isbn_candidate and source_name:
        isbn_candidates = _extract_isbn_candidates(source_name)
        if isbn_candidates:
            isbn_candidate = isbn_candidates[0]

    return BookLookupQuery(
        title=_normalize_title_for_search(parsed_title) if parsed_title else None,
        author=_normalize_text(parsed_author),  # Don't strip periods from author names
        isbn=isbn_candidate,
        source_name=_basename(source_name) if source_name else None,
    )


def _build_job_label(
    *,
    title: Optional[str],
    author: Optional[str],
    fallback: Optional[str],
) -> Optional[str]:
    if title and author:
        return f"{title} — {author}"
    if title:
        return title
    if fallback:
        try:
            stem = Path(fallback).stem
        except Exception:
            stem = fallback
        return stem or fallback
    return None


class BookMetadataService:
    """Lazy metadata enrichment for pipeline/book jobs using Open Library with Google Books fallback."""

    def __init__(
        self,
        *,
        job_manager: PipelineJobManager,
        openlibrary_client: Optional[OpenLibraryClient] = None,
        google_books_api_key: Optional[str] = None,
    ) -> None:
        self._job_manager = job_manager
        self._openlibrary = openlibrary_client or OpenLibraryClient()
        # Initialize Google Books client if API key is available
        self._google_books: Optional[GoogleBooksClient] = None
        api_key = google_books_api_key or self._get_google_books_api_key()
        if api_key:
            self._google_books = GoogleBooksClient(api_key=api_key)
            logger.info("Google Books API initialized (fallback enabled)")
        else:
            logger.debug("No Google Books API key - fallback disabled")

    @staticmethod
    def _get_google_books_api_key() -> Optional[str]:
        """Get Google Books API key from config."""
        try:
            settings = cfg.get_settings()
            if settings and hasattr(settings, "google_books_api_key") and settings.google_books_api_key:
                return settings.google_books_api_key.get_secret_value()
        except Exception:
            pass
        try:
            config = cfg.load_json_config()
            api_keys = config.get("api_keys", {})
            if isinstance(api_keys, dict):
                key = api_keys.get("google_books")
                if isinstance(key, str) and key.strip():
                    return key.strip()
        except Exception:
            pass
        return None

    def get_openlibrary_metadata(
        self,
        job_id: str,
        *,
        user_id: Optional[str] = None,
        user_role: Optional[str] = None,
    ) -> Dict[str, Any]:
        job = self._job_manager.get(job_id, user_id=user_id, user_role=user_role)
        if job.job_type not in {"pipeline", "book"}:
            raise KeyError("Book job not found")

        input_file = _resolve_input_file(job)
        source_name = _basename(input_file or "") if input_file else None
        book_metadata = _extract_existing_book_metadata(job)
        query = _infer_lookup_query(source_name, book_metadata)
        existing_lookup = _extract_existing_lookup(job)

        return {
            "job_id": job.job_id,
            "source_name": source_name,
            "query": {
                "title": query.title,
                "author": query.author,
                "isbn": query.isbn,
            }
            if (query.title or query.author or query.isbn)
            else None,
            "book_metadata_lookup": dict(existing_lookup) if existing_lookup is not None else None,
        }

    def lookup_openlibrary_metadata_for_query(self, query: str, *, force: bool = False) -> Dict[str, Any]:
        """Lookup Open Library metadata for a filename/title/ISBN without persisting anything."""

        normalized_source = _basename(query)
        seed = _parse_filename_title_author(query) if query else {}
        inferred = _infer_lookup_query(normalized_source or query, seed)
        lookup_payload = self._build_openlibrary_payload(inferred, job_id=None)
        return {
            "source_name": normalized_source or None,
            "query": {
                "title": inferred.title,
                "author": inferred.author,
                "isbn": inferred.isbn,
            }
            if (inferred.title or inferred.author or inferred.isbn)
            else None,
            "book_metadata_lookup": dict(lookup_payload),
        }

    def lookup_openlibrary_metadata(
        self,
        job_id: str,
        *,
        force: bool = False,
        user_id: Optional[str] = None,
        user_role: Optional[str] = None,
    ) -> Dict[str, Any]:
        job = self._job_manager.get(job_id, user_id=user_id, user_role=user_role)
        if job.job_type not in {"pipeline", "book"}:
            raise KeyError("Book job not found")

        existing_lookup = _extract_existing_lookup(job)
        if existing_lookup is not None and not force:
            return self.get_openlibrary_metadata(job_id, user_id=user_id, user_role=user_role)

        input_file = _resolve_input_file(job)
        source_name = _basename(input_file or "") if input_file else None
        book_metadata = _extract_existing_book_metadata(job)
        query = _infer_lookup_query(source_name, book_metadata)

        payload = self._build_openlibrary_payload(query, job_id=job_id)
        self._persist_lookup_result(job_id, payload, user_id=user_id, user_role=user_role)
        return self.get_openlibrary_metadata(job_id, user_id=user_id, user_role=user_role)

    def _try_google_books_fallback(
        self,
        query: BookLookupQuery,
        job_id: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        """Try Google Books API as fallback when OpenLibrary fails."""
        if self._google_books is None:
            return None

        logger.info(
            "Trying Google Books fallback for %s",
            query.isbn or query.title or query.source_name or "unknown",
        )

        try:
            lookup_query = LookupQuery(
                media_type=MediaType.BOOK,
                title=query.title,
                author=query.author,
                isbn=query.isbn,
            )
            options = LookupOptions(timeout_seconds=15.0)
            result = self._google_books.lookup(lookup_query, options)
        except Exception as exc:
            logger.warning("Google Books fallback failed: %s", exc)
            return None

        if result is None:
            logger.debug("Google Books returned no results")
            return None

        timestamp = datetime.now(timezone.utc).isoformat()
        source_name = query.source_name

        # Download cover image if available
        cover_file = None
        cover_url = result.cover_url
        if cover_url:
            # Use Google Books ID or title for destination
            dest_key = result.source_ids.google_books_id or (query.title or "book")
            destination = _cover_destination(f"gbooks_{dest_key}")
            if _download_cover(cover_url, destination):
                cover_file = str(destination)

        job_label = _build_job_label(
            title=result.title,
            author=result.author,
            fallback=source_name,
        )

        # Extract ISBN from result
        isbn = result.source_ids.isbn_13 or result.source_ids.isbn

        return {
            "kind": "book",
            "provider": "google_books",
            "queried_at": timestamp,
            "source_name": source_name,
            "query": {
                "title": query.title,
                "author": query.author,
                "isbn": query.isbn,
            },
            "job_label": job_label,
            "book": {
                "title": result.title,
                "author": result.author,
                "year": str(result.year) if result.year else None,
                "summary": result.summary,
                "isbn": isbn,
                "cover_url": cover_url,
                "cover_file": cover_file,
                "google_books_id": result.source_ids.google_books_id,
            },
        }

    def _build_openlibrary_payload(
        self,
        query: BookLookupQuery,
        *,
        job_id: Optional[str],
    ) -> Dict[str, Any]:
        timestamp = datetime.now(timezone.utc).isoformat()
        source_name = query.source_name

        def _error_payload(message: str) -> Dict[str, Any]:
            job_label = _build_job_label(title=query.title, author=query.author, fallback=source_name)
            payload: Dict[str, Any] = {
                "kind": "book",
                "provider": "openlibrary",
                "queried_at": timestamp,
                "source_name": source_name,
                "query": {
                    "title": query.title,
                    "author": query.author,
                    "isbn": query.isbn,
                }
                if (query.title or query.author or query.isbn)
                else None,
                "job_label": job_label,
                "error": message,
            }
            return payload

        if job_id:
            logger.info(
                "Looking up Open Library metadata for job %s (%s)",
                job_id,
                query.isbn or query.title or source_name or "unknown",
            )
        else:
            logger.info(
                "Looking up Open Library metadata (%s)",
                query.isbn or query.title or source_name or "unknown",
            )

        if query.isbn:
            try:
                isbn_payload = self._openlibrary.lookup_isbn(query.isbn)
            except Exception as exc:
                # Try Google Books fallback for ISBN
                google_result = self._try_google_books_fallback(query, job_id)
                if google_result is not None:
                    return google_result
                return _error_payload(f"Open Library ISBN lookup failed: {exc}")
            if not isbn_payload:
                # Try Google Books fallback for ISBN
                google_result = self._try_google_books_fallback(query, job_id)
                if google_result is not None:
                    return google_result
                return _error_payload("Open Library did not return a matching ISBN record.")

            title = _normalize_text(isbn_payload.get("title")) or query.title
            authors_raw = isbn_payload.get("authors")
            authors: list[str] = []
            if isinstance(authors_raw, list):
                for entry in authors_raw:
                    if isinstance(entry, Mapping):
                        name = _normalize_text(entry.get("name"))
                        if name:
                            authors.append(name)
            author = ", ".join(authors) if authors else query.author

            publish_date = _normalize_text(isbn_payload.get("publish_date"))
            year = None
            if publish_date:
                match = _FILENAME_YEAR_PATTERN.search(publish_date)
                if match:
                    year = match.group(0)

            description = isbn_payload.get("description")
            if isinstance(description, Mapping):
                description = description.get("value")
            summary = _normalize_text(description) or None
            if summary:
                summary = _limit_summary_length(summary)

            cover_info = isbn_payload.get("cover")
            cover_url = None
            if isinstance(cover_info, Mapping):
                cover_url = _normalize_text(cover_info.get("large") or cover_info.get("medium") or cover_info.get("small"))
            elif isinstance(cover_info, str):
                cover_url = _normalize_text(cover_info)

            cover_file = None
            if cover_url:
                destination = _cover_destination(f"isbn_{query.isbn}")
                if _download_cover(cover_url, destination):
                    cover_file = str(destination)

            job_label = _build_job_label(title=title, author=author, fallback=source_name)
            book_url = _normalize_text(isbn_payload.get("url"))
            book_key = _normalize_text(isbn_payload.get("key"))

            return {
                "kind": "book",
                "provider": "openlibrary",
                "queried_at": timestamp,
                "source_name": source_name,
                "query": {
                    "title": query.title,
                    "author": query.author,
                    "isbn": query.isbn,
                },
                "job_label": job_label,
                "book": {
                    "title": title,
                    "author": author,
                    "year": year,
                    "summary": summary,
                    "isbn": query.isbn,
                    "cover_url": cover_url,
                    "cover_file": cover_file,
                    "openlibrary_book_key": book_key,
                    "openlibrary_book_url": book_url,
                },
            }

        title_query = query.title or ""
        if not title_query.strip():
            return _error_payload("A title or ISBN is required for Open Library lookup.")

        # Normalize title to strip series numbering patterns for better search results
        normalized_title = _normalize_title_for_search(title_query)
        logger.debug("Normalized title '%s' -> '%s' for OpenLibrary search", title_query, normalized_title)

        try:
            docs = self._openlibrary.search(title=normalized_title, author=query.author)
        except Exception as exc:
            return _error_payload(f"Open Library search failed: {exc}")

        best_doc = _select_best_doc(docs, normalized_title, query.author)

        # If normalized search failed, try with original title as fallback
        if best_doc is None and normalized_title != title_query:
            logger.debug("Normalized search failed, trying original title: %s", title_query)
            try:
                docs = self._openlibrary.search(title=title_query, author=query.author)
                best_doc = _select_best_doc(docs, title_query, query.author)
            except Exception:
                pass  # Keep the original error

        if best_doc is None:
            # Try Google Books fallback if available
            google_result = self._try_google_books_fallback(query, job_id)
            if google_result is not None:
                return google_result
            return _error_payload("Open Library returned no matching works.")

        title = _normalize_text(best_doc.get("title")) or query.title
        authors_raw = best_doc.get("author_name")
        author = None
        if isinstance(authors_raw, list):
            names = [name.strip() for name in authors_raw if isinstance(name, str) and name.strip()]
            if names:
                author = ", ".join(names)
        author = author or query.author

        year_value = best_doc.get("first_publish_year") or (best_doc.get("publish_year", [None])[0] if isinstance(best_doc.get("publish_year"), list) else None)
        year = str(year_value) if isinstance(year_value, (int, str)) and str(year_value).strip() else None

        cover_url = None
        cover_file = None
        cover_id = best_doc.get("cover_i")
        if isinstance(cover_id, int):
            cover_url = _OPENLIBRARY_COVER_TEMPLATE.format(cover_id=cover_id)
            destination = _cover_destination(f"cover_{cover_id}")
            if _download_cover(cover_url, destination):
                cover_file = str(destination)

        summary = None
        first_sentence = best_doc.get("first_sentence")
        if isinstance(first_sentence, Mapping):
            summary = _normalize_text(first_sentence.get("value"))
        elif isinstance(first_sentence, str):
            summary = _normalize_text(first_sentence)

        work_key = _normalize_text(best_doc.get("key"))
        work_url = f"{_OPENLIBRARY_BASE_URL}{work_key}" if work_key else None
        if work_key:
            try:
                work = self._openlibrary.fetch_work(work_key)
            except Exception:
                work = None
            if work is not None:
                description = work.get("description")
                if isinstance(description, Mapping):
                    description = description.get("value")
                if isinstance(description, str):
                    summary = _normalize_text(description) or summary

        if summary:
            summary = _limit_summary_length(summary)

        isbn = None
        isbn_raw = best_doc.get("isbn")
        if isinstance(isbn_raw, list):
            for candidate in isbn_raw:
                normalized = _normalize_isbn(candidate) if isinstance(candidate, str) else None
                if normalized:
                    isbn = normalized
                    break

        job_label = _build_job_label(title=title, author=author, fallback=source_name)

        return {
            "kind": "book",
            "provider": "openlibrary",
            "queried_at": timestamp,
            "source_name": source_name,
            "query": {
                "title": query.title,
                "author": query.author,
                "isbn": query.isbn,
            },
            "job_label": job_label,
            "book": {
                "title": title,
                "author": author,
                "year": year,
                "summary": summary,
                "isbn": isbn,
                "cover_url": cover_url,
                "cover_file": cover_file,
                "openlibrary_work_key": work_key,
                "openlibrary_work_url": work_url,
                "openlibrary_cover_id": cover_id if isinstance(cover_id, int) else None,
            },
        }

    def _persist_lookup_result(
        self,
        job_id: str,
        payload: Mapping[str, Any],
        *,
        user_id: Optional[str],
        user_role: Optional[str],
    ) -> None:
        def _mutate(job: PipelineJob) -> None:
            request_payload = dict(job.request_payload) if isinstance(job.request_payload, Mapping) else {}
            request_payload["book_metadata_lookup"] = dict(payload)

            inputs = request_payload.get("inputs")
            if not isinstance(inputs, Mapping):
                inputs = {}
            inputs = dict(inputs)

            existing = inputs.get("book_metadata")
            if not isinstance(existing, Mapping):
                existing = {}
            book_metadata = dict(existing)

            config = request_payload.get("config")
            if not isinstance(config, Mapping):
                config = {}
            config_payload: Dict[str, Any] = dict(config)

            book_section = payload.get("book")
            if isinstance(book_section, Mapping):
                title = _normalize_text(book_section.get("title"))
                author = _normalize_text(book_section.get("author"))
                year = _normalize_text(book_section.get("year"))
                summary = _normalize_text(book_section.get("summary"))
                isbn = _normalize_isbn(book_section.get("isbn")) or _normalize_isbn(payload.get("query", {}).get("isbn") if isinstance(payload.get("query"), Mapping) else None)
                cover_url = _normalize_text(book_section.get("cover_url"))
                cover_file = _normalize_text(book_section.get("cover_file"))

                if title:
                    book_metadata["book_title"] = title
                    config_payload["book_title"] = title
                if author:
                    book_metadata["book_author"] = author
                    config_payload["book_author"] = author
                if year:
                    book_metadata["book_year"] = year
                    config_payload["book_year"] = year
                if summary:
                    book_metadata["book_summary"] = summary
                    config_payload["book_summary"] = summary
                if isbn:
                    book_metadata["isbn"] = isbn
                    book_metadata["book_isbn"] = isbn
                if cover_url:
                    book_metadata["cover_url"] = cover_url
                if cover_file:
                    book_metadata["book_cover_file"] = cover_file
                    config_payload["book_cover_file"] = cover_file

                # OpenLibrary-specific fields
                openlibrary_work_key = _normalize_text(book_section.get("openlibrary_work_key"))
                openlibrary_work_url = _normalize_text(book_section.get("openlibrary_work_url"))
                openlibrary_book_key = _normalize_text(book_section.get("openlibrary_book_key"))
                openlibrary_book_url = _normalize_text(book_section.get("openlibrary_book_url"))
                if openlibrary_work_key:
                    book_metadata["openlibrary_work_key"] = openlibrary_work_key
                if openlibrary_work_url:
                    book_metadata["openlibrary_work_url"] = openlibrary_work_url
                if openlibrary_book_key:
                    book_metadata["openlibrary_book_key"] = openlibrary_book_key
                if openlibrary_book_url:
                    book_metadata["openlibrary_book_url"] = openlibrary_book_url

                # Google Books-specific fields
                google_books_id = _normalize_text(book_section.get("google_books_id"))
                if google_books_id:
                    book_metadata["google_books_id"] = google_books_id

            job_label = payload.get("job_label")
            if isinstance(job_label, str) and job_label.strip():
                book_metadata["job_label"] = job_label.strip()

            queried_at = payload.get("queried_at")
            provider = payload.get("provider", "openlibrary")
            if isinstance(queried_at, str) and queried_at.strip():
                # Store provider-specific timestamp
                if provider == "google_books":
                    book_metadata["google_books_queried_at"] = queried_at.strip()
                else:
                    book_metadata["openlibrary_queried_at"] = queried_at.strip()
                # Also store generic timestamp
                book_metadata["metadata_queried_at"] = queried_at.strip()

            book_metadata["book_metadata_lookup"] = dict(payload)

            inputs["book_metadata"] = book_metadata
            request_payload["inputs"] = inputs
            request_payload["config"] = config_payload

            job.request_payload = request_payload
            job.resume_context = copy.deepcopy(request_payload)

            if job.request is not None:
                job.request.inputs.book_metadata = PipelineMetadata.from_mapping(book_metadata)
                try:
                    if title:
                        job.request.config["book_title"] = title
                    if author:
                        job.request.config["book_author"] = author
                    if year:
                        job.request.config["book_year"] = year
                    if summary:
                        job.request.config["book_summary"] = summary
                    if cover_file:
                        job.request.config["book_cover_file"] = cover_file
                except Exception:
                    pass

            if isinstance(job.result_payload, Mapping):
                result_payload = dict(job.result_payload)
                result_payload["book_metadata_lookup"] = dict(payload)
                result_book = result_payload.get("book_metadata")
                if isinstance(result_book, Mapping):
                    merged = dict(result_book)
                    merged.update(book_metadata)
                    result_payload["book_metadata"] = merged
                else:
                    result_payload["book_metadata"] = dict(book_metadata)
                job.result_payload = result_payload

            if job.result is not None:
                try:
                    job.result.metadata.update(dict(book_metadata))
                except Exception:
                    pass

        self._job_manager.mutate_job(job_id, _mutate, user_id=user_id, user_role=user_role)


__all__ = ["BookMetadataService", "OpenLibraryClient", "BookLookupQuery"]
