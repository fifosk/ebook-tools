"""Integration tests for multi-sentence chunk support.

These tests verify that word-level timing remains synchronized with audio
when multiple sentences are combined into a single chunk file.
"""

from __future__ import annotations

from typing import Any, Dict, List

import pytest

from modules.core.rendering.timeline import (
    SentenceTimingSpec,
    build_separate_track_timings,
    validate_timing_monotonic,
    validate_cross_sentence_continuity,
    validate_chunk_timing_alignment,
    compute_cumulative_offsets,
    scale_timing_to_audio_duration,
)

pytestmark = pytest.mark.pipeline


def _make_sentence_spec(
    sentence_idx: int,
    original_text: str,
    translation_text: str,
    original_duration: float,
    translation_duration: float,
    word_tokens: List[Dict[str, Any]] | None = None,
    original_word_tokens: List[Dict[str, Any]] | None = None,
    start_gate: float = 0.0,
    end_gate: float | None = None,
    original_start_gate: float = 0.0,
    original_end_gate: float | None = None,
) -> SentenceTimingSpec:
    """Helper to create a SentenceTimingSpec with sensible defaults."""
    original_words = original_text.split() if original_text else []
    translation_words = translation_text.split() if translation_text else []

    if end_gate is None:
        end_gate = start_gate + translation_duration
    if original_end_gate is None:
        original_end_gate = original_start_gate + original_duration

    return SentenceTimingSpec(
        sentence_idx=sentence_idx,
        original_text=original_text,
        translation_text=translation_text,
        original_words=original_words,
        translation_words=translation_words,
        word_tokens=word_tokens,
        original_word_tokens=original_word_tokens,
        translation_duration=translation_duration,
        original_duration=original_duration,
        gap_before_translation=0.0,
        gap_after_translation=0.0,
        char_weighted_enabled=True,
        punctuation_boost=False,
        policy="char_weighted",
        source="char_weighted_refined",
        original_policy="char_weighted",
        original_source="char_weighted_refined",
        start_gate=start_gate,
        end_gate=end_gate,
        original_start_gate=original_start_gate,
        original_end_gate=original_end_gate,
        pause_before_ms=0.0,
        pause_after_ms=0.0,
        original_pause_before_ms=0.0,
        original_pause_after_ms=0.0,
    )


def _generate_word_tokens(
    text: str,
    duration: float,
    offset: float = 0.0,
) -> List[Dict[str, Any]]:
    """Generate evenly distributed word tokens for a sentence."""
    words = text.split()
    if not words:
        return []

    per_word = duration / len(words)
    tokens = []
    cursor = offset

    for idx, word in enumerate(words):
        tokens.append({
            "text": word,
            "word": word,
            "wordIdx": idx,
            "start": round(cursor, 6),
            "end": round(cursor + per_word, 6),
        })
        cursor += per_word

    return tokens


