"""Audio highlight metadata utilities."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Literal

import regex

from pydub import AudioSegment

from modules import config_manager as cfg
from modules.audio import aligner
from modules.audio.tts import SILENCE_DURATION_MS


@dataclass(frozen=True)
class AudioHighlightPart:
    """Represents a contiguous audio fragment used for word highlighting."""

    kind: Literal["original", "translation", "other", "silence"]
    duration: float
    text: str = ""
    start_offset: float = 0.0
    steps: Tuple["HighlightStep", ...] = field(default_factory=tuple)


@dataclass
class SentenceAudioMetadata:
    """Metadata describing how a sentence's audio should drive highlighting."""

    parts: List[AudioHighlightPart]
    total_duration: float


@dataclass(frozen=True)
class HighlightStep:
    """Represents a timing step for a single grapheme cluster."""

    kind: Literal["original", "translation", "other", "silence"]
    word_index: Optional[int]
    char_index_start: Optional[int]
    char_index_end: Optional[int]
    start_ms: float
    duration_ms: float


@dataclass(frozen=True)
class HighlightEvent:
    """Represents a single highlight step and its corresponding duration."""

    duration: float
    original_index: int
    translation_index: int
    transliteration_index: int
    step: Optional[HighlightStep] = None


_AUDIO_METADATA_REGISTRY: Dict[int, SentenceAudioMetadata] = {}

_CJK_SCRIPT_PATTERN = regex.compile(
    r"\p{Script=Han}|\p{Script=Hiragana}|\p{Script=Katakana}|\p{Script=Hangul}"
)


def _contains_cjk(text: str) -> bool:
    return bool(_CJK_SCRIPT_PATTERN.search(text))


def _is_cjk_text(text: str) -> bool:
    has_cjk = False
    for char in text:
        if _is_separator(char):
            continue
        if _contains_cjk(char):
            has_cjk = True
        elif char.isalpha():
            return False
    return has_cjk


def translation_highlight_units(text: str) -> List[str]:
    """Return logical highlight units for a translated segment."""

    if not text:
        return []
    if _is_cjk_text(text):
        units: List[str] = []
        for match in regex.finditer(r"\X", text):
            grapheme = match.group()
            if _is_separator(grapheme):
                continue
            units.append(grapheme)
        if units:
            return units
        return [text]
    words = text.split()
    if words:
        return words
    return [text]


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


def _resolve_forced_alignment_preferences() -> Tuple[bool, str]:
    """Return the forced-alignment enable flag and smoothing preference."""

    try:
        settings = cfg.get_settings()
    except Exception:  # pragma: no cover - defensive for partially initialized config
        return False, "monotonic_cubic"

    enabled = bool(getattr(settings, "forced_alignment_enabled", False))
    smoothing = getattr(settings, "forced_alignment_smoothing", "monotonic_cubic")
    if not isinstance(smoothing, str):
        smoothing = "monotonic_cubic"
    return enabled, smoothing


