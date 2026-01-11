"""Schemas for pipeline job status and lifecycle responses."""

from __future__ import annotations

import copy
import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

from pydantic import BaseModel, Field

from ...services.file_locator import FileLocator
from modules.permissions import resolve_access_policy
from .access import AccessPolicyPayload
from ...transliteration import resolve_local_transliteration_module
from ..jobs import PipelineJob, PipelineJobStatus
from .pipeline_results import PipelineResponsePayload
from .progress import ProgressEventPayload


class JobParameterSnapshot(BaseModel):
    """Captured subset of the inputs/configuration used to execute a job."""

    input_file: Optional[str] = None
    base_output_file: Optional[str] = None
    input_language: Optional[str] = None
    source_language: Optional[str] = None
    target_languages: List[str] = Field(default_factory=list)
    start_sentence: Optional[int] = None
    end_sentence: Optional[int] = None
    sentences_per_output_file: Optional[int] = None
    llm_model: Optional[str] = None
    audio_mode: Optional[str] = None
    audio_bitrate_kbps: Optional[int] = None
    selected_voice: Optional[str] = None
    voice_overrides: Dict[str, str] = Field(default_factory=dict)
    worker_count: Optional[int] = None
    batch_size: Optional[int] = None
    show_original: Optional[bool] = None
    enable_transliteration: Optional[bool] = None
    start_time_offset_seconds: Optional[float] = None
    end_time_offset_seconds: Optional[float] = None
    video_path: Optional[str] = None
    subtitle_path: Optional[str] = None
    tempo: Optional[float] = None
    macos_reading_speed: Optional[int] = None
    output_dir: Optional[str] = None
    original_mix_percent: Optional[float] = None
    flush_sentences: Optional[int] = None
    split_batches: Optional[bool] = None
    include_transliteration: Optional[bool] = None
    add_images: Optional[bool] = None
    translation_provider: Optional[str] = None
    translation_batch_size: Optional[int] = None
    transliteration_mode: Optional[str] = None
    transliteration_model: Optional[str] = None
    transliteration_module: Optional[str] = None


class ImageGenerationSummary(BaseModel):
    """Aggregated image generation statistics for pipeline jobs."""

    enabled: bool
    expected: Optional[int] = None
    generated: Optional[int] = None
    completed: Optional[int] = None
    pending: Optional[int] = None
    percent: Optional[int] = None
    sentence_total: Optional[int] = None
    batch_size: Optional[int] = None


def _coerce_str(value: Any) -> Optional[str]:
    if isinstance(value, str):
        trimmed = value.strip()
        if trimmed:
            return trimmed
    return None


def _coerce_int(value: Any) -> Optional[int]:
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            return int(float(stripped))
        except ValueError:
            return None
    return None


