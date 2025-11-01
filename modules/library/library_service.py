"""High-level coordination for the Library feature."""

from __future__ import annotations

import json
import re
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Literal, Mapping, Optional, Tuple
from urllib.parse import quote

from modules import logging_manager
from modules.fsutils import AtomicMoveError, ChecksumMismatchError, DirectoryLock, atomic_move
from modules.services.file_locator import FileLocator
from modules.services.job_manager import PipelineJobManager, PipelineJobTransitionError

from .indexer import LibraryIndexer, LibraryItem

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
            self._job_manager.delete_job(job_id)
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

        metadata_dir = Path(item.library_path).resolve() / "metadata"
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
        metadata["generated_files"] = self._retarget_generated_files(
            metadata.get("generated_files"),
            job_id,
            job_root,
        )

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
            meta_json=serialized,
        )

    def _resolve_library_path(self, metadata: Dict[str, Any], job_id: str) -> Path:
        author_segment = _sanitize_segment(metadata.get("author"), _UNKNOWN_AUTHOR)
        book_segment = _sanitize_segment(metadata.get("book_title"), _UNTITLED_BOOK)
        language_segment = _sanitize_segment(metadata.get("language"), _UNKNOWN_LANGUAGE)
        job_segment = _sanitize_segment(job_id, "job")
        return self._library_root / author_segment / book_segment / language_segment / job_segment

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
