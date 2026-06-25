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
    static func contentIndexChapters(from value: JSONValue?) -> [AppleCreateChapterOption] {
        guard case let .object(root) = value,
              case let .array(chapterValues)? = root["chapters"] else {
            return []
        }
        var chapters = [AppleCreateChapterOption]()
        chapters.reserveCapacity(chapterValues.count)
        let totalSentences = contentIndexTotalSentences(from: root)
        for (index, chapterValue) in chapterValues.enumerated() {
            guard case let .object(chapter) = chapterValue else { continue }
            let start = chapter["start_sentence"]?.intValue
                ?? chapter["startSentence"]?.intValue
                ?? chapter["start"]?.intValue
            guard let start, start >= 0 else { continue }
            let normalizedStart = max(start, 1)
            let sentenceCount = chapter["sentence_count"]?.intValue ?? chapter["sentenceCount"]?.intValue
            var end = chapter["end_sentence"]?.intValue
                ?? chapter["endSentence"]?.intValue
                ?? chapter["end"]?.intValue
            if end == nil, let sentenceCount {
                end = normalizedStart + max(sentenceCount - 1, 0)
            }
            if let endValue = end, endValue < normalizedStart {
                end = normalizedStart
            }
            let id = chapter["id"]?.stringValue ?? "chapter-\(index + 1)"
            let title = chapter["title"]?.stringValue
                ?? chapter["toc_label"]?.stringValue
                ?? chapter["tocLabel"]?.stringValue
                ?? chapter["name"]?.stringValue
                ?? "Chapter \(index + 1)"
            chapters.append(
                AppleCreateChapterOption(
                    id: id,
                    title: title,
                    startSentence: normalizedStart,
                    endSentence: end
                )
            )
        }
        return inferredChapterEndSentences(chapters, totalSentences: totalSentences)
    }

    private static func contentIndexTotalSentences(from root: [String: JSONValue]) -> Int? {
        let direct = root["total_sentences"]?.intValue
            ?? root["totalSentences"]?.intValue
            ?? root["sentence_total"]?.intValue
            ?? root["sentenceTotal"]?.intValue
        if let direct, direct > 0 {
            return direct
        }
        guard case let .object(alignment)? = root["alignment"] else {
            return nil
        }
        let aligned = alignment["sentence_total"]?.intValue
            ?? alignment["sentenceTotal"]?.intValue
            ?? alignment["total_sentences"]?.intValue
            ?? alignment["totalSentences"]?.intValue
        return aligned.flatMap { $0 > 0 ? $0 : nil }
    }

    private static func inferredChapterEndSentences(
        _ chapters: [AppleCreateChapterOption],
        totalSentences: Int?
    ) -> [AppleCreateChapterOption] {
        chapters.enumerated().map { index, chapter in
            guard chapter.endSentence == nil else {
                return chapter
            }
            let nextStart = chapters.dropFirst(index + 1).first?.startSentence
            let inferredEnd = nextStart.map { max(chapter.startSentence, $0 - 1) }
                ?? totalSentences.map { max(chapter.startSentence, $0) }
            guard let inferredEnd else {
                return chapter
            }
            return AppleCreateChapterOption(
                id: chapter.id,
                title: chapter.title,
                startSentence: chapter.startSentence,
                endSentence: inferredEnd
            )
        }
    }

    static func chapterRangeSelection(
        chapters: [AppleCreateChapterOption],
        startChapterID: String,
        endChapterID: String
    ) -> AppleCreateChapterRangeSelection? {
        guard let startIndex = chapters.firstIndex(where: { $0.id == startChapterID }) else {
            return nil
        }
        let requestedEndIndex = chapters.firstIndex(where: { $0.id == endChapterID }) ?? startIndex
        let endIndex = max(startIndex, requestedEndIndex)
        let startChapter = chapters[startIndex]
        let endChapter = chapters[endIndex]
        let endSentence = endChapter.endSentence ?? endChapter.startSentence
        return AppleCreateChapterRangeSelection(
            startIndex: startIndex,
            endIndex: endIndex,
            startSentence: startChapter.startSentence,
            endSentence: max(startChapter.startSentence, endSentence),
            count: endIndex - startIndex + 1,
            label: startIndex == endIndex ? startChapter.title : "\(startChapter.title) - \(endChapter.title)"
        )
    }

    static func imageNodeAvailabilitySummary(_ response: ImageNodeAvailabilityResponse) -> String {
        let checked = response.nodes.count
        let available = response.available.count
        let unavailable = response.unavailable.count
        guard checked > 0 else {
            return "No image nodes were checked."
        }
        if unavailable == 0 {
            return "\(available) of \(checked) image nodes available."
        }
        return "\(available) of \(checked) image nodes available; \(unavailable) unavailable."
    }

    static func submitButtonPresentation(
        for mode: AppleCreateMode,
        isSubmitting: Bool
    ) -> AppleCreateSubmitPresentation {
        if isSubmitting {
            return AppleCreateSubmitPresentation(title: "Submitting", systemImage: "hourglass")
        }
        switch mode {
        case .generatedBook:
            return AppleCreateSubmitPresentation(title: "Generate Audiobook", systemImage: "sparkles")
        case .narrateEbook:
            return AppleCreateSubmitPresentation(title: "Narrate EPUB", systemImage: "book")
        case .subtitleJob:
            return AppleCreateSubmitPresentation(title: "Create Subtitles", systemImage: "captions.bubble")
        case .youtubeDub:
            return AppleCreateSubmitPresentation(title: "Create Dub", systemImage: "video")
        }
    }

    static func intakeStatusPresentation(for status: PipelineIntakeStatusResponse) -> AppleCreateIntakePresentation {
        let detailLines = [
            "Delayed jobs: \(status.delayCount)",
            status.softLimit.map { "Slowdown starts at \($0) pending" },
            status.hardLimit.map { "Capacity limit is \($0) pending" },
        ].compactMap { $0 }

        if !status.acceptingJobs {
            let limit = status.hardLimit.map { " of \($0)" } ?? ""
            return AppleCreateIntakePresentation(
                label: "Queue at capacity: \(status.queueDepth) pending\(limit). Wait for jobs to clear.",
                detailLines: detailLines
            )
        }

        if status.isUnderPressure {
            return AppleCreateIntakePresentation(
                label: "Queue pressure: \(status.queueDepth) pending, \(status.activeCount) running. New jobs may start more slowly.",
                detailLines: detailLines
            )
        }

        return AppleCreateIntakePresentation(
            label: "Job intake available: \(status.queueDepth) pending, \(status.activeCount) running.",
            detailLines: detailLines
        )
    }

    static func canSubmit(_ state: AppleCreateSubmitState) -> Bool {
        guard state.hasConfiguration else { return false }
        switch state.mode {
        case .generatedBook:
            return !normalizedPresentationText(state.topic).isEmpty
                && !normalizedPresentationText(state.bookName).isEmpty
                && !normalizedPresentationText(state.genre).isEmpty
        case .narrateEbook:
            return (state.hasNarrateLocalFile || !normalizedPresentationText(state.sourcePath).isEmpty)
                && !normalizedPresentationText(state.sourceBaseOutput).isEmpty
        case .subtitleJob:
            return state.hasSubtitleLocalFile || !normalizedPresentationText(state.subtitleSourcePath).isEmpty
        case .youtubeDub:
            return !normalizedPresentationText(state.youtubeVideoPath).isEmpty
                && !normalizedPresentationText(state.youtubeSubtitlePath).isEmpty
        }
    }

    static func derivedBaseOutput(
        for mode: AppleCreateMode,
        topic: String,
        bookName: String,
        sourceBaseOutput: String,
        subtitleSourcePath: String,
        youtubeVideoPath: String
    ) -> String {
        switch mode {
        case .generatedBook:
            return deriveBaseOutputName(bookName.isEmpty ? topic : bookName)
        case .narrateEbook:
            return normalizedPresentationText(sourceBaseOutput)
        case .subtitleJob:
            return deriveBaseOutputName(subtitleSourcePath)
        case .youtubeDub:
            return deriveBaseOutputName(youtubeVideoPath)
        }
    }

    static func subtitleModelLabel(_ model: String) -> String {
        let trimmedModel = normalizedPresentationText(model)
        return trimmedModel.isEmpty ? "Backend default" : trimmedModel
    }

    static func subtitleTransliterationModelLabel(_ model: String) -> String {
        let trimmedModel = normalizedPresentationText(model)
        return trimmedModel.isEmpty ? "Use translation model" : trimmedModel
    }

    static func availableSubtitleLlmModels(
        selected: String,
        inventory: [String]
    ) -> [String] {
        let selectedModel = normalizedPresentationText(selected)
        var seen = Set<String>()
        var options: [String] = []

        if !selectedModel.isEmpty {
            seen.insert(selectedModel.lowercased())
            options.append(selectedModel)
        }

        for model in inventory {
            let trimmedModel = normalizedPresentationText(model)
            guard !trimmedModel.isEmpty else { continue }
            if seen.insert(trimmedModel.lowercased()).inserted {
                options.append(trimmedModel)
            }
        }

        return options.isEmpty ? [""] : options
    }

    static func availableSubtitleTransliterationModels(
        selected: String,
        translationModel: String,
        inventory: [String]
    ) -> [String] {
        var seen = Set<String>()
        var options = [""]
        seen.insert("")

        for model in [selected, translationModel] + inventory {
            let trimmedModel = normalizedPresentationText(model)
            guard !trimmedModel.isEmpty else { continue }
            if seen.insert(trimmedModel.lowercased()).inserted {
                options.append(trimmedModel)
            }
        }
        return options
    }

    static func formattedAssEmphasisScale(_ value: Double) -> String {
        clampAssEmphasisScale(value).formatted(.number.precision(.fractionLength(2)))
    }

    static func formattedYoutubeOriginalMixPercent(_ value: Double) -> String {
        "\(Int(clampYoutubeOriginalMixPercent(value).rounded()))%"
    }

    static func formatDurationLabel(seconds: Double) -> String {
        let totalSeconds = max(0, Int(seconds.rounded(.down)))
        let hours = totalSeconds / 3_600
        let minutes = (totalSeconds % 3_600) / 60
        let seconds = totalSeconds % 60
        return String(format: "%02d:%02d:%02d", hours, minutes, seconds)
    }

    static func estimatedAudioDurationLabel(sentenceCount: Int?) -> String? {
        guard let sentenceCount, sentenceCount > 0 else {
            return nil
        }
        let seconds = Double(sentenceCount) * AppleCreateEstimatedAudio.secondsPerSentence
        let sentenceLabel = sentenceCount == 1 ? "sentence" : "sentences"
        return "Estimated audio duration: ~\(formatDurationLabel(seconds: seconds)) (\(sentenceCount) \(sentenceLabel), 6.4s/sentence)"
    }

    static func estimatedNarrateSentenceCount(startSentence: String, endSentence: String) -> Int? {
        let normalizedStart = normalizedPositiveInteger(startSentence) ?? 1
        guard let normalizedEnd = normalizedEndSentence(endSentence, startSentence: normalizedStart) else {
            return nil
        }
        let count = normalizedEnd - normalizedStart + 1
        return count > 0 ? count : nil
    }

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

    private static func normalizedPresentationText(_ value: String) -> String {
        value.trimmingCharacters(in: .whitespacesAndNewlines)
    }
}
