import SwiftUI

@MainActor
final class AppleBookCreateViewModel: ObservableObject {
    @Published var isSubmitting = false
    @Published private(set) var isLoadingOptions = false
    @Published private(set) var isLoadingIntakeStatus = false
    @Published private(set) var isLoadingPipelineFiles = false
    @Published private(set) var creationOptions: BookCreationOptionsResponse?
    @Published private(set) var intakeStatus: PipelineIntakeStatusResponse?
    @Published private(set) var pipelineFiles: PipelineFileBrowserResponse?
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
    @Published private(set) var subtitleLlmModels: [String] = []
    @Published private(set) var narrateChapterOptions: [AppleCreateChapterOption] = []
    @Published private(set) var isLoadingNarrateChapters = false
    @Published private(set) var isLoadingSubtitleSources = false
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
    @Published private(set) var narrateChaptersErrorMessage: String?
    @Published private(set) var pipelineFilesErrorMessage: String?
    @Published private(set) var subtitleSourcesErrorMessage: String?
    @Published var subtitleMetadataMessage: String?
    @Published var subtitleMetadataErrorMessage: String?
    @Published private(set) var youtubeLibraryErrorMessage: String?
    @Published private(set) var youtubeSubtitleExtractionMessage: String?
    @Published private(set) var youtubeSubtitleExtractionErrorMessage: String?
    @Published var youtubeMetadataMessage: String?
    @Published var youtubeMetadataErrorMessage: String?
    @Published private(set) var voiceInventoryErrorMessage: String?
    @Published private(set) var voicePreviewStates: [String: AppleVoicePreviewState] = [:]
    @Published private(set) var voicePreviewErrorMessages: [String: String] = [:]
    @Published private(set) var optionsErrorMessage: String?
    @Published var errorMessage: String?
    @Published var submittedJobId: String?
    private var loadedOptionsCacheKey: String?
    private var loadedIntakeStatusCacheKey: String?
    private var loadedPipelineFilesCacheKey: String?
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
                voicePreviewSpeaker.playAudio(data)
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
