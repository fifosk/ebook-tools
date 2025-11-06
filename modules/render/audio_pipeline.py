"""Worker implementations for media rendering pipelines."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from queue import Empty, Full, Queue
from typing import Any, Callable, Dict, List, Mapping, Optional, Protocol, Sequence, TYPE_CHECKING

from pydub import AudioSegment

from modules import logging_manager as log_mgr
from modules.audio.backends import get_default_backend_name
from modules.render.backends.base import SynthesisResult
from .context import RenderBatchContext

if TYPE_CHECKING:  # pragma: no cover - imports for static analysis only
    from modules.progress_tracker import ProgressTracker
    from modules.translation_engine import TranslationTask
    from modules.audio_video_generator import MediaPipelineResult

logger = log_mgr.logger


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


def _extract_word_tokens(
    *,
    text: str,
    audio_segment: Optional[AudioSegment],
    metadata: Mapping[str, object],
) -> List[Dict[str, float | str]]:
    """Return per-word timing tokens derived from char timings or equal slices."""

    if not text:
        return []

    char_timings: Optional[Sequence[Mapping[str, object]]] = None
    candidate = metadata.get("char_timings") if isinstance(metadata, Mapping) else None
    if isinstance(candidate, Sequence):
        char_timings = candidate  # type: ignore[assignment]
    if char_timings is None:
        char_timings = _segment_char_timings(audio_segment)

    tokens: List[Dict[str, float | str]] = []
    if char_timings:
        tokens = _tokens_from_char_timings(text, char_timings)

    if not tokens:
        duration = float(audio_segment.duration_seconds) if audio_segment is not None else 0.0
        tokens = _evenly_distributed_tokens(text, duration)

    return tokens


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
        voice_metadata: Mapping[str, Mapping[str, str]] = {}
        metadata: Dict[str, Any] = {}
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
                    audio_segment = audio_output.audio
                    voice_metadata = audio_output.voice_metadata
                    raw_metadata = getattr(audio_output, "metadata", None)
                    if isinstance(raw_metadata, Mapping):
                        metadata = dict(raw_metadata)
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

        translation_text = translation_task.translation or ""
        char_timings_candidate = metadata.get("char_timings")
        has_char_timings = isinstance(char_timings_candidate, Sequence) and not isinstance(
            char_timings_candidate, (str, bytes)
        )
        if translation_text and (audio_segment is not None or has_char_timings):
            word_tokens = _extract_word_tokens(
                text=translation_text,
                audio_segment=audio_segment,
                metadata=metadata,
            )
            if word_tokens:
                metadata["word_tokens"] = word_tokens

        if translation_text:
            metadata.setdefault("text", translation_text)
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

        if audio_segment is not None and metadata.get("word_tokens"):
            try:
                setattr(audio_segment, "word_tokens", metadata["word_tokens"])
            except Exception:
                pass

        payload = media_result_factory(
            index=translation_task.index,
            sentence_number=translation_task.sentence_number,
            sentence=translation_task.sentence,
            target_language=translation_task.target_language,
            translation=translation_task.translation,
            transliteration=translation_task.transliteration,
            audio_segment=audio_segment,
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
