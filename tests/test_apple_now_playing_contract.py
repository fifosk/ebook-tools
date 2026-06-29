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
    transport_resolver = _source(PLAYBACK / "ReaderTransportCommandResolver.swift")
    interactive_view = _source(INTERACTIVE / "InteractivePlayerView.swift")
    interactive_input = _source(INTERACTIVE / "InteractivePlayerView+InputHandlers.swift")
    interactive_layout = _source(INTERACTIVE / "InteractivePlayerView+Layout.swift")
    interactive_e2e = _source(INTERACTIVE / "InteractivePlayerView+E2E.swift")
    interactive_transcript = _source(INTERACTIVE / "InteractivePlayerView+Transcript.swift")
    video_now_playing = _source(PLAYBACK / "VideoPlayerView+NowPlaying.swift")
    video_playback = _source(PLAYBACK / "VideoPlayerView+Playback.swift")
    music = _source(SERVICES / "MusicKitCoordinator.swift")

    system_playing_body = _function_body(music, "var isSystemPlaybackPlaying: Bool")
    assert "ApplicationMusicPlayer.shared.state.playbackStatus == .playing" in system_playing_body
    assert "#if canImport(MusicKit)" in system_playing_body
    assert "isPlaying" in system_playing_body

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
    assert "remoteCommandTargetRegistrations: [RemoteCommandTargetRegistration]" in coordinator
    assert "private final class RemoteCommandTargetRegistration" in coordinator
    assert "private func removeRemoteCommandTargets(on centers: [MPRemoteCommandCenter]? = nil)" in coordinator
    assert "removeRemoteCommandTargets()" in coordinator
    assert "removeRemoteCommandTargets(on: staleCenters)" in coordinator
    assert "registration.command.removeTarget(registration.target)" in coordinator
    assert "Reader NowPlaying session active=" in coordinator
    assert "func reassertReaderSession()" in coordinator
    assert "activateNowPlayingSessionIfPossible(forceLog: true)" in coordinator
    assert "Reader NowPlaying session reassert requested" in coordinator
    attach_body = _function_body(coordinator, "func attachPlayer(_ player: AVPlayer?)")
    assert "if attachedPlayer === player" in attach_body
    assert "if !metadata.isEmpty" in attach_body
    assert "applyNowPlaying()" in attach_body
    assert "removeRemoteCommandTargets()" in attach_body
    assert "var nowPlayingPlayer: AVPlayer?" in audio
    assert "func reassertAudioSession(force: Bool = false)" in audio
    reassert_body = _function_body(audio, "func reassertAudioSession(")
    assert "configureAudioSession(force: force)" in reassert_body
    assert (
        ".onPlayPauseCommand {\n"
        "                guard playbackToggleOverride == nil else { return }\n"
        "                handlePlaybackToggleCommand()"
    ) in interactive_view

    assert "nowPlaying.attachPlayer(viewModel.audioCoordinator.nowPlayingPlayer)" in job_now_playing
    assert job_now_playing.count("nowPlaying.attachPlayer(viewModel.audioCoordinator.nowPlayingPlayer)") >= 3
    assert "onPlay: { playReaderNowPlayingTransport() }" in job_now_playing
    assert "onPause: { pauseReaderNowPlayingTransport() }" in job_now_playing
    assert "onNext: { skipReaderSentence(forward: true) }" in job_now_playing
    assert "onPrevious: { skipReaderSentence(forward: false) }" in job_now_playing
    assert "onSkipForward: { skipReaderSentence(forward: true) }" in job_now_playing
    assert "onSkipBackward: { skipReaderSentence(forward: false) }" in job_now_playing
    assert "onSeek: { viewModel.audioCoordinator.seek(to: $0) }" in job_now_playing
    assert "onToggle: { toggleReaderNowPlayingTransport() }" in job_now_playing
    assert "onBookmark: { addNowPlayingBookmark() }" in job_now_playing
    job_skip_body = _function_body(job_now_playing, "func skipReaderSentence(forward: Bool)")
    assert "anchorSentenceNumber: sentenceIndex" in job_skip_body
    assert "func playReaderNowPlayingTransport()" in job_now_playing
    assert "func pauseReaderNowPlayingTransport()" in job_now_playing
    assert 'func toggleReaderNowPlayingTransport(source: String = "toggle")' in job_now_playing
    assert "@State var lastReaderTransportCommandTime: TimeInterval = 0" in job_playback
    assert '@State var lastReaderTransportAction = "none"' in job_playback
    assert "@State var localReaderTransportPauseHoldUntil: TimeInterval = 0" in job_playback
    assert ".onPlayPauseCommand" in job_playback
    assert "handleTVPlayPauseCommand()" in job_playback
    assert ".onReceive(NotificationCenter.default.publisher(for: .keyboardShortcutPlayPause))" in job_playback
    assert "handleTVBrokerPlayPauseCommand()" in job_playback
    assert "private func handleTVPlayPauseCommand()" in job_playback
    assert "private func handleTVBrokerPlayPauseCommand()" in job_playback
    assert "guard !isVideoPreferred else" in job_playback
    assert "Job foreground tvOS Play/Pause command" in job_playback
    assert "Job broker tvOS Play/Pause command" in job_playback
    assert "shouldIgnoreTVReaderTransportBrokerEcho()" in job_playback
    assert "Job broker tvOS Play/Pause ignored reader transport pause echo" in job_playback
    assert "if shouldForceTVReaderNowPlayingPause()" in job_playback
    assert 'forcePauseReaderNowPlayingTransport(source: "foreground")' in job_playback
    assert 'forcePauseReaderNowPlayingTransport(source: "broker")' in job_playback
    assert 'toggleReaderNowPlayingTransport(source: "foreground")' in job_playback
    assert "@State var e2eReaderTransportCommandCount = 0" in job_playback
    assert "e2eReaderTransportCommandCount += 1" in job_now_playing
    assert "readerTransportCommandCount: e2eReaderTransportCommandCount" in job_playback
    assert "@State var e2eTVPlayPauseCommandCount = 0" in job_playback
    assert "e2eTVPlayPauseCommandCount += 1" in job_playback
    assert "foregroundPlayPauseCount: e2eTVPlayPauseCommandCount" in job_playback
    assert "lastReaderTransportAction: lastReaderTransportAction" in job_playback
    assert "onReaderPlayCommand: { playReaderNowPlayingTransport() }" in job_playback
    assert "onReaderPauseCommand: { pauseReaderNowPlayingTransport() }" in job_playback
    job_toggle_body = _function_body(job_now_playing, "func toggleReaderNowPlayingTransport(source: String = \"toggle\")")
    job_accept_body = _function_body(job_now_playing, "private func shouldAcceptReaderTransportCommand(_ command: String, resolvedAction: String)")
    assert "ProcessInfo.processInfo.systemUptime" in job_accept_body
    assert "ReaderTransportCommandResolver.shouldReapplyDuplicateCommand" in job_accept_body
    assert "ReaderTransportCommandResolver.shouldRejectDuplicateCommand" in job_accept_body
    assert "shouldBlockReaderTransportResumeAfterPause(resolvedAction: resolvedAction, elapsed: elapsed, now: now)" in job_accept_body
    assert "Job reader transport \\(command, privacy: .public) command ignored reader-pause-guard" in job_accept_body
    assert "command reapplying duplicate action=" in job_accept_body
    assert "lastReaderTransportCommandTime = now" in job_accept_body
    assert "lastReaderTransportAction = resolvedAction" in job_accept_body
    assert "Job reader transport \\(command, privacy: .public) command ignored duplicate action=" in job_accept_body
    job_block_resume_body = _function_body(
        job_now_playing,
        "private func shouldBlockReaderTransportResumeAfterPause",
    )
    assert "ReaderTransportCommandResolver.shouldHoldReaderResumeAfterPause" in job_block_resume_body
    assert 'guard resolvedAction == "play" else { return false }' in job_block_resume_body
    assert 'guard lastReaderTransportAction != "pause" || elapsed < readerTransportDuplicateWindow else' not in job_block_resume_body
    assert "now < localReaderTransportPauseHoldUntil" in job_block_resume_body
    assert "musicOwnership.shouldRejectReaderTransportResumeAfterPause" in job_block_resume_body
    assert "musicOwnership.isReaderTransportPauseHoldWindowActive" in job_block_resume_body
    job_reinforce_body = _function_body(
        job_now_playing,
        "private func reinforceReaderTransportPauseIfNeeded(command: String, resolvedAction: String)",
    )
    assert "ReaderTransportCommandResolver.shouldHoldReaderResumeAfterPause" in job_reinforce_body
    assert 'resolvedAction == "play"' in job_reinforce_body
    assert "musicOwnership.ownershipState == .appleMusicBed" in job_reinforce_body
    assert 'lastReaderTransportAction == "pause" &&' in job_reinforce_body
    assert "now >= localReaderTransportPauseHoldUntil" in job_reinforce_body
    assert "!musicOwnership.shouldRejectReaderTransportResumeAfterPause" in job_reinforce_body
    assert "!musicOwnership.isReaderTransportPauseHoldWindowActive" in job_reinforce_body
    assert "!shouldAllowPostPauseResume" in job_reinforce_body
    assert "now < localReaderTransportPauseHoldUntil" in job_reinforce_body
    assert "musicOwnership.shouldRejectReaderTransportResumeAfterPause" in job_reinforce_body
    assert "musicOwnership.isReaderTransportPauseGuardActive" in job_reinforce_body
    assert "rejected play reinforced pause" in job_reinforce_body
    assert "musicOwnership.isSystemPlaybackPlaying" in job_reinforce_body
    assert "pauseAppleMusicBedFromReaderTransportIfNeeded()" in job_reinforce_body
    assert "viewModel.pauseForReaderTransport()" in job_reinforce_body
    assert "publishReaderNowPlayingSnapshot(force: true)" in job_reinforce_body
    assert "localReaderTransportPauseHoldUntil = 0" in job_now_playing
    assert "localReaderTransportPauseHoldUntil = ProcessInfo.processInfo.systemUptime + ReaderTransportCommandResolver.pauseHoldWindow" in job_now_playing
    assert "ReaderTransportCommandResolver.duplicateWindow" in job_now_playing
    job_force_pause_body = _function_body(job_now_playing, "func shouldForceTVReaderNowPlayingPause()")
    assert "viewModel.audioCoordinator.isPlaybackRequested" in job_force_pause_body
    assert "viewModel.audioCoordinator.isPlaying" in job_force_pause_body
    assert "musicOwnership.ownershipState == .appleMusicBed" in job_force_pause_body
    assert "!musicOwnership.isPausedByReaderTransport" in job_force_pause_body
    assert "!musicOwnership.isManuallyPaused" in job_force_pause_body
    job_forced_transport_body = _function_body(job_now_playing, "func forcePauseReaderNowPlayingTransport(source: String)")
    assert 'lastReaderTransportAction = "pause"' in job_forced_transport_body
    assert "performReaderNowPlayingPauseTransport()" in job_forced_transport_body
    job_broker_echo_body = _function_body(job_now_playing, "func shouldIgnoreTVReaderTransportBrokerEcho()")
    assert "let elapsed = ProcessInfo.processInfo.systemUptime - lastReaderTransportCommandTime" in job_broker_echo_body
    assert "ReaderTransportCommandResolver.shouldHoldReaderResumeAfterPause" in job_broker_echo_body
    assert 'lastReaderTransportAction == "pause"' in job_broker_echo_body
    assert "elapsed < ReaderTransportCommandResolver.brokerEchoWindow" in job_broker_echo_body
    assert "musicOwnership.isReaderTransportPauseGuardActive" in job_broker_echo_body
    assert "static func shouldReapplyDuplicateCommand" in transport_resolver
    assert "static func shouldRejectDuplicateCommand" in transport_resolver
    assert "static var brokerEchoWindow: TimeInterval" in transport_resolver
    broker_echo_window_body = _function_body(transport_resolver, "static var brokerEchoWindow: TimeInterval")
    assert "return 2.5" in broker_echo_window_body
    assert "static var shouldHoldReaderResumeAfterPause: Bool" in transport_resolver
    resume_hold_body = _function_body(transport_resolver, "static var shouldHoldReaderResumeAfterPause: Bool")
    assert "#if os(tvOS)" in resume_hold_body
    assert "return true" in resume_hold_body
    assert "return false" in resume_hold_body
    assert "resolvedAction == previousAction" in transport_resolver
    assert "resolvedAction != previousAction" in transport_resolver
    assert "return 1.25" in transport_resolver
    assert "return 0.25" in transport_resolver
    assert "command == \"toggle\"" in transport_resolver
    assert "ownershipState == .appleMusicBed" in transport_resolver
    assert "#if os(tvOS)" in transport_resolver
    resolver_body = _function_body(transport_resolver, "static func resolvedAction(")
    tvos_resolver_body = resolver_body[
        resolver_body.index("#if os(tvOS)") : resolver_body.index("#endif", resolver_body.index("#if os(tvOS)"))
    ]
    assert "if command == \"pause\"" in tvos_resolver_body
    assert "return \"pause\"" in tvos_resolver_body
    assert "if command == \"play\" || command == \"toggle\"" in tvos_resolver_body
    assert "guard command == \"toggle\" else { return command }" in transport_resolver
    job_play_body = _function_body(job_now_playing, "func playReaderNowPlayingTransport()")
    job_pause_body = _function_body(job_now_playing, "func pauseReaderNowPlayingTransport()")
    assert 'let resolvedAction = resolvedReaderTransportAction(forCommand: "play")' in job_play_body
    assert 'guard shouldAcceptReaderTransportCommand("play", resolvedAction: resolvedAction) else' in job_play_body
    assert 'reinforceReaderTransportPauseIfNeeded(command: "play", resolvedAction: resolvedAction)' in job_play_body
    assert 'let resolvedAction = resolvedReaderTransportAction(forCommand: "pause")' in job_pause_body
    assert 'guard shouldAcceptReaderTransportCommand("pause", resolvedAction: resolvedAction) else' in job_pause_body
    assert 'reinforceReaderTransportPauseIfNeeded(command: "pause", resolvedAction: resolvedAction)' in job_pause_body
    assert 'let resolvedAction = resolvedReaderTransportAction(forCommand: "toggle")' in job_toggle_body
    assert "guard shouldAcceptReaderTransportCommand(source, resolvedAction: resolvedAction) else" in job_toggle_body
    assert "reinforceReaderTransportPauseIfNeeded(command: source, resolvedAction: resolvedAction)" in job_toggle_body
    assert "let shouldPause = shouldPauseReaderTransportForToggle" not in job_toggle_body
    assert "private func resolvedReaderTransportAction(forCommand command: String) -> String" in job_now_playing
    assert "performReaderNowPlayingPlayTransport()" in job_now_playing
    assert "performReaderNowPlayingPauseTransport()" in job_now_playing
    assert "resumeAppleMusicBedFromReaderTransportIfNeeded()" in job_now_playing
    assert "pauseAppleMusicBedFromReaderTransportIfNeeded()" in job_now_playing
    job_perform_play_body = _function_body(job_now_playing, "private func performReaderNowPlayingPlayTransport()")
    assert "viewModel.playForReaderTransport()" in job_perform_play_body
    assert "scheduleReaderTransportPlaybackRecovery()" in job_perform_play_body
    assert "recoverReaderTransportPlaybackIfNeeded()" not in job_perform_play_body
    assert job_perform_play_body.index("viewModel.playForReaderTransport()") < job_perform_play_body.index(
        "resumeAppleMusicBedFromReaderTransportIfNeeded()"
    )
    assert job_perform_play_body.index("resumeAppleMusicBedFromReaderTransportIfNeeded()") < job_perform_play_body.index(
        "scheduleReaderTransportPlaybackRecovery()"
    )
    assert "viewModel.audioCoordinator.play()" not in job_perform_play_body
    job_recover_body = _function_body(job_now_playing, "private func recoverReaderTransportPlaybackIfNeeded()")
    assert "guard !isVideoPreferred else { return }" in job_recover_body
    assert "guard !viewModel.audioCoordinator.isPlaying else { return }" in job_recover_body
    assert "guard !viewModel.audioCoordinator.isPlaybackRequested else { return }" not in job_recover_body
    assert "if canResumeReaderTransportInPlace" in job_recover_body
    assert "Job reader transport in-place recovery requested=" in job_recover_body
    assert job_recover_body.index("viewModel.playForReaderTransport()") < job_recover_body.index(
        "startInteractivePlayback(at: sentenceIndex ?? firstInteractiveSentenceNumber())"
    )
    assert "private var canResumeReaderTransportInPlace: Bool" in job_now_playing
    assert "viewModel.audioCoordinator.nowPlayingPlayer != nil" in job_now_playing
    assert "viewModel.audioCoordinator.activeURL != nil" in job_now_playing
    assert "!viewModel.audioCoordinator.activeURLs.isEmpty" in job_now_playing
    assert "Job reader transport recovery requested=" in job_recover_body
    assert "startInteractivePlayback(at: sentenceIndex ?? firstInteractiveSentenceNumber())" in job_recover_body
    job_recovery_schedule_body = _function_body(job_now_playing, "private func scheduleReaderTransportPlaybackRecovery()")
    assert "cancelReaderTransportPlaybackRecovery()" in job_recovery_schedule_body
    assert "let scheduledAction = lastReaderTransportAction" in job_recovery_schedule_body
    assert "readerTransportPlaybackRecoveryTask = Task" in job_recovery_schedule_body
    assert "defer { readerTransportPlaybackRecoveryTask = nil }" in job_recovery_schedule_body
    assert "for delay in [180_000_000, 600_000_000, 1_200_000_000] as [UInt64]" in job_recovery_schedule_body
    assert "guard !Task.isCancelled else { return }" in job_recovery_schedule_body
    assert 'guard lastReaderTransportAction == scheduledAction, scheduledAction == "play" else { return }' in job_recovery_schedule_body
    assert "if viewModel.audioCoordinator.isPlaying" in job_recovery_schedule_body
    assert "viewModel.audioCoordinator.isPlaybackRequested || viewModel.audioCoordinator.isPlaying" not in job_recovery_schedule_body
    assert "recoverReaderTransportPlaybackIfNeeded()" in job_recovery_schedule_body
    assert "func cancelReaderTransportPlaybackRecovery()" in job_now_playing
    job_perform_pause_body = _function_body(job_now_playing, "private func performReaderNowPlayingPauseTransport()")
    assert "cancelReaderTransportPlaybackRecovery()" in job_perform_pause_body
    assert "viewModel.pauseForReaderTransport()" in job_perform_pause_body
    assert job_perform_pause_body.index("pauseAppleMusicBedFromReaderTransportIfNeeded()") < job_perform_pause_body.index(
        "viewModel.pauseForReaderTransport()"
    )
    assert job_perform_pause_body.count("publishReaderNowPlayingSnapshot(force: true)") == 1
    assert job_perform_pause_body.index(
        "pauseAppleMusicBedFromReaderTransportIfNeeded()"
    ) < job_perform_pause_body.index(
        "publishReaderNowPlayingSnapshot(force: true)"
    )
    job_interactive_toggle_body = _function_body(job_now_playing, "func toggleInteractiveReaderPlaybackTransport()")
    assert "musicOwnership.isPausedByReaderTransport" in job_interactive_toggle_body
    assert "!viewModel.audioCoordinator.isPlaying" in job_interactive_toggle_body
    assert "playReaderNowPlayingTransport()" in job_interactive_toggle_body
    assert "playbackToggleOverride: {" in job_playback
    assert "toggleInteractiveReaderPlaybackTransport()" in job_playback

    assert "nowPlaying.attachPlayer(viewModel.audioCoordinator.nowPlayingPlayer)" in library_now_playing
    assert library_now_playing.count("nowPlaying.attachPlayer(viewModel.audioCoordinator.nowPlayingPlayer)") >= 3
    assert "onPlay: { playReaderNowPlayingTransport() }" in library_now_playing
    assert "onPause: { pauseReaderNowPlayingTransport() }" in library_now_playing
    assert "onNext: { skipReaderSentence(forward: true) }" in library_now_playing
    assert "onPrevious: { skipReaderSentence(forward: false) }" in library_now_playing
    assert "onSkipForward: { skipReaderSentence(forward: true) }" in library_now_playing
    assert "onSkipBackward: { skipReaderSentence(forward: false) }" in library_now_playing
    assert "onSeek: { viewModel.audioCoordinator.seek(to: $0) }" in library_now_playing
    assert "onToggle: { toggleReaderNowPlayingTransport() }" in library_now_playing
    assert "onBookmark: { addNowPlayingBookmark() }" in library_now_playing
    library_skip_body = _function_body(library_now_playing, "func skipReaderSentence(forward: Bool)")
    assert "anchorSentenceNumber: sentenceIndexTracker.value" in library_skip_body
    assert "func playReaderNowPlayingTransport()" in library_now_playing
    assert "func pauseReaderNowPlayingTransport()" in library_now_playing
    assert 'func toggleReaderNowPlayingTransport(source: String = "toggle")' in library_now_playing
    assert "@State var lastReaderTransportCommandTime: TimeInterval = 0" in library_playback
    assert '@State var lastReaderTransportAction = "none"' in library_playback
    assert "@State var localReaderTransportPauseHoldUntil: TimeInterval = 0" in library_playback
    assert ".onPlayPauseCommand" in library_playback
    assert "handleTVPlayPauseCommand()" in library_playback
    assert ".onReceive(NotificationCenter.default.publisher(for: .keyboardShortcutPlayPause))" in library_playback
    assert "handleTVBrokerPlayPauseCommand()" in library_playback
    assert "private func handleTVPlayPauseCommand()" in library_playback
    assert "private func handleTVBrokerPlayPauseCommand()" in library_playback
    assert "guard !isVideoPreferred else" in library_playback
    assert "Library foreground tvOS Play/Pause command" in library_playback
    assert "Library broker tvOS Play/Pause command" in library_playback
    assert "shouldIgnoreTVReaderTransportBrokerEcho()" in library_playback
    assert "Library broker tvOS Play/Pause ignored reader transport pause echo" in library_playback
    assert "if shouldForceTVReaderNowPlayingPause()" in library_playback
    assert 'forcePauseReaderNowPlayingTransport(source: "foreground")' in library_playback
    assert 'forcePauseReaderNowPlayingTransport(source: "broker")' in library_playback
    assert 'toggleReaderNowPlayingTransport(source: "foreground")' in library_playback
    assert "@State var e2eReaderTransportCommandCount = 0" in library_playback
    assert "e2eReaderTransportCommandCount += 1" in library_now_playing
    assert "readerTransportCommandCount: e2eReaderTransportCommandCount" in library_playback
    assert "@State var e2eTVPlayPauseCommandCount = 0" in library_playback
    assert "e2eTVPlayPauseCommandCount += 1" in library_playback
    assert "foregroundPlayPauseCount: e2eTVPlayPauseCommandCount" in library_playback
    assert "lastReaderTransportAction: lastReaderTransportAction" in library_playback
    assert "onReaderPlayCommand: { playReaderNowPlayingTransport() }" in library_playback
    assert "onReaderPauseCommand: { pauseReaderNowPlayingTransport() }" in library_playback
    library_toggle_body = _function_body(library_now_playing, "func toggleReaderNowPlayingTransport(source: String = \"toggle\")")
    library_accept_body = _function_body(library_now_playing, "private func shouldAcceptReaderTransportCommand(_ command: String, resolvedAction: String)")
    assert "ProcessInfo.processInfo.systemUptime" in library_accept_body
    assert "ReaderTransportCommandResolver.shouldReapplyDuplicateCommand" in library_accept_body
    assert "ReaderTransportCommandResolver.shouldRejectDuplicateCommand" in library_accept_body
    assert "shouldBlockReaderTransportResumeAfterPause(resolvedAction: resolvedAction, elapsed: elapsed, now: now)" in library_accept_body
    assert "Library reader transport \\(command, privacy: .public) command ignored reader-pause-guard" in library_accept_body
    assert "command reapplying duplicate action=" in library_accept_body
    assert "lastReaderTransportCommandTime = now" in library_accept_body
    assert "lastReaderTransportAction = resolvedAction" in library_accept_body
    assert "Library reader transport \\(command, privacy: .public) command ignored duplicate action=" in library_accept_body
    library_block_resume_body = _function_body(
        library_now_playing,
        "private func shouldBlockReaderTransportResumeAfterPause",
    )
    assert "ReaderTransportCommandResolver.shouldHoldReaderResumeAfterPause" in library_block_resume_body
    assert 'guard resolvedAction == "play" else { return false }' in library_block_resume_body
    assert 'guard lastReaderTransportAction != "pause" || elapsed < readerTransportDuplicateWindow else' not in library_block_resume_body
    assert "now < localReaderTransportPauseHoldUntil" in library_block_resume_body
    assert "musicOwnership.shouldRejectReaderTransportResumeAfterPause" in library_block_resume_body
    assert "musicOwnership.isReaderTransportPauseHoldWindowActive" in library_block_resume_body
    library_reinforce_body = _function_body(
        library_now_playing,
        "private func reinforceReaderTransportPauseIfNeeded(command: String, resolvedAction: String)",
    )
    assert "ReaderTransportCommandResolver.shouldHoldReaderResumeAfterPause" in library_reinforce_body
    assert 'resolvedAction == "play"' in library_reinforce_body
    assert "musicOwnership.ownershipState == .appleMusicBed" in library_reinforce_body
    assert 'lastReaderTransportAction == "pause" &&' in library_reinforce_body
    assert "now >= localReaderTransportPauseHoldUntil" in library_reinforce_body
    assert "!musicOwnership.shouldRejectReaderTransportResumeAfterPause" in library_reinforce_body
    assert "!musicOwnership.isReaderTransportPauseHoldWindowActive" in library_reinforce_body
    assert "!shouldAllowPostPauseResume" in library_reinforce_body
    assert "now < localReaderTransportPauseHoldUntil" in library_reinforce_body
    assert "musicOwnership.shouldRejectReaderTransportResumeAfterPause" in library_reinforce_body
    assert "musicOwnership.isReaderTransportPauseGuardActive" in library_reinforce_body
    assert "rejected play reinforced pause" in library_reinforce_body
    assert "musicOwnership.isSystemPlaybackPlaying" in library_reinforce_body
    assert "pauseAppleMusicBedFromReaderTransportIfNeeded()" in library_reinforce_body
    assert "viewModel.pauseForReaderTransport()" in library_reinforce_body
    assert "publishReaderNowPlayingSnapshot(force: true)" in library_reinforce_body
    assert "localReaderTransportPauseHoldUntil = 0" in library_now_playing
    assert "localReaderTransportPauseHoldUntil = ProcessInfo.processInfo.systemUptime + ReaderTransportCommandResolver.pauseHoldWindow" in library_now_playing
    assert "ReaderTransportCommandResolver.duplicateWindow" in library_now_playing
    library_force_pause_body = _function_body(library_now_playing, "func shouldForceTVReaderNowPlayingPause()")
    assert "viewModel.audioCoordinator.isPlaybackRequested" in library_force_pause_body
    assert "viewModel.audioCoordinator.isPlaying" in library_force_pause_body
    assert "musicOwnership.ownershipState == .appleMusicBed" in library_force_pause_body
    assert "!musicOwnership.isPausedByReaderTransport" in library_force_pause_body
    assert "!musicOwnership.isManuallyPaused" in library_force_pause_body
    library_forced_transport_body = _function_body(library_now_playing, "func forcePauseReaderNowPlayingTransport(source: String)")
    assert 'lastReaderTransportAction = "pause"' in library_forced_transport_body
    assert "performReaderNowPlayingPauseTransport()" in library_forced_transport_body
    library_broker_echo_body = _function_body(library_now_playing, "func shouldIgnoreTVReaderTransportBrokerEcho()")
    assert "let elapsed = ProcessInfo.processInfo.systemUptime - lastReaderTransportCommandTime" in library_broker_echo_body
    assert "ReaderTransportCommandResolver.shouldHoldReaderResumeAfterPause" in library_broker_echo_body
    assert 'lastReaderTransportAction == "pause"' in library_broker_echo_body
    assert "elapsed < ReaderTransportCommandResolver.brokerEchoWindow" in library_broker_echo_body
    assert "musicOwnership.isReaderTransportPauseGuardActive" in library_broker_echo_body
    library_play_body = _function_body(library_now_playing, "func playReaderNowPlayingTransport()")
    library_pause_body = _function_body(library_now_playing, "func pauseReaderNowPlayingTransport()")
    assert 'let resolvedAction = resolvedReaderTransportAction(forCommand: "play")' in library_play_body
    assert 'guard shouldAcceptReaderTransportCommand("play", resolvedAction: resolvedAction) else' in library_play_body
    assert 'reinforceReaderTransportPauseIfNeeded(command: "play", resolvedAction: resolvedAction)' in library_play_body
    assert 'let resolvedAction = resolvedReaderTransportAction(forCommand: "pause")' in library_pause_body
    assert 'guard shouldAcceptReaderTransportCommand("pause", resolvedAction: resolvedAction) else' in library_pause_body
    assert 'reinforceReaderTransportPauseIfNeeded(command: "pause", resolvedAction: resolvedAction)' in library_pause_body
    assert 'let resolvedAction = resolvedReaderTransportAction(forCommand: "toggle")' in library_toggle_body
    assert "guard shouldAcceptReaderTransportCommand(source, resolvedAction: resolvedAction) else" in library_toggle_body
    assert "reinforceReaderTransportPauseIfNeeded(command: source, resolvedAction: resolvedAction)" in library_toggle_body
    assert "let shouldPause = shouldPauseReaderTransportForToggle" not in library_toggle_body
    assert "private func resolvedReaderTransportAction(forCommand command: String) -> String" in library_now_playing
    assert "performReaderNowPlayingPlayTransport()" in library_now_playing
    assert "performReaderNowPlayingPauseTransport()" in library_now_playing
    assert "resumeAppleMusicBedFromReaderTransportIfNeeded()" in library_now_playing
    assert "pauseAppleMusicBedFromReaderTransportIfNeeded()" in library_now_playing
    library_perform_play_body = _function_body(library_now_playing, "private func performReaderNowPlayingPlayTransport()")
    assert "viewModel.playForReaderTransport()" in library_perform_play_body
    assert "scheduleReaderTransportPlaybackRecovery()" in library_perform_play_body
    assert "recoverReaderTransportPlaybackIfNeeded()" not in library_perform_play_body
    assert library_perform_play_body.index("viewModel.playForReaderTransport()") < library_perform_play_body.index(
        "resumeAppleMusicBedFromReaderTransportIfNeeded()"
    )
    assert library_perform_play_body.index("resumeAppleMusicBedFromReaderTransportIfNeeded()") < library_perform_play_body.index(
        "scheduleReaderTransportPlaybackRecovery()"
    )
    assert "viewModel.audioCoordinator.play()" not in library_perform_play_body
    library_recover_body = _function_body(library_now_playing, "private func recoverReaderTransportPlaybackIfNeeded()")
    assert "guard !isVideoPreferred else { return }" in library_recover_body
    assert "guard !viewModel.audioCoordinator.isPlaying else { return }" in library_recover_body
    assert "guard !viewModel.audioCoordinator.isPlaybackRequested else { return }" not in library_recover_body
    assert "if canResumeReaderTransportInPlace" in library_recover_body
    assert "Library reader transport in-place recovery requested=" in library_recover_body
    assert library_recover_body.index("viewModel.playForReaderTransport()") < library_recover_body.index(
        "startInteractivePlayback(at: currentSentence)"
    )
    assert "private var canResumeReaderTransportInPlace: Bool" in library_now_playing
    assert "viewModel.audioCoordinator.nowPlayingPlayer != nil" in library_now_playing
    assert "viewModel.audioCoordinator.activeURL != nil" in library_now_playing
    assert "!viewModel.audioCoordinator.activeURLs.isEmpty" in library_now_playing
    assert "Library reader transport recovery requested=" in library_recover_body
    assert "let trackedSentence = sentenceIndexTracker.value" in library_recover_body
    assert "let currentSentence = (trackedSentence ?? 0) > 0 ? trackedSentence : nil" in library_recover_body
    assert "startInteractivePlayback(at: currentSentence)" in library_recover_body
    assert "startPlaybackFromBeginning()" in library_recover_body
    library_recovery_schedule_body = _function_body(library_now_playing, "private func scheduleReaderTransportPlaybackRecovery()")
    assert "cancelReaderTransportPlaybackRecovery()" in library_recovery_schedule_body
    assert "let scheduledAction = lastReaderTransportAction" in library_recovery_schedule_body
    assert "readerTransportPlaybackRecoveryTask = Task" in library_recovery_schedule_body
    assert "defer { readerTransportPlaybackRecoveryTask = nil }" in library_recovery_schedule_body
    assert "for delay in [180_000_000, 600_000_000, 1_200_000_000] as [UInt64]" in library_recovery_schedule_body
    assert "guard !Task.isCancelled else { return }" in library_recovery_schedule_body
    assert 'guard lastReaderTransportAction == scheduledAction, scheduledAction == "play" else { return }' in library_recovery_schedule_body
    assert "if viewModel.audioCoordinator.isPlaying" in library_recovery_schedule_body
    assert "viewModel.audioCoordinator.isPlaybackRequested || viewModel.audioCoordinator.isPlaying" not in library_recovery_schedule_body
    assert "recoverReaderTransportPlaybackIfNeeded()" in library_recovery_schedule_body
    assert "func cancelReaderTransportPlaybackRecovery()" in library_now_playing
    library_perform_pause_body = _function_body(library_now_playing, "private func performReaderNowPlayingPauseTransport()")
    assert "cancelReaderTransportPlaybackRecovery()" in library_perform_pause_body
    assert "viewModel.pauseForReaderTransport()" in library_perform_pause_body
    assert library_perform_pause_body.index("pauseAppleMusicBedFromReaderTransportIfNeeded()") < library_perform_pause_body.index(
        "viewModel.pauseForReaderTransport()"
    )
    assert library_perform_pause_body.count("publishReaderNowPlayingSnapshot(force: true)") == 1
    assert library_perform_pause_body.index(
        "pauseAppleMusicBedFromReaderTransportIfNeeded()"
    ) < library_perform_pause_body.index(
        "publishReaderNowPlayingSnapshot(force: true)"
    )
    library_interactive_toggle_body = _function_body(library_now_playing, "func toggleInteractiveReaderPlaybackTransport()")
    assert "musicOwnership.isPausedByReaderTransport" in library_interactive_toggle_body
    assert "!viewModel.audioCoordinator.isPlaying" in library_interactive_toggle_body
    assert "playReaderNowPlayingTransport()" in library_interactive_toggle_body
    assert "playbackToggleOverride: {" in library_playback
    assert "toggleInteractiveReaderPlaybackTransport()" in library_playback

    assert "let playbackToggleOverride: (() -> Void)?" in interactive_view
    assert "playbackToggleOverride: (() -> Void)? = nil" in interactive_view
    assert "self.playbackToggleOverride = playbackToggleOverride" in interactive_view
    interactive_exit_body = _function_body(interactive_view, "private func handleExitCommand()")
    assert "Resume playback if paused" not in interactive_exit_body
    assert "isPlaybackFinished" not in interactive_exit_body
    assert "dismiss()" in interactive_exit_body
    video_exit_body = _function_body(video_playback, "func handleExitCommand()")
    assert "if !coordinator.isPlaying" not in video_exit_body
    assert "reportPlaybackProgress(time: resolvedPlaybackTime(), isPlaying: coordinator.isPlaying)" in video_exit_body
    assert "dismiss()" in video_exit_body
    playback_toggle_body = _function_body(interactive_input, "func handlePlaybackToggleCommand()")
    assert "linguistVM.stopPronunciation()" in playback_toggle_body
    assert "audioCoordinator.reassertAudioSession(force: true)" in playback_toggle_body
    assert playback_toggle_body.index("linguistVM.stopPronunciation()") < playback_toggle_body.index(
        "audioCoordinator.reassertAudioSession(force: true)"
    )
    assert playback_toggle_body.index("audioCoordinator.reassertAudioSession(force: true)") < playback_toggle_body.index(
        "if let playbackToggleOverride"
    )
    assert "if let playbackToggleOverride" in playback_toggle_body
    assert "playbackToggleOverride()" in playback_toggle_body
    assert "pauseReaderTransportFromCommand()" in playback_toggle_body
    assert "resumeReaderTransportFromCommand()" in playback_toggle_body
    assert "resumeAppleMusicBedForReaderTransportIfNeeded()" in playback_toggle_body
    pause_reader_transport_body = _function_body(interactive_input, "private func pauseReaderTransportFromCommand()")
    resume_reader_transport_body = _function_body(interactive_input, "private func resumeReaderTransportFromCommand()")
    assert "pauseAppleMusicBedForReaderTransportIfNeeded()" in pause_reader_transport_body
    assert "viewModel.pauseForReaderTransport()" in pause_reader_transport_body
    assert pause_reader_transport_body.index("pauseAppleMusicBedForReaderTransportIfNeeded()") < pause_reader_transport_body.index(
        "viewModel.pauseForReaderTransport()"
    )
    assert "viewModel.playForReaderTransport()" in resume_reader_transport_body
    assert "resumeAppleMusicBedForReaderTransportIfNeeded()" in resume_reader_transport_body
    assert "musicCoordinator.pauseReadingBedForReaderTransport()" in interactive_input
    assert "musicCoordinator.resumeReadingBedForReaderTransport()" in interactive_input
    assert "e2eBubbleResumeLayer" in interactive_layout
    assert "#if DEBUG" in interactive_e2e
    assert "#if os(iOS)" in interactive_e2e
    assert 'ProcessInfo.processInfo.environment["E2E_MUSIC_BED_SYNC_TEST"] == "1"' in interactive_e2e
    assert "static let e2eBubblePronunciationResume" in interactive_e2e
    assert "enum InteractivePlayerE2EState" in interactive_e2e
    assert "static func resetBubbleWordNavigation()" in interactive_e2e
    assert "static func recordBubbleWordNavigation(" in interactive_e2e
    assert "static func recordBubbleLookupCommand(" in interactive_e2e
    assert '"bubbleWordNav=\\(bubbleWordNavigationCount)"' in interactive_e2e
    assert '"bubbleLookup=\\(bubbleLookupCommandCount)"' in interactive_e2e
    assert '"bubbleLookupHadBubble=\\(bubbleLookupHadBubble ? "true" : "false")"' in interactive_e2e
    assert "InteractivePlayerE2EState.resetBubbleWordNavigation()" in interactive_e2e
    assert ".allowsHitTesting(false)" in interactive_e2e
    assert "NotificationCenter.default.publisher(for: .e2eBubblePronunciationResume)" in interactive_e2e
    assert "prepareBubblePronunciationResumeForE2E()" in interactive_e2e
    assert "pausePlaybackForLinguistLookupIfNeeded()" in interactive_e2e
    assert "viewModel.pauseForReaderTransport()" in interactive_e2e
    assert "musicCoordinator.simulateReadingBedPauseForE2E()" in interactive_e2e
    assert 'pronunciationSpeaker.speakFallback("resume", language: "en-US")' in interactive_e2e
    assert "InteractivePlayerE2EState.recordBubbleWordNavigation(" in interactive_transcript
    assert "direction: direction" in interactive_transcript
    assert "linguistBubble != nil" in interactive_transcript
    assert "InteractivePlayerE2EState.recordBubbleLookupCommand(" in interactive_input
    assert "hadBubble: linguistBubble != nil || linguistSelection != nil" in interactive_input
    assert "selection: linguistSelection" in interactive_input

    assert "onPlay: { coordinator.play() }" in video_now_playing
    assert "onPause: { coordinator.pause() }" in video_now_playing
    assert "onSeek: { coordinator.seek(to: $0) }" in video_now_playing
    assert "onToggle: { coordinator.togglePlayback() }" in video_now_playing
    assert "onSkipForward: { coordinator.skip(by: 15) }" in video_now_playing
    assert "onSkipBackward: { coordinator.skip(by: -15) }" in video_now_playing
    assert "onBookmark: { addBookmark() }" in video_now_playing
    assert "mediaType: .video" in video_now_playing

    assert "private func adoptPauseAsReaderTransport(reason: String, source: String)" in music
    observed_non_playing_body = _function_body(music, "private func handleObservedNonPlayingStatus(")
    adopt_pause_body = _function_body(music, "private func adoptPauseAsReaderTransport(reason: String, source: String)")
    assert 'adoptPauseAsReaderTransport(reason: "observedNonPlaying", source: "observed non-playing")' in observed_non_playing_body
    assert 'adoptPauseAsReaderTransport(reason: "readerTransportPause", source: "reader transport")' in music
    assert "advanceReaderTransportResumeBarrier(reason: reason)" in adopt_pause_body
    assert "cancelReaderTransportResumeTask(reason: reason)" in adopt_pause_body
    assert "cancelPlaybackSurfaceReassertions()" in adopt_pause_body
    assert "cancelObservedNonPlayingPause()" in adopt_pause_body
    assert "beginReaderTransportPauseHold()" in adopt_pause_body
    assert "updateMusicPlaybackSurfaceSuppression(reason: reason)" in adopt_pause_body
    assert "pauseSystemPlayerForReaderTransport(reason: reason)" in adopt_pause_body
    assert "scheduleReaderTransportPauseConfirmation()" in adopt_pause_body

    chrome = _source(PLAYBACK / "LibraryPlaybackChromeViews.swift")
    assert "let readerTransportCommandCount: Int" in chrome
    assert '"readerTransportCommands=\\(readerTransportCommandCount)"' in chrome
    assert "let foregroundPlayPauseCount: Int" in chrome
    assert '"foregroundPlayPause=\\(foregroundPlayPauseCount)"' in chrome
    assert "let lastReaderTransportAction: String" in chrome
    assert '"lastAction=\\(lastReaderTransportAction)"' in chrome
    assert "let onReaderPlayCommand: () -> Void" in chrome
    assert "let onReaderPauseCommand: () -> Void" in chrome
    assert "let onReaderToggleCommand: () -> Void" in chrome
    assert 'accessibilityIdentifier("e2eReaderPlayCommandButton")' in chrome
    assert 'accessibilityLabel("e2eReaderPlayCommandButton")' in chrome
    assert 'accessibilityIdentifier("e2eReaderPauseCommandButton")' in chrome
    assert 'accessibilityLabel("e2eReaderPauseCommandButton")' in chrome
    assert 'NotificationCenter.default.post(name: .keyboardShortcutPlayPause, object: nil)' in chrome
    assert 'accessibilityIdentifier("e2eKeyboardSpaceCommandButton")' in chrome
    assert 'accessibilityLabel("e2eKeyboardSpaceCommandButton")' in chrome
    assert "NotificationCenter.default.post(name: .keyboardShortcutPrevious, object: nil)" in chrome
    assert 'accessibilityIdentifier("e2eKeyboardLeftCommandButton")' in chrome
    assert 'accessibilityLabel("e2eKeyboardLeftCommandButton")' in chrome
    assert "NotificationCenter.default.post(name: .keyboardShortcutNext, object: nil)" in chrome
    assert 'accessibilityIdentifier("e2eKeyboardRightCommandButton")' in chrome
    assert 'accessibilityLabel("e2eKeyboardRightCommandButton")' in chrome
    assert 'accessibilityIdentifier("e2eReaderToggleCommandButton")' in chrome
    assert 'accessibilityLabel("e2eReaderToggleCommandButton")' in chrome


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
    assert "setRemoteCommandsEnabled(false)" in clear_body
    assert "removeRemoteCommandTargets()" in clear_body
    assert "configuredRemoteCommandCenters = []" in clear_body
    assert "isConfigured = false" in clear_body
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
    transport_resolver = _source(PLAYBACK / "ReaderTransportCommandResolver.swift")
    chrome = _source(PLAYBACK / "LibraryPlaybackChromeViews.swift")

    assert "case appleMusicBed" in music
    assert "@Published private(set) var playbackSurfaceRevision = 0" in music
    assert "@Published private(set) var isPausedByReaderTransport = false" in music
    assert "func updateCurrentTrackInfo(reason: String)" in music
    assert "func markPlaybackSurfaceDidChange(reason: String)" in music
    assert "private func schedulePlaybackSurfaceReassertions(reason: String)" in music
    assert "func resumeReadingBedForReaderTransport()" in music
    assert "func pauseReadingBedForReaderTransport()" in music
    assert "func updateReaderNarrationActivityForMusicBed(isActive: Bool, reason: String)" in music
    assert "private var isReaderNarrationActiveForMusicBed = false" in music
    assert "readerTransportPauseHoldUntil" in music
    assert "readerTransportPauseDuplicateHoldUntil" in music
    assert "readerTransportPauseHoldDuration" in music
    assert "readerTransportPauseDuplicateHoldDuration" in music
    assert "private let readerTransportPauseHoldDuration: TimeInterval = 1.5" in music
    assert "static var pauseHoldWindow: TimeInterval {\n        1.5\n    }" in transport_resolver
    assert "readerTransportPauseConfirmationTask" in music
    assert "readerTransportResumeTask" in music
    assert "readerTransportResumeTaskID" in music
    assert "readerTransportResumeBarrier" in music
    assert "var readerTransportResumeBarrierValue: Int" in music
    assert "var shouldRejectReaderTransportResumeAfterPause: Bool" in music
    assert "var isFullscreenMusicArtworkSuppressed: Bool" in music
    assert "func isReaderTransportResumeBarrierCurrent(_ barrier: Int) -> Bool" in music
    assert "func refreshMusicPlaybackSurfaceSuppression(reason: String)" in music
    assert "private func cancelReaderTransportResumeTask(reason: String)" in music
    assert "private func isExpectedReaderTransportResumeCurrent(_ expectedBarrier: Int?) -> Bool" in music
    assert "private var shouldSuppressObservedPlayDuringReaderPause: Bool" in music
    assert "private var shouldTreatObservedNonPlayingAsReaderPause: Bool" in music
    assert "private func scheduleReaderTransportPauseConfirmation()" in music
    assert "schedulePlaybackSurfaceReassertions(reason: \"resume\")" in music
    assert "schedulePlaybackSurfaceReassertions(reason: \"playSong\")" in music
    assert "schedulePlaybackSurfaceReassertions(reason: \"playStation\")" in music
    assert "updateCurrentTrackInfo(reason: \"\\(reason)-reader-reassert\")" in music
    assert "playbackSurfaceRevision &+= 1" in music
    assert "Apple Music playback surface changed reason=" in music
    non_playing_body = _function_body(music, "private func handleObservedNonPlayingStatus(")
    assert "shouldTreatObservedNonPlayingAsReaderPause" in non_playing_body
    assert "autoResume=" in non_playing_body
    assert "deferObservedNonPlayingDuringActiveReadingBed(reason: \"observedNonPlaying\")" in non_playing_body
    assert non_playing_body.index("shouldDeferObservedNonPlayingDuringActiveReadingBed") < non_playing_body.index(
        "shouldTreatObservedNonPlayingAsReaderPause"
    )
    assert "observed non-playing confirmation ignored after state changed" in non_playing_body
    assert 'adoptPauseAsReaderTransport(reason: "observedNonPlaying", source: "observed non-playing")' in non_playing_body
    assert "guard allowE2E || !isE2EMusicBedSyncTest else { return }" in non_playing_body
    deferred_non_playing_body = _function_body(
        music,
        "private func deferObservedNonPlayingDuringActiveReadingBed(reason: String)",
    )
    assert "hasAutoResumeIntent = true" in deferred_non_playing_body
    assert "Apple Music observed non-playing deferred for active reading bed" in deferred_non_playing_body
    assert "Apple Music deferred non-playing recovering active reading bed" in deferred_non_playing_body
    assert 'recoverReadingBedForActiveNarration(reason: "deferredObservedNonPlaying")' in deferred_non_playing_body
    assert "adoptPauseAsReaderTransport" not in deferred_non_playing_body
    adopt_pause_body = _function_body(music, "private func adoptPauseAsReaderTransport(reason: String, source: String)")
    assert "isManuallyPaused = true" in adopt_pause_body
    assert "isPausedByReaderTransport = true" in adopt_pause_body
    assert "hasAutoResumeIntent = false" in adopt_pause_body
    assert "beginReaderTransportPauseHold()" in adopt_pause_body
    assert "pauseSystemPlayerForReaderTransport(reason: reason)" in adopt_pause_body
    assert "scheduleReaderTransportPauseConfirmation()" in adopt_pause_body
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
    assert "suppressObservedPlaybackDuringReaderPause(" in observe_body
    assert "suppressedObservedTrackChangeDuringReaderPause" in observe_body
    assert "suppressedObservedPlayDuringReaderPause" in observe_body
    assert "shouldSuppressObservedPlayDuringReaderPause" in observe_body
    suppress_index = observe_body.index("suppressObservedPlaybackDuringReaderPause(")
    publish_play_index = observe_body.index("isPlaying = status == .playing")
    assert suppress_index < publish_play_index
    suppress_observed_body = _function_body(
        music,
        "private func suppressObservedPlaybackDuringReaderPause(reason: String)",
    )
    assert "Apple Music observed play suppressed during reader transport pause" in suppress_observed_body
    assert "ApplicationMusicPlayer.shared.pause()" in suppress_observed_body
    assert "markPlaybackSurfaceDidChange(reason: reason)" in suppress_observed_body
    assert "var isBackgroundMode: Bool { ownershipState == .appleMusic || ownershipState == .appleMusicBed }" in music
    assert "func simulateObservedNonPlayingPauseForE2E()" in music
    assert "func simulateReadingBedPauseForE2E()" in music
    assert "func simulateReadingBedPlayForE2E()" in music
    assert "private var isE2EMusicBedSyncTest: Bool" in music
    assert "handleObservedNonPlayingStatus(allowE2E: true)" in music
    assert 'e2eMusicBedSyncPhase = "observedPauseImmediate"' in music
    assert "scheduleSimulatedReadingBedPlayForE2E" not in music
    reader_pause_body = _function_body(music, "func pauseReadingBedForReaderTransport()")
    reader_resume_body = _function_body(music, "func resumeReadingBedForReaderTransport()")
    resume_body = _function_body(music, "func resume(userInitiated: Bool = true")
    assert "if isE2EMusicBedSyncTest" in reader_pause_body
    assert "simulateReadingBedPauseForE2E()" in reader_pause_body
    assert "if isE2EMusicBedSyncTest" in reader_resume_body
    assert "simulateReadingBedPlayForE2E()" in reader_resume_body
    assert "ownershipState = .appleMusicBed" in reader_resume_body
    assert 'adoptPauseAsReaderTransport(reason: "readerTransportPause", source: "reader transport")' in reader_pause_body
    assert "beginReaderTransportPauseHold()" in adopt_pause_body
    assert "advanceReaderTransportResumeBarrier(reason: reason)" in adopt_pause_body
    assert "cancelReaderTransportResumeTask(reason: reason)" in adopt_pause_body
    assert "scheduleReaderTransportPauseConfirmation()" in adopt_pause_body
    assert "clearReaderTransportPauseHold()" in reader_resume_body
    assert 'advanceReaderTransportResumeBarrier(reason: "readerTransportResume")' in reader_resume_body
    assert "let resumeBarrier = readerTransportResumeBarrier" in reader_resume_body
    assert "resume(userInitiated: false, expectedReaderTransportBarrier: resumeBarrier)" in reader_resume_body
    assert "expectedReaderTransportBarrier: Int? = nil" in music
    assert "readerTransportResumeTask?.cancel()" in resume_body
    assert "readerTransportResumeTaskID &+= 1" in resume_body
    assert "isExpectedReaderTransportResumeCurrent(expectedReaderTransportBarrier)" in resume_body
    assert "if userInitiated" in resume_body
    assert "cancelTVOSSystemPlaybackSurfaceSuppression()" in resume_body
    assert "resume skipped stale reader transport barrier before play" in resume_body
    assert "resume cancelled stale reader transport barrier after play" in resume_body
    assert 'pauseSystemPlayerForReaderTransport(reason: "staleReaderTransportResume")' in resume_body
    assert "shouldIgnoreNextNonPlayingStatus = false" in reader_resume_body
    assert "cancelTVOSSystemPlaybackSurfaceSuppression()" not in reader_resume_body
    assert "private let readerTransportPauseHoldDuration: TimeInterval = 1.5" in music
    assert "private let readerTransportPauseDuplicateHoldDuration: TimeInterval = 1.5" in music
    assert "var isReaderTransportPauseGuardActive: Bool" in music
    assert "var isReaderTransportPauseHoldWindowActive: Bool" in music
    duplicate_resume_body = _function_body(music, "var shouldRejectReaderTransportResumeAfterPause: Bool")
    assert "isReaderTransportPauseDuplicateHoldActive" in duplicate_resume_body
    assert "isPausedByReaderTransport" in duplicate_resume_body
    pause_guard_body = _function_body(music, "var isReaderTransportPauseGuardActive: Bool")
    assert "isReaderTransportPauseHoldActive" in pause_guard_body
    assert "isReaderTransportPauseSuppressionActive" in pause_guard_body
    pause_hold_body = _function_body(music, "var isReaderTransportPauseHoldWindowActive: Bool")
    assert "isReaderTransportPauseHoldActive" in pause_hold_body
    suppress_body = _function_body(music, "private var shouldSuppressObservedPlayDuringReaderPause: Bool")
    assert "isReaderTransportPauseGuardActive" in suppress_body
    observed_non_playing_body = _function_body(music, "private var shouldTreatObservedNonPlayingAsReaderPause: Bool")
    assert "observedPlayingAsReadingBed" in observed_non_playing_body
    assert "ownershipState == .appleMusicBed && isReaderNarrationActiveForMusicBed" not in observed_non_playing_body
    assert "hasAutoResumeIntent" in observed_non_playing_body
    assert "isPausedByReaderTransport" in observed_non_playing_body
    deferred_non_playing_guard = _function_body(
        music,
        "private var shouldDeferObservedNonPlayingDuringActiveReadingBed: Bool",
    )
    assert "ownershipState == .appleMusicBed" in deferred_non_playing_guard
    assert "isReaderNarrationActiveForMusicBed" in deferred_non_playing_guard
    assert "observedPlayingAsReadingBed || hasAutoResumeIntent" not in deferred_non_playing_guard
    update_reader_activity_body = _function_body(music, "func updateReaderNarrationActivityForMusicBed(isActive: Bool, reason: String)")
    assert "guard ownershipState == .appleMusicBed else" in update_reader_activity_body
    assert "isReaderNarrationActiveForMusicBed = false" in update_reader_activity_body
    assert "Apple Music reader narration activity=" in update_reader_activity_body
    suppression_active_body = _function_body(music, "private var isReaderTransportPauseSuppressionActive: Bool")
    assert "ownershipState == .appleMusicBed" in suppression_active_body
    assert "isPausedByReaderTransport" in suppression_active_body
    assert "isManuallyPaused" in suppression_active_body
    pause_confirm_body = _function_body(music, "private func scheduleReaderTransportPauseConfirmation()")
    assert "readerTransportPauseConfirmationTask?.cancel()" in pause_confirm_body
    assert "readerTransportPauseConfirmationTask = Task" in pause_confirm_body
    assert "while !Task.isCancelled" in pause_confirm_body
    assert "Task.sleep(nanoseconds: 250_000_000)" in pause_confirm_body
    assert "shouldSuppressObservedPlayDuringReaderPause" in pause_confirm_body
    assert "readerTransportPauseConfirmationTask = nil" in pause_confirm_body
    assert "ApplicationMusicPlayer.shared.state.playbackStatus == .playing" in pause_confirm_body
    assert "reader transport pause confirmation re-pausing" in pause_confirm_body
    assert 'markPlaybackSurfaceDidChange(reason: "readerTransportPauseConfirmation")' in pause_confirm_body
    observe_body = _function_body(music, "private func observePlaybackState()")
    assert "suppressObservedPlaybackDuringReaderPause(" in observe_body
    assert "suppressedObservedTrackChangeDuringReaderPause" in observe_body
    assert (
        observe_body.index("suppressObservedPlaybackDuringReaderPause(")
        < observe_body.index("isPlaying = status == .playing")
    )
    suppress_observed_body = _function_body(
        music,
        "private func suppressObservedPlaybackDuringReaderPause(reason: String)",
    )
    assert "isManuallyPaused = true" in suppress_observed_body
    assert "isPausedByReaderTransport = true" in suppress_observed_body
    assert "hasAutoResumeIntent = false" in suppress_observed_body
    clear_hold_body = _function_body(music, "private func clearReaderTransportPauseHold()")
    assert "readerTransportPauseConfirmationTask?.cancel()" in clear_hold_body
    assert "readerTransportPauseConfirmationTask = nil" in clear_hold_body
    assert "readerTransportPauseDuplicateHoldUntil = Date.distantPast" in clear_hold_body
    cancel_resume_body = _function_body(music, "private func cancelReaderTransportResumeTask(reason: String)")
    assert "readerTransportResumeTask?.cancel()" in cancel_resume_body
    assert "readerTransportResumeTask = nil" in cancel_resume_body
    assert "readerTransportResumeTaskID &+= 1" in cancel_resume_body
    assert "reader transport resume task cancelled" in cancel_resume_body
    expected_resume_body = _function_body(music, "private func isExpectedReaderTransportResumeCurrent(_ expectedBarrier: Int?)")
    assert "readerTransportResumeBarrier == expectedBarrier" in expected_resume_body
    assert "!isReaderTransportPauseGuardActive" in expected_resume_body
    assert "!isPausedByReaderTransport" in expected_resume_body
    begin_hold_body = _function_body(music, "private func beginReaderTransportPauseHold()")
    assert "readerTransportPauseDuplicateHoldUntil = Date().addingTimeInterval(readerTransportPauseDuplicateHoldDuration)" in begin_hold_body
    barrier_body = _function_body(music, "private func advanceReaderTransportResumeBarrier(reason: String)")
    assert "readerTransportResumeBarrier &+= 1" in barrier_body
    assert "reader transport barrier advanced" in barrier_body
    simulated_pause_body = _function_body(music, "func simulateReadingBedPauseForE2E()")
    assert "simulateReadingBedPlayForE2E()" not in simulated_pause_body
    assert 'advanceReaderTransportResumeBarrier(reason: "e2ePause")' in simulated_pause_body
    simulated_play_body = _function_body(music, "func simulateReadingBedPlayForE2E()")
    assert 'advanceReaderTransportResumeBarrier(reason: "e2ePlay")' in simulated_play_body
    assert "shouldIgnoreNextNonPlayingStatus = false" in simulated_play_body
    assert "isSuppressingMusicPlaybackSurface = true" in simulated_play_body
    assert 'updateFullscreenMusicArtworkSuppression(true, reason: "e2ePlay")' in simulated_play_body
    ensure_play_body = _function_body(music, "func ensureReadingBedPlayStateForE2E()")
    assert 'ProcessInfo.processInfo.environment["E2E_MUSIC_BED_SYNC_TEST"] == "1"' in ensure_play_body
    assert 'e2eMusicBedSyncPhase == "play"' in ensure_play_body
    assert "ownershipState = .appleMusicBed" in ensure_play_body
    assert "isSuppressingMusicPlaybackSurface = true" in ensure_play_body
    assert 'ProcessInfo.processInfo.environment["E2E_MUSIC_BED_SYNC_TEST"] == "1"' in music

    ownership_body = _function_body(job, "private func handleAudioOwnershipChange(_ state: AudioOwnership)")
    assert "case .appleMusicBed:" in ownership_body
    assert "configureAppleMusicBedAudioSession()" in ownership_body
    assert "viewModel.audioCoordinator.configureAudioSessionForMixing(false)" in ownership_body
    assert "publishReaderNowPlayingSnapshot(force: true)" in ownership_body
    assert "scheduleAppleMusicBedNowPlayingReassertion()" in ownership_body
    assert "case .appleMusic:" in ownership_body
    assert "nowPlaying.setRemoteCommandsEnabled(false)" in ownership_body
    assert "nowPlaying.clear()" in ownership_body
    assert "@State var nowPlayingReassertionTask: Task<Void, Never>?" in job
    assert "@State var readerTransportPlaybackRecoveryTask: Task<Void, Never>?" in job
    assert ".onReceive(musicOwnership.$isPlaying) { _ in handleMusicKitPlaybackSurfaceChange() }" in job
    assert ".onReceive(musicOwnership.$isManuallyPaused) { _ in handleMusicKitPlaybackSurfaceChange() }" in job
    assert ".onReceive(musicOwnership.$isPausedByReaderTransport) { _ in handleMusicKitPlaybackSurfaceChange() }" in job
    assert ".onReceive(musicOwnership.$isSuppressingMusicPlaybackSurface) { _ in handleMusicKitPlaybackSurfaceChange() }" in job
    assert ".onReceive(musicOwnership.$currentSongTitle) { _ in handleMusicKitPlaybackSurfaceChange() }" in job
    assert ".onReceive(musicOwnership.$playbackSurfaceRevision) { _ in handleMusicKitPlaybackSurfaceChange() }" in job
    assert "Timer.publish(every: 0.5, on: .main, in: .common).autoconnect()" in job
    assert "handleMusicKitReadingBedWatchdogTick()" in job
    assert "@AppStorage(MusicPreferences.musicVolumeKey) var musicVolume" in job
    assert "private var appleMusicDuckingMixThreshold: Double { 0.35 }" in job
    assert "private func configureAppleMusicBedAudioSession()" in job
    assert "viewModel.audioCoordinator.configureAudioSessionForMixing(" in job
    assert "duckOthers: musicVolume < appleMusicDuckingMixThreshold" in job
    assert "func scheduleAppleMusicBedNowPlayingReassertion()" in job
    job_reassertion_scheduler_body = _function_body(job, "func scheduleAppleMusicBedNowPlayingReassertion()")
    assert "guard shouldKeepReaderNowPlayingReassertionAlive else { return }" in job_reassertion_scheduler_body
    assert "guard nowPlayingReassertionTask == nil else { return }" in job_reassertion_scheduler_body
    assert "defer { nowPlayingReassertionTask = nil }" in job_reassertion_scheduler_body
    assert "let reassertionDelays: [UInt64] = [" in job
    assert "75_000_000" in job
    assert "850_000_000" in job
    assert "5_000_000_000" in job
    assert "while !Task.isCancelled" in job
    assert "try? await Task.sleep(nanoseconds: 1_000_000_000)" in job
    assert 'musicOwnership.refreshMusicPlaybackSurfaceSuppression(reason: "jobNowPlayingReassertion")' in job_reassertion_scheduler_body
    assert "private var shouldKeepReaderNowPlayingReassertionAlive: Bool" in job
    assert "private var shouldMirrorAppleMusicPauseToNarration: Bool" in job
    job_reassert_body = _function_body(job, "private var shouldKeepReaderNowPlayingReassertionAlive: Bool")
    assert "musicOwnership.isSuppressingMusicPlaybackSurface" not in job_reassert_body
    assert "musicOwnership.isReaderTransportPauseGuardActive" in job_reassert_body
    assert "musicOwnership.isPausedByReaderTransport" in job_reassert_body
    assert "!musicOwnership.isManuallyPaused" in job_reassert_body
    assert "updateReaderNarrationActivityForMusicBed" in job
    job_mirror_body = _function_body(job, "private var shouldMirrorAppleMusicPauseToNarration: Bool")
    assert "musicOwnership.isPausedByReaderTransport" in job_mirror_body
    assert "#if os(tvOS)" in job_mirror_body
    assert "musicOwnership.isManuallyPaused && musicOwnership.ownershipState == .appleMusicBed" in job_mirror_body
    assert "guard viewModel.audioCoordinator.isPlaybackRequested || viewModel.audioCoordinator.isPlaying else" in job_mirror_body
    assert "musicOwnership.ownershipState == .appleMusicBed &&" in job
    assert "viewModel.audioCoordinator.isPlaybackRequested" in job
    assert "musicOwnership.isPlaying" in job
    assert "private var shouldClearNowPlayingOnDisappear: Bool" in job
    assert "musicOwnership.ownershipState != .appleMusicBed" in job
    job_audio_state_body = _function_body(job, "private func handleAudioStateChange()")
    assert "guard musicOwnership.ownershipState == .appleMusicBed else { return }" in job_audio_state_body
    assert "musicOwnership.updateReaderNarrationActivityForMusicBed(" in job_audio_state_body
    assert "publishReaderNowPlayingSnapshot(force: true)" in job_audio_state_body
    assert "scheduleAppleMusicBedNowPlayingReassertion()" in job_audio_state_body
    job_music_surface_body = _function_body(job, "private func handleMusicKitPlaybackSurfaceChange()")
    assert "if shouldMirrorAppleMusicPlayToNarration" in job_music_surface_body
    assert "viewModel.audioCoordinator.play()" in job_music_surface_body
    assert job_music_surface_body.index("if shouldMirrorAppleMusicPlayToNarration") < job_music_surface_body.index(
        "if shouldMirrorAppleMusicPauseToNarration"
    )
    assert "if shouldMirrorAppleMusicPauseToNarration" in job_music_surface_body
    assert "cancelReaderTransportPlaybackRecovery()" in job_music_surface_body
    assert 'lastReaderTransportAction = "pause"' in job_music_surface_body
    assert "localReaderTransportPauseHoldUntil = ProcessInfo.processInfo.systemUptime + ReaderTransportCommandResolver.pauseHoldWindow" in job_music_surface_body
    assert "viewModel.pauseForReaderTransport()" in job_music_surface_body
    assert "return" in job_music_surface_body
    job_mirror_play_body = _function_body(job, "private var shouldMirrorAppleMusicPlayToNarration: Bool")
    assert "musicOwnership.isPlaying" in job_mirror_play_body
    assert "!musicOwnership.isManuallyPaused" in job_mirror_play_body
    assert "!musicOwnership.isPausedByReaderTransport" in job_mirror_play_body
    assert "!musicOwnership.isReaderTransportPauseGuardActive" in job_mirror_play_body
    assert "!viewModel.audioCoordinator.isPlaybackRequested" in job_mirror_play_body
    assert "!viewModel.audioCoordinator.isPlaying" in job_mirror_play_body
    job_watchdog_body = _function_body(job, "private func handleMusicKitReadingBedWatchdogTick()")
    assert "musicOwnership.ownershipState == .appleMusicBed" in job_watchdog_body
    assert "!musicOwnership.isReaderTransportPauseGuardActive" in job_watchdog_body
    assert "viewModel.audioCoordinator.isPlaybackRequested || viewModel.audioCoordinator.isPlaying" in job_watchdog_body
    assert "musicOwnership.updateReaderNarrationActivityForMusicBed(" in job_watchdog_body
    assert job_watchdog_body.index("if shouldMirrorAppleMusicPauseToNarration") < job_watchdog_body.index(
        "guard !musicOwnership.isReaderTransportPauseGuardActive else { return }"
    )
    assert job_watchdog_body.index("guard !musicOwnership.isReaderTransportPauseGuardActive else { return }") < job_watchdog_body.index(
        "musicOwnership.reconcileReadingBedSystemPlayback()"
    )
    assert "musicOwnership.reconcileReadingBedSystemPlayback()" in job_watchdog_body
    assert 'musicOwnership.recoverReadingBedForActiveNarration(reason: "jobWatchdog")' in job_watchdog_body
    assert 'musicOwnership.refreshMusicPlaybackSurfaceSuppression(reason: "jobWatchdog")' in job_watchdog_body
    assert "viewModel.pauseForReaderTransport()" in job_watchdog_body
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
    assert "private func resolvedReaderTransportAction(forCommand command: String) -> String" in job_now_playing
    job_accept_body = _function_body(job_now_playing, "private func shouldAcceptReaderTransportCommand(_ command: String, resolvedAction: String)")
    assert "shouldBlockReaderTransportResumeAfterPause(resolvedAction: resolvedAction, elapsed: elapsed, now: now)" in job_accept_body
    job_block_resume_body = _function_body(job_now_playing, "private func shouldBlockReaderTransportResumeAfterPause")
    assert "ReaderTransportCommandResolver.shouldHoldReaderResumeAfterPause" in job_block_resume_body
    assert "musicOwnership.shouldRejectReaderTransportResumeAfterPause" in job_block_resume_body
    assert 'lastReaderTransportAction != "pause" || elapsed < readerTransportDuplicateWindow' not in job_block_resume_body
    assert "now < localReaderTransportPauseHoldUntil" in job_block_resume_body
    assert "musicOwnership.isReaderTransportPauseHoldWindowActive" in job_block_resume_body
    job_resolve_body = _function_body(job_now_playing, "private func resolvedReaderTransportAction(forCommand command: String) -> String")
    assert "#if os(tvOS)" not in job_resolve_body
    assert 'if command == "play" || command == "pause" || command == "toggle"' not in job_resolve_body
    assert "ReaderTransportCommandResolver.resolvedAction(" in job_resolve_body
    assert "ReaderTransportCommandResolver.duplicateWindow" in job_now_playing
    assert "ReaderTransportCommandResolver.shouldReapplyDuplicateCommand" in job_accept_body
    assert "ReaderTransportCommandResolver.shouldRejectDuplicateCommand" in job_accept_body
    assert "command reapplying duplicate action=" in job_accept_body
    assert "static func shouldReapplyDuplicateCommand" in transport_resolver
    assert "static func shouldRejectDuplicateCommand" in transport_resolver
    assert "static var shouldHoldReaderResumeAfterPause: Bool" in transport_resolver
    assert "isMusicPausedByReaderTransport,\n           !isReaderPlaying" in transport_resolver
    assert "resolvedAction == previousAction" in transport_resolver
    assert "resolvedAction != previousAction" in transport_resolver
    assert "return shouldPauseReaderTransportForToggle" not in job_now_playing
    assert "command == \"toggle\"" in transport_resolver
    assert "ownershipState == .appleMusicBed" in transport_resolver
    assert "#if os(tvOS)" in transport_resolver
    resolver_body = _function_body(transport_resolver, "static func resolvedAction(")
    tvos_resolver_body = resolver_body[
        resolver_body.index("#if os(tvOS)") : resolver_body.index("#endif", resolver_body.index("#if os(tvOS)"))
    ]
    assert "if command == \"pause\"" in tvos_resolver_body
    assert "return \"pause\"" in tvos_resolver_body
    assert "if command == \"play\" || command == \"toggle\"" in tvos_resolver_body
    assert "guard command == \"toggle\" else { return command }" in transport_resolver
    assert "return command" in transport_resolver
    assert "private func performReaderNowPlayingTransport(action: String)" in job_now_playing
    job_play_body = _function_body(job_now_playing, "func playReaderNowPlayingTransport()")
    job_pause_body = _function_body(job_now_playing, "func pauseReaderNowPlayingTransport()")
    assert 'let resolvedAction = resolvedReaderTransportAction(forCommand: "play")' in job_play_body
    assert "performReaderNowPlayingTransport(action: resolvedAction)" in job_play_body
    assert 'let resolvedAction = resolvedReaderTransportAction(forCommand: "pause")' in job_pause_body
    assert "performReaderNowPlayingTransport(action: resolvedAction)" in job_pause_body
    job_pause_music_body = _function_body(job_now_playing, "private func pauseAppleMusicBedFromReaderTransportIfNeeded()")
    assert "nowPlayingReassertionTask?.cancel()" in job_pause_music_body
    assert "nowPlayingReassertionTask = nil" in job_pause_music_body
    assert "scheduleAppleMusicBedNowPlayingReassertion()" in job_pause_music_body
    job_resume_music_body = _function_body(job_now_playing, "private func resumeAppleMusicBedFromReaderTransportIfNeeded()")
    assert "musicOwnership.ownershipState == .appleMusicBed" in job_resume_music_body
    assert "musicOwnership.ownershipState == .appleMusic" in job_resume_music_body
    assert "musicOwnership.prepareForNarrationMix()" in job_resume_music_body
    assert "musicOwnership.resumeReadingBedForReaderTransport()" in job_resume_music_body
    assert "Task { @MainActor" not in job_resume_music_body
    assert "ensureLastSelectionLoadedForReadingBed()" not in job_resume_music_body
    assert job_resume_music_body.index("musicOwnership.resumeReadingBedForReaderTransport()") < job_resume_music_body.index(
        "publishReaderNowPlayingSnapshot(force: true)"
    )
    assert "scheduleAppleMusicBedNowPlayingReassertion()" in job_now_playing
    assert "if isVideoPreferred || isAppleMusicOwningLockScreen" in job_loading

    assert "@StateObject var musicOwnership = MusicKitCoordinator.shared" in library
    assert "@State var nowPlayingReassertionTask: Task<Void, Never>?" in library
    assert ".onChange(of: musicOwnership.ownershipState) { _, state in handleAudioOwnershipChange(state) }" in library
    assert ".onReceive(musicOwnership.$isPlaying) { _ in handleMusicKitPlaybackSurfaceChange() }" in library
    assert ".onReceive(musicOwnership.$isManuallyPaused) { _ in handleMusicKitPlaybackSurfaceChange() }" in library
    assert ".onReceive(musicOwnership.$isPausedByReaderTransport) { _ in handleMusicKitPlaybackSurfaceChange() }" in library
    assert ".onReceive(musicOwnership.$isSuppressingMusicPlaybackSurface) { _ in handleMusicKitPlaybackSurfaceChange() }" in library
    assert ".onReceive(musicOwnership.$currentSongTitle) { _ in handleMusicKitPlaybackSurfaceChange() }" in library
    assert ".onReceive(musicOwnership.$playbackSurfaceRevision) { _ in handleMusicKitPlaybackSurfaceChange() }" in library
    assert "Timer.publish(every: 0.5, on: .main, in: .common).autoconnect()" in library
    assert "handleMusicKitReadingBedWatchdogTick()" in library
    library_ownership_body = _function_body(library, "private func handleAudioOwnershipChange(_ state: AudioOwnership)")
    assert "case .appleMusicBed:" in library_ownership_body
    assert "configureAppleMusicBedAudioSession()" in library_ownership_body
    assert "viewModel.audioCoordinator.configureAudioSessionForMixing(false)" in library_ownership_body
    assert "publishReaderNowPlayingSnapshot(force: true)" in library_ownership_body
    assert "scheduleAppleMusicBedNowPlayingReassertion()" in library_ownership_body
    assert "@AppStorage(MusicPreferences.musicVolumeKey) var musicVolume" in library
    assert "private var appleMusicDuckingMixThreshold: Double { 0.35 }" in library
    assert "private func configureAppleMusicBedAudioSession()" in library
    assert "viewModel.audioCoordinator.configureAudioSessionForMixing(" in library
    assert "duckOthers: musicVolume < appleMusicDuckingMixThreshold" in library
    library_reassertion_scheduler_body = _function_body(library, "func scheduleAppleMusicBedNowPlayingReassertion()")
    assert "guard shouldKeepReaderNowPlayingReassertionAlive else { return }" in library_reassertion_scheduler_body
    assert "guard nowPlayingReassertionTask == nil else { return }" in library_reassertion_scheduler_body
    assert "defer { nowPlayingReassertionTask = nil }" in library_reassertion_scheduler_body
    assert "75_000_000" in library_reassertion_scheduler_body
    assert "850_000_000" in library_reassertion_scheduler_body
    assert "try? await Task.sleep(nanoseconds: 1_000_000_000)" in library_reassertion_scheduler_body
    assert 'musicOwnership.refreshMusicPlaybackSurfaceSuppression(reason: "libraryNowPlayingReassertion")' in library_reassertion_scheduler_body
    assert "private var shouldKeepReaderNowPlayingReassertionAlive: Bool" in library
    assert "private var shouldMirrorAppleMusicPauseToNarration: Bool" in library
    assert "@State var readerTransportPlaybackRecoveryTask: Task<Void, Never>?" in library
    library_reassert_body = _function_body(library, "private var shouldKeepReaderNowPlayingReassertionAlive: Bool")
    assert "musicOwnership.isSuppressingMusicPlaybackSurface" not in library_reassert_body
    assert "musicOwnership.isReaderTransportPauseGuardActive" in library_reassert_body
    assert "musicOwnership.isPausedByReaderTransport" in library_reassert_body
    assert "!musicOwnership.isManuallyPaused" in library_reassert_body
    assert "updateReaderNarrationActivityForMusicBed" in library
    library_mirror_body = _function_body(library, "private var shouldMirrorAppleMusicPauseToNarration: Bool")
    assert "musicOwnership.isPausedByReaderTransport" in library_mirror_body
    assert "#if os(tvOS)" in library_mirror_body
    assert "musicOwnership.isManuallyPaused && musicOwnership.ownershipState == .appleMusicBed" in library_mirror_body
    assert "guard viewModel.audioCoordinator.isPlaybackRequested || viewModel.audioCoordinator.isPlaying else" in library_mirror_body
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
    assert "cancelReaderTransportPlaybackRecovery()" in library_music_surface_body
    assert 'lastReaderTransportAction = "pause"' in library_music_surface_body
    assert "localReaderTransportPauseHoldUntil = ProcessInfo.processInfo.systemUptime + ReaderTransportCommandResolver.pauseHoldWindow" in library_music_surface_body
    assert "viewModel.pauseForReaderTransport()" in library_music_surface_body
    assert "return" in library_music_surface_body
    library_mirror_play_body = _function_body(library, "private var shouldMirrorAppleMusicPlayToNarration: Bool")
    assert "musicOwnership.isPlaying" in library_mirror_play_body
    assert "!musicOwnership.isManuallyPaused" in library_mirror_play_body
    assert "!musicOwnership.isPausedByReaderTransport" in library_mirror_play_body
    assert "!musicOwnership.isReaderTransportPauseGuardActive" in library_mirror_play_body
    assert "!viewModel.audioCoordinator.isPlaybackRequested" in library_mirror_play_body
    assert "!viewModel.audioCoordinator.isPlaying" in library_mirror_play_body
    library_watchdog_body = _function_body(library, "private func handleMusicKitReadingBedWatchdogTick()")
    assert "musicOwnership.ownershipState == .appleMusicBed" in library_watchdog_body
    assert "!musicOwnership.isReaderTransportPauseGuardActive" in library_watchdog_body
    assert "viewModel.audioCoordinator.isPlaybackRequested || viewModel.audioCoordinator.isPlaying" in library_watchdog_body
    assert library_watchdog_body.index("if shouldMirrorAppleMusicPauseToNarration") < library_watchdog_body.index(
        "guard !musicOwnership.isReaderTransportPauseGuardActive else { return }"
    )
    assert library_watchdog_body.index("guard !musicOwnership.isReaderTransportPauseGuardActive else { return }") < library_watchdog_body.index(
        "musicOwnership.reconcileReadingBedSystemPlayback()"
    )
    assert "musicOwnership.reconcileReadingBedSystemPlayback()" in library_watchdog_body
    assert 'musicOwnership.recoverReadingBedForActiveNarration(reason: "libraryWatchdog")' in library_watchdog_body
    assert 'musicOwnership.refreshMusicPlaybackSurfaceSuppression(reason: "libraryWatchdog")' in library_watchdog_body
    assert "viewModel.pauseForReaderTransport()" in library_watchdog_body
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
    assert "private func resolvedReaderTransportAction(forCommand command: String) -> String" in library_now_playing
    library_accept_body = _function_body(library_now_playing, "private func shouldAcceptReaderTransportCommand(_ command: String, resolvedAction: String)")
    assert "shouldBlockReaderTransportResumeAfterPause(resolvedAction: resolvedAction, elapsed: elapsed, now: now)" in library_accept_body
    library_block_resume_body = _function_body(library_now_playing, "private func shouldBlockReaderTransportResumeAfterPause")
    assert "ReaderTransportCommandResolver.shouldHoldReaderResumeAfterPause" in library_block_resume_body
    assert "musicOwnership.shouldRejectReaderTransportResumeAfterPause" in library_block_resume_body
    assert 'lastReaderTransportAction != "pause" || elapsed < readerTransportDuplicateWindow' not in library_block_resume_body
    assert "now < localReaderTransportPauseHoldUntil" in library_block_resume_body
    assert "musicOwnership.isReaderTransportPauseHoldWindowActive" in library_block_resume_body
    library_resolve_body = _function_body(library_now_playing, "private func resolvedReaderTransportAction(forCommand command: String) -> String")
    assert "#if os(tvOS)" not in library_resolve_body
    assert 'if command == "play" || command == "pause" || command == "toggle"' not in library_resolve_body
    assert "ReaderTransportCommandResolver.resolvedAction(" in library_resolve_body
    assert "ReaderTransportCommandResolver.duplicateWindow" in library_now_playing
    assert "ReaderTransportCommandResolver.shouldReapplyDuplicateCommand" in library_accept_body
    assert "ReaderTransportCommandResolver.shouldRejectDuplicateCommand" in library_accept_body
    assert "command reapplying duplicate action=" in library_accept_body
    assert "return shouldPauseReaderTransportForToggle" not in library_now_playing
    assert "private func performReaderNowPlayingTransport(action: String)" in library_now_playing
    library_play_body = _function_body(library_now_playing, "func playReaderNowPlayingTransport()")
    library_pause_body = _function_body(library_now_playing, "func pauseReaderNowPlayingTransport()")
    assert 'let resolvedAction = resolvedReaderTransportAction(forCommand: "play")' in library_play_body
    assert "performReaderNowPlayingTransport(action: resolvedAction)" in library_play_body
    assert 'let resolvedAction = resolvedReaderTransportAction(forCommand: "pause")' in library_pause_body
    assert "performReaderNowPlayingTransport(action: resolvedAction)" in library_pause_body
    library_pause_music_body = _function_body(library_now_playing, "private func pauseAppleMusicBedFromReaderTransportIfNeeded()")
    assert "nowPlayingReassertionTask?.cancel()" in library_pause_music_body
    assert "nowPlayingReassertionTask = nil" in library_pause_music_body
    assert "scheduleAppleMusicBedNowPlayingReassertion()" in library_pause_music_body
    library_resume_music_body = _function_body(library_now_playing, "private func resumeAppleMusicBedFromReaderTransportIfNeeded()")
    assert "musicOwnership.ownershipState == .appleMusicBed" in library_resume_music_body
    assert "musicOwnership.ownershipState == .appleMusic" in library_resume_music_body
    assert "musicOwnership.prepareForNarrationMix()" in library_resume_music_body
    assert "musicOwnership.resumeReadingBedForReaderTransport()" in library_resume_music_body
    assert "Task { @MainActor" not in library_resume_music_body
    assert "ensureLastSelectionLoadedForReadingBed()" not in library_resume_music_body
    assert library_resume_music_body.index("musicOwnership.resumeReadingBedForReaderTransport()") < library_resume_music_body.index(
        "publishReaderNowPlayingSnapshot(force: true)"
    )
    assert "scheduleAppleMusicBedNowPlayingReassertion()" in library_now_playing

    assert "struct MusicBedSyncE2EControls: View" in chrome
    assert 'ProcessInfo.processInfo.environment["E2E_MUSIC_BED_SYNC_TEST"] == "1"' in chrome
    assert 'accessibilityIdentifier("e2eMusicBedPauseButton")' in chrome
    assert 'accessibilityLabel("e2eMusicBedPauseButton")' in chrome
    assert 'accessibilityIdentifier("e2eMusicBedPlayButton")' in chrome
    assert 'accessibilityLabel("e2eMusicBedPlayButton")' in chrome
    assert 'accessibilityIdentifier("e2eObservedMusicPauseButton")' in chrome
    assert 'accessibilityLabel("e2eObservedMusicPauseButton")' in chrome
    assert 'accessibilityIdentifier("e2eReaderPlayCommandButton")' in chrome
    assert 'accessibilityLabel("e2eReaderPlayCommandButton")' in chrome
    assert 'accessibilityIdentifier("e2eReaderPauseCommandButton")' in chrome
    assert 'accessibilityLabel("e2eReaderPauseCommandButton")' in chrome
    assert 'accessibilityIdentifier("e2eReaderToggleCommandButton")' in chrome
    assert 'accessibilityLabel("e2eReaderToggleCommandButton")' in chrome
    assert "musicOwnership.simulateAlreadyPlayingAutoResumeForE2E()" in chrome
    assert 'accessibilityIdentifier("e2eMusicBedAutoResumeButton")' in chrome
    assert 'accessibilityLabel("e2eMusicBedAutoResumeButton")' in chrome
    assert "musicOwnership.simulateSentenceTransitionForE2E()" in chrome
    assert "audioCoordinator.simulateRequestedTransitionPauseForMusicBedE2E()" in chrome
    assert 'accessibilityIdentifier("e2eReaderTransitionButton")' in chrome
    assert 'accessibilityLabel("e2eReaderTransitionButton")' in chrome
    assert "audioCoordinator.simulateRequestedTransitionResumeForMusicBedE2E()" in chrome
    assert 'musicOwnership.simulateSentenceTransitionForE2E(phase: "sentenceTransitionResume")' in chrome
    assert 'accessibilityIdentifier("e2eReaderTransitionResumeButton")' in chrome
    assert 'accessibilityLabel("e2eReaderTransitionResumeButton")' in chrome
    assert "NotificationCenter.default.post(name: .e2eBubblePronunciationResume, object: nil)" in chrome
    assert 'accessibilityIdentifier("e2eBubblePronunciationResumeButton")' in chrome
    assert 'accessibilityLabel("e2eBubblePronunciationResumeButton")' in chrome
    assert 'accessibilityIdentifier("e2eMusicBedSyncStatus")' in chrome
    assert 'accessibilityLabel("e2eMusicBedSyncStatus")' in chrome
    assert 'accessibilityIdentifier("e2eMusicBedSyncControls")' in chrome
    assert "private enum MusicBedSyncE2EState" in chrome
    assert "static var didRunAutoSequence = false" in chrome
    assert "private func runAutoSequenceIfNeeded() async" in chrome
    assert "DispatchQueue.main.asyncAfter(deadline: .now() + 8.0)" in chrome
    assert "#if os(tvOS)" in chrome
    assert "DispatchQueue.main.asyncAfter(deadline: .now() + 20.0)" in chrome
    assert "DispatchQueue.main.asyncAfter(deadline: .now() + 45.0)" in chrome
    assert "musicOwnership.simulateObservedNonPlayingPauseForE2E()" in chrome
    assert "musicOwnership.simulateReadingBedPauseForE2E()" in chrome
    assert "musicOwnership.simulateReadingBedPlayForE2E()" in chrome
    assert 'NotificationCenter.default.post(name: .keyboardShortcutLookup, object: nil)' in chrome
    assert 'accessibilityIdentifier("e2eKeyboardLookupCommandButton")' in chrome
    assert "MusicBedSyncE2EControls(" in job
    assert "MusicBedSyncE2EControls(" in library
    assert "musicOwnership.ensureReadingBedPlayStateForE2E()" in chrome
    assert '"guard=\\(musicOwnership.isReaderTransportPauseGuardActive ? "true" : "false")"' in chrome
    assert '"owner=\\(musicOwnership.ownershipState)"' in chrome
    assert '"surface=\\(musicOwnership.isReaderPlaybackSurfaceActive ? "reader" : "music")"' in chrome
    assert '"fullscreen=\\(musicOwnership.isFullscreenMusicArtworkSuppressed ? "blocked" : "available")"' in chrome
    assert '"sessionStable=\\(audioCoordinator.isAudioSessionStableForMusicBed ? "true" : "false")"' in chrome
    assert '"sessionLabel=\\(audioCoordinator.audioSessionLastLabel)"' in chrome
    assert '"sessionApply=\\(audioCoordinator.audioSessionApplyCount)"' in chrome
    assert '"sessionSkip=\\(audioCoordinator.audioSessionSkipCount)"' in chrome
    assert '"autoResumeAlreadyPlaying=\\(musicOwnership.e2eMusicBedAlreadyPlayingResumeSkipCount)"' in chrome
    assert '"transitionPauses=\\(audioCoordinator.e2eRequestedTransitionPauseCount)"' in chrome
    assert "fields.append(InteractivePlayerE2EState.statusText)" in chrome

    interactive_linguist = _source(INTERACTIVE / "InteractivePlayerView+Linguist.swift")
    lookup_pause_body = _function_body(interactive_linguist, "func pausePlaybackForLinguistLookupIfNeeded()")
    assert "audioCoordinator.isPlaying || audioCoordinator.isPlaybackRequested" in lookup_pause_body
    assert "musicCoordinator.ownershipState == .appleMusicBed" in lookup_pause_body
    assert "!musicCoordinator.isPausedByReaderTransport" in lookup_pause_body
    assert "musicCoordinator.pauseReadingBedForReaderTransport()" in lookup_pause_body
    assert "viewModel.pauseForReaderTransport()" in lookup_pause_body
    assert lookup_pause_body.index("musicCoordinator.pauseReadingBedForReaderTransport()") < lookup_pause_body.index(
        "viewModel.pauseForReaderTransport()"
    )

    journey = _source(ROOT / "tests" / "e2e" / "journeys" / "music_bed_sync.json")
    assert '"key": "right"' in journey
    assert '"key": "left"' in journey
    assert '"key": "enter"' in journey
    assert '"selector": "e2eKeyboardLookupCommandButton"' in journey
    assert '"key": "bubbleWordNav"' in journey
    assert '"key": "bubbleLookup"' in journey
    assert '"text": "bubbleWordNavDirection=1"' in journey
    assert '"text": "bubbleWordNavDirection=-1"' in journey
    assert '"text": "bubbleLookupHadBubble=true"' in journey
    assert '"text": "fullscreen=blocked"' in journey
    assert "music_bed_guarded_remote_play_pressed" in journey
    assert "music_bed_guarded_remote_play_ignored" in journey
    assert '"count": 2' in journey
    assert "music_bed_remote_double_pause_pressed" in journey


