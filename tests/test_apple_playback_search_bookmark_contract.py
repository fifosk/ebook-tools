from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APPLE = ROOT / "ios" / "InteractiveReader" / "InteractiveReader"
SHARED = APPLE / "Features" / "Shared"
INTERACTIVE = APPLE / "Features" / "InteractivePlayer"
PLAYBACK = APPLE / "Features" / "Playback"
SERVICES = APPLE / "Services"


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


def test_media_search_normalizes_job_id_before_backend_lookup() -> None:
    view_model = _source(SHARED / "MediaSearchViewModel.swift")
    api_client = _source(SERVICES / "APIClient+Linguist.swift")

    assert "jobId?.trimmingCharacters(in: .whitespacesAndNewlines)" in view_model
    assert "state = .error(\"No job ID available\")" in view_model
    assert "await runSearch(jobId: normalizedJobId, query: trimmed, using: client)" in view_model
    assert "let trimmedJobId = jobId.trimmingCharacters(in: .whitespacesAndNewlines)" in api_client
    assert "guard !trimmedJobId.isEmpty else" in api_client
    assert "URLQueryItem(name: \"job_id\", value: trimmedJobId)" in api_client
    assert "URLQueryItem(name: \"job_id\", value: jobId)" not in api_client


def test_interactive_playback_search_and_bookmarks_share_jump_paths() -> None:
    interactive_search = _source(INTERACTIVE / "InteractivePlayerView+Search.swift")
    interactive_bookmarks = _source(INTERACTIVE / "InteractivePlayerView+Bookmarks.swift")
    interactive_header = _source(INTERACTIVE / "InteractivePlayerView+HeaderOverlay.swift")
    menu_controls = _source(INTERACTIVE / "InteractivePlayerView+MenuControls.swift")
    transcript = _source(INTERACTIVE / "InteractivePlayerView+Transcript.swift")
    selection = _source(INTERACTIVE / "InteractivePlayerViewModel+Selection.swift")
    loading = _source(INTERACTIVE / "InteractivePlayerViewModel+Loading.swift")

    assert "MediaSearchPillView(" in interactive_search
    assert "actionType: .jumpToSentence" in interactive_search
    assert "searchViewModel.calculateTargetSentence(from: result)" in interactive_search
    assert "viewModel.jumpToSentence(targetSentence, autoPlay: audioCoordinator.isPlaybackRequested)" in interactive_search
    assert "MediaSearchOverlayView(" in interactive_search

    assert "BookmarkRibbonPillView(" in interactive_bookmarks
    assert "onJumpToBookmark: jumpToBookmark" in interactive_bookmarks
    assert "let shouldPlay = audioCoordinator.isPlaybackRequested" in interactive_bookmarks
    assert "prepareExplicitSentenceJump(to: sentence)" in interactive_bookmarks
    assert "viewModel.jumpToTime(time, in: chunk, autoPlay: shouldPlay)" in interactive_bookmarks
    assert "viewModel.jumpToSentence(sentence, autoPlay: shouldPlay)" in interactive_bookmarks
    assert "DispatchQueue.main.async" not in interactive_bookmarks
    add_bookmark_body = interactive_bookmarks.split("func addBookmark(for chunk: InteractiveChunk)", 1)[1].split(
        "\n    func storeBookmark",
        1,
    )[0]
    assert "storeBookmark(entry)" in add_bookmark_body
    assert add_bookmark_body.index("storeBookmark(entry)") < add_bookmark_body.index("createRemoteBookmark(")
    create_remote_body = interactive_bookmarks.split("func createRemoteBookmarkAsync(", 1)[1].split(
        "\n    func jumpToBookmark",
        1,
    )[0]
    assert "removeStoredBookmark(entry, jobId: jobId)" in create_remote_body
    assert "catch {\n            return\n        }" in create_remote_body

    assert "jumpPillView" in interactive_header
    assert "searchPillView" in interactive_header
    assert "bookmarkRibbonPillView" in interactive_header
    assert ".focusScope(headerControlsNamespace)" in interactive_header
    assert ".focused($focusedArea, equals: .controls)" in interactive_header
    assert "if isPhone, showHeaderContent {" in interactive_header
    assert "if isPhone, showHeaderContent, let info = headerInfo, !info.languageFlags.isEmpty" not in interactive_header
    assert "if !isPhone {" in interactive_header
    assert "if !isPhone, !info.languageFlags.isEmpty" not in interactive_header
    assert "private func headerInlineControlsRow(" in interactive_header
    assert "private func headerIdentityCluster(" in interactive_header
    assert "showHeaderContent && headerInfo == nil" in interactive_header
    assert "infoBadgeView(" in interactive_header
    assert "slideLabel: slideLabel" in interactive_header
    assert "timelineLabel: timelineLabel" in interactive_header
    assert "viewModel.jumpToSentence(target.startSentence, autoPlay: audioCoordinator.isPlaybackRequested)" in menu_controls
    assert "viewModel.jumpToSentence(newValue, autoPlay: audioCoordinator.isPlaybackRequested)" in transcript
    assert "viewModel.jumpToSentence(target.startSentence, autoPlay: audioCoordinator.isPlaying)" not in menu_controls
    assert "viewModel.jumpToSentence(newValue, autoPlay: audioCoordinator.isPlaying)" not in transcript

    assert "func isTranscriptReady(for chunk: InteractiveChunk) -> Bool" in selection
    assert "func isSentenceReadyForDisplay(in chunk: InteractiveChunk, targetIndex: Int?) -> Bool" in selection
    assert "let needsRenderableMetadata = !self.isSentenceReadyForDisplay(" in selection
    assert "force: needsRenderableMetadata" in selection
    assert "guard self.isSentenceReadyForDisplay(in: updatedChunk, targetIndex: targetIndex) else" in selection
    assert "self.prepareAudio(for: updatedChunk, autoPlay: autoPlay, targetSentenceIndex: targetIndex)" in selection
    assert "waitForInFlightChunkMetadataLoad" in loading


