import SwiftUI
#if os(iOS) || os(tvOS)
import UIKit
#endif

struct InteractiveBubbleHeightKey: PreferenceKey {
    static var defaultValue: CGFloat = 0

    static func reduce(value: inout CGFloat, nextValue: () -> CGFloat) {
        value = max(value, nextValue())
    }
}

struct InteractiveBubbleFrameKey: PreferenceKey {
    static var defaultValue: CGRect = .zero

    static func reduce(value: inout CGRect, nextValue: () -> CGRect) {
        value = nextValue()
    }
}

struct InteractiveTranscriptView: View {
    let viewModel: InteractivePlayerViewModel
    @ObservedObject var audioCoordinator: AudioPlayerCoordinator
    let sentences: [TextPlayerSentenceDisplay]
    let selection: TextPlayerWordSelection?
    let selectionRange: TextPlayerWordSelectionRange?
    let bubble: MyLinguistBubbleState?
    let lookupLanguage: String
    let lookupLanguageOptions: [String]
    let onLookupLanguageChange: (String) -> Void
    let llmModel: String
    let llmModelOptions: [String]
    let onLlmModelChange: (String) -> Void
    var ttsVoice: String? = nil
    var ttsVoiceOptions: [String] = []
    var onTtsVoiceChange: ((String?) -> Void)? = nil
    let playbackPrimaryKind: TextPlayerVariantKind?
    let visibleTracks: Set<TextPlayerVariantKind>
    let isBubbleFocusEnabled: Bool
    let onToggleTrack: (TextPlayerVariantKind) -> Void
    let isMenuVisible: Bool
    let isTranscriptLoading: Bool
    let transcriptLoadError: String?
    let onRetryTranscriptLoad: (() -> Void)?
    let trackFontScale: CGFloat
    let minTrackFontScale: CGFloat
    let maxTrackFontScale: CGFloat
    let autoScaleEnabled: Bool
    let linguistFontScale: CGFloat
    let canIncreaseLinguistFont: Bool
    let canDecreaseLinguistFont: Bool
    @FocusState.Binding var focusedArea: InteractivePlayerFocusArea?
    let onSkipSentence: (Int) -> Void
    let onNavigateTrack: (Int) -> Void
    let onShowMenu: () -> Void
    let onHideMenu: () -> Void
    let onLookup: () -> Void
    let onLookupToken: (Int, TextPlayerVariantKind, Int, String) -> Void
    let onSeekToken: (Int, Int?, TextPlayerVariantKind, Int, Double?, Bool) -> Void
    let onUpdateSelectionRange: (TextPlayerWordSelectionRange, TextPlayerWordSelection) -> Void
    let onIncreaseLinguistFont: () -> Void
    let onDecreaseLinguistFont: () -> Void
    let onSetTrackFontScale: (CGFloat) -> Void
    let onSetLinguistFontScale: (CGFloat) -> Void
    let onCloseBubble: () -> Void
    let onTogglePlayback: () -> Void
    var onToggleHeader: (() -> Void)? = nil
    /// Callback to navigate to previous token (swipe right on bubble)
    var onBubblePreviousToken: (() -> Void)? = nil
    /// Callback to navigate to next token (swipe left on bubble)
    var onBubbleNextToken: (() -> Void)? = nil
    /// iPad split layout direction
    var iPadSplitDirection: iPadBubbleSplitDirection = .vertical
    /// iPad split ratio (0.0-1.0, percentage of space for tracks in vertical, or bubble in horizontal)
    @Binding var iPadSplitRatio: CGFloat
    /// Callback to toggle iPad layout direction
    var onToggleLayoutDirection: (() -> Void)? = nil
    /// (iPad) Whether the bubble is pinned (stays visible during playback)
    var iPadBubblePinned: Bool = false
    /// Callback to toggle iPad bubble pin state
    var onToggleBubblePin: (() -> Void)? = nil
    /// Callback to play word from narration audio (seeks to cached timing)
    var onPlayFromNarration: (() -> Void)? = nil
    /// Callback to read the current lookup query aloud.
    var onReadAloud: (() -> Void)? = nil
    /// Keyboard navigator for iPad bubble focus management (iOS only, ignored on tvOS)
    @ObservedObject var bubbleKeyboardNavigator: iOSBubbleKeyboardNavigator = iOSBubbleKeyboardNavigator()

