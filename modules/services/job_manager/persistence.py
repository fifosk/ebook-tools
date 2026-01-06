"""Helpers for serializing pipeline job state to persistent metadata."""

from __future__ import annotations

import copy
import glob
import json
import os
import shutil
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any, Dict, Mapping, Optional, Tuple

from ..file_locator import FileLocator
from ... import config_manager as cfg
from ... import logging_manager
from ...transliteration import resolve_local_transliteration_module
from ..pipeline_service import (
    serialize_pipeline_request,
    serialize_pipeline_response,
)
from .job import PipelineJob
from .metadata import PipelineJobMetadata
from .progress import deserialize_progress_event, serialize_progress_event
from ...progress_tracker import ProgressEvent

_LOGGER = logging_manager.get_logger().getChild("job_manager.persistence")


def _iterate_sentence_entries(payload: Any) -> list[Mapping[str, Any]]:
    """Return flattened sentence entries from a chunk payload."""

    entries: list[Mapping[str, Any]] = []
    if isinstance(payload, list):
        for item in payload:
            entries.extend(_iterate_sentence_entries(item))
    elif isinstance(payload, Mapping):
        sentences = payload.get("sentences")
        if isinstance(sentences, list):
            for sentence in sentences:
                entries.extend(_iterate_sentence_entries(sentence))
        else:
            entries.append(payload)  # Treat mapping as a sentence-level entry
        chunks = payload.get("chunks")
        if isinstance(chunks, list):
            for chunk in chunks:
                entries.extend(_iterate_sentence_entries(chunk))
    return entries


def _normalize_audio_track_entry(value: Any) -> Optional[Dict[str, Any]]:
    """Return a normalized audio track entry with stable fields."""

    if isinstance(value, Mapping):
        entry: Dict[str, Any] = {}
        path = value.get("path")
        url = value.get("url")
        duration = value.get("duration")
        sample_rate = value.get("sampleRate") or value.get("sample_rate")
        if isinstance(path, str) and path.strip():
            entry["path"] = path.strip()
        if isinstance(url, str) and url.strip():
            entry["url"] = url.strip()
        try:
            entry["duration"] = round(float(duration), 6)
        except (TypeError, ValueError):
            pass
        try:
            entry["sampleRate"] = int(sample_rate)
        except (TypeError, ValueError):
            pass
        return entry or None
    if isinstance(value, str):
        trimmed = value.strip()
        if trimmed:
            return {"path": trimmed}
    return None


def _normalize_language_label(value: Any) -> Optional[str]:
    if isinstance(value, str):
        trimmed = value.strip()
        return trimmed or None
    if isinstance(value, list):
        for entry in value:
            if isinstance(entry, str):
                trimmed = entry.strip()
                if trimmed:
                    return trimmed
    return None


def _normalize_language_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [entry.strip() for entry in value if isinstance(entry, str) and entry.strip()]
    if isinstance(value, str):
        trimmed = value.strip()
        return [trimmed] if trimmed else []
    return []


def _normalize_option_label(value: Any) -> Optional[str]:
    if isinstance(value, str):
        trimmed = value.strip()
        return trimmed or None
    if isinstance(value, list):
        for entry in value:
            if isinstance(entry, str):
                trimmed = entry.strip()
                if trimmed:
                    return trimmed
    return None


