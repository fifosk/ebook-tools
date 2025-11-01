"""File operations and metadata transformations for library sync."""

from __future__ import annotations

import itertools
import json
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple
from urllib.parse import quote

from modules import logging_manager

from conf.sync_config import (
    AUDIO_SUFFIXES,
    MEDIA_EXTENSIONS,
    SANITIZE_PATTERN,
    UNKNOWN_AUTHOR,
    UNKNOWN_GENRE,
    UNKNOWN_LANGUAGE,
    UNTITLED_BOOK,
    VIDEO_SUFFIXES,
)

from . import utils

LOGGER = logging_manager.get_logger().getChild("library.sync.file_ops")


def load_metadata(job_root: Path) -> Dict[str, Any]:
    """Read the ``job.json`` payload for ``job_root``."""

    metadata_path = job_root / "metadata" / "job.json"
    if not metadata_path.exists():
        raise FileNotFoundError(f"No metadata found at {metadata_path}")
    with metadata_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_metadata(job_root: Path, payload: Dict[str, Any]) -> None:
    """Persist ``payload`` to ``job_root``."""

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


def ensure_source_material(job_root: Path, metadata: Mapping[str, Any]) -> Optional[str]:
    """Ensure the source EPUB/PDF for ``job_root`` resides in the data directory."""

    data_root = job_root / "data"
    data_root.mkdir(parents=True, exist_ok=True)

    existing_relative = resolve_source_relative(metadata, job_root)
    if existing_relative:
        return existing_relative

    epub_path = locate_input_epub(metadata, job_root)
    if epub_path is None or not epub_path.exists():
        return None

    if data_root in epub_path.parents:
        try:
            return epub_path.relative_to(job_root).as_posix()
        except ValueError:
            return epub_path.as_posix()

    sanitized_name = sanitize_source_filename(epub_path.name)
    destination = next_source_candidate(data_root / sanitized_name)

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


def resolve_source_relative(metadata: Mapping[str, Any], job_root: Path) -> Optional[str]:
    """Resolve a relative source file path from metadata."""

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
        resolved = resolve_epub_candidate(raw, job_root)
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


def sanitize_source_filename(filename: str) -> str:
    """Return a sanitized filename for staged source material."""

    name = Path(filename).name
    stem = Path(name).stem
    suffix = Path(name).suffix or ".epub"
    if not suffix.startswith("."):
        suffix = f".{suffix}"
    cleaned_stem = SANITIZE_PATTERN.sub("_", stem).strip("._") or "source"
    return f"{cleaned_stem}{suffix}"


def next_source_candidate(destination: Path) -> Path:
    """Return a unique destination for the source file."""

    if not destination.exists():
        return destination
    stem = destination.stem
    suffix = destination.suffix
    for index in itertools.count(1):
        candidate = destination.with_name(f"{stem}-{index}{suffix}")
        if not candidate.exists():
            return candidate
    return destination


def locate_input_epub(metadata: Mapping[str, Any], job_root: Path) -> Optional[Path]:
    """Return the EPUB path referenced by ``metadata``."""

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
        resolved = resolve_epub_candidate(raw, job_root)
        if resolved is not None:
            return resolved

    for candidate in job_root.rglob("*.epub"):
        if candidate.is_file():
            return candidate
    return None


def resolve_epub_candidate(raw: str, job_root: Path) -> Optional[Path]:
    """Resolve a raw EPUB path reference relative to ``job_root``."""

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

    target_name = relative_candidate.name
    if target_name:
        for match in job_root.rglob(target_name):
            if match.is_file():
                return match

    return None


def mirror_cover_asset(job_root: Path, cover_reference: Optional[str]) -> Optional[str]:
    """Copy cover assets referenced by metadata into the metadata directory."""

    metadata_root = job_root / "metadata"
    metadata_root.mkdir(parents=True, exist_ok=True)

    if not cover_reference:
        cleanup_cover_assets(metadata_root)
        return None

    source = resolve_cover_source(job_root, cover_reference)
    if source is None:
        cleanup_cover_assets(metadata_root)
        return None

    try:
        return copy_cover_asset(metadata_root, source)
    except Exception as exc:  # pragma: no cover - defensive logging
        LOGGER.debug("Unable to mirror cover asset %s: %s", source, exc)
        return None


def resolve_cover_source(job_root: Path, raw_value: str) -> Optional[Path]:
    """Resolve the source cover asset on disk."""

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


