import Foundation

struct AppleBookCreateVideoDiscoveryAvailability {
    let youtubeSearchUnavailableMessage: String?
    let isYoutubeSearchAvailable: Bool
    let downloadStationUnavailableMessage: String?
    let isDownloadStationAvailable: Bool
}

struct AppleBookCreateDiscoveryProviderOption: Identifiable {
    let id: String
    let label: String
    let available: Bool
}

struct AppleBookCreateVideoDiscoveryProviderOption: Identifiable {
    let id: String
    let label: String
    let available: Bool
}

struct AppleBookCreateBookDiscoveryMetadataApplication: Equatable {
    let sourceBookTitle: String?
    let sourceBookAuthor: String?
    let sourceBookGenre: String?
    let bookSummary: String?
    let bookYear: String?
    let bookIsbn: String?
    let bookCoverFile: String?
    let bookMetadataExtras: [String: JSONValue]
}

extension AppleBookCreatePresentation {
    static func youtubeVideoDiscoveryAvailability(
        providers: [AcquisitionProviderEntry]
    ) -> AppleBookCreateVideoDiscoveryAvailability {
        let youtubeSearchProvider = providers.first { $0.id == "youtube_search" }
        let downloadStationProvider = providers.first { $0.id == "download_station" }
        let hasProviderInventory = !providers.isEmpty
        return AppleBookCreateVideoDiscoveryAvailability(
            youtubeSearchUnavailableMessage: youtubeSearchUnavailableMessage(for: youtubeSearchProvider),
            isYoutubeSearchAvailable: youtubeSearchProvider?.available ?? !hasProviderInventory,
            downloadStationUnavailableMessage: downloadStationUnavailableMessage(for: downloadStationProvider),
            isDownloadStationAvailable: downloadStationProvider?.available == true
        )
    }

    static func bookDiscoveryProviderUnavailableMessage(
        for provider: AcquisitionProviderEntry?,
        selectedOption: AppleBookCreateDiscoveryProviderOption?
    ) -> String? {
        if let provider {
            guard !provider.available else {
                return nil
            }
            return discoveryProviderUnavailableMessage(
                for: provider,
                fallbackAction: "Configure the backend source root or choose another discovery source."
            )
        }
        guard let selectedOption, !selectedOption.available else {
            return nil
        }
        if selectedOption.id == "zlibrary_attended" {
            return "Direct Z-Library automation is intentionally disabled. Use attended browser downloads, then import the EPUB through Manual downloads or Choose EPUB."
        }
        return "\(selectedOption.label) is unavailable. Configure the backend source root or choose another discovery source."
    }

    static func videoDiscoveryProviderUnavailableMessage(
        for provider: AcquisitionProviderEntry?,
        youtubeSearchUnavailableMessage: String?
    ) -> String? {
        guard let provider, !provider.available else {
            return nil
        }
        if provider.id == "youtube_search" {
            return youtubeSearchUnavailableMessage
        }
        if provider.id == "newznab_torznab" {
            return "\(provider.label) is \(formattedProviderStatus(provider.status)). Configure backend Newznab/Torznab indexer settings, or use NAS videos."
        }
        return discoveryProviderUnavailableMessage(
            for: provider,
            fallbackAction: "Configure the backend source root or choose another discovery source."
        )
    }

    static func bookDiscoveryProviderOptions(
        from providers: [AcquisitionProviderEntry],
        defaultProviderIds: [String: [String]] = [:]
    ) -> [AppleBookCreateDiscoveryProviderOption] {
        let providers = providers.filter(isBookDiscoveryProvider)
        guard !providers.isEmpty else {
            return fallbackBookDiscoveryProviders
        }
        let providerOptions = providers
            .sorted { left, right in
                let leftRank = bookDiscoveryProviderRank(left.id)
                let rightRank = bookDiscoveryProviderRank(right.id)
                if leftRank != rightRank {
                    return leftRank < rightRank
                }
                return bookDiscoveryProviderLabel(left)
                    .localizedCaseInsensitiveCompare(bookDiscoveryProviderLabel(right)) == .orderedAscending
            }
            .map {
                AppleBookCreateDiscoveryProviderOption(
                    id: $0.id,
                    label: bookDiscoveryProviderLabel($0),
                    available: $0.available
                )
            }
        guard let defaultOption = defaultBookDiscoveryProviderOption(
            options: providerOptions,
            defaultProviderIds: defaultProviderIds
        ) else {
            return providerOptions
        }
        return [defaultOption] + providerOptions
    }

