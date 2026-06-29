from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APPLE = ROOT / "ios" / "InteractiveReader" / "InteractiveReader"
PARITY_PLAN = ROOT / "docs" / "plans" / "cross-surface-parity-and-optimization.md"
FRONTEND_SYNC = ROOT / "docs" / "frontend-sync.md"
SHARED = APPLE / "Features" / "Shared"
INTERACTIVE = APPLE / "Features" / "InteractivePlayer"
PLAYBACK = APPLE / "Features" / "Playback"
SERVICES = APPLE / "Services"


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _app_changelog_source() -> str:
    return "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(SHARED.glob("AppChangelogData*.swift"))
    )


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


def test_interactive_ipad_paused_lookup_arrows_move_words_not_bubble_controls() -> None:
    interactive_view = _source(INTERACTIVE / "InteractivePlayerView.swift")
    input_handlers = _source(INTERACTIVE / "InteractivePlayerView+InputHandlers.swift")
    layout = _source(INTERACTIVE / "InteractivePlayerView+Layout.swift")
    transcript = _source(INTERACTIVE / "InteractivePlayerView+Transcript.swift")
    shortcut_support = _source(INTERACTIVE / "InteractivePlayerShortcutSupport.swift")
    shortcut_dispatch = _source(INTERACTIVE / "InteractivePlayerShortcutDispatch.swift")
    hardware_fallback = _source(INTERACTIVE / "InteractivePlayerShortcutHardwareFallback.swift")
    shortcut_focus = _source(INTERACTIVE / "InteractivePlayerShortcutFocus.swift")
    bubble_view = _source(SHARED / "LinguistBubbleView.swift")
    bubble_models = _source(SHARED / "LinguistBubbleModels.swift")
    bubble_wrapper = _source(INTERACTIVE / "InteractivePlayerLinguistBubbleView.swift")
    app_shortcuts = _source(APPLE / "App" / "GlobalKeyboardShortcuts.swift")
    app_entry = _source(APPLE / "App" / "InteractiveReaderApp.swift")
    app_delegate = _source(APPLE / "App" / "AppDelegate.swift")
    job_playback = _source(PLAYBACK / "JobPlaybackView.swift")
    job_resume = _source(PLAYBACK / "JobPlaybackView+Resume.swift")
    library_playback = _source(PLAYBACK / "LibraryPlaybackView.swift")
    library_resume = _source(PLAYBACK / "LibraryPlaybackView+Resume.swift")
    platform_adapter = _source(SHARED / "PlatformAdapter.swift")
    app_changelog = _app_changelog_source()
    pronunciation_speaker = _source(APPLE / "Utilities" / "PronunciationSpeaker.swift")
    parity_plan = _source(PARITY_PLAN)
    frontend_sync = _source(FRONTEND_SYNC)
    normalized_parity_plan = " ".join(parity_plan.split())
    normalized_frontend_sync = " ".join(frontend_sync.split())

    previous_body = input_handlers.split("func handleKeyboardPrevious()", 1)[1].split(
        "\n    func handleKeyboardNext()",
        1,
    )[0]
    play_pause_body = input_handlers.split("func handleKeyboardPlayPause()", 1)[1].split(
        "\n    func handlePlaybackToggleCommand()",
        1,
    )[0]
    playback_toggle_body = input_handlers.split("func handlePlaybackToggleCommand()", 1)[1].split(
        "\n    func handleKeyboardPrevious()",
        1,
    )[0]
    next_body = input_handlers.split("func handleKeyboardNext()", 1)[1].split(
        "\n    func handleKeyboardPreviousWord()",
        1,
    )[0]
    previous_sentence_body = input_handlers.split("func handleKeyboardPreviousSentence()", 1)[1].split(
        "\n    func handleKeyboardNextSentence()",
        1,
    )[0]
    next_sentence_body = input_handlers.split("func handleKeyboardNextSentence()", 1)[1].split(
        "\n    func handleKeyboardExtendSelectionBackward()",
        1,
    )[0]
    bubble_left_body = input_handlers.split("func handleKeyboardBubbleNavigateLeft()", 1)[1].split(
        "\n    func handleKeyboardBubbleNavigateRight()",
        1,
    )[0]
    bubble_right_body = input_handlers.split("func handleKeyboardBubbleNavigateRight()", 1)[1].split(
        "\n    func handleKeyboardBubbleWordNavigation",
        1,
    )[0]
    bubble_word_body = input_handlers.split("func handleKeyboardBubbleWordNavigation(_ delta: Int)", 1)[1].split(
        "\n    func logInteractiveKeyboardAction",
        1,
    )[0]
    keyboard_lookup_body = input_handlers.split("func handleUIKitKeyboardLookup()", 1)[1].split(
        "\n    func handleUIKitKeyboardShowMenu()",
        1,
    )[0]
    linguist = _source(INTERACTIVE / "InteractivePlayerView+Linguist.swift")
    current_selection_lookup_body = linguist.split("func handleLinguistLookupForCurrentSelection", 1)[1].split(
        "\n    // MARK: - Lookup Execution",
        1,
    )[0]
    dispatch_body = shortcut_dispatch.split("func dispatchShortcut(", 1)[1].split(
        "\n    func cancelPendingUIKitFallbacks()",
        1,
    )[0]
    keyboard_layer_body = input_handlers.split("var keyboardShortcutLayer: some View", 1)[1].split(
        "\n    @ViewBuilder\n    var trackpadSwipeLayer",
        1,
    )[0]
    request_focus_body = input_handlers.split("func requestKeyboardShortcutFocus()", 1)[1].split(
        "\n    @ViewBuilder\n    var shortcutHelpOverlay",
        1,
    )[0]
    broker_set_active_body = app_shortcuts.split("func setActive(_ active: Bool)", 1)[1].split(
        "\n    func resetDispatchDebounce()",
        1,
    )[0]
    broker_set_actions_body = app_shortcuts.split("func setActions(", 1)[1].split(
        "\n    func clearActions",
        1,
    )[0]
    job_autoplay_body = job_playback.split("private func handleAutoPlayIntentChange", 1)[1].split(
        "\n    private func handleAudioTimeChange",
        1,
    )[0]
    library_autoplay_body = library_playback.split("private func handleAutoPlayIntentChange", 1)[1].split(
        "\n    private func handleAudioTimeChange",
        1,
    )[0]

    assert "swiftUIKeyboardShortcutLayer" not in layout
    assert "var swiftUIKeyboardShortcutLayer" not in input_handlers
    assert "Button(\"Previous\", action: handleKeyboardPrevious)" not in input_handlers
    assert "Button(\"Next\", action: handleKeyboardNext)" not in input_handlers
    assert "KeyboardCommandHandler(" in keyboard_layer_body
    assert "if isPad" not in keyboard_layer_body
    assert "guard isPad else" not in request_focus_body
    assert "focusedArea = .transcript" in request_focus_body
    assert "return UIDevice.current.userInterfaceIdiom == .pad || UIDevice.current.userInterfaceIdiom == .phone" in platform_adapter
    assert "handlePlaybackToggleCommand()" in play_pause_body
    assert "audioCoordinator.togglePlayback()" not in play_pause_body
    assert "audioCoordinator.isPlaying || audioCoordinator.isPlaybackRequested" in playback_toggle_body
    assert "audioCoordinator.pause()" in playback_toggle_body
    assert "viewModel.prepareAudio(for: chunk, autoPlay: true)" in playback_toggle_body
    assert "audioCoordinator.play()" in playback_toggle_body
    assert "handleWordNavigation(-1, in: viewModel.selectedChunk)" in previous_body
    assert "handleWordNavigation(1, in: viewModel.selectedChunk)" in next_body
    assert "} else {\n            handleWordNavigation(-1, in: viewModel.selectedChunk)\n        }" in previous_body
    assert "} else {\n            handleWordNavigation(1, in: viewModel.selectedChunk)\n        }" in next_body
    assert "handleKeyboardBubbleNavigateLeft()" in previous_body
    assert "handleKeyboardBubbleNavigateRight()" in next_body
    assert previous_body.index("if linguistBubble != nil") < previous_body.index("audioCoordinator.isPlaying")
    assert next_body.index("if linguistBubble != nil") < next_body.index("audioCoordinator.isPlaying")
    assert "handleKeyboardBubbleNavigateLeft()" in previous_sentence_body
    assert "handleKeyboardBubbleNavigateRight()" in next_sentence_body
    assert previous_sentence_body.index("if linguistBubble != nil") < previous_sentence_body.index(
        "audioCoordinator.isPlaying"
    )
    assert next_sentence_body.index("if linguistBubble != nil") < next_sentence_body.index(
        "audioCoordinator.isPlaying"
    )
    assert "bubbleKeyboardNavigator.navigateLeft()" not in previous_body
    assert "bubbleKeyboardNavigator.navigateRight()" not in next_body
    assert "handleKeyboardBubbleWordNavigation(-1)" in bubble_left_body
    assert "handleKeyboardBubbleWordNavigation(1)" in bubble_right_body
    assert "guard let chunk = viewModel.selectedChunk else { return }" in bubble_word_body
    assert "handleWordNavigation(delta, in: chunk)" in bubble_word_body
    assert "scheduleAutoLinguistLookup(in: chunk)" not in bubble_word_body
    assert "handleBubbleKeyboardActivate()" in keyboard_lookup_body
    assert "guard !audioCoordinator.isPlaying else { return }" not in keyboard_lookup_body
    assert "handleLinguistLookupForCurrentSelection(in: chunk)" in keyboard_lookup_body
    assert "handleLinguistLookup(in: chunk)" not in keyboard_lookup_body
    assert "if linguistBubble != nil" in transcript
    assert "linguistVM.autoLookupTask?.cancel()" in transcript
    assert "handleLinguistLookupForCurrentSelection(in: chunk)" in transcript
    assert "scheduleAutoLinguistLookup(in: chunk)" in transcript
    assert "let selection = linguistSelection" in current_selection_lookup_body
    assert "selection.sentenceIndex == sentence.index" in current_selection_lookup_body
    assert "nearestLookupTokenIndex(" in current_selection_lookup_body
    assert "startLinguistLookup(query: query, variantKind: selection.variantKind)" in current_selection_lookup_body
    assert "bubbleKeyboardNavigator.navigateLeft()" not in bubble_left_body
    assert "bubbleKeyboardNavigator.navigateRight()" not in bubble_right_body
    assert "shouldNavigateBubbleWords: {" in input_handlers
    should_navigate_body = input_handlers.split("shouldNavigateBubbleWords: {", 1)[1].split(
        "},",
        1,
    )[0]
    assert "linguistBubble != nil" in should_navigate_body
    assert "audioCoordinator.isPlaying" not in should_navigate_body
    assert "var shouldNavigateBubbleWords: (() -> Bool)?" in shortcut_support
    assert "dispatchPreviousArrowShortcut(source: \"ui\")" in shortcut_support
    assert "dispatchNextArrowShortcut(source: \"ui\")" in shortcut_support
    assert "dispatchPreviousArrowShortcut(source: \"press\")" in shortcut_support
    assert "dispatchNextArrowShortcut(source: \"press\")" in shortcut_support
    assert (
        ".onPlayPauseCommand {\n"
        "                guard playbackToggleOverride == nil else { return }\n"
        "                handlePlaybackToggleCommand()"
    ) in interactive_view
    assert "dispatchShortcut(.playPause, source: \"ui\")" in shortcut_support
    assert "dispatchShortcut(.playPause, source: \"press\")" in shortcut_support
    assert "dispatchShortcut(.playPause, source: \"input\")" in shortcut_support
    assert "case bubbleNavigateLeft" in shortcut_dispatch
    assert "case bubbleNavigateRight" in shortcut_dispatch
    assert "shouldRoutePlainArrowToBubbleWords" in shortcut_dispatch
    assert "dispatchShortcut(.bubbleNavigateLeft" in shortcut_dispatch
    assert "dispatchShortcut(.bubbleNavigateRight" in shortcut_dispatch
    assert "var shouldNavigateBubbleWords: () -> Bool = { false }" in app_shortcuts
    assert "var bubbleNavigateLeft: (() -> Void)?" in app_shortcuts
    assert "var bubbleNavigateRight: (() -> Void)?" in app_shortcuts
    assert "actions.shouldNavigateBubbleWords()" in app_shortcuts
    assert "bubbleNavigateLeft()" in app_shortcuts
    assert "bubbleNavigateRight()" in app_shortcuts
    assert "shouldNavigateBubbleWords: { [weak self] in" in hardware_fallback
    assert "self?.shouldRoutePlainArrowToBubbleWords == true" in hardware_fallback
    assert "bubbleNavigateLeft: { [weak self] in" in hardware_fallback
    assert "bubbleNavigateRight: { [weak self] in" in hardware_fallback
    assert "dispatchPreviousArrowShortcut(source: \"broker\")" in hardware_fallback
    assert "dispatchNextArrowShortcut(source: \"broker\")" in hardware_fallback
    assert "dispatchPreviousArrowShortcut(source: \"gc\")" in hardware_fallback
    assert "dispatchNextArrowShortcut(source: \"gc\")" in hardware_fallback
    assert "var lastPhysicalArrowDispatch: (direction: Int, timestamp: TimeInterval)?" in shortcut_support
    assert "var physicalArrowDirection: Int?" in shortcut_dispatch
    assert "case .previous, .previousSentence, .extendSelectionBackward, .bubbleNavigateLeft:" in shortcut_dispatch
    assert "case .next, .nextSentence, .extendSelectionForward, .bubbleNavigateRight:" in shortcut_dispatch
    assert "func shouldSuppressPhysicalArrowDuplicate(" in shortcut_dispatch
    assert "now - lastPhysicalArrowDispatch.timestamp < 0.16" in shortcut_dispatch
    assert "source != \"gc\", source != \"broker\", hardwareKeyboardInput != nil" in shortcut_dispatch
    assert "scheduleUIKitFallback(shortcut, action: action)\n            return" not in dispatch_body
    assert "scheduleUIKitFallback(shortcut, action: action)\n        }\n        guard !shouldSuppressPhysicalArrowDuplicate" in dispatch_body
    assert shortcut_dispatch.index(
        "source != \"gc\", source != \"broker\", hardwareKeyboardInput != nil"
    ) < shortcut_dispatch.index(
        "shouldSuppressPhysicalArrowDuplicate(shortcut, source: source)"
    )
    assert "private var iOSBubbleKeyboardShortcutLayer: some View" not in bubble_view
    assert 'Button("Previous Lookup Word")' not in bubble_view
    assert 'Button("Next Lookup Word")' not in bubble_view
    assert ".keyboardShortcut(.leftArrow, modifiers: [])" not in bubble_view
    assert ".keyboardShortcut(.rightArrow, modifiers: [])" not in bubble_view
    assert "keyboardNavigator.navigateLeft()" not in bubble_view
    assert "keyboardNavigator.navigateRight()" not in bubble_view
    assert "iOSBubbleHardwareKeyBridge(actions: actions)" in bubble_view
    assert "final class CaptureView: UIView, UIKeyInput" in bubble_view
    assert "func insertText(_ text: String)" in bubble_view
    assert "override func pressesBegan(_ presses: Set<UIPress>, with event: UIPressesEvent?)" in bubble_view
    assert "UIKeyCommand.inputLeftArrow" in bubble_view
    assert "UIKeyCommand.inputRightArrow" in bubble_view
    assert "Bubble bridge \\(source) routed" in bubble_view
    assert "PlayerKeyboardShortcutBroker.shared.handleCommandIfActive(command)" in bubble_view
    assert "fallback?()" in bubble_view
    assert "var onKeyboardPlayPause: (() -> Void)? = nil" in bubble_models
    assert "var onKeyboardPreviousToken: (() -> Void)? = nil" in bubble_models
    assert "var onKeyboardNextToken: (() -> Void)? = nil" in bubble_models
    assert "var onKeyboardLookup: (() -> Void)? = nil" in bubble_models
    assert "actions.onKeyboardPlayPause = onKeyboardPlayPause" in bubble_wrapper
    assert "actions.onKeyboardPreviousToken = onPreviousToken" in bubble_wrapper
    assert "actions.onKeyboardNextToken = onNextToken" in bubble_wrapper
    assert "actions.onKeyboardLookup = onKeyboardLookup" in bubble_wrapper
    assert "onKeyboardPlayPause: onTogglePlayback" in _source(INTERACTIVE / "InteractiveTranscriptView+iPadSplit.swift")
    assert "onKeyboardLookup: onLookup" in _source(INTERACTIVE / "InteractiveTranscriptView+iPadSplit.swift")
    assert "func handleCommandIfActive(_ name: Notification.Name) -> Bool" in app_shortcuts
    assert "func handleCommand(_ name: Notification.Name)" in app_shortcuts
    assert "post(name)" in app_shortcuts
    assert "if !isActive {\n            setActive(true)\n        }" in broker_set_actions_body
    assert "resetDispatchDebounce()" not in broker_set_active_body.split(
        "guard isActive != active else",
        1,
    )[1].split("return", 1)[0]
    assert "func resetModifierState()" in app_shortcuts
    assert "refreshModifierStateFromKeyboardInput()" in app_shortcuts
    assert "leftControlDown = keyboardInput.button(forKeyCode: .leftControl)?.isPressed == true" in app_shortcuts
    assert "rightControlDown = keyboardInput.button(forKeyCode: .rightControl)?.isPressed == true" in app_shortcuts
    assert app_shortcuts.index("refreshModifierStateFromKeyboardInput()") < app_shortcuts.index(
        "case .spacebar:"
    )
    assert "case .ended, .cancelled:" in app_shortcuts
    assert "_ = updateModifier(key.keyCode, pressed: false)" in app_shortcuts
    assert "private func updateModifier(_ keyCode: UIKeyboardHIDUsage, pressed: Bool) -> Bool" in app_shortcuts
    assert "private func syncModifierState(from flags: UIKeyModifierFlags)" in app_shortcuts
    assert "syncModifierState(from: key.modifierFlags)" in app_shortcuts
    assert "private func resolvedControlModifierState(for key: UIKey) -> Bool" in app_shortcuts
    assert "if keyboardInput != nil" in app_shortcuts
    assert "return controlDown" in app_shortcuts
    assert "let controlDown = resolvedControlModifierState(for: key)" in app_shortcuts
    assert "let controlDown = key.modifierFlags.contains(.control)" not in app_shortcuts
    assert "case .keyboardSpacebar:" in app_shortcuts
    assert "case .spacebar, .leftArrow, .rightArrow, .returnOrEnter," in app_shortcuts
    assert "case .keyboardSpacebar, .keyboardLeftArrow, .keyboardRightArrow," in app_shortcuts
    assert "post(.keyboardShortcutPlayPause)" in app_shortcuts
    assert "#if os(iOS) || os(tvOS)" in app_shortcuts
    assert "handleRemotePress(press)" in app_shortcuts
    assert "private func handleRemotePress(_ press: UIPress)" in app_shortcuts
    assert "case .playPause:" in app_shortcuts
    assert 'keyboardShortcutDebugLog("[KeyboardShortcut] App event remote playPause")' in app_shortcuts
    assert "case .keyboardShortcutPlayPause:\n            actions.playPause()" in app_shortcuts
    assert (
        "playPause: { [weak self] in\n"
        "                self?.dispatchShortcut(.playPause, source: \"broker\")"
    ) in hardware_fallback
    assert "PlayerKeyboardShortcutBroker.shared.handleCommand(.keyboardShortcutPrevious)" in app_entry
    assert "PlayerKeyboardShortcutBroker.shared.handleCommand(.keyboardShortcutNext)" in app_entry
    assert "PlayerKeyboardShortcutBroker.shared.handleCommand(.keyboardShortcutPlayPause)" in app_entry
    assert "override var keyCommands: [UIKeyCommand]?" in app_delegate
    assert "appPlayerCommand(input: \" \", action: #selector(handlePlayerPlayPauseCommand))" in app_delegate
    assert "appPlayerCommand(input: UIKeyCommand.inputLeftArrow, action: #selector(handlePlayerPreviousCommand))" in app_delegate
    assert "appPlayerCommand(input: UIKeyCommand.inputRightArrow, action: #selector(handlePlayerNextCommand))" in app_delegate
    assert "PlayerKeyboardShortcutBroker.shared.handleCommand(.keyboardShortcutPlayPause)" in app_delegate
    assert "PlayerKeyboardShortcutBroker.shared.handleCommand(.keyboardShortcutPrevious)" in app_delegate
    assert "PlayerKeyboardShortcutBroker.shared.handleCommand(.keyboardShortcutNext)" in app_delegate
    assert ".keyboardShortcut(.space, modifiers: [])" in app_entry
    assert "UIApplication.installInteractiveReaderKeyboardEventInterceptor()" in app_entry
    assert "#if os(iOS) || os(tvOS)" in app_entry
    assert "NotificationCenter.default.post(name: .keyboardShortcutPrevious" not in app_entry
    assert "NotificationCenter.default.post(name: .keyboardShortcutNext" not in app_entry
    assert "@MainActor var onPlaybackStarted: (() -> Void)?" in pronunciation_speaker
    assert "@MainActor var onPlaybackFinished: (() -> Void)?" in pronunciation_speaker
    assert "onPlaybackStarted?()" in pronunciation_speaker
    assert "onPlaybackFinished?()" in pronunciation_speaker
    assert "audioPlayerDecodeErrorDidOccur" in pronunciation_speaker
    assert "speechSynthesizer(_ synthesizer: AVSpeechSynthesizer, didFinish" in pronunciation_speaker
    assert "speechSynthesizer(_ synthesizer: AVSpeechSynthesizer, didCancel" in pronunciation_speaker
    assert "linguistVM.pronunciationSpeaker.onPlaybackStarted = {" in linguist
    assert "linguistVM.pronunciationSpeaker.onPlaybackFinished = {" in linguist
    assert "requestKeyboardShortcutFocus()" in linguist
    assert "refreshHardwareModifierState()" in hardware_fallback
    assert "PlayerKeyboardShortcutBroker.shared.setActions(actions, owner: self)" in hardware_fallback
    assert "PlayerKeyboardShortcutBroker.shared.setActive(true)" in hardware_fallback
    assert "gcLeftControlDown = hardwareKeyboardInput.button(forKeyCode: .leftControl)?.isPressed == true" in hardware_fallback
    assert "gcRightControlDown = hardwareKeyboardInput.button(forKeyCode: .rightControl)?.isPressed == true" in hardware_fallback
    assert hardware_fallback.index("refreshHardwareModifierState()") < hardware_fallback.index(
        "let controlDown = gcControlDown"
    )
    force_reclaim_body = shortcut_focus.split("func forceReclaimFirstResponderNow()", 1)[1].split(
        "\n    func performFirstResponderReclaim",
        1,
    )[0]
    assert force_reclaim_body.count("refreshShortcutFocusState()") >= 3
    assert force_reclaim_body.count("refreshHardwareKeyboardFallback()") >= 3
    assert "lastShortcutDispatch = nil" not in shortcut_focus
    reset_body = shortcut_focus.split("func refreshShortcutFocusState()", 1)[1].split(
        "\n    func performFirstResponderReclaim",
        1,
    )[0]
    assert "lastPhysicalArrowDispatch = nil" not in reset_body
    assert "lastShortcutDispatch = nil" not in reset_body
    assert "cancelPendingUIKitFallbacks()" in shortcut_focus
    assert "PlayerKeyboardShortcutBroker.shared.resetDispatchDebounce()" not in shortcut_focus
    assert "PlayerKeyboardShortcutBroker.shared.resetModifierState()" in shortcut_focus
    assert ".onChange(of: autoPlayOnLoad) { _, newValue in handleAutoPlayIntentChange(newValue) }" in job_playback
    assert ".onChange(of: autoPlayOnLoad) { _, newValue in handleAutoPlayIntentChange(newValue) }" in library_playback
    assert "guard shouldAutoPlay, viewModel.loadState == .loaded else { return }" in job_autoplay_body
    assert "guard shouldAutoPlay, viewModel.loadState == .loaded else { return }" in library_autoplay_body
    assert "autoPlayOnLoad = false" in job_autoplay_body
    assert "autoPlayOnLoad = false" in library_autoplay_body
    assert "applyPlaybackStartIntent()" in job_autoplay_body
    assert "applyPlaybackStartIntent()" in library_autoplay_body
    for resume_source in (job_resume, library_resume):
        assert "startInteractivePlayback(at: firstInteractiveSentenceNumber())" in resume_source
        assert "func firstInteractiveSentenceNumber() -> Int?" in resume_source
        assert "SentencePositionProvider.sentenceNumber(for: sentence)" in resume_source
        assert "if let start = chunk.startSentence, start > 0" in resume_source
        assert "startInteractivePlayback(at: 1)" not in resume_source
    assert force_reclaim_body.index("refreshHardwareKeyboardFallback()") < force_reclaim_body.index(
        "performFirstResponderReclaim(ignoringSoftwareKeyboard: true)"
    )
    assert "single `PlayerKeyboardShortcutBroker` path" in normalized_parity_plan
    assert "duplicate hidden SwiftUI arrow shortcut layers stay removed" in normalized_parity_plan
    assert "Lookup Read Aloud also reclaims or reactivates that shared" in normalized_parity_plan
    assert "starts, finishes, or cancels" in normalized_parity_plan
    assert "single `PlayerKeyboardShortcutBroker` path" in normalized_frontend_sync
    assert "lookup read-aloud starts, finishes, or cancels" in normalized_frontend_sync
    assert "starts, finishes, or cancels" in app_changelog
    assert "Space play/pause, Enter lookup, and Left/Right word movement keep working" in app_changelog
    assert "swiftUIKeyboardShortcutLayer" not in frontend_sync
    assert 'logInteractiveKeyboardAction("previous")' in previous_body
    assert 'logInteractiveKeyboardAction("next")' in next_body
    assert "Interactive wordNav requested" in transcript
    assert "Interactive wordNav selected" in transcript
    assert "@discardableResult\n    func handleWordNavigation(_ delta: Int, in chunk: InteractiveChunk) -> Bool" in transcript
    assert "wrappedLookupTokenIndex(" in transcript
    assert "guard linguistSelection == nil else { return }" in transcript
    assert "selectedSentenceID = SentencePositionProvider.sentenceNumber(in: chunk, at: sentence.index)" in transcript
    assert "while tokens.indices.contains(candidate)" in transcript
    assert "candidate = direction >= 0 ? 0 : tokens.count - 1" in transcript
    assert "viewModel.playForReaderTransport()" in playback_toggle_body
    assert "return true" in transcript


