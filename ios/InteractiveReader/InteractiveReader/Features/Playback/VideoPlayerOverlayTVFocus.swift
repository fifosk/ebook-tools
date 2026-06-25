import SwiftUI

#if os(tvOS)
extension VideoPlayerOverlayView {
    func handleTVAppear() {
        if showTVControls {
            focusTarget = .control(.playPause)
        } else {
            // Keep focus on subtitles so a single tap can trigger lookup immediately.
            focusTarget = .subtitles
        }
    }

    func handleTVSettingsChange(_ isVisible: Bool) {
        if isVisible {
            focusTarget = nil
        } else if showTVControls {
            focusTarget = .control(.playPause)
        } else {
            focusTarget = .subtitles
        }
    }

    func handleTVControlsChange(_ isVisible: Bool) {
        if isVisible {
            focusTarget = .control(.playPause)
        } else {
            focusTarget = .subtitles
        }
    }

    func handleTVPlayingChange(_ playing: Bool) {
        if playing {
            showTVControls = false
            focusTarget = .subtitles
        } else if showTVControls {
            focusTarget = .control(.playPause)
        } else {
            focusTarget = .subtitles
        }
    }

    func handleBubbleMoveCommand(_ direction: MoveCommandDirection) {
        guard focusTarget == .bubble else { return }
        switch direction {
        case .up:
            focusTarget = .control(.header)
        case .down:
            focusTarget = .subtitles
        default:
            break
        }
    }

    func handleHeaderLongPress() {
        onToggleHeaderCollapsed()
    }

    func handleTimelinePillMoveCommand(_ direction: MoveCommandDirection) {
        guard focusTarget == .control(.header) else { return }
        switch direction {
        case .down:
            if subtitleBubble != nil {
                focusTarget = .bubble
            } else {
                focusTarget = .subtitles
            }
        case .left:
            if onAddBookmark != nil {
                focusTarget = .control(.headerBookmark)
            } else if searchPill != nil {
                focusTarget = .control(.headerSearch)
            }
        default:
            break
        }
    }

    func handleSearchPillMoveCommand(_ direction: MoveCommandDirection) {
        guard focusTarget == .control(.headerSearch) else { return }
        switch direction {
        case .right:
            if onAddBookmark != nil {
                focusTarget = .control(.headerBookmark)
            } else {
                focusTarget = .control(.header)
            }
        case .down:
            if subtitleBubble != nil {
                focusTarget = .bubble
            } else {
                focusTarget = .subtitles
            }
        default:
            break
        }
    }

    func handleSubtitleMoveCommand(_ direction: MoveCommandDirection) {
        guard !showSubtitleSettings else { return }
        switch direction {
        case .left:
            if isPlaying {
                handlePlaybackDirectionalCommand(direction)
            } else {
                onNavigateSubtitleWord(-1)
            }
            focusTarget = .subtitles
        case .right:
            if isPlaying {
                handlePlaybackDirectionalCommand(direction)
            } else {
                onNavigateSubtitleWord(1)
            }
            focusTarget = .subtitles
        case .up:
            if isPlaying {
                revealTVControls(focus: .header)
            } else {
                let moved = onNavigateSubtitleTrack(-1)
                if moved {
                    suppressControlFocusTemporarily()
                    focusTarget = .subtitles
                } else if subtitleBubble != nil {
                    suppressControlFocus = false
                    focusTarget = .bubble
                } else {
                    suppressControlFocus = false
                    focusTarget = .control(.header)
                }
            }
        case .down:
            if isPlaying {
                revealTVControls(focus: .playPause)
                return
            }
            let moved = onNavigateSubtitleTrack(1)
            if moved {
                suppressControlFocusTemporarily()
                focusTarget = .subtitles
            } else {
                suppressControlFocus = false
                if subtitleBubble != nil {
                    focusTarget = .bubble
                } else {
                    showTVControls = true
                    focusTarget = .control(.playPause)
                }
            }
        default:
            break
        }
    }

    func handleSubtitleTap() {
        guard focusTarget != .bubble else { return }
        if isPlaying {
            revealTVControls(focus: .playPause)
        } else {
            onSubtitleLookup()
        }
    }

    func revealTVControls(focus target: TVPlayerControlTarget) {
        suppressControlFocus = false
        showTVControls = true
        focusTarget = .control(target)
        onUserInteraction()
    }

    func handlePlaybackDirectionalCommand(_ direction: MoveCommandDirection) {
        guard direction == .left || direction == .right else { return }
        if pendingSkipTask != nil, pendingSkipDirection == direction {
            pendingSkipTask?.cancel()
            pendingSkipTask = nil
            pendingSkipDirection = nil
            beginScrubbing()
            return
        }
        pendingSkipTask?.cancel()
        pendingSkipDirection = direction
        let delta = direction == .left ? -1 : 1
        pendingSkipTask = Task {
            try? await Task.sleep(nanoseconds: 200_000_000)
            await MainActor.run {
                pendingSkipTask = nil
                pendingSkipDirection = nil
                onSkipSentence(delta)
            }
        }
    }

    func beginScrubbing() {
        showTVControls = true
        scrubberValue = displayTime
        focusTarget = .control(.scrubber)
        onUserInteraction()
    }

    func suppressControlFocusTemporarily() {
        suppressFocusTask?.cancel()
        suppressControlFocus = true
        suppressFocusTask = Task { @MainActor in
            try? await Task.sleep(nanoseconds: 150_000_000)
            suppressControlFocus = false
        }
    }
}
#endif