    static func videoDiscoveryProviderOptions(
        from providers: [AcquisitionProviderEntry],
        defaultProviderIds: [String: [String]] = [:]
    ) -> [AppleBookCreateVideoDiscoveryProviderOption] {
        let providers = providers.filter(isVideoDiscoveryProvider)
        guard !providers.isEmpty else {
            return fallbackVideoDiscoveryProviders
        }
        let providerOptions = providers
            .sorted { left, right in
                let leftRank = videoDiscoveryProviderRank(left.id)
                let rightRank = videoDiscoveryProviderRank(right.id)
                if leftRank != rightRank {
                    return leftRank < rightRank
                }
                return videoDiscoveryProviderLabel(left)
                    .localizedCaseInsensitiveCompare(videoDiscoveryProviderLabel(right)) == .orderedAscending
            }
            .map {
                AppleBookCreateVideoDiscoveryProviderOption(
                    id: $0.id,
                    label: videoDiscoveryProviderLabel($0),
                    available: $0.available
                )
            }
        guard let defaultOption = defaultVideoDiscoveryProviderOption(
            options: providerOptions,
            defaultProviderIds: defaultProviderIds
        ) else {
            return providerOptions
        }
        return [defaultOption] + providerOptions
    }

    static func defaultDiscoveryProviderID(
        for mediaKind: String,
        defaultProviderIds: [String: [String]],
        optionIds: [String],
        availableOptionIds: [String]? = nil,
        fallback: String
    ) -> String? {
        guard !optionIds.isEmpty else {
            return fallback
        }
        let optionIdSet = Set(optionIds)
        if mediaKind == "book", optionIdSet.contains(defaultBookDiscoveryProviderID) {
            return defaultBookDiscoveryProviderID
        }
        if mediaKind == "video", optionIdSet.contains(defaultVideoDiscoveryProviderID) {
            return defaultVideoDiscoveryProviderID
        }
        let availableOptionIdSet = Set(availableOptionIds ?? optionIds)
        let preferredOptionIdSet = availableOptionIdSet.isEmpty ? optionIdSet : availableOptionIdSet
        let backendDefaults = defaultableProviderIDs(
            for: mediaKind,
            providerIDs: defaultProviderIds[mediaKind] ?? []
        )
        if let backendDefault = backendDefaults.first(where: { preferredOptionIdSet.contains($0) }) {
            return backendDefault
        }
        if preferredOptionIdSet.contains(fallback) {
            return fallback
        }
        if let firstPreferred = optionIds.first(where: { preferredOptionIdSet.contains($0) }) {
            return firstPreferred
        }
        return optionIdSet.contains(fallback) ? fallback : optionIds.first
    }

    static func bookDiscoveryCandidates(
        from discovery: AcquisitionDiscoveryResponse?
    ) -> [AcquisitionCandidate] {
        discovery?.candidates.filter {
            guard $0.mediaKind == "book" else {
                return false
            }
            let localPath = $0.localPath?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
            return !localPath.isEmpty
                || $0.capabilities.contains("acquire")
                || ($0.capabilities.contains("metadata") && $0.provider == "openlibrary")
        } ?? []
    }

    static func bookDiscoveryCandidateDetail(_ candidate: AcquisitionCandidate) -> String {
        var details = [candidate.provider]
        if let contributor = candidate.contributors.first?.trimmingCharacters(in: .whitespacesAndNewlines),
           !contributor.isEmpty {
            details.append(contributor)
        }
        if let language = candidate.language?.trimmingCharacters(in: .whitespacesAndNewlines), !language.isEmpty {
            details.append(language)
        }
        if let localPath = candidate.localPath?.trimmingCharacters(in: .whitespacesAndNewlines), !localPath.isEmpty {
            details.append(localPath)
        } else if candidate.sourceUrl?.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty == false {
            details.append(candidate.provider == "openlibrary" ? "metadata catalog" : "public catalog")
        }
        if let modifiedAt = candidate.modifiedAt?.trimmingCharacters(in: .whitespacesAndNewlines), !modifiedAt.isEmpty {
            details.append(modifiedAt)
        }
        return details.joined(separator: " · ")
    }

