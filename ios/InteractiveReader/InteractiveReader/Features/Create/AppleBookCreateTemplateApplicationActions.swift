import Foundation

extension AppleBookCreateView {
    func applyCreationTemplate(_ template: CreationTemplateEntry) {
        guard let settings = AppleBookCreateTemplateSettings.settings(from: template) else {
            viewModel.creationTemplateMessage = nil
            viewModel.errorMessage = "Template \(template.displayName) does not contain creation settings."
            return
        }

        switch AppleBookCreateTemplateSettings.mode(for: template) {
        case .generatedBook, .narrateEbook:
            applyBookCreationTemplate(template, settings: settings)
        case .subtitleJob:
            applySubtitleCreationTemplate(template, settings: settings)
        case .youtubeDub:
            applyYoutubeDubCreationTemplate(template, settings: settings)
        case nil:
            viewModel.creationTemplateMessage = nil
            viewModel.errorMessage = "Template \(template.displayName) is not supported by Apple Create yet."
        }
    }

    private func applyBookCreationTemplate(_ template: CreationTemplateEntry, settings formState: [String: JSONValue]) {
        var appliedFields = Set<AppleBookCreateEditedField>()
        func markApplied(_ field: AppleBookCreateEditedField) {
            appliedFields.insert(field)
        }

        if AppleBookCreateTemplateSettings.mode(for: template) == .generatedBook {
            creationMode = .generatedBook
        } else if AppleBookCreateTemplateSettings.mode(for: template) == .narrateEbook {
            creationMode = .narrateEbook
        }

        if let value = AppleBookCreateTemplateSettings.string(formState, "input_file") {
            sourcePath = value
            selectedNarrateFileURL = nil
            selectedNarrateFileName = nil
            clearNarrateChapterSelection()
            clearNarrateSourceMetadata()
            markApplied(.sourcePath)
        }
        if let value = AppleBookCreateTemplateSettings.string(formState, "base_output_file") {
            sourceBaseOutput = value
            markApplied(.sourceBaseOutput)
        }
        if let value = AppleBookCreateTemplateSettings.int(formState, "start_sentence") {
            sourceStartSentence = "\(value)"
            markApplied(.sourceStartSentence)
        }
        if let value = AppleBookCreateTemplateSettings.endSentenceText(from: formState["end_sentence"]) {
            sourceEndSentence = value
            markApplied(.sourceEndSentence)
        }
        if let value = AppleBookCreateTemplateSettings.int(formState, "sentences_per_output_file") {
            bookSentencesPerOutputFile = AppleBookCreatePresentation.clampBookSentencesPerOutputFile(value)
            markApplied(.bookSentencesPerOutputFile)
        }
        if let value = AppleBookCreateTemplateSettings.string(formState, "sentence_splitter_mode") {
            bookSentenceSplitterMode = AppleBookSentenceSplitterMode(backendValue: value)
            markApplied(.bookSentenceSplitterMode)
        }

        applyTemplateLanguages(formState, appliedFields: &appliedFields)
        applyTemplateNarrationSettings(formState, appliedFields: &appliedFields)
        applyTemplateOutputSettings(formState, appliedFields: &appliedFields)
        applyTemplateImageSettings(formState, appliedFields: &appliedFields)
        applyTemplateWorkerSettings(formState, appliedFields: &appliedFields)
        applyTemplateMetadata(formState, appliedFields: &appliedFields)
        applyTemplateSourceBookContext(formState, appliedFields: &appliedFields)
        applyTemplateDiscoveryState(template, formState: formState)

        editedFields.formUnion(appliedFields)
        viewModel.errorMessage = nil
        viewModel.creationTemplateMessage = "Applied template \(template.displayName)."
    }