def copy_cover_asset(metadata_root: Path, source: Path) -> str:
    """Copy ``source`` into the metadata directory and return its relative path."""

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


def cleanup_cover_assets(metadata_root: Path) -> None:
    """Remove any existing cover assets."""

    for existing in metadata_root.glob("cover.*"):
        try:
            existing.unlink()
        except FileNotFoundError:
            continue
        except OSError:
            LOGGER.debug("Unable to remove cover asset %s", existing, exc_info=True)


def extract_cover_path(metadata: Mapping[str, Any], job_root: Path) -> Optional[str]:
    """Extract the cover path from metadata."""

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
        normalized = normalize_cover_path(raw, job_root)
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


def normalize_cover_path(raw: str, job_root: Path) -> Optional[str]:
    """Normalize a raw cover reference relative to ``job_root``."""

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


def resolve_library_path(
    library_root: Path,
    metadata: Mapping[str, Any],
    job_id: str,
) -> Path:
    """Build the canonical library path for ``job_id``."""

    author_segment = utils.sanitize_segment(metadata.get("author"), UNKNOWN_AUTHOR)
    book_segment = utils.sanitize_segment(metadata.get("book_title"), UNTITLED_BOOK)
    language_segment = utils.sanitize_segment(metadata.get("language"), UNKNOWN_LANGUAGE)
    job_segment = utils.sanitize_segment(job_id, "job")
    return library_root / author_segment / book_segment / language_segment / job_segment


def retarget_generated_files(payload: Any, job_id: str, job_root: Path) -> Any:
    """Rewrite generated file payloads so they reference library paths."""

    if not isinstance(payload, Mapping):
        return payload
    updated: Dict[str, Any] = {}
    for key, value in payload.items():
        if key == "files":
            if isinstance(value, list):
                updated[key] = [
                    retarget_media_entry(entry, job_id, job_root)
                    for entry in value
                    if isinstance(entry, Mapping)
                ]
            elif isinstance(value, Mapping):
                updated[key] = {
                    name: retarget_media_entry(entry, job_id, job_root)
                    for name, entry in value.items()
                    if isinstance(entry, Mapping)
                }
            else:
                updated[key] = value
        elif key == "chunks":
            if isinstance(value, list):
                updated[key] = [
                    retarget_chunk_entry(chunk, job_id, job_root)
                    for chunk in value
                    if isinstance(chunk, Mapping)
                ]
            elif isinstance(value, Mapping):
                updated[key] = {
                    name: retarget_chunk_entry(chunk, job_id, job_root)
                    for name, chunk in value.items()
                    if isinstance(chunk, Mapping)
                }
            else:
                updated[key] = value
        else:
            updated[key] = value
    return updated


def retarget_chunk_entry(chunk: Mapping[str, Any], job_id: str, job_root: Path) -> Dict[str, Any]:
    """Retarget chunk metadata."""

    payload = dict(chunk)
    files = chunk.get("files")
    if isinstance(files, list):
        payload["files"] = [
            retarget_media_entry(entry, job_id, job_root)
            for entry in files
            if isinstance(entry, Mapping)
        ]
    elif isinstance(files, Mapping):
        payload["files"] = {
            name: retarget_media_entry(entry, job_id, job_root)
            for name, entry in files.items()
            if isinstance(entry, Mapping)
        }
    return payload


def retarget_media_entry(
    entry: Mapping[str, Any],
    job_id: str,
    job_root: Path,
) -> Dict[str, Any]:
    """Retarget a generated media entry."""

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
        payload["url"] = build_library_media_url(job_id, normalized_relative.as_posix())
        absolute_path = (job_root / normalized_relative).resolve()
    elif "relative_path" in payload and not payload["relative_path"]:
        payload.pop("relative_path", None)

    if absolute_path is not None:
        payload["path"] = absolute_path.as_posix()
        if "url" not in payload and job_root in absolute_path.parents:
            relative = absolute_path.relative_to(job_root).as_posix()
            payload["url"] = build_library_media_url(job_id, relative)

    payload.setdefault("source", "completed")

    return payload


def build_library_media_url(job_id: str, relative_path: str) -> str:
    """Return the API URL for the given media path."""

    job_segment = quote(str(job_id), safe="")
    normalized = relative_path.replace("\\", "/")
    path_segment = quote(normalized, safe="/")
    return f"/api/library/media/{job_segment}/file/{path_segment}"