def _compute_audio_highlight_metadata(
    audio: AudioSegment,
    sequence: Sequence[str],
    segments: Mapping[str, AudioSegment],
    tempo: float,
    texts: Optional[Mapping[str, str]] = None,
) -> SentenceAudioMetadata:
    """Compute highlight metadata using the generated sentence audio."""

    if tempo <= 0:
        tempo_scale = 1.0
    else:
        tempo_scale = 1.0 / tempo

    parts: List[AudioHighlightPart] = []
    silence_duration_sec = (SILENCE_DURATION_MS / 1000.0) * tempo_scale if sequence else 0.0

    current_offset_ms = 0.0
    for key in sequence:
        segment = segments.get(key)
        base_ms = len(segment) if segment is not None else 0
        duration_sec = (base_ms / 1000.0) * tempo_scale
        text = texts.get(key, "") if texts else ""
        if key == "input":
            kind: Literal["original", "translation", "other", "silence"] = "original"
        elif key == "translation":
            kind = "translation"
        else:
            kind = "other"
        steps = _segment_highlight_steps(text, segment, tempo_scale, current_offset_ms, kind)
        parts.append(
            AudioHighlightPart(
                kind=kind,
                duration=duration_sec,
                text=text,
                start_offset=current_offset_ms / 1000.0,
                steps=tuple(steps),
            )
        )
        current_offset_ms += duration_sec * 1000.0
        if silence_duration_sec > 0:
            parts.append(
                AudioHighlightPart(
                    kind="silence",
                    duration=silence_duration_sec,
                    text="",
                    start_offset=current_offset_ms / 1000.0,
                    steps=tuple(
                        _silence_highlight_steps(silence_duration_sec, current_offset_ms)
                    ),
                )
            )
            current_offset_ms += silence_duration_sec * 1000.0

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
    fallback_offset_ms = 0.0

    for part in metadata.parts:
        base_duration = max(part.duration, 0.0)
        if base_duration == 0:
            continue
        if part.steps:
            for step in part.steps:
                duration = step.duration_ms / 1000.0
                if duration <= 0:
                    continue
                if part.kind == "original" and num_original_words > 0:
                    if step.word_index is not None:
                        target = min(num_original_words, step.word_index + 1)
                        original_index = max(original_index, target)
                elif part.kind == "translation" and num_translation_words > 0:
                    if step.word_index is not None:
                        target = min(num_translation_words, step.word_index + 1)
                        translation_index = max(translation_index, target)
                        if num_translation_words:
                            progress = translation_index / num_translation_words
                        else:
                            progress = 1.0
                        if num_translit_words:
                            target_translit = int(round(progress * num_translit_words))
                            transliteration_index = max(
                                transliteration_index,
                                min(num_translit_words, target_translit),
                            )
                events.append(
                    HighlightEvent(
                        duration=duration,
                        original_index=original_index,
                        translation_index=translation_index,
                        transliteration_index=transliteration_index,
                        step=step,
                    )
                )
            fallback_offset_ms = max(
                fallback_offset_ms, part.start_offset * 1000.0 + base_duration * 1000.0
            )
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
                        step=_fallback_step(part, fallback_offset_ms, base_duration, part.kind),
                    )
                )
            else:
                per_word = duration / remaining if remaining else duration
                per_word_ms = (base_duration * 1000.0) / remaining if remaining else base_duration * 1000.0
                for index in range(remaining):
                    start_ms = fallback_offset_ms + per_word_ms * index
                    original_index = min(original_index + 1, num_original_words)
                    events.append(
                        HighlightEvent(
                            duration=per_word,
                            original_index=original_index,
                            translation_index=translation_index,
                            transliteration_index=transliteration_index,
                            step=HighlightStep(
                                kind=part.kind,
                                word_index=original_index - 1,
                                char_index_start=None,
                                char_index_end=None,
                                start_ms=start_ms,
                                duration_ms=per_word_ms,
                            ),
                        )
                    )
            fallback_offset_ms += base_duration * 1000.0
        elif part.kind == "translation" and num_translation_words > 0:
            remaining = max(0, num_translation_words - translation_index)
            if remaining <= 0:
                events.append(
                    HighlightEvent(
                        duration=duration,
                        original_index=original_index,
                        translation_index=translation_index,
                        transliteration_index=transliteration_index,
                        step=_fallback_step(part, fallback_offset_ms, base_duration, part.kind),
                    )
                )
            else:
                per_unit = duration / remaining if remaining else duration
                per_unit_ms = (base_duration * 1000.0) / remaining if remaining else base_duration * 1000.0
                for index in range(remaining):
                    start_ms = fallback_offset_ms + per_unit_ms * index
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
                            step=HighlightStep(
                                kind=part.kind,
                                word_index=translation_index - 1,
                                char_index_start=None,
                                char_index_end=None,
                                start_ms=start_ms,
                                duration_ms=per_unit_ms,
                            ),
                        )
                    )
            fallback_offset_ms += base_duration * 1000.0
        else:
            events.append(
                HighlightEvent(
                    duration=duration,
                    original_index=original_index,
                    translation_index=translation_index,
                    transliteration_index=transliteration_index,
                    step=_fallback_step(part, fallback_offset_ms, base_duration, part.kind),
                )
            )
            fallback_offset_ms += base_duration * 1000.0
    return events


def _fallback_step(
    part: AudioHighlightPart,
    base_offset_ms: float,
    base_duration: float,
    kind: Literal["original", "translation", "other", "silence"],
) -> HighlightStep:
    return HighlightStep(
        kind=kind,
        word_index=None,
        char_index_start=None,
        char_index_end=None,
        start_ms=base_offset_ms,
        duration_ms=base_duration * 1000.0,
    )


