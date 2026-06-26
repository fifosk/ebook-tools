import Foundation

struct PipelineInputPayload: Encodable, Equatable {
    let inputFile: String
    let baseOutputFile: String
    let inputLanguage: String
    let targetLanguages: [String]
    let sentencesPerOutputFile: Int
    let startSentence: Int
    let endSentence: Int?
    let stitchFull: Bool
    let generateAudio: Bool
    let audioMode: String
    let audioBitrateKbps: Int?
    let writtenMode: String
    let selectedVoice: String
    let voiceOverrides: [String: String]
    let outputHtml: Bool
    let outputPdf: Bool
    let addImages: Bool
    let includeTransliteration: Bool
    let translationProvider: String
    let translationBatchSize: Int
    let transliterationMode: String
    let transliterationModel: String?
    let enableLookupCache: Bool
    let lookupCacheBatchSize: Int
    let tempo: Double
    let bookMetadata: [String: JSONValue]

    init(
        inputFile: String,
        baseOutputFile: String,
        inputLanguage: String,
        targetLanguages: [String],
        sentencesPerOutputFile: Int = 10,
        startSentence: Int = 1,
        endSentence: Int? = nil,
        stitchFull: Bool = false,
        generateAudio: Bool = true,
        audioMode: String = "1",
        audioBitrateKbps: Int? = nil,
        writtenMode: String = "4",
        selectedVoice: String = "gTTS",
        voiceOverrides: [String: String] = [:],
        outputHtml: Bool = false,
        outputPdf: Bool = false,
        addImages: Bool = false,
        includeTransliteration: Bool = true,
        translationProvider: String = "llm",
        translationBatchSize: Int = 10,
        transliterationMode: String = "default",
        transliterationModel: String? = nil,
        enableLookupCache: Bool = true,
        lookupCacheBatchSize: Int = 10,
        tempo: Double = 1.0,
        bookMetadata: [String: JSONValue] = [:]
    ) {
        self.inputFile = inputFile
        self.baseOutputFile = baseOutputFile
        self.inputLanguage = inputLanguage
        self.targetLanguages = targetLanguages
        self.sentencesPerOutputFile = sentencesPerOutputFile
        self.startSentence = startSentence
        self.endSentence = endSentence
        self.stitchFull = stitchFull
        self.generateAudio = generateAudio
        self.audioMode = audioMode
        self.audioBitrateKbps = audioBitrateKbps
        self.writtenMode = writtenMode
        self.selectedVoice = selectedVoice
        self.voiceOverrides = voiceOverrides
        self.outputHtml = outputHtml
        self.outputPdf = outputPdf
        self.addImages = addImages
        self.includeTransliteration = includeTransliteration
        self.translationProvider = translationProvider
        self.translationBatchSize = translationBatchSize
        self.transliterationMode = transliterationMode
        self.transliterationModel = transliterationModel
        self.enableLookupCache = enableLookupCache
        self.lookupCacheBatchSize = lookupCacheBatchSize
        self.tempo = tempo
        self.bookMetadata = bookMetadata
    }

    enum CodingKeys: String, CodingKey {
        case inputFile = "input_file"
        case baseOutputFile = "base_output_file"
        case inputLanguage = "input_language"
        case targetLanguages = "target_languages"
        case sentencesPerOutputFile = "sentences_per_output_file"
        case startSentence = "start_sentence"
        case endSentence = "end_sentence"
        case stitchFull = "stitch_full"
        case generateAudio = "generate_audio"
        case audioMode = "audio_mode"
        case audioBitrateKbps = "audio_bitrate_kbps"
        case writtenMode = "written_mode"
        case selectedVoice = "selected_voice"
        case voiceOverrides = "voice_overrides"
        case outputHtml = "output_html"
        case outputPdf = "output_pdf"
        case addImages = "add_images"
        case includeTransliteration = "include_transliteration"
        case translationProvider = "translation_provider"
        case translationBatchSize = "translation_batch_size"
        case transliterationMode = "transliteration_mode"
        case transliterationModel = "transliteration_model"
        case enableLookupCache = "enable_lookup_cache"
        case lookupCacheBatchSize = "lookup_cache_batch_size"
        case tempo
        case bookMetadata = "book_metadata"
    }
}

