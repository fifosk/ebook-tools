import SwiftUI

struct TextPlayerSentenceView: View {
    let sentence: TextPlayerSentenceDisplay
    let selection: TextPlayerWordSelection?
    let selectionRange: TextPlayerWordSelectionRange?
    let playbackPrimaryKind: TextPlayerVariantKind?
    let visibleTracks: Set<TextPlayerVariantKind>
    let onToggleTrack: ((TextPlayerVariantKind) -> Void)?
    let onTokenLookup: ((Int, TextPlayerVariantKind, Int, String) -> Void)?
    let onTokenSeek: ((Int, Int?, TextPlayerVariantKind, Int, Double?) -> Void)?
    let fontScale: CGFloat
    let shouldReportTokenFrames: Bool

    var body: some View {
        Group {
            variantContent
        }
        .padding(.vertical, 10)
        .padding(.horizontal, 12)
        .frame(maxWidth: .infinity)
        .background(sentenceBackground)
        .clipShape(RoundedRectangle(cornerRadius: 12))
        .shadow(color: sentenceShadow, radius: sentenceShadowRadius, x: 0, y: 6)
        .opacity(sentenceOpacity)
    }

    @ViewBuilder
    private var variantContent: some View {
        let playbackPrimaryIndex = playbackPrimaryTokenIndex()
        #if os(tvOS)
        VStack(spacing: 8) {
            ForEach(sentence.variants) { variant in
                TextPlayerVariantView(
                    variant: variant,
                    sentenceIndex: sentence.index,
                    sentenceState: sentence.state,
                    selectedTokenIndex: selectedTokenIndex(for: variant),
                    selectedTokenRange: selectedTokenRange(for: variant),
                    shadowTokenIndex: shadowTokenIndex(for: variant),
                    playbackTokenIndex: playbackTokenIndex(for: variant, primaryIndex: playbackPrimaryIndex),
                    playbackShadowIndex: playbackShadowIndex(for: variant, primaryIndex: playbackPrimaryIndex),
                    isVisible: visibleTracks.contains(variant.kind),
                    onToggleVisibility: { handleTrackVisibilityToggle(variant.kind) },
                    fontScale: fontScale,
                    onTokenLookup: { tokenIndex, token in
                        onTokenLookup?(sentence.index, variant.kind, tokenIndex, token)
                    },
                    onTokenSeek: { tokenIndex, seekTime in
                        onTokenSeek?(sentence.index, sentence.sentenceNumber, variant.kind, tokenIndex, seekTime)
                    },
                    shouldReportTokenFrames: shouldReportTokenFrames
                )
            }
        }
        #else
        let visibleVariants = sentence.variants.filter { visibleTracks.contains($0.kind) }
        let hiddenVariants = sentence.variants.filter { !visibleTracks.contains($0.kind) }
        VStack(spacing: 8) {
            if !hiddenVariants.isEmpty {
                HStack {
                    Spacer()
                    hiddenTrackHeaderRow(for: hiddenVariants)
                }
            }
            ForEach(visibleVariants) { variant in
                TextPlayerVariantView(
                    variant: variant,
                    sentenceIndex: sentence.index,
                    sentenceState: sentence.state,
                    selectedTokenIndex: selectedTokenIndex(for: variant),
                    selectedTokenRange: selectedTokenRange(for: variant),
                    shadowTokenIndex: shadowTokenIndex(for: variant),
                    playbackTokenIndex: playbackTokenIndex(for: variant, primaryIndex: playbackPrimaryIndex),
                    playbackShadowIndex: playbackShadowIndex(for: variant, primaryIndex: playbackPrimaryIndex),
                    isVisible: true,
                    onToggleVisibility: { handleTrackVisibilityToggle(variant.kind) },
                    fontScale: fontScale,
                    onTokenLookup: { tokenIndex, token in
                        onTokenLookup?(sentence.index, variant.kind, tokenIndex, token)
                    },
                    onTokenSeek: { tokenIndex, seekTime in
                        onTokenSeek?(sentence.index, sentence.sentenceNumber, variant.kind, tokenIndex, seekTime)
                    },
                    shouldReportTokenFrames: shouldReportTokenFrames
                )
            }
        }
        #endif
    }

    private var sentenceBackground: Color {
        sentence.state == .active ? TextPlayerTheme.sentenceActiveBackground : TextPlayerTheme.sentenceBackground
    }

    private var sentenceShadow: Color {
        sentence.state == .active ? TextPlayerTheme.sentenceActiveShadow : .clear
    }

    private var sentenceShadowRadius: CGFloat {
        sentence.state == .active ? 18 : 0
    }