def _silence_highlight_steps(duration_sec: float, base_offset_ms: float) -> Iterable[HighlightStep]:
    duration_ms = duration_sec * 1000.0
    yield HighlightStep(
        kind="silence",
        word_index=None,
        char_index_start=None,
        char_index_end=None,
        start_ms=base_offset_ms,
        duration_ms=duration_ms,
    )


def _segment_highlight_steps(
    text: str,
    segment: Optional[AudioSegment],
    tempo_scale: float,
    base_offset_ms: float,
    kind: Literal["original", "translation", "other", "silence"],
) -> List[HighlightStep]:
    if not text or segment is None:
        return []
    treat_as_cjk = _is_cjk_text(text)
    raw = _extract_character_timings(segment)
    needs_alignment = True
    if raw:
        for entry in raw:
            if isinstance(entry, Mapping):
                needs_alignment = False
                break
    if needs_alignment:
        enabled, smoothing = _resolve_forced_alignment_preferences()
        if enabled:
            try:
                raw = aligner.align_characters(segment, text, smoothing=smoothing)
            except Exception:  # pragma: no cover - forced alignment is best-effort
                raw = []
    if not raw:
        if not treat_as_cjk:
            return []
        return list(
            _distribute_cjk_steps(text, segment, tempo_scale, base_offset_ms, kind)
        )
    return list(
        _collapse_char_timings_to_graphemes(
            text, raw, tempo_scale, base_offset_ms, kind, treat_as_cjk=treat_as_cjk
        )
    )


def _distribute_cjk_steps(
    text: str,
    segment: AudioSegment,
    tempo_scale: float,
    base_offset_ms: float,
    kind: Literal["original", "translation", "other", "silence"],
) -> Iterable[HighlightStep]:
    grapheme_matches = [
        match
        for match in regex.finditer(r"\X", text)
        if not _is_separator(match.group())
    ]
    if not grapheme_matches:
        return []

    total_duration_ms = float(len(segment)) * tempo_scale
    if total_duration_ms <= 0:
        return []

    count = len(grapheme_matches)
    per_unit_ms = total_duration_ms / count if count else total_duration_ms

    steps: List[HighlightStep] = []
    current_start = base_offset_ms
    for index, match in enumerate(grapheme_matches):
        if index == count - 1:
            consumed = current_start - base_offset_ms
            duration_ms = max(total_duration_ms - consumed, 0.0)
        else:
            duration_ms = per_unit_ms
        steps.append(
            HighlightStep(
                kind=kind,
                word_index=index,
                char_index_start=match.start(),
                char_index_end=match.end(),
                start_ms=current_start,
                duration_ms=duration_ms,
            )
        )
        current_start += per_unit_ms
    return steps


def _extract_character_timings(segment: AudioSegment) -> Optional[Sequence[Mapping[str, object]]]:
    for attr in (
        "highlight_character_timing",
        "character_timing",
        "char_timings",
        "alignment",
    ):
        timings = getattr(segment, attr, None)
        if timings:
            return timings  # type: ignore[return-value]
    provider = getattr(segment, "get_alignment_metadata", None)
    if callable(provider):
        try:
            result = provider()
        except TypeError:
            result = provider(segment)  # type: ignore[misc]
        if result:
            return result  # type: ignore[return-value]
    return None