    static func bookDiscoveryCandidateAction(_ candidate: AcquisitionCandidate) -> String {
        let localPath = candidate.localPath?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        if !localPath.isEmpty {
            return "Use"
        }
        if candidate.capabilities.contains("acquire") {
            return "Acquire"
        }
        if !internetArchiveSourceIDs(candidate).isEmpty {
            return "Find EPUB"
        }
        return candidate.capabilities.contains("metadata") ? "Apply metadata" : "Review"
    }

    static func canSelectBookDiscoveryCandidate(_ candidate: AcquisitionCandidate) -> Bool {
        let localPath = candidate.localPath?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        return !localPath.isEmpty
            || candidate.capabilities.contains("acquire")
            || candidate.capabilities.contains("metadata")
    }

    static func bookDiscoveryMetadataApplication(
        _ candidate: AcquisitionCandidate
    ) -> AppleBookCreateBookDiscoveryMetadataApplication? {
        guard candidate.capabilities.contains("metadata") else {
            return nil
        }
        let metadata = candidate.metadata ?? [:]
        let title = bookDiscoveryMetadataText(metadata, keys: "book_title", "title")
            ?? candidate.title.trimmingCharacters(in: .whitespacesAndNewlines).nonEmptyValue
        let author = bookDiscoveryMetadataText(metadata, keys: "book_author", "author")
            ?? candidate.contributors.first?.trimmingCharacters(in: .whitespacesAndNewlines).nonEmptyValue
        let genre = bookDiscoveryMetadataText(metadata, keys: "book_genre", "genre")
        let summary = bookDiscoveryMetadataText(metadata, keys: "book_summary", "summary")
        let year = bookDiscoveryMetadataText(metadata, keys: "book_year", "year")
            ?? candidate.year.map(String.init)
        let isbn = bookDiscoveryMetadataText(metadata, keys: "book_isbn", "isbn")
        let cover = bookDiscoveryMetadataText(metadata, keys: "book_cover_file", "cover_file", "cover_url")
            ?? candidate.coverUrl?.trimmingCharacters(in: .whitespacesAndNewlines).nonEmptyValue

        return AppleBookCreateBookDiscoveryMetadataApplication(
            sourceBookTitle: title,
            sourceBookAuthor: author,
            sourceBookGenre: genre,
            bookSummary: summary,
            bookYear: year,
            bookIsbn: isbn,
            bookCoverFile: cover,
            bookMetadataExtras: bookDiscoveryMetadataExtras(candidate, metadata: metadata)
        )
    }

    static func internetArchiveSourceIDs(_ candidate: AcquisitionCandidate) -> [String] {
        guard let metadataValue = candidate.metadata?["internet_archive_ids"] else {
            return []
        }
        let values = metadataValue.arrayValue ?? [metadataValue]
        var seen = Set<String>()
        var ids: [String] = []
        for value in values {
            guard let id = value.stringValue?.trimmingCharacters(in: .whitespacesAndNewlines),
                  !id.isEmpty else {
                continue
            }
            let key = id.lowercased()
            guard !seen.contains(key) else {
                continue
            }
            seen.insert(key)
            ids.append(id)
        }
        return ids
    }

    static func videoDiscoveryCandidates(
        from discovery: AcquisitionDiscoveryResponse?,
        providerID: String
    ) -> [AcquisitionCandidate] {
        let queriedProviders = Set(discovery?.providersQueried ?? [])
        return discovery?.candidates.filter {
            let effectiveProvider = isDefaultVideoDiscoveryProviderID(providerID) ? $0.provider : providerID
            if isDefaultVideoDiscoveryProviderID(providerID),
               explicitOnlyDefaultVideoDiscoveryProviderIDs.contains($0.provider) {
                return false
            }
            guard $0.mediaKind == "video", $0.provider == effectiveProvider else {
                return false
            }
            if isDefaultVideoDiscoveryProviderID(providerID),
               !queriedProviders.isEmpty,
               !queriedProviders.contains($0.provider) {
                return false
            }
            if isYoutubeMetadataVideoDiscoveryProviderID(effectiveProvider) {
                return youtubeMetadataSourceURL(for: $0) != nil
            }
            if effectiveProvider == "newznab_torznab" {
                return $0.requiresConfirmation
            }
            return $0.localPath?.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty == false
        } ?? []
    }

