import SwiftUI
#if os(iOS) || os(tvOS)
import UIKit
#endif

// MARK: - Comparable Clamping Extension

private extension Comparable {
    func clamped(to range: ClosedRange<Self>) -> Self {
        min(max(self, range.lowerBound), range.upperBound)
    }
}

struct InteractiveBubbleHeightKey: PreferenceKey {
    static var defaultValue: CGFloat = 0

    static func reduce(value: inout CGFloat, nextValue: () -> CGFloat) {
        value = max(value, nextValue())
    }
}

struct InteractiveAutoScaleTrackHeightKey: PreferenceKey {
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
    let onSeekToken: (Int, Int?, TextPlayerVariantKind, Int, Double?) -> Void
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
    @State private var bubbleHeight: CGFloat = 0
    @State private var trackHeight: CGFloat = 0
    @State private var effectiveTrackFontScale: CGFloat = 0
    @State var suppressPlaybackToggle = false
    @State var suppressPlaybackTask: Task<Void, Never>?
    @State private var autoScaleNeedsUpdate = false
    @State private var autoScaleTask: Task<Void, Never>?
    @State private var lastMeasuredTrackHeight: CGFloat = 0
    @State private var lastAvailableTrackHeight: CGFloat = 0
    @State private var lastLayoutSize: CGSize = .zero
    @State var tokenFrames: [TextPlayerTokenFrame] = []
    @State var tapExclusionFrames: [CGRect] = []
    @State var bubbleFrame: CGRect = .zero
    @State var dragSelectionAnchor: TextPlayerWordSelection?
    @State var dragLookupTask: Task<Void, Never>?
    let dragLookupDelayNanos: UInt64 = 350_000_000
    private var autoScaleHeightTolerance: CGFloat {
        isPhone ? 8 : 4
    }

