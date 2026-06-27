from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APPLE = ROOT / "ios" / "InteractiveReader" / "InteractiveReader"
SERVICES = APPLE / "Services"
PLAYBACK = APPLE / "Features" / "Playback"
INTERACTIVE = APPLE / "Features" / "InteractivePlayer"
LIBRARY = APPLE / "Features" / "Library"
SUPPORTING = APPLE / "Supporting"
TESTING_DOC = ROOT / "docs" / "testing.md"


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


def test_now_playing_remote_commands_cover_text_video_and_bookmarks() -> None:
    coordinator = _source(SERVICES / "NowPlayingCoordinator.swift")
    audio = _source(SERVICES / "AudioPlayerCoordinator.swift")
    job_now_playing = _source(PLAYBACK / "JobPlaybackView+NowPlaying.swift")
    job_playback = _source(PLAYBACK / "JobPlaybackView.swift")
    library_now_playing = _source(PLAYBACK / "LibraryPlaybackView+NowPlaying.swift")
    library_playback = _source(PLAYBACK / "LibraryPlaybackView.swift")
    interactive_view = _source(INTERACTIVE / "InteractivePlayerView.swift")
    interactive_input = _source(INTERACTIVE / "InteractivePlayerView+InputHandlers.swift")
    video_now_playing = _source(PLAYBACK / "VideoPlayerView+NowPlaying.swift")

    assert "center.playCommand.addTarget" in coordinator
    assert "center.pauseCommand.addTarget" in coordinator
    assert "center.togglePlayPauseCommand.addTarget" in coordinator
    assert "center.nextTrackCommand.addTarget" in coordinator
    assert "center.previousTrackCommand.addTarget" in coordinator
    assert "center.changePlaybackPositionCommand.addTarget" in coordinator
    assert "center.skipForwardCommand.addTarget" in coordinator
    assert "center.skipBackwardCommand.addTarget" in coordinator
    assert "center.bookmarkCommand.addTarget" in coordinator
    assert "UIApplication.shared.beginReceivingRemoteControlEvents()" in coordinator
    assert "MPNowPlayingSession(players: [player])" in coordinator
    assert "Reader NowPlaying session attached player=true" in coordinator
    assert "nowPlayingSession.becomeActiveIfPossible" in coordinator
    assert "nowPlayingSession.nowPlayingInfoCenter.nowPlayingInfo = metadata" in coordinator
    assert "session.nowPlayingInfoCenter.nowPlayingInfo = metadata" in coordinator
    assert "nowPlayingSession.remoteCommandCenter" in coordinator
    assert "private var remoteCommandCentersForReader: [MPRemoteCommandCenter]" in coordinator
    assert "return [active, shared]" in coordinator
    assert "private func addRemoteCommandTargets(on center: MPRemoteCommandCenter)" in coordinator
    assert "configuredRemoteCommandCenters: [MPRemoteCommandCenter]" in coordinator
    assert "Reader NowPlaying session active=" in coordinator
    assert "func reassertReaderSession()" in coordinator
    assert "activateNowPlayingSessionIfPossible(forceLog: true)" in coordinator
    assert "Reader NowPlaying session reassert requested" in coordinator
    attach_body = _function_body(coordinator, "func attachPlayer(_ player: AVPlayer?)")
    assert "if attachedPlayer === player" in attach_body
    assert "if !metadata.isEmpty" in attach_body
    assert "applyNowPlaying()" in attach_body
    assert "var nowPlayingPlayer: AVPlayer?" in audio
    assert "func reassertAudioSession()" in audio

    assert "nowPlaying.attachPlayer(viewModel.audioCoordinator.nowPlayingPlayer)" in job_now_playing
    assert job_now_playing.count("nowPlaying.attachPlayer(viewModel.audioCoordinator.nowPlayingPlayer)") >= 3
    assert "onPlay: { playReaderNowPlayingTransport() }" in job_now_playing
    assert "onPause: { pauseReaderNowPlayingTransport() }" in job_now_playing
    assert "onNext: { viewModel.skipSentence(forward: true) }" in job_now_playing
    assert "onPrevious: { viewModel.skipSentence(forward: false) }" in job_now_playing
    assert "onSeek: { viewModel.audioCoordinator.seek(to: $0) }" in job_now_playing
    assert "onToggle: { toggleReaderNowPlayingTransport() }" in job_now_playing
    assert "onBookmark: { addNowPlayingBookmark() }" in job_now_playing
    assert "func playReaderNowPlayingTransport()" in job_now_playing
    assert "func pauseReaderNowPlayingTransport()" in job_now_playing
    assert "func toggleReaderNowPlayingTransport()" in job_now_playing
    assert "@State var lastReaderTransportToggleTime: TimeInterval = 0" in job_playback
    assert ".onPlayPauseCommand" in job_playback
    assert "handleTVPlayPauseCommand()" in job_playback
    assert "private func handleTVPlayPauseCommand()" in job_playback
    assert "guard !isVideoPreferred else" in job_playback
    assert "Job foreground tvOS Play/Pause command" in job_playback
    job_toggle_body = _function_body(job_now_playing, "func toggleReaderNowPlayingTransport()")
    assert "ProcessInfo.processInfo.systemUptime" in job_toggle_body
    assert "now - lastReaderTransportToggleTime >= 0.25" in job_toggle_body
    assert "lastReaderTransportToggleTime = now" in job_toggle_body
    assert "Job reader transport toggle command ignored duplicate" in job_toggle_body
    assert "resumeAppleMusicBedFromReaderTransportIfNeeded()" in job_now_playing
    assert "pauseAppleMusicBedFromReaderTransportIfNeeded()" in job_now_playing
    assert "playbackToggleOverride: {" in job_playback
    assert "toggleReaderNowPlayingTransport()" in job_playback

    assert "nowPlaying.attachPlayer(viewModel.audioCoordinator.nowPlayingPlayer)" in library_now_playing
    assert library_now_playing.count("nowPlaying.attachPlayer(viewModel.audioCoordinator.nowPlayingPlayer)") >= 3
    assert "onPlay: { playReaderNowPlayingTransport() }" in library_now_playing
    assert "onPause: { pauseReaderNowPlayingTransport() }" in library_now_playing
    assert "onNext: { viewModel.skipSentence(forward: true) }" in library_now_playing
    assert "onPrevious: { viewModel.skipSentence(forward: false) }" in library_now_playing
    assert "onSeek: { viewModel.audioCoordinator.seek(to: $0) }" in library_now_playing
    assert "onToggle: { toggleReaderNowPlayingTransport() }" in library_now_playing
    assert "onBookmark: { addNowPlayingBookmark() }" in library_now_playing
    assert "func playReaderNowPlayingTransport()" in library_now_playing
    assert "func pauseReaderNowPlayingTransport()" in library_now_playing
    assert "func toggleReaderNowPlayingTransport()" in library_now_playing
    assert "@State var lastReaderTransportToggleTime: TimeInterval = 0" in library_playback
    assert ".onPlayPauseCommand" in library_playback
    assert "handleTVPlayPauseCommand()" in library_playback
    assert "private func handleTVPlayPauseCommand()" in library_playback
    assert "guard !isVideoPreferred else" in library_playback
    assert "Library foreground tvOS Play/Pause command" in library_playback
    library_toggle_body = _function_body(library_now_playing, "func toggleReaderNowPlayingTransport()")
    assert "ProcessInfo.processInfo.systemUptime" in library_toggle_body
    assert "now - lastReaderTransportToggleTime >= 0.25" in library_toggle_body
    assert "lastReaderTransportToggleTime = now" in library_toggle_body
    assert "Library reader transport toggle command ignored duplicate" in library_toggle_body
    assert "resumeAppleMusicBedFromReaderTransportIfNeeded()" in library_now_playing
    assert "pauseAppleMusicBedFromReaderTransportIfNeeded()" in library_now_playing
    assert "playbackToggleOverride: {" in library_playback
    assert "toggleReaderNowPlayingTransport()" in library_playback

    assert "let playbackToggleOverride: (() -> Void)?" in interactive_view
    assert "playbackToggleOverride: (() -> Void)? = nil" in interactive_view
    assert "self.playbackToggleOverride = playbackToggleOverride" in interactive_view
    playback_toggle_body = _function_body(interactive_input, "func handlePlaybackToggleCommand()")
    assert "if let playbackToggleOverride" in playback_toggle_body
    assert "playbackToggleOverride()" in playback_toggle_body

    assert "onPlay: { coordinator.play() }" in video_now_playing
    assert "onPause: { coordinator.pause() }" in video_now_playing
    assert "onSeek: { coordinator.seek(to: $0) }" in video_now_playing
    assert "onToggle: { coordinator.togglePlayback() }" in video_now_playing
    assert "onSkipForward: { coordinator.skip(by: 15) }" in video_now_playing
    assert "onSkipBackward: { coordinator.skip(by: -15) }" in video_now_playing
    assert "onBookmark: { addBookmark() }" in video_now_playing
    assert "mediaType: .video" in video_now_playing


