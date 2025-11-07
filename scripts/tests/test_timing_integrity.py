"""Regression tests for word timing integrity."""

from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.core.rendering.timeline import (
    build_word_events,
    smooth_token_boundaries,
    compute_char_weighted_timings,
)


def _make_sample_tokens() -> list[dict[str, float | str]]:
    return [
        {"text": "Hello", "start": 0.0, "end": 0.42},
        {"text": "there", "start": 0.4, "end": 0.78},
        {"text": "friend", "start": 0.75, "end": 1.23},
    ]


def _build_uniform_tokens(text: str, duration: float) -> list[dict[str, float | str]]:
    words = [word for word in text.split() if word]
    if not words:
        return []
    slice_duration = max(duration, 0.0) / len(words)
    cursor = 0.0
    tokens: list[dict[str, float | str]] = []
    for index, word in enumerate(words):
        start = cursor
        end = duration if index == len(words) - 1 else cursor + slice_duration
        start = round(max(start, 0.0), 3)
        end = round(max(end, start), 3)
        tokens.append({"text": word, "start": start, "end": end})
        cursor = end
    return tokens


def _drift_ms(tokens: list[dict[str, float | str]]) -> float:
    if not tokens:
        return 0.0
    start = float(tokens[0]["start"])
    end = float(tokens[-1]["end"])
    expected = max(end - start, 0.0)
    actual = 0.0
    for token in tokens:
        span = float(token["end"]) - float(token["start"])
        actual += max(span, 0.0)
    return abs(actual - expected) * 1000.0


def test_smooth_tokens_are_monotonic_and_contiguous() -> None:
    tokens = _make_sample_tokens()
    smoothed = smooth_token_boundaries(tokens, smoothing=0.35)
    assert smoothed, "Expected smoothing to yield tokens"

    prev_end = 0.0
    for index, token in enumerate(smoothed):
        start = float(token["start"])
        end = float(token["end"])
        assert start >= prev_end - 0.0001, "Token start regressed"
        assert end >= start, "Token end precedes start"
        if index > 0:
            # Allow at most 5ms gap to absorb rounding errors.
            assert math.isclose(start, prev_end, abs_tol=0.005), "Gap exceeds 5ms"
        prev_end = end


def test_build_word_events_stays_within_duration_budget() -> None:
    tokens = _make_sample_tokens()
    meta = {
        "sentence_number": 1,
        "text": "Hello there friend",
        "t0": 0.0,
        "t1": 1.235,
        "word_tokens": tokens,
    }
    events = build_word_events(meta)
    assert events, "Expected events from metadata"
    total_duration = sum(float(event["t1"]) - float(event["t0"]) for event in events)
    sentence_duration = float(meta["t1"]) - float(meta["t0"])
    # Allow up to 10ms deviation due to rounding.
    assert math.isclose(total_duration, sentence_duration, abs_tol=0.01)


def test_char_weighted_timings_are_monotonic_and_precise() -> None:
    sentence_text = "Weighted timing fallback ensures contiguous estimates"
    requested_duration = 2.137
    tokens = compute_char_weighted_timings(sentence_text, requested_duration)
    assert tokens, "Expected char-weighted helper to return tokens"
    words = [word for word in sentence_text.split() if word]
    assert len(tokens) == len(words)

    prev_end = 0.0
    for token in tokens:
        start = float(token["start"])
        end = float(token["end"])
        assert start >= prev_end - 0.0001, "Start regressed"
        assert math.isclose(start, prev_end, abs_tol=0.005), "Non-contiguous interval"
        assert end >= start, "End precedes start"
        prev_end = end

    assert math.isclose(prev_end, requested_duration, abs_tol=0.005)


def test_policy_drift_thresholds() -> None:
    base_text = "Testing highlight drift expectations across policies"
    forced_tokens = smooth_token_boundaries(_make_sample_tokens())
    forced_drift = _drift_ms(forced_tokens)

    estimated_tokens = compute_char_weighted_timings(
        base_text,
        3.276,
        punctuation_boost=True,
    )
    estimated_drift = _drift_ms(estimated_tokens)

    inferred_tokens = _build_uniform_tokens(base_text, 3.276)
    inferred_drift = _drift_ms(inferred_tokens)

    summary = [
        ("forced", forced_drift),
        ("estimated_punct", estimated_drift),
        ("inferred", inferred_drift),
    ]
    print("\nHighlight drift summary (ms):")
    for label, value in summary:
        print(f"{label:<16}{value:>8.3f}")

    assert forced_drift < 10.0
    assert estimated_drift < 50.0
    assert inferred_drift < 80.0