    private func applySubtitleCreationTemplate(_ template: CreationTemplateEntry, settings formState: [String: JSONValue]) {
        var appliedFields = Set<AppleBookCreateEditedField>()
        creationMode = .subtitleJob

        let subtitleApplication = AppleBookCreateTemplateSettings.subtitleApplication(from: formState)
        if let value = subtitleApplication.sourcePath {
            subtitleSourcePath = value
            selectedSubtitleFileURL = nil
            selectedSubtitleFileName = nil
            subtitleMetadataLookupSourceName = URL(fileURLWithPath: value).lastPathComponent
            appliedFields.insert(.subtitleSourcePath)
        }
        if let language = subtitleApplication.inputLanguage {
            inputLanguage = language
            appliedFields.insert(.inputLanguage)
        }
        if let language = subtitleApplication.targetLanguage {
            targetLanguage = language
            appliedFields.insert(.targetLanguage)
        }
        if let format = subtitleApplication.outputFormat {
            subtitleOutputFormat = format
            appliedFields.insert(.subtitleOutputFormat)
        }
        if let value = subtitleApplication.startTime {
            subtitleStartTime = value
            appliedFields.insert(.subtitleStartTime)
        }
        if let value = subtitleApplication.endTime {
            subtitleEndTime = value
            appliedFields.insert(.subtitleEndTime)
        }
        if let value = subtitleApplication.enableTransliteration {
            subtitleEnableTransliteration = value
            appliedFields.insert(.subtitleEnableTransliteration)
        }
        if let value = subtitleApplication.highlight {
            subtitleHighlight = value
            appliedFields.insert(.subtitleHighlight)
        }
        if let value = subtitleApplication.showOriginal {
            subtitleShowOriginal = value
            appliedFields.insert(.subtitleShowOriginal)
        }
        if let value = subtitleApplication.generateAudioBook {
            subtitleGenerateAudioBook = value
            appliedFields.insert(.subtitleGenerateAudioBook)
        }
        if let value = subtitleApplication.mirrorBatchesToSourceDir {
            subtitleMirrorBatchesToSourceDir = value
            appliedFields.insert(.subtitleMirrorBatchesToSourceDir)
        }
        if let provider = subtitleApplication.translationProvider {
            subtitleTranslationProvider = provider
            appliedFields.insert(.subtitleTranslationProvider)
        }
        if let value = subtitleApplication.llmModel {
            subtitleLlmModel = value
            appliedFields.insert(.subtitleLlmModel)
        }
        if let mode = subtitleApplication.transliterationMode {
            subtitleTransliterationMode = mode
            appliedFields.insert(.subtitleTransliterationMode)
        }
        if let value = subtitleApplication.transliterationModel {
            subtitleTransliterationModel = value
            appliedFields.insert(.subtitleTransliterationModel)
        }
        if let value = subtitleApplication.workerCount {
            subtitleWorkerCount = AppleBookCreatePresentation.clampSubtitleWorkerCount(value)
            appliedFields.insert(.subtitleWorkerCount)
        }
        if let value = subtitleApplication.batchSize {
            subtitleBatchSize = AppleBookCreatePresentation.clampSubtitleBatchSize(value)
            appliedFields.insert(.subtitleBatchSize)
        }
        if let value = subtitleApplication.translationBatchSize {
            subtitleTranslationBatchSize = AppleBookCreatePresentation.clampSubtitleTranslationBatchSize(value)
            appliedFields.insert(.subtitleTranslationBatchSize)
        }
        if let value = subtitleApplication.assFontSize {
            subtitleAssFontSize = AppleBookCreatePresentation.clampAssFontSize(value)
            appliedFields.insert(.subtitleAssFontSize)
        }
        if let value = subtitleApplication.assEmphasisScale {
            subtitleAssEmphasisScale = AppleBookCreatePresentation.clampAssEmphasisScale(value)
            appliedFields.insert(.subtitleAssEmphasisScale)
        }
        applyTemplateSubtitleMetadata(formState)

        editedFields.formUnion(appliedFields)
        viewModel.errorMessage = nil
        viewModel.creationTemplateMessage = "Applied template \(template.displayName)."
    }

