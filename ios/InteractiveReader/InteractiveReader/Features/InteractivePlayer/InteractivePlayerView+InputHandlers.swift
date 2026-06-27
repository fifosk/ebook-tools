import SwiftUI

// MARK: - Input Handlers

extension InteractivePlayerView {

    @ViewBuilder
    var keyboardShortcutLayer: some View {
        #if os(iOS)
        KeyboardCommandHandler(
            onPlayPause: handleKeyboardPlayPause,
            onPrevious: handleKeyboardPrevious,
            onNext: handleKeyboardNext,
            onPreviousWord: handleKeyboardPreviousWord,
            onNextWord: handleKeyboardNextWord,
            // Ctrl+Arrow: sentence navigation when paused (keeps bubble visible), word navigation when playing
            onPreviousSentence: handleKeyboardPreviousSentence,
            onNextSentence: handleKeyboardNextSentence,
            onExtendSelectionBackward: handleKeyboardExtendSelectionBackward,
            onExtendSelectionForward: handleKeyboardExtendSelectionForward,
            onLookup: handleUIKitKeyboardLookup,
            onIncreaseFont: { adjustTrackFontScale(by: trackFontScaleStep) },
            onDecreaseFont: { adjustTrackFontScale(by: -trackFontScaleStep) },
            onToggleOriginal: { toggleTrackIfAvailable(.original) },
            onToggleTransliteration: { toggleTrackIfAvailable(.transliteration) },
            onToggleTranslation: { toggleTrackIfAvailable(.translation) },
            onToggleOriginalAudio: { toggleAudioTrack(.original) },
            onToggleTranslationAudio: { toggleAudioTrack(.translation) },
            onToggleReadingBed: { toggleReadingBed() },
            onIncreaseLinguistFont: { handleKeyboardFontAdjust(increase: true) },
            onDecreaseLinguistFont: { handleKeyboardFontAdjust(increase: false) },
            onToggleShortcutHelp: { toggleShortcutHelp() },
            onToggleHeader: { toggleHeaderCollapsed() },
            onIncreaseHeaderScale: { adjustHeaderScale(by: headerScaleStep) },
            onDecreaseHeaderScale: { adjustHeaderScale(by: -headerScaleStep) },
            onOptionKeyDown: { showShortcutHelpModifier() },
            onOptionKeyUp: { hideShortcutHelpModifier() },
            onShowMenu: handleUIKitKeyboardShowMenu,
            onHideMenu: handleKeyboardHideMenu,
            shouldNavigateBubbleWords: {
                linguistBubble != nil
            },
            onBubbleNavigateLeft: handleKeyboardBubbleNavigateLeft,
            onBubbleNavigateRight: handleKeyboardBubbleNavigateRight
        )
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .accessibilityHidden(true)
        #else
        EmptyView()
        #endif
    }

    @ViewBuilder
    var trackpadSwipeLayer: some View {
        #if os(iOS)
        if isPad {
            TrackpadSwipeHandler(
                onSwipeDown: showMenu,
                onSwipeUp: hideMenu
            )
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .accessibilityHidden(true)
        }
        #else
        EmptyView()
        #endif
    }

    #if os(iOS)
    func handleKeyboardPlayPause() {
        logInteractiveKeyboardAction("playPause")
        handlePlaybackToggleCommand()
    }

    func handleKeyboardPrevious() {
        logInteractiveKeyboardAction("previous")
        if linguistBubble != nil {
            handleKeyboardBubbleNavigateLeft()
        } else if audioCoordinator.isPlaying {
            if let chunk = viewModel.selectedChunk {
                handleSentenceSkip(-1, in: chunk)
            }
        } else {
            handleWordNavigation(-1, in: viewModel.selectedChunk)
        }
    }

