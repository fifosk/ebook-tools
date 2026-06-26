import SwiftUI
#if os(iOS)
import UIKit
#endif

struct TextPlayerVariantView: View {
    let variant: TextPlayerVariantDisplay
    let sentenceIndex: Int
    let sentenceNumber: Int?
    let sentenceState: TextPlayerSentenceState
    let selectedTokenIndex: Int?
    let selectedTokenRange: ClosedRange<Int>?
    let shadowTokenIndex: Int?
    let playbackTokenIndex: Int?
    let playbackShadowIndex: Int?
    let isVisible: Bool
    let onToggleVisibility: (() -> Void)?
    let fontScale: CGFloat
    let onTokenLookup: ((Int, String) -> Void)?
    let onTokenSeek: ((Int, Double?, Bool) -> Void)?
    let shouldReportTokenFrames: Bool

    var body: some View {
        VStack(spacing: 6) {
            headerControl
            Group {
                if isVisible {
                    tokenFlow
                        .font(lineFont)
                        .frame(maxWidth: .infinity)
                        .layoutPriority(1)
                } else {
                    Color.clear
                        .frame(height: 1)
                }
            }
        }
    }

    @ViewBuilder
    private var headerControl: some View {
        #if os(tvOS)
        headerLabel
            .focusEffectDisabled()
        #else
        Button(action: handleHeaderToggle) {
            headerLabel
        }
        .buttonStyle(.plain)
        .disabled(onToggleVisibility == nil)
        #endif
    }

    private var headerLabel: some View {
        HStack(spacing: 6) {
            Text(variant.label)
                .font(labelFont)
                .textCase(.uppercase)
                .tracking(1.2)
                .lineLimit(1)
                .minimumScaleFactor(0.7)
                .allowsTightening(true)
            Image(systemName: isVisible ? "chevron.up" : "chevron.down")
                .font(labelFont.weight(.semibold))
        }
        .foregroundStyle(TextPlayerTheme.lineLabel)
        .opacity(isVisible ? 1 : 0.55)
        .frame(maxWidth: .infinity)
        .applyIf(shouldReportTokenFrames) { view in
            view.background(
                GeometryReader { proxy in
                    Color.clear.preference(
                        key: TextPlayerTapExclusionPreferenceKey.self,
                        value: [proxy.frame(in: .named(TextPlayerTokenCoordinateSpace.name))]
                    )
                }
            )
        }
    }

    private var labelFont: Font {
        .caption
    }

    private var lineFont: Font {
        #if os(tvOS)
        return sentenceState == .active ? .title2 : .title3
        #elseif os(iOS)
        let isPad = UIDevice.current.userInterfaceIdiom == .pad
        let textStyle: UIFont.TextStyle = {
            if isPad {
                return sentenceState == .active ? .title1 : .title2
            }
            return sentenceState == .active ? .title2 : .title3
        }()
        let baseSize = UIFont.preferredFont(forTextStyle: textStyle).pointSize
        return .system(size: baseSize * fontScale)
        #else
        return sentenceState == .active ? .title2 : .title3
        #endif
    }

    private var tokenFlow: some View {
        TokenFlowLayout(itemSpacing: tokenItemSpacing, lineSpacing: tokenLineSpacing) {
            ForEach(displayTokenIndices, id: \.self) { index in
                let token = variant.tokens[index]
                let isRangeSelected = selectedTokenRange?.contains(index) ?? false
                TokenWordView(
                    text: token,
                    color: tokenColor(for: tokenState(for: index)),
                    isSelected: index == selectedTokenIndex || isRangeSelected,
                    isShadowSelected: index == shadowTokenIndex,
                    isPlaybackSelected: index == playbackTokenIndex,
                    isPlaybackShadowSelected: index == playbackShadowIndex,
                    horizontalPadding: tokenHorizontalPadding,
                    verticalPadding: tokenVerticalPadding,
                    cornerRadius: tokenCornerRadius,
                    onTap: { shouldPlay in
                        onTokenSeek?(index, tokenSeekTime(for: index), shouldPlay)
                    },
                    onLookup: {
                        onTokenLookup?(index, token)
                    }
                )
                .applyIf(shouldReportTokenFrames) { view in
                    view.background(
                        GeometryReader { proxy in
                            Color.clear.preference(
                                key: TextPlayerTokenFramePreferenceKey.self,
                                value: [
                                    TextPlayerTokenFrame(
                                        sentenceIndex: sentenceIndex,
                                        sentenceNumber: sentenceNumber,
                                        variantKind: variant.kind,
                                        tokenIndex: index,
                                        token: token,
                                        frame: proxy.frame(in: .named(TextPlayerTokenCoordinateSpace.name))
                                    )
                                ]
                            )
                        }
                    )
                }
            }
        }
    }

    private var displayTokenIndices: [Int] {
        Array(variant.tokens.indices)
    }

    private var tokenItemSpacing: CGFloat {
        #if os(tvOS)
        return 10
        #else
        return 8
        #endif
    }

    private var tokenLineSpacing: CGFloat {
        #if os(tvOS)
        return 8
        #else
        return 6
        #endif
    }

    private var tokenHorizontalPadding: CGFloat {
        #if os(tvOS)
        return 4
        #else
        return 3
        #endif
    }

    private var tokenVerticalPadding: CGFloat {
        #if os(tvOS)
        return 2
        #else
        return 1
        #endif
    }

    private var tokenCornerRadius: CGFloat {
        #if os(tvOS)
        return 6
        #else
        return 4
        #endif
    }

    private func handleHeaderToggle() {
        onToggleVisibility?()
    }

    private func tokenSeekTime(for index: Int) -> Double? {
        guard let seekTimes = variant.seekTimes,
              seekTimes.indices.contains(index) else {
            return nil
        }
        let value = seekTimes[index]
        return value.isFinite ? value : nil
    }

    private func tokenState(for index: Int) -> TokenState {
        if sentenceState == .future {
            return .future
        }
        if sentenceState == .past {
            return .past
        }
        if variant.revealedCount == 0 {
            return .future
        }
        if index < variant.revealedCount - 1 {
            return .past
        }
        if index == variant.revealedCount - 1 {
            if playbackTokenIndex != nil {
                return .current
            }
            return .past
        }
        return .future
    }

    private func tokenColor(for state: TokenState) -> Color {
        switch state {
        case .past:
            return TextPlayerTheme.progress
        case .current:
            switch variant.kind {
            case .original:
                return TextPlayerTheme.originalCurrent
            case .translation:
                return TextPlayerTheme.translationCurrent
            case .transliteration:
                return TextPlayerTheme.transliterationCurrent
            }
        case .future:
            switch variant.kind {
            case .original:
                return TextPlayerTheme.original
            case .translation:
                return TextPlayerTheme.translation
            case .transliteration:
                return TextPlayerTheme.transliteration
            }
        }
    }

    private enum TokenState {
        case past
        case current
        case future
    }
}
