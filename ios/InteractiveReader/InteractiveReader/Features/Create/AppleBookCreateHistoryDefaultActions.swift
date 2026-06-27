import SwiftUI

extension AppleBookCreateView {
    func applyHistoryDefaultsForCurrentMode() {
        switch creationMode {
        case .generatedBook:
            applyGeneratedBookHistoryDefaults()
        case .narrateEbook:
            applyNarrationHistoryDefaults()
        case .subtitleJob:
            applySubtitleHistoryDefaults()
        case .youtubeDub:
            applyYoutubeHistoryDefaults()
        }
    }

    private func applyGeneratedBookHistoryDefaults() {
        guard let defaults = AppleBookCreatePresentation.generatedBookHistoryDefaults(from: recentJobs) else {
            return
        }

        if !editedFields.contains(.topic),
           let value = defaults.topic?.nonEmptyValue {
            topic = value
        }
        if !editedFields.contains(.bookName),
           let value = defaults.bookName?.nonEmptyValue {
            bookName = value
        }
        if !editedFields.contains(.genre),
           let value = defaults.genre?.nonEmptyValue {
            genre = value
        }
        if !editedFields.contains(.author),
           let value = defaults.author?.nonEmptyValue {
            author = value
        }
        if !editedFields.contains(.sourceBookTitle),
           let value = defaults.sourceBookTitle?.nonEmptyValue {
            sourceBookTitle = value
        }
        if !editedFields.contains(.sourceBookAuthor),
           let value = defaults.sourceBookAuthor?.nonEmptyValue {
            sourceBookAuthor = value
        }
        if !editedFields.contains(.sourceBookGenre),
           let value = defaults.sourceBookGenre?.nonEmptyValue {
            sourceBookGenre = value
        }
        if !editedFields.contains(.sourceBookSummary),
           let value = defaults.sourceBookSummary?.nonEmptyValue {
            sourceBookSummary = value
        }
        if !editedFields.contains(.sentenceCount),
           let value = defaults.sentenceCount {
            sentenceCount = clampSentenceCount(value)
        }
        if !editedFields.contains(.inputLanguage),
           let inputLanguage = defaults.inputLanguage {
            self.inputLanguage = inputLanguage
        }
        if !editedFields.contains(.targetLanguage),
           let targetLanguage = defaults.targetLanguage {
            self.targetLanguage = targetLanguage
        }
        if !editedFields.contains(.additionalTargetLanguages),
           let additionalTargetLanguages = defaults.additionalTargetLanguages {
            self.additionalTargetLanguages = additionalTargetLanguages
        }
        if !editedFields.contains(.voice),
           let voice = defaults.voice {
            self.voice = voice
        }
        if !editedFields.contains(.languageVoiceOverrides),
           let voiceOverrides = defaults.voiceOverrides,
           !voiceOverrides.isEmpty {
            languageVoiceOverrides = voiceOverrides
        }
        if !editedFields.contains(.generateAudio),
           let generateAudio = defaults.generateAudio {
            self.generateAudio = generateAudio
        }
        if !editedFields.contains(.audioMode),
           let audioMode = defaults.audioMode?.nonEmptyValue {
            self.audioMode = audioMode
        }
        if !editedFields.contains(.audioBitrateKbps),
           let audioBitrateKbps = defaults.audioBitrateKbps?.nonEmptyValue {
            self.audioBitrateKbps = audioBitrateKbps
        }
        if !editedFields.contains(.writtenMode),
           let writtenMode = defaults.writtenMode?.nonEmptyValue {
            self.writtenMode = writtenMode
        }
        if !editedFields.contains(.tempo),
           let tempo = defaults.tempo {
            self.tempo = tempo
        }
        if !editedFields.contains(.bookSentencesPerOutputFile),
           let bookSentencesPerOutputFile = defaults.bookSentencesPerOutputFile {
            self.bookSentencesPerOutputFile = bookSentencesPerOutputFile
        }
        if !editedFields.contains(.bookSentenceSplitterMode),
           let bookSentenceSplitterMode = defaults.bookSentenceSplitterMode {
            self.bookSentenceSplitterMode = bookSentenceSplitterMode
        }
        if !editedFields.contains(.stitchFull),
           let stitchFull = defaults.stitchFull {
            self.stitchFull = stitchFull
        }
        if !editedFields.contains(.includeTransliteration),
           let includeTransliteration = defaults.includeTransliteration {
            self.includeTransliteration = includeTransliteration
        }
        if !editedFields.contains(.bookTranslationProvider),
           let bookTranslationProvider = defaults.bookTranslationProvider {
            self.bookTranslationProvider = bookTranslationProvider
        }
        if !editedFields.contains(.bookLlmModel),
           let bookLlmModel = defaults.bookLlmModel?.nonEmptyValue {
            self.bookLlmModel = bookLlmModel
        }
        if !editedFields.contains(.bookTranslationBatchSize),
           let bookTranslationBatchSize = defaults.bookTranslationBatchSize {
            self.bookTranslationBatchSize = bookTranslationBatchSize
        }
        if !editedFields.contains(.bookTransliterationMode),
           let bookTransliterationMode = defaults.bookTransliterationMode {
            self.bookTransliterationMode = bookTransliterationMode
        }
        if !editedFields.contains(.bookTransliterationModel),
           let bookTransliterationModel = defaults.bookTransliterationModel?.nonEmptyValue {
            self.bookTransliterationModel = bookTransliterationModel
        }
        if !editedFields.contains(.enableLookupCache),
           let enableLookupCache = defaults.enableLookupCache {
            self.enableLookupCache = enableLookupCache
        }
        if !editedFields.contains(.bookLookupCacheBatchSize),
           let bookLookupCacheBatchSize = defaults.bookLookupCacheBatchSize {
            self.bookLookupCacheBatchSize = bookLookupCacheBatchSize
        }
        if !editedFields.contains(.outputHtml),
           let outputHtml = defaults.outputHtml {
            self.outputHtml = outputHtml
        }
        if !editedFields.contains(.outputPdf),
           let outputPdf = defaults.outputPdf {
            self.outputPdf = outputPdf
        }
        if !editedFields.contains(.includeImages),
           let includeImages = defaults.includeImages {
            self.includeImages = includeImages
        }
        if !editedFields.contains(.imagePromptPipeline),
           let imagePromptPipeline = defaults.imagePromptPipeline {
            self.imagePromptPipeline = imagePromptPipeline
        }
        if !editedFields.contains(.imageStyleTemplate),
           let imageStyleTemplate = defaults.imageStyleTemplate {
            self.imageStyleTemplate = imageStyleTemplate
        }
        if !editedFields.contains(.imagePromptContextSentences),
           let imagePromptContextSentences = defaults.imagePromptContextSentences {
            self.imagePromptContextSentences = imagePromptContextSentences
        }
        if !editedFields.contains(.imageWidth),
           let imageWidth = defaults.imageWidth?.nonEmptyValue {
            self.imageWidth = imageWidth
        }
        if !editedFields.contains(.imageHeight),
           let imageHeight = defaults.imageHeight?.nonEmptyValue {
            self.imageHeight = imageHeight
        }
    }

