import Foundation

struct AppleBookCreatePreparedDiscoverySelection: Equatable {
    let path: String
    let metadata: [String: JSONValue]?
}

extension AppleBookCreateViewModel {
    func loadAcquisitionProviders(
        using appState: AppState,
        cacheKey: String,
        force: Bool = false
    ) async -> [AcquisitionProviderEntry] {
        guard let configuration = appState.configuration else {
            acquisitionProvidersErrorMessage = "API configuration is unavailable."
            return acquisitionProviders
        }
        if !force, loadedAcquisitionProvidersCacheKey == cacheKey, !acquisitionProviders.isEmpty {
            return acquisitionProviders
        }

        acquisitionProvidersErrorMessage = nil
        do {
            let client = APIClient(configuration: configuration)
            let response = try await client.fetchAcquisitionProviders()
            acquisitionProviders = response.providers
            acquisitionDefaultProviderIds = response.defaultProviderIds ?? [:]
            loadedAcquisitionProvidersCacheKey = cacheKey
        } catch {
            acquisitionProvidersErrorMessage = error.localizedDescription
        }
        return acquisitionProviders
    }

    func loadPipelineFiles(
        using appState: AppState,
        cacheKey: String,
        force: Bool = false
    ) async -> PipelineFileBrowserResponse? {
        guard let configuration = appState.configuration else {
            return nil
        }
        if !force, loadedPipelineFilesCacheKey == cacheKey, let pipelineFiles {
            return pipelineFiles
        }

        isLoadingPipelineFiles = true
        pipelineFilesErrorMessage = nil
        defer { isLoadingPipelineFiles = false }

        do {
            let client = APIClient(configuration: configuration)
            let response = try await client.fetchPipelineFiles()
            pipelineFiles = response
            loadedPipelineFilesCacheKey = cacheKey
            return response
        } catch {
            pipelineFiles = nil
            pipelineFilesErrorMessage = error.localizedDescription
            return nil
        }
    }

    func loadEbookDiscovery(
        using appState: AppState,
        cacheKey: String,
        query: String? = nil,
        provider: String = AppleBookCreatePresentation.defaultBookDiscoveryProviderID,
        sourceIds: [String] = [],
        force: Bool = false
    ) async -> AcquisitionDiscoveryResponse? {
        guard let configuration = appState.configuration else {
            return nil
        }
        let normalizedQuery = query?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        let normalizedProvider = provider.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
            ? AppleBookCreatePresentation.defaultBookDiscoveryProviderID
            : provider.trimmingCharacters(in: .whitespacesAndNewlines)
        let requestProvider = AppleBookCreatePresentation.discoveryRequestProviderID(
            for: normalizedProvider,
            mediaKind: "book"
        )
        let normalizedSourceIds = sourceIds
            .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
            .filter { !$0.isEmpty }
        let discoveryCacheKey = "\(cacheKey)::book::\(normalizedProvider)::\(normalizedQuery)::\(normalizedSourceIds.joined(separator: ","))"
        if !force, loadedEbookAcquisitionDiscoveryCacheKey == discoveryCacheKey, let ebookAcquisitionDiscovery {
            return ebookAcquisitionDiscovery
        }

        ebookAcquisitionDiscoveryRequestSequence += 1
        let requestSequence = ebookAcquisitionDiscoveryRequestSequence
        isLoadingEbookAcquisitionDiscovery = true
        ebookAcquisitionDiscoveryErrorMessage = nil
        defer {
            if requestSequence == ebookAcquisitionDiscoveryRequestSequence {
                isLoadingEbookAcquisitionDiscovery = false
            }
        }

        do {
            let client = APIClient(configuration: configuration)
            let response = try await client.discoverAcquisitionCandidates(
                mediaKind: "book",
                query: normalizedQuery,
                provider: requestProvider,
                sourceIds: normalizedSourceIds,
                limit: 25
            )
            guard requestSequence == ebookAcquisitionDiscoveryRequestSequence else {
                return ebookAcquisitionDiscovery
            }
            ebookAcquisitionDiscovery = response
            loadedEbookAcquisitionDiscoveryCacheKey = discoveryCacheKey
            return response
        } catch APIClientError.httpError(let statusCode, _) where statusCode == 404 {
            guard requestSequence == ebookAcquisitionDiscoveryRequestSequence else {
                return ebookAcquisitionDiscovery
            }
            ebookAcquisitionDiscovery = nil
            ebookAcquisitionDiscoveryErrorMessage = "This backend does not expose source discovery yet."
            return nil
        } catch {
            guard requestSequence == ebookAcquisitionDiscoveryRequestSequence else {
                return ebookAcquisitionDiscovery
            }
            ebookAcquisitionDiscovery = nil
            ebookAcquisitionDiscoveryErrorMessage = error.localizedDescription
            return nil
        }
    }

