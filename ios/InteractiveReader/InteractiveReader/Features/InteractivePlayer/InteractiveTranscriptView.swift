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
    @State private var trackMagnifyStartScale: CGFloat?
    @State private var bubbleMagnifyStartScale: CGFloat?
    @State private var isDraggingDivider = false
    @State private var dividerDragStartRatio: CGFloat = 0
    /// Track previous split ratio for calculating font scale changes
    @State private var previousSplitRatio: CGFloat = 0.5
    #endif
    @State private var bubbleHeight: CGFloat = 0
    @State private var trackHeight: CGFloat = 0
    @State private var effectiveTrackFontScale: CGFloat = 0
    @State private var suppressPlaybackToggle = false
    @State private var suppressPlaybackTask: Task<Void, Never>?
    @State private var autoScaleNeedsUpdate = false
    @State private var autoScaleTask: Task<Void, Never>?
    @State private var lastMeasuredTrackHeight: CGFloat = 0
    @State private var lastAvailableTrackHeight: CGFloat = 0
    @State private var lastLayoutSize: CGSize = .zero
    @State private var tokenFrames: [TextPlayerTokenFrame] = []
    @State private var tapExclusionFrames: [CGRect] = []
    @State private var bubbleFrame: CGRect = .zero
    @State private var dragSelectionAnchor: TextPlayerWordSelection?
    @State private var dragLookupTask: Task<Void, Never>?
    private let dragLookupDelayNanos: UInt64 = 350_000_000
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
                onTokenSeek: onSeekToken,
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

    #if !os(tvOS)
    private var swipeGesture: some Gesture {
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
    #endif

    #if os(iOS)
    private var selectionDragGesture: some Gesture {
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
    private var doubleTapGesture: some Gesture {
        TapGesture(count: 2)
            .onEnded {
                guard !suppressPlaybackToggle else { return }
                onTogglePlayback()
            }
    }
    #endif

    #if os(iOS)
    private var playbackSingleTapGesture: some Gesture {
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

    private var backgroundPlaybackTapGesture: some Gesture {
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
                    onCloseBubble()
                    if !audioCoordinator.isPlaying {
                        onTogglePlayback()
                    }
                } else {
                    onTogglePlayback()
                }
            }
    }
    #endif

    #if os(iOS)
    private var trackMagnifyGesture: some Gesture {
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

    private var bubbleMagnifyGesture: some Gesture {
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

    private func updateSelectionRange(at location: CGPoint) {
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

    private func nearestTokenFrame(at location: CGPoint) -> TextPlayerTokenFrame? {
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

    private func tokenFrameContaining(_ location: CGPoint) -> TextPlayerTokenFrame? {
        let candidates = tokenFrames
        guard !candidates.isEmpty else { return nil }
        if let exact = candidates.first(where: { $0.frame.contains(location) }) {
            return exact
        }
        return nil
    }

    /// Find the nearest token frame within a maximum distance threshold.
    /// Used for tap-to-lookup to be more forgiving than exact hit testing.
    private func nearestTokenFrameForTap(at location: CGPoint, maxDistance: CGFloat = 20) -> TextPlayerTokenFrame? {
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

    private func scheduleDragLookup() {
        dragLookupTask?.cancel()
        dragLookupTask = Task { @MainActor in
            try? await Task.sleep(nanoseconds: dragLookupDelayNanos)
            guard !Task.isCancelled else { return }
            guard !audioCoordinator.isPlaying else { return }
            onLookup()
        }
    }

    private var isPad: Bool {
        #if os(iOS)
        return UIDevice.current.userInterfaceIdiom == .pad
        #else
        return false
        #endif
    }

    private var isTV: Bool {
        #if os(tvOS)
        return true
        #else
        return false
        #endif
    }

    private var isPhone: Bool {
        #if os(iOS)
        return UIDevice.current.userInterfaceIdiom == .phone
        #else
        return false
        #endif
    }

    private func isPortraitLayout(size: CGSize) -> Bool {
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

    #if os(iOS)
    // MARK: - iPad Split Layout

    /// Minimum split ratio (tracks get at least 20% in vertical, bubble gets at least 20% in horizontal)
    private let iPadMinSplitRatio: CGFloat = 0.20
    /// Maximum split ratio
    private let iPadMaxSplitRatio: CGFloat = 0.80
    /// Divider thickness
    private let iPadDividerThickness: CGFloat = 12
    /// Divider handle size
    private let iPadDividerHandleWidth: CGFloat = 40
    private let iPadDividerHandleHeight: CGFloat = 4

    @ViewBuilder
    private func iPadSplitLayout(
        trackView: AnyView,
        bubble: MyLinguistBubbleState?,
        resolvedLinguistFontScale: CGFloat,
        bubbleFocusEnabled: Bool,
        availableSize: CGSize
    ) -> some View {
        let trackViewWithPlayback = AnyView(trackView.contentShape(Rectangle()))

        Group {
            if iPadSplitDirection == .vertical {
                iPadVerticalSplitLayout(
                    trackViewWithPlayback: trackViewWithPlayback,
                    bubble: bubble,
                    resolvedLinguistFontScale: resolvedLinguistFontScale,
                    bubbleFocusEnabled: bubbleFocusEnabled,
                    availableSize: availableSize
                )
            } else {
                iPadHorizontalSplitLayout(
                    trackViewWithPlayback: trackViewWithPlayback,
                    bubble: bubble,
                    resolvedLinguistFontScale: resolvedLinguistFontScale,
                    bubbleFocusEnabled: bubbleFocusEnabled,
                    availableSize: availableSize
                )
            }
        }
        .coordinateSpace(name: TextPlayerTokenCoordinateSpace.name)
        .onAppear {
            // Initialize previous ratio when layout appears
            previousSplitRatio = iPadSplitRatio
        }
        .onChange(of: iPadSplitRatio) { oldRatio, newRatio in
            // Dynamically adjust font scales based on split ratio changes
            // In vertical: ratio = tracks height percentage, so increasing ratio = more track space
            // In horizontal: ratio = bubble width percentage, so increasing ratio = more bubble space
            adjustFontScalesForSplitChange(
                oldRatio: oldRatio,
                newRatio: newRatio,
                isVertical: iPadSplitDirection == .vertical
            )
        }
        .onChange(of: iPadSplitDirection) { _, _ in
            // Reset previous ratio when direction changes
            previousSplitRatio = iPadSplitRatio
        }
    }

    /// Adjust track and linguist font scales based on split ratio changes
    private func adjustFontScalesForSplitChange(
        oldRatio: CGFloat,
        newRatio: CGFloat,
        isVertical: Bool
    ) {
        guard abs(newRatio - oldRatio) > 0.001 else { return }

        // Calculate how each area's size changed
        // In vertical mode:
        //   - ratio = track area percentage (0.5 means tracks get 50% of height)
        //   - track area grows when ratio increases
        //   - bubble area shrinks when ratio increases (1 - ratio)
        // In horizontal mode:
        //   - ratio = bubble area percentage (0.5 means bubble gets 50% of width)
        //   - bubble area grows when ratio increases
        //   - track area shrinks when ratio increases (1 - ratio)

        let trackRatioOld = isVertical ? oldRatio : (1 - oldRatio)
        let trackRatioNew = isVertical ? newRatio : (1 - newRatio)
        let bubbleRatioOld = isVertical ? (1 - oldRatio) : oldRatio
        let bubbleRatioNew = isVertical ? (1 - newRatio) : newRatio

        // Calculate scaling factors: how much did each area grow/shrink?
        // We want fonts to scale proportionally to fill the new space
        let trackScaleFactor = trackRatioOld > 0.001 ? trackRatioNew / trackRatioOld : 1.0
        let bubbleScaleFactor = bubbleRatioOld > 0.001 ? bubbleRatioNew / bubbleRatioOld : 1.0

        // Apply scaling to track font
        // Use square root for more gentle scaling (full linear feels too aggressive)
        let trackAdjustment = sqrt(trackScaleFactor)
        let newTrackScale = trackFontScale * trackAdjustment
        let clampedTrackScale = max(minTrackFontScale, min(maxTrackFontScale, newTrackScale))
        if abs(clampedTrackScale - trackFontScale) > 0.01 {
            onSetTrackFontScale(clampedTrackScale)
        }

        // Apply scaling to linguist font
        // linguistFontScale bounds come from the parent view
        let linguistMin: CGFloat = 0.8
        let linguistMax: CGFloat = 3.2  // iPad max from InteractivePlayerView
        let bubbleAdjustment = sqrt(bubbleScaleFactor)
        let newLinguistScale = linguistFontScale * bubbleAdjustment
        let clampedLinguistScale = max(linguistMin, min(linguistMax, newLinguistScale))
        if abs(clampedLinguistScale - linguistFontScale) > 0.01 {
            onSetLinguistFontScale(clampedLinguistScale)
        }

        previousSplitRatio = newRatio
    }

    @ViewBuilder
    private func iPadVerticalSplitLayout(
        trackViewWithPlayback: AnyView,
        bubble: MyLinguistBubbleState?,
        resolvedLinguistFontScale: CGFloat,
        bubbleFocusEnabled: Bool,
        availableSize: CGSize
    ) -> some View {
        let totalHeight = availableSize.height
        // Calculate exact heights for each section
        let trackHeight = max(0, totalHeight * iPadSplitRatio - iPadDividerThickness / 2)
        let bubbleHeight = max(0, totalHeight * (1 - iPadSplitRatio) - iPadDividerThickness / 2)
        let _ = print("[iPadVerticalSplit] ratio=\(String(format: "%.3f", iPadSplitRatio)), totalHeight=\(String(format: "%.0f", totalHeight)), trackHeight=\(String(format: "%.0f", trackHeight)), bubbleHeight=\(String(format: "%.0f", bubbleHeight))")

        VStack(spacing: 0) {
            // Tracks area - fixed height, clipped to bounds
            trackViewWithPlayback
                .frame(maxWidth: .infinity, alignment: .top)
                .frame(height: trackHeight)
                .clipped()
                .contentShape(Rectangle())
                .simultaneousGesture(swipeGesture, including: .all)
                .simultaneousGesture(selectionDragGesture, including: .gesture)
                .simultaneousGesture(backgroundPlaybackTapGesture, including: .all)
                .highPriorityGesture(trackMagnifyGesture, including: .all)

            // Divider
            iPadDivider(isVertical: true, availableSize: availableSize)

            // Bubble area - fixed height, clipped to bounds
            if let bubble {
                iPadBubbleContent(
                    bubble: bubble,
                    resolvedLinguistFontScale: resolvedLinguistFontScale,
                    bubbleFocusEnabled: bubbleFocusEnabled,
                    maxHeight: bubbleHeight,
                    fillWidth: true
                )
                .frame(height: bubbleHeight)
                .clipped()
            }
        }
        .frame(width: availableSize.width, height: availableSize.height)
    }

    @ViewBuilder
    private func iPadHorizontalSplitLayout(
        trackViewWithPlayback: AnyView,
        bubble: MyLinguistBubbleState?,
        resolvedLinguistFontScale: CGFloat,
        bubbleFocusEnabled: Bool,
        availableSize: CGSize
    ) -> some View {
        let totalWidth = availableSize.width
        // Calculate exact widths for each section
        let bubbleWidth = max(0, totalWidth * iPadSplitRatio - iPadDividerThickness / 2)
        let trackWidth = max(0, totalWidth * (1 - iPadSplitRatio) - iPadDividerThickness / 2)
        let _ = print("[iPadHorizontalSplit] ratio=\(String(format: "%.3f", iPadSplitRatio)), totalWidth=\(String(format: "%.0f", totalWidth)), bubbleWidth=\(String(format: "%.0f", bubbleWidth)), trackWidth=\(String(format: "%.0f", trackWidth))")

        HStack(spacing: 0) {
            // Bubble area (left side, like iPhone landscape) - fixed width, clipped
            if let bubble {
                iPadBubbleContent(
                    bubble: bubble,
                    resolvedLinguistFontScale: resolvedLinguistFontScale,
                    bubbleFocusEnabled: bubbleFocusEnabled,
                    maxHeight: availableSize.height,
                    fillWidth: false
                )
                .frame(width: bubbleWidth, height: availableSize.height)
                .clipped()
            }

            // Divider
            iPadDivider(isVertical: false, availableSize: availableSize)

            // Tracks area (right side) - fixed width, clipped
            trackViewWithPlayback
                .frame(maxHeight: .infinity, alignment: .center)
                .frame(width: trackWidth)
                .clipped()
                .contentShape(Rectangle())
                .simultaneousGesture(swipeGesture, including: .all)
                .simultaneousGesture(selectionDragGesture, including: .gesture)
                .simultaneousGesture(backgroundPlaybackTapGesture, including: .all)
                .highPriorityGesture(trackMagnifyGesture, including: .all)
        }
        .padding(.leading, 24) // Extra left padding to avoid content clipping at left edge
        .frame(width: availableSize.width, height: availableSize.height)
    }

    @ViewBuilder
    private func iPadDivider(isVertical: Bool, availableSize: CGSize) -> some View {
        let dividerColor = Color.white.opacity(isDraggingDivider ? 0.4 : 0.2)
        let handleColor = Color.white.opacity(isDraggingDivider ? 0.7 : 0.5)

        Group {
            if isVertical {
                // Horizontal divider (for vertical split)
                ZStack {
                    Rectangle()
                        .fill(dividerColor)
                        .frame(height: 1)
                    // Handle
                    RoundedRectangle(cornerRadius: iPadDividerHandleHeight / 2)
                        .fill(handleColor)
                        .frame(width: iPadDividerHandleWidth, height: iPadDividerHandleHeight)
                }
                .frame(height: iPadDividerThickness)
                .contentShape(Rectangle())
                .gesture(
                    DragGesture(minimumDistance: 1)
                        .onChanged { value in
                            if !isDraggingDivider {
                                isDraggingDivider = true
                                dividerDragStartRatio = iPadSplitRatio
                                print("[SplitDivider] Drag started, startRatio=\(dividerDragStartRatio)")
                            }
                            let delta = value.translation.height / availableSize.height
                            let newRatio = (dividerDragStartRatio + delta)
                                .clamped(to: iPadMinSplitRatio...iPadMaxSplitRatio)
                            iPadSplitRatio = newRatio
                            print("[SplitDivider] delta=\(String(format: "%.3f", delta)), newRatio=\(String(format: "%.3f", newRatio)), availableHeight=\(String(format: "%.0f", availableSize.height))")
                        }
                        .onEnded { _ in
                            isDraggingDivider = false
                            print("[SplitDivider] Drag ended, finalRatio=\(String(format: "%.3f", iPadSplitRatio))")
                        }
                )
            } else {
                // Vertical divider (for horizontal split)
                ZStack {
                    Rectangle()
                        .fill(dividerColor)
                        .frame(width: 1)
                    // Handle
                    RoundedRectangle(cornerRadius: iPadDividerHandleHeight / 2)
                        .fill(handleColor)
                        .frame(width: iPadDividerHandleHeight, height: iPadDividerHandleWidth)
                }
                .frame(width: iPadDividerThickness)
                .contentShape(Rectangle())
                .gesture(
                    DragGesture(minimumDistance: 1)
                        .onChanged { value in
                            if !isDraggingDivider {
                                isDraggingDivider = true
                                dividerDragStartRatio = iPadSplitRatio
                            }
                            let delta = value.translation.width / availableSize.width
                            let newRatio = (dividerDragStartRatio + delta)
                                .clamped(to: iPadMinSplitRatio...iPadMaxSplitRatio)
                            iPadSplitRatio = newRatio
                        }
                        .onEnded { _ in
                            isDraggingDivider = false
                        }
                )
            }
        }
    }

    @ViewBuilder
    private func iPadBubbleContent(
        bubble: MyLinguistBubbleState,
        resolvedLinguistFontScale: CGFloat,
        bubbleFocusEnabled: Bool,
        maxHeight: CGFloat,
        fillWidth: Bool
    ) -> some View {
        ZStack(alignment: .top) {
            // Tap to dismiss area
            Color.clear
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                .contentShape(Rectangle())
                .onTapGesture {
                    onCloseBubble()
                    if !audioCoordinator.isPlaying {
                        onTogglePlayback()
                    }
                }

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
                fillWidth: fillWidth,
                maxContentHeight: max(maxHeight - 120, 80),
                onPreviousToken: onBubblePreviousToken,
                onNextToken: onBubbleNextToken,
                onToggleLayoutDirection: onToggleLayoutDirection,
                isPinned: iPadBubblePinned,
                onTogglePin: onToggleBubblePin,
                onPlayFromNarration: onPlayFromNarration,
                keyboardNavigator: bubbleKeyboardNavigator
            )
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
            .simultaneousGesture(bubbleMagnifyGesture, including: .all)
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 8)
        .contentShape(Rectangle())
        // Consume taps on bubble content
        .onTapGesture { /* consume tap */ }
        .background(GeometryReader { bubbleProxy in
            Color.clear.preference(
                key: InteractiveBubbleFrameKey.self,
                value: bubbleProxy.frame(in: .named(TextPlayerTokenCoordinateSpace.name))
            )
        })
    }
    #endif

    // MARK: - Phone Layout

    #if os(iOS)
    @ViewBuilder
    private func phoneLayout(
        trackView: AnyView,
        bubble: MyLinguistBubbleState?,
        resolvedLinguistFontScale: CGFloat,
        bubbleFocusEnabled: Bool,
        availableHeight: CGFloat,
        layoutSize: CGSize
    ) -> some View {
        let trackViewWithPlayback = AnyView(
            trackView
                .contentShape(Rectangle())
        )
        let isPortrait = isPortraitLayout(size: layoutSize)

        if bubble != nil {
            // iPhone with bubble: optimized split layout
            // Use stable ID to prevent view recreation when bubble content changes
            if isPortrait {
                // Portrait: tracks in upper half, bubble in lower half
                phonePortraitBubbleLayout(
                    trackViewWithPlayback: trackViewWithPlayback,
                    bubble: bubble,
                    resolvedLinguistFontScale: resolvedLinguistFontScale,
                    bubbleFocusEnabled: bubbleFocusEnabled,
                    availableHeight: availableHeight
                )
                .id("phone-portrait-bubble")
            } else {
                // Landscape: bubble on left, tracks on right
                phoneLandscapeBubbleLayout(
                    trackViewWithPlayback: trackViewWithPlayback,
                    bubble: bubble,
                    resolvedLinguistFontScale: resolvedLinguistFontScale,
                    bubbleFocusEnabled: bubbleFocusEnabled,
                    layoutWidth: layoutSize.width
                )
                .id("phone-landscape-bubble")
            }
        } else {
            // No bubble: original centered layout
            VStack {
                Spacer(minLength: 0)
                trackViewWithPlayback
                    .padding(.horizontal, 12)
                Spacer(minLength: 0)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .contentShape(Rectangle())
            .coordinateSpace(name: TextPlayerTokenCoordinateSpace.name)
            .simultaneousGesture(swipeGesture, including: .all)
            .simultaneousGesture(selectionDragGesture, including: .gesture)
            .simultaneousGesture(backgroundPlaybackTapGesture, including: .all)
            .highPriorityGesture(trackMagnifyGesture, including: .all)
        }
    }

    @ViewBuilder
    private func phonePortraitBubbleLayout(
        trackViewWithPlayback: AnyView,
        bubble: MyLinguistBubbleState?,
        resolvedLinguistFontScale: CGFloat,
        bubbleFocusEnabled: Bool,
        availableHeight: CGFloat
    ) -> some View {
        let upperHalfHeight = availableHeight * 0.50
        let lowerHalfHeight = availableHeight * 0.50

        VStack(spacing: 0) {
            // Upper half: tracks - use fixed frame with center alignment to prevent layout jumps
            trackViewWithPlayback
                .padding(.horizontal, 12)
                .frame(maxWidth: .infinity, maxHeight: upperHalfHeight, alignment: .center)
                .contentShape(Rectangle())
                .simultaneousGesture(swipeGesture, including: .all)
                .simultaneousGesture(selectionDragGesture, including: .gesture)
                .simultaneousGesture(phoneBubbleOpenBackgroundTapGesture, including: .all)
                .highPriorityGesture(trackMagnifyGesture, including: .all)

            // Lower half: bubble
            // Use bubble! since we know it's non-nil (this layout is only used when bubble exists)
            // Avoiding `if let` prevents SwiftUI from treating content changes as structural changes
            ZStack(alignment: .top) {
                // Tap to dismiss area
                Color.clear
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                    .contentShape(Rectangle())
                    .onTapGesture {
                        onCloseBubble()
                        if !audioCoordinator.isPlaying {
                            onTogglePlayback()
                        }
                    }

                // Use GeometryReader to get available height and pass to bubble
                GeometryReader { bubbleGeo in
                    let contentHeight = max(bubbleGeo.size.height - 60, 80)
                    MyLinguistBubbleView(
                        bubble: bubble!,
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
                        useCompactLayout: false,
                        fillWidth: true,
                        hideTitle: true,
                        edgeToEdgeStyle: false,
                        maxContentHeight: contentHeight,
                        onPreviousToken: onBubblePreviousToken,
                        onNextToken: onBubbleNextToken,
                        onPlayFromNarration: onPlayFromNarration,
                        keyboardNavigator: bubbleKeyboardNavigator
                    )
                    .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
                    .clipped()
                    .simultaneousGesture(bubbleMagnifyGesture, including: .all)
                }
                .padding(.horizontal, 12)
                .padding(.bottom, 8)
                .contentShape(Rectangle())
                // Consume taps on bubble content to prevent them from reaching the dismiss area
                .onTapGesture { /* consume tap */ }
                .background(GeometryReader { bubbleProxy in
                    Color.clear.preference(
                        key: InteractiveBubbleFrameKey.self,
                        value: bubbleProxy.frame(in: .named(TextPlayerTokenCoordinateSpace.name))
                    )
                })
            }
            .frame(maxWidth: .infinity, maxHeight: lowerHalfHeight)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .coordinateSpace(name: TextPlayerTokenCoordinateSpace.name)
    }

    @ViewBuilder
    private func phoneLandscapeBubbleLayout(
        trackViewWithPlayback: AnyView,
        bubble: MyLinguistBubbleState?,
        resolvedLinguistFontScale: CGFloat,
        bubbleFocusEnabled: Bool,
        layoutWidth: CGFloat
    ) -> some View {
        let leftWidth = layoutWidth * 0.45
        let rightWidth = layoutWidth * 0.55

        HStack(spacing: 0) {
            // Left side: bubble
            ZStack(alignment: .topLeading) {
                // Tap to dismiss area
                Color.clear
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                    .contentShape(Rectangle())
                    .onTapGesture {
                        onCloseBubble()
                        if !audioCoordinator.isPlaying {
                            onTogglePlayback()
                        }
                    }

                // Use bubble! since we know it's non-nil (this layout is only used when bubble exists)
                // Avoiding `if let` prevents SwiftUI from treating content changes as structural changes
                // Use GeometryReader to get available height and pass to bubble
                GeometryReader { bubbleGeo in
                    let contentHeight = max(bubbleGeo.size.height - 100, 80)
                    MyLinguistBubbleView(
                        bubble: bubble!,
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
                        useCompactLayout: false,
                        fillWidth: true,
                        hideTitle: true,
                        edgeToEdgeStyle: false,
                        maxContentHeight: contentHeight,
                        onPreviousToken: onBubblePreviousToken,
                        onNextToken: onBubbleNextToken,
                        onPlayFromNarration: onPlayFromNarration,
                        keyboardNavigator: bubbleKeyboardNavigator
                    )
                    .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
                    .clipped()
                    .simultaneousGesture(bubbleMagnifyGesture, including: .all)
                }
                .padding(.horizontal, 12)
                .padding(.vertical, 8)
                .contentShape(Rectangle())
                // Consume taps on bubble content to prevent them from reaching the dismiss area
                .onTapGesture { /* consume tap */ }
                .background(GeometryReader { bubbleProxy in
                    Color.clear.preference(
                        key: InteractiveBubbleFrameKey.self,
                        value: bubbleProxy.frame(in: .named(TextPlayerTokenCoordinateSpace.name))
                    )
                })
            }
            .frame(width: leftWidth)
            .clipped()

            // Right side: tracks - use fixed frame with center alignment to prevent layout jumps
            trackViewWithPlayback
                .padding(.horizontal, 12)
                .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .center)
                .frame(width: rightWidth)
                .contentShape(Rectangle())
                .simultaneousGesture(swipeGesture, including: .all)
                .simultaneousGesture(selectionDragGesture, including: .gesture)
                .simultaneousGesture(phoneBubbleOpenBackgroundTapGesture, including: .all)
                .highPriorityGesture(trackMagnifyGesture, including: .all)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .coordinateSpace(name: TextPlayerTokenCoordinateSpace.name)
    }

    /// Background tap gesture for iPhone when bubble is open.
    /// Tapping on or near a token triggers lookup; tapping elsewhere closes bubble and plays.
    private var phoneBubbleOpenBackgroundTapGesture: some Gesture {
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