def test_now_playing_clear_resets_cached_elapsed_and_duration_state() -> None:
    coordinator = _source(SERVICES / "NowPlayingCoordinator.swift")
    playback_body = _function_body(coordinator, "func updatePlaybackState(")
    metadata_body = _function_body(coordinator, "func updateMetadata(")
    remote_body = _function_body(coordinator, "func setRemoteCommandsEnabled(_ enabled: Bool)")
    clear_body = _function_body(coordinator, "func clear()")

    assert "applyPlaybackState(isPlaying ? .playing : .paused)" in playback_body
    assert "MPNowPlayingInfoPropertyPlaybackRate" in playback_body
    assert "Reader NowPlaying transport=" in playback_body
    assert "playbackRate=" in playback_body
    assert "force=\\(force, privacy: .public)" in playback_body
    assert "Reader NowPlaying metadata published" in metadata_body
    assert "titlePresent=" in metadata_body
    assert "Reader NowPlaying remoteCommandsEnabled=" in remote_body
    assert "for center in centers" in remote_body
    assert "metadata = [:]" in clear_body
    assert "lastElapsedUpdate = -1" in clear_body
    assert "lastDuration = -1" in clear_body
    assert "lastArtworkURL = nil" in clear_body
    assert "lastLoggedTransportState = nil" in clear_body
    assert "lastLoggedRemoteCommandsEnabled = nil" in clear_body
    assert "currentPlaybackState = .unknown" in clear_body
    assert "clearNowPlayingInfo()" in clear_body
    assert "Reader NowPlaying cleared" in clear_body
    playback_state_body = _function_body(coordinator, "private func applyPlaybackState(_ state: MPNowPlayingPlaybackState)")
    assert "MPNowPlayingInfoCenter.default().playbackState = state" in playback_state_body
    assert "nowPlayingSession.nowPlayingInfoCenter.playbackState = state" in playback_state_body
    activate_body = _function_body(coordinator, "private func activateNowPlayingSessionIfPossible(forceLog: Bool = false)")
    assert "guard forceLog ||" in activate_body
    clear_info_body = _function_body(coordinator, "private func clearNowPlayingInfo()")
    assert "MPNowPlayingInfoCenter.default().nowPlayingInfo = nil" in clear_info_body
    assert "applyPlaybackState(.unknown)" in clear_info_body
    assert "nowPlayingSession.nowPlayingInfoCenter.nowPlayingInfo = nil" in clear_info_body


