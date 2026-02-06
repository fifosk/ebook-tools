import SwiftUI

// MARK: - Gestures

extension InteractiveTranscriptView {

    #if !os(tvOS)
    var swipeGesture: some Gesture {
        DragGesture(minimumDistance: 24, coordinateSpace: .local)
            .onEnded { value in
                // Don't process swipes if drag selection was/is active
                guard dragSelectionAnchor == nil else { return }
                guard !suppressPlaybackToggle else { return }
                let horizontal = value.translation.width
                let vertical = value.translation.height
                if abs(horizontal) > abs(vertical) {
                    if horizontal < 0 {
                        onSkipSentence(1)
                    } else if horizontal > 0 {
                        onSkipSentence(-1)
                    }
                } else {
                    if vertical > 0 {
                        onShowMenu()
                    } else if vertical < 0 {
                        if isMenuVisible {
                            onHideMenu()
                        } else {
                            onNavigateTrack(-1)
                        }
                    }
                }
            }
    }

    /// Swipe gesture for the bubble area in split view.
    /// Horizontal swipes navigate tokens (previous/next word).
    var bubbleAreaSwipeGesture: some Gesture {
        DragGesture(minimumDistance: 24, coordinateSpace: .local)
            .onEnded { value in
                let horizontal = value.translation.width
                let vertical = value.translation.height
                guard abs(horizontal) > abs(vertical) else { return }
                if horizontal < 0 {
                    onBubbleNextToken?()
                } else {
                    onBubblePreviousToken?()
                }
            }
    }
    #endif

    #if os(iOS)
    var selectionDragGesture: some Gesture {
        DragGesture(minimumDistance: 8, coordinateSpace: .named(TextPlayerTokenCoordinateSpace.name))
            .onChanged { value in
                // Allow drag selection on both iPad and iPhone when paused
                guard !audioCoordinator.isPlaying else { return }
                if dragSelectionAnchor == nil {
                    guard let anchorToken = tokenFrameContaining(value.startLocation) else { return }
                    dragSelectionAnchor = TextPlayerWordSelection(
                        sentenceIndex: anchorToken.sentenceIndex,
                        variantKind: anchorToken.variantKind,
                        tokenIndex: anchorToken.tokenIndex
                    )
                    // Suppress playback toggle during drag selection to prevent
                    // background tap gesture from triggering playback on drag end
                    suppressPlaybackTask?.cancel()
                    suppressPlaybackToggle = true
                }
                updateSelectionRange(at: value.location)
            }
            .onEnded { _ in
                dragSelectionAnchor = nil
                // Keep suppression active until lookup completes (350ms delay)
                // scheduleDragLookup sets up the delayed lookup, so we need to
                // keep suppression until after that task runs
                suppressPlaybackTask?.cancel()
                suppressPlaybackTask = Task { @MainActor in
                    // Wait for drag lookup delay plus a small buffer
                    try? await Task.sleep(nanoseconds: dragLookupDelayNanos + 50_000_000)
                    suppressPlaybackToggle = false
                }
            }
    }
    #endif

    #if !os(tvOS)
    var doubleTapGesture: some Gesture {
        TapGesture(count: 2)
            .onEnded {
                guard !suppressPlaybackToggle else { return }
                onTogglePlayback()
            }
    }
    #endif

    #if os(iOS)
    var playbackSingleTapGesture: some Gesture {
        DragGesture(minimumDistance: 0, coordinateSpace: .named(TextPlayerTokenCoordinateSpace.name))
            .onEnded { value in
                guard !suppressPlaybackToggle else { return }
                if isPhone, bubble != nil {
                    return
                }
                let distance = hypot(value.translation.width, value.translation.height)
                guard distance < 8 else { return }
                let location = value.location
                if tokenFrames.contains(where: { $0.frame.contains(location) }) {
                    return
                }
                if tapExclusionFrames.contains(where: { $0.contains(location) }) {
                    return
                }
                onTogglePlayback()
            }
    }

    var backgroundPlaybackTapGesture: some Gesture {
        DragGesture(minimumDistance: 0, coordinateSpace: .named(TextPlayerTokenCoordinateSpace.name))
            .onEnded { value in
                guard !suppressPlaybackToggle else { return }
                let distance = hypot(value.translation.width, value.translation.height)
                guard distance < 8 else { return }
                let location = value.location
                if bubble != nil, bubbleFrame.contains(location) {
                    return
                }
                if tokenFrames.contains(where: { $0.frame.contains(location) }) {
                    return
                }
                if tapExclusionFrames.contains(where: { $0.contains(location) }) {
                    return
                }
                if bubble != nil {
                    // Check if bubble is pinned (iPad only for this iOS code path)
                    let isPinned = isPad && iPadBubblePinned
                    if isPinned {
                        // Bubble is pinned - just toggle playback, don't close bubble
                        onTogglePlayback()
                    } else {
                        // Bubble is not pinned - close it, and toggle playback only if paused
                        onCloseBubble()
                        if !audioCoordinator.isPlaying {
                            onTogglePlayback()
                        }
                    }
                } else {
                    onTogglePlayback()
                }
            }
    }
    #endif

    #if os(iOS)
    var trackMagnifyGesture: some Gesture {
        MagnificationGesture()
            .onChanged { value in
                if trackMagnifyStartScale == nil {
                    trackMagnifyStartScale = trackFontScale
                }
                let startScale = trackMagnifyStartScale ?? trackFontScale
                onSetTrackFontScale(startScale * value)
            }
            .onEnded { _ in
                trackMagnifyStartScale = nil
            }
    }

    var bubbleMagnifyGesture: some Gesture {
        MagnificationGesture()
            .onChanged { value in
                if bubbleMagnifyStartScale == nil {
                    bubbleMagnifyStartScale = linguistFontScale
                }
                let startScale = bubbleMagnifyStartScale ?? linguistFontScale
                onSetLinguistFontScale(startScale * value)
            }
            .onEnded { _ in
                bubbleMagnifyStartScale = nil
            }
    }
    #endif

    #if os(iOS)
    /// Background tap gesture for iPhone when bubble is open.
    /// Tapping on or near a token triggers lookup; tapping elsewhere closes bubble and plays.
    var phoneBubbleOpenBackgroundTapGesture: some Gesture {
        DragGesture(minimumDistance: 0, coordinateSpace: .named(TextPlayerTokenCoordinateSpace.name))
            .onEnded { value in
                guard !suppressPlaybackToggle else { return }
                let distance = hypot(value.translation.width, value.translation.height)
                guard distance < 8 else { return }
                let location = value.location
                // Tapping on exclusion frames (track toggles, etc.) - ignore first
                if tapExclusionFrames.contains(where: { $0.contains(location) }) {
                    return
                }
                // If tapping on or near a token while paused, do lookup
                // Use nearestTokenFrameForTap for more forgiving hit testing
                if let tokenFrame = nearestTokenFrameForTap(at: location), !audioCoordinator.isPlaying {
                    // Suppress playback toggle when doing lookup
                    suppressPlaybackTask?.cancel()
                    suppressPlaybackToggle = true
                    suppressPlaybackTask = Task { @MainActor in
                        try? await Task.sleep(nanoseconds: 350_000_000)
                        suppressPlaybackToggle = false
                    }
                    onLookupToken(tokenFrame.sentenceIndex, tokenFrame.variantKind, tokenFrame.tokenIndex, tokenFrame.token)
                    return
                }
                // Tapping elsewhere - close bubble and resume playback
                onCloseBubble()
                if !audioCoordinator.isPlaying {
                    onTogglePlayback()
                }
            }
    }
    #endif
}