    var body: some View {
        transcriptContent
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: isTV ? .top : .center)
            .onChange(of: audioCoordinator.duration) { _, newValue in
                viewModel.recordAudioDuration(newValue, for: audioCoordinator.activeURL)
            }
            .onChange(of: audioCoordinator.activeURL) { _, _ in
                viewModel.recordAudioDuration(audioCoordinator.duration, for: audioCoordinator.activeURL)
            }
            .onAppear {
                viewModel.recordAudioDuration(audioCoordinator.duration, for: audioCoordinator.activeURL)
            }
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
            let tvBubbleHeight = tvBubbleSplit ? max(bubbleReserve - stackSpacing, 0) : 0
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
            let tokenSeekHandler: (Int, Int?, TextPlayerVariantKind, Int, Double?) -> Void = {
                sentenceIndex, sentenceNumber, variantKind, tokenIndex, seekTime in
                // When paused, single tap triggers lookup — suppress background gesture
                // to prevent it from closing the bubble
                if !audioCoordinator.isPlaying {
                    suppressPlaybackTask?.cancel()
                    suppressPlaybackToggle = true
                    suppressPlaybackTask = Task { @MainActor in
                        try? await Task.sleep(nanoseconds: 350_000_000)
                        suppressPlaybackToggle = false
                    }
                }
                onSeekToken(sentenceIndex, sentenceNumber, variantKind, tokenIndex, seekTime)
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
                isLoading: isTranscriptLoading
            )
            let measuredTrackView = baseTrackView
                .background(GeometryReader { trackProxy in
                    Color.clear.preference(
                        key: InteractiveAutoScaleTrackHeightKey.self,
                        value: trackProxy.size.height
                    )
                })
            let trackView: AnyView = AnyView(measuredTrackView)

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
                            .onTapGesture {
                                if bubble != nil {
                                    // Respect pin state - don't close if pinned
                                    if !iPadBubblePinned {
                                        onCloseBubble()
                                    }
                                } else {
                                    onLookup()
                                }
                            }
                            .onLongPressGesture(minimumDuration: 0.6) {
                                onToggleHeader?()
                            }
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
                                onPlayFromNarration: onPlayFromNarration
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
                    let trackViewWithPlayback: AnyView = {
                        if isPad {
                            return AnyView(trackView.contentShape(Rectangle()))
                        }
                        return AnyView(
                            trackView
                                .contentShape(Rectangle())
                                .simultaneousGesture(doubleTapGesture, including: .gesture)
                        )
                    }()
                    VStack(alignment: .leading, spacing: stackSpacing) {
                        trackViewWithPlayback
                    }
                    .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
                    .contentShape(Rectangle())
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
            .onPreferenceChange(InteractiveBubbleHeightKey.self) { value in
                if !isPhone {
                    bubbleHeight = value
                }
            }
            .onPreferenceChange(InteractiveAutoScaleTrackHeightKey.self) { value in
                guard shouldAutoScaleTracks else { return }
                trackHeight = value
                lastMeasuredTrackHeight = value
                lastAvailableTrackHeight = textHeightLimit
                if effectiveTrackFontScale == 0 {
                    autoScaleNeedsUpdate = true
                }
                applyAutoScaleIfNeeded()
            }
            .onPreferenceChange(InteractiveBubbleFrameKey.self) { value in
                bubbleFrame = value
            }
            .onChange(of: proxy.size) { _, newSize in
                guard shouldAutoScaleTracks else { return }
                guard newSize != lastLayoutSize else { return }
                lastLayoutSize = newSize
                lastAvailableTrackHeight = textHeightLimit
                requestAutoScaleUpdate(delay: 250_000_000)
            }
            .onChange(of: trackFontScale) { _, _ in
                guard shouldAutoScaleTracks else { return }
                effectiveTrackFontScale = trackFontScale
                requestAutoScaleUpdate()
            }
            .onChange(of: visibleTracks) { _, _ in
                guard shouldAutoScaleTracks else { return }
                autoScaleNeedsUpdate = true
                requestAutoScaleUpdate()
            }
            .onChange(of: sentenceSignature) { _, _ in
                guard shouldAutoScaleTracks else { return }
                autoScaleNeedsUpdate = true
                requestAutoScaleUpdate()
            }
            .onChange(of: autoScaleEnabled) { _, enabled in
                effectiveTrackFontScale = trackFontScale
                autoScaleTask?.cancel()
                autoScaleTask = nil
                autoScaleNeedsUpdate = enabled
                if enabled {
                    requestAutoScaleUpdate()
                }
            }
            .onChange(of: bubble) { oldBubble, newBubble in
                // Recalculate auto-scale when bubble appears/disappears
                // as the available track height changes
                guard shouldAutoScaleTracks, isPhone else { return }
                let bubbleWasOpen = oldBubble != nil
                let bubbleIsOpen = newBubble != nil
                if bubbleWasOpen != bubbleIsOpen {
                    lastAvailableTrackHeight = textHeightLimit
                    autoScaleNeedsUpdate = true
                    requestAutoScaleUpdate(delay: 100_000_000)
                }
            }
            .onChange(of: audioCoordinator.isPlaying) { _, isPlaying in
                if isPlaying {
                    dragSelectionAnchor = nil
                    dragLookupTask?.cancel()
                    dragLookupTask = nil
                }
            }
            .onDisappear {
                suppressPlaybackTask?.cancel()
                suppressPlaybackTask = nil
                autoScaleTask?.cancel()
                autoScaleTask = nil
                dragLookupTask?.cancel()
                dragLookupTask = nil
            }
        }
    }



    private func updateEffectiveTrackFontScale(measuredHeight: CGFloat, availableHeight: CGFloat) {
        guard !isTV else { return }
        guard measuredHeight > 0, availableHeight > 0 else {
            if effectiveTrackFontScale != trackFontScale {
                effectiveTrackFontScale = trackFontScale
            }
            return
        }
        let currentScale = effectiveTrackFontScale == 0 ? trackFontScale : effectiveTrackFontScale
        let fitHeight = max(availableHeight - autoScaleHeightTolerance, 0)
        let ratio = fitHeight / measuredHeight
        let proposed = currentScale * ratio
        let clamped = max(autoScaleFloor, min(maxTrackFontScale, proposed))
        if abs(clamped - currentScale) > 0.02 {
            effectiveTrackFontScale = clamped
        }
    }

    private func requestAutoScaleUpdate(delay: UInt64 = 120_000_000) {
        guard autoScaleEnabled, !isTV else { return }
        autoScaleNeedsUpdate = true
        autoScaleTask?.cancel()
        autoScaleTask = Task { @MainActor in
            try? await Task.sleep(nanoseconds: delay)
            applyAutoScaleIfNeeded()
        }
    }

    private func applyAutoScaleIfNeeded() {
        guard autoScaleNeedsUpdate else { return }
        guard lastMeasuredTrackHeight > 0, lastAvailableTrackHeight > 0 else { return }
        updateEffectiveTrackFontScale(
            measuredHeight: lastMeasuredTrackHeight,
            availableHeight: lastAvailableTrackHeight
        )
        autoScaleNeedsUpdate = false
    }

    func updateSelectionRange(at location: CGPoint) {
        guard let anchor = dragSelectionAnchor else { return }
        guard let token = nearestTokenFrame(at: location) else { return }
        let selection = TextPlayerWordSelection(
            sentenceIndex: token.sentenceIndex,
            variantKind: token.variantKind,
            tokenIndex: token.tokenIndex
        )
        guard anchor.sentenceIndex == selection.sentenceIndex,
              anchor.variantKind == selection.variantKind else {
            return
        }
        let range = TextPlayerWordSelectionRange(
            sentenceIndex: anchor.sentenceIndex,
            variantKind: anchor.variantKind,
            anchorIndex: anchor.tokenIndex,
            focusIndex: selection.tokenIndex
        )
        onUpdateSelectionRange(range, selection)
        scheduleDragLookup()
    }

    func nearestTokenFrame(at location: CGPoint) -> TextPlayerTokenFrame? {
        let candidates: [TextPlayerTokenFrame]
        if let anchor = dragSelectionAnchor {
            candidates = tokenFrames.filter { frame in
                frame.sentenceIndex == anchor.sentenceIndex && frame.variantKind == anchor.variantKind
            }
        } else {
            candidates = tokenFrames
        }
        guard !candidates.isEmpty else { return nil }
        if let exact = candidates.first(where: { $0.frame.contains(location) }) {
            return exact
        }
        let sorted = candidates.sorted { lhs, rhs in
            let lhsCenter = CGPoint(x: lhs.frame.midX, y: lhs.frame.midY)
            let rhsCenter = CGPoint(x: rhs.frame.midX, y: rhs.frame.midY)
            let lhsDistance = hypot(lhsCenter.x - location.x, lhsCenter.y - location.y)
            let rhsDistance = hypot(rhsCenter.x - location.x, rhsCenter.y - location.y)
            return lhsDistance < rhsDistance
        }
        return sorted.first
    }

    func tokenFrameContaining(_ location: CGPoint) -> TextPlayerTokenFrame? {
        let candidates = tokenFrames
        guard !candidates.isEmpty else { return nil }
        if let exact = candidates.first(where: { $0.frame.contains(location) }) {
            return exact
        }
        return nil
    }

    /// Find the nearest token frame within a maximum distance threshold.
    /// Used for tap-to-lookup to be more forgiving than exact hit testing.
    func nearestTokenFrameForTap(at location: CGPoint, maxDistance: CGFloat = 20) -> TextPlayerTokenFrame? {
        let candidates = tokenFrames
        guard !candidates.isEmpty else { return nil }
        // First try exact hit
        if let exact = candidates.first(where: { $0.frame.contains(location) }) {
            return exact
        }
        // Find nearest within threshold
        var bestMatch: TextPlayerTokenFrame?
        var bestDistance: CGFloat = .greatestFiniteMagnitude
        for candidate in candidates {
            let center = CGPoint(x: candidate.frame.midX, y: candidate.frame.midY)
            let distance = hypot(center.x - location.x, center.y - location.y)
            if distance < bestDistance && distance <= maxDistance {
                bestDistance = distance
                bestMatch = candidate
            }
        }
        return bestMatch
    }

    func scheduleDragLookup() {
        dragLookupTask?.cancel()
        dragLookupTask = Task { @MainActor in
            try? await Task.sleep(nanoseconds: dragLookupDelayNanos)
            guard !Task.isCancelled else { return }
            guard !audioCoordinator.isPlaying else { return }
            onLookup()
        }
    }

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

    private var autoScaleFloor: CGFloat {
        guard isPhone else { return minTrackFontScale }
        return max(0.75, minTrackFontScale * 0.75)
    }

    private var sentenceSignature: String {
        sentences.map(\.id).joined(separator: "|")
    }

    #if os(tvOS)
    // MARK: - tvOS Split Layout

    /// tvOS horizontal split layout: 30% bubble on left, 70% tracks on right
    @ViewBuilder
    private func tvSplitLayout(
        trackView: AnyView,
        bubble: MyLinguistBubbleState,
        resolvedLinguistFontScale: CGFloat,
        bubbleFocusEnabled: Bool,
        availableWidth: CGFloat,
        availableHeight: CGFloat
    ) -> some View {
        let bubbleRatio: CGFloat = 0.30
        let trackRatio: CGFloat = 0.70
        let spacing: CGFloat = 20
        let bubbleWidth = max(0, availableWidth * bubbleRatio - spacing / 2)
        let trackWidth = max(0, availableWidth * trackRatio - spacing / 2)

        HStack(spacing: spacing) {
            // Bubble area (left side, 30%)
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
                availableHeight: availableHeight,
                onPreviousToken: onBubblePreviousToken,
                onNextToken: onBubbleNextToken,
                onToggleLayoutDirection: onToggleLayoutDirection,
                isPinned: iPadBubblePinned,
                onTogglePin: onToggleBubblePin,
                isSplitMode: true,
                onPlayFromNarration: onPlayFromNarration
            )
            .frame(width: bubbleWidth, height: availableHeight)
            .clipped()

            // Tracks area (right side, 70%)
            trackView
                .frame(width: trackWidth, height: availableHeight, alignment: .top)
                .clipped()
                .contentShape(Rectangle())
                .focusable(!isMenuVisible)
                .focused($focusedArea, equals: .transcript)
                .focusEffectDisabled()
                .onTapGesture {
                    // Respect pin state on tvOS - don't close if pinned
                    if !iPadBubblePinned {
                        onCloseBubble()
                    }
                }
                .onLongPressGesture(minimumDuration: 0.6) {
                    onToggleHeader?()
                }
                .accessibilityAddTraits(.isButton)
        }
        .frame(width: availableWidth, height: availableHeight)
        .padding(.leading, 12)
        .padding(.trailing, 24)
    }
    #endif


}

