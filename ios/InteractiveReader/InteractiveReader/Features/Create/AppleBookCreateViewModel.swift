import SwiftUI

@MainActor
final class AppleBookCreateViewModel: ObservableObject {
    @Published private(set) var isSubmitting = false
    @Published private(set) var isLoadingOptions = false
    @Published private(set) var isLoadingIntakeStatus = false
    @Published private(set) var isLoadingPipelineFiles = false
    @Published private(set) var creationOptions: BookCreationOptionsResponse?
    @Published private(set) var intakeStatus: PipelineIntakeStatusResponse?
    @Published private(set) var pipelineFiles: PipelineFileBrowserResponse?
    @Published private(set) var subtitleSources: SubtitleSourceListResponse?
    @Published private(set) var subtitleTvMetadataPreview: SubtitleTvMetadataPreviewResponse?
    @Published private(set) var subtitleMediaMetadataDraft: [String: JSONValue]?
    @Published var subtitleMediaMetadataJSONText = ""
    @Published private(set) var subtitleMediaMetadataJSONErrorMessage: String?
    @Published private(set) var youtubeLibrary: YoutubeNasLibraryResponse?
    @Published private(set) var youtubeInlineSubtitleStreams: [YoutubeInlineSubtitleStream] = []
    @Published private(set) var youtubeTvMetadataPreview: SubtitleTvMetadataPreviewResponse?
    @Published private(set) var youtubeVideoMetadataPreview: YoutubeVideoMetadataPreviewResponse?
    @Published private(set) var youtubeMediaMetadataDraft: [String: JSONValue] = ["source": .string("apple")]
    @Published var youtubeMediaMetadataJSONText = ""
    @Published private(set) var youtubeMediaMetadataJSONErrorMessage: String?
    @Published private(set) var voiceInventory: AppleBookCreateVoiceInventory?
    @Published private(set) var subtitleLlmModels: [String] = []
    @Published private(set) var narrateChapterOptions: [AppleCreateChapterOption] = []
    @Published private(set) var isLoadingNarrateChapters = false
    @Published private(set) var isLoadingSubtitleSources = false
    @Published private(set) var isLoadingSubtitleTvMetadata = false
    @Published private(set) var isLoadingYoutubeLibrary = false
    @Published private(set) var isLoadingYoutubeSubtitleStreams = false
    @Published private(set) var isExtractingYoutubeSubtitles = false
    @Published private(set) var isLoadingYoutubeTvMetadata = false
    @Published private(set) var isLoadingYoutubeVideoMetadata = false
    @Published private(set) var isClearingSubtitleTvMetadataCache = false
    @Published private(set) var isClearingYoutubeTvMetadataCache = false
    @Published private(set) var isClearingYoutubeMetadataCache = false
    @Published private(set) var isLoadingVoiceInventory = false
    @Published private(set) var narrateChaptersErrorMessage: String?
    @Published private(set) var pipelineFilesErrorMessage: String?
    @Published private(set) var subtitleSourcesErrorMessage: String?
    @Published private(set) var subtitleMetadataMessage: String?
    @Published private(set) var subtitleMetadataErrorMessage: String?
    @Published private(set) var youtubeLibraryErrorMessage: String?
    @Published private(set) var youtubeSubtitleExtractionMessage: String?
    @Published private(set) var youtubeSubtitleExtractionErrorMessage: String?
    @Published private(set) var youtubeMetadataMessage: String?
    @Published private(set) var youtubeMetadataErrorMessage: String?
    @Published private(set) var voiceInventoryErrorMessage: String?
    @Published private(set) var voicePreviewStates: [String: AppleVoicePreviewState] = [:]
    @Published private(set) var voicePreviewErrorMessages: [String: String] = [:]
    @Published private(set) var optionsErrorMessage: String?
    @Published var errorMessage: String?
    @Published private(set) var submittedJobId: String?
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