def _normalize_translation_provider(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    normalized = value.strip().lower()
    if normalized in {"google", "googletrans", "googletranslate", "google-translate", "gtranslate", "gtrans"}:
        return "googletrans"
    if normalized in {"llm", "ollama", "default"}:
        return "llm"
    return normalized or None


def _normalize_transliteration_mode(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    normalized = value.strip().lower().replace("_", "-")
    if normalized in {"python", "python-module", "module", "local-module"}:
        return "python"
    if normalized.startswith("local-gemma3") or normalized == "gemma3-12b":
        return "default"
    if normalized in {"llm", "ollama", "default"}:
        return "default"
    return normalized or None


def _read_language_key(section: Mapping[str, Any], key: str) -> Any:
    if key in section:
        return section.get(key)
    camel = "".join(
        [part if idx == 0 else part.capitalize() for idx, part in enumerate(key.split("_"))]
    )
    if camel in section:
        return section.get(camel)
    return None


def _iter_language_sections(payload: Any) -> list[Mapping[str, Any]]:
    if not isinstance(payload, Mapping):
        return []
    sections: list[Mapping[str, Any]] = [payload]
    for key in ("inputs", "options", "config", "metadata"):
        candidate = payload.get(key)
        if isinstance(candidate, Mapping):
            sections.append(candidate)
    return sections


def _extract_language_context(
    payloads: tuple[Any, ...],
) -> tuple[Optional[str], Optional[str], Optional[str], list[str]]:
    input_language: Optional[str] = None
    original_language: Optional[str] = None
    target_language: Optional[str] = None
    target_languages: list[str] = []
    media_language: Optional[str] = None
    for payload in payloads:
        for section in _iter_language_sections(payload):
            if input_language is None:
                input_language = _normalize_language_label(
                    _read_language_key(section, "input_language")
                    or _read_language_key(section, "original_language")
                    or _read_language_key(section, "source_language")
                    or _read_language_key(section, "translation_source_language")
                )
            if original_language is None:
                original_language = _normalize_language_label(
                    _read_language_key(section, "original_language")
                )
            if not target_languages:
                target_languages = _normalize_language_list(
                    _read_language_key(section, "target_languages")
                    or _read_language_key(section, "target_language")
                    or _read_language_key(section, "translation_language")
                )
            if target_language is None:
                target_language = _normalize_language_label(
                    _read_language_key(section, "target_language")
                    or _read_language_key(section, "translation_language")
                )
        if media_language is None and isinstance(payload, Mapping):
            media_metadata = payload.get("media_metadata")
            if isinstance(media_metadata, Mapping):
                media_language = _normalize_language_label(
                    media_metadata.get("language")
                    or media_metadata.get("source_language")
                    or media_metadata.get("original_language")
                    or media_metadata.get("input_language")
                )
                if media_language is None:
                    show = media_metadata.get("show")
                    if isinstance(show, Mapping):
                        media_language = _normalize_language_label(show.get("language"))
    if original_language is None:
        original_language = input_language
    if input_language is None and media_language is not None:
        input_language = media_language
        if original_language is None:
            original_language = media_language
    if target_language is None and target_languages:
        target_language = target_languages[0]
    if target_language and not target_languages:
        target_languages = [target_language]
    return input_language, original_language, target_language, target_languages


def _set_if_blank(metadata: Dict[str, Any], key: str, value: Optional[str]) -> None:
    if value is None:
        return
    trimmed = value.strip()
    if not trimmed:
        return
    existing = metadata.get(key)
    if isinstance(existing, str) and existing.strip():
        return
    metadata[key] = trimmed


def _set_list_if_blank(metadata: Dict[str, Any], key: str, values: list[str]) -> None:
    if not values:
        return
    cleaned = [value.strip() for value in values if isinstance(value, str) and value.strip()]
    if not cleaned:
        return
    existing = metadata.get(key)
    if isinstance(existing, list) and any(
        isinstance(entry, str) and entry.strip() for entry in existing
    ):
        return
    if isinstance(existing, str) and existing.strip():
        return
    metadata[key] = cleaned


def _apply_language_metadata(
    book_metadata: Dict[str, Any],
    request_payload: Mapping[str, Any] | None,
    resume_context: Mapping[str, Any] | None,
    result_payload: Mapping[str, Any] | None,
) -> None:
    subtitle_metadata: Optional[Mapping[str, Any]] = None
    if isinstance(result_payload, Mapping):
        subtitle_section = result_payload.get("subtitle")
        if isinstance(subtitle_section, Mapping):
            metadata_section = subtitle_section.get("metadata")
            if isinstance(metadata_section, Mapping):
                subtitle_metadata = metadata_section

    input_language, original_language, target_language, target_languages = _extract_language_context(
        (
            request_payload,
            resume_context,
            subtitle_metadata,
        )
    )
    _set_if_blank(book_metadata, "input_language", input_language)
    _set_if_blank(book_metadata, "original_language", original_language or input_language)
    _set_if_blank(book_metadata, "target_language", target_language)
    _set_if_blank(book_metadata, "translation_language", target_language)
    _set_list_if_blank(book_metadata, "target_languages", target_languages)

    translation_provider: Optional[str] = None
    transliteration_mode: Optional[str] = None
    for payload in (request_payload, resume_context, subtitle_metadata):
        for section in _iter_language_sections(payload):
            if translation_provider is None:
                translation_provider = _normalize_translation_provider(
                    _normalize_option_label(_read_language_key(section, "translation_provider"))
                )
            if transliteration_mode is None:
                transliteration_mode = _normalize_transliteration_mode(
                    _normalize_option_label(_read_language_key(section, "transliteration_mode"))
                )

    llm_model: Optional[str] = None
    for payload in (request_payload, resume_context):
        if not isinstance(payload, Mapping):
            continue
        pipeline_overrides = payload.get("pipeline_overrides")
        if isinstance(pipeline_overrides, Mapping):
            llm_model = _normalize_option_label(pipeline_overrides.get("ollama_model")) or llm_model
        config_section = payload.get("config")
        if isinstance(config_section, Mapping):
            llm_model = _normalize_option_label(config_section.get("ollama_model")) or llm_model
        if llm_model:
            break

    if llm_model is None and isinstance(result_payload, Mapping):
        pipeline_config = result_payload.get("pipeline_config")
        if isinstance(pipeline_config, Mapping):
            llm_model = _normalize_option_label(pipeline_config.get("ollama_model")) or llm_model

    translation_model = None
    if translation_provider == "googletrans":
        translation_model = "googletrans"
    elif translation_provider == "llm":
        translation_model = llm_model

    transliteration_model = None
    transliteration_module = None
    if transliteration_mode == "default":
        transliteration_model = llm_model
    elif transliteration_mode == "python":
        target_for_module = target_language or (target_languages[0] if target_languages else None)
        if target_for_module:
            transliteration_module = resolve_local_transliteration_module(target_for_module)

    _set_if_blank(book_metadata, "translation_provider", translation_provider)
    _set_if_blank(book_metadata, "translation_model", translation_model)
    _set_if_blank(book_metadata, "transliteration_mode", transliteration_mode)
    _set_if_blank(book_metadata, "transliteration_model", transliteration_model)
    _set_if_blank(book_metadata, "transliteration_module", transliteration_module)


def _extract_highlighting_policy(entry: Mapping[str, Any]) -> Optional[str]:
    """Return the highlighting policy encoded on a sentence entry."""

    summary = entry.get("highlighting_summary")
    if isinstance(summary, Mapping):
        policy = summary.get("policy")
        if isinstance(policy, str) and policy.strip():
            return policy.strip()
    policy = entry.get("highlighting_policy") or entry.get("alignment_policy")
    if isinstance(policy, str) and policy.strip():
        return policy.strip()
    return None


def _is_estimated_policy(policy: Optional[str]) -> bool:
    if not isinstance(policy, str):
        return False
    normalized = policy.strip().lower()
    return normalized.startswith("estimated")


def _extract_policy_from_timing_tracks(payload: Mapping[str, Any]) -> Optional[str]:
    tracks = payload.get("timingTracks") or payload.get("timing_tracks")
    if not isinstance(tracks, Mapping):
        return None
    fallback: Optional[str] = None
    for entries in tracks.values():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, Mapping):
                continue
            policy = entry.get("policy")
            if not isinstance(policy, str):
                continue
            normalized = policy.strip()
            if not normalized:
                continue
            if _is_estimated_policy(normalized):
                return normalized
            if fallback is None:
                fallback = normalized
    return fallback


def resolve_highlighting_policy(job_dir: str | os.PathLike[str]) -> Optional[str]:
    """Inspect chunk metadata files to determine the active highlighting policy."""

    job_path = Path(job_dir)
    metadata_dir = job_path / "metadata"
    if not metadata_dir.exists():
        return None

    fallback_policy: Optional[str] = None
    pattern = metadata_dir / "chunk_*.json"
    for chunk_path in sorted(glob.glob(os.fspath(pattern))):
        try:
            with open(chunk_path, "r", encoding="utf-8") as handle:
                chunk_payload = json.load(handle)
        except (OSError, json.JSONDecodeError):
            continue

        if isinstance(chunk_payload, Mapping):
            top_level_policy = chunk_payload.get("highlighting_policy")
            if isinstance(top_level_policy, str) and top_level_policy.strip():
                normalized = top_level_policy.strip()
                if _is_estimated_policy(normalized):
                    return normalized
                if fallback_policy is None:
                    fallback_policy = normalized
            policy = _extract_policy_from_timing_tracks(chunk_payload)
            if policy:
                if _is_estimated_policy(policy):
                    return policy
                if fallback_policy is None:
                    fallback_policy = policy

        for entry in _iterate_sentence_entries(chunk_payload):
            if isinstance(entry, Mapping):
                policy = _extract_highlighting_policy(entry)
                if policy:
                    if _is_estimated_policy(policy):
                        return policy
                    if fallback_policy is None:
                        fallback_policy = policy

    return fallback_policy


def ensure_timing_manifest(
    manifest: Mapping[str, Any] | None,
    job_dir: str | os.PathLike[str],
) -> Dict[str, Any]:
    """
    Attach highlighting metadata to ``manifest`` without persisting timing indexes.
    """

    manifest_payload = dict(manifest or {})
    manifest_payload.pop("timing_tracks", None)

    job_path = Path(job_dir)
    policy = resolve_highlighting_policy(job_path)
    if policy:
        manifest_payload["highlighting_policy"] = policy
    return manifest_payload


class PipelineJobPersistence:
    """Serialize and deserialize :class:`PipelineJob` instances."""

    def __init__(self, file_locator: FileLocator) -> None:
        self._file_locator = file_locator

    def snapshot(self, job: PipelineJob) -> PipelineJobMetadata:
        """Return a metadata snapshot for ``job``."""

        last_event = (
            serialize_progress_event(job.last_event)
            if job.last_event is not None
            else None
        )
        result_payload = (
            copy.deepcopy(job.result_payload)
            if job.result_payload is not None
            else (
                serialize_pipeline_response(job.result)
                if job.result is not None
                else None
            )
        )
        if job.request is not None:
            request_payload = serialize_pipeline_request(job.request)
        else:
            request_payload = (
                copy.deepcopy(job.request_payload) if job.request_payload is not None else None
            )
        resume_context = (
            copy.deepcopy(job.resume_context)
            if job.resume_context is not None
            else (copy.deepcopy(request_payload) if request_payload is not None else None)
        )

        normalized_files = self._normalize_generated_files(job.job_id, job.generated_files)
        job.generated_files = copy.deepcopy(normalized_files) if normalized_files is not None else None
        if isinstance(normalized_files, Mapping):
            complete_flag = normalized_files.get("complete")
            if isinstance(complete_flag, bool):
                job.media_completed = complete_flag

        retry_summary = job.retry_summary or (job.tracker.get_retry_counts() if job.tracker else None)
        if retry_summary:
            job.retry_summary = copy.deepcopy(retry_summary)

        snapshot = PipelineJobMetadata(
            job_id=job.job_id,
            job_type=job.job_type,
            status=job.status,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            error_message=job.error_message,
            last_event=copy.deepcopy(last_event) if last_event is not None else None,
            result=result_payload,
            request_payload=request_payload,
            resume_context=resume_context,
            tuning_summary=copy.deepcopy(job.tuning_summary)
            if job.tuning_summary is not None
            else None,
            retry_summary=copy.deepcopy(retry_summary),
            user_id=job.user_id,
            user_role=job.user_role,
            generated_files=copy.deepcopy(normalized_files)
            if normalized_files is not None
            else None,
            media_completed=job.media_completed,
        )
        chunk_manifest = self._persist_metadata_files(job, snapshot)
        manifest_source = chunk_manifest if chunk_manifest is not None else snapshot.chunk_manifest
        if manifest_source is not None:
            snapshot.chunk_manifest = copy.deepcopy(manifest_source)
            job.chunk_manifest = copy.deepcopy(manifest_source)
        else:
            snapshot.chunk_manifest = None
            job.chunk_manifest = None
        return snapshot

    def build_job(self, metadata: PipelineJobMetadata) -> PipelineJob:
        """Return a :class:`PipelineJob` hydrated from ``metadata``."""

        request_payload = (
            copy.deepcopy(metadata.request_payload)
            if metadata.request_payload is not None
            else None
        )
        resume_context = (
            copy.deepcopy(metadata.resume_context)
            if metadata.resume_context is not None
            else (copy.deepcopy(request_payload) if request_payload is not None else None)
        )
        result_payload = (
            copy.deepcopy(metadata.result) if metadata.result is not None else None
        )

        normalized_files = self._normalize_generated_files(
            metadata.job_id, metadata.generated_files
        )

        job = PipelineJob(
            job_id=metadata.job_id,
            job_type=metadata.job_type,
            status=metadata.status,
            created_at=metadata.created_at,
            started_at=metadata.started_at,
            completed_at=metadata.completed_at,
            error_message=metadata.error_message,
            result_payload=result_payload,
            request_payload=request_payload,
            resume_context=resume_context,
            tuning_summary=copy.deepcopy(metadata.tuning_summary)
            if metadata.tuning_summary is not None
            else None,
            retry_summary=copy.deepcopy(metadata.retry_summary)
            if metadata.retry_summary is not None
            else None,
            user_id=metadata.user_id,
            user_role=metadata.user_role,
            generated_files=copy.deepcopy(normalized_files)
            if normalized_files is not None
            else None,
        )
        job.chunk_manifest = (
            copy.deepcopy(metadata.chunk_manifest)
            if metadata.chunk_manifest is not None
            else None
        )
        job.media_completed = bool(metadata.media_completed)
        if isinstance(normalized_files, Mapping):
            complete_flag = normalized_files.get("complete")
            if isinstance(complete_flag, bool):
                job.media_completed = complete_flag

        if metadata.last_event is not None:
            job.last_event = deserialize_progress_event(metadata.last_event)

        return job

    def _persist_metadata_files(
        self,
        job: PipelineJob,
        snapshot: PipelineJobMetadata,
    ) -> Optional[Dict[str, Any]]:
        try:
            metadata_root = self._file_locator.metadata_root(job.job_id)
            metadata_root.mkdir(parents=True, exist_ok=True)
            job_root = self._file_locator.job_root(job.job_id)
        except Exception:  # pragma: no cover - defensive logging
            _LOGGER.debug("Unable to prepare metadata directory", exc_info=True)
            return None

        result_payload_raw = snapshot.result or {}
        if isinstance(result_payload_raw, Mapping):
            result_payload = dict(result_payload_raw)
        else:
            result_payload = {}

        raw_book_metadata = result_payload.get("book_metadata")
        book_metadata: Dict[str, Any]
        if isinstance(raw_book_metadata, Mapping):
            book_metadata = dict(raw_book_metadata)
        else:
            book_metadata = {}
        _apply_language_metadata(
            book_metadata,
            snapshot.request_payload if isinstance(snapshot.request_payload, Mapping) else None,
            snapshot.resume_context if isinstance(snapshot.resume_context, Mapping) else None,
            result_payload,
        )

        cover_asset = self._mirror_cover_asset(job.job_id, metadata_root, book_metadata)
        if cover_asset:
            book_metadata["job_cover_asset"] = cover_asset
            book_metadata.setdefault("job_cover_asset_url", f"/api/pipelines/{job.job_id}/cover")
        else:
            book_metadata.pop("job_cover_asset", None)
            book_metadata.pop("job_cover_asset_url", None)
        raw_content_index = book_metadata.get("content_index")
        content_index_written = False
        content_index_total_sentences: Optional[int] = None
        if isinstance(raw_content_index, Mapping):
            try:
                content_index_payload = copy.deepcopy(dict(raw_content_index))
                content_index_path = metadata_root / "content_index.json"
                content_index_path.write_text(
                    json.dumps(content_index_payload, indent=2, sort_keys=True),
                    encoding="utf-8",
                )
                content_index_written = True
                relative_path = Path("metadata") / "content_index.json"
                book_metadata["content_index_path"] = relative_path.as_posix()
                url_candidate = self._file_locator.resolve_url(
                    job.job_id, relative_path.as_posix()
                )
                if url_candidate:
                    book_metadata["content_index_url"] = url_candidate
                chapter_list = content_index_payload.get("chapters")
                chapter_count = (
                    len(chapter_list) if isinstance(chapter_list, list) else 0
                )
                alignment = None
                alignment_payload = content_index_payload.get("alignment")
                if isinstance(alignment_payload, Mapping):
                    alignment = alignment_payload.get("status")
                book_metadata["content_index_summary"] = {
                    "chapter_count": chapter_count,
                    "alignment": alignment,
                }
                total_candidate = content_index_payload.get("total_sentences")
                try:
                    total_value = int(total_candidate)
                except (TypeError, ValueError):
                    total_value = None
                if total_value and total_value > 0:
                    content_index_total_sentences = total_value
            except Exception:  # pragma: no cover - defensive logging
                _LOGGER.debug(
                    "Unable to persist content index for job %s",
                    job.job_id,
                    exc_info=True,
                )
        result_payload["book_metadata"] = book_metadata
        snapshot.result = result_payload

        if job.result_payload is not None:
            job.result_payload = dict(job.result_payload)
            job.result_payload["book_metadata"] = copy.deepcopy(book_metadata)
        if job.result is not None:
            if cover_asset:
                job.result.metadata.update({"job_cover_asset": cover_asset})
            else:
                job.result.metadata.values.pop("job_cover_asset", None)

        try:
            (metadata_root / "book.json").write_text(
                json.dumps(dict(book_metadata), indent=2, sort_keys=True),
                encoding="utf-8",
            )
        except Exception:  # pragma: no cover - defensive logging
            _LOGGER.debug("Unable to persist book metadata", exc_info=True)

        sentences = result_payload.get("refined_sentences")
        wrote_sentences = False
        if isinstance(sentences, list) and sentences:
            if not content_index_written:
                try:
                    (metadata_root / "sentences.json").write_text(
                        json.dumps(sentences, indent=2),
                        encoding="utf-8",
                    )
                    wrote_sentences = True
                except Exception:  # pragma: no cover - defensive logging
                    _LOGGER.debug("Unable to persist refined sentences", exc_info=True)
            else:
                wrote_sentences = True
            if content_index_total_sentences is None:
                content_index_total_sentences = len(sentences)

        if content_index_total_sentences and content_index_total_sentences > 0:
            book_metadata.setdefault("total_sentences", content_index_total_sentences)
            book_metadata.setdefault("book_sentence_count", content_index_total_sentences)

        if wrote_sentences:
            result_payload.pop("refined_sentences", None)
            if isinstance(job.result_payload, Mapping):
                job.result_payload = dict(job.result_payload)
                job.result_payload.pop("refined_sentences", None)

        prompt_plan_summary: Optional[Dict[str, Any]] = None
        prompt_plan_summary_path = metadata_root / "image_prompt_plan_summary.json"
        if prompt_plan_summary_path.exists():
            try:
                raw_summary = json.loads(prompt_plan_summary_path.read_text(encoding="utf-8"))
                if isinstance(raw_summary, Mapping):
                    prompt_plan_summary = copy.deepcopy(dict(raw_summary))
            except Exception:  # pragma: no cover - defensive logging
                _LOGGER.debug(
                    "Unable to load image prompt plan summary for job %s",
                    job.job_id,
                    exc_info=True,
                )

        chunk_manifest = None
        generated_payload = snapshot.generated_files
        if isinstance(generated_payload, Mapping) or prompt_plan_summary is not None:
            if isinstance(generated_payload, Mapping):
                generated_payload = dict(generated_payload)
            else:
                generated_payload = {"chunks": [], "files": []}
            if prompt_plan_summary is not None:
                generated_payload["image_prompt_plan_summary"] = prompt_plan_summary
            updated_generated, chunk_manifest = self._write_chunk_metadata(
                job.job_id,
                metadata_root,
                generated_payload,
            )
            snapshot.generated_files = copy.deepcopy(updated_generated)
            if isinstance(result_payload, Mapping):
                result_payload["generated_files"] = copy.deepcopy(updated_generated)
            if job.result_payload is not None:
                job.result_payload["generated_files"] = copy.deepcopy(updated_generated)
            if job.result is not None:
                job.result.generated_files = copy.deepcopy(updated_generated)
            job.generated_files = copy.deepcopy(updated_generated)

        if chunk_manifest is not None:
            if isinstance(result_payload, Mapping):
                result_payload["chunk_manifest"] = copy.deepcopy(chunk_manifest)
            if job.result_payload is not None:
                job.result_payload["chunk_manifest"] = copy.deepcopy(chunk_manifest)
            if job.result is not None:
                job.result.chunk_manifest = copy.deepcopy(chunk_manifest)
            job.chunk_manifest = copy.deepcopy(chunk_manifest)
            snapshot.chunk_manifest = copy.deepcopy(chunk_manifest)

        manifest_payload = ensure_timing_manifest(snapshot.result, job_root)
        snapshot.result = manifest_payload
        timing_tracks = manifest_payload.get("timing_tracks")
        snapshot.timing_tracks = copy.deepcopy(timing_tracks) if timing_tracks else None

        if job.result_payload is not None:
            job.result_payload = ensure_timing_manifest(job.result_payload, job_root)
        if job.result is not None and timing_tracks:
            try:
                job.result.metadata.update({"timing_tracks": copy.deepcopy(timing_tracks)})
            except Exception:  # pragma: no cover - defensive logging
                _LOGGER.debug("Unable to attach timing tracks to job result", exc_info=True)

        return chunk_manifest

    @staticmethod
    def _coerce_chunk_id(chunk: Mapping[str, Any]) -> Optional[str]:
        value = chunk.get("chunk_id") or chunk.get("chunkId")
        if isinstance(value, str):
            trimmed = value.strip()
            if trimmed:
                return trimmed
        return None

    def _merge_generated_files(
        self,
        existing: Optional[Any],
        update: Mapping[str, Any],
    ) -> Dict[str, Any]:
        if not isinstance(existing, Mapping):
            return copy.deepcopy(dict(update))

        existing_chunks = existing.get("chunks")
        update_chunks = update.get("chunks")

        merged_chunks: list[Dict[str, Any]] = []
        index_by_chunk_id: Dict[str, int] = {}

        if isinstance(existing_chunks, list):
            for entry in existing_chunks:
                if not isinstance(entry, Mapping):
                    continue
                chunk_copy = copy.deepcopy(dict(entry))
                chunk_id = self._coerce_chunk_id(chunk_copy)
                if chunk_id:
                    index_by_chunk_id[chunk_id] = len(merged_chunks)
                merged_chunks.append(chunk_copy)

        if isinstance(update_chunks, list):
            for entry in update_chunks:
                if not isinstance(entry, Mapping):
                    continue
                chunk_copy = copy.deepcopy(dict(entry))
                chunk_id = self._coerce_chunk_id(chunk_copy)
                if not chunk_id:
                    continue
                existing_index = index_by_chunk_id.get(chunk_id)
                if existing_index is None:
                    index_by_chunk_id[chunk_id] = len(merged_chunks)
                    merged_chunks.append(chunk_copy)
                else:
                    merged_chunks[existing_index] = chunk_copy

        merged: Dict[str, Any] = {"chunks": merged_chunks}

        complete_flag = update.get("complete")
        if isinstance(complete_flag, bool):
            merged["complete"] = complete_flag
        else:
            existing_complete = existing.get("complete")
            if isinstance(existing_complete, bool):
                merged["complete"] = existing_complete

        for key, value in existing.items():
            if key in {"chunks", "files", "complete"}:
                continue
            merged[key] = copy.deepcopy(value)
        for key, value in update.items():
            if key in {"chunks", "files", "complete"}:
                continue
            merged[key] = copy.deepcopy(value)

        return merged

    def apply_event(self, job: PipelineJob, event: ProgressEvent) -> PipelineJobMetadata:
        """Update ``job`` using ``event`` and return the persisted metadata."""

        job.last_event = event
        metadata = event.metadata
        if isinstance(metadata, Mapping):
            generated = metadata.get("generated_files")
            if generated is not None:
                if isinstance(generated, Mapping):
                    job.generated_files = self._merge_generated_files(job.generated_files, generated)
                    complete_flag = job.generated_files.get("complete")
                    if isinstance(complete_flag, bool):
                        job.media_completed = complete_flag
                else:
                    job.generated_files = copy.deepcopy(generated)
                job.chunk_manifest = None

        return self.snapshot(job)

    def _mirror_cover_asset(
        self,
        job_id: str,
        metadata_root: Path,
        book_metadata: Mapping[str, Any],
    ) -> Optional[str]:
        raw_value = book_metadata.get("book_cover_file")
        if not isinstance(raw_value, str) or not raw_value.strip():
            self._cleanup_cover_assets(metadata_root)
            return None

        source = self._resolve_cover_source(job_id, metadata_root, raw_value)
        if source is None:
            self._cleanup_cover_assets(metadata_root)
            return None

        try:
            return self._copy_cover_asset(metadata_root, source)
        except Exception:  # pragma: no cover - defensive logging
            _LOGGER.debug("Unable to mirror cover asset for job %s", job_id, exc_info=True)
            return None

    def _resolve_cover_source(
        self,
        job_id: str,
        metadata_root: Path,
        raw_value: str,
    ) -> Optional[Path]:
        candidate = Path(raw_value.strip())
        search_paths: list[Path] = []

        if candidate.is_absolute():
            search_paths.append(candidate)
        else:
            normalised = raw_value.strip().lstrip("/\\")
            relative_candidate = Path(normalised)
            relative_variants = [relative_candidate]

            parts = [part.lower() for part in relative_candidate.parts]
            if parts and parts[0] in {"storage", "metadata"} and len(parts) > 1:
                relative_variants.append(Path(*relative_candidate.parts[1:]))
            if parts and parts[0] == "covers" and len(parts) > 1:
                relative_variants.append(Path(*relative_candidate.parts[1:]))

            for relative in relative_variants:
                search_paths.append(metadata_root / relative)
                try:
                    search_paths.append(self._file_locator.resolve_path(job_id, relative))
                except ValueError:
                    pass
                search_paths.append(self._file_locator.storage_root / relative)

                covers_root = cfg.resolve_directory(None, cfg.DEFAULT_COVERS_RELATIVE)
                search_paths.append(covers_root / relative)

                resolved_script = cfg.resolve_file_path(relative)
                if resolved_script is not None:
                    search_paths.append(resolved_script)

        seen: set[Path] = set()
        for path in search_paths:
            try:
                resolved = path.resolve()
            except FileNotFoundError:
                continue
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
                _LOGGER.debug("Unable to remove stale cover asset %s", existing, exc_info=True)

        relative_path = Path("metadata") / destination_name
        return relative_path.as_posix()

    def _cleanup_cover_assets(self, metadata_root: Path) -> None:
        for existing in metadata_root.glob("cover.*"):
            try:
                existing.unlink()
            except FileNotFoundError:
                continue
            except OSError:
                _LOGGER.debug("Unable to remove cover asset %s", existing, exc_info=True)

    def _write_chunk_metadata(
        self,
        job_id: str,
        metadata_root: Path,
        generated: Mapping[str, Any],
    ) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
        chunks_raw = generated.get("chunks")
        payload = dict(generated)
        if not isinstance(chunks_raw, list):
            payload["chunks"] = []
            self._cleanup_unused_chunk_files(metadata_root, set())
            return payload, None

        updated_chunks: list[Dict[str, Any]] = []
        manifest_entries: list[Dict[str, Any]] = []
        preserved_files: set[str] = set()

        for index, chunk in enumerate(chunks_raw):
            if not isinstance(chunk, Mapping):
                continue
            chunk_entry = {
                key: copy.deepcopy(value)
                for key, value in chunk.items()
                if key != "sentences"
            }
            sentences_raw = chunk.get("sentences")
            sentences: list[Any]
            if isinstance(sentences_raw, list):
                sentences = copy.deepcopy(sentences_raw)
            else:
                sentences = []

            metadata_path_str = chunk_entry.get("metadata_path")
            metadata_url_str = chunk_entry.get("metadata_url")

            sentence_count = chunk_entry.get("sentence_count")
            if not isinstance(sentence_count, int):
                sentence_count = len(sentences)

            wrote_chunk_file = False
            if sentences:
                filename = self._format_chunk_filename(index)
                destination = metadata_root / filename
                chunk_payload = {
                    "version": 1,
                    "chunk_id": chunk_entry.get("chunk_id"),
                    "range_fragment": chunk_entry.get("range_fragment"),
                    "start_sentence": chunk_entry.get("start_sentence"),
                    "end_sentence": chunk_entry.get("end_sentence"),
                    "sentence_count": len(sentences),
                    "sentences": sentences,
                }
                audio_tracks_raw = chunk_entry.get("audio_tracks") or chunk_entry.get("audioTracks")
                if isinstance(audio_tracks_raw, Mapping):
                    normalized_tracks: Dict[str, Dict[str, Any]] = {}
                    for track_key, track_value in audio_tracks_raw.items():
                        if not isinstance(track_key, str):
                            continue
                        normalized_entry = _normalize_audio_track_entry(track_value)
                        if normalized_entry:
                            normalized_tracks[track_key] = normalized_entry
                    if normalized_tracks:
                        chunk_payload["audioTracks"] = normalized_tracks
                        chunk_entry["audio_tracks"] = normalized_tracks
                        chunk_entry["audioTracks"] = normalized_tracks
                timing_tracks_raw = chunk_entry.get("timing_tracks") or chunk_entry.get("timingTracks")
                if isinstance(timing_tracks_raw, Mapping):
                    normalized_timing = copy.deepcopy(dict(timing_tracks_raw))
                    chunk_payload["timingTracks"] = normalized_timing
                    chunk_entry["timing_tracks"] = normalized_timing
                highlight_policy = chunk_entry.get("highlighting_policy")
                if isinstance(highlight_policy, str) and highlight_policy.strip():
                    normalized_policy = highlight_policy.strip()
                    chunk_payload["highlighting_policy"] = normalized_policy
                    chunk_entry["highlighting_policy"] = normalized_policy
                try:
                    self._write_chunk_file(destination, chunk_payload)
                except Exception:  # pragma: no cover - defensive logging
                    _LOGGER.debug(
                        "Unable to persist chunk metadata for job %s", job_id, exc_info=True
                    )
                    chunk_entry["sentences"] = sentences
                else:
                    metadata_rel = Path("metadata") / filename
                    metadata_path_str = metadata_rel.as_posix()
                    chunk_entry["metadata_path"] = metadata_path_str
                    url_candidate = self._file_locator.resolve_url(job_id, metadata_path_str)
                    if url_candidate:
                        chunk_entry["metadata_url"] = url_candidate
                        metadata_url_str = url_candidate
                    sentence_count = len(sentences)
                    preserved_files.add(destination.name)
                    wrote_chunk_file = True
            elif isinstance(metadata_path_str, str):
                preserved_files.add(Path(metadata_path_str).name)
                if not metadata_url_str:
                    url_candidate = self._file_locator.resolve_url(job_id, metadata_path_str)
                    if url_candidate:
                        chunk_entry["metadata_url"] = url_candidate
                        metadata_url_str = url_candidate

            chunk_entry["sentence_count"] = sentence_count
            if isinstance(metadata_path_str, str) and metadata_path_str.strip():
                for heavy_key in (
                    "sentences",
                    "audio_tracks",
                    "audioTracks",
                    "timing_tracks",
                    "timingTracks",
                ):
                    chunk_entry.pop(heavy_key, None)
            if isinstance(metadata_path_str, str) and metadata_path_str:
                chunk_entry.pop("sentences", None)

            manifest_entries.append(
                {
                    "index": index,
                    "chunk_id": chunk_entry.get("chunk_id"),
                    "path": metadata_path_str if isinstance(metadata_path_str, str) else None,
                    "url": metadata_url_str if isinstance(metadata_url_str, str) else None,
                    "sentence_count": chunk_entry.get("sentence_count"),
                }
            )
            updated_chunks.append(chunk_entry)

        self._cleanup_unused_chunk_files(metadata_root, preserved_files)

        payload["chunks"] = updated_chunks
        chunk_manifest: Optional[Dict[str, Any]]
        if updated_chunks:
            chunk_manifest = {
                "chunk_count": len(updated_chunks),
                "chunks": manifest_entries,
            }
        else:
            chunk_manifest = None
        return payload, chunk_manifest

    def _write_chunk_file(self, destination: Path, payload: Mapping[str, Any]) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        serialized = json.dumps(payload, ensure_ascii=False, indent=2)
        tmp_handle = tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=destination.parent, delete=False
        )
        try:
            with tmp_handle as handle:
                handle.write(serialized)
                handle.flush()
            Path(tmp_handle.name).replace(destination)
        except Exception:
            Path(tmp_handle.name).unlink(missing_ok=True)
            raise

    def _cleanup_unused_chunk_files(self, metadata_root: Path, preserved: set[str]) -> None:
        for existing in metadata_root.glob("chunk_*.json"):
            if existing.name in preserved:
                continue
            try:
                existing.unlink()
            except FileNotFoundError:
                continue
            except OSError:  # pragma: no cover - defensive logging
                _LOGGER.debug(
                    "Unable to remove stale chunk metadata file %s", existing, exc_info=True
                )

    @staticmethod
    def _format_chunk_filename(index: int) -> str:
        return f"chunk_{index:04d}.json"

    def _normalize_generated_files(
        self, job_id: str, raw: Optional[Any]
    ) -> Optional[Dict[str, Any]]:
        if not raw:
            return None
        if not isinstance(raw, Mapping):
            return copy.deepcopy(raw)  # type: ignore[return-value]

        chunks_raw = raw.get("chunks", [])
        if not isinstance(chunks_raw, list):
            return None

        job_root = self._file_locator.resolve_path(job_id)
        normalized_chunks: list[Dict[str, Any]] = []
        for chunk in chunks_raw:
            if not isinstance(chunk, Mapping):
                continue
            has_metadata_file = False
            metadata_path = chunk.get("metadata_path")
            if isinstance(metadata_path, str) and metadata_path.strip():
                has_metadata_file = True

            chunk_entry: Dict[str, Any] = {
                "chunk_id": chunk.get("chunk_id"),
                "range_fragment": chunk.get("range_fragment"),
                "start_sentence": chunk.get("start_sentence"),
                "end_sentence": chunk.get("end_sentence"),
                "files": [],
            }
            if has_metadata_file:
                chunk_entry["metadata_path"] = metadata_path.strip()
            metadata_url = chunk.get("metadata_url")
            if isinstance(metadata_url, str) and metadata_url.strip():
                chunk_entry["metadata_url"] = metadata_url
            sentence_count = chunk.get("sentence_count")
            if isinstance(sentence_count, int):
                chunk_entry["sentence_count"] = sentence_count
            sentences_raw = chunk.get("sentences")
            if isinstance(sentences_raw, list) and not has_metadata_file:
                chunk_entry["sentences"] = copy.deepcopy(sentences_raw)
            files_raw = chunk.get("files", [])
            if not isinstance(files_raw, list):
                files_raw = []
            for file_entry in files_raw:
                if not isinstance(file_entry, Mapping):
                    continue
                normalized_entry: Dict[str, Any] = {}
                file_type = file_entry.get("type")
                if file_type is not None:
                    normalized_entry["type"] = file_type

                relative_path_value = file_entry.get("relative_path")
                relative_path: Optional[str] = None
                path_candidate: Optional[Path] = None

                if relative_path_value:
                    relative_candidate = PurePosixPath(
                        str(relative_path_value).replace("\\", "/")
                    )
                    if not relative_candidate.is_absolute() and ".." not in relative_candidate.parts:
                        relative_path = relative_candidate.as_posix()
                        path_candidate = job_root.joinpath(*relative_candidate.parts)

                path_value = file_entry.get("path")
                if path_candidate is None and path_value:
                    path_candidate = Path(str(path_value))
                    if not path_candidate.is_absolute():
                        path_candidate = job_root / path_candidate

                if path_candidate is not None:
                    normalized_entry["path"] = path_candidate.as_posix()
                    if relative_path is None:
                        try:
                            relative_candidate = path_candidate.relative_to(job_root)
                        except ValueError:
                            relative_candidate = None
                        else:
                            relative_path = relative_candidate.as_posix()

                url: Optional[str] = None
                if relative_path:
                    normalized_entry["relative_path"] = relative_path
                    try:
                        url = self._file_locator.resolve_url(job_id, relative_path)
                    except ValueError:
                        url = None
                if url:
                    normalized_entry["url"] = url
                chunk_entry.setdefault("files", []).append(normalized_entry)
            audio_tracks_raw = chunk.get("audio_tracks") or chunk.get("audioTracks")
            if isinstance(audio_tracks_raw, Mapping) and not has_metadata_file:
                normalized_tracks: Dict[str, Dict[str, Any]] = {}
                for track_key, track_value in audio_tracks_raw.items():
                    if not isinstance(track_key, str):
                        continue
                    normalized_entry = _normalize_audio_track_entry(track_value)
                    if normalized_entry:
                        normalized_tracks[track_key] = normalized_entry
                if normalized_tracks:
                    chunk_entry["audio_tracks"] = normalized_tracks
                    chunk_entry["audioTracks"] = normalized_tracks

            timing_tracks_raw = chunk.get("timing_tracks") or chunk.get("timingTracks")
            if isinstance(timing_tracks_raw, Mapping) and not has_metadata_file:
                normalized_timing = copy.deepcopy(dict(timing_tracks_raw))
                chunk_entry["timing_tracks"] = normalized_timing
                chunk_entry["timingTracks"] = normalized_timing
            normalized_chunks.append(chunk_entry)

        files_index: list[Dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()
        for chunk in normalized_chunks:
            chunk_id = chunk.get("chunk_id")
            range_fragment = chunk.get("range_fragment")
            start_sentence = chunk.get("start_sentence")
            end_sentence = chunk.get("end_sentence")
            for entry in chunk.get("files", []):
                path_value = entry.get("path")
                file_type = entry.get("type")
                if not path_value:
                    continue
                key = (str(path_value), str(file_type))
                if key in seen:
                    continue
                seen.add(key)
                record = dict(entry)
                record["chunk_id"] = chunk_id
                if range_fragment is not None and "range_fragment" not in record:
                    record["range_fragment"] = range_fragment
                if start_sentence is not None and "start_sentence" not in record:
                    record["start_sentence"] = start_sentence
                if end_sentence is not None and "end_sentence" not in record:
                    record["end_sentence"] = end_sentence
                files_index.append(record)

        extras: Dict[str, Any] = {}
        for key, value in raw.items():
            if key in {"chunks", "files", "complete"}:
                continue
            extras[key] = copy.deepcopy(value)

        if not normalized_chunks and not files_index and not extras:
            return None

        complete_flag = raw.get("complete")
        payload: Dict[str, Any] = {"chunks": normalized_chunks, "files": files_index}
        if isinstance(complete_flag, bool):
            payload["complete"] = complete_flag
        if extras:
            payload.update(extras)
        return payload


__all__ = ["PipelineJobPersistence"]
