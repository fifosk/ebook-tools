from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APPLE = ROOT / "ios" / "InteractiveReader" / "InteractiveReader"
SERVICES = APPLE / "Services"
PLAYBACK = APPLE / "Features" / "Playback"
LIBRARY = APPLE / "Features" / "Library"
SUPPORTING = APPLE / "Supporting"


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
    job_now_playing = _source(PLAYBACK / "JobPlaybackView+NowPlaying.swift")
    library_now_playing = _source(PLAYBACK / "LibraryPlaybackView+NowPlaying.swift")
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

    assert "onPlay: { viewModel.audioCoordinator.play() }" in job_now_playing
    assert "onPause: { viewModel.audioCoordinator.pause() }" in job_now_playing
    assert "onNext: { viewModel.skipSentence(forward: true) }" in job_now_playing
    assert "onPrevious: { viewModel.skipSentence(forward: false) }" in job_now_playing
    assert "onSeek: { viewModel.audioCoordinator.seek(to: $0) }" in job_now_playing
    assert "onToggle: { viewModel.audioCoordinator.togglePlayback() }" in job_now_playing
    assert "onBookmark: { addNowPlayingBookmark() }" in job_now_playing

    assert "onPlay: { viewModel.audioCoordinator.play() }" in library_now_playing
    assert "onPause: { viewModel.audioCoordinator.pause() }" in library_now_playing
    assert "onNext: { viewModel.skipSentence(forward: true) }" in library_now_playing
    assert "onPrevious: { viewModel.skipSentence(forward: false) }" in library_now_playing
    assert "onSeek: { viewModel.audioCoordinator.seek(to: $0) }" in library_now_playing
    assert "onToggle: { viewModel.audioCoordinator.togglePlayback() }" in library_now_playing
    assert "onBookmark: { addNowPlayingBookmark() }" in library_now_playing

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
    clear_body = _function_body(coordinator, "func clear()")

    assert "metadata = [:]" in clear_body
    assert "lastElapsedUpdate = -1" in clear_body
    assert "lastDuration = -1" in clear_body
    assert "lastArtworkURL = nil" in clear_body
    assert "MPNowPlayingInfoCenter.default().nowPlayingInfo = nil" in clear_body


def test_ios_declares_audio_background_mode_for_lock_screen_playback() -> None:
    info = _source(SUPPORTING / "Info.plist")

    assert "<key>UIBackgroundModes</key>" in info
    assert "<string>audio</string>" in info


def test_library_shell_exposes_cross_surface_now_playing_return_button() -> None:
    shell = _source(LIBRARY / "LibraryShellView.swift")
    button = _source(LIBRARY / "LibraryShellNowPlayingReturnButton.swift")
    project = _source(ROOT / "ios" / "InteractiveReader" / "InteractiveReader.xcodeproj" / "project.pbxproj")

    assert "private enum NowPlayingPlaybackTarget: Hashable" in shell
    assert "@State private var nowPlayingTargetSnapshot: NowPlayingPlaybackTarget?" in shell
    assert "@FocusState private var isNowPlayingReturnFocused: Bool" in shell
    assert "private var nowPlayingTarget: NowPlayingPlaybackTarget?" in shell
    assert "if let nowPlayingTargetSnapshot" in shell
    assert "private var shouldShowNowPlayingReturnButton: Bool" in shell
    assert "return !isSplitLayout || activeSection == .create || activeSection == .settings" in shell
    assert "private var nowPlayingReturnHorizontalPadding: CGFloat" in shell
    assert "return isCompactLayout ? 16 : 12" in shell
    assert "private var nowPlayingReturnTopPadding: CGFloat" in shell
    assert "nowPlayingReturnButton(for: nowPlayingTarget)" in shell
    assert ".focused($isNowPlayingReturnFocused)" in shell
    assert "#if os(tvOS)\n            if let nowPlayingTarget" not in shell
    assert "#if os(tvOS)\n    private func nowPlayingReturnButton" not in shell
    assert "LibraryShellNowPlayingReturnButton(" in shell
    assert "struct LibraryShellNowPlayingReturnButton: View" in button
    assert "let title: String" in button
    assert "let subtitle: String?" in button
    assert "let horizontalPadding: CGFloat" in button
    assert "let topPadding: CGFloat" in button
    assert "let action: () -> Void" in button
    assert '.accessibilityLabel("Return to Now Playing")' in button
    assert ".accessibilityValue(title)" in button
    assert '.accessibilityIdentifier("nowPlayingReturnButton")' in button

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
    assert "if isSplitLayout" in return_body
    assert "collapseSidebar()" in return_body
    assert "navigationPath.append(item)" in return_body
    assert "navigationPath.append(job)" in return_body

    focus_body = _function_body(shell, "private func focusNowPlayingReturnIfNeeded()")
    assert "guard shouldShowNowPlayingReturnButton, nowPlayingTarget != nil else { return }" in focus_body
    assert "#if os(tvOS)" in focus_body
    assert "isNowPlayingReturnFocused = true" in focus_body

    depth_body = _function_body(shell, "private func handleNavigationDepthChange(_ newValue: Int)")
    assert "guard newValue == 0 else { return }" in depth_body
    assert "focusNowPlayingReturnIfNeeded()" in depth_body

    assert "LibraryShellNowPlayingReturnButton.swift in Sources" in project
    assert project.count("LibraryShellNowPlayingReturnButton.swift in Sources") == 4
