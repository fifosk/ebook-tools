from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APPLE = ROOT / "ios" / "InteractiveReader" / "InteractiveReader"
SERVICES = APPLE / "Services"
PLAYBACK = APPLE / "Features" / "Playback"
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
