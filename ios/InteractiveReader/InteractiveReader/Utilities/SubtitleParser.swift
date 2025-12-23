import Foundation

struct SubtitleCue: Identifiable, Hashable {
    let id = UUID()
    let start: Double
    let end: Double
    let text: String
}

enum SubtitleParser {
    static func parse(from content: String) -> [SubtitleCue] {
        let trimmed = content.replacingOccurrences(of: "\r\n", with: "\n")
            .replacingOccurrences(of: "\r", with: "\n")
        if trimmed.trimmingCharacters(in: .whitespacesAndNewlines).hasPrefix("WEBVTT") {
            return parseWebVTT(trimmed)
        }
        return parseSRT(trimmed)
    }

    private static func parseWebVTT(_ content: String) -> [SubtitleCue] {
        let lines = content.components(separatedBy: "\n")
        return parseLines(lines)
    }

    private static func parseSRT(_ content: String) -> [SubtitleCue] {
        let lines = content.components(separatedBy: "\n")
        return parseLines(lines)
    }

    private static func parseLines(_ lines: [String]) -> [SubtitleCue] {
        var cues: [SubtitleCue] = []
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
                    textLines.append(textLine)
                    index += 1
                }
                if let start, let end {
                    let text = textLines.joined(separator: "\n").trimmingCharacters(in: .whitespacesAndNewlines)
                    if !text.isEmpty {
                        cues.append(SubtitleCue(start: start, end: end, text: text))
                    }
                }
            } else {
                index += 1
            }
            index += 1
        }
        return cues
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
}