def test_apple_playback_translation_language_does_not_fall_back_to_book_language() -> None:
    job_metadata = _source(PLAYBACK / "JobPlaybackView+Metadata.swift")
    library_metadata = _source(PLAYBACK / "LibraryPlaybackMetadata.swift")
    job_row = _source(APPLE / "Features" / "Jobs" / "JobRowView+Presentation.swift")
    library_row = _source(APPLE / "Features" / "Library" / "LibraryRowView+Metadata.swift")

    for source, marker in [
        (job_metadata, "var linguistLookupLanguage: String"),
        (library_metadata, "var linguistLookupLanguage: String"),
        (job_row, "private var translationLanguage: String?"),
        (library_row, "var translationLanguage: String?"),
    ]:
        body = source.split(marker, 1)[1].split("\n    }", 1)[0]
        assert '"book_language"' not in body
        if "preferredTargetLanguage" in body:
            assert "PlaybackMetadataHelpers.preferredTargetLanguage" in body
        else:
            assert '"target_language"' in body
            assert '"translation_language"' in body
            assert '"target_languages"' in body
            assert "PlaybackMetadataHelpers.distinctTranslationFallback" in body

    playback_helpers = _source(PLAYBACK / "Shared" / "PlaybackMetadataHelpers.swift")
    target_language_body = playback_helpers.split("static func preferredTargetLanguage", 1)[1].split(
        "\n    static func metadataStringArray",
        1,
    )[0]
    assert '"target_languages"' in target_language_body
    assert '"targetLanguages"' in target_language_body
    assert '"target_language"' in target_language_body
    assert '"translation_language"' in target_language_body
    assert target_language_body.index('"target_languages"') < target_language_body.index('"target_language"')
    assert '["media_metadata"]' in target_language_body
    assert '["book_metadata"]' in target_language_body
    assert "static func distinctTranslationFallback" in playback_helpers
    assert "AppleLanguageCatalog.languageCode(for: fallback)" in playback_helpers
    assert "maxDepth: 0" in target_language_body


