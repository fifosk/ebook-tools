from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APPLE = ROOT / "ios" / "InteractiveReader" / "InteractiveReader"
SHARED = APPLE / "Features" / "Shared"
INTERACTIVE = APPLE / "Features" / "InteractivePlayer"
PLAYBACK = APPLE / "Features" / "Playback"


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_search_and_bookmark_pills_are_native_accessible_controls() -> None:
    search_controls = _source(SHARED / "MediaSearchControls.swift")
    search_results = _source(SHARED / "MediaSearchResultsViews.swift")
    bookmark_pill = _source(PLAYBACK / "BookmarkRibbonPillView.swift")

    assert "struct MediaSearchPillView: View" in search_controls
    assert "Button(action: onTap)" in search_controls
    assert '.accessibilityIdentifier("mediaSearchPill")' in search_controls
    assert "TVSearchPillButtonStyle" in search_controls

    assert "struct MediaSearchResultRowView: View" in search_results
    assert "Button(action: handleSelect)" in search_results
    assert '.accessibilityIdentifier("mediaSearchResultRow.\\(model.id)")' in search_results
    assert "TVSearchResultCardStyle" in search_results

    assert "struct BookmarkRibbonPillView: View" in bookmark_pill
    assert "Menu {" in bookmark_pill
    assert '.accessibilityIdentifier("bookmarkRibbonPill")' in bookmark_pill
    assert "Section(\"Jump\")" in bookmark_pill
    assert "handleJumpToBookmark(bookmark)" in bookmark_pill


def test_interactive_playback_search_and_bookmarks_share_jump_paths() -> None:
    interactive_search = _source(INTERACTIVE / "InteractivePlayerView+Search.swift")
    interactive_bookmarks = _source(INTERACTIVE / "InteractivePlayerView+Bookmarks.swift")
    interactive_header = _source(INTERACTIVE / "InteractivePlayerView+HeaderOverlay.swift")

    assert "MediaSearchPillView(" in interactive_search
    assert "actionType: .jumpToSentence" in interactive_search
    assert "searchViewModel.calculateTargetSentence(from: result)" in interactive_search
    assert "viewModel.jumpToSentence(targetSentence, autoPlay: audioCoordinator.isPlaybackRequested)" in interactive_search
    assert "MediaSearchOverlayView(" in interactive_search

    assert "BookmarkRibbonPillView(" in interactive_bookmarks
    assert "onJumpToBookmark: jumpToBookmark" in interactive_bookmarks
    assert "viewModel.jumpToSentence(sentence, autoPlay: audioCoordinator.isPlaybackRequested)" in interactive_bookmarks
    assert "viewModel.jumpToTime(time, in: chunk, autoPlay: audioCoordinator.isPlaybackRequested)" in interactive_bookmarks
    assert "DispatchQueue.main.async" not in interactive_bookmarks

    assert "jumpPillView" in interactive_header
    assert "searchPillView" in interactive_header
    assert "bookmarkRibbonPillView" in interactive_header
    assert ".focusScope(headerControlsNamespace)" in interactive_header
    assert ".focused($focusedArea, equals: .controls)" in interactive_header


def test_video_playback_search_bookmarks_and_tvos_focus_are_reachable() -> None:
    video_search = _source(PLAYBACK / "VideoPlayerView+Search.swift")
    video_bookmarks = _source(PLAYBACK / "VideoPlayerView+Bookmarks.swift")
    tv_focus = _source(PLAYBACK / "VideoPlayerOverlayTVFocus.swift")
    tv_layout = _source(PLAYBACK / "VideoPlayerOverlayView+TVLayout.swift")
    overlay_config = _source(PLAYBACK / "VideoPlayerOverlayConfiguration.swift")

    assert "MediaSearchPillView(" in video_search
    assert "actionType: .seekToTime" in video_search
    assert "searchViewModel.calculateSeekTime(from: result)" in video_search
    assert "coordinator.seek(to: seekTime)" in video_search
    assert "scrubberValue = seekTime" in video_search
    assert ".focusScope(searchFocusNamespace)" in video_search

    assert "func jumpToBookmark(_ bookmark: PlaybackBookmarkEntry)" in video_bookmarks
    assert "pendingBookmarkSeek = PendingVideoBookmarkSeek" in video_bookmarks
    assert "onSelectSegment(segmentId)" in video_bookmarks
    assert "applyBookmarkSeek(time: time, shouldPlay: shouldPlay)" in video_bookmarks

    assert "case headerSearch" in overlay_config
    assert "func handleSearchPillMoveCommand(_ direction: MoveCommandDirection)" in tv_focus
    assert "focusTarget = .control(.headerSearch)" in tv_focus
    assert "focusTarget = .control(.headerBookmark)" in tv_focus
    assert ".focused($focusTarget, equals: .control(.headerSearch))" in tv_layout
    assert ".onMoveCommand(perform: handleSearchPillMoveCommand)" in tv_layout
    assert "onMoveLeft: searchPill == nil ? nil : { focusTarget = .control(.headerSearch) }" in tv_layout
    assert "onMoveRight: { focusTarget = .control(.header) }" in tv_layout


def test_interactive_bookmark_time_jumps_wait_for_ready_audio() -> None:
    selection = _source(INTERACTIVE / "InteractivePlayerViewModel+Selection.swift")
    models = _source(INTERACTIVE / "InteractivePlayerModels.swift")
    loading = _source(INTERACTIVE / "InteractivePlayerViewModel+Loading.swift")
    view_model = _source(INTERACTIVE / "InteractivePlayerViewModel.swift")

    assert "struct PendingTimeSeek" in models
    assert "var pendingTimeSeek: PendingTimeSeek?" in view_model
    assert "pendingTimeSeek = nil" in loading

    assert "func jumpToTime(_ time: Double, in chunk: InteractiveChunk, autoPlay: Bool = false)" in selection
    assert "pendingTimeSeek = PendingTimeSeek(chunkID: chunk.id, time: time, autoPlay: autoPlay)" in selection
    assert "selectChunk(id: chunk.id, autoPlay: autoPlay)" in selection
    assert "func attemptPendingTimeSeek(in chunk: InteractiveChunk)" in selection
    assert "seekPlaybackWhenReady(to: pending.time, in: chunk, autoPlay: pending.autoPlay)" in selection
    assert "func seekPlaybackWhenReady(to time: Double, in chunk: InteractiveChunk, autoPlay: Bool)" in selection
    assert "guard let currentChunk = self.selectedChunk, currentChunk.id == chunkId else" in selection
    assert "if autoPlay && !self.audioCoordinator.isPlaying" in selection

    immediate_prepare = (
        "prepareAudio(for: chunk, autoPlay: autoPlay, targetSentenceIndex: effectiveTargetIndex)\n"
        "            attemptPendingSentenceJump(in: chunk)\n"
        "            attemptPendingTimeSeek(in: chunk)"
    )
    metadata_prepare = (
        "self.prepareAudio(for: updatedChunk, autoPlay: autoPlay, targetSentenceIndex: effectiveTargetIndex)\n"
        "            self.attemptPendingSentenceJump(in: updatedChunk)\n"
        "            self.attemptPendingTimeSeek(in: updatedChunk)"
    )
    assert immediate_prepare in selection
    assert metadata_prepare in selection