    private func applyYoutubeDubCreationTemplate(_ template: CreationTemplateEntry, settings formState: [String: JSONValue]) {
        var appliedFields = Set<AppleBookCreateEditedField>()
        creationMode = .youtubeDub
        let discoveryState = AppleBookCreatePresentation.normalizedVideoDiscoveryState(
            AppleBookCreateTemplateSettings.discoveryState(from: template)
        )
        youtubeDiscoveryState = discoveryState
        let youtubeApplication = AppleBookCreateTemplateSettings.youtubeDubApplication(
            from: formState,
            discoveryState: discoveryState
        )

        if let value = youtubeApplication.videoPath {
            youtubeVideoPath = value
            youtubeSubtitleExtractionLanguages = ""
            viewModel.resetYoutubeSubtitleExtractionState()
            appliedFields.insert(.youtubeVideoPath)
        }
        if let value = youtubeApplication.subtitlePath {
            youtubeSubtitlePath = value
            appliedFields.insert(.youtubeSubtitlePath)
        }
        if let language = youtubeApplication.sourceLanguage {
            inputLanguage = language
            appliedFields.insert(.inputLanguage)
        }
        if let language = youtubeApplication.targetLanguage {
            targetLanguage = language
            appliedFields.insert(.targetLanguage)
        }
        if let option = youtubeApplication.voice {
            voice = option
            appliedFields.insert(.voice)
        }
        if let value = youtubeApplication.startTimeOffset {
            youtubeStartOffset = value
            appliedFields.insert(.youtubeStartOffset)
        }
        if let value = youtubeApplication.endTimeOffset {
            youtubeEndOffset = value
            appliedFields.insert(.youtubeEndOffset)
        }
        if let value = youtubeApplication.originalMixPercent {
            youtubeOriginalMixPercent = AppleBookCreatePresentation.clampYoutubeOriginalMixPercent(value)
            appliedFields.insert(.youtubeOriginalMixPercent)
        }
        if let value = youtubeApplication.flushSentences {
            youtubeFlushSentences = AppleBookCreatePresentation.clampYoutubeFlushSentences(value)
            appliedFields.insert(.youtubeFlushSentences)
        }
        if let provider = youtubeApplication.translationProvider {
            subtitleTranslationProvider = provider
            appliedFields.insert(.subtitleTranslationProvider)
        }
        if let value = youtubeApplication.llmModel {
            subtitleLlmModel = value
            appliedFields.insert(.subtitleLlmModel)
        }
        if let value = youtubeApplication.translationBatchSize {
            subtitleTranslationBatchSize = AppleBookCreatePresentation.clampSubtitleTranslationBatchSize(value)
            appliedFields.insert(.subtitleTranslationBatchSize)
        }
        if let mode = youtubeApplication.transliterationMode {
            subtitleTransliterationMode = mode
            appliedFields.insert(.subtitleTransliterationMode)
        }
        if let value = youtubeApplication.transliterationModel {
            subtitleTransliterationModel = value
            appliedFields.insert(.subtitleTransliterationModel)
        }
        if let value = youtubeApplication.splitBatches {
            youtubeSplitBatches = value
            appliedFields.insert(.youtubeSplitBatches)
        }
        if let value = youtubeApplication.stitchBatches {
            youtubeStitchBatches = value
            appliedFields.insert(.youtubeStitchBatches)
        }
        if let value = youtubeApplication.includeTransliteration {
            youtubeIncludeTransliteration = value
            appliedFields.insert(.youtubeIncludeTransliteration)
        }
        if let height = youtubeApplication.targetHeight {
            youtubeTargetHeight = height
            appliedFields.insert(.youtubeTargetHeight)
        }
        if let value = youtubeApplication.preserveAspectRatio {
            youtubePreserveAspectRatio = value
            appliedFields.insert(.youtubePreserveAspectRatio)
        }
        if let value = youtubeApplication.enableLookupCache {
            youtubeEnableLookupCache = value
            appliedFields.insert(.youtubeEnableLookupCache)
        }
        applyTemplateYoutubeMetadata(formState)

        editedFields.formUnion(appliedFields)
        viewModel.errorMessage = nil
        viewModel.creationTemplateMessage = "Applied template \(template.displayName)."
    }

