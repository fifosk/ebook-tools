"""Helpers for searching generated ebook content."""

from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime, timezone
import re
import textwrap
from html import unescape
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Mapping, MutableMapping, Optional, Sequence, Tuple

from ..metadata_manager import MetadataLoader
from ..services.file_locator import FileLocator
from ..services.job_manager.job import PipelineJob
from ..subtitles.io import _read_subtitle_text, load_subtitle_cues
from ..subtitles.models import SubtitleCue
from ..subtitles.text import _normalize_text

MediaBucket = Dict[str, List[MutableMapping[str, object]]]

_TEXT_TYPES = {
    "text",
    "html",
    "written",
    "doc",
    "docx",
    "rtf",
    "pdf",
}
_AUDIO_TYPES = {
    "audio",
    "mp3",
    "wav",
    "flac",
}
_VIDEO_TYPES = {
    "video",
    "mp4",
    "webm",
    "mov",
}

_SCRIPT_STYLE_PATTERN = re.compile(r"<\s*(script|style)[^>]*>.*?<\s*/\s*\1\s*>", re.IGNORECASE | re.DOTALL)
_TAG_PATTERN = re.compile(r"<[^>]+>")
_WHITESPACE_PATTERN = re.compile(r"\s+")
_SUBTITLE_EXTENSIONS = {".srt", ".vtt", ".ass"}
_SUBTITLE_EXTENSION_ORDER = [".ass", ".vtt", ".srt"]
_DEFAULT_ASS_FIELDS = [
    "layer",
    "start",
    "end",
    "style",
    "name",
    "marginl",
    "marginr",
    "marginv",
    "effect",
    "text",
]
_ASS_TIMESTAMP_PATTERN = re.compile(
    r"^(?P<hours>\d+):(?P<minutes>\d{2}):(?P<seconds>\d{2})[.](?P<centis>\d{2})$"
)


@dataclass(slots=True)
class SearchMediaResult:
    """Describes a chunk of generated media that matches a search query."""

    job_id: str
    job_label: str | None
    base_id: str | None
    chunk_id: str | None
    chunk_index: int | None
    chunk_total: int | None
    range_fragment: str | None
    start_sentence: int | None
    end_sentence: int | None
    snippet: str
    occurrence_count: int
    match_start: int | None
    match_end: int | None
    text_length: int | None
    offset_ratio: float | None
    approximate_time_seconds: float | None
    media: MediaBucket
    cue_start_seconds: float | None = None
    cue_end_seconds: float | None = None
def _coerce_inputs_mapping(candidate: object) -> Optional[Mapping[str, object]]:
    if candidate is None:
        return None
    if isinstance(candidate, Mapping):
        return candidate
    if is_dataclass(candidate):
        try:
            return asdict(candidate)
        except TypeError:
            pass
    namespace = getattr(candidate, "__dict__", None)
    if isinstance(namespace, Mapping):
        return dict(namespace)
    return None


def _normalise_media_type(raw_type: object) -> Optional[str]:
    if not isinstance(raw_type, str):
        return None
    token = raw_type.strip().lower()
    if token in _AUDIO_TYPES:
        return "audio"
    if token in _VIDEO_TYPES:
        return "video"
    if token in _TEXT_TYPES or token.startswith("html"):
        return "text"
    return None


def _resolve_job_label(job: PipelineJob) -> str | None:
    """Attempt to derive a friendly label for ``job``."""

    inputs: Mapping[str, object] | None = None
    if job.request is not None and getattr(job.request, "inputs", None) is not None:
        inputs = _coerce_inputs_mapping(job.request.inputs)
    elif job.resume_context and isinstance(job.resume_context, Mapping):
        candidate = job.resume_context.get("inputs")
        if isinstance(candidate, Mapping):
            inputs = candidate
    elif job.request_payload and isinstance(job.request_payload, Mapping):
        candidate = job.request_payload.get("inputs")
        if isinstance(candidate, Mapping):
            inputs = candidate

    base_output = None
    if inputs:
        base_output = inputs.get("base_output_file")
        if isinstance(base_output, str) and base_output.strip():
            label = Path(base_output).stem
            return label or None

        metadata = inputs.get("book_metadata")
        if isinstance(metadata, Mapping):
            title = metadata.get("title")
            if isinstance(title, str) and title.strip():
                return title.strip()

    if job.request and getattr(job.request, "inputs", None) is not None:
        candidate = getattr(job.request.inputs, "base_output_file", None)
        if isinstance(candidate, str) and candidate.strip():
            label = Path(candidate).stem
            if label:
                return label

    return None


