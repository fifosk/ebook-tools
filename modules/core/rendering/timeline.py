"""Lightweight helpers shared by rendering metadata builders."""

from __future__ import annotations

import math
import re
import string
from dataclasses import dataclass
from statistics import fmean
from typing import Any, Mapping, Sequence, List, Optional

from modules.text import split_highlight_tokens


_TIMING_PRECISION = 0.003  # 3 ms precision
_PAUSE_PUNCTUATION = {",", ";", "،", "؛"}
_FINAL_PUNCTUATION = {".", "!", "?", "؟", "…", "！", "？", "。"}
_TRAILING_WRAPPERS = {'"', "'", "”", "’", "）", ")", "]", "}", "›", "»"}
_VISIBLE_PUNCT_PATTERN = re.compile(rf"[{re.escape(string.punctuation)}«»“”„‘’]")


@dataclass(slots=True)
class SentenceTimingSpec:
    """Specification describing per-sentence timing inputs for dual tracks."""

    sentence_idx: int
    original_text: str
    translation_text: str
    original_words: Sequence[str]
    translation_words: Sequence[str]
    word_tokens: Sequence[Mapping[str, Any]] | None
    translation_duration: float
    original_duration: float
    gap_before_translation: float
    gap_after_translation: float
    char_weighted_enabled: bool
    punctuation_boost: bool
    policy: Optional[str]
    source: Optional[str]
    original_word_tokens: Sequence[Mapping[str, Any]] | None = None
    original_policy: Optional[str] = None
    original_source: Optional[str] = None
    start_gate: float = 0.0
    end_gate: float = 0.0
    original_start_gate: float = 0.0
    original_end_gate: float = 0.0
    pause_before_ms: float = 0.0
    pause_after_ms: float = 0.0
    original_pause_before_ms: float = 0.0
    original_pause_after_ms: float = 0.0
    mix_start_gate: float = 0.0
    mix_end_gate: float = 0.0
    validation_metrics: Optional[dict[str, dict[str, float]]] = None


def _round_to_precision(value: float) -> float:
    """Round ``value`` to the configured precision while keeping six decimal places."""

    if not math.isfinite(value):
        return 0.0
    if value < 0:
        value = 0.0
    increments = round(value / _TIMING_PRECISION)
    rounded = increments * _TIMING_PRECISION
    return round(rounded, 6)


def smooth_token_boundaries(
    tokens: Sequence[Mapping[str, Any]], smoothing: float = 0.35
) -> list[dict[str, float | str]]:
    """
    Apply temporal smoothing to word-level boundaries.

    Uses a low-pass blend with neighbouring tokens to dampen jitter while enforcing
    monotonic boundaries.
    """

    if not tokens:
        return []

    try:
        factor = float(smoothing)
    except (TypeError, ValueError):
        factor = 0.35
    factor = max(0.0, min(1.0, factor))

    smoothed: list[dict[str, float | str]] = []
    for index, token in enumerate(tokens):
        if not isinstance(token, Mapping):
            continue
        start = token.get("start")
        end = token.get("end")
        text = token.get("text")
        try:
            t0 = float(start)
            t1 = float(end)
        except (TypeError, ValueError):
            continue
        if t1 < t0:
            t1 = t0
        # neighbour influence
        if 0 < index < len(tokens) - 1 and factor > 0:
            prev_tok = tokens[index - 1]
            next_tok = tokens[index + 1]
            try:
                prev_end = float(prev_tok.get("end", t0))
            except (TypeError, ValueError):
                prev_end = t0
            try:
                next_start = float(next_tok.get("start", t1))
            except (TypeError, ValueError):
                next_start = t1
            t0 = fmean([t0, prev_end * factor + t0 * (1 - factor)])
            t1 = fmean([t1, next_start * factor + t1 * (1 - factor)])
        smoothed.append(
            {
                "text": text if text is not None else "",
                "start": round(t0, 6),
                "end": round(max(t0, t1), 6),
            }
        )

    # enforce strict monotonicity
    for index in range(1, len(smoothed)):
        prev_end = smoothed[index - 1]["end"]
        try:
            prev_end_val = float(prev_end)
        except (TypeError, ValueError):
            prev_end_val = 0.0
        current_start = smoothed[index]["start"]
        try:
            current_start_val = float(current_start)
        except (TypeError, ValueError):
            current_start_val = prev_end_val
        if current_start_val < prev_end_val:
            smoothed[index]["start"] = prev_end_val
            current_end = smoothed[index]["end"]
            try:
                current_end_val = float(current_end)
            except (TypeError, ValueError):
                current_end_val = prev_end_val
            if current_end_val < prev_end_val:
                smoothed[index]["end"] = prev_end_val

    return smoothed


