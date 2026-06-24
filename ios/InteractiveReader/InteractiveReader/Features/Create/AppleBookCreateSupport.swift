import Foundation

enum AppleBookCreatePresentation {
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
        sourceBookTitle: String,
        sourceBookAuthor: String,
        sourceBookGenre: String,
        sourceBookSummary: String,
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
            sourceBookTitle: trimmed(sourceBookTitle).nonEmptyValue,
            sourceBookAuthor: trimmed(sourceBookAuthor).nonEmptyValue,
            sourceBookGenre: trimmed(sourceBookGenre).nonEmptyValue,
            sourceBookSummary: trimmed(sourceBookSummary).nonEmptyValue,
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
        mediaMetadata: [String: JSONValue]?,
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
            mediaMetadata: normalizedSubtitleMediaMetadata(mediaMetadata),
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

    static func normalizedSubtitleMediaMetadata(_ value: [String: JSONValue]?) -> [String: JSONValue]? {
        guard var metadata = value, !metadata.isEmpty else {
            return nil
        }
        metadata["source"] = .string("apple")
        return metadata
    }

    static func youtubeDubDraft(
        videoPath: String,
        subtitlePath: String,
        sourceLanguage: AppleBookCreateLanguage,
        subtitleLanguage: String?,
        targetLanguage: AppleBookCreateLanguage,
        voice: AppleBookCreateVoiceOption,
        mediaMetadata: [String: JSONValue],
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
            mediaMetadata: normalizedYoutubeMediaMetadata(mediaMetadata),
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

    static func normalizedYoutubeMediaMetadata(_ value: [String: JSONValue]) -> [String: JSONValue] {
        var metadata = value
        metadata["source"] = .string("apple")
        return metadata
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

    private static func clamp<T: Comparable>(_ value: T, to range: ClosedRange<T>) -> T {
        min(range.upperBound, max(range.lowerBound, value))
    }
}
