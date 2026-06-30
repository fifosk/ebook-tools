from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLAYBACK = ROOT / "ios" / "InteractiveReader" / "InteractiveReader" / "Features" / "Playback"


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _function_body(source: str, signature: str) -> str:
    start = source.index(signature)
    brace = source.index("{", start)
    depth = 0
    for index in range(brace, len(source)):
        character = source[index]
        if character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth == 0:
                return source[brace + 1 : index]
    raise AssertionError(f"Could not find body for {signature}")


def test_tvos_observed_music_pause_after_reader_play_is_time_bounded() -> None:
    resolver = _source(PLAYBACK / "ReaderTransportCommandResolver.swift")
    window_body = _function_body(resolver, "static var observedPauseAfterPlayEchoWindow")
    ignore_body = _function_body(
        resolver,
        "static func shouldIgnoreObservedPauseAfterReaderPlay",
    )

    assert "#if os(tvOS)" in window_body
    assert "return duplicateWindow" in window_body
    assert "return 0" in window_body
    assert 'previousAction == "play"' in ignore_body
    assert "now - lastCommandTime < observedPauseAfterPlayEchoWindow" in ignore_body
    assert "lastCommandTime" in ignore_body


def test_apple_playback_surfaces_do_not_ignore_all_post_play_music_pauses() -> None:
    for filename, label in (
        ("JobPlaybackView.swift", "Job"),
        ("LibraryPlaybackView.swift", "Library"),
    ):
        source = _source(PLAYBACK / filename)
        adoption_body = _function_body(source, "private func handleMusicKitReaderTransportPauseAdoption()")
        mirror_decision_body = _function_body(source, "private var shouldMirrorAppleMusicPauseToNarration")
        stale_gate_body = _function_body(source, "private var shouldIgnoreStaleAppleMusicPauseAfterReaderPlay")

        assert "if shouldIgnoreStaleAppleMusicPauseAfterReaderPlay" in adoption_body, label
        assert 'if lastReaderTransportAction == "play"' not in adoption_body, label
        assert adoption_body.index("if shouldIgnoreStaleAppleMusicPauseAfterReaderPlay") < adoption_body.index(
            'mirrorAppleMusicPauseToReaderTransport(source: "musicAdoption")'
        )
        assert "if shouldIgnoreStaleAppleMusicPauseAfterReaderPlay" in mirror_decision_body, label
        assert 'if lastReaderTransportAction == "play"' not in mirror_decision_body, label
        assert "ReaderTransportCommandResolver.shouldIgnoreObservedPauseAfterReaderPlay(" in stale_gate_body, label
        assert "previousAction: lastReaderTransportAction" in stale_gate_body, label
        assert "lastCommandTime: lastReaderTransportCommandTime" in stale_gate_body, label
        assert 'guard lastReaderTransportAction == "play" else { return false }' in stale_gate_body, label
        assert "musicOwnership.isPausedByReaderTransport" in stale_gate_body, label
        assert "musicOwnership.isReaderTransportPauseGuardActive" in stale_gate_body, label
        assert "readerTransportMusicResumeTask != nil" in stale_gate_body, label
