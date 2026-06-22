import SwiftUI

@MainActor
final class AppleBookCreateViewModel: ObservableObject {
    @Published private(set) var isSubmitting = false
    @Published private(set) var isLoadingOptions = false
    @Published private(set) var creationOptions: BookCreationOptionsResponse?
    @Published private(set) var optionsErrorMessage: String?
    @Published var errorMessage: String?
    @Published private(set) var submittedJobId: String?
    private var loadedOptionsCacheKey: String?

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

    func submit(_ draft: AppleBookCreateDraft, using appState: AppState) async -> String? {
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

    private static func makeSubmission(from draft: AppleBookCreateDraft) -> BookGenerationJobSubmission {
        let inputFile = "\(draft.baseOutput).epub"
        let pipelineDefaults = draft.pipelineDefaults
        let generatedDefaults = draft.generatedSourceDefaults
        let pipelineOverrides = makePipelineOverrides(from: generatedDefaults)
        let input = PipelineInputPayload(
            inputFile: inputFile,
            baseOutputFile: draft.baseOutput,
            inputLanguage: draft.inputLanguage,
            targetLanguages: [draft.targetLanguage],
            sentencesPerOutputFile: pipelineDefaults?.sentencesPerOutputFile ?? 10,
            startSentence: 1,
            generateAudio: pipelineDefaults?.generateAudio ?? true,
            audioMode: pipelineDefaults?.audioMode ?? "4",
            audioBitrateKbps: pipelineDefaults?.audioBitrateKbps ?? 96,
            writtenMode: pipelineDefaults?.writtenMode ?? "4",
            selectedVoice: draft.voice,
            outputHtml: pipelineDefaults?.outputHtml ?? false,
            outputPdf: pipelineDefaults?.outputPdf ?? false,
            addImages: generatedDefaults?.addImages ?? false,
            includeTransliteration: draft.includeTransliteration,
            translationProvider: pipelineDefaults?.translationProvider ?? "llm",
            translationBatchSize: pipelineDefaults?.translationBatchSize ?? 10,
            transliterationMode: pipelineDefaults?.transliterationMode ?? "default",
            enableLookupCache: draft.enableLookupCache,
            lookupCacheBatchSize: pipelineDefaults?.lookupCacheBatchSize ?? 10,
            tempo: pipelineDefaults?.tempo ?? 1.0,
            bookMetadata: [
                "title": .string(draft.bookName),
                "book_title": .string(draft.bookName),
                "author": .string(draft.author),
                "genre": .string(draft.genre),
                "job_label": .string(draft.bookName),
                "source": .string("apple")
            ]
        )
        let pipeline = PipelineRequestPayload(
            pipelineOverrides: pipelineOverrides,
            inputs: input,
            correlationId: "apple-create"
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

enum AppleBookCreateVoice: String, CaseIterable, Identifiable {
    case gtts = "gTTS"
    case macos = "macOS"
    case edge = "edge-tts"

    var id: String { rawValue }
    var backendValue: String { rawValue }

    var label: String {
        switch self {
        case .gtts: return "gTTS"
        case .macos: return "macOS"
        case .edge: return "Edge TTS"
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