def build_word_events(meta: Mapping[str, Any] | None) -> list[dict[str, float | str]]:
    """
    Build token timeline events from ``meta["word_tokens"]``.

    Expects an iterable of dicts containing ``text``, ``start``, and ``end`` keys.
    Values are rounded to three decimals to keep payloads compact.
    """

    if not isinstance(meta, Mapping):
        return []

    raw_tokens: Sequence[Mapping[str, Any]] | None = meta.get("word_tokens")  # type: ignore[assignment]
    if not isinstance(raw_tokens, Sequence):
        return []

    cleaned: list[dict[str, Any]] = []
    for token in raw_tokens:
        if not isinstance(token, Mapping):
            continue
        text = token.get("text")
        start = token.get("start")
        end = token.get("end")
        if text is None or start is None or end is None:
            continue
        try:
            start_val = float(start)
            end_val = float(end)
        except (TypeError, ValueError):
            continue
        cleaned.append(
            {
                "text": str(text),
                "start": start_val,
                "end": end_val,
            }
        )

    if not cleaned:
        return []

    smoothed = smooth_token_boundaries(cleaned)

    events: list[dict[str, float | str]] = []
    for token in smoothed:
        try:
            t0 = round(float(token["start"]), 3)
            t1 = round(float(token["end"]), 3)
        except (TypeError, ValueError, KeyError):
            continue
        events.append({"token": str(token.get("text", "")), "t0": t0, "t1": t1})
    return events


def compute_char_weighted_timings(
    words: Sequence[str],
    total_duration: float,
    *,
    pause_before_ms: float = 0.0,
    pause_after_ms: float = 0.0,
) -> List[dict[str, float | str]]:
    """
    Derive per-word timings by distributing ``total_duration`` using visible grapheme counts.

    Leading/trailing pauses are preserved so the emitted tokens stay within the sentence gate.
    """

    if not words:
        return []
    normalized_words = [str(word) for word in words if isinstance(word, str) and word.strip()]
    if not normalized_words:
        return []
    total_duration = max(float(total_duration or 0.0), 0.0)
    if total_duration <= 0.0:
        return []

    pause_before = max(float(pause_before_ms or 0.0) / 1000.0, 0.0)
    pause_after = max(float(pause_after_ms or 0.0) / 1000.0, 0.0)
    if pause_before > total_duration:
        pause_before = total_duration
    remaining = max(total_duration - pause_before, 0.0)
    if pause_after > remaining:
        pause_after = remaining
    available_duration = max(total_duration - (pause_before + pause_after), 0.0)

    def _visible_length(word: str) -> int:
        stripped = _VISIBLE_PUNCT_PATTERN.sub("", word)
        length = len(stripped)
        return length if length > 0 else max(len(word.strip()), 1)

    counts = [_visible_length(word) for word in normalized_words]
    total_chars = sum(counts)
    if total_chars <= 0:
        return []

    tokens: List[dict[str, float | str]] = []
    cursor = pause_before
    target_final = max(total_duration - pause_after, pause_before)

    for idx, (word, count) in enumerate(zip(normalized_words, counts)):
        share = available_duration * (count / total_chars) if available_duration > 0 else 0.0
        start = _round_to_precision(min(cursor, total_duration))
        cursor += share
        end = _round_to_precision(min(max(cursor, start), total_duration))
        tokens.append(
            {
                "wordIdx": idx,
                "text": word,
                "word": word,
                "start": start,
                "end": end,
                "policy": "char_weighted",
                "source": "char_weighted_refined",
            }
        )

    if tokens:
        final_end = _round_to_precision(min(max(target_final, tokens[-1]["start"]), total_duration))
        tokens[-1]["end"] = final_end

    return tokens