def test_interactive_reader_cover_opens_metadata_overlay_on_ios() -> None:
    interactive_view = _source(INTERACTIVE / "InteractivePlayerView.swift")
    interactive_layout = _source(INTERACTIVE / "InteractivePlayerView+Layout.swift")
    interactive_header = _source(INTERACTIVE / "InteractivePlayerView+HeaderOverlay.swift")
    metadata_overlay = _source(INTERACTIVE / "InteractivePlayerView+BookMetadataOverlay.swift")

    assert "@State var showBookMetadataOverlay = false" in interactive_view
    assert "bookMetadataOverlayContainer" in interactive_layout
    assert "InteractivePlayerBookMetadataOverlay(" in interactive_layout
    assert "onTapGesture(perform: onCoverTap)" in interactive_header
    assert "handleHeaderCoverTap" in interactive_header
    assert "func handleHeaderCoverTap()" in metadata_overlay
    assert "showBookMetadataOverlay = true" in metadata_overlay
    assert "struct InteractivePlayerBookMetadataOverlay: View" in metadata_overlay
    assert "Close book metadata" in metadata_overlay


def test_interactive_reader_jump_input_supports_ios_number_pad_submit() -> None:
    jump_overlay = _source(INTERACTIVE / "JumpControlOverlayView.swift")

    assert "private var sanitizedInputSentence: String" in jump_overlay
    assert "inputSentence.filter(\\.isNumber)" in jump_overlay
    assert ".toolbar {" in jump_overlay
    assert 'Button("Done")' in jump_overlay
    assert 'Button("Go")' in jump_overlay
    assert "onJumpToSentence(clampedSentence(inputSentenceNumber))" in jump_overlay
    assert "private func clampedSentence(_ sentence: Int) -> Int" in jump_overlay


