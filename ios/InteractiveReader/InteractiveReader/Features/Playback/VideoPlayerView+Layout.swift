import AVFoundation
import SwiftUI
#if canImport(UIKit)
import UIKit
#endif

extension VideoPlayerView {
    @ViewBuilder
    var playerContent: some View {
        if let player = coordinator.playerInstance() {
            ZStack {
                playerSurface(player)
                overlayView
                #if os(iOS)
                if isPad {
                    VideoKeyboardCommandHandler(
                        onPlayPause: { coordinator.togglePlayback() },
                        onSkipBackward: {
                            if coordinator.isPlaying {
                                handleSentenceSkip(-1)
                            } else {
                                handleSubtitleWordNavigation(-1)
                            }
                        },
                        onSkipForward: {
                            if coordinator.isPlaying {
                                handleSentenceSkip(1)
                            } else {
                                handleSubtitleWordNavigation(1)
                            }
                        },
                        onNavigateLineUp: { _ = handleSubtitleTrackNavigation(-1) },
                        onNavigateLineDown: { _ = handleSubtitleTrackNavigation(1) },
                        onLookup: {
                            guard !coordinator.isPlaying else { return }
                            handleSubtitleLookup()
                        },
                        onIncreaseFont: { adjustSubtitleFontScale(by: subtitleFontScaleStep) },
                        onDecreaseFont: { adjustSubtitleFontScale(by: -subtitleFontScaleStep) },
                        onToggleOriginal: { toggleSubtitleVisibility(.original) },
                        onToggleTransliteration: { toggleSubtitleVisibility(.transliteration) },
                        onToggleTranslation: { toggleSubtitleVisibility(.translation) },
                        onToggleShortcutHelp: { toggleShortcutHelp() },
                        onOptionKeyDown: { showShortcutHelpModifier() },
                        onOptionKeyUp: { hideShortcutHelpModifier() }
                    )
                    .frame(width: 0, height: 0)
                    .accessibilityHidden(true)
                }
                if isPad, isShortcutHelpVisible {
                    VideoShortcutHelpOverlayView(onDismiss: { dismissShortcutHelp() })
                        .transition(.opacity)
                        .zIndex(4)
                }
                #endif
            }
        } else {
            ProgressView("Preparing video…")
        }
    }

    @ViewBuilder
    func playerSurface(_ player: AVPlayer) -> some View {
        VideoPlayerControllerView(
            player: player,
            onShowControls: handleUserInteraction
        )
        #if os(iOS)
        .background(videoViewportReader)
        .simultaneousGesture(videoTapGesture, including: .gesture)
        .simultaneousGesture(videoScrubGesture, including: .gesture)
        #endif
        #if os(tvOS)
        .focusable(false)
        .allowsHitTesting(false)
        #endif
    }

    var overlayView: VideoPlayerOverlayView {
        VideoPlayerOverlayView(
            cues: cues,
            currentTime: coordinator.currentTime,
            duration: coordinator.duration,
            subtitleError: subtitleError,
            tracks: orderedTracks,
            selectedTrack: $selectedTrack,
            subtitleVisibility: $subtitleVisibility,
            showSubtitleSettings: $showSubtitleSettings,
            showTVControls: $showTVControls,
            scrubberValue: $scrubberValue,
            isScrubbing: $isScrubbing,
            metadata: metadata,
            segmentOptions: segmentOptions,
            selectedSegmentID: selectedSegmentID,
            jobProgressLabel: jobProgressLabel,
            jobRemainingLabel: jobRemainingLabel,
            bookmarks: bookmarks,
            onAddBookmark: canUseBookmarks ? addBookmark : nil,
            onJumpToBookmark: jumpToBookmark,
            onRemoveBookmark: removeBookmark,
            subtitleFontScale: subtitleFontScale,
            isPlaying: coordinator.isPlaying,
            subtitleSelection: subtitleSelection,
            subtitleBubble: subtitleBubble,
            lookupLanguage: resolvedLookupLanguage,
            lookupLanguageOptions: lookupLanguageOptions,
            onLookupLanguageChange: { storedLookupLanguage = $0 },
            llmModel: resolvedLlmModel ?? MyLinguistPreferences.defaultLlmModel,
            llmModelOptions: llmModelOptions,
            onLlmModelChange: { storedLlmModel = $0 },
            subtitleLinguistFontScale: subtitleLinguistFontScale,
            canIncreaseSubtitleLinguistFont: canIncreaseSubtitleLinguistFont,
            canDecreaseSubtitleLinguistFont: canDecreaseSubtitleLinguistFont,
            isHeaderCollapsed: isHeaderCollapsed,
            onToggleHeaderCollapsed: toggleHeaderCollapsed,
            onResetSubtitleFont: {
                resetSubtitleFontScale()
            },
            onSetSubtitleFont: { value in
                setSubtitleFontScale(value)
            },
            onResetSubtitleBubbleFont: {
                resetSubtitleLinguistFontScale()
            },
            onSetSubtitleBubbleFont: { value in
                setSubtitleLinguistFontScale(value)
            },
            onPlayPause: {
                handleUserInteraction()
                coordinator.togglePlayback()
            },
            onSkipForward: {
                handleUserInteraction()
                coordinator.skip(by: 15)
            },
            onSkipBackward: {
                handleUserInteraction()
                coordinator.skip(by: -15)
            },
            onSeek: { time in
                handleUserInteraction()
                coordinator.seek(to: time)
            },
            onSkipSentence: { delta in
                handleSentenceSkip(delta)
            },
            onNavigateSubtitleWord: { delta in
                handleSubtitleWordNavigation(delta)
            },
            onNavigateSubtitleTrack: { delta in
                handleSubtitleTrackNavigation(delta)
            },
            onSubtitleLookup: {
                handleSubtitleLookup()
            },
            onSubtitleTokenLookup: { token in
                handleSubtitleTokenLookup(token)
            },
            onSubtitleTokenSeek: { token in
                handleSubtitleTokenSeek(token)
            },
            onIncreaseSubtitleLinguistFont: {
                adjustSubtitleLinguistFontScale(by: subtitleLinguistFontScaleStep)
            },
            onDecreaseSubtitleLinguistFont: {
                adjustSubtitleLinguistFontScale(by: -subtitleLinguistFontScaleStep)
            },
            onSelectSegment: { id in
                showSubtitleSettings = false
                onSelectSegment?(id)
            },
            onCloseSubtitleBubble: {
                closeSubtitleBubble()
            },
            onUserInteraction: handleUserInteraction
        )
    }

    var orderedTracks: [VideoSubtitleTrack] {
        subtitleTracks.sorted { lhs, rhs in
            if lhs.format.priority == rhs.format.priority {
                return lhs.label.localizedCaseInsensitiveCompare(rhs.label) == .orderedAscending
            }
            return lhs.format.priority < rhs.format.priority
        }
    }

    var isPad: Bool {
        #if os(iOS)
        return UIDevice.current.userInterfaceIdiom == .pad
        #else
        return false
        #endif
    }

    var isShortcutHelpVisible: Bool {
        isShortcutHelpPinned || isShortcutHelpModifierActive
    }
}
