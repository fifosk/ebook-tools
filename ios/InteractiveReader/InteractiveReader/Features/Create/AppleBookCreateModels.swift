import Foundation

struct AppleBookCreateDraft: Equatable {
    let topic: String
    let bookName: String
    let genre: String
    let author: String
    let summary: String?
    let year: String?
    let isbn: String?
    let coverFile: String?
    let sourceBookTitle: String?
    let sourceBookAuthor: String?
    let sourceBookGenre: String?
    let sourceBookSummary: String?
    let sentenceCount: Int
    let inputLanguage: String
    let targetLanguage: String
    let targetLanguages: [String]
    let voice: String
    let voiceOverrides: [String: String]
    let baseOutput: String
    let generateAudio: Bool
    let audioMode: String
    let audioBitrateKbps: Int?
    let writtenMode: String
    let tempo: Double
    let sentencesPerOutputFile: Int
    let stitchFull: Bool
    let includeTransliteration: Bool
    let translationProvider: String
    let llmModel: String?
    let translationBatchSize: Int
    let transliterationMode: String
    let transliterationModel: String?
    let enableLookupCache: Bool
    let lookupCacheBatchSize: Int
    let outputHtml: Bool
    let outputPdf: Bool
    let includeImages: Bool
    let imagePromptPipeline: String
    let imageStyleTemplate: String
    let imagePromptBatchingEnabled: Bool
    let imagePromptBatchSize: Int
    let imagePromptPlanBatchSize: Int
    let imagePromptContextSentences: Int
    let imageWidth: String
    let imageHeight: String
    let imageSteps: Int?
    let imageCfgScale: Double?
    let imageSamplerName: String?
    let imageSeedWithPreviousImage: Bool
    let imageBlankDetectionEnabled: Bool
    let imageApiBaseURLs: [String]
    let imageConcurrency: Int?
    let imageApiTimeoutSeconds: Double?
    let threadCount: Int?
    let queueSize: Int?
    let jobMaxWorkers: Int?
    let pipelineDefaults: BookCreationPipelineDefaults?
    let generatedSourceDefaults: BookCreationGeneratedSourceDefaults?
}

struct AppleNarrateEbookDraft: Equatable {
    let inputFile: String
    let baseOutput: String
    let title: String?
    let author: String?
    let genre: String?
    let summary: String?
    let year: String?
    let isbn: String?
    let coverFile: String?
    let startSentence: Int
    let endSentence: Int?
    let inputLanguage: String
    let targetLanguage: String
    let targetLanguages: [String]
    let voice: String
    let voiceOverrides: [String: String]
    let generateAudio: Bool
    let audioMode: String
    let audioBitrateKbps: Int?
    let writtenMode: String
    let tempo: Double
    let sentencesPerOutputFile: Int
    let stitchFull: Bool
    let includeTransliteration: Bool
    let translationProvider: String
    let llmModel: String?
    let translationBatchSize: Int
    let transliterationMode: String
    let transliterationModel: String?
    let enableLookupCache: Bool
    let lookupCacheBatchSize: Int
    let outputHtml: Bool
    let outputPdf: Bool
    let threadCount: Int?
    let queueSize: Int?
    let jobMaxWorkers: Int?
    let pipelineDefaults: BookCreationPipelineDefaults?

    func replacingInputFile(_ inputFile: String) -> AppleNarrateEbookDraft {
        AppleNarrateEbookDraft(
            inputFile: inputFile,
            baseOutput: baseOutput,
            title: title,
            author: author,
            genre: genre,
            summary: summary,
            year: year,
            isbn: isbn,
            coverFile: coverFile,
            startSentence: startSentence,
            endSentence: endSentence,
            inputLanguage: inputLanguage,
            targetLanguage: targetLanguage,
            targetLanguages: targetLanguages,
            voice: voice,
            voiceOverrides: voiceOverrides,
            generateAudio: generateAudio,
            audioMode: audioMode,
            audioBitrateKbps: audioBitrateKbps,
            writtenMode: writtenMode,
            tempo: tempo,
            sentencesPerOutputFile: sentencesPerOutputFile,
            stitchFull: stitchFull,
            includeTransliteration: includeTransliteration,
            translationProvider: translationProvider,
            llmModel: llmModel,
            translationBatchSize: translationBatchSize,
            transliterationMode: transliterationMode,
            transliterationModel: transliterationModel,
            enableLookupCache: enableLookupCache,
            lookupCacheBatchSize: lookupCacheBatchSize,
            outputHtml: outputHtml,
            outputPdf: outputPdf,
            threadCount: threadCount,
            queueSize: queueSize,
            jobMaxWorkers: jobMaxWorkers,
            pipelineDefaults: pipelineDefaults
        )
    }
}

