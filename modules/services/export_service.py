"""Offline export packaging for interactive player bundles."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import uuid
from typing import Any, Dict, Iterable, Mapping, Optional, Tuple
from urllib.parse import urlparse

from conf.sync_config import AUDIO_SUFFIXES, VIDEO_SUFFIXES
from modules import logging_manager
from modules.core.rendering.constants import LANGUAGE_CODES
from modules.metadata_manager import MetadataLoader
from modules.services.file_locator import FileLocator
from modules.services.pipeline_service import PipelineService
from modules.permissions import can_access, resolve_access_policy
from modules.library import LibraryService, LibraryEntry


LOGGER = logging_manager.get_logger().getChild("export.service")


DEFAULT_EXPORT_PLAYER_TYPE = "interactive-text"
DEFAULT_SCHEMA_VERSION = 1
DEFAULT_READING_BED_ID = "lost-in-the-pages"
DEFAULT_READING_BED_LABEL = "Lost in the Pages"
DEFAULT_READING_BED_URL = "assets/reading-beds/lost-in-the-pages.mp3"
DEFAULT_UNKNOWN_LANGUAGE_CODE = "und"
UNTITLED_BOOK = "Untitled Book"
UNKNOWN_AUTHOR = "Unknown Author"
IMAGE_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".gif",
    ".bmp",
    ".tiff",
    ".tif",
    ".heic",
    ".heif",
}
INLINE_SUBTITLE_SUFFIXES = {".ass", ".srt", ".vtt"}


class ExportServiceError(RuntimeError):
    """Raised when an export bundle cannot be created."""


@dataclass(frozen=True)
class ExportResult:
    export_id: str
    zip_path: Path
    download_name: str
    created_at: str


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resolve_export_assets_root() -> Path:
    override = os.environ.get("EBOOK_EXPORT_PLAYER_ROOT")
    if override:
        return Path(override).expanduser().resolve()
    return Path(__file__).resolve().parents[2] / "web" / "export-dist"


def _resolve_export_root(file_locator: FileLocator) -> Path:
    override = os.environ.get("EBOOK_EXPORT_ROOT")
    if override:
        return Path(override).expanduser().resolve()
    return file_locator.storage_root / "exports"


def _sanitize_filename(value: str, fallback: str = "export") -> str:
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_, ")
    raw = " ".join((value or "").split())
    if not raw:
        return fallback
    normalized = []
    last_sep = False
    for ch in raw:
        if ch in allowed:
            normalized.append(ch)
            last_sep = False
        elif ch.isspace() or ch in {".", ",", ":", ";", "/", "\\", "|"}:
            if not last_sep and normalized:
                normalized.append("-")
                last_sep = True
        else:
            if not last_sep and normalized:
                normalized.append("-")
                last_sep = True
    result = "".join(normalized).strip(" -_,")
    return result or fallback


_LANG_CODE_LOOKUP = {key.lower(): value for key, value in LANGUAGE_CODES.items()}
_LANG_CODE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")


def _camel_key(key: str) -> str:
    parts = key.split("_")
    return parts[0] + "".join(part.capitalize() for part in parts[1:])


def _extract_first_text(payload: Mapping[str, Any], keys: Iterable[str]) -> Optional[str]:
    for key in keys:
        for lookup in (key, _camel_key(key)):
            if lookup not in payload:
                continue
            value = payload.get(lookup)
            if isinstance(value, str):
                trimmed = value.strip()
                if trimmed:
                    return trimmed
            if isinstance(value, list):
                for entry in value:
                    if isinstance(entry, str):
                        trimmed = entry.strip()
                        if trimmed:
                            return trimmed
    return None


def _normalize_language_tag(value: str) -> str:
    parts = [part for part in value.replace("_", "-").split("-") if part]
    if not parts:
        return value
    normalized = [parts[0].lower()]
    for part in parts[1:]:
        if len(part) in {2, 3}:
            normalized.append(part.upper())
        elif len(part) == 4:
            normalized.append(part.title())
        else:
            normalized.append(part.lower())
    return "-".join(normalized)


def _normalize_language_code(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    raw = value.strip()
    if not raw:
        return None
    mapped = _LANG_CODE_LOOKUP.get(raw.lower())
    if mapped:
        return mapped
    if any(ch.isspace() for ch in raw) or not _LANG_CODE_PATTERN.fullmatch(raw):
        return None
    return _normalize_language_tag(raw)


def _coerce_int(value: Any) -> Optional[int]:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _iter_metadata_sections(metadata: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    yield metadata
    for key in ("request", "result", "request_payload", "resume_context", "parameters", "inputs", "options", "config"):
        section = metadata.get(key)
        if isinstance(section, Mapping):
            yield section
            for nested_key in ("inputs", "options", "config"):
                nested = section.get(nested_key)
                if isinstance(nested, Mapping):
                    yield nested


def _resolve_language_labels(
    metadata: Mapping[str, Any],
    book_metadata: Optional[Mapping[str, Any]],
) -> Tuple[Optional[str], Optional[str]]:
    original = None
    target = None
    original_keys = ("original_language", "input_language", "source_language")
    target_keys = ("target_language", "translation_language", "target_languages")

    for section in _iter_metadata_sections(metadata):
        if original is None:
            original = _extract_first_text(section, original_keys)
        if target is None:
            target = _extract_first_text(section, target_keys)
        if original and target:
            break

    if original is None:
        original = _extract_first_text(metadata, ("book_language", "language"))
    if target is None:
        target = _extract_first_text(metadata, ("language", "book_language"))

    if isinstance(book_metadata, Mapping):
        if original is None:
            original = _extract_first_text(book_metadata, ("original_language", "input_language", "book_language", "language"))
        if target is None:
            target = _extract_first_text(book_metadata, ("target_language", "translation_language", "target_languages", "language", "book_language"))

    return original, target


def _resolve_sentence_range(
    metadata: Mapping[str, Any],
    chunks: Iterable[Mapping[str, Any]],
) -> Tuple[Optional[int], Optional[int]]:
    start_candidates: list[int] = []
    end_candidates: list[int] = []

    for chunk in chunks:
        start = _coerce_int(chunk.get("start_sentence") or chunk.get("startSentence"))
        end = _coerce_int(chunk.get("end_sentence") or chunk.get("endSentence"))
        sentence_count = _coerce_int(chunk.get("sentence_count") or chunk.get("sentenceCount"))
        if start is not None and end is None and sentence_count:
            end = start + sentence_count - 1
        if end is not None and start is None and sentence_count:
            start = end - sentence_count + 1
        if start is not None:
            start_candidates.append(start)
        if end is not None:
            end_candidates.append(end)

    if not start_candidates:
        for section in _iter_metadata_sections(metadata):
            start = _coerce_int(section.get("start_sentence") or section.get("startSentence"))
            if start is not None:
                start_candidates.append(start)
                break
    if not end_candidates:
        for section in _iter_metadata_sections(metadata):
            end = _coerce_int(section.get("end_sentence") or section.get("endSentence"))
            if end is not None:
                end_candidates.append(end)
                break

    start_value = min(start_candidates) if start_candidates else None
    end_value = max(end_candidates) if end_candidates else None
    if start_value is None and end_value is None:
        return None, None
    if start_value is None and end_value is not None:
        start_value = end_value
    if end_value is None and start_value is not None:
        end_value = start_value
    return start_value, end_value


def _normalize_label_text(value: Optional[str], fallback: str) -> str:
    if not value:
        return fallback
    trimmed = " ".join(value.strip().split())
    return trimmed or fallback


def _resolve_book_metadata_section(metadata: Mapping[str, Any]) -> Optional[Mapping[str, Any]]:
    candidate = metadata.get("book_metadata")
    return candidate if isinstance(candidate, Mapping) else None


def _is_book_export(
    item_type: Optional[str],
    job_type: Optional[str],
    book_metadata: Mapping[str, Any],
) -> bool:
    if isinstance(item_type, str) and item_type.strip().lower() == "book":
        return True
    if isinstance(job_type, str) and "book" in job_type.lower():
        return True
    for key in ("book_title", "title", "book_name", "book_author", "author"):
        value = book_metadata.get(key)
        if isinstance(value, str) and value.strip():
            return True
    nested = _resolve_book_metadata_section(book_metadata)
    if isinstance(nested, Mapping):
        for key in ("book_title", "title", "book_name", "book_author", "author"):
            value = nested.get(key)
            if isinstance(value, str) and value.strip():
                return True
    return False


def _has_interactive_chunks(chunks: Iterable[Mapping[str, Any]]) -> bool:
    for chunk in chunks:
        if not isinstance(chunk, Mapping):
            continue
        sentences = chunk.get("sentences")
        if isinstance(sentences, list) and len(sentences) > 0:
            return True
        sentence_count = _coerce_int(chunk.get("sentence_count") or chunk.get("sentenceCount"))
        if sentence_count and sentence_count > 0:
            return True
    return False


def _is_video_export(
    *,
    item_type: Optional[str],
    job_type: Optional[str],
    metadata: Mapping[str, Any],
    media_map: Mapping[str, list[Dict[str, Any]]],
    chunks: Iterable[Mapping[str, Any]],
) -> bool:
    if isinstance(item_type, str) and item_type.strip().lower() == "video":
        return True
    if isinstance(job_type, str):
        normalized = job_type.strip().lower()
        if normalized == "youtube_dub" or "video" in normalized:
            return True
    if isinstance(metadata.get("youtube_dub"), Mapping):
        return True
    result_section = metadata.get("result")
    if isinstance(result_section, Mapping) and isinstance(result_section.get("youtube_dub"), Mapping):
        return True
    has_video_media = bool(media_map.get("video"))
    if has_video_media and not _has_interactive_chunks(chunks):
        return True
    return False


def _build_export_label(
    *,
    metadata: Mapping[str, Any],
    book_metadata: Mapping[str, Any],
    chunks: Iterable[Mapping[str, Any]],
    library_entry: Optional[LibraryEntry] = None,
) -> Optional[str]:
    nested_book = _resolve_book_metadata_section(book_metadata)
    author_candidate = library_entry.author if library_entry else None
    title_candidate = library_entry.book_title if library_entry else None

    if not author_candidate:
        author_candidate = _extract_first_text(
            nested_book or book_metadata,
            ("book_author", "author", "writer", "creator"),
        )
    if not title_candidate:
        title_candidate = _extract_first_text(
            nested_book or book_metadata,
            ("book_title", "title", "book_name", "name"),
        )

    author = _normalize_label_text(author_candidate, UNKNOWN_AUTHOR)
    title = _normalize_label_text(title_candidate, UNTITLED_BOOK)
    original_label, target_label = _resolve_language_labels(metadata, nested_book or book_metadata)
    original_code = _normalize_language_code(original_label) or DEFAULT_UNKNOWN_LANGUAGE_CODE
    target_code = _normalize_language_code(target_label) or DEFAULT_UNKNOWN_LANGUAGE_CODE
    start_sentence, end_sentence = _resolve_sentence_range(metadata, chunks)
    if start_sentence is None:
        start_sentence = 1
    if end_sentence is None:
        end_sentence = start_sentence

    return f"{author}, {title}, {original_code}-{target_code}, sentence {start_sentence}-{end_sentence}"


def _strip_url_suffix(value: str) -> str:
    base = value.split("#", 1)[0]
    return base.split("?", 1)[0]


def _normalize_relative_path(value: Optional[str], *, job_root: Path) -> Optional[str]:
    if not value:
        return None
    raw = value.strip()
    if not raw:
        return None
    if raw.startswith("http://") or raw.startswith("https://"):
        parsed = urlparse(raw)
        raw = parsed.path or ""
    raw = _strip_url_suffix(raw)
    if not raw:
        return None
    normalized = raw.replace("\\", "/")
    candidate = Path(normalized)
    if candidate.is_absolute():
        try:
            candidate = candidate.resolve().relative_to(job_root.resolve())
        except ValueError:
            parts = [part for part in candidate.parts if part not in {"", "."}]
            if "media" in parts:
                candidate = Path(*parts[parts.index("media"):])
            elif "metadata" in parts:
                candidate = Path(*parts[parts.index("metadata"):])
            else:
                return None
    relative = candidate.as_posix().lstrip("/")
    return relative or None


def _resolve_media_category(entry: Mapping[str, Any]) -> Optional[str]:
    raw_type = entry.get("type")
    if isinstance(raw_type, str):
        normalized = raw_type.strip().lower()
        if normalized in {"audio", "video", "text"}:
            return normalized
        if normalized == "image" or normalized.startswith("image_"):
            return None
    candidate = entry.get("relative_path") or entry.get("path") or entry.get("url")
    suffix = ""
    if isinstance(candidate, str):
        suffix = Path(candidate.replace("\\", "/")).suffix.lower()
    if suffix in IMAGE_SUFFIXES:
        return None
    if suffix in AUDIO_SUFFIXES:
        return "audio"
    if suffix in VIDEO_SUFFIXES:
        return "video"
    return "text"


def _sanitize_media_entry(entry: Mapping[str, Any], *, job_root: Path) -> Optional[Dict[str, Any]]:
    relative = _normalize_relative_path(
        entry.get("relative_path") if isinstance(entry.get("relative_path"), str) else None,
        job_root=job_root,
    )
    if relative is None:
        relative = _normalize_relative_path(
            entry.get("path") if isinstance(entry.get("path"), str) else None,
            job_root=job_root,
        )
    if relative is None:
        return None
    payload: Dict[str, Any] = {}
    for key in (
        "type",
        "chunk_id",
        "range_fragment",
        "start_sentence",
        "end_sentence",
        "name",
        "size",
        "updated_at",
        "source",
    ):
        if key in entry:
            payload[key] = entry[key]
    payload["relative_path"] = relative
    payload["path"] = relative
    payload["url"] = relative
    return payload


def _collect_inline_subtitles(
    media_map: Mapping[str, Iterable[Mapping[str, Any]]], *, job_root: Path
) -> Optional[Dict[str, str]]:
    inline: Dict[str, str] = {}
    for entries in media_map.values():
        if not isinstance(entries, Iterable):
            continue
        for entry in entries:
            if not isinstance(entry, Mapping):
                continue
            candidate = entry.get("relative_path") or entry.get("url") or entry.get("path")
            if not isinstance(candidate, str) or not candidate.strip():
                continue
            normalized = _normalize_relative_path(candidate, job_root=job_root)
            if not normalized:
                continue
            suffix = Path(normalized).suffix.lower()
            if suffix not in INLINE_SUBTITLE_SUFFIXES:
                continue
            source_path = job_root / normalized
            if not source_path.exists():
                continue
            try:
                payload = source_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                payload = source_path.read_text(encoding="utf-8", errors="replace")
            inline[normalized] = payload
    return inline or None


def _sanitize_audio_tracks(
    payload: Mapping[str, Any], *, job_root: Path
) -> Optional[Dict[str, Dict[str, Any]]]:
    if not isinstance(payload, Mapping):
        return None
    normalized: Dict[str, Dict[str, Any]] = {}
    for key, value in payload.items():
        if not isinstance(key, str):
            continue
        entry: Dict[str, Any] = {}
        raw_path: Optional[str] = None
        raw_url: Optional[str] = None
        if isinstance(value, Mapping):
            raw_path = value.get("path") if isinstance(value.get("path"), str) else None
            raw_url = value.get("url") if isinstance(value.get("url"), str) else None
            duration_value = value.get("duration")
            sample_rate_value = value.get("sampleRate")
            if duration_value is not None:
                try:
                    entry["duration"] = round(float(duration_value), 6)
                except (TypeError, ValueError):
                    pass
            if sample_rate_value is not None:
                try:
                    entry["sampleRate"] = int(sample_rate_value)
                except (TypeError, ValueError):
                    pass
        elif isinstance(value, str):
            raw_path = value
        resolved = (
            _normalize_relative_path(raw_url, job_root=job_root)
            if raw_url
            else _normalize_relative_path(raw_path, job_root=job_root)
        )
        if resolved:
            entry["path"] = resolved
            entry["url"] = resolved
        if entry:
            normalized[key] = entry
    return normalized or None


def _sanitize_sentence_images(sentence: Mapping[str, Any], *, job_root: Path) -> Dict[str, Any]:
    payload = dict(sentence)
    image_payload = payload.get("image")
    if isinstance(image_payload, Mapping):
        image_entry = dict(image_payload)
        raw_path = image_entry.get("path") if isinstance(image_entry.get("path"), str) else None
        resolved = _normalize_relative_path(raw_path, job_root=job_root)
        if resolved:
            image_entry["path"] = resolved
        payload["image"] = image_entry
    for key in ("image_path", "imagePath"):
        raw_value = payload.get(key)
        if isinstance(raw_value, str):
            resolved = _normalize_relative_path(raw_value, job_root=job_root)
            if resolved:
                payload[key] = resolved
    return payload


def _sanitize_book_metadata(metadata: Mapping[str, Any], *, job_root: Path) -> Dict[str, Any]:
    payload = {key: value for key, value in metadata.items() if key not in {"generated_files", "chunk_manifest", "chunks"}}
    cover_candidates = [
        payload.get("job_cover_asset"),
        payload.get("job_cover_asset_url"),
        payload.get("book_cover_file"),
    ]
    resolved_cover: Optional[str] = None
    for candidate in cover_candidates:
        if isinstance(candidate, str):
            resolved_cover = _normalize_relative_path(candidate, job_root=job_root)
            if resolved_cover:
                break
    if resolved_cover:
        payload["job_cover_asset"] = resolved_cover
        payload["job_cover_asset_url"] = resolved_cover
        payload.setdefault("book_cover_file", resolved_cover)
    return payload


def _ensure_export_assets(assets_root: Path) -> Path:
    if not assets_root.exists():
        raise ExportServiceError(
            "Export assets root "
            f"{assets_root} does not exist. Build export assets with "
            "`cd web && vite build --mode export` (or `pnpm -C web build -- --mode export`), "
            "or set EBOOK_EXPORT_PLAYER_ROOT."
        )
    export_html = assets_root / "export.html"
    if export_html.exists():
        return export_html
    fallback = assets_root / "index.html"
    if fallback.exists():
        return fallback
    raise ExportServiceError(f"No export template found in {assets_root}.")


_SCRIPT_TAG_RE = re.compile(r'<script\b[^>]*\bsrc="([^"]+)"[^>]*></script>', re.IGNORECASE)
_MODULEPRELOAD_RE = re.compile(r'\s*<link\b[^>]*rel="modulepreload"[^>]*>\s*', re.IGNORECASE)
_CROSSORIGIN_RE = re.compile(r'\s+crossorigin(?:="[^"]*")?', re.IGNORECASE)


def _rewrite_export_index_for_file_scheme(index_path: Path) -> None:
    try:
        html = index_path.read_text(encoding="utf-8")
    except OSError:
        return

    def replace_script(match: re.Match[str]) -> str:
        src = match.group(1)
        if src.endswith("player-data.js"):
            return f'<script src="{src}"></script>'
        return f'<script src="{src}" defer></script>'

    updated = _SCRIPT_TAG_RE.sub(replace_script, html)
    updated = _MODULEPRELOAD_RE.sub("", updated)
    updated = _CROSSORIGIN_RE.sub("", updated)

    if updated != html:
        index_path.write_text(updated, encoding="utf-8")


class ExportService:
    """Build offline export bundles for completed jobs or library entries."""

    def __init__(
        self,
        pipeline_service: PipelineService,
        library_service: LibraryService,
        file_locator: FileLocator,
        *,
        assets_root: Optional[Path] = None,
        export_root: Optional[Path] = None,
    ) -> None:
        self._pipeline_service = pipeline_service
        self._library_service = library_service
        self._file_locator = file_locator
        self._assets_root = assets_root or _resolve_export_assets_root()
        self._export_root = export_root or _resolve_export_root(file_locator)

    def create_export(
        self,
        *,
        source_kind: str,
        source_id: str,
        player_type: str = DEFAULT_EXPORT_PLAYER_TYPE,
        user_id: Optional[str] = None,
        user_role: Optional[str] = None,
    ) -> ExportResult:
        if player_type != DEFAULT_EXPORT_PLAYER_TYPE:
            raise ExportServiceError(f"Unsupported player type: {player_type}")
        if source_kind == "job":
            job = self._pipeline_service.get_job(source_id, user_id=user_id, user_role=user_role)
            job_root = self._file_locator.resolve_path(job.job_id)
            metadata = self._load_manifest(job_root)
            generated_files = self._load_generated_files(job_root, metadata)
            return self._build_export(
                job_id=job.job_id,
                job_root=job_root,
                source_kind=source_kind,
                job_type=job.job_type if hasattr(job, "job_type") else None,
                item_type=metadata.get("item_type"),
                metadata=metadata,
                generated_files=generated_files,
            )
        if source_kind == "library":
            entry = self._library_service.repository.get_entry_by_id(source_id)
            if entry is None:
                raise ExportServiceError(f"Library entry {source_id} not found.")
            metadata_payload = entry.metadata.data if hasattr(entry.metadata, "data") else {}
            owner_id = entry.owner_id or metadata_payload.get("user_id") or metadata_payload.get("owner_id")
            if isinstance(owner_id, str):
                owner_id = owner_id.strip() or None
            policy = resolve_access_policy(metadata_payload.get("access"), default_visibility="public")
            if not can_access(
                policy,
                owner_id=owner_id,
                user_id=user_id,
                user_role=user_role,
                permission="view",
            ):
                raise PermissionError("Not authorized to export this library entry")
            job_root = Path(entry.library_path)
            metadata = self._load_manifest(job_root)
            generated_files = self._load_generated_files(job_root, metadata)
            return self._build_export(
                job_id=entry.id,
                job_root=job_root,
                source_kind=source_kind,
                job_type=metadata.get("job_type"),
                item_type=entry.item_type,
                metadata=metadata,
                generated_files=generated_files,
                library_entry=entry,
            )
        raise ExportServiceError(f"Unsupported source kind: {source_kind}")

    def resolve_export_download(self, export_id: str) -> ExportResult:
        export_root = self._export_root
        meta_path = export_root / f"{export_id}.json"
        zip_path = export_root / f"{export_id}.zip"
        if not meta_path.exists() or not zip_path.exists():
            raise ExportServiceError("Export not found.")
        try:
            payload = json.loads(meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ExportServiceError("Export metadata is corrupted.") from exc
        download_name = payload.get("download_name") or f"{export_id}.zip"
        created_at = payload.get("created_at") or _now_iso()
        return ExportResult(
            export_id=export_id,
            zip_path=zip_path,
            download_name=download_name,
            created_at=created_at,
        )

    def _load_manifest(self, job_root: Path) -> Dict[str, Any]:
        manifest_path = job_root / "metadata" / "job.json"
        if not manifest_path.exists():
            raise ExportServiceError(f"Missing metadata manifest at {manifest_path}.")
        loader = MetadataLoader(job_root)
        return loader.load_manifest()

    def _load_generated_files(self, job_root: Path, metadata: Mapping[str, Any]) -> Mapping[str, Any]:
        generated = metadata.get("generated_files")
        if isinstance(generated, Mapping):
            return generated
        loader = MetadataLoader(job_root)
        return loader.get_generated_files()

    def _build_export(
        self,
        *,
        job_id: str,
        job_root: Path,
        source_kind: str,
        job_type: Optional[str],
        item_type: Optional[str],
        metadata: Mapping[str, Any],
        generated_files: Mapping[str, Any],
        library_entry: Optional[LibraryEntry] = None,
    ) -> ExportResult:
        complete_flag = generated_files.get("complete")
        media_completed = (
            bool(complete_flag)
            if isinstance(complete_flag, bool)
            else bool(metadata.get("media_completed"))
            if isinstance(metadata.get("media_completed"), bool)
            else False
        )
        chunks_section = generated_files.get("chunks")
        files_section = generated_files.get("files")
        has_media = bool(chunks_section) or bool(files_section)
        if not has_media:
            raise ExportServiceError("No generated media found for export.")
        if not media_completed:
            raise ExportServiceError("Media is still processing; export is only available for completed jobs.")

        assets_root = self._assets_root
        export_root = self._export_root
        export_root.mkdir(parents=True, exist_ok=True)
        export_id = uuid.uuid4().hex
        export_dir = export_root / export_id
        export_dir.mkdir(parents=True, exist_ok=True)

        template_path = _ensure_export_assets(assets_root)
        shutil.copy2(template_path, export_dir / "index.html")
        _rewrite_export_index_for_file_scheme(export_dir / "index.html")

        assets_dir = assets_root / "assets"
        if assets_dir.exists():
            shutil.copytree(assets_dir, export_dir / "assets", dirs_exist_ok=True)

        for folder in ("media", "metadata"):
            source_dir = job_root / folder
            if source_dir.exists():
                shutil.copytree(source_dir, export_dir / folder, dirs_exist_ok=True)

        loader = MetadataLoader(job_root)
        chunk_payloads = loader.load_chunks(include_sentences=True)
        media_map: Dict[str, list[Dict[str, Any]]] = {}
        chunk_records: list[Dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()

        for chunk in chunk_payloads:
            if not isinstance(chunk, Mapping):
                continue
            files_raw = chunk.get("files")
            chunk_files: list[Dict[str, Any]] = []
            if isinstance(files_raw, list):
                for entry in files_raw:
                    if not isinstance(entry, Mapping):
                        continue
                    sanitized = _sanitize_media_entry(entry, job_root=job_root)
                    if not sanitized:
                        continue
                    category = _resolve_media_category(sanitized)
                    if category:
                        signature = (sanitized.get("url") or "", category)
                        if signature not in seen:
                            seen.add(signature)
                            media_map.setdefault(category, []).append(sanitized)
                    chunk_files.append(sanitized)

            chunk_record = {
                key: value
                for key, value in chunk.items()
                if key
                not in {
                    "files",
                    "metadata_url",
                }
            }
            metadata_path = chunk_record.get("metadata_path")
            if isinstance(metadata_path, str):
                resolved_meta = _normalize_relative_path(metadata_path, job_root=job_root)
                if resolved_meta:
                    chunk_record["metadata_path"] = resolved_meta
                else:
                    chunk_record.pop("metadata_path", None)
            chunk_record["files"] = chunk_files
            sentences = chunk.get("sentences")
            if isinstance(sentences, list):
                chunk_record["sentences"] = [
                    _sanitize_sentence_images(sentence, job_root=job_root)
                    if isinstance(sentence, Mapping)
                    else sentence
                    for sentence in sentences
                ]
            audio_tracks_raw = chunk.get("audio_tracks") or chunk.get("audioTracks")
            audio_tracks = _sanitize_audio_tracks(audio_tracks_raw, job_root=job_root)
            if audio_tracks:
                chunk_record["audio_tracks"] = audio_tracks
                chunk_record["audioTracks"] = audio_tracks
            chunk_records.append(chunk_record)

        files_section = generated_files.get("files")
        if isinstance(files_section, list):
            for entry in files_section:
                if not isinstance(entry, Mapping):
                    continue
                sanitized = _sanitize_media_entry(entry, job_root=job_root)
                if not sanitized:
                    continue
                category = _resolve_media_category(sanitized)
                if not category:
                    continue
                signature = (sanitized.get("url") or "", category)
                if signature in seen:
                    continue
                seen.add(signature)
                media_map.setdefault(category, []).append(sanitized)

        complete = bool(complete_flag) if isinstance(complete_flag, bool) else False

        book_metadata = _sanitize_book_metadata(metadata, job_root=job_root)
        is_video_export = _is_video_export(
            item_type=item_type,
            job_type=job_type,
            metadata=metadata,
            media_map=media_map,
            chunks=chunk_payloads,
        )
        is_book_export = False if is_video_export else _is_book_export(item_type, job_type, book_metadata)
        export_label = (
            _build_export_label(
                metadata=metadata,
                book_metadata=book_metadata,
                chunks=chunk_payloads,
                library_entry=library_entry,
            )
            if is_book_export
            else None
        )
        export_player_type = "video" if is_video_export else DEFAULT_EXPORT_PLAYER_TYPE
        inline_subtitles = _collect_inline_subtitles(media_map, job_root=job_root)

        source_payload: Dict[str, Any] = {
            "kind": source_kind,
            "id": job_id,
            "job_type": job_type,
            "item_type": item_type,
        }
        if library_entry:
            source_payload["label"] = library_entry.book_title or None
            source_payload["author"] = library_entry.author or None

        export_manifest = {
            "schema_version": DEFAULT_SCHEMA_VERSION,
            "player": {
                "type": export_player_type,
                "features": {
                    "linguist": False,
                    "painter": False,
                    "search": True,
                },
            },
            "source": source_payload,
            "book_metadata": book_metadata,
            "media": media_map,
            "chunks": chunk_records,
            "complete": complete,
            "reading_bed": {
                "id": DEFAULT_READING_BED_ID,
                "label": DEFAULT_READING_BED_LABEL,
                "url": DEFAULT_READING_BED_URL,
            },
            "created_at": _now_iso(),
        }
        if inline_subtitles:
            export_manifest["inline_subtitles"] = inline_subtitles
        if export_label:
            export_manifest["export_label"] = export_label

        manifest_path = export_dir / "manifest.json"
        manifest_path.write_text(
            json.dumps(export_manifest, ensure_ascii=True, indent=2),
            encoding="utf-8",
        )
        player_data_path = export_dir / "player-data.js"
        player_data_path.write_text(
            "window.__EXPORT_DATA__ = "
            + json.dumps(export_manifest, ensure_ascii=True)
            + ";\n",
            encoding="utf-8",
        )

        if export_label:
            base_name = _sanitize_filename(export_label, fallback="export")
            download_name = f"{base_name}.zip"
        else:
            download_label = book_metadata.get("book_title") or job_id
            download_name = f"{_sanitize_filename(str(download_label), fallback='export')}-player.zip"

        zip_path = export_root / f"{export_id}.zip"
        shutil.make_archive(str(zip_path.with_suffix("")), "zip", root_dir=export_dir)
        meta_path = export_root / f"{export_id}.json"
        meta_path.write_text(
            json.dumps(
                {
                    "export_id": export_id,
                    "download_name": download_name,
                    "created_at": export_manifest["created_at"],
                },
                ensure_ascii=True,
                indent=2,
            ),
            encoding="utf-8",
        )
        return ExportResult(
            export_id=export_id,
            zip_path=zip_path,
            download_name=download_name,
            created_at=export_manifest["created_at"],
        )
