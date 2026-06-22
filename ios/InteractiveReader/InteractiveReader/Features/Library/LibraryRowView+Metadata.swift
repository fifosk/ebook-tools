import SwiftUI

extension LibraryRowView {
    var languageFlags: [LanguageFlagEntry] {
        LanguageFlagResolver.resolveFlags(
            originalLanguage: originalLanguage,
            translationLanguage: translationLanguage
        )
    }

    var displayTitle: String {
        item.bookTitle.isEmpty ? "Untitled" : item.bookTitle
    }

    var displayAuthor: String {
        item.author.isEmpty ? "Unknown author" : item.author
    }

    var originalLanguage: String? {
        metadataString(for: [
            "input_language",
            "original_language",
            "source_language",
            "translation_source_language",
            "book_language"
        ]) ?? item.language
    }

    var translationLanguage: String? {
        metadataString(for: [
            "target_language",
            "translation_language",
            "target_languages",
            "book_language"
        ]) ?? metadataString(for: ["language"], maxDepth: 0) ?? item.language
    }

    var jobTypeValue: String? {
        metadataString(for: ["job_type", "jobType", "type"], maxDepth: 2) ?? item.itemType
    }

    var isTvSeries: Bool {
        guard let metadata = tvMetadata else { return false }
        if let kind = metadata["kind"]?.stringValue?.lowercased(),
           kind == "tv_episode" {
            return true
        }
        if metadata["show"]?.objectValue != nil || metadata["episode"]?.objectValue != nil {
            return true
        }
        return false
    }

    var tvMetadata: [String: JSONValue]? {
        guard let metadata = item.metadata else { return nil }
        return extractTvMediaMetadata(from: metadata)
    }

    var itemVariant: PlayerChannelVariant {
        let type = (jobTypeValue ?? "").lowercased()
        if isTvSeries {
            return .tv
        }
        if type.contains("youtube") {
            return .youtube
        }
        if type.contains("dub") {
            return .dub
        }
        if type.contains("subtitle") {
            return .subtitles
        }
        if type.contains("video") {
            return .video
        }
        if type.contains("nas") {
            return .nas
        }
        if type.contains("book") || type.contains("pipeline") || type.isEmpty {
            return .book
        }
        return .job
    }

    var summaryText: String? {
        var parts: [String] = []

        if let duration = formattedDuration {
            parts.append(duration)
        }

        if let count = sentenceCount {
            let label = count == 1 ? "sentence" : "sentences"
            parts.append("\(count) \(label)")
        }

        return parts.isEmpty ? nil : parts.joined(separator: " · ")
    }

    var descriptionText: String? {
        guard let metadata = item.metadata else { return nil }

        if isTvSeries {
            if let summary = tvEpisodeSummary ?? tvShowSummary {
                return summary
            }
        }

        if let mediaMeta = extractMediaMetadata(from: metadata) {
            for key in ["book_summary", "summary", "description", "synopsis"] {
                if let desc = mediaMeta[key]?.stringValue?.nonEmptyValue {
                    return desc
                }
            }
        }

        if let desc = metadataString(for: [
            "description",
            "book_description",
            "bookDescription",
            "book_summary",
            "bookSummary",
            "summary",
            "synopsis"
        ], maxDepth: 6)?.nonEmptyValue {
            return desc
        }

        return nil
    }

    var tvShowName: String? {
        guard let metadata = tvMetadata else { return nil }
        return metadata["show"]?.objectValue?["name"]?.stringValue
            ?? metadata["show"]?.objectValue?["title"]?.stringValue
    }

    var tvSeasonNumber: Int? {
        guard let metadata = tvMetadata else { return nil }
        return metadata["episode"]?.objectValue?["season"]?.intValue
            ?? metadata["season"]?.intValue
    }

    var tvEpisodeNumber: Int? {
        guard let metadata = tvMetadata else { return nil }
        return metadata["episode"]?.objectValue?["episode"]?.intValue
            ?? metadata["episode_number"]?.intValue
    }

    var tvEpisodeName: String? {
        guard let metadata = tvMetadata else { return nil }
        return metadata["episode"]?.objectValue?["name"]?.stringValue
            ?? metadata["episode"]?.objectValue?["title"]?.stringValue
    }

    var tvEpisodeSummary: String? {
        guard let metadata = tvMetadata else { return nil }
        return metadata["episode"]?.objectValue?["summary"]?.stringValue
    }

    var tvShowSummary: String? {
        guard let metadata = tvMetadata else { return nil }
        return metadata["show"]?.objectValue?["summary"]?.stringValue
    }

    var formattedDuration: String? {
        guard item.metadata != nil else { return nil }
        guard let seconds = metadataString(for: [
            "duration",
            "duration_seconds",
            "durationSeconds",
            "length_seconds",
            "lengthSeconds",
            "video_duration",
            "videoDuration",
            "audio_duration",
            "audioDuration"
        ], maxDepth: 6),
              let value = Double(seconds), value > 0 else {
            return nil
        }
        let minutes = Int(value) / 60
        let secs = Int(value) % 60
        if minutes >= 60 {
            let hours = minutes / 60
            let mins = minutes % 60
            return "\(hours)h \(mins)m"
        }
        return "\(minutes):\(String(format: "%02d", secs))"
    }

    var sentenceCount: Int? {
        guard let metadata = item.metadata else { return nil }

        if let mediaMeta = extractMediaMetadata(from: metadata) {
            for key in ["total_sentences", "book_sentence_count", "sentence_count"] {
                if let value = mediaMeta[key]?.intValue, value > 0 {
                    return value
                }
            }
            if let contentIndex = mediaMeta["content_index"]?.objectValue {
                for key in ["total_sentences", "sentence_total"] {
                    if let value = contentIndex[key]?.intValue, value > 0 {
                        return value
                    }
                }
            }
        }

        if let count = metadataString(for: [
            "total_sentences",
            "totalSentences",
            "book_sentence_count",
            "bookSentenceCount",
            "sentence_count",
            "sentenceCount",
            "num_sentences",
            "numSentences",
            "sentence_total",
            "sentenceTotal"
        ], maxDepth: 8),
           let doubleValue = Double(count),
           doubleValue > 0 {
            return Int(doubleValue)
        }
        return nil
    }

    func metadataString(for keys: [String], maxDepth: Int = 4) -> String? {
        guard let metadata = item.metadata else { return nil }
        return RowMetadataLookup.metadataString(in: metadata, keys: keys, maxDepth: maxDepth)
    }

    func extractTvMediaMetadata(from metadata: [String: JSONValue]) -> [String: JSONValue]? {
        RowMetadataLookup.firstObject(in: metadata, paths: [
            ["result", "youtube_dub", "media_metadata"],
            ["result", "subtitle", "metadata", "media_metadata"],
            ["request", "media_metadata"],
            ["media_metadata"]
        ])
    }

    func extractMediaMetadata(from metadata: [String: JSONValue]) -> [String: JSONValue]? {
        RowMetadataLookup.firstObject(in: metadata, paths: [
            ["result", "media_metadata"],
            ["result", "book_metadata"],
            ["request", "inputs", "media_metadata"],
            ["request", "inputs", "book_metadata"],
            ["media_metadata"],
            ["book_metadata"]
        ])
    }
}
