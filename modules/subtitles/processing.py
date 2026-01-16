"""Core subtitle parsing and processing logic."""

from __future__ import annotations

import contextlib
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional, Sequence, Tuple

from modules import text_normalization as text_norm
from modules.llm_client import create_client
from modules.retry_annotations import format_retry_failure, is_failure_annotation
from modules.progress_tracker import ProgressTracker
from modules.transliteration import (
    TransliterationService,
    get_transliterator,
    resolve_local_transliteration_module,
)
from modules.translation_engine import _unexpected_script_used, translate_batch

from .common import ASS_EXTENSION, SRT_EXTENSION, logger
from .errors import SubtitleJobCancelled, SubtitleProcessingError
from .io import load_subtitle_cues, write_srt
from .language import (
    SubtitleLanguageContext,
    _normalize_language_label,
    _resolve_language_context,
    _target_uses_cyrillic_script,
    _target_uses_non_latin_script,
)
from .merge import (
    _merge_redundant_rendered_cues,
    _merge_rendered_timeline,
    _deduplicate_cues_by_text,
    _merge_overlapping_lines,
    _should_merge_youtube_cues,
    merge_youtube_subtitle_cues,
)
from .models import (
    SubtitleCue,
    SubtitleHtmlEntry,
    SubtitleJobOptions,
    SubtitleProcessingResult,
)
from .render import (
    CueTextRenderer,
    _HtmlTranscriptWriter,
    _SubtitleFileWriter,
    _build_output_cues,
    _resolve_ass_emphasis_scale,
    _resolve_ass_font_size,
)
from .text import _format_timecode_label, _normalize_text
from .translation import _looks_like_gibberish_translation, _translate_text
from .utils import _is_cancelled, _resolve_batch_size, _resolve_worker_count


_LATIN_ASS_EMPHASIS_CAP = 1.1


