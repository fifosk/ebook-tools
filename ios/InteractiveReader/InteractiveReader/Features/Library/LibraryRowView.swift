import SwiftUI
#if os(tvOS)
import UIKit
#endif

struct LibraryRowView: View {
    let item: LibraryItem
    let coverURL: URL?
    let resumeStatus: ResumeStatus
    var usesDarkBackground: Bool = false

    #if os(iOS)
    @Environment(\.horizontalSizeClass) private var horizontalSizeClass
    #endif
    #if os(tvOS)
    @Environment(\.isFocused) private var isFocused
    #endif

    var body: some View {
        #if os(tvOS)
        landscapeLayout
        #else
        if isCompactWidth {
            compactLayout
        } else {
            landscapeLayout
        }
        #endif
    }

    // MARK: - Compact Layout (iPhone Portrait)

    private var compactLayout: some View {
        HStack(alignment: .top, spacing: rowSpacing) {
            UnifiedCoverView(
                url: coverURL,
                variant: itemVariant,
                height: coverHeight
            )

            VStack(alignment: .leading, spacing: textSpacing) {
                Text(item.bookTitle.isEmpty ? "Untitled" : item.bookTitle)
                    .font(titleFont)
                    .lineLimit(2)
                    .minimumScaleFactor(0.9)
                    .truncationMode(.tail)

                Text(item.author.isEmpty ? "Unknown author" : item.author)
                    .font(authorFont)
                    .lineLimit(1)
                    .minimumScaleFactor(0.85)
                    .foregroundStyle(.secondary)

                if let summaryText {
                    Text(summaryText)
                        .font(metaFont)
                        .foregroundStyle(.tertiary)
                        .lineLimit(1)
                        .truncationMode(.tail)
                }

                if let descriptionText {
                    Text(descriptionText)
                        .font(metaFont)
                        .foregroundStyle(.tertiary)
                        .lineLimit(2)
                        .truncationMode(.tail)
                }

                HStack(spacing: 6) {
                    LanguageFlagPairView(flags: languageFlags)
                        .font(metaFont)

                    Text(resumeStatus.label)
                        .font(metaFont)
                        .lineLimit(1)
                        .minimumScaleFactor(0.8)
                        .foregroundStyle(resumeStatus.foreground)
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .background(resumeStatus.background, in: Capsule())
                }
            }

            Spacer(minLength: 4)

            VStack {
                #if !os(tvOS)
                OfflineSyncBadge(jobId: item.jobId, kind: .library, isEligible: true)
                #endif
                Spacer()
                Image(systemName: "chevron.right")
                    .foregroundStyle(.secondary)
                    .font(.caption)
            }
        }
        .padding(.vertical, rowPadding)
    }

    // MARK: - Landscape Layout (iPad / tvOS)

    private var landscapeLayout: some View {
        HStack(spacing: rowSpacing) {
            UnifiedCoverView(
                url: coverURL,
                variant: itemVariant,
                height: coverHeight
            )

            VStack(alignment: .leading, spacing: textSpacing) {
                Text(item.bookTitle.isEmpty ? "Untitled" : item.bookTitle)
                    .font(titleFont)
                    .lineLimit(titleLineLimit)
                    .minimumScaleFactor(titleScaleFactor)
                    .truncationMode(.tail)
                    .foregroundStyle(titleColor)

                Text(item.author.isEmpty ? "Unknown author" : item.author)
                    .font(authorFont)
                    .lineLimit(1)
                    .minimumScaleFactor(0.85)
                    .foregroundStyle(secondaryTextColor)

                if let summaryText {
                    Text(summaryText)
                        .font(metaFont)
                        .foregroundStyle(tertiaryTextColor)
                        .lineLimit(1)
                        .truncationMode(.tail)
                }

                if let descriptionText {
                    Text(descriptionText)
                        .font(metaFont)
                        .foregroundStyle(tertiaryTextColor)
                        .lineLimit(1)
                        .truncationMode(.tail)
                }

                HStack(spacing: 8) {
                    LanguageFlagPairView(flags: languageFlags)
                        .font(metaFont)

                    Text(resumeStatus.label)
                        .font(metaFont)
                        .lineLimit(1)
                        .minimumScaleFactor(0.8)
                        .foregroundStyle(resumeStatus.foreground)
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .background(resumeStatus.background, in: Capsule())
                }
            }

            Spacer()

            #if !os(tvOS)
            OfflineSyncBadge(jobId: item.jobId, kind: .library, isEligible: true)
            Image(systemName: "chevron.right")
                .foregroundStyle(secondaryTextColor)
            #endif
        }
        .padding(.vertical, rowPadding)
    }

    // MARK: - Layout Helpers

    private var isCompactWidth: Bool {
        #if os(iOS)
        return horizontalSizeClass == .compact
        #else
        return false
        #endif
    }

    private var languageFlags: [LanguageFlagEntry] {
        LanguageFlagResolver.resolveFlags(
            originalLanguage: originalLanguage,
            translationLanguage: translationLanguage
        )
    }