def test_apple_music_reading_bed_keeps_reader_now_playing_controls() -> None:
    music = _source(SERVICES / "MusicKitCoordinator.swift")
    job = _source(PLAYBACK / "JobPlaybackView.swift")
    job_now_playing = _source(PLAYBACK / "JobPlaybackView+NowPlaying.swift")
    job_loading = _source(PLAYBACK / "JobPlaybackView+Loading.swift")
    library = _source(PLAYBACK / "LibraryPlaybackView.swift")
    library_now_playing = _source(PLAYBACK / "LibraryPlaybackView+NowPlaying.swift")
    chrome = _source(PLAYBACK / "LibraryPlaybackChromeViews.swift")

    assert "case appleMusicBed" in music
    assert "@Published private(set) var playbackSurfaceRevision = 0" in music
    assert "@Published private(set) var isPausedByReaderTransport = false" in music
    assert "func updateCurrentTrackInfo(reason: String)" in music
    assert "func markPlaybackSurfaceDidChange(reason: String)" in music
    assert "private func schedulePlaybackSurfaceReassertions(reason: String)" in music
    assert "func resumeReadingBedForReaderTransport()" in music
    assert "func pauseReadingBedForReaderTransport()" in music
    assert "schedulePlaybackSurfaceReassertions(reason: \"resume\")" in music
    assert "schedulePlaybackSurfaceReassertions(reason: \"playSong\")" in music
    assert "schedulePlaybackSurfaceReassertions(reason: \"playStation\")" in music
    assert "updateCurrentTrackInfo(reason: \"\\(reason)-reader-reassert\")" in music
    assert "playbackSurfaceRevision &+= 1" in music
    assert "Apple Music playback surface changed reason=" in music
    non_playing_body = _function_body(music, "private func handleObservedNonPlayingStatus()")
    assert "isManuallyPaused = true" in non_playing_body
    assert "isPausedByReaderTransport = true" in non_playing_body
    assert "hasAutoResumeIntent = false" in non_playing_body
    assert "marking reader transport paused" in non_playing_body
    assert 'markPlaybackSurfaceDidChange(reason: "observedNonPlaying")' in non_playing_body
    assert "guard !isE2EMusicBedSyncTest else { return }" in non_playing_body
    observe_body = _function_body(music, "private func observePlaybackState()")
    assert "Apple Music observed reader transport resume from system playback" in observe_body
    assert 'markPlaybackSurfaceDidChange(reason: "observedReaderTransportResume")' in observe_body
    recovery_body = _function_body(music, "func recoverReadingBedForActiveNarration(reason: String)")
    assert "ownershipState == .appleMusicBed" in recovery_body
    assert "!isPlaying, !isManuallyPaused, !isPausedByReaderTransport" in recovery_body
    assert "guard canAutoResumeReadingBed else { return }" in recovery_body
    assert "readingBedRecoveryInterval" in recovery_body
    assert "resume(userInitiated: false)" in recovery_body
    activate_body = _function_body(music, "func activateAsReadingBed() async")
    deactivate_body = _function_body(music, "func deactivateAsReadingBed() async")
    assert "ownershipState = .appleMusicBed" in activate_body
    assert "Apple Music reading bed activating" in activate_body
    assert "Apple Music reading bed ownership=appleMusicBed" in activate_body
    assert "Apple Music reading bed deactivating" in deactivate_body
    assert "Apple Music reading bed ownership=narration" in deactivate_body
    assert "Apple Music observed playbackStatus=" in observe_body
    assert "var isBackgroundMode: Bool { ownershipState == .appleMusic || ownershipState == .appleMusicBed }" in music
    assert "func simulateReadingBedPauseForE2E()" in music
    assert "func simulateReadingBedPlayForE2E()" in music
    assert "private var isE2EMusicBedSyncTest: Bool" in music
    assert "scheduleSimulatedReadingBedPlayForE2E" not in music
    reader_pause_body = _function_body(music, "func pauseReadingBedForReaderTransport()")
    reader_resume_body = _function_body(music, "func resumeReadingBedForReaderTransport()")
    assert "if isE2EMusicBedSyncTest" in reader_pause_body
    assert "simulateReadingBedPauseForE2E()" in reader_pause_body
    assert "if isE2EMusicBedSyncTest" in reader_resume_body
    assert "simulateReadingBedPlayForE2E()" in reader_resume_body
    simulated_pause_body = _function_body(music, "func simulateReadingBedPauseForE2E()")
    assert "simulateReadingBedPlayForE2E()" not in simulated_pause_body
    assert 'ProcessInfo.processInfo.environment["E2E_MUSIC_BED_SYNC_TEST"] == "1"' in music

    ownership_body = _function_body(job, "private func handleAudioOwnershipChange(_ state: AudioOwnership)")
    assert "case .appleMusicBed:" in ownership_body
    assert "publishReaderNowPlayingSnapshot(force: true)" in ownership_body
    assert "scheduleAppleMusicBedNowPlayingReassertion()" in ownership_body
    assert "case .appleMusic:" in ownership_body
    assert "nowPlaying.setRemoteCommandsEnabled(false)" in ownership_body
    assert "nowPlaying.clear()" in ownership_body
    assert "@State var nowPlayingReassertionTask: Task<Void, Never>?" in job
    assert ".onReceive(musicOwnership.$isPlaying) { _ in handleMusicKitPlaybackSurfaceChange() }" in job
    assert ".onReceive(musicOwnership.$isManuallyPaused) { _ in handleMusicKitPlaybackSurfaceChange() }" in job
    assert ".onReceive(musicOwnership.$isPausedByReaderTransport) { _ in handleMusicKitPlaybackSurfaceChange() }" in job
    assert ".onReceive(musicOwnership.$currentSongTitle) { _ in handleMusicKitPlaybackSurfaceChange() }" in job
    assert ".onReceive(musicOwnership.$playbackSurfaceRevision) { _ in handleMusicKitPlaybackSurfaceChange() }" in job
    assert "Timer.publish(every: 0.5, on: .main, in: .common).autoconnect()" in job
    assert "handleMusicKitReadingBedWatchdogTick()" in job
    assert "func scheduleAppleMusicBedNowPlayingReassertion()" in job
    assert "let reassertionDelays: [UInt64] = [" in job
    assert "5_000_000_000" in job
    assert "while !Task.isCancelled" in job
    assert "try? await Task.sleep(nanoseconds: 2_000_000_000)" in job
    assert "private var shouldKeepReaderNowPlayingReassertionAlive: Bool" in job
    assert "private var shouldMirrorAppleMusicPauseToNarration: Bool" in job
    job_reassert_body = _function_body(job, "private var shouldKeepReaderNowPlayingReassertionAlive: Bool")
    assert "!musicOwnership.isManuallyPaused" in job_reassert_body
    assert "!musicOwnership.isPausedByReaderTransport" in job_reassert_body
    job_mirror_body = _function_body(job, "private var shouldMirrorAppleMusicPauseToNarration: Bool")
    assert "musicOwnership.isPausedByReaderTransport" in job_mirror_body
    assert "musicOwnership.isManuallyPaused" not in job_mirror_body
    assert "musicOwnership.ownershipState == .appleMusicBed &&" in job
    assert "viewModel.audioCoordinator.isPlaybackRequested" in job
    assert "musicOwnership.isPlaying" in job
    assert "private var shouldClearNowPlayingOnDisappear: Bool" in job
    assert "musicOwnership.ownershipState != .appleMusicBed" in job
    job_audio_state_body = _function_body(job, "private func handleAudioStateChange()")
    assert "guard musicOwnership.ownershipState == .appleMusicBed else { return }" in job_audio_state_body
    assert "publishReaderNowPlayingSnapshot(force: true)" in job_audio_state_body
    assert "scheduleAppleMusicBedNowPlayingReassertion()" in job_audio_state_body
    job_music_surface_body = _function_body(job, "private func handleMusicKitPlaybackSurfaceChange()")
    assert "if shouldMirrorAppleMusicPlayToNarration" in job_music_surface_body
    assert "viewModel.audioCoordinator.play()" in job_music_surface_body
    assert job_music_surface_body.index("if shouldMirrorAppleMusicPlayToNarration") < job_music_surface_body.index(
        "if shouldMirrorAppleMusicPauseToNarration"
    )
    assert "if shouldMirrorAppleMusicPauseToNarration" in job_music_surface_body
    assert "viewModel.audioCoordinator.pause()" in job_music_surface_body
    assert "return" in job_music_surface_body
    job_mirror_play_body = _function_body(job, "private var shouldMirrorAppleMusicPlayToNarration: Bool")
    assert "musicOwnership.isPlaying" in job_mirror_play_body
    assert "!musicOwnership.isManuallyPaused" in job_mirror_play_body
    assert "!musicOwnership.isPausedByReaderTransport" in job_mirror_play_body
    assert "!viewModel.audioCoordinator.isPlaybackRequested" in job_mirror_play_body
    assert "!viewModel.audioCoordinator.isPlaying" in job_mirror_play_body
    job_watchdog_body = _function_body(job, "private func handleMusicKitReadingBedWatchdogTick()")
    assert "musicOwnership.ownershipState == .appleMusicBed" in job_watchdog_body
    assert "viewModel.audioCoordinator.isPlaybackRequested || viewModel.audioCoordinator.isPlaying" in job_watchdog_body
    assert job_watchdog_body.index("if shouldMirrorAppleMusicPauseToNarration") < job_watchdog_body.index(
        "musicOwnership.reconcileReadingBedSystemPlayback()"
    )
    assert "musicOwnership.reconcileReadingBedSystemPlayback()" in job_watchdog_body
    assert 'musicOwnership.recoverReadingBedForActiveNarration(reason: "jobWatchdog")' in job_watchdog_body
    assert "viewModel.audioCoordinator.pause()" in job_watchdog_body
    job_disappear_body = _function_body(job, "private func handleJobDisappear()")
    assert "if shouldKeepReaderNowPlayingReassertionAlive" in job_disappear_body
    assert "scheduleAppleMusicBedNowPlayingReassertion()" in job_disappear_body
    assert "if shouldClearNowPlayingOnDisappear" in job_disappear_body
    assert "publishReaderNowPlayingSnapshot(force: true)" in job

    owning_body = _function_body(job, "var isAppleMusicOwningLockScreen: Bool")
    assert "musicOwnership.ownershipState == .appleMusic" in owning_body
    assert ".appleMusicBed" not in owning_body
    assert "guard !isAppleMusicOwningLockScreen else { return }" in job_now_playing
    assert "func publishReaderNowPlayingSnapshot(force: Bool = false)" in job_now_playing
    assert "viewModel.audioCoordinator.reassertAudioSession()" in job_now_playing
    assert "nowPlaying.setRemoteCommandsEnabled(true)" in job_now_playing
    assert "configureNowPlaying()" in job_now_playing
    assert "updateNowPlayingMetadata(sentenceIndex: sentenceIndex)" in job_now_playing
    assert "nowPlaying.reassertReaderSession()" in job_now_playing
    assert "musicOwnership.pauseReadingBedForReaderTransport()" in job_now_playing
    assert "musicOwnership.resumeReadingBedForReaderTransport()" in job_now_playing
    job_pause_music_body = _function_body(job_now_playing, "private func pauseAppleMusicBedFromReaderTransportIfNeeded()")
    assert "nowPlayingReassertionTask?.cancel()" in job_pause_music_body
    assert "nowPlayingReassertionTask = nil" in job_pause_music_body
    assert "scheduleAppleMusicBedNowPlayingReassertion()" in job_now_playing
    assert "if isVideoPreferred || isAppleMusicOwningLockScreen" in job_loading

    assert "@StateObject var musicOwnership = MusicKitCoordinator.shared" in library
    assert "@State var nowPlayingReassertionTask: Task<Void, Never>?" in library
    assert ".onChange(of: musicOwnership.ownershipState) { _, state in handleAudioOwnershipChange(state) }" in library
    assert ".onReceive(musicOwnership.$isPlaying) { _ in handleMusicKitPlaybackSurfaceChange() }" in library
    assert ".onReceive(musicOwnership.$isManuallyPaused) { _ in handleMusicKitPlaybackSurfaceChange() }" in library
    assert ".onReceive(musicOwnership.$isPausedByReaderTransport) { _ in handleMusicKitPlaybackSurfaceChange() }" in library
    assert ".onReceive(musicOwnership.$currentSongTitle) { _ in handleMusicKitPlaybackSurfaceChange() }" in library
    assert ".onReceive(musicOwnership.$playbackSurfaceRevision) { _ in handleMusicKitPlaybackSurfaceChange() }" in library
    assert "Timer.publish(every: 0.5, on: .main, in: .common).autoconnect()" in library
    assert "handleMusicKitReadingBedWatchdogTick()" in library
    library_ownership_body = _function_body(library, "private func handleAudioOwnershipChange(_ state: AudioOwnership)")
    assert "case .appleMusicBed:" in library_ownership_body
    assert "publishReaderNowPlayingSnapshot(force: true)" in library_ownership_body
    assert "scheduleAppleMusicBedNowPlayingReassertion()" in library_ownership_body
    assert "private var shouldKeepReaderNowPlayingReassertionAlive: Bool" in library
    assert "private var shouldMirrorAppleMusicPauseToNarration: Bool" in library
    library_reassert_body = _function_body(library, "private var shouldKeepReaderNowPlayingReassertionAlive: Bool")
    assert "!musicOwnership.isManuallyPaused" in library_reassert_body
    assert "!musicOwnership.isPausedByReaderTransport" in library_reassert_body
    library_mirror_body = _function_body(library, "private var shouldMirrorAppleMusicPauseToNarration: Bool")
    assert "musicOwnership.isPausedByReaderTransport" in library_mirror_body
    assert "musicOwnership.isManuallyPaused" not in library_mirror_body
    assert "private var shouldClearNowPlayingOnDisappear: Bool" in library
    assert "musicOwnership.ownershipState != .appleMusicBed" in library
    library_audio_state_body = _function_body(library, "private func handleAudioStateChange()")
    assert "guard musicOwnership.ownershipState == .appleMusicBed else { return }" in library_audio_state_body
    assert "publishReaderNowPlayingSnapshot(force: true)" in library_audio_state_body
    assert "scheduleAppleMusicBedNowPlayingReassertion()" in library_audio_state_body
    library_music_surface_body = _function_body(library, "private func handleMusicKitPlaybackSurfaceChange()")
    assert "if shouldMirrorAppleMusicPlayToNarration" in library_music_surface_body
    assert "viewModel.audioCoordinator.play()" in library_music_surface_body
    assert library_music_surface_body.index("if shouldMirrorAppleMusicPlayToNarration") < library_music_surface_body.index(
        "if shouldMirrorAppleMusicPauseToNarration"
    )
    assert "if shouldMirrorAppleMusicPauseToNarration" in library_music_surface_body
    assert "viewModel.audioCoordinator.pause()" in library_music_surface_body
    assert "return" in library_music_surface_body
    library_mirror_play_body = _function_body(library, "private var shouldMirrorAppleMusicPlayToNarration: Bool")
    assert "musicOwnership.isPlaying" in library_mirror_play_body
    assert "!musicOwnership.isManuallyPaused" in library_mirror_play_body
    assert "!musicOwnership.isPausedByReaderTransport" in library_mirror_play_body
    assert "!viewModel.audioCoordinator.isPlaybackRequested" in library_mirror_play_body
    assert "!viewModel.audioCoordinator.isPlaying" in library_mirror_play_body
    library_watchdog_body = _function_body(library, "private func handleMusicKitReadingBedWatchdogTick()")
    assert "musicOwnership.ownershipState == .appleMusicBed" in library_watchdog_body
    assert "viewModel.audioCoordinator.isPlaybackRequested || viewModel.audioCoordinator.isPlaying" in library_watchdog_body
    assert library_watchdog_body.index("if shouldMirrorAppleMusicPauseToNarration") < library_watchdog_body.index(
        "musicOwnership.reconcileReadingBedSystemPlayback()"
    )
    assert "musicOwnership.reconcileReadingBedSystemPlayback()" in library_watchdog_body
    assert 'musicOwnership.recoverReadingBedForActiveNarration(reason: "libraryWatchdog")' in library_watchdog_body
    assert "viewModel.audioCoordinator.pause()" in library_watchdog_body
    library_disappear_body = _function_body(library, "private func handleLibraryDisappear()")
    assert "if shouldKeepReaderNowPlayingReassertionAlive" in library_disappear_body
    assert "scheduleAppleMusicBedNowPlayingReassertion()" in library_disappear_body
    assert "if shouldClearNowPlayingOnDisappear" in library_disappear_body
    job_scene_phase_body = _function_body(job, "private func handleScenePhaseChange(_ newPhase: ScenePhase)")
    library_scene_phase_body = _function_body(library, "private func handleScenePhaseChange(_ newPhase: ScenePhase)")
    for scene_phase_body in (job_scene_phase_body, library_scene_phase_body):
        assert "musicOwnership.ownershipState == .appleMusicBed" in scene_phase_body
        assert "publishReaderNowPlayingSnapshot(force: true)" in scene_phase_body
        assert "scheduleAppleMusicBedNowPlayingReassertion()" in scene_phase_body
        assert scene_phase_body.index("publishReaderNowPlayingSnapshot(force: true)") < scene_phase_body.index(
            "guard newPhase != .active else { return }"
        )
    assert "func publishReaderNowPlayingSnapshot(force: Bool = false)" in library_now_playing
    assert "viewModel.audioCoordinator.reassertAudioSession()" in library_now_playing
    assert "updateNowPlayingMetadata(sentenceIndex: sentenceIndexTracker.value)" in library_now_playing
    assert "nowPlaying.reassertReaderSession()" in library_now_playing
    assert "musicOwnership.pauseReadingBedForReaderTransport()" in library_now_playing
    assert "musicOwnership.resumeReadingBedForReaderTransport()" in library_now_playing
    library_pause_music_body = _function_body(library_now_playing, "private func pauseAppleMusicBedFromReaderTransportIfNeeded()")
    assert "nowPlayingReassertionTask?.cancel()" in library_pause_music_body
    assert "nowPlayingReassertionTask = nil" in library_pause_music_body
    assert "scheduleAppleMusicBedNowPlayingReassertion()" in library_now_playing

    assert "struct MusicBedSyncE2EControls: View" in chrome
    assert 'ProcessInfo.processInfo.environment["E2E_MUSIC_BED_SYNC_TEST"] == "1"' in chrome
    assert 'accessibilityIdentifier("e2eMusicBedPauseButton")' in chrome
    assert 'accessibilityLabel("e2eMusicBedPauseButton")' in chrome
    assert 'accessibilityIdentifier("e2eMusicBedPlayButton")' in chrome
    assert 'accessibilityLabel("e2eMusicBedPlayButton")' in chrome
    assert 'accessibilityIdentifier("e2eMusicBedSyncStatus")' in chrome
    assert 'accessibilityLabel("e2eMusicBedSyncStatus")' in chrome
    assert 'accessibilityIdentifier("e2eMusicBedSyncControls")' in chrome
    assert "private enum MusicBedSyncE2EState" in chrome
    assert "static var didRunAutoSequence = false" in chrome
    assert "private func runAutoSequenceIfNeeded() async" in chrome
    assert "DispatchQueue.main.asyncAfter(deadline: .now() + 8.0)" in chrome
    assert "DispatchQueue.main.asyncAfter(deadline: .now() + 45.0)" in chrome
    assert "musicOwnership.simulateReadingBedPauseForE2E()" in chrome
    assert "musicOwnership.simulateReadingBedPlayForE2E()" in chrome
    assert "MusicBedSyncE2EControls(" in job
    assert "MusicBedSyncE2EControls(" in library


