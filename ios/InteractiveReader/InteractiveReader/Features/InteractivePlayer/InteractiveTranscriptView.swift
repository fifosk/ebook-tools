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

struct InteractiveTrackHeightKey: PreferenceKey {
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
            let textHeightLimit = isPhone ? availableHeight : textHeight
            let shouldAutoScaleTracks = isPad
            let bubbleFocusEnabled: Bool = {
                #if os(tvOS)
                return focusedArea == .bubble
                #else
                return true
                #endif
            }()
            let resolvedTrackFontScale = (isTV || !shouldAutoScaleTracks) ? trackFontScale : {
                let current = effectiveTrackFontScale == 0 ? trackFontScale : effectiveTrackFontScale
                return min(current, trackFontScale)
            }()
            let baseTrackView = TextPlayerFrame(
                sentences: sentences,
                selection: selection,
                onTokenLookup: onLookupToken,
                onTokenSeek: onSeekToken,
                fontScale: resolvedTrackFontScale,
                playbackPrimaryKind: playbackPrimaryKind,
                visibleTracks: visibleTracks,
                onToggleTrack: onToggleTrack
            )
            let trackView = shouldAutoScaleTracks
                ? AnyView(baseTrackView.background(GeometryReader { trackProxy in
                    Color.clear.preference(
                        key: InteractiveTrackHeightKey.self,
                        value: trackProxy.size.height
                    )
                }))
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
                        Spacer(minLength: 0)
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
                        Spacer(minLength: 0)
                    }
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
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
            .onPreferenceChange(InteractiveTrackHeightKey.self) { value in
                guard shouldAutoScaleTracks else { return }
                trackHeight = value
                updateEffectiveTrackFontScale(measuredHeight: value, availableHeight: textHeightLimit)
            }
            .onChange(of: bubbleHeight) { _, _ in
                guard shouldAutoScaleTracks else { return }
                updateEffectiveTrackFontScale(measuredHeight: trackHeight, availableHeight: textHeightLimit)
            }
            .onChange(of: proxy.size) { _, _ in
                guard shouldAutoScaleTracks else { return }
                updateEffectiveTrackFontScale(measuredHeight: trackHeight, availableHeight: textHeightLimit)
            }
            .onChange(of: trackFontScale) { _, _ in
                guard shouldAutoScaleTracks else { return }
                effectiveTrackFontScale = trackFontScale
                updateEffectiveTrackFontScale(measuredHeight: trackHeight, availableHeight: textHeightLimit)
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
        guard !isTV, !isPhone else { return }
        guard measuredHeight > 0, availableHeight > 0 else {
            if effectiveTrackFontScale != trackFontScale {
                effectiveTrackFontScale = trackFontScale
            }
            return
        }
        let currentScale = effectiveTrackFontScale == 0 ? trackFontScale : effectiveTrackFontScale
        let ratio = availableHeight / measuredHeight
        let proposed = min(trackFontScale, currentScale * ratio)
        let clamped = max(minTrackFontScale, proposed)
        if abs(clamped - currentScale) > 0.01 {
            effectiveTrackFontScale = clamped
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
}
