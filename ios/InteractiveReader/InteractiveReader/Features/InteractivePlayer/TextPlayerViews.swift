import SwiftUI
#if os(iOS) || os(tvOS)
import UIKit
#endif

struct TextPlayerFrame: View {
    let sentences: [TextPlayerSentenceDisplay]
    let selection: TextPlayerWordSelection?
    let onTokenLookup: ((Int, TextPlayerVariantKind, Int, String) -> Void)?
    let onTokenSeek: ((Int, Int?, TextPlayerVariantKind, Int, Double?) -> Void)?
    let fontScale: CGFloat
    let playbackPrimaryKind: TextPlayerVariantKind?
    let visibleTracks: Set<TextPlayerVariantKind>
    let onToggleTrack: ((TextPlayerVariantKind) -> Void)?

    var body: some View {
        VStack(spacing: 10) {
            if sentences.isEmpty {
                Text("Waiting for transcript...")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .frame(maxWidth: .infinity)
            } else {
                ForEach(sentences) { sentence in
                    TextPlayerSentenceView(
                        sentence: sentence,
                        selection: selection,
                        playbackPrimaryKind: playbackPrimaryKind,
                        visibleTracks: visibleTracks,
                        onToggleTrack: onToggleTrack,
                        onTokenLookup: onTokenLookup,
                        onTokenSeek: onTokenSeek,
                        fontScale: fontScale
                    )
                }
            }
        }
        .padding(framePadding)
        .frame(maxWidth: .infinity)
        .background(TextPlayerTheme.frameBackground)
        .clipShape(RoundedRectangle(cornerRadius: 16))
    }

    private var framePadding: CGFloat {
        #if os(tvOS)
        return 20
        #else
        return 14
        #endif
    }
}

struct TextPlayerSentenceView: View {
    let sentence: TextPlayerSentenceDisplay
    let selection: TextPlayerWordSelection?
    let playbackPrimaryKind: TextPlayerVariantKind?
    let visibleTracks: Set<TextPlayerVariantKind>
    let onToggleTrack: ((TextPlayerVariantKind) -> Void)?
    let onTokenLookup: ((Int, TextPlayerVariantKind, Int, String) -> Void)?
    let onTokenSeek: ((Int, Int?, TextPlayerVariantKind, Int, Double?) -> Void)?
    let fontScale: CGFloat

