from __future__ import annotations

import pytest

from modules.core.rendering.timeline import SentenceTimingSpec, build_dual_track_timings


def test_dual_track_timings_respect_mix_gate_offsets() -> None:
    spec = SentenceTimingSpec(
        sentence_idx=1,
        original_text="orig",
        translation_text="trans",
        original_words=["orig"],
        translation_words=["trans"],
        word_tokens=[{"text": "trans", "start": 0.0, "end": 1.0}],
        translation_duration=1.0,
        original_duration=2.0,
        gap_before_translation=0.5,
        gap_after_translation=0.0,
        char_weighted_enabled=False,
        punctuation_boost=False,
        policy="estimated",
        source="char_weighted",
        start_gate=2.5,
        end_gate=3.5,
        pause_before_ms=0.0,
        pause_after_ms=0.0,
    )
    spec.mix_start_gate = 0.0
    spec.mix_end_gate = 3.5

    tracks = build_dual_track_timings([spec], mix_duration=3.5, translation_duration=3.5)

    assert pytest.approx(0.0) == tracks["mix"][0]["start"]
    assert pytest.approx(0.0, abs=1e-6) == tracks["translation"][0]["start"]
