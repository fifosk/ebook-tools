import SwiftUI

#if canImport(UIKit)
import UIKit
#endif

struct VideoSubtitleWordSelection: Equatable {
    let lineKind: VideoSubtitleLineKind
    let lineIndex: Int
    let tokenIndex: Int
}

struct VideoSubtitleTokenReference: Equatable {
    let lineKind: VideoSubtitleLineKind
    let lineIndex: Int
    let tokenIndex: Int
    let token: String
}

struct VideoSubtitleDisplayLine: Identifiable {
    let id: String
    let index: Int
    let kind: VideoSubtitleLineKind
    let tokens: [String]
    let revealTimes: [Double]
    let tokenStyles: [VideoSubtitleTokenStyle]?
}

struct VideoSubtitleDisplay {
    let cue: VideoSubtitleCue
    let lines: [VideoSubtitleDisplayLine]
    let highlightStart: Double
    let highlightEnd: Double
}

enum VideoSubtitleDisplayBuilder {
    static func build(
        cues: [VideoSubtitleCue],
        time: Double,
        visibility: SubtitleVisibility
    ) -> VideoSubtitleDisplay? {
        guard let activeIndex = cues.lastIndex(where: { time >= $0.start && time <= $0.end }) else {
            return nil
        }
        let cue = cues[activeIndex]
        let lines = visibleLines(for: cue, visibility: visibility)
        guard !lines.isEmpty else { return nil }
        var tokenEntries: [(line: VideoSubtitleLine, tokens: [String], styles: [VideoSubtitleTokenStyle]?)] = []
        var hasHighlightStyles = false
        for line in lines {
            let tokenResult = tokenize(line.text, spans: line.spans)
            let tokens = tokenResult.tokens
            guard !tokens.isEmpty else { continue }
            if let styles = tokenResult.styles,
               styles.contains(where: { $0 != .base }) {
                hasHighlightStyles = true
            }
            tokenEntries.append((line: line, tokens: tokens, styles: tokenResult.styles))
        }
        guard !tokenEntries.isEmpty else { return nil }
        let highlightWindow = resolveHighlightWindow(
            cues: cues,
            activeIndex: activeIndex,
            allowGrouping: !hasHighlightStyles
        )
        var displays: [VideoSubtitleDisplayLine] = []
        for (index, entry) in tokenEntries.enumerated() {
            let revealTimes = buildRevealTimes(
                count: entry.tokens.count,
                startTime: highlightWindow.start,
                endTime: highlightWindow.end
            )
            displays.append(
                VideoSubtitleDisplayLine(
                    id: "\(index)-\(entry.line.kind.rawValue)",
                    index: index,
                    kind: entry.line.kind,
                    tokens: entry.tokens,
                    revealTimes: revealTimes,
                    tokenStyles: entry.styles
                )
            )
        }
        guard !displays.isEmpty else { return nil }
        return VideoSubtitleDisplay(
            cue: cue,
            lines: displays,
            highlightStart: highlightWindow.start,
            highlightEnd: highlightWindow.end
        )
    }

    private static func visibleLines(
        for cue: VideoSubtitleCue,
        visibility: SubtitleVisibility
    ) -> [VideoSubtitleLine] {
        let lines = cue.lines.isEmpty
            ? [VideoSubtitleLine(text: cue.text, spans: cue.spans, kind: .translation)]
            : cue.lines
        return lines.filter { !($0.text.isEmpty) && visibility.allows($0.kind) }
    }