class TestMultiSentenceTimingContinuity:
    """Tests verifying timing continuity across sentence boundaries."""

    def test_two_sentence_timing_is_contiguous(self) -> None:
        """Two sentences should have contiguous timing with no gaps."""
        specs = [
            _make_sentence_spec(
                sentence_idx=0,
                original_text="Hello world",
                translation_text="Bonjour monde",
                original_duration=1.0,
                translation_duration=1.2,
                start_gate=0.0,
                end_gate=1.2,
                original_start_gate=0.0,
                original_end_gate=1.0,
            ),
            _make_sentence_spec(
                sentence_idx=1,
                original_text="How are you",
                translation_text="Comment allez vous",
                original_duration=1.5,
                translation_duration=1.8,
                start_gate=1.2,
                end_gate=3.0,
                original_start_gate=1.0,
                original_end_gate=2.5,
            ),
        ]

        total_original = sum(s.original_duration for s in specs)
        total_translation = sum(s.translation_duration for s in specs)

        tracks = build_separate_track_timings(
            specs,
            original_duration=total_original,
            translation_duration=total_translation,
        )

        trans_tokens = tracks["translation"]
        orig_tokens = tracks["original"]

        # Verify no gaps between sentences in translation track
        assert len(trans_tokens) > 0
        sentence_0_trans = [t for t in trans_tokens if t["sentenceIdx"] == 0]
        sentence_1_trans = [t for t in trans_tokens if t["sentenceIdx"] == 1]

        assert len(sentence_0_trans) > 0
        assert len(sentence_1_trans) > 0

        # Last token of sentence 0 should end where sentence 1 starts
        last_s0_end = max(t["end"] for t in sentence_0_trans)
        first_s1_start = min(t["start"] for t in sentence_1_trans)

        gap_ms = abs(first_s1_start - last_s0_end) * 1000
        assert gap_ms < 10, f"Gap between sentences: {gap_ms}ms"

    def test_ten_sentence_chunk_has_no_drift(self) -> None:
        """Ten sentences combined should maintain timing accuracy."""
        specs = []
        sentences = [
            ("Hello world", "Bonjour monde", 0.8, 1.0),
            ("This is a test", "Ceci est un test", 1.2, 1.4),
            ("How are you today", "Comment allez vous", 1.0, 1.3),
            ("I am fine thank you", "Je vais bien merci", 1.1, 1.5),
            ("The weather is nice", "Il fait beau", 1.0, 0.9),
            ("Let us go outside", "Allons dehors", 0.9, 1.0),
            ("What time is it", "Quelle heure est il", 0.8, 1.1),
            ("It is three oclock", "Il est trois heures", 1.0, 1.2),
            ("See you tomorrow", "A demain", 0.7, 0.8),
            ("Goodbye my friend", "Au revoir mon ami", 0.9, 1.1),
        ]

        trans_cursor = 0.0
        orig_cursor = 0.0

        for idx, (orig, trans, orig_dur, trans_dur) in enumerate(sentences):
            specs.append(_make_sentence_spec(
                sentence_idx=idx,
                original_text=orig,
                translation_text=trans,
                original_duration=orig_dur,
                translation_duration=trans_dur,
                start_gate=trans_cursor,
                end_gate=trans_cursor + trans_dur,
                original_start_gate=orig_cursor,
                original_end_gate=orig_cursor + orig_dur,
            ))
            trans_cursor += trans_dur
            orig_cursor += orig_dur

        total_original = sum(s.original_duration for s in specs)
        total_translation = sum(s.translation_duration for s in specs)

        tracks = build_separate_track_timings(
            specs,
            original_duration=total_original,
            translation_duration=total_translation,
        )

        trans_tokens = tracks["translation"]
        orig_tokens = tracks["original"]

        # Verify timing covers full duration
        assert len(trans_tokens) > 0
        first_trans_start = min(t["start"] for t in trans_tokens)
        last_trans_end = max(t["end"] for t in trans_tokens)

        assert first_trans_start == pytest.approx(0.0, abs=0.01)
        drift_ms = abs(last_trans_end - total_translation) * 1000
        assert drift_ms < 50, f"End drift: {drift_ms}ms (expected {total_translation}, got {last_trans_end})"

        # Verify each sentence has tokens
        for idx in range(10):
            sentence_tokens = [t for t in trans_tokens if t["sentenceIdx"] == idx]
            assert len(sentence_tokens) > 0, f"Sentence {idx} has no tokens"

    def test_timing_monotonicity_across_sentences(self) -> None:
        """Timing should be strictly monotonic across all sentences."""
        specs = [
            _make_sentence_spec(
                sentence_idx=i,
                original_text=f"Sentence {i} original",
                translation_text=f"Sentence {i} translation",
                original_duration=1.0 + i * 0.1,
                translation_duration=1.2 + i * 0.1,
                start_gate=sum(1.2 + j * 0.1 for j in range(i)),
                original_start_gate=sum(1.0 + j * 0.1 for j in range(i)),
            )
            for i in range(5)
        ]

        # Recalculate end gates
        trans_cursor = 0.0
        orig_cursor = 0.0
        for spec in specs:
            spec.start_gate = trans_cursor
            spec.end_gate = trans_cursor + spec.translation_duration
            spec.original_start_gate = orig_cursor
            spec.original_end_gate = orig_cursor + spec.original_duration
            trans_cursor = spec.end_gate
            orig_cursor = spec.original_end_gate

        total_original = sum(s.original_duration for s in specs)
        total_translation = sum(s.translation_duration for s in specs)

        tracks = build_separate_track_timings(
            specs,
            original_duration=total_original,
            translation_duration=total_translation,
        )

        # Sort tokens by start time and verify monotonicity
        trans_sorted = sorted(tracks["translation"], key=lambda t: t["start"])

        last_end = 0.0
        for i, token in enumerate(trans_sorted):
            assert token["start"] >= last_end - 0.001, (
                f"Token {i} starts at {token['start']} but previous ended at {last_end}"
            )
            assert token["end"] >= token["start"], (
                f"Token {i} has end ({token['end']}) before start ({token['start']})"
            )
            last_end = token["end"]


