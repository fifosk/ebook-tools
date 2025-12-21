"""Worker implementations for media rendering pipelines."""

from __future__ import annotations

import os
import tempfile
import threading
import time
from dataclasses import dataclass
from queue import Empty, Full, Queue
from contextlib import suppress
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Protocol, Sequence, TYPE_CHECKING

from pydub import AudioSegment
from pydub.silence import detect_silence

from modules import logging_manager as log_mgr
from modules import config_manager as cfg
from modules import text_normalization as text_norm
from modules.audio.backends import get_default_backend_name
from modules.render.backends.base import SynthesisResult
from modules.audio.highlight import _get_audio_metadata
from modules.core.rendering.timeline import smooth_token_boundaries, compute_char_weighted_timings
from modules.core.rendering.constants import LANGUAGE_CODES as GLOBAL_LANGUAGE_CODES
from modules.text import split_highlight_tokens
from .context import RenderBatchContext

if TYPE_CHECKING:  # pragma: no cover - imports for static analysis only
    from modules.progress_tracker import ProgressTracker
    from modules.translation_engine import TranslationTask
    from modules.audio_video_generator import MediaPipelineResult

logger = log_mgr.logger
_REQUIRED_HIGHLIGHT_POLICY = (os.environ.get("EBOOK_HIGHLIGHT_POLICY") or "").strip().lower() or None
_MULTILINGUAL_ALIGNMENT_MODEL = "large-v2"


class AudioGenerator(Protocol):
    """Callable protocol used to synthesize audio for a translation task."""

    def __call__(
        self,
        sentence_number: int,
        input_sentence: str,
        fluent_translation: str,
        input_language: str,
        target_language: str,
        audio_mode: str,
        total_sentences: int,
        language_codes: Mapping[str, str],
        selected_voice: str,
        voice_overrides: Mapping[str, str] | None,
        tempo: float,
        macos_reading_speed: int,
    ) -> AudioSegment | SynthesisResult:
        """Render audio for a single translated sentence."""


