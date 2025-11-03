"""High-level coordination for the Library feature."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

from modules import logging_manager
from modules.fsutils import AtomicMoveError, ChecksumMismatchError, DirectoryLock, atomic_move
from modules.services.file_locator import FileLocator
from modules.services.job_manager import PipelineJobManager

from modules.library.sync import db_sync, file_ops, metadata as metadata_utils, remote_sync, utils

from .library_metadata import LibraryMetadataManager
from .library_models import LibraryEntry, MetadataSnapshot
from .library_repository import LibraryRepository

LOGGER = logging_manager.get_logger().getChild("library.sync")

LibraryStatus = utils.LibraryStatus


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
    items: List[LibraryEntry]
    groups: Optional[List[Dict[str, Any]]]


class LibrarySync:
    """Coordinate filesystem operations and index maintenance for the Library."""

    def __init__(
        self,
        *,
        library_root: Path,
        file_locator: FileLocator,
        repository: Optional[LibraryRepository] = None,
        metadata_manager: Optional[LibraryMetadataManager] = None,
        job_manager: Optional[PipelineJobManager] = None,
    ) -> None:
        self._library_root = Path(library_root)
        self._library_root.mkdir(parents=True, exist_ok=True)
        self._locator = file_locator
        self._repository = repository or LibraryRepository(self._library_root)
        self._metadata_manager = metadata_manager or LibraryMetadataManager(self._library_root)
        self._job_manager = job_manager
        self._library_job_cache: Dict[str, Path] = {}
        self._missing_job_cache: set[str] = set()
        # Prime the database and ensure migrations run up-front.
        with self._repository.connect():
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
    ) -> LibraryEntry:
        """Move ``job_id`` from the queue storage into the Library."""

        job_root = self._locator.job_root(job_id)
        if not job_root.exists():
            raise LibraryNotFoundError(f"Job {job_id} not found in queue storage")

        with DirectoryLock(job_root) as lock:
            metadata = file_ops.load_metadata(job_root)
            normalized_status = utils.normalize_status(
                status_override or metadata.get("status"),
                error_cls=LibraryError,
            )
            now = utils.current_timestamp()
            media_ready = file_ops.is_media_complete(metadata, normalized_status, job_root)
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

            target_path = file_ops.resolve_library_path(self._library_root, metadata, job_id)

            existing_item = self._repository.get_entry_by_id(job_id)
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

            source_relative = file_ops.ensure_source_material(target_path, metadata)
            if source_relative:
                metadata_utils.apply_source_reference(metadata, source_relative)

            isbn_value = metadata_utils.extract_isbn(metadata)
            if isbn_value:
                metadata_utils.apply_isbn(metadata, isbn_value)

            metadata["generated_files"] = file_ops.retarget_generated_files(
                metadata.get("generated_files"),
                job_id,
                target_path,
            )

            cover_reference: Optional[str] = None

            def _select_cover_candidate(value: Any) -> None:
                nonlocal cover_reference
                if cover_reference is not None:
                    return
                if isinstance(value, str):
                    candidate = value.strip()
                    if candidate:
                        cover_reference = candidate

            _select_cover_candidate(metadata.get("job_cover_asset"))
            _select_cover_candidate(metadata.get("book_cover_file"))

            book_metadata = metadata.get("book_metadata")
            if cover_reference is None and isinstance(book_metadata, Mapping):
                _select_cover_candidate(book_metadata.get("job_cover_asset"))
                _select_cover_candidate(book_metadata.get("book_cover_file"))

            cover_asset = (
                file_ops.mirror_cover_asset(target_path, cover_reference) if cover_reference else None
            )
            if cover_asset:
                metadata["job_cover_asset"] = cover_asset
                metadata["book_cover_file"] = cover_asset
                if isinstance(book_metadata, Mapping):
                    nested = dict(book_metadata)
                    nested["job_cover_asset"] = cover_asset
                    nested["book_cover_file"] = cover_asset
                    metadata["book_metadata"] = nested
            else:
                metadata.pop("job_cover_asset", None)
                if not metadata.get("book_cover_file"):
                    metadata.pop("book_cover_file", None)
                if isinstance(book_metadata, Mapping):
                    nested = dict(book_metadata)
                    nested.pop("job_cover_asset", None)
                    if not nested.get("book_cover_file"):
                        nested.pop("book_cover_file", None)
                    metadata["book_metadata"] = nested

            file_ops.write_metadata(target_path, metadata)

        library_item = metadata_utils.build_entry(
            metadata,
            target_path,
            error_cls=LibraryError,
            normalize_status=lambda value: utils.normalize_status(value, error_cls=LibraryError),
            current_timestamp=utils.current_timestamp,
        )
        self._repository.add_entry(library_item)
        db_sync.remove_from_job_queue(self._job_manager, job_id)
        return library_item

    def remove_media(self, job_id: str) -> Tuple[Optional[LibraryEntry], int]:
        """Remove generated media files for ``job_id`` without deleting metadata."""

        item = self._repository.get_entry_by_id(job_id)
        if item:
            job_root = Path(item.library_path)
            is_library = True
        else:
            job_root = self._locator.job_root(job_id)
            is_library = False

        if not job_root.exists():
            raise LibraryNotFoundError(f"Job {job_id} does not exist on disk")

        with DirectoryLock(job_root):
            metadata = file_ops.load_metadata(job_root)
            removed = file_ops.purge_media_files(job_root)
            metadata["updated_at"] = utils.current_timestamp()
            metadata["media_completed"] = False
            metadata["generated_files"] = file_ops.retarget_generated_files(
                metadata.get("generated_files"),
                job_id,
                job_root,
            )
            file_ops.write_metadata(job_root, metadata)

        if is_library:
            updated_item = metadata_utils.build_entry(
                metadata,
                job_root,
                error_cls=LibraryError,
                normalize_status=lambda value: utils.normalize_status(value, error_cls=LibraryError),
                current_timestamp=utils.current_timestamp,
            )
            self._repository.add_entry(updated_item)
            return updated_item, removed

        return None, removed

    def remove_entry(self, job_id: str) -> None:
        """Remove ``job_id`` from the Library entirely."""

        item = self._repository.get_entry_by_id(job_id)
        if not item:
            raise LibraryNotFoundError(f"Job {job_id} is not stored in the library")

        job_root = Path(item.library_path)
        with DirectoryLock(job_root):
            if job_root.exists():
                shutil.rmtree(job_root, ignore_errors=True)

        self._repository.delete_entry(job_id)
        self._library_job_cache.pop(job_id, None)
        self._missing_job_cache.discard(job_id)
        self._prune_empty_ancestors(job_root)

    def update_metadata(
        self,
        job_id: str,
        *,
        title: Optional[str] = None,
        author: Optional[str] = None,
        genre: Optional[str] = None,
        language: Optional[str] = None,
        isbn: Optional[str] = None,
    ) -> LibraryEntry:
        """Persist user-supplied metadata changes for ``job_id``."""

        item = self._repository.get_entry_by_id(job_id)
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

        now = utils.current_timestamp()

        with DirectoryLock(job_root) as lock:
            metadata = file_ops.load_metadata(job_root)
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
                    normalized_isbn = metadata_utils.normalize_isbn(cleaned_isbn)
                    if normalized_isbn is None:
                        raise LibraryError("ISBN must contain 10 or 13 digits (optionally including X)")
                    metadata_utils.apply_isbn(metadata, normalized_isbn)
                    book_metadata["isbn"] = normalized_isbn
                    book_metadata["book_isbn"] = normalized_isbn
                    metadata["isbn"] = normalized_isbn
                else:
                    metadata.pop("isbn", None)
                    book_metadata.pop("isbn", None)
                    book_metadata.pop("book_isbn", None)
            else:
                existing_isbn = metadata_utils.extract_isbn(metadata)
                if existing_isbn:
                    book_metadata.setdefault("isbn", existing_isbn)
                    book_metadata.setdefault("book_isbn", existing_isbn)
                    metadata.setdefault("isbn", existing_isbn)

            target_path = file_ops.resolve_library_path(self._library_root, metadata, job_id)
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

            file_ops.write_metadata(job_root, metadata)

        updated_item = metadata_utils.build_entry(
            metadata,
            job_root,
            error_cls=LibraryError,
            normalize_status=lambda value: utils.normalize_status(value, error_cls=LibraryError),
            current_timestamp=utils.current_timestamp,
        )
        self._repository.add_entry(updated_item)
        return updated_item

    def refresh_metadata(self, job_id: str) -> LibraryEntry:
        """Recompute metadata for ``job_id`` using the shared metadata manager."""

        item = self._repository.get_entry_by_id(job_id)
        if not item:
            raise LibraryNotFoundError(f"Job {job_id} is not stored in the library")

        job_root = Path(item.library_path)
        if not job_root.exists():
            raise LibraryNotFoundError(f"Job {job_id} is missing from the library filesystem")

        with DirectoryLock(job_root):
            metadata = file_ops.load_metadata(job_root)
            refreshed = remote_sync.refresh_metadata(
                job_id,
                job_root,
                metadata,
                self._metadata_manager,
                error_cls=LibraryError,
                current_timestamp=utils.current_timestamp,
            )
            file_ops.write_metadata(job_root, refreshed)

        refreshed_item = metadata_utils.build_entry(
            refreshed,
            job_root,
            error_cls=LibraryError,
            normalize_status=lambda value: utils.normalize_status(value, error_cls=LibraryError),
            current_timestamp=utils.current_timestamp,
        )
        self._repository.add_entry(refreshed_item)
        return refreshed_item

    def reupload_source_from_path(self, job_id: str, source_path: Path) -> LibraryEntry:
        """Replace the stored source file for ``job_id`` using an external path."""

        item = self._repository.get_entry_by_id(job_id)
        if not item:
            raise LibraryNotFoundError(f"Job {job_id} is not stored in the library")

        resolved_source = Path(source_path).expanduser()
        if not resolved_source.exists():
            raise LibraryError(f"Source file {resolved_source} does not exist")

        job_root = Path(item.library_path)
        if not job_root.exists():
            raise LibraryNotFoundError(f"Job {job_id} is missing from the library filesystem")

        with DirectoryLock(job_root):
            metadata = file_ops.load_metadata(job_root)
            data_root = job_root / "data"
            data_root.mkdir(parents=True, exist_ok=True)

            sanitized_name = file_ops.sanitize_source_filename(resolved_source.name)
            destination = file_ops.next_source_candidate(data_root / sanitized_name)

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
            metadata_utils.apply_source_reference(metadata, source_relative)
            metadata["updated_at"] = utils.current_timestamp()
            file_ops.write_metadata(job_root, metadata)

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
        fallback_metadata = file_ops.load_metadata(job_root)
        fallback_item = metadata_utils.build_entry(
            fallback_metadata,
            job_root,
            error_cls=LibraryError,
            normalize_status=lambda value: utils.normalize_status(value, error_cls=LibraryError),
            current_timestamp=utils.current_timestamp,
        )
        self._repository.add_entry(fallback_item)
        return fallback_item

    def apply_isbn_metadata(self, job_id: str, isbn: str) -> LibraryEntry:
        """Persist ``isbn`` for ``job_id`` and refresh metadata using remote lookups."""

        item = self._repository.get_entry_by_id(job_id)
        if not item:
            raise LibraryNotFoundError(f"Job {job_id} is not stored in the library")

        job_root = Path(item.library_path)
        if not job_root.exists():
            raise LibraryNotFoundError(f"Job {job_id} is missing from the library filesystem")

        with DirectoryLock(job_root):
            metadata = file_ops.load_metadata(job_root)
            updated = remote_sync.apply_isbn_metadata(
                metadata,
                isbn=isbn,
                error_cls=LibraryError,
                current_timestamp=utils.current_timestamp,
            )
            file_ops.write_metadata(job_root, updated)

        return self.refresh_metadata(job_id)

    def lookup_isbn_metadata(self, isbn: str) -> Dict[str, Optional[str]]:
        """Return metadata fetched from public ISBN APIs without mutating state."""

        return remote_sync.lookup_isbn_metadata(
            self._metadata_manager,
            isbn,
            error_cls=LibraryError,
        )

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
        total, items, groups = db_sync.search_entries(
            self._repository,
            query=query,
            filters=filters,
            limit=normalized_limit,
            offset=offset,
            sort_desc=sort_desc,
            view=view,
            serializer=self.serialize_item,
        )
        return LibrarySearchResult(
            total=total,
            page=normalized_page,
            limit=normalized_limit,
            view=view,
            items=items,
            groups=groups,
        )

    def get_item(self, job_id: str) -> Optional[LibraryEntry]:
        """Return the indexed ``LibraryEntry`` for ``job_id`` if present."""

        if not job_id:
            return None
        if job_id in self._missing_job_cache:
            return None

        item = self._repository.get_entry_by_id(job_id)
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
                    metadata = file_ops.load_metadata(cached_root)
                    recovered = metadata_utils.build_entry(
                        metadata,
                        cached_root,
                        error_cls=LibraryError,
                        normalize_status=lambda value: utils.normalize_status(value, error_cls=LibraryError),
                        current_timestamp=utils.current_timestamp,
                    )
                except (FileNotFoundError, LibraryError):
                    pass
                else:
                    self._repository.add_entry(recovered)
                    return recovered

        job_root = self._locate_job_root(job_id)
        if job_root is None:
            self._missing_job_cache.add(job_id)
            return None

        try:
            metadata = file_ops.load_metadata(job_root)
            recovered = metadata_utils.build_entry(
                metadata,
                job_root,
                error_cls=LibraryError,
                normalize_status=lambda value: utils.normalize_status(value, error_cls=LibraryError),
                current_timestamp=utils.current_timestamp,
            )
        except (FileNotFoundError, LibraryError):
            self._missing_job_cache.add(job_id)
            return None

        self._library_job_cache[job_id] = job_root
        self._repository.add_entry(recovered)
        self._missing_job_cache.discard(job_id)
        return recovered

    def get_media(
        self,
        job_id: str,
    ) -> Tuple[Dict[str, List[Dict[str, Any]]], List[Dict[str, Any]], bool]:
        """Return generated media details for ``job_id``."""

        item = self._repository.get_entry_by_id(job_id)
        if not item:
            raise LibraryNotFoundError(f"Job {job_id} is not stored in the library")

        job_root = Path(item.library_path)
        metadata = file_ops.load_metadata(job_root)
        generated = metadata.get("generated_files")
        media_map, chunk_records, generated_complete = file_ops.serialize_media_entries(
            job_id,
            generated,
            job_root,
        )
        completed_flag = bool(metadata.get("media_completed")) or generated_complete
        return media_map, chunk_records, completed_flag

    def reindex_from_fs(self) -> int:
        """Scan the library filesystem and rebuild the SQLite index."""

        def build_entry(metadata: Mapping[str, Any], job_root: Path) -> LibraryEntry:
            return metadata_utils.build_entry(
                dict(metadata),
                job_root,
                error_cls=LibraryError,
                normalize_status=lambda value: utils.normalize_status(
                    value, error_cls=LibraryError
                ),
                current_timestamp=utils.current_timestamp,
            )

        return db_sync.reindex_from_fs(
            self._library_root,
            self._repository,
            load_metadata=file_ops.load_metadata,
            build_entry=build_entry,
        )

    def build_entry(self, metadata: Mapping[str, Any], job_root: Path) -> LibraryEntry:
        """Create a :class:`LibraryEntry` from raw metadata without persisting."""

        return metadata_utils.build_entry(
            dict(metadata),
            Path(job_root),
            error_cls=LibraryError,
            normalize_status=lambda value: utils.normalize_status(value, error_cls=LibraryError),
            current_timestamp=utils.current_timestamp,
        )

    def resolve_library_path(self, metadata: Mapping[str, Any], job_id: str) -> Path:
        """Return the normalized library path for ``job_id`` without mutating state."""

        return file_ops.resolve_library_path(self._library_root, dict(metadata), job_id)

    def serialize_item(self, item: LibraryEntry) -> Dict[str, Any]:
        """Return a JSON-serializable representation of ``item``."""

        if isinstance(item.metadata, MetadataSnapshot):
            metadata_payload: Dict[str, Any] = dict(item.metadata.data)
        elif isinstance(item.metadata, Mapping):
            metadata_payload = dict(item.metadata)
        else:
            metadata_payload = {}

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
            "metadata": metadata_payload,
        }
        media_completed = bool(metadata_payload.get("media_completed"))
        if not media_completed:
            generated = metadata_payload.get("generated_files")
            if isinstance(generated, Mapping):
                complete_flag = generated.get("complete")
                media_completed = bool(complete_flag) or utils.has_generated_media(generated)
        payload["media_completed"] = media_completed
        return payload


    def resolve_media_file(self, job_id: str, relative_path: str) -> Path:
        item = self._repository.get_entry_by_id(job_id)
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

        item = self._repository.get_entry_by_id(job_id)
        if not item:
            raise LibraryNotFoundError(f"Job {job_id} is not stored in the library")

        job_root = Path(item.library_path).resolve()
        if item.cover_path:
            candidate = job_root / Path(item.cover_path)
            if candidate.is_file():
                return candidate

        cover_candidate = file_ops.contains_cover_asset(job_root)
        return cover_candidate

    def _prune_empty_ancestors(self, path: Path) -> None:
        """Remove empty parent directories up to the library root."""

        try:
            library_root = self._library_root.resolve()
            current = Path(path).resolve().parent
            while current != library_root and library_root in current.parents:
                if not current.exists():
                    current = current.parent
                    continue
                try:
                    current.rmdir()
                except OSError:
                    break
                current = current.parent
        except Exception:
            LOGGER.debug("Unable to prune directories for %s", path, exc_info=True)
 
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
