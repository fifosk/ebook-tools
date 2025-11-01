"""Database-oriented helpers for library synchronization."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Tuple

from modules import logging_manager
from modules.library.library_models import LibraryEntry
from modules.services.job_manager import PipelineJobManager, PipelineJobTransitionError

from conf.sync_config import UNKNOWN_AUTHOR, UNKNOWN_GENRE

from . import utils

LOGGER = logging_manager.get_logger().getChild("library.sync.db")


def remove_from_job_queue(job_manager: Optional[PipelineJobManager], job_id: str) -> None:
    """Best-effort removal of a job from the pipeline queue."""

    if job_manager is None:
        return
    try:
        job_manager.delete_job(job_id, user_role="admin")
    except KeyError:
        LOGGER.debug("Job %s already absent from job queue storage; skipping removal", job_id)
    except PipelineJobTransitionError as exc:
        LOGGER.warning(
            "Failed to remove job %s from queue due to transition error: %s",
            job_id,
            exc,
        )
    except ValueError as exc:
        LOGGER.warning("Unable to remove job %s from queue: %s", job_id, exc)


def search_entries(
    repository,
    *,
    query: Optional[str],
    filters: Mapping[str, Optional[str]],
    limit: int,
    offset: int,
    sort_desc: bool,
    view: str,
    serializer: Callable[[LibraryEntry], Dict[str, Any]],
) -> Tuple[int, List[LibraryEntry], Optional[List[Dict[str, Any]]]]:
    """Execute a search against the repository with grouping support."""

    normalized_filters = utils.compact_filters(dict(filters))
    total = repository.count_entries(query=query, filters=normalized_filters)
    items = repository.list_entries(
        query=query,
        filters=normalized_filters,
        limit=limit,
        offset=offset,
        sort_desc=sort_desc,
    )
    groups = build_groups(items, view=view, serializer=serializer)
    return total, items, groups


def reindex_from_fs(
    library_root: Path,
    repository,
    *,
    load_metadata: Callable[[Path], Dict[str, Any]],
    build_entry: Callable[[Mapping[str, Any], Path], LibraryEntry],
) -> int:
    """Rebuild the repository index by scanning the filesystem."""

    items: List[LibraryEntry] = []
    state_dir = repository.db_path.parent
    for metadata_file in library_root.rglob("job.json"):
        if metadata_file.parent.name != "metadata":
            continue
        if state_dir in metadata_file.parents:
            continue
        job_root = metadata_file.parent.parent
        try:
            metadata = load_metadata(job_root)
        except FileNotFoundError:
            continue
        job_id = str(metadata.get("job_id") or "").strip()
        if not job_id:
            continue
        items.append(build_entry(metadata, job_root))

    repository.replace_entries(items)
    return len(items)


def build_groups(
    items: Iterable[LibraryEntry],
    *,
    view: str,
    serializer: Callable[[LibraryEntry], Dict[str, Any]],
) -> Optional[List[Dict[str, Any]]]:
    """Return grouped payloads for supported views."""

    if view == "flat":
        return None
    if view == "by_author":
        return _group_by_author(items, serializer)
    if view == "by_genre":
        return _group_by_genre(items, serializer)
    if view == "by_language":
        return _group_by_language(items, serializer)
    return None


def _group_by_author(
    items: Iterable[LibraryEntry],
    serializer: Callable[[LibraryEntry], Dict[str, Any]],
) -> List[Dict[str, Any]]:
    by_author: Dict[str, Dict[str, Dict[str, List[LibraryEntry]]]] = {}
    for item in items:
        author_label = item.author or UNKNOWN_AUTHOR.replace("_", " ")
        author_bucket = by_author.setdefault(author_label, {})
        book_label = item.book_title or "Untitled Book"
        book_bucket = author_bucket.setdefault(book_label, {})
        language_bucket = book_bucket.setdefault(item.language, [])
        language_bucket.append(item)

    result: List[Dict[str, Any]] = []
    for author_label in sorted(by_author):
        books_payload: List[Dict[str, Any]] = []
        for book_label in sorted(by_author[author_label]):
            language_payload: List[Dict[str, Any]] = []
            for language_label, entries in sorted(by_author[author_label][book_label].items()):
                sorted_entries = sorted(entries, key=lambda entry: entry.updated_at, reverse=True)
                language_payload.append(
                    {
                        "language": language_label,
                        "items": [serializer(entry) for entry in sorted_entries],
                    }
                )
            books_payload.append({"bookTitle": book_label, "languages": language_payload})
        result.append({"author": author_label, "books": books_payload})
    return result


def _group_by_genre(
    items: Iterable[LibraryEntry],
    serializer: Callable[[LibraryEntry], Dict[str, Any]],
) -> List[Dict[str, Any]]:
    by_genre: Dict[str, Dict[str, Dict[str, List[LibraryEntry]]]] = {}
    for item in items:
        genre_label = item.genre or UNKNOWN_GENRE
        genre_bucket = by_genre.setdefault(genre_label, {})
        author_label = item.author or UNKNOWN_AUTHOR.replace("_", " ")
        author_bucket = genre_bucket.setdefault(author_label, {})
        book_label = item.book_title or "Untitled Book"
        book_bucket = author_bucket.setdefault(book_label, [])
        book_bucket.append(item)

    result: List[Dict[str, Any]] = []
    for genre_label in sorted(by_genre):
        authors_payload: List[Dict[str, Any]] = []
        for author_label in sorted(by_genre[genre_label]):
            books_payload: List[Dict[str, Any]] = []
            for book_label, entries in sorted(by_genre[genre_label][author_label].items()):
                sorted_entries = sorted(entries, key=lambda entry: entry.updated_at, reverse=True)
                books_payload.append(
                    {
                        "bookTitle": book_label,
                        "items": [serializer(entry) for entry in sorted_entries],
                    }
                )
            authors_payload.append({"author": author_label, "books": books_payload})
        result.append({"genre": genre_label, "authors": authors_payload})
    return result


def _group_by_language(
    items: Iterable[LibraryEntry],
    serializer: Callable[[LibraryEntry], Dict[str, Any]],
) -> List[Dict[str, Any]]:
    by_language: Dict[str, Dict[str, List[LibraryEntry]]] = {}
    for item in items:
        language_label = item.language
        language_bucket = by_language.setdefault(language_label, {})
        author_label = item.author or UNKNOWN_AUTHOR.replace("_", " ")
        author_bucket = language_bucket.setdefault(author_label, [])
        author_bucket.append(item)

    result: List[Dict[str, Any]] = []
    for language_label in sorted(by_language):
        authors_payload: List[Dict[str, Any]] = []
        for author_label, author_entries in sorted(by_language[language_label].items()):
            books_group: Dict[str, List[LibraryEntry]] = {}
            for entry in author_entries:
                book_label = entry.book_title or "Untitled Book"
                books_group.setdefault(book_label, []).append(entry)
            books_payload: List[Dict[str, Any]] = []
            for book_label, entries in sorted(books_group.items()):
                sorted_entries = sorted(entries, key=lambda entry: entry.updated_at, reverse=True)
                books_payload.append(
                    {
                        "bookTitle": book_label,
                        "items": [serializer(entry) for entry in sorted_entries],
                    }
                )
            authors_payload.append({"author": author_label, "books": books_payload})
        result.append({"language": language_label, "authors": authors_payload})
    return result


__all__ = [
    "build_groups",
    "reindex_from_fs",
    "remove_from_job_queue",
    "search_entries",
]