def serialize_media_entries(
    job_id: str,
    generated_files: Any,
    job_root: Path,
) -> Tuple[Dict[str, List[Dict[str, Any]]], List[Dict[str, Any]], bool]:
    """Return categorized media payloads for API responses."""

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
                    record, category, signature = build_media_record(
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
                        "chunk_id": utils.to_string(chunk.get("chunk_id")),
                        "range_fragment": utils.to_string(chunk.get("range_fragment")),
                        "start_sentence": utils.coerce_int(chunk.get("start_sentence")),
                        "end_sentence": utils.coerce_int(chunk.get("end_sentence")),
                        "files": chunk_files,
                    }
                )

    files_section = generated_files.get("files")
    if isinstance(files_section, list):
        for file_entry in files_section:
            if not isinstance(file_entry, Mapping):
                continue
            record, category, signature = build_media_record(
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


def build_media_record(
    job_id: str,
    entry: Mapping[str, Any],
    job_root: Path,
) -> Tuple[Optional[Dict[str, Any]], Optional[str], Tuple[str, str, str]]:
    """Build a media record from a generated entry."""

    sanitized = retarget_media_entry(entry, job_id, job_root)
    category = resolve_media_category(sanitized)
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
        "start_sentence": utils.coerce_int(
            sanitized.get("start_sentence") or sanitized.get("startSentence")
        ),
        "end_sentence": utils.coerce_int(
            sanitized.get("end_sentence") or sanitized.get("endSentence")
        ),
    }

    return record, category, signature


def resolve_media_category(entry: Mapping[str, Any]) -> Optional[str]:
    """Classify media entries based on their suffix."""

    type_value = entry.get("type")
    if isinstance(type_value, str):
        normalized = type_value.strip().lower()
        if normalized in {"audio", "video", "text"}:
            return normalized

    candidate = entry.get("relative_path") or entry.get("path")
    suffix = ""
    if isinstance(candidate, str):
        suffix = Path(candidate.replace("\\", "/")).suffix.lower()

    if suffix in AUDIO_SUFFIXES:
        return "audio"
    if suffix in VIDEO_SUFFIXES:
        return "video"
    return "text"


def contains_media_files(job_root: Path) -> bool:
    """Return True if ``job_root`` contains generated media."""

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
    for path in job_root.rglob("*"):
        if not path.is_file():
            continue
        if path.name == ".lock":
            continue
        if metadata_dir in path.parents:
            continue
        if path.suffix.lower() in MEDIA_EXTENSIONS:
            return True
    return False


def is_media_complete(metadata: Mapping[str, Any], status: str, job_root: Path) -> bool:
    """Determine whether media generation is complete."""

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
        if normalized_status == "paused" and utils.has_generated_media(generated):
            return True
    if normalized_status == "paused" and contains_media_files(job_root):
        return True
    return False


def purge_media_files(job_root: Path) -> int:
    """Delete generated media artifacts under ``job_root`` and return the count."""

    removed = 0
    metadata_dir = job_root / "metadata"
    for path in job_root.rglob("*"):
        if not path.is_file():
            continue
        if metadata_dir in path.parents:
            continue
        if path.suffix.lower() in MEDIA_EXTENSIONS:
            try:
                path.unlink()
                removed += 1
            except OSError:
                LOGGER.warning("Failed to delete media file %s", path)
    return removed


def contains_cover_asset(job_root: Path) -> Optional[Path]:
    """Return the first cover asset stored under ``job_root``."""

    metadata_dir = job_root / "metadata"
    if not metadata_dir.exists():
        return None
    for candidate in sorted(metadata_dir.glob("cover.*")):
        if candidate.is_file():
            return candidate
    return None


__all__ = [
    "build_library_media_url",
    "build_media_record",
    "cleanup_cover_assets",
    "contains_cover_asset",
    "contains_media_files",
    "copy_cover_asset",
    "ensure_source_material",
    "extract_cover_path",
    "is_media_complete",
    "locate_input_epub",
    "load_metadata",
    "mirror_cover_asset",
    "next_source_candidate",
    "normalize_cover_path",
    "purge_media_files",
    "resolve_cover_source",
    "resolve_epub_candidate",
    "resolve_library_path",
    "resolve_source_relative",
    "retarget_chunk_entry",
    "retarget_generated_files",
    "retarget_media_entry",
    "sanitize_source_filename",
    "serialize_media_entries",
    "write_metadata",
]