struct AppleSubtitleJobDraft: Equatable {
    let sourcePath: String?
    let mediaMetadata: [String: JSONValue]?
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
    let workerCount: Int
    let batchSize: Int
    let translationBatchSize: Int
    let assFontSize: Int?
    let assEmphasisScale: Double?
}

struct AppleYoutubeDubDraft: Equatable {
    let videoPath: String
    let subtitlePath: String
    let mediaMetadata: [String: JSONValue]
    let sourceLanguage: String?
    let targetLanguage: String?
    let voice: String
    let startTimeOffset: String?
    let endTimeOffset: String?
    let originalMixPercent: Double
    let flushSentences: Int
    let llmModel: String?
    let translationProvider: String
    let translationBatchSize: Int
    let transliterationMode: String?
    let transliterationModel: String?
    let splitBatches: Bool
    let stitchBatches: Bool
    let includeTransliteration: Bool
    let targetHeight: Int
    let preserveAspectRatio: Bool
    let enableLookupCache: Bool
}

struct AppleCreateChapterOption: Identifiable, Equatable {
    let id: String
    let title: String
    let startSentence: Int
    let endSentence: Int?

    var sentenceRangeLabel: String {
        guard let endSentence else {
            return "from sentence \(startSentence)"
        }
        return "sentences \(startSentence)-\(endSentence)"
    }

    var pickerLabel: String {
        "\(title) · \(sentenceRangeLabel)"
    }
}

struct AppleCreateChapterRangeSelection: Equatable {
    let startIndex: Int
    let endIndex: Int
    let startSentence: Int
    let endSentence: Int
    let count: Int
    let label: String

    var sentenceRangeLabel: String {
        "sentences \(startSentence)-\(endSentence)"
    }
}

struct AppleYoutubeSourceSelection: Equatable {
    let video: YoutubeNasVideoEntry
    let subtitle: YoutubeNasSubtitleEntry?
}

struct AppleNarrateSourceDefaults: Equatable {
    let path: String
    let baseOutput: String?
}

struct AppleSubtitleSourceDefaults: Equatable {
    let path: String
    let metadataLookupSourceName: String
}

struct AppleYoutubeSourceDefaults: Equatable {
    let nextStorageScope: String
    let videoPath: String?
    let subtitlePath: String?
}

struct AppleCreateEstimatedAudio {
    static let secondsPerSentence = 6.4
}

struct AppleBookCreateVoiceInventory: Equatable {
    struct MacOSVoice: Equatable {
        let name: String
        let lang: String
        let quality: String?
        let gender: String?
    }

    struct GTTSLanguage: Equatable {
        let code: String
        let name: String
    }

    struct PiperVoice: Equatable {
        let name: String
        let lang: String
        let quality: String
    }

    let macos: [MacOSVoice]
    let gtts: [GTTSLanguage]
    let piper: [PiperVoice]
}

struct AppleBookCreateLanguage: Hashable, Identifiable {
    let value: String

    var id: String { value.lowercased() }
    var backendValue: String { value }
    var label: String { Self.displayLabel(for: value) }