struct PipelineRequestPayload: Encodable, Equatable {
    let config: [String: JSONValue]
    let environmentOverrides: [String: JSONValue]
    let pipelineOverrides: [String: JSONValue]
    let inputs: PipelineInputPayload
    let correlationId: String?

    init(
        config: [String: JSONValue] = [:],
        environmentOverrides: [String: JSONValue] = [:],
        pipelineOverrides: [String: JSONValue] = [:],
        inputs: PipelineInputPayload,
        correlationId: String? = nil
    ) {
        self.config = config
        self.environmentOverrides = environmentOverrides
        self.pipelineOverrides = pipelineOverrides
        self.inputs = inputs
        self.correlationId = correlationId
    }

    enum CodingKeys: String, CodingKey {
        case config
        case environmentOverrides = "environment_overrides"
        case pipelineOverrides = "pipeline_overrides"
        case inputs
        case correlationId = "correlation_id"
    }
}

struct PipelineSubmissionResponse: Decodable, Equatable {
    let jobId: String
    let status: PipelineJobStatus
    let createdAt: String
    let jobType: String
}

struct CreationTemplateListResponse: Decodable, Equatable {
    let templates: [CreationTemplateEntry]
}

struct CreationTemplateEntry: Decodable, Equatable, Identifiable {
    let id: String
    let name: String
    let mode: String
    let createdAt: Double
    let updatedAt: Double
    let payload: [String: JSONValue]

    var normalizedMode: String {
        mode.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
    }

    var displayName: String {
        name.trimmingCharacters(in: .whitespacesAndNewlines).nonEmptyValue ?? "Untitled template"
    }

    var isBookNarrationTemplate: Bool {
        normalizedMode == "generated_book" || normalizedMode == "narrate_ebook"
    }
}

struct CreationTemplateSaveRequest: Encodable, Equatable {
    let id: String?
    let name: String
    let mode: String
    let payload: [String: JSONValue]
}

struct PipelineIntakeStatusResponse: Decodable, Equatable {
    let acceptingJobs: Bool
    let isUnderPressure: Bool
    let queueDepth: Int
    let activeCount: Int
    let softLimit: Int?
    let hardLimit: Int?
    let delayCount: Int
}

struct ImageNodeAvailabilityRequest: Encodable, Equatable {
    let baseUrls: [String]

    enum CodingKeys: String, CodingKey {
        case baseUrls = "base_urls"
    }
}

struct ImageNodeAvailabilityEntry: Decodable, Equatable {
    let baseUrl: String
    let available: Bool
}

struct ImageNodeAvailabilityResponse: Decodable, Equatable {
    let nodes: [ImageNodeAvailabilityEntry]
    let available: [String]
    let unavailable: [String]
}

struct PipelineFileEntry: Decodable, Equatable {
    let name: String
    let path: String
    let type: String?
    let sizeBytes: Int?
    let modifiedAt: String?

    init(
        name: String,
        path: String,
        type: String? = "file",
        sizeBytes: Int? = nil,
        modifiedAt: String? = nil
    ) {
        self.name = name
        self.path = path
        self.type = type
        self.sizeBytes = sizeBytes
        self.modifiedAt = modifiedAt
    }
}

struct PipelineFileBrowserResponse: Decodable, Equatable {
    let ebooks: [PipelineFileEntry]
    let outputs: [PipelineFileEntry]
    let booksRoot: String
    let outputRoot: String
}

struct AcquisitionSubtitleHint: Decodable, Equatable {
    let path: String
    let filename: String
    let language: String?
    let format: String?
}

struct AcquisitionProviderEntry: Decodable, Equatable, Identifiable {
    let id: String
    let label: String
    let mediaKinds: [String]
    let capabilities: [String]
    let status: String
    let configured: Bool
    let available: Bool
    let rights: [String]
    let discoveryMediaKinds: [String]?
    let sourcePath: String?
    let policyNotes: [String]
    let nextActions: [String]
}