    func acquireEbookDiscoveryCandidate(
        using appState: AppState,
        candidate: AcquisitionCandidate
    ) async -> AppleBookCreatePreparedDiscoverySelection? {
        guard let configuration = appState.configuration else {
            return nil
        }
        guard candidate.capabilities.contains("acquire") else {
            ebookAcquisitionDiscoveryErrorMessage =
                "Open Library results provide metadata only. Choose a local, Gutenberg, Internet Archive, or manually downloaded EPUB source before narrating."
            return nil
        }
        isAcquiringEbookDiscoveryCandidate = true
        ebookAcquisitionDiscoveryErrorMessage = nil
        defer { isAcquiringEbookDiscoveryCandidate = false }

        do {
            let client = APIClient(configuration: configuration)
            let artifact = try await client.acquireAcquisitionCandidate(
                candidateToken: candidate.candidateToken,
                confirmed: true,
                filename: "\(candidate.title).epub"
            )
            if let artifactId = artifact.artifactId.trimmingCharacters(in: .whitespacesAndNewlines).nonEmptyValue {
                let prepared = try await client.prepareAcquisitionArtifact(artifactId: artifactId)
                guard let path = prepared.inputFile?.trimmingCharacters(in: .whitespacesAndNewlines).nonEmptyValue
                    ?? prepared.localPath.trimmingCharacters(in: .whitespacesAndNewlines).nonEmptyValue
                    ?? artifact.localPath.trimmingCharacters(in: .whitespacesAndNewlines).nonEmptyValue else {
                    return nil
                }
                return AppleBookCreatePreparedDiscoverySelection(path: path, metadata: prepared.metadata)
            }
            guard let path = artifact.localPath.trimmingCharacters(in: .whitespacesAndNewlines).nonEmptyValue else {
                return nil
            }
            return AppleBookCreatePreparedDiscoverySelection(path: path, metadata: artifact.metadata)
        } catch {
            ebookAcquisitionDiscoveryErrorMessage = error.localizedDescription
            return nil
        }
    }

    func prepareEbookDiscoveryCandidate(
        using appState: AppState,
        candidate: AcquisitionCandidate
    ) async -> AppleBookCreatePreparedDiscoverySelection? {
        guard let configuration = appState.configuration else {
            return nil
        }
        isAcquiringEbookDiscoveryCandidate = true
        ebookAcquisitionDiscoveryErrorMessage = nil
        defer { isAcquiringEbookDiscoveryCandidate = false }

        do {
            let client = APIClient(configuration: configuration)
            let prepared = try await client.prepareAcquisitionArtifact(
                artifactId: candidate.candidateToken
            )
            guard let path = prepared.inputFile?.trimmingCharacters(in: .whitespacesAndNewlines).nonEmptyValue
                ?? prepared.localPath.trimmingCharacters(in: .whitespacesAndNewlines).nonEmptyValue
                ?? candidate.localPath?.trimmingCharacters(in: .whitespacesAndNewlines).nonEmptyValue else {
                return nil
            }
            return AppleBookCreatePreparedDiscoverySelection(path: path, metadata: prepared.metadata)
        } catch {
            ebookAcquisitionDiscoveryErrorMessage = error.localizedDescription
            return nil
        }
    }

