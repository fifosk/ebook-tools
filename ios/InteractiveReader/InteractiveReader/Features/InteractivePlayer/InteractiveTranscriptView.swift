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

struct InteractiveAutoScaleTrackHeightKey: PreferenceKey {
    static var defaultValue: CGFloat = 0

    static func reduce(value: inout CGFloat, nextValue: () -> CGFloat) {
        value = max(value, nextValue())
    }
}

struct InteractiveTranscriptView: View {
    let viewModel: InteractivePlayerViewModel
    @ObservedObject var audioCoordinator: AudioPlayerCoordinator
    let sentences: [TextPlayerSentenceDisplay]
    let selection: TextPlayerWordSelection?
    let bubble: MyLinguistBubbleState?
    let lookupLanguage: String
    let lookupLanguageOptions: [String]
    let onLookupLanguageChange: (String) -> Void
    let llmModel: String
    let llmModelOptions: [String]
    let onLlmModelChange: (String) -> Void
    let playbackPrimaryKind: TextPlayerVariantKind?
    let visibleTracks: Set<TextPlayerVariantKind>
    let onToggleTrack: (TextPlayerVariantKind) -> Void
    let isMenuVisible: Bool
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
    let onIncreaseLinguistFont: () -> Void
    let onDecreaseLinguistFont: () -> Void
    let onSetTrackFontScale: (CGFloat) -> Void
    let onSetLinguistFontScale: (CGFloat) -> Void
    let onCloseBubble: () -> Void
    let onTogglePlayback: () -> Void