    private func applyNarrationHistoryDefaults() {
        guard let defaults = AppleBookCreatePresentation.narrationHistoryDefaults(
            from: recentJobs,
            currentInputFile: sourcePath
        ) else {
            return
        }

        if selectedNarrateFileURL == nil,
           !editedFields.contains(.sourcePath),
           let inputFile = defaults.inputFile?.nonEmptyValue {
            if sourcePath != inputFile {
                sourcePath = inputFile
                clearNarrateSourceMetadata()
            }
        }
        if !editedFields.contains(.sourceBaseOutput),
           let baseOutput = defaults.baseOutput?.nonEmptyValue {
            sourceBaseOutput = baseOutput
        }
        if !editedFields.contains(.sourceStartSentence),
           let startSentence = defaults.startSentence {
            sourceStartSentence = "\(startSentence)"
        }
        if !editedFields.contains(.inputLanguage),
           let inputLanguage = defaults.inputLanguage {
            self.inputLanguage = inputLanguage
        }
        if !editedFields.contains(.targetLanguage),
           let targetLanguage = defaults.targetLanguage {
            self.targetLanguage = targetLanguage
        }
        if !editedFields.contains(.additionalTargetLanguages),
           let additionalTargetLanguages = defaults.additionalTargetLanguages {
            self.additionalTargetLanguages = additionalTargetLanguages
        }
        if !editedFields.contains(.voice),
           let voice = defaults.voice {
            self.voice = voice
        }
        if !editedFields.contains(.languageVoiceOverrides),
           let voiceOverrides = defaults.voiceOverrides,
           !voiceOverrides.isEmpty {
            languageVoiceOverrides = voiceOverrides
        }
        if !editedFields.contains(.generateAudio),
           let generateAudio = defaults.generateAudio {
            self.generateAudio = generateAudio
        }
        if !editedFields.contains(.audioMode),
           let audioMode = defaults.audioMode?.nonEmptyValue {
            self.audioMode = audioMode
        }
        if !editedFields.contains(.audioBitrateKbps),
           let audioBitrateKbps = defaults.audioBitrateKbps?.nonEmptyValue {
            self.audioBitrateKbps = audioBitrateKbps
        }
        if !editedFields.contains(.writtenMode),
           let writtenMode = defaults.writtenMode?.nonEmptyValue {
            self.writtenMode = writtenMode
        }
        if !editedFields.contains(.tempo),
           let tempo = defaults.tempo {
            self.tempo = tempo
        }
        if !editedFields.contains(.bookSentencesPerOutputFile),
           let sentencesPerOutputFile = defaults.sentencesPerOutputFile {
            bookSentencesPerOutputFile = sentencesPerOutputFile
        }
        if !editedFields.contains(.bookSentenceSplitterMode),
           let sentenceSplitterMode = defaults.sentenceSplitterMode {
            bookSentenceSplitterMode = sentenceSplitterMode
        }
        if !editedFields.contains(.stitchFull),
           let stitchFull = defaults.stitchFull {
            self.stitchFull = stitchFull
        }
        if !editedFields.contains(.includeTransliteration),
           let includeTransliteration = defaults.includeTransliteration {
            self.includeTransliteration = includeTransliteration
        }
        if !editedFields.contains(.bookTranslationProvider),
           let translationProvider = defaults.translationProvider {
            bookTranslationProvider = translationProvider
        }
        if !editedFields.contains(.bookLlmModel),
           let llmModel = defaults.llmModel?.nonEmptyValue {
            bookLlmModel = llmModel
        }
        if !editedFields.contains(.bookTranslationBatchSize),
           let translationBatchSize = defaults.translationBatchSize {
            bookTranslationBatchSize = translationBatchSize
        }
        if !editedFields.contains(.bookTransliterationMode),
           let transliterationMode = defaults.transliterationMode {
            bookTransliterationMode = transliterationMode
        }
        if !editedFields.contains(.bookTransliterationModel),
           let transliterationModel = defaults.transliterationModel?.nonEmptyValue {
            bookTransliterationModel = transliterationModel
        }
        if !editedFields.contains(.enableLookupCache),
           let enableLookupCache = defaults.enableLookupCache {
            self.enableLookupCache = enableLookupCache
        }
        if !editedFields.contains(.bookLookupCacheBatchSize),
           let lookupCacheBatchSize = defaults.lookupCacheBatchSize {
            bookLookupCacheBatchSize = lookupCacheBatchSize
        }
        if !editedFields.contains(.outputHtml),
           let outputHtml = defaults.outputHtml {
            self.outputHtml = outputHtml
        }
        if !editedFields.contains(.outputPdf),
           let outputPdf = defaults.outputPdf {
            self.outputPdf = outputPdf
        }
    }