    func loadVideoDiscovery(
        using appState: AppState,
        cacheKey: String,
        query: String? = nil,
        provider: String = AppleBookCreatePresentation.defaultVideoDiscoveryProviderID,
        force: Bool = false
    ) async -> AcquisitionDiscoveryResponse? {
        guard let configuration = appState.configuration else {
            return nil
        }
        let normalizedQuery = query?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        let requestedProvider = provider.trimmingCharacters(in: .whitespacesAndNewlines)
        let normalizedProvider = requestedProvider.nonEmptyValue
            ?? AppleBookCreatePresentation.defaultVideoDiscoveryProviderID
        let requestProvider = AppleBookCreatePresentation.discoveryRequestProviderID(
            for: normalizedProvider,
            mediaKind: "video"
        )
        let discoveryCacheKey = "\(cacheKey)::video::\(normalizedProvider)::\(normalizedQuery)"
        if !force, loadedYoutubeAcquisitionDiscoveryCacheKey == discoveryCacheKey, let youtubeAcquisitionDiscovery {
            return youtubeAcquisitionDiscovery
        }

        youtubeAcquisitionDiscoveryRequestSequence += 1
        let requestSequence = youtubeAcquisitionDiscoveryRequestSequence
        isLoadingYoutubeAcquisitionDiscovery = true
        youtubeAcquisitionDiscoveryErrorMessage = nil
        defer {
            if requestSequence == youtubeAcquisitionDiscoveryRequestSequence {
                isLoadingYoutubeAcquisitionDiscovery = false
            }
        }

        do {
            let client = APIClient(configuration: configuration)
            let response = try await client.discoverAcquisitionCandidates(
                mediaKind: "video",
                query: normalizedQuery,
                provider: requestProvider,
                limit: 25
            )
            guard requestSequence == youtubeAcquisitionDiscoveryRequestSequence else {
                return youtubeAcquisitionDiscovery
            }
            youtubeAcquisitionDiscovery = response
            loadedYoutubeAcquisitionDiscoveryCacheKey = discoveryCacheKey
            return response
        } catch APIClientError.httpError(let statusCode, _) where statusCode == 404 {
            guard requestSequence == youtubeAcquisitionDiscoveryRequestSequence else {
                return youtubeAcquisitionDiscovery
            }
            youtubeAcquisitionDiscovery = nil
            youtubeAcquisitionDiscoveryErrorMessage = "This backend does not expose source discovery yet."
            return nil
        } catch {
            guard requestSequence == youtubeAcquisitionDiscoveryRequestSequence else {
                return youtubeAcquisitionDiscovery
            }
            youtubeAcquisitionDiscovery = nil
            youtubeAcquisitionDiscoveryErrorMessage = error.localizedDescription
            return nil
        }
    }

    func prepareVideoDiscoveryCandidate(
        using appState: AppState,
        candidate: AcquisitionCandidate
    ) async -> AcquisitionPreparedArtifactResponse? {
        guard let configuration = appState.configuration else {
            youtubeAcquisitionDiscoveryErrorMessage = "API configuration is unavailable."
            return nil
        }
        isPreparingYoutubeAcquisitionCandidate = true
        youtubeAcquisitionDiscoveryErrorMessage = nil
        defer { isPreparingYoutubeAcquisitionCandidate = false }

        do {
            let client = APIClient(configuration: configuration)
            return try await client.prepareAcquisitionArtifact(
                artifactId: candidate.candidateToken
            )
        } catch {
            youtubeAcquisitionDiscoveryErrorMessage = error.localizedDescription
            return nil
        }
    }

    func submitDownloadStationTask(
        using appState: AppState,
        sourceURI: String?,
        candidateToken: String? = nil,
        destination: String?,
        confirmed: Bool
    ) async -> Bool {
        guard let configuration = appState.configuration else {
            downloadStationErrorMessage = "Configure a valid API base URL before submitting Download Station tasks."
            return false
        }
        let trimmedSourceURI = sourceURI?.trimmingCharacters(in: .whitespacesAndNewlines).nonEmptyValue
        let trimmedCandidateToken = candidateToken?.trimmingCharacters(in: .whitespacesAndNewlines).nonEmptyValue
        guard trimmedSourceURI != nil || trimmedCandidateToken != nil else {
            downloadStationErrorMessage = "Enter a reviewed URL or magnet link."
            return false
        }
        guard confirmed else {
            downloadStationErrorMessage = "Confirm that you are authorized to download and process this source."
            return false
        }

        isSubmittingDownloadStation = true
        downloadStationErrorMessage = nil
        downloadStationMessage = nil
        defer { isSubmittingDownloadStation = false }

        do {
            let client = APIClient(configuration: configuration)
            let job = try await client.createAcquisitionJob(
                sourceURI: trimmedSourceURI,
                candidateToken: trimmedCandidateToken,
                confirmed: true,
                destination: destination?.trimmingCharacters(in: .whitespacesAndNewlines).nonEmptyValue
            )
            downloadStationJob = job
            downloadStationMessage = job.message ?? "Download Station task \(job.taskId) submitted."
            return true
        } catch {
            downloadStationErrorMessage = error.localizedDescription
            return false
        }
    }