def _coerce_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return None
    return None


def _load_text_from_entry(job_id: str, entry: Mapping[str, object], locator: FileLocator) -> str | None:
    """Return the plain-text content for the provided generated file entry."""

    path_value = entry.get("path")
    relative = entry.get("relative_path")

    candidate: Optional[Path] = None
    if isinstance(path_value, str) and path_value.strip():
        candidate = Path(path_value)
    if (candidate is None or not candidate.is_file()) and isinstance(relative, str) and relative.strip():
        try:
            candidate = locator.resolve_path(job_id, relative)
        except ValueError:
            candidate = None

    if candidate is None or not candidate.is_file():
        return None

    try:
        raw_html = candidate.read_text(encoding="utf-8")
    except OSError:
        return None

    if not raw_html.strip():
        return ""

    stripped = _SCRIPT_STYLE_PATTERN.sub(" ", raw_html)
    stripped = re.sub(r"<br\s*/?>", "\n", stripped, flags=re.IGNORECASE)
    stripped = re.sub(r"</p\s*>", "\n", stripped, flags=re.IGNORECASE)
    stripped = _TAG_PATTERN.sub(" ", stripped)
    text = unescape(stripped)
    text = _WHITESPACE_PATTERN.sub(" ", text)
    return text.strip()


def _iterate_chunk_entries(generated: Mapping[str, object]) -> Iterator[Mapping[str, object]]:
    chunks = generated.get("chunks")
    if not isinstance(chunks, Sequence):
        return iter(())
    return (chunk for chunk in chunks if isinstance(chunk, Mapping))


def _find_matches(text: str, query: str) -> List[Tuple[int, int]]:
    lowered = text.lower()
    needle = query.lower()
    matches: List[Tuple[int, int]] = []
    start = 0
    length = len(needle)
    while True:
        position = lowered.find(needle, start)
        if position == -1:
            break
        matches.append((position, position + length))
        start = position + length
    return matches


def _build_snippet(text: str, matches: Sequence[Tuple[int, int]], context: int = 80) -> Tuple[str, int]:
    if not matches:
        snippet = text[: context * 2]
        shortened = textwrap.shorten(snippet, width=context * 2 + 20, placeholder="…")
        return shortened, 0

    first_start, first_end = matches[0]
    span_start = max(0, first_start - context)
    span_end = min(len(text), first_end + context)

    while span_start > 0 and not text[span_start - 1].isspace():
        span_start -= 1

    while span_end < len(text) and not text[span_end - 1].isspace():
        span_end += 1

    snippet = text[span_start:span_end].strip()
    prefix = "…" if span_start > 0 else ""
    suffix = "…" if span_end < len(text) else ""
    snippet_with_context = f"{prefix}{snippet}{suffix}".strip()
    return snippet_with_context, len(matches)


