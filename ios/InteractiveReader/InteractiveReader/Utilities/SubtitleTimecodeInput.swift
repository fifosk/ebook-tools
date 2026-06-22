import Foundation

enum SubtitleTimecodeInput {
    static func normalize(
        _ value: String,
        allowRelative: Bool = false,
        emptyValue: String = ""
    ) -> String? {
        let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
        if trimmed.isEmpty {
            return emptyValue
        }
        if allowRelative, trimmed.hasPrefix("+") {
            guard let parsed = parseRelative(String(trimmed.dropFirst())) else {
                return nil
            }
            return "+\(formatRelativeDuration(parsed.seconds))"
        }
        return parseAbsolute(trimmed)?.normalized
    }

    private static func parseAbsolute(_ value: String) -> ParsedTimecode? {
        let parts = value.split(separator: ":", omittingEmptySubsequences: false)
        guard parts.count == 2 || parts.count == 3 else {
            return nil
        }
        let values = parts.compactMap { Int($0) }
        guard values.count == parts.count, values.allSatisfy({ $0 >= 0 }) else {
            return nil
        }

        if values.count == 3 {
            let hours = values[0]
            let minutes = values[1]
            let seconds = values[2]
            guard minutes < 60, seconds < 60 else {
                return nil
            }
            return ParsedTimecode(
                seconds: hours * 3600 + minutes * 60 + seconds,
                normalized: [hours, minutes, seconds].map(formatComponent).joined(separator: ":")
            )
        }

        let minutes = values[0]
        let seconds = values[1]
        guard seconds < 60 else {
            return nil
        }
        return ParsedTimecode(
            seconds: minutes * 60 + seconds,
            normalized: "\(formatComponent(minutes)):\(formatComponent(seconds))"
        )
    }

    private static func parseRelative(_ value: String) -> ParsedTimecode? {
        let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
        if !trimmed.isEmpty, trimmed.allSatisfy(\.isNumber) {
            guard let minutes = Int(trimmed), minutes >= 0 else {
                return nil
            }
            return ParsedTimecode(seconds: minutes * 60, normalized: formatRelativeDuration(minutes * 60))
        }
        guard let absolute = parseAbsolute(trimmed) else {
            return nil
        }
        return ParsedTimecode(seconds: absolute.seconds, normalized: formatRelativeDuration(absolute.seconds))
    }

    private static func formatRelativeDuration(_ totalSeconds: Int) -> String {
        let clamped = max(0, totalSeconds)
        if clamped >= 3600 {
            let hours = clamped / 3600
            let remainder = clamped % 3600
            let minutes = remainder / 60
            let seconds = remainder % 60
            return [hours, minutes, seconds].map(formatComponent).joined(separator: ":")
        }
        let minutes = clamped / 60
        let seconds = clamped % 60
        return "\(formatComponent(minutes)):\(formatComponent(seconds))"
    }

    private static func formatComponent(_ value: Int) -> String {
        String(format: "%02d", value)
    }

    private struct ParsedTimecode {
        let seconds: Int
        let normalized: String
    }
}
