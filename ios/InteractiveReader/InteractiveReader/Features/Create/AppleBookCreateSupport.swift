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
    let enableLookupCache: Bool?
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
    let sentenceCount: Int?
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
}

enum AppleCreateMode: String, CaseIterable, Identifiable {
    case generatedBook
    case narrateEbook
    case subtitleJob
    case youtubeDub

    var id: String { rawValue }

    var label: String {
        switch self {
        case .generatedBook:
            return "Generate"
        case .narrateEbook:
            return "Narrate EPUB"
        case .subtitleJob:
            return "Subtitles"
        case .youtubeDub:
            return "YouTube Dub"
        }
    }
}

struct AppleCreateTargetLanguageDefaults: Equatable {
    let primary: AppleBookCreateLanguage?
    let additionalTargets: String
}

struct AppleCreateLanguagePreferences: Codable, Equatable {
    let inputLanguage: String?
    let targetLanguages: [String]
    let enableLookupCache: Bool?
}

struct AppleCreateResolvedLanguagePreferences: Equatable {
    let inputLanguage: AppleBookCreateLanguage?
    let targetLanguage: AppleBookCreateLanguage?
    let additionalTargetLanguages: String?
    let enableLookupCache: Bool?
}

struct AppleCreateSubmitPresentation: Equatable {
    let title: String
    let systemImage: String
}

struct AppleCreateIntakePresentation: Equatable {
    let label: String
    let detailLines: [String]
}

struct AppleCreateSubmitState: Equatable {
    let hasConfiguration: Bool
    let mode: AppleCreateMode
    let topic: String
    let bookName: String
    let genre: String
    let hasNarrateLocalFile: Bool
    let sourcePath: String
    let sourceBaseOutput: String
    let hasSubtitleLocalFile: Bool
    let subtitleSourcePath: String
    let youtubeVideoPath: String
    let youtubeSubtitlePath: String
}

enum AppleBookCreatePresentation {
    private static let preferredSampleEbookName = "test-agatha-poirot-30sentences.epub"
    private static let subtitleJobSourceFormats: Set<String> = ["srt", "vtt"]
    private static let youtubePlayableSubtitleFormats: Set<String> = ["ass", "srt", "vtt", "sub"]

    static func availableCreateModes(isTV: Bool) -> [AppleCreateMode] {
        isTV ? [.generatedBook] : AppleCreateMode.allCases
    }

    static func preferredPipelineEbook(from files: PipelineFileBrowserResponse?) -> PipelineFileEntry? {
        guard let ebooks = files?.ebooks.filter({ $0.type == "file" }), !ebooks.isEmpty else {
            return nil
        }
        return ebooks.first { entry in
            trimmed(entry.name).lowercased() == preferredSampleEbookName
        } ?? ebooks[0]
    }

    static func subtitleJobSources(from response: SubtitleSourceListResponse?) -> [SubtitleSourceEntry] {
        response?.sources.filter { subtitleJobSourceFormats.contains(trimmed($0.format).lowercased()) } ?? []
    }

    static func preferredSubtitleSource(from response: SubtitleSourceListResponse?) -> SubtitleSourceEntry? {
        subtitleJobSources(from: response).sorted { left, right in
            let leftDate = parseSubtitleSourceDate(left.modifiedAt)
            let rightDate = parseSubtitleSourceDate(right.modifiedAt)
            if leftDate != rightDate {
                return leftDate > rightDate
            }
            return left.path.localizedStandardCompare(right.path) == .orderedAscending
        }.first
    }

    static func playableYoutubeSubtitles(for video: YoutubeNasVideoEntry?) -> [YoutubeNasSubtitleEntry] {
        video?.subtitles.filter { youtubePlayableSubtitleFormats.contains(trimmed($0.format).lowercased()) } ?? []
    }

    static func preferredYoutubeSubtitle(for video: YoutubeNasVideoEntry?) -> YoutubeNasSubtitleEntry? {
        let candidates = playableYoutubeSubtitles(for: video)
        guard !candidates.isEmpty else {
            return nil
        }
        return candidates.first { subtitle in
            trimmed(subtitle.language ?? "").lowercased().hasPrefix("en")
        } ?? candidates[0]
    }

    static func preferredYoutubeSelection(from library: YoutubeNasLibraryResponse?) -> AppleYoutubeSourceSelection? {
        guard let videos = library?.videos, !videos.isEmpty else {
            return nil
        }
        let video = videos.first { !playableYoutubeSubtitles(for: $0).isEmpty } ?? videos[0]
        return AppleYoutubeSourceSelection(video: video, subtitle: preferredYoutubeSubtitle(for: video))
    }

    static func youtubeSelection(
        from library: YoutubeNasLibraryResponse?,
        storedVideoPath: String?,
        storedSubtitlePath: String?
    ) -> AppleYoutubeSourceSelection? {
        guard let videos = library?.videos, !videos.isEmpty else {
            return nil
        }

        let requestedVideoPath = storedVideoPath?.nonEmptyValue
        let selectedVideo = videos.first { $0.path == requestedVideoPath }
            ?? preferredYoutubeSelection(from: library)?.video
            ?? videos[0]
        let subtitleCandidates = playableYoutubeSubtitles(for: selectedVideo)
        let requestedSubtitlePath = storedSubtitlePath?.nonEmptyValue
        let storedSubtitle = requestedVideoPath == selectedVideo.path
            ? subtitleCandidates.first { $0.path == requestedSubtitlePath }
            : nil
        let subtitle = storedSubtitle ?? preferredYoutubeSubtitle(for: selectedVideo)

        return AppleYoutubeSourceSelection(video: selectedVideo, subtitle: subtitle)
    }

    static func youtubeSubtitleLanguage(
        from library: YoutubeNasLibraryResponse?,
        videoPath: String,
        subtitlePath: String
    ) -> String? {
        let normalizedVideoPath = trimmed(videoPath)
        let normalizedSubtitlePath = trimmed(subtitlePath)
        guard !normalizedVideoPath.isEmpty, !normalizedSubtitlePath.isEmpty else {
            return nil
        }
        guard let video = library?.videos.first(where: { $0.path == normalizedVideoPath }) else {
            return nil
        }
        return playableYoutubeSubtitles(for: video)
            .first { $0.path == normalizedSubtitlePath }?
            .language?
            .nonEmptyValue
    }

    static func youtubeLibraryCacheKey(baseKey: String, baseDir: String) -> String {
        let normalizedBaseDir = trimmed(baseDir)
        guard !normalizedBaseDir.isEmpty else {
            return baseKey
        }
        return "\(baseKey)|youtubeBaseDir=\(normalizedBaseDir)"
    }

    static func subtitleShowOriginalPreferenceKey(baseKey: String) -> String {
        "ebookTools.appleCreate.subtitles.showOriginal.\(baseKey)"
    }

    static func narrationHistoryDefaults(
        from jobs: [PipelineStatusResponse],
        currentInputFile: String
    ) -> AppleNarrationHistoryDefaults? {
        guard !jobs.isEmpty else { return nil }
        let latest = latestNarrationJob(from: jobs)
        let inputFile = latest.flatMap { narrationString($0, keys: ["input_file", "inputFile"]) }
        let baseOutput = latest.flatMap { narrationString($0, keys: ["base_output_file", "baseOutputFile"]) }
        let startInput = trimmed(inputFile ?? currentInputFile)
        let startSentence = narrationStartSentence(inputFile: startInput, from: jobs)

        let inputLanguage = latest
            .flatMap { narrationString($0, keys: ["input_language", "inputLanguage", "source_language", "sourceLanguage"]) }
            .flatMap(AppleBookCreateLanguage.init(backendValue:))
        let targetLanguages = latest
            .flatMap { narrationStringArray($0, keys: ["target_languages", "targetLanguages"]) } ?? []
        let normalizedTargets = normalizedLanguageList(targetLanguages)
        let targetLanguage = normalizedTargets.first.flatMap(AppleBookCreateLanguage.init(backendValue:))
        let additionalTargetLanguages = normalizedTargets.dropFirst().joined(separator: ", ")
        let lookupCache = latest.flatMap { narrationBool($0, keys: ["enable_lookup_cache", "enableLookupCache"]) }

        guard inputFile != nil
            || baseOutput != nil
            || startSentence != nil
            || inputLanguage != nil
            || targetLanguage != nil
            || !additionalTargetLanguages.isEmpty
            || lookupCache != nil
        else {
            return nil
        }

        return AppleNarrationHistoryDefaults(
            inputFile: inputFile,
            baseOutput: baseOutput,
            startSentence: startSentence,
            inputLanguage: inputLanguage,
            targetLanguage: targetLanguage,
            additionalTargetLanguages: additionalTargetLanguages.isEmpty ? nil : additionalTargetLanguages,
            enableLookupCache: lookupCache
        )
    }

