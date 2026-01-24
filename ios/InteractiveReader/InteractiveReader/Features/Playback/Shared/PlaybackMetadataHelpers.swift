import Foundation

/// Shared metadata parsing utilities for playback views.
/// Consolidates duplicate metadata extraction logic.
enum PlaybackMetadataHelpers {
    static let summaryLengthLimit: Int = 320

    // MARK: - Summary Normalization

    static func normalizedSummary(_ value: String?, lengthLimit: Int = summaryLengthLimit) -> String? {
        guard var value = value?.trimmingCharacters(in: .whitespacesAndNewlines),
              !value.isEmpty
        else {
            return nil
        }
        value = value.replacingOccurrences(of: "<[^>]+>", with: " ", options: .regularExpression)
        value = value.replacingOccurrences(of: "\\s+", with: " ", options: .regularExpression)
        value = value.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !value.isEmpty else { return nil }
        if value.count > lengthLimit {
            let cutoff = max(lengthLimit - 3, 0)
            value = String(value.prefix(cutoff)).trimmingCharacters(in: .whitespacesAndNewlines) + "..."
        }
        return value
    }

    // MARK: - Metadata String Extraction

    static func metadataString(
        in metadata: [String: JSONValue],
        keys: [String],
        maxDepth: Int = 4
    ) -> String? {
        for key in keys {
            if let found = metadataString(in: metadata, key: key, maxDepth: maxDepth) {
                return found
            }
        }
        return nil
    }

    static func metadataString(
        in metadata: [String: JSONValue],
        key: String,
        maxDepth: Int
    ) -> String? {
        if let value = metadata[key]?.stringValue {
            return value
        }
        guard maxDepth > 0 else { return nil }
        for value in metadata.values {
            if let nested = value.objectValue {
                if let found = metadataString(in: nested, key: key, maxDepth: maxDepth - 1) {
                    return found
                }
            }
            if case let .array(items) = value {
                for entry in items {
                    if let nested = entry.objectValue,
                       let found = metadataString(in: nested, key: key, maxDepth: maxDepth - 1) {
                        return found
                    }
                }
            }
        }
        return nil
    }

    // MARK: - Nested Value Extraction

    static func nestedValue(_ source: [String: JSONValue], path: [String]) -> JSONValue? {
        var current: JSONValue = .object(source)
        for key in path {
            guard let object = current.objectValue, let next = object[key] else { return nil }
            current = next
        }
        return current
    }

    // MARK: - TV Metadata Extraction

    static func extractTvMediaMetadata(from metadata: [String: JSONValue]) -> [String: JSONValue]? {
        let paths: [[String]] = [
            ["result", "youtube_dub", "media_metadata"],
            ["result", "subtitle", "metadata", "media_metadata"],
            ["request", "media_metadata"],
            ["media_metadata"]
        ]
        for path in paths {
            if let value = nestedValue(metadata, path: path)?.objectValue {
                return value
            }
        }
        return nil
    }

    static func isTvSeriesMetadata(_ tvMetadata: [String: JSONValue]?) -> Bool {
        guard let tvMetadata else { return false }
        if let kind = tvMetadata["kind"]?.stringValue?.lowercased(),
           kind == "tv_episode" {
            return true
        }
        if tvMetadata["show"]?.objectValue != nil || tvMetadata["episode"]?.objectValue != nil {
            return true
        }
        return false
    }

    // MARK: - YouTube Metadata

    static func extractYoutubeMetadata(from tvMetadata: [String: JSONValue]?) -> [String: JSONValue]? {
        guard let tvMetadata,
              let youtube = tvMetadata["youtube"]?.objectValue
        else {
            return nil
        }
        return youtube
    }

    static func youtubeSummary(from youtubeMetadata: [String: JSONValue]?) -> String? {
        let summary = youtubeMetadata?["summary"]?.stringValue
        let description = youtubeMetadata?["description"]?.stringValue
        return normalizedSummary(summary ?? description)
    }

    static func tvSummary(from tvMetadata: [String: JSONValue]?) -> String? {
        guard let tvMetadata else { return nil }
        if let episode = tvMetadata["episode"]?.objectValue,
           let summary = episode["summary"]?.stringValue {
            return normalizedSummary(summary)
        }
        if let show = tvMetadata["show"]?.objectValue,
           let summary = show["summary"]?.stringValue {
            return normalizedSummary(summary)
        }
        return nil
    }

    // MARK: - Int Value Parsing

    static func intValue(_ value: JSONValue?) -> Int? {
        guard let value else { return nil }
        switch value {
        case let .number(number) where number.isFinite:
            return Int(number)
        case .string:
            return Int(value.stringValue ?? "")
        case let .array(values):
            for entry in values {
                if let parsed = intValue(entry) {
                    return parsed
                }
            }
            return nil
        default:
            return nil
        }
    }
}