def _gather_media_entries(
    job_id: str,
    files: Iterable[Mapping[str, object]],
    locator: FileLocator,
) -> MediaBucket:
    buckets: MediaBucket = {
        "text": [],
        "audio": [],
        "video": [],
    }

    for entry in files:
        media_type = _normalise_media_type(entry.get("type"))
        if media_type is None:
            continue

        relative_path = entry.get("relative_path")
        path_value = entry.get("path")
        absolute: Optional[Path] = None

        if isinstance(path_value, str) and path_value.strip():
            candidate = Path(path_value)
            absolute = candidate if candidate.exists() else None
        if absolute is None and isinstance(relative_path, str) and relative_path.strip():
            try:
                candidate = locator.resolve_path(job_id, relative_path)
            except ValueError:
                candidate = None
            if candidate is not None and candidate.exists():
                absolute = candidate

        entry_url = entry.get("url")
        if isinstance(entry_url, str) and entry_url.strip():
            url: Optional[str] = entry_url.strip()
        else:
            url = None
            if isinstance(relative_path, str) and relative_path.strip():
                try:
                    url = locator.resolve_url(job_id, relative_path)
                except ValueError:
                    url = None

        size: Optional[int] = None
        updated_at: Optional[datetime] = None
        if absolute is not None and absolute.exists():
            try:
                stat_result = absolute.stat()
            except OSError:
                stat_result = None
            if stat_result is not None:
                size = stat_result.st_size
                updated_at = datetime.fromtimestamp(stat_result.st_mtime, tz=timezone.utc)

        source_value = entry.get("source")
        if isinstance(source_value, str) and source_value.strip().lower() == "live":
            source = "live"
        else:
            source = "completed"
        name: str
        path_candidate = relative_path or path_value
        if isinstance(path_candidate, str) and path_candidate.strip():
            name = Path(path_candidate).name
        else:
            name = "media"

        normalized_relative: Optional[str] = None
        if isinstance(relative_path, str) and relative_path.strip():
            trimmed_relative = relative_path.strip().lstrip("./")
            if trimmed_relative.startswith("media/"):
                stripped = trimmed_relative.split("/", 1)[1]
                normalized_relative = stripped or trimmed_relative
            else:
                normalized_relative = trimmed_relative

        payload: MutableMapping[str, object] = {
            "name": name,
            "source": source,
        }
        if url:
            payload["url"] = url
        if size is not None:
            payload["size"] = size
        if updated_at is not None:
            payload["updated_at"] = updated_at.isoformat()
        if normalized_relative is not None:
            payload["relative_path"] = normalized_relative
        elif isinstance(relative_path, str) and relative_path.strip():
            payload["relative_path"] = relative_path.strip()
        if isinstance(path_value, str) and path_value.strip():
            payload["path"] = path_value

        buckets.setdefault(media_type, []).append(payload)

    return buckets


def _coerce_existing_path(raw: object) -> Optional[Path]:
    if isinstance(raw, Path):
        candidate = raw.expanduser()
    elif isinstance(raw, str):
        text = raw.strip()
        if not text:
            return None
        candidate = Path(text).expanduser()
    else:
        return None
    try:
        return candidate if candidate.exists() else None
    except OSError:
        return None


def _resolve_job_root(job: PipelineJob, locator: FileLocator) -> Optional[Path]:
    override = getattr(job, "job_root", None)
    if override is None:
        override = getattr(job, "library_path", None)
    candidate = _coerce_existing_path(override)
    if candidate is not None:
        return candidate

    try:
        default_root = locator.job_root(job.job_id)
    except Exception:
        return None
    return default_root if default_root.exists() else None


def _extract_entry_extension(entry: Mapping[str, object]) -> str:
    for key in ("relative_path", "path", "url", "name"):
        value = entry.get(key)
        if not isinstance(value, str):
            continue
        cleaned = value.strip()
        if not cleaned:
            continue
        cleaned = cleaned.split("?", 1)[0].split("#", 1)[0]
        suffix = Path(cleaned).suffix.lower()
        if suffix:
            return suffix
    return ""


def _subtitle_entry_identity(entry: Mapping[str, object]) -> Optional[str]:
    for key in ("relative_path", "path", "url", "name"):
        value = entry.get(key)
        if not isinstance(value, str):
            continue
        cleaned = value.strip()
        if not cleaned:
            continue
        cleaned = cleaned.split("?", 1)[0].split("#", 1)[0]
        if cleaned:
            return cleaned.lower()
    return None


def _subtitle_entry_base_id(entry: Mapping[str, object]) -> Optional[str]:
    identity = _subtitle_entry_identity(entry)
    if not identity:
        return None
    stem = Path(identity).stem
    return stem.lower() if stem else None