def validate_timing_monotonic(
    track_tokens: list[dict[str, Any]],
    start_gate: float | None = None,
    end_gate: float | None = None,
    *,
    epsilon: float = 0.02,
) -> dict[str, float]:
    """
    Clamp and validate monotonicity for ``track_tokens``.

    Returns a drift summary while mutating tokens in-place.
    """

    if not track_tokens:
        return {"count": 0, "drift": 0.0}

    sorted_tokens = sorted(
        track_tokens,
        key=lambda token: float(token.get("start", 0.0)),
    )
    last_end = float(sorted_tokens[0].get("start", 0.0))
    for token in sorted_tokens:
        start_val = float(token.get("start", 0.0))
        end_val = float(token.get("end", start_val))
        if start_val < last_end:
            start_val = last_end
        if end_val <= start_val:
            end_val = start_val + _TIMING_PRECISION
        token["start"] = _round_to_precision(start_val)
        token["end"] = _round_to_precision(end_val)
        last_end = end_val

    if start_gate is not None and sorted_tokens:
        offset = start_gate - float(sorted_tokens[0]["start"])
        if abs(offset) > 0:
            for token in sorted_tokens:
                token["start"] = _round_to_precision(float(token["start"]) + offset)
                token["end"] = _round_to_precision(float(token["end"]) + offset)

    drift = 0.0
    if end_gate is not None and sorted_tokens:
        final_end = float(sorted_tokens[-1]["end"])
        drift = abs(final_end - end_gate)
        if drift > epsilon:
            start_base = float(sorted_tokens[0]["start"])
            span = max(final_end - start_base, _TIMING_PRECISION)
            target_span = max(end_gate - start_base, 0.0)
            if span > 0:
                scale = target_span / span
                for token in sorted_tokens:
                    token["start"] = _round_to_precision(start_base + (float(token["start"]) - start_base) * scale)
                    token["end"] = _round_to_precision(start_base + (float(token["end"]) - start_base) * scale)
                drift = 0.0
        sorted_tokens[-1]["end"] = _round_to_precision(end_gate)

    return {"count": len(track_tokens), "drift": round(float(drift), 6)}