    private var originalLanguage: String? {
        metadataString(for: [
            "input_language",
            "original_language",
            "source_language",
            "translation_source_language",
            "book_language"
        ]) ?? item.language
    }

    private var translationLanguage: String? {
        metadataString(for: [
            "target_language",
            "translation_language",
            "target_languages",
            "book_language"
        ]) ?? metadataString(for: ["language"], maxDepth: 0) ?? item.language
    }

    private var jobTypeValue: String? {
        metadataString(for: ["job_type", "jobType", "type"], maxDepth: 2) ?? item.itemType
    }

    private var isTvSeries: Bool {
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

    private var tvMetadata: [String: JSONValue]? {
        guard let metadata = item.metadata else { return nil }
        return extractTvMediaMetadata(from: metadata)
    }

    private var itemVariant: PlayerChannelVariant {
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

    // MARK: - Summary Info

    private var summaryText: String? {
        var parts: [String] = []

        // Duration if available
        if let duration = formattedDuration {
            parts.append(duration)
        }

        // Sentence/segment count
        if let count = sentenceCount {
            let label = count == 1 ? "sentence" : "sentences"
            parts.append("\(count) \(label)")
        }

        return parts.isEmpty ? nil : parts.joined(separator: " · ")
    }

    /// Description/summary text for a second line (if available)
    private var descriptionText: String? {
        guard let metadata = item.metadata else { return nil }

        // TV episode summary
        if isTvSeries {
            if let summary = tvEpisodeSummary ?? tvShowSummary {
                return summary
            }
        }

        // Try direct path to book_metadata for book descriptions
        if let bookMeta = extractBookMetadata(from: metadata) {
            for key in ["book_summary", "summary", "description", "synopsis"] {
                if let desc = bookMeta[key]?.stringValue?.nonEmptyValue {
                    return desc
                }
            }
        }

        // Fallback to recursive search
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

    private var tvShowName: String? {
        guard let metadata = tvMetadata else { return nil }
        return metadata["show"]?.objectValue?["name"]?.stringValue
            ?? metadata["show"]?.objectValue?["title"]?.stringValue
    }

    private var tvSeasonNumber: Int? {
        guard let metadata = tvMetadata else { return nil }
        return metadata["episode"]?.objectValue?["season"]?.intValue
            ?? metadata["season"]?.intValue
    }

    private var tvEpisodeNumber: Int? {
        guard let metadata = tvMetadata else { return nil }
        return metadata["episode"]?.objectValue?["episode"]?.intValue
            ?? metadata["episode_number"]?.intValue
    }

    private var tvEpisodeName: String? {
        guard let metadata = tvMetadata else { return nil }
        return metadata["episode"]?.objectValue?["name"]?.stringValue
            ?? metadata["episode"]?.objectValue?["title"]?.stringValue
    }

    private var tvEpisodeSummary: String? {
        guard let metadata = tvMetadata else { return nil }
        return metadata["episode"]?.objectValue?["summary"]?.stringValue
    }

    private var tvShowSummary: String? {
        guard let metadata = tvMetadata else { return nil }
        return metadata["show"]?.objectValue?["summary"]?.stringValue
    }

    private var formattedDuration: String? {
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

    private var sentenceCount: Int? {
        guard let metadata = item.metadata else { return nil }

        // Try direct path to book_metadata first (most reliable for book jobs)
        if let bookMeta = extractBookMetadata(from: metadata) {
            for key in ["total_sentences", "book_sentence_count", "sentence_count"] {
                if let value = bookMeta[key]?.intValue, value > 0 {
                    return value
                }
            }
            // Check content_index nested structure
            if let contentIndex = bookMeta["content_index"]?.objectValue {
                for key in ["total_sentences", "sentence_total"] {
                    if let value = contentIndex[key]?.intValue, value > 0 {
                        return value
                    }
                }
            }
        }

        // Fallback to recursive search (handles various metadata structures)
        // Note: metadataString may return "123.0" for numeric values, so parse via Double first
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

    // MARK: - Styling

    private var coverHeight: CGFloat {
        CoverMetrics.rowHeight(isTV: isTV)
    }

    private var isTV: Bool {
        #if os(tvOS)
        return true
        #else
        return false
        #endif
    }

    private var titleFont: Font {
        #if os(tvOS)
        return scaledTVOSFont(.headline)
        #else
        return .headline
        #endif
    }

    private var authorFont: Font {
        #if os(tvOS)
        return scaledTVOSFont(.subheadline)
        #else
        return .subheadline
        #endif
    }

    private var metaFont: Font {
        #if os(tvOS)
        return scaledTVOSFont(.caption1)
        #else
        return .caption
        #endif
    }

    private var titleLineLimit: Int {
        #if os(tvOS)
        return 1
        #else
        return 2
        #endif
    }

    private var titleScaleFactor: CGFloat {
        #if os(tvOS)
        return 0.9
        #else
        return 0.95
        #endif
    }

    private var rowSpacing: CGFloat {
        #if os(tvOS)
        return 10
        #else
        return 12
        #endif
    }

    private var textSpacing: CGFloat {
        #if os(tvOS)
        return 3
        #else
        return 4
        #endif
    }

    private var rowPadding: CGFloat {
        #if os(tvOS)
        return 4
        #else
        return 6
        #endif
    }

    // MARK: - Text Colors (tvOS and iPad light mode use custom colors for readability)

    /// Whether to use light-on-dark color scheme (tvOS unfocused)
    private var useLightOnDarkColors: Bool {
        #if os(tvOS)
        return !isFocused
        #else
        return false
        #endif
    }

    /// Whether to use dark-on-light color scheme (tvOS focused only)
    private var useDarkOnLightColors: Bool {
        #if os(tvOS)
        return isFocused
        #else
        return false
        #endif
    }

    private var titleColor: Color {
        #if os(tvOS)
        if useLightOnDarkColors {
            return .white
        } else if useDarkOnLightColors {
            return .black
        }
        return Color.primary
        #elseif os(iOS)
        return usesDarkBackground ? .white : Color.primary
        #else
        return Color.primary
        #endif
    }

    private var secondaryTextColor: Color {
        #if os(tvOS)
        if useLightOnDarkColors {
            return .white.opacity(0.75)
        } else if useDarkOnLightColors {
            return .black.opacity(0.7)
        }
        return .gray
        #elseif os(iOS)
        return usesDarkBackground ? .white.opacity(0.75) : .gray
        #else
        return .gray
        #endif
    }

    private var tertiaryTextColor: Color {
        #if os(tvOS)
        if useLightOnDarkColors {
            return .white.opacity(0.6)
        } else if useDarkOnLightColors {
            return .black.opacity(0.55)
        }
        return .gray.opacity(0.6)
        #elseif os(iOS)
        return usesDarkBackground ? .white.opacity(0.6) : .gray.opacity(0.8)
        #else
        return .gray.opacity(0.6)
        #endif
    }

    // MARK: - Metadata Helpers

    private func metadataString(for keys: [String], maxDepth: Int = 4) -> String? {
        guard let metadata = item.metadata else { return nil }
        return metadataString(in: metadata, keys: keys, maxDepth: maxDepth)
    }

    private func metadataString(
        in metadata: [String: JSONValue],
        keys: [String],
        maxDepth: Int
    ) -> String? {
        for key in keys {
            if let found = metadataString(in: metadata, key: key, maxDepth: maxDepth) {
                return found
            }
        }
        return nil
    }

    private func metadataString(
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

    private func extractTvMediaMetadata(from metadata: [String: JSONValue]) -> [String: JSONValue]? {
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

    private func extractBookMetadata(from metadata: [String: JSONValue]) -> [String: JSONValue]? {
        let paths: [[String]] = [
            ["result", "book_metadata"],
            ["request", "inputs", "book_metadata"],
            ["book_metadata"]
        ]
        for path in paths {
            if let value = nestedValue(metadata, path: path)?.objectValue {
                return value
            }
        }
        return nil
    }

    private func nestedValue(_ source: [String: JSONValue], path: [String]) -> JSONValue? {
        var current: JSONValue = .object(source)
        for key in path {
            guard let object = current.objectValue, let next = object[key] else { return nil }
            current = next
        }
        return current
    }

    #if os(tvOS)
    private func scaledTVOSFont(_ style: UIFont.TextStyle) -> Font {
        let size = UIFont.preferredFont(forTextStyle: style).pointSize * 0.5
        return .system(size: size)
    }
    #endif
}

extension LibraryRowView {
    struct ResumeStatus: Equatable {
        let label: String
        let foreground: Color
        let background: Color

        private static var isTV: Bool {
            #if os(tvOS)
            return true
            #else
            return false
            #endif
        }

        static func none() -> ResumeStatus {
            ResumeStatus(
                label: "None",
                foreground: isTV ? .white.opacity(0.7) : .secondary,
                background: isTV ? Color.white.opacity(0.15) : Color.secondary.opacity(0.15)
            )
        }

        static func local(label: String) -> ResumeStatus {
            ResumeStatus(
                label: label,
                foreground: isTV ? .yellow : .orange,
                background: isTV ? Color.yellow.opacity(0.25) : Color.orange.opacity(0.2)
            )
        }

        static func cloud(label: String) -> ResumeStatus {
            // Use cyan/teal on tvOS for better contrast against blue focus backgrounds
            ResumeStatus(
                label: label,
                foreground: isTV ? .cyan : .blue,
                background: isTV ? Color.cyan.opacity(0.25) : Color.blue.opacity(0.2)
            )
        }

        static func both(label: String) -> ResumeStatus {
            ResumeStatus(
                label: label,
                foreground: .green,
                background: isTV ? Color.green.opacity(0.25) : Color.green.opacity(0.2)
            )
        }
    }
}