    static func generatedBookHistoryDefaults(from jobs: [PipelineStatusResponse]) -> AppleGeneratedBookHistoryDefaults? {
        guard let latest = latestGeneratedBookJob(from: jobs),
              let parameters = latest.parameters?.objectValue
        else {
            return nil
        }
        let sources = generatedBookParameterSources(parameters)
        let targetLanguages = historyStringArray(in: sources, keys: ["target_languages", "targetLanguages"]) ?? []
        let normalizedTargets = normalizedLanguageList(targetLanguages)
        let targetLanguage = (normalizedTargets.first
            ?? historyString(in: sources, keys: ["output_language", "outputLanguage", "target_language", "targetLanguage"]))
            .flatMap(AppleBookCreateLanguage.init(backendValue:))
        let additionalTargetLanguages = normalizedTargets.dropFirst().joined(separator: ", ")
        let sentenceCount = historyInt(in: sources, keys: ["num_sentences", "numSentences", "sentence_count", "sentenceCount"])
            .map { max(1, $0) }

        let defaults = AppleGeneratedBookHistoryDefaults(
            topic: historyString(in: sources, keys: ["topic", "book_topic", "bookTopic"]),
            bookName: historyString(in: sources, keys: ["book_name", "bookName", "book_title", "bookTitle"]),
            genre: historyString(in: sources, keys: ["genre", "book_genre", "bookGenre"]),
            author: historyString(in: sources, keys: ["author", "book_author", "bookAuthor"]),
            sentenceCount: sentenceCount,
            inputLanguage: historyString(in: sources, keys: ["input_language", "inputLanguage", "source_language", "sourceLanguage"])
                .flatMap(AppleBookCreateLanguage.init(backendValue:)),
            targetLanguage: targetLanguage,
            additionalTargetLanguages: additionalTargetLanguages.isEmpty ? nil : additionalTargetLanguages,
            voice: historyString(in: sources, keys: ["voice", "selected_voice", "selectedVoice"])
                .flatMap(AppleBookCreateVoiceOption.init(backendValue:)),
            generateAudio: historyBool(in: sources, keys: ["generate_audio", "generateAudio"]),
            audioMode: historyString(in: sources, keys: ["audio_mode", "audioMode"]),
            audioBitrateKbps: historyInt(in: sources, keys: ["audio_bitrate_kbps", "audioBitrateKbps"])
                .map { "\(max(32, $0))" },
            writtenMode: historyString(in: sources, keys: ["written_mode", "writtenMode"]),
            tempo: historyDouble(in: sources, keys: ["tempo"])
                .map(clampTempo),
            bookSentencesPerOutputFile: historyInt(in: sources, keys: ["sentences_per_output_file", "sentencesPerOutputFile"])
                .map(clampBookSentencesPerOutputFile),
            stitchFull: historyBool(in: sources, keys: ["stitch_full", "stitchFull"]),
            includeTransliteration: historyBool(in: sources, keys: ["include_transliteration", "includeTransliteration"]),
            bookTranslationProvider: historyString(in: sources, keys: ["translation_provider", "translationProvider"])
                .flatMap(AppleSubtitleTranslationProvider.init(backendValue:)),
            bookLlmModel: historyString(in: sources, keys: ["llm_model", "llmModel"]),
            bookTranslationBatchSize: historyInt(in: sources, keys: ["translation_batch_size", "translationBatchSize"])
                .map(clampSubtitleTranslationBatchSize),
            bookTransliterationMode: historyString(in: sources, keys: ["transliteration_mode", "transliterationMode"])
                .flatMap(AppleSubtitleTransliterationMode.init(backendValue:)),
            bookTransliterationModel: historyString(in: sources, keys: ["transliteration_model", "transliterationModel"]),
            enableLookupCache: historyBool(in: sources, keys: ["enable_lookup_cache", "enableLookupCache"]),
            bookLookupCacheBatchSize: historyInt(in: sources, keys: ["lookup_cache_batch_size", "lookupCacheBatchSize"])
                .map(clampSubtitleTranslationBatchSize),
            outputHtml: historyBool(in: sources, keys: ["output_html", "outputHtml"]),
            outputPdf: historyBool(in: sources, keys: ["output_pdf", "outputPdf"]),
            includeImages: historyBool(in: sources, keys: ["add_images", "addImages"]),
            imagePromptPipeline: historyString(in: sources, keys: ["image_prompt_pipeline", "imagePromptPipeline"])
                .flatMap(AppleGeneratedBookImagePromptPipeline.init(backendValue:)),
            imageStyleTemplate: historyString(in: sources, keys: ["image_style_template", "imageStyleTemplate"])
                .flatMap(AppleGeneratedBookImageStyleTemplate.init(backendValue:)),
            imagePromptContextSentences: historyInt(in: sources, keys: ["image_prompt_context_sentences", "imagePromptContextSentences"])
                .map(clampImagePromptContextSentences),
            imageWidth: historyString(in: sources, keys: ["image_width", "imageWidth"])
                .map(normalizedImageDimension),
            imageHeight: historyString(in: sources, keys: ["image_height", "imageHeight"])
                .map(normalizedImageDimension)
        )

        guard defaults.topic != nil
            || defaults.bookName != nil
            || defaults.genre != nil
            || defaults.author != nil
            || defaults.sentenceCount != nil
            || defaults.inputLanguage != nil
            || defaults.targetLanguage != nil
            || defaults.additionalTargetLanguages != nil
            || defaults.voice != nil
            || defaults.generateAudio != nil
            || defaults.audioMode != nil
            || defaults.audioBitrateKbps != nil
            || defaults.writtenMode != nil
            || defaults.tempo != nil
            || defaults.bookSentencesPerOutputFile != nil
            || defaults.stitchFull != nil
            || defaults.includeTransliteration != nil
            || defaults.bookTranslationProvider != nil
            || defaults.bookLlmModel != nil
            || defaults.bookTranslationBatchSize != nil
            || defaults.bookTransliterationMode != nil
            || defaults.bookTransliterationModel != nil
            || defaults.enableLookupCache != nil
            || defaults.bookLookupCacheBatchSize != nil
            || defaults.outputHtml != nil
            || defaults.outputPdf != nil
            || defaults.includeImages != nil
            || defaults.imagePromptPipeline != nil
            || defaults.imageStyleTemplate != nil
            || defaults.imagePromptContextSentences != nil
            || defaults.imageWidth != nil
            || defaults.imageHeight != nil
        else {
            return nil
        }

        return defaults
    }

    static func subtitleHistoryDefaults(from jobs: [PipelineStatusResponse]) -> AppleSubtitleHistoryDefaults? {
        guard let latest = latestSubtitleJob(from: jobs) else { return nil }

        let sourcePath = narrationString(latest, keys: ["subtitle_path", "subtitlePath", "input_file", "inputFile"])
        let inputLanguage = narrationString(latest, keys: ["input_language", "inputLanguage", "source_language", "sourceLanguage"])
            .flatMap(AppleBookCreateLanguage.init(backendValue:))
        let targetLanguage = (narrationStringArray(latest, keys: ["target_languages", "targetLanguages"])?.first
            ?? narrationString(latest, keys: ["target_language", "targetLanguage"]))
            .flatMap(AppleBookCreateLanguage.init(backendValue:))
        let startTime = historyOffset(
            latest,
            stringKeys: ["start_time", "startTime", "start_time_offset", "startTimeOffset"],
            secondsKeys: ["start_time_offset_seconds", "startTimeOffsetSeconds"],
            allowRelative: false
        )
        let endTime = historyOffset(
            latest,
            stringKeys: ["end_time", "endTime", "end_time_offset", "endTimeOffset"],
            secondsKeys: ["end_time_offset_seconds", "endTimeOffsetSeconds"],
            allowRelative: true
        )
        let enableTransliteration = narrationBool(latest, keys: ["enable_transliteration", "enableTransliteration"])
        let showOriginal = narrationBool(latest, keys: ["show_original", "showOriginal"])
        let translationProvider = narrationString(latest, keys: ["translation_provider", "translationProvider"])
            .flatMap(AppleSubtitleTranslationProvider.init(backendValue:))
        let llmModel = narrationString(latest, keys: ["llm_model", "llmModel", "selected_model", "selectedModel"])
        let transliterationMode = narrationString(latest, keys: ["transliteration_mode", "transliterationMode"])
            .flatMap(AppleSubtitleTransliterationMode.init(backendValue:))
        let transliterationModel = narrationString(latest, keys: ["transliteration_model", "transliterationModel"])
        let workerCount = narrationInt(latest, keys: ["worker_count", "workerCount"])
            .map(clampSubtitleWorkerCount)
        let batchSize = narrationInt(latest, keys: ["batch_size", "batchSize"])
            .map(clampSubtitleBatchSize)
        let translationBatchSize = narrationInt(latest, keys: ["translation_batch_size", "translationBatchSize"])
            .map(clampSubtitleTranslationBatchSize)

        guard sourcePath != nil
            || inputLanguage != nil
            || targetLanguage != nil
            || startTime != nil
            || endTime != nil
            || enableTransliteration != nil
            || showOriginal != nil
            || translationProvider != nil
            || llmModel != nil
            || transliterationMode != nil
            || transliterationModel != nil
            || workerCount != nil
            || batchSize != nil
            || translationBatchSize != nil
        else {
            return nil
        }

        return AppleSubtitleHistoryDefaults(
            sourcePath: sourcePath,
            inputLanguage: inputLanguage,
            targetLanguage: targetLanguage,
            startTime: startTime,
            endTime: endTime,
            enableTransliteration: enableTransliteration,
            showOriginal: showOriginal,
            translationProvider: translationProvider,
            llmModel: llmModel,
            transliterationMode: transliterationMode,
            transliterationModel: transliterationModel,
            workerCount: workerCount,
            batchSize: batchSize,
            translationBatchSize: translationBatchSize
        )
    }

    static func youtubeHistoryDefaults(from jobs: [PipelineStatusResponse]) -> AppleYoutubeHistoryDefaults? {
        guard let latest = latestYoutubeJob(from: jobs) else { return nil }

        let targetLanguage = (narrationStringArray(latest, keys: ["target_languages", "targetLanguages"])?.first
            ?? narrationString(latest, keys: ["target_language", "targetLanguage"]))
            .flatMap(AppleBookCreateLanguage.init(backendValue:))
        let targetHeight = narrationInt(latest, keys: ["target_height", "targetHeight"])
            .flatMap(AppleYoutubeDubTargetHeight.init(rawValue:))

        let defaults = AppleYoutubeHistoryDefaults(
            videoPath: narrationString(latest, keys: ["input_file", "inputFile", "video_path", "videoPath"]),
            subtitlePath: narrationString(latest, keys: ["subtitle_path", "subtitlePath"]),
            targetLanguage: targetLanguage,
            voice: narrationString(latest, keys: ["selected_voice", "selectedVoice", "voice"])
                .flatMap(AppleBookCreateVoiceOption.init(backendValue:)),
            startOffset: historyOffset(
                latest,
                stringKeys: ["start_time_offset", "startTimeOffset", "start_offset", "startOffset"],
                secondsKeys: ["start_time_offset_seconds", "startTimeOffsetSeconds"],
                allowRelative: false
            ),
            endOffset: historyOffset(
                latest,
                stringKeys: ["end_time_offset", "endTimeOffset", "end_offset", "endOffset"],
                secondsKeys: ["end_time_offset_seconds", "endTimeOffsetSeconds"],
                allowRelative: false
            ),
            originalMixPercent: historyDouble(latest, keys: ["original_mix_percent", "originalMixPercent"])
                .map(clampYoutubeOriginalMixPercent),
            flushSentences: narrationInt(latest, keys: ["flush_sentences", "flushSentences"])
                .map(clampYoutubeFlushSentences),
            translationProvider: narrationString(latest, keys: ["translation_provider", "translationProvider"])
                .flatMap(AppleSubtitleTranslationProvider.init(backendValue:)),
            llmModel: narrationString(latest, keys: ["llm_model", "llmModel"]),
            translationBatchSize: narrationInt(latest, keys: ["translation_batch_size", "translationBatchSize"])
                .map(clampSubtitleTranslationBatchSize),
            transliterationMode: narrationString(latest, keys: ["transliteration_mode", "transliterationMode"])
                .flatMap(AppleSubtitleTransliterationMode.init(backendValue:)),
            transliterationModel: narrationString(latest, keys: ["transliteration_model", "transliterationModel"]),
            splitBatches: narrationBool(latest, keys: ["split_batches", "splitBatches"]),
            stitchBatches: narrationBool(latest, keys: ["stitch_batches", "stitchBatches"]),
            includeTransliteration: narrationBool(latest, keys: ["include_transliteration", "includeTransliteration"]),
            targetHeight: targetHeight,
            preserveAspectRatio: narrationBool(latest, keys: ["preserve_aspect_ratio", "preserveAspectRatio"]),
            enableLookupCache: narrationBool(latest, keys: ["enable_lookup_cache", "enableLookupCache"])
        )

        guard defaults.videoPath != nil
            || defaults.subtitlePath != nil
            || defaults.targetLanguage != nil
            || defaults.voice != nil
            || defaults.startOffset != nil
            || defaults.endOffset != nil
            || defaults.originalMixPercent != nil
            || defaults.flushSentences != nil
            || defaults.translationProvider != nil
            || defaults.llmModel != nil
            || defaults.translationBatchSize != nil
            || defaults.transliterationMode != nil
            || defaults.transliterationModel != nil
            || defaults.splitBatches != nil
            || defaults.stitchBatches != nil
            || defaults.includeTransliteration != nil
            || defaults.targetHeight != nil
            || defaults.preserveAspectRatio != nil
            || defaults.enableLookupCache != nil
        else {
            return nil
        }

        return defaults
    }

