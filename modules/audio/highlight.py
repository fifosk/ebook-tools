"""Audio highlight metadata utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Mapping, Optional, Sequence, Literal

from pydub import AudioSegment

from modules.audio.tts import SILENCE_DURATION_MS


@dataclass(frozen=True)
class AudioHighlightPart:
    """Represents a contiguous audio fragment used for word highlighting."""

    kind: Literal["original", "translation", "other", "silence"]
    duration: float


@dataclass
class SentenceAudioMetadata:
    """Metadata describing how a sentence's audio should drive highlighting."""

    parts: List[AudioHighlightPart]
    total_duration: float


@dataclass(frozen=True)
class HighlightEvent:
    """Represents a single highlight step and its corresponding duration."""

    duration: float
    original_index: int
    translation_index: int
    transliteration_index: int


_AUDIO_METADATA_REGISTRY: Dict[int, SentenceAudioMetadata] = {}


def _store_audio_metadata(audio: AudioSegment, metadata: SentenceAudioMetadata) -> None:
    """Attach sentence-level metadata to an ``AudioSegment`` instance."""

    try:
        setattr(audio, "_sentence_audio_metadata", metadata)
    except AttributeError:
        key = id(audio)
        _AUDIO_METADATA_REGISTRY[key] = metadata
        try:
            setattr(audio, "_sentence_audio_metadata_key", key)
        except AttributeError:
            # If both attempts fail, fallback to registry lookup by id without hint.
            pass
    else:
        key = id(audio)
        _AUDIO_METADATA_REGISTRY[key] = metadata
        setattr(audio, "_sentence_audio_metadata_key", key)


def _get_audio_metadata(audio: AudioSegment) -> Optional[SentenceAudioMetadata]:
    """Retrieve previously attached sentence-level audio metadata."""

    metadata = getattr(audio, "_sentence_audio_metadata", None)
    if metadata is not None:
        return metadata
    key = getattr(audio, "_sentence_audio_metadata_key", None)
    if key is not None:
        return _AUDIO_METADATA_REGISTRY.get(key)
    return _AUDIO_METADATA_REGISTRY.get(id(audio))


def _compute_audio_highlight_metadata(
    audio: AudioSegment,
    sequence: Sequence[str],
    segments: Mapping[str, AudioSegment],
    tempo: float,
) -> SentenceAudioMetadata:
    """Compute highlight metadata using the generated sentence audio."""

    if tempo <= 0:
        tempo_scale = 1.0
    else:
        tempo_scale = 1.0 / tempo

    parts: List[AudioHighlightPart] = []
    silence_duration_sec = (SILENCE_DURATION_MS / 1000.0) * tempo_scale if sequence else 0.0

    for key in sequence:
        segment = segments.get(key)
        base_ms = len(segment) if segment is not None else 0
        duration_sec = (base_ms / 1000.0) * tempo_scale
        if key == "input":
            kind: Literal["original", "translation", "other", "silence"] = "original"
        elif key == "translation":
            kind = "translation"
        else:
            kind = "other"
        parts.append(AudioHighlightPart(kind=kind, duration=duration_sec))
        if silence_duration_sec > 0:
            parts.append(AudioHighlightPart(kind="silence", duration=silence_duration_sec))

    total_duration = len(audio) / 1000.0 if audio else 0.0
    return SentenceAudioMetadata(parts=parts, total_duration=total_duration)