def test_apple_music_now_playing_device_evidence_is_documented() -> None:
    testing = TESTING_DOC.read_text(encoding="utf-8")

    assert "MPNowPlayingSession" in testing
    assert "Reader NowPlaying session attached player=true" in testing
    assert "Reader NowPlaying session active=true canBecomeActive=true" in testing
    assert "Reader NowPlaying session reassert requested" in testing
    assert "private-entitlement-gated MediaRemote playback-state\nsetter" in testing


def test_apple_music_reading_bed_uses_spoken_audio_session_while_mixing() -> None:
    audio = _source(SERVICES / "AudioPlayerCoordinator.swift")
    mixing_body = _function_body(audio, "func configureAudioSessionForMixing(")
    configure_body = _function_body(audio, "private func configureAudioSession()")

    assert "let mode: AVAudioSession.Mode = .spokenAudio" in mixing_body
    assert "let mode: AVAudioSession.Mode = .spokenAudio" in configure_body
    assert "mixing ? .default : .spokenAudio" not in audio
    assert "isMixingEnabled ? .default : .spokenAudio" not in audio
    assert "return duckOthers ? [.mixWithOthers, .duckOthers] : [.mixWithOthers]" in audio


def test_ios_declares_audio_background_mode_for_lock_screen_playback() -> None:
    info = _source(SUPPORTING / "Info.plist")

    assert "<key>UIBackgroundModes</key>" in info
    assert "<string>audio</string>" in info