    #if os(iOS)
    @State private var trackMagnifyStartScale: CGFloat?
    @State private var bubbleMagnifyStartScale: CGFloat?
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
            let stackSpacing: CGFloat = bubble == nil ? 12 : (isTV ? 10 : (isPad ? 0 : 6))
            let minBubbleReserve: CGFloat = availableHeight * (isTV ? 0.3 : (isPad ? 0.35 : 0.4))
            let bubbleReserve = bubble == nil ? 0 : max(bubbleHeight + stackSpacing, minBubbleReserve)
            let preferredTextHeight = (isPad && bubble != nil) ? availableHeight * 0.7 : availableHeight
            let textHeight = max(min(preferredTextHeight, availableHeight - bubbleReserve), 0)
            let safeAreaBottom: CGFloat = {
                #if os(iOS)
                return isPhone ? proxy.safeAreaInsets.bottom : 0
                #else
                return 0
                #endif
            }()
            let textHeightLimit = isPhone ? max(availableHeight - safeAreaBottom, 0) : textHeight
            let shouldAutoScaleTracks = !isTV && autoScaleEnabled
            let bubbleFocusEnabled: Bool = {
                #if os(tvOS)
                return focusedArea == .bubble
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
            let resolvedTrackFontScale = (isTV || !shouldAutoScaleTracks) ? trackFontScale : {
                let current = effectiveTrackFontScale == 0 ? trackFontScale : effectiveTrackFontScale
                return min(current, maxTrackFontScale)
            }()
            let baseTrackView = TextPlayerFrame(
                sentences: sentences,
                selection: selection,
                onTokenLookup: tokenLookupHandler,
                onTokenSeek: onSeekToken,
                fontScale: resolvedTrackFontScale,
                playbackPrimaryKind: playbackPrimaryKind,
                visibleTracks: visibleTracks,
                onToggleTrack: onToggleTrack
            )
            let measuredTrackView = baseTrackView
                .background(GeometryReader { trackProxy in
                    Color.clear.preference(
                        key: InteractiveAutoScaleTrackHeightKey.self,
                        value: trackProxy.size.height
                    )
                })
            let trackView: AnyView = shouldAutoScaleTracks
                ? AnyView(measuredTrackView)
                : AnyView(baseTrackView)

            Group {
                #if os(tvOS)
                VStack(alignment: .leading, spacing: stackSpacing) {
                    trackView
                        .frame(maxWidth: .infinity, maxHeight: textHeight, alignment: .top)
                        .contentShape(Rectangle())
                        .focusable(!isMenuVisible)
                        .focused($focusedArea, equals: .transcript)
                        .focusEffectDisabled()
                        .onTapGesture {
                            onLookup()
                        }
                        .onLongPressGesture(minimumDuration: 0.6) {
                            onToggleTrack(.transliteration)
                        }
                        .accessibilityAddTraits(.isButton)

                    if let bubble {
                        MyLinguistBubbleView(
                            bubble: bubble,
                            fontScale: linguistFontScale,
                            canIncreaseFont: canIncreaseLinguistFont,
                            canDecreaseFont: canDecreaseLinguistFont,
                            lookupLanguage: lookupLanguage,
                            lookupLanguageOptions: lookupLanguageOptions,
                            onLookupLanguageChange: onLookupLanguageChange,
                            llmModel: llmModel,
                            llmModelOptions: llmModelOptions,
                            onLlmModelChange: onLlmModelChange,
                            onIncreaseFont: onIncreaseLinguistFont,
                            onDecreaseFont: onDecreaseLinguistFont,
                            onClose: onCloseBubble,
                            isFocusEnabled: bubbleFocusEnabled,
                            focusBinding: $focusedArea
                        )
                        .background(GeometryReader { bubbleProxy in
                            Color.clear.preference(
                                key: InteractiveBubbleHeightKey.self,
                                value: bubbleProxy.size.height
                            )
                        })
                    }
                }
                #else
                if isPhone {
                    ZStack(alignment: .bottom) {
                        VStack {
                            Spacer(minLength: 0)
                            trackView
                            Spacer(minLength: 0)
                        }
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                        .contentShape(Rectangle())
                        .gesture(swipeGesture)
                        .simultaneousGesture(doubleTapGesture, including: .gesture)
                        .highPriorityGesture(trackMagnifyGesture, including: .all)

                        if bubble != nil {
                            Color.clear
                                .frame(maxWidth: .infinity, maxHeight: .infinity)
                                .contentShape(Rectangle())
                                .onTapGesture {
                                    onCloseBubble()
                                    if !audioCoordinator.isPlaying {
                                        onTogglePlayback()
                                    }
                                }
                        }

                        if let bubble {
                            MyLinguistBubbleView(
                                bubble: bubble,
                                fontScale: linguistFontScale,
                                canIncreaseFont: canIncreaseLinguistFont,
                                canDecreaseFont: canDecreaseLinguistFont,
                                lookupLanguage: lookupLanguage,
                                lookupLanguageOptions: lookupLanguageOptions,
                                onLookupLanguageChange: onLookupLanguageChange,
                                llmModel: llmModel,
                                llmModelOptions: llmModelOptions,
                                onLlmModelChange: onLlmModelChange,
                                onIncreaseFont: onIncreaseLinguistFont,
                                onDecreaseFont: onDecreaseLinguistFont,
                                onClose: onCloseBubble,
                                isFocusEnabled: bubbleFocusEnabled,
                                focusBinding: $focusedArea
                            )
                            .frame(maxWidth: .infinity, alignment: .top)
                            .padding(.horizontal)
                            .padding(.bottom, 6)
                            .simultaneousGesture(bubbleMagnifyGesture, including: .all)
                        }
                    }
                } else {
                    VStack(alignment: .leading, spacing: stackSpacing) {
                        trackView
                        if let bubble {
                            MyLinguistBubbleView(
                                bubble: bubble,
                                fontScale: linguistFontScale,
                                canIncreaseFont: canIncreaseLinguistFont,
                                canDecreaseFont: canDecreaseLinguistFont,
                                lookupLanguage: lookupLanguage,
                                lookupLanguageOptions: lookupLanguageOptions,
                                onLookupLanguageChange: onLookupLanguageChange,
                                llmModel: llmModel,
                                llmModelOptions: llmModelOptions,
                                onLlmModelChange: onLlmModelChange,
                                onIncreaseFont: onIncreaseLinguistFont,
                                onDecreaseFont: onDecreaseLinguistFont,
                                onClose: onCloseBubble,
                                isFocusEnabled: bubbleFocusEnabled,
                                focusBinding: $focusedArea
                            )
                            .frame(maxWidth: .infinity, alignment: .top)
                            .background(GeometryReader { bubbleProxy in
                                Color.clear.preference(
                                    key: InteractiveBubbleHeightKey.self,
                                    value: bubbleProxy.size.height
                                )
                            })
                            .simultaneousGesture(bubbleMagnifyGesture, including: .all)
                        }
                    }
                    .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
                    .contentShape(Rectangle())
                    .gesture(swipeGesture)
                    .simultaneousGesture(doubleTapGesture, including: .gesture)
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
            .onDisappear {
                suppressPlaybackTask?.cancel()
                suppressPlaybackTask = nil
                autoScaleTask?.cancel()
                autoScaleTask = nil
            }
        }
    }

    #if !os(tvOS)
    private var swipeGesture: some Gesture {
        DragGesture(minimumDistance: 24, coordinateSpace: .local)
            .onEnded { value in
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

    private var autoScaleFloor: CGFloat {
        guard isPhone else { return minTrackFontScale }
        return max(0.75, minTrackFontScale * 0.75)
    }

    private var sentenceSignature: String {
        sentences.map(\.id).joined(separator: "|")
    }
}