class TestMultiSentenceWithWordTokens:
    """Tests with explicit word tokens (from forced alignment)."""

    def test_preserves_word_token_timing_with_offset(self) -> None:
        """Word tokens from forced alignment should be offset correctly."""
        # Sentence 0: tokens at 0.0-0.5, 0.5-1.0
        # Sentence 1: tokens at 0.0-0.6, 0.6-1.2 (should become 1.0-1.6, 1.6-2.2)
        specs = [
            _make_sentence_spec(
                sentence_idx=0,
                original_text="Hello world",
                translation_text="Bonjour monde",
                original_duration=1.0,
                translation_duration=1.0,
                word_tokens=[
                    {"text": "Bonjour", "start": 0.0, "end": 0.5},
                    {"text": "monde", "start": 0.5, "end": 1.0},
                ],
                start_gate=0.0,
                end_gate=1.0,
                original_start_gate=0.0,
                original_end_gate=1.0,
            ),
            _make_sentence_spec(
                sentence_idx=1,
                original_text="How are you",
                translation_text="Comment vas tu",
                original_duration=1.2,
                translation_duration=1.2,
                word_tokens=[
                    {"text": "Comment", "start": 0.0, "end": 0.4},
                    {"text": "vas", "start": 0.4, "end": 0.7},
                    {"text": "tu", "start": 0.7, "end": 1.2},
                ],
                start_gate=1.0,
                end_gate=2.2,
                original_start_gate=1.0,
                original_end_gate=2.2,
            ),
        ]

        tracks = build_separate_track_timings(
            specs,
            original_duration=2.2,
            translation_duration=2.2,
        )

        trans_tokens = tracks["translation"]

        # Sentence 0 tokens should be at original positions
        s0_tokens = [t for t in trans_tokens if t["sentenceIdx"] == 0]
        assert len(s0_tokens) == 2
        assert s0_tokens[0]["start"] == pytest.approx(0.0, abs=0.01)
        assert s0_tokens[1]["end"] == pytest.approx(1.0, abs=0.01)

        # Sentence 1 tokens should be offset by sentence 0's duration
        s1_tokens = [t for t in trans_tokens if t["sentenceIdx"] == 1]
        assert len(s1_tokens) == 3
        assert s1_tokens[0]["start"] == pytest.approx(1.0, abs=0.01)
        assert s1_tokens[2]["end"] == pytest.approx(2.2, abs=0.01)


class TestCumulativeOffsetCalculation:
    """Tests specifically for cumulative offset calculation."""

    def test_cumulative_offsets_match_durations(self) -> None:
        """Verify sentence offsets equal cumulative durations."""
        durations = [1.5, 2.0, 1.8, 2.2, 1.0]
        specs = []

        trans_cursor = 0.0
        for idx, dur in enumerate(durations):
            specs.append(_make_sentence_spec(
                sentence_idx=idx,
                original_text=f"Original {idx}",
                translation_text=f"Translation {idx}",
                original_duration=dur,
                translation_duration=dur,
                start_gate=trans_cursor,
                end_gate=trans_cursor + dur,
                original_start_gate=trans_cursor,
                original_end_gate=trans_cursor + dur,
            ))
            trans_cursor += dur

        total = sum(durations)
        tracks = build_separate_track_timings(
            specs,
            original_duration=total,
            translation_duration=total,
        )

        # Verify each sentence starts at cumulative offset
        expected_offset = 0.0
        for idx, dur in enumerate(durations):
            sentence_tokens = [t for t in tracks["translation"] if t["sentenceIdx"] == idx]
            if sentence_tokens:
                first_start = min(t["start"] for t in sentence_tokens)
                assert first_start == pytest.approx(expected_offset, abs=0.02), (
                    f"Sentence {idx}: expected start at {expected_offset}, got {first_start}"
                )
            expected_offset += dur


