import SwiftUI

@MainActor
final class AppleBookCreateViewModel: ObservableObject {
    @Published var isSubmitting = false
    @Published private(set) var isLoadingOptions = false
    @Published private(set) var isLoadingIntakeStatus = false
    @Published var isLoadingPipelineFiles = false
    @Published var isUploadingPipelineEbook = false
    @Published var isLoadingCreationTemplates = false
    @Published var isSavingCreationTemplate = false
    @Published var isDeletingCreationTemplate = false
    @Published var isDeletingPipelineEbook = false
    @Published private(set) var creationOptions: BookCreationOptionsResponse?
    @Published private(set) var intakeStatus: PipelineIntakeStatusResponse?
    @Published var pipelineFiles: PipelineFileBrowserResponse?
    @Published var acquisitionProviders: [AcquisitionProviderEntry] = []
    @Published var acquisitionDefaultProviderIds: [String: [String]] = [:]
    @Published var ebookAcquisitionDiscovery: AcquisitionDiscoveryResponse?
    @Published var youtubeAcquisitionDiscovery: AcquisitionDiscoveryResponse?
    @Published var downloadStationJob: AcquisitionJobStatusResponse?
    @Published var creationTemplates: [CreationTemplateEntry] = []
    @Published var subtitleSources: SubtitleSourceListResponse?
    @Published var subtitleTvMetadataPreview: SubtitleTvMetadataPreviewResponse?
    @Published var subtitleMediaMetadataDraft: [String: JSONValue]?
    @Published var subtitleMediaMetadataJSONText = ""
    @Published var subtitleMediaMetadataJSONErrorMessage: String?
    @Published var youtubeLibrary: YoutubeNasLibraryResponse?
    @Published var youtubeInlineSubtitleStreams: [YoutubeInlineSubtitleStream] = []
    @Published var youtubeTvMetadataPreview: SubtitleTvMetadataPreviewResponse?
    @Published var youtubeVideoMetadataPreview: YoutubeVideoMetadataPreviewResponse?
    @Published var youtubeMediaMetadataDraft: [String: JSONValue] = ["source": .string("apple")]
    @Published var youtubeMediaMetadataJSONText = ""
    @Published var youtubeMediaMetadataJSONErrorMessage: String?
    @Published private(set) var voiceInventory: AppleBookCreateVoiceInventory?
    @Published private(set) var imageNodeAvailability: ImageNodeAvailabilityResponse?
    @Published private(set) var subtitleLlmModels: [String] = []
    @Published var narrateChapterOptions: [AppleCreateChapterOption] = []
    @Published var isLoadingEbookAcquisitionDiscovery = false
    @Published var isLoadingYoutubeAcquisitionDiscovery = false
    @Published var isAcquiringEbookDiscoveryCandidate = false
    @Published var isPreparingYoutubeAcquisitionCandidate = false
    @Published var isSubmittingDownloadStation = false
    @Published var isPollingDownloadStation = false
    @Published var isLoadingNarrateChapters = false
    @Published var isLoadingSubtitleSources = false
    @Published var isDeletingSubtitleSource = false
    @Published var isLoadingSubtitleTvMetadata = false
    @Published var isLoadingYoutubeLibrary = false
    @Published var isLoadingYoutubeSubtitleStreams = false
    @Published var isExtractingYoutubeSubtitles = false
    @Published var isLoadingYoutubeTvMetadata = false
    @Published var isLoadingYoutubeVideoMetadata = false
    @Published var isClearingSubtitleTvMetadataCache = false
    @Published var isClearingYoutubeTvMetadataCache = false
    @Published var isClearingYoutubeMetadataCache = false
    @Published private(set) var isLoadingVoiceInventory = false
    @Published private(set) var isCheckingImageNodes = false
    @Published var narrateChaptersErrorMessage: String?
    @Published var pipelineFilesErrorMessage: String?
    @Published var acquisitionProvidersErrorMessage: String?
    @Published var ebookAcquisitionDiscoveryErrorMessage: String?
    @Published var youtubeAcquisitionDiscoveryErrorMessage: String?
    @Published var downloadStationMessage: String?
    @Published var downloadStationErrorMessage: String?
    @Published var creationTemplatesErrorMessage: String?
    @Published var subtitleSourcesErrorMessage: String?
    @Published var creationTemplateMessage: String?
    @Published var subtitleMetadataMessage: String?
    @Published var subtitleMetadataErrorMessage: String?
    @Published var youtubeLibraryErrorMessage: String?
    @Published var youtubeSubtitleExtractionMessage: String?
    @Published var youtubeSubtitleExtractionErrorMessage: String?
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
    private var intakeStatusRequestSequence = 0
    var creationTemplatesRequestSequence = 0
    var loadedPipelineFilesCacheKey: String?
    var loadedAcquisitionProvidersCacheKey: String?
    var loadedEbookAcquisitionDiscoveryCacheKey: String?
    var ebookAcquisitionDiscoveryRequestSequence = 0
    var loadedYoutubeAcquisitionDiscoveryCacheKey: String?
    var youtubeAcquisitionDiscoveryRequestSequence = 0
    var loadedCreationTemplatesCacheKey: String?
    var loadedSubtitleSourcesCacheKey: String?
    var loadedYoutubeLibraryCacheKey: String?
    var youtubeSubtitleStreamsRequestSequence = 0
    var narrateChaptersRequestSequence = 0
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

        intakeStatusRequestSequence += 1
        let requestSequence = intakeStatusRequestSequence
        isLoadingIntakeStatus = true
        defer {
            if requestSequence == intakeStatusRequestSequence {
                isLoadingIntakeStatus = false
            }
        }

        do {
            let client = APIClient(configuration: configuration)
            let status = try await client.fetchPipelineIntakeStatus()
            guard requestSequence == intakeStatusRequestSequence else { return }
            intakeStatus = status
            loadedIntakeStatusCacheKey = cacheKey
        } catch {
            guard requestSequence == intakeStatusRequestSequence else { return }
            intakeStatus = nil
        }
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