    init?(_ value: String) {
        let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return nil }
        self.value = trimmed
    }

    init?(backendValue: String) {
        self.init(backendValue)
    }

    static let english = AppleBookCreateLanguage("English")!
    static let arabic = AppleBookCreateLanguage("Arabic")!
    static let slovak = AppleBookCreateLanguage("Slovak")!
    static let spanish = AppleBookCreateLanguage("Spanish")!
    static let french = AppleBookCreateLanguage("French")!
    static let german = AppleBookCreateLanguage("German")!

    static let fallbackOptions: [AppleBookCreateLanguage] =
        AppleLanguageCatalog.orderedLanguageNames.compactMap { AppleBookCreateLanguage($0) }
    static let allCases = fallbackOptions

    static func options(from supported: [String]) -> [AppleBookCreateLanguage] {
        var seen = Set<String>()
        var options: [AppleBookCreateLanguage] = []
        for language in supported.compactMap(AppleBookCreateLanguage.init(backendValue:)) + fallbackOptions {
            let key = language.id
            guard !seen.contains(key) else { continue }
            seen.insert(key)
            options.append(language)
        }
        return options
    }

    private static func displayLabel(for value: String) -> String {
        value.trimmingCharacters(in: .whitespacesAndNewlines)
    }
}

enum AppleGeneratedBookImageStyleTemplate: String, CaseIterable, Identifiable {
    case photorealistic
    case comics
    case childrenBook = "children_book"
    case wireframe

    var id: String { rawValue }
    var backendValue: String { rawValue }

    var label: String {
        switch self {
        case .photorealistic:
            return "Photorealistic"
        case .comics:
            return "Comics"
        case .childrenBook:
            return "Children's book"
        case .wireframe:
            return "Wireframe"
        }
    }

    init?(backendValue: String) {
        let normalized = backendValue.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        let aliases = [
            "comic": "comics",
            "comic panel": "comics",
            "graphic novel": "comics",
            "storybook": "children_book",
            "children": "children_book",
            "children book": "children_book",
            "children's book": "children_book",
            "wire frame": "wireframe",
            "blueprint": "wireframe",
            "line art": "wireframe"
        ]
        let candidate = aliases[normalized] ?? normalized
        guard let match = Self.allCases.first(where: { $0.rawValue == candidate }) else {
            return nil
        }
        self = match
    }
}

enum AppleGeneratedBookImagePromptPipeline: String, CaseIterable, Identifiable {
    case promptPlan = "prompt_plan"
    case visualCanon = "visual_canon"

    var id: String { rawValue }
    var backendValue: String { rawValue }

    var label: String {
        switch self {
        case .promptPlan:
            return "Prompt plan"
        case .visualCanon:
            return "Visual canon"
        }
    }

    init?(backendValue: String) {
        let normalized = backendValue.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        switch normalized {
        case "visual_canon", "visual-canon", "canon":
            self = .visualCanon
        case "prompt_plan", "prompt-plan", "plan":
            self = .promptPlan
        default:
            self = .promptPlan
        }
    }
}

struct AppleCreateTimeRange: Equatable {
    let start: String
    let end: String
}

struct AppleCreateOffsetRange: Equatable {
    let start: String
    let end: String
}

enum AppleCreateValidationError: Error, Equatable {
    case subtitleStartTime
    case subtitleEndTime
    case youtubeStartOffset
    case youtubeEndOffset

    var message: String {
        switch self {
        case .subtitleStartTime:
            return "Enter a valid start time in MM:SS or HH:MM:SS format."
        case .subtitleEndTime:
            return "Enter a valid end time in MM:SS, HH:MM:SS, or +offset format."
        case .youtubeStartOffset:
            return "Enter a valid start offset in seconds, MM:SS, or HH:MM:SS format."
        case .youtubeEndOffset:
            return "Enter a valid end offset in seconds, MM:SS, or HH:MM:SS format."
        }
    }
}

enum AppleVoicePreviewState: Equatable {
    case idle
    case loading
    case playing
}

