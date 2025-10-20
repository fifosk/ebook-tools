"""Heuristic forced-alignment utilities for synthesized audio."""

from __future__ import annotations

from bisect import bisect_right
from typing import List, MutableMapping, Sequence

import regex

from pydub import AudioSegment


def _monotone_cubic_interpolate(
    x_values: Sequence[float],
    y_values: Sequence[float],
    targets: Sequence[float],
) -> List[float]:
    """Evaluate a monotone cubic Hermite spline defined by ``x_values``/``y_values``."""

    if not x_values or not y_values or len(x_values) != len(y_values):
        return [0.0 for _ in targets]

    count = len(x_values)
    if count == 1:
        return [y_values[0] for _ in targets]

    deltas = []
    for i in range(count - 1):
        span = x_values[i + 1] - x_values[i]
        if span <= 0:
            deltas.append(0.0)
            continue
        deltas.append((y_values[i + 1] - y_values[i]) / span)

    slopes = [0.0] * count
    slopes[0] = deltas[0]
    slopes[-1] = deltas[-1]
    for i in range(1, count - 1):
        prev_delta = deltas[i - 1]
        next_delta = deltas[i]
        if prev_delta == 0.0 or next_delta == 0.0 or prev_delta * next_delta < 0.0:
            slopes[i] = 0.0
            continue
        w1 = 2 * (x_values[i + 1] - x_values[i]) + (x_values[i] - x_values[i - 1])
        w2 = (x_values[i + 1] - x_values[i]) + 2 * (x_values[i] - x_values[i - 1])
        denominator = (w1 / prev_delta) + (w2 / next_delta)
        if denominator == 0.0:
            slopes[i] = 0.0
        else:
            slopes[i] = (w1 + w2) / denominator

    results: List[float] = []
    for target in targets:
        if target <= x_values[0]:
            results.append(y_values[0])
            continue
        if target >= x_values[-1]:
            results.append(y_values[-1])
            continue
        idx = bisect_right(x_values, target) - 1
        idx = min(max(idx, 0), count - 2)
        span = x_values[idx + 1] - x_values[idx]
        if span <= 0:
            results.append(y_values[idx])
            continue
        s = (target - x_values[idx]) / span
        s2 = s * s
        s3 = s2 * s
        h00 = 2 * s3 - 3 * s2 + 1
        h10 = s3 - 2 * s2 + s
        h01 = -2 * s3 + 3 * s2
        h11 = s3 - s2
        value = (
            h00 * y_values[idx]
            + h10 * span * slopes[idx]
            + h01 * y_values[idx + 1]
            + h11 * span * slopes[idx + 1]
        )
        results.append(value)

    adjusted: List[float] = []
    floor = y_values[0]
    ceiling = y_values[-1]
    for value in results:
        clamped = min(max(value, floor), ceiling)
        if adjusted:
            clamped = max(clamped, adjusted[-1])
        adjusted.append(clamped)
    return adjusted


def align_characters(
    segment: AudioSegment,
    text: str,
    *,
    smoothing: str = "monotonic_cubic",
) -> List[MutableMapping[str, float]]:
    """Generate per-character timings for ``text`` using ``segment`` duration."""

    duration_ms = float(len(segment) or 0)
    if duration_ms <= 0 or not text:
        return []

    grapheme_matches = list(regex.finditer(r"\X", text))
    if not grapheme_matches:
        return []

    words: List[List[int]] = []
    current_word: List[int] = []
    for idx, match in enumerate(grapheme_matches):
        grapheme = match.group()
        if grapheme.isspace():
            if current_word:
                words.append(current_word)
                current_word = []
            continue
        current_word.append(idx)
    if current_word:
        words.append(current_word)

    non_space_indices = [idx for word in words for idx in word]
    if not non_space_indices:
        return []

    word_lengths = [len(word) for word in words]
    total_weight = float(sum(word_lengths)) or 1.0
    word_durations = [duration_ms * (length / total_weight) for length in word_lengths]

    boundary_positions: List[float] = [0.0]
    boundary_times: List[float] = [0.0]
    cumulative_positions = 0.0
    cumulative_time = 0.0
    for length, duration in zip(word_lengths, word_durations):
        cumulative_positions += float(length)
        cumulative_time += duration
        boundary_positions.append(cumulative_positions)
        boundary_times.append(cumulative_time)

    target_positions = [0.0]
    for offset in range(1, len(non_space_indices) + 1):
        target_positions.append(float(offset))

    if smoothing.lower() == "monotonic_cubic":
        cumulative_times = _monotone_cubic_interpolate(
            boundary_positions, boundary_times, target_positions
        )
    else:
        # Linear fallback.
        cumulative_times = []
        for target in target_positions:
            if target <= boundary_positions[0]:
                cumulative_times.append(boundary_times[0])
            elif target >= boundary_positions[-1]:
                cumulative_times.append(boundary_times[-1])
            else:
                idx = bisect_right(boundary_positions, target) - 1
                idx = min(max(idx, 0), len(boundary_positions) - 2)
                span = boundary_positions[idx + 1] - boundary_positions[idx]
                if span <= 0:
                    cumulative_times.append(boundary_times[idx])
                else:
                    ratio = (target - boundary_positions[idx]) / span
                    value = boundary_times[idx] + ratio * (
                        boundary_times[idx + 1] - boundary_times[idx]
                    )
                    cumulative_times.append(value)

    if cumulative_times:
        cumulative_times[-1] = duration_ms

    char_timings: List[MutableMapping[str, float]] = [
        {"char": ch, "start_ms": 0.0, "duration_ms": 0.0}
        for ch in text
    ]

    position_lookup = {index: pos for pos, index in enumerate(non_space_indices, start=1)}

    for idx, match in enumerate(grapheme_matches):
        start = match.start()
        end = match.end()
        if idx not in position_lookup:
            continue
        pos = position_lookup[idx]
        start_time = cumulative_times[pos - 1]
        end_time = cumulative_times[pos]
        duration = max(end_time - start_time, 0.0)
        for char_index in range(start, end):
            char_timings[char_index] = {
                "char": text[char_index],
                "start_ms": float(start_time),
                "duration_ms": float(duration),
            }

    last_time = 0.0
    for entry in char_timings:
        start_time = float(entry.get("start_ms", 0.0))
        duration = float(entry.get("duration_ms", 0.0))
        if duration == 0.0:
            entry["start_ms"] = last_time
        else:
            last_time = max(last_time, start_time + duration)

    return char_timings


__all__ = ["align_characters"]

