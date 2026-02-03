import SwiftUI
#if os(tvOS)
import UIKit
#endif

struct JobRowView: View {
    @EnvironmentObject var appState: AppState
    let job: PipelineStatusResponse
    let resumeStatus: LibraryRowView.ResumeStatus
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
        HStack(alignment: .top, spacing: rowSpacing) {
            UnifiedCoverView(
                url: coverURL,
                variant: jobVariant,
                height: coverHeight
            )

            VStack(alignment: .leading, spacing: textSpacing) {
                Text(jobTitle)
                    .font(titleFont)
                    .lineLimit(2)
                    .minimumScaleFactor(0.9)
                    .truncationMode(.tail)

                if let summaryText {
                    Text(summaryText)
                        .font(summaryFont)
                        .foregroundStyle(.secondary)
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

                    Text(statusGlyph.icon)
                        .font(statusGlyphFont)
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .foregroundStyle(statusColor)
                        .background(statusColor.opacity(0.18), in: Capsule())
                        .accessibilityLabel(statusGlyph.label)

                    Text(resumeStatus.label)
                        .font(metaFont)
                        .lineLimit(1)
                        .minimumScaleFactor(0.8)
                        .foregroundStyle(resumeStatus.foreground)
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .background(resumeStatus.background, in: Capsule())
                }

                if let progressLabel {
                    Text(progressLabel)
                        .font(metaFont)
                        .foregroundStyle(.secondary)
                        .lineLimit(1)
                        .minimumScaleFactor(0.75)
                }

                if let progressValue {
                    ProgressView(value: progressValue)
                        .tint(progressTint)
                }
            }

            Spacer(minLength: 4)

            VStack {
                #if !os(tvOS)
                if job.isFinishedForDisplay {
                    OfflineSyncBadge(jobId: job.jobId, kind: .job, isEligible: true)
                }
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
                variant: jobVariant,
                height: coverHeight
            )

            VStack(alignment: .leading, spacing: textSpacing) {
                Text(jobTitle)
                    .font(titleFont)
                    .lineLimit(titleLineLimit)
                    .minimumScaleFactor(titleScaleFactor)
                    .truncationMode(.tail)
                    .foregroundStyle(titleColor)

                if let summaryText {
                    Text(summaryText)
                        .font(summaryFont)
                        .foregroundStyle(secondaryTextColor)
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

                    Text(statusGlyph.icon)
                        .font(statusGlyphFont)
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .foregroundStyle(statusColor)
                        .background(statusColor.opacity(0.18), in: Capsule())
                        .accessibilityLabel(statusGlyph.label)

                    Text(resumeStatus.label)
                        .font(metaFont)
                        .lineLimit(1)
                        .minimumScaleFactor(0.8)
                        .foregroundStyle(resumeStatus.foreground)
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .background(resumeStatus.background, in: Capsule())
                }

                if let progressLabel {
                    Text(progressLabel)
                        .font(metaFont)
                        .foregroundStyle(secondaryTextColor)
                        .lineLimit(1)
                        .minimumScaleFactor(0.75)
                }

                if let progressValue {
                    ProgressView(value: progressValue)
                        .tint(progressTint)
                }
            }

            Spacer()

            #if os(tvOS)
            // Show download indicator on tvOS
            if job.isFinishedForDisplay && offlineStore.status(for: job.jobId, kind: .job).isSynced {
                Image(systemName: "arrow.down.circle.fill")
                    .font(.system(size: 18, weight: .semibold))
                    .foregroundStyle(isFocused ? .black.opacity(0.6) : .green)
            }
            #else
            if job.isFinishedForDisplay {
                OfflineSyncBadge(jobId: job.jobId, kind: .job, isEligible: true)
            }
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
            originalLanguage: inputLanguage,
            translationLanguage: translationLanguage
        )
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

    private var jobTitle: String {
        if let label = job.jobLabel?.nonEmptyValue {
            return label
        }
        if let title = job.result?.objectValue?["title"]?.stringValue?.nonEmptyValue {
            return title
        }
        if let book = job.result?.objectValue?["book_metadata"]?.objectValue,
           let title = book["title"]?.stringValue?.nonEmptyValue {
            return title
        }
        return "Job \(job.jobId)"
    }

