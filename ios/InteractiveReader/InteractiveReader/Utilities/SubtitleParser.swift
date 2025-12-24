import Foundation

enum SubtitleFormat: String {
    case ass
    case vtt
    case srt
    case unknown

    var label: String {
        switch self {
        case .ass:
            return "ASS"
        case .vtt:
            return "VTT"
        case .srt:
            return "SRT"
        case .unknown:
            return "SUB"
        }
    }

    var priority: Int {
        switch self {
        case .ass:
            return 0
        case .vtt:
            return 1
        case .srt:
            return 2
        case .unknown:
            return 3
        }
    }
}

struct VideoSubtitleTrack: Identifiable, Hashable {
    let id: String
    let url: URL
    let format: SubtitleFormat
    let label: String
}

struct VideoSubtitleSpan: Hashable {
    let text: String
    let colorHex: String?
    let isBold: Bool
    let scale: Double
}

enum VideoSubtitleLineKind: String {
    case original
    case translation
    case transliteration
    case unknown
}

struct VideoSubtitleLine: Hashable {
    let text: String
    let spans: [VideoSubtitleSpan]?
    let kind: VideoSubtitleLineKind
}

struct VideoSubtitleCue: Identifiable {
    let id = UUID()
    let start: Double
    let end: Double
    let text: String
    let spans: [VideoSubtitleSpan]?
    let lines: [VideoSubtitleLine]
}

enum SubtitleParser {
    static func parse(from content: String, format: SubtitleFormat? = nil) -> [VideoSubtitleCue] {
        let resolvedFormat = format ?? detectFormat(content)
        switch resolvedFormat {
        case .ass:
            return parseASS(content)
        case .vtt:
            return parseWebVTT(content)
        case .srt:
            return parseSRT(content)
        case .unknown:
            return parseSRT(content)
        }
    }

    static func format(for path: String?) -> SubtitleFormat {
        guard let path, !path.isEmpty else { return .unknown }
        let trimmed = path.split(separator: "?").first.map(String.init) ?? path
        let ext = trimmed.split(separator: ".").last?.lowercased() ?? ""
        switch ext {
        case "ass":
            return .ass
        case "vtt":
            return .vtt
        case "srt":
            return .srt
        default:
            return .unknown
        }
    }

    private static func detectFormat(_ content: String) -> SubtitleFormat {
        let trimmed = content.trimmingCharacters(in: .whitespacesAndNewlines)
        if trimmed.uppercased().hasPrefix("WEBVTT") {
            return .vtt
        }
        if trimmed.contains("[Script Info]") || trimmed.contains("[V4+ Styles]") || trimmed.contains("[Events]") {
            return .ass
        }
        return .srt
    }

    private static func parseWebVTT(_ content: String) -> [VideoSubtitleCue] {
        let lines = normalizeLines(content)
        return parseLines(lines)
    }

    private static func parseSRT(_ content: String) -> [VideoSubtitleCue] {
        let lines = normalizeLines(content)
        return parseLines(lines)
    }