def test_interactive_audio_roles_follow_single_track_mode() -> None:
    audio_management = _source(INTERACTIVE / "InteractivePlayerView+AudioManagement.swift")
    selection = _source(INTERACTIVE / "InteractivePlayerViewModel+Selection.swift")
    selected_kind_body = audio_management.split(
        "func selectedAudioKind(for chunk: InteractiveChunk) -> InteractiveChunk.AudioOption.Kind?",
        1,
    )[1].split("\n    func availableAudioRoles", 1)[0]
    active_roles_body = audio_management.split(
        "func activeAudioRoles(\n        for chunk: InteractiveChunk,",
        1,
    )[1].split("\n    func toggleHeaderAudioRole", 1)[0]

    assert "if option.kind == .combined" in selected_kind_body
    assert "case .singleTrack(.original):" in selected_kind_body
    assert "return .original" in selected_kind_body
    assert "case .singleTrack(.translation):" in selected_kind_body
    assert "return .translation" in selected_kind_body
    assert "case .sequence:" in selected_kind_body
    assert "return .combined" in selected_kind_body
    assert "switch audioModeManager.currentMode" in active_roles_body
    assert "case .singleTrack(.translation):" in active_roles_body
    assert "return [.translation]" in active_roles_body

    playback = _source(INTERACTIVE / "InteractivePlayerViewModel+Playback.swift")
    combined_phase_body = playback.split(
        "func useCombinedPhases(for chunk: InteractiveChunk) -> Bool",
        1,
    )[1].split("\n    func usesCombinedQueue", 1)[0]
    assert "track.kind == .combined, track.streamURLs.count == 1" in combined_phase_body
    assert "audioCoordinator.activeURL" in combined_phase_body
    assert "activeURL == track.primaryURL" in combined_phase_body
    skip_body = playback.split("func skipSentence(\n", 1)[1].split(
        "\n    /// Skip to the next/previous sequence segment.",
        1,
    )[0]
    assert "anchorSentenceNumber: Int? = nil" in skip_body
    assert "let anchoredIndex = anchorSentenceNumber.flatMap" in skip_body
    assert "SentencePositionProvider.sentenceIndex(in: chunk, matching: $0)" in skip_body
    assert "let resolvedActiveIndex = anchoredIndex ?? activeSentenceIndex(" in skip_body
    assert "activeSentenceIndex(" in skip_body
    assert "let targetIndex = activeIndex + 1" in skip_body
    assert "let targetIndex = activeIndex - 1" in skip_body
    assert "activeStart.map" not in skip_body
    assert "sorted.first(where: { $0.1 > currentTime + epsilon })" not in skip_body
    assert "sorted.last(where: { $0.1 < anchorTime })" not in skip_body
    active_index_body = playback.split("private func activeSentenceIndex(", 1)[1].split(
        "\n    private func nearestSentenceIndex",
        1,
    )[0]
    assert "TextPlayerTimeline.resolveActiveIndex(\n            sentences: chunk.sentences" in active_index_body
    assert "activeTimingTrack: activeTimingTrack" in active_index_body
    assert "useCombinedPhases: useCombinedPhases" in active_index_body
    assert active_index_body.index("sentences: chunk.sentences") < active_index_body.index(
        "timelineSentences: timelineSentences"
    )
    same_url_body = selection.split("private func handleSameURLPlayback", 1)[1].split(
        "\n    /// Load a single track",
        1,
    )[0]
    assert "sequenceController.isEnabled || !sequenceController.plan.isEmpty" in same_url_body
    assert "sequenceController.reset()" in same_url_body


