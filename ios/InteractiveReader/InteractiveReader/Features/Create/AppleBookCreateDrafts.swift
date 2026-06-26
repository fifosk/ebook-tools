import Foundation

extension AppleBookCreatePresentation {
    static func generatedBookDraft(
        topic: String,
        bookName: String,
        genre: String,
        author: String,
        summary: String,
        year: String,
        isbn: String,
        coverFile: String,
        bookMetadataExtras: [String: JSONValue] = [:],
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
        sentenceSplitterMode: AppleBookSentenceSplitterMode,
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
            topic: normalizedDraftText(topic),
            bookName: normalizedDraftText(bookName),
            genre: normalizedDraftText(genre),
            author: normalizedDraftText(author).nonEmptyValue ?? "Me",
            summary: normalizedDraftText(summary).nonEmptyValue,
            year: normalizedDraftText(year).nonEmptyValue,
            isbn: normalizedDraftText(isbn).nonEmptyValue,
            coverFile: normalizedDraftText(coverFile).nonEmptyValue,
            bookMetadataExtras: normalizedBookMetadataExtras(bookMetadataExtras),
            sourceBookTitle: normalizedDraftText(sourceBookTitle).nonEmptyValue,
            sourceBookAuthor: normalizedDraftText(sourceBookAuthor).nonEmptyValue,
            sourceBookGenre: normalizedDraftText(sourceBookGenre).nonEmptyValue,
            sourceBookSummary: normalizedDraftText(sourceBookSummary).nonEmptyValue,
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
            sentenceSplitterMode: sentenceSplitterMode.backendValue,
            stitchFull: stitchFull,
            includeTransliteration: includeTransliteration,
            translationProvider: translationProvider.backendValue,
            llmModel: translationProvider == .llm ? normalizedDraftText(llmModel).nonEmptyValue : nil,
            translationBatchSize: clampSubtitleTranslationBatchSize(translationBatchSize),
            transliterationMode: includeTransliteration ? transliterationMode.backendValue : "default",
            transliterationModel: includeTransliteration && transliterationMode.allowsModelOverride
                ? normalizedDraftText(transliterationModel).nonEmptyValue
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
            imageSamplerName: normalizedDraftText(imageSamplerName).nonEmptyValue,
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
        bookMetadataExtras: [String: JSONValue] = [:],
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
        sentenceSplitterMode: AppleBookSentenceSplitterMode,
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
            inputFile: normalizedDraftText(inputFile),
            baseOutput: normalizedDraftText(baseOutput),
            title: normalizedDraftText(title).nonEmptyValue,
            author: normalizedDraftText(author).nonEmptyValue,
            genre: normalizedDraftText(genre).nonEmptyValue,
            summary: normalizedDraftText(summary).nonEmptyValue,
            year: normalizedDraftText(year).nonEmptyValue,
            isbn: normalizedDraftText(isbn).nonEmptyValue,
            coverFile: normalizedDraftText(coverFile).nonEmptyValue,
            bookMetadataExtras: normalizedBookMetadataExtras(bookMetadataExtras),
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
            sentenceSplitterMode: sentenceSplitterMode.backendValue,
            stitchFull: stitchFull,
            includeTransliteration: includeTransliteration,
            translationProvider: translationProvider.backendValue,
            llmModel: translationProvider == .llm ? normalizedDraftText(llmModel).nonEmptyValue : nil,
            translationBatchSize: clampSubtitleTranslationBatchSize(translationBatchSize),
            transliterationMode: includeTransliteration ? transliterationMode.backendValue : "default",
            transliterationModel: includeTransliteration && transliterationMode.allowsModelOverride
                ? normalizedDraftText(transliterationModel).nonEmptyValue
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

    static func normalizedBookMetadataExtras(_ extras: [String: JSONValue]) -> [String: JSONValue] {
        var normalized = [String: JSONValue]()
        for (key, value) in extras {
            let trimmedKey = key.trimmingCharacters(in: .whitespacesAndNewlines)
            guard !trimmedKey.isEmpty,
                  !isSensitiveBookMetadataExtraKey(trimmedKey),
                  let value = normalizedBookMetadataExtraValue(value) else {
                continue
            }
            normalized[trimmedKey] = value
        }
        return normalized
    }

    private static func isSensitiveBookMetadataExtraKey(_ key: String) -> Bool {
        let normalized = key
            .replacingOccurrences(of: "-", with: "")
            .replacingOccurrences(of: "_", with: "")
            .lowercased()
        return [
            "password",
            "secret",
            "token",
            "authorization",
            "authheader",
            "apikey",
        ].contains { normalized.contains($0) }
    }

    private static func normalizedBookMetadataExtraValue(_ value: JSONValue) -> JSONValue? {
        switch value {
        case let .string(string):
            let trimmed = string.trimmingCharacters(in: .whitespacesAndNewlines)
            return trimmed.isEmpty ? nil : .string(trimmed)
        case let .number(number):
            return number.isFinite ? .number(number) : nil
        case let .bool(bool):
            return .bool(bool)
        case let .object(object):
            let normalized = normalizedBookMetadataExtras(object)
            return normalized.isEmpty ? nil : .object(normalized)
        case let .array(values):
            let normalized = values.compactMap(normalizedBookMetadataExtraValue)
            return normalized.isEmpty ? nil : .array(normalized)
        case .null:
            return nil
        }
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
            sourcePath: normalizedDraftText(sourcePath).nonEmptyValue,
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
            llmModel: translationProvider == .llm ? normalizedDraftText(llmModel).nonEmptyValue : nil,
            transliterationMode: enableTransliteration ? transliterationMode.backendValue : nil,
            transliterationModel: enableTransliteration && transliterationMode.allowsModelOverride
                ? normalizedDraftText(transliterationModel).nonEmptyValue
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
        videoDiscoveryState: [String: JSONValue]? = nil,
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
            videoPath: normalizedDraftText(videoPath),
            subtitlePath: normalizedDraftText(subtitlePath),
            mediaMetadata: normalizedYoutubeMediaMetadata(mediaMetadata),
            videoDiscoveryState: normalizedVideoDiscoveryState(videoDiscoveryState),
            sourceLanguage: subtitleLanguage?.nonEmptyValue ?? sourceLanguage.backendValue,
            targetLanguage: targetLanguage.backendLanguageCode,
            voice: voice.backendValue,
            startTimeOffset: startTimeOffset.nonEmptyValue,
            endTimeOffset: endTimeOffset.nonEmptyValue,
            originalMixPercent: clampYoutubeOriginalMixPercent(originalMixPercent),
            flushSentences: clampYoutubeFlushSentences(flushSentences),
            llmModel: translationProvider == .llm ? normalizedDraftText(llmModel).nonEmptyValue : nil,
            translationProvider: translationProvider.backendValue,
            translationBatchSize: clampSubtitleTranslationBatchSize(translationBatchSize),
            transliterationMode: includeTransliteration ? transliterationMode.backendValue : nil,
            transliterationModel: includeTransliteration && transliterationMode.allowsModelOverride
                ? normalizedDraftText(transliterationModel).nonEmptyValue
                : nil,
            splitBatches: splitBatches,
            stitchBatches: splitBatches && stitchBatches,
            includeTransliteration: includeTransliteration,
            targetHeight: targetHeight.backendValue,
            preserveAspectRatio: preserveAspectRatio,
            enableLookupCache: enableLookupCache
        )
    }

    static func normalizedVideoDiscoveryState(_ value: [String: JSONValue]?) -> [String: JSONValue]? {
        guard let value else { return nil }
        var normalized = [String: JSONValue]()
        for (key, jsonValue) in value {
            let trimmedKey = key.trimmingCharacters(in: .whitespacesAndNewlines)
            guard !trimmedKey.isEmpty else { continue }
            let lowered = trimmedKey.lowercased()
            guard !lowered.contains("token") else { continue }
            guard let normalizedValue = normalizedBookMetadataExtraValue(jsonValue) else { continue }
            normalized[trimmedKey] = normalizedValue
        }
        return normalized.isEmpty ? nil : normalized
    }

    static func normalizedYoutubeMediaMetadata(_ value: [String: JSONValue]) -> [String: JSONValue] {
        var metadata = value
        metadata["source"] = .string("apple")
        return metadata
    }

    static func deriveBaseOutputName(_ value: String) -> String {
        let trimmedValue = normalizedDraftText(value)
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

    private static func normalizedDraftText(_ value: String) -> String {
        value.trimmingCharacters(in: .whitespacesAndNewlines)
    }
}