    private static func parseLines(_ lines: [String]) -> [VideoSubtitleCue] {
        var cues: [VideoSubtitleCue] = []
        var index = 0
        while index < lines.count {
            let line = lines[index].trimmingCharacters(in: .whitespaces)
            if line.isEmpty || line.allSatisfy({ $0.isNumber }) {
                index += 1
                continue
            }
            if line.contains("-->") {
                let parts = line.components(separatedBy: "-->")
                guard parts.count >= 2 else {
                    index += 1
                    continue
                }
                let start = parseTimecode(parts[0].trimmingCharacters(in: .whitespaces))
                let end = parseTimecode(parts[1].split(separator: " ").first.map(String.init) ?? "")
                index += 1
                var textLines: [String] = []
                while index < lines.count {
                    let textLine = lines[index]
                    if textLine.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                        break
                    }
                    textLines.append(stripMarkup(textLine))
                    index += 1
                }
                if let start, let end {
                    let text = textLines.joined(separator: "\n").trimmingCharacters(in: .whitespacesAndNewlines)
                    if !text.isEmpty {
                        let lines = buildPlainLines(from: text)
                        cues.append(VideoSubtitleCue(start: start, end: end, text: text, spans: nil, lines: lines))
                    }
                }
            } else {
                index += 1
            }
            index += 1
        }
        return cues
    }

    private static func parseASS(_ content: String) -> [VideoSubtitleCue] {
        let lines = normalizeLines(content)
        var cues: [VideoSubtitleCue] = []
        var inEvents = false
        var formatFields: [String] = []
        var startIndex: Int?
        var endIndex: Int?
        var textIndex: Int?

        for rawLine in lines {
            let line = rawLine.trimmingCharacters(in: .whitespacesAndNewlines)
            if line.isEmpty {
                continue
            }
            if line.hasPrefix("[Events]") {
                inEvents = true
                continue
            }
            guard inEvents else { continue }

            if line.lowercased().hasPrefix("format:") {
                let formatLine = line.dropFirst("format:".count)
                let fields = formatLine.split(separator: ",").map { $0.trimmingCharacters(in: .whitespaces) }
                formatFields = fields.map { $0.lowercased() }
                startIndex = formatFields.firstIndex(of: "start")
                endIndex = formatFields.firstIndex(of: "end")
                textIndex = formatFields.firstIndex(of: "text")
                continue
            }

            if line.lowercased().hasPrefix("dialogue:") {
                guard let startIndex, let endIndex, let textIndex else { continue }
                let payload = line.dropFirst("dialogue:".count).trimmingCharacters(in: .whitespaces)
                let parts = payload.split(separator: ",", maxSplits: max(0, formatFields.count - 1), omittingEmptySubsequences: false)
                guard parts.count >= formatFields.count else { continue }
                let startValue = String(parts[startIndex]).trimmingCharacters(in: .whitespaces)
                let endValue = String(parts[endIndex]).trimmingCharacters(in: .whitespaces)
                let textValue = String(parts[textIndex])
                guard let start = parseASSTimecode(startValue), let end = parseASSTimecode(endValue) else { continue }
                let parsed = parseASSLines(textValue)
                let cleaned = parsed.text.trimmingCharacters(in: .whitespacesAndNewlines)
                guard !cleaned.isEmpty else { continue }
                cues.append(
                    VideoSubtitleCue(
                        start: start,
                        end: end,
                        text: cleaned,
                        spans: parsed.spans,
                        lines: parsed.lines
                    )
                )
            }
        }
        return cues
    }

    private static func parseASSLines(
        _ value: String
    ) -> (text: String, spans: [VideoSubtitleSpan]?, lines: [VideoSubtitleLine]) {
        let normalized = value
            .replacingOccurrences(of: "\\\\N", with: "\n")
            .replacingOccurrences(of: "\\\\n", with: "\n")
            .replacingOccurrences(of: "\\\\h", with: " ")
            .replacingOccurrences(of: "\\N", with: "\n")
            .replacingOccurrences(of: "\\n", with: "\n")
            .replacingOccurrences(of: "\\h", with: " ")

        var spans: [VideoSubtitleSpan] = []
        var buffer = ""
        var style = AssStyle()
        var hasTags = false

        var index = normalized.startIndex
        while index < normalized.endIndex {
            let char = normalized[index]
            if char == "{" {
                if let close = normalized[index...].firstIndex(of: "}") {
                    if !buffer.isEmpty {
                        spans.append(VideoSubtitleSpan(
                            text: buffer,
                            colorHex: style.colorHex,
                            isBold: style.isBold,
                            scale: style.scale
                        ))
                        buffer.removeAll()
                    }
                    let tagContent = String(normalized[normalized.index(after: index)..<close])
                    if tagContent.contains("\\") {
                        hasTags = true
                        style = applyAssTags(tagContent, to: style)
                    }
                    index = normalized.index(after: close)
                    continue
                }
            }
            if char == "\\" {
                let nextIndex = normalized.index(after: index)
                if nextIndex < normalized.endIndex {
                    let nextChar = normalized[nextIndex]
                    if nextChar == "{" || nextChar == "}" {
                        buffer.append(nextChar)
                        index = normalized.index(after: nextIndex)
                        continue
                    }
                }
            }
            buffer.append(char)
            index = normalized.index(after: index)
        }
        if !buffer.isEmpty {
            spans.append(VideoSubtitleSpan(
                text: buffer,
                colorHex: style.colorHex,
                isBold: style.isBold,
                scale: style.scale
            ))
        }

        let text = spans.map(\.text).joined()
        let resolvedSpans = hasTags ? spans : nil
        let lines = buildLines(from: text, spans: resolvedSpans)
        return (text, resolvedSpans, lines)
    }

    private static func normalizeLines(_ content: String) -> [String] {
        content.replacingOccurrences(of: "\r\n", with: "\n")
            .replacingOccurrences(of: "\r", with: "\n")
            .components(separatedBy: "\n")
    }

    private static func stripMarkup(_ value: String) -> String {
        guard value.contains("<") else { return value }
        let pattern = "<[^>]+>"
        let regex = try? NSRegularExpression(pattern: pattern, options: [])
        let range = NSRange(value.startIndex..., in: value)
        return regex?.stringByReplacingMatches(in: value, options: [], range: range, withTemplate: "") ?? value
    }

    private static func parseTimecode(_ value: String) -> Double? {
        let cleaned = value.replacingOccurrences(of: ",", with: ".")
        let parts = cleaned.split(separator: ":").map(String.init)
        guard !parts.isEmpty else { return nil }
        var seconds: Double = 0
        if parts.count == 3 {
            let hours = Double(parts[0]) ?? 0
            let minutes = Double(parts[1]) ?? 0
            let secs = Double(parts[2]) ?? 0
            seconds = hours * 3600 + minutes * 60 + secs
        } else if parts.count == 2 {
            let minutes = Double(parts[0]) ?? 0
            let secs = Double(parts[1]) ?? 0
            seconds = minutes * 60 + secs
        } else if let secs = Double(parts[0]) {
            seconds = secs
        }
        return seconds.isFinite ? seconds : nil
    }

    private static func parseASSTimecode(_ value: String) -> Double? {
        let cleaned = value.replacingOccurrences(of: ",", with: ".")
        let parts = cleaned.split(separator: ":").map(String.init)
        guard parts.count >= 2 else { return parseTimecode(cleaned) }
        var seconds: Double = 0
        if parts.count == 3 {
            let hours = Double(parts[0]) ?? 0
            let minutes = Double(parts[1]) ?? 0
            let secs = Double(parts[2]) ?? 0
            seconds = hours * 3600 + minutes * 60 + secs
        } else if parts.count == 2 {
            let minutes = Double(parts[0]) ?? 0
            let secs = Double(parts[1]) ?? 0
            seconds = minutes * 60 + secs
        }
        return seconds.isFinite ? seconds : nil
    }

    private static func applyAssTags(_ content: String, to style: AssStyle) -> AssStyle {
        var updated = style
        var index = content.startIndex
        while index < content.endIndex {
            guard content[index] == "\\" else {
                index = content.index(after: index)
                continue
            }
            index = content.index(after: index)
            var name = ""
            while index < content.endIndex && content[index].isAssTagName {
                name.append(content[index])
                index = content.index(after: index)
            }
            var value = ""
            while index < content.endIndex && content[index] != "\\" {
                value.append(content[index])
                index = content.index(after: index)
            }
            let token = name.lowercased()
            if token == "c" || token == "1c" {
                updated.colorHex = parseASSColor(value) ?? updated.colorHex
            } else if token == "b" {
                let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
                if let numeric = Int(trimmed) {
                    updated.isBold = numeric != 0
                }
            } else if token == "fscx" || token == "fscy" {
                let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
                if let numeric = Double(trimmed), numeric > 0 {
                    updated.scale = numeric / 100.0
                }
            } else if token == "r" {
                updated = AssStyle()
            }
        }
        return updated
    }

    private static func parseASSColor(_ value: String) -> String? {
        let cleaned = value
            .replacingOccurrences(of: "&H", with: "")
            .replacingOccurrences(of: "&", with: "")
            .trimmingCharacters(in: .whitespacesAndNewlines)
        guard !cleaned.isEmpty else { return nil }
        let hex = cleaned.count >= 6 ? String(cleaned.suffix(6)) : cleaned
        guard hex.count == 6 else { return nil }
        let b = hex.prefix(2)
        let g = hex.dropFirst(2).prefix(2)
        let r = hex.dropFirst(4).prefix(2)
        return "#\(r)\(g)\(b)".uppercased()
    }

    private static func buildPlainLines(from text: String) -> [VideoSubtitleLine] {
        let fragments = text.split(separator: "\n", omittingEmptySubsequences: false)
        if fragments.isEmpty {
            return []
        }
        return fragments.map { fragment in
            VideoSubtitleLine(text: String(fragment), spans: nil, kind: .translation)
        }
    }

    private static func buildLines(from text: String, spans: [VideoSubtitleSpan]?) -> [VideoSubtitleLine] {
        guard let spans, !spans.isEmpty else {
            return buildPlainLines(from: text)
        }
        let splitSpans = splitSpansByNewlines(spans)
        if splitSpans.isEmpty {
            return buildPlainLines(from: text)
        }
        var lines = splitSpans.map { lineSpans -> VideoSubtitleLine in
            let lineText = lineSpans.map(\.text).joined()
            return VideoSubtitleLine(text: lineText, spans: lineSpans, kind: .unknown)
        }
        lines = assignLineKinds(lines)
        return lines
    }

    private static func splitSpansByNewlines(
        _ spans: [VideoSubtitleSpan]
    ) -> [[VideoSubtitleSpan]] {
        var lines: [[VideoSubtitleSpan]] = [[]]
        for span in spans {
            let parts = span.text.split(separator: "\n", omittingEmptySubsequences: false)
            for (index, part) in parts.enumerated() {
                if index > 0 {
                    lines.append([])
                }
                if !part.isEmpty {
                    let updated = VideoSubtitleSpan(
                        text: String(part),
                        colorHex: span.colorHex,
                        isBold: span.isBold,
                        scale: span.scale
                    )
                    lines[lines.count - 1].append(updated)
                }
            }
        }
        return lines
    }

    private static func assignLineKinds(_ lines: [VideoSubtitleLine]) -> [VideoSubtitleLine] {
        guard !lines.isEmpty else { return lines }
        var updated = lines
        let originalIndex = lines.firstIndex { lineContainsOriginalColor($0) }
        if let originalIndex {
            updated[originalIndex] = VideoSubtitleLine(
                text: updated[originalIndex].text,
                spans: updated[originalIndex].spans,
                kind: .original
            )
        }
        let remaining = lines.indices.filter { $0 != originalIndex }
        if originalIndex == nil {
            if remaining.count == 1 {
                let idx = remaining[0]
                updated[idx] = VideoSubtitleLine(
                    text: updated[idx].text,
                    spans: updated[idx].spans,
                    kind: .translation
                )
            } else if remaining.count >= 2 {
                updated[remaining[0]] = VideoSubtitleLine(
                    text: updated[remaining[0]].text,
                    spans: updated[remaining[0]].spans,
                    kind: .translation
                )
                updated[remaining[1]] = VideoSubtitleLine(
                    text: updated[remaining[1]].text,
                    spans: updated[remaining[1]].spans,
                    kind: .transliteration
                )
            }
            return updated
        }
        if remaining.count == 1, let idx = remaining.first {
            updated[idx] = VideoSubtitleLine(
                text: updated[idx].text,
                spans: updated[idx].spans,
                kind: .translation
            )
            return updated
        }
        if remaining.count >= 2 {
            let translationIndex = remaining[0]
            let transliterationIndex = remaining[1]
            updated[translationIndex] = VideoSubtitleLine(
                text: updated[translationIndex].text,
                spans: updated[translationIndex].spans,
                kind: .translation
            )
            updated[transliterationIndex] = VideoSubtitleLine(
                text: updated[transliterationIndex].text,
                spans: updated[transliterationIndex].spans,
                kind: .transliteration
            )
        }
        return updated
    }

    private static func lineContainsOriginalColor(_ line: VideoSubtitleLine) -> Bool {
        guard let spans = line.spans else { return false }
        return spans.contains { span in
            span.colorHex?.caseInsensitiveCompare("#FFD60A") == .orderedSame
        }
    }
}

private struct AssStyle {
    var colorHex: String? = nil
    var isBold: Bool = false
    var scale: Double = 1.0
}

private extension Character {
    var isAssTagName: Bool {
        unicodeScalars.allSatisfy { CharacterSet.alphanumerics.contains($0) }
    }
}
