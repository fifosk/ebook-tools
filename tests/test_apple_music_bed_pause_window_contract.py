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
    recovery_limit_body = _function_body(
        resolver,
        "static var pendingInteractiveAutoplayRecoveryAttemptLimit",
    )
    ignore_body = _function_body(
        resolver,
        "static func shouldIgnoreObservedPauseAfterReaderPlay",
    )

    assert "#if os(tvOS)" in window_body
    assert "return duplicateWindow" in window_body
    assert "return 0" in window_body
    assert "#if os(tvOS)" in adopted_window_body
    assert adopted_window_body.count("return brokerEchoWindow") == 2
    assert "#if os(tvOS)" in recovery_limit_body
    assert "return 6" in recovery_limit_body
    assert "return 2" in recovery_limit_body
    assert 'previousAction == "play"' in ignore_body
    assert "now - lastCommandTime < observedPauseAfterPlayEchoWindow" in ignore_body
    assert "lastCommandTime" in ignore_body


def test_apple_playback_surfaces_do_not_ignore_all_post_play_music_pauses() -> None:
    for filename, label in (
        ("JobPlaybackView.swift", "Job"),
        ("LibraryPlaybackView.swift", "Library"),
    ):
        source = _source(PLAYBACK / filename)
        adoption_body = _function_body(source, "private func handleMusicKitReaderTransportPauseAdoption(reason: String? = nil, source: String? = nil)")
        music_surface_body = _function_body(source, "private func handleMusicKitPlaybackSurfaceChange()")
        mirror_decision_body = _function_body(source, "private var shouldMirrorAppleMusicPauseToNarration")
        active_pause_guard_body = _function_body(source, "private func shouldKeepReaderActiveDuringAppleMusicPause(reason: String?, source: String?)")
        stale_gate_body = _function_body(source, "private var shouldIgnoreStaleAppleMusicPauseAfterReaderPlay")
        expected_prefix = "job" if label == "Job" else "library"

        assert ".onReceive(viewModel.audioCoordinator.$isPlaybackRequested) { _ in handleAudioStateChange() }" in source, label
        assert f'func refreshReaderNarrationActivityForMusicBed(reason: String)' in source, label
        assert f'refreshReaderNarrationActivityForMusicBed(reason: "{expected_prefix}MusicSurface")' in music_surface_body, label
        assert music_surface_body.index(
            f'refreshReaderNarrationActivityForMusicBed(reason: "{expected_prefix}MusicSurface")'
        ) < music_surface_body.index("if shouldMirrorAppleMusicPlayToNarration"), label
        assert "if shouldIgnoreStaleAppleMusicPauseAfterReaderPlay" in adoption_body, label
        assert "if shouldKeepReaderActiveDuringAppleMusicPause(reason: reason, source: source)" in adoption_body, label
        assert "!shouldHonorAppleMusicPauseAdoptionImmediately(reason: reason, source: source)" in adoption_body, label
        assert 'if lastReaderTransportAction == "play"' not in adoption_body, label
        assert adoption_body.index("if shouldKeepReaderActiveDuringAppleMusicPause(reason: reason, source: source)") < adoption_body.index(
            "if shouldIgnoreRequestedAppleMusicPauseBeforeReaderAudible"
        )
        assert adoption_body.index("if shouldIgnoreStaleAppleMusicPauseAfterReaderPlay") < adoption_body.index(
            'mirrorAppleMusicPauseToReaderTransport(source: "musicAdoption")'
        )
        assert "if shouldKeepReaderActiveDuringAppleMusicPause(" in music_surface_body, label
        assert music_surface_body.index("if shouldKeepReaderActiveDuringAppleMusicPause(") < music_surface_body.index(
            "if shouldIgnoreRequestedAppleMusicPauseBeforeReaderAudible"
        ), label
        assert "if shouldKeepReaderActiveDuringAppleMusicPause(" in mirror_decision_body, label
        assert mirror_decision_body.index("if shouldKeepReaderActiveDuringAppleMusicPause(") < mirror_decision_body.index(
            "if musicOwnership.isPausedByReaderTransport"
        ), label
        assert "if shouldIgnoreStaleAppleMusicPauseAfterReaderPlay" in mirror_decision_body, label
        assert 'if lastReaderTransportAction == "play"' not in mirror_decision_body, label
        assert mirror_decision_body.index("if musicOwnership.isPausedByReaderTransport") < mirror_decision_body.index(
            "if shouldIgnoreStaleAppleMusicPauseAfterReaderPlay"
        ), label
        assert mirror_decision_body.index(
            "musicOwnership.isManuallyPaused && musicOwnership.ownershipState == .appleMusicBed"
        ) < mirror_decision_body.index("if shouldIgnoreStaleAppleMusicPauseAfterReaderPlay"), label
        assert "if musicOwnership.ownershipState == .appleMusicBed" in mirror_decision_body, label
        assert "!musicOwnership.isPlaying &&" not in mirror_decision_body, label
        assert "!musicOwnership.isSystemPlaybackPlaying" not in mirror_decision_body, label
        assert mirror_decision_body.index("if shouldIgnoreStaleAppleMusicPauseAfterReaderPlay") < mirror_decision_body.index(
            "if musicOwnership.ownershipState == .appleMusicBed"
        ), label
        honor_adoption_body = _function_body(source, "private func shouldHonorAppleMusicPauseAdoptionImmediately(reason: String?, source: String?)")
        assert 'reason == "manualPause", source == "musicSurface"' in honor_adoption_body, label
        assert 'source == "active observed non-playing"' not in honor_adoption_body, label
        assert 'source == "persistent observed non-playing"' not in honor_adoption_body, label
        assert "ReaderTransportCommandResolver.shouldIgnoreObservedPauseAfterReaderPlay(" in stale_gate_body, label
        assert "previousAction: lastReaderTransportAction" in stale_gate_body, label
        assert "lastCommandTime: lastReaderTransportCommandTime" in stale_gate_body, label
        assert 'guard lastReaderTransportAction == "play" else { return false }' in stale_gate_body, label
        assert "hasPendingReaderMusicResume" in stale_gate_body, label
        assert "musicOwnership.isPausedByReaderTransport" not in stale_gate_body, label
        assert "musicOwnership.isReaderTransportPauseGuardActive" in stale_gate_body, label
        assert "readerTransportMusicResumeTask != nil" in stale_gate_body, label
        assert "let isWithinPostPlayEchoWindow = ReaderTransportCommandResolver.shouldIgnoreObservedPauseAfterReaderPlay(" in stale_gate_body, label
        assert "if isWithinPostPlayEchoWindow" in stale_gate_body, label
        assert "guard !viewModel.isNarrationAudibleForReaderTransport else { return false }" in stale_gate_body, label
        assert "return !(viewModel.audioCoordinator.isPlaybackRequested || viewModel.audioCoordinator.isPlaying)" in stale_gate_body, label
        assert "return hasPendingReaderMusicResume" not in stale_gate_body, label
        assert "musicOwnership.ownershipState == .appleMusicBed" in active_pause_guard_body, label
        assert "viewModel.audioCoordinator.isPlaybackRequested ||" in active_pause_guard_body, label
        assert "viewModel.audioCoordinator.isPlaying" in active_pause_guard_body, label
        assert 'reason == "readerTransportPause" || source == "reader transport"' in active_pause_guard_body, label
        assert "isObservedAppleMusicNonPlayingPause(reason: reason, source: source)" in active_pause_guard_body, label
        assert 'reason == "manualPause", source == "musicSurface"' in active_pause_guard_body, label
        assert active_pause_guard_body.index(
            "isObservedAppleMusicNonPlayingPause(reason: reason, source: source)"
        ) < active_pause_guard_body.index('reason == "manualPause", source == "musicSurface"'), label
        assert 'lastReaderTransportAction == "pause"' in active_pause_guard_body, label
        assert "return true" in active_pause_guard_body, label
        observed_pause_body = _function_body(source, "private func isObservedAppleMusicNonPlayingPause(reason: String?, source: String?)")
        assert 'reason == "observedNonPlaying"' in observed_pause_body, label
        assert 'localizedCaseInsensitiveContains("observed non-playing")' in observed_pause_body, label