def test_apple_music_reader_pause_suppresses_music_surface_until_reader_resumes() -> None:
    music = _source(SERVICES / "MusicKitCoordinator.swift")
    audio = _source(SERVICES / "AudioPlayerCoordinator.swift")

    assert "@Published private(set) var isSuppressingMusicPlaybackSurface = false" in music
    assert "var isReaderPlaybackSurfaceActive: Bool" in music
    surface_body = _function_body(music, "var isReaderPlaybackSurfaceActive: Bool")
    assert "isSuppressingMusicPlaybackSurface || ownershipState == .appleMusicBed" in surface_body
    assert "#if os(tvOS)\nimport UIKit\n#endif" in music
    assert "private var didDisableIdleTimerForMusicSurface = false" in music
    assert "private var tvOSMusicSurfaceSuppressionWatchdogTask: Task<Void, Never>?" in music
    fullscreen_body = _function_body(music, "var isFullscreenMusicArtworkSuppressed: Bool")
    assert "PlaybackIdleTimerCoordinator.shared.isMusicSurfaceSuppressed" in fullscreen_body
    assert "isReaderPlaybackSurfaceActive" in fullscreen_body
    assert "private var isReaderTransportPauseSuppressionActive: Bool" in music
    suppression_body = _function_body(music, "private var isReaderTransportPauseSuppressionActive: Bool")
    assert "ownershipState == .appleMusicBed" in suppression_body
    assert "isPausedByReaderTransport" in suppression_body
    assert "isManuallyPaused" in suppression_body

    observed_play_body = _function_body(music, "private var shouldSuppressObservedPlayDuringReaderPause: Bool")
    assert "isReaderTransportPauseGuardActive" in observed_play_body
    observed_non_playing_body = _function_body(music, "private func handleObservedNonPlayingStatus(")
    assert "shouldAdoptObservedNonPlayingImmediately" not in music
    assert "observedNonPlayingImmediate" not in observed_non_playing_body
    assert "observed non-playing immediate" not in observed_non_playing_body
    assert observed_non_playing_body.index("shouldDeferObservedNonPlayingDuringActiveReadingBed") < observed_non_playing_body.index(
        "observedNonPlayingTask?.cancel()"
    )

    reconcile_body = _function_body(music, "func reconcileReadingBedSystemPlayback()")
    assert "guard !isReaderTransportPauseSuppressionActive else" in reconcile_body
    assert 'pauseSystemPlayerForReaderTransport(reason: "reconcileReaderPause")' in reconcile_body
    assert 'updateMusicPlaybackSurfaceSuppression(reason: "reconcileReaderPause")' in reconcile_body

    confirmation_body = _function_body(music, "private func scheduleReaderTransportPauseConfirmation()")
    assert "self.shouldSuppressObservedPlayDuringReaderPause" in confirmation_body
    assert 'pauseSystemPlayerForReaderTransport(reason: "readerTransportPauseConfirmation")' in confirmation_body
    assert 'updateMusicPlaybackSurfaceSuppression(reason: "readerTransportPauseConfirmation")' in confirmation_body

    reader_pause_body = _function_body(music, "func pauseReadingBedForReaderTransport()")
    assert 'adoptPauseAsReaderTransport(reason: "readerTransportPause", source: "reader transport")' in reader_pause_body
    adopt_pause_body = _function_body(music, "private func adoptPauseAsReaderTransport(reason: String, source: String)")
    assert "pauseSystemPlayerForReaderTransport(reason: reason)" in adopt_pause_body

    pause_body = _function_body(music, "private func pauseSystemPlayerForReaderTransport(reason: String)")
    assert "#if os(tvOS)" in pause_body
    assert "ApplicationMusicPlayer.shared.pause()" in pause_body
    assert "scheduleTVOSSystemPlaybackSurfaceSuppression(reason: reason)" in pause_body
    assert "paused tvOS system playback surface" in pause_body
    assert "private func scheduleTVOSSystemPlaybackSurfaceSuppression(reason: String)" in music
    assert "private func startTVOSMusicSurfaceSuppressionWatchdog(reason: String)" in music
    assert "private func stopTVOSMusicSurfaceSuppressionWatchdog()" in music
    assert "private func reassertFullscreenMusicArtworkSuppressionIfNeeded(reason: String)" in music
    assert "private var shouldKeepFullscreenMusicArtworkSuppressed: Bool" in music
    assert "tvOSMusicSurfaceSuppressionWatchdogTask?.cancel()" in music
    assert 'reassertFullscreenMusicArtworkSuppressionIfNeeded(reason: "tvOSFullscreenWatchdog")' in music
    delayed_release_body = _function_body(music, "private func scheduleTVOSSystemPlaybackSurfaceSuppression(reason: String)")
    assert "suppressionDelays" in delayed_release_body
    assert "12_500_000_000" in delayed_release_body
    assert "15_000_000_000" in delayed_release_body
    assert "self.shouldSuppressObservedPlayDuringReaderPause" in delayed_release_body
    assert "updateFullscreenMusicArtworkSuppression(true" in delayed_release_body
    assert "Apple Music tvOS playback surface suppression re-pausing stray playback" in delayed_release_body
    assert "ApplicationMusicPlayer.shared.stop()" not in delayed_release_body
    assert "self.hasRestoredQueueForAutoResume = false" not in delayed_release_body
    assert "tvOSSurfaceSuppressed" in delayed_release_body
    assert "Apple Music reader transport kept tvOS playback surface suppressed" in delayed_release_body
    assert "private var tvOSSystemSurfaceSuppressionTask: Task<Void, Never>?" in music
    assert "tvOSSystemSurfaceReleaseTask" not in music
    assert "private func cancelTVOSSystemPlaybackSurfaceSuppression()" in music
    cancel_release_body = _function_body(music, "private func cancelTVOSSystemPlaybackSurfaceSuppression()")
    assert "tvOSSystemSurfaceSuppressionTask?.cancel()" in cancel_release_body
    assert "tvOSSystemSurfaceSuppressionTask = nil" in cancel_release_body
    assert "#else" in pause_body
    assert "ApplicationMusicPlayer.shared.pause()" in pause_body

    update_surface_body = _function_body(music, "private func updateMusicPlaybackSurfaceSuppression(reason: String)")
    assert "updateFullscreenMusicArtworkSuppression(shouldSuppress, reason: reason)" in update_surface_body
    refresh_surface_body = _function_body(music, "func refreshMusicPlaybackSurfaceSuppression(reason: String)")
    assert "updateMusicPlaybackSurfaceSuppression(reason: reason)" in refresh_surface_body
    assert "reassertFullscreenMusicArtworkSuppressionIfNeeded(reason: reason)" in refresh_surface_body
    fullscreen_body = _function_body(music, "private func updateFullscreenMusicArtworkSuppression(_ shouldSuppress: Bool, reason: String)")
    assert "#if os(tvOS)" in fullscreen_body
    assert "startTVOSMusicSurfaceSuppressionWatchdog(reason: reason)" in fullscreen_body
    assert "stopTVOSMusicSurfaceSuppressionWatchdog()" in fullscreen_body
    assert "let wasSuppressed = PlaybackIdleTimerCoordinator.shared.isMusicSurfaceSuppressed" in fullscreen_body
    assert "wasSuppressed != shouldSuppress" in fullscreen_body
    assert "didDisableIdleTimerForMusicSurface = shouldSuppress" in fullscreen_body
    assert "PlaybackIdleTimerCoordinator.shared.setMusicSurfaceIdleDisabled(shouldSuppress)" in fullscreen_body
    assert "Apple Music fullscreen artwork suppression=" in fullscreen_body
    reassert_fullscreen_body = _function_body(music, "private func reassertFullscreenMusicArtworkSuppressionIfNeeded(reason: String)")
    assert "shouldKeepFullscreenMusicArtworkSuppressed" in reassert_fullscreen_body
    assert "PlaybackIdleTimerCoordinator.shared.reassertMusicSurfaceIdleDisabled()" in reassert_fullscreen_body
    assert "Apple Music fullscreen artwork suppression reasserted" in reassert_fullscreen_body
    assert "fullscreenSuppressionReasserted" in reassert_fullscreen_body

    idle_body = _function_body(audio, "private func setIdleTimerDisabled(_ disabled: Bool)")
    assert "#if os(iOS) || os(tvOS)" in idle_body
    assert "PlaybackIdleTimerCoordinator.shared.setReaderPlaybackIdleDisabled(disabled)" in idle_body
    assert "final class PlaybackIdleTimerCoordinator" in audio
    assert "setReaderPlaybackIdleDisabled" in audio
    assert "setMusicSurfaceIdleDisabled" in audio
    assert "func reassertMusicSurfaceIdleDisabled()" in audio
    assert "apply(force: true)" in audio
    assert "private func apply(force: Bool = false)" in audio
    assert "isReaderPlaybackDisablingIdleTimer || isMusicSurfaceDisablingIdleTimer" in audio