def _select_preferred_subtitle_keys(
    chunks: Sequence[Mapping[str, object]],
) -> set[str]:
    preferred: Dict[str, Tuple[str, int]] = {}
    for chunk in chunks:
        files = chunk.get("files")
        if not isinstance(files, Iterable):
            continue
        for entry in files:
            if not isinstance(entry, Mapping):
                continue
            suffix = _extract_entry_extension(entry)
            if suffix not in _SUBTITLE_EXTENSIONS:
                continue
            identity = _subtitle_entry_identity(entry)
            if not identity:
                continue
            base_id = _subtitle_entry_base_id(entry)
            group_key = base_id or identity
            rank = (
                _SUBTITLE_EXTENSION_ORDER.index(suffix)
                if suffix in _SUBTITLE_EXTENSION_ORDER
                else len(_SUBTITLE_EXTENSION_ORDER)
            )
            existing = preferred.get(group_key)
            if existing is None or rank < existing[1]:
                preferred[group_key] = (identity, rank)
    return {value[0] for value in preferred.values()}


def _resolve_entry_path(
    job_id: str,
    entry: Mapping[str, object],
    locator: FileLocator,
) -> Optional[Path]:
    path_value = entry.get("path")
    if isinstance(path_value, str) and path_value.strip():
        candidate = Path(path_value)
        try:
            if candidate.exists():
                return candidate
        except OSError:
            pass
    relative = entry.get("relative_path")
    if isinstance(relative, str) and relative.strip():
        try:
            candidate = locator.resolve_path(job_id, relative)
        except ValueError:
            candidate = None
        if candidate is not None:
            try:
                if candidate.exists():
                    return candidate
            except OSError:
                return None
    return None


def _parse_ass_timestamp(value: str) -> Optional[float]:
    match = _ASS_TIMESTAMP_PATTERN.match(value.strip())
    if not match:
        return None
    hours = int(match.group("hours"))
    minutes = int(match.group("minutes"))
    seconds = int(match.group("seconds"))
    centis = int(match.group("centis"))
    return hours * 3600 + minutes * 60 + seconds + centis / 100.0


def _parse_ass_cues(payload: str) -> List[SubtitleCue]:
    cues: List[SubtitleCue] = []
    in_events = False
    fields: Optional[List[str]] = None
    index = 1
    for raw_line in payload.replace("\r\n", "\n").splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue
        if stripped.startswith("[") and stripped.endswith("]"):
            in_events = stripped.strip().lower() == "[events]"
            continue
        if not in_events:
            continue
        lowered = stripped.lower()
        if lowered.startswith("format:"):
            field_list = stripped.split(":", 1)[1]
            fields = [field.strip().lower() for field in field_list.split(",") if field.strip()]
            continue
        if not lowered.startswith("dialogue:"):
            continue
        raw_dialogue = stripped.split(":", 1)[1].lstrip()
        active_fields = fields or _DEFAULT_ASS_FIELDS
        parts = [part.strip() for part in raw_dialogue.split(",", len(active_fields) - 1)]
        if len(parts) < len(active_fields):
            continue
        try:
            start_idx = active_fields.index("start")
            end_idx = active_fields.index("end")
            text_idx = active_fields.index("text")
        except ValueError:
            continue
        start_time = _parse_ass_timestamp(parts[start_idx]) if parts[start_idx] else None
        end_time = _parse_ass_timestamp(parts[end_idx]) if parts[end_idx] else None
        if start_time is None:
            continue
        if end_time is None:
            end_time = start_time
        text_value = parts[text_idx] if text_idx < len(parts) else ""
        cues.append(
            SubtitleCue(
                index=index,
                start=start_time,
                end=end_time,
                lines=[text_value],
            )
        )
        index += 1
    return cues


def _load_subtitle_cues_for_entry(
    job_id: str,
    entry: Mapping[str, object],
    locator: FileLocator,
) -> List[SubtitleCue]:
    suffix = _extract_entry_extension(entry)
    if suffix not in _SUBTITLE_EXTENSIONS:
        return []
    path = _resolve_entry_path(job_id, entry, locator)
    if path is None:
        return []
    if suffix in {".srt", ".vtt"}:
        try:
            return load_subtitle_cues(path)
        except Exception:
            return []
    if suffix == ".ass":
        try:
            payload = _read_subtitle_text(path)
        except Exception:
            return []
        return _parse_ass_cues(payload)
    return []


