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
    @Published private(set) var youtubeLibrary: YoutubeNasLibraryResponse?
    @Published private(set) var youtubeInlineSubtitleStreams: [YoutubeInlineSubtitleStream] = []
    @Published private(set) var voiceInventory: AppleBookCreateVoiceInventory?
    @Published private(set) var subtitleLlmModels: [String] = []
    @Published private(set) var narrateChapterOptions: [AppleCreateChapterOption] = []
    @Published private(set) var isLoadingNarrateChapters = false
    @Published private(set) var isLoadingSubtitleSources = false
    @Published private(set) var isLoadingYoutubeLibrary = false
    @Published private(set) var isLoadingYoutubeSubtitleStreams = false
    @Published private(set) var isExtractingYoutubeSubtitles = false
    @Published private(set) var isLoadingVoiceInventory = false
    @Published private(set) var narrateChaptersErrorMessage: String?
    @Published private(set) var pipelineFilesErrorMessage: String?
    @Published private(set) var subtitleSourcesErrorMessage: String?
    @Published private(set) var youtubeLibraryErrorMessage: String?
    @Published private(set) var youtubeSubtitleExtractionMessage: String?
    @Published private(set) var youtubeSubtitleExtractionErrorMessage: String?
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

    func submitGeneratedBook(_ draft: AppleBookCreateDraft, using appState: AppState) async -> String? {
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
            let response = try await client.submitBookGenerationJob(Self.makeSubmission(from: draft))
            submittedJobId = response.jobId
            return response.jobId
        } catch {
            errorMessage = error.localizedDescription
            return nil
        }
    }

    func submitNarrateEbook(
        _ draft: AppleNarrateEbookDraft,
        localFileURL: URL? = nil,
        localFilename: String? = nil,
        using appState: AppState
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
            let effectiveDraft: AppleNarrateEbookDraft
            if let localFileURL {
                let upload = try await client.uploadPipelineEbook(fileURL: localFileURL, filename: localFilename)
                effectiveDraft = draft.replacingInputFile(upload.path)
            } else {
                effectiveDraft = draft
            }
            let response = try await client.submitPipeline(Self.makePipelineSubmission(from: effectiveDraft))
            submittedJobId = response.jobId
            return response.jobId
        } catch {
            errorMessage = error.localizedDescription
            return nil
        }
    }

    func submitSubtitleJob(
        _ draft: AppleSubtitleJobDraft,
        localFileURL: URL? = nil,
        localFilename: String? = nil,
        using appState: AppState
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
            let response = try await client.submitSubtitleJob(
                Self.makeSubtitlePayload(from: draft),
                fileURL: localFileURL,
                filename: localFilename
            )
            submittedJobId = response.jobId
            return response.jobId
        } catch {
            errorMessage = error.localizedDescription
            return nil
        }
    }

    func submitYoutubeDub(
        _ draft: AppleYoutubeDubDraft,
        using appState: AppState
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
            let response = try await client.submitYoutubeDub(Self.makeYoutubeDubPayload(from: draft))
            submittedJobId = response.jobId
            return response.jobId
        } catch {
            errorMessage = error.localizedDescription
            return nil
        }
    }

    private static func makeSubmission(from draft: AppleBookCreateDraft) -> BookGenerationJobSubmission {
        let inputFile = "\(draft.baseOutput).epub"
        let generatedDefaults = draft.generatedSourceDefaults
        var pipelineOverrides = makePipelineOverrides(
            from: generatedDefaults,
            imagePromptPipeline: draft.imagePromptPipeline,
            imageStyleTemplate: draft.imageStyleTemplate,
            imagePromptBatchingEnabled: draft.imagePromptBatchingEnabled,
            imagePromptBatchSize: draft.imagePromptBatchSize,
            imagePromptPlanBatchSize: draft.imagePromptPlanBatchSize,
            imagePromptContextSentences: draft.imagePromptContextSentences,
            imageWidth: draft.imageWidth,
            imageHeight: draft.imageHeight,
            imageSteps: draft.imageSteps,
            imageCfgScale: draft.imageCfgScale,
            imageSamplerName: draft.imageSamplerName,
            imageSeedWithPreviousImage: draft.imageSeedWithPreviousImage,
            imageBlankDetectionEnabled: draft.imageBlankDetectionEnabled,
            imageApiBaseURLs: draft.imageApiBaseURLs,
            imageConcurrency: draft.imageConcurrency,
            imageApiTimeoutSeconds: draft.imageApiTimeoutSeconds
        )
        mergeBookPerformanceOverrides(
            threadCount: draft.threadCount,
            queueSize: draft.queueSize,
            jobMaxWorkers: draft.jobMaxWorkers,
            into: &pipelineOverrides
        )
        mergeBookModelOverride(draft.llmModel, into: &pipelineOverrides)
        mergeBookVoiceOverrides(draft.voiceOverrides, into: &pipelineOverrides)
        let bookMetadata = makeBookMetadata(
            title: draft.bookName,
            author: draft.author,
            genre: draft.genre,
            language: draft.inputLanguage,
            summary: draft.summary,
            year: draft.year,
            isbn: draft.isbn,
            coverFile: draft.coverFile
        )

        let pipeline = makePipelineSubmission(
            inputFile: inputFile,
            baseOutputFile: draft.baseOutput,
            inputLanguage: draft.inputLanguage,
            targetLanguages: draft.targetLanguages,
            selectedVoice: draft.voice,
            voiceOverrides: draft.voiceOverrides,
            startSentence: 1,
            endSentence: nil,
            addImages: draft.includeImages,
            generateAudio: draft.generateAudio,
            audioMode: draft.audioMode,
            audioBitrateKbps: draft.audioBitrateKbps,
            writtenMode: draft.writtenMode,
            tempo: draft.tempo,
            sentencesPerOutputFile: draft.sentencesPerOutputFile,
            stitchFull: draft.stitchFull,
            includeTransliteration: draft.includeTransliteration,
            translationProvider: draft.translationProvider,
            translationBatchSize: draft.translationBatchSize,
            transliterationMode: draft.transliterationMode,
            transliterationModel: draft.transliterationModel,
            enableLookupCache: draft.enableLookupCache,
            lookupCacheBatchSize: draft.lookupCacheBatchSize,
            outputHtml: draft.outputHtml,
            outputPdf: draft.outputPdf,
            pipelineDefaults: draft.pipelineDefaults,
            pipelineOverrides: pipelineOverrides,
            correlationId: "apple-create",
            bookMetadata: bookMetadata
        )
        return BookGenerationJobSubmission(
            generator: BookGenerationRequest(
                topic: draft.topic,
                bookName: draft.bookName,
                genre: draft.genre,
                author: draft.author,
                numSentences: draft.sentenceCount,
                inputLanguage: draft.inputLanguage,
                outputLanguage: draft.targetLanguage,
                voice: draft.voice
            ),
            pipeline: pipeline
        )
    }

    private static func makePipelineSubmission(from draft: AppleNarrateEbookDraft) -> PipelineRequestPayload {
        var pipelineOverrides = [String: JSONValue]()
        mergeBookPerformanceOverrides(
            threadCount: draft.threadCount,
            queueSize: draft.queueSize,
            jobMaxWorkers: draft.jobMaxWorkers,
            into: &pipelineOverrides
        )
        mergeBookModelOverride(draft.llmModel, into: &pipelineOverrides)
        mergeBookVoiceOverrides(draft.voiceOverrides, into: &pipelineOverrides)
        let bookMetadata = makeBookMetadata(
            title: draft.title ?? draft.baseOutput,
            author: draft.author,
            genre: draft.genre,
            language: draft.inputLanguage,
            summary: draft.summary,
            year: draft.year,
            isbn: draft.isbn,
            coverFile: draft.coverFile
        )

        return makePipelineSubmission(
            inputFile: draft.inputFile,
            baseOutputFile: draft.baseOutput,
            inputLanguage: draft.inputLanguage,
            targetLanguages: draft.targetLanguages,
            selectedVoice: draft.voice,
            voiceOverrides: draft.voiceOverrides,
            startSentence: draft.startSentence,
            endSentence: draft.endSentence,
            addImages: false,
            generateAudio: draft.generateAudio,
            audioMode: draft.audioMode,
            audioBitrateKbps: draft.audioBitrateKbps,
            writtenMode: draft.writtenMode,
            tempo: draft.tempo,
            sentencesPerOutputFile: draft.sentencesPerOutputFile,
            stitchFull: draft.stitchFull,
            includeTransliteration: draft.includeTransliteration,
            translationProvider: draft.translationProvider,
            translationBatchSize: draft.translationBatchSize,
            transliterationMode: draft.transliterationMode,
            transliterationModel: draft.transliterationModel,
            enableLookupCache: draft.enableLookupCache,
            lookupCacheBatchSize: draft.lookupCacheBatchSize,
            outputHtml: draft.outputHtml,
            outputPdf: draft.outputPdf,
            pipelineDefaults: draft.pipelineDefaults,
            pipelineOverrides: pipelineOverrides,
            correlationId: "apple-narrate-ebook",
            bookMetadata: bookMetadata
        )
    }

    private static func makeBookMetadata(
        title: String,
        author: String?,
        genre: String?,
        language: String?,
        summary: String?,
        year: String?,
        isbn: String?,
        coverFile: String?
    ) -> [String: JSONValue] {
        let normalizedTitle = title.trimmingCharacters(in: .whitespacesAndNewlines)
        var metadata: [String: JSONValue] = [
            "title": .string(normalizedTitle),
            "book_title": .string(normalizedTitle),
            "job_label": .string(normalizedTitle),
            "source": .string("apple")
        ]
        if let author = author?.trimmingCharacters(in: .whitespacesAndNewlines), !author.isEmpty {
            metadata["author"] = .string(author)
            metadata["book_author"] = .string(author)
        }
        if let genre = genre?.trimmingCharacters(in: .whitespacesAndNewlines), !genre.isEmpty {
            metadata["genre"] = .string(genre)
            metadata["book_genre"] = .string(genre)
            let genres = AppleBookCreatePresentation.normalizedBookGenres(genre)
            if !genres.isEmpty {
                metadata["book_genres"] = .array(genres.map { .string($0) })
            }
        }
        if let language = language?.trimmingCharacters(in: .whitespacesAndNewlines), !language.isEmpty {
            metadata["language"] = .string(language)
            metadata["book_language"] = .string(language)
        }
        if let summary = summary?.trimmingCharacters(in: .whitespacesAndNewlines), !summary.isEmpty {
            metadata["book_summary"] = .string(summary)
        }
        if let year = year?.trimmingCharacters(in: .whitespacesAndNewlines), !year.isEmpty {
            metadata["book_year"] = .string(year)
        }
        if let isbn = isbn?.trimmingCharacters(in: .whitespacesAndNewlines), !isbn.isEmpty {
            metadata["isbn"] = .string(isbn)
            metadata["book_isbn"] = .string(isbn)
        }
        if let coverFile = coverFile?.trimmingCharacters(in: .whitespacesAndNewlines), !coverFile.isEmpty {
            metadata["book_cover_file"] = .string(coverFile)
        }
        return metadata
    }

    private static func makePipelineSubmission(
        inputFile: String,
        baseOutputFile: String,
        inputLanguage: String,
        targetLanguages: [String],
        selectedVoice: String,
        voiceOverrides: [String: String],
        startSentence: Int,
        endSentence: Int?,
        addImages: Bool,
        generateAudio: Bool,
        audioMode: String,
        audioBitrateKbps: Int?,
        writtenMode: String,
        tempo: Double,
        sentencesPerOutputFile: Int,
        stitchFull: Bool,
        includeTransliteration: Bool,
        translationProvider: String,
        translationBatchSize: Int,
        transliterationMode: String,
        transliterationModel: String?,
        enableLookupCache: Bool,
        lookupCacheBatchSize: Int,
        outputHtml: Bool,
        outputPdf: Bool,
        pipelineDefaults: BookCreationPipelineDefaults?,
        pipelineOverrides: [String: JSONValue],
        correlationId: String,
        bookMetadata: [String: JSONValue]
    ) -> PipelineRequestPayload {
        let input = PipelineInputPayload(
            inputFile: inputFile,
            baseOutputFile: baseOutputFile,
            inputLanguage: inputLanguage,
            targetLanguages: targetLanguages,
            sentencesPerOutputFile: sentencesPerOutputFile,
            startSentence: startSentence,
            endSentence: endSentence,
            stitchFull: stitchFull,
            generateAudio: generateAudio,
            audioMode: audioMode,
            audioBitrateKbps: audioBitrateKbps,
            writtenMode: writtenMode,
            selectedVoice: selectedVoice,
            voiceOverrides: voiceOverrides,
            outputHtml: outputHtml,
            outputPdf: outputPdf,
            addImages: addImages,
            includeTransliteration: includeTransliteration,
            translationProvider: translationProvider,
            translationBatchSize: translationBatchSize,
            transliterationMode: transliterationMode,
            transliterationModel: transliterationModel,
            enableLookupCache: enableLookupCache,
            lookupCacheBatchSize: lookupCacheBatchSize,
            tempo: tempo,
            bookMetadata: bookMetadata
        )
        return PipelineRequestPayload(
            config: makeBookConfig(from: bookMetadata),
            pipelineOverrides: pipelineOverrides,
            inputs: input,
            correlationId: correlationId
        )
    }

    private static func makeBookConfig(from metadata: [String: JSONValue]) -> [String: JSONValue] {
        var config = [String: JSONValue]()
        for key in [
            "book_title",
            "book_author",
            "book_genre",
            "book_genres",
            "book_language",
            "book_year",
            "book_isbn",
            "book_summary",
            "book_cover_file"
        ] {
            if let value = metadata[key] {
                config[key] = value
            }
        }
        return config
    }

    private static func makePipelineOverrides(
        from defaults: BookCreationGeneratedSourceDefaults?,
        imagePromptPipeline: String? = nil,
        imageStyleTemplate: String? = nil,
        imagePromptBatchingEnabled: Bool? = nil,
        imagePromptBatchSize: Int? = nil,
        imagePromptPlanBatchSize: Int? = nil,
        imagePromptContextSentences: Int? = nil,
        imageWidth: String? = nil,
        imageHeight: String? = nil,
        imageSteps: Int? = nil,
        imageCfgScale: Double? = nil,
        imageSamplerName: String? = nil,
        imageSeedWithPreviousImage: Bool? = nil,
        imageBlankDetectionEnabled: Bool? = nil,
        imageApiBaseURLs: [String] = [],
        imageConcurrency: Int? = nil,
        imageApiTimeoutSeconds: Double? = nil
    ) -> [String: JSONValue] {
        var overrides = [String: JSONValue]()
        if let defaults {
            overrides = [
                "image_prompt_pipeline": .string(defaults.imagePromptPipeline),
                "image_style_template": .string(defaults.imageStyleTemplate),
                "image_prompt_context_sentences": .number(Double(defaults.imagePromptContextSentences)),
                "image_width": .string(defaults.imageWidth),
                "image_height": .string(defaults.imageHeight)
            ]
        }
        if let imagePromptPipeline = imagePromptPipeline?.trimmingCharacters(in: .whitespacesAndNewlines),
           !imagePromptPipeline.isEmpty {
            overrides["image_prompt_pipeline"] = .string(imagePromptPipeline)
        }
        if let imageStyleTemplate = imageStyleTemplate?.trimmingCharacters(in: .whitespacesAndNewlines),
           !imageStyleTemplate.isEmpty {
            overrides["image_style_template"] = .string(imageStyleTemplate)
        }
        if let imagePromptBatchingEnabled {
            overrides["image_prompt_batching_enabled"] = .bool(imagePromptBatchingEnabled)
        }
        if let imagePromptBatchSize {
            overrides["image_prompt_batch_size"] = .number(Double(imagePromptBatchSize))
        }
        if let imagePromptPlanBatchSize {
            overrides["image_prompt_plan_batch_size"] = .number(Double(imagePromptPlanBatchSize))
        }
        if let imagePromptContextSentences {
            overrides["image_prompt_context_sentences"] = .number(Double(imagePromptContextSentences))
        }
        if let imageWidth = imageWidth?.trimmingCharacters(in: .whitespacesAndNewlines),
           !imageWidth.isEmpty {
            overrides["image_width"] = .string(imageWidth)
        }
        if let imageHeight = imageHeight?.trimmingCharacters(in: .whitespacesAndNewlines),
           !imageHeight.isEmpty {
            overrides["image_height"] = .string(imageHeight)
        }
        if let imageSteps {
            overrides["image_steps"] = .number(Double(imageSteps))
        }
        if let imageCfgScale {
            overrides["image_cfg_scale"] = .number(imageCfgScale)
        }
        if let imageSamplerName = imageSamplerName?.trimmingCharacters(in: .whitespacesAndNewlines),
           !imageSamplerName.isEmpty {
            overrides["image_sampler_name"] = .string(imageSamplerName)
        }
        if let imageSeedWithPreviousImage {
            overrides["image_seed_with_previous_image"] = .bool(imageSeedWithPreviousImage)
        }
        if let imageBlankDetectionEnabled {
            overrides["image_blank_detection_enabled"] = .bool(imageBlankDetectionEnabled)
        }
        if !imageApiBaseURLs.isEmpty {
            overrides["image_api_base_urls"] = .array(imageApiBaseURLs.map { .string($0) })
            overrides["image_api_base_url"] = .string(imageApiBaseURLs[0])
        }
        if let imageConcurrency {
            overrides["image_concurrency"] = .number(Double(imageConcurrency))
        }
        if let imageApiTimeoutSeconds {
            overrides["image_api_timeout_seconds"] = .number(imageApiTimeoutSeconds)
        }
        return overrides
    }

    private static func mergeBookModelOverride(
        _ llmModel: String?,
        into overrides: inout [String: JSONValue]
    ) {
        guard let model = llmModel?.trimmingCharacters(in: .whitespacesAndNewlines),
              !model.isEmpty else {
            return
        }
        overrides["ollama_model"] = .string(model)
    }

    private static func mergeBookVoiceOverrides(
        _ voiceOverrides: [String: String],
        into overrides: inout [String: JSONValue]
    ) {
        guard let value = AppleBookCreatePresentation.voiceOverridePipelineValue(voiceOverrides) else {
            return
        }
        overrides["voice_overrides"] = value
    }

    private static func mergeBookPerformanceOverrides(
        threadCount: Int?,
        queueSize: Int?,
        jobMaxWorkers: Int?,
        into overrides: inout [String: JSONValue]
    ) {
        if let threadCount {
            overrides["thread_count"] = .number(Double(threadCount))
        }
        if let queueSize {
            overrides["queue_size"] = .number(Double(queueSize))
        }
        if let jobMaxWorkers {
            overrides["job_max_workers"] = .number(Double(jobMaxWorkers))
        }
    }

    private static func makeSubtitlePayload(from draft: AppleSubtitleJobDraft) -> SubtitleJobFormPayload {
        SubtitleJobFormPayload(
            inputLanguage: draft.inputLanguage,
            targetLanguage: draft.targetLanguage,
            sourcePath: draft.sourcePath,
            originalLanguage: draft.inputLanguage,
            llmModel: draft.llmModel,
            translationProvider: draft.translationProvider,
            transliterationMode: draft.transliterationMode ?? "default",
            transliterationModel: draft.transliterationModel,
            enableTransliteration: draft.enableTransliteration,
            highlight: draft.highlight,
            showOriginal: draft.showOriginal,
            generateAudioBook: draft.generateAudioBook,
            batchSize: draft.batchSize,
            translationBatchSize: draft.translationBatchSize,
            workerCount: draft.workerCount,
            startTime: draft.startTime,
            endTime: draft.endTime,
            assFontSize: draft.assFontSize,
            assEmphasisScale: draft.assEmphasisScale,
            mediaMetadataJSON: #"{"source":"apple"}"#,
            mirrorBatchesToSourceDir: draft.mirrorBatchesToSourceDir,
            outputFormat: draft.outputFormat
        )
    }

    private static func makeYoutubeDubPayload(from draft: AppleYoutubeDubDraft) -> YoutubeDubRequestPayload {
        YoutubeDubRequestPayload(
            videoPath: draft.videoPath,
            subtitlePath: draft.subtitlePath,
            mediaMetadata: ["source": .string("apple")],
            sourceLanguage: draft.sourceLanguage,
            targetLanguage: draft.targetLanguage,
            voice: draft.voice,
            startTimeOffset: draft.startTimeOffset,
            endTimeOffset: draft.endTimeOffset,
            originalMixPercent: draft.originalMixPercent,
            flushSentences: draft.flushSentences,
            llmModel: draft.llmModel,
            translationProvider: draft.translationProvider,
            translationBatchSize: draft.translationBatchSize,
            transliterationMode: draft.transliterationMode,
            transliterationModel: draft.transliterationModel,
            splitBatches: draft.splitBatches,
            stitchBatches: draft.stitchBatches,
            includeTransliteration: draft.includeTransliteration,
            targetHeight: draft.targetHeight,
            preserveAspectRatio: draft.preserveAspectRatio,
            enableLookupCache: draft.enableLookupCache
        )
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
