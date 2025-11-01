"""High-level coordination for the Library feature."""

from __future__ import annotations

import itertools
import json
import re
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Literal, Mapping, Optional, Tuple
from urllib.parse import quote

from modules import logging_manager, metadata_manager
from modules.fsutils import AtomicMoveError, ChecksumMismatchError, DirectoryLock, atomic_move
from modules.services.file_locator import FileLocator
from modules.services.job_manager import PipelineJobManager, PipelineJobTransitionError

from .sqlite_indexer import LibraryIndexer, LibraryItem

LOGGER = logging_manager.get_logger().getChild("library.service")

_SANITIZE_PATTERN = re.compile(r"[^\w.\- ]+")
_UNKNOWN_AUTHOR = "Unknown_Author"
_UNTITLED_BOOK = "Untitled_Book"
_UNKNOWN_LANGUAGE = "unknown"
_UNKNOWN_GENRE = "Unknown Genre"


def _has_generated_media(payload: Mapping[str, Any]) -> bool:
    """Return True when ``payload`` describes at least one generated media file."""

    files_section = payload.get("files")
    if isinstance(files_section, list):
        for entry in files_section:
            if isinstance(entry, Mapping) and entry:
                return True
    elif isinstance(files_section, Mapping):
        for entry in files_section.values():
            if isinstance(entry, Mapping) and entry:
                return True
            if isinstance(entry, str) and entry.strip():
                return True

    chunks_section = payload.get("chunks")
    if isinstance(chunks_section, list):
        for chunk in chunks_section:
            if not isinstance(chunk, Mapping):
                continue
            if any(
                chunk.get(key)
                for key in ("chunk_id", "range_fragment")
            ) or any(
                chunk.get(key) is not None
                for key in ("start_sentence", "end_sentence")
            ):
                return True
            files = chunk.get("files")
            if isinstance(files, list):
                for entry in files:
                    if isinstance(entry, Mapping) and entry:
                        return True
            elif isinstance(files, Mapping):
                for entry in files.values():
                    if isinstance(entry, Mapping) and entry:
                        return True
                    if isinstance(entry, str) and entry.strip():
                        return True
    return False

_MEDIA_EXTENSIONS = {
    ".mp3",
    ".wav",
    ".aac",
    ".flac",
    ".ogg",
    ".m4a",
    ".mp4",
    ".mkv",
    ".mov",
    ".webm",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".html",
    ".htm",
    ".md",
    ".pdf",
    ".json",
    ".jsonl",
    ".srt",
    ".vtt",
    ".doc",
    ".docx",
    ".rtf",
}

_AUDIO_SUFFIXES = {
    ".mp3",
    ".wav",
    ".aac",
    ".flac",
    ".ogg",
    ".m4a",
}

_VIDEO_SUFFIXES = {
    ".mp4",
    ".mkv",
    ".mov",
    ".webm",
}

LibraryStatus = Literal["finished", "paused"]


class LibraryError(RuntimeError):
    """Base class for library-related failures."""


class LibraryConflictError(LibraryError):
    """Raised when a conflicting record already exists."""


class LibraryNotFoundError(LibraryError):
    """Raised when an expected job does not exist."""


@dataclass(frozen=True)
class LibrarySearchResult:
    """Structured response returned from library searches."""

    total: int
    page: int
    limit: int
    view: str
    items: List[LibraryItem]
    groups: Optional[List[Dict[str, Any]]]