    func handleKeyboardNext() {
        logInteractiveKeyboardAction("next")
        if linguistBubble != nil {
            handleKeyboardBubbleNavigateRight()
        } else if audioCoordinator.isPlaying {
            if let chunk = viewModel.selectedChunk {
                handleSentenceSkip(1, in: chunk)
            }
        } else {
            handleWordNavigation(1, in: viewModel.selectedChunk)
        }
    }

    func handleKeyboardPreviousWord() {
        logInteractiveKeyboardAction("previousWord")
        handleWordNavigation(-1, in: viewModel.selectedChunk)
    }

    func handleKeyboardNextWord() {
        logInteractiveKeyboardAction("nextWord")
        handleWordNavigation(1, in: viewModel.selectedChunk)
    }

    func handleKeyboardPreviousSentence() {
        logInteractiveKeyboardAction("previousSentence")
        if linguistBubble != nil {
            handleKeyboardBubbleNavigateLeft()
        } else if audioCoordinator.isPlaying {
            handleWordNavigation(-1, in: viewModel.selectedChunk)
        } else {
            if let chunk = viewModel.selectedChunk {
                handleSentenceSkip(-1, in: chunk)
            }
        }
    }

    func handleKeyboardNextSentence() {
        logInteractiveKeyboardAction("nextSentence")
        if linguistBubble != nil {
            handleKeyboardBubbleNavigateRight()
        } else if audioCoordinator.isPlaying {
            handleWordNavigation(1, in: viewModel.selectedChunk)
        } else {
            if let chunk = viewModel.selectedChunk {
                handleSentenceSkip(1, in: chunk)
            }
        }
    }

    func handleKeyboardExtendSelectionBackward() {
        logInteractiveKeyboardAction("extendSelectionBackward")
        guard let chunk = viewModel.selectedChunk else { return }
        handleWordRangeSelection(-1, in: chunk)
    }

    func handleKeyboardExtendSelectionForward() {
        logInteractiveKeyboardAction("extendSelectionForward")
        guard let chunk = viewModel.selectedChunk else { return }
        handleWordRangeSelection(1, in: chunk)
    }

    func handleUIKitKeyboardLookup() {
        logInteractiveKeyboardAction("lookup.ui")
        if bubbleKeyboardNavigator.isKeyboardFocusActive {
            handleBubbleKeyboardActivate()
            return
        }
        guard !audioCoordinator.isPlaying else { return }
        guard let chunk = viewModel.selectedChunk else { return }
        handleLinguistLookup(in: chunk)
    }

    func handleUIKitKeyboardShowMenu() {
        logInteractiveKeyboardAction("showMenu.ui")
        if audioCoordinator.isPlaying {
            showMenu()
        } else if bubbleKeyboardNavigator.isKeyboardFocusActive {
            return
        } else if linguistBubble != nil, let chunk = viewModel.selectedChunk {
            let moved = handleTrackNavigation(1, in: chunk)
            if !moved {
                bubbleKeyboardNavigator.enterFocus()
            }
        } else if let chunk = viewModel.selectedChunk {
            handleTrackNavigation(1, in: chunk)
        }
    }

    func handleKeyboardHideMenu() {
        logInteractiveKeyboardAction("hideMenu")
        if audioCoordinator.isPlaying {
            hideMenu()
        } else if bubbleKeyboardNavigator.isKeyboardFocusActive {
            bubbleKeyboardNavigator.exitFocus()
        } else if let chunk = viewModel.selectedChunk {
            handleTrackNavigation(-1, in: chunk)
        }
    }

    func handleKeyboardBubbleNavigateLeft() {
        logInteractiveKeyboardAction("bubbleNavigateLeft")
        handleKeyboardBubbleWordNavigation(-1)
    }

    func handleKeyboardBubbleNavigateRight() {
        logInteractiveKeyboardAction("bubbleNavigateRight")
        handleKeyboardBubbleWordNavigation(1)
    }