    var body: some View {
        let playbackPrimaryIndex = playbackPrimaryTokenIndex()
        VStack(spacing: 8) {
            ForEach(sentence.variants) { variant in
                TextPlayerVariantView(
                    variant: variant,
                    sentenceState: sentence.state,
                    selectedTokenIndex: selectedTokenIndex(for: variant),
                    shadowTokenIndex: shadowTokenIndex(for: variant),
                    playbackTokenIndex: playbackTokenIndex(for: variant, primaryIndex: playbackPrimaryIndex),
                    playbackShadowIndex: playbackShadowIndex(for: variant, primaryIndex: playbackPrimaryIndex),
                    isVisible: visibleTracks.contains(variant.kind),
                    onToggleVisibility: {
                        onToggleTrack?(variant.kind)
                    },
                    fontScale: fontScale,
                    onTokenLookup: { tokenIndex, token in
                        onTokenLookup?(sentence.index, variant.kind, tokenIndex, token)
                    },
                    onTokenSeek: { tokenIndex, seekTime in
                        onTokenSeek?(sentence.index, sentence.sentenceNumber, variant.kind, tokenIndex, seekTime)
                    }
                )
            }
        }
        .padding(.vertical, 10)
        .padding(.horizontal, 12)
        .frame(maxWidth: .infinity)
        .background(sentenceBackground)
        .clipShape(RoundedRectangle(cornerRadius: 12))
        .shadow(color: sentenceShadow, radius: sentenceShadowRadius, x: 0, y: 6)
        .opacity(sentenceOpacity)
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

    private func selectedTokenIndex(for variant: TextPlayerVariantDisplay) -> Int? {
        guard let selection, selection.sentenceIndex == sentence.index else { return nil }
        guard selection.variantKind == variant.kind else { return nil }
        return selection.tokenIndex
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

struct TokenFlowLayout: Layout {
    let itemSpacing: CGFloat
    let lineSpacing: CGFloat
    let alignment: HorizontalAlignment

    private struct Line {
        var indices: [Int] = []
        var width: CGFloat = 0
        var height: CGFloat = 0
    }

    init(itemSpacing: CGFloat, lineSpacing: CGFloat, alignment: HorizontalAlignment = .center) {
        self.itemSpacing = itemSpacing
        self.lineSpacing = lineSpacing
        self.alignment = alignment
    }

    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        let maxWidth = proposal.width ?? .greatestFiniteMagnitude
        let lines = buildLines(maxWidth: maxWidth, subviews: subviews)
        let maxLineWidth = lines.map(\.width).max() ?? 0
        let totalHeight = lines.reduce(0) { $0 + $1.height }
            + lineSpacing * max(0, CGFloat(lines.count - 1))
        return CGSize(width: min(maxWidth, maxLineWidth), height: totalHeight)
    }

    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        guard bounds.width > 0 else { return }
        let lines = buildLines(maxWidth: bounds.width, subviews: subviews)
        var y = bounds.minY
        for line in lines {
            let lineWidth = line.width
            let xStart: CGFloat = {
                switch alignment {
                case .leading:
                    return bounds.minX
                case .trailing:
                    return bounds.minX + max(0, bounds.width - lineWidth)
                default:
                    return bounds.minX + max(0, (bounds.width - lineWidth) / 2)
                }
            }()
            var x = xStart
            for index in line.indices {
                let subview = subviews[index]
                let size = subview.sizeThatFits(.unspecified)
                let origin = CGPoint(x: x, y: y + (line.height - size.height) / 2)
                subview.place(at: origin, proposal: ProposedViewSize(width: size.width, height: size.height))
                x += size.width + itemSpacing
            }
            y += line.height + lineSpacing
        }
    }

    private func buildLines(maxWidth: CGFloat, subviews: Subviews) -> [Line] {
        guard !subviews.isEmpty else { return [] }
        let effectiveWidth = maxWidth > 0 ? maxWidth : .greatestFiniteMagnitude
        var lines: [Line] = []
        var current = Line()
        for index in subviews.indices {
            let size = subviews[index].sizeThatFits(.unspecified)
            let itemWidth = size.width
            if current.indices.isEmpty {
                current.indices = [index]
                current.width = itemWidth
                current.height = size.height
                continue
            }
            if current.width + itemSpacing + itemWidth <= effectiveWidth {
                current.indices.append(index)
                current.width += itemSpacing + itemWidth
                current.height = max(current.height, size.height)
            } else {
                lines.append(current)
                current = Line(indices: [index], width: itemWidth, height: size.height)
            }
        }
        if !current.indices.isEmpty {
            lines.append(current)
        }
        return lines
    }
}

struct TokenWordView: View {
    let text: String
    let color: Color
    let isSelected: Bool
    let isShadowSelected: Bool
    let isPlaybackSelected: Bool
    let isPlaybackShadowSelected: Bool
    let horizontalPadding: CGFloat
    let verticalPadding: CGFloat
    let cornerRadius: CGFloat
    let onTap: (() -> Void)?
    let onLookup: (() -> Void)?

    var body: some View {
        let isPrimaryHighlight = isSelected || isPlaybackSelected
        let isShadowHighlight = !isPrimaryHighlight && (isShadowSelected || isPlaybackShadowSelected)
        Text(text)
            .lineLimit(1)
            .minimumScaleFactor(0.7)
            .allowsTightening(true)
            .padding(.horizontal, horizontalPadding)
            .padding(.vertical, verticalPadding)
            .foregroundStyle(isPrimaryHighlight ? TextPlayerTheme.selectionText : color)
            .background(
                Group {
                    if isPrimaryHighlight || isShadowHighlight {
                        RoundedRectangle(cornerRadius: cornerRadius)
                            .fill(isPrimaryHighlight ? TextPlayerTheme.selectionGlow : TextPlayerTheme.selectionShadow)
                    }
                }
            )
            #if !os(tvOS)
            .gesture(tokenTapGesture)
            #endif
            #if os(iOS)
            .contextMenu {
                Button("Look Up") {
                    DictionaryLookupPresenter.show(term: text)
                }
                Button("Copy") {
                    UIPasteboard.general.string = text
                }
            }
            #endif
    }

    #if !os(tvOS)
    private var tokenTapGesture: some Gesture {
        let doubleTap = TapGesture(count: 2)
            .onEnded { onLookup?() }
        let singleTap = TapGesture(count: 1)
            .onEnded { onTap?() }
        return doubleTap.exclusively(before: singleTap)
    }
    #endif
}

#if os(iOS)
enum DictionaryLookupPresenter {
    static func show(term: String) {
        let trimmed = term.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }
        let controller = UIReferenceLibraryViewController(term: trimmed)
        guard let presenter = topViewController() else { return }
        presenter.present(controller, animated: true)
    }