    static func videoDiscoveryStatePayload(
        from candidate: AcquisitionCandidate,
        selectedVideoPath: String?,
        selectedSubtitlePath: String?
    ) -> [String: JSONValue] {
        var state: [String: JSONValue] = [
            "media_kind": .string("video"),
            "provider": .string(candidate.provider),
            "candidate_id": .string(candidate.candidateId),
            "title": .string(candidate.title),
            "rights": .string(candidate.rights),
            "capabilities": .array(candidate.capabilities.map { .string($0) }),
        ]
        if let sourceKind = candidate.metadata?["source_kind"]?.stringValue?
            .trimmingCharacters(in: .whitespacesAndNewlines)
            .nonEmptyValue {
            state["source_kind"] = .string(sourceKind)
        } else {
            state["source_kind"] = .string(candidate.provider)
        }
        if let sourceURL = candidate.sourceUrl?.trimmingCharacters(in: .whitespacesAndNewlines).nonEmptyValue {
            state["source_url"] = .string(sourceURL)
        }
        if let localPath = candidate.localPath?.trimmingCharacters(in: .whitespacesAndNewlines).nonEmptyValue {
            state["local_path"] = .string(localPath)
        }
        if let selectedVideoPath = selectedVideoPath?.trimmingCharacters(in: .whitespacesAndNewlines).nonEmptyValue {
            state["selected_video_path"] = .string(selectedVideoPath)
        }
        if let selectedSubtitlePath = selectedSubtitlePath?.trimmingCharacters(in: .whitespacesAndNewlines).nonEmptyValue {
            state["selected_subtitle_path"] = .string(selectedSubtitlePath)
        }
        if candidate.requiresConfirmation {
            state["requires_confirmation"] = .bool(true)
        }
        return state
    }

    static func videoDiscoveryState(
        _ state: [String: JSONValue]?,
        replacingSelectedSubtitlePath path: String
    ) -> [String: JSONValue]? {
        guard var state else {
            return nil
        }
        if let trimmed = path.trimmingCharacters(in: .whitespacesAndNewlines).nonEmptyValue {
            state["selected_subtitle_path"] = .string(trimmed)
        } else {
            state.removeValue(forKey: "selected_subtitle_path")
        }
        return state
    }

    static func videoDiscoveryQueryPlaceholder(providerID: String) -> String {
        if isDefaultVideoDiscoveryProviderID(providerID) {
            return "Search default video sources"
        }
        if providerID == "youtube_search" {
            return "Search YouTube videos"
        }
        if providerID == "youtube_url" {
            return "Paste a YouTube URL or video id"
        }
        if providerID == "newznab_torznab" {
            return "Search configured indexers"
        }
        return "Search title or filename"
    }

    static func noVideoDiscoveryCandidatesMessage(providerID: String) -> String {
        if isDefaultVideoDiscoveryProviderID(providerID) {
            return "No default video sources matched this discovery search."
        }
        if providerID == "youtube_search" {
            return "No YouTube search results matched this discovery search."
        }
        if providerID == "youtube_url" {
            return "No YouTube URL metadata matched this discovery search."
        }
        if providerID == "newznab_torznab" {
            return "No indexer metadata matched this discovery search."
        }
        return "No local video sources matched this discovery search."
    }

    static func videoDiscoveryProviderFallbackLabel(for providerID: String) -> String {
        if isDefaultVideoDiscoveryProviderID(providerID) {
            return "Default sources"
        }
        return fallbackVideoDiscoveryProviders.first { $0.id == providerID }?.label ?? providerID
    }

    static let defaultVideoDiscoveryProviderID = "backend_defaults"
    static let defaultBookDiscoveryProviderID = "backend_defaults"

    static func isDefaultVideoDiscoveryProviderID(_ providerID: String) -> Bool {
        providerID
            .trimmingCharacters(in: .whitespacesAndNewlines)
            .localizedCaseInsensitiveCompare(defaultVideoDiscoveryProviderID) == .orderedSame
    }