struct AcquisitionProviderListResponse: Decodable, Equatable {
    let providers: [AcquisitionProviderEntry]
    let policyNotes: [String]
    let paths: [String: String]
    let defaultProviderIds: [String: [String]]?
}

struct AcquisitionCandidate: Decodable, Equatable, Identifiable {
    let candidateId: String
    let provider: String
    let mediaKind: String
    let title: String
    let rights: String
    let capabilities: [String]
    let candidateToken: String
    let subtitle: String?
    let contributors: [String]
    let language: String?
    let year: Int?
    let publishedAt: String?
    let sourceUrl: String?
    let thumbnailUrl: String?
    let coverUrl: String?
    let localPath: String?
    let sizeBytes: Int?
    let modifiedAt: String?
    let durationSeconds: Int?
    let subtitles: [AcquisitionSubtitleHint]
    let metadata: [String: JSONValue]?
    let requiresConfirmation: Bool
    let policyNotes: [String]

    var id: String { candidateId }
}

struct AcquisitionDiscoveryResponse: Decodable, Equatable {
    let candidates: [AcquisitionCandidate]
    let policyNotes: [String]
    let providersQueried: [String]
}

struct AcquisitionAcquireRequest: Encodable, Equatable {
    let candidateToken: String
    let confirmed: Bool
    let filename: String?

    enum CodingKeys: String, CodingKey {
        case candidateToken = "candidate_token"
        case confirmed
        case filename
    }
}

struct AcquisitionJobCreateRequest: Encodable, Equatable {
    let provider: String
    let sourceURI: String?
    let candidateToken: String?
    let confirmed: Bool
    let destination: String?

    init(
        provider: String,
        sourceURI: String?,
        candidateToken: String? = nil,
        confirmed: Bool,
        destination: String?
    ) {
        self.provider = provider
        self.sourceURI = sourceURI
        self.candidateToken = candidateToken
        self.confirmed = confirmed
        self.destination = destination
    }

    enum CodingKeys: String, CodingKey {
        case provider
        case sourceURI = "source_uri"
        case candidateToken = "candidate_token"
        case confirmed
        case destination
    }
}

struct AcquisitionArtifactResponse: Decodable, Equatable {
    let provider: String
    let mediaKind: String
    let status: String
    let artifactId: String
    let artifactPath: String
    let localPath: String
    let filename: String
    let sizeBytes: Int
    let modifiedAt: String?
    let nextActions: [String]
    let metadata: [String: JSONValue]?
}

struct AcquisitionPreparedArtifactResponse: Decodable, Equatable {
    let provider: String
    let mediaKind: String
    let sourceKind: String
    let localPath: String
    let inputFile: String?
    let videoPath: String?
    let subtitlePath: String?
    let subtitles: [AcquisitionSubtitleHint]
    let nextActions: [String]
    let metadata: [String: JSONValue]?
}

struct AcquisitionJobStatusResponse: Decodable, Equatable {
    let provider: String
    let taskId: String
    let status: String
    let progress: Double?
    let message: String?
    let externalTaskId: String?
    let rawStatus: String?
    let startedAt: String?
    let updatedAt: String
    let completedFiles: [String]
    let nextActions: [String]
}

struct PipelineFileDeleteRequest: Encodable, Equatable {
    let path: String
}

struct BookContentIndexResponse: Decodable, Equatable {
    let inputFile: String
    let contentIndex: JSONValue?
}

struct SubtitleSourceEntry: Decodable, Equatable {
    let name: String
    let path: String
    let format: String
    let language: String?
    let modifiedAt: String?
}

struct SubtitleSourceListResponse: Decodable, Equatable {
    let sources: [SubtitleSourceEntry]
}

struct SubtitleSourceDeleteRequest: Encodable, Equatable {
    let subtitlePath: String
    let baseDir: String?

    enum CodingKeys: String, CodingKey {
        case subtitlePath = "subtitle_path"
        case baseDir = "base_dir"
    }
}

