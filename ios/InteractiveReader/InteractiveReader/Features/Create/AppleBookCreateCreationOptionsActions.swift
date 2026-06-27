import Foundation

extension AppleBookCreateView {
    var sentenceBounds: BookCreationSentenceBounds {
        viewModel.creationOptions?.sentenceBounds ?? BookCreationSentenceBounds(min: 1, max: 500, default: 30)
    }

    func refreshCreationOptions(force: Bool = false) async {
        guard let options = await viewModel.loadCreationOptions(
            using: appState,
            cacheKey: creationOptionsLoadKey,
            force: force
        ) else {
            return
        }
        applyCreationOptions(options)
        applyStoredLanguagePreferences()
    }

    func persistLanguagePreferences() {
        let preferences = AppleBookCreatePresentation.languagePreferences(
            inputLanguage: inputLanguage,
            targetLanguage: targetLanguage,
            additionalTargetLanguages: additionalTargetLanguages,
            enableLookupCache: enableLookupCache
        )
        preferenceScope.persistLanguagePreferences(preferences)
    }

    func clampSentenceCount(_ value: Int) -> Int {
        AppleBookCreatePresentation.clampSentenceCount(value, bounds: sentenceBounds)
    }

    private func applyStoredLanguagePreferences() {
        guard
            let preferences = preferenceScope.storedLanguagePreferences(),
            let resolved = AppleBookCreatePresentation.resolvedLanguagePreferences(from: preferences)
        else {
            return
        }

        if !editedFields.contains(.inputLanguage),
           let inputLanguage = resolved.inputLanguage {
            self.inputLanguage = inputLanguage
        }
        if !editedFields.contains(.targetLanguage),
           let targetLanguage = resolved.targetLanguage {
            self.targetLanguage = targetLanguage
        }
        if !editedFields.contains(.additionalTargetLanguages),
           let additionalTargetLanguages = resolved.additionalTargetLanguages {
            self.additionalTargetLanguages = additionalTargetLanguages
        }
        if !editedFields.contains(.enableLookupCache),
           let enableLookupCache = resolved.enableLookupCache {
            self.enableLookupCache = enableLookupCache
        }
    }

    private func applyCreationOptions(_ options: BookCreationOptionsResponse) {
        let defaults = AppleBookCreatePresentation.resolvedDefaults(
            from: options,
            editedFields: editedFields,
            currentSentenceCount: sentenceCount
        )
        if let value = defaults.topic {
            topic = value
        }
        if let value = defaults.bookName {
            bookName = value
        }
        if let value = defaults.genre {
            genre = value
        }
        if let value = defaults.author {
            author = value
        }
        sentenceCount = defaults.sentenceCount
        if let language = defaults.inputLanguage {
            inputLanguage = language
        }
        if let language = defaults.targetLanguage {
            targetLanguage = language
        }
        if let value = defaults.additionalTargetLanguages {
            additionalTargetLanguages = value
        }
        if let option = defaults.voice {
            voice = option
        }
        if let value = defaults.generateAudio {
            generateAudio = value
        }
        if let value = defaults.audioMode {
            audioMode = value
        }
        if let value = defaults.audioBitrateKbps {
            audioBitrateKbps = value
        }
        if let value = defaults.writtenMode {
            writtenMode = value
        }
        if let value = defaults.tempo {
            tempo = value
        }
        if let value = defaults.bookSentencesPerOutputFile {
            bookSentencesPerOutputFile = value
        }
        if let value = defaults.bookSentenceSplitterMode {
            bookSentenceSplitterMode = value
        }
        if let value = defaults.stitchFull {
            stitchFull = value
        }
        if let value = defaults.includeTransliteration {
            includeTransliteration = value
            if !editedFields.contains(.youtubeIncludeTransliteration) {
                youtubeIncludeTransliteration = value
            }
        }
        if let provider = defaults.bookTranslationProvider {
            bookTranslationProvider = provider
        }
        if let value = defaults.bookTranslationBatchSize {
            bookTranslationBatchSize = value
        }
        if let mode = defaults.bookTransliterationMode {
            bookTransliterationMode = mode
        }
        if let value = defaults.enableLookupCache {
            enableLookupCache = value
            if !editedFields.contains(.youtubeEnableLookupCache) {
                youtubeEnableLookupCache = value
            }
        }
        if let value = defaults.bookLookupCacheBatchSize {
            bookLookupCacheBatchSize = value
        }
        if let value = defaults.outputHtml {
            outputHtml = value
        }
        if let value = defaults.outputPdf {
            outputPdf = value
        }
        if let value = defaults.includeImages {
            includeImages = value
        }
        if let value = defaults.imagePromptPipeline {
            imagePromptPipeline = value
        }
        if let value = defaults.imageStyleTemplate {
            imageStyleTemplate = value
        }
        if let value = defaults.imagePromptContextSentences {
            imagePromptContextSentences = value
        }
        if let value = defaults.imageWidth {
            imageWidth = value
        }
        if let value = defaults.imageHeight {
            imageHeight = value
        }
        if let provider = defaults.subtitleTranslationProvider {
            subtitleTranslationProvider = provider
        }
        if let value = defaults.subtitleWorkerCount {
            subtitleWorkerCount = value
        }
        if let value = defaults.subtitleBatchSize {
            subtitleBatchSize = value
        }
        if let value = defaults.subtitleTranslationBatchSize {
            subtitleTranslationBatchSize = value
        }
        if let value = defaults.subtitleAssFontSize {
            subtitleAssFontSize = value
        }
        if let value = defaults.subtitleAssEmphasisScale {
            subtitleAssEmphasisScale = value
        }
        if let value = defaults.youtubeOriginalMixPercent {
            youtubeOriginalMixPercent = value
        }
        if let value = defaults.youtubeFlushSentences {
            youtubeFlushSentences = value
        }
        if let value = defaults.youtubeTargetHeight {
            youtubeTargetHeight = value
        }
        if let value = defaults.youtubePreserveAspectRatio {
            youtubePreserveAspectRatio = value
        }
        if let value = defaults.youtubeSplitBatches {
            youtubeSplitBatches = value
        }
        if let value = defaults.youtubeStitchBatches {
            youtubeStitchBatches = value
        }
    }
}