    static func isDefaultBookDiscoveryProviderID(_ providerID: String) -> Bool {
        providerID
            .trimmingCharacters(in: .whitespacesAndNewlines)
            .localizedCaseInsensitiveCompare(defaultBookDiscoveryProviderID) == .orderedSame
    }

    static func isYoutubeMetadataVideoDiscoveryProviderID(_ providerID: String) -> Bool {
        let normalized = providerID.trimmingCharacters(in: .whitespacesAndNewlines)
        return normalized == "youtube_search" || normalized == "youtube_url"
    }

    static func youtubeMetadataSourceURL(for candidate: AcquisitionCandidate) -> String? {
        if let sourceURL = candidate.sourceUrl?.trimmingCharacters(in: .whitespacesAndNewlines).nonEmptyValue {
            return sourceURL
        }
        return candidate.metadata?["youtube_url"]?.stringValue?
            .trimmingCharacters(in: .whitespacesAndNewlines)
            .nonEmptyValue
    }

    static func youtubeVideoLabel(_ video: YoutubeNasVideoEntry) -> String {
        let subtitleCount = playableYoutubeSubtitles(for: video).count
        let label = subtitleCount == 1 ? "1 subtitle" : "\(subtitleCount) subtitles"
        return "\(video.filename) · \(label)"
    }

    static func youtubeSubtitleLabel(_ subtitle: YoutubeNasSubtitleEntry) -> String {
        let language = subtitle.language?.trimmingCharacters(in: .whitespacesAndNewlines)
        let suffix = [subtitle.format.uppercased(), language]
            .compactMap { value -> String? in
                guard let value, !value.isEmpty else { return nil }
                return value
            }
            .joined(separator: " · ")
        return suffix.isEmpty ? subtitle.filename : "\(subtitle.filename) · \(suffix)"
    }

    static func filenameFromPath(_ path: String) -> String {
        let trimmed = path.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else {
            return ""
        }
        return (trimmed as NSString).lastPathComponent
    }

    static func downloadStationCompletedFiles(from job: AcquisitionJobStatusResponse?) -> [String] {
        guard let job else {
            return []
        }
        let topLevel = normalizedMetadataStrings(job.completedFiles)
        if !topLevel.isEmpty {
            return topLevel
        }
        let metadata = job.metadata ?? [:]
        for key in ["completed_files", "completed_paths", "files"] {
            let values = normalizedMetadataStrings(metadata[key])
            if !values.isEmpty {
                return values
            }
        }
        return normalizedMetadataStrings(
            metadata["completed_file"] ?? metadata["completed_path"] ?? metadata["local_path"]
        )
    }

    static func downloadStationCompletedCandidate(
        from discovery: AcquisitionDiscoveryResponse?,
        job: AcquisitionJobStatusResponse?
    ) -> AcquisitionCandidate? {
        let completedNames = Set(
            downloadStationCompletedFileHints(from: job).flatMap(downloadStationNameKeys)
        )
        guard !completedNames.isEmpty else {
            return nil
        }
        return discovery?.candidates.first { candidate in
            guard candidate.localPath?.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty == false else {
                return false
            }
            return downloadStationCandidateNameSet(candidate).contains { completedNames.contains($0) }
        }
    }

    private static func normalizedMetadataStrings(_ values: [String]) -> [String] {
        values.compactMap { $0.trimmingCharacters(in: .whitespacesAndNewlines).nonEmptyValue }
    }

    private static func normalizedMetadataStrings(_ value: JSONValue?) -> [String] {
        if let array = value?.arrayValue {
            return array.compactMap {
                $0.stringValue?.trimmingCharacters(in: .whitespacesAndNewlines).nonEmptyValue
            }
        }
        return value?.stringValue?
            .trimmingCharacters(in: .whitespacesAndNewlines)
            .nonEmptyValue
            .map { [$0] } ?? []
    }

    private static func bookDiscoveryMetadataText(_ metadata: [String: JSONValue], keys: String...) -> String? {
        for key in keys {
            if let value = metadata[key]?.stringValue?.trimmingCharacters(in: .whitespacesAndNewlines),
               !value.isEmpty {
                return value
            }
        }
        return nil
    }

