import SwiftUI

@MainActor
final class AppleBookCreateViewModel: ObservableObject {
    @Published var isSubmitting = false
    @Published private(set) var isLoadingOptions = false
    @Published private(set) var isLoadingIntakeStatus = false
    @Published private(set) var isLoadingPipelineFiles = false
    @Published private(set) var isUploadingPipelineEbook = false
    @Published private(set) var isLoadingCreationTemplates = false
    @Published private(set) var isSavingCreationTemplate = false
    @Published private(set) var isDeletingCreationTemplate = false
    @Published private(set) var isDeletingPipelineEbook = false
    @Published private(set) var creationOptions: BookCreationOptionsResponse?
    @Published private(set) var intakeStatus: PipelineIntakeStatusResponse?
    @Published private(set) var pipelineFiles: PipelineFileBrowserResponse?
    @Published private(set) var acquisitionProviders: [AcquisitionProviderEntry] = []
    @Published private(set) var acquisitionDefaultProviderIds: [String: [String]] = [:]
    @Published private(set) var ebookAcquisitionDiscovery: AcquisitionDiscoveryResponse?
    @Published private(set) var youtubeAcquisitionDiscovery: AcquisitionDiscoveryResponse?
    @Published private(set) var downloadStationJob: AcquisitionJobStatusResponse?
    @Published private(set) var creationTemplates: [CreationTemplateEntry] = []
    @Published private(set) var subtitleSources: SubtitleSourceListResponse?
    @Published var subtitleTvMetadataPreview: SubtitleTvMetadataPreviewResponse?
    @Published var subtitleMediaMetadataDraft: [String: JSONValue]?
    @Published var subtitleMediaMetadataJSONText = ""
    @Published var subtitleMediaMetadataJSONErrorMessage: String?
    @Published private(set) var youtubeLibrary: YoutubeNasLibraryResponse?
    @Published private(set) var youtubeInlineSubtitleStreams: [YoutubeInlineSubtitleStream] = []
    @Published var youtubeTvMetadataPreview: SubtitleTvMetadataPreviewResponse?
    @Published var youtubeVideoMetadataPreview: YoutubeVideoMetadataPreviewResponse?
    @Published var youtubeMediaMetadataDraft: [String: JSONValue] = ["source": .string("apple")]
    @Published var youtubeMediaMetadataJSONText = ""
    @Published var youtubeMediaMetadataJSONErrorMessage: String?
    @Published private(set) var voiceInventory: AppleBookCreateVoiceInventory?
    @Published private(set) var imageNodeAvailability: ImageNodeAvailabilityResponse?
    @Published private(set) var subtitleLlmModels: [String] = []
    @Published private(set) var narrateChapterOptions: [AppleCreateChapterOption] = []
    @Published private(set) var isLoadingEbookAcquisitionDiscovery = false
    @Published private(set) var isLoadingYoutubeAcquisitionDiscovery = false
    @Published private(set) var isAcquiringEbookDiscoveryCandidate = false
    @Published private(set) var isSubmittingDownloadStation = false
    @Published private(set) var isPollingDownloadStation = false
    @Published private(set) var isLoadingNarrateChapters = false
    @Published private(set) var isLoadingSubtitleSources = false
    @Published private(set) var isDeletingSubtitleSource = false
    @Published var isLoadingSubtitleTvMetadata = false
    @Published private(set) var isLoadingYoutubeLibrary = false
    @Published private(set) var isLoadingYoutubeSubtitleStreams = false
    @Published private(set) var isExtractingYoutubeSubtitles = false
    @Published var isLoadingYoutubeTvMetadata = false
    @Published var isLoadingYoutubeVideoMetadata = false
    @Published var isClearingSubtitleTvMetadataCache = false
    @Published var isClearingYoutubeTvMetadataCache = false
    @Published var isClearingYoutubeMetadataCache = false
    @Published private(set) var isLoadingVoiceInventory = false
    @Published private(set) var isCheckingImageNodes = false
    @Published private(set) var narrateChaptersErrorMessage: String?
    @Published private(set) var pipelineFilesErrorMessage: String?
    @Published private(set) var acquisitionProvidersErrorMessage: String?
    @Published private(set) var ebookAcquisitionDiscoveryErrorMessage: String?
    @Published private(set) var youtubeAcquisitionDiscoveryErrorMessage: String?
    @Published private(set) var downloadStationMessage: String?
    @Published private(set) var downloadStationErrorMessage: String?
    @Published private(set) var creationTemplatesErrorMessage: String?
    @Published private(set) var subtitleSourcesErrorMessage: String?
    @Published var creationTemplateMessage: String?
    @Published var subtitleMetadataMessage: String?
    @Published var subtitleMetadataErrorMessage: String?
    @Published private(set) var youtubeLibraryErrorMessage: String?
    @Published private(set) var youtubeSubtitleExtractionMessage: String?
    @Published private(set) var youtubeSubtitleExtractionErrorMessage: String?
    @Published var youtubeMetadataMessage: String?
    @Published var youtubeMetadataErrorMessage: String?
    @Published private(set) var voiceInventoryErrorMessage: String?
    @Published private(set) var imageNodeAvailabilityMessage: String?
    @Published private(set) var imageNodeAvailabilityErrorMessage: String?
    @Published private(set) var voicePreviewStates: [String: AppleVoicePreviewState] = [:]
    @Published private(set) var voicePreviewErrorMessages: [String: String] = [:]
    @Published private(set) var optionsErrorMessage: String?
    @Published var errorMessage: String?
    @Published var submittedJobId: String?
    private var loadedOptionsCacheKey: String?
    private var loadedIntakeStatusCacheKey: String?
    private var loadedPipelineFilesCacheKey: String?
    private var loadedAcquisitionProvidersCacheKey: String?
    private var loadedEbookAcquisitionDiscoveryCacheKey: String?
    private var loadedYoutubeAcquisitionDiscoveryCacheKey: String?
    private var loadedCreationTemplatesCacheKey: String?
    private var loadedSubtitleSourcesCacheKey: String?
    private var loadedYoutubeLibraryCacheKey: String?
    private var loadedVoiceInventoryCacheKey: String?
    private var loadedSubtitleModelsCacheKey: String?
    private let voicePreviewSpeaker = PronunciationSpeaker()
    private var voicePreviewTask: Task<Void, Never>?