def _coerce_float(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            return float(stripped)
        except ValueError:
            return None
    return None


def _load_image_prompt_plan_summary(job_id: str) -> Optional[Dict[str, Any]]:
    locator = FileLocator()
    summary_path = locator.resolve_metadata_path(job_id, "image_prompt_plan_summary.json")
    if not summary_path.exists():
        return None
    try:
        payload = json.loads(summary_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return dict(payload) if isinstance(payload, Mapping) else None


def _count_generated_images(payload: Mapping[str, Any]) -> int:
    def _is_image_entry(entry: Mapping[str, Any]) -> bool:
        type_value = entry.get("type")
        type_label = str(type_value).strip().lower() if type_value is not None else ""
        path_value = entry.get("path") or entry.get("relative_path") or entry.get("relativePath")
        path_label = str(path_value).strip().lower() if path_value is not None else ""
        if type_label == "image":
            return True
        if "/images/" in path_label and path_label.endswith((".png", ".jpg", ".jpeg")):
            return True
        return False

    seen: set[str] = set()
    count = 0
    files_section = payload.get("files")
    if isinstance(files_section, list):
        for entry in files_section:
            if not isinstance(entry, Mapping):
                continue
            if not _is_image_entry(entry):
                continue
            path_value = entry.get("path") or entry.get("relative_path") or entry.get("relativePath")
            key = str(path_value or entry)
            if key in seen:
                continue
            seen.add(key)
            count += 1

    chunks_section = payload.get("chunks")
    if isinstance(chunks_section, list):
        for chunk in chunks_section:
            if not isinstance(chunk, Mapping):
                continue
            files = chunk.get("files")
            if not isinstance(files, list):
                continue
            for entry in files:
                if not isinstance(entry, Mapping):
                    continue
                if not _is_image_entry(entry):
                    continue
                path_value = entry.get("path") or entry.get("relative_path") or entry.get("relativePath")
                key = str(path_value or entry)
                if key in seen:
                    continue
                seen.add(key)
                count += 1

    return count


def _resolve_image_prompt_summary(
    job_id: str,
    generated_files: Optional[Mapping[str, Any]],
) -> Optional[Dict[str, Any]]:
    if isinstance(generated_files, Mapping):
        summary = generated_files.get("image_prompt_plan_summary")
        if isinstance(summary, Mapping):
            return dict(summary)
    return _load_image_prompt_plan_summary(job_id)


def _build_image_generation_summary(
    job: PipelineJob,
    *,
    parameters: Optional[JobParameterSnapshot],
    latest_event: Optional[ProgressEventPayload],
    generated_files: Optional[Mapping[str, Any]],
) -> Optional[ImageGenerationSummary]:
    if job.job_type not in {"pipeline", "book"}:
        return None
    enabled = bool(parameters.add_images) if parameters is not None and parameters.add_images is not None else False
    summary = _resolve_image_prompt_summary(job.job_id, generated_files)
    if parameters is None or parameters.add_images is None:
        if summary or generated_files:
            enabled = True
    if not enabled and not generated_files and not summary:
        return None
    summary_record = summary or {}
    quality = summary_record.get("quality")
    quality_record = quality if isinstance(quality, Mapping) else {}

    start_sentence = _coerce_int(summary_record.get("start_sentence") or summary_record.get("startSentence"))
    end_sentence = _coerce_int(summary_record.get("end_sentence") or summary_record.get("endSentence"))
    sentence_total: Optional[int] = None
    if start_sentence is not None and end_sentence is not None and end_sentence >= start_sentence:
        sentence_total = int(end_sentence - start_sentence + 1)
    if sentence_total is None:
        sentence_total = _coerce_int(quality_record.get("total_sentences") or quality_record.get("totalSentences"))

    batch_size = _coerce_int(
        summary_record.get("prompt_batch_size")
        or summary_record.get("promptBatchSize")
        or quality_record.get("prompt_batch_size")
        or quality_record.get("promptBatchSize")
    )
    if batch_size is not None:
        batch_size = max(1, int(batch_size))

    expected: Optional[int] = None
    if sentence_total is not None and batch_size is not None:
        if batch_size > 1:
            total_batches = _coerce_int(quality_record.get("total_batches") or quality_record.get("totalBatches"))
            if total_batches is not None:
                expected = max(0, int(total_batches))
            else:
                expected = int(math.ceil(sentence_total / float(batch_size))) if sentence_total > 0 else 0
        else:
            expected = max(0, int(sentence_total))

    if generated_files:
        generated = _count_generated_images(generated_files)
    else:
        generated = 0 if enabled else None

    completed: Optional[int] = None
    pending: Optional[int] = None
    if expected is not None and sentence_total is not None and latest_event is not None:
        try:
            completed_total = int(latest_event.snapshot.completed)
        except Exception:
            completed_total = None
        if completed_total is not None:
            completed = max(0, min(expected, completed_total - sentence_total))
            pending = max(0, expected - completed)

    percent: Optional[int] = None
    if expected is not None and expected > 0 and generated is not None:
        percent = max(0, min(100, int(round((generated / expected) * 100))))

    return ImageGenerationSummary(
        enabled=enabled,
        expected=expected,
        generated=generated,
        completed=completed,
        pending=pending,
        percent=percent,
        sentence_total=sentence_total,
        batch_size=batch_size,
    )


def _coerce_bool(value: Any) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "on"}:
            return True
        if lowered in {"false", "0", "no", "off"}:
            return False
    return None


def _normalize_language_list(value: Any) -> List[str]:
    languages: List[str] = []
    if isinstance(value, (list, tuple, set)):
        for entry in value:
            text = _coerce_str(entry)
            if text:
                languages.append(text)
    else:
        text = _coerce_str(value)
        if text:
            languages.append(text)
    return languages


def _normalize_voice_overrides(value: Any) -> Dict[str, str]:
    if not isinstance(value, Mapping):
        return {}
    overrides: Dict[str, str] = {}
    for raw_key, raw_value in value.items():
        if not isinstance(raw_key, str):
            continue
        key = raw_key.strip()
        if not key:
            continue
        normalized_value = _coerce_str(raw_value)
        if normalized_value:
            overrides[key] = normalized_value
    return overrides


def _build_pipeline_parameters(payload: Mapping[str, Any]) -> Optional[JobParameterSnapshot]:
    inputs = payload.get("inputs")
    if not isinstance(inputs, Mapping):
        return None

    target_languages = _normalize_language_list(inputs.get("target_languages"))
    input_language = _coerce_str(inputs.get("input_language"))
    start_sentence = _coerce_int(inputs.get("start_sentence"))
    end_sentence = _coerce_int(inputs.get("end_sentence"))
    sentences_per_file = _coerce_int(inputs.get("sentences_per_output_file"))
    audio_mode = _coerce_str(inputs.get("audio_mode"))
    audio_bitrate_kbps = _coerce_int(inputs.get("audio_bitrate_kbps"))
    selected_voice = _coerce_str(inputs.get("selected_voice"))
    voice_overrides = _normalize_voice_overrides(inputs.get("voice_overrides"))
    include_transliteration = _coerce_bool(inputs.get("include_transliteration"))
    add_images = _coerce_bool(inputs.get("add_images"))
    translation_provider = _coerce_str(inputs.get("translation_provider"))
    translation_batch_size = _coerce_int(inputs.get("translation_batch_size"))
    transliteration_mode_raw = _coerce_str(inputs.get("transliteration_mode"))

    input_file = _coerce_str(inputs.get("input_file"))
    base_output_file = _coerce_str(inputs.get("base_output_file"))

    llm_model = None
    config_payload = payload.get("config")
    if isinstance(config_payload, Mapping):
        llm_model = _coerce_str(config_payload.get("ollama_model"))

    pipeline_overrides = payload.get("pipeline_overrides")
    if isinstance(pipeline_overrides, Mapping):
        override_model = _coerce_str(pipeline_overrides.get("ollama_model"))
        if override_model:
            llm_model = override_model
        override_audio_mode = _coerce_str(pipeline_overrides.get("audio_mode"))
        if override_audio_mode:
            audio_mode = override_audio_mode
        override_audio_bitrate = _coerce_int(pipeline_overrides.get("audio_bitrate_kbps"))
        if override_audio_bitrate is not None:
            audio_bitrate_kbps = override_audio_bitrate
        override_voice_overrides = _normalize_voice_overrides(
            pipeline_overrides.get("voice_overrides")
        )
        if override_voice_overrides:
            voice_overrides = override_voice_overrides

    normalized_transliteration_mode = None
    if transliteration_mode_raw:
        normalized = transliteration_mode_raw.strip().lower().replace("_", "-")
        if normalized in {"python", "python-module", "module", "local-module"}:
            normalized_transliteration_mode = "python"
        else:
            normalized_transliteration_mode = "default"

    transliteration_model = None
    transliteration_module = None
    if normalized_transliteration_mode == "default":
        transliteration_model = llm_model
    elif normalized_transliteration_mode == "python":
        target_for_module = target_languages[0] if target_languages else None
        if target_for_module:
            transliteration_module = resolve_local_transliteration_module(target_for_module)

    return JobParameterSnapshot(
        input_file=input_file,
        base_output_file=base_output_file,
        input_language=input_language,
        target_languages=target_languages,
        start_sentence=start_sentence,
        end_sentence=end_sentence,
        sentences_per_output_file=sentences_per_file,
        llm_model=llm_model,
        audio_mode=audio_mode,
        audio_bitrate_kbps=audio_bitrate_kbps,
        selected_voice=selected_voice,
        voice_overrides=voice_overrides,
        include_transliteration=include_transliteration,
        add_images=add_images,
        translation_provider=translation_provider,
        translation_batch_size=translation_batch_size,
        transliteration_mode=normalized_transliteration_mode,
        transliteration_model=transliteration_model,
        transliteration_module=transliteration_module,
    )


def _build_subtitle_parameters(payload: Mapping[str, Any]) -> Optional[JobParameterSnapshot]:
    options = payload.get("options")
    if not isinstance(options, Mapping):
        return None

    subtitle_path = (
        _coerce_str(payload.get("original_name"))
        or _coerce_str(payload.get("source_path"))
        or _coerce_str(payload.get("source_file"))
        or _coerce_str(payload.get("submitted_source"))
    )

    target_language = _coerce_str(options.get("target_language"))
    target_languages = [target_language] if target_language else []
    input_language = _coerce_str(options.get("input_language")) or _coerce_str(
        options.get("original_language")
    )

    return JobParameterSnapshot(
        input_language=input_language,
        target_languages=target_languages,
        subtitle_path=subtitle_path,
        llm_model=_coerce_str(options.get("llm_model")),
        translation_provider=_coerce_str(options.get("translation_provider")),
        translation_batch_size=_coerce_int(options.get("translation_batch_size")),
        transliteration_mode=_coerce_str(options.get("transliteration_mode")),
        worker_count=_coerce_int(options.get("worker_count")),
        batch_size=_coerce_int(options.get("batch_size")),
        show_original=_coerce_bool(options.get("show_original")),
        enable_transliteration=_coerce_bool(options.get("enable_transliteration")),
        start_time_offset_seconds=_coerce_float(options.get("start_time_offset")),
        end_time_offset_seconds=_coerce_float(options.get("end_time_offset")),
    )


def _build_youtube_dub_parameters(payload: Mapping[str, Any]) -> Optional[JobParameterSnapshot]:
    video_path = _coerce_str(payload.get("video_path"))
    subtitle_path = _coerce_str(payload.get("subtitle_path"))
    source_language = _coerce_str(payload.get("source_language"))
    target_language = _coerce_str(payload.get("target_language"))
    voice = _coerce_str(payload.get("voice"))
    tempo = _coerce_float(payload.get("tempo"))
    reading_speed = _coerce_int(payload.get("macos_reading_speed"))
    output_dir = _coerce_str(payload.get("output_dir"))
    start_offset = _coerce_float(payload.get("start_time_offset"))
    end_offset = _coerce_float(payload.get("end_time_offset"))
    original_mix_percent = _coerce_float(payload.get("original_mix_percent"))
    flush_sentences = _coerce_int(payload.get("flush_sentences"))
    llm_model = _coerce_str(payload.get("llm_model"))
    translation_provider = _coerce_str(payload.get("translation_provider"))
    translation_batch_size = _coerce_int(payload.get("translation_batch_size"))
    transliteration_mode = _coerce_str(payload.get("transliteration_mode"))
    split_batches = _coerce_bool(payload.get("split_batches"))

    target_languages = [target_language] if target_language else []

    return JobParameterSnapshot(
        input_file=video_path,
        video_path=video_path,
        subtitle_path=subtitle_path,
        input_language=source_language,
        source_language=source_language,
        target_languages=target_languages,
        selected_voice=voice,
        tempo=tempo,
        macos_reading_speed=reading_speed,
        output_dir=output_dir,
        start_time_offset_seconds=start_offset,
        end_time_offset_seconds=end_offset,
        original_mix_percent=original_mix_percent,
        flush_sentences=flush_sentences,
        llm_model=llm_model,
        translation_provider=translation_provider,
        translation_batch_size=translation_batch_size,
        transliteration_mode=transliteration_mode,
        split_batches=split_batches,
    )


def _build_job_parameters(job: PipelineJob) -> Optional[JobParameterSnapshot]:
    payload: Optional[Mapping[str, Any]] = None
    if isinstance(job.request_payload, Mapping):
        payload = job.request_payload
    elif isinstance(job.resume_context, Mapping):
        payload = job.resume_context

    if payload is None:
        return None

    if job.job_type == "subtitle":
        return _build_subtitle_parameters(payload)
    if job.job_type == "youtube_dub":
        return _build_youtube_dub_parameters(payload)
    return _build_pipeline_parameters(payload)


def _filename_stem(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    trimmed = value.strip()
    if not trimmed:
        return None
    basename = trimmed.split("/")[-1].split("\\")[-1]
    try:
        stem = Path(basename).stem
    except Exception:
        return basename
    return stem or basename


def _resolve_job_label(job: PipelineJob) -> Optional[str]:
    """Return a human-friendly label for ``job`` when possible."""

    request_payload: Optional[Mapping[str, Any]] = None
    if isinstance(job.request_payload, Mapping):
        request_payload = job.request_payload
    elif isinstance(job.resume_context, Mapping):
        request_payload = job.resume_context

    if job.job_type == "subtitle":
        if request_payload is not None:
            media_metadata = request_payload.get("media_metadata")
            if isinstance(media_metadata, Mapping):
                label = media_metadata.get("job_label")
                if isinstance(label, str) and label.strip():
                    return label.strip()
            for key in ("original_name", "source_file", "source_path", "submitted_source"):
                stem = _filename_stem(request_payload.get(key))
                if stem:
                    return stem

        if isinstance(job.result_payload, Mapping):
            subtitle_section = job.result_payload.get("subtitle")
            if isinstance(subtitle_section, Mapping):
                metadata = subtitle_section.get("metadata")
                if isinstance(metadata, Mapping):
                    label = metadata.get("job_label")
                    if isinstance(label, str) and label.strip():
                        return label.strip()
                    for key in ("input_file", "source", "subtitle_name"):
                        stem = _filename_stem(metadata.get(key))
                        if stem:
                            return stem

        return None

    if job.job_type == "youtube_dub":
        if request_payload is not None:
            media_metadata = request_payload.get("media_metadata")
            if isinstance(media_metadata, Mapping):
                label = media_metadata.get("job_label")
                if isinstance(label, str) and label.strip():
                    return label.strip()
            for key in ("video_path", "subtitle_path"):
                stem = _filename_stem(request_payload.get(key))
                if stem:
                    return stem

        if isinstance(job.result_payload, Mapping):
            dub_section = job.result_payload.get("youtube_dub")
            if isinstance(dub_section, Mapping):
                for key in ("video_path", "output_path", "subtitle_path"):
                    stem = _filename_stem(dub_section.get(key))
                    if stem:
                        return stem

        return None

    if request_payload is not None and job.job_type in {"pipeline", "book"}:
        inputs = request_payload.get("inputs")
        if isinstance(inputs, Mapping):
            for key in ("job_label", "title", "name", "topic"):
                candidate = inputs.get(key)
                if isinstance(candidate, str) and candidate.strip():
                    return candidate.strip()
            book_metadata = inputs.get("book_metadata")
            if isinstance(book_metadata, Mapping):
                for key in ("job_label", "title", "book_title", "book_name", "name", "topic"):
                    candidate = book_metadata.get(key)
                    if isinstance(candidate, str) and candidate.strip():
                        return candidate.strip()
            stem = _filename_stem(inputs.get("input_file")) or _filename_stem(
                inputs.get("base_output_file")
            )
            if stem:
                return stem

    return None


class PipelineStatusResponse(BaseModel):
    """Full status payload for a pipeline job."""

    job_id: str
    job_type: str
    status: PipelineJobStatus
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    result: Optional[Dict[str, Any] | PipelineResponsePayload]
    error: Optional[str]
    latest_event: Optional[ProgressEventPayload]
    tuning: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = None
    user_role: Optional[str] = None
    access: Optional[AccessPolicyPayload] = None
    generated_files: Optional[Dict[str, Any]] = None
    parameters: Optional[JobParameterSnapshot] = None
    media_completed: Optional[bool] = None
    retry_summary: Optional[Dict[str, Dict[str, int]]] = None
    job_label: Optional[str] = None
    image_generation: Optional[ImageGenerationSummary] = None

    @classmethod
    def from_job(cls, job: PipelineJob) -> "PipelineStatusResponse":
        result_payload: Optional[PipelineResponsePayload | Dict[str, Any]] = None
        if job.job_type in {"pipeline", "book"}:
            if job.result is not None:
                result_payload = PipelineResponsePayload.from_response(job.result)
            elif job.result_payload is not None:
                result_payload = PipelineResponsePayload(**job.result_payload)
        elif job.result_payload is not None:
            result_payload = copy.deepcopy(job.result_payload)

        if job.job_type in {"pipeline", "book"} and result_payload is not None:
            cover_url = f"/api/pipelines/{job.job_id}/cover"
            if isinstance(result_payload, PipelineResponsePayload):
                book_metadata = result_payload.book_metadata
                if (
                    isinstance(book_metadata, dict)
                    and book_metadata.get("job_cover_asset")
                    and not book_metadata.get("job_cover_asset_url")
                ):
                    book_metadata["job_cover_asset_url"] = cover_url
            elif isinstance(result_payload, Mapping):
                raw_book = result_payload.get("book_metadata")
                if (
                    isinstance(raw_book, Mapping)
                    and raw_book.get("job_cover_asset")
                    and not raw_book.get("job_cover_asset_url")
                ):
                    updated = dict(raw_book)
                    updated["job_cover_asset_url"] = cover_url
                    result_payload = dict(result_payload)
                    result_payload["book_metadata"] = updated

        latest_event = None
        if job.last_event is not None:
            latest_event = ProgressEventPayload.from_event(job.last_event)

        generated_files = None
        if job.generated_files is not None:
            generated_files = copy.deepcopy(job.generated_files)
        elif job.tracker is not None:
            generated_files = job.tracker.get_generated_files() or None

        parameters = _build_job_parameters(job)
        image_generation = _build_image_generation_summary(
            job,
            parameters=parameters,
            latest_event=latest_event,
            generated_files=generated_files,
        )
        default_visibility = "private" if job.user_id else "public"
        access_policy = resolve_access_policy(job.access, default_visibility=default_visibility)
        access_payload = AccessPolicyPayload.model_validate(access_policy.to_dict())

        return cls(
            job_id=job.job_id,
            job_type=job.job_type,
            status=job.status,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            result=result_payload,
            error=job.error_message,
            latest_event=latest_event,
            tuning=dict(job.tuning_summary) if job.tuning_summary else None,
            user_id=job.user_id,
            user_role=job.user_role,
            access=access_payload,
            generated_files=generated_files,
            parameters=parameters,
            media_completed=job.media_completed,
            retry_summary=job.tracker.get_retry_counts() if job.tracker else job.retry_summary,
            job_label=_resolve_job_label(job),
            image_generation=image_generation,
        )


class PipelineJobListResponse(BaseModel):
    """Response payload describing a collection of pipeline jobs."""

    jobs: List[PipelineStatusResponse] = Field(default_factory=list)


class PipelineJobActionResponse(BaseModel):
    """Response payload for job lifecycle mutations."""

    job: PipelineStatusResponse
    error: Optional[str] = None