class MediaResultFactory(Protocol):
    """Protocol describing the factory used to build media worker outputs."""

    def __call__(
        self,
        *,
        index: int,
        sentence_number: int,
        sentence: str,
        target_language: str,
        translation: str,
        transliteration: str,
        audio_segment: Optional[AudioSegment],
        audio_tracks: Optional[Mapping[str, AudioSegment]] = None,
        voice_metadata: Optional[Mapping[str, Mapping[str, str]]] = None,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> "MediaPipelineResult":
        """Return a media result instance."""


@dataclass(slots=True)
class AudioWorker:
    """Wrap the audio worker coroutine so it can be reused and extended."""

    name: str
    audio_task_queue: "Queue[Optional[TranslationTask]]"
    audio_result_queue: "Queue[Optional[MediaPipelineResult]]"
    batch_context: RenderBatchContext
    media_result_factory: MediaResultFactory
    audio_stop_event: Optional[threading.Event] = None
    progress_tracker: Optional["ProgressTracker"] = None
    audio_generator: Optional[AudioGenerator] = None

    def run(self) -> None:
        """Execute the wrapped audio worker coroutine."""

        audio_worker_body(
            self.name,
            self.audio_task_queue,
            self.audio_result_queue,
            batch_context=self.batch_context,
            media_result_factory=self.media_result_factory,
            audio_stop_event=self.audio_stop_event,
            progress_tracker=self.progress_tracker,
            audio_generator=self.audio_generator,
        )


@dataclass(slots=True)
class _SimpleWorker:
    """Utility wrapper that exposes a ``run`` method for simple callables."""

    name: str
    worker_fn: Callable[..., None]

    def run(self, *args, **kwargs) -> None:
        self.worker_fn(*args, **kwargs)


class VideoWorker(_SimpleWorker):
    """Wrapper for video worker coroutines."""


class TextWorker(_SimpleWorker):
    """Wrapper for text worker coroutines."""


def _coerce_float(value: object) -> Optional[float]:
    """Best-effort conversion of arbitrary values to floats."""

    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _time_from_entry(entry: Mapping[str, object], keys: Sequence[str]) -> Optional[float]:
    """Extract a timing value in seconds from a metadata entry."""

    for raw_key in keys:
        key = str(raw_key)
        if key not in entry:
            continue
        value = _coerce_float(entry.get(key))
        if value is None:
            continue
        if key.lower().endswith("_ms"):
            return value / 1000.0
        return value
    return None


def _normalize_char_timing(entry: Mapping[str, object]) -> tuple[Optional[float], Optional[float]]:
    """Return normalized (start, end) timings in seconds for a single character."""

    start = _time_from_entry(
        entry,
        (
            "start_ms",
            "offset_ms",
            "begin_ms",
            "start",
            "offset",
            "begin",
            "time",
        ),
    )
    end = _time_from_entry(
        entry,
        ("end_ms", "stop_ms", "finish_ms", "end", "stop", "finish"),
    )
    duration = _time_from_entry(
        entry,
        (
            "duration_ms",
            "length_ms",
            "time_span_ms",
            "duration",
            "length",
            "time_span",
        ),
    )

    if start is None and end is not None and duration is not None:
        start = end - duration
    if start is not None and duration is not None and end is None:
        end = start + duration
    if start is not None:
        start = max(start, 0.0)
    if end is not None:
        end = max(end, 0.0)
    if start is not None and end is not None and end < start:
        end = start
    return start, end


def _measure_pause_edges(
    segment: Optional[AudioSegment],
    *,
    threshold_db: float = -40.0,
    min_len_ms: int = 80,
) -> tuple[int, int]:
    """Estimate leading/trailing silence durations (ms) for ``segment``."""

    if segment is None:
        return 0, 0
    duration_ms = len(segment)
    if duration_ms <= 0:
        return 0, 0
    min_len = max(int(min_len_ms), 1)
    tolerance = 4  # ms tolerance for boundary rounding
    try:
        silences = detect_silence(
            segment,
            min_silence_len=min_len,
            silence_thresh=threshold_db,
        )
    except Exception:
        return 0, 0
    if not silences:
        return 0, 0
    pause_before = 0
    pause_after = 0
    first_start, first_end = silences[0]
    if first_start <= tolerance:
        pause_before = max(first_end - first_start, 0)
    last_start, last_end = silences[-1]
    if abs(last_end - duration_ms) <= tolerance:
        pause_after = max(last_end - last_start, 0)
    return int(pause_before), int(pause_after)


def _segment_char_timings(audio_segment: Optional[AudioSegment]) -> Optional[Sequence[Mapping[str, object]]]:
    """Retrieve per-character timing metadata from an audio segment if available."""

    if audio_segment is None:
        return None
    for attr in ("char_timings", "character_timing", "highlight_character_timing", "alignment"):
        candidate = getattr(audio_segment, attr, None)
        if isinstance(candidate, Sequence):
            return candidate  # type: ignore[return-value]
    provider = getattr(audio_segment, "get_alignment_metadata", None)
    if callable(provider):
        try:
            result = provider()
        except TypeError:
            result = provider(audio_segment)  # type: ignore[misc]
        if isinstance(result, Sequence):
            return result  # type: ignore[return-value]
    return None


def _tokens_from_char_timings(
    text: str,
    char_timings: Sequence[Mapping[str, object]],
) -> List[Dict[str, float | str]]:
    """Collapse character-level timings into whitespace-delimited tokens."""

    if not text or not char_timings:
        return []

    normalized: List[tuple[Optional[float], Optional[float]]] = []
    for entry in char_timings:
        if isinstance(entry, Mapping):
            normalized.append(_normalize_char_timing(entry))
        else:
            normalized.append((None, None))

    tokens: List[Dict[str, float | str]] = []
    index = 0
    length = len(text)
    while index < length:
        while index < length and text[index].isspace():
            index += 1
        if index >= length:
            break
        token_chars: List[str] = []
        token_start: Optional[float] = None
        token_end: Optional[float] = None
        while index < length and not text[index].isspace():
            token_chars.append(text[index])
            if index < len(normalized):
                start, end = normalized[index]
                if start is not None:
                    token_start = start if token_start is None else min(token_start, start)
                if end is not None:
                    token_end = end if token_end is None else max(token_end, end)
            index += 1
        token_text = "".join(token_chars)
        if token_text:
            if token_start is not None:
                token_start = round(max(token_start, 0.0), 6)
            if token_end is not None:
                token_end = round(max(token_end, 0.0), 6)
            tokens.append({"text": token_text, "start": token_start, "end": token_end})
        while index < length and text[index].isspace():
            index += 1

    if not tokens or any(token["start"] is None or token["end"] is None for token in tokens):
        return []

    previous_end = 0.0
    for token in tokens:
        start = float(token["start"])  # type: ignore[arg-type]
        end = float(token["end"])  # type: ignore[arg-type]
        if start < previous_end:
            start = previous_end
            token["start"] = round(start, 6)
        if end < start:
            end = start
            token["end"] = round(end, 6)
        previous_end = end

    return tokens


def _evenly_distributed_tokens(text: str, duration: float) -> List[Dict[str, float | str]]:
    """Distribute total duration evenly across whitespace-delimited words."""

    words = [word for word in text.split() if word]
    if not words:
        return []
    total_duration = max(duration, 0.0)
    count = len(words)
    slice_duration = total_duration / count if count else 0.0
    tokens: List[Dict[str, float | str]] = []
    cursor = 0.0
    for idx, word in enumerate(words):
        start = cursor
        if idx == count - 1:
            end = total_duration
        else:
            end = cursor + slice_duration
        start = round(max(start, 0.0), 6)
        end = round(max(end, 0.0), 6)
        tokens.append({"text": word, "start": start, "end": end})
        cursor = end
    return tokens


def _resolve_sentence_duration_hint(
    audio_segment: Optional[AudioSegment],
    metadata: Mapping[str, object],
) -> Optional[float]:
    """Best-effort duration estimate for a sentence."""

    if audio_segment is not None:
        try:
            duration = float(audio_segment.duration_seconds)
        except Exception:
            duration = None
        if duration is not None and duration > 0:
            return duration
        try:
            length_ms = len(audio_segment)
        except Exception:
            length_ms = None
        if length_ms and length_ms > 0:
            return length_ms / 1000.0

    tokens = metadata.get("word_tokens")
    if isinstance(tokens, Sequence) and tokens:
        last_token = tokens[-1]
        if isinstance(last_token, Mapping):
            maybe_end = _coerce_float(last_token.get("end"))
            if maybe_end and maybe_end > 0:
                return maybe_end

    for key in ("t1", "duration", "time_span"):
        value = metadata.get(key)
        duration_candidate = _coerce_float(value)
        if duration_candidate and duration_candidate > 0:
            return duration_candidate
    return None


def _export_audio_for_alignment(audio_segment: AudioSegment) -> Optional[Path]:
    """Write ``audio_segment`` to a temporary WAV file for alignment backends."""

    try:
        handle = tempfile.NamedTemporaryFile(prefix="alignment_", suffix=".wav", delete=False)
    except OSError:
        return None
    temp_path = Path(handle.name)
    handle.close()
    try:
        audio_segment.export(temp_path, format="wav")
    except Exception as exc:  # pragma: no cover - export failures are rare
        logger.warning("Failed to export audio for alignment: %s", exc, exc_info=True)
        with suppress(OSError):
            temp_path.unlink()
        return None
    return temp_path


def _align_with_whisperx(
    audio_segment: AudioSegment,
    text: str,
    *,
    model: Optional[str] = None,
) -> tuple[List[Dict[str, float | str]], bool]:
    """Invoke the WhisperX CLI to align ``text`` against ``audio_segment``."""

    audio_path = _export_audio_for_alignment(audio_segment)
    if audio_path is None:
        return [], False
    try:
        try:
            from modules.align.backends import whisperx_adapter
        except Exception as exc:  # pragma: no cover - optional dependency
            logger.warning("WhisperX adapter unavailable: %s", exc)
            return [], False
        try:
            tokens, exhausted = whisperx_adapter.retry_alignment(
                audio_path, text, model=model
            )
            return tokens, exhausted
        except Exception as exc:  # pragma: no cover - adapter best effort
            logger.warning("WhisperX alignment failed: %s", exc, exc_info=True)
            return [], False
    finally:
        with suppress(OSError):
            audio_path.unlink()


def _align_with_backend(
    *,
    audio_segment: AudioSegment,
    text: str,
    backend: str,
    model: Optional[str],
) -> tuple[List[Dict[str, float | str]], bool]:
    """Dispatch to the requested alignment backend.

    Returns a tuple of (tokens, exhausted_retry_flag).
    """

    backend_key = backend.strip().lower()
    if not backend_key:
        return [], False
    if backend_key == "whisperx":
        return _align_with_whisperx(audio_segment, text, model=model)
    logger.warning("Unsupported alignment backend '%s'", backend)
    return [], False


def _lookup_language_code(
    language_label: Optional[str],
    language_codes: Mapping[str, str],
) -> Optional[str]:
    """Return the ISO-like code for ``language_label`` when available."""

    if not language_label or not isinstance(language_label, str):
        return None
    normalized_label = language_label.strip()
    if not normalized_label:
        return None

    for mapping in (language_codes, GLOBAL_LANGUAGE_CODES):
        if not isinstance(mapping, Mapping):
            continue
        direct = mapping.get(normalized_label)
        if isinstance(direct, str) and direct.strip():
            return direct.strip()
        lower_label = normalized_label.lower()
        for key, value in mapping.items():
            if isinstance(key, str) and key.lower() == lower_label and isinstance(value, str):
                return value.strip()

    # If the language label already looks like a code (e.g. "en" or "en-US"), trust it.
    stripped = normalized_label.replace("-", "")
    if stripped.isalpha() and len(stripped) <= 8:
        return normalized_label
    return None


def _resolve_alignment_model_choice(
    settings: Optional[Any],
    *,
    language_label: str,
    iso_code: Optional[str],
) -> tuple[Optional[str], str]:
    """Return the alignment model to use plus the selection source label."""

    default_model: Optional[str] = None
    overrides: Optional[Mapping[str, str]] = None
    if settings is not None:
        overrides_candidate = getattr(settings, "alignment_model_overrides", None)
        if isinstance(overrides_candidate, Mapping):
            overrides = overrides_candidate
        default_model = (
            getattr(settings, "alignment_model", None)
            or getattr(settings, "forced_alignment_model", None)
        )

    keys_to_try = []
    if isinstance(iso_code, str):
        keys_to_try.extend([iso_code, iso_code.lower()])
    if language_label:
        keys_to_try.extend([language_label, language_label.lower()])

    if overrides:
        for key in keys_to_try:
            if not isinstance(key, str):
                continue
            value = overrides.get(key) or overrides.get(key.lower())
            if isinstance(value, str) and value.strip():
                return value.strip(), f"override:{key}"

    if isinstance(default_model, str) and default_model.strip():
        return default_model.strip(), "default"

    normalized_iso = iso_code.lower() if isinstance(iso_code, str) else ""
    if normalized_iso.startswith("en"):
        return "medium.en", "heuristic:en"
    if normalized_iso:
        return _MULTILINGUAL_ALIGNMENT_MODEL, "heuristic:multilingual"
    return None, "unspecified"


def _extract_word_tokens(
    *,
    text: str,
    audio_segment: Optional[AudioSegment],
    metadata: Mapping[str, object],
) -> tuple[List[Dict[str, float | str]], str, str]:
    """
    Return per-word timing tokens plus the alignment policy and source.

    Policy is ``forced`` when explicit character timings are provided,
    ``inferred`` when timings are derived from audio duration, and ``uniform``
    when the engine falls back to evenly-spaced tokens because no audio data
    exists for the sentence.
    """

    if not text:
        return [], "uniform", "missing-text"

    char_timings: Optional[Sequence[Mapping[str, object]]] = None
    char_timing_source = "metadata"
    candidate = metadata.get("char_timings") if isinstance(metadata, Mapping) else None
    if isinstance(candidate, Sequence):
        char_timings = candidate  # type: ignore[assignment]
    if char_timings is None:
        char_timings = _segment_char_timings(audio_segment)
        if char_timings:
            char_timing_source = "backend"

    tokens: List[Dict[str, float | str]] = []
    policy = "uniform"
    source = "unknown"
    if char_timings:
        tokens = _tokens_from_char_timings(text, char_timings)
        policy = "forced"
        source = char_timing_source or "char_timings"

    if not tokens:
        duration = float(audio_segment.duration_seconds) if audio_segment is not None else 0.0
        if duration > 0:
            policy = "inferred"
            source = "audio_duration"
        else:
            policy = "uniform"
            source = "fallback"
        tokens = _evenly_distributed_tokens(text, duration)

    return tokens, policy, source


def audio_worker_body(
    worker_name: str,
    audio_task_queue: "Queue[Optional[TranslationTask]]",
    audio_result_queue: "Queue[Optional[MediaPipelineResult]]",
    *,
    batch_context: RenderBatchContext,
    media_result_factory: MediaResultFactory,
    audio_stop_event: Optional[threading.Event] = None,
    progress_tracker: Optional["ProgressTracker"] = None,
    audio_generator: Optional[AudioGenerator] = None,
) -> None:
    """Consume translation results and emit completed media payloads."""

    manifest_context = batch_context.manifest
    audio_context = batch_context.media_context("audio")

    total_sentences = int(
        audio_context.get("total_sentences")
        or manifest_context.get("total_sentences")
        or 0
    )
    input_language = str(
        audio_context.get("input_language")
        or manifest_context.get("input_language")
        or ""
    )
    audio_mode = str(audio_context.get("audio_mode") or manifest_context.get("audio_mode") or "1")
    raw_language_codes = audio_context.get("language_codes") or manifest_context.get("language_codes") or {}
    if not isinstance(raw_language_codes, Mapping):
        raw_language_codes = {}
    language_codes = dict(raw_language_codes)
    selected_voice = str(
        audio_context.get("selected_voice")
        or manifest_context.get("selected_voice")
        or ""
    )
    raw_voice_overrides = (
        audio_context.get("voice_overrides")
        or manifest_context.get("voice_overrides")
        or {}
    )
    if not isinstance(raw_voice_overrides, Mapping):
        raw_voice_overrides = {}
    voice_overrides = {
        str(key).strip(): str(value).strip()
        for key, value in raw_voice_overrides.items()
        if isinstance(key, str)
        and isinstance(value, str)
        and str(key).strip()
        and str(value).strip()
    }
    tempo = float(audio_context.get("tempo") or manifest_context.get("tempo") or 1.0)
    macos_reading_speed = int(
        audio_context.get("macos_reading_speed")
        or manifest_context.get("macos_reading_speed")
        or 0
    )
    generate_audio = bool(
        audio_context.get("generate_audio", manifest_context.get("generate_audio", True))
    )
    raw_tts_backend = audio_context.get("tts_backend") or manifest_context.get("tts_backend")
    default_tts_backend = get_default_backend_name()
    if isinstance(raw_tts_backend, str):
        stripped_backend = raw_tts_backend.strip()
        if not stripped_backend or stripped_backend.lower() == "auto":
            tts_backend = default_tts_backend
        else:
            tts_backend = stripped_backend
    else:
        tts_backend = default_tts_backend
    raw_tts_executable = (
        audio_context.get("tts_executable_path")
        or audio_context.get("say_path")
        or manifest_context.get("tts_executable_path")
        or manifest_context.get("say_path")
    )
    if isinstance(raw_tts_executable, str):
        stripped_executable = raw_tts_executable.strip()
        tts_executable_path = stripped_executable or None
    else:
        tts_executable_path = None

    while True:
        if audio_stop_event and audio_stop_event.is_set():
            break
        try:
            translation_task = audio_task_queue.get(timeout=0.1)
        except Empty:
            continue
        if translation_task is None:
            audio_task_queue.task_done()
            break

        start_time = time.perf_counter()
        audio_segment: Optional[AudioSegment] = None
        audio_tracks: Optional[Dict[str, AudioSegment]] = None
        original_audio_segment: Optional[AudioSegment] = None
        voice_metadata: Mapping[str, Mapping[str, str]] = {}
        metadata: Dict[str, Any] = {}
        backend_word_tokens: Optional[List[Mapping[str, object]]] = None
        try:
            if generate_audio and audio_generator is not None:
                audio_output = audio_generator(
                    sentence_number=translation_task.sentence_number,
                    input_sentence=translation_task.sentence,
                    fluent_translation=translation_task.translation,
                    input_language=input_language,
                    target_language=translation_task.target_language,
                    audio_mode=audio_mode,
                    total_sentences=total_sentences,
                    language_codes=language_codes,
                    selected_voice=selected_voice,
                    tempo=tempo,
                    macos_reading_speed=macos_reading_speed,
                    voice_overrides=voice_overrides,
                    tts_backend=tts_backend,
                    tts_executable_path=tts_executable_path,
                )
                if isinstance(audio_output, SynthesisResult):
                    raw_tracks = getattr(audio_output, "audio_tracks", None)
                    if isinstance(raw_tracks, Mapping):
                        normalized_tracks: Dict[str, AudioSegment] = {}
                        for raw_key, raw_value in raw_tracks.items():
                            if not isinstance(raw_key, str) or not isinstance(raw_value, AudioSegment):
                                continue
                            key = raw_key.strip().lower()
                            if not key:
                                continue
                            if key in {"trans"}:
                                key = "translation"
                            elif key in {"original", "source"}:
                                key = "orig"
                            normalized_tracks[key] = raw_value
                        if normalized_tracks:
                            audio_tracks = normalized_tracks
                            audio_segment = normalized_tracks.get("translation")
                            original_audio_segment = normalized_tracks.get("orig")
                    if audio_tracks is None:
                        audio_segment = audio_output.audio
                    voice_metadata = audio_output.voice_metadata
                    raw_metadata = getattr(audio_output, "metadata", None)
                    if isinstance(raw_metadata, Mapping):
                        metadata = dict(raw_metadata)
                    tokens_attr = getattr(audio_output, "word_tokens", None)
                    if isinstance(tokens_attr, Sequence) and not isinstance(tokens_attr, (str, bytes)):
                        backend_word_tokens = [
                            token for token in tokens_attr if isinstance(token, Mapping)
                        ]
                else:
                    audio_segment = audio_output
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error(
                "Consumer %s failed for sentence %s: %s",
                worker_name,
                translation_task.sentence_number,
                exc,
            )
            if generate_audio:
                audio_segment = AudioSegment.silent(duration=0)
        finally:
            audio_task_queue.task_done()

        elapsed = time.perf_counter() - start_time
        logger.debug(
            "Consumer %s processed sentence %s in %.3fs",
            worker_name,
            translation_task.sentence_number,
            elapsed,
        )

        if not isinstance(metadata, dict):
            try:
                metadata = dict(metadata)  # type: ignore[arg-type]
            except Exception:
                metadata = {}

        pause_before_ms = 0
        pause_after_ms = 0
        if audio_segment is not None and len(audio_segment) > 0:
            pause_before_ms, pause_after_ms = _measure_pause_edges(audio_segment)
            sentence_audio_meta = _get_audio_metadata(audio_segment)
            if sentence_audio_meta is not None:
                sentence_audio_meta.pause_before_ms = pause_before_ms
                sentence_audio_meta.pause_after_ms = pause_after_ms
        metadata["pause_before_ms"] = pause_before_ms
        metadata["pause_after_ms"] = pause_after_ms
        metadata["pauseBeforeMs"] = pause_before_ms
        metadata["pauseAfterMs"] = pause_after_ms

        translation_text = text_norm.collapse_whitespace(
            translation_task.translation or ""
        )
        translation_text_display = translation_text
        translation_track_available = audio_segment is not None and len(audio_segment) > 0
        if not translation_track_available:
            translation_text = ""
        try:
            settings_obj = cfg.get_settings()
        except Exception:
            settings_obj = None
        target_language_label = translation_task.target_language or ""
        target_language_code = _lookup_language_code(target_language_label, language_codes)
        char_timings_candidate = metadata.get("char_timings")
        has_char_timings = isinstance(char_timings_candidate, Sequence) and not isinstance(
            char_timings_candidate, (str, bytes)
        )
        if not backend_word_tokens:
            meta_tokens_candidate = metadata.get("word_tokens")
            if isinstance(meta_tokens_candidate, Sequence) and not isinstance(
                meta_tokens_candidate, (str, bytes)
            ):
                backend_word_tokens = [
                    token for token in meta_tokens_candidate if isinstance(token, Mapping)
                ]
        alignment_policy = "uniform"
        alignment_source = "unavailable"
        alignment_model_used: Optional[str] = None
        word_tokens: List[Dict[str, float | str]] = []
        translation_words = split_highlight_tokens(translation_text)
        char_weighted_used = False
        char_weighted_punctuation = False
        duration_hint_cache: Optional[float] = None
        char_weighted_failure_policy: Optional[str] = None
        char_weighted_requested = bool(
            settings_obj
            and getattr(settings_obj, "char_weighted_highlighting_default", False)
        )
        punctuation_boost_enabled = bool(
            settings_obj
            and getattr(settings_obj, "char_weighted_punctuation_boost", False)
        )

        def _apply_char_weighted_timings(
            *,
            policy_override: Optional[str] = None,
            use_punctuation: bool = False,
        ) -> bool:
            nonlocal word_tokens, alignment_policy, alignment_source, char_weighted_used
            nonlocal duration_hint_cache, char_weighted_punctuation
            if not translation_text:
                return False
            if duration_hint_cache is None:
                duration_hint_cache = _resolve_sentence_duration_hint(audio_segment, metadata)
            duration_hint = duration_hint_cache
            if duration_hint is None or duration_hint <= 0:
                return False
            fallback_words = translation_words or [translation_text] if translation_text else []
            estimated_tokens = compute_char_weighted_timings(
                fallback_words,
                duration_hint,
                pause_before_ms=pause_before_ms,
                pause_after_ms=pause_after_ms,
            )
            if not estimated_tokens:
                return False
            word_tokens = estimated_tokens
            metadata["word_tokens"] = word_tokens
            char_weighted_used = True
            if use_punctuation:
                char_weighted_punctuation = True
            alignment_policy = policy_override or ("estimated_punct" if use_punctuation else "estimated")
            alignment_source = "char_weighted_duration"
            return True

        if char_weighted_requested:
            _apply_char_weighted_timings(use_punctuation=punctuation_boost_enabled)

        if translation_text and backend_word_tokens and not word_tokens:
            normalized_backend_tokens: List[Dict[str, float | str]] = []
            for entry in backend_word_tokens:
                if not isinstance(entry, Mapping):
                    continue
                start_val = _coerce_float(entry.get("start"))
                end_val = _coerce_float(entry.get("end"))
                if start_val is None or end_val is None:
                    continue
                start_rounded = round(max(start_val, 0.0), 6)
                end_rounded = round(max(end_val, 0.0), 6)
                if end_rounded < start_rounded:
                    end_rounded = start_rounded
                token_text = entry.get("text")
                if not isinstance(token_text, str):
                    token_text = entry.get("word", "")
                    if not isinstance(token_text, str):
                        token_text = ""
                normalized_backend_tokens.append(
                    {
                        "text": token_text,
                        "start": start_rounded,
                        "end": end_rounded,
                    }
                )
            if translation_words and len(normalized_backend_tokens) == len(translation_words):
                for idx, word_text in enumerate(translation_words):
                    normalized_backend_tokens[idx]["text"] = (
                        normalized_backend_tokens[idx].get("text") or word_text
                    )
                word_tokens = normalized_backend_tokens
                alignment_policy = "forced"
                alignment_source = "word_tokens"
                metadata["word_tokens"] = word_tokens
            elif backend_word_tokens and translation_words:
                logger.warning(
                    "Sentence %s backend supplied word token count mismatch "
                    "(tokens=%d words=%d); falling back to inference.",
                    translation_task.sentence_number,
                    len(backend_word_tokens),
                    len(translation_words),
                )
        if word_tokens:
            char_weighted_failure_policy = None
        if (
            not word_tokens
            and translation_text
            and audio_segment is not None
            and len(audio_segment) > 0
            and settings_obj
            and getattr(settings_obj, "forced_alignment_enabled", False)
        ):
            backend_candidate = getattr(settings_obj, "alignment_backend", None) or getattr(
                settings_obj, "forced_alignment_backend", None
            )
            backend_name = backend_candidate.strip() if isinstance(backend_candidate, str) else ""
            if backend_name:
                alignment_model, model_source = _resolve_alignment_model_choice(
                    settings_obj,
                    language_label=target_language_label,
                    iso_code=target_language_code,
                )
                logger.info(
                    "Sentence %s alignment backend=%s model=%s source=%s language=%s (%s)",
                    translation_task.sentence_number,
                    backend_name,
                    alignment_model or "<default>",
                    model_source,
                    target_language_label or "?",
                    target_language_code or "unknown",
                )
                aligned_tokens, retry_exhausted = _align_with_backend(
                    audio_segment=audio_segment,
                    text=translation_text,
                    backend=backend_name,
                    model=alignment_model,
                )
                if aligned_tokens:
                    word_tokens = aligned_tokens
                    alignment_policy = "forced"
                    alignment_source = "aligner"
                    metadata["word_tokens"] = word_tokens
                    alignment_model_used = alignment_model
                    char_weighted_failure_policy = None
                else:
                    if retry_exhausted:
                        char_weighted_failure_policy = "retry_failed_align"
                        logger.warning(
                            "Sentence %s alignment backend '%s' produced no tokens after retries.",
                            translation_task.sentence_number,
                            backend_name,
                        )
                    else:
                        logger.warning(
                            "Sentence %s alignment backend '%s' returned no tokens.",
                            translation_task.sentence_number,
                            backend_name,
                        )
        if not word_tokens and translation_text and (audio_segment is not None or has_char_timings):
            extracted_tokens, policy, source = _extract_word_tokens(
                text=translation_text,
                audio_segment=audio_segment,
                metadata=metadata,
            )
            word_tokens = extracted_tokens
            alignment_policy = policy or "uniform"
            alignment_source = source or "unavailable"
            if word_tokens:
                char_weighted_failure_policy = None
        if translation_text and (char_weighted_requested or not word_tokens):
            if not char_weighted_used:
                policy_override = char_weighted_failure_policy
                use_punct = punctuation_boost_enabled
                applied = _apply_char_weighted_timings(
                    policy_override=policy_override,
                    use_punctuation=use_punct,
                )
                if not applied and policy_override:
                    alignment_policy = policy_override
        if word_tokens:
            smoothed_tokens = word_tokens
            if settings_obj and getattr(settings_obj, "forced_alignment_enabled", False):
                smoothing_value = getattr(settings_obj, "forced_alignment_smoothing", 0.35)
                try:
                    smoothing_factor = float(smoothing_value)
                except (TypeError, ValueError):
                    smoothing_factor = 0.35
                smoothed_tokens = smooth_token_boundaries(word_tokens, smoothing=smoothing_factor)
                metadata["word_tokens"] = smoothed_tokens
                word_tokens = smoothed_tokens

        if translation_text_display:
            metadata.setdefault("text", translation_text_display)
        metadata.setdefault("sentence_number", translation_task.sentence_number)
        metadata.setdefault("id", str(translation_task.sentence_number))
        metadata.setdefault("t0", 0.0)

        total_duration: Optional[float] = None
        if audio_segment is not None:
            try:
                total_duration = float(audio_segment.duration_seconds)
            except Exception:
                total_duration = None
        if total_duration is None:
            tokens = metadata.get("word_tokens")
            if isinstance(tokens, Sequence) and tokens:
                last_token = tokens[-1]
                try:
                    total_duration = float(last_token.get("end", 0.0))
                except (TypeError, ValueError, AttributeError):
                    total_duration = None
        if total_duration is not None:
            metadata.setdefault("t1", round(max(total_duration, 0.0), 6))

        highlight_duration = total_duration if isinstance(total_duration, float) else 0.0
        highlighting_summary = {
            "policy": alignment_policy,
            "tempo": tempo,
            "tokens": len(word_tokens),
            "token_count": len(word_tokens),
            "duration": round(highlight_duration, 6) if highlight_duration else highlight_duration,
            "source": alignment_source,
            "punctuation_weighting": bool(char_weighted_punctuation),
            "pause_before_ms": pause_before_ms,
            "pause_after_ms": pause_after_ms,
        }
        if char_weighted_used:
            highlighting_summary["method"] = "char_weighted"
            highlighting_summary["char_weighted"] = True
            highlighting_summary["char_weighted_refined"] = True
        if alignment_model_used:
            highlighting_summary["alignment_model"] = alignment_model_used
        metadata["highlighting_summary"] = highlighting_summary
        metadata["highlighting_policy"] = alignment_policy
        if (
            _REQUIRED_HIGHLIGHT_POLICY
            and (alignment_policy or "").lower() != _REQUIRED_HIGHLIGHT_POLICY
        ):
            raise RuntimeError(
                f"Highlighting policy '{alignment_policy}' does not satisfy "
                f"EBOOK_HIGHLIGHT_POLICY={_REQUIRED_HIGHLIGHT_POLICY} "
                f"(sentence {translation_task.sentence_number})."
            )

        original_text = text_norm.collapse_whitespace(translation_task.sentence or "")
        if original_audio_segment is not None and len(original_audio_segment) > 0 and original_text:
            original_pause_before_ms = 0
            original_pause_after_ms = 0
            original_pause_before_ms, original_pause_after_ms = _measure_pause_edges(
                original_audio_segment
            )
            original_language_label = input_language or ""
            original_language_code = _lookup_language_code(
                original_language_label, language_codes
            )
            original_words = split_highlight_tokens(original_text)
            original_alignment_policy = "uniform"
            original_alignment_source = "unavailable"
            original_alignment_model_used: Optional[str] = None
            original_word_tokens: List[Dict[str, float | str]] = []
            original_char_weighted_used = False
            original_char_weighted_punctuation = False
            original_duration_hint_cache: Optional[float] = None
            original_char_weighted_failure_policy: Optional[str] = None
            original_char_weighted_requested = bool(
                settings_obj
                and getattr(settings_obj, "char_weighted_highlighting_default", False)
            )
            original_punctuation_boost_enabled = bool(
                settings_obj
                and getattr(settings_obj, "char_weighted_punctuation_boost", False)
            )

            def _apply_original_char_weighted(
                *,
                policy_override: Optional[str] = None,
                use_punctuation: bool = False,
            ) -> bool:
                nonlocal original_word_tokens, original_alignment_policy, original_alignment_source
                nonlocal original_char_weighted_used, original_duration_hint_cache
                nonlocal original_char_weighted_punctuation
                if not original_text:
                    return False
                if original_duration_hint_cache is None:
                    original_duration_hint_cache = _resolve_sentence_duration_hint(
                        original_audio_segment, {}
                    )
                duration_hint = original_duration_hint_cache
                if duration_hint is None or duration_hint <= 0:
                    return False
                fallback_words = original_words or [original_text]
                estimated_tokens = compute_char_weighted_timings(
                    fallback_words,
                    duration_hint,
                    pause_before_ms=original_pause_before_ms,
                    pause_after_ms=original_pause_after_ms,
                )
                if not estimated_tokens:
                    return False
                original_word_tokens = estimated_tokens
                original_char_weighted_used = True
                if use_punctuation:
                    original_char_weighted_punctuation = True
                original_alignment_policy = policy_override or (
                    "estimated_punct" if use_punctuation else "estimated"
                )
                original_alignment_source = "char_weighted_duration"
                return True

            if original_char_weighted_requested:
                _apply_original_char_weighted(use_punctuation=original_punctuation_boost_enabled)

            if (
                not original_word_tokens
                and original_text
                and settings_obj
                and getattr(settings_obj, "forced_alignment_enabled", False)
            ):
                backend_candidate = getattr(settings_obj, "alignment_backend", None) or getattr(
                    settings_obj, "forced_alignment_backend", None
                )
                backend_name = backend_candidate.strip() if isinstance(backend_candidate, str) else ""
                if backend_name:
                    alignment_model, model_source = _resolve_alignment_model_choice(
                        settings_obj,
                        language_label=original_language_label,
                        iso_code=original_language_code,
                    )
                    logger.info(
                        "Sentence %s original alignment backend=%s model=%s source=%s language=%s (%s)",
                        translation_task.sentence_number,
                        backend_name,
                        alignment_model or "<default>",
                        model_source,
                        original_language_label or "?",
                        original_language_code or "unknown",
                    )
                    aligned_tokens, retry_exhausted = _align_with_backend(
                        audio_segment=original_audio_segment,
                        text=original_text,
                        backend=backend_name,
                        model=alignment_model,
                    )
                    if aligned_tokens:
                        original_word_tokens = aligned_tokens
                        original_alignment_policy = "forced"
                        original_alignment_source = "aligner"
                        original_alignment_model_used = alignment_model
                        original_char_weighted_failure_policy = None
                    else:
                        if retry_exhausted:
                            original_char_weighted_failure_policy = "retry_failed_align"
                        else:
                            original_char_weighted_failure_policy = None
            if not original_word_tokens and original_text:
                extracted_tokens, policy, source = _extract_word_tokens(
                    text=original_text,
                    audio_segment=original_audio_segment,
                    metadata={},
                )
                original_word_tokens = extracted_tokens
                original_alignment_policy = policy or "uniform"
                original_alignment_source = source or "unavailable"
                if original_word_tokens:
                    original_char_weighted_failure_policy = None
            if original_text and (original_char_weighted_requested or not original_word_tokens):
                if not original_char_weighted_used:
                    policy_override = original_char_weighted_failure_policy
                    applied = _apply_original_char_weighted(
                        policy_override=policy_override,
                        use_punctuation=original_punctuation_boost_enabled,
                    )
                    if not applied and policy_override:
                        original_alignment_policy = policy_override
            if (
                original_word_tokens
                and settings_obj
                and getattr(settings_obj, "forced_alignment_enabled", False)
            ):
                smoothing_value = getattr(settings_obj, "forced_alignment_smoothing", 0.35)
                try:
                    smoothing_factor = float(smoothing_value)
                except (TypeError, ValueError):
                    smoothing_factor = 0.35
                original_word_tokens = smooth_token_boundaries(
                    original_word_tokens, smoothing=smoothing_factor
                )

            if original_word_tokens:
                metadata["original_word_tokens"] = original_word_tokens
                metadata["originalWordTokens"] = original_word_tokens

            original_total_duration: Optional[float] = None
            try:
                original_total_duration = float(original_audio_segment.duration_seconds)
            except Exception:
                original_total_duration = None
            if original_total_duration is None and original_word_tokens:
                last_token = original_word_tokens[-1]
                try:
                    original_total_duration = float(last_token.get("end", 0.0))
                except (TypeError, ValueError, AttributeError):
                    original_total_duration = None
            original_highlight_duration = (
                original_total_duration if isinstance(original_total_duration, float) else 0.0
            )
            original_summary = {
                "policy": original_alignment_policy,
                "tempo": tempo,
                "tokens": len(original_word_tokens),
                "token_count": len(original_word_tokens),
                "duration": round(original_highlight_duration, 6)
                if original_highlight_duration
                else original_highlight_duration,
                "source": original_alignment_source,
                "punctuation_weighting": bool(original_char_weighted_punctuation),
                "pause_before_ms": original_pause_before_ms,
                "pause_after_ms": original_pause_after_ms,
            }
            if original_char_weighted_used:
                original_summary["method"] = "char_weighted"
                original_summary["char_weighted"] = True
                original_summary["char_weighted_refined"] = True
            if original_alignment_model_used:
                original_summary["alignment_model"] = original_alignment_model_used
            metadata["original_highlighting_summary"] = original_summary
            metadata["original_highlighting_policy"] = original_alignment_policy
            metadata["original_pause_before_ms"] = original_pause_before_ms
            metadata["original_pause_after_ms"] = original_pause_after_ms
            metadata["originalPauseBeforeMs"] = original_pause_before_ms
            metadata["originalPauseAfterMs"] = original_pause_after_ms

        if audio_segment is not None and metadata.get("word_tokens"):
            try:
                setattr(audio_segment, "word_tokens", metadata["word_tokens"])
            except Exception:
                pass
        if original_audio_segment is not None and metadata.get("original_word_tokens"):
            try:
                setattr(original_audio_segment, "word_tokens", metadata["original_word_tokens"])
            except Exception:
                pass

        logger.info(
            "Sentence %s highlighting policy=%s tokens=%d duration=%.3fs tempo=%.2f (source=%s)",
            translation_task.sentence_number,
            alignment_policy,
            len(word_tokens),
            highlight_duration or 0.0,
            tempo,
            alignment_source,
        )

        payload = media_result_factory(
            index=translation_task.index,
            sentence_number=translation_task.sentence_number,
            sentence=translation_task.sentence,
            target_language=translation_task.target_language,
            translation=translation_task.translation,
            transliteration=translation_task.transliteration,
            audio_segment=audio_segment,
            audio_tracks=audio_tracks,
            voice_metadata=voice_metadata,
            metadata=metadata,
        )

        while True:
            if audio_stop_event and audio_stop_event.is_set():
                break
            try:
                audio_result_queue.put(payload, timeout=0.1)
                break
            except Full:
                continue


__all__ = [
    "AudioWorker",
    "VideoWorker",
    "TextWorker",
    "audio_worker_body",
]