    static func narrationStartSentence(
        inputFile: String,
        from jobs: [PipelineStatusResponse]
    ) -> Int? {
        let normalizedInput = normalizedNarrationPath(inputFile)
        guard let normalizedInput, !jobs.isEmpty else { return nil }

        var latest: (createdAt: Date, anchor: Int)?
        for job in jobs where isReusableNarrationJob(job) {
            guard let createdAt = parseJobDate(job.createdAt),
                  let candidate = normalizedNarrationPath(
                    narrationString(job, keys: ["input_file", "inputFile", "base_output_file", "baseOutputFile"])
                  ),
                  candidate == normalizedInput
            else {
                continue
            }
            let anchor = narrationInt(job, keys: ["end_sentence", "endSentence"])
                ?? narrationInt(job, keys: ["start_sentence", "startSentence"])
            guard let anchor else { continue }
            if latest == nil || createdAt > latest!.createdAt {
                latest = (createdAt, anchor)
            }
        }

        guard let latest else { return nil }
        return max(1, latest.anchor - 5)
    }

    static func webCreateViewID(for mode: AppleCreateMode) -> String {
        switch mode {
        case .generatedBook:
            return "books:create"
        case .narrateEbook:
            return "pipeline:source"
        case .subtitleJob:
            return "subtitles:home"
        case .youtubeDub:
            return "subtitles:youtube-dub"
        }
    }

    static func webCreateHandoffURL(apiBaseURL: URL?, mode: AppleCreateMode) -> URL? {
        guard
            let apiBaseURL,
            var components = URLComponents(url: apiBaseURL, resolvingAgainstBaseURL: false),
            let scheme = components.scheme,
            !scheme.isEmpty,
            var host = components.host,
            !host.isEmpty
        else {
            return nil
        }

        if host.hasPrefix("api.") {
            host.removeFirst(4)
        }

        if (host == "localhost" || host == "127.0.0.1" || host == "::1"), components.port == 8000 {
            components.port = 5173
        }

        components.host = host
        components.path = "/"
        components.queryItems = [
            URLQueryItem(name: "view", value: webCreateViewID(for: mode))
        ]
        components.fragment = nil
        return components.url
    }

    static func resolvedDefaults(
        from options: BookCreationOptionsResponse,
        editedFields: Set<AppleBookCreateEditedField>,
        currentSentenceCount: Int
    ) -> AppleCreateResolvedDefaults {
        AppleCreateResolvedDefaults(
            topic: editedFields.contains(.topic) ? nil : trimmed(options.defaults.topic).nonEmptyValue,
            bookName: editedFields.contains(.bookName) ? nil : trimmed(options.defaults.bookName).nonEmptyValue,
            genre: editedFields.contains(.genre) ? nil : trimmed(options.defaults.genre).nonEmptyValue,
            author: editedFields.contains(.author)
                ? nil
                : (trimmed(options.defaults.author).nonEmptyValue ?? "Me"),
            sentenceCount: clampSentenceCount(
                editedFields.contains(.sentenceCount) ? currentSentenceCount : options.sentenceBounds.default,
                bounds: options.sentenceBounds
            ),
            inputLanguage: editedFields.contains(.inputLanguage)
                ? nil
                : AppleBookCreateLanguage(backendValue: options.defaults.inputLanguage),
            targetLanguage: editedFields.contains(.targetLanguage)
                ? nil
                : targetLanguageDefaults(from: options.defaults).primary,
            additionalTargetLanguages: editedFields.contains(.additionalTargetLanguages)
                ? nil
                : targetLanguageDefaults(from: options.defaults).additionalTargets,
            voice: editedFields.contains(.voice)
                ? nil
                : AppleBookCreateVoiceOption(backendValue: options.defaults.voice),
            generateAudio: editedFields.contains(.generateAudio)
                ? nil
                : options.pipelineDefaults.generateAudio,
            audioMode: editedFields.contains(.audioMode)
                ? nil
                : normalizedMode(options.pipelineDefaults.audioMode, fallback: "4"),
            audioBitrateKbps: editedFields.contains(.audioBitrateKbps)
                ? nil
                : options.pipelineDefaults.audioBitrateKbps.map { "\($0)" } ?? "",
            writtenMode: editedFields.contains(.writtenMode)
                ? nil
                : normalizedMode(options.pipelineDefaults.writtenMode, fallback: "4"),
            tempo: editedFields.contains(.tempo)
                ? nil
                : clampTempo(options.pipelineDefaults.tempo),
            bookSentencesPerOutputFile: editedFields.contains(.bookSentencesPerOutputFile)
                ? nil
                : clampBookSentencesPerOutputFile(options.pipelineDefaults.sentencesPerOutputFile),
            stitchFull: editedFields.contains(.stitchFull)
                ? nil
                : options.pipelineDefaults.stitchFull,
            includeTransliteration: editedFields.contains(.includeTransliteration)
                ? nil
                : options.pipelineDefaults.includeTransliteration,
            bookTranslationProvider: editedFields.contains(.bookTranslationProvider)
                ? nil
                : AppleSubtitleTranslationProvider(backendValue: options.pipelineDefaults.translationProvider),
            bookTranslationBatchSize: editedFields.contains(.bookTranslationBatchSize)
                ? nil
                : clampSubtitleTranslationBatchSize(options.pipelineDefaults.translationBatchSize),
            bookTransliterationMode: editedFields.contains(.bookTransliterationMode)
                ? nil
                : AppleSubtitleTransliterationMode(backendValue: options.pipelineDefaults.transliterationMode),
            enableLookupCache: editedFields.contains(.enableLookupCache)
                ? nil
                : options.pipelineDefaults.enableLookupCache,
            bookLookupCacheBatchSize: editedFields.contains(.bookLookupCacheBatchSize)
                ? nil
                : clampSubtitleTranslationBatchSize(options.pipelineDefaults.lookupCacheBatchSize),
            outputHtml: editedFields.contains(.outputHtml)
                ? nil
                : options.pipelineDefaults.outputHtml,
            outputPdf: editedFields.contains(.outputPdf)
                ? nil
                : options.pipelineDefaults.outputPdf,
            includeImages: editedFields.contains(.includeImages)
                ? nil
                : options.generatedSourceDefaults.addImages,
            imagePromptPipeline: editedFields.contains(.imagePromptPipeline)
                ? nil
                : (
                    AppleGeneratedBookImagePromptPipeline(
                        backendValue: options.generatedSourceDefaults.imagePromptPipeline
                    ) ?? .promptPlan
                ),
            imageStyleTemplate: editedFields.contains(.imageStyleTemplate)
                ? nil
                : (
                    AppleGeneratedBookImageStyleTemplate(
                        backendValue: options.generatedSourceDefaults.imageStyleTemplate
                    ) ?? .wireframe
                ),
            imagePromptContextSentences: editedFields.contains(.imagePromptContextSentences)
                ? nil
                : clampImagePromptContextSentences(options.generatedSourceDefaults.imagePromptContextSentences),
            imageWidth: editedFields.contains(.imageWidth)
                ? nil
                : normalizedImageDimension(options.generatedSourceDefaults.imageWidth),
            imageHeight: editedFields.contains(.imageHeight)
                ? nil
                : normalizedImageDimension(options.generatedSourceDefaults.imageHeight),
            subtitleTranslationProvider: editedFields.contains(.subtitleTranslationProvider)
                ? nil
                : AppleSubtitleTranslationProvider(backendValue: options.pipelineDefaults.translationProvider)
        )
    }

    static func clampSentenceCount(
        _ value: Int,
        bounds: BookCreationSentenceBounds
    ) -> Int {
        max(bounds.min, min(bounds.max, value))
    }

    static func clampImagePromptContextSentences(_ value: Int) -> Int {
        clamp(value, to: 0...50)
    }

    static func clampImagePromptBatchSize(_ value: Int) -> Int {
        clamp(value, to: 1...50)
    }

    static func clampBookSentencesPerOutputFile(_ value: Int) -> Int {
        clamp(value, to: AppleBookOutputChunking.sentencesPerOutputFileRange)
    }

    static func normalizedImageDimension(_ value: String) -> String {
        let trimmedValue = trimmed(value)
        guard let parsed = Double(trimmedValue), parsed.isFinite else {
            return "512"
        }
        return "\(max(64, Int(parsed.rounded(.down))))"
    }

    static func normalizedImageSteps(_ value: String) -> Int? {
        let trimmedValue = trimmed(value)
        guard !trimmedValue.isEmpty,
              let parsed = Double(trimmedValue),
              parsed.isFinite else {
            return nil
        }
        return max(1, Int(parsed.rounded(.down)))
    }

    static func normalizedImageCfgScale(_ value: String) -> Double? {
        let trimmedValue = trimmed(value)
        guard !trimmedValue.isEmpty,
              let parsed = Double(trimmedValue),
              parsed.isFinite else {
            return nil
        }
        return max(0, parsed)
    }

    static func normalizedPositiveInteger(_ value: String) -> Int? {
        let trimmedValue = trimmed(value)
        guard !trimmedValue.isEmpty,
              let parsed = Double(trimmedValue),
              parsed.isFinite else {
            return nil
        }
        return max(1, Int(parsed.rounded(.down)))
    }