def _collapse_char_timings_to_graphemes(
    text: str,
    char_timings: Sequence[Mapping[str, object]],
    tempo_scale: float,
    base_offset_ms: float,
    kind: Literal["original", "translation", "other", "silence"],
    *,
    treat_as_cjk: bool = False,
) -> Iterable[HighlightStep]:
    if not text:
        return []

    normalized_timings: List[Optional[Tuple[float, float]]] = [None] * len(text)
    for idx in range(min(len(char_timings), len(text))):
        entry = char_timings[idx]
        if isinstance(entry, Mapping):
            start_val = entry.get("start_ms", entry.get("start", entry.get("offset", 0)))
            duration_val = entry.get(
                "duration_ms", entry.get("duration", entry.get("length", 0))
            )
        else:
            continue
        try:
            start = float(start_val) * tempo_scale
            duration = float(duration_val) * tempo_scale
        except (TypeError, ValueError):
            continue
        normalized_timings[idx] = (start, duration)

    if not any(normalized_timings):
        return []

    has_whitespace = any(ch.isspace() for ch in text)
    char_to_word_index: Dict[int, int] = {}
    if has_whitespace and not treat_as_cjk:
        word_index = 0
        idx = 0
        length = len(text)
        while idx < length:
            ch = text[idx]
            if ch.isspace():
                idx += 1
                continue
            start_idx = idx
            while idx < length and not text[idx].isspace():
                char_to_word_index[idx] = word_index
                idx += 1
            word_index += 1
    else:
        # Without explicit whitespace boundaries treat every grapheme as its own word.
        pass

    grapheme_iter = list(regex.finditer(r"\X", text))
    word_counter = 0
    for cluster_index, match in enumerate(grapheme_iter):
        start_idx = match.start()
        end_idx = match.end()
        grapheme = match.group()
        if _is_separator(grapheme):
            continue
        relevant_timings = [
            normalized_timings[i]
            for i in range(start_idx, end_idx)
            if i < len(normalized_timings) and normalized_timings[i] is not None
        ]
        if not relevant_timings:
            continue
        start = min(val[0] for val in relevant_timings) + base_offset_ms
        end = max(val[0] + val[1] for val in relevant_timings) + base_offset_ms
        duration = max(end - start, 0.0)
        if has_whitespace:
            word_index = char_to_word_index.get(start_idx)
            if word_index is None:
                word_index = word_counter
        else:
            word_index = word_counter
        yield HighlightStep(
            kind=kind,
            word_index=word_index,
            char_index_start=start_idx,
            char_index_end=end_idx,
            start_ms=start,
            duration_ms=duration,
        )
        word_counter += 1


def _is_separator(grapheme: str) -> bool:
    if not grapheme:
        return True
    if grapheme.isspace():
        return True
    category = unicodedata.category(grapheme[0])
    return category.startswith("Z")


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


@dataclass
class HighlightSegment:
    """Represents a coalesced rendering instruction for a highlight frame."""

    duration: float
    original_index: int
    translation_index: int
    transliteration_index: int
    original_char_range: Optional[Tuple[int, int]] = None
    translation_char_range: Optional[Tuple[int, int]] = None
    transliteration_char_range: Optional[Tuple[int, int]] = None
    step_kind: Optional[Literal["original", "translation", "other", "silence"]] = None

    def style_signature(self) -> Tuple[
        int,
        int,
        int,
        Optional[Tuple[int, int]],
        Optional[Tuple[int, int]],
        Optional[Tuple[int, int]],
        Optional[Literal["original", "translation", "other", "silence"]],
    ]:
        """Return an immutable signature describing the rendered highlight style."""

        return (
            self.original_index,
            self.translation_index,
            self.transliteration_index,
            self.original_char_range,
            self.translation_char_range,
            self.transliteration_char_range,
            self.step_kind,
        )


def _event_char_range(
    event: HighlightEvent, target_kind: Literal["original", "translation", "other"]
) -> Optional[Tuple[int, int]]:
    """Return the character span for ``event`` if it applies to ``target_kind``."""

    step = event.step
    if step is None or step.kind != target_kind:
        return None
    start = step.char_index_start
    end = step.char_index_end
    if start is None or end is None:
        return None
    start_idx = int(start)
    end_idx = int(end)
    if end_idx <= start_idx:
        return None
    return (start_idx, end_idx)


def coalesce_highlight_events(
    events: Sequence[HighlightEvent],
) -> List[HighlightSegment]:
    """Merge contiguous events with identical styling metadata."""

    segments: List[HighlightSegment] = []
    previous: Optional[HighlightSegment] = None

    for event in events:
        segment = HighlightSegment(
            duration=event.duration,
            original_index=event.original_index,
            translation_index=event.translation_index,
            transliteration_index=event.transliteration_index,
            original_char_range=_event_char_range(event, "original"),
            translation_char_range=_event_char_range(event, "translation"),
            transliteration_char_range=_event_char_range(event, "other"),
            step_kind=event.step.kind if event.step else None,
        )
        if previous is not None and previous.style_signature() == segment.style_signature():
            previous.duration += segment.duration
        else:
            segments.append(segment)
            previous = segment

    return segments


__all__ = [
    "AudioHighlightPart",
    "SentenceAudioMetadata",
    "HighlightStep",
    "HighlightEvent",
    "HighlightSegment",
    "coalesce_highlight_events",
    "_store_audio_metadata",
    "_get_audio_metadata",
    "_compute_audio_highlight_metadata",
    "_build_events_from_metadata",
    "_build_legacy_highlight_events",
    "translation_highlight_units",
]