    init() {
        syncYoutubeMediaMetadataJSONText()
    }

    func loadCreationOptions(
        using appState: AppState,
        cacheKey: String,
        force: Bool = false
    ) async -> BookCreationOptionsResponse? {
        guard let configuration = appState.configuration else {
            return nil
        }
        if !force, loadedOptionsCacheKey == cacheKey, let creationOptions {
            return creationOptions
        }

        isLoadingOptions = true
        optionsErrorMessage = nil
        defer { isLoadingOptions = false }

        do {
            let client = APIClient(configuration: configuration)
            let options = try await client.fetchBookCreationOptions()
            creationOptions = options
            loadedOptionsCacheKey = cacheKey
            return options
        } catch APIClientError.httpError(let statusCode, _) where statusCode == 404 {
            optionsErrorMessage = Self.creationOptionsUnavailableMessage
            return nil
        } catch {
            optionsErrorMessage = error.localizedDescription
            return nil
        }
    }

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

    static let creationOptionsUnavailableMessage = (
        "This backend does not advertise Apple Create defaults yet. "
        + "Using built-in defaults; deploy the latest ebook-tools API before running Create readiness checks."
    )

    func loadSubtitleModels(
        using appState: AppState,
        cacheKey: String,
        force: Bool = false
    ) async {
        guard let configuration = appState.configuration else {
            return
        }
        if !force, loadedSubtitleModelsCacheKey == cacheKey {
            return
        }

        do {
            let client = APIClient(configuration: configuration)
            let response = try await client.fetchSubtitleLlmModels()
            subtitleLlmModels = response.models
            loadedSubtitleModelsCacheKey = cacheKey
        } catch {
            return
        }
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
        provider: String = "local_epub",
        sourceIds: [String] = [],
        force: Bool = false
    ) async -> AcquisitionDiscoveryResponse? {
        guard let configuration = appState.configuration else {
            return nil
        }
        let normalizedQuery = query?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        let normalizedProvider = provider.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
            ? "local_epub"
            : provider.trimmingCharacters(in: .whitespacesAndNewlines)
        let requestProvider = AppleBookCreatePresentation.isDefaultBookDiscoveryProviderID(normalizedProvider)
            ? nil
            : normalizedProvider
        let normalizedSourceIds = sourceIds
            .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
            .filter { !$0.isEmpty }
        let discoveryCacheKey = "\(cacheKey)::book::\(normalizedProvider)::\(normalizedQuery)::\(normalizedSourceIds.joined(separator: ","))"
        if !force, loadedEbookAcquisitionDiscoveryCacheKey == discoveryCacheKey, let ebookAcquisitionDiscovery {
            return ebookAcquisitionDiscovery
        }

        isLoadingEbookAcquisitionDiscovery = true
        ebookAcquisitionDiscoveryErrorMessage = nil
        defer { isLoadingEbookAcquisitionDiscovery = false }

        do {
            let client = APIClient(configuration: configuration)
            let response = try await client.discoverAcquisitionCandidates(
                mediaKind: "book",
                query: normalizedQuery,
                provider: requestProvider,
                sourceIds: normalizedSourceIds,
                limit: 25
            )
            ebookAcquisitionDiscovery = response
            loadedEbookAcquisitionDiscoveryCacheKey = discoveryCacheKey
            return response
        } catch APIClientError.httpError(let statusCode, _) where statusCode == 404 {
            ebookAcquisitionDiscovery = nil
            ebookAcquisitionDiscoveryErrorMessage = "This backend does not expose source discovery yet."
            return nil
        } catch {
            ebookAcquisitionDiscovery = nil
            ebookAcquisitionDiscoveryErrorMessage = error.localizedDescription
            return nil
        }
    }