    func lookupSubtitleTvMetadata(
        sourceName: String,
        force: Bool = false,
        using appState: AppState
    ) async {
        guard let configuration = appState.configuration else {
            subtitleMetadataErrorMessage = "API configuration is unavailable."
            return
        }
        let trimmedSourceName = sourceName.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmedSourceName.isEmpty else {
            subtitleMetadataErrorMessage = "Choose a subtitle before loading TV metadata."
            return
        }

        isLoadingSubtitleTvMetadata = true
        subtitleMetadataErrorMessage = nil
        subtitleMetadataMessage = nil
        defer { isLoadingSubtitleTvMetadata = false }

        do {
            let client = APIClient(configuration: configuration)
            let request = SubtitleTvMetadataPreviewLookupRequest(sourceName: trimmedSourceName, force: force)
            let response = try await client.lookupSubtitleTvMetadataPreview(request)
            subtitleTvMetadataPreview = response
            if let mediaMetadata = response.mediaMetadata {
                subtitleMediaMetadataDraft = AppleBookCreatePresentation.normalizedSubtitleMediaMetadata(mediaMetadata)
                syncSubtitleMediaMetadataJSONText()
                subtitleMetadataMessage = "Loaded TV metadata for \(response.sourceName ?? trimmedSourceName)."
            } else {
                subtitleMediaMetadataDraft = nil
                syncSubtitleMediaMetadataJSONText()
                subtitleMetadataMessage = "No TV metadata match for \(response.sourceName ?? trimmedSourceName)."
            }
        } catch {
            subtitleTvMetadataPreview = nil
            subtitleMediaMetadataDraft = nil
            syncSubtitleMediaMetadataJSONText()
            subtitleMetadataErrorMessage = error.localizedDescription
        }
    }

    func clearSubtitleMetadata() {
        subtitleTvMetadataPreview = nil
        subtitleMediaMetadataDraft = nil
        syncSubtitleMediaMetadataJSONText()
        subtitleMetadataMessage = nil
        subtitleMetadataErrorMessage = nil
    }

    func clearSubtitleTvMetadataCache(
        query: String,
        using appState: AppState
    ) async {
        guard let configuration = appState.configuration else {
            subtitleMetadataErrorMessage = "API configuration is unavailable."
            return
        }
        let trimmedQuery = query.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmedQuery.isEmpty else {
            subtitleMetadataErrorMessage = "Enter a lookup filename before clearing the cache."
            return
        }

        isClearingSubtitleTvMetadataCache = true
        subtitleMetadataErrorMessage = nil
        subtitleMetadataMessage = nil
        defer { isClearingSubtitleTvMetadataCache = false }

        do {
            let client = APIClient(configuration: configuration)
            let response = try await client.clearSubtitleTvMetadataCache(query: trimmedQuery)
            subtitleMetadataMessage = Self.metadataCacheClearMessage(
                cleared: response.cleared,
                kind: "TV",
                query: trimmedQuery
            )
        } catch {
            subtitleMetadataErrorMessage = error.localizedDescription
        }
    }

    func updateSubtitleMediaMetadata(section: String?, key: String, value: String) {
        let trimmedValue = value.trimmingCharacters(in: .whitespacesAndNewlines)
        if let section = section?.trimmingCharacters(in: .whitespacesAndNewlines), !section.isEmpty {
            updateSubtitleMetadataSection(section) { sectionDraft in
                if trimmedValue.isEmpty {
                    sectionDraft.removeValue(forKey: key)
                } else {
                    sectionDraft[key] = .string(trimmedValue)
                }
            }
        } else if trimmedValue.isEmpty {
            subtitleMediaMetadataDraft?.removeValue(forKey: key)
        } else {
            ensureSubtitleMediaMetadataDraft()
            subtitleMediaMetadataDraft?[key] = .string(trimmedValue)
        }
        normalizeSubtitleMetadataAfterEdit()
        syncSubtitleMediaMetadataJSONText()
    }

    func updateSubtitleMediaMetadataNumber(section: String, key: String, value: String) {
        let trimmedValue = value.trimmingCharacters(in: .whitespacesAndNewlines)
        updateSubtitleMetadataSection(section) { sectionDraft in
            guard !trimmedValue.isEmpty else {
                sectionDraft.removeValue(forKey: key)
                return
            }
            guard let parsed = Double(trimmedValue), parsed.isFinite, parsed > 0 else {
                return
            }
            sectionDraft[key] = .number(floor(parsed))
        }
        normalizeSubtitleMetadataAfterEdit()
        syncSubtitleMediaMetadataJSONText()
    }

