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
    @EnvironmentObject var offlineStore: OfflineMediaStore
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
        rowLayout(
            accessoryStyle: .compact,
            titleLineLimit: 2,
            titleScaleFactor: 0.9,
            descriptionLineLimit: 2,
            badgeSpacing: 6,
            titleStyle: AnyShapeStyle(.primary),
            secondaryTextStyle: AnyShapeStyle(.secondary),
            tertiaryTextStyle: AnyShapeStyle(.tertiary),
            accessorySecondaryTextColor: .secondary
        )
    }

    // MARK: - Landscape Layout (iPad / tvOS)

    private var landscapeLayout: some View {
        rowLayout(
            accessoryStyle: .landscape,
            titleLineLimit: titleLineLimit,
            titleScaleFactor: titleScaleFactor,
            descriptionLineLimit: 1,
            badgeSpacing: 8,
            titleStyle: AnyShapeStyle(titleColor),
            secondaryTextStyle: AnyShapeStyle(secondaryTextColor),
            tertiaryTextStyle: AnyShapeStyle(tertiaryTextColor),
            accessorySecondaryTextColor: secondaryTextColor
        )
    }

    private func rowLayout(
        accessoryStyle: LibraryRowAccessoryStyle,
        titleLineLimit: Int,
        titleScaleFactor: CGFloat,
        descriptionLineLimit: Int,
        badgeSpacing: CGFloat,
        titleStyle: AnyShapeStyle,
        secondaryTextStyle: AnyShapeStyle,
        tertiaryTextStyle: AnyShapeStyle,
        accessorySecondaryTextColor: Color
    ) -> some View {
        LibraryRowLayout(
            coverURL: coverURL,
            variant: itemVariant,
            coverHeight: coverHeight,
            rowSpacing: rowSpacing,
            rowPadding: rowPadding,
            title: displayTitle,
            author: displayAuthor,
            summaryText: summaryText,
            descriptionText: descriptionText,
            languageFlags: languageFlags,
            resumeStatus: resumeStatus,
            titleFont: titleFont,
            authorFont: authorFont,
            metaFont: metaFont,
            textSpacing: textSpacing,
            titleLineLimit: titleLineLimit,
            titleScaleFactor: titleScaleFactor,
            descriptionLineLimit: descriptionLineLimit,
            badgeSpacing: badgeSpacing,
            titleStyle: titleStyle,
            secondaryTextStyle: secondaryTextStyle,
            tertiaryTextStyle: tertiaryTextStyle,
            accessoryJobId: item.jobId,
            accessoryStyle: accessoryStyle,
            accessorySecondaryTextColor: accessorySecondaryTextColor,
            isSynced: isLibrarySynced,
            isFocused: isRowFocused
        )
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

    private var displayTitle: String {
        item.bookTitle.isEmpty ? "Untitled" : item.bookTitle
    }

    private var displayAuthor: String {
        item.author.isEmpty ? "Unknown author" : item.author
    }

    private var isLibrarySynced: Bool {
        #if os(tvOS)
        offlineStore.status(for: item.jobId, kind: .library).isSynced
        #else
        false
        #endif
    }

    private var isRowFocused: Bool {
        #if os(tvOS)
        isFocused
        #else
        false
        #endif
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

        // Try direct path to media_metadata for book descriptions
        if let mediaMeta = extractMediaMetadata(from: metadata) {
            for key in ["book_summary", "summary", "description", "synopsis"] {
                if let desc = mediaMeta[key]?.stringValue?.nonEmptyValue {
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

        // Try direct path to media_metadata first (most reliable for book jobs)
        if let mediaMeta = extractMediaMetadata(from: metadata) {
            for key in ["total_sentences", "book_sentence_count", "sentence_count"] {
                if let value = mediaMeta[key]?.intValue, value > 0 {
                    return value
                }
            }
            // Check content_index nested structure
            if let contentIndex = mediaMeta["content_index"]?.objectValue {
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
        PlatformTypography.scaledFont(.headline)
    }

    private var authorFont: Font {
        PlatformTypography.scaledFont(.subheadline)
    }

    private var metaFont: Font {
        PlatformTypography.scaledFont(.caption1)
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

    // MARK: - Text Colors

    private var titleColor: Color {
        #if os(tvOS)
        PlatformColors.rowTitleColor(isFocused: isFocused)
        #else
        PlatformColors.rowTitleColor(usesDarkBackground: usesDarkBackground)
        #endif
    }

    private var secondaryTextColor: Color {
        #if os(tvOS)
        PlatformColors.rowSecondaryColor(isFocused: isFocused)
        #else
        PlatformColors.rowSecondaryColor(usesDarkBackground: usesDarkBackground)
        #endif
    }

    private var tertiaryTextColor: Color {
        #if os(tvOS)
        PlatformColors.rowTertiaryColor(isFocused: isFocused)
        #else
        PlatformColors.rowTertiaryColor(usesDarkBackground: usesDarkBackground)
        #endif
    }

    // MARK: - Metadata Helpers

    private func metadataString(for keys: [String], maxDepth: Int = 4) -> String? {
        guard let metadata = item.metadata else { return nil }
        return RowMetadataLookup.metadataString(in: metadata, keys: keys, maxDepth: maxDepth)
    }

    private func extractTvMediaMetadata(from metadata: [String: JSONValue]) -> [String: JSONValue]? {
        RowMetadataLookup.firstObject(in: metadata, paths: [
            ["result", "youtube_dub", "media_metadata"],
            ["result", "subtitle", "metadata", "media_metadata"],
            ["request", "media_metadata"],
            ["media_metadata"]
        ])
    }

    private func extractMediaMetadata(from metadata: [String: JSONValue]) -> [String: JSONValue]? {
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