    private static func bookDiscoveryMetadataExtras(
        _ candidate: AcquisitionCandidate,
        metadata: [String: JSONValue]
    ) -> [String: JSONValue] {
        var extras = metadata
        extras["acquisition_provider"] = .string(candidate.provider)
        extras["acquisition_candidate_id"] = .string(candidate.candidateId)
        extras["rights"] = .string(candidate.rights)
        extras["capabilities"] = .array(candidate.capabilities.map { .string($0) })
        if extras["title"] == nil {
            extras["title"] = .string(candidate.title)
        }
        if extras["book_title"] == nil {
            extras["book_title"] = .string(candidate.title)
        }
        if let language = candidate.language?.trimmingCharacters(in: .whitespacesAndNewlines),
           !language.isEmpty,
           extras["language"] == nil {
            extras["language"] = .string(language)
        }
        if let year = candidate.year, extras["year"] == nil {
            extras["year"] = .number(Double(year))
        }
        if let sourceUrl = candidate.sourceUrl?.trimmingCharacters(in: .whitespacesAndNewlines),
           !sourceUrl.isEmpty,
           extras["source_url"] == nil {
            extras["source_url"] = .string(sourceUrl)
        }
        if let coverUrl = candidate.coverUrl?.trimmingCharacters(in: .whitespacesAndNewlines),
           !coverUrl.isEmpty,
           extras["cover_url"] == nil {
            extras["cover_url"] = .string(coverUrl)
        }
        if extras["source_kind"] == nil {
            extras["source_kind"] = .string(candidate.provider)
        }
        return normalizedBookMetadataExtras(extras)
    }

    private static func downloadStationCompletedFileHints(
        from job: AcquisitionJobStatusResponse?
    ) -> [String] {
        guard let job else {
            return []
        }
        var hints = normalizedMetadataStrings(job.completedFiles)
        let metadata = job.metadata ?? [:]
        for key in ["completed_file", "completed_path", "local_path", "filename"] {
            hints.append(contentsOf: normalizedMetadataStrings(metadata[key]))
        }
        for key in ["completed_files", "completed_paths", "files"] {
            hints.append(contentsOf: normalizedMetadataStrings(metadata[key]))
        }
        return hints
    }

    private static func downloadStationCandidateNameSet(_ candidate: AcquisitionCandidate) -> Set<String> {
        Set(
            [
                candidate.localPath,
                candidate.title.nonEmptyValue,
                candidate.sourceUrl?.nonEmptyValue
            ]
            .compactMap { $0 }
            .flatMap(downloadStationNameKeys)
        )
    }

    private static func downloadStationNameKeys(for value: String) -> [String] {
        let name = downloadStationLastPathComponent(value)
        let trimmed = name.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else {
            return []
        }
        let normalized = trimmed.lowercased()
        let stem = downloadStationFileStem(normalized)
        return stem == normalized ? [normalized] : [normalized, stem]
    }

    private static func downloadStationLastPathComponent(_ value: String) -> String {
        let separators: Set<Character> = ["/", "\\"]
        if let index = value.lastIndex(where: { separators.contains($0) }) {
            return String(value[value.index(after: index)...])
        }
        return value
    }

    private static func downloadStationFileStem(_ filename: String) -> String {
        guard let dot = filename.lastIndex(of: "."),
              dot > filename.startIndex else {
            return filename
        }
        return String(filename[..<dot])
    }

    static func videoDiscoveryCandidateDetail(_ candidate: AcquisitionCandidate) -> String {
        var details = [candidate.provider]
        if let localPath = candidate.localPath?.trimmingCharacters(in: .whitespacesAndNewlines), !localPath.isEmpty {
            details.append(localPath)
        }
        if let sourceURL = youtubeMetadataSourceURL(for: candidate)
            ?? candidate.sourceUrl?.trimmingCharacters(in: .whitespacesAndNewlines).nonEmptyValue {
            details.append(sourceURL)
        }
        if let contributor = candidate.contributors.first?.trimmingCharacters(in: .whitespacesAndNewlines),
           !contributor.isEmpty {
            details.append(contributor)
        }
        if let durationSeconds = candidate.durationSeconds, durationSeconds > 0 {
            details.append("\(durationSeconds)s")
        }
        if candidate.provider == "newznab_torznab" {
            if let sizeBytes = candidate.sizeBytes, sizeBytes > 0 {
                details.append(ByteCountFormatter.string(fromByteCount: Int64(sizeBytes), countStyle: .file))
            }
            if case let .number(seeders)? = candidate.metadata?["seeders"] {
                details.append("\(Int(seeders)) seeders")
            }
            if case let .number(peers)? = candidate.metadata?["peers"] {
                details.append("\(Int(peers)) peers")
            }
            if isDownloadStationHandoffCandidate(candidate) {
                details.append("Download Station handoff")
            }
        }
        if !candidate.subtitles.isEmpty {
            let count = candidate.subtitles.count
            details.append(count == 1 ? "1 subtitle" : "\(count) subtitles")
        }
        return details.joined(separator: " · ")
    }

