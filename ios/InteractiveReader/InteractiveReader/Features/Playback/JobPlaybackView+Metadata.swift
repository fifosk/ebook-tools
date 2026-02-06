import Foundation
import SwiftUI

extension JobPlaybackView {
    var videoMetadata: VideoPlaybackMetadata {
        let channelLabel: String
        let channelVariant = videoChannelVariant
        switch channelVariant {
        case .subtitles:
            channelLabel = "Subtitles"
        case .youtube:
            channelLabel = "YouTube"
        case .dub:
            channelLabel = "Dubbing"
        case .video:
            channelLabel = "Video"
        case .tv:
            channelLabel = "TV"
        case .nas:
            channelLabel = "NAS"
        case .book, .job:
            channelLabel = "Video"
        }
        let title = videoTitleOverride ?? jobTitle
        let subtitle = videoSubtitleOverride ?? jobAuthor.nonEmptyValue
        return VideoPlaybackMetadata(
            title: title,
            subtitle: subtitle,
            artist: subtitle,
            album: title.nonEmptyValue,
            artworkURL: coverURL,
            secondaryArtworkURL: secondaryCoverURL,
            languageFlags: languageFlags,
            translationModel: translationModelLabel,
            summary: summaryText,
            channelVariant: channelVariant,
            channelLabel: channelLabel
        )
    }

    var videoChannelVariant: PlayerChannelVariant {
        if isTvSeries {
            return .tv
        }
        return jobVariant
    }

    var videoTitleOverride: String? {
        if let youtubeTitle = resolvedYoutubeTitle {
            return youtubeTitle
        }
        if let tvTitle = resolvedTvTitle {
            return tvTitle
        }
        return nil
    }

    var videoSubtitleOverride: String? {
        if let youtubeChannel = resolvedYoutubeChannel {
            return youtubeChannel
        }
        if let tvEpisodeLabel = resolvedTvEpisodeLabel {
            return tvEpisodeLabel
        }
        if let sourceName = subtitleTvMetadata?.sourceName?.nonEmptyValue {
            return sourceName
        }
        return nil
    }

    var jobTitle: String {
        if let label = currentJob.jobLabel?.nonEmptyValue {
            return label
        }
        if let title = metadataString(for: ["title", "book_title", "name", "source_name"]) {
            return title
        }
        return "Job \(job.jobId)"
    }

    var jobProgressPercent: Int? {
        let chunkPercent = chunkProgressPercent
        if chunkPercent > 0 {
            return chunkPercent
        }
        if currentJob.isFinishedForDisplay {
            return 100
        }
        guard let snapshot = currentJob.readyProgressSnapshot,
              let total = snapshot.total,
              total > 0
        else {
            return nil
        }
        let value = Int((Double(snapshot.completed) / Double(total)) * 100)
        return min(max(value, 0), 100)
    }

    var chunkProgressPercent: Int {
        guard !videoSegments.isEmpty else { return 0 }
        guard let activeID = activeVideoSegmentID ?? videoSegments.first?.id,
              let activeIndex = videoSegments.firstIndex(where: { $0.id == activeID })
        else {
            return 0
        }
        let percent = Int((Double(activeIndex + 1) / Double(max(videoSegments.count, 1))) * 100)
        return min(max(percent, 0), 100)
    }

    var jobRemainingLabel: String? {
        guard let remaining = jobRemainingEstimate, remaining > 0 else { return nil }
        return "Job remaining \(formatDurationLabel(remaining))"
    }

    var jobRemainingEstimate: Double? {
        guard !videoSegments.isEmpty else { return nil }
        let durations = completedSegmentDurations.values.filter { $0.isFinite && $0 > 0 }
        guard !durations.isEmpty else { return nil }
        let average = durations.reduce(0, +) / Double(durations.count)
        let remainingCount = max(videoSegments.count - durations.count, 0)
        guard remainingCount > 0 else { return 0 }
        return average * Double(remainingCount)
    }

    var jobStatusLabel: String {
        switch currentJob.displayStatus {
        case .pending:
            return "Pending"
        case .running:
            return "Running"
        case .pausing:
            return "Pausing"
        case .paused:
            return "Paused"
        case .completed:
            return "Completed"
        case .failed:
            return "Failed"
        case .cancelled:
            return "Cancelled"
        }
    }

    var jobAuthor: String {
        metadataString(for: ["author", "book_author", "creator", "artist"]) ?? "Unknown author"
    }

    var summaryText: String? {
        if let summary = resolvedYoutubeSummary {
            return summary
        }
        if let summary = resolvedTvSummary {
            return summary
        }
        if let summary = bookSummary {
            return summary
        }
        return nil
    }

    var resolvedTvMetadata: [String: JSONValue]? {
        if let tvMetadata = subtitleTvMetadata?.mediaMetadata {
            return tvMetadata
        }
        guard let metadata = jobMetadata else { return nil }
        return extractTvMediaMetadata(from: metadata)
    }

