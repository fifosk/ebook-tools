from __future__ import annotations

import math
import os
import shutil
import subprocess
import tempfile
import threading
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable, List, Optional, Sequence, Tuple, TextIO

from pydub import AudioSegment

from modules.audio.tts import generate_audio
from modules.progress_tracker import ProgressTracker
from modules.retry_annotations import is_failure_annotation
from modules.subtitles.models import SubtitleCue, SubtitleColorPalette
from modules.subtitles.render import CueTextRenderer, _SubtitleFileWriter, _build_output_cues
from modules.subtitles.translation import _translate_text as _translate_subtitle_text
from modules.transliteration import TransliterationService, get_transliterator

from .audio_utils import (
    _apply_gap_audio_mix,
    _clamp_original_mix,
    _coerce_channels,
    _compute_reference_rms,
    _has_audio_stream,
    _measure_active_window,
    _mix_with_original_audio,
    _sanitize_for_tts,
    _resolve_gap_mix_percent,
)
from .common import _DEFAULT_FLUSH_SENTENCES, _TARGET_DUB_HEIGHT, _TEMP_DIR, _AssDialogue, _DubJobCancelled, logger
from .dialogues import (
    _clip_dialogues_to_window,
    _compute_pace_factor,
    _merge_overlapping_dialogues,
    _parse_dialogues,
    _validate_time_window,
)
from .language import (
    _find_language_token,
    _language_uses_non_latin,
    _normalize_rtl_word_order,
    _resolve_language_code,
    _transliterate_text,
)
from .translation import translate_dialogues
from .video_utils import (
    _concat_video_segments,
    _downscale_video,
    _mux_audio_track,
    _pad_clip_to_duration,
    _probe_duration_seconds,
    _resolve_batch_output_path,
    _resolve_output_path,
    _resolve_temp_batch_path,
    _resolve_temp_output_path,
    _resolve_temp_target,
    _trim_video_segment,
)
from .subtitle_render import render_ass_for_block
from .webvtt import _write_webvtt
from .workers import _resolve_encoding_worker_count, _resolve_llm_worker_count, _resolve_worker_count