def process_subtitle_file(
    source_path: Path,
    output_path: Path,
    options: SubtitleJobOptions,
    *,
    mirror_output_path: Optional[Path] = None,
    tracker: Optional[ProgressTracker] = None,
    stop_event=None,
    transliterator: Optional[TransliterationService] = None,
    collect_transcript_entries: bool = False,
    on_transcript_batch: Optional[Callable[[Sequence[Tuple[int, SubtitleHtmlEntry]]], None]] = None,
) -> SubtitleProcessingResult:
    """Process ``source_path`` and persist the translated subtitles."""

    cues = load_subtitle_cues(source_path)

    start_offset = max(0.0, options.start_time_offset or 0.0)
    end_offset = options.end_time_offset
    if end_offset is not None:
        end_offset = max(0.0, float(end_offset))
        if end_offset <= start_offset:
            raise SubtitleProcessingError("End time must be greater than start time")

    if start_offset > 0 or end_offset is not None:
        trimmed: List[SubtitleCue] = []
        for cue in cues:
            if cue.start < start_offset:
                continue
            if end_offset is not None and cue.start >= end_offset:
                continue
            clipped_end = cue.end
            if end_offset is not None and cue.end > end_offset:
                clipped_end = end_offset
            if clipped_end <= cue.start:
                continue
            trimmed.append(
                SubtitleCue(
                    index=cue.index,
                    start=cue.start,
                    end=clipped_end,
                    lines=list(cue.lines),
                )
            )
        cues = trimmed

    if options.generate_audio_book:
        cues = merge_youtube_subtitle_cues(cues)
    total_cues = len(cues)
    if not cues:
        if end_offset is not None:
            start_label = _format_timecode_label(start_offset)
            end_label = _format_timecode_label(end_offset)
            raise SubtitleProcessingError(
                f"No cues found between {start_label} and {end_label}"
            )
        if start_offset > 0:
            label = _format_timecode_label(start_offset)
            raise SubtitleProcessingError(f"No cues found at or after start time {label}")
        raise SubtitleProcessingError("No cues processed from source subtitle")

    language_context = _resolve_language_context(cues, options)

    batch_size = _resolve_batch_size(options.batch_size, total_cues)
    worker_count = _resolve_worker_count(options.worker_count, batch_size, total_cues)

    if tracker is not None:
        total_steps = total_cues
        if options.generate_audio_book:
            total_steps *= 2
        tracker.set_total(total_steps)
        tracker.publish_start(
            {
                "stage": "subtitle",
                "input_file": source_path.name,
                "target_language": options.target_language,
                "batch_size": batch_size,
                "workers": worker_count,
                "start_time_offset": start_offset,
                "generate_audio_book": bool(options.generate_audio_book),
            }
        )

    transliteration_enabled = (
        options.enable_transliteration
        and _target_uses_non_latin_script(options.target_language)
    )

    transliterator_to_use = transliterator
    if transliteration_enabled and transliterator_to_use is None:
        transliterator_to_use = get_transliterator()
    transliteration_enabled = transliteration_enabled and transliterator_to_use is not None
    translation_batch_size = options.translation_batch_size
    use_llm_batching = (
        options.translation_provider == "llm"
        and translation_batch_size is not None
        and translation_batch_size > 1
    )
    allow_llm_transliteration = (
        transliteration_enabled
        and options.transliteration_mode != "python"
        and transliterator_to_use is not None
    )

    resolved_ass_font_size = _resolve_ass_font_size(options.ass_font_size)
    resolved_ass_emphasis = _resolve_ass_emphasis_scale(options.ass_emphasis_scale)
    if options.output_format == "ass" and (
        not _target_uses_non_latin_script(options.target_language)
        or _target_uses_cyrillic_script(options.target_language)
    ):
        resolved_ass_emphasis = min(resolved_ass_emphasis, _LATIN_ASS_EMPHASIS_CAP)
    temp_output = output_path.with_suffix(output_path.suffix + ".tmp")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    renderer = CueTextRenderer(
        options.output_format,
        options.color_palette,
        emphasis_scale=resolved_ass_emphasis,
    )
    output_extension = ASS_EXTENSION if options.output_format == "ass" else SRT_EXTENSION
    html_writer = _HtmlTranscriptWriter(output_path)

    translated_count = 0
    next_index = 1
    mirror_next_index = 1
    mirror_target: Optional[Path] = None
    if mirror_output_path is not None:
        try:
            mirror_target = mirror_output_path.expanduser()
            if mirror_target.suffix.lower() != output_extension:
                mirror_target = mirror_target.with_suffix(output_extension)
            mirror_target.parent.mkdir(parents=True, exist_ok=True)
            mirror_target.unlink(missing_ok=True)
        except Exception:  # pragma: no cover - best effort mirror
            logger.warning(
                "Unable to prepare subtitle mirror output at %s",
                mirror_output_path,
                exc_info=True,
            )
            mirror_target = None

    mirror_html_writer: Optional[_HtmlTranscriptWriter] = (
        _HtmlTranscriptWriter(mirror_target) if mirror_target is not None else None
    )
    transcript_entries: List[SubtitleHtmlEntry] = []

    try:
        temp_output.unlink(missing_ok=True)
        all_rendered_cues: List[SubtitleCue] = []
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            for batch_number, batch_start in enumerate(range(0, total_cues, batch_size), start=1):
                if _is_cancelled(stop_event):
                    raise SubtitleJobCancelled("Subtitle job interrupted by cancellation request")

                batch = cues[batch_start : batch_start + batch_size]
                translation_overrides: List[Optional[str]] = [None] * len(batch)
                transliteration_overrides: List[Optional[str]] = [None] * len(batch)
                if use_llm_batching and batch:
                    batch_sentences = [cue.as_text() for cue in batch]
                    batch_sentence_numbers = [
                        batch_start + idx + 1 for idx in range(len(batch_sentences))
                    ]
                    client_context = (
                        create_client(model=options.llm_model)
                        if options.llm_model
                        else contextlib.nullcontext()
                    )
                    transliteration_model = (
                        options.transliteration_model
                        if allow_llm_transliteration
                        else None
                    )
                    transliteration_context = (
                        create_client(model=transliteration_model)
                        if transliteration_model
                        and transliteration_model != options.llm_model
                        else contextlib.nullcontext()
                    )
                    try:
                        with client_context as client, transliteration_context as translit_client:
                            resolved_client = client if options.llm_model else None
                            resolved_transliteration_client = (
                                translit_client
                                if transliteration_model
                                and transliteration_model != options.llm_model
                                else None
                            )
                            translations = translate_batch(
                                batch_sentences,
                                language_context.translation_source_language,
                                options.target_language,
                                include_transliteration=allow_llm_transliteration,
                                transliteration_mode=options.transliteration_mode,
                                transliteration_client=resolved_transliteration_client,
                                translation_provider=options.translation_provider,
                                llm_batch_size=translation_batch_size,
                                client=resolved_client,
                                max_workers=worker_count,
                                progress_tracker=tracker,
                                sentence_numbers=batch_sentence_numbers,
                            )
                    except Exception:  # pragma: no cover - fallback to per-cue translation
                        logger.warning(
                            "Unable to batch translate subtitle cues; falling back to per-cue translation",
                            exc_info=True,
                        )
                        translations = []
                    if len(translations) == len(batch_sentences):
                        for idx, raw_translation in enumerate(translations):
                            raw_text = raw_translation or ""
                            if not raw_text.strip() or is_failure_annotation(raw_text):
                                continue
                            translation_line, inline_translit = text_norm.split_translation_and_transliteration(
                                raw_text
                            )
                            translation_line = _normalize_text(translation_line or raw_text)
                            inline_translit = _normalize_text(inline_translit or "")
                            if inline_translit and not text_norm.is_latin_heavy(inline_translit):
                                inline_translit = ""
                            if not translation_line:
                                continue
                            if _looks_like_gibberish_translation(
                                source=batch_sentences[idx],
                                candidate=translation_line,
                            ):
                                continue
                            translation_overrides[idx] = translation_line
                            if inline_translit:
                                transliteration_overrides[idx] = inline_translit
                processed_batch = list(
                    executor.map(
                        lambda payload: _process_cue(
                            payload[0],
                            options,
                            transliterator_to_use,
                            stop_event,
                            renderer,
                            language_context,
                            tracker,
                            translation_override=payload[1],
                            transliteration_override=payload[2],
                        ),
                        zip(batch, translation_overrides, transliteration_overrides),
                    )
                )

                html_entries: List[SubtitleHtmlEntry] = []
                transcript_batch: List[Tuple[int, SubtitleHtmlEntry]] = []
                batch_rendered: List[SubtitleCue] = []
                for offset, rendered_batch in enumerate(processed_batch, start=1):
                    cue_index = batch_start + offset
                    if tracker is not None:
                        tracker.record_step_completion(
                            stage="subtitle",
                            index=cue_index,
                            total=total_cues,
                            metadata={
                                "batch": batch_number,
                                "batch_size": batch_size,
                            },
                        )
                    all_rendered_cues.extend(rendered_batch.cues)
                    batch_rendered.extend(rendered_batch.cues)
                    translated_count += 1
                    if rendered_batch.html_entry is not None:
                        html_entries.append(rendered_batch.html_entry)
                        if on_transcript_batch is not None:
                            transcript_batch.append((cue_index, rendered_batch.html_entry))

                if html_entries:
                    html_writer.append(html_entries)
                    if mirror_html_writer is not None:
                        mirror_html_writer.append(html_entries)
                    if collect_transcript_entries:
                        transcript_entries.extend(html_entries)
                    if transcript_batch and on_transcript_batch is not None:
                        on_transcript_batch(transcript_batch)

                # Write incrementally each batch.
                if options.highlight:
                    incremental_cues = list(batch_rendered)
                    if not incremental_cues:
                        continue
                    mode = "w" if next_index == 1 else "a"
                    with temp_output.open(mode, encoding="utf-8", newline="\n") as handle:
                        writer = _SubtitleFileWriter(
                            handle,
                            renderer,
                            options.output_format,
                            start_index=next_index,
                            ass_font_size=resolved_ass_font_size,
                        )
                        next_index = writer.write(incremental_cues)
                    if mirror_target is not None:
                        try:
                            with mirror_target.open(mode, encoding="utf-8", newline="\n") as mirror_handle:
                                mirror_writer = _SubtitleFileWriter(
                                    mirror_handle,
                                    renderer,
                                    options.output_format,
                                    start_index=mirror_next_index,
                                    ass_font_size=resolved_ass_font_size,
                                )
                                mirror_next_index = mirror_writer.write(incremental_cues)
                        except Exception:  # pragma: no cover - best effort mirror
                            logger.warning(
                                "Unable to mirror subtitle output to %s",
                                mirror_target,
                                exc_info=True,
                            )
                            mirror_target = None
                            mirror_html_writer = None
                    continue

                merged_timeline = _merge_rendered_timeline(
                    all_rendered_cues,
                    preserve_states=False,
                )
                if not merged_timeline:
                    continue

                with temp_output.open("w", encoding="utf-8", newline="\n") as handle:
                    writer = _SubtitleFileWriter(
                        handle,
                        renderer,
                        options.output_format,
                        start_index=1,
                        ass_font_size=resolved_ass_font_size,
                    )
                    next_index = writer.write(merged_timeline)

                if mirror_target is not None:
                    try:
                        with mirror_target.open("w", encoding="utf-8", newline="\n") as mirror_handle:
                            mirror_writer = _SubtitleFileWriter(
                                mirror_handle,
                                renderer,
                                options.output_format,
                                start_index=1,
                                ass_font_size=resolved_ass_font_size,
                            )
                            mirror_next_index = mirror_writer.write(merged_timeline)
                    except Exception:  # pragma: no cover - best effort mirror
                        logger.warning(
                            "Unable to mirror merged subtitle output to %s",
                            mirror_target,
                            exc_info=True,
                        )
                        mirror_target = None
                        mirror_html_writer = None
    except SubtitleJobCancelled:
        temp_output.unlink(missing_ok=True)
        html_writer.discard()
        if mirror_html_writer is not None:
            mirror_html_writer.discard()
        raise
    except Exception:
        temp_output.unlink(missing_ok=True)
        html_writer.discard()
        if mirror_html_writer is not None:
            mirror_html_writer.discard()
        raise
    else:
        temp_output.replace(output_path)
        html_writer.finalize()
        if mirror_html_writer is not None:
            mirror_html_writer.finalize()

    metadata = {
        "input_file": source_path.name,
        "input_language": options.input_language,
        "original_language": options.original_language,
        "target_language": options.target_language,
        "detected_language": language_context.detected_language,
        "detected_language_code": _normalize_language_label(language_context.detected_language),
        "translation_source_language": language_context.translation_source_language,
        "translation_source_language_code": _normalize_language_label(
            language_context.translation_source_language
        ),
        "llm_model": options.llm_model,
        "translation_provider": options.translation_provider,
        "origin_translation": {
            "active": language_context.origin_translation_needed,
            "source_language": language_context.translation_source_language,
            "target_language": language_context.origin_language,
            "source_language_code": _normalize_language_label(
                language_context.translation_source_language
            ),
            "target_language_code": _normalize_language_label(language_context.origin_language),
        },
        "language_detection_source": language_context.detection_source,
        "language_detection_sample": language_context.detection_sample,
        "origin_translation_applied": language_context.origin_translation_needed,
        "highlight": options.highlight,
        "transliteration": transliteration_enabled,
        "transliteration_mode": options.transliteration_mode,
        "transliteration_model": (
            options.transliteration_model or options.llm_model
            if options.transliteration_mode == "default"
            else None
        ),
        "transliteration_module": resolve_local_transliteration_module(options.target_language)
        if options.transliteration_mode == "python"
        else None,
        "show_original": options.show_original,
        "batch_size": batch_size,
        "translation_batch_size": options.translation_batch_size,
        "workers": worker_count,
    }
    metadata["start_time_offset_seconds"] = float(start_offset)
    metadata["start_time_offset_label"] = _format_timecode_label(start_offset)
    if end_offset is not None:
        metadata["end_time_offset_seconds"] = float(end_offset)
        metadata["end_time_offset_label"] = _format_timecode_label(end_offset)
    else:
        metadata["end_time_offset_seconds"] = None
        metadata["end_time_offset_label"] = None
    metadata["output_format"] = options.output_format
    if options.output_format == "ass":
        metadata["ass_font_size"] = resolved_ass_font_size
        metadata["ass_emphasis_scale"] = resolved_ass_emphasis
    metadata["color_palette"] = options.color_palette.to_dict()
    metadata["output_extension"] = output_extension

    return SubtitleProcessingResult(
        output_path=output_path,
        cue_count=total_cues,
        translated_count=translated_count,
        metadata=metadata,
        transcript_entries=transcript_entries if collect_transcript_entries else [],
    )


