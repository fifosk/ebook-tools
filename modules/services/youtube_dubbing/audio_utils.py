from __future__ import annotations

import math
import os
import re
import subprocess
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable, List, Optional, Sequence, Tuple

from pydub import AudioSegment

from modules.audio.tts import generate_audio
from modules.retry_annotations import is_failure_annotation
from modules.subtitles.translation import _translate_text as _translate_subtitle_text
from modules.transliteration import TransliterationService

from .common import (
    _DEFAULT_ORIGINAL_MIX_PERCENT,
    _GAP_MIX_MAX_PERCENT,
    _GAP_MIX_SCALAR,
    _TEMP_DIR,
    _AssDialogue,
    _DubJobCancelled,
    logger,
)
from .dialogues import _clip_dialogues_to_window, _parse_dialogues, _validate_time_window
from .language import _find_language_token, _language_uses_non_latin
from .workers import _resolve_worker_count

_HTML_TAG_PATTERN = re.compile(r"<[^>]+>")


def _measure_active_window(
    audio: AudioSegment,
    *,
    silence_floor: float = -50.0,
    head_padding_ms: int = 60,
) -> Tuple[float, float]:
    """Return (offset_seconds, duration_seconds) of voiced audio inside ``audio``."""

    if len(audio) == 0:
        return 0.0, 0.0
    threshold = max(silence_floor, (audio.dBFS if math.isfinite(audio.dBFS) else silence_floor) - 18.0)
    step_ms = 20
    first = None
    last = None
    for position in range(0, len(audio), step_ms):
        frame = audio[position : position + step_ms]
        if frame.dBFS > threshold:
            first = position if first is None else first
            last = position + len(frame)
    if first is None or last is None:
        return 0.0, len(audio) / 1000.0
    start_ms = max(0, first - head_padding_ms)
    end_ms = min(len(audio), last + head_padding_ms)
    return start_ms / 1000.0, max(0.0, (end_ms - start_ms) / 1000.0)


def _sanitize_for_tts(text: str) -> str:
    """Clean noisy markers while preserving diacritics for languages like Czech/Hungarian."""

    try:
        cleaned = text.replace(">>", " ").replace("<<", " ").replace("»", " ").replace("«", " ")
        cleaned = _HTML_TAG_PATTERN.sub(" ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned or text
    except Exception:
        return text


def _build_atempo_filters(target_ratio: float) -> List[float]:
    """Break a tempo ratio into ffmpeg-safe atempo factors (each 0.5–2.0)."""

    factors: List[float] = []
    ratio = max(0.01, target_ratio)
    while ratio > 2.0:
        factors.append(2.0)
        ratio /= 2.0
    while ratio < 0.5:
        factors.append(0.5)
        ratio *= 2.0
    factors.append(ratio)
    return factors


def _time_stretch_to_duration(segment: AudioSegment, target_ms: int) -> AudioSegment:
    """Time-stretch ``segment`` toward ``target_ms`` with pitch-preserving atempo."""

    if target_ms <= 0:
        return segment
    duration_ms = len(segment)
    if duration_ms <= 0:
        return segment
    ratio = duration_ms / max(target_ms, 1)
    if abs(ratio - 1.0) < 0.01:
        return segment

    ffmpeg_bin = os.environ.get("FFMPEG_PATH") or os.environ.get("FFMPEG_BIN") or "ffmpeg"
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False, prefix="stretch-in-", dir=_TEMP_DIR) as in_handle:
        temp_in = Path(in_handle.name)
        segment.export(temp_in, format="wav", parameters=["-acodec", "pcm_s16le"])
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False, prefix="stretch-out-", dir=_TEMP_DIR) as out_handle:
        temp_out = Path(out_handle.name)

    filters = _build_atempo_filters(ratio)
    filter_arg = ",".join(f"atempo={factor:.5f}" for factor in filters)
    command = [
        ffmpeg_bin,
        "-y",
        "-i",
        str(temp_in),
        "-vn",
        "-ac",
        str(segment.channels or 2),
        "-ar",
        str(segment.frame_rate),
        "-filter:a",
        filter_arg,
        "-f",
        "wav",
        str(temp_out),
    ]

    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if result.returncode != 0:
            logger.warning(
                "ffmpeg atempo stretch failed (exit %s); falling back to original segment",
                result.returncode,
                extra={"event": "youtube.dub.atempo.failed"},
            )
            return segment
        stretched = AudioSegment.from_file(temp_out, format="wav")
    finally:
        temp_in.unlink(missing_ok=True)
        temp_out.unlink(missing_ok=True)

    # Final pad/trim within a tiny tolerance to hit the target window.
    final = stretched
    if len(final) > target_ms:
        final = final[:target_ms]
    elif len(final) < target_ms:
        final += AudioSegment.silent(duration=target_ms - len(final), frame_rate=final.frame_rate)
    return _coerce_channels(final.set_frame_rate(segment.frame_rate), segment.channels)


