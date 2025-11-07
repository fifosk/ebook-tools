"""Lightweight helpers shared by rendering metadata builders."""

from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import fmean
from typing import Any, Mapping, Sequence, List, Optional


_TIMING_PRECISION = 0.003  # 3 ms precision
_PAUSE_PUNCTUATION = {",", ";", "،", "؛"}
_FINAL_PUNCTUATION = {".", "!", "?", "؟", "…", "！", "？", "。"}
_TRAILING_WRAPPERS = {'"', "'", "”", "’", "）", ")", "]", "}", "›", "»"}


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
    sentence_text: str,
    duration: float,
    *,
    punctuation_boost: bool = False,
) -> List[dict[str, float | str]]:
    """
    Derive per-word timings by distributing ``duration`` using character weights.

    Words inherit a share of the total duration proportional to their character count,
    rounded to 3ms increments, and emit contiguous monotonic intervals.
    """

    if not sentence_text:
        return []
    words = [word for word in sentence_text.split() if word]
    if not words:
        return []
    total_duration = max(float(duration or 0.0), 0.0)
    if total_duration <= 0.0:
        return []

    def _classified_multiplier(word: str, is_last: bool) -> float:
        if not punctuation_boost:
            return 1.0
        trimmed = word.strip()
        while trimmed and trimmed[-1] in _TRAILING_WRAPPERS:
            trimmed = trimmed[:-1]
        if not trimmed:
            return 1.0
        last_char = trimmed[-1]
        if last_char in _FINAL_PUNCTUATION or (is_last and last_char in {"-", "–", "—"}):
            return 1.5
        if last_char in _PAUSE_PUNCTUATION:
            return 1.2
        return 1.0

    weighted_chars: list[float] = []
    total_weight = 0.0
    for idx, word in enumerate(words):
        base = max(len(word), 1)
        multiplier = _classified_multiplier(word, idx == len(words) - 1)
        weight = base * multiplier
        weighted_chars.append(weight)
        total_weight += weight

    if total_weight <= 0:
        return []

    total_increments = max(1, int(round(total_duration / _TIMING_PRECISION)))
    target_duration = total_increments * _TIMING_PRECISION

    raw_shares = [
        (weight / total_weight) * total_increments if total_weight else 0.0
        for weight in weighted_chars
    ]
    increments = [int(math.floor(share)) for share in raw_shares]
    remainder = total_increments - sum(increments)

    if remainder != 0:
        fractional_parts = [
            (share - math.floor(share), index) for index, share in enumerate(raw_shares)
        ]
        if remainder > 0:
            fractional_parts.sort(reverse=True)
            idx = 0
            while remainder > 0 and fractional_parts:
                _, word_index = fractional_parts[idx % len(fractional_parts)]
                increments[word_index] += 1
                remainder -= 1
                idx += 1
        else:
            fractional_parts.sort()
            idx = 0
            needed = abs(remainder)
            safeguard = len(fractional_parts) * 2
            while needed > 0 and fractional_parts and safeguard > 0:
                _, word_index = fractional_parts[idx % len(fractional_parts)]
                if increments[word_index] > 0:
                    increments[word_index] -= 1
                    needed -= 1
                idx += 1
                safeguard -= 1

    cursor = 0.0
    tokens: List[dict[str, float | str]] = []
    for word, inc in zip(words, increments):
        segment_duration = max(inc, 0) * _TIMING_PRECISION
        end = cursor + segment_duration
        start = _round_to_precision(cursor)
        end = _round_to_precision(max(end, start))
        tokens.append(
            {
                "text": word,
                "word": word,
                "start": start,
                "end": end,
            }
        )
        cursor = end

    if tokens:
        tokens[-1]["end"] = _round_to_precision(target_duration)
        for index in range(1, len(tokens)):
            prev_end = float(tokens[index - 1]["end"])
            tokens[index]["start"] = _round_to_precision(prev_end)
            if float(tokens[index]["end"]) < prev_end:
                tokens[index]["end"] = _round_to_precision(prev_end)

    return tokens


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
    text: str,
    duration: float,
    *,
    punctuation_boost: bool,
) -> list[dict[str, Any]]:
    """Convenience wrapper for char-weighted fallback timings."""

    return compute_char_weighted_timings(
        sentence_text=text,
        duration=duration,
        punctuation_boost=punctuation_boost,
    )


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

    mix_offset = 0.0
    translation_offset = 0.0

    for spec in sentences:
        translation_target = max(spec.translation_duration, 0.0)
        original_target = max(spec.original_duration, 0.0)
        policy = spec.policy.strip() if isinstance(spec.policy, str) else None
        source = spec.source.strip() if isinstance(spec.source, str) else None

        sentence_translation_tokens = _fit_tokens_to_duration(
            spec.word_tokens or [],
            translation_target,
        )
        fallback_translation = False
        if not sentence_translation_tokens and translation_target > 0:
            sentence_translation_tokens = _char_weighted_tokens(
                spec.translation_text or " ".join(spec.translation_words),
                translation_target,
                punctuation_boost=spec.punctuation_boost,
            )
            fallback_translation = True
            policy = "char_weighted"
            source = "char_weighted"

        if not sentence_translation_tokens:
            sentence_translation_tokens = []

        translation_word_idx = 0
        for token in sentence_translation_tokens:
            start = translation_offset + float(token["start"])
            end = translation_offset + float(token["end"])
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
                }
            )
            translation_word_idx += 1

        mix_sentence_offset = mix_offset
        if original_target > 0 and spec.original_words:
            original_tokens = _char_weighted_tokens(
                spec.original_text or " ".join(spec.original_words),
                original_target,
                punctuation_boost=spec.punctuation_boost,
            )
            for idx, token in enumerate(original_tokens):
                start = mix_sentence_offset + float(token["start"])
                end = mix_sentence_offset + float(token["end"])
                mix_tokens.append(
                    {
                        "lane": "orig",
                        "sentenceIdx": spec.sentence_idx,
                        "wordIdx": idx,
                        "start": _round_to_precision(start),
                        "end": _round_to_precision(end),
                        "text": token.get("text", ""),
                        "policy": "char_weighted",
                        "source": "original",
                    }
                )

        translation_lane_offset = (
            mix_sentence_offset + original_target + max(spec.gap_before_translation, 0.0)
        )
        for idx, token in enumerate(sentence_translation_tokens):
            start = translation_lane_offset + float(token["start"])
            end = translation_lane_offset + float(token["end"])
            mix_tokens.append(
                {
                    "lane": "trans",
                    "sentenceIdx": spec.sentence_idx,
                    "wordIdx": idx,
                    "start": _round_to_precision(start),
                    "end": _round_to_precision(end),
                    "text": token.get("text", ""),
                    "policy": policy,
                    "source": source,
                    "fallback": fallback_translation,
                }
            )

        translation_offset += translation_target
        mix_offset += (
            original_target
            + max(spec.gap_before_translation, 0.0)
            + translation_target
            + max(spec.gap_after_translation, 0.0)
        )

    mix_track = _clamp_track_tokens(mix_tokens, max(mix_duration, 0.0))
    translation_track = _clamp_track_tokens(translation_tokens, max(translation_duration, 0.0))
    return {
        "mix": mix_track,
        "translation": translation_track,
    }


__all__ = [
    "SentenceTimingSpec",
    "build_dual_track_timings",
    "build_word_events",
    "smooth_token_boundaries",
    "compute_char_weighted_timings",
]