def test_interactive_sentence_skip_preserves_slider_anchor_through_fallbacks() -> None:
    transcript = _source(INTERACTIVE / "InteractivePlayerView+Transcript.swift")
    selection = _source(INTERACTIVE / "InteractivePlayerViewModel+Selection.swift")
    handle_skip_body = transcript.split(
        "func handleSentenceSkip(_ delta: Int, in chunk: InteractiveChunk)",
        1,
    )[1].split("\n    func stableSentenceIndexForNavigation", 1)[0]

    assert "let explicitAnchorSentenceID = pendingExplicitSentenceJumpID.flatMap" in handle_skip_body
    assert handle_skip_body.count("anchorSentenceNumber: explicitAnchorSentenceID") >= 4
    assert "viewModel.skipSentence(forward: delta > 0, preferredTrack: preferredSequenceTrack)" not in handle_skip_body
    assert "Date().timeIntervalSince(started) > 12.0" in transcript
    assert "private let recentSingleTrackSentenceAnchorLifetime: TimeInterval = 12.0" in selection
    jump_body = selection.split(
        "func jumpToSentence(_ sentenceNumber: Int, autoPlay: Bool = false)",
        1,
    )[1].split("\n    func resolveChunk", 1)[0]
    assert "if audioModeManager?.isSequenceMode == false" in jump_body
    assert "rememberSingleTrackSentenceAnchor(\n                chunkID: targetChunk.id,\n                sentenceNumber: sentenceNumber" in jump_body


