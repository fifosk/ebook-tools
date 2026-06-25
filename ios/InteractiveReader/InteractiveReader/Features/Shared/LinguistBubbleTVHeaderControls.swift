import SwiftUI

#if os(tvOS)
// MARK: - tvOS Header Controls

extension LinguistBubbleView {

    var tvSplitModeHeader: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 8) {
                lookupLanguageMenu
                voiceMenu
                tvReadAloudButton
                modelMenu
                tvPlayFromNarrationButton
                fontSizeControls
                Spacer(minLength: 4)
                tvPinToggleButton
                tvLayoutToggleButton
                closeButton
            }
            HStack(spacing: 4) {
                tvLookupSourceIndicator
                Text(state.query)
                    .font(queryFont)
                    .foregroundStyle(bubbleTextColor)
                    .lineLimit(3)
                    .minimumScaleFactor(0.7)
            }
        }
    }

    var tvOverlayModeHeader: some View {
        HStack(spacing: 8) {
            tvLookupSourceIndicator
            Text(state.query)
                .font(queryFont)
                .foregroundStyle(bubbleTextColor)
                .lineLimit(2)
                .minimumScaleFactor(0.8)
            Spacer(minLength: 8)
            lookupLanguageMenu
            voiceMenu
            tvReadAloudButton
            modelMenu
            tvPlayFromNarrationButton
            fontSizeControls
            tvPinToggleButton
            tvLayoutToggleButton
            closeButton
        }
    }

    @ViewBuilder
    var tvReadAloudButton: some View {
        if let onReadAloud = actions.onReadAloud {
            bubbleControlItem(control: .readAloud, isEnabled: true, action: onReadAloud) {
                Image(systemName: "speaker.wave.2.fill")
                    .foregroundStyle(.green)
            }
            .accessibilityLabel("Read lookup aloud")
        }
    }

    @ViewBuilder
    var tvPlayFromNarrationButton: some View {
        if let onPlay = actions.onPlayFromNarration, state.cachedAudioRef != nil {
            bubbleControlItem(control: .playFromNarration, isEnabled: true, action: onPlay) {
                Image(systemName: "waveform")
                    .foregroundStyle(.cyan)
            }
            .accessibilityLabel("Play from narration")
        }
    }

    @ViewBuilder
    var tvLookupSourceIndicator: some View {
        if state.status == .ready, let source = state.lookupSource {
            Text(source == .cache ? "⚡" : "☁")
                .font(.system(size: 16))
                .foregroundStyle(source == .cache ? .yellow : .cyan)
                .accessibilityLabel(source == .cache ? "Cached lookup" : "Live lookup")
        }
    }

    @ViewBuilder
    var tvLayoutToggleButton: some View {
        if let onToggle = actions.onToggleLayoutDirection {
            bubbleControlItem(control: .layout, isEnabled: true, action: onToggle) {
                Image(systemName: "rectangle.split.2x1")
            }
            .accessibilityLabel("Toggle layout")
        }
    }

    @ViewBuilder
    var tvPinToggleButton: some View {
        if let onToggle = actions.onTogglePin {
            bubbleControlItem(control: .pin, isEnabled: true, action: onToggle) {
                Image(systemName: configuration.isPinned ? "pin.fill" : "pin")
                    .foregroundStyle(configuration.isPinned ? .yellow : .white)
            }
            .accessibilityLabel(configuration.isPinned ? "Unpin bubble" : "Pin bubble")
        }
    }
}
#endif