    private func applyTemplateLanguages(
        _ formState: [String: JSONValue],
        appliedFields: inout Set<AppleBookCreateEditedField>
    ) {
        let languageApplication = AppleBookCreateTemplateSettings.languageApplication(from: formState)
        if let input = languageApplication.inputLanguage {
            inputLanguage = input
            appliedFields.insert(.inputLanguage)
        }

        if let primary = languageApplication.targetLanguages.first {
            targetLanguage = primary
            appliedFields.insert(.targetLanguage)
            additionalTargetLanguages = languageApplication.targetLanguages
                .dropFirst()
                .map(\.backendValue)
                .joined(separator: ", ")
            appliedFields.insert(.additionalTargetLanguages)
        }
    }

    private func applyTemplateNarrationSettings(
        _ formState: [String: JSONValue],
        appliedFields: inout Set<AppleBookCreateEditedField>
    ) {
        let voiceApplication = AppleBookCreateTemplateSettings.voiceApplication(from: formState)
        if let option = voiceApplication.voice {
            voice = option
            appliedFields.insert(.voice)
        }
        if let overrides = voiceApplication.overrides {
            languageVoiceOverrides = overrides
            appliedFields.insert(.languageVoiceOverrides)
        }
        let audioApplication = AppleBookCreateTemplateSettings.audioApplication(from: formState)
        if let value = audioApplication.generateAudio {
            generateAudio = value
            appliedFields.insert(.generateAudio)
        }
        if let value = audioApplication.audioMode {
            audioMode = value
            appliedFields.insert(.audioMode)
        }
        if let value = audioApplication.audioBitrateKbps {
            audioBitrateKbps = value
            appliedFields.insert(.audioBitrateKbps)
        }
        if let value = audioApplication.writtenMode {
            writtenMode = value
            appliedFields.insert(.writtenMode)
        }
        if let value = audioApplication.tempo {
            tempo = value
            appliedFields.insert(.tempo)
        }
        if let value = audioApplication.stitchFull {
            stitchFull = value
            appliedFields.insert(.stitchFull)
        }
        if let value = audioApplication.includeTransliteration {
            includeTransliteration = value
            appliedFields.insert(.includeTransliteration)
        }
        let translationApplication = AppleBookCreateTemplateSettings.bookTranslationApplication(from: formState)
        if let provider = translationApplication.provider {
            bookTranslationProvider = provider
            appliedFields.insert(.bookTranslationProvider)
        }
        if let value = translationApplication.llmModel {
            bookLlmModel = value
            appliedFields.insert(.bookLlmModel)
        }
        if let value = translationApplication.translationBatchSize {
            bookTranslationBatchSize = AppleBookCreatePresentation.clampSubtitleTranslationBatchSize(value)
            appliedFields.insert(.bookTranslationBatchSize)
        }
        if let mode = translationApplication.transliterationMode {
            bookTransliterationMode = mode
            appliedFields.insert(.bookTransliterationMode)
        }
        if let value = translationApplication.transliterationModel {
            bookTransliterationModel = value
            appliedFields.insert(.bookTransliterationModel)
        }
        if let value = translationApplication.enableLookupCache {
            enableLookupCache = value
            appliedFields.insert(.enableLookupCache)
        }
        if let value = translationApplication.lookupCacheBatchSize {
            bookLookupCacheBatchSize = AppleBookCreatePresentation.clampSubtitleTranslationBatchSize(value)
            appliedFields.insert(.bookLookupCacheBatchSize)
        }
    }

    private func applyTemplateOutputSettings(
        _ formState: [String: JSONValue],
        appliedFields: inout Set<AppleBookCreateEditedField>
    ) {
        let outputApplication = AppleBookCreateTemplateSettings.outputApplication(from: formState)
        if let value = outputApplication.outputHtml {
            outputHtml = value
            appliedFields.insert(.outputHtml)
        }
        if let value = outputApplication.outputPdf {
            outputPdf = value
            appliedFields.insert(.outputPdf)
        }
    }