class TestValidationHelpers:
    """Tests for timing validation utilities."""

    def test_validate_timing_monotonic_fixes_overlaps(self) -> None:
        """validate_timing_monotonic should fix overlapping tokens."""
        tokens = [
            {"start": 0.0, "end": 0.5},
            {"start": 0.4, "end": 0.9},  # Overlaps with previous
            {"start": 0.8, "end": 1.2},  # Overlaps with previous
        ]

        result = validate_timing_monotonic(tokens, start_gate=0.0, end_gate=1.2)

        # Should have fixed the overlaps
        assert tokens[1]["start"] >= tokens[0]["end"]
        assert tokens[2]["start"] >= tokens[1]["end"]
        assert result["count"] == 3

    def test_validate_timing_monotonic_scales_to_end_gate(self) -> None:
        """Tokens should be scaled to fit within the end gate."""
        tokens = [
            {"start": 0.0, "end": 0.5},
            {"start": 0.5, "end": 1.0},
            {"start": 1.0, "end": 1.5},
        ]

        # End gate is shorter than tokens
        result = validate_timing_monotonic(tokens, start_gate=0.0, end_gate=1.2)

        # Last token should end at end_gate
        assert tokens[-1]["end"] == pytest.approx(1.2, abs=0.01)


class TestEdgeCases:
    """Edge case tests for multi-sentence chunks."""

    def test_single_word_sentences(self) -> None:
        """Handle sentences with single words correctly."""
        specs = [
            _make_sentence_spec(
                sentence_idx=i,
                original_text="Word",
                translation_text="Mot",
                original_duration=0.5,
                translation_duration=0.6,
                start_gate=i * 0.6,
                end_gate=(i + 1) * 0.6,
                original_start_gate=i * 0.5,
                original_end_gate=(i + 1) * 0.5,
            )
            for i in range(5)
        ]

        tracks = build_separate_track_timings(
            specs,
            original_duration=2.5,
            translation_duration=3.0,
        )

        # Should have 5 tokens, one per sentence
        assert len(tracks["translation"]) == 5
        assert len(tracks["original"]) == 5

    def test_empty_sentence_handling(self) -> None:
        """Handle empty sentences gracefully."""
        specs = [
            _make_sentence_spec(
                sentence_idx=0,
                original_text="Hello",
                translation_text="Bonjour",
                original_duration=0.5,
                translation_duration=0.6,
                start_gate=0.0,
                end_gate=0.6,
            ),
            _make_sentence_spec(
                sentence_idx=1,
                original_text="",
                translation_text="",
                original_duration=0.0,
                translation_duration=0.0,
                start_gate=0.6,
                end_gate=0.6,
            ),
            _make_sentence_spec(
                sentence_idx=2,
                original_text="Goodbye",
                translation_text="Au revoir",
                original_duration=0.5,
                translation_duration=0.7,
                start_gate=0.6,
                end_gate=1.3,
            ),
        ]

        tracks = build_separate_track_timings(
            specs,
            original_duration=1.0,
            translation_duration=1.3,
        )

        # Should handle empty sentence without breaking
        assert len(tracks["translation"]) >= 2

    def test_very_short_durations(self) -> None:
        """Handle very short sentence durations."""
        specs = [
            _make_sentence_spec(
                sentence_idx=i,
                original_text="A",
                translation_text="B",
                original_duration=0.1,
                translation_duration=0.1,
                start_gate=i * 0.1,
                end_gate=(i + 1) * 0.1,
                original_start_gate=i * 0.1,
                original_end_gate=(i + 1) * 0.1,
            )
            for i in range(10)
        ]

        tracks = build_separate_track_timings(
            specs,
            original_duration=1.0,
            translation_duration=1.0,
        )

        # Should still produce valid timing
        trans_tokens = tracks["translation"]
        if trans_tokens:
            first_start = min(t["start"] for t in trans_tokens)
            last_end = max(t["end"] for t in trans_tokens)
            assert first_start >= 0.0
            assert last_end <= 1.1  # Small tolerance

    def test_large_chunk_performance(self) -> None:
        """Verify reasonable performance with many sentences."""
        specs = []
        cursor = 0.0

        for i in range(50):
            dur = 1.0 + (i % 5) * 0.2
            specs.append(_make_sentence_spec(
                sentence_idx=i,
                original_text=f"Sentence {i} with some words",
                translation_text=f"Phrase {i} avec quelques mots",
                original_duration=dur,
                translation_duration=dur * 1.1,
                start_gate=cursor,
                end_gate=cursor + dur * 1.1,
                original_start_gate=cursor / 1.1,
                original_end_gate=cursor / 1.1 + dur,
            ))
            cursor += dur * 1.1

        total_trans = sum(s.translation_duration for s in specs)
        total_orig = sum(s.original_duration for s in specs)

        # Should complete without timeout
        tracks = build_separate_track_timings(
            specs,
            original_duration=total_orig,
            translation_duration=total_trans,
        )

        # Basic sanity checks
        assert len(tracks["translation"]) > 0
        assert len(tracks["original"]) > 0