    func pollDownloadStationTask(using appState: AppState) async -> Bool {
        guard let configuration = appState.configuration else {
            downloadStationErrorMessage = "Configure a valid API base URL before polling Download Station tasks."
            return false
        }
        guard let taskID = downloadStationJob?.taskId.trimmingCharacters(in: .whitespacesAndNewlines),
              !taskID.isEmpty else {
            downloadStationErrorMessage = "No Download Station task is ready to poll."
            return false
        }

        isPollingDownloadStation = true
        downloadStationErrorMessage = nil
        defer { isPollingDownloadStation = false }

        do {
            let client = APIClient(configuration: configuration)
            let job = try await client.fetchAcquisitionJobStatus(taskId: taskID)
            downloadStationJob = job
            if job.status == "completed" {
                let completedFiles = AppleBookCreatePresentation.downloadStationCompletedFiles(from: job)
                    .map(AppleBookCreatePresentation.filenameFromPath)
                    .filter { !$0.isEmpty }
                let completedSummary = completedFiles.isEmpty
                    ? ""
                    : " Completed: \(completedFiles.joined(separator: ", "))."
                downloadStationMessage = "Download Station task completed.\(completedSummary) Manual downloads were refreshed for selection."
            } else {
                downloadStationMessage = job.message ?? "Download Station task is \(job.status)."
            }
            return job.status == "completed"
        } catch {
            downloadStationErrorMessage = error.localizedDescription
            return false
        }
    }

    func deletePipelineEbook(
        path: String,
        using appState: AppState
    ) async -> Bool {
        guard let configuration = appState.configuration else {
            pipelineFilesErrorMessage = "Configure a valid API base URL before continuing."
            return false
        }
        let trimmedPath = path.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmedPath.isEmpty else {
            pipelineFilesErrorMessage = "Select a server EPUB before deleting it."
            return false
        }

        isDeletingPipelineEbook = true
        pipelineFilesErrorMessage = nil
        defer { isDeletingPipelineEbook = false }

        do {
            let client = APIClient(configuration: configuration)
            try await client.deletePipelineEbook(path: trimmedPath)
            if let currentFiles = pipelineFiles {
                pipelineFiles = PipelineFileBrowserResponse(
                    ebooks: currentFiles.ebooks.filter { $0.path != trimmedPath },
                    outputs: currentFiles.outputs,
                    booksRoot: currentFiles.booksRoot,
                    outputRoot: currentFiles.outputRoot
                )
            }
            return true
        } catch {
            pipelineFilesErrorMessage = error.localizedDescription
            return false
        }
    }

    func uploadPipelineEbook(
        fileURL: URL,
        filename: String?,
        using appState: AppState
    ) async -> PipelineFileEntry? {
        guard let configuration = appState.configuration else {
            pipelineFilesErrorMessage = "Configure a valid API base URL before importing an EPUB."
            return nil
        }

        isUploadingPipelineEbook = true
        pipelineFilesErrorMessage = nil
        errorMessage = nil
        defer { isUploadingPipelineEbook = false }

        do {
            let client = APIClient(configuration: configuration)
            let uploaded = try await client.uploadPipelineEbook(fileURL: fileURL, filename: filename)
            mergePipelineEbook(uploaded)
            loadedPipelineFilesCacheKey = nil
            return uploaded
        } catch {
            pipelineFilesErrorMessage = error.localizedDescription
            errorMessage = "EPUB import failed: \(error.localizedDescription)"
            return nil
        }
    }