    func handleKeyboardBubbleWordNavigation(_ delta: Int) {
        guard let chunk = viewModel.selectedChunk else { return }
        handleWordNavigation(delta, in: chunk)
    }

    func logInteractiveKeyboardAction(_ action: String) {
        keyboardShortcutDebugLog(
            "[KeyboardShortcut] Interactive action=\(action) " +
            "playing=\(audioCoordinator.isPlaying) " +
            "bubble=\(linguistBubble != nil) " +
            "bubbleFocus=\(bubbleKeyboardNavigator.isKeyboardFocusActive) " +
            "chunk=\(viewModel.selectedChunk?.id ?? "<none>")"
        )
    }
    #endif

    func handlePlaybackToggleCommand() {
        if audioCoordinator.isPlaying || audioCoordinator.isPlaybackRequested {
            audioCoordinator.pause()
            return
        }
        guard let chunk = viewModel.selectedChunk else {
            audioCoordinator.play()
            return
        }
        if audioCoordinator.activeURL == nil && audioCoordinator.activeURLs.isEmpty {
            viewModel.prepareAudio(for: chunk, autoPlay: true)
            return
        }
        audioCoordinator.play()
    }

    func handleKeyboardFontAdjust(increase: Bool) {
        if linguistBubble != nil {
            adjustLinguistFontScale(by: increase ? linguistFontScaleStep : -linguistFontScaleStep)
        } else {
            adjustTrackFontScale(by: increase ? trackFontScaleStep : -trackFontScaleStep)
        }
    }

    func requestKeyboardShortcutFocus() {
        #if os(iOS)
        PlayerKeyboardShortcutBroker.shared.setActive(true)
        focusedArea = .transcript
        NotificationCenter.default.post(name: .keyboardShortcutReclaimFocus, object: nil)
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.1) {
            PlayerKeyboardShortcutBroker.shared.setActive(true)
            focusedArea = .transcript
            NotificationCenter.default.post(name: .keyboardShortcutReclaimFocus, object: nil)
        }
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.35) {
            PlayerKeyboardShortcutBroker.shared.setActive(true)
            focusedArea = .transcript
            NotificationCenter.default.post(name: .keyboardShortcutReclaimFocus, object: nil)
        }
        #endif
    }

    @ViewBuilder
    var shortcutHelpOverlay: some View {
        #if os(iOS)
        if isPad, isShortcutHelpVisible {
            ShortcutHelpOverlayView(onDismiss: { dismissShortcutHelp() })
                .transition(.opacity)
                .zIndex(4)
        }
        #else
        EmptyView()
        #endif
    }

    #if !os(tvOS)
    var menuToggleGesture: some Gesture {
        DragGesture(minimumDistance: 24, coordinateSpace: .local)
            .onEnded { value in
                let horizontal = value.translation.width
                let vertical = value.translation.height
                guard abs(vertical) > abs(horizontal) else { return }
                if vertical > 24 {
                    showMenu()
                } else if vertical < -24 {
                    hideMenu()
                }
            }
    }
    #endif

    func showMenu() {
        #if os(tvOS)
        // Menu is disabled on tvOS - controls are in header pills
        return
        #else
        guard !isMenuVisible else { return }
        guard viewModel.selectedChunk != nil else { return }
        resumePlaybackAfterMenu = audioCoordinator.isPlaybackRequested || audioCoordinator.isPlaying
        if resumePlaybackAfterMenu {
            audioCoordinator.pause()
        }
        withAnimation(.easeOut(duration: 0.2)) {
            isMenuVisible = true
        }
        #endif
    }

    func hideMenu() {
        #if os(tvOS)
        // Menu is disabled on tvOS
        return
        #else
        guard isMenuVisible else { return }
        withAnimation(.easeOut(duration: 0.2)) {
            isMenuVisible = false
        }
        if resumePlaybackAfterMenu {
            audioCoordinator.play()
        }
        resumePlaybackAfterMenu = false
        #endif
    }
}
