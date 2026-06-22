import SwiftUI
#if os(iOS)
import UIKit

// MARK: - iOS Header Controls

extension LinguistBubbleView {

    @ViewBuilder
    var iOSHeaderRow: some View {
        if isPhone {
            VStack(alignment: .leading, spacing: 6) {
                HStack(spacing: 6) {
                    lookupLanguageMenu
                    voiceMenu
                    modelMenu
                    playFromNarrationButton
                    Spacer()
                    closeButton
                }
                HStack(spacing: 4) {
                    lookupSourceIndicator
                    lookupQueryText
                }
            }
        } else {
            VStack(alignment: .leading, spacing: 6) {
                HStack(spacing: 6) {
                    lookupLanguageMenu
                    voiceMenu
                    modelMenu
                    playFromNarrationButton
                    Spacer()
                    pinToggleButton
                    layoutToggleButton
                    closeButton
                }
                HStack(spacing: 4) {
                    lookupSourceIndicator
                    lookupQueryText
                }
            }
        }
    }

    var lookupQueryText: some View {
        Text(state.query)
            .font(queryFont)
            .foregroundStyle(bubbleTextColor)
            .lineLimit(2)
            .minimumScaleFactor(0.8)
            .contextMenu {
                let sanitized = TextLookupSanitizer.sanitize(state.query)
                Button("Look Up") {
                    DictionaryLookupPresenter.show(term: sanitized)
                }
                Button("Copy") {
                    UIPasteboard.general.string = sanitized
                }
            }
    }

    @ViewBuilder
    var playFromNarrationButton: some View {
        if let onPlay = actions.onPlayFromNarration, state.cachedAudioRef != nil {
            Button(action: onPlay) {
                Image(systemName: "waveform")
                    .font(bubbleIconFont)
                    .foregroundStyle(.cyan)
                    .padding(bubbleControlPadding)
                    .background(.black.opacity(0.3), in: Circle())
            }
            .buttonStyle(.plain)
            .accessibilityLabel("Play from narration")
        }
    }

    @ViewBuilder
    var lookupSourceIndicator: some View {
        if state.status == .ready, let source = state.lookupSource {
            Text(source == .cache ? "⚡" : "☁")
                .font(.system(size: configuration.uiScale * 10))
                .foregroundStyle(source == .cache ? .yellow : .cyan)
                .padding(.horizontal, 4)
                .padding(.vertical, 2)
                .background(.black.opacity(0.3), in: Capsule())
                .accessibilityLabel(source == .cache ? "Cached lookup" : "Live lookup")
        }
    }

    @ViewBuilder
    var pinToggleButton: some View {
        if let onToggle = actions.onTogglePin {
            Button(action: onToggle) {
                Image(systemName: configuration.isPinned ? "pin.fill" : "pin")
                    .font(bubbleIconFont)
                    .foregroundStyle(configuration.isPinned ? .yellow : .white)
                    .padding(bubbleControlPadding)
                    .background(.black.opacity(0.3), in: Circle())
            }
            .buttonStyle(.plain)
            .accessibilityLabel(configuration.isPinned ? "Unpin bubble" : "Pin bubble")
        }
    }

    @ViewBuilder
    var layoutToggleButton: some View {
        if let onToggle = actions.onToggleLayoutDirection {
            Button(action: onToggle) {
                Image(systemName: "rectangle.split.2x1")
                    .font(bubbleIconFont)
                    .foregroundStyle(.white)
                    .padding(bubbleControlPadding)
                    .background(.black.opacity(0.3), in: Circle())
            }
            .buttonStyle(.plain)
            .accessibilityLabel("Toggle layout direction")
        }
    }
}
#endif