    private func applyTemplateImageSettings(
        _ formState: [String: JSONValue],
        appliedFields: inout Set<AppleBookCreateEditedField>
    ) {
        let imageApplication = AppleBookCreateTemplateSettings.imageApplication(from: formState)
        if let value = imageApplication.includeImages {
            includeImages = value
            appliedFields.insert(.includeImages)
        }
        if let pipeline = imageApplication.promptPipeline {
            imagePromptPipeline = pipeline
            appliedFields.insert(.imagePromptPipeline)
        }
        if let style = imageApplication.styleTemplate {
            imageStyleTemplate = style
            appliedFields.insert(.imageStyleTemplate)
        }
        if let value = imageApplication.promptBatchingEnabled {
            imagePromptBatchingEnabled = value
            appliedFields.insert(.imagePromptBatchingEnabled)
        }
        if let value = imageApplication.promptBatchSize {
            imagePromptBatchSize = AppleBookCreatePresentation.clampImagePromptBatchSize(value)
            appliedFields.insert(.imagePromptBatchSize)
        }
        if let value = imageApplication.promptPlanBatchSize {
            imagePromptPlanBatchSize = AppleBookCreatePresentation.clampImagePromptBatchSize(value)
            appliedFields.insert(.imagePromptPlanBatchSize)
        }
        if let value = imageApplication.promptContextSentences {
            imagePromptContextSentences = AppleBookCreatePresentation.clampImagePromptContextSentences(value)
            appliedFields.insert(.imagePromptContextSentences)
        }
        if let value = imageApplication.width {
            imageWidth = value
            appliedFields.insert(.imageWidth)
        }
        if let value = imageApplication.height {
            imageHeight = value
            appliedFields.insert(.imageHeight)
        }
        if let value = imageApplication.steps {
            imageSteps = value
            appliedFields.insert(.imageSteps)
        }
        if let value = imageApplication.cfgScale {
            imageCfgScale = value
            appliedFields.insert(.imageCfgScale)
        }
        if let value = imageApplication.samplerName {
            imageSamplerName = value
            appliedFields.insert(.imageSamplerName)
        }
        if let value = imageApplication.seedWithPreviousImage {
            imageSeedWithPreviousImage = value
            appliedFields.insert(.imageSeedWithPreviousImage)
        }
        if let value = imageApplication.blankDetectionEnabled {
            imageBlankDetectionEnabled = value
            appliedFields.insert(.imageBlankDetectionEnabled)
        }
        if !imageApplication.apiBaseURLs.isEmpty {
            imageApiBaseURLs = imageApplication.apiBaseURLs.joined(separator: "\n")
            appliedFields.insert(.imageApiBaseURLs)
        }
        if let value = imageApplication.apiTimeoutSeconds {
            imageApiTimeoutSeconds = value
            appliedFields.insert(.imageApiTimeoutSeconds)
        }
    }

    private func applyTemplateWorkerSettings(
        _ formState: [String: JSONValue],
        appliedFields: inout Set<AppleBookCreateEditedField>
    ) {
        let workerApplication = AppleBookCreateTemplateSettings.workerApplication(from: formState)
        if let value = workerApplication.threadCount {
            bookThreadCount = value
            appliedFields.insert(.threadCount)
        }
        if let value = workerApplication.queueSize {
            bookQueueSize = value
            appliedFields.insert(.queueSize)
        }
        if let value = workerApplication.jobMaxWorkers {
            bookJobMaxWorkers = value
            appliedFields.insert(.jobMaxWorkers)
        }
        if let value = workerApplication.imageConcurrency {
            imageConcurrency = value
            appliedFields.insert(.imageConcurrency)
        }
    }

