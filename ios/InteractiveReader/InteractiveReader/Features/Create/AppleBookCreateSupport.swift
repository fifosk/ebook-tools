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
    let includeImages: Bool
    let imagePromptPipeline: String
    let imageStyleTemplate: String
    let imagePromptContextSentences: Int
    let imageWidth: String
    let imageHeight: String
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

enum AppleBookCreateEditedField: Hashable {
    case topic
    case bookName
    case genre
    case author
    case sourcePath
    case sourceBaseOutput
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
    case voice
    case includeTransliteration
    case enableLookupCache
    case includeImages
    case imagePromptPipeline
    case imageStyleTemplate
    case imagePromptContextSentences
    case imageWidth
    case imageHeight
}

struct AppleCreateResolvedDefaults: Equatable {
    let topic: String?
    let bookName: String?
    let genre: String?
    let author: String?
    let sentenceCount: Int
    let inputLanguage: AppleBookCreateLanguage?
    let targetLanguage: AppleBookCreateLanguage?
    let voice: AppleBookCreateVoiceOption?
    let includeTransliteration: Bool?
    let enableLookupCache: Bool?
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

struct AppleCreateSubmitPresentation: Equatable {
    let title: String
    let systemImage: String
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
    static func availableCreateModes(isTV: Bool) -> [AppleCreateMode] {
        isTV ? [.generatedBook] : AppleCreateMode.allCases
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
                : AppleBookCreateLanguage(backendValue: options.defaults.outputLanguage),
            voice: editedFields.contains(.voice)
                ? nil
                : AppleBookCreateVoiceOption(backendValue: options.defaults.voice),
            includeTransliteration: editedFields.contains(.includeTransliteration)
                ? nil
                : options.pipelineDefaults.includeTransliteration,
            enableLookupCache: editedFields.contains(.enableLookupCache)
                ? nil
                : options.pipelineDefaults.enableLookupCache,
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

    static func normalizedImageDimension(_ value: String) -> String {
        let trimmedValue = trimmed(value)
        guard let parsed = Double(trimmedValue), parsed.isFinite else {
            return "512"
        }
        return "\(max(64, Int(parsed.rounded(.down))))"
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
        selected: AppleBookCreateVoiceOption
    ) -> [AppleBookCreateVoiceOption] {
        AppleBookCreateVoiceOption.options(
            from: options?.supportedVoices ?? [],
            selected: selected
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
        includeImages: Bool,
        imagePromptPipeline: AppleGeneratedBookImagePromptPipeline,
        imageStyleTemplate: AppleGeneratedBookImageStyleTemplate,
        imagePromptContextSentences: Int,
        imageWidth: String,
        imageHeight: String,
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
            includeImages: includeImages,
            imagePromptPipeline: imagePromptPipeline.backendValue,
            imageStyleTemplate: imageStyleTemplate.backendValue,
            imagePromptContextSentences: clampImagePromptContextSentences(imagePromptContextSentences),
            imageWidth: normalizedImageDimension(imageWidth),
            imageHeight: normalizedImageDimension(imageHeight),
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

    private static func availableLanguages(_ supported: [String]) -> [AppleBookCreateLanguage] {
        let mapped = supported.compactMap(AppleBookCreateLanguage.init(backendValue:))
        return mapped.isEmpty ? AppleBookCreateLanguage.allCases : mapped
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
