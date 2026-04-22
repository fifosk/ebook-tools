import SwiftUI

// MARK: - Input Handlers

extension InteractivePlayerView {

    @ViewBuilder
    var keyboardShortcutLayer: some View {
        #if os(iOS)
        if isPad {
            KeyboardCommandHandler(
                onPlayPause: { audioCoordinator.togglePlayback() },
                onPrevious: {
                    if bubbleKeyboardNavigator.isKeyboardFocusActive {
                        bubbleKeyboardNavigator.navigateLeft()
                    } else if audioCoordinator.isPlaying {
                        viewModel.skipSentence(forward: false, preferredTrack: preferredSequenceTrack)
                    } else {
                        handleWordNavigation(-1, in: viewModel.selectedChunk)
                    }
                },
                onNext: {
                    if bubbleKeyboardNavigator.isKeyboardFocusActive {
                        bubbleKeyboardNavigator.navigateRight()
                    } else if audioCoordinator.isPlaying {
                        viewModel.skipSentence(forward: true, preferredTrack: preferredSequenceTrack)
                    } else {
                        handleWordNavigation(1, in: viewModel.selectedChunk)
                    }
                },
                onPreviousWord: { handleWordNavigation(-1, in: viewModel.selectedChunk) },
                onNextWord: { handleWordNavigation(1, in: viewModel.selectedChunk) },
                // Ctrl+Arrow: sentence navigation when paused (keeps bubble visible), word navigation when playing
                onPreviousSentence: {
                    if audioCoordinator.isPlaying {
                        handleWordNavigation(-1, in: viewModel.selectedChunk)
                    } else {
                        // Navigate to previous sentence while paused (bubble stays visible)
                        viewModel.skipSentence(forward: false, preferredTrack: preferredSequenceTrack)
                    }
                },
                onNextSentence: {
                    if audioCoordinator.isPlaying {
                        handleWordNavigation(1, in: viewModel.selectedChunk)
                    } else {
                        // Navigate to next sentence while paused (bubble stays visible)
                        viewModel.skipSentence(forward: true, preferredTrack: preferredSequenceTrack)
                    }
                },
                onExtendSelectionBackward: {
                    guard let chunk = viewModel.selectedChunk else { return }
                    handleWordRangeSelection(-1, in: chunk)
                },
                onExtendSelectionForward: {
                    guard let chunk = viewModel.selectedChunk else { return }
                    handleWordRangeSelection(1, in: chunk)
                },
                onLookup: {
                    // Handle Enter key when in bubble keyboard focus mode
                    if bubbleKeyboardNavigator.isKeyboardFocusActive {
                        handleBubbleKeyboardActivate()
                        return
                    }
                    guard !audioCoordinator.isPlaying else { return }
                    guard let chunk = viewModel.selectedChunk else { return }
                    handleLinguistLookup(in: chunk)
                },
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
                onShowMenu: {
                    if audioCoordinator.isPlaying {
                        showMenu()
                    } else if bubbleKeyboardNavigator.isKeyboardFocusActive {
                        // Already in bubble focus mode, ignore down arrow
                        return
                    } else if linguistBubble != nil, let chunk = viewModel.selectedChunk {
                        // Bubble is open, try to navigate down to it
                        let moved = handleTrackNavigation(1, in: chunk)
                        if !moved {
                            // At bottom track, enter bubble keyboard focus
                            bubbleKeyboardNavigator.enterFocus()
                        }
                    } else if let chunk = viewModel.selectedChunk {
                        handleTrackNavigation(1, in: chunk)
                    }
                },
                onHideMenu: {
                    if audioCoordinator.isPlaying {
                        hideMenu()
                    } else if bubbleKeyboardNavigator.isKeyboardFocusActive {
                        // Exit bubble keyboard focus
                        bubbleKeyboardNavigator.exitFocus()
                    } else if let chunk = viewModel.selectedChunk {
                        handleTrackNavigation(-1, in: chunk)
                    }
                },
                onBubbleNavigateLeft: {
                    bubbleKeyboardNavigator.navigateLeft()
                },
                onBubbleNavigateRight: {
                    bubbleKeyboardNavigator.navigateRight()
                }
            )
            .frame(width: 0, height: 0)
            .accessibilityHidden(true)
        }
        #else
        EmptyView()
        #endif
    }