    private func applyTemplateMetadata(
        _ formState: [String: JSONValue],
        appliedFields: inout Set<AppleBookCreateEditedField>
    ) {
        guard let metadataApplication = AppleBookCreateTemplateSettings.bookMetadataApplication(from: formState) else {
            return
        }

        if let title = metadataApplication.title {
            if creationMode == .generatedBook {
                bookName = title
                appliedFields.insert(.bookName)
            } else {
                sourceBookTitle = title
                appliedFields.insert(.sourceBookTitle)
            }
        }
        if let metadataAuthor = metadataApplication.author {
            if creationMode == .generatedBook {
                author = metadataAuthor
                appliedFields.insert(.author)
            } else {
                sourceBookAuthor = metadataAuthor
                appliedFields.insert(.sourceBookAuthor)
            }
        }
        if let metadataGenre = metadataApplication.genre {
            if creationMode == .generatedBook {
                genre = metadataGenre
                appliedFields.insert(.genre)
            } else {
                sourceBookGenre = metadataGenre
                appliedFields.insert(.sourceBookGenre)
            }
        }
        if let value = metadataApplication.summary {
            bookSummary = value
            appliedFields.insert(.bookSummary)
        }
        if let value = metadataApplication.year {
            bookYear = value
            appliedFields.insert(.bookYear)
        }
        if let value = metadataApplication.isbn {
            bookIsbn = value
            appliedFields.insert(.bookIsbn)
        }
        if let value = metadataApplication.coverFile {
            bookCoverFile = value
            appliedFields.insert(.bookCoverFile)
        }
    }

    private func applyTemplateSourceBookContext(
        _ formState: [String: JSONValue],
        appliedFields: inout Set<AppleBookCreateEditedField>
    ) {
        guard creationMode == .generatedBook else {
            return
        }
        let contextApplication = AppleBookCreateTemplateSettings.sourceBookContextApplication(from: formState)
        if let value = contextApplication.title {
            sourceBookTitle = value
            appliedFields.insert(.sourceBookTitle)
        }
        if let value = contextApplication.author {
            sourceBookAuthor = value
            appliedFields.insert(.sourceBookAuthor)
        }
        if let value = contextApplication.genre {
            sourceBookGenre = value
            appliedFields.insert(.sourceBookGenre)
        }
        if let value = contextApplication.summary {
            sourceBookSummary = value
            appliedFields.insert(.sourceBookSummary)
        }
    }

    private func applyTemplateDiscoveryState(
        _ template: CreationTemplateEntry,
        formState: [String: JSONValue]
    ) {
        let application = AppleBookCreateTemplateSettings.discoveryApplication(
            from: template,
            formState: formState,
            mode: creationMode
        )
        if let shouldUseDiscoverySourcePanel = application.shouldUseDiscoverySourcePanel {
            narrateSourcePanel = shouldUseDiscoverySourcePanel ? .discovery : .server
        }
        if let extras = application.bookMetadataExtras {
            bookMetadataExtras = extras
        }
    }

    private func applyTemplateSubtitleMetadata(_ formState: [String: JSONValue]) {
        guard let metadata = AppleBookCreateTemplateSettings.metadataObject(from: formState) else {
            return
        }
        viewModel.subtitleMediaMetadataDraft = AppleBookCreatePresentation.normalizedSubtitleMediaMetadata(metadata)
        viewModel.syncSubtitleMediaMetadataJSONText()
        viewModel.subtitleMetadataMessage = "Applied template metadata."
        viewModel.subtitleMetadataErrorMessage = nil
    }

    private func applyTemplateYoutubeMetadata(_ formState: [String: JSONValue]) {
        guard let metadata = AppleBookCreateTemplateSettings.metadataObject(from: formState) else {
            return
        }
        viewModel.youtubeMediaMetadataDraft = AppleBookCreatePresentation.normalizedYoutubeMediaMetadata(metadata)
        viewModel.syncYoutubeMediaMetadataJSONText()
        viewModel.youtubeMetadataMessage = "Applied template metadata."
        viewModel.youtubeMetadataErrorMessage = nil
    }
}