    private var summaryText: String? {
        var parts: [String] = []

        // Author/creator (for non-TV content, since TV shows author in title)
        if !isTvSeries {
            if let author = metadataString(for: [
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
        }

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
        // TV episode summary
        if isTvSeries {
            if let summary = tvEpisodeSummary ?? tvShowSummary {
                return summary
            }
        }

        // Book/video description
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
        // Try to get from image_generation summary first (most reliable for active jobs)
        if let imageGen = job.imageGeneration,
           let total = imageGen["sentence_total"]?.intValue, total > 0 {
            return total
        }
        // Try to get from latestEvent snapshot total
        if let total = job.latestEvent?.snapshot.total, total > 0 {
            return total
        }
        // Fallback to searching in result/parameters metadata
        // Note: metadataString may return "123.0" for numeric values, so parse via Double first
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

    private var jobIdLabel: String {
        #if os(iOS)
        return "J: \(job.jobId)"
        #else
        return "ID: \(job.jobId)"
        #endif
    }

    private var progressLabel: String? {
        guard job.isActiveForDisplay else { return nil }
        guard let snapshot = job.readyProgressSnapshot else {
            // Only show "preparing" if job is pending; otherwise omit to avoid flicker
            if job.status == .pending {
                return "Progress: preparing"
            }
            return nil
        }
        if let total = snapshot.total, total > 0 {
            let percent = Int((Double(snapshot.completed) / Double(total)) * 100)
            return "Progress \(snapshot.completed)/\(total) · \(percent)%"
        }
        return "Progress \(snapshot.completed)"
    }

    private var progressValue: Double? {
        guard job.isActiveForDisplay else { return nil }
        guard let snapshot = job.readyProgressSnapshot else { return nil }
        guard let total = snapshot.total, total > 0 else { return nil }
        return Double(snapshot.completed) / Double(total)
    }

    private var statusGlyph: (icon: String, label: String) {
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

    private var statusGlyphFont: Font {
        #if os(iOS) || os(tvOS)
        let base = UIFont.preferredFont(forTextStyle: .caption1).pointSize
        return .system(size: base * 2.0)
        #else
        return .system(size: 28)
        #endif
    }

    private var statusColor: Color {
        switch job.displayStatus {
        case .pending, .pausing:
            #if os(tvOS)
            return .yellow
            #else
            return .orange
            #endif
        case .running:
            #if os(tvOS)
            return .cyan  // Better contrast against blue focus background on tvOS
            #else
            return .blue
            #endif
        case .paused:
            return .yellow
        case .completed:
            return .green
        case .failed, .cancelled:
            return .red
        }
    }

    private var jobVariant: PlayerChannelVariant {
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

    private var progressTint: Color {
        CoverStyle.from(variant: jobVariant).iconColor
    }

    private var titleFont: Font {
        #if os(tvOS)
        return scaledTVOSFont(.headline)
        #else
        return .headline
        #endif
    }

    private var metaFont: Font {
        #if os(tvOS)
        return scaledTVOSFont(.caption1)
        #else
        return .caption
        #endif
    }

    private var summaryFont: Font {
        #if os(tvOS)
        return scaledTVOSFont(.subheadline)
        #else
        return .subheadline
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
        return 12
        #else
        return 10
        #endif
    }

    private var textSpacing: CGFloat {
        #if os(tvOS)
        return 4
        #else
        return 3
        #endif
    }

    private var rowPadding: CGFloat {
        #if os(tvOS)
        return 6
        #else
        return 5
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
        if useDarkOnLightColors {
            return .black
        } else if useLightOnDarkColors {
            return .white
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
        if useDarkOnLightColors {
            return .black.opacity(0.7)
        } else if useLightOnDarkColors {
            return .white.opacity(0.75)
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
        if useDarkOnLightColors {
            return .black.opacity(0.55)
        } else if useLightOnDarkColors {
            return .white.opacity(0.6)
        }
        return .gray.opacity(0.6)
        #elseif os(iOS)
        return usesDarkBackground ? .white.opacity(0.6) : .gray.opacity(0.8)
        #else
        return .gray.opacity(0.6)
        #endif
    }

    private var coverURL: URL? {
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

    private func coverCandidates(youtubeFallback: String?) -> [String] {
        var candidates: [String] = []
        var seen = Set<String>()

        func add(_ value: String?) {
            guard let trimmed = value?.nonEmptyValue else { return }
            guard !seen.contains(trimmed) else { return }
            seen.insert(trimmed)
            candidates.append(trimmed)
        }

        // Video/YouTube thumbnails
        add(metadataString(for: ["thumbnail"], maxDepth: 6))

        // TV show images (nested under image.original or image.medium)
        if let imageObj = metadataValue(for: ["image"], maxDepth: 6)?.objectValue {
            add(imageObj["original"]?.stringValue)
            add(imageObj["medium"]?.stringValue)
        }

        // Cover URLs
        add(metadataString(for: ["cover_url", "cover", "poster", "poster_url"], maxDepth: 6))

        // Job cover assets
        add(metadataString(for: ["job_cover_asset_url", "job_cover_asset", "book_cover_file"], maxDepth: 6))

        // YouTube fallback
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
        for source in sources {
            guard let source, let id = extractYoutubeVideoId(from: source) else { continue }
            return "https://i.ytimg.com/vi/\(id)/hqdefault.jpg"
        }
        return nil
    }

    private func extractYoutubeVideoId(from value: String) -> String? {
        let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return nil }
        if let url = URL(string: trimmed), let id = extractYoutubeVideoId(from: url) {
            return id
        }
        if let id = extractBracketedYoutubeId(from: trimmed) {
            return id
        }
        if let id = extractIdBeforeToken(in: trimmed, token: "_yt") {
            return id
        }
        return nil
    }

    private func extractYoutubeVideoId(from url: URL) -> String? {
        let host = url.host?.lowercased() ?? ""
        let pathComponents = url.path.split(separator: "/").map(String.init)
        if host.contains("youtu.be"), let first = pathComponents.first, isValidYoutubeID(first) {
            return first
        }
        if host.contains("youtube.com") {
            if url.path.contains("/watch") {
                let components = URLComponents(url: url, resolvingAgainstBaseURL: false)
                let id = components?.queryItems?.first(where: { $0.name == "v" })?.value
                if let id, isValidYoutubeID(id) {
                    return id
                }
            }
            if let shortsIndex = pathComponents.firstIndex(of: "shorts"),
               pathComponents.indices.contains(shortsIndex + 1) {
                let id = pathComponents[shortsIndex + 1]
                if isValidYoutubeID(id) {
                    return id
                }
            }
            if let embedIndex = pathComponents.firstIndex(of: "embed"),
               pathComponents.indices.contains(embedIndex + 1) {
                let id = pathComponents[embedIndex + 1]
                if isValidYoutubeID(id) {
                    return id
                }
            }
        }
        return nil
    }

    private func extractBracketedYoutubeId(from value: String) -> String? {
        var searchRange = value.startIndex..<value.endIndex
        while let open = value.range(of: "[", options: [], range: searchRange)?.lowerBound {
            let afterOpen = value.index(after: open)
            guard let closeRange = value.range(of: "]", options: [], range: afterOpen..<value.endIndex) else {
                break
            }
            let candidate = String(value[afterOpen..<closeRange.lowerBound])
            let suffix = value[closeRange.upperBound...].lowercased()
            if isValidYoutubeID(candidate), suffix.hasPrefix("_yt") || suffix.hasPrefix(".yt") || suffix.hasPrefix("-yt") || suffix.contains("youtube") {
                return candidate
            }
            searchRange = closeRange.upperBound..<value.endIndex
        }
        return nil
    }

    private func extractIdBeforeToken(in value: String, token: String) -> String? {
        let lowered = value.lowercased()
        guard let range = lowered.range(of: token) else { return nil }
        let endIndex = range.lowerBound
        let prefix = value[..<endIndex]
        let validChars = CharacterSet(charactersIn: "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-")
        var buffer = ""
        for character in prefix.reversed() {
            guard let scalar = character.unicodeScalars.first, validChars.contains(scalar) else { break }
            buffer.append(character)
            if buffer.count >= 11 {
                break
            }
        }
        let reversed = String(buffer.reversed())
        return isValidYoutubeID(reversed) ? reversed : nil
    }

    private func isValidYoutubeID(_ value: String) -> Bool {
        guard value.count == 11 else { return false }
        let validChars = CharacterSet(charactersIn: "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-")
        return value.unicodeScalars.allSatisfy { validChars.contains($0) }
    }

    private func resolveCoverCandidate(_ candidate: String) -> URL? {
        let trimmed = candidate.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return nil }
        let normalized = normalizeCoverCandidate(trimmed)
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

    private func normalizeCoverCandidate(_ candidate: String) -> String {
        if candidate.hasPrefix("//") {
            return "https:" + candidate
        }
        let lower = candidate.lowercased()
        if lower.hasPrefix("http://"),
           (lower.contains("youtube.com") || lower.contains("ytimg.com") || lower.contains("youtu.be")) {
            return "https://" + candidate.dropFirst("http://".count)
        }
        return candidate
    }

    private func metadataString(for keys: [String], maxDepth: Int = 4) -> String? {
        let sources = [job.result?.objectValue, job.parameters?.objectValue].compactMap { $0 }
        for source in sources {
            if let found = metadataString(in: source, keys: keys, maxDepth: maxDepth) {
                return found
            }
        }
        return nil
    }

    private func metadataValue(for keys: [String], maxDepth: Int = 4) -> JSONValue? {
        let sources = [job.result?.objectValue, job.parameters?.objectValue].compactMap { $0 }
        for source in sources {
            if let found = metadataValue(in: source, keys: keys, maxDepth: maxDepth) {
                return found
            }
        }
        return nil
    }

    private func metadataValue(in metadata: [String: JSONValue], keys: [String], maxDepth: Int) -> JSONValue? {
        for key in keys {
            if let found = metadataValue(in: metadata, key: key, maxDepth: maxDepth) {
                return found
            }
        }
        return nil
    }

    private func metadataValue(in metadata: [String: JSONValue], key: String, maxDepth: Int) -> JSONValue? {
        if let value = metadata[key] {
            return value
        }
        guard maxDepth > 0 else { return nil }
        for value in metadata.values {
            if let nested = value.objectValue {
                if let found = metadataValue(in: nested, key: key, maxDepth: maxDepth - 1) {
                    return found
                }
            }
            if case let .array(items) = value {
                for entry in items {
                    if let nested = entry.objectValue,
                       let found = metadataValue(in: nested, key: key, maxDepth: maxDepth - 1) {
                        return found
                    }
                }
            }
        }
        return nil
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
        let sources = [job.result?.objectValue, job.parameters?.objectValue].compactMap { $0 }
        for source in sources {
            if let value = extractTvMediaMetadata(from: source) {
                return value
            }
        }
        return nil
    }

    private func extractTvMediaMetadata(from metadata: [String: JSONValue]) -> [String: JSONValue]? {
        let paths: [[String]] = [
            ["youtube_dub", "media_metadata"],
            ["subtitle", "metadata", "media_metadata"],
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

    private func nestedValue(_ source: [String: JSONValue], path: [String]) -> JSONValue? {
        var current: JSONValue = .object(source)
        for key in path {
            guard let object = current.objectValue, let next = object[key] else { return nil }
            current = next
        }
        return current
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

    #if os(tvOS)
    private func scaledTVOSFont(_ style: UIFont.TextStyle) -> Font {
        let size = UIFont.preferredFont(forTextStyle: style).pointSize * 0.5
        return .system(size: size)
    }
    #endif
}