struct SubtitleSourceDeleteResponse: Decodable, Equatable {
    let subtitlePath: String
    let baseDir: String?
    let removed: [String]
    let missing: [String]
}

struct YoutubeNasSubtitleEntry: Decodable, Equatable {
    let path: String
    let filename: String
    let language: String?
    let format: String
}

struct YoutubeNasVideoEntry: Decodable, Equatable {
    let path: String
    let filename: String
    let folder: String
    let sizeBytes: Int
    let modifiedAt: String
    let source: String?
    let linkedJobIds: [String]
    let subtitles: [YoutubeNasSubtitleEntry]
}

struct YoutubeNasLibraryResponse: Decodable, Equatable {
    let baseDir: String
    let videos: [YoutubeNasVideoEntry]
}

struct YoutubeInlineSubtitleStream: Decodable, Equatable, Identifiable {
    let index: Int
    let position: Int
    let language: String?
    let codec: String?
    let title: String?
    let canExtract: Bool

    var id: Int { index }
}

struct YoutubeInlineSubtitleListResponse: Decodable, Equatable {
    let videoPath: String
    let streams: [YoutubeInlineSubtitleStream]
}

struct YoutubeSubtitleExtractionRequestPayload: Encodable, Equatable {
    let videoPath: String
    let languages: [String]?

    enum CodingKeys: String, CodingKey {
        case videoPath = "video_path"
        case languages
    }
}

struct YoutubeSubtitleExtractionResponse: Decodable, Equatable {
    let videoPath: String
    let extracted: [YoutubeNasSubtitleEntry]
}

struct BookCreationSentenceBounds: Decodable, Equatable {
    let min: Int
    let max: Int
    let `default`: Int
}

struct BookCreationDefaults: Decodable, Equatable {
    let topic: String
    let bookName: String
    let genre: String
    let author: String
    let inputLanguage: String
    let outputLanguage: String
    let targetLanguages: [String]?
    let outputLanguages: [String]?
    let voice: String
}

struct BookCreationPipelineDefaults: Decodable, Equatable {
    let sentencesPerOutputFile: Int
    let stitchFull: Bool
    let audioMode: String
    let audioBitrateKbps: Int?
    let writtenMode: String
    let selectedVoice: String
    let generateAudio: Bool
    let outputHtml: Bool
    let outputPdf: Bool
    let includeTransliteration: Bool
    let translationProvider: String
    let translationBatchSize: Int
    let transliterationMode: String
    let sentenceSplitterMode: String?
    let enableLookupCache: Bool
    let lookupCacheBatchSize: Int
    let tempo: Double
}

struct BookCreationGeneratedSourceDefaults: Decodable, Equatable {
    let addImages: Bool
    let imagePromptPipeline: String
    let imageStyleTemplate: String
    let imagePromptContextSentences: Int
    let imageWidth: String
    let imageHeight: String
}

struct BookCreationSubtitleDefaults: Decodable, Equatable {
    let workerCount: Int
    let batchSize: Int
    let translationBatchSize: Int
    let assFontSize: Int
    let assEmphasisScale: Double
}

struct BookCreationYoutubeDubDefaults: Decodable, Equatable {
    let originalMixPercent: Double
    let flushSentences: Int
    let translationBatchSize: Int
    let splitBatches: Bool
    let stitchBatches: Bool
    let targetHeight: Int
    let preserveAspectRatio: Bool
}

struct BookCreationOptionsResponse: Decodable, Equatable {
    let sentenceBounds: BookCreationSentenceBounds
    let defaults: BookCreationDefaults
    let pipelineDefaults: BookCreationPipelineDefaults
    let generatedSourceDefaults: BookCreationGeneratedSourceDefaults
    let subtitleDefaults: BookCreationSubtitleDefaults?
    let youtubeDubDefaults: BookCreationYoutubeDubDefaults?
    let supportedInputLanguages: [String]
    let supportedOutputLanguages: [String]
    let supportedVoices: [String]
}

struct AppleBookCreateVoiceOption: Hashable, Identifiable {
    let value: String

    var id: String { value }
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

    static let gtts = AppleBookCreateVoiceOption("gTTS")!