def test_interactive_reader_uses_footer_progress_slider() -> None:
    interactive_view = _source(INTERACTIVE / "InteractivePlayerView.swift")
    interactive_layout = _source(INTERACTIVE / "InteractivePlayerView+Layout.swift")
    interactive_models = _source(INTERACTIVE / "InteractivePlayerModels.swift")
    interactive_content = _source(INTERACTIVE / "InteractivePlayerView+InteractiveContent.swift")
    interactive_header = _source(INTERACTIVE / "InteractivePlayerView+HeaderOverlay.swift")
    video_layout = _source(PLAYBACK / "VideoPlayerView+Layout.swift")
    progress_footer = _source(
        ROOT
        / "ios"
        / "InteractiveReader"
        / "InteractiveReader"
        / "Features"
        / "Shared"
        / "PlayerProgressFooterView.swift"
    )
    header_behavior = _source(INTERACTIVE / "InteractivePlayerView+HeaderBehavior.swift")
    input_handlers = _source(INTERACTIVE / "InteractivePlayerView+InputHandlers.swift")
    project = _source(ROOT / "ios" / "InteractiveReader" / "InteractiveReader.xcodeproj" / "project.pbxproj")

    assert "@State var headerSentenceSliderValue: Double?" in interactive_view
    assert "@State var isHeaderSentenceSliderEditing = false" in interactive_view
    assert '@AppStorage("interactive.phoneProgressFooterVisible") var phoneProgressFooterVisible = false' in interactive_view
    assert "@State var phoneProgressFooterAutoHideTask: Task<Void, Never>?" in interactive_view
    assert "@State var headerOverlayMeasuredHeight: CGFloat = 0" in interactive_view
    assert "sentenceProgressRange: headerSentenceProgressRange(for: chunk)" in interactive_header
    assert "struct PlayerProgressFooterView: View" in progress_footer
    assert "case sentence" in progress_footer
    assert "case time" in progress_footer
    assert "#if os(tvOS)" in progress_footer
    assert "TVScrubber(" in progress_footer
    assert "Slider(value: $value" in progress_footer
    assert "var onTVFocusChanged: ((Bool) -> Void)? = nil" in progress_footer
    assert "onFocusChanged: onTVFocusChanged" in progress_footer
    assert 'return "interactiveReaderProgressFooter"' in progress_footer
    assert 'return "videoPlayerProgressFooter"' in progress_footer
    assert "interactiveProgressFooter(for: chunk)" in interactive_layout
    assert "compactPhoneProgressFooterButton(for: chunk)" in interactive_layout
    assert "interactiveReaderProgressFooterShow" in interactive_layout
    assert "interactiveReaderProgressFooterHide" in interactive_layout
    assert "shouldShowFullPhoneProgressFooter(for: chunk)" in interactive_layout
    assert ".focused($focusedArea, equals: .progress)" in interactive_layout
    assert "handleTVProgressFooterMoveCommand" in interactive_layout
    assert ".padding(.bottom, transcriptBottomPadding(for: chunk))" in interactive_content
    assert "if viewModel.isTranscriptLoading {\n                return transcriptSentences.isEmpty\n            }" in interactive_content
    assert "PlayerProgressFooterView(" in interactive_layout
    assert "style: .sentence" in interactive_layout
    assert "videoProgressFooter" not in video_layout
    assert "style: .time" not in video_layout
    assert "PlayerProgressFooterView.swift in Sources" in project
    assert project.count("PlayerProgressFooterView.swift in Sources") == 4
    assert "viewModel.jumpToSentence(targetSentence, autoPlay: audioCoordinator.isPlaybackRequested)" in interactive_header
    assert "audioCoordinator.isPlaying || viewModel.isSequenceTransitioning || viewModel.sequenceController.isDwelling" in interactive_header
    assert interactive_header.index("if audioCoordinator.isPlaying") < interactive_header.index("if let selectedSentenceID")
    assert "if isHeaderSentenceSliderEditing, let headerSentenceSliderValue" in interactive_header
    assert "isHeaderSentenceSliderEditing = true" in interactive_header
    assert "func clearHeaderSentenceProgressDraft()" in interactive_header
    assert "func showPhoneProgressFooter()" in interactive_header
    assert "func hidePhoneProgressFooter()" in interactive_header
    assert "func schedulePhoneProgressFooterAutoHide()" in interactive_header
    assert "phoneProgressFooterVisible = false" in interactive_header
    assert "case progress" in interactive_models
    assert "focusedArea = .progress" in interactive_view
    assert "func handleTVProgressFooterMoveCommand(_ direction: MoveCommandDirection)" in interactive_view
    assert "func handleTVProgressFooterFocusChanged(_ isFocused: Bool)" in interactive_view
    assert "onTVFocusChanged: handleTVProgressFooterFocusChanged" in interactive_layout
    assert "handleProgressMoveCommand(_ direction: MoveCommandDirection, chunk: InteractiveChunk) -> Bool" in interactive_view
    assert "handleTVProgressFooterHorizontalMove(-1, chunk: chunk)" in interactive_view
    assert "handleTVProgressFooterHorizontalMove(1, chunk: chunk)" in interactive_view
    assert "handleHeaderSentenceProgressEditingChanged(false)" in interactive_view
    assert "if headerSentenceProgressRange(for: chunk) != nil {\n            focusedArea = .progress" in interactive_view
    assert "prepareExplicitSentenceJump(to: targetSentence)" in interactive_header
    assert "struct InteractivePlayerHeaderHeightKey: PreferenceKey" in interactive_header
    assert "GeometryReader { proxy in" in interactive_header
    assert "headerOverlayMeasuredHeight = nextHeight" in interactive_header
    assert "if isTV { return .infinity }" in interactive_header
    assert ".frame(maxWidth: .infinity, alignment: .leading)" in interactive_header
    assert "headerSliderReservedHeight" in header_behavior
    assert "let bannerRowHeight = max(PlayerInfoMetrics.badgeHeight(isTV: true), PlayerInfoMetrics.coverHeight(isTV: true))" in header_behavior
    assert "let controlsAllowance: CGFloat = 34" in header_behavior
    assert "let outerClearance: CGFloat = 28" in header_behavior
    assert "let estimatedHeight = baseHeight + padding + controlsAllowance + headerSliderReservedHeight" in header_behavior
    assert "return max(estimatedHeight, measuredInfoHeaderReservedHeight)" in header_behavior
    assert "var measuredInfoHeaderReservedHeight: CGFloat" in header_behavior
    assert "#if os(iOS) || os(tvOS)" in header_behavior
    assert "let clearance = isTV ? 20" in header_behavior
    assert "func transcriptBottomPadding(for chunk: InteractiveChunk) -> CGFloat" in header_behavior
    assert "return shouldShowFullPhoneProgressFooter(for: chunk) ? 108 : 48" in header_behavior
    assert input_handlers.count("clearHeaderSentenceProgressDraft()") >= 4