    private func applySubtitleHistoryDefaults() {
        guard let defaults = AppleBookCreatePresentation.subtitleHistoryDefaults(from: recentJobs) else {
            return
        }

        if selectedSubtitleFileURL == nil,
           !editedFields.contains(.subtitleSourcePath),
           trimmed(subtitleSourcePath).isEmpty,
           let sourcePath = defaults.sourcePath?.nonEmptyValue {
            subtitleSourcePath = sourcePath
        }
        if !editedFields.contains(.inputLanguage),
           let inputLanguage = defaults.inputLanguage {
            self.inputLanguage = inputLanguage
        }
        if !editedFields.contains(.targetLanguage),
           let targetLanguage = defaults.targetLanguage {
            self.targetLanguage = targetLanguage
        }
        if !editedFields.contains(.subtitleStartTime),
           let startTime = defaults.startTime {
            subtitleStartTime = startTime
        }
        if !editedFields.contains(.subtitleEndTime),
           let endTime = defaults.endTime {
            subtitleEndTime = endTime
        }
        if !editedFields.contains(.subtitleEnableTransliteration),
           let enableTransliteration = defaults.enableTransliteration {
            subtitleEnableTransliteration = enableTransliteration
        }
        if !editedFields.contains(.subtitleShowOriginal),
           let showOriginal = defaults.showOriginal {
            subtitleShowOriginal = showOriginal
        }
        if !editedFields.contains(.subtitleTranslationProvider),
           let translationProvider = defaults.translationProvider {
            subtitleTranslationProvider = translationProvider
        }
        if !editedFields.contains(.subtitleLlmModel),
           let llmModel = defaults.llmModel?.nonEmptyValue {
            subtitleLlmModel = llmModel
        }
        if !editedFields.contains(.subtitleTransliterationMode),
           let transliterationMode = defaults.transliterationMode {
            subtitleTransliterationMode = transliterationMode
        }
        if !editedFields.contains(.subtitleTransliterationModel),
           let transliterationModel = defaults.transliterationModel?.nonEmptyValue {
            subtitleTransliterationModel = transliterationModel
        }
        if !editedFields.contains(.subtitleWorkerCount),
           let workerCount = defaults.workerCount {
            subtitleWorkerCount = workerCount
        }
        if !editedFields.contains(.subtitleBatchSize),
           let batchSize = defaults.batchSize {
            subtitleBatchSize = batchSize
        }
        if !editedFields.contains(.subtitleTranslationBatchSize),
           let translationBatchSize = defaults.translationBatchSize {
            subtitleTranslationBatchSize = translationBatchSize
        }
    }