    private static func tokenize(
        _ text: String,
        spans: [VideoSubtitleSpan]?
    ) -> (tokens: [String], styles: [VideoSubtitleTokenStyle]?) {
        if let spans, !spans.isEmpty {
            var tokens: [String] = []
            var styles: [VideoSubtitleTokenStyle] = []
            for span in spans {
                let spanTokens = span.text
                    .split(whereSeparator: { $0.isWhitespace })
                    .map { String($0) }
                if spanTokens.isEmpty {
                    continue
                }
                let style = tokenStyle(for: span)
                for token in spanTokens {
                    tokens.append(token)
                    styles.append(style)
                }
            }
            if !tokens.isEmpty {
                let hasHighlight = styles.contains { $0 != .base }
                return (tokens, hasHighlight ? styles : nil)
            }
        }
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return ([], nil) }
        let tokens = trimmed
            .split(whereSeparator: { $0.isWhitespace })
            .map { String($0) }
        return (tokens, nil)
    }

    private static func tokenStyle(for span: VideoSubtitleSpan) -> VideoSubtitleTokenStyle {
        if span.isBold {
            return .highlightCurrent
        }
        if let color = span.colorHex, highlightColors.contains(normalizeColor(color)) {
            return .highlightPrior
        }
        return .base
    }

    private static func normalizeColor(_ value: String) -> String {
        let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines).uppercased()
        if trimmed.hasPrefix("#") {
            return trimmed
        }
        return "#\(trimmed)"
    }

    private static let highlightColors: Set<String> = [
        "#FB923C",
        "#FF8C00"
    ]

    private static func resolveHighlightWindow(
        cues: [VideoSubtitleCue],
        activeIndex: Int,
        allowGrouping: Bool
    ) -> (start: Double, end: Double) {
        let cue = cues[activeIndex]
        guard allowGrouping else { return (cue.start, cue.end) }
        let targetText = cue.text
        let maxGap = 0.06
        var startIndex = activeIndex
        while startIndex > 0 {
            let previous = cues[startIndex - 1]
            let gap = cues[startIndex].start - previous.end
            if previous.text == targetText && gap <= maxGap {
                startIndex -= 1
            } else {
                break
            }
        }
        var endIndex = activeIndex
        while endIndex + 1 < cues.count {
            let next = cues[endIndex + 1]
            let gap = next.start - cues[endIndex].end
            if next.text == targetText && gap <= maxGap {
                endIndex += 1
            } else {
                break
            }
        }
        if startIndex == endIndex {
            return (cue.start, cue.end)
        }
        let start = cues[startIndex].start
        let end = cues[endIndex].end
        return (start, max(start, end))
    }

    private static func buildRevealTimes(
        count: Int,
        startTime: Double,
        endTime: Double
    ) -> [Double] {
        let tokenCount = max(0, count)
        guard tokenCount > 0 else { return [] }
        let duration = max(endTime - startTime, 0)
        if duration == 0 {
            return Array(repeating: startTime, count: tokenCount)
        }
        let step = duration / Double(tokenCount)
        var revealTimes: [Double] = []
        for index in 0..<tokenCount {
            let offset = step > 0 ? step * Double(index) : 0
            revealTimes.append(startTime + max(0, min(duration, offset)))
        }
        return revealTimes
    }
}

struct SubtitleOverlayView: View {
    let cues: [VideoSubtitleCue]
    let currentTime: Double
    let visibility: SubtitleVisibility
    let fontScale: CGFloat
    let selection: VideoSubtitleWordSelection?
    let onTokenLookup: ((VideoSubtitleTokenReference) -> Void)?

    var body: some View {
        if let display = VideoSubtitleDisplayBuilder.build(
            cues: cues,
            time: currentTime,
            visibility: visibility
        ) {
            VStack(spacing: 8) {
                ForEach(display.lines) { line in
                    SubtitleTokenLineView(
                        line: line,
                        highlightStart: display.highlightStart,
                        highlightEnd: display.highlightEnd,
                        currentTime: currentTime,
                        selection: selection,
                        fontScale: clampedFontScale,
                        onTokenLookup: onTokenLookup
                    )
                }
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 10)
            .background(.black.opacity(0.6), in: RoundedRectangle(cornerRadius: 12))
            .padding(.bottom, 24)
            .frame(maxWidth: .infinity)
            .transition(.opacity)
        }
    }

    private var clampedFontScale: CGFloat {
        max(0.7, min(fontScale, 2.0))
    }
}

private struct SubtitleTokenLineView: View {
    let line: VideoSubtitleDisplayLine
    let highlightStart: Double
    let highlightEnd: Double
    let currentTime: Double
    let selection: VideoSubtitleWordSelection?
    let fontScale: CGFloat
    let onTokenLookup: ((VideoSubtitleTokenReference) -> Void)?

    var body: some View {
        TokenFlowLayout(itemSpacing: tokenItemSpacing, lineSpacing: tokenLineSpacing) {
            ForEach(displayTokenIndices, id: \.self) { index in
                let token = line.tokens[index]
                SubtitleTokenWordView(
                    text: token,
                    color: tokenColor(for: tokenState(for: index)),
                    isSelected: isSelectedToken(index),
                    fontScale: fontScale,
                    horizontalPadding: tokenHorizontalPadding,
                    verticalPadding: tokenVerticalPadding,
                    cornerRadius: tokenCornerRadius,
                    onDoubleTap: {
                        onTokenLookup?(VideoSubtitleTokenReference(
                            lineKind: line.kind,
                            lineIndex: line.index,
                            tokenIndex: index,
                            token: token
                        ))
                    }
                )
            }
        }
        .frame(maxWidth: .infinity)
    }

    private var tokenRevealCutoff: Double {
        let clamped = min(max(currentTime, highlightStart), highlightEnd)
        return clamped.isFinite ? clamped : highlightStart
    }

    private var revealedCount: Int {
        let epsilon = 1e-3
        let count = line.revealTimes.filter { $0 <= tokenRevealCutoff + epsilon }.count
        if tokenRevealCutoff >= highlightEnd - epsilon {
            return line.tokens.count
        }
        return min(max(count, 0), line.tokens.count)
    }

    private var currentIndex: Int? {
        let epsilon = 1e-3
        if line.tokens.isEmpty {
            return nil
        }
        if tokenRevealCutoff >= highlightEnd - epsilon {
            return line.tokens.count - 1
        }
        if revealedCount > 0 {
            return min(revealedCount - 1, line.tokens.count - 1)
        }
        if tokenRevealCutoff >= highlightStart - epsilon {
            return 0
        }
        return nil
    }