def _collect_subtitle_matches(
    cues: Sequence[SubtitleCue],
    query: str,
) -> List[Tuple[str, int, int, int, int, float, float, float, float]]:
    matches: List[Tuple[str, int, int, int, int, float, float, float, float]] = []
    merged_text: Optional[str] = None
    merged_start: Optional[float] = None
    merged_end: Optional[float] = None
    merge_gap = 0.1

    def flush_group() -> None:
        nonlocal merged_text, merged_start, merged_end
        if not merged_text or merged_start is None or merged_end is None:
            merged_text = None
            merged_start = None
            merged_end = None
            return
        hit_points = _find_matches(merged_text, query)
        if hit_points:
            snippet, occurrence_count = _build_snippet(merged_text, hit_points)
            match_start, match_end = hit_points[0]
            text_length = len(merged_text)
            offset_ratio = (
                max(min(match_start / text_length, 1.0), 0.0) if text_length else 0.0
            )
            duration = max(0.0, merged_end - merged_start)
            approximate_time = (
                merged_start + offset_ratio * duration if duration > 0 else merged_start
            )
            matches.append(
                (
                    snippet,
                    occurrence_count,
                    match_start,
                    match_end,
                    text_length,
                    offset_ratio,
                    approximate_time,
                    merged_start,
                    merged_end,
                )
            )
        merged_text = None
        merged_start = None
        merged_end = None

    for cue in cues:
        raw_text = cue.as_text()
        if not raw_text:
            continue
        normalized = _normalize_text(raw_text)
        if not normalized:
            continue
        if (
            merged_text is not None
            and normalized == merged_text
            and merged_end is not None
            and cue.start <= merged_end + merge_gap
        ):
            merged_end = max(merged_end, cue.end)
            continue
        flush_group()
        merged_text = normalized
        merged_start = cue.start
        merged_end = cue.end

    flush_group()
    return matches


def _load_text_from_chunk_metadata(
    loader: MetadataLoader,
    chunk: Mapping[str, object],
) -> Tuple[Optional[str], Optional[Mapping[str, object]]]:
    try:
        payload = loader.load_chunk(chunk, include_sentences=True)
    except Exception:
        return None, None

    sentences = payload.get("sentences")
    if not isinstance(sentences, list) or not sentences:
        return None, payload

    fragments: List[str] = []
    for sentence in sentences:
        texts: List[str] = []
        if isinstance(sentence, Mapping):
            original = sentence.get("original")
            if isinstance(original, Mapping):
                value = original.get("text")
                if isinstance(value, str):
                    texts.append(value)
            translation = sentence.get("translation")
            if isinstance(translation, Mapping):
                value = translation.get("text")
                if isinstance(value, str):
                    texts.append(value)
            transliteration = sentence.get("transliteration")
            if isinstance(transliteration, Mapping):
                value = transliteration.get("text")
                if isinstance(value, str):
                    texts.append(value)
            direct_text = sentence.get("text")
            if isinstance(direct_text, str):
                texts.append(direct_text)
        elif isinstance(sentence, str):
            texts.append(sentence)

        for text in texts:
            trimmed = text.strip()
            if trimmed:
                fragments.append(trimmed)

    if not fragments:
        return None, payload
    return " ".join(fragments), payload


def _chunk_entries_from_manifest(manifest: Mapping[str, object]) -> List[Mapping[str, object]]:
    raw_chunks = manifest.get("chunks")
    if not isinstance(raw_chunks, list):
        return []
    entries: List[Tuple[int, Dict[str, object]]] = []
    for entry in raw_chunks:
        if not isinstance(entry, Mapping):
            continue
        index_value = entry.get("index")
        index = index_value if isinstance(index_value, int) else None
        chunk_entry: Dict[str, object] = {
            "chunk_id": entry.get("chunk_id"),
            "metadata_path": entry.get("path"),
            "metadata_url": entry.get("url"),
            "sentence_count": entry.get("sentence_count"),
        }
        entries.append((index if index is not None else len(entries), chunk_entry))
    entries.sort(key=lambda item: item[0])
    return [entry for _, entry in entries]


