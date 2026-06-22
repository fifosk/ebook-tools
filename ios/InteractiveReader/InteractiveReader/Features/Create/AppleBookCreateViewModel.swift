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

    private static func makeSubmission(from draft: AppleBookCreateDraft) -> BookGenerationJobSubmission {
        let inputFile = "\(draft.baseOutput).epub"
        let generatedDefaults = draft.generatedSourceDefaults
        let pipeline = makePipelineSubmission(
            inputFile: inputFile,
            baseOutputFile: draft.baseOutput,
            inputLanguage: draft.inputLanguage,
            targetLanguage: draft.targetLanguage,
            selectedVoice: draft.voice,
            addImages: generatedDefaults?.addImages ?? false,
            includeTransliteration: draft.includeTransliteration,
            enableLookupCache: draft.enableLookupCache,
            pipelineDefaults: draft.pipelineDefaults,
            pipelineOverrides: makePipelineOverrides(from: generatedDefaults),
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
            addImages: false,
            includeTransliteration: draft.includeTransliteration,
            enableLookupCache: draft.enableLookupCache,
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
        addImages: Bool,
        includeTransliteration: Bool,
        enableLookupCache: Bool,
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
            startSentence: 1,
            generateAudio: pipelineDefaults?.generateAudio ?? true,
            audioMode: pipelineDefaults?.audioMode ?? "4",
            audioBitrateKbps: pipelineDefaults?.audioBitrateKbps ?? 96,
            writtenMode: pipelineDefaults?.writtenMode ?? "4",
            selectedVoice: selectedVoice,
            outputHtml: pipelineDefaults?.outputHtml ?? false,
            outputPdf: pipelineDefaults?.outputPdf ?? false,
            addImages: addImages,
            includeTransliteration: includeTransliteration,
            translationProvider: pipelineDefaults?.translationProvider ?? "llm",
            translationBatchSize: pipelineDefaults?.translationBatchSize ?? 10,
            transliterationMode: pipelineDefaults?.transliterationMode ?? "default",
            enableLookupCache: enableLookupCache,
            lookupCacheBatchSize: pipelineDefaults?.lookupCacheBatchSize ?? 10,
            tempo: pipelineDefaults?.tempo ?? 1.0,
            bookMetadata: bookMetadata
        )
        return PipelineRequestPayload(
            pipelineOverrides: pipelineOverrides,
            inputs: input,
            correlationId: correlationId
        )
    }

    private static func makePipelineOverrides(
        from defaults: BookCreationGeneratedSourceDefaults?
    ) -> [String: JSONValue] {
        guard let defaults else { return [:] }
        return [
            "image_prompt_pipeline": .string(defaults.imagePromptPipeline),
            "image_style_template": .string(defaults.imageStyleTemplate),
            "image_prompt_context_sentences": .number(Double(defaults.imagePromptContextSentences)),
            "image_width": .string(defaults.imageWidth),
            "image_height": .string(defaults.imageHeight)
        ]
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
            translationBatchSize: draft.translationBatchSize,
            startTime: draft.startTime,
            endTime: draft.endTime,
            assFontSize: draft.assFontSize,
            assEmphasisScale: draft.assEmphasisScale,
            mediaMetadataJSON: #"{"source":"apple"}"#,
            mirrorBatchesToSourceDir: draft.mirrorBatchesToSourceDir,
            outputFormat: draft.outputFormat
        )
    }
}

struct AppleBookCreateDraft: Equatable {
    let topic: String
    let bookName: String
    let genre: String
    let author: String
    let sentenceCount: Int
    let inputLanguage: String
    let targetLanguage: String
    let voice: String
    let baseOutput: String
    let includeTransliteration: Bool
    let enableLookupCache: Bool
    let pipelineDefaults: BookCreationPipelineDefaults?
    let generatedSourceDefaults: BookCreationGeneratedSourceDefaults?
}

struct AppleNarrateEbookDraft: Equatable {
    let inputFile: String
    let baseOutput: String
    let inputLanguage: String
    let targetLanguage: String
    let voice: String
    let includeTransliteration: Bool
    let enableLookupCache: Bool
    let pipelineDefaults: BookCreationPipelineDefaults?

    func replacingInputFile(_ inputFile: String) -> AppleNarrateEbookDraft {
        AppleNarrateEbookDraft(
            inputFile: inputFile,
            baseOutput: baseOutput,
            inputLanguage: inputLanguage,
            targetLanguage: targetLanguage,
            voice: voice,
            includeTransliteration: includeTransliteration,
            enableLookupCache: enableLookupCache,
            pipelineDefaults: pipelineDefaults
        )
    }
}

struct AppleSubtitleJobDraft: Equatable {
    let sourcePath: String?
    let inputLanguage: String
    let targetLanguage: String
    let outputFormat: String
    let startTime: String
    let endTime: String?
    let enableTransliteration: Bool
    let highlight: Bool
    let showOriginal: Bool
    let generateAudioBook: Bool
    let mirrorBatchesToSourceDir: Bool
    let translationProvider: String
    let llmModel: String?
    let transliterationMode: String?
    let transliterationModel: String?
    let translationBatchSize: Int
    let assFontSize: Int?
    let assEmphasisScale: Double?
}

enum AppleBookCreateLanguage: String, CaseIterable, Identifiable {
    case english = "English"
    case arabic = "Arabic"
    case slovak = "Slovak"
    case spanish = "Spanish"
    case french = "French"
    case german = "German"

    var id: String { rawValue }
    var backendValue: String { rawValue }

    var label: String {
        switch self {
        case .english: return "English"
        case .arabic: return "Arabic"
        case .slovak: return "Slovak"
        case .spanish: return "Spanish"
        case .french: return "French"
        case .german: return "German"
        }
    }

    init?(backendValue: String) {
        let normalized = backendValue.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        guard let match = Self.allCases.first(where: { $0.rawValue.lowercased() == normalized }) else {
            return nil
        }
        self = match
    }
}