    #if os(iOS)
    @State var trackMagnifyStartScale: CGFloat?
    @State var bubbleMagnifyStartScale: CGFloat?
    @State var isDraggingDivider = false
    @State var dividerDragStartRatio: CGFloat = 0
    /// Track previous split ratio for calculating font scale changes
    @State var previousSplitRatio: CGFloat = 0.5
    #endif
    @State var bubbleHeight: CGFloat = 0
    @State var trackHeight: CGFloat = 0
    @State var effectiveTrackFontScale: CGFloat = 0
    @State var suppressPlaybackToggle = false
    @State var suppressPlaybackTask: Task<Void, Never>?
    @State var autoScaleNeedsUpdate = false
    @State var autoScaleTask: Task<Void, Never>?
    @State var lastMeasuredTrackHeight: CGFloat = 0
    @State var lastAvailableTrackHeight: CGFloat = 0
    @State var lastLayoutSize: CGSize = .zero
    @State var tokenFrames: [TextPlayerTokenFrame] = []
    @State var tapExclusionFrames: [CGRect] = []
    @State var bubbleFrame: CGRect = .zero
    @State var dragSelectionAnchor: TextPlayerWordSelection?
    @State var dragLookupTask: Task<Void, Never>?
    let dragLookupDelayNanos: UInt64 = 350_000_000