    static func isDownloadStationHandoffCandidate(_ candidate: AcquisitionCandidate) -> Bool {
        guard candidate.provider == "newznab_torznab" else {
            return false
        }
        if candidate.metadata?["handoff_provider"]?.stringValue?
            .trimmingCharacters(in: .whitespacesAndNewlines)
            .localizedCaseInsensitiveCompare("download_station") == .orderedSame {
            return true
        }
        return candidate.metadata?["has_download_url"]?.stringValue?
            .trimmingCharacters(in: .whitespacesAndNewlines)
            .localizedCaseInsensitiveCompare("true") == .orderedSame
    }

    private static func youtubeSearchUnavailableMessage(
        for provider: AcquisitionProviderEntry?
    ) -> String? {
        guard let provider, !provider.available else {
            return nil
        }
        return "\(provider.label) is \(formattedProviderStatus(provider.status)). Configure the YouTube Data API key to search videos, or use NAS videos."
    }

    private static func downloadStationUnavailableMessage(
        for provider: AcquisitionProviderEntry?
    ) -> String? {
        guard let provider else {
            return "This backend does not advertise Download Station handoff yet. Use manual downloads or NAS videos."
        }
        guard !provider.available else {
            return nil
        }
        return "\(provider.label) is \(formattedProviderStatus(provider.status)). Configure backend Download Station credentials, or use manual downloads."
    }

    private static let fallbackBookDiscoveryProviders = [
        AppleBookCreateDiscoveryProviderOption(id: "local_epub", label: "Local EPUBs", available: true),
        AppleBookCreateDiscoveryProviderOption(id: "manual_downloads", label: "Manual downloads", available: true),
        AppleBookCreateDiscoveryProviderOption(id: "gutenberg", label: "Gutenberg", available: true),
        AppleBookCreateDiscoveryProviderOption(id: "internet_archive", label: "Internet Archive", available: true),
        AppleBookCreateDiscoveryProviderOption(id: "openlibrary", label: "Open Library", available: true),
        AppleBookCreateDiscoveryProviderOption(id: "zlibrary_attended", label: "Z-Library import", available: false)
    ]

    private static let fallbackVideoDiscoveryProviders = [
        AppleBookCreateVideoDiscoveryProviderOption(id: "nas_video", label: "NAS videos", available: true),
        AppleBookCreateVideoDiscoveryProviderOption(id: "manual_downloads", label: "Manual downloads", available: true),
        AppleBookCreateVideoDiscoveryProviderOption(id: "youtube_url", label: "YouTube URL", available: true),
        AppleBookCreateVideoDiscoveryProviderOption(id: "youtube_search", label: "YouTube search", available: true),
        AppleBookCreateVideoDiscoveryProviderOption(id: "newznab_torznab", label: "Indexers", available: true)
    ]

    private static let defaultBookDiscoveryProvider = AppleBookCreateDiscoveryProviderOption(
        id: defaultBookDiscoveryProviderID,
        label: "Default sources",
        available: true
    )

    private static let defaultVideoDiscoveryProvider = AppleBookCreateVideoDiscoveryProviderOption(
        id: defaultVideoDiscoveryProviderID,
        label: "Default sources",
        available: true
    )

    private static let bookDiscoveryCapabilities: Set<String> = [
        "search",
        "metadata",
        "acquire",
        "import_local"
    ]

    private static let videoDiscoveryCapabilities: Set<String> = [
        "search",
        "import_local"
    ]

