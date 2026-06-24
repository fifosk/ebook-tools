import SwiftUI

extension JobRowView {
    var languageFlags: [LanguageFlagEntry] {
        LanguageFlagResolver.resolveFlags(
            originalLanguage: inputLanguage,
            translationLanguage: translationLanguage
        )
    }

    var jobTitle: String {
        if let label = job.jobLabel?.nonEmptyValue {
            return label
        }
        if let title = job.result?.objectValue?["title"]?.stringValue?.nonEmptyValue {
            return title
        }
        if let book = (job.result?.objectValue?["media_metadata"] ?? job.result?.objectValue?["book_metadata"])?.objectValue,
           let title = book["title"]?.stringValue?.nonEmptyValue {
            return title
        }
        return "Job \(job.jobId)"
    }

    var summaryText: String? {
        var parts: [String] = []

        if !isTvSeries,
           let author = metadataString(for: [
               "book_author",
               "bookAuthor",
               "author",
               "creator",
               "channel",
               "uploader",
               "channel_title",
               "channelTitle"
           ], maxDepth: 6)?.nonEmptyValue {
            parts.append(author)
        }

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
        if isTvSeries,
           let summary = tvEpisodeSummary ?? tvShowSummary {
            return summary
        }

        if let creationSummaryText {
            return creationSummaryText
        }

        if let desc = metadataString(for: [
            "description",
            "book_description",
            "bookDescription",
            "summary",
            "synopsis"
        ], maxDepth: 6)?.nonEmptyValue {
            return desc
        }

        return nil
    }

    var progressLabel: String? {
        guard job.isActiveForDisplay else { return nil }
        guard let snapshot = job.readyProgressSnapshot else {
            if let healthTimelineLabel = job.healthTimelineLabel {
                return "Progress: preparing · \(healthTimelineLabel)"
            }
            if job.status == .pending {
                return "Progress: preparing"
            }
            return job.healthTimelineLabel
        }
        let healthSuffix = job.healthTimelineLabel.map { " · \($0)" } ?? ""
        if let total = snapshot.total, total > 0 {
            let percent = Int((Double(snapshot.completed) / Double(total)) * 100)
            return "Progress \(snapshot.completed)/\(total) · \(percent)%\(healthSuffix)"
        }
        return "Progress \(snapshot.completed)\(healthSuffix)"
    }

    var progressValue: Double? {
        guard job.isActiveForDisplay else { return nil }
        guard let snapshot = job.readyProgressSnapshot else { return nil }
        guard let total = snapshot.total, total > 0 else { return nil }
        return Double(snapshot.completed) / Double(total)
    }

    var statusGlyph: (icon: String, label: String) {
        switch job.displayStatus {
        case .pending:
            return ("⏳", "Pending")
        case .running:
            return ("▶️", "Running")
        case .pausing:
            return ("⏯️", "Pausing")
        case .paused:
            return ("⏸️", "Paused")
        case .completed:
            return ("✅", "Completed")
        case .failed:
            return ("❌", "Failed")
        case .cancelled:
            return ("🚫", "Cancelled")
        }
    }

    var statusGlyphFont: Font {
        #if os(iOS) || os(tvOS)
        let base = UIFont.preferredFont(forTextStyle: .caption1).pointSize
        return .system(size: base * 2.0)
        #else
        return .system(size: 28)
        #endif
    }

    var statusColor: Color {
        switch job.displayStatus {
        case .pending, .pausing:
            return PlatformColors.statusPendingColor
        case .running:
            return PlatformColors.statusActiveColor
        case .paused:
            return .yellow
        case .completed:
            return .green
        case .failed, .cancelled:
            return .red
        }
    }

    var jobVariant: PlayerChannelVariant {
        let type = job.jobType.lowercased()
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
        if type.contains("book") || type.contains("pipeline") {
            return .book
        }
        return .job
    }

    var progressTint: Color {
        CoverStyle.from(variant: jobVariant).iconColor
    }

    var coverURL: URL? {
        let youtubeFallback = resolveYoutubeThumbnailFallback()
        let supportsCover = jobVariant == .youtube || jobVariant == .video || jobVariant == .tv || jobVariant == .dub || jobVariant == .subtitles || jobVariant == .book
        guard supportsCover || youtubeFallback != nil else { return nil }
        let candidates = coverCandidates(youtubeFallback: youtubeFallback)
        for candidate in candidates {
            if let url = resolveCoverCandidate(candidate) {
                return url
            }
        }
        return nil
    }

    private var inputLanguage: String? {
        metadataString(for: [
            "input_language",
            "original_language",
            "source_language",
            "translation_source_language",
            "book_language"
        ]) ?? metadataString(for: ["language"], maxDepth: 0)
    }

    private var translationLanguage: String? {
        metadataString(for: [
            "target_language",
            "translation_language",
            "target_languages",
            "book_language"
        ]) ?? metadataString(for: ["language"], maxDepth: 0)
    }

    private var tvEpisodeSummary: String? {
        guard let metadata = tvMetadata else { return nil }
        return metadata["episode"]?.objectValue?["summary"]?.stringValue
    }

    private var tvShowSummary: String? {
        guard let metadata = tvMetadata else { return nil }
        return metadata["show"]?.objectValue?["summary"]?.stringValue
    }