enum AppleBookCreateEditedField: Hashable {
    case topic
    case bookName
    case genre
    case author
    case sourceBookTitle
    case sourceBookAuthor
    case sourceBookGenre
    case bookSummary
    case bookYear
    case bookIsbn
    case bookCoverFile
    case sourcePath
    case sourceBaseOutput
    case sourceStartSentence
    case sourceEndSentence
    case subtitleSourcePath
    case youtubeVideoPath
    case youtubeSubtitlePath
    case youtubeStartOffset
    case youtubeEndOffset
    case youtubeOriginalMixPercent
    case youtubeFlushSentences
    case youtubeTargetHeight
    case youtubePreserveAspectRatio
    case youtubeSplitBatches
    case youtubeStitchBatches
    case subtitleOutputFormat
    case subtitleStartTime
    case subtitleEndTime
    case subtitleEnableTransliteration
    case subtitleHighlight
    case subtitleShowOriginal
    case subtitleGenerateAudioBook
    case subtitleMirrorBatchesToSourceDir
    case subtitleTranslationProvider
    case subtitleLlmModel
    case subtitleTransliterationMode
    case subtitleTransliterationModel
    case subtitleWorkerCount
    case subtitleBatchSize
    case subtitleTranslationBatchSize
    case subtitleAssFontSize
    case subtitleAssEmphasisScale
    case sentenceCount
    case inputLanguage
    case targetLanguage
    case additionalTargetLanguages
    case voice
    case targetVoice
    case languageVoiceOverrides
    case generateAudio
    case audioMode
    case audioBitrateKbps
    case writtenMode
    case tempo
    case bookSentencesPerOutputFile
    case stitchFull
    case includeTransliteration
    case bookTranslationProvider
    case bookLlmModel
    case bookTranslationBatchSize
    case bookTransliterationMode
    case bookTransliterationModel
    case enableLookupCache
    case bookLookupCacheBatchSize
    case outputHtml
    case outputPdf
    case includeImages
    case imagePromptPipeline
    case imageStyleTemplate
    case imagePromptBatchingEnabled
    case imagePromptBatchSize
    case imagePromptPlanBatchSize
    case imagePromptContextSentences
    case imageWidth
    case imageHeight
    case imageSteps
    case imageCfgScale
    case imageSamplerName
    case imageSeedWithPreviousImage
    case imageBlankDetectionEnabled
    case imageApiBaseURLs
    case imageConcurrency
    case imageApiTimeoutSeconds
    case threadCount
    case queueSize
    case jobMaxWorkers
}

struct AppleNarrationHistoryDefaults: Equatable {
    let inputFile: String?
    let baseOutput: String?
    let startSentence: Int?
    let inputLanguage: AppleBookCreateLanguage?
    let targetLanguage: AppleBookCreateLanguage?
    let additionalTargetLanguages: String?
    let voice: AppleBookCreateVoiceOption?
    let voiceOverrides: [String: String]?
    let generateAudio: Bool?
    let audioMode: String?
    let audioBitrateKbps: String?
    let writtenMode: String?
    let tempo: Double?
    let sentencesPerOutputFile: Int?
    let stitchFull: Bool?
    let includeTransliteration: Bool?
    let translationProvider: AppleSubtitleTranslationProvider?
    let llmModel: String?
    let translationBatchSize: Int?
    let transliterationMode: AppleSubtitleTransliterationMode?
    let transliterationModel: String?
    let enableLookupCache: Bool?
    let lookupCacheBatchSize: Int?
    let outputHtml: Bool?
    let outputPdf: Bool?
}

struct AppleSubtitleHistoryDefaults: Equatable {
    let sourcePath: String?
    let inputLanguage: AppleBookCreateLanguage?
    let targetLanguage: AppleBookCreateLanguage?
    let startTime: String?
    let endTime: String?
    let enableTransliteration: Bool?
    let showOriginal: Bool?
    let translationProvider: AppleSubtitleTranslationProvider?
    let llmModel: String?
    let transliterationMode: AppleSubtitleTransliterationMode?
    let transliterationModel: String?
    let workerCount: Int?
    let batchSize: Int?
    let translationBatchSize: Int?
}