def _chunk_entry_key(chunk: Mapping[str, object]) -> Optional[str]:
    for key in ("chunk_id", "metadata_path", "metadata_url"):
        value = chunk.get(key)
        if isinstance(value, str):
            trimmed = value.strip()
            if trimmed:
                return trimmed
    return None


def _merge_chunk_entries(
    primary: List[Mapping[str, object]],
    fallback: List[Mapping[str, object]],
) -> List[Mapping[str, object]]:
    if not primary:
        return fallback
    if not fallback:
        return primary
    fallback_map: Dict[str, Mapping[str, object]] = {}
    for entry in fallback:
        key = _chunk_entry_key(entry)
        if key:
            fallback_map[key] = entry
    merged: List[Mapping[str, object]] = []
    used_keys: set[str] = set()
    for entry in primary:
        key = _chunk_entry_key(entry)
        supplement = fallback_map.get(key) if key else None
        if supplement:
            combined: Dict[str, object] = dict(entry)
            for field, value in supplement.items():
                if field not in combined or combined[field] in (None, [], {}):
                    combined[field] = value
            merged.append(combined)
            used_keys.add(key)
        else:
            merged.append(entry)
    for entry in fallback:
        key = _chunk_entry_key(entry)
        if key and key in used_keys:
            continue
        merged.append(entry)
    return merged