def _sanitize_word_tokens(word_tokens: Sequence[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
    """Return cleaned word tokens with numeric boundaries."""

    if not isinstance(word_tokens, Sequence):
        return []

    sanitized: list[dict[str, Any]] = []
    for token in word_tokens:
        if not isinstance(token, Mapping):
            continue
        text = token.get("text") or token.get("word") or ""
        try:
            start = float(token.get("start", 0.0))
            end = float(token.get("end", start))
        except (TypeError, ValueError):
            continue
        if end < start:
            end = start
        sanitized.append(
            {
                "text": str(text),
                "start": max(start, 0.0),
                "end": max(end, 0.0),
            }
        )
    return sanitized


def _fit_tokens_to_duration(
    tokens: Sequence[Mapping[str, Any]],
    target_duration: float,
) -> list[dict[str, Any]]:
    """Project ``tokens`` so they are contiguous within ``target_duration`` seconds."""

    cleaned = _sanitize_word_tokens(tokens)
    if not cleaned:
        return []

    durations: list[tuple[str, float]] = []
    total_duration = 0.0
    for token in cleaned:
        length = max(float(token["end"]) - float(token["start"]), 0.0)
        durations.append((str(token.get("text", "")), length))
        total_duration += length

    if total_duration <= 0:
        total_duration = max(target_duration, 0.0)

    cursor = 0.0
    scale = 1.0
    if target_duration > 0 and total_duration > 0:
        scale = target_duration / total_duration

    projected: list[dict[str, Any]] = []
    for text, span in durations:
        effective = max(span * scale, 0.0)
        start = cursor
        end = start + effective
        projected.append(
            {
                "text": text,
                "start": _round_to_precision(start),
                "end": _round_to_precision(max(end, start)),
            }
        )
        cursor = end

    if target_duration > 0 and projected:
        projected[-1]["end"] = _round_to_precision(target_duration)
    return projected


def _char_weighted_tokens(
    words: Sequence[str],
    duration: float,
    *,
    pause_before_ms: float = 0.0,
    pause_after_ms: float = 0.0,
) -> list[dict[str, Any]]:
    """Convenience wrapper for refined char-weighted fallback timings."""

    filtered = [word for word in words if isinstance(word, str) and word]
    if not filtered:
        return []
    return compute_char_weighted_timings(
        filtered,
        duration,
        pause_before_ms=pause_before_ms,
        pause_after_ms=pause_after_ms,
    )


def _resolve_word_list(
    primary_words: Sequence[str],
    fallback_text: str | None,
) -> list[str]:
    words = [word for word in primary_words if isinstance(word, str) and word.strip()]
    if words:
        return words
    if isinstance(fallback_text, str):
        return split_highlight_tokens(fallback_text)
    return []


def _build_mix_sentence_tokens(spec: SentenceTimingSpec) -> list[dict[str, Any]]:
    """Return mix-lane tokens for a single sentence within its gate."""

    start_gate = float(getattr(spec, "mix_start_gate", spec.start_gate) or 0.0)
    end_gate = float(getattr(spec, "mix_end_gate", spec.end_gate) or start_gate)
    pause_before = max(float(getattr(spec, "pause_before_ms", 0) or 0) / 1000.0, 0.0)

    original_tokens: list[dict[str, Any]] = []
    if spec.original_words:
        original_tokens = _char_weighted_tokens(
            spec.original_words,
            spec.original_duration,
        )
        for token in original_tokens:
            token["lane"] = "orig"
            token["policy"] = token.get("policy") or "char_weighted"
            token["source"] = token.get("source") or "original"
            token["start"] = start_gate + float(token.get("start", 0.0))
            token["end"] = start_gate + float(token.get("end", 0.0))

    translation_source_tokens: list[dict[str, Any]] = []
    if spec.word_tokens:
        for idx, token in enumerate(spec.word_tokens):
            start_val = float(token.get("start", 0.0))
            end_val = float(token.get("end", start_val))
            translation_source_tokens.append(
                {
                    "lane": "trans",
                    "wordIdx": idx,
                    "text": token.get("text", token.get("word", "")),
                    "start": start_val,
                    "end": end_val,
                    "policy": token.get("policy") or spec.policy,
                    "source": token.get("source") or spec.source,
                }
            )
    if not translation_source_tokens and spec.translation_words:
        translation_source_tokens = _char_weighted_tokens(
            spec.translation_words,
            spec.translation_duration,
        )
        for token in translation_source_tokens:
            token["lane"] = "trans"
            token["policy"] = token.get("policy") or "char_weighted"
            token["source"] = token.get("source") or "char_weighted_refined"
            token["fallback"] = True

    translation_offset = start_gate + spec.original_duration + pause_before
    for token in translation_source_tokens:
        token["start"] = translation_offset + float(token.get("start", 0.0))
        token["end"] = translation_offset + float(token.get("end", 0.0))

    sentence_tokens = original_tokens + translation_source_tokens
    for token in sentence_tokens:
        token["sentenceIdx"] = spec.sentence_idx
        token["startGate"] = start_gate
        token["endGate"] = end_gate
        token["start_gate"] = start_gate
        token["end_gate"] = end_gate
        token["pauseBeforeMs"] = getattr(spec, "pause_before_ms", 0) or 0
        token["pauseAfterMs"] = getattr(spec, "pause_after_ms", 0) or 0
        token["pause_before_ms"] = getattr(spec, "pause_before_ms", 0) or 0
        token["pause_after_ms"] = getattr(spec, "pause_after_ms", 0) or 0
        start_val = float(token.get("start", start_gate))
        end_val = float(token.get("end", start_val))
        if start_val < start_gate:
            start_val = start_gate
        if end_val > end_gate:
            end_val = end_gate
        token["start"] = _round_to_precision(start_val)
        token["end"] = _round_to_precision(max(end_val, start_val))

    if sentence_tokens:
        sentence_tokens[-1]["end"] = _round_to_precision(end_gate)
    validate_timing_monotonic(sentence_tokens, start_gate, end_gate)
    return sentence_tokens


def _clamp_track_tokens(
    tokens: list[dict[str, Any]],
    total_duration: float,
) -> list[dict[str, Any]]:
    """Clamp ``tokens`` into ``[0, total_duration]`` while preserving order."""

    if total_duration <= 0 or not tokens:
        return []

    clamped: list[dict[str, Any]] = []
    cursor = 0.0
    for token in tokens:
        start = max(float(token.get("start", 0.0)), 0.0)
        end = max(float(token.get("end", start)), 0.0)
        if start < cursor:
            start = cursor
        if end < start:
            end = start
        if start >= total_duration:
            break
        bounded_end = min(end, total_duration)
        clamped.append(
            {
                **token,
                "start": _round_to_precision(start),
                "end": _round_to_precision(bounded_end),
            }
        )
        cursor = bounded_end
        if cursor >= total_duration:
            break
    if clamped:
        clamped[0]["start"] = 0.0
        clamped[-1]["end"] = _round_to_precision(min(clamped[-1]["end"], total_duration))
    return clamped


def build_dual_track_timings(
    sentences: Sequence[SentenceTimingSpec],
    *,
    mix_duration: float,
    translation_duration: float,
) -> dict[str, list[dict[str, Any]]]:
    """Build MIX + TRANSLATION timing tracks from per-sentence specifications."""

    mix_tokens: list[dict[str, Any]] = []
    translation_tokens: list[dict[str, Any]] = []

    sentence_translation_offsets: dict[int, float] = {}
    sentence_translation_spans: dict[int, float] = {}
    translation_cursor = 0.0
    for spec in sentences:
        sentence_translation_offsets[spec.sentence_idx] = translation_cursor
        sentence_translation_spans[spec.sentence_idx] = max(spec.translation_duration, 0.0)
        translation_cursor += max(spec.translation_duration, 0.0)

    mix_offset = 0.0

    for spec in sentences:
        translation_target = max(spec.translation_duration, 0.0)
        original_target = max(spec.original_duration, 0.0)
        policy = spec.policy.strip() if isinstance(spec.policy, str) else None
        source = spec.source.strip() if isinstance(spec.source, str) else None
        try:
            mix_start_gate = round(max(float(getattr(spec, "mix_start_gate", spec.start_gate) or mix_offset), 0.0), 6)
        except (TypeError, ValueError):
            mix_start_gate = _round_to_precision(mix_offset)
        sentence_mix_total = (
            original_target
            + max(spec.gap_before_translation, 0.0)
            + translation_target
            + max(spec.gap_after_translation, 0.0)
        )
        try:
            mix_end_gate = round(
                max(float(getattr(spec, "mix_end_gate", mix_start_gate + sentence_mix_total)), mix_start_gate),
                6,
            )
        except (TypeError, ValueError):
            mix_end_gate = _round_to_precision(mix_start_gate + sentence_mix_total)
        try:
            pause_before_ms = int(round(float(spec.pause_before_ms)))
        except (TypeError, ValueError):
            pause_before_ms = 0
        if pause_before_ms < 0:
            pause_before_ms = 0
        try:
            pause_after_ms = int(round(float(spec.pause_after_ms)))
        except (TypeError, ValueError):
            pause_after_ms = 0
        if pause_after_ms < 0:
            pause_after_ms = 0

        sentence_translation_tokens = _fit_tokens_to_duration(
            spec.word_tokens or [],
            translation_target,
        )
        fallback_translation = False
        if not sentence_translation_tokens and translation_target > 0:
            fallback_words = _resolve_word_list(spec.translation_words, spec.translation_text)
            sentence_translation_tokens = _char_weighted_tokens(
                fallback_words,
                translation_target,
                pause_before_ms=spec.pause_before_ms,
                pause_after_ms=spec.pause_after_ms,
            )
            fallback_translation = True
            policy = "char_weighted"
            source = "char_weighted_refined"

        if not sentence_translation_tokens:
            sentence_translation_tokens = []

        try:
            gate_start = round(max(float(spec.start_gate), 0.0), 6)
        except (TypeError, ValueError):
            gate_start = _round_to_precision(mix_start_gate + original_target + max(spec.gap_before_translation, 0.0))
        try:
            gate_end = round(max(float(spec.end_gate), gate_start), 6)
        except (TypeError, ValueError):
            gate_end = _round_to_precision(gate_start + translation_target)

        sentence_translation_offset = sentence_translation_offsets.get(spec.sentence_idx, 0.0)
        translation_word_idx = 0
        for token in sentence_translation_tokens:
            start = sentence_translation_offset + float(token.get("start", 0.0))
            end = sentence_translation_offset + float(token.get("end", 0.0))
            translation_tokens.append(
                {
                    "lane": "trans",
                    "sentenceIdx": spec.sentence_idx,
                    "wordIdx": translation_word_idx,
                    "start": _round_to_precision(start),
                    "end": _round_to_precision(end),
                    "text": token.get("text", ""),
                    "policy": policy,
                    "source": source,
                    "start_gate": gate_start,
                    "end_gate": gate_end,
                    "startGate": gate_start,
                    "endGate": gate_end,
                    "pause_before_ms": pause_before_ms,
                    "pause_after_ms": pause_after_ms,
                    "pauseBeforeMs": pause_before_ms,
                    "pauseAfterMs": pause_after_ms,
                }
            )
            translation_word_idx += 1

        spec.mix_start_gate = _round_to_precision(mix_start_gate)
        spec.mix_end_gate = _round_to_precision(mix_end_gate)
        mix_sentence_tokens = _build_mix_sentence_tokens(spec)
        mix_tokens.extend(mix_sentence_tokens)

        mix_offset = mix_end_gate

    mix_track = _clamp_track_tokens(mix_tokens, max(mix_duration, 0.0))
    translation_track = _clamp_track_tokens(translation_tokens, max(translation_duration, 0.0))

    for spec in sentences:
        sentence_idx = spec.sentence_idx
        mix_subset = [token for token in mix_track if token.get("sentenceIdx") == sentence_idx]
        translation_subset = [
            token for token in translation_track if token.get("sentenceIdx") == sentence_idx
        ]
        mix_metrics = validate_timing_monotonic(
            mix_subset,
            start_gate=spec.mix_start_gate,
            end_gate=spec.mix_end_gate,
        )
        translation_start_offset = sentence_translation_offsets.get(sentence_idx, 0.0)
        translation_span = sentence_translation_spans.get(sentence_idx, 0.0)
        translation_metrics = validate_timing_monotonic(
            translation_subset,
            start_gate=translation_start_offset,
            end_gate=translation_start_offset + translation_span,
        )
        spec.validation_metrics = {
            "mix": mix_metrics,
            "translation": translation_metrics,
        }
        for token in mix_subset:
            token["validation"] = mix_metrics
        for token in translation_subset:
            token["validation"] = translation_metrics

    return {
        "mix": mix_track,
        "translation": translation_track,
    }


def build_separate_track_timings(
    sentences: Sequence[SentenceTimingSpec],
    *,
    original_duration: float,
    translation_duration: float,
) -> dict[str, list[dict[str, Any]]]:
    """Build ORIGINAL + TRANSLATION timing tracks from per-sentence specifications."""

    original_tokens: list[dict[str, Any]] = []
    translation_tokens: list[dict[str, Any]] = []

    sentence_original_offsets: dict[int, float] = {}
    sentence_original_spans: dict[int, float] = {}
    sentence_translation_offsets: dict[int, float] = {}
    sentence_translation_spans: dict[int, float] = {}

    original_cursor = 0.0
    translation_cursor = 0.0
    for spec in sentences:
        original_span = max(spec.original_duration, 0.0)
        translation_span = max(spec.translation_duration, 0.0)
        sentence_original_offsets[spec.sentence_idx] = original_cursor
        sentence_original_spans[spec.sentence_idx] = original_span
        sentence_translation_offsets[spec.sentence_idx] = translation_cursor
        sentence_translation_spans[spec.sentence_idx] = translation_span
        original_cursor += original_span
        translation_cursor += translation_span

    for spec in sentences:
        translation_target = max(spec.translation_duration, 0.0)
        original_target = max(spec.original_duration, 0.0)

        translation_policy = spec.policy.strip() if isinstance(spec.policy, str) else None
        translation_source = spec.source.strip() if isinstance(spec.source, str) else None
        original_policy = (
            spec.original_policy.strip() if isinstance(spec.original_policy, str) else None
        )
        original_source = (
            spec.original_source.strip() if isinstance(spec.original_source, str) else None
        )

        try:
            pause_before_ms = int(round(float(spec.pause_before_ms)))
        except (TypeError, ValueError):
            pause_before_ms = 0
        if pause_before_ms < 0:
            pause_before_ms = 0
        try:
            pause_after_ms = int(round(float(spec.pause_after_ms)))
        except (TypeError, ValueError):
            pause_after_ms = 0
        if pause_after_ms < 0:
            pause_after_ms = 0

        try:
            original_pause_before_ms = int(round(float(spec.original_pause_before_ms)))
        except (TypeError, ValueError):
            original_pause_before_ms = 0
        if original_pause_before_ms < 0:
            original_pause_before_ms = 0
        try:
            original_pause_after_ms = int(round(float(spec.original_pause_after_ms)))
        except (TypeError, ValueError):
            original_pause_after_ms = 0
        if original_pause_after_ms < 0:
            original_pause_after_ms = 0

        translation_source_tokens = _fit_tokens_to_duration(
            spec.word_tokens or [], translation_target
        )
        if not translation_source_tokens and translation_target > 0:
            fallback_words = _resolve_word_list(spec.translation_words, spec.translation_text)
            translation_source_tokens = _char_weighted_tokens(
                fallback_words,
                translation_target,
                pause_before_ms=pause_before_ms,
                pause_after_ms=pause_after_ms,
            )
            translation_policy = "char_weighted"
            translation_source = "char_weighted_refined"

        original_source_tokens = _fit_tokens_to_duration(
            spec.original_word_tokens or [], original_target
        )
        if not original_source_tokens and original_target > 0:
            fallback_words = _resolve_word_list(spec.original_words, spec.original_text)
            original_source_tokens = _char_weighted_tokens(
                fallback_words,
                original_target,
                pause_before_ms=original_pause_before_ms,
                pause_after_ms=original_pause_after_ms,
            )
            original_policy = original_policy or "char_weighted"
            original_source = original_source or "char_weighted_refined"

        translation_start_gate = sentence_translation_offsets.get(spec.sentence_idx, 0.0)
        translation_end_gate = translation_start_gate + translation_target
        translation_word_idx = 0
        for token in translation_source_tokens:
            start = translation_start_gate + float(token.get("start", 0.0))
            end = translation_start_gate + float(token.get("end", start))
            translation_tokens.append(
                {
                    "lane": "trans",
                    "sentenceIdx": spec.sentence_idx,
                    "wordIdx": translation_word_idx,
                    "start": _round_to_precision(start),
                    "end": _round_to_precision(end),
                    "text": token.get("text", token.get("word", "")),
                    "policy": token.get("policy") or translation_policy,
                    "source": token.get("source") or translation_source,
                    "start_gate": translation_start_gate,
                    "end_gate": translation_end_gate,
                    "startGate": translation_start_gate,
                    "endGate": translation_end_gate,
                    "pause_before_ms": pause_before_ms,
                    "pause_after_ms": pause_after_ms,
                    "pauseBeforeMs": pause_before_ms,
                    "pauseAfterMs": pause_after_ms,
                }
            )
            translation_word_idx += 1

        original_start_gate = sentence_original_offsets.get(spec.sentence_idx, 0.0)
        original_end_gate = original_start_gate + original_target
        original_word_idx = 0
        for token in original_source_tokens:
            start = original_start_gate + float(token.get("start", 0.0))
            end = original_start_gate + float(token.get("end", start))
            original_tokens.append(
                {
                    "lane": "orig",
                    "sentenceIdx": spec.sentence_idx,
                    "wordIdx": original_word_idx,
                    "start": _round_to_precision(start),
                    "end": _round_to_precision(end),
                    "text": token.get("text", token.get("word", "")),
                    "policy": token.get("policy") or original_policy,
                    "source": token.get("source") or original_source,
                    "start_gate": original_start_gate,
                    "end_gate": original_end_gate,
                    "startGate": original_start_gate,
                    "endGate": original_end_gate,
                    "pause_before_ms": original_pause_before_ms,
                    "pause_after_ms": original_pause_after_ms,
                    "pauseBeforeMs": original_pause_before_ms,
                    "pauseAfterMs": original_pause_after_ms,
                }
            )
            original_word_idx += 1

    original_track = _clamp_track_tokens(
        original_tokens, max(original_duration, 0.0)
    )
    translation_track = _clamp_track_tokens(
        translation_tokens, max(translation_duration, 0.0)
    )

    for spec in sentences:
        sentence_idx = spec.sentence_idx
        original_subset = [token for token in original_track if token.get("sentenceIdx") == sentence_idx]
        translation_subset = [token for token in translation_track if token.get("sentenceIdx") == sentence_idx]
        original_start_offset = sentence_original_offsets.get(sentence_idx, 0.0)
        original_span = sentence_original_spans.get(sentence_idx, 0.0)
        translation_start_offset = sentence_translation_offsets.get(sentence_idx, 0.0)
        translation_span = sentence_translation_spans.get(sentence_idx, 0.0)
        original_metrics = validate_timing_monotonic(
            original_subset,
            start_gate=original_start_offset,
            end_gate=original_start_offset + original_span,
        )
        translation_metrics = validate_timing_monotonic(
            translation_subset,
            start_gate=translation_start_offset,
            end_gate=translation_start_offset + translation_span,
        )
        spec.validation_metrics = {
            "original": original_metrics,
            "translation": translation_metrics,
        }
        for token in original_subset:
            token["validation"] = original_metrics
        for token in translation_subset:
            token["validation"] = translation_metrics

    return {
        "original": original_track,
        "translation": translation_track,
    }


__all__ = [
    "SentenceTimingSpec",
    "build_dual_track_timings",
    "build_separate_track_timings",
    "build_word_events",
    "smooth_token_boundaries",
    "compute_char_weighted_timings",
    "validate_timing_monotonic",
]