    private static let explicitOnlyDefaultVideoDiscoveryProviderIDs: Set<String> = [
        "youtube_url"
    ]

    private static func isBookDiscoveryProvider(_ provider: AcquisitionProviderEntry) -> Bool {
        if let discoveryMediaKinds = provider.discoveryMediaKinds {
            return discoveryMediaKinds.contains("book")
        }
        return provider.mediaKinds.contains("book")
            && provider.capabilities.contains { bookDiscoveryCapabilities.contains($0) }
    }

    private static func isVideoDiscoveryProvider(_ provider: AcquisitionProviderEntry) -> Bool {
        if let discoveryMediaKinds = provider.discoveryMediaKinds {
            return discoveryMediaKinds.contains("video")
        }
        return provider.mediaKinds.contains("video")
            && provider.capabilities.contains { videoDiscoveryCapabilities.contains($0) }
    }

    private static func bookDiscoveryProviderRank(_ id: String) -> Int {
        if isDefaultBookDiscoveryProviderID(id) {
            return -1
        }
        return fallbackBookDiscoveryProviders.firstIndex { $0.id == id } ?? Int.max
    }

    private static func videoDiscoveryProviderRank(_ id: String) -> Int {
        if isDefaultVideoDiscoveryProviderID(id) {
            return -1
        }
        return fallbackVideoDiscoveryProviders.firstIndex { $0.id == id } ?? Int.max
    }

    private static func bookDiscoveryProviderLabel(_ provider: AcquisitionProviderEntry) -> String {
        fallbackBookDiscoveryProviders.first { $0.id == provider.id }?.label ?? provider.label
    }

    private static func videoDiscoveryProviderLabel(_ provider: AcquisitionProviderEntry) -> String {
        fallbackVideoDiscoveryProviders.first { $0.id == provider.id }?.label ?? provider.label
    }

    private static func defaultBookDiscoveryProviderOption(
        options: [AppleBookCreateDiscoveryProviderOption],
        defaultProviderIds: [String: [String]]
    ) -> AppleBookCreateDiscoveryProviderOption? {
        let backendDefaults = defaultProviderIds["book"] ?? []
        let optionIds = Set(options.map(\.id))
        let availableOptionIds = Set(options.filter(\.available).map(\.id))
        let availableDefaults = backendDefaults.filter { availableOptionIds.contains($0) }
        guard availableDefaults.count >= 2 else {
            return nil
        }
        guard backendDefaults.contains(where: { optionIds.contains($0) }) else {
            return nil
        }
        return defaultBookDiscoveryProvider
    }

    private static func defaultVideoDiscoveryProviderOption(
        options: [AppleBookCreateVideoDiscoveryProviderOption],
        defaultProviderIds: [String: [String]]
    ) -> AppleBookCreateVideoDiscoveryProviderOption? {
        let backendDefaults = defaultableProviderIDs(
            for: "video",
            providerIDs: defaultProviderIds["video"] ?? []
        )
        let optionIds = Set(options.map(\.id))
        let availableOptionIds = Set(options.filter(\.available).map(\.id))
        let availableDefaults = backendDefaults.filter { availableOptionIds.contains($0) }
        guard availableDefaults.count >= 2 else {
            return nil
        }
        guard backendDefaults.contains(where: { optionIds.contains($0) }) else {
            return nil
        }
        return defaultVideoDiscoveryProvider
    }

    private static func defaultableProviderIDs(
        for mediaKind: String,
        providerIDs: [String]
    ) -> [String] {
        guard mediaKind == "video" else {
            return providerIDs
        }
        return providerIDs.filter { !explicitOnlyDefaultVideoDiscoveryProviderIDs.contains($0) }
    }

    private static func discoveryProviderUnavailableMessage(
        for provider: AcquisitionProviderEntry,
        fallbackAction: String
    ) -> String {
        let status = formattedProviderStatus(provider.status)
        if let policyNote = provider.policyNotes.first(where: { !$0.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }) {
            return "\(provider.label) is \(status). \(policyNote)"
        }
        return "\(provider.label) is \(status). \(fallbackAction)"
    }

    private static func formattedProviderStatus(_ status: String) -> String {
        status.replacingOccurrences(of: "_", with: " ")
    }
}
