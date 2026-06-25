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
}

struct AppleBookCreateVideoDiscoveryProviderOption: Identifiable {
    let id: String
    let label: String
    let available: Bool
}

extension AppleBookCreatePresentation {
    static func youtubeVideoDiscoveryAvailability(
        providers: [AcquisitionProviderEntry]
    ) -> AppleBookCreateVideoDiscoveryAvailability {
        let youtubeSearchProvider = providers.first { $0.id == "youtube_search" }
        let downloadStationProvider = providers.first { $0.id == "download_station" }
        return AppleBookCreateVideoDiscoveryAvailability(
            youtubeSearchUnavailableMessage: youtubeSearchUnavailableMessage(for: youtubeSearchProvider),
            isYoutubeSearchAvailable: youtubeSearchProvider?.available != false,
            downloadStationUnavailableMessage: downloadStationUnavailableMessage(for: downloadStationProvider),
            isDownloadStationAvailable: downloadStationProvider?.available == true
        )
    }

    static func bookDiscoveryProviderUnavailableMessage(
        for provider: AcquisitionProviderEntry?
    ) -> String? {
        guard let provider, !provider.available else {
            return nil
        }
        return discoveryProviderUnavailableMessage(
            for: provider,
            fallbackAction: "Configure the backend source root or choose another discovery source."
        )
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
        from providers: [AcquisitionProviderEntry]
    ) -> [AppleBookCreateDiscoveryProviderOption] {
        let providers = providers.filter(isBookDiscoveryProvider)
        guard !providers.isEmpty else {
            return fallbackBookDiscoveryProviders
        }
        return providers
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
                    label: bookDiscoveryProviderLabel($0)
                )
            }
    }

    static func videoDiscoveryProviderOptions(
        from providers: [AcquisitionProviderEntry]
    ) -> [AppleBookCreateVideoDiscoveryProviderOption] {
        let providers = providers.filter(isVideoDiscoveryProvider)
        guard !providers.isEmpty else {
            return fallbackVideoDiscoveryProviders
        }
        return providers
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
        discovery?.candidates.filter {
            guard $0.mediaKind == "video", $0.provider == providerID else {
                return false
            }
            if providerID == "youtube_search" {
                return $0.sourceUrl?.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty == false
            }
            if providerID == "newznab_torznab" {
                return $0.requiresConfirmation
            }
            return $0.localPath?.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty == false
        } ?? []
    }

    static func videoDiscoveryQueryPlaceholder(providerID: String) -> String {
        providerID == "youtube_search"
            ? "Search YouTube videos"
            : providerID == "newznab_torznab"
                ? "Search configured indexers"
            : "Search title or filename"
    }

    static func noVideoDiscoveryCandidatesMessage(providerID: String) -> String {
        providerID == "youtube_search"
            ? "No YouTube search results matched this discovery search."
            : providerID == "newznab_torznab"
                ? "No indexer metadata matched this discovery search."
            : "No local video sources matched this discovery search."
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

    static func videoDiscoveryCandidateDetail(_ candidate: AcquisitionCandidate) -> String {
        var details = [candidate.provider]
        if let localPath = candidate.localPath?.trimmingCharacters(in: .whitespacesAndNewlines), !localPath.isEmpty {
            details.append(localPath)
        }
        if let sourceUrl = candidate.sourceUrl?.trimmingCharacters(in: .whitespacesAndNewlines), !sourceUrl.isEmpty {
            details.append(sourceUrl)
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
        }
        if !candidate.subtitles.isEmpty {
            let count = candidate.subtitles.count
            details.append(count == 1 ? "1 subtitle" : "\(count) subtitles")
        }
        return details.joined(separator: " · ")
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
        AppleBookCreateDiscoveryProviderOption(id: "local_epub", label: "Local EPUBs"),
        AppleBookCreateDiscoveryProviderOption(id: "manual_downloads", label: "Manual downloads"),
        AppleBookCreateDiscoveryProviderOption(id: "gutenberg", label: "Gutenberg"),
        AppleBookCreateDiscoveryProviderOption(id: "internet_archive", label: "Internet Archive"),
        AppleBookCreateDiscoveryProviderOption(id: "openlibrary", label: "Open Library"),
        AppleBookCreateDiscoveryProviderOption(id: "zlibrary_attended", label: "Z-Library import")
    ]

    private static let fallbackVideoDiscoveryProviders = [
        AppleBookCreateVideoDiscoveryProviderOption(id: "nas_video", label: "NAS videos", available: true),
        AppleBookCreateVideoDiscoveryProviderOption(id: "manual_downloads", label: "Manual downloads", available: true),
        AppleBookCreateVideoDiscoveryProviderOption(id: "youtube_search", label: "YouTube search", available: true),
        AppleBookCreateVideoDiscoveryProviderOption(id: "newznab_torznab", label: "Indexers", available: true)
    ]

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

    private static func isBookDiscoveryProvider(_ provider: AcquisitionProviderEntry) -> Bool {
        provider.mediaKinds.contains("book")
            && provider.capabilities.contains { bookDiscoveryCapabilities.contains($0) }
    }

    private static func isVideoDiscoveryProvider(_ provider: AcquisitionProviderEntry) -> Bool {
        provider.mediaKinds.contains("video")
            && provider.capabilities.contains { videoDiscoveryCapabilities.contains($0) }
    }

    private static func bookDiscoveryProviderRank(_ id: String) -> Int {
        fallbackBookDiscoveryProviders.firstIndex { $0.id == id } ?? Int.max
    }

    private static func videoDiscoveryProviderRank(_ id: String) -> Int {
        fallbackVideoDiscoveryProviders.firstIndex { $0.id == id } ?? Int.max
    }

    private static func bookDiscoveryProviderLabel(_ provider: AcquisitionProviderEntry) -> String {
        fallbackBookDiscoveryProviders.first { $0.id == provider.id }?.label ?? provider.label
    }

    private static func videoDiscoveryProviderLabel(_ provider: AcquisitionProviderEntry) -> String {
        fallbackVideoDiscoveryProviders.first { $0.id == provider.id }?.label ?? provider.label
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