class TestFrontendPayloadCompatibility:
    """Tests ensuring backend output matches frontend expectations."""

    def test_tokens_have_required_fields(self) -> None:
        """Tokens should have all fields required by frontend WordTiming."""
        specs = [
            _make_sentence_spec(
                sentence_idx=0,
                original_text="Hello world",
                translation_text="Bonjour monde",
                original_duration=1.0,
                translation_duration=1.2,
            ),
        ]

        tracks = build_separate_track_timings(
            specs,
            original_duration=1.0,
            translation_duration=1.2,
        )

        for token in tracks["translation"]:
            # Required fields for frontend WordTiming
            assert "sentenceIdx" in token, "Missing sentenceIdx"
            assert "wordIdx" in token, "Missing wordIdx"
            assert "start" in token, "Missing start"
            assert "end" in token, "Missing end"
            assert "lane" in token, "Missing lane"

            # Type checks
            assert isinstance(token["sentenceIdx"], int)
            assert isinstance(token["wordIdx"], int)
            assert isinstance(token["start"], (int, float))
            assert isinstance(token["end"], (int, float))
            assert token["lane"] in ("orig", "trans")

    def test_sentence_ids_are_global_by_default(self) -> None:
        """Sentence IDs should be global (not chunk-relative) by default."""
        # Simulate a chunk starting at sentence 100
        specs = [
            _make_sentence_spec(
                sentence_idx=100 + i,
                original_text=f"Sentence {100 + i}",
                translation_text=f"Phrase {100 + i}",
                original_duration=1.0,
                translation_duration=1.2,
                start_gate=i * 1.2,
                end_gate=(i + 1) * 1.2,
            )
            for i in range(5)
        ]

        tracks = build_separate_track_timings(
            specs,
            original_duration=5.0,
            translation_duration=6.0,
        )

        # Sentence IDs should be preserved as global
        sentence_ids = set(t["sentenceIdx"] for t in tracks["translation"])
        assert 100 in sentence_ids
        assert 104 in sentence_ids
        assert 0 not in sentence_ids  # Should NOT be chunk-relative

    def test_sentence_ids_are_local_when_requested(self) -> None:
        """Sentence IDs should be chunk-local when use_local_indices=True."""
        # Simulate a chunk starting at sentence 100
        specs = [
            _make_sentence_spec(
                sentence_idx=100 + i,
                original_text=f"Sentence {100 + i}",
                translation_text=f"Phrase {100 + i}",
                original_duration=1.0,
                translation_duration=1.2,
                start_gate=i * 1.2,
                end_gate=(i + 1) * 1.2,
            )
            for i in range(5)
        ]

        tracks = build_separate_track_timings(
            specs,
            original_duration=5.0,
            translation_duration=6.0,
            use_local_indices=True,
        )

        # Sentence IDs should be chunk-local (0-4)
        sentence_ids = set(t["sentenceIdx"] for t in tracks["translation"])
        assert 0 in sentence_ids
        assert 4 in sentence_ids
        assert 100 not in sentence_ids  # Should NOT be global
        assert 104 not in sentence_ids


class TestAudioTimingAlignment:
    """Tests for audio-timing alignment verification."""

    def test_timing_matches_expected_audio_duration(self) -> None:
        """Final token end should match expected audio duration."""
        expected_durations = [1.5, 2.0, 1.8]
        specs = []
        cursor = 0.0

        for idx, dur in enumerate(expected_durations):
            specs.append(_make_sentence_spec(
                sentence_idx=idx,
                original_text=f"Original sentence {idx}",
                translation_text=f"Translated sentence {idx}",
                original_duration=dur,
                translation_duration=dur,
                start_gate=cursor,
                end_gate=cursor + dur,
                original_start_gate=cursor,
                original_end_gate=cursor + dur,
            ))
            cursor += dur

        total = sum(expected_durations)
        tracks = build_separate_track_timings(
            specs,
            original_duration=total,
            translation_duration=total,
        )

        last_token = max(tracks["translation"], key=lambda t: t["end"])
        drift_ms = abs(last_token["end"] - total) * 1000

        assert drift_ms < 50, (
            f"Timing drift: {drift_ms}ms "
            f"(expected {total}s, got {last_token['end']}s)"
        )