def _process_cue(
    cue: SubtitleCue,
    options: SubtitleJobOptions,
    transliterator: Optional[TransliterationService],
    stop_event,
    renderer: CueTextRenderer,
    language_context: SubtitleLanguageContext,
    tracker: Optional[ProgressTracker],
    translation_override: Optional[str] = None,
    transliteration_override: Optional[str] = None,
) -> "_RenderedCueBatch":
    if _is_cancelled(stop_event):
        raise SubtitleJobCancelled("Subtitle job interrupted by cancellation request")

    source_text = cue.as_text()
    original_text = _normalize_text(source_text)
    if translation_override is not None:
        translation = _normalize_text(translation_override)
    else:
        translation = _normalize_text(
            _translate_text(
                source_text,
                source_language=language_context.translation_source_language,
                target_language=options.target_language,
                llm_model=options.llm_model,
                translation_provider=options.translation_provider,
                progress_tracker=tracker,
            )
        )
    translation_failed = is_failure_annotation(translation)
    if not translation_failed:
        script_mismatch, script_label = _unexpected_script_used(
            translation, options.target_language
        )
        if script_mismatch:
            translation_failed = True
            translation = format_retry_failure(
                "translation",
                1,
                reason=f"Unexpected script; expected {script_label or 'target script'}",
            )
            logger.warning(
                "Cue %s rejected due to unexpected script (target=%s, found=%s)",
                cue.index,
                options.target_language,
                script_label or "unknown",
            )

    if language_context.origin_translation_needed:
        try:
            translated_origin = _normalize_text(
                _translate_text(
                    source_text,
                    source_language=language_context.translation_source_language,
                    target_language=language_context.origin_language,
                    llm_model=options.llm_model,
                    translation_provider=options.translation_provider,
                    progress_tracker=tracker,
                )
            )
        except Exception:  # pragma: no cover - best effort fallback
            logger.warning(
                "Unable to translate cue %s into origin language %s",
                cue.index,
                language_context.origin_language,
                exc_info=True,
            )
        else:
            if translated_origin and not is_failure_annotation(translated_origin):
                original_text = translated_origin

    transliteration_text = ""
    allow_transliteration = (
        options.enable_transliteration
        and _target_uses_non_latin_script(options.target_language)
    )
    if (
        allow_transliteration
        and transliterator is not None
        and translation
        and not translation_failed
    ):
        try:
            candidate_override = ""
            if transliteration_override:
                candidate_override = _normalize_text(transliteration_override)
                if not text_norm.is_latin_heavy(candidate_override):
                    candidate_override = ""
            if candidate_override:
                transliteration_text = candidate_override
            elif options.transliteration_mode != "python":
                transliteration_model = options.transliteration_model or options.llm_model
                if transliteration_model:
                    with create_client(model=transliteration_model) as client:
                        transliteration_result = transliterator.transliterate(
                            translation,
                            options.target_language,
                            client=client,
                            mode=options.transliteration_mode,
                            progress_tracker=tracker,
                        )
                else:
                    transliteration_result = transliterator.transliterate(
                        translation,
                        options.target_language,
                        mode=options.transliteration_mode,
                        progress_tracker=tracker,
                    )
            else:
                transliteration_result = transliterator.transliterate(
                    translation,
                    options.target_language,
                    mode=options.transliteration_mode,
                    progress_tracker=tracker,
                )
        except Exception as exc:  # pragma: no cover - defensive fallbacks
            logger.debug(
                "Transliteration failed for cue %s: %s", cue.index, exc, exc_info=True
            )
        else:
            if not transliteration_text:
                transliteration_text = _normalize_text(transliteration_result.text)

    cues = _build_output_cues(
        cue,
        translation,
        transliteration_text,
        highlight=options.highlight,
        show_original=options.show_original,
        renderer=renderer,
        original_text=original_text,
    )
    if not options.highlight:
        cues = _merge_redundant_rendered_cues(cues)

    return _RenderedCueBatch(
        cues=cues,
        html_entry=SubtitleHtmlEntry(
            start=cue.start,
            end=cue.end,
            original_text=original_text,
            transliteration_text=transliteration_text,
            translation_text=translation,
        ),
    )


@dataclass(slots=True)
class _RenderedCueBatch:
    """Rendered cue payload plus the HTML-friendly snapshot."""

    cues: List[SubtitleCue]
    html_entry: Optional[SubtitleHtmlEntry]


# Backwards-compatible exports for callers expecting to import private helpers here.
__all__ = [
    "CueTextRenderer",
    "SubtitleJobCancelled",
    "SubtitleProcessingError",
    "_HtmlTranscriptWriter",
    "_SubtitleFileWriter",
    "_build_output_cues",
    "_deduplicate_cues_by_text",
    "_merge_overlapping_lines",
    "_merge_redundant_rendered_cues",
    "_merge_rendered_timeline",
    "_normalize_language_label",
    "_resolve_language_context",
    "_resolve_worker_count",
    "_should_merge_youtube_cues",
    "_target_uses_non_latin_script",
    "_translate_text",
    "load_subtitle_cues",
    "merge_youtube_subtitle_cues",
    "process_subtitle_file",
    "write_srt",
]