def test_interactive_sentence_slider_locks_rendering_to_explicit_jump() -> None:
    interactive_view = _source(INTERACTIVE / "InteractivePlayerView.swift")
    transcript = _source(INTERACTIVE / "InteractivePlayerView+Transcript.swift")
    header = _source(INTERACTIVE / "InteractivePlayerView+HeaderOverlay.swift")
    lifecycle = _source(INTERACTIVE / "InteractivePlayerView+LifecycleObservers.swift")

    assert "@State var pendingExplicitSentenceJumpID: Int?" in interactive_view
    assert "@State var pendingExplicitSentenceJumpStartedAt: Date?" in interactive_view

    prepare_body = transcript.split("func prepareExplicitSentenceJump(to sentenceNumber: Int)", 1)[1].split(
        "\n    func sentenceBinding",
        1,
    )[0]
    assert "pendingExplicitSentenceJumpID = sentenceNumber" in prepare_body
    assert "pendingExplicitSentenceJumpStartedAt = Date()" in prepare_body

    slider_commit_body = header.split(
        "func handleHeaderSentenceProgressEditingChanged(_ isEditing: Bool)",
        1,
    )[1].split("\n    func clearHeaderSentenceProgressDraft", 1)[0]
    assert "let targetChunk = viewModel.jobContext.flatMap" in slider_commit_body
    assert "viewModel.resolveChunk(containing: targetSentence, in: $0)" in slider_commit_body
    assert "rememberSingleTrackSentenceAnchor(chunkID: targetChunk.id, sentenceNumber: targetSentence)" in slider_commit_body

    sync_body = transcript.split("func syncSelectedSentence(for chunk: InteractiveChunk)", 1)[1].split(
        "\n    func handleSentenceSkip",
        1,
    )[0]
    assert "if let pending = pendingExplicitSentenceJumpID" in sync_body
    assert "if id == pending || pendingExplicitSentenceJumpIsExpired" in sync_body
    assert "selectedSentenceID = pending" in sync_body
    assert "return" in sync_body

    transcript_body = transcript.split("func transcriptSentences(for chunk: InteractiveChunk)", 1)[1].split(
        "\n\n    func activeSentenceDisplay",
        1,
    )[0]
    assert "pendingExplicitSentenceJumpDisplay(" in transcript_body
    assert "return [pendingDisplay]" in transcript_body
    assert "TextPlayerTimeline.buildInitialDisplay(" in transcript_body
    assert "Date().timeIntervalSince(started) > 12.0" in transcript_body
    pending_display_body = transcript.split("private func pendingExplicitSentenceJumpDisplay(", 1)[1].split(
        "\n\n    func activeSentenceDisplay",
        1,
    )[0]
    assert "viewModel.activeSentence(at: viewModel.highlightingTime)" in pending_display_body
    assert "SentencePositionProvider.sentenceNumber(in: chunk, at: activeIndex) == pending" in pending_display_body
    assert "return nil" in pending_display_body

    highlighting_change_body = lifecycle.split("private func handleHighlightingTimeChange()", 1)[1].split(
        "\n    private func handleReadingBedEnabledChange",
        1,
    )[0]
    assert "if audioCoordinator.isPlaying" in highlighting_change_body
    assert "syncSelectedSentence(for: chunk)" in highlighting_change_body
    assert "viewModel.prefetchAdjacentSentencesIfNeeded(isPlaying: true)" in highlighting_change_body

    skip_body = transcript.split("func handleSentenceSkip(_ delta: Int, in chunk: InteractiveChunk)", 1)[1].split(
        "\n    func stableSentenceIndexForNavigation",
        1,
    )[0]
    assert "jumpByOneSentenceFromExplicitAnchor(" in skip_body
    assert "viewModel.jumpToSentence(targetNumber, autoPlay: audioCoordinator.isPlaybackRequested)" in skip_body

    playback = _source(INTERACTIVE / "InteractivePlayerViewModel+Playback.swift")
    empty_chunk_body = playback.split("guard !chunk.sentences.isEmpty else", 1)[1].split(
        "\n        let anchoredIndex",
        1,
    )[0]
    assert "adjacentSentenceNumber(" in empty_chunk_body
    assert "jumpToSentence(targetSentence, autoPlay: audioCoordinator.isPlaybackRequested)" in empty_chunk_body

    header_current_body = header.split("private func currentHeaderSentenceNumber(for chunk: InteractiveChunk)", 1)[1].split(
        "\n    private func clampedHeaderSentenceProgressValue",
        1,
    )[0]
    assert "pendingExplicitSentenceJumpID" in header_current_body
    assert "!pendingExplicitSentenceJumpIsExpired" in header_current_body
    assert "viewModel.isSequenceModeActive" in header_current_body
    assert header_current_body.index("viewModel.isSequenceModeActive") < header_current_body.index(
        "chunk.sentences.indices.contains(currentIndex)"
    )
    clear_body = header.split("func clearHeaderSentenceProgressDraft()", 1)[1].split(
        "\n    func shouldShowFullPhoneProgressFooter",
        1,
    )[0]
    assert "pendingExplicitSentenceJumpID = nil" in clear_body
    assert "pendingExplicitSentenceJumpStartedAt = nil" in clear_body