def test_library_shell_exposes_cross_surface_now_playing_return_button() -> None:
    shell = _source(LIBRARY / "LibraryShellView.swift")
    button = _source(LIBRARY / "LibraryShellNowPlayingReturnButton.swift")
    library_view = _source(LIBRARY / "LibraryView.swift")
    library_loading = _source(PLAYBACK / "LibraryPlaybackView+Loading.swift")
    job_loading = _source(PLAYBACK / "JobPlaybackView+Loading.swift")
    project = _source(ROOT / "ios" / "InteractiveReader" / "InteractiveReader.xcodeproj" / "project.pbxproj")

    assert "private enum NowPlayingPlaybackTarget: Hashable" in shell
    assert "@State private var nowPlayingTargetSnapshot: NowPlayingPlaybackTarget?" in shell
    assert "@FocusState private var isNowPlayingReturnFocused: Bool" in shell
    assert "@FocusState private var isNowPlayingReturnOverlayFocused: Bool" in shell
    assert "private var nowPlayingTarget: NowPlayingPlaybackTarget?" in shell
    assert "if let nowPlayingTargetSnapshot" in shell
    assert "private var shouldShowNowPlayingReturnButton: Bool" in shell
    assert "private var shouldShowNowPlayingReturnOverlay: Bool" in shell
    assert "private var shouldShowNowPlayingReturnOverlay: Bool" in shell
    overlay_body = _function_body(shell, "private var shouldShowNowPlayingReturnOverlay: Bool")
    assert "#if os(tvOS)" in overlay_body
    assert "return navigationPath.isEmpty" in overlay_body
    assert "#else\n        return false" in overlay_body
    assert "private var shouldFocusNowPlayingReturn: Bool" in shell
    assert "shouldShowNowPlayingReturnButton || shouldShowNowPlayingReturnOverlay" in shell
    return_visibility_body = _function_body(shell, "private var shouldShowNowPlayingReturnButton: Bool")
    assert "#if os(tvOS)" in return_visibility_body
    assert "return false" in return_visibility_body
    assert "if !isSplitLayout { return true }" in return_visibility_body
    assert "case .create, .settings, .search:" in return_visibility_body
    assert "case .jobs, .library:" in return_visibility_body
    assert "ZStack(alignment: .bottom)" in shell
    assert "private var nowPlayingReturnHorizontalPadding: CGFloat" in shell
    assert "return isCompactLayout ? 16 : 12" in shell
    assert "private var nowPlayingReturnTopPadding: CGFloat" in shell
    assert "nowPlayingReturnButton(for: nowPlayingTarget)" in shell
    assert ".focused($isNowPlayingReturnFocused)" in shell
    assert "#if os(tvOS)\n            if let nowPlayingTarget" not in shell
    assert "#if os(tvOS)\n    private func nowPlayingReturnButton" not in shell
    assert ".frame(maxWidth: 720)" not in shell
    assert "LibraryShellNowPlayingReturnButton(" in shell
    assert "LibraryShellNowPlayingMiniButton(" in shell
    assert "private func nowPlayingReturnOverlay(for target: NowPlayingPlaybackTarget) -> some View" in shell
    assert 'accessibilityIdentifier: "nowPlayingReturnButton"' in shell
    assert '.focused($isNowPlayingReturnOverlayFocused)' in shell
    assert ".padding(.horizontal, 72)" in shell
    assert ".padding(.bottom, 46)" in shell
    assert "struct LibraryShellNowPlayingReturnButton: View" in button
    assert "struct LibraryShellNowPlayingMiniButton: View" in button
    assert "let title: String" in button
    assert "let subtitle: String?" in button
    assert "let horizontalPadding: CGFloat" in button
    assert "let topPadding: CGFloat" in button
    assert "let action: () -> Void" in button
    assert 'Image(systemName: "arrow.uturn.backward.circle.fill")' in button
    assert 'Text("Return to Now Playing")' in button
    assert '.accessibilityLabel("Return to Now Playing")' in button
    assert ".accessibilityValue(title)" in button
    assert '.accessibilityIdentifier("nowPlayingReturnButton")' in button
    assert 'Image(systemName: "waveform.circle.fill")' in button
    assert 'Text("Now Playing")' in button
    assert 'Text("Open")' in button
    assert 'Image(systemName: "chevron.right.circle.fill")' in button
    assert ".frame(minWidth: 520, maxWidth: 780, alignment: .leading)" in button
    assert 'var accessibilityIdentifier = "nowPlayingMiniReturnButton"' in button
    assert ".accessibilityIdentifier(accessibilityIdentifier)" in button

    select_item_body = _function_body(shell, "private func selectLibraryItem(_ item: LibraryItem, mode: PlaybackStartMode)")
    assert "selectedItem = item" in select_item_body
    assert "selectedJob = nil" in select_item_body
    assert "rememberNowPlaying(.library(item))" in select_item_body

    select_job_body = _function_body(shell, "private func selectJob(_ job: PipelineStatusResponse, mode: PlaybackStartMode)")
    assert "selectedJob = job" in select_job_body
    assert "selectedItem = nil" in select_job_body
    assert "rememberNowPlaying(.job(job))" in select_job_body

    navigate_job_body = _function_body(shell, "private func navigateToJob(_ job: PipelineStatusResponse, autoPlay: Bool)")
    assert "selectedJob = job" in navigate_job_body
    assert "selectedItem = nil" in navigate_job_body
    assert "rememberNowPlaying(.job(job))" in navigate_job_body

    navigate_item_body = _function_body(shell, "private func navigateToLibraryItem(_ item: LibraryItem, autoPlay: Bool)")
    assert "selectedItem = item" in navigate_item_body
    assert "selectedJob = nil" in navigate_item_body
    assert "rememberNowPlaying(.library(item))" in navigate_item_body

    return_body = _function_body(shell, "private func returnToNowPlaying()")
    assert "rememberNowPlaying(nowPlayingTarget)" in return_body
    assert "navigationPath = NavigationPath()" in return_body
    assert "case .library(let item):" in return_body
    assert "selectedItem = item" in return_body
    assert "selectedJob = nil" in return_body
    assert "case .job(let job):" in return_body
    assert "selectedJob = job" in return_body
    assert "selectedItem = nil" in return_body
    assert "libraryAutoPlay = true" in return_body
    assert "libraryPlaybackMode = .resumeExisting" in return_body
    assert "jobsAutoPlay = true" in return_body
    assert "jobsPlaybackMode = .resumeExisting" in return_body
    assert "if isSplitLayout" in return_body
    assert "collapseSidebar()" in return_body
    assert "navigationPath.append(item)" in return_body
    assert "navigationPath.append(job)" in return_body
    assert "case resumeExisting" in library_view
    assert "case .resumeExisting:" in library_loading
    assert "case .resumeExisting:" in job_loading
    library_resume_existing = library_loading.split("case .resumeExisting:", 1)[1].split("case .startOver:", 1)[0]
    job_resume_existing = job_loading.split("case .resumeExisting:", 1)[1].split("case .startOver:", 1)[0]
    assert "applyResume(resumeEntry)" in library_resume_existing
    assert "startPlaybackFromBeginning()" not in library_resume_existing
    assert "applyResume(resumeEntry)" in job_resume_existing
    assert "startPlaybackFromBeginning()" not in job_resume_existing

    focus_body = _function_body(shell, "private func focusNowPlayingReturnIfNeeded()")
    assert "guard shouldFocusNowPlayingReturn, nowPlayingTarget != nil else { return }" in focus_body
    assert "#if os(tvOS)" in focus_body
    assert "if shouldShowNowPlayingReturnOverlay" in focus_body
    assert "isNowPlayingReturnOverlayFocused = true" in focus_body
    assert "isNowPlayingReturnFocused = true" in focus_body

    depth_body = _function_body(shell, "private func handleNavigationDepthChange(_ newValue: Int)")
    assert "guard newValue == 0 else { return }" in depth_body
    assert "focusNowPlayingReturnIfNeeded()" in depth_body

    assert "LibraryShellNowPlayingReturnButton.swift in Sources" in project
    assert project.count("LibraryShellNowPlayingReturnButton.swift in Sources") == 4