    private func applyYoutubeHistoryDefaults() {
        guard let defaults = AppleBookCreatePresentation.youtubeHistoryDefaults(from: recentJobs) else {
            return
        }

        if !editedFields.contains(.youtubeVideoPath),
           trimmed(youtubeVideoPath).isEmpty,
           let videoPath = defaults.videoPath?.nonEmptyValue {
            youtubeVideoPath = videoPath
        }
        if !editedFields.contains(.youtubeSubtitlePath),
           trimmed(youtubeSubtitlePath).isEmpty,
           let subtitlePath = defaults.subtitlePath?.nonEmptyValue {
            youtubeSubtitlePath = subtitlePath
        }
        if !editedFields.contains(.targetLanguage),
           let targetLanguage = defaults.targetLanguage {
            self.targetLanguage = targetLanguage
        }
        if !editedFields.contains(.voice),
           let voice = defaults.voice {
            self.voice = voice
        }
        if !editedFields.contains(.youtubeStartOffset),
           let startOffset = defaults.startOffset {
            youtubeStartOffset = startOffset
        }
        if !editedFields.contains(.youtubeEndOffset),
           let endOffset = defaults.endOffset {
            youtubeEndOffset = endOffset
        }
        if !editedFields.contains(.youtubeOriginalMixPercent),
           let originalMixPercent = defaults.originalMixPercent {
            youtubeOriginalMixPercent = originalMixPercent
        }
        if !editedFields.contains(.youtubeFlushSentences),
           let flushSentences = defaults.flushSentences {
            youtubeFlushSentences = flushSentences
        }
        if !editedFields.contains(.subtitleTranslationProvider),
           let translationProvider = defaults.translationProvider {
            subtitleTranslationProvider = translationProvider
        }
        if !editedFields.contains(.subtitleLlmModel),
           let llmModel = defaults.llmModel?.nonEmptyValue {
            subtitleLlmModel = llmModel
        }
        if !editedFields.contains(.subtitleTranslationBatchSize),
           let translationBatchSize = defaults.translationBatchSize {
            subtitleTranslationBatchSize = translationBatchSize
        }
        if !editedFields.contains(.subtitleTransliterationMode),
           let transliterationMode = defaults.transliterationMode {
            subtitleTransliterationMode = transliterationMode
        }
        if !editedFields.contains(.subtitleTransliterationModel),
           let transliterationModel = defaults.transliterationModel?.nonEmptyValue {
            subtitleTransliterationModel = transliterationModel
        }
        if !editedFields.contains(.youtubeSplitBatches),
           let splitBatches = defaults.splitBatches {
            youtubeSplitBatches = splitBatches
        }
        if !editedFields.contains(.youtubeStitchBatches),
           let stitchBatches = defaults.stitchBatches {
            youtubeStitchBatches = stitchBatches
        }
        if !editedFields.contains(.youtubeIncludeTransliteration),
           let includeTransliteration = defaults.includeTransliteration {
            youtubeIncludeTransliteration = includeTransliteration
        }
        if !editedFields.contains(.youtubeTargetHeight),
           let targetHeight = defaults.targetHeight {
            youtubeTargetHeight = targetHeight
        }
        if !editedFields.contains(.youtubePreserveAspectRatio),
           let preserveAspectRatio = defaults.preserveAspectRatio {
            youtubePreserveAspectRatio = preserveAspectRatio
        }
        if !editedFields.contains(.youtubeEnableLookupCache),
           let enableLookupCache = defaults.enableLookupCache {
            youtubeEnableLookupCache = enableLookupCache
        }
    }
}