    func updateSubtitleMediaMetadataNestedText(
        section: String,
        nestedKey: String,
        key: String,
        value: String
    ) {
        updateSubtitleMetadataSection(section) { sectionDraft in
            Self.updateNestedText(in: &sectionDraft, nestedKey: nestedKey, key: key, value: value)
        }
        normalizeSubtitleMetadataAfterEdit()
        syncSubtitleMediaMetadataJSONText()
    }

    func syncSubtitleMediaMetadataJSONText() {
        subtitleMediaMetadataJSONText = Self.prettyMetadataJSONString(from: subtitleMediaMetadataDraft)
        subtitleMediaMetadataJSONErrorMessage = nil
    }

    func applySubtitleMediaMetadataJSONText() {
        let parsed = Self.parseMetadataJSONObject(subtitleMediaMetadataJSONText)
        if let error = parsed.error {
            subtitleMediaMetadataJSONErrorMessage = error
            return
        }
        subtitleMediaMetadataDraft = AppleBookCreatePresentation.normalizedSubtitleMediaMetadata(parsed.metadata)
        syncSubtitleMediaMetadataJSONText()
        subtitleMetadataMessage = "Applied advanced metadata JSON."
        subtitleMetadataErrorMessage = nil
    }

    func subtitleMediaMetadataText(section: String?, key: String) -> String {
        if let section,
           let sectionDraft = subtitleMediaMetadataDraft?[section]?.objectValue {
            return sectionDraft[key]?.stringValue ?? ""
        }
        return subtitleMediaMetadataDraft?[key]?.stringValue ?? ""
    }