def test_interactive_reader_token_taps_seek_and_lookup_by_gesture() -> None:
    token_word = _source(INTERACTIVE / "TextPlayerTokenWordView.swift")
    transcript = _source(INTERACTIVE / "InteractivePlayerView+Transcript.swift")
    transcript_view = _source(INTERACTIVE / "InteractiveTranscriptView.swift")
    transcript_gestures = _source(INTERACTIVE / "InteractiveTranscriptView+Gestures.swift")
    transcript_selection = _source(INTERACTIVE / "InteractiveTranscriptView+Selection.swift")
    token_geometry = _source(INTERACTIVE / "TextPlayerTokenGeometry.swift")
    sentence_view = _source(INTERACTIVE / "TextPlayerSentenceView.swift")
    variant_view = _source(INTERACTIVE / "TextPlayerVariantView.swift")
    sequence_controller = _source(
        ROOT / "ios" / "InteractiveReader" / "InteractiveReader" / "Services" / "SequencePlaybackController.swift"
    )
    playback = _source(INTERACTIVE / "InteractivePlayerViewModel+Playback.swift")

    assert "onTap?(false)\n                onLookup?()" in token_word
    assert ".onEnded { onTap?(true) }" in token_word
    assert "shouldPlay: Bool" in transcript
    assert "When paused, single tap selects the token and triggers a lookup" not in transcript
    assert "viewModel.seekSequencePlayback(" in transcript
    assert "viewModel.seekPlaybackWhenReady(to: resolvedSeekTime, in: chunk, autoPlay: shouldPlay)" in transcript
    assert "clearHeaderSentenceProgressDraft()" in transcript
    assert "func prepareExplicitSentenceJump(to sentenceNumber: Int)" in transcript
    assert "selectedSentenceID = sentenceNumber" in transcript
    assert "frozenTranscriptSentences = nil" in transcript
    assert "TextPlayerTimeline.buildInitialDisplay(" in transcript
    assert "let sequenceTimingTrack: TextPlayerTimingTrack = target.track == .original ? .original : .translation" in transcript
    assert "let sequenceAudioKind: InteractiveChunk.AudioOption.Kind = target.track == .original ? .original : .translation" in transcript
    assert "let sequenceSeekTime = tokenSeekTime(" in transcript
    assert "let targetTime = sequenceSeekTime ?? target.time" in transcript
    assert "sequenceSeekTime ?? resolvedSeekTime" not in transcript
    assert "let wasPaused = !audioCoordinator.isPlaying" in transcript_view
    assert "let effectiveShouldPlay = shouldPlay && !wasPaused" in transcript_view
    assert "onSeekToken(sentenceIndex, sentenceNumber, variantKind, tokenIndex, seekTime, effectiveShouldPlay)" in transcript_view
    assert "if wasPaused," in transcript_view
    assert "onLookupToken(sentenceIndex, variantKind, tokenIndex, token)" in transcript_view
    assert "private func tokenText(" in transcript_view
    assert "func seekSequencePlayback(" in playback
    assert "let sentenceNumber: Int?" in token_geometry
    assert "sentenceNumber: sentence.sentenceNumber" in sentence_view
    assert "sentenceNumber: sentenceNumber" in variant_view
    assert "func nearestTokenFrameForTap(" in transcript_selection
    assert "horizontalTolerance: CGFloat = 9" in transcript_selection
    assert "verticalTolerance: CGFloat = 8" in transcript_selection
    assert "func tokenTapDistance(from location: CGPoint, to frame: CGRect) -> CGFloat" in transcript_selection
    assert "func handleNearbyTokenTap(_ tokenFrame: TextPlayerTokenFrame, shouldPlay: Bool = true)" in transcript_selection
    assert "tokenFrame.sentenceNumber" in transcript_selection
    assert "if let tokenFrame = nearestTokenFrameForTap(at: location) {\n                    handleNearbyTokenTap(tokenFrame)" in transcript_gestures
    assert "tokenFrames.contains(where: { $0.frame.contains(location) })" not in transcript_gestures

    assert "let nextIndex = currentSegmentIndex + 1" in sequence_controller
    assert "let previousIndex = currentSegmentIndex - 1" in sequence_controller
    assert "preferredTrack ?? currentTrack" not in sequence_controller.split(
        "func nextSentenceTarget", 1
    )[1].split("func previousSentence", 1)[0]


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
    assert "onMoveRight: {" in tv_layout
    assert "focusTarget = .control(.headerSleepTimer)" in tv_layout
    assert "focusTarget = .control(.header)" in tv_layout


def test_playback_media_diagnostics_are_warning_only_by_default() -> None:
    diagnostics = _source(SHARED / "MediaDiagnosticsStripView.swift")
    job_playback = _source(PLAYBACK / "JobPlaybackView.swift")
    library_playback = _source(PLAYBACK / "LibraryPlaybackView.swift")

    assert "if let diagnostics, diagnostics.hasGaps" in diagnostics
    assert "Playback may skip sections until missing media is repaired." in diagnostics
    assert "LazyVGrid" not in diagnostics
    assert "MediaDiagnosticsMetricView" not in diagnostics
    assert 'MediaDiagnosticsItem(label: "Files"' not in diagnostics
    assert 'MediaDiagnosticsItem(label: "Chunks"' not in diagnostics
    assert "showsHealthyDiagnostics" not in diagnostics

    assert "MediaDiagnosticsStripView(" in job_playback
    assert "MediaDiagnosticsStripView(" in library_playback


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
