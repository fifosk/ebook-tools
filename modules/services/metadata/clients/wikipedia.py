"""Wikipedia/Wikidata API client for fallback metadata lookup."""

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

logger = log_mgr.get_logger().getChild("services.metadata.clients.wikipedia")

_WIKIPEDIA_API = "https://en.wikipedia.org/api/rest_v1"
_WIKIDATA_API = "https://www.wikidata.org/w/api.php"

_SUMMARY_MAX_CHARS = 600


def _normalize_text(value: Any) -> Optional[str]:
    """Normalize a string value."""
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


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


class WikipediaClient(BaseMetadataClient):
    """Wikipedia/Wikidata API client for fallback metadata.

    Uses the public Wikipedia REST API and Wikidata API.
    No authentication required.
    """

    name = MetadataSource.WIKIPEDIA
    supported_types = (MediaType.BOOK, MediaType.MOVIE, MediaType.TV_SERIES)
    requires_api_key = False

    def __init__(
        self,
        *,
        session: Optional[requests.Session] = None,
        api_key: Optional[str] = None,
        timeout_seconds: float = 10.0,
    ) -> None:
        super().__init__(session=session, api_key=api_key, timeout_seconds=timeout_seconds)

    def lookup(
        self,
        query: LookupQuery,
        options: LookupOptions,
    ) -> Optional[UnifiedMetadataResult]:
        """Look up metadata from Wikipedia."""
        if query.media_type == MediaType.BOOK:
            return self._lookup_book(query, options)
        elif query.media_type == MediaType.MOVIE:
            return self._lookup_movie(query, options)
        elif query.media_type == MediaType.TV_SERIES:
            return self._lookup_tv_series(query, options)
        return None

    def _lookup_book(
        self,
        query: LookupQuery,
        options: LookupOptions,
    ) -> Optional[UnifiedMetadataResult]:
        """Look up book on Wikipedia."""
        title = query.title
        if not title:
            return None

        # Try with "(novel)" suffix first for disambiguation
        search_terms = [
            f"{title} (novel)",
            f"{title} (book)",
            title,
        ]
        if query.author:
            search_terms.insert(0, f"{title} {query.author}")

        for term in search_terms:
            result = self._get_page_summary(term, options.timeout_seconds)
            if result:
                return self._parse_summary(result, query, MediaType.BOOK, options)

        return None

    def _lookup_movie(
        self,
        query: LookupQuery,
        options: LookupOptions,
    ) -> Optional[UnifiedMetadataResult]:
        """Look up movie on Wikipedia."""
        title = query.movie_title or query.title
        if not title:
            return None

        # Try with year and "(film)" suffix for disambiguation
        search_terms = []
        if query.year:
            search_terms.append(f"{title} ({query.year} film)")
        search_terms.extend([
            f"{title} (film)",
            f"{title} (movie)",
            title,
        ])

        for term in search_terms:
            result = self._get_page_summary(term, options.timeout_seconds)
            if result:
                return self._parse_summary(result, query, MediaType.MOVIE, options)

        return None

    def _lookup_tv_series(
        self,
        query: LookupQuery,
        options: LookupOptions,
    ) -> Optional[UnifiedMetadataResult]:
        """Look up TV series on Wikipedia."""
        title = query.series_name or query.title
        if not title:
            return None

        # Try with "(TV series)" suffix for disambiguation
        search_terms = [
            f"{title} (TV series)",
            f"{title} (television series)",
            f"{title} (TV show)",
            title,
        ]

        for term in search_terms:
            result = self._get_page_summary(term, options.timeout_seconds)
            if result:
                return self._parse_summary(result, query, MediaType.TV_SERIES, options)

        return None

    def _get_page_summary(
        self,
        title: str,
        timeout: float,
    ) -> Optional[Dict[str, Any]]:
        """Get Wikipedia page summary."""
        # URL-encode the title
        encoded_title = title.replace(" ", "_")

        try:
            response = self._session.get(
                f"{_WIKIPEDIA_API}/page/summary/{encoded_title}",
                headers={
                    "Accept": "application/json",
                    "User-Agent": "ebook-tools/1.0 (metadata lookup)",
                },
                timeout=timeout,
            )

            if response.status_code == 404:
                return None

            response.raise_for_status()
            data = response.json()

            # Skip disambiguation pages
            if data.get("type") == "disambiguation":
                return None

            return data if isinstance(data, dict) else None

        except Exception as exc:
            logger.debug("Wikipedia API error for '%s': %s", title, exc)
            return None

    def _parse_summary(
        self,
        data: Dict[str, Any],
        query: LookupQuery,
        media_type: MediaType,
        options: LookupOptions,
    ) -> UnifiedMetadataResult:
        """Parse Wikipedia summary into unified result."""
        # Extract title
        title = _normalize_text(data.get("title"))
        if not title:
            title = query.title or query.series_name or query.movie_title or "Unknown"

        # Clean up title (remove disambiguation suffix)
        title_clean = re.sub(r"\s*\([^)]+\)\s*$", "", title).strip() or title

        # Extract summary
        summary = _normalize_text(data.get("extract"))
        if summary:
            summary = _strip_html(summary)
            summary = _limit_summary_length(summary)

        # Extract thumbnail
        thumbnail = data.get("thumbnail", {})
        cover_url = None
        if isinstance(thumbnail, Mapping):
            cover_url = _normalize_text(thumbnail.get("source"))

        # Try to extract year from description
        description = _normalize_text(data.get("description")) or ""
        year = None
        # Look for year patterns like "2010 film" or "1984 novel"
        year_match = re.search(r"(\d{4})\s+(?:film|novel|book|series|show)", description.lower())
        if year_match:
            year = int(year_match.group(1))

        # Extract Wikidata QID if available
        wikibase_item = data.get("wikibase_item")
        wikidata_qid = _normalize_text(wikibase_item)

        source_ids = SourceIds(wikidata_qid=wikidata_qid)

        # Try to get more structured data from Wikidata
        genres: List[str] = []
        if wikidata_qid:
            wikidata_info = self._get_wikidata_info(wikidata_qid, options.timeout_seconds)
            if wikidata_info:
                # Merge additional info
                if not year and wikidata_info.get("year"):
                    year = wikidata_info["year"]
                if not cover_url and wikidata_info.get("image"):
                    cover_url = wikidata_info["image"]
                if wikidata_info.get("imdb_id"):
                    source_ids = SourceIds(
                        wikidata_qid=wikidata_qid,
                        imdb_id=wikidata_info["imdb_id"],
                    )
                # Resolve genre QIDs to labels
                genre_qids = wikidata_info.get("genre_qids", [])
                if genre_qids:
                    genres = self._resolve_genre_qids(genre_qids, options.timeout_seconds)

        return UnifiedMetadataResult(
            title=title_clean,
            type=media_type,
            year=year,
            genres=genres,  # Now populated from Wikidata if available
            summary=summary,
            cover_url=cover_url,
            source_ids=source_ids,
            confidence=ConfidenceLevel.LOW,  # Fallback source
            primary_source=MetadataSource.WIKIPEDIA,
            contributing_sources=[MetadataSource.WIKIPEDIA],
            queried_at=datetime.now(timezone.utc),
            raw_responses={"wikipedia": data} if options.include_raw_responses else {},
        )

    def _get_wikidata_info(
        self,
        qid: str,
        timeout: float,
    ) -> Optional[Dict[str, Any]]:
        """Get additional info from Wikidata."""
        if not qid or not qid.startswith("Q"):
            return None

        try:
            response = self._session.get(
                _WIKIDATA_API,
                params={
                    "action": "wbgetentities",
                    "ids": qid,
                    "format": "json",
                    "props": "claims",
                },
                headers={"User-Agent": "ebook-tools/1.0 (metadata lookup)"},
                timeout=timeout,
            )
            response.raise_for_status()
            data = response.json()

            entities = data.get("entities", {})
            entity = entities.get(qid, {})
            claims = entity.get("claims", {})

            result: Dict[str, Any] = {}

            # P577 = publication date
            pub_dates = claims.get("P577", [])
            if pub_dates and isinstance(pub_dates, list):
                for claim in pub_dates:
                    mainsnak = claim.get("mainsnak", {})
                    datavalue = mainsnak.get("datavalue", {})
                    value = datavalue.get("value", {})
                    time = value.get("time")
                    if time:
                        match = re.search(r"(\d{4})", str(time))
                        if match:
                            result["year"] = int(match.group(1))
                            break

            # P345 = IMDb ID
            imdb_ids = claims.get("P345", [])
            if imdb_ids and isinstance(imdb_ids, list):
                for claim in imdb_ids:
                    mainsnak = claim.get("mainsnak", {})
                    datavalue = mainsnak.get("datavalue", {})
                    imdb_id = datavalue.get("value")
                    if imdb_id and isinstance(imdb_id, str):
                        result["imdb_id"] = imdb_id
                        break

            # P18 = image
            images = claims.get("P18", [])
            if images and isinstance(images, list):
                for claim in images:
                    mainsnak = claim.get("mainsnak", {})
                    datavalue = mainsnak.get("datavalue", {})
                    filename = datavalue.get("value")
                    if filename and isinstance(filename, str):
                        # Construct Wikimedia Commons URL
                        import hashlib

                        filename = filename.replace(" ", "_")
                        md5 = hashlib.md5(filename.encode()).hexdigest()
                        result["image"] = (
                            f"https://upload.wikimedia.org/wikipedia/commons/"
                            f"{md5[0]}/{md5[0:2]}/{filename}"
                        )
                        break

            # P136 = genre (returns QIDs that need label resolution)
            genres = claims.get("P136", [])
            if genres and isinstance(genres, list):
                genre_qids = []
                for claim in genres:
                    mainsnak = claim.get("mainsnak", {})
                    datavalue = mainsnak.get("datavalue", {})
                    value = datavalue.get("value", {})
                    genre_qid = value.get("id")
                    if genre_qid and isinstance(genre_qid, str):
                        genre_qids.append(genre_qid)
                if genre_qids:
                    result["genre_qids"] = genre_qids[:10]

            return result if result else None

        except Exception as exc:
            logger.debug("Wikidata API error for '%s': %s", qid, exc)
            return None

    def _resolve_genre_qids(
        self,
        qids: List[str],
        timeout: float,
    ) -> List[str]:
        """Resolve Wikidata QIDs to genre labels."""
        if not qids:
            return []

        try:
            response = self._session.get(
                _WIKIDATA_API,
                params={
                    "action": "wbgetentities",
                    "ids": "|".join(qids),
                    "format": "json",
                    "props": "labels",
                    "languages": "en",
                },
                headers={"User-Agent": "ebook-tools/1.0 (metadata lookup)"},
                timeout=timeout,
            )
            response.raise_for_status()
            data = response.json()

            genres: List[str] = []
            entities = data.get("entities", {})
            for qid in qids:
                entity = entities.get(qid, {})
                labels = entity.get("labels", {})
                en_label = labels.get("en", {})
                label = _normalize_text(en_label.get("value"))
                if label:
                    genres.append(label)

            return genres

        except Exception as exc:
            logger.debug("Failed to resolve genre QIDs: %s", exc)
            return []


__all__ = ["WikipediaClient"]