    func loadSubtitleSources(
        using appState: AppState,
        cacheKey: String,
        force: Bool = false
    ) async -> SubtitleSourceListResponse? {
        guard let configuration = appState.configuration else {
            return nil
        }
        if !force, loadedSubtitleSourcesCacheKey == cacheKey, let subtitleSources {
            return subtitleSources
        }

        isLoadingSubtitleSources = true
        subtitleSourcesErrorMessage = nil
        defer { isLoadingSubtitleSources = false }

        do {
            let client = APIClient(configuration: configuration)
            let response = try await client.fetchSubtitleSources()
            subtitleSources = response
            loadedSubtitleSourcesCacheKey = cacheKey
            return response
        } catch {
            subtitleSources = nil
            subtitleSourcesErrorMessage = error.localizedDescription
            return nil
        }
    }

    func deleteSubtitleSource(
        path: String,
        using appState: AppState
    ) async -> Bool {
        guard let configuration = appState.configuration else {
            subtitleSourcesErrorMessage = "Configure a valid API base URL before continuing."
            return false
        }
        let trimmedPath = path.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmedPath.isEmpty else {
            subtitleSourcesErrorMessage = "Select a server subtitle before deleting it."
            return false
        }

        isDeletingSubtitleSource = true
        subtitleSourcesErrorMessage = nil
        defer { isDeletingSubtitleSource = false }

        do {
            let client = APIClient(configuration: configuration)
            _ = try await client.deleteSubtitleSource(subtitlePath: trimmedPath)
            if let currentSources = subtitleSources {
                subtitleSources = SubtitleSourceListResponse(
                    sources: currentSources.sources.filter { $0.path != trimmedPath }
                )
            }
            return true
        } catch {
            subtitleSourcesErrorMessage = error.localizedDescription
            return false
        }
    }

    func loadYoutubeLibrary(
        using appState: AppState,
        cacheKey: String,
        baseDir: String? = nil,
        force: Bool = false
    ) async -> YoutubeNasLibraryResponse? {
        guard let configuration = appState.configuration else {
            return nil
        }
        if !force, loadedYoutubeLibraryCacheKey == cacheKey, let youtubeLibrary {
            return youtubeLibrary
        }

        isLoadingYoutubeLibrary = true
        youtubeLibraryErrorMessage = nil
        defer { isLoadingYoutubeLibrary = false }

        do {
            let client = APIClient(configuration: configuration)
            let response = try await client.fetchYoutubeLibrary(baseDir: baseDir)
            youtubeLibrary = response
            loadedYoutubeLibraryCacheKey = cacheKey
            return response
        } catch {
            youtubeLibrary = nil
            youtubeLibraryErrorMessage = error.localizedDescription
            return nil
        }
    }

    func resetYoutubeSubtitleExtractionState() {
        youtubeInlineSubtitleStreams = []
        youtubeSubtitleExtractionMessage = nil
        youtubeSubtitleExtractionErrorMessage = nil
    }

    func loadYoutubeSubtitleStreams(
        videoPath: String,
        using appState: AppState
    ) async -> YoutubeInlineSubtitleListResponse? {
        guard let configuration = appState.configuration else {
            return nil
        }
        let trimmedPath = videoPath.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmedPath.isEmpty else {
            youtubeInlineSubtitleStreams = []
            youtubeSubtitleExtractionErrorMessage = "Select a NAS video before inspecting embedded subtitles."
            return nil
        }

        isLoadingYoutubeSubtitleStreams = true
        youtubeSubtitleExtractionMessage = nil
        youtubeSubtitleExtractionErrorMessage = nil
        defer { isLoadingYoutubeSubtitleStreams = false }

        do {
            let client = APIClient(configuration: configuration)
            let response = try await client.fetchYoutubeSubtitleStreams(videoPath: trimmedPath)
            youtubeInlineSubtitleStreams = response.streams
            if AppleBookCreatePresentation.extractableYoutubeInlineSubtitleStreams(from: response.streams).isEmpty {
                youtubeSubtitleExtractionErrorMessage = (
                    "No text-based subtitle streams were found. "
                    + "Image-based subtitle tracks cannot be extracted automatically."
                )
            }
            return response
        } catch {
            youtubeInlineSubtitleStreams = []
            youtubeSubtitleExtractionErrorMessage = error.localizedDescription
            return nil
        }
    }