def _build_events_from_metadata(
    metadata: SentenceAudioMetadata,
    sync_ratio: float,
    num_original_words: int,
    num_translation_words: int,
    num_translit_words: int,
) -> List[HighlightEvent]:
    """Create highlight events from stored audio metadata."""

    events: List[HighlightEvent] = []
    original_index = 0
    translation_index = 0
    transliteration_index = 0

    for part in metadata.parts:
        base_duration = max(part.duration, 0.0)
        if base_duration == 0:
            continue
        duration = base_duration * sync_ratio
        if duration <= 0:
            continue

        if part.kind == "original" and num_original_words > 0:
            remaining = max(0, num_original_words - original_index)
            if remaining <= 0:
                events.append(
                    HighlightEvent(
                        duration=duration,
                        original_index=original_index,
                        translation_index=translation_index,
                        transliteration_index=transliteration_index,
                    )
                )
            else:
                per_word = duration / remaining if remaining else duration
                for _ in range(remaining):
                    original_index = min(original_index + 1, num_original_words)
                    events.append(
                        HighlightEvent(
                            duration=per_word,
                            original_index=original_index,
                            translation_index=translation_index,
                            transliteration_index=transliteration_index,
                        )
                    )
        elif part.kind == "translation" and num_translation_words > 0:
            remaining = max(0, num_translation_words - translation_index)
            if remaining <= 0:
                events.append(
                    HighlightEvent(
                        duration=duration,
                        original_index=original_index,
                        translation_index=translation_index,
                        transliteration_index=transliteration_index,
                    )
                )
            else:
                per_unit = duration / remaining if remaining else duration
                for _ in range(remaining):
                    translation_index = min(translation_index + 1, num_translation_words)
                    if num_translation_words:
                        progress = translation_index / num_translation_words
                    else:
                        progress = 1.0
                    if num_translit_words:
                        target = int(round(progress * num_translit_words))
                        transliteration_index = max(
                            transliteration_index,
                            min(num_translit_words, target),
                        )
                    events.append(
                        HighlightEvent(
                            duration=per_unit,
                            original_index=original_index,
                            translation_index=translation_index,
                            transliteration_index=transliteration_index,
                        )
                    )
        else:
            events.append(
                HighlightEvent(
                    duration=duration,
                    original_index=original_index,
                    translation_index=translation_index,
                    transliteration_index=transliteration_index,
                )
            )
    return events


def _build_legacy_highlight_events(
    audio_duration: float,
    sync_ratio: float,
    original_words: Sequence[str],
    translation_units: Sequence[str],
    transliteration_words: Sequence[str],
) -> List[HighlightEvent]:
    """Fallback event generation mirroring the previous highlight behaviour."""

    total_letters = sum(len(unit) for unit in translation_units)
    num_units = len(translation_units)
    adjusted_duration = max(audio_duration, 0.0)

    word_durations: List[float] = []
    if num_units > 0 and adjusted_duration > 0:
        for unit in translation_units:
            if total_letters > 0:
                dur = (len(unit) / total_letters) * adjusted_duration * sync_ratio
            else:
                dur = (adjusted_duration / num_units) * sync_ratio
            word_durations.append(dur)
    else:
        word_durations.append(adjusted_duration * sync_ratio if adjusted_duration > 0 else 0.0)

    events: List[HighlightEvent] = []
    accumulated_time = 0.0
    num_original_words = len(original_words)
    num_translation_words = len(translation_units)
    num_translit_words = len(transliteration_words)

    for idx, duration in enumerate(word_durations):
        accumulated_time += duration
        if idx == len(word_durations) - 1:
            fraction = 1.0
        else:
            fraction = accumulated_time / adjusted_duration if adjusted_duration else 1.0
        original_index = int(fraction * num_original_words) if num_original_words else 0
        translation_index = int(fraction * num_translation_words) if num_translation_words else 0
        transliteration_index = int(fraction * num_translit_words) if num_translit_words else 0
        events.append(
            HighlightEvent(
                duration=duration,
                original_index=original_index,
                translation_index=translation_index,
                transliteration_index=transliteration_index,
            )
        )
    return events


__all__ = [
    "AudioHighlightPart",
    "SentenceAudioMetadata",
    "HighlightEvent",
    "_store_audio_metadata",
    "_get_audio_metadata",
    "_compute_audio_highlight_metadata",
    "_build_events_from_metadata",
    "_build_legacy_highlight_events",
]
