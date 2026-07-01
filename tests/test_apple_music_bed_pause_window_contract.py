from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APPLE = ROOT / "ios" / "InteractiveReader" / "InteractiveReader"
PLAYBACK = APPLE / "Features" / "Playback"
SERVICES = APPLE / "Services"


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
    adopted_window_body = _function_body(resolver, "static var adoptedMusicPauseBrokerEchoWindow")
    ignore_body = _function_body(
        resolver,
        "static func shouldIgnoreObservedPauseAfterReaderPlay",
    )

    assert "#if os(tvOS)" in window_body
    assert "return duplicateWindow" in window_body
    assert "return 0" in window_body
    assert "#if os(tvOS)" in adopted_window_body
    assert adopted_window_body.count("return brokerEchoWindow") == 2
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
        assert "hasPendingReaderMusicResume" in stale_gate_body, label
        assert "musicOwnership.isPausedByReaderTransport" not in stale_gate_body, label
        assert "musicOwnership.isReaderTransportPauseGuardActive" in stale_gate_body, label
        assert "readerTransportMusicResumeTask != nil" in stale_gate_body, label


def test_tvos_reader_pause_reasserts_against_stray_music_play() -> None:
    resolver = _source(PLAYBACK / "ReaderTransportCommandResolver.swift")
    assert 'source == "musicPlayReassert"' in resolver

    for filename, label in (
        ("JobPlaybackView.swift", "Job"),
        ("LibraryPlaybackView.swift", "Library"),
    ):
        source = _source(PLAYBACK / filename)
        surface_change_body = _function_body(source, "private func handleMusicKitPlaybackSurfaceChange()")
        reassert_body = _function_body(source, "private var shouldReassertReaderTransportPauseAfterMusicPlay")

        assert "if shouldReassertReaderTransportPauseAfterMusicPlay" in surface_change_body, label
        assert 'mirrorAppleMusicPauseToReaderTransport(source: "musicPlayReassert")' in surface_change_body, label
        assert surface_change_body.index("if shouldReassertReaderTransportPauseAfterMusicPlay") < surface_change_body.index(
            "if shouldMirrorAppleMusicPlayToNarration"
        ), label
        assert 'lastReaderTransportAction == "pause"' in reassert_body, label
        assert "musicOwnership.isPlaying" in reassert_body, label
        assert "!musicOwnership.isReaderTransportPauseGuardActive" in reassert_body, label
        assert 'ProcessInfo.processInfo.environment["E2E_MUSIC_BED_SYNC_TEST"] == "1"' in reassert_body, label
        assert "e2eReaderTransportCommandCount == 0" in reassert_body, label


def test_tvos_active_music_pause_confirms_reader_pause_before_recovery() -> None:
    music = _source(SERVICES / "MusicKitCoordinator.swift")
    observed_body = _function_body(music, "private func handleObservedNonPlayingStatus")
    confirm_gate_body = _function_body(
        music,
        "private var shouldConfirmActiveNarrationNonPlayingAsReaderPause",
    )
    confirm_body = _function_body(
        music,
        "private func confirmActiveNarrationNonPlayingAsReaderPause",
    )
    defer_body = _function_body(
        music,
        "private var shouldDeferObservedNonPlayingDuringActiveReadingBed",
    )

    assert "if shouldConfirmActiveNarrationNonPlayingAsReaderPause" in observed_body
    assert "confirmActiveNarrationNonPlayingAsReaderPause(reason: \"observedNonPlaying\")" in observed_body
    assert observed_body.index("if shouldConfirmActiveNarrationNonPlayingAsReaderPause") < observed_body.index(
        "if shouldDeferObservedNonPlayingDuringActiveReadingBed"
    )
    assert "#if os(tvOS)" in confirm_gate_body
    assert "ownershipState == .appleMusicBed" in confirm_gate_body
    assert "isReaderNarrationActiveForMusicBed" in confirm_gate_body
    assert "!isManuallyPaused" in confirm_gate_body
    assert "!isPausedByReaderTransport" in confirm_gate_body
    assert "350_000_000" in confirm_body
    assert "ApplicationMusicPlayer.shared.state.playbackStatus != .playing" in confirm_body
    assert "adoptPauseAsReaderTransport(" in confirm_body
    assert 'source: "active observed non-playing"' in confirm_body
    assert 'e2eMusicBedSyncPhase = "observedPauseImmediate"' in confirm_body
    assert "shouldAdoptObservedNonPlayingImmediately" in defer_body
