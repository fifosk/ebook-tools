import math
import pathlib
import sys
from dataclasses import dataclass

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.core.rendering.timeline import SentenceTimingSpec, _build_mix_sentence_tokens


def _spec(**overrides) -> SentenceTimingSpec:
    base = dict(
        sentence_idx=1,
        original_text="x y",
        translation_text="a b c",
        original_words=["x", "y"],
        translation_words=["a", "b", "c"],
        word_tokens=None,
        translation_duration=2.5,
        original_duration=3.0,
        gap_before_translation=0.0,
        gap_after_translation=0.0,
        char_weighted_enabled=True,
        punctuation_boost=False,
        policy="forced",
        source="aligner",
        start_gate=10.0,
        end_gate=16.0,
        pause_before_ms=200,
        pause_after_ms=0,
        mix_start_gate=10.0,
        mix_end_gate=16.0,
        validation_metrics=None,
    )
    base.update(overrides)
    return SentenceTimingSpec(**base)


def test_mix_char_weighted_interleaving():
    spec = _spec()
    tokens = _build_mix_sentence_tokens(spec)
    assert tokens, "expected mix tokens"

    starts = [token["start"] for token in tokens]
    ends = [token["end"] for token in tokens]

    assert min(starts) >= 9.999 - 1e-6
    assert max(ends) <= 16.001 + 1e-6

    orig_ends = [token["end"] for token in tokens if token["lane"] == "orig"]
    trans_starts = [token["start"] for token in tokens if token["lane"] == "trans"]

    assert orig_ends and max(orig_ends) <= 13.0 + 1e-6
    assert trans_starts and min(trans_starts) >= 13.2 - 1e-6

    assert math.isclose(max(ends), 16.0, abs_tol=1e-3)

    for idx in range(1, len(tokens)):
        assert tokens[idx]["start"] >= tokens[idx - 1]["end"] - 1e-6


def test_mix_with_translation_word_tokens():
    word_tokens = [
        {"text": "alpha", "start": 0.0, "end": 0.8},
        {"text": "beta", "start": 0.8, "end": 1.6},
    ]
    spec = _spec(translation_duration=1.6, word_tokens=word_tokens)
    tokens = _build_mix_sentence_tokens(spec)
    assert any(token["lane"] == "trans" and token.get("fallback") for token in tokens) is False
    trans_tokens = [token for token in tokens if token["lane"] == "trans"]
    assert len(trans_tokens) == len(word_tokens)
    assert math.isclose(trans_tokens[-1]["end"], 16.0, abs_tol=1e-3)
