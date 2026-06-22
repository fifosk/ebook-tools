import SwiftUI

struct VideoSubtitleWordSelection: Equatable {
    let lineKind: VideoSubtitleLineKind
    let lineIndex: Int
    let tokenIndex: Int
}

struct VideoSubtitleWordSelectionRange: Equatable {
    let lineKind: VideoSubtitleLineKind
    let lineIndex: Int
    let anchorIndex: Int
    let focusIndex: Int

    var startIndex: Int {
        min(anchorIndex, focusIndex)
    }

    var endIndex: Int {
        max(anchorIndex, focusIndex)
    }
}

enum VideoSubtitleTokenCoordinateSpace {
    static let name = "VideoSubtitleTokens"
}

struct VideoSubtitleTokenFrame: Equatable {
    let lineKind: VideoSubtitleLineKind
    let lineIndex: Int
    let tokenIndex: Int
    let frame: CGRect
}

struct VideoSubtitleTokenFramePreferenceKey: PreferenceKey {
    static var defaultValue: [VideoSubtitleTokenFrame] = []

    static func reduce(value: inout [VideoSubtitleTokenFrame], nextValue: () -> [VideoSubtitleTokenFrame]) {
        value.append(contentsOf: nextValue())
    }
}

struct VideoSubtitleTokenReference: Equatable {
    let lineKind: VideoSubtitleLineKind
    let lineIndex: Int
    let tokenIndex: Int
    let token: String
    let seekTime: Double?
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
        guard let activeIndex = activeCueIndex(cues: cues, time: time) else {
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
        return lines
            .filter { !($0.text.isEmpty) && visibility.allows($0.kind) }
            .sorted { $0.kind.displayOrder < $1.kind.displayOrder }
    }

    // Uses start-sorted cues to avoid linear scans on large subtitle sets.
    private static func activeCueIndex(cues: [VideoSubtitleCue], time: Double) -> Int? {
        guard !cues.isEmpty, time.isFinite else { return nil }
        var low = 0
        var high = cues.count
        while low < high {
            let mid = (low + high) / 2
            if cues[mid].start <= time {
                low = mid + 1
            } else {
                high = mid
            }
        }
        let index = low - 1
        guard index >= 0 else { return nil }
        let cue = cues[index]
        guard time <= cue.end else { return nil }
        return index
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