def test_apple_music_now_playing_device_evidence_is_documented() -> None:
    testing = TESTING_DOC.read_text(encoding="utf-8")

    assert "MPNowPlayingSession" in testing
    assert "Reader NowPlaying session attached player=true" in testing
    assert "Reader NowPlaying session active=true canBecomeActive=true" in testing
    assert "Reader NowPlaying session reassert requested" in testing
    assert "private-entitlement-gated MediaRemote playback-state\nsetter" in testing


def test_apple_music_reading_bed_uses_neutral_audio_session_while_mixing() -> None:
    audio = _source(SERVICES / "AudioPlayerCoordinator.swift")
    mixing_body = _function_body(audio, "func configureAudioSessionForMixing(")
    configure_body = _function_body(audio, "private func configureAudioSession(force: Bool = false) -> Bool")

    assert "configureAudioSession()" in mixing_body
    assert "var mode: AVAudioSession.Mode" in audio
    assert "mixing ? .default : .spokenAudio" in audio
    assert "let mode = configuration.mode" in configure_body
    assert "return duckOthers ? [.mixWithOthers, .duckOthers] : [.mixWithOthers]" in audio
    assert "private var appliedAudioSessionConfiguration: AudioSessionConfiguration?" in audio
    assert "private struct AudioSessionConfiguration: Equatable" in audio
    assert "@Published private(set) var audioSessionApplyCount = 0" in audio
    assert "@Published private(set) var audioSessionSkipCount = 0" in audio
    assert '@Published private(set) var audioSessionLastLabel = "unconfigured"' in audio
    assert "var isAudioSessionStableForMusicBed: Bool" in audio
    assert "audioSessionApplyCount <= 2" in audio
    assert "let configuration = AudioSessionConfiguration(" in configure_body
    assert "guard force || appliedAudioSessionConfiguration != configuration else" in configure_body
    assert "audioSessionSkipCount += 1" in configure_body
    assert "audioSessionLastLabel = configuration.label" in configure_body
    assert "Skipped unchanged audio session" in configure_body
    assert "appliedAudioSessionConfiguration = configuration" in configure_body
    assert "audioSessionApplyCount += 1" in configure_body
    assert "appliedAudioSessionConfiguration = nil" in configure_body
    assert "self.appliedAudioSessionConfiguration = nil" in audio


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
    assert ".onPlayPauseCommand" in shell
    assert "handleTVShellPlayPauseCommand()" in shell
    shell_play_pause_body = _function_body(shell, "private func handleTVShellPlayPauseCommand()")
    assert "#if os(tvOS)" in shell_play_pause_body
    assert "guard navigationPath.isEmpty, nowPlayingTarget != nil else { return }" in shell_play_pause_body
    assert "TV shell Play/Pause returning to Now Playing" in shell_play_pause_body
    assert "returnToNowPlaying()" in shell_play_pause_body
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
