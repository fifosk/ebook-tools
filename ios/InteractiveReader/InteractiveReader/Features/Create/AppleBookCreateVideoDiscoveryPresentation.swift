import Foundation

struct AppleBookCreateVideoDiscoveryAvailability {
    let youtubeSearchUnavailableMessage: String?
    let isYoutubeSearchAvailable: Bool
    let downloadStationUnavailableMessage: String?
    let isDownloadStationAvailable: Bool
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
        let hasProviderInventory = !providers.isEmpty
        return AppleBookCreateVideoDiscoveryAvailability(
            youtubeSearchUnavailableMessage: youtubeSearchUnavailableMessage(for: youtubeSearchProvider),
            isYoutubeSearchAvailable: youtubeSearchProvider?.available ?? !hasProviderInventory,
            downloadStationUnavailableMessage: downloadStationUnavailableMessage(for: downloadStationProvider),
            isDownloadStationAvailable: downloadStationProvider?.available == true
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
            fallbackAction: sourceFallbackAction(for: provider)
        )
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
            defaultProviderIds: defaultProviderIds,
            providers: providers
        ) else {
            return providerOptions
        }
        return [defaultOption] + providerOptions
    }

    static func videoDiscoveryCandidates(
        from discovery: AcquisitionDiscoveryResponse?,
        providerID: String,
        providers: [AcquisitionProviderEntry] = []
    ) -> [AcquisitionCandidate] {
        let queriedProviders = Set(discovery?.providersQueried ?? [])
        return discovery?.candidates.filter {
            let effectiveProvider = isDefaultVideoDiscoveryProviderID(providerID) ? $0.provider : providerID
            if isDefaultVideoDiscoveryProviderID(providerID),
               !defaultableProviderIDs(
                   for: "video",
                   providerIDs: [$0.provider],
                   providers: providers
               ).contains($0.provider) {
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
        selectedSubtitlePath: String?,
        selectedProvider: String? = nil,
        query: String? = nil,
        preparedMetadata: [String: JSONValue]? = nil
    ) -> [String: JSONValue] {
        var state: [String: JSONValue] = [
            "media_kind": .string("video"),
            "provider": .string(candidate.provider),
            "candidate_id": .string(candidate.candidateId),
            "title": .string(candidate.title),
            "rights": .string(candidate.rights),
            "capabilities": .array(candidate.capabilities.map { .string($0) }),
        ]
        let sourceProvider = preparedMetadata?["source_provider"]?.stringValue?
            .trimmingCharacters(in: .whitespacesAndNewlines)
            .nonEmptyValue
            ?? candidate.metadata?["source_provider"]?.stringValue?
                .trimmingCharacters(in: .whitespacesAndNewlines)
                .nonEmptyValue
        if let sourceProvider {
            state["source_provider"] = .string(sourceProvider)
        }
        let acquisitionProvider = preparedMetadata?["acquisition_provider"]?.stringValue?
            .trimmingCharacters(in: .whitespacesAndNewlines)
            .nonEmptyValue
            ?? candidate.metadata?["acquisition_provider"]?.stringValue?
                .trimmingCharacters(in: .whitespacesAndNewlines)
                .nonEmptyValue
        if let acquisitionProvider {
            state["acquisition_provider"] = .string(acquisitionProvider)
        }
        let acquisitionCandidateID = preparedMetadata?["acquisition_candidate_id"]?.stringValue?
            .trimmingCharacters(in: .whitespacesAndNewlines)
            .nonEmptyValue
            ?? candidate.metadata?["acquisition_candidate_id"]?.stringValue?
                .trimmingCharacters(in: .whitespacesAndNewlines)
                .nonEmptyValue
        if let acquisitionCandidateID {
            state["acquisition_candidate_id"] = .string(acquisitionCandidateID)
        }
        if let sourceKind = preparedMetadata?["source_kind"]?.stringValue?
            .trimmingCharacters(in: .whitespacesAndNewlines)
            .nonEmptyValue {
            state["source_kind"] = .string(sourceKind)
        } else if let sourceKind = candidate.metadata?["source_kind"]?.stringValue?
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
        if let selectedProvider = selectedProvider?.trimmingCharacters(in: .whitespacesAndNewlines).nonEmptyValue {
            state["selected_provider"] = .string(selectedProvider)
        }
        if let query = query?.trimmingCharacters(in: .whitespacesAndNewlines).nonEmptyValue {
            state["query"] = .string(query)
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

    static func isDefaultVideoDiscoveryProviderID(_ providerID: String) -> Bool {
        providerID
            .trimmingCharacters(in: .whitespacesAndNewlines)
            .localizedCaseInsensitiveCompare(defaultVideoDiscoveryProviderID) == .orderedSame
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

    private static let fallbackVideoDiscoveryProviders = [
        AppleBookCreateVideoDiscoveryProviderOption(id: "nas_video", label: "NAS videos", available: true),
        AppleBookCreateVideoDiscoveryProviderOption(id: "manual_downloads", label: "Manual downloads", available: true),
        AppleBookCreateVideoDiscoveryProviderOption(id: "youtube_url", label: "YouTube URL", available: true),
        AppleBookCreateVideoDiscoveryProviderOption(id: "youtube_search", label: "YouTube search", available: true),
        AppleBookCreateVideoDiscoveryProviderOption(id: "newznab_torznab", label: "Indexers", available: true)
    ]

    private static let defaultVideoDiscoveryProvider = AppleBookCreateVideoDiscoveryProviderOption(
        id: defaultVideoDiscoveryProviderID,
        label: "Default sources",
        available: true
    )

    private static let videoDiscoveryCapabilities: Set<String> = [
        "search",
        "import_local"
    ]

    private static func isVideoDiscoveryProvider(_ provider: AcquisitionProviderEntry) -> Bool {
        if let discoveryMediaKinds = provider.discoveryMediaKinds {
            return discoveryMediaKinds.contains("video")
        }
        return provider.mediaKinds.contains("video")
            && provider.capabilities.contains { videoDiscoveryCapabilities.contains($0) }
    }

    private static func videoDiscoveryProviderRank(_ id: String) -> Int {
        if isDefaultVideoDiscoveryProviderID(id) {
            return -1
        }
        return fallbackVideoDiscoveryProviders.firstIndex { $0.id == id } ?? Int.max
    }

    private static func videoDiscoveryProviderLabel(_ provider: AcquisitionProviderEntry) -> String {
        fallbackVideoDiscoveryProviders.first { $0.id == provider.id }?.label ?? provider.label
    }

    private static func defaultVideoDiscoveryProviderOption(
        options: [AppleBookCreateVideoDiscoveryProviderOption],
        defaultProviderIds: [String: [String]],
        providers: [AcquisitionProviderEntry]
    ) -> AppleBookCreateVideoDiscoveryProviderOption? {
        let backendDefaults = defaultableProviderIDs(
            for: "video",
            providerIDs: defaultProviderIds["video"] ?? [],
            providers: providers
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
}
