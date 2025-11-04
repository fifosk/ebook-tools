"""Helpers for searching generated ebook content."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
import textwrap
from html import unescape
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Mapping, MutableMapping, Optional, Sequence, Tuple

from ..metadata_manager import MetadataLoader
from ..services.file_locator import FileLocator
from ..services.job_manager.job import PipelineJob

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
        inputs = job.request.inputs.__dict__  # type: ignore[assignment]
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


def _load_text_from_chunk_metadata(loader: MetadataLoader, chunk: Mapping[str, object]) -> Optional[str]:
    try:
        payload = loader.load_chunk(chunk, include_sentences=True)
    except Exception:
        return None

    sentences = payload.get("sentences")
    if not isinstance(sentences, list) or not sentences:
        return None

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
        return None
    return " ".join(fragments)


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

        if not chunk_entries:
            continue

        chunk_total = len(chunk_entries)

        for chunk_index, chunk in enumerate(chunk_entries):
            files = chunk.get("files")
            if not isinstance(files, Iterable):
                continue

            text_entry = None
            for candidate in files:
                if not isinstance(candidate, Mapping):
                    continue
                if _normalise_media_type(candidate.get("type")) == "text":
                    text_entry = candidate
                    break
            if text_entry is None:
                text_content = None
            else:
                text_content = _load_text_from_entry(job.job_id, text_entry, locator)

            if text_content is None:
                if not loader_attempted:
                    loader_attempted = True
                    if job_root is not None:
                        manifest_path = job_root / "metadata" / "job.json"
                        if manifest_path.exists():
                            try:
                                metadata_loader = MetadataLoader(job_root)
                            except Exception:
                                metadata_loader = None
                if metadata_loader is not None:
                    text_content = _load_text_from_chunk_metadata(metadata_loader, chunk)

            if text_content is None:
                continue

            matches = _find_matches(text_content, normalized_query)
            if not matches:
                continue

            relative_value = text_entry.get("relative_path") if text_entry is not None else None
            base_id: Optional[str] = None
            if isinstance(relative_value, str) and relative_value.strip():
                base_candidate = Path(relative_value).name or relative_value
                base_id = Path(base_candidate).stem.lower() or None
            elif chunk.get("chunk_id"):
                chunk_candidate = str(chunk.get("chunk_id"))
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
                    chunk_id=str(chunk.get("chunk_id")) if chunk.get("chunk_id") is not None else None,
                    chunk_index=chunk_index,
                    chunk_total=chunk_total,
                    range_fragment=str(chunk.get("range_fragment"))
                    if chunk.get("range_fragment") is not None
                    else None,
                    start_sentence=_coerce_int(chunk.get("start_sentence")),
                    end_sentence=_coerce_int(chunk.get("end_sentence")),
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