def test_interactive_reader_surfaces_timing_provenance_pill() -> None:
    models = _source(INTERACTIVE / "InteractivePlayerModels.swift")
    context_builder = _source(INTERACTIVE / "InteractivePlayerContextBuilder.swift")
    audio_management = _source(INTERACTIVE / "InteractivePlayerView+AudioManagement.swift")
    header = _source(INTERACTIVE / "InteractivePlayerView+HeaderOverlay.swift")

    assert "let hasJobTiming: Bool" in models
    assert "hasJobTiming: Bool = false" in models
    assert "hasJobTiming: timing != nil" in context_builder

    label_body = audio_management.split("func timingProvenanceLabel(for chunk: InteractiveChunk) -> String?", 1)[1].split(
        "\n    func audioTimelineMetrics",
        1,
    )[0]
    assert "context.hasJobTiming" in label_body
    assert 'return context.hasEstimatedSegments ? "Timing: Job est." : "Timing: Job"' in label_body
    assert "chunkHasWordTiming(chunk)" in label_body
    assert 'return "Timing: Chunk v\\(version)"' in label_body
    assert 'return "Timing: Chunk"' in label_body
    assert "chunkHasSentenceGates(chunk)" in label_body
    assert 'return "Timing: Gates"' in label_body
    assert "private func chunkHasWordTiming(_ chunk: InteractiveChunk) -> Bool" in audio_management
    assert "!sentence.timingTokens.isEmpty || !sentence.originalTimingTokens.isEmpty" in audio_management
    assert "private func chunkHasSentenceGates(_ chunk: InteractiveChunk) -> Bool" in audio_management
    assert "sentence.originalStartGate != nil" in audio_management

    assert "let timingLabel = timingProvenanceLabel(for: chunk)" in header
    assert "timingLabel: timingLabel" in header
    assert "let timingLabel: String?" in header
    assert "if slideLabel != nil || timelineLabel != nil || timingLabel != nil" in header
    assert "func timingProvenanceView(label: String) -> some View" in header
    assert '.accessibilityIdentifier("interactiveReaderTimingProvenancePill")' in header
    assert "headerProgressPill(label: timingLabel, isProminent: false)" in header
    assert "Button" not in header.split("func timingProvenanceView(label: String) -> some View", 1)[1].split(
        "\n    func headerSentenceProgressRange",
        1,
    )[0]