    static let fallbackOptions: [AppleBookCreateVoiceOption] = [
        "gTTS",
        "macOS-auto",
        "macOS-auto-male",
        "macOS-auto-female",
        "piper-auto",
        "macOS",
        "edge-tts",
    ].compactMap { AppleBookCreateVoiceOption($0) }

    static func options(
        from supportedValues: [String],
        selected: AppleBookCreateVoiceOption?
    ) -> [AppleBookCreateVoiceOption] {
        var seen = Set<String>()
        var options = supportedValues.compactMap { AppleBookCreateVoiceOption($0) }.filter { option in
            seen.insert(option.value.lowercased()).inserted
        }

        if options.isEmpty {
            options = fallbackOptions
            seen = Set(options.map { $0.value.lowercased() })
        }

        if let selected, !seen.contains(selected.value.lowercased()) {
            options.insert(selected, at: 0)
        }

        return options
    }

    private static func displayLabel(for value: String) -> String {
        if value.contains(" - ") {
            return String(value.split(separator: " - ").first ?? Substring(value))
        }
        if value.hasPrefix("gTTS-") {
            return "gTTS (\(value.dropFirst(5)))"
        }
        switch value {
        case "gTTS":
            return "gTTS"
        case "macOS":
            return "macOS"
        case "macOS-auto":
            return "macOS Auto"
        case "macOS-auto-male":
            return "macOS Auto Male"
        case "macOS-auto-female":
            return "macOS Auto Female"
        case "piper-auto":
            return "Piper Auto"
        case "edge-tts":
            return "Edge TTS"
        default:
            return value
        }
    }
}

struct BookGenerationRequest: Encodable, Equatable {
    let topic: String
    let bookName: String
    let genre: String
    let author: String
    let numSentences: Int
    let inputLanguage: String?
    let outputLanguage: String?
    let voice: String?
    let sourceBookTitle: String?
    let sourceBookAuthor: String?
    let sourceBookGenre: String?
    let sourceBookSummary: String?

    init(
        topic: String,
        bookName: String,
        genre: String,
        author: String = "Me",
        numSentences: Int = 10,
        inputLanguage: String? = nil,
        outputLanguage: String? = nil,
        voice: String? = nil,
        sourceBookTitle: String? = nil,
        sourceBookAuthor: String? = nil,
        sourceBookGenre: String? = nil,
        sourceBookSummary: String? = nil
    ) {
        self.topic = topic
        self.bookName = bookName
        self.genre = genre
        self.author = author
        self.numSentences = numSentences
        self.inputLanguage = inputLanguage
        self.outputLanguage = outputLanguage
        self.voice = voice
        self.sourceBookTitle = sourceBookTitle
        self.sourceBookAuthor = sourceBookAuthor
        self.sourceBookGenre = sourceBookGenre
        self.sourceBookSummary = sourceBookSummary
    }

    enum CodingKeys: String, CodingKey {
        case topic
        case bookName = "book_name"
        case genre
        case author
        case numSentences = "num_sentences"
        case inputLanguage = "input_language"
        case outputLanguage = "output_language"
        case voice
        case sourceBookTitle = "source_book_title"
        case sourceBookAuthor = "source_book_author"
        case sourceBookGenre = "source_book_genre"
        case sourceBookSummary = "source_book_summary"
    }
}

struct BookGenerationJobSubmission: Encodable, Equatable {
    let generator: BookGenerationRequest
    let pipeline: PipelineRequestPayload
}

struct SubtitleJobFormPayload: Equatable {
    let inputLanguage: String
    let targetLanguage: String
    let sourcePath: String?
    let originalLanguage: String?
    let llmModel: String?
    let translationProvider: String?
    let transliterationMode: String?
    let transliterationModel: String?
    let enableTransliteration: Bool
    let highlight: Bool
    let showOriginal: Bool
    let generateAudioBook: Bool
    let batchSize: Int?
    let translationBatchSize: Int?
    let workerCount: Int?
    let startTime: String
    let endTime: String?
    let assFontSize: Int?
    let assEmphasisScale: Double?
    let mediaMetadataJSON: String?
    let cleanupSource: Bool
    let mirrorBatchesToSourceDir: Bool
    let outputFormat: String