    /// SwiftUI-native keyboard shortcuts. These are registered as Command
    /// menu items via SwiftUI and get dispatched by iPadOS's Magic-Keyboard
    /// integration layer REGARDLESS of which SwiftUI view currently has
    /// focus. Complements the UIKit UIKeyCommand path (KeyboardCommandHandler)
    /// — whichever path UIKit picks up first, the same action closures fire.
    ///
    /// Invisible Buttons with `.keyboardShortcut` are the supported idiom
    /// for global hardware-keyboard shortcuts in SwiftUI on iPadOS.
    @ViewBuilder
    var swiftUIKeyboardShortcutLayer: some View {
        #if os(iOS)
        if isPad {
            ZStack {
                Button("Play / Pause") { audioCoordinator.togglePlayback() }
                    .keyboardShortcut(.space, modifiers: [])
                Button("Previous") {
                    if bubbleKeyboardNavigator.isKeyboardFocusActive {
                        bubbleKeyboardNavigator.navigateLeft()
                    } else if audioCoordinator.isPlaying {
                        viewModel.skipSentence(forward: false, preferredTrack: preferredSequenceTrack)
                    } else {
                        handleWordNavigation(-1, in: viewModel.selectedChunk)
                    }
                }
                .keyboardShortcut(.leftArrow, modifiers: [])
                Button("Next") {
                    if bubbleKeyboardNavigator.isKeyboardFocusActive {
                        bubbleKeyboardNavigator.navigateRight()
                    } else if audioCoordinator.isPlaying {
                        viewModel.skipSentence(forward: true, preferredTrack: preferredSequenceTrack)
                    } else {
                        handleWordNavigation(1, in: viewModel.selectedChunk)
                    }
                }
                .keyboardShortcut(.rightArrow, modifiers: [])
                Button("Look Up Highlighted Word") {
                    if bubbleKeyboardNavigator.isKeyboardFocusActive {
                        handleBubbleKeyboardActivate()
                    } else if let chunk = viewModel.selectedChunk {
                        handleLinguistLookup(in: chunk)
                    }
                }
                .keyboardShortcut(.return, modifiers: [])
                Button("Previous Sentence") {
                    if audioCoordinator.isPlaying {
                        handleWordNavigation(-1, in: viewModel.selectedChunk)
                    } else {
                        viewModel.skipSentence(forward: false, preferredTrack: preferredSequenceTrack)
                    }
                }
                .keyboardShortcut(.leftArrow, modifiers: [.control])
                Button("Next Sentence") {
                    if audioCoordinator.isPlaying {
                        handleWordNavigation(1, in: viewModel.selectedChunk)
                    } else {
                        viewModel.skipSentence(forward: true, preferredTrack: preferredSequenceTrack)
                    }
                }
                .keyboardShortcut(.rightArrow, modifiers: [.control])
                Button("Show Menu") {
                    if audioCoordinator.isPlaying {
                        showMenu()
                    } else if let chunk = viewModel.selectedChunk {
                        handleTrackNavigation(1, in: chunk)
                    }
                }
                .keyboardShortcut(.downArrow, modifiers: [])
                Button("Hide Menu") {
                    if audioCoordinator.isPlaying {
                        hideMenu()
                    } else if bubbleKeyboardNavigator.isKeyboardFocusActive {
                        bubbleKeyboardNavigator.exitFocus()
                    } else if let chunk = viewModel.selectedChunk {
                        handleTrackNavigation(-1, in: chunk)
                    }
                }
                .keyboardShortcut(.upArrow, modifiers: [])
            }
            .frame(width: 0, height: 0)
            .opacity(0)
            .accessibilityHidden(true)
        }
        #else
        EmptyView()
        #endif
    }

    @ViewBuilder
    var trackpadSwipeLayer: some View {
        #if os(iOS)
        if isPad {
            TrackpadSwipeHandler(
                onSwipeDown: { showMenu() },
                onSwipeUp: { hideMenu() }
            )
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .accessibilityHidden(true)
        }
        #else
        EmptyView()
        #endif
    }

    func handleKeyboardFontAdjust(increase: Bool) {
        if linguistBubble != nil {
            adjustLinguistFontScale(by: increase ? linguistFontScaleStep : -linguistFontScaleStep)
        } else {
            adjustTrackFontScale(by: increase ? trackFontScaleStep : -trackFontScaleStep)
        }
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
        #endif
        guard !isMenuVisible else { return }
        guard viewModel.selectedChunk != nil else { return }
        resumePlaybackAfterMenu = audioCoordinator.isPlaybackRequested || audioCoordinator.isPlaying
        if resumePlaybackAfterMenu {
            audioCoordinator.pause()
        }
        withAnimation(.easeOut(duration: 0.2)) {
            isMenuVisible = true
        }
    }

    func hideMenu() {
        #if os(tvOS)
        // Menu is disabled on tvOS
        return
        #endif
        guard isMenuVisible else { return }
        withAnimation(.easeOut(duration: 0.2)) {
            isMenuVisible = false
        }
        if resumePlaybackAfterMenu {
            audioCoordinator.play()
        }
        resumePlaybackAfterMenu = false
    }
}