    static func normalizedImageApiBaseURLs(_ value: String) -> [String] {
        var urls = [String]()
        var seen = Set<String>()
        let separators = CharacterSet(charactersIn: ",\n")
        for component in value.components(separatedBy: separators) {
            let normalized = component.trimmingCharacters(in: .whitespacesAndNewlines)
                .replacingOccurrences(of: #"/+$"#, with: "", options: .regularExpression)
            guard !normalized.isEmpty, !seen.contains(normalized) else {
                continue
            }
            seen.insert(normalized)
            urls.append(normalized)
        }
        return urls
    }

    static func normalizedEndSentence(_ value: String, startSentence: Int) -> Int? {
        let trimmedValue = trimmed(value)
        guard !trimmedValue.isEmpty else { return nil }
        let isOffset = trimmedValue.hasPrefix("+")
        let numericValue = isOffset ? trimmed(String(trimmedValue.dropFirst())) : trimmedValue
        guard let parsed = normalizedPositiveInteger(numericValue) else { return nil }
        let candidate = isOffset ? startSentence + parsed - 1 : parsed
        return max(startSentence, candidate)
    }

    static func normalizedPositiveNumber(_ value: String) -> Double? {
        let trimmedValue = trimmed(value)
        guard !trimmedValue.isEmpty,
              let parsed = Double(trimmedValue),
              parsed.isFinite else {
            return nil
        }
        return max(1, parsed)
    }

    static func normalizedMode(_ value: String, fallback: String) -> String {
        let trimmedValue = trimmed(value)
        guard !trimmedValue.isEmpty else { return fallback }
        return trimmedValue
    }

    static func normalizedAudioBitrate(_ value: String) -> Int? {
        let trimmedValue = trimmed(value)
        guard !trimmedValue.isEmpty,
              let parsed = Double(trimmedValue),
              parsed.isFinite else {
            return nil
        }
        return max(32, Int(parsed.rounded(.down)))
    }

    static func clampTempo(_ value: Double) -> Double {
        guard value.isFinite else { return 1.0 }
        return min(2.0, max(0.5, value))
    }

    static func availableInputLanguages(
        from options: BookCreationOptionsResponse?
    ) -> [AppleBookCreateLanguage] {
        availableLanguages(options?.supportedInputLanguages ?? [])
    }

    static func availableTargetLanguages(
        from options: BookCreationOptionsResponse?
    ) -> [AppleBookCreateLanguage] {
        availableLanguages(options?.supportedOutputLanguages ?? [])
    }

    static func availableVoices(
        from options: BookCreationOptionsResponse?,
        selected: AppleBookCreateVoiceOption?
    ) -> [AppleBookCreateVoiceOption] {
        availableVoices(
            from: options,
            inventory: nil,
            language: "",
            selected: selected
        )
    }

    static func availableVoices(
        from options: BookCreationOptionsResponse?,
        inventory: AppleBookCreateVoiceInventory?,
        language: String,
        selected: AppleBookCreateVoiceOption?
    ) -> [AppleBookCreateVoiceOption] {
        let baseOptions = AppleBookCreateVoiceOption.options(
            from: options?.supportedVoices ?? [],
            selected: selected
        )
        let inventoryOptions = voiceInventoryOptions(from: inventory, language: language)
        return mergedVoiceOptions(baseOptions + inventoryOptions, selected: selected)
    }

    static func voiceInventoryOptions(
        from inventory: AppleBookCreateVoiceInventory?,
        language: String
    ) -> [AppleBookCreateVoiceOption] {
        guard let inventory else { return [] }
        let normalizedLanguage = normalizedVoiceLanguage(language)
        let baseLanguage = baseVoiceLanguage(normalizedLanguage)
        guard !baseLanguage.isEmpty else { return [] }

        var options = [AppleBookCreateVoiceOption]()
        var seen = Set<String>()

        for entry in inventory.gtts where voiceLanguageMatches(entry.code, normalizedLanguage: normalizedLanguage) {
            let identifier = "gTTS-\(baseVoiceLanguage(entry.code))"
            appendVoiceOption(identifier, to: &options, seen: &seen)
        }

        for voice in inventory.macos.sorted(by: { $0.name < $1.name })
            where voiceLanguageMatches(voice.lang, normalizedLanguage: normalizedLanguage) {
            appendVoiceOption(macOSVoiceIdentifier(voice), to: &options, seen: &seen)
        }

        for voice in inventory.piper.sorted(by: { $0.name < $1.name })
            where voiceLanguageMatches(voice.lang, normalizedLanguage: normalizedLanguage) {
            appendVoiceOption(voice.name, to: &options, seen: &seen)
        }

        return options
    }

    static func sampleSentence(language: String, fallbackLabel: String) -> String {
        let code = normalizedVoiceLanguage(language)
        let base = baseVoiceLanguage(code)
        switch base {
        case "ar":
            return "مرحبا! هذه جملة نموذجية لتحويل النص إلى كلام."
        case "de":
            return "Hallo! Dies ist ein Beispielsatz für Text-zu-Sprache."
        case "en":
            return "Hello! This is a sample sentence for text-to-speech."
        case "es":
            return "¡Hola! Esta es una frase de muestra para texto a voz."
        case "fr":
            return "Bonjour ! Ceci est une phrase d'exemple pour la synthese vocale."
        case "sk":
            return "Ahoj! Toto je ukazkova veta pre prevod textu na rec."
        default:
            let label = trimmed(fallbackLabel).nonEmptyValue ?? language
            return "Sample narration for \(label)."
        }
    }

    static func voicePreviewKey(language: String) -> String {
        normalizedVoiceLanguage(language).lowercased()
    }

    private static func mergedVoiceOptions(
        _ options: [AppleBookCreateVoiceOption],
        selected: AppleBookCreateVoiceOption?
    ) -> [AppleBookCreateVoiceOption] {
        var seen = Set<String>()
        var merged = [AppleBookCreateVoiceOption]()
        for option in options where seen.insert(option.backendValue.lowercased()).inserted {
            merged.append(option)
        }
        if let selected, !seen.contains(selected.backendValue.lowercased()) {
            merged.insert(selected, at: 0)
        }
        return merged.isEmpty ? AppleBookCreateVoiceOption.fallbackOptions : merged
    }

    private static func appendVoiceOption(
        _ value: String,
        to options: inout [AppleBookCreateVoiceOption],
        seen: inout Set<String>
    ) {
        guard let option = AppleBookCreateVoiceOption(backendValue: value),
              seen.insert(option.backendValue.lowercased()).inserted else {
            return
        }
        options.append(option)
    }

    private static func macOSVoiceIdentifier(_ voice: AppleBookCreateVoiceInventory.MacOSVoice) -> String {
        let quality = trimmed(voice.quality ?? "").nonEmptyValue ?? "Default"
        let gender = trimmed(voice.gender ?? "").nonEmptyValue.map { " - \(capitalizedFirst($0))" } ?? ""
        return "\(voice.name) - \(voice.lang) - (\(quality))\(gender)"
    }

    private static func capitalizedFirst(_ value: String) -> String {
        guard let first = value.first else { return value }
        return first.uppercased() + value.dropFirst()
    }

    private static func voiceLanguageMatches(
        _ candidate: String,
        normalizedLanguage: String
    ) -> Bool {
        let normalizedCandidate = normalizedVoiceLanguage(candidate)
        guard !normalizedCandidate.isEmpty, !normalizedLanguage.isEmpty else { return false }
        if normalizedCandidate == normalizedLanguage {
            return true
        }
        return baseVoiceLanguage(normalizedCandidate) == baseVoiceLanguage(normalizedLanguage)
    }

    private static func normalizedVoiceLanguage(_ value: String) -> String {
        let normalized = trimmed(value)
            .replacingOccurrences(of: "_", with: "-")
            .lowercased()
        let languageMap = [
            "english": "en",
            "arabic": "ar",
            "spanish": "es",
            "french": "fr",
            "german": "de",
            "slovak": "sk"
        ]
        return languageMap[normalized] ?? normalized
    }

    private static func baseVoiceLanguage(_ value: String) -> String {
        normalizedVoiceLanguage(value)
            .split(separator: "-", omittingEmptySubsequences: true)
            .first
            .map(String.init) ?? ""
    }

    private static func latestNarrationJob(from jobs: [PipelineStatusResponse]) -> PipelineStatusResponse? {
        var latest: (job: PipelineStatusResponse, createdAt: Date)?
        for job in jobs where isReusableNarrationJob(job) {
            guard let createdAt = parseJobDate(job.createdAt),
                  job.parameters?.objectValue != nil
            else {
                continue
            }
            if latest == nil || createdAt > latest!.createdAt {
                latest = (job, createdAt)
            }
        }
        return latest?.job
    }

    private static func latestGeneratedBookJob(from jobs: [PipelineStatusResponse]) -> PipelineStatusResponse? {
        latestJob(from: jobs) { job in
            jobHasBookGeneration(job)
        }
    }

    private static func latestSubtitleJob(from jobs: [PipelineStatusResponse]) -> PipelineStatusResponse? {
        latestJob(from: jobs) { job in
            job.jobType.lowercased() == "subtitle"
        }
    }

    private static func latestYoutubeJob(from jobs: [PipelineStatusResponse]) -> PipelineStatusResponse? {
        latestJob(from: jobs) { job in
            job.jobType.lowercased() == "youtube_dub"
        }
    }

    private static func latestJob(
        from jobs: [PipelineStatusResponse],
        matching predicate: (PipelineStatusResponse) -> Bool
    ) -> PipelineStatusResponse? {
        var latest: (job: PipelineStatusResponse, createdAt: Date)?
        for job in jobs where predicate(job) {
            guard let createdAt = parseJobDate(job.createdAt),
                  job.parameters?.objectValue != nil
            else {
                continue
            }
            if latest == nil || createdAt > latest!.createdAt {
                latest = (job, createdAt)
            }
        }
        return latest?.job
    }

    private static func isReusableNarrationJob(_ job: PipelineStatusResponse) -> Bool {
        let jobType = job.jobType.lowercased()
        return !jobType.contains("subtitle") && jobType != "youtube_dub" && !jobHasBookGeneration(job)
    }

    private static func jobHasBookGeneration(_ job: PipelineStatusResponse) -> Bool {
        guard let parameters = job.parameters?.objectValue else { return false }
        if parameters["book_generation"]?.objectValue != nil {
            return true
        }
        if let request = parameters["request"]?.objectValue,
           request["book_generation"]?.objectValue != nil {
            return true
        }
        return false
    }

    private static func narrationString(
        _ job: PipelineStatusResponse,
        keys: [String]
    ) -> String? {
        guard let parameters = job.parameters?.objectValue else { return nil }
        return narrationString(in: parameters, keys: keys)
    }

    private static func narrationString(
        in parameters: [String: JSONValue],
        keys: [String]
    ) -> String? {
        let sources = narrationParameterSources(parameters)
        for source in sources {
            for key in keys {
                if let value = source[key]?.stringValue?.nonEmptyValue {
                    return value
                }
            }
        }
        return nil
    }

    private static func historyString(
        in sources: [[String: JSONValue]],
        keys: [String]
    ) -> String? {
        for source in sources {
            for key in keys {
                if let value = source[key]?.stringValue?.nonEmptyValue {
                    return value
                }
            }
        }
        return nil
    }

    private static func narrationStringArray(
        _ job: PipelineStatusResponse,
        keys: [String]
    ) -> [String]? {
        guard let parameters = job.parameters?.objectValue else { return nil }
        let sources = narrationParameterSources(parameters)
        for source in sources {
            for key in keys {
                guard let value = source[key] else { continue }
                if let array = value.arrayValue {
                    let strings = array.compactMap { $0.stringValue?.nonEmptyValue }
                    if !strings.isEmpty {
                        return strings
                    }
                }
                if let string = value.stringValue?.nonEmptyValue {
                    let strings = normalizedLanguageList(string.split(separator: ",").map(String.init))
                    if !strings.isEmpty {
                        return strings
                    }
                }
            }
        }
        return nil
    }

    private static func historyStringArray(
        in sources: [[String: JSONValue]],
        keys: [String]
    ) -> [String]? {
        for source in sources {
            for key in keys {
                guard let value = source[key] else { continue }
                if let array = value.arrayValue {
                    let strings = array.compactMap { $0.stringValue?.nonEmptyValue }
                    if !strings.isEmpty {
                        return strings
                    }
                }
                if let string = value.stringValue?.nonEmptyValue {
                    let strings = normalizedLanguageList(string.split(separator: ",").map(String.init))
                    if !strings.isEmpty {
                        return strings
                    }
                }
            }
        }
        return nil
    }

    private static func narrationInt(
        _ job: PipelineStatusResponse,
        keys: [String]
    ) -> Int? {
        guard let parameters = job.parameters?.objectValue else { return nil }
        let sources = narrationParameterSources(parameters)
        for source in sources {
            for key in keys {
                if let value = source[key]?.intValue {
                    return value
                }
            }
        }
        return nil
    }

    private static func historyInt(
        in sources: [[String: JSONValue]],
        keys: [String]
    ) -> Int? {
        for source in sources {
            for key in keys {
                if let value = source[key]?.intValue {
                    return value
                }
            }
        }
        return nil
    }

    private static func historyDouble(
        _ job: PipelineStatusResponse,
        keys: [String]
    ) -> Double? {
        guard let parameters = job.parameters?.objectValue else { return nil }
        let sources = narrationParameterSources(parameters)
        for source in sources {
            for key in keys {
                guard let value = source[key] else { continue }
                if let doubleValue = historyDouble(from: value) {
                    return doubleValue
                }
            }
        }
        return nil
    }

    private static func historyDouble(
        in sources: [[String: JSONValue]],
        keys: [String]
    ) -> Double? {
        for source in sources {
            for key in keys {
                guard let value = source[key] else { continue }
                if let doubleValue = historyDouble(from: value) {
                    return doubleValue
                }
            }
        }
        return nil
    }

    private static func narrationBool(
        _ job: PipelineStatusResponse,
        keys: [String]
    ) -> Bool? {
        guard let parameters = job.parameters?.objectValue else { return nil }
        let sources = narrationParameterSources(parameters)
        for source in sources {
            for key in keys {
                guard let value = source[key] else { continue }
                if case let .bool(boolValue) = value {
                    return boolValue
                }
                if let string = value.stringValue?.lowercased() {
                    if ["1", "true", "yes", "on"].contains(string) {
                        return true
                    }
                    if ["0", "false", "no", "off"].contains(string) {
                        return false
                    }
                }
            }
        }
        return nil
    }

    private static func historyBool(
        in sources: [[String: JSONValue]],
        keys: [String]
    ) -> Bool? {
        for source in sources {
            for key in keys {
                guard let value = source[key] else { continue }
                if case let .bool(boolValue) = value {
                    return boolValue
                }
                if let string = value.stringValue?.lowercased() {
                    if ["1", "true", "yes", "on"].contains(string) {
                        return true
                    }
                    if ["0", "false", "no", "off"].contains(string) {
                        return false
                    }
                }
            }
        }
        return nil
    }

    private static func historyOffset(
        _ job: PipelineStatusResponse,
        stringKeys: [String],
        secondsKeys: [String],
        allowRelative: Bool
    ) -> String? {
        if let seconds = historyDouble(job, keys: secondsKeys) {
            return formatHistorySeconds(seconds)
        }

        guard let rawValue = narrationString(job, keys: stringKeys) else {
            return nil
        }
        if allowRelative {
            return SubtitleTimecodeInput.normalize(rawValue, allowRelative: true)
        }
        return normalizeYoutubeOffset(rawValue)
    }

    private static func historyDouble(from value: JSONValue) -> Double? {
        switch value {
        case let .number(number):
            guard number.isFinite else { return nil }
            return number
        case let .string(string):
            let trimmedValue = trimmed(string)
            guard let parsed = Double(trimmedValue), parsed.isFinite else {
                return nil
            }
            return parsed
        case let .bool(bool):
            return bool ? 1 : 0
        case let .array(values):
            for value in values {
                if let doubleValue = historyDouble(from: value) {
                    return doubleValue
                }
            }
            return nil
        default:
            return nil
        }
    }

    private static func formatHistorySeconds(_ value: Double) -> String? {
        guard value.isFinite, value >= 0 else { return nil }
        let totalSeconds = Int(value.rounded(.down))
        let hours = totalSeconds / 3600
        let minutes = (totalSeconds % 3600) / 60
        let seconds = totalSeconds % 60
        if hours > 0 {
            return [hours, minutes, seconds].map(formatTimecodeComponent).joined(separator: ":")
        }
        return "\(formatTimecodeComponent(minutes)):\(formatTimecodeComponent(seconds))"
    }

    private static func formatTimecodeComponent(_ value: Int) -> String {
        String(format: "%02d", value)
    }

    private static func generatedBookParameterSources(
        _ parameters: [String: JSONValue]
    ) -> [[String: JSONValue]] {
        var sources = [[String: JSONValue]]()
        appendGeneratedBookSources(from: parameters, to: &sources)
        if let request = parameters["request"]?.objectValue {
            appendGeneratedBookSources(from: request, to: &sources)
        }
        sources.append(parameters)
        return sources
    }

    private static func appendGeneratedBookSources(
        from parameters: [String: JSONValue],
        to sources: inout [[String: JSONValue]]
    ) {
        if let bookGeneration = parameters["book_generation"]?.objectValue {
            sources.append(bookGeneration)
        }
        if let inputs = parameters["inputs"]?.objectValue {
            sources.append(inputs)
            if let bookMetadata = inputs["book_metadata"]?.objectValue {
                sources.append(bookMetadata)
            }
        }
        if let pipelineOverrides = parameters["pipeline_overrides"]?.objectValue {
            sources.append(pipelineOverrides)
        }
        if let config = parameters["config"]?.objectValue {
            sources.append(config)
        }
    }

    private static func narrationParameterSources(
        _ parameters: [String: JSONValue]
    ) -> [[String: JSONValue]] {
        var sources = [parameters]
        if let inputs = parameters["inputs"]?.objectValue {
            sources.insert(inputs, at: 0)
        }
        if let request = parameters["request"]?.objectValue {
            sources.append(request)
            if let requestInputs = request["inputs"]?.objectValue {
                sources.insert(requestInputs, at: 0)
            }
        }
        return sources
    }

    private static func normalizedNarrationPath(_ value: String?) -> String? {
        guard let value else { return nil }
        let trimmedValue = trimmed(value)
        guard !trimmedValue.isEmpty else { return nil }
        return trimmedValue
            .trimmingCharacters(in: CharacterSet(charactersIn: "/\\"))
            .lowercased()
            .nonEmptyValue
    }

    private static func parseJobDate(_ value: String) -> Date? {
        jobDateFormatterWithFractional.date(from: value) ?? jobDateFormatter.date(from: value)
    }

    private static func parseSubtitleSourceDate(_ value: String?) -> Date {
        guard let value = value?.nonEmptyValue else { return .distantPast }
        return subtitleSourceDateFormatterWithFractional.date(from: value)
            ?? subtitleSourceDateFormatter.date(from: value)
            ?? .distantPast
    }

    private static let jobDateFormatter: ISO8601DateFormatter = {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime]
        return formatter
    }()