def _fit_segment_to_window(
    segment: AudioSegment,
    target_seconds: float,
    *,
    max_speedup: float = 1.0,
) -> AudioSegment:
    """
    Keep synthesized audio near its intended window without padding/trim.

    We avoid stretching or padding; any gating happens via scheduling downstream.
    """

    target_ms = max(50, int(target_seconds * 1000))
    if len(segment) <= 0:
        return AudioSegment.silent(duration=target_ms, frame_rate=segment.frame_rate)
    return segment


def _clamp_original_mix(percent: Optional[float]) -> float:
    if percent is None:
        return _DEFAULT_ORIGINAL_MIX_PERCENT
    try:
        value = float(percent)
    except Exception:
        return _DEFAULT_ORIGINAL_MIX_PERCENT
    if math.isnan(value) or math.isinf(value):
        return _DEFAULT_ORIGINAL_MIX_PERCENT
    return max(0.0, min(100.0, value))


def _compute_reference_rms(audios: Sequence[AudioSegment]) -> float:
    """Return a median-ish RMS reference for dubbing segments."""

    values = [audio.rms for audio in audios if audio and audio.rms]
    if not values:
        return 1.0
    values.sort()
    mid = len(values) // 2
    if len(values) % 2 == 1:
        return float(values[mid])
    return float((values[mid - 1] + values[mid]) / 2.0)


def _compute_underlay_gain_db(reference_rms: float, original_rms: float, mix_percent: float) -> float:
    """
    Compute the gain (in dB) that makes the original audio sit at ``mix_percent`` of the dubbed loudness.

    Falls back to a gentle attenuation when RMS values are missing.
    """

    if mix_percent <= 0:
        return -120.0
    target_linear = max(0.0, min(1.0, mix_percent / 100.0))
    dubbed_rms = max(reference_rms or 0.0, 1.0)
    original_rms = max(original_rms or 0.0, 1.0)
    relative_linear = target_linear * (dubbed_rms / original_rms)
    if relative_linear <= 0:
        return -120.0
    return 20 * math.log10(relative_linear)


def _resolve_gap_mix_percent(original_mix_percent: float) -> float:
    """Return a mix percentage for silent gaps that matches the underlay blend."""

    original = _clamp_original_mix(original_mix_percent)
    # Keep gaps quieter than the underlay so the bed never jumps in front of dialogue.
    scaled = original * _GAP_MIX_SCALAR
    return min(original, _GAP_MIX_MAX_PERCENT, scaled)


def _coerce_channels(segment: AudioSegment, target_channels: int) -> AudioSegment:
    """Safely convert to ``target_channels`` by downmixing to mono first when needed."""

    if target_channels <= 0 or segment.channels == target_channels:
        return segment
    if target_channels == 1:
        return segment.set_channels(1)
    if segment.channels == 1:
        return segment.set_channels(target_channels)
    mono = segment.set_channels(1)
    if target_channels == 1:
        return mono
    return mono.set_channels(target_channels)