    init(
        inputLanguage: String,
        targetLanguage: String,
        sourcePath: String? = nil,
        originalLanguage: String? = nil,
        llmModel: String? = nil,
        translationProvider: String? = nil,
        transliterationMode: String? = nil,
        transliterationModel: String? = nil,
        enableTransliteration: Bool = false,
        highlight: Bool = true,
        showOriginal: Bool = true,
        generateAudioBook: Bool = true,
        batchSize: Int? = nil,
        translationBatchSize: Int? = nil,
        workerCount: Int? = nil,
        startTime: String = "00:00",
        endTime: String? = nil,
        assFontSize: Int? = nil,
        assEmphasisScale: Double? = nil,
        mediaMetadataJSON: String? = nil,
        cleanupSource: Bool = false,
        mirrorBatchesToSourceDir: Bool = true,
        outputFormat: String = "srt"
    ) {
        self.inputLanguage = inputLanguage
        self.targetLanguage = targetLanguage
        self.sourcePath = sourcePath
        self.originalLanguage = originalLanguage
        self.llmModel = llmModel
        self.translationProvider = translationProvider
        self.transliterationMode = transliterationMode
        self.transliterationModel = transliterationModel
        self.enableTransliteration = enableTransliteration
        self.highlight = highlight
        self.showOriginal = showOriginal
        self.generateAudioBook = generateAudioBook
        self.batchSize = batchSize
        self.translationBatchSize = translationBatchSize
        self.workerCount = workerCount
        self.startTime = startTime
        self.endTime = endTime
        self.assFontSize = assFontSize
        self.assEmphasisScale = assEmphasisScale
        self.mediaMetadataJSON = mediaMetadataJSON
        self.cleanupSource = cleanupSource
        self.mirrorBatchesToSourceDir = mirrorBatchesToSourceDir
        self.outputFormat = outputFormat
    }

    var multipartFields: [String: String] {
        var fields: [String: String] = [
            "input_language": inputLanguage,
            "target_language": targetLanguage,
            "enable_transliteration": Self.formBool(enableTransliteration),
            "highlight": Self.formBool(highlight),
            "show_original": Self.formBool(showOriginal),
            "generate_audio_book": Self.formBool(generateAudioBook),
            "start_time": startTime,
            "cleanup_source": Self.formBool(cleanupSource),
            "mirror_batches_to_source_dir": Self.formBool(mirrorBatchesToSourceDir),
            "output_format": outputFormat,
        ]

        Self.add(sourcePath, named: "source_path", to: &fields)
        Self.add(originalLanguage, named: "original_language", to: &fields)
        Self.add(llmModel, named: "llm_model", to: &fields)
        Self.add(translationProvider, named: "translation_provider", to: &fields)
        Self.add(transliterationMode, named: "transliteration_mode", to: &fields)
        Self.add(transliterationModel, named: "transliteration_model", to: &fields)
        Self.add(endTime, named: "end_time", to: &fields)
        Self.add(assFontSize.map(String.init), named: "ass_font_size", to: &fields)
        Self.add(assEmphasisScale.map { Self.formDecimal($0) }, named: "ass_emphasis_scale", to: &fields)
        Self.add(mediaMetadataJSON, named: "media_metadata_json", to: &fields)
        Self.add(batchSize.map(String.init), named: "batch_size", to: &fields)
        Self.add(translationBatchSize.map(String.init), named: "translation_batch_size", to: &fields)
        Self.add(workerCount.map(String.init), named: "worker_count", to: &fields)
        return fields
    }

    private static func add(_ value: String?, named name: String, to fields: inout [String: String]) {
        guard let value = value?.trimmingCharacters(in: .whitespacesAndNewlines), !value.isEmpty else {
            return
        }
        fields[name] = value
    }

    private static func formBool(_ value: Bool) -> String {
        value ? "true" : "false"
    }