class TestNewValidationHelpers:
    """Tests for the new validation helper functions."""

    def test_validate_cross_sentence_continuity_valid(self) -> None:
        """Valid continuous sentences should pass validation."""
        specs = [
            _make_sentence_spec(
                sentence_idx=i,
                original_text=f"Sentence {i}",
                translation_text=f"Phrase {i}",
                original_duration=1.0,
                translation_duration=1.0,
                start_gate=i * 1.0,
                end_gate=(i + 1) * 1.0,
            )
            for i in range(5)
        ]

        result = validate_cross_sentence_continuity(specs)

        assert result["valid"] is True
        assert result["sentence_count"] == 5
        assert len(result["issues"]) == 0

    def test_validate_cross_sentence_continuity_with_gap(self) -> None:
        """Gaps between sentences should be detected."""
        specs = [
            _make_sentence_spec(
                sentence_idx=0,
                original_text="Sentence 0",
                translation_text="Phrase 0",
                original_duration=1.0,
                translation_duration=1.0,
                start_gate=0.0,
                end_gate=1.0,
            ),
            _make_sentence_spec(
                sentence_idx=1,
                original_text="Sentence 1",
                translation_text="Phrase 1",
                original_duration=1.0,
                translation_duration=1.0,
                start_gate=1.5,  # 500ms gap
                end_gate=2.5,
            ),
        ]

        result = validate_cross_sentence_continuity(specs)

        assert result["valid"] is False
        assert len(result["issues"]) == 1
        assert result["issues"][0]["gap_ms"] == pytest.approx(500.0, abs=1.0)

    def test_validate_cross_sentence_continuity_single_sentence(self) -> None:
        """Single sentence should always be valid."""
        specs = [
            _make_sentence_spec(
                sentence_idx=0,
                original_text="Only one",
                translation_text="Un seul",
                original_duration=1.0,
                translation_duration=1.0,
            ),
        ]

        result = validate_cross_sentence_continuity(specs)

        assert result["valid"] is True
        assert result["sentence_count"] == 1

    def test_validate_chunk_timing_alignment_valid(self) -> None:
        """Properly aligned tokens should pass."""
        tokens = [
            {"start": 0.0, "end": 0.5},
            {"start": 0.5, "end": 1.0},
            {"start": 1.0, "end": 1.5},
        ]

        result = validate_chunk_timing_alignment(tokens, expected_duration=1.5)

        assert result["valid"] is True
        assert result["start_drift_ms"] < 10.0
        assert result["end_drift_ms"] < 50.0

    def test_validate_chunk_timing_alignment_with_drift(self) -> None:
        """Detect drift when tokens don't match expected duration."""
        tokens = [
            {"start": 0.0, "end": 0.5},
            {"start": 0.5, "end": 1.0},
            {"start": 1.0, "end": 1.3},  # Ends early
        ]

        result = validate_chunk_timing_alignment(tokens, expected_duration=1.5)

        assert result["valid"] is False
        assert result["end_drift_ms"] == pytest.approx(200.0, abs=1.0)

    def test_validate_chunk_timing_alignment_empty(self) -> None:
        """Empty tokens should fail validation."""
        result = validate_chunk_timing_alignment([], expected_duration=1.0)

        assert result["valid"] is False
        assert result["error"] == "no_tokens"

    def test_compute_cumulative_offsets(self) -> None:
        """Compute correct cumulative offsets from durations."""
        durations = [1.0, 2.0, 1.5, 0.5]

        offsets = compute_cumulative_offsets(durations)

        assert offsets == [0.0, 1.0, 3.0, 4.5]

    def test_compute_cumulative_offsets_single(self) -> None:
        """Single duration should give single offset."""
        offsets = compute_cumulative_offsets([1.5])

        assert offsets == [0.0]

    def test_compute_cumulative_offsets_empty(self) -> None:
        """Empty durations should give single zero offset."""
        offsets = compute_cumulative_offsets([])

        assert offsets == [0.0]