    private static func topViewController() -> UIViewController? {
        let scenes = UIApplication.shared.connectedScenes.compactMap { $0 as? UIWindowScene }
        let windows = scenes.flatMap { $0.windows }
        let root = windows.first(where: { $0.isKeyWindow })?.rootViewController
        return topViewController(from: root)
    }

    private static func topViewController(from root: UIViewController?) -> UIViewController? {
        if let presented = root?.presentedViewController {
            return topViewController(from: presented)
        }
        if let navigation = root as? UINavigationController {
            return topViewController(from: navigation.visibleViewController)
        }
        if let tab = root as? UITabBarController {
            return topViewController(from: tab.selectedViewController)
        }
        return root
    }
}
#endif

struct TextPlayerVariantView: View {
    let variant: TextPlayerVariantDisplay
    let sentenceState: TextPlayerSentenceState
    let selectedTokenIndex: Int?
    let shadowTokenIndex: Int?
    let playbackTokenIndex: Int?
    let playbackShadowIndex: Int?
    let isVisible: Bool
    let onToggleVisibility: (() -> Void)?
    let fontScale: CGFloat
    let onTokenLookup: ((Int, String) -> Void)?
    let onTokenSeek: ((Int, Double?) -> Void)?

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
        Button(action: {
            onToggleVisibility?()
        }) {
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
    }

    private var labelFont: Font {
        #if os(tvOS)
        return .caption
        #else
        return .caption
        #endif
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
                TokenWordView(
                    text: token,
                    color: tokenColor(for: tokenState(for: index)),
                    isSelected: index == selectedTokenIndex,
                    isShadowSelected: index == shadowTokenIndex,
                    isPlaybackSelected: index == playbackTokenIndex,
                    isPlaybackShadowSelected: index == playbackShadowIndex,
                    horizontalPadding: tokenHorizontalPadding,
                    verticalPadding: tokenVerticalPadding,
                    cornerRadius: tokenCornerRadius,
                    onTap: {
                        onTokenSeek?(index, tokenSeekTime(for: index))
                    },
                    onLookup: {
                        onTokenLookup?(index, token)
                    }
                )
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
            return .current
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

    private var highlightShadowColor: Color {
        switch variant.kind {
        case .original:
            return TextPlayerTheme.progress.opacity(0.7)
        case .translation:
            return TextPlayerTheme.translation.opacity(0.55)
        case .transliteration:
            return TextPlayerTheme.transliteration.opacity(0.55)
        }
    }

    private enum TokenState {
        case past
        case current
        case future
    }
}

extension View {
    @ViewBuilder
    func applyIf<T: View>(_ condition: Bool, transform: (Self) -> T) -> some View {
        if condition {
            transform(self)
        } else {
            self
        }
    }
}

enum TextPlayerTheme {
    static let frameBackground = Color.black
    static let sentenceBackground = Color(red: 1.0, green: 0.878, blue: 0.521).opacity(0.04)
    static let sentenceActiveBackground = Color(red: 1.0, green: 0.647, blue: 0.0).opacity(0.16)
    static let sentenceActiveShadow = Color(red: 1.0, green: 0.549, blue: 0.0).opacity(0.18)
    static let lineLabel = Color.white.opacity(0.45)
    static let original = Color(red: 1.0, green: 0.831, blue: 0.0)
    static let translation = Color(red: 0.204, green: 0.827, blue: 0.6)
    static let transliteration = Color(red: 0.176, green: 0.831, blue: 0.749)
    static let progress = Color(red: 1.0, green: 0.549, blue: 0.0)
    static let selectionGlow = Color(red: 1.0, green: 0.549, blue: 0.0).opacity(0.6)
    static let selectionShadow = Color(red: 1.0, green: 0.549, blue: 0.0).opacity(0.25)
    static let selectionText = Color.black
    static let originalCurrent = Color.white
    static let translationCurrent = Color(red: 0.996, green: 0.941, blue: 0.541)
    static let transliterationCurrent = Color(red: 0.996, green: 0.976, blue: 0.765)
}

#if os(iOS) || os(tvOS)
extension UIFont.TextStyle {
    static var title: UIFont.TextStyle {
        .title1
    }
}
#endif