def generate_dubbed_video(
    video_path: Path,
    subtitle_path: Path,
    *,
    target_language: Optional[str] = None,
    voice: str = "gTTS",
    tempo: float = 1.0,
    macos_reading_speed: int = 100,
    llm_model: Optional[str] = None,
    translation_provider: Optional[str] = None,
    transliteration_mode: Optional[str] = None,
    output_dir: Optional[Path] = None,
    tracker: Optional[ProgressTracker] = None,
    stop_event: Optional[threading.Event] = None,
    max_workers: Optional[int] = None,
    start_time_offset: Optional[float] = None,
    end_time_offset: Optional[float] = None,
    original_mix_percent: Optional[float] = None,
    flush_sentences: Optional[int] = None,
    split_batches: bool = False,
    include_transliteration: Optional[bool] = None,
    on_batch_written: Optional[Callable[[Path], None]] = None,
    target_height: int = _TARGET_DUB_HEIGHT,
    preserve_aspect_ratio: bool = True,
) -> Tuple[Path, List[Path]]:
    """Render an audio dub from ``subtitle_path`` and mux it into ``video_path``."""

    if not video_path.exists():
        raise FileNotFoundError(f"Video file '{video_path}' does not exist")
    if not subtitle_path.exists():
        raise FileNotFoundError(f"Subtitle file '{subtitle_path}' does not exist")
    if subtitle_path.suffix.lower() not in {".ass", ".srt", ".vtt", ".sub"}:
        raise ValueError("Subtitle must be an ASS, SRT, SUB, or VTT file for timing extraction")

    start_offset, end_offset = _validate_time_window(start_time_offset, end_time_offset)
    mix_percent = _clamp_original_mix(original_mix_percent)
    flush_block = flush_sentences if flush_sentences and flush_sentences > 0 else _DEFAULT_FLUSH_SENTENCES
    target_height_resolved = int(target_height) if target_height is not None else _TARGET_DUB_HEIGHT
    if target_height_resolved < 0:
        target_height_resolved = 0
    preserve_aspect_ratio = bool(preserve_aspect_ratio)
    clipped_dialogues = _clip_dialogues_to_window(
        _parse_dialogues(subtitle_path),
        start_offset=start_offset,
        end_offset=end_offset,
    )
    if not clipped_dialogues:
        raise ValueError("No dialogue entries found in subtitle within the selected window.")
    write_batches = bool(split_batches)

    language_code = _resolve_language_code(target_language or _find_language_token(subtitle_path) or "en")
    logger.info(
        "Generating dubbed track for %s using %s (tempo=%s, speed=%s, mix=%s%%, flush_sentences=%s, llm_model=%s)",
        video_path.name,
        language_code,
        tempo,
        macos_reading_speed,
        mix_percent,
        flush_block,
        llm_model or "",
        extra={
            "event": "youtube.dub.start",
            "attributes": {
                "video": video_path.as_posix(),
                "subtitle": subtitle_path.as_posix(),
                "language": language_code,
                "voice": voice,
                "tempo": tempo,
                "speed": macos_reading_speed,
                "start_offset": start_offset,
                "end_offset": end_offset,
                "original_mix_percent": mix_percent,
                "flush_sentences": flush_block,
                "llm_model": llm_model,
                "target_height": target_height_resolved,
                "preserve_aspect_ratio": preserve_aspect_ratio,
            },
        },
    )
    trimmed_video_path: Optional[Path] = None
    source_video: Path = video_path
    written_paths: List[Path] = []
    written_set = set()
    written_batches: List[Tuple[float, Path]] = []
    encoding_futures: List[Tuple[float, Future[Path]]] = []
    encoding_executor: Optional[ThreadPoolExecutor] = None
    encoding_workers = 1
    encoding_lock = threading.Lock()
    speech_windows: List[Tuple[float, float]] = []
    last_reference_rms: Optional[float] = None
    output_path = _resolve_output_path(
        video_path,
        language_code,
        output_dir,
        start_offset=start_offset,
        end_offset=end_offset,
    )
    global_ass_handle: Optional[TextIO] = None
    try:
        if start_offset > 0 or end_offset is not None:
            trimmed_video_path = _trim_video_segment(
                video_path,
                start_offset=start_offset,
                end_offset=end_offset,
            )
            source_video = trimmed_video_path
        flushed_until = 0.0
        dubbed_track = AudioSegment.silent(duration=10, frame_rate=44100).set_channels(2)
        source_language = _find_language_token(subtitle_path) or language_code

        try:
            base_original_audio = _coerce_channels(AudioSegment.from_file(source_video).set_frame_rate(44100), 2)
        except Exception:
            base_original_audio = None
            logger.warning("Unable to preload original audio; will retry per flush", exc_info=True)

        requested_transliteration = (
            _language_uses_non_latin(language_code)
            if include_transliteration is None
            else bool(include_transliteration)
        )
        include_transliteration_resolved = bool(
            requested_transliteration and _language_uses_non_latin(language_code)
        )
        if requested_transliteration and not include_transliteration_resolved:
            logger.info(
                "Transliteration disabled for Latin-script language %s",
                language_code,
                extra={"event": "youtube.dub.transliteration.disabled", "language": language_code},
            )
        # Maintain the original name for any nested closures expecting it.
        include_transliteration = include_transliteration_resolved
        transliterator: Optional[TransliterationService] = None
        if include_transliteration_resolved:
            try:
                transliterator = get_transliterator()
            except Exception:
                transliterator = None
                include_transliteration_resolved = False
        palette = SubtitleColorPalette.default()
        uses_non_latin = _language_uses_non_latin(language_code)
        emphasis_scale = 1.3 if uses_non_latin else 1.0
        ass_renderer = CueTextRenderer(
            "ass",
            palette,
            emphasis_scale=emphasis_scale,
        )
        global_ass_writer: Optional[_SubtitleFileWriter] = None
        global_ass_handle = None
        subtitle_index = 1
        all_subtitle_dialogues: List[_AssDialogue] = []
        if not write_batches:
            ass_path = output_path.with_suffix(".ass")
            ass_path.parent.mkdir(parents=True, exist_ok=True)
            global_ass_handle = ass_path.open("w", encoding="utf-8")
            global_ass_writer = _SubtitleFileWriter(
                global_ass_handle,
                ass_renderer,
                "ass",
                start_index=subtitle_index,
            )

        total_dialogues = len(clipped_dialogues)
        if tracker is not None:
            tracker.set_total(total_dialogues)
            tracker.publish_progress(
                {
                    "stage": "translation",
                    "total": total_dialogues,
                    "source": source_language,
                    "target": language_code,
                    "flush_sentences": flush_block,
                }
            )
        if write_batches:
            expected_batches = max(1, math.ceil(total_dialogues / flush_block))
            encoding_workers = _resolve_encoding_worker_count(expected_batches, requested=max_workers)
            if encoding_workers > 1:
                encoding_executor = ThreadPoolExecutor(
                    max_workers=encoding_workers,
                    thread_name_prefix="dub-encode",
                )

        def _synthesise_batch(
            dialogues: List[_AssDialogue],
            *,
            batch_pace: float,
            next_starts: Optional[List[Optional[float]]] = None,
        ) -> List[Tuple[_AssDialogue, AudioSegment]]:
            workers = _resolve_worker_count(len(dialogues), requested=max_workers)
            segments: List[Optional[Tuple[_AssDialogue, AudioSegment]]] = [None] * len(dialogues)

            def _guard() -> None:
                if stop_event is not None and stop_event.is_set():
                    raise _DubJobCancelled()

            def _apply_reading_speed_factor(base_speed: int, factor: float) -> int:
                """Return a macOS reading speed tuned by factor, clamped to a sane range."""

                if factor <= 0:
                    return base_speed
                tuned = int(base_speed * factor)
                return max(60, min(tuned, 260))

            def _worker(index: int, entry: _AssDialogue, batch_pace: float) -> Tuple[int, _AssDialogue, AudioSegment]:
                _guard()
                reading_speed = _apply_reading_speed_factor(macos_reading_speed, batch_pace)
                sanitized = _sanitize_for_tts(entry.translation)
                segment = generate_audio(
                    sanitized,
                    language_code,
                    voice,
                    reading_speed,
                    progress_tracker=tracker,
                )
                normalized = _coerce_channels(segment.set_frame_rate(44100), 2)
                return index, entry, normalized

            if tracker is not None:
                tracker.publish_progress(
                    {"stage": "synthesis", "segments": len(dialogues), "workers": workers}
                )

            if workers <= 1:
                for idx, entry in enumerate(dialogues):
                    _guard()
                    _, resolved_entry, audio = _worker(idx, entry, batch_pace)
                    segments[idx] = (resolved_entry, audio)
            else:
                futures = []
                with ThreadPoolExecutor(max_workers=workers) as executor:
                    for idx, entry in enumerate(dialogues):
                        futures.append(executor.submit(_worker, idx, entry, batch_pace))
                    for future in as_completed(futures):
                        _guard()
                        idx, resolved_entry, audio = future.result()
                        segments[idx] = (resolved_entry, audio)

            resolved = [segment for segment in segments if segment is not None]
            if not resolved:
                raise ValueError("No synthesized segments produced for this batch.")
            return resolved  # type: ignore[return-value]

        def _encode_batch(
            sentence_clip_paths: List[Path],
            sentence_audio_paths: List[Path],
            *,
            block_source_start: float,
            block_start_seconds: float,
            block_end_seconds: float,
            ass_block_dialogues: List[_AssDialogue],
            scheduled_entries: List[_AssDialogue],
            final_batch_path: Path,
            temp_batch_path: Path,
            temp_ass_path: Path,
            temp_vtt_path: Path,
            final_ass_path: Path,
            final_vtt_path: Path,
            batch_start_sentence: int,
            batch_end_sentence: int,
            processed_sentences_snapshot: int,
        ) -> Path:
            batch_path = final_batch_path
            try:
                _concat_video_segments(sentence_clip_paths, temp_batch_path)
                batch_path = _downscale_video(
                    temp_batch_path,
                    target_height=target_height_resolved,
                    preserve_aspect_ratio=preserve_aspect_ratio,
                    output_path=final_batch_path,
                )
                try:
                    merged_dialogues = _merge_overlapping_dialogues(scheduled_entries)
                    _write_webvtt(
                        merged_dialogues,
                        temp_vtt_path,
                        target_language=language_code,
                        include_transliteration=include_transliteration_resolved,
                        transliterator=transliterator if include_transliteration_resolved else None,
                        transliteration_mode=transliteration_mode,
                        llm_model=llm_model,
                    )
                except Exception:
                    logger.debug("Unable to write batch-aligned VTT for %s", batch_path, exc_info=True)
                try:
                    temp_ass_path.parent.mkdir(parents=True, exist_ok=True)
                    with temp_ass_path.open("w", encoding="utf-8") as handle:
                        writer = _SubtitleFileWriter(
                            handle,
                            ass_renderer,
                            "ass",
                            start_index=1,
                        )
                        render_ass_for_block(
                            ass_block_dialogues,
                            writer,
                            start_index=1,
                            offset_seconds=block_start_seconds,
                            include_transliteration=include_transliteration_resolved,
                            transliterator=transliterator,
                            transliteration_mode=transliteration_mode,
                            llm_model=llm_model,
                            language_code=language_code,
                            ass_renderer=ass_renderer,
                        )
                    final_ass_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(temp_ass_path), final_ass_path)
                except Exception:
                    logger.debug("Unable to write batch ASS for %s", batch_path, exc_info=True)
                    try:
                        temp_ass_path.unlink(missing_ok=True)
                    except Exception:
                        pass
                try:
                    final_vtt_path.parent.mkdir(parents=True, exist_ok=True)
                    if temp_vtt_path.exists():
                        shutil.move(str(temp_vtt_path), final_vtt_path)
                except Exception:
                    logger.debug("Unable to move batch VTT for %s", batch_path, exc_info=True)
                    try:
                        temp_vtt_path.unlink(missing_ok=True)
                    except Exception:
                        pass
                try:
                    rendered_duration = _probe_duration_seconds(batch_path)
                    expected_duration = block_end_seconds - block_start_seconds
                    if abs(rendered_duration - expected_duration) > 0.15:
                        logger.warning(
                            "Batch duration drift detected (expected=%.3fs, actual=%.3fs)",
                            expected_duration,
                            rendered_duration,
                            extra={
                                "event": "youtube.dub.batch.duration_drift",
                                "batch": batch_path.as_posix(),
                                "expected": expected_duration,
                                "actual": rendered_duration,
                            },
                        )
                except Exception:
                    logger.debug("Unable to probe batch duration for %s", batch_path, exc_info=True)
                should_notify = False
                with encoding_lock:
                    if batch_path not in written_set:
                        written_set.add(batch_path)
                        written_paths.append(batch_path)
                        written_batches.append((block_source_start, batch_path))
                        should_notify = True
                if tracker is not None:
                    try:
                        tracker.publish_progress(
                            {
                                "stage": "mux",
                                "seconds_written": block_end_seconds,
                                "output_path": batch_path.as_posix(),
                                "processed_sentences": processed_sentences_snapshot,
                                "block_size": flush_block,
                                "batch_start_sentence": batch_start_sentence,
                                "batch_end_sentence": batch_end_sentence,
                            }
                        )
                    except Exception:
                        logger.debug("Unable to publish mux progress for %s", batch_path, exc_info=True)
                if should_notify and on_batch_written is not None:
                    try:
                        on_batch_written(batch_path)
                    except Exception:
                        logger.warning("Unable to process written batch %s", batch_path, exc_info=True)
                return batch_path
            finally:
                for clip in sentence_clip_paths:
                    clip.unlink(missing_ok=True)
                for audio_path in sentence_audio_paths:
                    audio_path.unlink(missing_ok=True)
                if temp_batch_path.exists() and temp_batch_path != batch_path:
                    temp_batch_path.unlink(missing_ok=True)
                if temp_ass_path.exists():
                    temp_ass_path.unlink(missing_ok=True)
                if temp_vtt_path.exists():
                    temp_vtt_path.unlink(missing_ok=True)

        def _wait_for_encoding_futures() -> None:
            if not encoding_futures:
                if written_batches:
                    ordered = sorted(written_batches, key=lambda item: item[0])
                    written_paths[:] = [path for _, path in ordered]
                return
            for _start, future in encoding_futures:
                future.result()
            encoding_futures.clear()
            if written_batches:
                ordered = sorted(written_batches, key=lambda item: item[0])
                written_paths[:] = [path for _, path in ordered]

        processed_sentences = 0
        global_pace = None
        if flush_block >= total_dialogues:
            global_pace = _compute_pace_factor(clipped_dialogues)
        for block_index in range(0, total_dialogues, flush_block):
            block = clipped_dialogues[block_index : block_index + flush_block]
            translated_block = translate_dialogues(
                block,
                source_language=source_language,
                target_language=language_code,
                translation_provider=translation_provider,
                include_transliteration=include_transliteration_resolved,
                transliterator=transliterator,
                llm_model=llm_model,
                transliteration_mode=transliteration_mode,
                tracker=tracker,
                offset=block_index,
                total_dialogues=total_dialogues,
            )
            block_pace = global_pace or _compute_pace_factor(translated_block)
            next_starts: List[Optional[float]] = []
            for idx, entry in enumerate(translated_block):
                if block_index + idx + 1 < total_dialogues:
                    next_starts.append(clipped_dialogues[block_index + idx + 1].start)
                else:
                    next_starts.append(None)
            synthesized = _synthesise_batch(translated_block, batch_pace=block_pace, next_starts=next_starts)
            reference_rms = _compute_reference_rms([audio for _entry, audio in synthesized])
            if reference_rms:
                last_reference_rms = reference_rms
            batch_start_sentence = block_index + 1
            batch_end_sentence = block_index + len(synthesized)
            block_start_seconds = 0.0 if write_batches else flushed_until
            block_source_start = min(entry.start for entry, _ in synthesized)
            block_source_end = max(entry.end for entry, _ in synthesized)
            # Build a scheduled timeline that preserves gaps between merged windows and stretches
            # each sentence to the dubbed duration.
            scheduled: List[Tuple[_AssDialogue, AudioSegment, float, float]] = []
            ass_block_dialogues: List[_AssDialogue] = []
            cursor = block_start_seconds
            last_source_end = block_source_start
            for idx, (entry, audio) in enumerate(synthesized):
                if len(audio) < 20:
                    # Guard against empty TTS output to keep timeline and mux stable.
                    audio = AudioSegment.silent(duration=200, frame_rate=44100).set_channels(2)
                speech_offset, speech_duration = _measure_active_window(audio)
                orig_start = translated_block[idx].start
                orig_end = translated_block[idx].end
                transliteration_text = translated_block[idx].transliteration
                render_translation = _normalize_rtl_word_order(
                    entry.translation,
                    language_code,
                    force=True,
                )
                next_gap_source = None
                if idx + 1 < len(translated_block):
                    next_gap_source = max(0.0, translated_block[idx + 1].start - orig_end)
                # Insert untouched gap video/audio for regions without subtitles.
                gap = max(0.0, orig_start - last_source_end)
                if gap > 0:
                    cursor += gap
                    last_source_end = orig_start
                duration_sec = len(audio) / 1000.0
                # Keep subtitles slightly longer than raw audio to avoid highlighting cutting off early,
                # but cap the pad to avoid overlaps in tight sequences (bounded by the upcoming source gap).
                base_pad = min(0.2, duration_sec * 0.15)
                if next_gap_source is not None:
                    base_pad = min(base_pad, max(0.0, next_gap_source - 0.05))
                subtitle_duration = duration_sec + base_pad
                speech_start = cursor + max(0.0, speech_offset or 0.0)
                speech_end = cursor + max(0.0, (speech_offset or 0.0) + (speech_duration or duration_sec))
                if speech_end < speech_start:
                    speech_end = speech_start
                speech_windows.append((speech_start, speech_end))
                scheduled_entry = _AssDialogue(
                    start=cursor,
                    end=cursor + subtitle_duration,
                    translation=render_translation,
                    original=entry.original,
                    transliteration=transliteration_text,
                    rtl_normalized=True,
                    speech_offset=speech_offset,
                    speech_duration=speech_duration,
                )
                scheduled.append((scheduled_entry, audio, orig_start, orig_end))
                ass_block_dialogues.append(scheduled_entry)
                cursor = scheduled_entry.end
                last_source_end = orig_end
            # Preserve trailing gap to the end of the merged window.
            if last_source_end < block_source_end:
                cursor += (block_source_end - last_source_end)
            block_end_seconds = cursor
            block_duration = max(0.0, block_end_seconds - block_start_seconds)
            scheduled_entries = [entry for entry, _audio, _start, _end in scheduled]

            all_subtitle_dialogues.extend(ass_block_dialogues if write_batches else scheduled_entries)

            # Defer batch subtitle writes until the batch media is finalized on RAM disk.
            if not write_batches and global_ass_writer is not None:
                # Keep ASS cues on the absolute dubbed timeline so highlights follow stretched audio.
                subtitle_index = render_ass_for_block(
                    ass_block_dialogues if write_batches else scheduled_entries,
                    global_ass_writer,
                    start_index=subtitle_index,
                    offset_seconds=0.0,
                    include_transliteration=include_transliteration_resolved,
                    transliterator=transliterator,
                    transliteration_mode=transliteration_mode,
                    llm_model=llm_model,
                    language_code=language_code,
                    ass_renderer=ass_renderer,
                )
            sentence_clip_paths: List[Path] = []
            sentence_audio_paths: List[Path] = []
            gap_start = block_source_start
            timeline_cursor = block_start_seconds
            for idx, (entry, audio, orig_start, orig_end) in enumerate(scheduled):
                # Insert gap clip (original A/V only) for regions without dialogue, sized to the scheduled gap.
                gap_duration = max(0.0, entry.start - timeline_cursor)
                if write_batches and gap_duration > 0.001:
                    try:
                        gap_clip = _trim_video_segment(
                            source_video,
                            start_offset=gap_start,
                            end_offset=orig_start,
                        )
                        gap_clip = _pad_clip_to_duration(gap_clip, gap_duration)
                        gap_clip = _apply_gap_audio_mix(
                            gap_clip,
                            mix_percent=mix_percent,
                            reference_rms=reference_rms,
                        )
                        sentence_clip_paths.append(gap_clip)
                        timeline_cursor += gap_duration
                    except Exception:
                        logger.warning(
                            "Failed to extract gap clip (start=%.3f end=%.3f); continuing without gap",
                            gap_start,
                            orig_start,
                            extra={"event": "youtube.dub.gap.clip.failed"},
                            exc_info=True,
                        )
                audio_duration = len(audio) / 1000.0
                audio_end_seconds = entry.start + audio_duration
                source_window_duration = max(0.0, orig_end - orig_start)
                if not write_batches:
                    end_ms = int(audio_end_seconds * 1000) + 50
                    if len(dubbed_track) < end_ms:
                        dubbed_track += AudioSegment.silent(duration=end_ms - len(dubbed_track), frame_rate=44100)
                    dubbed_track = dubbed_track.overlay(audio, position=int(entry.start * 1000))
                else:
                    # Per-sentence video slice cut and stretch to the dubbed duration.
                    original_slice = None
                    if base_original_audio is not None:
                        original_slice = base_original_audio[
                            int(orig_start * 1000) : int(math.ceil(orig_end * 1000))
                        ]
                    mixed_sentence = _mix_with_original_audio(
                        audio,
                        source_video,
                        original_mix_percent=mix_percent,
                        expected_duration_seconds=audio_duration,
                        original_audio=original_slice,
                    )
                    with tempfile.NamedTemporaryFile(
                        suffix=".wav",
                        delete=False,
                        prefix=f"dubbed-sentence-{batch_start_sentence + idx}-",
                        dir=_TEMP_DIR,
                    ) as sentence_audio_handle:
                        sentence_audio_path = Path(sentence_audio_handle.name)
                    mixed_sentence.export(
                        sentence_audio_path,
                        format="wav",
                        parameters=["-acodec", "pcm_s16le"],
                    )
                    sentence_audio_paths.append(sentence_audio_path)
                    local_start = orig_start
                    # Drive video length from dubbed audio; stretch/pad as needed.
                    window_duration = source_window_duration
                    sentence_video = source_video
                    trimmed = False
                    try:
                        sentence_video = _trim_video_segment(
                            source_video,
                            start_offset=orig_start,
                            end_offset=orig_end,
                        )
                        trimmed = True
                        # Trimmed clip is reset to start at 0 via -reset_timestamps.
                        local_start = 0.0
                    except Exception:
                        sentence_video = source_video
                    video_source_duration = None
                    if trimmed:
                        try:
                            video_source_duration = _probe_duration_seconds(sentence_video)
                        except Exception:
                            video_source_duration = None
                    if video_source_duration and video_source_duration > 0:
                        window_duration = video_source_duration
                if window_duration <= 0 and audio_duration > 0:
                    window_duration = audio_duration
                window_end = None
                if window_duration > 0:
                    window_end = local_start + window_duration
                    sentence_output = _resolve_temp_batch_path(
                        output_path,
                        orig_start,
                        suffix=".tmp.mp4",
                    )
                    _mux_audio_track(
                        sentence_video,
                        sentence_audio_paths[-1],
                        sentence_output,
                        language_code,
                        start_time=local_start,
                        end_time=window_end,
                        target_duration_seconds=audio_duration,
                        include_source_audio=False,
                        source_duration_seconds=window_duration if window_duration > 0 else None,
                    )
                    if not _has_audio_stream(sentence_output):
                        logger.warning(
                            "Sentence clip missing audio; re-muxing to force dubbed track",
                            extra={
                                "event": "youtube.dub.sentence.audio_missing",
                                "clip": sentence_output.as_posix(),
                                "audio": sentence_audio_paths[-1].as_posix(),
                            },
                        )
                        ffmpeg_bin = os.environ.get("FFMPEG_PATH") or os.environ.get("FFMPEG_BIN") or "ffmpeg"
                        recover_cmd = [
                            ffmpeg_bin,
                            "-y",
                            "-i",
                            str(sentence_video),
                            "-i",
                            str(sentence_audio_paths[-1]),
                            "-map",
                            "0:v:0",
                            "-map",
                            "1:a:0",
                            "-c:v",
                            "libx264",
                            "-profile:v",
                            "main",
                            "-level:v",
                            "4.1",
                            "-pix_fmt",
                            "yuv420p",
                            "-c:a",
                            "aac",
                            "-ac",
                            "2",
                            "-ar",
                            "44100",
                            "-movflags",
                            "+faststart",
                            str(sentence_output),
                        ]
                        subprocess.run(recover_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
                        if not _has_audio_stream(sentence_output):
                            # Last resort: attach dubbed audio with a silent video of the right duration.
                            subprocess.run(
                                [
                                    ffmpeg_bin,
                                    "-y",
                                    "-f",
                                    "lavfi",
                                    "-i",
                                    f"color=c=black:s=16x16:d={audio_duration:.6f}",
                                    "-i",
                                    str(sentence_audio_paths[-1]),
                                    "-map",
                                    "0:v:0",
                                    "-map",
                                    "1:a:0",
                                    "-c:v",
                                    "libx264",
                                    "-profile:v",
                                    "main",
                                    "-level:v",
                                    "4.1",
                                    "-pix_fmt",
                                    "yuv420p",
                                    "-preset",
                                    "ultrafast",
                                    "-c:a",
                                    "aac",
                                    "-ac",
                                    "2",
                                    "-ar",
                                    "44100",
                                    "-movflags",
                                    "+faststart",
                                    str(sentence_output),
                                ],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                check=False,
                            )
                    sentence_output = _pad_clip_to_duration(sentence_output, audio_duration)
                    final_duration = _probe_duration_seconds(sentence_output)
                    if abs(final_duration - audio_duration) > 0.05:
                        logger.warning(
                            "Sentence clip duration drift (expected=%.3fs, actual=%.3fs); padding to fix",
                            audio_duration,
                            final_duration,
                            extra={
                                "event": "youtube.dub.sentence.duration_drift",
                                "clip": sentence_output.as_posix(),
                                "expected": audio_duration,
                                "actual": final_duration,
                            },
                        )
                        sentence_output = _pad_clip_to_duration(sentence_output, audio_duration)
                    sentence_clip_paths.append(sentence_output)
                    if trimmed and sentence_video != source_video:
                        sentence_video.unlink(missing_ok=True)
                    timeline_cursor = entry.start + audio_duration
                gap_start = orig_end
            # Add trailing gap within the batch window so video length matches scheduled timeline.
            trailing_gap = max(0.0, block_end_seconds - timeline_cursor)
            if write_batches and trailing_gap > 0.001 and block_source_end > gap_start:
                try:
                    gap_clip = _trim_video_segment(
                        source_video,
                        start_offset=gap_start,
                        end_offset=block_source_end,
                    )
                    gap_clip = _pad_clip_to_duration(gap_clip, trailing_gap)
                    gap_clip = _apply_gap_audio_mix(
                        gap_clip,
                        mix_percent=mix_percent,
                        reference_rms=reference_rms,
                    )
                    sentence_clip_paths.append(gap_clip)
                except Exception:
                    logger.warning(
                        "Failed to extract trailing gap clip (start=%.3f end=%.3f)",
                        gap_start,
                        block_source_end,
                        extra={"event": "youtube.dub.gap.trailing.failed"},
                        exc_info=True,
                    )
            processed_sentences += len(synthesized)
            if write_batches and sentence_clip_paths:
                final_batch_path = _resolve_batch_output_path(output_path, block_source_start)
                final_batch_path.parent.mkdir(parents=True, exist_ok=True)
                temp_batch_path = _resolve_temp_batch_path(output_path, block_source_start)
                temp_batch_path.parent.mkdir(parents=True, exist_ok=True)
                final_ass_path = final_batch_path.with_suffix(".ass")
                final_vtt_path = final_ass_path.with_suffix(".vtt")
                temp_ass_path = _resolve_temp_target(final_ass_path)
                temp_vtt_path = _resolve_temp_target(final_vtt_path)
                processed_snapshot = processed_sentences
                if encoding_executor is not None:
                    encoding_futures.append(
                        (
                            block_source_start,
                            encoding_executor.submit(
                                _encode_batch,
                                sentence_clip_paths,
                                sentence_audio_paths,
                                block_source_start=block_source_start,
                                block_start_seconds=block_start_seconds,
                                block_end_seconds=block_end_seconds,
                                ass_block_dialogues=list(ass_block_dialogues),
                                scheduled_entries=list(scheduled_entries),
                                final_batch_path=final_batch_path,
                                temp_batch_path=temp_batch_path,
                                temp_ass_path=temp_ass_path,
                                temp_vtt_path=temp_vtt_path,
                                final_ass_path=final_ass_path,
                                final_vtt_path=final_vtt_path,
                                batch_start_sentence=batch_start_sentence,
                                batch_end_sentence=batch_end_sentence,
                                processed_sentences_snapshot=processed_snapshot,
                            ),
                        )
                    )
                else:
                    _encode_batch(
                        sentence_clip_paths,
                        sentence_audio_paths,
                        block_source_start=block_source_start,
                        block_start_seconds=block_start_seconds,
                        block_end_seconds=block_end_seconds,
                        ass_block_dialogues=list(ass_block_dialogues),
                        scheduled_entries=list(scheduled_entries),
                        final_batch_path=final_batch_path,
                        temp_batch_path=temp_batch_path,
                        temp_ass_path=temp_ass_path,
                        temp_vtt_path=temp_vtt_path,
                        final_ass_path=final_ass_path,
                        final_vtt_path=final_vtt_path,
                        batch_start_sentence=batch_start_sentence,
                        batch_end_sentence=batch_end_sentence,
                        processed_sentences_snapshot=processed_snapshot,
                    )
                flushed_until = block_end_seconds
            if write_batches:
                continue
            else:
                # For single-output mode, accumulate onto the main dubbed_track and mux once after loop.
                flushed_until = block_end_seconds

        if not write_batches and all_subtitle_dialogues:
            try:
                merged_dialogues = _merge_overlapping_dialogues(all_subtitle_dialogues)
                vtt_path = output_path.with_suffix(".vtt")
                _write_webvtt(
                    merged_dialogues,
                    vtt_path,
                    target_language=language_code,
                    include_transliteration=include_transliteration_resolved,
                    transliterator=transliterator if include_transliteration_resolved else None,
                    transliteration_mode=transliteration_mode,
                    llm_model=llm_model,
                )
            except Exception:
                logger.debug("Unable to create WebVTT subtitles for %s", output_path, exc_info=True)

        if write_batches:
            _wait_for_encoding_futures()

        total_seconds = flushed_until
        if write_batches and written_paths:
            final_output = written_paths[0]
        else:
            final_output = output_path

        if not write_batches:
            # Mux the full accumulated track once to avoid batch sync gaps.
            final_audio_slice = dubbed_track[: int(math.ceil(total_seconds * 1000))] if total_seconds > 0 else dubbed_track
            # Reapply the original underlay for the full track to honour mix_percent in single-output mode.
            original_audio_slice = None
            if base_original_audio is not None:
                original_audio_slice = base_original_audio[: len(final_audio_slice)]
            final_audio_slice = _mix_with_original_audio(
                final_audio_slice,
                source_video,
                original_mix_percent=mix_percent,
                expected_duration_seconds=total_seconds if total_seconds > 0 else None,
                original_audio=original_audio_slice,
                speech_windows=speech_windows,
                reference_rms=last_reference_rms,
                gap_mix_percent=_resolve_gap_mix_percent(mix_percent),
            )
            with tempfile.NamedTemporaryFile(
                suffix=".wav",
                delete=False,
                prefix="dubbed-track-final-",
                dir=_TEMP_DIR,
            ) as chunk_handle:
                chunk_path = Path(chunk_handle.name)
            final_output_path = output_path
            temp_output_path = _resolve_temp_output_path(output_path)
            temp_output_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                final_audio_slice.export(
                    chunk_path,
                    format="wav",
                    parameters=["-acodec", "pcm_s16le"],
                )
                _mux_audio_track(
                    source_video,
                    chunk_path,
                    temp_output_path,
                    language_code,
                    start_time=start_offset if start_offset > 0 else None,
                    end_time=end_offset,
                )
            finally:
                chunk_path.unlink(missing_ok=True)
            output_path = _downscale_video(
                temp_output_path,
                target_height=target_height_resolved,
                preserve_aspect_ratio=preserve_aspect_ratio,
                output_path=final_output_path,
            )
            if temp_output_path.exists() and temp_output_path != output_path:
                temp_output_path.unlink(missing_ok=True)
            written_paths.append(output_path)
            if on_batch_written is not None:
                try:
                    on_batch_written(output_path)
                except Exception:
                    logger.warning("Unable to process final dubbed output %s", output_path, exc_info=True)

        logger.info(
            "Dubbed video created at %s",
            final_output,
            extra={
                "event": "youtube.dub.complete",
                "attributes": {"output": final_output.as_posix(), "written_paths": [p.as_posix() for p in written_paths]},
            },
        )
        if not write_batches and not written_paths:
            written_paths.append(output_path)
        return final_output, written_paths
    finally:
        try:
            if write_batches:
                _wait_for_encoding_futures()
        except Exception:
            logger.debug("Unable to flush encoding futures during cleanup", exc_info=True)
        if encoding_executor is not None:
            try:
                encoding_executor.shutdown(wait=True)
            except Exception:
                logger.debug("Unable to shut down encoding executor", exc_info=True)
        try:
            if global_ass_handle is not None:
                global_ass_handle.close()
        except Exception:
            logger.debug("Unable to close ASS writer handle", exc_info=True)
        if trimmed_video_path is not None:
            try:
                trimmed_video_path.unlink(missing_ok=True)  # type: ignore[arg-type]
            except Exception:
                logger.debug("Unable to clean up temporary trimmed video %s", trimmed_video_path, exc_info=True)


__all__ = ["generate_dubbed_video"]
