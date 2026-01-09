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
    let isMenuVisible: Bool
    let trackFontScale: CGFloat
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

    var body: some View {
        transcriptContent
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
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
            let bubbleFocusEnabled: Bool = {
                #if os(tvOS)
                return focusedArea == .bubble
                #else
                return true
                #endif
            }()

            #if os(tvOS)
            VStack(alignment: .leading, spacing: stackSpacing) {
                TextPlayerFrame(
                    sentences: sentences,
                    selection: selection,
                    onTokenLookup: onLookupToken,
                    onTokenSeek: onSeekToken,
                    fontScale: trackFontScale,
                    playbackPrimaryKind: playbackPrimaryKind
                )
                    .frame(maxWidth: .infinity, maxHeight: textHeight, alignment: .top)
                    .contentShape(Rectangle())
                    .focusable(!isMenuVisible)
                    .focused($focusedArea, equals: .transcript)
                    .onTapGesture {
                        onLookup()
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
                    TextPlayerFrame(
                        sentences: sentences,
                        selection: selection,
                        onTokenLookup: onLookupToken,
                        onTokenSeek: onSeekToken,
                        fontScale: trackFontScale,
                        playbackPrimaryKind: playbackPrimaryKind
                    )
                        .frame(
                            maxWidth: .infinity,
                            maxHeight: bubble == nil ? .infinity : textHeight,
                            alignment: .top
                        )
                        .contentShape(Rectangle())
                        .gesture(swipeGesture)
                        .simultaneousGesture(doubleTapGesture, including: .gesture)
                        .highPriorityGesture(trackMagnifyGesture, including: .all)

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
                        .background(GeometryReader { bubbleProxy in
                            Color.clear.preference(
                                key: InteractiveBubbleHeightKey.self,
                                value: bubbleProxy.size.height
                            )
                        })
                        .simultaneousGesture(bubbleMagnifyGesture, including: .all)
                    }
                }
            } else {
                VStack(alignment: .leading, spacing: stackSpacing) {
                    TextPlayerFrame(
                        sentences: sentences,
                        selection: selection,
                        onTokenLookup: onLookupToken,
                        onTokenSeek: onSeekToken,
                        fontScale: trackFontScale,
                        playbackPrimaryKind: playbackPrimaryKind
                    )
                        .frame(
                            maxWidth: .infinity,
                            minHeight: bubble == nil ? textHeight : 0,
                            maxHeight: textHeight,
                            alignment: .top
                        )
                        .contentShape(Rectangle())
                        .gesture(swipeGesture)
                        .simultaneousGesture(doubleTapGesture, including: .gesture)
                        .highPriorityGesture(trackMagnifyGesture, including: .all)

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
            }
            #endif
        }
        .onPreferenceChange(InteractiveBubbleHeightKey.self) { value in
            bubbleHeight = value
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