    private static let jobDateFormatterWithFractional: ISO8601DateFormatter = {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return formatter
    }()

    private static let subtitleSourceDateFormatter: ISO8601DateFormatter = {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime]
        return formatter
    }()

    private static let subtitleSourceDateFormatterWithFractional: ISO8601DateFormatter = {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return formatter
    }()

    static func targetLanguageDefaults(
        from defaults: BookCreationDefaults
    ) -> AppleCreateTargetLanguageDefaults {
        let targetCandidates = defaults.targetLanguages?.isEmpty == false
            ? defaults.targetLanguages ?? []
            : (
                defaults.outputLanguages?.isEmpty == false
                    ? defaults.outputLanguages ?? []
                    : [defaults.outputLanguage]
            )
        let normalized = normalizedLanguageList(targetCandidates)
        guard let first = normalized.first else {
            return AppleCreateTargetLanguageDefaults(
                primary: AppleBookCreateLanguage(backendValue: defaults.outputLanguage),
                additionalTargets: ""
            )
        }
        let primary = AppleBookCreateLanguage(backendValue: first)
        let additionalTargets = normalized.dropFirst().joined(separator: ", ")
        return AppleCreateTargetLanguageDefaults(primary: primary, additionalTargets: additionalTargets)
    }

    static func languagePreferences(
        inputLanguage: AppleBookCreateLanguage,
        targetLanguage: AppleBookCreateLanguage,
        additionalTargetLanguages: String,
        enableLookupCache: Bool
    ) -> AppleCreateLanguagePreferences {
        AppleCreateLanguagePreferences(
            inputLanguage: inputLanguage.backendValue,
            targetLanguages: normalizedTargetLanguages(
                primary: targetLanguage.backendValue,
                additionalTargets: additionalTargetLanguages
            ),
            enableLookupCache: enableLookupCache
        )
    }

    static func resolvedLanguagePreferences(
        from preferences: AppleCreateLanguagePreferences?
    ) -> AppleCreateResolvedLanguagePreferences? {
        guard let preferences else { return nil }
        let normalizedTargets = normalizedLanguageList(preferences.targetLanguages)
        let targetLanguage = normalizedTargets.first.flatMap(AppleBookCreateLanguage.init(backendValue:))
        let additionalTargets = normalizedTargets.dropFirst().joined(separator: ", ")
        let inputLanguage = preferences.inputLanguage
            .flatMap { AppleBookCreateLanguage(backendValue: $0) }
        guard
            inputLanguage != nil
                || targetLanguage != nil
                || !additionalTargets.isEmpty
                || preferences.enableLookupCache != nil
        else {
            return nil
        }

        return AppleCreateResolvedLanguagePreferences(
            inputLanguage: inputLanguage,
            targetLanguage: targetLanguage,
            additionalTargetLanguages: additionalTargets.isEmpty ? nil : additionalTargets,
            enableLookupCache: preferences.enableLookupCache
        )
    }

    static func voiceOverrides(
        targetLanguages: [String],
        targetVoice: AppleBookCreateVoiceOption?,
        languageVoiceOverrides: [String: String] = [:]
    ) -> [String: String] {
        var overrides = [String: String]()
        var normalizedTargets = Set<String>()
        for targetLanguage in targetLanguages {
            let language = trimmed(targetLanguage)
            guard !language.isEmpty else { continue }
            normalizedTargets.insert(language.lowercased())
            if let targetVoice {
                overrides[language] = targetVoice.backendValue
            }
        }

        for (targetLanguage, voice) in languageVoiceOverrides {
            let language = trimmed(targetLanguage)
            let voiceValue = trimmed(voice)
            guard !language.isEmpty, !voiceValue.isEmpty else { continue }
            guard normalizedTargets.contains(language.lowercased()) else { continue }
            overrides[language] = voiceValue
        }
        return overrides
    }

    static func voiceOverridePipelineValue(_ voiceOverrides: [String: String]) -> JSONValue? {
        var normalized = [String: JSONValue]()
        for (key, value) in voiceOverrides {
            let language = trimmed(key)
            let voice = trimmed(value)
            guard !language.isEmpty, !voice.isEmpty else { continue }
            normalized[language] = .string(voice)
        }
        guard !normalized.isEmpty else { return nil }
        return .object(normalized)
    }

    static func normalizedTargetLanguages(
        primary: String,
        additionalTargets: String
    ) -> [String] {
        let primaryTarget = trimmed(primary)
        guard !primaryTarget.isEmpty else { return [] }

        var seen = Set<String>()
        seen.insert(primaryTarget.lowercased())
        var targetLanguages = [primaryTarget]

        for candidate in additionalTargets.components(separatedBy: CharacterSet(charactersIn: ",\n")) {
            let target = trimmed(candidate)
            guard !target.isEmpty else { continue }

            let lookupKey = target.lowercased()
            guard !seen.contains(lookupKey) else { continue }

            seen.insert(lookupKey)
            targetLanguages.append(target)
        }
        return targetLanguages
    }

    static func normalizedLanguageList(_ languages: [String]) -> [String] {
        var normalized = [String]()
        var seen = Set<String>()
        for language in languages {
            let value = trimmed(language)
            guard !value.isEmpty else { continue }
            let lookupKey = value.lowercased()
            guard !seen.contains(lookupKey) else { continue }
            seen.insert(lookupKey)
            normalized.append(value)
        }
        return normalized
    }

    static func normalizedBookGenres(_ value: String) -> [String] {
        var genres = [String]()
        var seen = Set<String>()
        for component in value.split(separator: ",") {
            let genre = trimmed(String(component))
            guard !genre.isEmpty else { continue }
            let lookupKey = genre.lowercased()
            guard seen.insert(lookupKey).inserted else { continue }
            genres.append(genre)
        }
        return genres
    }

    static func contentIndexChapters(from value: JSONValue?) -> [AppleCreateChapterOption] {
        guard case let .object(root) = value,
              case let .array(chapterValues)? = root["chapters"] else {
            return []
        }
        var chapters = [AppleCreateChapterOption]()
        chapters.reserveCapacity(chapterValues.count)
        for (index, chapterValue) in chapterValues.enumerated() {
            guard case let .object(chapter) = chapterValue else { continue }
            let start = chapter["start_sentence"]?.intValue
                ?? chapter["startSentence"]?.intValue
                ?? chapter["start"]?.intValue
            guard let start, start > 0 else { continue }
            let sentenceCount = chapter["sentence_count"]?.intValue ?? chapter["sentenceCount"]?.intValue
            var end = chapter["end_sentence"]?.intValue
                ?? chapter["endSentence"]?.intValue
                ?? chapter["end"]?.intValue
            if end == nil, let sentenceCount {
                end = start + max(sentenceCount - 1, 0)
            }
            if let endValue = end, endValue < start {
                end = start
            }
            let id = chapter["id"]?.stringValue ?? "chapter-\(index + 1)"
            let title = chapter["title"]?.stringValue
                ?? chapter["toc_label"]?.stringValue
                ?? chapter["tocLabel"]?.stringValue
                ?? chapter["name"]?.stringValue
                ?? "Chapter \(index + 1)"
            chapters.append(
                AppleCreateChapterOption(
                    id: id,
                    title: title,
                    startSentence: start,
                    endSentence: end
                )
            )
        }
        return chapters
    }

    static func chapterRangeSelection(
        chapters: [AppleCreateChapterOption],
        startChapterID: String,
        endChapterID: String
    ) -> AppleCreateChapterRangeSelection? {
        guard let startIndex = chapters.firstIndex(where: { $0.id == startChapterID }) else {
            return nil
        }
        let requestedEndIndex = chapters.firstIndex(where: { $0.id == endChapterID }) ?? startIndex
        let endIndex = max(startIndex, requestedEndIndex)
        let startChapter = chapters[startIndex]
        let endChapter = chapters[endIndex]
        let endSentence = endChapter.endSentence ?? endChapter.startSentence
        return AppleCreateChapterRangeSelection(
            startIndex: startIndex,
            endIndex: endIndex,
            startSentence: startChapter.startSentence,
            endSentence: max(startChapter.startSentence, endSentence),
            count: endIndex - startIndex + 1,
            label: startIndex == endIndex ? startChapter.title : "\(startChapter.title) - \(endChapter.title)"
        )
    }

    static func submitButtonPresentation(
        for mode: AppleCreateMode,
        isSubmitting: Bool
    ) -> AppleCreateSubmitPresentation {
        if isSubmitting {
            return AppleCreateSubmitPresentation(title: "Submitting", systemImage: "hourglass")
        }
        switch mode {
        case .generatedBook:
            return AppleCreateSubmitPresentation(title: "Generate Audiobook", systemImage: "sparkles")
        case .narrateEbook:
            return AppleCreateSubmitPresentation(title: "Narrate EPUB", systemImage: "book")
        case .subtitleJob:
            return AppleCreateSubmitPresentation(title: "Create Subtitles", systemImage: "captions.bubble")
        case .youtubeDub:
            return AppleCreateSubmitPresentation(title: "Create Dub", systemImage: "video")
        }
    }

    static func intakeStatusPresentation(for status: PipelineIntakeStatusResponse) -> AppleCreateIntakePresentation {
        let detailLines = [
            "Delayed jobs: \(status.delayCount)",
            status.softLimit.map { "Slowdown starts at \($0) pending" },
            status.hardLimit.map { "Capacity limit is \($0) pending" },
        ].compactMap { $0 }

        if !status.acceptingJobs {
            let limit = status.hardLimit.map { " of \($0)" } ?? ""
            return AppleCreateIntakePresentation(
                label: "Queue at capacity: \(status.queueDepth) pending\(limit). Wait for jobs to clear.",
                detailLines: detailLines
            )
        }

        if status.isUnderPressure {
            return AppleCreateIntakePresentation(
                label: "Queue pressure: \(status.queueDepth) pending, \(status.activeCount) running. New jobs may start more slowly.",
                detailLines: detailLines
            )
        }

        return AppleCreateIntakePresentation(
            label: "Job intake available: \(status.queueDepth) pending, \(status.activeCount) running.",
            detailLines: detailLines
        )
    }

    static func canSubmit(_ state: AppleCreateSubmitState) -> Bool {
        guard state.hasConfiguration else { return false }
        switch state.mode {
        case .generatedBook:
            return !trimmed(state.topic).isEmpty
                && !trimmed(state.bookName).isEmpty
                && !trimmed(state.genre).isEmpty
        case .narrateEbook:
            return (state.hasNarrateLocalFile || !trimmed(state.sourcePath).isEmpty)
                && !trimmed(state.sourceBaseOutput).isEmpty
        case .subtitleJob:
            return state.hasSubtitleLocalFile || !trimmed(state.subtitleSourcePath).isEmpty
        case .youtubeDub:
            return !trimmed(state.youtubeVideoPath).isEmpty
                && !trimmed(state.youtubeSubtitlePath).isEmpty
        }
    }

    static func derivedBaseOutput(
        for mode: AppleCreateMode,
        topic: String,
        bookName: String,
        sourceBaseOutput: String,
        subtitleSourcePath: String,
        youtubeVideoPath: String
    ) -> String {
        switch mode {
        case .generatedBook:
            return deriveBaseOutputName(bookName.isEmpty ? topic : bookName)
        case .narrateEbook:
            return trimmed(sourceBaseOutput)
        case .subtitleJob:
            return deriveBaseOutputName(subtitleSourcePath)
        case .youtubeDub:
            return deriveBaseOutputName(youtubeVideoPath)
        }
    }

    static func subtitleModelLabel(_ model: String) -> String {
        let trimmedModel = trimmed(model)
        return trimmedModel.isEmpty ? "Backend default" : trimmedModel
    }

    static func subtitleTransliterationModelLabel(_ model: String) -> String {
        let trimmedModel = trimmed(model)
        return trimmedModel.isEmpty ? "Use translation model" : trimmedModel
    }

    static func availableSubtitleLlmModels(
        selected: String,
        inventory: [String]
    ) -> [String] {
        let selectedModel = trimmed(selected)
        var seen = Set<String>()
        var options: [String] = []

        if !selectedModel.isEmpty {
            seen.insert(selectedModel.lowercased())
            options.append(selectedModel)
        }

        for model in inventory {
            let trimmedModel = trimmed(model)
            guard !trimmedModel.isEmpty else { continue }
            if seen.insert(trimmedModel.lowercased()).inserted {
                options.append(trimmedModel)
            }
        }

        return options.isEmpty ? [""] : options
    }

    static func availableSubtitleTransliterationModels(
        selected: String,
        translationModel: String,
        inventory: [String]
    ) -> [String] {
        var seen = Set<String>()
        var options = [""]
        seen.insert("")

        for model in [selected, translationModel] + inventory {
            let trimmedModel = trimmed(model)
            guard !trimmedModel.isEmpty else { continue }
            if seen.insert(trimmedModel.lowercased()).inserted {
                options.append(trimmedModel)
            }
        }
        return options
    }

    static func formattedAssEmphasisScale(_ value: Double) -> String {
        clampAssEmphasisScale(value).formatted(.number.precision(.fractionLength(2)))
    }

    static func formattedYoutubeOriginalMixPercent(_ value: Double) -> String {
        "\(Int(clampYoutubeOriginalMixPercent(value).rounded()))%"
    }

    static func formatDurationLabel(seconds: Double) -> String {
        let totalSeconds = max(0, Int(seconds.rounded(.down)))
        let hours = totalSeconds / 3_600
        let minutes = (totalSeconds % 3_600) / 60
        let seconds = totalSeconds % 60
        return String(format: "%02d:%02d:%02d", hours, minutes, seconds)
    }

    static func estimatedAudioDurationLabel(sentenceCount: Int?) -> String? {
        guard let sentenceCount, sentenceCount > 0 else {
            return nil
        }
        let seconds = Double(sentenceCount) * AppleCreateEstimatedAudio.secondsPerSentence
        let sentenceLabel = sentenceCount == 1 ? "sentence" : "sentences"
        return "Estimated audio duration: ~\(formatDurationLabel(seconds: seconds)) (\(sentenceCount) \(sentenceLabel), 6.4s/sentence)"
    }

    static func estimatedNarrateSentenceCount(startSentence: String, endSentence: String) -> Int? {
        let normalizedStart = normalizedPositiveInteger(startSentence) ?? 1
        guard let normalizedEnd = normalizedEndSentence(endSentence, startSentence: normalizedStart) else {
            return nil
        }
        let count = normalizedEnd - normalizedStart + 1
        return count > 0 ? count : nil
    }

    static func clampAssFontSize(_ value: Int) -> Int {
        clamp(value, to: AppleSubtitleAssTypography.fontSizeRange)
    }

    static func clampAssEmphasisScale(_ value: Double) -> Double {
        clamp(value, to: AppleSubtitleAssTypography.emphasisScaleRange)
    }

    static func clampSubtitleTranslationBatchSize(_ value: Int) -> Int {
        clamp(value, to: AppleSubtitleTuning.translationBatchSizeRange)
    }

    static func clampSubtitleWorkerCount(_ value: Int) -> Int {
        clamp(value, to: AppleSubtitleTuning.workerCountRange)
    }

    static func clampSubtitleBatchSize(_ value: Int) -> Int {
        clamp(value, to: AppleSubtitleTuning.batchSizeRange)
    }

    static func clampYoutubeOriginalMixPercent(_ value: Double) -> Double {
        min(100, max(0, value))
    }

    static func clampYoutubeFlushSentences(_ value: Int) -> Int {
        min(200, max(1, value))
    }

    static func normalizeYoutubeOffset(_ value: String) -> String? {
        let trimmedValue = trimmed(value)
        if trimmedValue.isEmpty {
            return ""
        }
        if let seconds = Int(trimmedValue), seconds >= 0 {
            return "\(seconds)"
        }
        return SubtitleTimecodeInput.normalize(trimmedValue)
    }

    static func normalizedSubtitleTimeRange(
        start: String,
        end: String
    ) -> Result<AppleCreateTimeRange, AppleCreateValidationError> {
        guard let normalizedStart = SubtitleTimecodeInput.normalize(
            start,
            emptyValue: "00:00"
        ) else {
            return .failure(.subtitleStartTime)
        }
        guard let normalizedEnd = SubtitleTimecodeInput.normalize(
            end,
            allowRelative: true
        ) else {
            return .failure(.subtitleEndTime)
        }
        return .success(AppleCreateTimeRange(start: normalizedStart, end: normalizedEnd))
    }

    static func normalizedYoutubeOffsetRange(
        start: String,
        end: String
    ) -> Result<AppleCreateOffsetRange, AppleCreateValidationError> {
        guard let normalizedStart = normalizeYoutubeOffset(start) else {
            return .failure(.youtubeStartOffset)
        }
        guard let normalizedEnd = normalizeYoutubeOffset(end) else {
            return .failure(.youtubeEndOffset)
        }
        return .success(AppleCreateOffsetRange(start: normalizedStart, end: normalizedEnd))
    }

    static func generatedBookDraft(
        topic: String,
        bookName: String,
        genre: String,
        author: String,
        summary: String,
        year: String,
        isbn: String,
        coverFile: String,
        sentenceCount: Int,
        inputLanguage: AppleBookCreateLanguage,
        targetLanguage: AppleBookCreateLanguage,
        additionalTargetLanguages: String,
        voice: AppleBookCreateVoiceOption,
        targetVoice: AppleBookCreateVoiceOption?,
        languageVoiceOverrides: [String: String] = [:],
        baseOutput: String,
        generateAudio: Bool,
        audioMode: String,
        audioBitrateKbps: String,
        writtenMode: String,
        tempo: Double,
        sentencesPerOutputFile: Int,
        stitchFull: Bool,
        includeTransliteration: Bool,
        translationProvider: AppleSubtitleTranslationProvider,
        llmModel: String,
        translationBatchSize: Int,
        transliterationMode: AppleSubtitleTransliterationMode,
        transliterationModel: String,
        enableLookupCache: Bool,
        lookupCacheBatchSize: Int,
        outputHtml: Bool,
        outputPdf: Bool,
        includeImages: Bool,
        imagePromptPipeline: AppleGeneratedBookImagePromptPipeline,
        imageStyleTemplate: AppleGeneratedBookImageStyleTemplate,
        imagePromptBatchingEnabled: Bool,
        imagePromptBatchSize: Int,
        imagePromptPlanBatchSize: Int,
        imagePromptContextSentences: Int,
        imageWidth: String,
        imageHeight: String,
        imageSteps: String,
        imageCfgScale: String,
        imageSamplerName: String,
        imageSeedWithPreviousImage: Bool,
        imageBlankDetectionEnabled: Bool,
        imageApiBaseURLs: String,
        imageConcurrency: String,
        imageApiTimeoutSeconds: String,
        threadCount: String,
        queueSize: String,
        jobMaxWorkers: String,
        pipelineDefaults: BookCreationPipelineDefaults?,
        generatedSourceDefaults: BookCreationGeneratedSourceDefaults?
    ) -> AppleBookCreateDraft {
        let targetLanguageValue = targetLanguage.backendValue
        let targetLanguages = normalizedTargetLanguages(
            primary: targetLanguageValue,
            additionalTargets: additionalTargetLanguages
        )
        return AppleBookCreateDraft(
            topic: trimmed(topic),
            bookName: trimmed(bookName),
            genre: trimmed(genre),
            author: trimmed(author).nonEmptyValue ?? "Me",
            summary: trimmed(summary).nonEmptyValue,
            year: trimmed(year).nonEmptyValue,
            isbn: trimmed(isbn).nonEmptyValue,
            coverFile: trimmed(coverFile).nonEmptyValue,
            sentenceCount: sentenceCount,
            inputLanguage: inputLanguage.backendValue,
            targetLanguage: targetLanguageValue,
            targetLanguages: targetLanguages,
            voice: voice.backendValue,
            voiceOverrides: voiceOverrides(
                targetLanguages: targetLanguages,
                targetVoice: targetVoice,
                languageVoiceOverrides: languageVoiceOverrides
            ),
            baseOutput: baseOutput,
            generateAudio: generateAudio,
            audioMode: normalizedMode(audioMode, fallback: "4"),
            audioBitrateKbps: normalizedAudioBitrate(audioBitrateKbps),
            writtenMode: normalizedMode(writtenMode, fallback: "4"),
            tempo: clampTempo(tempo),
            sentencesPerOutputFile: clampBookSentencesPerOutputFile(sentencesPerOutputFile),
            stitchFull: stitchFull,
            includeTransliteration: includeTransliteration,
            translationProvider: translationProvider.backendValue,
            llmModel: translationProvider == .llm ? trimmed(llmModel).nonEmptyValue : nil,
            translationBatchSize: clampSubtitleTranslationBatchSize(translationBatchSize),
            transliterationMode: includeTransliteration ? transliterationMode.backendValue : "default",
            transliterationModel: includeTransliteration && transliterationMode.allowsModelOverride
                ? trimmed(transliterationModel).nonEmptyValue
                : nil,
            enableLookupCache: enableLookupCache,
            lookupCacheBatchSize: clampSubtitleTranslationBatchSize(lookupCacheBatchSize),
            outputHtml: outputHtml,
            outputPdf: outputPdf,
            includeImages: includeImages,
            imagePromptPipeline: imagePromptPipeline.backendValue,
            imageStyleTemplate: imageStyleTemplate.backendValue,
            imagePromptBatchingEnabled: imagePromptBatchingEnabled,
            imagePromptBatchSize: clampImagePromptBatchSize(imagePromptBatchSize),
            imagePromptPlanBatchSize: clampImagePromptBatchSize(imagePromptPlanBatchSize),
            imagePromptContextSentences: clampImagePromptContextSentences(imagePromptContextSentences),
            imageWidth: normalizedImageDimension(imageWidth),
            imageHeight: normalizedImageDimension(imageHeight),
            imageSteps: normalizedImageSteps(imageSteps),
            imageCfgScale: normalizedImageCfgScale(imageCfgScale),
            imageSamplerName: trimmed(imageSamplerName).nonEmptyValue,
            imageSeedWithPreviousImage: imageSeedWithPreviousImage,
            imageBlankDetectionEnabled: imageBlankDetectionEnabled,
            imageApiBaseURLs: normalizedImageApiBaseURLs(imageApiBaseURLs),
            imageConcurrency: normalizedPositiveInteger(imageConcurrency),
            imageApiTimeoutSeconds: normalizedPositiveNumber(imageApiTimeoutSeconds),
            threadCount: normalizedPositiveInteger(threadCount),
            queueSize: normalizedPositiveInteger(queueSize),
            jobMaxWorkers: normalizedPositiveInteger(jobMaxWorkers),
            pipelineDefaults: pipelineDefaults,
            generatedSourceDefaults: generatedSourceDefaults
        )
    }

    static func narrateEbookDraft(
        inputFile: String,
        baseOutput: String,
        title: String,
        author: String,
        genre: String,
        summary: String,
        year: String,
        isbn: String,
        coverFile: String,
        startSentence: String,
        endSentence: String,
        inputLanguage: AppleBookCreateLanguage,
        targetLanguage: AppleBookCreateLanguage,
        additionalTargetLanguages: String,
        voice: AppleBookCreateVoiceOption,
        targetVoice: AppleBookCreateVoiceOption?,
        languageVoiceOverrides: [String: String] = [:],
        generateAudio: Bool,
        audioMode: String,
        audioBitrateKbps: String,
        writtenMode: String,
        tempo: Double,
        sentencesPerOutputFile: Int,
        stitchFull: Bool,
        includeTransliteration: Bool,
        translationProvider: AppleSubtitleTranslationProvider,
        llmModel: String,
        translationBatchSize: Int,
        transliterationMode: AppleSubtitleTransliterationMode,
        transliterationModel: String,
        enableLookupCache: Bool,
        lookupCacheBatchSize: Int,
        outputHtml: Bool,
        outputPdf: Bool,
        threadCount: String,
        queueSize: String,
        jobMaxWorkers: String,
        pipelineDefaults: BookCreationPipelineDefaults?
    ) -> AppleNarrateEbookDraft {
        let normalizedStart = normalizedPositiveInteger(startSentence) ?? 1
        let targetLanguageValue = targetLanguage.backendValue
        let targetLanguages = normalizedTargetLanguages(
            primary: targetLanguageValue,
            additionalTargets: additionalTargetLanguages
        )
        return AppleNarrateEbookDraft(
            inputFile: trimmed(inputFile),
            baseOutput: trimmed(baseOutput),
            title: trimmed(title).nonEmptyValue,
            author: trimmed(author).nonEmptyValue,
            genre: trimmed(genre).nonEmptyValue,
            summary: trimmed(summary).nonEmptyValue,
            year: trimmed(year).nonEmptyValue,
            isbn: trimmed(isbn).nonEmptyValue,
            coverFile: trimmed(coverFile).nonEmptyValue,
            startSentence: normalizedStart,
            endSentence: normalizedEndSentence(endSentence, startSentence: normalizedStart),
            inputLanguage: inputLanguage.backendValue,
            targetLanguage: targetLanguageValue,
            targetLanguages: targetLanguages,
            voice: voice.backendValue,
            voiceOverrides: voiceOverrides(
                targetLanguages: targetLanguages,
                targetVoice: targetVoice,
                languageVoiceOverrides: languageVoiceOverrides
            ),
            generateAudio: generateAudio,
            audioMode: normalizedMode(audioMode, fallback: "4"),
            audioBitrateKbps: normalizedAudioBitrate(audioBitrateKbps),
            writtenMode: normalizedMode(writtenMode, fallback: "4"),
            tempo: clampTempo(tempo),
            sentencesPerOutputFile: clampBookSentencesPerOutputFile(sentencesPerOutputFile),
            stitchFull: stitchFull,
            includeTransliteration: includeTransliteration,
            translationProvider: translationProvider.backendValue,
            llmModel: translationProvider == .llm ? trimmed(llmModel).nonEmptyValue : nil,
            translationBatchSize: clampSubtitleTranslationBatchSize(translationBatchSize),
            transliterationMode: includeTransliteration ? transliterationMode.backendValue : "default",
            transliterationModel: includeTransliteration && transliterationMode.allowsModelOverride
                ? trimmed(transliterationModel).nonEmptyValue
                : nil,
            enableLookupCache: enableLookupCache,
            lookupCacheBatchSize: clampSubtitleTranslationBatchSize(lookupCacheBatchSize),
            outputHtml: outputHtml,
            outputPdf: outputPdf,
            threadCount: normalizedPositiveInteger(threadCount),
            queueSize: normalizedPositiveInteger(queueSize),
            jobMaxWorkers: normalizedPositiveInteger(jobMaxWorkers),
            pipelineDefaults: pipelineDefaults
        )
    }

    static func subtitleJobDraft(
        sourcePath: String,
        inputLanguage: AppleBookCreateLanguage,
        targetLanguage: AppleBookCreateLanguage,
        outputFormat: AppleSubtitleOutputFormat,
        startTime: String,
        endTime: String,
        enableTransliteration: Bool,
        highlight: Bool,
        showOriginal: Bool,
        generateAudioBook: Bool,
        mirrorBatchesToSourceDir: Bool,
        translationProvider: AppleSubtitleTranslationProvider,
        llmModel: String,
        transliterationMode: AppleSubtitleTransliterationMode,
        transliterationModel: String,
        workerCount: Int,
        batchSize: Int,
        translationBatchSize: Int,
        assFontSize: Int,
        assEmphasisScale: Double
    ) -> AppleSubtitleJobDraft {
        AppleSubtitleJobDraft(
            sourcePath: trimmed(sourcePath).nonEmptyValue,
            inputLanguage: inputLanguage.backendValue,
            targetLanguage: targetLanguage.backendValue,
            outputFormat: outputFormat.rawValue,
            startTime: startTime,
            endTime: endTime.nonEmptyValue,
            enableTransliteration: enableTransliteration,
            highlight: highlight,
            showOriginal: showOriginal,
            generateAudioBook: generateAudioBook,
            mirrorBatchesToSourceDir: mirrorBatchesToSourceDir,
            translationProvider: translationProvider.backendValue,
            llmModel: translationProvider == .llm ? trimmed(llmModel).nonEmptyValue : nil,
            transliterationMode: enableTransliteration ? transliterationMode.backendValue : nil,
            transliterationModel: enableTransliteration && transliterationMode.allowsModelOverride
                ? trimmed(transliterationModel).nonEmptyValue
                : nil,
            workerCount: clampSubtitleWorkerCount(workerCount),
            batchSize: clampSubtitleBatchSize(batchSize),
            translationBatchSize: clampSubtitleTranslationBatchSize(translationBatchSize),
            assFontSize: outputFormat == .ass ? clampAssFontSize(assFontSize) : nil,
            assEmphasisScale: outputFormat == .ass ? clampAssEmphasisScale(assEmphasisScale) : nil
        )
    }

    static func youtubeDubDraft(
        videoPath: String,
        subtitlePath: String,
        sourceLanguage: AppleBookCreateLanguage,
        subtitleLanguage: String?,
        targetLanguage: AppleBookCreateLanguage,
        voice: AppleBookCreateVoiceOption,
        startTimeOffset: String,
        endTimeOffset: String,
        originalMixPercent: Double,
        flushSentences: Int,
        translationProvider: AppleSubtitleTranslationProvider,
        llmModel: String,
        translationBatchSize: Int,
        transliterationMode: AppleSubtitleTransliterationMode,
        transliterationModel: String,
        splitBatches: Bool,
        stitchBatches: Bool,
        includeTransliteration: Bool,
        targetHeight: AppleYoutubeDubTargetHeight,
        preserveAspectRatio: Bool,
        enableLookupCache: Bool
    ) -> AppleYoutubeDubDraft {
        AppleYoutubeDubDraft(
            videoPath: trimmed(videoPath),
            subtitlePath: trimmed(subtitlePath),
            sourceLanguage: subtitleLanguage?.nonEmptyValue ?? sourceLanguage.backendValue,
            targetLanguage: targetLanguage.backendValue,
            voice: voice.backendValue,
            startTimeOffset: startTimeOffset.nonEmptyValue,
            endTimeOffset: endTimeOffset.nonEmptyValue,
            originalMixPercent: clampYoutubeOriginalMixPercent(originalMixPercent),
            flushSentences: clampYoutubeFlushSentences(flushSentences),
            llmModel: translationProvider == .llm ? trimmed(llmModel).nonEmptyValue : nil,
            translationProvider: translationProvider.backendValue,
            translationBatchSize: clampSubtitleTranslationBatchSize(translationBatchSize),
            transliterationMode: includeTransliteration ? transliterationMode.backendValue : nil,
            transliterationModel: includeTransliteration && transliterationMode.allowsModelOverride
                ? trimmed(transliterationModel).nonEmptyValue
                : nil,
            splitBatches: splitBatches,
            stitchBatches: splitBatches && stitchBatches,
            includeTransliteration: includeTransliteration,
            targetHeight: targetHeight.backendValue,
            preserveAspectRatio: preserveAspectRatio,
            enableLookupCache: enableLookupCache
        )
    }

    static func deriveBaseOutputName(_ value: String) -> String {
        let trimmedValue = trimmed(value)
        let withoutExtension = trimmedValue.replacingOccurrences(
            of: #"\.[^/.]+$"#,
            with: "",
            options: .regularExpression
        )
        let scalars = withoutExtension.unicodeScalars.map { scalar -> Character in
            CharacterSet.alphanumerics.contains(scalar) ? Character(scalar) : "-"
        }
        let collapsed = String(scalars)
            .split(separator: "-", omittingEmptySubsequences: true)
            .joined(separator: "-")
            .lowercased()
        return collapsed.nonEmptyValue ?? withoutExtension.nonEmptyValue ?? "generated-book"
    }

    private static func trimmed(_ value: String) -> String {
        value.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private static func availableLanguages(_ supported: [String]) -> [AppleBookCreateLanguage] {
        AppleBookCreateLanguage.options(from: supported)
    }

    private static func clamp<T: Comparable>(_ value: T, to range: ClosedRange<T>) -> T {
        min(range.upperBound, max(range.lowerBound, value))
    }
}