    private var creationSummaryText: String? {
        if let summary = creationSummaryObject {
            if let warning = firstCreationString(in: summary, keys: ["warnings"]) {
                return "Creation warning: \(warning)"
            }
            if let message = firstCreationString(in: summary, keys: ["messages"]) {
                return "Creation: \(message)"
            }
            if let sample = firstCreationString(in: summary, keys: ["sentences_preview", "sentencesPreview"]) {
                return "Sample: \(sample)"
            }
            if let path = firstCreationString(in: summary, keys: ["epub_path", "epubPath"]) {
                return "Seed EPUB: \(path)"
            }
        }

        if let warning = metadataString(for: ["creation_warnings", "creationWarnings"], maxDepth: 6)?.nonEmptyValue {
            return "Creation warning: \(warning)"
        }
        if let message = metadataString(for: ["creation_messages", "creationMessages"], maxDepth: 6)?.nonEmptyValue {
            return "Creation: \(message)"
        }
        if let sample = metadataString(
            for: ["creation_sentences_preview", "creationSentencesPreview"],
            maxDepth: 6
        )?.nonEmptyValue {
            return "Sample: \(sample)"
        }
        if let path = metadataString(for: ["seed_epub_path", "seedEpubPath"], maxDepth: 6)?.nonEmptyValue {
            return "Seed EPUB: \(path)"
        }

        return nil
    }

    private var creationSummaryObject: [String: JSONValue]? {
        metadataValue(for: ["creation_summary", "creationSummary"], maxDepth: 6)?.objectValue
    }

    private func firstCreationString(in summary: [String: JSONValue], keys: [String]) -> String? {
        for key in keys {
            if let value = summary[key]?.stringValue?.nonEmptyValue {
                return value
            }
        }
        return nil
    }

    private var formattedDuration: String? {
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
        if let imageGen = job.imageGeneration,
           let total = imageGen["sentence_total"]?.intValue, total > 0 {
            return total
        }
        if let total = job.latestEvent?.snapshot.total, total > 0 {
            return total
        }
        if let count = metadataString(for: [
            "total_sentences",
            "totalSentences",
            "book_sentence_count",
            "bookSentenceCount",
            "sentence_count",
            "sentenceCount",
            "num_sentences",
            "numSentences"
        ], maxDepth: 6),
           let doubleValue = Double(count),
           doubleValue > 0 {
            return Int(doubleValue)
        }
        return nil
    }

    private func coverCandidates(youtubeFallback: String?) -> [String] {
        var candidates: [String] = []
        var seen = Set<String>()

        func add(_ value: String?) {
            guard let trimmed = value?.nonEmptyValue else { return }
            guard !seen.contains(trimmed) else { return }
            seen.insert(trimmed)
            candidates.append(trimmed)
        }

        add(metadataString(for: ["thumbnail"], maxDepth: 6))

        if let imageObj = metadataValue(for: ["image"], maxDepth: 6)?.objectValue {
            add(imageObj["original"]?.stringValue)
            add(imageObj["medium"]?.stringValue)
        }

        add(metadataString(for: ["cover_url", "cover", "poster", "poster_url"], maxDepth: 6))
        add(metadataString(for: ["job_cover_asset_url", "job_cover_asset", "book_cover_file"], maxDepth: 6))
        add(youtubeFallback)
        return candidates
    }

    private func resolveYoutubeThumbnailFallback() -> String? {
        guard jobVariant == .youtube || jobVariant == .video || jobVariant == .tv || jobVariant == .dub || jobVariant == .subtitles else {
            return nil
        }
        let sources = [
            job.jobLabel,
            metadataString(for: ["video_id", "videoId"], maxDepth: 6),
            metadataString(for: ["video_path", "subtitle_path", "source_name", "source_path"], maxDepth: 4),
            metadataString(for: ["input_file", "input_path"], maxDepth: 3),
        ]
        return JobRowCoverParsing.youtubeThumbnailFallback(from: sources)
    }

    private func resolveCoverCandidate(_ candidate: String) -> URL? {
        let trimmed = candidate.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return nil }
        let normalized = JobRowCoverParsing.normalizeCoverCandidate(trimmed)
        if let url = URL(string: normalized), url.scheme != nil {
            return appendAccessTokenIfNeeded(url)
        }
        guard let base = appState.apiBaseURL else {
            return URL(string: normalized)
        }
        if let url = URL(string: normalized, relativeTo: base) {
            return appendAccessTokenIfNeeded(url)
        }
        return nil
    }

    private func appendAccessTokenIfNeeded(_ url: URL) -> URL {
        guard let token = appState.authToken, !token.isEmpty else {
            return url
        }
        guard let apiHost = appState.apiBaseURL?.host?.lowercased(),
              let urlHost = url.host?.lowercased(),
              apiHost == urlHost
        else {
            return url
        }
        guard var components = URLComponents(url: url, resolvingAgainstBaseURL: true) else {
            return url
        }
        var items = components.queryItems ?? []
        if items.contains(where: { $0.name == "access_token" }) {
            return url
        }
        items.append(URLQueryItem(name: "access_token", value: token))
        components.queryItems = items
        return components.url ?? url
    }

    private func metadataString(for keys: [String], maxDepth: Int = 4) -> String? {
        RowMetadataLookup.metadataString(in: metadataSources, keys: keys, maxDepth: maxDepth)
    }

    private func metadataValue(for keys: [String], maxDepth: Int = 4) -> JSONValue? {
        RowMetadataLookup.metadataValue(in: metadataSources, keys: keys, maxDepth: maxDepth)
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
        RowMetadataLookup.firstObject(in: metadataSources, paths: jobTvMetadataPaths)
    }

    private var metadataSources: [[String: JSONValue]] {
        [job.result?.objectValue, job.parameters?.objectValue].compactMap { $0 }
    }

    private var jobTvMetadataPaths: [[String]] {
        [
            ["youtube_dub", "media_metadata"],
            ["subtitle", "metadata", "media_metadata"],
            ["result", "youtube_dub", "media_metadata"],
            ["result", "subtitle", "metadata", "media_metadata"],
            ["request", "media_metadata"],
            ["media_metadata"]
        ]
    }
}
