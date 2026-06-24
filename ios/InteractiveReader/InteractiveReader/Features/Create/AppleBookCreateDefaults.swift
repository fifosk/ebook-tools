import Foundation

extension AppleBookCreatePresentation {
    static func resolvedDefaults(
        from options: BookCreationOptionsResponse,
        editedFields: Set<AppleBookCreateEditedField>,
        currentSentenceCount: Int
    ) -> AppleCreateResolvedDefaults {
        AppleCreateResolvedDefaults(
            topic: editedFields.contains(.topic) ? nil : normalizedDefaultText(options.defaults.topic).nonEmptyValue,
            bookName: editedFields.contains(.bookName) ? nil : normalizedDefaultText(options.defaults.bookName).nonEmptyValue,
            genre: editedFields.contains(.genre) ? nil : normalizedDefaultText(options.defaults.genre).nonEmptyValue,
            author: editedFields.contains(.author)
                ? nil
                : (normalizedDefaultText(options.defaults.author).nonEmptyValue ?? "Me"),
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
                : AppleSubtitleTranslationProvider(backendValue: options.pipelineDefaults.translationProvider),
            subtitleWorkerCount: editedFields.contains(.subtitleWorkerCount)
                ? nil
                : options.subtitleDefaults.map { clampSubtitleWorkerCount($0.workerCount) },
            subtitleBatchSize: editedFields.contains(.subtitleBatchSize)
                ? nil
                : options.subtitleDefaults.map { clampSubtitleBatchSize($0.batchSize) },
            subtitleTranslationBatchSize: editedFields.contains(.subtitleTranslationBatchSize)
                ? nil
                : (
                    options.subtitleDefaults.map { clampSubtitleTranslationBatchSize($0.translationBatchSize) }
                        ?? options.youtubeDubDefaults.map { clampSubtitleTranslationBatchSize($0.translationBatchSize) }
                ),
            subtitleAssFontSize: editedFields.contains(.subtitleAssFontSize)
                ? nil
                : options.subtitleDefaults.map { clampAssFontSize($0.assFontSize) },
            subtitleAssEmphasisScale: editedFields.contains(.subtitleAssEmphasisScale)
                ? nil
                : options.subtitleDefaults.map { clampAssEmphasisScale($0.assEmphasisScale) },
            youtubeOriginalMixPercent: editedFields.contains(.youtubeOriginalMixPercent)
                ? nil
                : options.youtubeDubDefaults.map { clampYoutubeOriginalMixPercent($0.originalMixPercent) },
            youtubeFlushSentences: editedFields.contains(.youtubeFlushSentences)
                ? nil
                : options.youtubeDubDefaults.map { clampYoutubeFlushSentences($0.flushSentences) },
            youtubeTargetHeight: editedFields.contains(.youtubeTargetHeight)
                ? nil
                : options.youtubeDubDefaults.flatMap { AppleYoutubeDubTargetHeight(rawValue: $0.targetHeight) },
            youtubePreserveAspectRatio: editedFields.contains(.youtubePreserveAspectRatio)
                ? nil
                : options.youtubeDubDefaults?.preserveAspectRatio,
            youtubeSplitBatches: editedFields.contains(.youtubeSplitBatches)
                ? nil
                : options.youtubeDubDefaults?.splitBatches,
            youtubeStitchBatches: editedFields.contains(.youtubeStitchBatches)
                ? nil
                : options.youtubeDubDefaults?.stitchBatches
        )
    }

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
            let language = normalizedDefaultText(targetLanguage)
            guard !language.isEmpty else { continue }
            normalizedTargets.insert(language.lowercased())
            if let targetVoice {
                overrides[language] = targetVoice.backendValue
            }
        }

        for (targetLanguage, voice) in languageVoiceOverrides {
            let language = normalizedDefaultText(targetLanguage)
            let voiceValue = normalizedDefaultText(voice)
            guard !language.isEmpty, !voiceValue.isEmpty else { continue }
            guard normalizedTargets.contains(language.lowercased()) else { continue }
            overrides[language] = voiceValue
        }
        return overrides
    }

    static func voiceOverridePipelineValue(_ voiceOverrides: [String: String]) -> JSONValue? {
        var normalized = [String: JSONValue]()
        for (key, value) in voiceOverrides {
            let language = normalizedDefaultText(key)
            let voice = normalizedDefaultText(value)
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
        let primaryTarget = normalizedDefaultText(primary)
        guard !primaryTarget.isEmpty else { return [] }

        var seen = Set<String>()
        seen.insert(primaryTarget.lowercased())
        var targetLanguages = [primaryTarget]

        for candidate in additionalTargets.components(separatedBy: CharacterSet(charactersIn: ",\n")) {
            let target = normalizedDefaultText(candidate)
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
            let value = normalizedDefaultText(language)
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
            let genre = normalizedDefaultText(String(component))
            guard !genre.isEmpty else { continue }
            let lookupKey = genre.lowercased()
            guard seen.insert(lookupKey).inserted else { continue }
            genres.append(genre)
        }
        return genres
    }

    private static func normalizedDefaultText(_ value: String) -> String {
        value.trimmingCharacters(in: .whitespacesAndNewlines)
    }
}
