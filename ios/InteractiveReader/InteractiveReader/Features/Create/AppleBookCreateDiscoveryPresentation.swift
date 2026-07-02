import Foundation

struct AppleBookCreateDiscoveryProviderOption: Identifiable {
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
    static func discoveryPolicyNotes(from discovery: AcquisitionDiscoveryResponse?) -> [String] {
        var seen = Set<String>()
        return (discovery?.policyNotes ?? []).reduce(into: [String]()) { notes, rawNote in
            let note = rawNote.trimmingCharacters(in: .whitespacesAndNewlines)
            guard !note.isEmpty, !seen.contains(note) else {
                return
            }
            seen.insert(note)
            notes.append(note)
        }
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
                fallbackAction: sourceFallbackAction(for: provider)
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
            defaultProviderIds: defaultProviderIds,
            providers: providers
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
        providers: [AcquisitionProviderEntry] = [],
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
            providerIDs: defaultProviderIds[mediaKind] ?? [],
            providers: providers
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
        from discovery: AcquisitionDiscoveryResponse?,
        providerID: String,
        providers: [AcquisitionProviderEntry] = []
    ) -> [AcquisitionCandidate] {
        let queriedProviders = Set(discovery?.providersQueried ?? [])
        return discovery?.candidates.filter {
            let effectiveProvider = isDefaultBookDiscoveryProviderID(providerID) ? $0.provider : providerID
            guard $0.mediaKind == "book" else {
                return false
            }
            guard $0.provider == effectiveProvider else {
                return false
            }
            if isDefaultBookDiscoveryProviderID(providerID),
               !defaultableProviderIDs(
                   for: "book",
                   providerIDs: [$0.provider],
                   providers: providers
               ).contains($0.provider) {
                return false
            }
            if isDefaultBookDiscoveryProviderID(providerID),
               !queriedProviders.isEmpty,
               !queriedProviders.contains($0.provider) {
                return false
            }
            let localPath = $0.localPath?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
            return !localPath.isEmpty
                || $0.capabilities.contains("acquire")
                || $0.capabilities.contains("metadata")
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
        _ candidate: AcquisitionCandidate,
        preparedMetadata: [String: JSONValue]? = nil
    ) -> AppleBookCreateBookDiscoveryMetadataApplication? {
        guard candidate.capabilities.contains("metadata") else {
            return nil
        }
        var metadata = candidate.metadata ?? [:]
        if let preparedMetadata {
            for (key, value) in preparedMetadata {
                metadata[key] = value
            }
        }
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

    static let defaultBookDiscoveryProviderID = "backend_defaults"

    static func isDefaultBookDiscoveryProviderID(_ providerID: String) -> Bool {
        providerID
            .trimmingCharacters(in: .whitespacesAndNewlines)
            .localizedCaseInsensitiveCompare(defaultBookDiscoveryProviderID) == .orderedSame
    }

    static func discoveryRequestProviderID(for providerID: String, mediaKind: String) -> String? {
        guard let normalizedProvider = providerID
            .trimmingCharacters(in: .whitespacesAndNewlines)
            .nonEmptyValue
        else {
            return nil
        }
        let normalizedMediaKind = mediaKind
            .trimmingCharacters(in: .whitespacesAndNewlines)
            .lowercased()
        if normalizedMediaKind == "book", isDefaultBookDiscoveryProviderID(normalizedProvider) {
            return nil
        }
        if normalizedMediaKind == "video", isDefaultVideoDiscoveryProviderID(normalizedProvider) {
            return nil
        }
        return normalizedProvider
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
        if extras["source_provider"] == nil {
            extras["source_provider"] = .string(candidate.provider)
        }
        if extras["acquisition_provider"] == nil {
            extras["acquisition_provider"] = .string(candidate.provider)
        }
        if extras["acquisition_candidate_id"] == nil {
            extras["acquisition_candidate_id"] = .string(candidate.candidateId)
        }
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

    private static let fallbackBookDiscoveryProviders = [
        AppleBookCreateDiscoveryProviderOption(id: "local_epub", label: "Local EPUBs", available: true),
        AppleBookCreateDiscoveryProviderOption(id: "manual_downloads", label: "Manual downloads", available: true),
        AppleBookCreateDiscoveryProviderOption(id: "gutenberg", label: "Gutenberg", available: true),
        AppleBookCreateDiscoveryProviderOption(id: "internet_archive", label: "Internet Archive", available: true),
        AppleBookCreateDiscoveryProviderOption(id: "openlibrary", label: "Open Library", available: true),
        AppleBookCreateDiscoveryProviderOption(id: "zlibrary_attended", label: "Z-Library import", available: false)
    ]

    private static let defaultBookDiscoveryProvider = AppleBookCreateDiscoveryProviderOption(
        id: defaultBookDiscoveryProviderID,
        label: "Default sources",
        available: true
    )

    private static let explicitOnlyDefaultVideoDiscoveryProviderIDs: Set<String> = [
        "youtube_url"
    ]

    private static func isBookDiscoveryProvider(_ provider: AcquisitionProviderEntry) -> Bool {
        return provider.discoveryMediaKinds.contains("book")
    }

    private static func bookDiscoveryProviderRank(_ id: String) -> Int {
        if isDefaultBookDiscoveryProviderID(id) {
            return -1
        }
        return fallbackBookDiscoveryProviders.firstIndex { $0.id == id } ?? Int.max
    }

    private static func bookDiscoveryProviderLabel(_ provider: AcquisitionProviderEntry) -> String {
        fallbackBookDiscoveryProviders.first { $0.id == provider.id }?.label ?? provider.label
    }

    private static func defaultBookDiscoveryProviderOption(
        options: [AppleBookCreateDiscoveryProviderOption],
        defaultProviderIds: [String: [String]],
        providers: [AcquisitionProviderEntry]
    ) -> AppleBookCreateDiscoveryProviderOption? {
        let backendDefaults = defaultableProviderIDs(
            for: "book",
            providerIDs: defaultProviderIds["book"] ?? [],
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
        return defaultBookDiscoveryProvider
    }

    static func defaultableProviderIDs(
        for mediaKind: String,
        providerIDs: [String],
        providers: [AcquisitionProviderEntry] = []
    ) -> [String] {
        let providersByID = Dictionary(uniqueKeysWithValues: providers.map { ($0.id, $0) })
        let hasProviderInventory = !providers.isEmpty
        return providerIDs.filter {
            guard let provider = providersByID[$0] else {
                if hasProviderInventory {
                    return false
                }
                guard mediaKind == "video" else {
                    return true
                }
                return !explicitOnlyDefaultVideoDiscoveryProviderIDs.contains($0)
            }
            return provider.defaultEligibleMediaKinds.contains(mediaKind)
        }
    }

    static func discoveryProviderUnavailableMessage(
        for provider: AcquisitionProviderEntry,
        fallbackAction: String
    ) -> String {
        let status = formattedProviderStatus(provider.status)
        if let policyNote = provider.policyNotes.first(where: { !$0.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }) {
            return "\(provider.label) is \(status). \(policyNote)"
        }
        return "\(provider.label) is \(status). \(fallbackAction)"
    }

    static func sourceFallbackAction(for provider: AcquisitionProviderEntry) -> String {
        let sourceLabel = provider.sourceLabel?
            .trimmingCharacters(in: .whitespacesAndNewlines)
            .lowercased()
        let sourceName: String
        if let sourceLabel, !sourceLabel.isEmpty {
            sourceName = sourceLabel
        } else {
            sourceName = "the backend source root"
        }
        return "Configure \(sourceName) or choose another discovery source."
    }

    static func formattedProviderStatus(_ status: String) -> String {
        status.replacingOccurrences(of: "_", with: " ")
    }
}