    func subtitleMediaMetadataNestedText(section: String, nestedKey: String, keys: [String]) -> String {
        guard let nested = subtitleMediaMetadataDraft?[section]?.objectValue?[nestedKey]?.objectValue else {
            return ""
        }
        for key in keys {
            if let value = nested[key]?.stringValue {
                return value
            }
        }
        return ""
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

    func lookupYoutubeTvMetadata(
        sourceName: String,
        force: Bool = false,
        using appState: AppState
    ) async {
        guard let configuration = appState.configuration else {
            youtubeMetadataErrorMessage = "API configuration is unavailable."
            return
        }
        let trimmedSourceName = sourceName.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmedSourceName.isEmpty else {
            youtubeMetadataErrorMessage = "Choose a subtitle before loading TV metadata."
            return
        }

        isLoadingYoutubeTvMetadata = true
        youtubeMetadataErrorMessage = nil
        youtubeMetadataMessage = nil
        defer { isLoadingYoutubeTvMetadata = false }

        do {
            let client = APIClient(configuration: configuration)
            let request = SubtitleTvMetadataPreviewLookupRequest(sourceName: trimmedSourceName, force: force)
            let response = try await client.lookupSubtitleTvMetadataPreview(request)
            youtubeTvMetadataPreview = response
            if let mediaMetadata = response.mediaMetadata {
                mergeYoutubeTvMetadata(mediaMetadata)
                syncYoutubeMediaMetadataJSONText()
                youtubeMetadataMessage = "Loaded TV metadata for \(response.sourceName ?? trimmedSourceName)."
            } else {
                youtubeMetadataMessage = "No TV metadata match for \(response.sourceName ?? trimmedSourceName)."
            }
        } catch {
            youtubeMetadataErrorMessage = error.localizedDescription
        }
    }

    func lookupYoutubeVideoMetadata(
        sourceName: String,
        force: Bool = false,
        using appState: AppState
    ) async {
        guard let configuration = appState.configuration else {
            youtubeMetadataErrorMessage = "API configuration is unavailable."
            return
        }
        let trimmedSourceName = sourceName.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmedSourceName.isEmpty else {
            youtubeMetadataErrorMessage = "Choose a video before loading YouTube metadata."
            return
        }

        isLoadingYoutubeVideoMetadata = true
        youtubeMetadataErrorMessage = nil
        youtubeMetadataMessage = nil
        defer { isLoadingYoutubeVideoMetadata = false }

        do {
            let client = APIClient(configuration: configuration)
            let request = YoutubeVideoMetadataPreviewLookupRequest(sourceName: trimmedSourceName, force: force)
            let response = try await client.lookupYoutubeMetadataPreview(request)
            youtubeVideoMetadataPreview = response
            if let youtubeMetadata = response.youtubeMetadata {
                updateYoutubeMetadataSection("youtube") { section in
                    for (key, value) in youtubeMetadata {
                        section[key] = value
                    }
                }
                syncYoutubeMediaMetadataJSONText()
                youtubeMetadataMessage = "Loaded YouTube metadata for \(response.sourceName ?? trimmedSourceName)."
            } else {
                youtubeMetadataMessage = "No YouTube metadata match for \(response.sourceName ?? trimmedSourceName)."
            }
        } catch {
            youtubeMetadataErrorMessage = error.localizedDescription
        }
    }

    func resetYoutubeMetadataState() {
        youtubeTvMetadataPreview = nil
        youtubeVideoMetadataPreview = nil
        youtubeMetadataMessage = nil
        youtubeMetadataErrorMessage = nil
        youtubeMediaMetadataDraft = ["source": .string("apple")]
        syncYoutubeMediaMetadataJSONText()
    }

    func clearYoutubeTvMetadataCache(
        query: String,
        using appState: AppState
    ) async {
        guard let configuration = appState.configuration else {
            youtubeMetadataErrorMessage = "API configuration is unavailable."
            return
        }
        let trimmedQuery = query.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmedQuery.isEmpty else {
            youtubeMetadataErrorMessage = "Choose a video before clearing TV metadata cache."
            return
        }

        isClearingYoutubeTvMetadataCache = true
        youtubeMetadataErrorMessage = nil
        youtubeMetadataMessage = nil
        defer { isClearingYoutubeTvMetadataCache = false }

        do {
            let client = APIClient(configuration: configuration)
            let response = try await client.clearSubtitleTvMetadataCache(query: trimmedQuery)
            youtubeMetadataMessage = Self.metadataCacheClearMessage(
                cleared: response.cleared,
                kind: "TV",
                query: trimmedQuery
            )
        } catch {
            youtubeMetadataErrorMessage = error.localizedDescription
        }
    }

    func clearYoutubeVideoMetadataCache(
        query: String,
        using appState: AppState
    ) async {
        guard let configuration = appState.configuration else {
            youtubeMetadataErrorMessage = "API configuration is unavailable."
            return
        }
        let trimmedQuery = query.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmedQuery.isEmpty else {
            youtubeMetadataErrorMessage = "Choose a video before clearing YouTube metadata cache."
            return
        }

        isClearingYoutubeMetadataCache = true
        youtubeMetadataErrorMessage = nil
        youtubeMetadataMessage = nil
        defer { isClearingYoutubeMetadataCache = false }

        do {
            let client = APIClient(configuration: configuration)
            let response = try await client.clearYoutubeMetadataCache(query: trimmedQuery)
            youtubeMetadataMessage = Self.metadataCacheClearMessage(
                cleared: response.cleared,
                kind: "YouTube",
                query: trimmedQuery
            )
        } catch {
            youtubeMetadataErrorMessage = error.localizedDescription
        }
    }

    func updateYoutubeMediaMetadata(section: String?, key: String, value: String) {
        let trimmedValue = value.trimmingCharacters(in: .whitespacesAndNewlines)
        if let section = section?.trimmingCharacters(in: .whitespacesAndNewlines), !section.isEmpty {
            updateYoutubeMetadataSection(section) { sectionDraft in
                if trimmedValue.isEmpty {
                    sectionDraft.removeValue(forKey: key)
                } else {
                    sectionDraft[key] = .string(trimmedValue)
                }
            }
        } else if trimmedValue.isEmpty {
            youtubeMediaMetadataDraft.removeValue(forKey: key)
        } else {
            youtubeMediaMetadataDraft[key] = .string(trimmedValue)
        }
        youtubeMediaMetadataDraft["source"] = .string("apple")
        syncYoutubeMediaMetadataJSONText()
    }

    func updateYoutubeMediaMetadataNumber(section: String, key: String, value: String) {
        let trimmedValue = value.trimmingCharacters(in: .whitespacesAndNewlines)
        updateYoutubeMetadataSection(section) { sectionDraft in
            guard !trimmedValue.isEmpty else {
                sectionDraft.removeValue(forKey: key)
                return
            }
            guard let parsed = Double(trimmedValue), parsed.isFinite, parsed > 0 else {
                return
            }
            sectionDraft[key] = .number(floor(parsed))
        }
        youtubeMediaMetadataDraft["source"] = .string("apple")
        syncYoutubeMediaMetadataJSONText()
    }

    func updateYoutubeMediaMetadataNestedText(
        section: String,
        nestedKey: String,
        key: String,
        value: String
    ) {
        updateYoutubeMetadataSection(section) { sectionDraft in
            Self.updateNestedText(in: &sectionDraft, nestedKey: nestedKey, key: key, value: value)
        }
        youtubeMediaMetadataDraft["source"] = .string("apple")
        syncYoutubeMediaMetadataJSONText()
    }

    func syncYoutubeMediaMetadataJSONText() {
        youtubeMediaMetadataJSONText = Self.prettyMetadataJSONString(from: youtubeMediaMetadataDraft)
        youtubeMediaMetadataJSONErrorMessage = nil
    }

    func applyYoutubeMediaMetadataJSONText() {
        let parsed = Self.parseMetadataJSONObject(youtubeMediaMetadataJSONText)
        if let error = parsed.error {
            youtubeMediaMetadataJSONErrorMessage = error
            return
        }
        youtubeMediaMetadataDraft = AppleBookCreatePresentation.normalizedYoutubeMediaMetadata(parsed.metadata ?? [:])
        syncYoutubeMediaMetadataJSONText()
        youtubeMetadataMessage = "Applied advanced metadata JSON."
        youtubeMetadataErrorMessage = nil
    }

    func youtubeMediaMetadataText(section: String?, key: String) -> String {
        if let section,
           let sectionDraft = youtubeMediaMetadataDraft[section]?.objectValue {
            return sectionDraft[key]?.stringValue ?? ""
        }
        return youtubeMediaMetadataDraft[key]?.stringValue ?? ""
    }

    func youtubeMediaMetadataNestedText(section: String, nestedKey: String, keys: [String]) -> String {
        guard let nested = youtubeMediaMetadataDraft[section]?.objectValue?[nestedKey]?.objectValue else {
            return ""
        }
        for key in keys {
            if let value = nested[key]?.stringValue {
                return value
            }
        }
        return ""
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

    func submitGeneratedBook(_ draft: AppleBookCreateDraft, using appState: AppState) async -> String? {
        await submitJob(using: appState) { client in
            let response = try await client.submitBookGenerationJob(
                AppleBookCreatePayloadFactory.makeSubmission(from: draft)
            )
            return response.jobId
        }
    }

    func submitNarrateEbook(
        _ draft: AppleNarrateEbookDraft,
        localFileURL: URL? = nil,
        localFilename: String? = nil,
        using appState: AppState
    ) async -> String? {
        await submitJob(using: appState) { client in
            let effectiveDraft: AppleNarrateEbookDraft
            if let localFileURL {
                let upload = try await client.uploadPipelineEbook(fileURL: localFileURL, filename: localFilename)
                effectiveDraft = draft.replacingInputFile(upload.path)
            } else {
                effectiveDraft = draft
            }
            let response = try await client.submitPipeline(
                AppleBookCreatePayloadFactory.makePipelineSubmission(from: effectiveDraft)
            )
            return response.jobId
        }
    }

    func submitSubtitleJob(
        _ draft: AppleSubtitleJobDraft,
        localFileURL: URL? = nil,
        localFilename: String? = nil,
        using appState: AppState
    ) async -> String? {
        await submitJob(using: appState) { client in
            let response = try await client.submitSubtitleJob(
                AppleBookCreatePayloadFactory.makeSubtitlePayload(from: draft),
                fileURL: localFileURL,
                filename: localFilename
            )
            return response.jobId
        }
    }

    func submitYoutubeDub(
        _ draft: AppleYoutubeDubDraft,
        using appState: AppState
    ) async -> String? {
        await submitJob(using: appState) { client in
            let response = try await client.submitYoutubeDub(
                AppleBookCreatePayloadFactory.makeYoutubeDubPayload(from: draft)
            )
            return response.jobId
        }
    }

    private func submitJob(
        using appState: AppState,
        operation: (APIClient) async throws -> String
    ) async -> String? {
        guard let configuration = appState.configuration else {
            errorMessage = "API configuration is unavailable."
            return nil
        }

        isSubmitting = true
        errorMessage = nil
        submittedJobId = nil
        defer { isSubmitting = false }

        do {
            let client = APIClient(configuration: configuration)
            let jobId = try await operation(client)
            submittedJobId = jobId
            return jobId
        } catch {
            errorMessage = error.localizedDescription
            return nil
        }
    }

    private static func prettyMetadataJSONString(from metadata: [String: JSONValue]?) -> String {
        guard let metadata, !metadata.isEmpty else {
            return ""
        }
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys, .withoutEscapingSlashes]
        guard let data = try? encoder.encode(metadata) else {
            return ""
        }
        return String(data: data, encoding: .utf8) ?? ""
    }

    private static func parseMetadataJSONObject(_ value: String) -> (metadata: [String: JSONValue]?, error: String?) {
        let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else {
            return (nil, nil)
        }
        guard let data = trimmed.data(using: .utf8) else {
            return (nil, "Metadata JSON must be valid UTF-8 text.")
        }
        do {
            return (try JSONDecoder().decode([String: JSONValue].self, from: data), nil)
        } catch {
            return (nil, "Enter a valid JSON object.")
        }
    }

    private static func metadataCacheClearMessage(cleared: Int, kind: String, query: String) -> String {
        let entryLabel = cleared == 1 ? "entry" : "entries"
        return "Cleared \(cleared) cached \(kind) metadata \(entryLabel) for \(query)."
    }

    private static func updateNestedText(
        in sectionDraft: inout [String: JSONValue],
        nestedKey: String,
        key: String,
        value: String
    ) {
        var nested = sectionDraft[nestedKey]?.objectValue ?? [:]
        let trimmedValue = value.trimmingCharacters(in: .whitespacesAndNewlines)
        if trimmedValue.isEmpty {
            nested.removeValue(forKey: key)
        } else {
            nested[key] = .string(trimmedValue)
        }
        if nested.isEmpty {
            sectionDraft.removeValue(forKey: nestedKey)
        } else {
            sectionDraft[nestedKey] = .object(nested)
        }
    }

    private func ensureSubtitleMediaMetadataDraft() {
        if subtitleMediaMetadataDraft == nil {
            subtitleMediaMetadataDraft = [:]
        }
    }

    private func normalizeSubtitleMetadataAfterEdit() {
        guard let draft = subtitleMediaMetadataDraft else {
            return
        }
        subtitleMediaMetadataDraft = AppleBookCreatePresentation.normalizedSubtitleMediaMetadata(draft)
    }

    private func updateSubtitleMetadataSection(
        _ section: String,
        mutate: (inout [String: JSONValue]) -> Void
    ) {
        ensureSubtitleMediaMetadataDraft()
        var sectionDraft = subtitleMediaMetadataDraft?[section]?.objectValue ?? [:]
        mutate(&sectionDraft)
        if sectionDraft.isEmpty {
            subtitleMediaMetadataDraft?.removeValue(forKey: section)
        } else {
            subtitleMediaMetadataDraft?[section] = .object(sectionDraft)
        }
    }

    private func mergeYoutubeTvMetadata(_ mediaMetadata: [String: JSONValue]) {
        let preservedYoutube = youtubeMediaMetadataDraft["youtube"]
        youtubeMediaMetadataDraft = mediaMetadata
        if preservedYoutube != nil, youtubeMediaMetadataDraft["youtube"] == nil {
            youtubeMediaMetadataDraft["youtube"] = preservedYoutube
        }
        youtubeMediaMetadataDraft["source"] = .string("apple")
    }

    private func updateYoutubeMetadataSection(
        _ section: String,
        mutate: (inout [String: JSONValue]) -> Void
    ) {
        var sectionDraft = youtubeMediaMetadataDraft[section]?.objectValue ?? [:]
        mutate(&sectionDraft)
        if sectionDraft.isEmpty {
            youtubeMediaMetadataDraft.removeValue(forKey: section)
        } else {
            youtubeMediaMetadataDraft[section] = .object(sectionDraft)
        }
        youtubeMediaMetadataDraft["source"] = .string("apple")
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