    func acquireEbookDiscoveryCandidate(
        using appState: AppState,
        candidate: AcquisitionCandidate
    ) async -> String? {
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
                return prepared.inputFile?.trimmingCharacters(in: .whitespacesAndNewlines).nonEmptyValue
                    ?? prepared.localPath.trimmingCharacters(in: .whitespacesAndNewlines).nonEmptyValue
                    ?? artifact.localPath.trimmingCharacters(in: .whitespacesAndNewlines).nonEmptyValue
            }
            return artifact.localPath.trimmingCharacters(in: .whitespacesAndNewlines).nonEmptyValue
        } catch {
            ebookAcquisitionDiscoveryErrorMessage = error.localizedDescription
            return nil
        }
    }

    func prepareEbookDiscoveryCandidate(
        using appState: AppState,
        candidate: AcquisitionCandidate
    ) async -> String? {
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
            return prepared.inputFile?.trimmingCharacters(in: .whitespacesAndNewlines).nonEmptyValue
                ?? prepared.localPath.trimmingCharacters(in: .whitespacesAndNewlines).nonEmptyValue
                ?? candidate.localPath?.trimmingCharacters(in: .whitespacesAndNewlines).nonEmptyValue
        } catch {
            ebookAcquisitionDiscoveryErrorMessage = error.localizedDescription
            return nil
        }
    }

    func loadVideoDiscovery(
        using appState: AppState,
        cacheKey: String,
        query: String? = nil,
        provider: String = "nas_video",
        force: Bool = false
    ) async -> AcquisitionDiscoveryResponse? {
        guard let configuration = appState.configuration else {
            return nil
        }
        let normalizedQuery = query?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        let requestedProvider = provider.trimmingCharacters(in: .whitespacesAndNewlines)
        let normalizedProvider = requestedProvider.nonEmptyValue ?? "nas_video"
        let requestProvider = AppleBookCreatePresentation.isDefaultVideoDiscoveryProviderID(normalizedProvider)
            ? nil
            : normalizedProvider
        let discoveryCacheKey = "\(cacheKey)::video::\(normalizedProvider)::\(normalizedQuery)"
        if !force, loadedYoutubeAcquisitionDiscoveryCacheKey == discoveryCacheKey, let youtubeAcquisitionDiscovery {
            return youtubeAcquisitionDiscovery
        }

        isLoadingYoutubeAcquisitionDiscovery = true
        youtubeAcquisitionDiscoveryErrorMessage = nil
        defer { isLoadingYoutubeAcquisitionDiscovery = false }

        do {
            let client = APIClient(configuration: configuration)
            let response = try await client.discoverAcquisitionCandidates(
                mediaKind: "video",
                query: normalizedQuery,
                provider: requestProvider,
                limit: 25
            )
            youtubeAcquisitionDiscovery = response
            loadedYoutubeAcquisitionDiscoveryCacheKey = discoveryCacheKey
            return response
        } catch APIClientError.httpError(let statusCode, _) where statusCode == 404 {
            youtubeAcquisitionDiscovery = nil
            youtubeAcquisitionDiscoveryErrorMessage = "This backend does not expose source discovery yet."
            return nil
        } catch {
            youtubeAcquisitionDiscovery = nil
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

    func loadCreationTemplates(
        using appState: AppState,
        cacheKey: String,
        force: Bool = false
    ) async -> [CreationTemplateEntry] {
        guard let configuration = appState.configuration else {
            return []
        }
        if !force, loadedCreationTemplatesCacheKey == cacheKey {
            return creationTemplates
        }

        isLoadingCreationTemplates = true
        creationTemplatesErrorMessage = nil
        defer { isLoadingCreationTemplates = false }

        do {
            let client = APIClient(configuration: configuration)
            let response = try await client.fetchCreationTemplates()
            creationTemplates = response.templates
            loadedCreationTemplatesCacheKey = cacheKey
            return response.templates
        } catch APIClientError.httpError(let statusCode, _) where statusCode == 404 {
            creationTemplates = []
            creationTemplatesErrorMessage = "This backend does not expose saved creation templates yet."
            return []
        } catch {
            creationTemplates = []
            creationTemplatesErrorMessage = error.localizedDescription
            return []
        }
    }

    func deleteCreationTemplate(
        templateID: String,
        using appState: AppState
    ) async -> Bool {
        guard let configuration = appState.configuration else {
            creationTemplatesErrorMessage = "Configure a valid API base URL before deleting saved templates."
            return false
        }
        let trimmedID = templateID.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmedID.isEmpty else {
            creationTemplatesErrorMessage = "Choose a saved template before deleting it."
            return false
        }

        isDeletingCreationTemplate = true
        creationTemplatesErrorMessage = nil
        creationTemplateMessage = nil
        defer { isDeletingCreationTemplate = false }

        do {
            let client = APIClient(configuration: configuration)
            try await client.deleteCreationTemplate(templateId: trimmedID)
            creationTemplates.removeAll { $0.id == trimmedID }
            creationTemplateMessage = "Deleted saved template."
            return true
        } catch {
            creationTemplatesErrorMessage = error.localizedDescription
            return false
        }
    }

    func saveCreationTemplate(
        _ request: CreationTemplateSaveRequest,
        using appState: AppState
    ) async -> CreationTemplateEntry? {
        guard let configuration = appState.configuration else {
            creationTemplatesErrorMessage = "Configure a valid API base URL before saving templates."
            return nil
        }
        guard !request.name.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
            creationTemplatesErrorMessage = "Template name cannot be empty."
            return nil
        }

        isSavingCreationTemplate = true
        creationTemplatesErrorMessage = nil
        creationTemplateMessage = nil
        defer { isSavingCreationTemplate = false }

        do {
            let client = APIClient(configuration: configuration)
            let saved = try await client.saveCreationTemplate(request)
            creationTemplates.removeAll { $0.id == saved.id }
            creationTemplates.insert(saved, at: 0)
            loadedCreationTemplatesCacheKey = nil
            creationTemplateMessage = "Saved template \(saved.displayName)."
            return saved
        } catch {
            creationTemplatesErrorMessage = error.localizedDescription
            return nil
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

    func loadVoiceInventory(
        using appState: AppState,
        cacheKey: String,
        force: Bool = false
    ) async -> AppleBookCreateVoiceInventory? {
        guard let configuration = appState.configuration else {
            return nil
        }
        if !force, loadedVoiceInventoryCacheKey == cacheKey, let voiceInventory {
            return voiceInventory
        }

        isLoadingVoiceInventory = true
        voiceInventoryErrorMessage = nil
        defer { isLoadingVoiceInventory = false }

        do {
            let client = APIClient(configuration: configuration)
            let response = try await client.fetchVoiceInventory()
            voiceInventory = AppleBookCreateVoiceInventory(response)
            loadedVoiceInventoryCacheKey = cacheKey
            return voiceInventory
        } catch {
            voiceInventory = nil
            voiceInventoryErrorMessage = error.localizedDescription
            return nil
        }
    }

    func checkImageNodeAvailability(
        baseURLsText: String,
        using appState: AppState
    ) async -> ImageNodeAvailabilityResponse? {
        let baseURLs = AppleBookCreatePresentation.normalizedImageApiBaseURLs(baseURLsText)
        guard !baseURLs.isEmpty else {
            imageNodeAvailability = nil
            imageNodeAvailabilityMessage = nil
            imageNodeAvailabilityErrorMessage = "Enter at least one image API URL before checking nodes."
            return nil
        }
        guard let configuration = appState.configuration else {
            imageNodeAvailability = nil
            imageNodeAvailabilityMessage = nil
            imageNodeAvailabilityErrorMessage = "API configuration is unavailable."
            return nil
        }

        isCheckingImageNodes = true
        imageNodeAvailabilityMessage = nil
        imageNodeAvailabilityErrorMessage = nil
        defer { isCheckingImageNodes = false }

        do {
            let client = APIClient(configuration: configuration)
            let response = try await client.checkImageNodeAvailability(baseURLs: baseURLs)
            imageNodeAvailability = response
            imageNodeAvailabilityMessage = AppleBookCreatePresentation.imageNodeAvailabilitySummary(response)
            return response
        } catch {
            imageNodeAvailability = nil
            imageNodeAvailabilityMessage = nil
            imageNodeAvailabilityErrorMessage = "Unable to check image nodes. Verify the image API URLs and backend connectivity."
            return nil
        }
    }

    func previewVoice(
        language: String,
        languageLabel: String,
        voice: AppleBookCreateVoiceOption,
        using appState: AppState
    ) {
        let key = AppleBookCreatePresentation.voicePreviewKey(language: language)
        let sample = AppleBookCreatePresentation.sampleSentence(language: language, fallbackLabel: languageLabel)
        let apiLanguage = normalizeLanguageCode(language)

        voicePreviewTask?.cancel()
        voicePreviewSpeaker.stop()
        voicePreviewStates[key] = .loading
        voicePreviewErrorMessages[key] = nil

        voicePreviewTask = Task { @MainActor in
            do {
                guard let configuration = appState.configuration else {
                    voicePreviewSpeaker.speakFallback(sample, language: apiLanguage)
                    voicePreviewStates[key] = .playing
                    try? await Task.sleep(nanoseconds: 5_000_000_000)
                    if !Task.isCancelled {
                        voicePreviewStates[key] = .idle
                    }
                    return
                }
                let client = APIClient(configuration: configuration)
                let data = try await client.synthesizeAudio(
                    text: sample,
                    language: apiLanguage,
                    voice: voice.backendValue
                )
                guard !Task.isCancelled else { return }
                if !voicePreviewSpeaker.playAudio(data) {
                    voicePreviewSpeaker.speakFallback(sample, language: apiLanguage)
                }
                voicePreviewStates[key] = .playing
                try? await Task.sleep(nanoseconds: 5_000_000_000)
                if !Task.isCancelled {
                    voicePreviewStates[key] = .idle
                }
            } catch {
                guard !Task.isCancelled else { return }
                voicePreviewSpeaker.speakFallback(sample, language: apiLanguage)
                voicePreviewStates[key] = .idle
                voicePreviewErrorMessages[key] = error.localizedDescription
            }
        }
    }

    func loadIntakeStatus(
        using appState: AppState,
        cacheKey: String,
        force: Bool = false
    ) async {
        guard let configuration = appState.configuration else {
            return
        }
        if !force, loadedIntakeStatusCacheKey == cacheKey {
            return
        }

        isLoadingIntakeStatus = true
        defer { isLoadingIntakeStatus = false }

        do {
            let client = APIClient(configuration: configuration)
            intakeStatus = try await client.fetchPipelineIntakeStatus()
            loadedIntakeStatusCacheKey = cacheKey
        } catch {
            intakeStatus = nil
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

private extension AppleBookCreateVoiceInventory {
    init(_ response: VoiceInventoryResponse) {
        self.init(
            macos: response.macos.map {
                MacOSVoice(
                    name: $0.name,
                    lang: $0.lang,
                    quality: $0.quality,
                    gender: $0.gender
                )
            },
            gtts: response.gtts.map {
                GTTSLanguage(code: $0.code, name: $0.name)
            },
            piper: response.piper.map {
                PiperVoice(name: $0.name, lang: $0.lang, quality: $0.quality)
            }
        )
    }
}