    var resolvedYoutubeMetadata: [String: JSONValue]? {
        if let youtubeMetadata = youtubeVideoMetadata?.youtubeMetadata {
            return youtubeMetadata
        }
        guard let tvMetadata = resolvedTvMetadata,
              let youtube = tvMetadata["youtube"]?.objectValue
        else {
            return nil
        }
        return youtube
    }

    var resolvedYoutubeSummary: String? {
        let summary = resolvedYoutubeMetadata?["summary"]?.stringValue
        let description = resolvedYoutubeMetadata?["description"]?.stringValue
        return normalizedSummary(summary ?? description)
    }

    var resolvedTvSummary: String? {
        guard let tvMetadata = resolvedTvMetadata else { return nil }
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

    var isTvSeries: Bool {
        guard let tvMetadata = resolvedTvMetadata else { return false }
        if let kind = tvMetadata["kind"]?.stringValue?.lowercased(),
           kind == "tv_episode" {
            return true
        }
        if tvMetadata["show"]?.objectValue != nil || tvMetadata["episode"]?.objectValue != nil {
            return true
        }
        return false
    }

    var bookSummary: String? {
        if let metadata = jobMetadata,
           let mediaMetadata = extractMediaMetadata(from: metadata) {
            let summary = mediaMetadata["book_summary"]?.stringValue
                ?? mediaMetadata["summary"]?.stringValue
                ?? mediaMetadata["description"]?.stringValue
            return normalizedSummary(summary)
        }
        return normalizedSummary(metadataString(for: ["book_summary"], maxDepth: 4))
    }

    var resolvedTvTitle: String? {
        if let tvMetadata = resolvedTvMetadata,
           let show = tvMetadata["show"]?.objectValue,
           let name = show["name"]?.stringValue?.nonEmptyValue {
            return name
        }
        if let parsed = subtitleTvMetadata?.parsed?.series.nonEmptyValue {
            return parsed
        }
        if let source = subtitleTvMetadata?.sourceName?.nonEmptyValue {
            return source
        }
        return nil
    }

    var resolvedYoutubeTitle: String? {
        resolvedYoutubeMetadata?["title"]?.stringValue?.nonEmptyValue
    }

    var resolvedYoutubeChannel: String? {
        if let channel = resolvedYoutubeMetadata?["channel"]?.stringValue?.nonEmptyValue {
            return channel
        }
        return resolvedYoutubeMetadata?["uploader"]?.stringValue?.nonEmptyValue
    }

    func normalizedSummary(_ value: String?) -> String? {
        PlaybackMetadataHelpers.normalizedSummary(value, lengthLimit: summaryLengthLimit)
    }

    var jobVariant: PlayerChannelVariant {
        let type = currentJob.jobType.lowercased()
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

    var shouldFetchTvMetadata: Bool {
        switch jobVariant {
        case .subtitles, .youtube, .dub, .video, .tv:
            return true
        case .book, .nas, .job:
            return false
        }
    }

    var shouldFetchYoutubeMetadata: Bool {
        switch jobVariant {
        case .youtube, .dub:
            return true
        case .book, .subtitles, .video, .tv, .nas, .job:
            return false
        }
    }

    var itemTypeLabel: String {
        switch jobVariant {
        case .book:
            return "Book"
        case .subtitles:
            return "Subtitles"
        case .video, .youtube:
            return "Video"
        case .tv:
            return "TV"
        case .dub:
            return "Dubbing"
        case .nas:
            return "NAS"
        case .job:
            return "Job"
        }
    }

    var linguistInputLanguage: String {
        metadataString(for: [
            "input_language",
            "original_language",
            "source_language",
            "translation_source_language",
            "book_language"
        ]) ?? metadataString(for: ["language"], maxDepth: 0) ?? ""
    }

    var linguistLookupLanguage: String {
        metadataString(for: [
            "target_language",
            "translation_language",
            "target_languages",
            "book_language"
        ]) ?? metadataString(for: ["language"], maxDepth: 0) ?? ""
    }

    var interactiveHeaderInfo: InteractivePlayerHeaderInfo {
        InteractivePlayerHeaderInfo(
            title: jobTitle,
            author: jobAuthor,
            itemTypeLabel: itemTypeLabel,
            coverURL: coverURL,
            secondaryCoverURL: secondaryCoverURL,
            languageFlags: languageFlags,
            translationModel: translationModelLabel
        )
    }

    var languageFlags: [LanguageFlagEntry] {
        LanguageFlagResolver.resolveFlags(
            originalLanguage: linguistInputLanguage.nonEmptyValue,
            translationLanguage: linguistLookupLanguage.nonEmptyValue
        )
    }

    var translationModelLabel: String? {
        metadataString(for: ["llm_model", "ollama_model"])?.nonEmptyValue
    }

    var coverURL: URL? {
        let candidates = coverCandidates()
        for candidate in candidates {
            if let url = resolveCoverCandidate(candidate) {
                return url
            }
        }
        return nil
    }

    var secondaryCoverURL: URL? {
        guard let tvMetadata = resolvedTvMetadata else { return nil }
        let episode = resolveTvImage(from: tvMetadata, path: "episode")
        let show = resolveTvImage(from: tvMetadata, path: "show")
        let primary = episode ?? show
        guard let show, let primary, show != primary else { return nil }
        return resolveCoverCandidate(show)
    }

    func coverCandidates() -> [String] {
        let metadata = jobMetadata
        var candidates: [String] = []
        var seen = Set<String>()

        func add(_ value: String?) {
            guard let trimmed = value?.nonEmptyValue else { return }
            guard !seen.contains(trimmed) else { return }
            seen.insert(trimmed)
            candidates.append(trimmed)
        }

        let isVideoJob = jobVariant != .book
        if isVideoJob {
            appendTvCandidates(add: add)
        }
        if let metadata {
            if let mediaMetadata = extractMediaMetadata(from: metadata) {
                add(mediaMetadata["job_cover_asset_url"]?.stringValue)
                add(mediaMetadata["job_cover_asset"]?.stringValue)
                add(mediaMetadata["book_cover_file"]?.stringValue)
            }
            add(metadata["job_cover_asset_url"]?.stringValue)
            add(metadata["job_cover_asset"]?.stringValue)
            add(metadata["cover_url"]?.stringValue)
            add(metadata["cover"]?.stringValue)
        }
        if !isVideoJob {
            appendTvCandidates(add: add)
        }
        return candidates
    }

    func resolveCoverCandidate(_ candidate: String) -> URL? {
        if let url = viewModel.resolvePath(candidate) {
            return url
        }
        if let base = appState.apiBaseURL, let url = URL(string: candidate, relativeTo: base) {
            return url
        }
        return URL(string: candidate)
    }

    func appendTvCandidates(add: (String?) -> Void) {
        if let tvMetadata = resolvedTvMetadata {
            add(resolveTvImage(from: tvMetadata, path: "episode"))
            add(resolveTvImage(from: tvMetadata, path: "show"))
            add(resolveYoutubeThumbnailFromTvMetadata(tvMetadata))
        }
        if let youtubeMetadata = resolvedYoutubeMetadata {
            add(resolveYoutubeThumbnailFromYoutubeMetadata(youtubeMetadata))
        }
    }

    var jobMetadata: [String: JSONValue]? {
        if let result = currentJob.result?.objectValue {
            return result
        }
        return currentJob.parameters?.objectValue
    }

    func metadataString(for keys: [String], maxDepth: Int = 4) -> String? {
        let sources = [currentJob.result?.objectValue, currentJob.parameters?.objectValue].compactMap { $0 }
        for source in sources {
            if let found = PlaybackMetadataHelpers.metadataString(in: source, keys: keys, maxDepth: maxDepth) {
                return found
            }
        }
        return nil
    }

    func extractMediaMetadata(from metadata: [String: JSONValue]) -> [String: JSONValue]? {
        if let direct = (metadata["media_metadata"] ?? metadata["book_metadata"])?.objectValue {
            return direct
        }
        if let result = metadata["result"]?.objectValue,
           let nested = (result["media_metadata"] ?? result["book_metadata"])?.objectValue {
            return nested
        }
        return nil
    }

    func extractTvMediaMetadata(from metadata: [String: JSONValue]) -> [String: JSONValue]? {
        PlaybackMetadataHelpers.extractTvMediaMetadata(from: metadata)
    }

    func resolveTvImage(from tvMetadata: [String: JSONValue], path: String) -> String? {
        guard let section = tvMetadata[path]?.objectValue else { return nil }
        guard let imageValue = section["image"] else { return nil }
        if let direct = imageValue.stringValue {
            return direct
        }
        if let imageObject = imageValue.objectValue {
            return imageObject["medium"]?.stringValue ?? imageObject["original"]?.stringValue
        }
        return nil
    }

    func resolveYoutubeThumbnailFromTvMetadata(_ tvMetadata: [String: JSONValue]) -> String? {
        guard let youtube = tvMetadata["youtube"]?.objectValue else { return nil }
        return youtube["thumbnail"]?.stringValue
    }

    func resolveYoutubeThumbnailFromYoutubeMetadata(_ youtubeMetadata: [String: JSONValue]) -> String? {
        youtubeMetadata["thumbnail"]?.stringValue
    }

    func intValue(_ value: JSONValue?) -> Int? {
        PlaybackMetadataHelpers.intValue(value)
    }

    var currentJob: PipelineStatusResponse {
        jobStatus ?? job
    }

    func formatDurationLabel(_ value: Double) -> String {
        let total = max(0, Int(value.rounded()))
        let hours = total / 3600
        let minutes = (total % 3600) / 60
        let seconds = total % 60
        return String(format: "%02d:%02d:%02d", hours, minutes, seconds)
    }
}