def search_generated_media(
    *,
    query: str,
    jobs: Iterable[PipelineJob],
    locator: FileLocator,
    limit: int = 20,
) -> List[SearchMediaResult]:
    """Search ``jobs`` for ``query`` returning matching generated media chunks."""

    if not query or not query.strip():
        return []
    if limit <= 0:
        return []

    normalized_query = query.strip()
    results: List[SearchMediaResult] = []
    seen_subtitle_hits: set[tuple] = set()

    for job in jobs:
        generated = job.generated_files
        if not isinstance(generated, Mapping):
            continue

        job_root = _resolve_job_root(job, locator)
        metadata_loader: Optional[MetadataLoader] = None
        loader_attempted = False

        raw_chunks = generated.get("chunks") if isinstance(generated, Mapping) else None
        if isinstance(raw_chunks, list):
            chunk_entries = [chunk for chunk in raw_chunks if isinstance(chunk, Mapping)]
        else:
            chunk_entries = list(_iterate_chunk_entries(generated))

        if job_root is not None:
            try:
                metadata_loader = MetadataLoader(job_root)
            except Exception:
                metadata_loader = None
            else:
                loader_chunks = list(metadata_loader.iter_chunks())
                if not loader_chunks:
                    loader_chunks = _chunk_entries_from_manifest(
                        metadata_loader.build_chunk_manifest()
                    )
                if loader_chunks and len(loader_chunks) > len(chunk_entries):
                    chunk_entries = _merge_chunk_entries(loader_chunks, chunk_entries)

        if not chunk_entries:
            continue

        preferred_subtitle_keys = _select_preferred_subtitle_keys(chunk_entries)
        processed_subtitle_keys: set[str] = set()
        chunk_total = len(chunk_entries)

        for chunk_index, chunk in enumerate(chunk_entries):
            files = chunk.get("files")
            if not isinstance(files, Iterable):
                files = []

            file_entries = [entry for entry in files if isinstance(entry, Mapping)]
            subtitle_entry: Optional[Mapping[str, object]] = None
            subtitle_rank = len(_SUBTITLE_EXTENSION_ORDER)
            for entry in file_entries:
                suffix = _extract_entry_extension(entry)
                if suffix in _SUBTITLE_EXTENSIONS:
                    rank = (
                        _SUBTITLE_EXTENSION_ORDER.index(suffix)
                        if suffix in _SUBTITLE_EXTENSION_ORDER
                        else len(_SUBTITLE_EXTENSION_ORDER)
                    )
                    if subtitle_entry is None or rank < subtitle_rank:
                        subtitle_entry = entry
                        subtitle_rank = rank
            if subtitle_entry is not None:
                subtitle_key = _subtitle_entry_identity(subtitle_entry)
                if subtitle_key:
                    if preferred_subtitle_keys and subtitle_key not in preferred_subtitle_keys:
                        subtitle_entry = None
                    elif subtitle_key in processed_subtitle_keys:
                        continue

            metadata_payload = None
            if metadata_loader is not None:
                try:
                    metadata_payload = metadata_loader.load_chunk(
                        chunk, include_sentences=False
                    )
                except Exception:
                    metadata_payload = None

            text_entry = None
            for candidate in file_entries:
                if _normalise_media_type(candidate.get("type")) == "text":
                    text_entry = candidate
                    break
            if text_entry is None:
                text_content = None
            else:
                text_content = _load_text_from_entry(job.job_id, text_entry, locator)

            chunk_id_value = chunk.get("chunk_id")
            if chunk_id_value is None and isinstance(metadata_payload, Mapping):
                chunk_id_value = metadata_payload.get("chunk_id")
            range_fragment_value = chunk.get("range_fragment")
            if range_fragment_value is None and isinstance(metadata_payload, Mapping):
                range_fragment_value = metadata_payload.get("range_fragment")
            start_sentence_value = chunk.get("start_sentence")
            if start_sentence_value is None and isinstance(metadata_payload, Mapping):
                start_sentence_value = metadata_payload.get("start_sentence")
            end_sentence_value = chunk.get("end_sentence")
            if end_sentence_value is None and isinstance(metadata_payload, Mapping):
                end_sentence_value = metadata_payload.get("end_sentence")

            base_id: Optional[str] = None
            if subtitle_entry is not None:
                for key in ("relative_path", "path", "url", "name"):
                    value = subtitle_entry.get(key)
                    if not isinstance(value, str):
                        continue
                    candidate = value.strip()
                    if not candidate:
                        continue
                    candidate = candidate.split("?", 1)[0].split("#", 1)[0]
                    stem = Path(candidate).stem
                    if stem:
                        base_id = stem.lower()
                        break

            if text_content is None:
                if metadata_loader is None and not loader_attempted:
                    loader_attempted = True
                    if job_root is not None:
                        manifest_path = job_root / "metadata" / "job.json"
                        if manifest_path.exists():
                            try:
                                metadata_loader = MetadataLoader(job_root)
                            except Exception:
                                metadata_loader = None
                if metadata_loader is not None:
                    text_content, metadata_payload = _load_text_from_chunk_metadata(
                        metadata_loader, chunk
                    )
                    if chunk_id_value is None and isinstance(metadata_payload, Mapping):
                        chunk_id_value = metadata_payload.get("chunk_id")
                    if range_fragment_value is None and isinstance(metadata_payload, Mapping):
                        range_fragment_value = metadata_payload.get("range_fragment")
                    if start_sentence_value is None and isinstance(metadata_payload, Mapping):
                        start_sentence_value = metadata_payload.get("start_sentence")
                    if end_sentence_value is None and isinstance(metadata_payload, Mapping):
                        end_sentence_value = metadata_payload.get("end_sentence")

            subtitle_matches: List[
                Tuple[str, int, int, int, int, float, float, float, float]
            ] = []
            if subtitle_entry is not None:
                subtitle_key = _subtitle_entry_identity(subtitle_entry)
                if subtitle_key:
                    processed_subtitle_keys.add(subtitle_key)
                cues = _load_subtitle_cues_for_entry(job.job_id, subtitle_entry, locator)
                if cues:
                    subtitle_matches = _collect_subtitle_matches(
                        cues, normalized_query
                    )

            if subtitle_matches:
                relative_value = (
                    text_entry.get("relative_path") if text_entry is not None else None
                )
                if base_id is None and isinstance(relative_value, str) and relative_value.strip():
                    base_candidate = Path(relative_value).name or relative_value
                    base_id = Path(base_candidate).stem.lower() or None
                if base_id is None and chunk_id_value:
                    base_candidate = str(chunk_id_value)
                    if base_candidate:
                        base_id = Path(base_candidate).stem.lower()
                media_bucket = _gather_media_entries(
                    job.job_id,
                    (entry for entry in file_entries if isinstance(entry, Mapping)),
                    locator,
                )
                for (
                    snippet,
                    occurrence_count,
                    match_start,
                    match_end,
                    text_length,
                    offset_ratio,
                    approximate_time,
                    cue_start,
                    cue_end,
                ) in subtitle_matches:
                    subtitle_key = (
                        job.job_id,
                        base_id,
                        cue_start,
                        cue_end,
                    )
                    if subtitle_key in seen_subtitle_hits:
                        continue
                    seen_subtitle_hits.add(subtitle_key)
                    results.append(
                        SearchMediaResult(
                            job_id=job.job_id,
                            job_label=_resolve_job_label(job),
                            base_id=base_id,
                            chunk_id=str(chunk_id_value) if chunk_id_value is not None else None,
                            chunk_index=chunk_index,
                            chunk_total=chunk_total,
                            range_fragment=str(range_fragment_value)
                            if range_fragment_value is not None
                            else None,
                            start_sentence=_coerce_int(start_sentence_value),
                            end_sentence=_coerce_int(end_sentence_value),
                            snippet=snippet,
                            occurrence_count=occurrence_count,
                            match_start=match_start,
                            match_end=match_end,
                            text_length=text_length,
                            offset_ratio=offset_ratio,
                            approximate_time_seconds=approximate_time,
                            cue_start_seconds=cue_start,
                            cue_end_seconds=cue_end,
                            media=media_bucket,
                        )
                    )
                    if len(results) >= limit:
                        return results
                continue

            if text_content is None:
                continue

            matches = _find_matches(text_content, normalized_query)
            if not matches:
                continue

            relative_value = text_entry.get("relative_path") if text_entry is not None else None
            if isinstance(relative_value, str) and relative_value.strip():
                base_candidate = Path(relative_value).name or relative_value
                base_id = Path(base_candidate).stem.lower() or None
            else:
                if chunk_id_value:
                    chunk_candidate = str(chunk_id_value)
                    if chunk_candidate:
                        base_id = Path(chunk_candidate).stem.lower()

            text_length = len(text_content)
            match_start = matches[0][0]
            match_end = matches[0][1]
            offset_ratio: Optional[float] = None
            if text_length > 0:
                offset_ratio = max(min(match_start / text_length, 1.0), 0.0)
            estimated_duration: Optional[float] = None
            if text_length > 0:
                estimated_duration = text_length / _AVERAGE_CHARACTERS_PER_SECOND
            approximate_time: Optional[float] = None
            if offset_ratio is not None and estimated_duration is not None:
                approximate_time = offset_ratio * estimated_duration

            snippet, occurrence_count = _build_snippet(text_content, matches)
            media_bucket = _gather_media_entries(
                job.job_id,
                (entry for entry in files if isinstance(entry, Mapping)),
                locator,
            )

            results.append(
                SearchMediaResult(
                    job_id=job.job_id,
                    job_label=_resolve_job_label(job),
                    base_id=base_id,
                    chunk_id=str(chunk_id_value) if chunk_id_value is not None else None,
                    chunk_index=chunk_index,
                    chunk_total=chunk_total,
                    range_fragment=str(range_fragment_value)
                    if range_fragment_value is not None
                    else None,
                    start_sentence=_coerce_int(start_sentence_value),
                    end_sentence=_coerce_int(end_sentence_value),
                    snippet=snippet,
                    occurrence_count=occurrence_count,
                    match_start=match_start,
                    match_end=match_end,
                    text_length=text_length,
                    offset_ratio=offset_ratio,
                    approximate_time_seconds=approximate_time,
                    media=media_bucket,
                )
            )

            if len(results) >= limit:
                return results

    return results
_AVERAGE_CHARACTERS_PER_SECOND = 15.0
