import SwiftUI

// MARK: - Phone Layout

#if os(iOS)
extension InteractiveTranscriptView {

    @ViewBuilder
    func phoneLayout(
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
    func phonePortraitBubbleLayout(
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
                .simultaneousGesture(bubbleAreaSwipeGesture, including: .all)
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
    func phoneLandscapeBubbleLayout(
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
                .simultaneousGesture(bubbleAreaSwipeGesture, including: .all)
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
}
#endif