    private static func formDecimal(_ value: Double) -> String {
        let rounded = (value * 100).rounded() / 100
        if rounded.rounded() == rounded {
            return String(Int(rounded))
        }
        return String(format: "%.2f", rounded)
    }
}

struct YoutubeDubRequestPayload: Encodable, Equatable {
    let videoPath: String
    let subtitlePath: String
    let mediaMetadata: [String: JSONValue]?
    let sourceLanguage: String?
    let targetLanguage: String?
    let voice: String?
    let tempo: Double?
    let macosReadingSpeed: Int?
    let outputDir: String?
    let startTimeOffset: String?
    let endTimeOffset: String?
    let originalMixPercent: Double?
    let flushSentences: Int?
    let llmModel: String?
    let translationProvider: String?
    let translationBatchSize: Int?
    let transliterationMode: String?
    let transliterationModel: String?
    let splitBatches: Bool?
    let stitchBatches: Bool?
    let includeTransliteration: Bool?
    let targetHeight: Int?
    let preserveAspectRatio: Bool?
    let enableLookupCache: Bool?

    init(
        videoPath: String,
        subtitlePath: String,
        mediaMetadata: [String: JSONValue]? = nil,
        sourceLanguage: String? = nil,
        targetLanguage: String? = nil,
        voice: String? = nil,
        tempo: Double? = nil,
        macosReadingSpeed: Int? = nil,
        outputDir: String? = nil,
        startTimeOffset: String? = nil,
        endTimeOffset: String? = nil,
        originalMixPercent: Double? = nil,
        flushSentences: Int? = nil,
        llmModel: String? = nil,
        translationProvider: String? = nil,
        translationBatchSize: Int? = nil,
        transliterationMode: String? = nil,
        transliterationModel: String? = nil,
        splitBatches: Bool? = nil,
        stitchBatches: Bool? = nil,
        includeTransliteration: Bool? = nil,
        targetHeight: Int? = nil,
        preserveAspectRatio: Bool? = nil,
        enableLookupCache: Bool? = nil
    ) {
        self.videoPath = videoPath
        self.subtitlePath = subtitlePath
        self.mediaMetadata = mediaMetadata
        self.sourceLanguage = sourceLanguage
        self.targetLanguage = targetLanguage
        self.voice = voice
        self.tempo = tempo
        self.macosReadingSpeed = macosReadingSpeed
        self.outputDir = outputDir
        self.startTimeOffset = startTimeOffset
        self.endTimeOffset = endTimeOffset
        self.originalMixPercent = originalMixPercent
        self.flushSentences = flushSentences
        self.llmModel = llmModel
        self.translationProvider = translationProvider
        self.translationBatchSize = translationBatchSize
        self.transliterationMode = transliterationMode
        self.transliterationModel = transliterationModel
        self.splitBatches = splitBatches
        self.stitchBatches = stitchBatches
        self.includeTransliteration = includeTransliteration
        self.targetHeight = targetHeight
        self.preserveAspectRatio = preserveAspectRatio
        self.enableLookupCache = enableLookupCache
    }

    enum CodingKeys: String, CodingKey {
        case videoPath = "video_path"
        case subtitlePath = "subtitle_path"
        case mediaMetadata = "media_metadata"
        case sourceLanguage = "source_language"
        case targetLanguage = "target_language"
        case voice
        case tempo
        case macosReadingSpeed = "macos_reading_speed"
        case outputDir = "output_dir"
        case startTimeOffset = "start_time_offset"
        case endTimeOffset = "end_time_offset"
        case originalMixPercent = "original_mix_percent"
        case flushSentences = "flush_sentences"
        case llmModel = "llm_model"
        case translationProvider = "translation_provider"
        case translationBatchSize = "translation_batch_size"
        case transliterationMode = "transliteration_mode"
        case transliterationModel = "transliteration_model"
        case splitBatches = "split_batches"
        case stitchBatches = "stitch_batches"
        case includeTransliteration = "include_transliteration"
        case targetHeight = "target_height"
        case preserveAspectRatio = "preserve_aspect_ratio"
        case enableLookupCache = "enable_lookup_cache"
    }
}