    var body: some View {
        transcriptContent
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: isTV ? .top : .center)
            .onChange(of: audioCoordinator.duration) { _, newValue in handleAudioDurationChange(newValue) }
            .onChange(of: audioCoordinator.activeURL) { _, _ in handleAudioURLChange() }
            .onAppear(perform: handleTranscriptAppear)
    }

    private func handleAudioDurationChange(_ newValue: Double) {
        viewModel.recordAudioDuration(newValue, for: audioCoordinator.activeURL)
    }

    private func handleAudioURLChange() {
        viewModel.recordAudioDuration(audioCoordinator.duration, for: audioCoordinator.activeURL)
    }

    private func handleTranscriptAppear() {
        viewModel.recordAudioDuration(audioCoordinator.duration, for: audioCoordinator.activeURL)
    }

    @ViewBuilder
    private var transcriptContent: some View {
        GeometryReader { proxy in
            let availableHeight = proxy.size.height
            let tvBubbleSplit = isTV && bubble != nil
            let stackSpacing: CGFloat = bubble == nil ? 12 : (isTV ? 10 : (isPad ? 0 : 6))
            let minBubbleReserve: CGFloat = tvBubbleSplit
                ? availableHeight * 0.5
                : availableHeight * (isPad ? 0.35 : 0.4)
            let bubbleReserve = bubble == nil
                ? 0
                : max(bubbleHeight + stackSpacing, minBubbleReserve)
            let preferredTextHeight = (isPad && bubble != nil && !tvBubbleSplit)
                ? availableHeight * 0.7
                : availableHeight
            let textHeight = max(min(preferredTextHeight, availableHeight - bubbleReserve), 0)
            let safeAreaBottom: CGFloat = {
                #if os(iOS)
                return isPhone ? proxy.safeAreaInsets.bottom : 0
                #else
                return 0
                #endif
            }()
            // Calculate available track height for auto-scaling
            // For phone with bubble: use the constrained track area height
            let textHeightLimit: CGFloat = {
                if isPhone {
                    let fullHeight = max(availableHeight - safeAreaBottom, 0)
                    if bubble != nil {
                        let isPortrait = proxy.size.height > proxy.size.width
                        if isPortrait {
                            // Portrait: tracks get 45% of height
                            return fullHeight * 0.45
                        } else {
                            // Landscape: tracks get full height but in a narrower area
                            // Still use full height for auto-scale calculation
                            return fullHeight
                        }
                    }
                    return fullHeight
                }
                return textHeight
            }()
            let shouldAutoScaleTracks = !isTV && autoScaleEnabled
            let bubbleFocusEnabled: Bool = {
                #if os(tvOS)
                return isBubbleFocusEnabled
                #else
                return true
                #endif
            }()
            let tokenLookupHandler: (Int, TextPlayerVariantKind, Int, String) -> Void = {
                sentenceIndex, variantKind, tokenIndex, token in
                suppressPlaybackTask?.cancel()
                suppressPlaybackToggle = true
                suppressPlaybackTask = Task { @MainActor in
                    try? await Task.sleep(nanoseconds: 350_000_000)
                    suppressPlaybackToggle = false
                }
                onLookupToken(sentenceIndex, variantKind, tokenIndex, token)
            }
            let tokenSeekHandler: (Int, Int?, TextPlayerVariantKind, Int, Double?, Bool) -> Void = {
                sentenceIndex, sentenceNumber, variantKind, tokenIndex, seekTime, shouldPlay in
                // Token taps handle playback directly. Suppress the background gesture so
                // it never interprets the same tap as a play/pause toggle.
                let wasPaused = !audioCoordinator.isPlaying
                let effectiveShouldPlay = shouldPlay && !wasPaused
                if shouldPlay || !audioCoordinator.isPlaying {
                    suppressPlaybackTask?.cancel()
                    suppressPlaybackToggle = true
                    suppressPlaybackTask = Task { @MainActor in
                        try? await Task.sleep(nanoseconds: 350_000_000)
                        suppressPlaybackToggle = false
                    }
                }
                onSeekToken(sentenceIndex, sentenceNumber, variantKind, tokenIndex, seekTime, effectiveShouldPlay)
                if wasPaused,
                   shouldPlay,
                   let token = tokenText(sentenceIndex: sentenceIndex, variantKind: variantKind, tokenIndex: tokenIndex) {
                    onLookupToken(sentenceIndex, variantKind, tokenIndex, token)
                }
            }
            let resolvedTrackFontScale = isTV ? {
                guard bubble != nil else { return trackFontScale }
                return max(trackFontScale * 0.85, 0.85)
            }() : (shouldAutoScaleTracks ? {
                let current = effectiveTrackFontScale == 0 ? trackFontScale : effectiveTrackFontScale
                return min(current, maxTrackFontScale)
            }() : trackFontScale)
            let resolvedLinguistFontScale: CGFloat = {
                guard isTV, bubble != nil else { return linguistFontScale }
                return max(linguistFontScale * 0.9, 0.9)
            }()
            let shouldReportTokenFrames = isPad || isPhone
            let baseTrackView = TextPlayerFrame(
                sentences: sentences,
                selection: selection,
                selectionRange: selectionRange,
                onTokenLookup: tokenLookupHandler,
                onTokenSeek: tokenSeekHandler,
                fontScale: resolvedTrackFontScale,
                playbackPrimaryKind: playbackPrimaryKind,
                visibleTracks: visibleTracks,
                onToggleTrack: onToggleTrack,
                onTokenFramesChange: shouldReportTokenFrames ? { tokenFrames = $0 } : nil,
                onTapExclusionFramesChange: shouldReportTokenFrames ? { tapExclusionFrames = $0 } : nil,
                shouldReportTokenFrames: shouldReportTokenFrames,
                isLoading: isTranscriptLoading,
                loadErrorMessage: transcriptLoadError,
                onRetryLoad: onRetryTranscriptLoad
            )
            let measuredTrackView = baseTrackView
                .background(GeometryReader { trackProxy in
                    Color.clear.preference(
                        key: InteractiveAutoScaleTrackHeightKey.self,
                        value: trackProxy.size.height
                    )
                })
            let trackView = measuredTrackView

            Group {
                #if os(tvOS)
                if iPadSplitDirection == .horizontal && bubble != nil {
                    // tvOS horizontal split layout: 30% bubble | 70% tracks
                    tvSplitLayout(
                        trackView: trackView,
                        bubble: bubble!,
                        resolvedLinguistFontScale: resolvedLinguistFontScale,
                        bubbleFocusEnabled: bubbleFocusEnabled,
                        availableWidth: proxy.size.width,
                        availableHeight: availableHeight
                    )
                } else {
                    // Default overlay layout: bubble overlays tracks from bottom
                    ZStack(alignment: .bottom) {
                        // Tracks layer (always visible, behind bubble)
                        // Allow focus when no bubble, or when bubble is pinned (to enable long press for header toggle)
                        let canFocusTracks = !isMenuVisible && (bubble == nil || iPadBubblePinned)
                        trackView
                            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
                            .contentShape(Rectangle())
                            .focusable(canFocusTracks)
                            .focused($focusedArea, equals: .transcript)
                            .focusEffectDisabled()
                            .onTapGesture(perform: handleTVOverlayTrackTap)
                            .onLongPressGesture(
                                minimumDuration: 0.6,
                                perform: handleTVTrackLongPress
                            )
                            .accessibilityAddTraits(.isButton)

                        // Bubble layer (overlays tracks from bottom)
                        if let bubble {
                            MyLinguistBubbleView(
                                bubble: bubble,
                                fontScale: resolvedLinguistFontScale,
                                canIncreaseFont: canIncreaseLinguistFont,
                                canDecreaseFont: canDecreaseLinguistFont,
                                lookupLanguage: lookupLanguage,
                                lookupLanguageOptions: lookupLanguageOptions,
                                onLookupLanguageChange: onLookupLanguageChange,
                                llmModel: llmModel,
                                llmModelOptions: llmModelOptions,
                                onLlmModelChange: onLlmModelChange,
                                ttsVoice: ttsVoice,
                                ttsVoiceOptions: ttsVoiceOptions,
                                onTtsVoiceChange: onTtsVoiceChange,
                                onIncreaseFont: onIncreaseLinguistFont,
                                onDecreaseFont: onDecreaseLinguistFont,
                                onClose: onCloseBubble,
                                isFocusEnabled: bubbleFocusEnabled,
                                focusBinding: $focusedArea,
                                availableHeight: availableHeight * 0.85,
                                onPreviousToken: onBubblePreviousToken,
                                onNextToken: onBubbleNextToken,
                                onToggleLayoutDirection: onToggleLayoutDirection,
                                isPinned: iPadBubblePinned,
                                onTogglePin: onToggleBubblePin,
                                onPlayFromNarration: onPlayFromNarration,
                                onReadAloud: onReadAloud,
                                onKeyboardPlayPause: onTogglePlayback,
                                onKeyboardLookup: onLookup
                            )
                            // Let bubble size itself based on content, up to 85% of screen
                            .frame(maxWidth: .infinity, maxHeight: availableHeight * 0.85, alignment: .bottom)
                            .padding(.horizontal, 24)
                            .padding(.bottom, 16)
                            .background(GeometryReader { bubbleProxy in
                                Color.clear.preference(
                                    key: InteractiveBubbleHeightKey.self,
                                    value: bubbleProxy.size.height
                                )
                            })
                        }
                    }
                }
                #else
                if isPhone {
                    phoneLayout(
                        trackView: trackView,
                        bubble: bubble,
                        resolvedLinguistFontScale: resolvedLinguistFontScale,
                        bubbleFocusEnabled: bubbleFocusEnabled,
                        availableHeight: availableHeight,
                        layoutSize: proxy.size
                    )
                    // Coordinate space is defined inside phoneLayout
                } else if isPad && bubble != nil {
                    // iPad with bubble: resizable split layout
                    iPadSplitLayout(
                        trackView: trackView,
                        bubble: bubble,
                        resolvedLinguistFontScale: resolvedLinguistFontScale,
                        bubbleFocusEnabled: bubbleFocusEnabled,
                        availableSize: proxy.size
                    )
                } else {
                    // iPad without bubble or other platforms
                    VStack(alignment: .leading, spacing: stackSpacing) {
                        playbackTrackView(trackView)
                    }
                    .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
                    .contentShape(Rectangle())
                    .focusable(!isMenuVisible)
                    .focused($focusedArea, equals: .transcript)
                    .focusEffectDisabled()
                    .coordinateSpace(name: TextPlayerTokenCoordinateSpace.name)
                    .gesture(swipeGesture)
                    #if os(iOS)
                    .simultaneousGesture(selectionDragGesture, including: .gesture)
                    .simultaneousGesture(backgroundPlaybackTapGesture, including: .all)
                    #endif
                    .highPriorityGesture(trackMagnifyGesture, including: .all)
                }
                #endif
            }
            .onPreferenceChange(InteractiveBubbleHeightKey.self, perform: handleBubbleHeightChange)
            .onPreferenceChange(InteractiveAutoScaleTrackHeightKey.self) { value in
                handleAutoScaleTrackHeightChange(
                    value,
                    shouldAutoScaleTracks: shouldAutoScaleTracks,
                    textHeightLimit: textHeightLimit
                )
            }
            .onPreferenceChange(InteractiveBubbleFrameKey.self, perform: handleBubbleFrameChange)
            .onChange(of: proxy.size) { _, newSize in
                handleLayoutSizeChange(
                    newSize,
                    shouldAutoScaleTracks: shouldAutoScaleTracks,
                    textHeightLimit: textHeightLimit
                )
            }
            .onChange(of: trackFontScale) { _, _ in
                handleTrackFontScaleChange(shouldAutoScaleTracks: shouldAutoScaleTracks)
            }
            .onChange(of: visibleTracks) { _, _ in
                handleVisibleTracksChange(shouldAutoScaleTracks: shouldAutoScaleTracks)
            }
            .onChange(of: sentenceSignature) { _, _ in
                handleSentenceSignatureChange(shouldAutoScaleTracks: shouldAutoScaleTracks)
            }
            .onChange(of: autoScaleEnabled) { _, enabled in
                handleAutoScaleEnabledChange(enabled)
            }
            .onChange(of: bubble) { oldBubble, newBubble in
                handleBubbleChange(
                    oldBubble: oldBubble,
                    newBubble: newBubble,
                    shouldAutoScaleTracks: shouldAutoScaleTracks,
                    textHeightLimit: textHeightLimit
                )
            }
            .onChange(of: audioCoordinator.isPlaying) { _, isPlaying in
                handleAudioPlayingChange(isPlaying)
            }
            .onDisappear(perform: handleTranscriptDisappear)
        }
    }

    private func tokenText(
        sentenceIndex: Int,
        variantKind: TextPlayerVariantKind,
        tokenIndex: Int
    ) -> String? {
        guard let sentence = sentences.first(where: { $0.index == sentenceIndex }),
              let variant = sentence.variants.first(where: { $0.kind == variantKind }),
              variant.tokens.indices.contains(tokenIndex) else {
            return nil
        }
        return variant.tokens[tokenIndex]
    }

    private func handleBubbleHeightChange(_ value: CGFloat) {
        guard !isPhone else { return }
        bubbleHeight = value
    }

    private func handleBubbleFrameChange(_ value: CGRect) {
        bubbleFrame = value
    }

    private func handleAudioPlayingChange(_ isPlaying: Bool) {
        guard isPlaying else { return }
        dragSelectionAnchor = nil
        dragLookupTask?.cancel()
        dragLookupTask = nil
    }

    private func handleTranscriptDisappear() {
        suppressPlaybackTask?.cancel()
        suppressPlaybackTask = nil
        autoScaleTask?.cancel()
        autoScaleTask = nil
        dragLookupTask?.cancel()
        dragLookupTask = nil
    }


    #if !os(tvOS)
    @ViewBuilder
    private func playbackTrackView<TrackContent: View>(_ trackView: TrackContent) -> some View {
        if isPad {
            trackView
                .contentShape(Rectangle())
        } else {
            trackView
                .contentShape(Rectangle())
                .simultaneousGesture(doubleTapGesture, including: .gesture)
        }
    }
    #endif

    var isPad: Bool {
        #if os(iOS)
        return UIDevice.current.userInterfaceIdiom == .pad
        #else
        return false
        #endif
    }

    var isTV: Bool {
        #if os(tvOS)
        return true
        #else
        return false
        #endif
    }

    var isPhone: Bool {
        #if os(iOS)
        return UIDevice.current.userInterfaceIdiom == .phone
        #else
        return false
        #endif
    }

    func isPortraitLayout(size: CGSize) -> Bool {
        #if os(iOS)
        guard isPhone else { return false }
        return size.height > size.width
        #else
        return false
        #endif
    }

}