class TestScaleTimingToAudioDuration:
    """Tests for the scale_timing_to_audio_duration function."""

    def test_no_scaling_when_within_tolerance(self) -> None:
        """When expected and actual durations are close, no scaling is applied."""
        tokens = [
            {"start": 0.0, "end": 0.5, "text": "Hello"},
            {"start": 0.5, "end": 1.0, "text": "world"},
        ]

        scaled, validation = scale_timing_to_audio_duration(
            tokens, expected_duration=1.0, actual_duration=1.01  # 1% diff
        )

        assert validation["scaling_applied"] is False
        assert validation["scale_factor"] == 1.0
        # Tokens should be essentially unchanged (last token clamped)
        assert scaled[0]["start"] == 0.0
        assert scaled[0]["end"] == 0.5
        assert scaled[1]["start"] == 0.5
        assert scaled[1]["end"] == pytest.approx(1.0, abs=0.01)

    def test_scaling_applied_when_exceeds_tolerance(self) -> None:
        """When expected and actual durations differ by >2%, scaling is applied."""
        tokens = [
            {"start": 0.0, "end": 0.5, "text": "Hello"},
            {"start": 0.5, "end": 1.0, "text": "world"},
        ]

        # 20% difference should trigger scaling
        scaled, validation = scale_timing_to_audio_duration(
            tokens, expected_duration=1.0, actual_duration=1.2
        )

        assert validation["scaling_applied"] is True
        assert validation["scale_factor"] == pytest.approx(1.2, abs=0.001)
        # Tokens should be scaled
        assert scaled[0]["start"] == pytest.approx(0.0, abs=0.01)
        assert scaled[0]["end"] == pytest.approx(0.6, abs=0.01)  # 0.5 * 1.2
        assert scaled[1]["start"] == pytest.approx(0.6, abs=0.01)  # 0.5 * 1.2
        assert scaled[1]["end"] == pytest.approx(1.2, abs=0.01)  # Last token ends at actual_duration

    def test_scaling_down_when_actual_shorter(self) -> None:
        """When actual duration is shorter, tokens are compressed."""
        tokens = [
            {"start": 0.0, "end": 0.5, "text": "Hello"},
            {"start": 0.5, "end": 1.0, "text": "world"},
        ]

        scaled, validation = scale_timing_to_audio_duration(
            tokens, expected_duration=1.0, actual_duration=0.8
        )

        assert validation["scaling_applied"] is True
        assert validation["scale_factor"] == pytest.approx(0.8, abs=0.001)
        # Tokens should be compressed
        assert scaled[0]["start"] == pytest.approx(0.0, abs=0.01)
        assert scaled[0]["end"] == pytest.approx(0.4, abs=0.01)  # 0.5 * 0.8
        assert scaled[1]["start"] == pytest.approx(0.4, abs=0.01)
        assert scaled[1]["end"] == pytest.approx(0.8, abs=0.01)

    def test_empty_tokens_returns_empty(self) -> None:
        """Empty token list should return empty list."""
        scaled, validation = scale_timing_to_audio_duration(
            [], expected_duration=1.0, actual_duration=1.2
        )

        assert scaled == []
        assert validation["scaling_applied"] is False

    def test_zero_expected_duration_no_scaling(self) -> None:
        """Zero expected duration should not cause errors."""
        tokens = [{"start": 0.0, "end": 0.5, "text": "Hello"}]

        scaled, validation = scale_timing_to_audio_duration(
            tokens, expected_duration=0.0, actual_duration=1.0
        )

        assert validation["scaling_applied"] is False
        assert scaled == tokens

    def test_drift_ms_calculated_correctly(self) -> None:
        """Drift in milliseconds should be calculated correctly."""
        tokens = [{"start": 0.0, "end": 1.0, "text": "Hello"}]

        _, validation = scale_timing_to_audio_duration(
            tokens, expected_duration=1.0, actual_duration=1.1
        )

        assert validation["drift_ms"] == pytest.approx(100.0, abs=1.0)

    def test_preserves_other_token_fields(self) -> None:
        """Scaling should preserve other token fields."""
        tokens = [
            {"start": 0.0, "end": 1.0, "text": "Hello", "wordIdx": 0, "sentenceIdx": 0, "lane": "trans"},
        ]

        scaled, _ = scale_timing_to_audio_duration(
            tokens, expected_duration=1.0, actual_duration=1.5
        )

        assert scaled[0]["text"] == "Hello"
        assert scaled[0]["wordIdx"] == 0
        assert scaled[0]["sentenceIdx"] == 0
        assert scaled[0]["lane"] == "trans"