def _extract_audio_from_video(path: Path, *, sample_rate: int = 44100, channels: int = 2) -> AudioSegment:
    """Extract the audio stream from a video file via FFmpeg.

    Instead of loading the entire video container into memory with
    ``AudioSegment.from_file()``, this shells out to FFmpeg to extract and
    transcode only the audio stream to a temporary WAV file, then loads that.
    For large video files (multi-GB MKVs) this reduces peak memory from
    several GB down to a few hundred MB.
    """
    ffmpeg_bin = os.environ.get("FFMPEG_PATH") or os.environ.get("FFMPEG_BIN") or "ffmpeg"
    with tempfile.NamedTemporaryFile(
        suffix=".wav",
        delete=False,
        prefix="dub-extract-audio-",
        dir=_TEMP_DIR,
    ) as handle:
        tmp_wav = Path(handle.name)
    try:
        subprocess.run(
            [
                ffmpeg_bin,
                "-y",
                "-i", str(path),
                "-vn",                          # drop video
                "-ac", str(channels),
                "-ar", str(sample_rate),
                "-c:a", "pcm_s16le",
                "-f", "wav",
                str(tmp_wav),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        audio = AudioSegment.from_file(tmp_wav, format="wav")
        return audio
    finally:
        try:
            tmp_wav.unlink(missing_ok=True)
        except Exception:
            pass


def _has_audio_stream(path: Path) -> bool:
    """Return True if ffprobe detects an audio stream."""

    ffmpeg_bin = os.environ.get("FFMPEG_PATH") or os.environ.get("FFMPEG_BIN") or "ffmpeg"
    ffprobe_bin = ffmpeg_bin.replace("ffmpeg", "ffprobe")
    try:
        result = subprocess.run(
            [
                ffprobe_bin,
                "-v",
                "error",
                "-select_streams",
                "a:0",
                "-show_entries",
                "stream=codec_type",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if result.returncode != 0:
            return False
        return b"audio" in result.stdout
    except Exception:
        return False


def _apply_audio_gain_to_clip(path: Path, gain_db: float) -> Path:
    """Apply an audio gain to a video clip while copying video streams."""

    if abs(gain_db) < 0.01:
        return path
    ffmpeg_bin = os.environ.get("FFMPEG_PATH") or os.environ.get("FFMPEG_BIN") or "ffmpeg"
    with tempfile.NamedTemporaryFile(
        suffix=path.suffix or ".mp4",
        delete=False,
        prefix="dub-gain-",
        dir=_TEMP_DIR,
    ) as handle:
        target = Path(handle.name)
    command = [
        ffmpeg_bin,
        "-y",
        "-i",
        str(path),
        "-c:v",
        "copy",
        "-af",
        f"volume={gain_db:.4f}dB",
        "-c:a",
        "aac",
        str(target),
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if result.returncode != 0:
        # Some containers (e.g., certain MKVs) may not expose the audio stream cleanly to ffprobe/ffmpeg.
        # When we're trying to attenuate heavily, fall back to stripping the audio entirely to avoid loud gaps.
        if gain_db <= -20.0:
            mute_cmd = [
                ffmpeg_bin,
                "-y",
                "-i",
                str(path),
                "-c:v",
                "copy",
                "-an",
                str(target),
            ]
            mute_result = subprocess.run(mute_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
            if mute_result.returncode == 0:
                try:
                    path.unlink(missing_ok=True)
                except Exception:
                    pass
                return target
        target.unlink(missing_ok=True)
        return path
    try:
        path.unlink(missing_ok=True)
    except Exception:
        pass
    return target


def _apply_gap_audio_mix(path: Path, *, mix_percent: float, reference_rms: float) -> Path:
    """Downmix gap clip audio to a quieter underlay level to avoid jumps."""

    gap_mix_percent = _resolve_gap_mix_percent(mix_percent)
    if gap_mix_percent >= 99.0:
        return path
    if gap_mix_percent <= 0.0:
        return _apply_audio_gain_to_clip(path, -120.0)
    clip_rms = 1.0
    try:
        clip_audio = _coerce_channels(AudioSegment.from_file(path).set_frame_rate(44100), 2)
        if clip_audio.rms:
            clip_rms = clip_audio.rms
    except Exception:
        clip_rms = 1.0
    gain_db = _compute_underlay_gain_db(reference_rms, clip_rms, gap_mix_percent)
    # Avoid boosting quiet ambience and enforce a consistent attenuation in gaps.
    if gain_db > 0:
        gain_db = 0.0
    gain_db = min(gain_db, -20.0)
    return _apply_audio_gain_to_clip(path, gain_db)


def _mix_with_original_audio(
    dubbed_track: AudioSegment,
    source_video: Path,
    *,
    original_mix_percent: float,
    expected_duration_seconds: Optional[float] = None,
    original_audio: Optional[AudioSegment] = None,
    speech_windows: Optional[Sequence[Tuple[float, float]]] = None,
    reference_rms: Optional[float] = None,
    gap_mix_percent: Optional[float] = None,
) -> AudioSegment:
    """Blend the original audio underneath the dubbed track at the given percentage."""

    mix_percent = _clamp_original_mix(original_mix_percent)
    if mix_percent <= 0:
        return dubbed_track

    if original_audio is None:
        try:
            original = _extract_audio_from_video(
                source_video,
                sample_rate=dubbed_track.frame_rate,
                channels=dubbed_track.channels,
            )
        except Exception:
            logger.warning(
                "Unable to read original audio for underlay; continuing without mix",
                extra={"event": "youtube.dub.mix.failed", "video": source_video.as_posix()},
                exc_info=True,
            )
            return dubbed_track
    else:
        original = original_audio

    target_rate = dubbed_track.frame_rate
    target_channels = dubbed_track.channels
    original = _coerce_channels(original.set_frame_rate(target_rate), target_channels)

    max_duration_ms = None
    if expected_duration_seconds is not None:
        max_duration_ms = int(expected_duration_seconds * 1000)
    target_ms = len(dubbed_track) if max_duration_ms is None else max(max_duration_ms, len(dubbed_track))
    # Stretch the original slice to match the dubbed duration so both tracks stay aligned.
    if len(original) != target_ms and target_ms > 0:
        original = _time_stretch_to_duration(original, target_ms)
    if len(original) < target_ms:
        original += AudioSegment.silent(duration=target_ms - len(original), frame_rate=target_rate)
    elif len(original) > target_ms:
        original = original[:target_ms]

    reference_rms_resolved = reference_rms if reference_rms is not None else (dubbed_track.rms or 1)
    original_rms = original.rms or 1
    # Normalize the underlay relative to the dubbed track so the percentage reflects loudness, not just peak.
    dubbed_rms = reference_rms_resolved or 1
    target_linear = mix_percent / 100.0
    relative_linear = target_linear * (dubbed_rms / original_rms)
    if relative_linear <= 0:
        return dubbed_track
    original_gain_db = 20 * math.log10(relative_linear)
    if speech_windows and gap_mix_percent is not None:
        gap_target_linear = max(0.0, min(1.0, gap_mix_percent / 100.0))
        gap_relative_linear = gap_target_linear * (dubbed_rms / original_rms)
        gap_gain_db = -120.0
        if gap_relative_linear > 0:
            gap_gain_db = 20 * math.log10(gap_relative_linear)
        if gap_gain_db > 0:
            gap_gain_db = 0.0
        gap_gain_db = min(gap_gain_db, -20.0)
        base_underlay = original.apply_gain(gap_gain_db)
        bump_track = AudioSegment.silent(duration=target_ms, frame_rate=target_rate).set_channels(target_channels)
        bump_gain_db = original_gain_db
        if bump_gain_db > 0:
            bump_gain_db = 0.0
        for start_sec, end_sec in speech_windows:
            start_ms = max(0, int(start_sec * 1000))
            end_ms = min(target_ms, int(end_sec * 1000))
            if end_ms <= start_ms:
                continue
            segment = original[start_ms:end_ms].apply_gain(bump_gain_db)
            bump_track = bump_track.overlay(segment, position=start_ms)
        underlay = base_underlay.overlay(bump_track)
        base = dubbed_track - 1.0  # Leave a little headroom before mixing in the underlay.
        return base.overlay(underlay)

    base = dubbed_track - 1.0  # Leave a little headroom before mixing in the underlay.
    return base.overlay(original.apply_gain(original_gain_db))


def _synthesise_track_from_ass(
    subtitle_path: Path,
    *,
    language: str,
    voice: str,
    tempo: float,
    macos_reading_speed: int,
    llm_model: Optional[str],
    translation_provider: Optional[str] = None,
    tracker=None,
    stop_event: Optional[threading.Event] = None,
    max_workers: Optional[int] = None,
    start_time_offset: Optional[float] = None,
    end_time_offset: Optional[float] = None,
    progress_milestones: Optional[Sequence[float]] = None,
    progressive_flush: Optional[Callable[[AudioSegment, float], None]] = None,
) -> Tuple[AudioSegment, List[_AssDialogue]]:
    target_rate = 44100
    target_channels = 2
    start_offset, end_offset = _validate_time_window(start_time_offset, end_time_offset)
    all_dialogues = _parse_dialogues(subtitle_path)
    source_language = _find_language_token(subtitle_path) or language
    clipped_dialogues = _clip_dialogues_to_window(
        all_dialogues,
        start_offset=start_offset,
        end_offset=end_offset,
    )
    translated_dialogues: List[_AssDialogue] = []
    needs_translation = source_language and language and source_language.lower() != language.lower()
    total_dialogues = len(clipped_dialogues)
    if tracker is not None:
        tracker.set_total(total_dialogues)
        tracker.publish_progress(
            {"stage": "translation", "total": total_dialogues, "source": source_language, "target": language}
        )
    for idx, entry in enumerate(clipped_dialogues):
        translated_text = entry.translation
        if needs_translation:
            try:
                translated_text = _translate_subtitle_text(
                    entry.translation,
                    source_language=source_language or language,
                    target_language=language,
                    llm_model=llm_model,
                    translation_provider=translation_provider,
                    progress_tracker=tracker,
                )
                if is_failure_annotation(translated_text):
                    translated_text = entry.translation
            except Exception:
                translated_text = entry.translation
        if tracker is not None and needs_translation:
            tracker.record_step_completion(
                stage="translation",
                index=idx + 1,
                total=total_dialogues,
                metadata={"start": entry.start, "end": entry.end},
            )
        translated_dialogues.append(
            _AssDialogue(
                start=entry.start,
                end=entry.end,
                translation=translated_text,
                original=entry.original,
            )
        )
    translated_dialogues = [entry for entry in translated_dialogues if entry.translation]
    if not translated_dialogues:
        raise ValueError("No dialogue entries found in ASS subtitle.")

    total_segments = len(translated_dialogues)
    workers = _resolve_worker_count(total_segments, requested=max_workers)
    if progressive_flush is not None:
        # Keep ordering predictable for progressive flushes.
        workers = 1
    segments: List[Optional[Tuple[_AssDialogue, AudioSegment]]] = [None] * total_segments

    def _guard() -> None:
        if stop_event is not None and stop_event.is_set():
            raise _DubJobCancelled()

    def _synthesise(index: int, entry: _AssDialogue) -> Tuple[int, _AssDialogue, AudioSegment]:
        _guard()
        sanitized = _sanitize_for_tts(entry.translation)
        segment = generate_audio(
            sanitized,
            language,
            voice,
            macos_reading_speed,
            progress_tracker=tracker,
        )
        fitted = _fit_segment_to_window(segment, entry.duration)
        normalized = _coerce_channels(fitted.set_frame_rate(target_rate), target_channels)
        return index, entry, normalized

    if tracker is not None:
        tracker.publish_progress(
            {
                "stage": "synthesis",
                "segments": total_segments,
                "workers": workers,
            }
        )

    try:
        if workers <= 1:
            for idx, dialogue in enumerate(translated_dialogues):
                _guard()
                _, entry, fitted = _synthesise(idx, dialogue)
                segments[idx] = (entry, fitted)
                if tracker is not None:
                    tracker.record_step_completion(
                        stage="synthesis",
                        index=idx + 1,
                        total=total_segments,
                        metadata={"start": entry.start, "end": entry.end},
                    )
        else:
            futures = []
            with ThreadPoolExecutor(max_workers=workers) as executor:
                for idx, dialogue in enumerate(translated_dialogues):
                    futures.append(executor.submit(_synthesise, idx, dialogue))
                completed = 0
                for future in as_completed(futures):
                    _guard()
                    idx, entry, fitted = future.result()
                    segments[idx] = (entry, fitted)
                    completed += 1
                    if tracker is not None:
                        tracker.record_step_completion(
                            stage="synthesis",
                            index=completed,
                            total=total_segments,
                            metadata={"start": entry.start, "end": entry.end},
                        )
    except _DubJobCancelled:
        for future in locals().get("futures", []):
            future.cancel()
        raise

    resolved_segments: List[Tuple[_AssDialogue, AudioSegment]] = [
        segment for segment in segments if segment is not None
    ]
    if not resolved_segments:
        raise ValueError("No translatable dialogue lines were found in the subtitle.")

    clip_end = end_offset - start_offset if end_offset is not None else None
    max_end = clip_end if clip_end is not None else max(entry.end for entry, _ in resolved_segments)
    base_rate = resolved_segments[0][1].frame_rate
    # Keep a tiny buffer to avoid truncating the last syllable, but stay close to the subtitle window.
    track = AudioSegment.silent(duration=int(max_end * 1000) + 100, frame_rate=base_rate)
    if tracker is not None:
        tracker.publish_progress({"stage": "mixdown", "duration_seconds": max_end})
    milestone_index = 0
    milestones = list(progress_milestones or [])
    for entry, audio in resolved_segments:
        _guard()
        start_ms = int(entry.start * 1000)
        track = track.overlay(audio, position=start_ms)
        while milestone_index < len(milestones) and entry.end >= milestones[milestone_index]:
            if progressive_flush is not None:
                try:
                    progressive_flush(track, milestones[milestone_index])
                except Exception:
                    logger.warning("Progressive mux failed for milestone %.2f", milestones[milestone_index], exc_info=True)
            milestone_index += 1
    return track, [entry for entry, _ in resolved_segments]


__all__ = [
    "_apply_audio_gain_to_clip",
    "_apply_gap_audio_mix",
    "_build_atempo_filters",
    "_clamp_original_mix",
    "_coerce_channels",
    "_compute_reference_rms",
    "_compute_underlay_gain_db",
    "_fit_segment_to_window",
    "_has_audio_stream",
    "_measure_active_window",
    "_mix_with_original_audio",
    "_resolve_gap_mix_percent",
    "_sanitize_for_tts",
    "_synthesise_track_from_ass",
    "_time_stretch_to_duration",
    "logger",
]