def test_apple_music_reading_bed_uses_narration_mix_semantics() -> None:
    reading_bed = _source(INTERACTIVE / "InteractivePlayerView+ReadingBed.swift")
    music = _source(SERVICES / "MusicKitCoordinator.swift")
    audio = _source(SERVICES / "AudioPlayerCoordinator.swift")
    frontend_sync = (ROOT / "docs" / "frontend-sync.md").read_text(encoding="utf-8")

    apple_music_body = reading_bed.split("private func handleAppleMusicPlaybackChange", 1)[1].split(
        "\n    // MARK: - Built-in Reading Bed Playback Control",
        1,
    )[0]
    assert "musicCoordinator.prepareForNarrationMix()" in apple_music_body
    assert "musicCoordinator.resume(userInitiated: false)" in apple_music_body
    assert "musicCoordinator.pause(userInitiated: false)" in apple_music_body
    assert "musicCoordinator.isPausedByReaderTransport || musicCoordinator.isReaderTransportPauseGuardActive" in apple_music_body
    assert "musicCoordinator.pauseReadingBedForReaderTransport()" in apple_music_body
    assert "readingBedPauseTask = Task" in apple_music_body
    assert "audioCoordinator.isPlaybackRequested" in apple_music_body
    assert "Unlike built-in reading bed, Apple Music continues as ambient background" not in apple_music_body

    mix_body = reading_bed.split("func applyMixVolume(_ mix: Double)", 1)[1].split(
        "\n    /// Handle reading bed enable/disable toggle",
        1,
    )[0]
    assert "let narrationVolume = 1.0 - (mix * 0.7)" in mix_body
    assert "audioCoordinator.setTargetVolume(narrationVolume)" in mix_body
    assert "if !useAppleMusicForBed" in mix_body
    assert "readingBedCoordinator.setVolume(bedVolume)" in mix_body
    assert "configureAppleMusicAudioSession(for: mix)" in mix_body
    assert "low mixes request system ducking" in mix_body

    assert "func prepareForNarrationMix()" in music
    assert "shouldIgnoreNextNonPlayingStatus = true" in music
    assert "hasAutoResumeIntent = true" in music
    assert "hasQueuedMusicForAutoResume" in music
    prepare_body = music.split("func prepareForNarrationMix()", 1)[1].split("\n    func skipToNext()", 1)[0]
    assert "guard ownershipState == .appleMusic else { return }" not in prepare_body
    assert "shouldIgnoreNextNonPlayingStatus = true" not in prepare_body
    assert ".duckOthers" in audio
    assert "return duckOthers ? [.mixWithOthers, .duckOthers] : [.mixWithOthers]" in audio
    assert "var mode: AVAudioSession.Mode" in audio
    assert "mixing ? .default : .spokenAudio" in audio
    assert "Apple Music is an optional background bed, not narration audio" in frontend_sync
    assert "low mix values request `.duckOthers`" in frontend_sync


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
    interactive_transcript = _source(INTERACTIVE / "InteractivePlayerView+Transcript.swift")
    video_overlay = _source(PLAYBACK / "VideoPlayerOverlayView.swift")
    video_header = _source(PLAYBACK / "VideoPlayerHeaderView.swift")
    video_layout = _source(PLAYBACK / "VideoPlayerView+Layout.swift")
    tv_layout = _source(PLAYBACK / "VideoPlayerOverlayView+TVLayout.swift")
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
    tv_video_controls = _source(PLAYBACK / "TVVideoPlayerControls.swift")
    video_overlay_config = _source(PLAYBACK / "VideoPlayerOverlayConfiguration.swift")
    video_overlay_focus = _source(PLAYBACK / "VideoPlayerOverlayTVFocus.swift")
    project = _source(ROOT / "ios" / "InteractiveReader" / "InteractiveReader.xcodeproj" / "project.pbxproj")

    assert "@State var headerSentenceSliderValue: Double?" in interactive_view
    assert "@State var isHeaderSentenceSliderEditing = false" in interactive_view
    assert '@AppStorage("interactive.phoneProgressFooterVisible") var phoneProgressFooterVisible = false' in interactive_view
    assert "@State var phoneProgressFooterAutoHideTask: Task<Void, Never>?" in interactive_view
    assert "@State var headerOverlayMeasuredHeight: CGFloat = 0" in interactive_view
    assert "sentenceProgressRange: headerSentenceProgressRange(for: chunk)" in interactive_header
    assert "struct PlayerProgressFooterView: View" in progress_footer
    assert "#if os(tvOS)" in progress_footer
    assert "TVScrubber(" in progress_footer
    assert "step: step" in progress_footer
    assert "Slider(value: $value" in progress_footer
    assert "var onTVFocusChanged: ((Bool) -> Void)? = nil" in progress_footer
    assert "onFocusChanged: onTVFocusChanged" in progress_footer
    assert '"interactiveReaderProgressFooter"' in progress_footer
    assert "videoPlayerProgressFooter" not in progress_footer
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
    assert "videoProgressFooter" in video_layout
    assert "PlayerProgressFooterView(" in video_layout
    assert "accessibilityLabel: \"Video progress\"" in video_layout
    assert "handleVideoScrubberSeek(time)" in video_layout
    assert "step: 15" in video_layout
    assert "style: .time" not in video_layout
    assert "let showTimelinePill: Bool" in video_header
    assert "showTimelinePill: Bool = true" in video_header
    assert "let timelineLabel = showTimelinePill ? videoTimelineLabel : nil" in video_header
    assert "showTimelinePill: false" in video_overlay
    assert "let timelineLabel: String? = nil" in tv_layout
    assert "let timelineLabel = videoTimelineLabel" not in tv_layout
    assert "scrubberRow" in tv_video_controls
    assert ".control(.scrubber)" in tv_video_controls
    assert "var step: Double? = nil" in tv_video_controls
    assert "if let step, step > 0" in tv_video_controls
    assert "step: 15" in tv_video_controls
    assert "onCommit: handleScrubberCommit" in tv_video_controls
    assert "case scrubber" in video_overlay_config
    assert "scrubberValue: Binding<Double>" not in video_overlay_config
    assert "isScrubbing: Binding<Bool>" not in video_overlay_config
    assert "beginScrubbing()" not in video_overlay_focus
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
    progress_move_body = interactive_view.split(
        "private func handleProgressMoveCommand(_ direction: MoveCommandDirection, chunk: InteractiveChunk) -> Bool",
        1,
    )[1].split("\n    func handleTVProgressFooterMoveCommand", 1)[0]
    footer_move_body = interactive_view.split(
        "func handleTVProgressFooterMoveCommand(_ direction: MoveCommandDirection)",
        1,
    )[1].split("\n    private func handleTranscriptMoveCommand", 1)[0]
    assert "case .up, .down:" in progress_move_body
    assert "case .up, .down:" in footer_move_body
    assert ".left" not in progress_move_body
    assert ".right" not in progress_move_body
    assert ".left" not in footer_move_body
    assert ".right" not in footer_move_body
    assert "handleTVProgressFooterHorizontalMove" not in interactive_view
    assert "onEditingChanged: handleHeaderSentenceProgressEditingChanged" in interactive_layout
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
    assert "clearHeaderSentenceProgressDraft()" in interactive_transcript
    assert input_handlers.count("handleSentenceSkip(") >= 4


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

    assert "let candidates = sentenceIndices.filter { $0 > currentSentence }" in sequence_controller
    assert "let candidates = sentenceIndices.filter { $0 < currentSentence }.reversed()" in sequence_controller
    assert "findSentenceTarget(sentenceIndex, preferredTrack: preferred)" in sequence_controller
    assert "preferredTrack ?? currentTrack" in sequence_controller.split(
        "func nextSentenceTarget", 1
    )[1].split("func previousSentence", 1)[0]