def test_tvos_music_paused_resume_does_not_override_active_reader_pause() -> None:
    resolver = _source(PLAYBACK / "ReaderTransportCommandResolver.swift")
    force_resume_body = _function_body(resolver, "static func shouldForceNowPlayingResume")

    assert "guard !isReaderPlaybackRequested, !isReaderPlaying else { return false }" in force_resume_body
    assert "if isMusicPausedByReaderTransport" in force_resume_body
    assert force_resume_body.index(
        "guard !isReaderPlaybackRequested, !isReaderPlaying else { return false }"
    ) < force_resume_body.index(
        "if isMusicPausedByReaderTransport"
    )


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
        assert "musicOwnership.isPausedByReaderTransport" in reassert_body, label
        assert "musicOwnership.isManuallyPaused" in reassert_body, label
        assert "musicOwnership.isReaderTransportPauseGuardActive" in reassert_body, label
        assert "!musicOwnership.isReaderTransportPauseGuardActive" not in reassert_body, label
        assert 'ProcessInfo.processInfo.environment["E2E_MUSIC_BED_SYNC_TEST"] == "1"' not in reassert_body, label
        assert "e2eReaderTransportCommandCount == 0" not in reassert_body, label


def test_tvos_active_music_pause_keeps_reader_transport() -> None:
    music = _source(SERVICES / "MusicKitCoordinator.swift")
    observed_body = _function_body(music, "private func handleObservedNonPlayingStatus")
    defer_body = _function_body(
        music,
        "private var shouldDeferObservedNonPlayingDuringActiveReadingBed",
    )
    recover_body = _function_body(
        music,
        "private var shouldRecoverObservedNonPlayingForReadingBed",
    )
    deferred_non_playing_body = _function_body(
        music,
        "private func deferObservedNonPlayingDuringActiveReadingBed(reason: String)",
    )

    assert "if shouldConfirmActiveNarrationNonPlayingAsReaderPause" not in observed_body
    assert "confirmActiveNarrationNonPlayingAsReaderPause(reason: \"observedNonPlaying\")" not in observed_body
    assert "private var shouldConfirmActiveNarrationNonPlayingAsReaderPause" not in music
    assert "private func confirmActiveNarrationNonPlayingAsReaderPause" not in music
    assert observed_body.index("if shouldRecoverObservedNonPlayingForReadingBed") < observed_body.index(
        "guard shouldTreatObservedNonPlayingAsReaderPause else"
    )
    assert observed_body.index("guard shouldTreatObservedNonPlayingAsReaderPause else") < observed_body.index(
        "if shouldAdoptObservedNonPlayingImmediately"
    )
    assert observed_body.index("if shouldAdoptObservedNonPlayingImmediately") < observed_body.index(
        "observedNonPlayingTask = Task"
    )
    assert "if shouldRecoverObservedNonPlayingForReadingBed" in observed_body
    ignored_gate_body = _function_body(
        music,
        "private var shouldAdoptIgnoredObservedNonPlayingAsReaderPause",
    )
    assert "ownershipState == .appleMusicBed" in ignored_gate_body
    assert "!isPausedByReaderTransport" in ignored_gate_body
    assert "isReaderNarrationActiveForMusicBed" in ignored_gate_body
    assert "!isReaderNarrationActiveForMusicBed" in ignored_gate_body
    assert "observedPlayingAsReadingBed" in ignored_gate_body
    assert "hasAutoResumeIntent" in ignored_gate_body
    assert "shouldAdoptObservedNonPlayingImmediately" in defer_body
    assert "shouldAdoptObservedNonPlayingImmediately" in recover_body
    assert "ownershipState == .appleMusicBed" in recover_body
    assert "!isManuallyPaused" in recover_body
    assert "if isReaderNarrationActiveForMusicBed" in recover_body
    assert "guard !isPausedByReaderTransport else { return false }" in recover_body
    assert "observedPlayingAsReadingBed ||" in recover_body
    assert "hasAutoResumeIntent" in recover_body
    assert "Apple Music deferred non-playing persisted while reader stayed active; keeping narration transport" in deferred_non_playing_body
    assert "self.shouldRecoverObservedNonPlayingForReadingBed" in deferred_non_playing_body
    assert "self.shouldDeferObservedNonPlayingDuringActiveReadingBed" not in deferred_non_playing_body
    assert 'source: "persistent observed non-playing"' not in deferred_non_playing_body
    assert 'adoptPauseAsReaderTransport(\n                reason: "deferredObservedNonPlaying",' not in deferred_non_playing_body