class LibraryService:
    """Coordinate filesystem operations and index maintenance for the Library."""

    def __init__(
        self,
        *,
        library_root: Path,
        file_locator: FileLocator,
        indexer: Optional[LibraryIndexer] = None,
        job_manager: Optional[PipelineJobManager] = None,
    ) -> None:
        self._library_root = Path(library_root)
        self._library_root.mkdir(parents=True, exist_ok=True)
        self._locator = file_locator
        self._indexer = indexer or LibraryIndexer(self._library_root)
        self._job_manager = job_manager
        self._library_job_cache: Dict[str, Path] = {}
        self._missing_job_cache: set[str] = set()
        # Prime the database and ensure migrations run up-front.
        with self._indexer.connect():
            pass

    @property
    def library_root(self) -> Path:
        return self._library_root

    def move_to_library(
        self,
        job_id: str,
        *,
        status_override: Optional[str] = None,
        force: bool = False,
    ) -> LibraryItem:
        """Move ``job_id`` from the queue storage into the Library."""

        job_root = self._locator.job_root(job_id)
        if not job_root.exists():
            raise LibraryNotFoundError(f"Job {job_id} not found in queue storage")

        with DirectoryLock(job_root) as lock:
            metadata = self._load_metadata(job_root)
            normalized_status = self._normalize_status(status_override or metadata.get("status"))
            now = self._current_timestamp()
            media_ready = self._is_media_complete(metadata, normalized_status, job_root)
            if normalized_status == "paused" and not media_ready and not force:
                raise LibraryError(
                    "Job media is still finalizing; wait for generation to complete or retry with force."
                )
            if normalized_status == "finished":
                media_ready = True
            metadata.setdefault("job_id", job_id)
            metadata.setdefault("created_at", now)
            metadata["status"] = normalized_status
            metadata["updated_at"] = now
            metadata["media_completed"] = bool(media_ready)

            target_path = self._resolve_library_path(metadata, job_id)

            existing_item = self._indexer.get(job_id)
            if target_path.exists():
                if not force:
                    raise LibraryConflictError(
                        f"Library path {target_path} already exists for job {job_id}"
                    )
                LOGGER.info(
                    "Removing existing library path for job %s due to force move",
                    job_id,
                )
                shutil.rmtree(target_path, ignore_errors=True)
            if existing_item and not force:
                raise LibraryConflictError(f"Job {job_id} already indexed in library")

            try:
                atomic_move(job_root, target_path)
            except (AtomicMoveError, ChecksumMismatchError) as exc:
                raise LibraryError(f"Failed to move job {job_id} into library: {exc}") from exc

            lock.relocate(target_path)

            source_relative = self._ensure_source_material(target_path, metadata)
            if source_relative:
                self._apply_source_reference(metadata, source_relative)

            isbn_value = self._extract_isbn(metadata)
            if isbn_value:
                self._apply_isbn(metadata, isbn_value)

            metadata["generated_files"] = self._retarget_generated_files(
                metadata.get("generated_files"),
                job_id,
                target_path,
            )
            self._write_metadata(target_path, metadata)

        library_item = self._build_item(metadata, target_path)
        self._indexer.upsert(library_item)
        self._remove_from_job_queue(job_id)
        return library_item

    def _remove_from_job_queue(self, job_id: str) -> None:
        if self._job_manager is None:
            return
        try:
            self._job_manager.delete_job(job_id, user_role="admin")
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

    def remove_media(self, job_id: str) -> Tuple[Optional[LibraryItem], int]:
        """Remove generated media files for ``job_id`` without deleting metadata."""

        item = self._indexer.get(job_id)
        if item:
            job_root = Path(item.library_path)
            is_library = True
        else:
            job_root = self._locator.job_root(job_id)
            is_library = False

        if not job_root.exists():
            raise LibraryNotFoundError(f"Job {job_id} does not exist on disk")

        with DirectoryLock(job_root):
            metadata = self._load_metadata(job_root)
            removed = self._purge_media_files(job_root)
            metadata["updated_at"] = self._current_timestamp()
            metadata["media_completed"] = False
            metadata["generated_files"] = self._retarget_generated_files(
                metadata.get("generated_files"),
                job_id,
                job_root,
            )
            self._write_metadata(job_root, metadata)

        if is_library:
            updated_item = self._build_item(metadata, job_root)
            self._indexer.upsert(updated_item)
            return updated_item, removed

        return None, removed

    def remove_entry(self, job_id: str) -> None:
        """Remove ``job_id`` from the Library entirely."""

        item = self._indexer.get(job_id)
        if not item:
            raise LibraryNotFoundError(f"Job {job_id} is not stored in the library")

        job_root = Path(item.library_path)
        with DirectoryLock(job_root):
            if job_root.exists():
                shutil.rmtree(job_root, ignore_errors=True)

        self._indexer.delete(job_id)

    def update_metadata(
        self,
        job_id: str,
        *,
        title: Optional[str] = None,
        author: Optional[str] = None,
        genre: Optional[str] = None,
        language: Optional[str] = None,
        isbn: Optional[str] = None,
    ) -> LibraryItem:
        """Persist user-supplied metadata changes for ``job_id``."""

        item = self._indexer.get(job_id)
        if not item:
            raise LibraryNotFoundError(f"Job {job_id} is not stored in the library")

        job_root = Path(item.library_path)
        if not job_root.exists():
            raise LibraryNotFoundError(f"Job {job_id} is missing from the library filesystem")

        normalized_title = (title or item.book_title or "").strip() or item.book_title
        normalized_author = (author or item.author or "").strip() or item.author
        if genre is not None:
            if isinstance(genre, str):
                normalized_genre = genre.strip() or None
            else:
                normalized_genre = None
        else:
            normalized_genre = item.genre
        normalized_language = (language or item.language or "").strip() or item.language

        now = self._current_timestamp()

        with DirectoryLock(job_root) as lock:
            metadata = self._load_metadata(job_root)
            metadata["book_title"] = normalized_title
            metadata["author"] = normalized_author
            metadata["genre"] = normalized_genre
            metadata["language"] = normalized_language
            metadata["updated_at"] = now

            book_metadata_raw = metadata.get("book_metadata")
            book_metadata: Dict[str, Any]
            if isinstance(book_metadata_raw, Mapping):
                book_metadata = dict(book_metadata_raw)
            else:
                book_metadata = {}
            book_metadata["book_title"] = normalized_title
            book_metadata["book_author"] = normalized_author
            if normalized_genre:
                book_metadata["book_genre"] = normalized_genre
            elif "book_genre" in book_metadata:
                book_metadata.pop("book_genre", None)
            metadata["book_metadata"] = book_metadata

            if isbn is not None:
                cleaned_isbn = isbn.strip() if isinstance(isbn, str) else ""
                if cleaned_isbn:
                    normalized_isbn = self._normalize_isbn(cleaned_isbn)
                    if normalized_isbn is None:
                        raise LibraryError("ISBN must contain 10 or 13 digits (optionally including X)")
                    self._apply_isbn(metadata, normalized_isbn)
                    book_metadata["isbn"] = normalized_isbn
                    book_metadata["book_isbn"] = normalized_isbn
                    metadata["isbn"] = normalized_isbn
                else:
                    metadata.pop("isbn", None)
                    book_metadata.pop("isbn", None)
                    book_metadata.pop("book_isbn", None)
            else:
                existing_isbn = self._extract_isbn(metadata)
                if existing_isbn:
                    book_metadata.setdefault("isbn", existing_isbn)
                    book_metadata.setdefault("book_isbn", existing_isbn)
                    metadata.setdefault("isbn", existing_isbn)

            target_path = self._resolve_library_path(metadata, job_id)
            current_resolved = job_root.resolve()
            target_resolved = target_path.resolve()

            if target_resolved != current_resolved:
                if target_resolved.exists():
                    raise LibraryConflictError(
                        f"Library path {target_resolved} already exists for job {job_id}"
                    )
                target_resolved.parent.mkdir(parents=True, exist_ok=True)
                try:
                    atomic_move(current_resolved, target_resolved)
                except (AtomicMoveError, ChecksumMismatchError) as exc:
                    raise LibraryError(f"Failed to relocate library entry: {exc}") from exc
                lock.relocate(target_resolved)
                job_root = target_resolved

            self._write_metadata(job_root, metadata)

        updated_item = self._build_item(metadata, job_root)
        self._indexer.upsert(updated_item)
        return updated_item

    def refresh_metadata(self, job_id: str) -> LibraryItem:
        """Recompute metadata for ``job_id`` using the shared metadata manager."""

        item = self._indexer.get(job_id)
        if not item:
            raise LibraryNotFoundError(f"Job {job_id} is not stored in the library")

        job_root = Path(item.library_path)
        if not job_root.exists():
            raise LibraryNotFoundError(f"Job {job_id} is missing from the library filesystem")

        with DirectoryLock(job_root):
            metadata = self._load_metadata(job_root)
            source_relative = self._ensure_source_material(job_root, metadata)
            if source_relative:
                self._apply_source_reference(metadata, source_relative)

            book_metadata_raw = metadata.get("book_metadata")
            existing_metadata: Dict[str, Optional[str]]
            if isinstance(book_metadata_raw, Mapping):
                existing_metadata = {
                    key: str(value) if isinstance(value, str) else None
                    for key, value in book_metadata_raw.items()
                }
            else:
                existing_metadata = {}

            epub_path = self._locate_input_epub(metadata, job_root)
            local_metadata: Dict[str, Optional[str]] = {}
            if epub_path is not None and epub_path.exists():
                try:
                    local_metadata = metadata_manager.infer_metadata(
                        str(epub_path),
                        existing_metadata=existing_metadata,
                        force_refresh=True,
                    )
                except Exception as exc:
                    raise LibraryError(f"Metadata refresh failed: {exc}") from exc

            isbn_value = self._extract_isbn(metadata)
            isbn_metadata: Dict[str, Optional[str]] = {}
            if isbn_value:
                try:
                    isbn_metadata = metadata_manager.fetch_metadata_from_isbn(isbn_value)
                except Exception as exc:  # pragma: no cover - defensive logging
                    LOGGER.debug(
                        "Unable to fetch ISBN metadata for job %s (%s): %s",
                        job_id,
                        isbn_value,
                        exc,
                    )

            if (epub_path is None or not (epub_path.exists() if epub_path else False)) and not isbn_metadata:
                raise LibraryError(
                    f"Unable to locate a source EPUB or ISBN metadata for job {job_id}; cannot refresh metadata"
                )

            updated_metadata = self._merge_metadata_payloads(existing_metadata, local_metadata, isbn_metadata)
            if isbn_value:
                updated_metadata["isbn"] = isbn_value

            metadata["book_metadata"] = dict(updated_metadata)

            if updated_metadata.get("book_title"):
                metadata["book_title"] = updated_metadata["book_title"]
            if updated_metadata.get("book_author"):
                metadata["author"] = updated_metadata["book_author"]
            if updated_metadata.get("book_language"):
                metadata["language"] = updated_metadata["book_language"] or metadata.get("language")
            if updated_metadata.get("book_genre"):
                metadata["genre"] = updated_metadata.get("book_genre")

            if source_relative:
                self._apply_source_reference(metadata, source_relative)

            if isbn_value:
                self._apply_isbn(metadata, isbn_value)

            cover_reference = updated_metadata.get("book_cover_file") or updated_metadata.get("job_cover_asset")
            cover_asset = self._mirror_cover_asset(job_root, cover_reference)
            if cover_asset:
                metadata["job_cover_asset"] = cover_asset
                updated_metadata["job_cover_asset"] = cover_asset
                updated_metadata["book_cover_file"] = cover_asset
            else:
                metadata.pop("job_cover_asset", None)
                updated_metadata.pop("job_cover_asset", None)
                if "book_cover_file" in updated_metadata and not updated_metadata["book_cover_file"]:
                    updated_metadata.pop("book_cover_file", None)

            try:
                metadata["book_metadata"] = dict(updated_metadata)
            except TypeError:
                metadata["book_metadata"] = dict(updated_metadata or {})

            metadata["updated_at"] = self._current_timestamp()
            self._write_metadata(job_root, metadata)

        refreshed_item = self._build_item(metadata, job_root)
        self._indexer.upsert(refreshed_item)
        return refreshed_item

    def reupload_source_from_path(self, job_id: str, source_path: Path) -> LibraryItem:
        """Replace the stored source file for ``job_id`` using an external path."""

        item = self._indexer.get(job_id)
        if not item:
            raise LibraryNotFoundError(f"Job {job_id} is not stored in the library")

        resolved_source = Path(source_path).expanduser()
        if not resolved_source.exists():
            raise LibraryError(f"Source file {resolved_source} does not exist")

        job_root = Path(item.library_path)
        if not job_root.exists():
            raise LibraryNotFoundError(f"Job {job_id} is missing from the library filesystem")

        with DirectoryLock(job_root):
            metadata = self._load_metadata(job_root)
            data_root = job_root / "data"
            data_root.mkdir(parents=True, exist_ok=True)

            sanitized_name = self._sanitize_source_filename(resolved_source.name)
            destination = self._next_source_candidate(data_root / sanitized_name)

            try:
                shutil.copy2(resolved_source, destination)
            except Exception as exc:
                raise LibraryError(f"Failed to store source file: {exc}") from exc

            for existing in data_root.iterdir():
                if existing == destination:
                    continue
                if existing.is_file() and existing.suffix.lower() in {".epub", ".pdf"}:
                    try:
                        existing.unlink()
                    except OSError:
                        LOGGER.debug("Unable to remove obsolete source file %s", existing, exc_info=True)

            source_relative = destination.relative_to(job_root).as_posix()
            self._apply_source_reference(metadata, source_relative)
            metadata["updated_at"] = self._current_timestamp()
            self._write_metadata(job_root, metadata)

        try:
            return self.refresh_metadata(job_id)
        except LibraryError as exc:
            LOGGER.warning(
                "Metadata refresh failed after source upload for %s: %s",
                job_id,
                exc,
            )
        except Exception as exc:  # pragma: no cover - defensive guard
            LOGGER.exception(
                "Unexpected failure refreshing metadata after source upload for %s",
                job_id,
            )

        # Fallback: return the item with updated source details even if refresh failed.
        fallback_metadata = self._load_metadata(job_root)
        fallback_item = self._build_item(fallback_metadata, job_root)
        self._indexer.upsert(fallback_item)
        return fallback_item

    def apply_isbn_metadata(self, job_id: str, isbn: str) -> LibraryItem:
        """Persist ``isbn`` for ``job_id`` and refresh metadata using remote lookups."""

        normalized = self._normalize_isbn(isbn)
        if not normalized:
            raise LibraryError("ISBN must contain 10 or 13 digits (optionally including X)")

        item = self._indexer.get(job_id)
        if not item:
            raise LibraryNotFoundError(f"Job {job_id} is not stored in the library")

        job_root = Path(item.library_path)
        if not job_root.exists():
            raise LibraryNotFoundError(f"Job {job_id} is missing from the library filesystem")

        with DirectoryLock(job_root):
            metadata = self._load_metadata(job_root)
            self._apply_isbn(metadata, normalized)
            metadata["updated_at"] = self._current_timestamp()
            self._write_metadata(job_root, metadata)

        return self.refresh_metadata(job_id)

    def lookup_isbn_metadata(self, isbn: str) -> Dict[str, Optional[str]]:
        """Return metadata fetched from public ISBN APIs without mutating state."""

        normalized = self._normalize_isbn(isbn)
        if not normalized:
            raise LibraryError("ISBN must contain 10 or 13 digits (optionally including X)")
        return metadata_manager.fetch_metadata_from_isbn(normalized)

    def search(
        self,
        *,
        query: Optional[str] = None,
        author: Optional[str] = None,
        book_title: Optional[str] = None,
        genre: Optional[str] = None,
        language: Optional[str] = None,
        status: Optional[str] = None,
        view: str = "flat",
        page: int = 1,
        limit: int = 25,
        sort: str = "updated_at_desc",
    ) -> LibrarySearchResult:
        """Query the Library index with optional filters and grouping."""

        normalized_page = max(1, page)
        normalized_limit = max(1, min(limit, 100))
        offset = (normalized_page - 1) * normalized_limit
        filters = {
            "author": author,
            "book_title": book_title,
            "genre": genre,
            "language": language,
            "status": status,
        }

        sort_desc = sort.lower() != "updated_at_asc"
        total = self._indexer.count(query=query, filters=_compact_filters(filters))
        items = self._indexer.search(
            query=query,
            filters=_compact_filters(filters),
            limit=normalized_limit,
            offset=offset,
            sort_desc=sort_desc,
        )
        groups = self._build_groups(items, view=view)
        return LibrarySearchResult(
            total=total,
            page=normalized_page,
            limit=normalized_limit,
            view=view,
            items=items,
            groups=groups,
        )

    def get_item(self, job_id: str) -> Optional[LibraryItem]:
        """Return the indexed ``LibraryItem`` for ``job_id`` if present."""

        if not job_id:
            return None
        if job_id in self._missing_job_cache:
            return None

        item = self._indexer.get(job_id)
        if item:
            try:
                self._library_job_cache[job_id] = Path(item.library_path)
            except Exception:
                pass
            return item

        cached_root = self._library_job_cache.get(job_id)
        if cached_root is not None:
            metadata_path = cached_root / "metadata" / "job.json"
            if metadata_path.exists():
                try:
                    metadata = self._load_metadata(cached_root)
                    recovered = self._build_item(metadata, cached_root)
                except (FileNotFoundError, LibraryError):
                    pass
                else:
                    self._indexer.upsert(recovered)
                    return recovered

        job_root = self._locate_job_root(job_id)
        if job_root is None:
            self._missing_job_cache.add(job_id)
            return None

        try:
            metadata = self._load_metadata(job_root)
            recovered = self._build_item(metadata, job_root)
        except (FileNotFoundError, LibraryError):
            self._missing_job_cache.add(job_id)
            return None

        self._library_job_cache[job_id] = job_root
        self._indexer.upsert(recovered)
        self._missing_job_cache.discard(job_id)
        return recovered

    def reindex_from_fs(self) -> int:
        """Scan the library filesystem and rebuild the SQLite index."""

        items: List[LibraryItem] = []
        state_dir = self._indexer.db_path.parent
        for metadata_file in self._library_root.rglob("job.json"):
            if metadata_file.parent.name != "metadata":
                continue
            if state_dir in metadata_file.parents:
                continue
            job_root = metadata_file.parent.parent
            try:
                metadata = self._load_metadata(job_root)
            except FileNotFoundError:
                continue
            job_id = str(metadata.get("job_id") or "").strip()
            if not job_id:
                continue
            items.append(self._build_item(metadata, job_root))

        self._indexer.replace_all(items)
        return len(items)

    def serialize_item(self, item: LibraryItem) -> Dict[str, Any]:
        """Return a JSON-serializable representation of ``item``."""

        payload = {
            "job_id": item.id,
            "author": item.author or "",
            "book_title": item.book_title or "",
            "genre": item.genre,
            "language": item.language,
            "status": item.status,
            "created_at": item.created_at,
            "updated_at": item.updated_at,
            "library_path": item.library_path,
            "cover_path": item.cover_path,
            "isbn": item.isbn,
            "source_path": item.source_path,
            "metadata": item.metadata,
        }
        metadata_payload = item.metadata if isinstance(item.metadata, dict) else {}
        media_completed = bool(metadata_payload.get("media_completed"))
        if not media_completed:
            generated = metadata_payload.get("generated_files")
            if isinstance(generated, Mapping):
                complete_flag = generated.get("complete")
                media_completed = bool(complete_flag) or _has_generated_media(generated)
        payload["media_completed"] = media_completed
        return payload

    def _build_groups(
        self,
        items: Iterable[LibraryItem],
        *,
        view: str,
    ) -> Optional[List[Dict[str, Any]]]:
        if view == "flat":
            return None
        serializer = self.serialize_item
        if view == "by_author":
            return _group_by_author(items, serializer)
        if view == "by_genre":
            return _group_by_genre(items, serializer)
        if view == "by_language":
            return _group_by_language(items, serializer)
        return None

    @staticmethod
    def _contains_media_files(job_root: Path) -> bool:
        metadata_dir = job_root / "metadata"
        media_root = job_root / "media"
        search_roots = [media_root] if media_root.exists() else [job_root]
        for root in search_roots:
            for path in root.rglob("*"):
                if not path.is_file():
                    continue
                if path.name == ".lock":
                    continue
                if metadata_dir in path.parents:
                    continue
                return True
        # Fallback to original extension-based scan if media directory missing
        for path in job_root.rglob("*"):
            if path.is_file() and path.suffix.lower() in _MEDIA_EXTENSIONS:
                if path.name == ".lock":
                    continue
                if metadata_dir in path.parents:
                    continue
                return True
        return False

    def _is_media_complete(self, metadata: Mapping[str, Any], status: str, job_root: Path) -> bool:
        normalized_status = str(status or "").strip().lower()
        if normalized_status in {"finished", "completed", "success"}:
            return True
        if bool(metadata.get("media_completed")):
            return True
        generated = metadata.get("generated_files")
        if isinstance(generated, Mapping):
            complete_flag = generated.get("complete")
            if isinstance(complete_flag, bool):
                return complete_flag
            if normalized_status == "paused" and _has_generated_media(generated):
                return True
        if normalized_status == "paused" and self._contains_media_files(job_root):
            return True
        return False

    def get_media(
        self,
        job_id: str,
    ) -> Tuple[Dict[str, List[Dict[str, Any]]], List[Dict[str, Any]], bool]:
        item = self._indexer.get(job_id)
        if not item:
            raise LibraryNotFoundError(f"Job {job_id} is not stored in the library")
        job_root = Path(item.library_path)
        metadata = self._load_metadata(job_root)
        generated = metadata.get("generated_files")
        media_map, chunk_records, generated_complete = self._serialize_media_entries(
            job_id,
            generated,
            job_root,
        )
        return media_map, chunk_records, bool(metadata.get("media_completed")) or generated_complete

    def _retarget_generated_files(self, payload: Any, job_id: str, job_root: Path) -> Any:
        if not isinstance(payload, Mapping):
            return payload
        updated: Dict[str, Any] = {}
        for key, value in payload.items():
            if key == "files":
                if isinstance(value, list):
                    updated[key] = [
                        self._retarget_media_entry(entry, job_id, job_root)
                        for entry in value
                        if isinstance(entry, Mapping)
                    ]
                elif isinstance(value, Mapping):
                    updated[key] = {
                        name: self._retarget_media_entry(entry, job_id, job_root)
                        for name, entry in value.items()
                        if isinstance(entry, Mapping)
                    }
                else:
                    updated[key] = value
            elif key == "chunks":
                if isinstance(value, list):
                    updated[key] = [
                        self._retarget_chunk_entry(chunk, job_id, job_root)
                        for chunk in value
                        if isinstance(chunk, Mapping)
                    ]
                elif isinstance(value, Mapping):
                    updated[key] = {
                        name: self._retarget_chunk_entry(chunk, job_id, job_root)
                        for name, chunk in value.items()
                        if isinstance(chunk, Mapping)
                    }
                else:
                    updated[key] = value
            else:
                updated[key] = value
        return updated

    def _retarget_chunk_entry(self, chunk: Mapping[str, Any], job_id: str, job_root: Path) -> Dict[str, Any]:
        payload = dict(chunk)
        files = chunk.get("files")
        if isinstance(files, list):
            payload["files"] = [
                self._retarget_media_entry(entry, job_id, job_root)
                for entry in files
                if isinstance(entry, Mapping)
            ]
        elif isinstance(files, Mapping):
            payload["files"] = {
                name: self._retarget_media_entry(entry, job_id, job_root)
                for name, entry in files.items()
                if isinstance(entry, Mapping)
            }
        return payload

    def _retarget_media_entry(
        self,
        entry: Mapping[str, Any],
        job_id: str,
        job_root: Path,
    ) -> Dict[str, Any]:
        payload = dict(entry)
        job_root = job_root.resolve()

        def normalize_relative(raw: str) -> Optional[Path]:
            text = raw.strip()
            if not text:
                return None
            candidate = Path(text.replace("\\", "/"))
            if candidate.is_absolute():
                try:
                    candidate = candidate.relative_to(job_root)
                except ValueError:
                    parts = [part for part in candidate.parts if part not in {"", "."}]
                    if not parts:
                        return None
                    if "media" in parts:
                        index = parts.index("media")
                        candidate = Path(*parts[index:])
                    else:
                        candidate = Path(*parts[-1:])
            return candidate

        relative_path: Optional[Path] = None
        absolute_path: Optional[Path] = None

        relative_value = entry.get("relative_path")
        if isinstance(relative_value, str):
            relative_path = normalize_relative(relative_value)

        path_value = entry.get("path")
        if isinstance(path_value, str) and path_value.strip():
            path_candidate = Path(path_value.strip()).expanduser()
            if not path_candidate.is_absolute():
                path_candidate = (job_root / path_candidate).resolve()
            else:
                try:
                    path_candidate = path_candidate.resolve()
                except OSError:
                    pass
            absolute_path = path_candidate
            if relative_path is None:
                try:
                    relative_path = path_candidate.relative_to(job_root)
                except ValueError:
                    relative_path = None

        if relative_path is not None:
            normalized_relative = Path(relative_path.as_posix())
            payload["relative_path"] = normalized_relative.as_posix()
            payload["url"] = self._build_library_media_url(job_id, normalized_relative.as_posix())
            absolute_path = (job_root / normalized_relative).resolve()
        elif "relative_path" in payload and not payload["relative_path"]:
            payload.pop("relative_path", None)

        if absolute_path is not None:
            payload["path"] = absolute_path.as_posix()
            if "url" not in payload and job_root in absolute_path.parents:
                relative = absolute_path.relative_to(job_root).as_posix()
                payload["url"] = self._build_library_media_url(job_id, relative)

        payload.setdefault("source", "completed")

        return payload

    def _build_library_media_url(self, job_id: str, relative_path: str) -> str:
        job_segment = quote(str(job_id), safe="")
        normalized = relative_path.replace("\\", "/")
        path_segment = quote(normalized, safe="/")
        return f"/api/library/media/{job_segment}/file/{path_segment}"

    def _serialize_media_entries(
        self,
        job_id: str,
        generated_files: Any,
        job_root: Path,
    ) -> Tuple[Dict[str, List[Dict[str, Any]]], List[Dict[str, Any]], bool]:
        media_map: Dict[str, List[Dict[str, Any]]] = {}
        chunk_records: List[Dict[str, Any]] = []
        if not isinstance(generated_files, Mapping):
            return media_map, chunk_records, False

        complete_flag = generated_files.get("complete")
        complete = bool(complete_flag) if isinstance(complete_flag, bool) else False

        seen: set[Tuple[str, str, str]] = set()

        chunks_section = generated_files.get("chunks")
        if isinstance(chunks_section, list):
            for chunk in chunks_section:
                if not isinstance(chunk, Mapping):
                    continue
                files_raw = chunk.get("files")
                chunk_files: List[Dict[str, Any]] = []
                if isinstance(files_raw, list):
                    for file_entry in files_raw:
                        if not isinstance(file_entry, Mapping):
                            continue
                        record, category, signature = self._build_media_record(
                            job_id,
                            file_entry,
                            job_root,
                        )
                        if record is None or category is None:
                            continue
                        chunk_files.append(record)
                        if signature in seen:
                            continue
                        seen.add(signature)
                        media_map.setdefault(category, []).append(record)
                if chunk_files:
                    chunk_records.append(
                        {
                            "chunk_id": self._to_string(chunk.get("chunk_id")),
                            "range_fragment": self._to_string(chunk.get("range_fragment")),
                            "start_sentence": self._coerce_int(chunk.get("start_sentence")),
                            "end_sentence": self._coerce_int(chunk.get("end_sentence")),
                            "files": chunk_files,
                        }
                    )

        files_section = generated_files.get("files")
        if isinstance(files_section, list):
            for file_entry in files_section:
                if not isinstance(file_entry, Mapping):
                    continue
                record, category, signature = self._build_media_record(
                    job_id,
                    file_entry,
                    job_root,
                )
                if record is None or category is None:
                    continue
                if signature in seen:
                    continue
                seen.add(signature)
                media_map.setdefault(category, []).append(record)

        return media_map, chunk_records, complete

    def _build_media_record(
        self,
        job_id: str,
        entry: Mapping[str, Any],
        job_root: Path,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str], Tuple[str, str, str]]:
        sanitized = self._retarget_media_entry(entry, job_id, job_root)
        category = self._resolve_media_category(sanitized)
        if category is None:
            return None, None, ("", "", "")

        path_value = sanitized.get("path")
        relative_value = sanitized.get("relative_path")
        signature = (
            category,
            str(path_value or ""),
            str(relative_value or ""),
        )

        absolute_path = None
        if isinstance(path_value, str) and path_value.strip():
            absolute_path = Path(path_value.strip())

        size: Optional[int] = None
        updated_at: Optional[str] = None
        if absolute_path is not None and absolute_path.exists():
            try:
                stat_result = absolute_path.stat()
            except OSError:
                pass
            else:
                size = int(stat_result.st_size)
                updated_at = datetime.fromtimestamp(stat_result.st_mtime, tz=timezone.utc).isoformat()

        name_value = sanitized.get("name")
        if isinstance(name_value, str) and name_value.strip():
            name = name_value.strip()
        else:
            candidate = None
            if isinstance(relative_value, str) and relative_value.strip():
                candidate = relative_value.strip()
            elif isinstance(path_value, str) and path_value.strip():
                candidate = path_value.strip()
            if candidate:
                name = Path(candidate.replace("\\", "/")).name or candidate
            else:
                name = "media"

        record: Dict[str, Any] = {
            "name": name,
            "url": sanitized.get("url"),
            "size": size,
            "updated_at": updated_at,
            "source": sanitized.get("source") or "completed",
            "relative_path": sanitized.get("relative_path"),
            "path": sanitized.get("path"),
            "chunk_id": sanitized.get("chunk_id") or sanitized.get("chunkId"),
            "range_fragment": sanitized.get("range_fragment") or sanitized.get("rangeFragment"),
            "start_sentence": self._coerce_int(
                sanitized.get("start_sentence") or sanitized.get("startSentence")
            ),
            "end_sentence": self._coerce_int(
                sanitized.get("end_sentence") or sanitized.get("endSentence")
            ),
        }

        return record, category, signature

    def _resolve_media_category(self, entry: Mapping[str, Any]) -> Optional[str]:
        type_value = entry.get("type")
        if isinstance(type_value, str):
            normalized = type_value.strip().lower()
            if normalized in {"audio", "video", "text"}:
                return normalized

        candidate = entry.get("relative_path") or entry.get("path")
        suffix = ""
        if isinstance(candidate, str):
            suffix = Path(candidate.replace("\\", "/")).suffix.lower()

        if suffix in _AUDIO_SUFFIXES:
            return "audio"
        if suffix in _VIDEO_SUFFIXES:
            return "video"
        return "text"

    @staticmethod
    def _coerce_int(value: Any) -> Optional[int]:
        try:
            number = int(value)
        except (TypeError, ValueError):
            return None
        return number

    @staticmethod
    def _to_string(value: Any) -> Optional[str]:
        if isinstance(value, str):
            trimmed = value.strip()
            return trimmed or None
        if value is None:
            return None
        return str(value)

    def resolve_media_file(self, job_id: str, relative_path: str) -> Path:
        item = self._indexer.get(job_id)
        if not item:
            raise LibraryNotFoundError(f"Job {job_id} is not stored in the library")

        normalized = Path(relative_path.replace("\\", "/"))
        if normalized.is_absolute() or any(part == ".." for part in normalized.parts):
            raise LibraryError("Invalid media path")

        job_root = Path(item.library_path).resolve()
        candidate = (job_root / normalized).resolve()
        library_root = self._library_root.resolve()
        if library_root not in candidate.parents and candidate != library_root:
            raise LibraryError("Invalid media path")
        if not candidate.is_file():
            raise LibraryNotFoundError(
                f"Media file {relative_path} not found for job {job_id}"
            )
        return candidate

    def find_cover_asset(self, job_id: str) -> Optional[Path]:
        """Return the cover asset for ``job_id`` if the library stores one."""

        item = self._indexer.get(job_id)
        if not item:
            raise LibraryNotFoundError(f"Job {job_id} is not stored in the library")

        job_root = Path(item.library_path).resolve()
        if item.cover_path:
            candidate = job_root / Path(item.cover_path)
            if candidate.is_file():
                return candidate

        metadata_dir = job_root / "metadata"
        if not metadata_dir.exists():
            return None
        for candidate in sorted(metadata_dir.glob("cover.*")):
            if candidate.is_file():
                return candidate
        return None

    def _load_metadata(self, job_root: Path) -> Dict[str, Any]:
        metadata_path = job_root / "metadata" / "job.json"
        if not metadata_path.exists():
            raise FileNotFoundError(f"No metadata found at {metadata_path}")
        with metadata_path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _write_metadata(self, job_root: Path, payload: Dict[str, Any]) -> None:
        metadata_dir = job_root / "metadata"
        metadata_dir.mkdir(parents=True, exist_ok=True)
        metadata_path = metadata_dir / "job.json"
        serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2)
        tmp_handle = tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=metadata_dir, delete=False
        )
        try:
            with tmp_handle as handle:
                handle.write(serialized)
                handle.flush()
                LOGGER.debug("Wrote metadata snapshot to temporary file %s", handle.name)
            Path(tmp_handle.name).replace(metadata_path)
        except Exception:
            Path(tmp_handle.name).unlink(missing_ok=True)
            raise

    def _extract_cover_path(
        self,
        metadata: Mapping[str, Any],
        job_root: Path,
    ) -> Optional[str]:
        candidates: List[str] = []

        def push(value: Any) -> None:
            if not value:
                return
            if isinstance(value, str):
                trimmed = value.strip()
                if trimmed:
                    candidates.append(trimmed)

        push(metadata.get("job_cover_asset"))
        push(metadata.get("book_cover_file"))

        book_metadata = metadata.get("book_metadata")
        if isinstance(book_metadata, Mapping):
            push(book_metadata.get("job_cover_asset"))
            push(book_metadata.get("book_cover_file"))

        for raw in candidates:
            normalized = self._normalize_cover_path(raw, job_root)
            if normalized:
                return normalized

        metadata_dir = job_root / "metadata"
        for candidate in sorted(metadata_dir.glob("cover.*")):
            if candidate.is_file():
                try:
                    relative = candidate.relative_to(job_root)
                except ValueError:
                    return candidate.as_posix()
                return relative.as_posix()

        return None

    @staticmethod
    def _normalize_cover_path(raw: str, job_root: Path) -> Optional[str]:
        trimmed = raw.strip()
        if not trimmed or "://" in trimmed:
            return None

        candidate = Path(trimmed.replace("\\", "/"))
        try:
            if candidate.is_absolute():
                try:
                    relative = candidate.relative_to(job_root)
                except ValueError:
                    return candidate.as_posix()
                return relative.as_posix()
        except OSError:
            return None

        normalized = trimmed.lstrip("/\\")
        relative_candidate = Path(normalized.replace("\\", "/"))
        resolved_candidate = job_root / relative_candidate
        if resolved_candidate.exists():
            try:
                relative = resolved_candidate.relative_to(job_root)
            except ValueError:
                return relative_candidate.as_posix()
            return relative.as_posix()

        metadata_candidate = job_root / "metadata" / relative_candidate.name
        if metadata_candidate.exists():
            try:
                relative = metadata_candidate.relative_to(job_root)
            except ValueError:
                return metadata_candidate.as_posix()
            return relative.as_posix()

        return relative_candidate.as_posix()

    def _locate_input_epub(
        self,
        metadata: Mapping[str, Any],
        job_root: Path,
    ) -> Optional[Path]:
        candidates: List[str] = []

        def push(value: Any) -> None:
            if isinstance(value, str):
                trimmed = value.strip()
                if trimmed:
                    candidates.append(trimmed)

        def collect(payload: Any) -> None:
            if isinstance(payload, Mapping):
                for key, value in payload.items():
                    lowered = str(key).lower()
                    if lowered in {
                        "input_file",
                        "input_path",
                        "source_file",
                        "source_path",
                        "epub_path",
                    }:
                        push(value)
                    else:
                        collect(value)
            elif isinstance(payload, list):
                for entry in payload:
                    collect(entry)

        collect(metadata)

        for raw in candidates:
            resolved = self._resolve_epub_candidate(raw, job_root)
            if resolved is not None:
                return resolved

        for candidate in job_root.rglob("*.epub"):
            if candidate.is_file():
                return candidate
        return None

    @staticmethod
    def _resolve_epub_candidate(raw: str, job_root: Path) -> Optional[Path]:
        trimmed = raw.strip()
        if not trimmed or "://" in trimmed:
            return None

        candidate = Path(trimmed)
        try:
            if candidate.is_absolute():
                return candidate if candidate.exists() else None
        except OSError:
            return None

        normalized = trimmed.lstrip("/\\")
        relative_candidate = Path(normalized.replace("\\", "/"))

        search_roots = [
            job_root,
            job_root / "data",
            job_root / "metadata",
            job_root / "media",
            job_root / "source",
        ]
        for root in search_roots:
            resolved = root / relative_candidate
            if resolved.exists():
                return resolved

        # Fallback: search by filename anywhere under the job root
        target_name = relative_candidate.name
        if target_name:
            for match in job_root.rglob(target_name):
                if match.is_file():
                    return match

        return None

    def _mirror_cover_asset(
        self,
        job_root: Path,
        cover_reference: Optional[str],
    ) -> Optional[str]:
        metadata_root = job_root / "metadata"
        metadata_root.mkdir(parents=True, exist_ok=True)

        if not cover_reference:
            self._cleanup_cover_assets(metadata_root)
            return None

        source = self._resolve_cover_source(job_root, cover_reference)
        if source is None:
            self._cleanup_cover_assets(metadata_root)
            return None

        try:
            return self._copy_cover_asset(metadata_root, source)
        except Exception as exc:
            LOGGER.debug("Unable to mirror cover asset %s: %s", source, exc)
            return None

    def _resolve_cover_source(self, job_root: Path, raw_value: str) -> Optional[Path]:
        trimmed = raw_value.strip()
        if not trimmed or "://" in trimmed:
            return None

        candidate = Path(trimmed.replace("\\", "/"))
        search_paths: List[Path] = []

        try:
            if candidate.is_absolute():
                search_paths.append(candidate)
        except OSError:
            candidate = Path()

        normalized = trimmed.lstrip("/\\")
        relative_candidate = Path(normalized.replace("\\", "/"))

        search_roots = [
            job_root,
            job_root / "metadata",
            job_root / "media",
            job_root.parent if job_root.parent != job_root else job_root,
        ]
        for root in search_roots:
            search_paths.append(root / relative_candidate)

        if len(relative_candidate.parts) > 1 and relative_candidate.parts[0].lower() in {
            "metadata",
            "media",
            "covers",
        }:
            search_paths.append(job_root / Path(*relative_candidate.parts[1:]))

        search_paths.append(job_root / relative_candidate.name)
        search_paths.append(job_root / "metadata" / relative_candidate.name)

        seen: set[Path] = set()
        for path in search_paths:
            try:
                resolved = path.resolve()
            except OSError:
                continue
            if resolved in seen:
                continue
            seen.add(resolved)
            if resolved.is_file():
                return resolved
        return None

    def _copy_cover_asset(self, metadata_root: Path, source: Path) -> str:
        metadata_root.mkdir(parents=True, exist_ok=True)
        try:
            resolved_source = source.resolve()
        except OSError:
            resolved_source = source

        suffix = resolved_source.suffix.lower() or ".jpg"
        if not suffix.startswith("."):
            suffix = f".{suffix}"
        destination_name = f"cover{suffix}"
        destination_path = metadata_root / destination_name
        destination_abs = destination_path.parent.resolve() / destination_path.name

        if destination_abs != resolved_source:
            should_copy = True
            if destination_path.exists():
                try:
                    src_stat = resolved_source.stat()
                    dest_stat = destination_path.stat()
                    if (
                        src_stat.st_size == dest_stat.st_size
                        and int(src_stat.st_mtime) == int(dest_stat.st_mtime)
                    ):
                        should_copy = False
                except OSError:
                    pass
            if should_copy:
                shutil.copy2(resolved_source, destination_path)

        for existing in metadata_root.glob("cover.*"):
            if existing.name == destination_name:
                continue
            try:
                existing.unlink()
            except FileNotFoundError:
                continue
            except OSError:
                LOGGER.debug("Unable to remove stale cover asset %s", existing, exc_info=True)

        relative_path = Path("metadata") / destination_name
        return relative_path.as_posix()

    @staticmethod
    def _cleanup_cover_assets(metadata_root: Path) -> None:
        for existing in metadata_root.glob("cover.*"):
            try:
                existing.unlink()
            except FileNotFoundError:
                continue
            except OSError:
                LOGGER.debug("Unable to remove cover asset %s", existing, exc_info=True)

    @staticmethod
    def _sanitize_source_filename(filename: str) -> str:
        name = Path(filename).name
        stem = Path(name).stem
        suffix = Path(name).suffix or ".epub"
        if not suffix.startswith("."):
            suffix = f".{suffix}"
        cleaned_stem = _SANITIZE_PATTERN.sub("_", stem).strip("._") or "source"
        return f"{cleaned_stem}{suffix}"

    @staticmethod
    def _next_source_candidate(destination: Path) -> Path:
        if not destination.exists():
            return destination
        stem = destination.stem
        suffix = destination.suffix
        for index in itertools.count(1):
            candidate = destination.with_name(f"{stem}-{index}{suffix}")
            if not candidate.exists():
                return candidate
        return destination

    def _resolve_source_relative(self, metadata: Mapping[str, Any], job_root: Path) -> Optional[str]:
        candidates: List[str] = []

        def push(value: Any) -> None:
            if isinstance(value, str):
                trimmed = value.strip()
                if trimmed:
                    candidates.append(trimmed)

        push(metadata.get("source_path"))
        push(metadata.get("source_file"))
        push(metadata.get("input_file"))
        push(metadata.get("input_path"))

        book_metadata = metadata.get("book_metadata")
        if isinstance(book_metadata, Mapping):
            push(book_metadata.get("source_path"))
            push(book_metadata.get("source_file"))
            push(book_metadata.get("book_source_path"))
            push(book_metadata.get("book_file"))

        for raw in candidates:
            resolved = self._resolve_epub_candidate(raw, job_root)
            if resolved is not None and resolved.exists():
                try:
                    return resolved.relative_to(job_root).as_posix()
                except ValueError:
                    return resolved.as_posix()

        data_root = job_root / "data"
        if data_root.exists():
            for path in sorted(data_root.glob("*")):
                if path.is_file() and path.suffix.lower() in {".epub", ".pdf"}:
                    try:
                        return path.relative_to(job_root).as_posix()
                    except ValueError:
                        return path.as_posix()
        return None

    def _apply_source_reference(self, metadata: Dict[str, Any], source_relative: str) -> None:
        metadata["source_path"] = source_relative
        metadata["source_file"] = source_relative
        book_metadata = metadata.get("book_metadata")
        if isinstance(book_metadata, Mapping):
            nested = dict(book_metadata)
            nested["source_path"] = source_relative
            nested["source_file"] = source_relative
            metadata["book_metadata"] = nested

    def _ensure_source_material(
        self,
        job_root: Path,
        metadata: Mapping[str, Any],
    ) -> Optional[str]:
        data_root = job_root / "data"
        data_root.mkdir(parents=True, exist_ok=True)

        existing_relative = self._resolve_source_relative(metadata, job_root)
        if existing_relative:
            return existing_relative

        epub_path = self._locate_input_epub(metadata, job_root)
        if epub_path is None or not epub_path.exists():
            return None

        if data_root in epub_path.parents:
            try:
                return epub_path.relative_to(job_root).as_posix()
            except ValueError:
                return epub_path.as_posix()

        sanitized_name = self._sanitize_source_filename(epub_path.name)
        destination = self._next_source_candidate(data_root / sanitized_name)

        try:
            shutil.copy2(epub_path, destination)
        except Exception:
            LOGGER.debug(
                "Unable to stage source file %s into %s",
                epub_path,
                destination,
                exc_info=True,
            )
            return None

        return destination.relative_to(job_root).as_posix()

    @staticmethod
    def _normalize_isbn(raw: str) -> Optional[str]:
        if not raw:
            return None
        cleaned = re.sub(r"[^0-9Xx]", "", raw)
        if len(cleaned) in {10, 13}:
            return cleaned.upper()
        return None

    def _extract_isbn(self, metadata: Mapping[str, Any]) -> Optional[str]:
        candidates: List[str] = []

        def push(value: Any) -> None:
            if isinstance(value, str):
                trimmed = value.strip()
                if trimmed:
                    candidates.append(trimmed)

        push(metadata.get("isbn"))
        book_metadata = metadata.get("book_metadata")
        if isinstance(book_metadata, Mapping):
            push(book_metadata.get("isbn"))
            push(book_metadata.get("book_isbn"))

        for raw in candidates:
            normalized = self._normalize_isbn(raw)
            if normalized:
                return normalized
        return None

    def _apply_isbn(self, metadata: Dict[str, Any], isbn: Optional[str]) -> None:
        if not isbn:
            return
        metadata["isbn"] = isbn
        book_metadata = metadata.get("book_metadata")
        if isinstance(book_metadata, Mapping):
            nested = dict(book_metadata)
            nested["isbn"] = isbn
            nested["book_isbn"] = isbn
            metadata["book_metadata"] = nested

    @staticmethod
    def _merge_metadata_payloads(*payloads: Mapping[str, Any]) -> Dict[str, Any]:
        merged: Dict[str, Any] = {}
        placeholder_checker = getattr(metadata_manager, "_is_placeholder", None)

        def is_placeholder(key: str, value: Any) -> bool:
            if value is None:
                return True
            if isinstance(value, str):
                stripped = value.strip()
                if not stripped:
                    return True
                if callable(placeholder_checker):
                    try:
                        return bool(placeholder_checker(key, value))  # type: ignore[misc]
                    except Exception:
                        return False
            return False

        for payload in payloads:
            if not isinstance(payload, Mapping):
                continue
            for key, value in payload.items():
                if value is None:
                    continue
                current = merged.get(key)
                if isinstance(value, str):
                    candidate = value.strip()
                    if not candidate:
                        continue
                    if current is None or is_placeholder(key, current):
                        merged[key] = value
                    elif is_placeholder(key, value):
                        continue
                else:
                    if current is None:
                        merged[key] = value
        return merged

    def _build_item(self, metadata: Dict[str, Any], job_root: Path) -> LibraryItem:
        job_id = str(metadata.get("job_id") or "").strip()
        if not job_id:
            raise LibraryError("Job metadata is missing 'job_id'")

        author = str(metadata.get("author") or "").strip()
        book_title = str(metadata.get("book_title") or "").strip()
        genre = metadata.get("genre")
        language = str(metadata.get("language") or "").strip() or _UNKNOWN_LANGUAGE
        try:
            status = self._normalize_status(metadata.get("status"))
        except LibraryError:
            status = "finished"
        created_at = str(metadata.get("created_at") or self._current_timestamp())
        updated_at = str(metadata.get("updated_at") or created_at)

        metadata = dict(metadata)
        metadata["job_id"] = job_id
        metadata["status"] = status
        metadata.setdefault("created_at", created_at)
        metadata["updated_at"] = updated_at

        source_relative = self._resolve_source_relative(metadata, job_root)
        if source_relative:
            self._apply_source_reference(metadata, source_relative)

        isbn = self._extract_isbn(metadata)
        if isbn:
            self._apply_isbn(metadata, isbn)

        metadata["generated_files"] = self._retarget_generated_files(
            metadata.get("generated_files"),
            job_id,
            job_root,
        )

        cover_path = self._extract_cover_path(metadata, job_root)
        if cover_path:
            metadata["job_cover_asset"] = cover_path
            book_metadata = metadata.get("book_metadata")
            if isinstance(book_metadata, Mapping):
                nested = dict(book_metadata)
                nested["job_cover_asset"] = cover_path
                nested.setdefault("book_cover_file", cover_path)
                metadata["book_metadata"] = nested

        serialized = json.dumps(metadata, ensure_ascii=False, sort_keys=True)
        return LibraryItem(
            id=job_id,
            author=author,
            book_title=book_title,
            genre=str(genre) if genre not in {None, ""} else None,
            language=language,
            status=status,
            created_at=created_at,
            updated_at=updated_at,
            library_path=str(job_root.resolve()),
            cover_path=cover_path,
            isbn=isbn,
            source_path=source_relative,
            meta_json=serialized,
        )

    def _resolve_library_path(self, metadata: Dict[str, Any], job_id: str) -> Path:
        author_segment = _sanitize_segment(metadata.get("author"), _UNKNOWN_AUTHOR)
        book_segment = _sanitize_segment(metadata.get("book_title"), _UNTITLED_BOOK)
        language_segment = _sanitize_segment(metadata.get("language"), _UNKNOWN_LANGUAGE)
        job_segment = _sanitize_segment(job_id, "job")
        return self._library_root / author_segment / book_segment / language_segment / job_segment

    def _locate_job_root(self, job_id: str) -> Optional[Path]:
        normalized = str(job_id or "").strip()
        if not normalized:
            return None

        cached = self._library_job_cache.get(normalized)
        if cached is not None:
            metadata_path = cached / "metadata" / "job.json"
            if metadata_path.exists():
                return cached

        try:
            author_dirs = [path for path in self._library_root.iterdir() if path.is_dir()]
        except FileNotFoundError:
            return None

        for author_dir in author_dirs:
            if author_dir.name.startswith("."):
                continue
            try:
                book_dirs = [path for path in author_dir.iterdir() if path.is_dir()]
            except FileNotFoundError:
                continue
            for book_dir in book_dirs:
                try:
                    language_dirs = [path for path in book_dir.iterdir() if path.is_dir()]
                except FileNotFoundError:
                    continue
                for language_dir in language_dirs:
                    candidate = language_dir / normalized
                    metadata_path = candidate / "metadata" / "job.json"
                    if metadata_path.exists():
                        self._library_job_cache[normalized] = candidate
                        self._missing_job_cache.discard(normalized)
                        return candidate
        return None

    def _purge_media_files(self, job_root: Path) -> int:
        removed = 0
        metadata_dir = job_root / "metadata"
        for path in job_root.rglob("*"):
            if not path.is_file():
                continue
            if metadata_dir in path.parents:
                continue
            if path.suffix.lower() in _MEDIA_EXTENSIONS:
                try:
                    path.unlink()
                    removed += 1
                except OSError:
                    LOGGER.warning("Failed to delete media file %s", path)
        return removed

    def _normalize_status(self, status: Any) -> LibraryStatus:
        candidate = str(status or "").strip().lower()
        if candidate in {"completed", "finished", "success"}:
            return "finished"
        if candidate == "paused":
            return "paused"
        raise LibraryError(f"Unsupported library status '{status}'")

    @staticmethod
    def _current_timestamp() -> str:
        return datetime.now(timezone.utc).isoformat()