def test_video_playback_search_bookmarks_and_tvos_focus_are_reachable() -> None:
    video_search = _source(PLAYBACK / "VideoPlayerView+Search.swift")
    video_bookmarks = _source(PLAYBACK / "VideoPlayerView+Bookmarks.swift")
    video_player = _source(PLAYBACK / "VideoPlayerView.swift")
    video_lifecycle = _source(PLAYBACK / "VideoPlayerView+Lifecycle.swift")
    video_keyboard = _source(PLAYBACK / "VideoKeyboardSupport.swift")
    video_layout = _source(PLAYBACK / "VideoPlayerView+Layout.swift")
    video_linguist_source = _source(PLAYBACK / "VideoPlayerView+Linguist.swift")
    video_linguist = _source(SHARED / "LinguistBubbleCompatibility.swift")
    video_overlay = _source(PLAYBACK / "VideoPlayerOverlayView.swift")
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

    assert "appState.playerKeyboardShortcutsActive = true" in video_lifecycle
    assert "appState.playerKeyboardShortcutsActive = false" in video_lifecycle
    assert "videoSwiftUIKeyboardShortcutLayer" not in video_player
    assert "var videoSwiftUIKeyboardShortcutLayer" not in video_keyboard
    assert ".keyboardShortcut(.space, modifiers: [])" not in video_keyboard
    assert "Button(\"Previous Word\", action: handleVideoKeyboardPrevious)" not in video_keyboard
    assert "Button(\"Next Word\", action: handleVideoKeyboardNext)" not in video_keyboard
    assert "handleVideoKeyboardPrevious()" in video_player
    assert "handleVideoKeyboardNext()" in video_player
    assert "NotificationCenter.default.publisher(for: .keyboardShortcutPrevious)" in video_player
    assert "NotificationCenter.default.publisher(for: .keyboardShortcutNext)" in video_player
    assert "lastKeyboardShortcutDispatch" in video_player
    assert 'dispatchVideoKeyboardShortcut("playPause")' in video_keyboard
    assert 'dispatchVideoKeyboardShortcut("previous")' in video_keyboard
    assert 'dispatchVideoKeyboardShortcut("next")' in video_keyboard
    assert "handleSubtitleWordNavigation(-1)" in video_keyboard
    assert "handleSubtitleWordNavigation(1)" in video_keyboard
    assert "onPlayPause: handleVideoKeyboardPlayPause" in video_layout
    assert "onSkipBackward: handleVideoKeyboardPrevious" in video_layout
    assert "onSkipForward: handleVideoKeyboardNext" in video_layout
    assert "onLookup: handleVideoKeyboardLookup" in video_layout
    assert "PlayerKeyboardShortcutActions(" in video_keyboard
    assert 'self.dispatchShortcut("playPause") { self.onPlayPause?() }' in video_keyboard
    assert 'self.dispatchShortcut("previous") { self.onSkipBackward?() }' in video_keyboard
    assert 'self.dispatchShortcut("next") { self.onSkipForward?() }' in video_keyboard
    assert 'dispatchShortcut("playPause") { onPlayPause?() }' in video_keyboard
    assert "linguistVM.pronunciationSpeaker.onPlaybackStarted = {" in video_linguist_source
    assert "PlayerKeyboardShortcutBroker.shared.resetDispatchDebounce()" not in video_linguist_source
    assert "PlayerKeyboardShortcutBroker.shared.setActive(true)" in video_linguist_source
    assert "linguistVM.pronunciationSpeaker.onPlaybackFinished = {" in video_linguist_source
    assert "lastKeyboardShortcutDispatch = nil" in video_linguist_source
    assert "let subtitleAutoLookupDelayNanos: UInt64 = 250_000_000" in video_player
    assert "var onPreviousToken: (() -> Void)?" in video_linguist
    assert "actions.onPreviousToken = onPreviousToken" in video_linguist
    assert "onPreviousToken: { onNavigateSubtitleWord(-1) }" in video_overlay
    assert "onNextToken: { onNavigateSubtitleWord(1) }" in video_overlay

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
    assert selection.count("SentencePositionProvider.targetSentenceIndex(") >= 3
    assert "pendingJump: pendingSentenceJump" in selection
    assert "pendingJump: self.pendingSentenceJump" in selection