    func extractYoutubeSubtitles(
        videoPath: String,
        languages: [String],
        using appState: AppState
    ) async -> YoutubeSubtitleExtractionResponse? {
        guard let configuration = appState.configuration else {
            return nil
        }
        let trimmedPath = videoPath.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmedPath.isEmpty else {
            youtubeSubtitleExtractionErrorMessage = "Select a NAS video before extracting embedded subtitles."
            return nil
        }

        isExtractingYoutubeSubtitles = true
        youtubeSubtitleExtractionMessage = nil
        youtubeSubtitleExtractionErrorMessage = nil
        defer { isExtractingYoutubeSubtitles = false }

        do {
            let client = APIClient(configuration: configuration)
            let response = try await client.extractYoutubeSubtitles(
                YoutubeSubtitleExtractionRequestPayload(
                    videoPath: trimmedPath,
                    languages: languages.isEmpty ? nil : languages
                )
            )
            youtubeSubtitleExtractionMessage = AppleBookCreatePresentation.youtubeSubtitleExtractionStatus(
                extractedCount: response.extracted.count,
                videoFilename: URL(fileURLWithPath: trimmedPath).lastPathComponent
            )
            youtubeInlineSubtitleStreams = []
            return response
        } catch {
            youtubeSubtitleExtractionErrorMessage = error.localizedDescription
            return nil
        }
    }

    func loadNarrateChapters(inputFile: String, using appState: AppState) async {
        let trimmedInput = inputFile.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmedInput.isEmpty else {
            narrateChapterOptions = []
            narrateChaptersErrorMessage = "Enter a server EPUB path first."
            return
        }
        if Self.shouldSkipNarrateChapterLookup(for: trimmedInput) {
            narrateChapterOptions = []
            narrateChaptersErrorMessage = "Generated sources use manual sentence ranges; chapter loading is skipped."
            return
        }
        guard let configuration = appState.configuration else {
            narrateChapterOptions = []
            narrateChaptersErrorMessage = "API configuration is unavailable."
            return
        }

        isLoadingNarrateChapters = true
        narrateChaptersErrorMessage = nil
        defer { isLoadingNarrateChapters = false }

        do {
            let client = APIClient(configuration: configuration)
            let response = try await client.fetchBookContentIndex(inputFile: trimmedInput)
            let chapters = AppleBookCreatePresentation.contentIndexChapters(from: response.contentIndex)
            narrateChapterOptions = chapters
            if chapters.isEmpty {
                narrateChaptersErrorMessage = "No chapter index was found for this EPUB."
            }
        } catch {
            narrateChapterOptions = []
            narrateChaptersErrorMessage = error.localizedDescription
        }
    }

    func clearNarrateChapters() {
        narrateChapterOptions = []
        narrateChaptersErrorMessage = nil
    }

    private func mergePipelineEbook(_ uploaded: PipelineFileEntry) {
        guard let currentFiles = pipelineFiles else {
            pipelineFiles = PipelineFileBrowserResponse(
                ebooks: [uploaded],
                outputs: [],
                booksRoot: "",
                outputRoot: ""
            )
            return
        }
        var ebooks = currentFiles.ebooks.filter { $0.path != uploaded.path }
        ebooks.insert(uploaded, at: 0)
        pipelineFiles = PipelineFileBrowserResponse(
            ebooks: ebooks,
            outputs: currentFiles.outputs,
            booksRoot: currentFiles.booksRoot,
            outputRoot: currentFiles.outputRoot
        )
    }

    private static func shouldSkipNarrateChapterLookup(for inputFile: String) -> Bool {
        let normalized = inputFile
            .trimmingCharacters(in: .whitespacesAndNewlines)
            .replacingOccurrences(of: "\\", with: "/")
            .lowercased()
        return normalized.hasPrefix("runtime/generated/")
            || normalized.contains("/runtime/generated/")
            || normalized.hasPrefix("generated/source")
            || normalized.contains("/generated/source")
    }
}
