import math
import pathlib
import sys

import pytest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.core.rendering.timeline import SentenceTimingSpec, build_dual_track_timings


def _spec(sentence_idx: int, original_duration: float, translation_duration: float) -> SentenceTimingSpec:
    return SentenceTimingSpec(
        sentence_idx=sentence_idx,
        original_text="hello world" if original_duration else "",
        translation_text="bonjour le monde",
        original_words=["hello", "world"] if original_duration else [],
        translation_words=["bonjour", "le", "monde"],
        word_tokens=[
            {"text": "bonjour", "start": 0.0, "end": translation_duration * 0.3},
            {"text": "le", "start": translation_duration * 0.3, "end": translation_duration * 0.6},
            {"text": "monde", "start": translation_duration * 0.6, "end": translation_duration},
        ],
        translation_duration=translation_duration,
        original_duration=original_duration,
        gap_before_translation=0.1 if original_duration else 0.0,
        gap_after_translation=0.05,
        char_weighted_enabled=False,
        punctuation_boost=True,
        policy="forced",
        source="aligner",
    )


def test_mix_track_alignment_and_bounds() -> None:
    specs = [
        _spec(sentence_idx=1, original_duration=0.8, translation_duration=1.2),
        _spec(sentence_idx=2, original_duration=0.6, translation_duration=1.0),
    ]
    mix_duration = sum(
        spec.original_duration + spec.gap_before_translation + spec.translation_duration + spec.gap_after_translation
        for spec in specs
    )
    translation_duration = sum(spec.translation_duration for spec in specs)

    tracks = build_dual_track_timings(
        specs,
        mix_duration=mix_duration,
        translation_duration=translation_duration,
    )

    assert "mix" in tracks and "translation" in tracks

    mix_tokens = tracks["mix"]
    translation_tokens = tracks["translation"]

    assert mix_tokens, "mix track empty"
    assert translation_tokens, "translation track empty"

    assert math.isclose(mix_tokens[0]["start"], 0.0, abs_tol=0.005)

    max_mix_end = max(token["end"] for token in mix_tokens)
    assert max_mix_end <= mix_duration + 0.005

    for sentence in {spec.sentence_idx for spec in specs}:
        sentence_tokens = [token for token in mix_tokens if token["sentenceIdx"] == sentence]
        if not sentence_tokens:
            continue
        lanes = [token["lane"] for token in sentence_tokens]
        first_trans_index = next((idx for idx, lane in enumerate(lanes) if lane == "trans"), None)
        if first_trans_index is None:
            continue
        assert all(lane == "orig" for lane in lanes[:first_trans_index])
        assert all(lane == "trans" for lane in lanes[first_trans_index:])

    if translation_tokens:
        max_translation_end = max(token["end"] for token in translation_tokens)
        assert max_translation_end <= translation_duration + 0.005