    private var sentenceOpacity: Double {
        switch sentence.state {
        case .past:
            return 0.9
        case .future:
            return 0.85
        case .active:
            return 1.0
        }
    }

    #if !os(tvOS)
    private func hiddenTrackHeaderRow(for hiddenVariants: [TextPlayerVariantDisplay]) -> some View {
        HStack(spacing: 8) {
            ForEach(hiddenVariants) { variant in
                Button(action: { handleTrackVisibilityToggle(variant.kind) }) {
                    compactHeaderLabel(for: variant)
                }
                .buttonStyle(.plain)
                .disabled(onToggleTrack == nil)
            }
        }
    }

    private func compactHeaderLabel(for variant: TextPlayerVariantDisplay) -> some View {
        HStack(spacing: 4) {
            Text(variant.label)
                .font(.caption2)
                .textCase(.uppercase)
                .tracking(1.0)
                .lineLimit(1)
                .minimumScaleFactor(0.7)
                .allowsTightening(true)
            Image(systemName: "chevron.down")
                .font(.caption2.weight(.semibold))
        }
        .foregroundStyle(TextPlayerTheme.lineLabel)
        .opacity(0.6)
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
    #endif

    private func handleTrackVisibilityToggle(_ kind: TextPlayerVariantKind) {
        onToggleTrack?(kind)
    }

    private func selectedTokenIndex(for variant: TextPlayerVariantDisplay) -> Int? {
        guard let selection, selection.sentenceIndex == sentence.index else { return nil }
        guard selection.variantKind == variant.kind else { return nil }
        return selection.tokenIndex
    }

    private func selectedTokenRange(for variant: TextPlayerVariantDisplay) -> ClosedRange<Int>? {
        guard let selectionRange, selectionRange.sentenceIndex == sentence.index else { return nil }
        guard selectionRange.variantKind == variant.kind else { return nil }
        guard !variant.tokens.isEmpty else { return nil }
        let maxIndex = variant.tokens.count - 1
        let startIndex = max(0, min(selectionRange.startIndex, maxIndex))
        let endIndex = max(0, min(selectionRange.endIndex, maxIndex))
        guard startIndex <= endIndex else { return nil }
        return startIndex...endIndex
    }

    private func shadowTokenIndex(for variant: TextPlayerVariantDisplay) -> Int? {
        guard let selection, selection.sentenceIndex == sentence.index else { return nil }
        let isTranslationPair = selection.variantKind == .translation || selection.variantKind == .transliteration
        guard isTranslationPair else { return nil }
        let isShadowVariant = (variant.kind == .translation && selection.variantKind == .transliteration)
            || (variant.kind == .transliteration && selection.variantKind == .translation)
        guard isShadowVariant else { return nil }
        guard variant.tokens.indices.contains(selection.tokenIndex) else { return nil }
        return selection.tokenIndex
    }

    private func playbackPrimaryTokenIndex() -> Int? {
        guard sentence.state == .active else { return nil }
        guard let playbackPrimaryKind else { return nil }
        guard let variant = sentence.variants.first(where: { $0.kind == playbackPrimaryKind }) else { return nil }
        if let currentIndex = variant.currentIndex {
            return currentIndex
        }
        if variant.revealedCount > 0 {
            return max(0, min(variant.revealedCount - 1, variant.tokens.count - 1))
        }
        return nil
    }

    private func playbackTokenIndex(
        for variant: TextPlayerVariantDisplay,
        primaryIndex: Int?
    ) -> Int? {
        guard sentence.state == .active else { return nil }
        guard let playbackPrimaryKind else { return nil }
        guard variant.kind == playbackPrimaryKind else { return nil }
        guard let primaryIndex, variant.tokens.indices.contains(primaryIndex) else { return nil }
        return primaryIndex
    }

    private func playbackShadowIndex(
        for variant: TextPlayerVariantDisplay,
        primaryIndex: Int?
    ) -> Int? {
        guard sentence.state == .active else { return nil }
        guard let playbackPrimaryKind else { return nil }
        guard let primaryIndex else { return nil }
        let isTranslationPair = playbackPrimaryKind == .translation || playbackPrimaryKind == .transliteration
        guard isTranslationPair else { return nil }
        let isShadowVariant = (variant.kind == .translation && playbackPrimaryKind == .transliteration)
            || (variant.kind == .transliteration && playbackPrimaryKind == .translation)
        guard isShadowVariant else { return nil }
        guard variant.tokens.indices.contains(primaryIndex) else { return nil }
        return primaryIndex
    }
}