struct AppleYoutubeHistoryDefaults: Equatable {
    let videoPath: String?
    let subtitlePath: String?
    let targetLanguage: AppleBookCreateLanguage?
    let voice: AppleBookCreateVoiceOption?
    let startOffset: String?
    let endOffset: String?
    let originalMixPercent: Double?
    let flushSentences: Int?
    let translationProvider: AppleSubtitleTranslationProvider?
    let llmModel: String?
    let translationBatchSize: Int?
    let transliterationMode: AppleSubtitleTransliterationMode?
    let transliterationModel: String?
    let splitBatches: Bool?
    let stitchBatches: Bool?
    let includeTransliteration: Bool?
    let targetHeight: AppleYoutubeDubTargetHeight?
    let preserveAspectRatio: Bool?
    let enableLookupCache: Bool?
}

struct AppleGeneratedBookHistoryDefaults: Equatable {
    let topic: String?
    let bookName: String?
    let genre: String?
    let author: String?
    let sourceBookTitle: String?
    let sourceBookAuthor: String?
    let sourceBookGenre: String?
    let sourceBookSummary: String?
    let sentenceCount: Int?
    let inputLanguage: AppleBookCreateLanguage?
    let targetLanguage: AppleBookCreateLanguage?
    let additionalTargetLanguages: String?
    let voice: AppleBookCreateVoiceOption?
    let voiceOverrides: [String: String]?
    let generateAudio: Bool?
    let audioMode: String?
    let audioBitrateKbps: String?
    let writtenMode: String?
    let tempo: Double?
    let bookSentencesPerOutputFile: Int?
    let stitchFull: Bool?
    let includeTransliteration: Bool?
    let bookTranslationProvider: AppleSubtitleTranslationProvider?
    let bookLlmModel: String?
    let bookTranslationBatchSize: Int?
    let bookTransliterationMode: AppleSubtitleTransliterationMode?
    let bookTransliterationModel: String?
    let enableLookupCache: Bool?
    let bookLookupCacheBatchSize: Int?
    let outputHtml: Bool?
    let outputPdf: Bool?
    let includeImages: Bool?
    let imagePromptPipeline: AppleGeneratedBookImagePromptPipeline?
    let imageStyleTemplate: AppleGeneratedBookImageStyleTemplate?
    let imagePromptContextSentences: Int?
    let imageWidth: String?
    let imageHeight: String?
}

struct AppleCreateResolvedDefaults: Equatable {
    let topic: String?
    let bookName: String?
    let genre: String?
    let author: String?
    let sentenceCount: Int
    let inputLanguage: AppleBookCreateLanguage?
    let targetLanguage: AppleBookCreateLanguage?
    let additionalTargetLanguages: String?
    let voice: AppleBookCreateVoiceOption?
    let generateAudio: Bool?
    let audioMode: String?
    let audioBitrateKbps: String?
    let writtenMode: String?
    let tempo: Double?
    let bookSentencesPerOutputFile: Int?
    let stitchFull: Bool?
    let includeTransliteration: Bool?
    let bookTranslationProvider: AppleSubtitleTranslationProvider?
    let bookTranslationBatchSize: Int?
    let bookTransliterationMode: AppleSubtitleTransliterationMode?
    let enableLookupCache: Bool?
    let bookLookupCacheBatchSize: Int?
    let outputHtml: Bool?
    let outputPdf: Bool?
    let includeImages: Bool?
    let imagePromptPipeline: AppleGeneratedBookImagePromptPipeline?
    let imageStyleTemplate: AppleGeneratedBookImageStyleTemplate?
    let imagePromptContextSentences: Int?
    let imageWidth: String?
    let imageHeight: String?
    let subtitleTranslationProvider: AppleSubtitleTranslationProvider?
    let subtitleWorkerCount: Int?
    let subtitleBatchSize: Int?
    let subtitleTranslationBatchSize: Int?
    let subtitleAssFontSize: Int?
    let subtitleAssEmphasisScale: Double?
    let youtubeOriginalMixPercent: Double?
    let youtubeFlushSentences: Int?
    let youtubeTargetHeight: AppleYoutubeDubTargetHeight?
    let youtubePreserveAspectRatio: Bool?
    let youtubeSplitBatches: Bool?
    let youtubeStitchBatches: Bool?
}