    private var displayTokenIndices: [Int] {
        shouldReverseTokens
            ? Array(line.tokens.indices.reversed())
            : Array(line.tokens.indices)
    }

    private func isSelectedToken(_ index: Int) -> Bool {
        guard let selection else { return false }
        return selection.lineKind == line.kind
            && selection.lineIndex == line.index
            && selection.tokenIndex == index
    }

    private func tokenState(for index: Int) -> SubtitleTokenState {
        if let styles = line.tokenStyles, styles.indices.contains(index) {
            switch styles[index] {
            case .highlightPrior:
                return .past
            case .highlightCurrent:
                return .current
            case .base:
                return .future
            }
        }
        guard shouldHighlightLine else { return .future }
        if tokenRevealCutoff <= highlightStart {
            return .future
        }
        if tokenRevealCutoff >= highlightEnd {
            return .past
        }
        if revealedCount == 0 {
            return .future
        }
        if index < max(revealedCount - 1, 0) {
            return .past
        }
        if index == max(revealedCount - 1, 0) {
            return .current
        }
        return .future
    }

    private var shouldHighlightLine: Bool {
        line.kind == .translation || line.kind == .transliteration || line.kind == .unknown
    }

    private func tokenColor(for state: SubtitleTokenState) -> Color {
        switch state {
        case .past:
            return SubtitleOverlayTheme.progress
        case .current:
            switch line.kind {
            case .original:
                return SubtitleOverlayTheme.originalCurrent
            case .translation, .unknown:
                return SubtitleOverlayTheme.translationCurrent
            case .transliteration:
                return SubtitleOverlayTheme.transliterationCurrent
            }
        case .future:
            switch line.kind {
            case .original:
                return SubtitleOverlayTheme.original
            case .translation, .unknown:
                return SubtitleOverlayTheme.translation
            case .transliteration:
                return SubtitleOverlayTheme.transliteration
            }
        }
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

    private var shouldReverseTokens: Bool {
        guard line.kind == .translation else { return false }
        return line.tokens.contains(where: containsRTLCharacters)
    }

    private func containsRTLCharacters(_ value: String) -> Bool {
        for scalar in value.unicodeScalars {
            let point = scalar.value
            if (0x0590...0x08FF).contains(point) || (0xFB1D...0xFEFF).contains(point) {
                return true
            }
        }
        return false
    }
}

private struct SubtitleTokenWordView: View {
    let text: String
    let color: Color
    let isSelected: Bool
    let fontScale: CGFloat
    let horizontalPadding: CGFloat
    let verticalPadding: CGFloat
    let cornerRadius: CGFloat
    let onDoubleTap: () -> Void

    var body: some View {
        Text(text)
            .lineLimit(1)
            .minimumScaleFactor(0.7)
            .allowsTightening(true)
            .font(tokenFont)
            .padding(.horizontal, horizontalPadding)
            .padding(.vertical, verticalPadding)
            .foregroundStyle(isSelected ? SubtitleOverlayTheme.selectionText : color)
            .background(
                Group {
                    if isSelected {
                        RoundedRectangle(cornerRadius: cornerRadius)
                            .fill(SubtitleOverlayTheme.selectionGlow)
                    }
                }
            )
            #if !os(tvOS)
            .simultaneousGesture(
                TapGesture(count: 2)
                    .onEnded(onDoubleTap)
            )
            #endif
    }

    private var tokenFont: Font {
        #if os(tvOS)
        let baseSize = UIFont.preferredFont(forTextStyle: .title2).pointSize
        return .system(size: baseSize * fontScale, weight: .semibold)
        #else
        let baseSize = UIFont.preferredFont(forTextStyle: .title3).pointSize
        return .system(size: baseSize * fontScale, weight: .semibold)
        #endif
    }
}

private struct TokenFlowLayout: Layout {
    let itemSpacing: CGFloat
    let lineSpacing: CGFloat

    private struct Line {
        var indices: [Int] = []
        var width: CGFloat = 0
        var height: CGFloat = 0
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
            let xStart = bounds.minX + max(0, (bounds.width - lineWidth) / 2)
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

private enum SubtitleTokenState {
    case past
    case current
    case future
}

enum VideoSubtitleTokenStyle {
    case base
    case highlightPrior
    case highlightCurrent
}

private enum SubtitleOverlayTheme {
    static let original = Color(red: 1.0, green: 0.831, blue: 0.0)
    static let translation = Color(red: 0.204, green: 0.827, blue: 0.6)
    static let transliteration = Color(red: 0.176, green: 0.831, blue: 0.749)
    static let progress = Color(red: 1.0, green: 0.549, blue: 0.0)
    static let selectionGlow = Color(red: 1.0, green: 0.549, blue: 0.0).opacity(0.6)
    static let selectionText = Color.black
    static let originalCurrent = Color.white
    static let translationCurrent = Color(red: 0.996, green: 0.941, blue: 0.541)
    static let transliterationCurrent = Color(red: 0.996, green: 0.976, blue: 0.765)
}