def _compact_filters(filters: Dict[str, Optional[str]]) -> Dict[str, str]:
    return {key: value for key, value in filters.items() if value}


def _sanitize_segment(value: Any, placeholder: str) -> str:
    token = str(value or "").strip()
    if not token:
        token = placeholder
    sanitized = _SANITIZE_PATTERN.sub("_", token)
    sanitized = sanitized.strip("._ ")
    return sanitized or placeholder


def _group_by_author(
    items: Iterable[LibraryItem],
    serializer,
) -> List[Dict[str, Any]]:
    by_author: Dict[str, Dict[str, Dict[str, List[LibraryItem]]]] = {}
    for item in items:
        author_label = item.author or _UNKNOWN_AUTHOR.replace("_", " ")
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
    items: Iterable[LibraryItem],
    serializer,
) -> List[Dict[str, Any]]:
    by_genre: Dict[str, Dict[str, Dict[str, List[LibraryItem]]]] = {}
    for item in items:
        genre_label = item.genre or _UNKNOWN_GENRE
        genre_bucket = by_genre.setdefault(genre_label, {})
        author_label = item.author or _UNKNOWN_AUTHOR.replace("_", " ")
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
    items: Iterable[LibraryItem],
    serializer,
) -> List[Dict[str, Any]]:
    by_language: Dict[str, Dict[str, List[LibraryItem]]] = {}
    for item in items:
        language_label = item.language
        language_bucket = by_language.setdefault(language_label, {})
        author_label = item.author or _UNKNOWN_AUTHOR.replace("_", " ")
        author_bucket = language_bucket.setdefault(author_label, [])
        author_bucket.append(item)

    result: List[Dict[str, Any]] = []
    for language_label in sorted(by_language):
        authors_payload: List[Dict[str, Any]] = []
        for author_label, author_entries in sorted(by_language[language_label].items()):
            books_group: Dict[str, List[LibraryItem]] = {}
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