enum AppleYoutubeDubTargetHeight: Int, CaseIterable, Identifiable {
    case p320 = 320
    case p480 = 480
    case p720 = 720

    var id: Int { rawValue }
    var backendValue: Int { rawValue }

    var label: String {
        switch self {
        case .p320:
            return "320p"
        case .p480:
            return "480p"
        case .p720:
            return "720p"
        }
    }
}

enum AppleSubtitleOutputFormat: String, CaseIterable, Identifiable {
    case ass
    case srt

    var id: String { rawValue }

    var label: String {
        switch self {
        case .ass:
            return "ASS"
        case .srt:
            return "SRT"
        }
    }
}

enum AppleSubtitleTranslationProvider: String, CaseIterable, Identifiable {
    case llm
    case googleTranslate

    var id: String { rawValue }

    var backendValue: String {
        switch self {
        case .llm:
            return "llm"
        case .googleTranslate:
            return "googletrans"
        }
    }

    var label: String {
        switch self {
        case .llm:
            return "LLM"
        case .googleTranslate:
            return "Google Translate"
        }
    }

    init?(backendValue: String) {
        let normalized = backendValue.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        let dashed = normalized.replacingOccurrences(of: "_", with: "-")
        switch dashed {
        case "llm", "ollama", "default":
            self = .llm
        case "googletrans", "google", "googletranslate", "google-translate", "gtranslate", "gtrans":
            self = .googleTranslate
        default:
            return nil
        }
    }
}

