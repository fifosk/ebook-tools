"""Tests for deriving audio tracks during batch export."""

from __future__ import annotations

from pydub import AudioSegment

from modules.audio.highlight import AudioHighlightPart, SentenceAudioMetadata, _store_audio_metadata
from modules.audio.tts import SILENCE_DURATION_MS
from modules.core.rendering.exporters import _derive_audio_tracks_from_segments


def _duration_seconds(segment: AudioSegment) -> float:
    return len(segment) / 1000.0


def test_derive_audio_tracks_with_original_and_translation() -> None:
    original = AudioSegment.silent(duration=150)
    silence = AudioSegment.silent(duration=SILENCE_DURATION_MS)
    translation = AudioSegment.silent(duration=220)
    combined = original + silence + translation

    metadata = SentenceAudioMetadata(
        parts=[
            AudioHighlightPart(kind="original", duration=_duration_seconds(original), start_offset=0.0),
            AudioHighlightPart(
                kind="silence",
                duration=_duration_seconds(silence),
                start_offset=_duration_seconds(original),
            ),
            AudioHighlightPart(
                kind="translation",
                duration=_duration_seconds(translation),
                start_offset=_duration_seconds(original) + _duration_seconds(silence),
            ),
        ],
        total_duration=_duration_seconds(combined),
    )
    _store_audio_metadata(combined, metadata)

    tracks = _derive_audio_tracks_from_segments([combined])

    assert "orig" in tracks
    assert "trans" in tracks
    assert len(tracks["orig"]) == 1
    assert len(tracks["trans"]) == 1
    assert abs(_duration_seconds(tracks["orig"][0]) - _duration_seconds(original)) < 0.01
    assert abs(_duration_seconds(tracks["trans"][0]) - _duration_seconds(translation)) < 0.01


def test_derive_audio_tracks_without_metadata_falls_back_to_translation() -> None:
    segment = AudioSegment.silent(duration=480)

    # Ensure any recycled audio metadata registry entries are cleared for this segment.
    empty_metadata = SentenceAudioMetadata(parts=[], total_duration=_duration_seconds(segment))
    _store_audio_metadata(segment, empty_metadata)

    tracks = _derive_audio_tracks_from_segments([segment])

    assert "orig" not in tracks
    assert "trans" in tracks
    assert len(tracks["trans"]) == 1
    assert abs(_duration_seconds(tracks["trans"][0]) - _duration_seconds(segment)) < 0.01
