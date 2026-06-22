import SwiftUI

#if os(tvOS)
extension InteractiveTranscriptView {
    func handleTVOverlayTrackTap() {
        if bubble != nil {
            if !iPadBubblePinned {
                onCloseBubble()
            }
        } else {
            onLookup()
        }
    }

    func handleTVSplitTrackTap() {
        if !iPadBubblePinned {
            onCloseBubble()
        }
    }

    func handleTVTrackLongPress() {
        onToggleHeader?()
    }

    /// tvOS horizontal split layout: 30% bubble on left, 70% tracks on right.
    @ViewBuilder
    func tvSplitLayout<TrackContent: View>(
        trackView: TrackContent,
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

            trackView
                .frame(width: trackWidth, height: availableHeight, alignment: .top)
                .clipped()
                .contentShape(Rectangle())
                .focusable(!isMenuVisible)
                .focused($focusedArea, equals: .transcript)
                .focusEffectDisabled()
                .onTapGesture(perform: handleTVSplitTrackTap)
                .onLongPressGesture(
                    minimumDuration: 0.6,
                    perform: handleTVTrackLongPress
                )
                .accessibilityAddTraits(.isButton)
        }
        .frame(width: availableWidth, height: availableHeight)
        .padding(.leading, 12)
        .padding(.trailing, 24)
    }
}
#endif
