import SwiftUI

@MainActor
final class AppleBookCreateViewModel: ObservableObject {
    @Published private(set) var isSubmitting = false
    @Published private(set) var isLoadingOptions = false
    @Published private(set) var creationOptions: BookCreationOptionsResponse?
    @Published private(set) var subtitleLlmModels: [String] = []
    @Published private(set) var optionsErrorMessage: String?
    @Published var errorMessage: String?
    @Published private(set) var submittedJobId: String?
    private var loadedOptionsCacheKey: String?
    private var loadedSubtitleModelsCacheKey: String?

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
        } catch {
            optionsErrorMessage = error.localizedDescription
            return nil
        }
    }

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
        let pipeline = makePipelineSubmission(
            inputFile: inputFile,
            baseOutputFile: draft.baseOutput,
            inputLanguage: draft.inputLanguage,
            targetLanguage: draft.targetLanguage,
            selectedVoice: draft.voice,
            startSentence: 1,
            endSentence: nil,
            addImages: draft.includeImages,
            generateAudio: draft.generateAudio,
            audioMode: draft.audioMode,
            audioBitrateKbps: draft.audioBitrateKbps,
            writtenMode: draft.writtenMode,
            tempo: draft.tempo,
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
            pipelineOverrides: makePipelineOverrides(
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
                imageConcurrency: draft.imageConcurrency,
                imageApiTimeoutSeconds: draft.imageApiTimeoutSeconds
            ),
            correlationId: "apple-create",
            bookMetadata: [
                "title": .string(draft.bookName),
                "book_title": .string(draft.bookName),
                "author": .string(draft.author),
                "genre": .string(draft.genre),
                "job_label": .string(draft.bookName),
                "source": .string("apple")
            ]
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
        makePipelineSubmission(
            inputFile: draft.inputFile,
            baseOutputFile: draft.baseOutput,
            inputLanguage: draft.inputLanguage,
            targetLanguage: draft.targetLanguage,
            selectedVoice: draft.voice,
            startSentence: draft.startSentence,
            endSentence: draft.endSentence,
            addImages: false,
            generateAudio: draft.generateAudio,
            audioMode: draft.audioMode,
            audioBitrateKbps: draft.audioBitrateKbps,
            writtenMode: draft.writtenMode,
            tempo: draft.tempo,
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
            pipelineOverrides: [:],
            correlationId: "apple-narrate-ebook",
            bookMetadata: [
                "title": .string(draft.baseOutput),
                "book_title": .string(draft.baseOutput),
                "job_label": .string(draft.baseOutput),
                "source": .string("apple")
            ]
        )
    }

    private static func makePipelineSubmission(
        inputFile: String,
        baseOutputFile: String,
        inputLanguage: String,
        targetLanguage: String,
        selectedVoice: String,
        startSentence: Int,
        endSentence: Int?,
        addImages: Bool,
        generateAudio: Bool,
        audioMode: String,
        audioBitrateKbps: Int?,
        writtenMode: String,
        tempo: Double,
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
            targetLanguages: [targetLanguage],
            sentencesPerOutputFile: pipelineDefaults?.sentencesPerOutputFile ?? 10,
            startSentence: startSentence,
            endSentence: endSentence,
            generateAudio: generateAudio,
            audioMode: audioMode,
            audioBitrateKbps: audioBitrateKbps,
            writtenMode: writtenMode,
            selectedVoice: selectedVoice,
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
            pipelineOverrides: pipelineOverrides,
            inputs: input,
            correlationId: correlationId
        )
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
        if let imageConcurrency {
            overrides["image_concurrency"] = .number(Double(imageConcurrency))
        }
        if let imageApiTimeoutSeconds {
            overrides["image_api_timeout_seconds"] = .number(imageApiTimeoutSeconds)
        }
        return overrides
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