enum AppleSubtitleTransliterationMode: String, CaseIterable, Identifiable {
    case `default`
    case python

    var id: String { rawValue }

    var backendValue: String {
        switch self {
        case .default:
            return "default"
        case .python:
            return "python"
        }
    }

    var label: String {
        switch self {
        case .default:
            return "Use selected LLM model"
        case .python:
            return "Python transliteration module"
        }
    }

    var allowsModelOverride: Bool {
        self != .python
    }

    init?(backendValue: String) {
        let normalized = backendValue.trimmingCharacters(in: .whitespacesAndNewlines)
            .lowercased()
            .replacingOccurrences(of: "_", with: "-")
        switch normalized {
        case "default", "llm", "ollama":
            self = .default
        case "python", "module", "python-module", "local-module":
            self = .python
        default:
            return nil
        }
    }
}

enum AppleSubtitleAssTypography {
    static let defaultFontSize = 56
    static let fontSizeRange = 12...120
    static let defaultEmphasisScale = 1.3
    static let emphasisScaleRange = 1.0...2.5
}

enum AppleSubtitleTuning {
    static let defaultWorkerCount = 10
    static let workerCountRange = 1...32
    static let defaultBatchSize = 20
    static let batchSizeRange = 1...500
    static let defaultTranslationBatchSize = 10
    static let translationBatchSizeRange = 1...50
}

enum AppleBookOutputChunking {
    static let defaultSentencesPerOutputFile = 10
    static let sentencesPerOutputFileRange = 1...100
}
