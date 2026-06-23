import Foundation

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

struct AppleCreateSubmitPresentation: Equatable {
    let title: String
    let systemImage: String
}

enum AppleBookCreatePresentation {
    static func availableCreateModes(isTV: Bool) -> [AppleCreateMode] {
        isTV ? [.generatedBook] : AppleCreateMode.allCases
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
        sentenceCount: Int,
        inputLanguage: AppleBookCreateLanguage,
        targetLanguage: AppleBookCreateLanguage,
        voice: AppleBookCreateVoiceOption,
        baseOutput: String,
        includeTransliteration: Bool,
        enableLookupCache: Bool,
        pipelineDefaults: BookCreationPipelineDefaults?,
        generatedSourceDefaults: BookCreationGeneratedSourceDefaults?
    ) -> AppleBookCreateDraft {
        AppleBookCreateDraft(
            topic: trimmed(topic),
            bookName: trimmed(bookName),
            genre: trimmed(genre),
            author: trimmed(author).nonEmptyValue ?? "Me",
            sentenceCount: sentenceCount,
            inputLanguage: inputLanguage.backendValue,
            targetLanguage: targetLanguage.backendValue,
            voice: voice.backendValue,
            baseOutput: baseOutput,
            includeTransliteration: includeTransliteration,
            enableLookupCache: enableLookupCache,
            pipelineDefaults: pipelineDefaults,
            generatedSourceDefaults: generatedSourceDefaults
        )
    }

    static func narrateEbookDraft(
        inputFile: String,
        baseOutput: String,
        inputLanguage: AppleBookCreateLanguage,
        targetLanguage: AppleBookCreateLanguage,
        voice: AppleBookCreateVoiceOption,
        includeTransliteration: Bool,
        enableLookupCache: Bool,
        pipelineDefaults: BookCreationPipelineDefaults?
    ) -> AppleNarrateEbookDraft {
        AppleNarrateEbookDraft(
            inputFile: trimmed(inputFile),
            baseOutput: trimmed(baseOutput),
            inputLanguage: inputLanguage.backendValue,
            targetLanguage: targetLanguage.backendValue,
            voice: voice.backendValue,
            includeTransliteration: includeTransliteration,
            enableLookupCache: enableLookupCache,
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
            sourceLanguage: sourceLanguage.backendValue,
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
        let scalars = trimmedValue.unicodeScalars.map { scalar -> Character in
            CharacterSet.alphanumerics.contains(scalar) ? Character(scalar) : "-"
        }
        let collapsed = String(scalars)
            .split(separator: "-", omittingEmptySubsequences: true)
            .joined(separator: "-")
            .lowercased()
        return collapsed.nonEmptyValue ?? "generated-book"
    }

    private static func trimmed(_ value: String) -> String {
        value.trimmingCharacters(in: .whitespacesAndNewlines)
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
        switch normalized {
        case "llm":
            self = .llm
        case "googletrans", "google", "google_translate", "google-translate":
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
