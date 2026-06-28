import SwiftUI

struct AppleBookCreateView: View {
    @EnvironmentObject var appState: AppState
    @Environment(\.openURL) private var openURL
    #if os(iOS)
    @Environment(\.horizontalSizeClass) private var horizontalSizeClass
    #endif
    @StateObject var viewModel = AppleBookCreateViewModel()

    let sectionPicker: BrowseSectionPicker?
    @Binding var creationMode: AppleCreateMode
    let showsInlineJobTypePicker: Bool
    let onJobSubmitted: (String) -> Void
    let onOpenJobs: (String) -> Void
    let recentJobs: [PipelineStatusResponse]
    let usesDarkBackground: Bool

    @State var topic = ""
    @State var bookName = ""
    @State var genre = ""
    @State var author = "Me"
    @State var sourceBookTitle = ""
    @State var sourceBookAuthor = ""
    @State var sourceBookGenre = ""
    @State var sourceBookSummary = ""
    @State var bookSummary = ""
    @State var bookYear = ""
    @State var bookIsbn = ""
    @State var bookCoverFile = ""
    @State var bookMetadataExtras = [String: JSONValue]()
    @State var sourcePath = ""
    @State var sourceBaseOutput = ""
    @State var sourceStartSentence = "1"
    @State var sourceEndSentence = ""
    @State var narrateSourcePanel = AppleBookCreateNarrateSourcePanel.server
    @State var bookDiscoveryQuery = ""
    @State var bookDiscoveryProvider = "local_epub"
    @State var selectedNarrateStartChapterID = ""
    @State var selectedNarrateEndChapterID = ""
    @State var subtitleSourcePath = ""
    @State var subtitleMetadataLookupSourceName = ""
    @State var youtubeBaseDir = ""
    @State var youtubeVideoPath = ""
    @State var youtubeSubtitlePath = ""
    @State var youtubeDiscoveryState: [String: JSONValue]?
    @State var youtubeStartOffset = ""
    @State var youtubeEndOffset = ""
    @State var youtubeOriginalMixPercent = 5.0
    @State var youtubeFlushSentences = 10
    @State var youtubeTargetHeight = AppleYoutubeDubTargetHeight.p480
    @State var youtubePreserveAspectRatio = true
    @State var youtubeSplitBatches = true
    @State var youtubeStitchBatches = true
    @State var youtubeIncludeTransliteration = true
    @State var youtubeEnableLookupCache = true
    @State var youtubeSubtitleExtractionLanguages = ""
    @State var subtitleOutputFormat = AppleSubtitleOutputFormat.ass
    @State var subtitleStartTime = "00:00"
    @State var subtitleEndTime = ""
    @State var subtitleEnableTransliteration = true
    @State var subtitleHighlight = true
    @State var subtitleShowOriginal = true
    @State var subtitleGenerateAudioBook = true
    @State var subtitleMirrorBatchesToSourceDir = true
    @State var subtitleTranslationProvider = AppleSubtitleTranslationProvider.llm
    @State var subtitleLlmModel = ""
    @State var subtitleTransliterationMode = AppleSubtitleTransliterationMode.default
    @State var subtitleTransliterationModel = ""
    @State var subtitleWorkerCount = AppleSubtitleTuning.defaultWorkerCount
    @State var subtitleBatchSize = AppleSubtitleTuning.defaultBatchSize
    @State var subtitleTranslationBatchSize = AppleSubtitleTuning.defaultTranslationBatchSize
    @State var subtitleAssFontSize = AppleSubtitleAssTypography.defaultFontSize
    @State var subtitleAssEmphasisScale = AppleSubtitleAssTypography.defaultEmphasisScale
    @State var selectedNarrateFileURL: URL?
    @State var selectedNarrateFileName: String?
    @State var isImportingNarrateEbook = false
    @State var pipelineEbookPendingDelete: PipelineFileEntry?
    @State var creationTemplatePendingDelete: CreationTemplateEntry?
    @State var selectedSubtitleFileURL: URL?
    @State var selectedSubtitleFileName: String?
    @State var isImportingSubtitleFile = false
    @State var subtitleSourcePendingDelete: SubtitleSourceEntry?
    @State var sentenceCount = 30
    @State var inputLanguage = AppleBookCreateLanguage.english
    @State var targetLanguage = AppleBookCreateLanguage.arabic
    @State var additionalTargetLanguages = ""
    @State var voice = AppleBookCreateVoiceOption.gtts
    @State var targetVoice: AppleBookCreateVoiceOption?
    @State var languageVoiceOverrides = [String: String]()
    @State var generateAudio = true
    @State var audioMode = "4"
    @State var audioBitrateKbps = "96"
    @State var writtenMode = "4"
    @State var tempo = 1.0
    @State var bookSentencesPerOutputFile = AppleBookOutputChunking.defaultSentencesPerOutputFile
    @State var bookSentenceSplitterMode = AppleBookSentenceSplitterMode.regex
    @State var stitchFull = false
    @State var includeTransliteration = true
    @State var bookTranslationProvider = AppleSubtitleTranslationProvider.llm
    @State var bookLlmModel = ""
    @State var bookTranslationBatchSize = AppleSubtitleTuning.defaultTranslationBatchSize
    @State var bookTransliterationMode = AppleSubtitleTransliterationMode.default
    @State var bookTransliterationModel = ""
    @State var enableLookupCache = true
    @State var bookLookupCacheBatchSize = AppleSubtitleTuning.defaultTranslationBatchSize
    @State var outputHtml = false
    @State var outputPdf = false
    @State var includeImages = false
    @State var imagePromptPipeline = AppleGeneratedBookImagePromptPipeline.promptPlan
    @State var imageStyleTemplate = AppleGeneratedBookImageStyleTemplate.wireframe
    @State var imagePromptBatchingEnabled = true
    @State var imagePromptBatchSize = 10
    @State var imagePromptPlanBatchSize = 50
    @State var imagePromptContextSentences = 0
    @State var imageWidth = "256"
    @State var imageHeight = "256"
    @State var imageSteps = ""
    @State var imageCfgScale = ""
    @State var imageSamplerName = ""
    @State var imageSeedWithPreviousImage = false
    @State var imageBlankDetectionEnabled = false
    @State var imageApiBaseURLs = ""
    @State var imageConcurrency = ""
    @State var imageApiTimeoutSeconds = ""
    @State var bookThreadCount = ""
    @State var bookQueueSize = ""
    @State var bookJobMaxWorkers = ""
    @State var editedFields = Set<AppleBookCreateEditedField>()
    @State var youtubeSelectionStorageScope = ""
    @State var selectedTemplateID = ""

    var body: some View {
        AppleBookCreateContainer(
            sectionPicker: sectionPicker,
            usesRegularWidthLayout: usesRegularWidthCreateLayout,
            usesDarkBackground: usesDarkBackground
        ) {
            createSetupSections
        } settingsContent: {
            createSettingsSections
        }
        .modifier(
            AppleBookCreateLifecycleModifier(
                creationOptionsLoadKey: creationOptionsLoadKey,
                recentJobs: recentJobs,
                creationMode: creationMode,
                youtubeBaseDir: youtubeBaseDir,
                subtitleSourcePath: subtitleSourcePath,
                youtubeVideoPath: youtubeVideoPath,
                youtubeSubtitlePath: youtubeSubtitlePath,
                inputLanguage: inputLanguage,
                targetLanguage: targetLanguage,
                additionalTargetLanguages: additionalTargetLanguages,
                enableLookupCache: enableLookupCache,
                subtitleShowOriginal: subtitleShowOriginal,
                pendingEbookDelete: $pipelineEbookPendingDelete,
                pendingSubtitleDelete: $subtitleSourcePendingDelete,
                pendingTemplateDelete: $creationTemplatePendingDelete,
                onLoadCreateDependencies: loadCreateDependencies,
                onRefreshHistoryDefaults: refreshHistoryDefaults,
                onYoutubeBaseDirChange: handleYoutubeBaseDirChange,
                onSubtitleSourcePathChange: handleSubtitleSourcePathChange,
                onYoutubeVideoPathChange: handleYoutubeVideoPathChange,
                onYoutubeSubtitlePathChange: handleYoutubeSubtitlePathChange,
                onLanguagePreferenceChange: handleLanguagePreferenceChange,
                onSubtitleShowOriginalChange: handleSubtitleShowOriginalChange,
                onDeleteEbook: deletePipelineEbook,
                onDeleteSubtitleSource: deleteSubtitleSource,
                onDeleteCreationTemplate: deleteCreationTemplate
            )
        )
        .modifier(
            AppleBookCreateFileImporterModifier(
                isImportingNarrateEbook: $isImportingNarrateEbook,
                isImportingSubtitleFile: $isImportingSubtitleFile,
                onNarrateImport: handleNarrateEbookImport,
                onSubtitleImport: handleSubtitleFileImport
            )
        )
        .accessibilityIdentifier("appleBookCreateView")
    }

    private var usesRegularWidthCreateLayout: Bool {
        #if os(iOS)
        return horizontalSizeClass == .regular
        #else
        return false
        #endif
    }

    @ViewBuilder
    private var createSetupSections: some View {
        sourceSection
    }

    @ViewBuilder
    private var createSettingsSections: some View {
        AppleBookCreateSettingsContent(
            creationMode: creationMode,
            jobTypeSection: { jobTypeSection },
            templateSection: { templateSection },
            promptSection: { promptSection },
            metadataSection: { metadataSection },
            jobSettingsSection: { jobSettingsSection },
            narrationSection: { narrationSection },
            subtitleMetadataSection: { subtitleMetadataSection },
            youtubeMetadataSection: { youtubeMetadataSection },
            outputSection: { outputSection },
            statusSection: { statusSection },
            submitSection: { submitSection }
        )
    }

    private var promptSection: some View {
        AppleBookCreatePromptSection(
            topic: textBinding(for: .topic, value: $topic),
            bookName: textBinding(for: .bookName, value: $bookName),
            genre: textBinding(for: .genre, value: $genre),
            author: textBinding(for: .author, value: $author)
        )
    }

    private var metadataSection: some View {
        AppleBookCreateMetadataSection(
            creationMode: creationMode,
            sourceBookTitle: textBinding(for: .sourceBookTitle, value: $sourceBookTitle),
            sourceBookAuthor: textBinding(for: .sourceBookAuthor, value: $sourceBookAuthor),
            sourceBookGenre: textBinding(for: .sourceBookGenre, value: $sourceBookGenre),
            bookSummary: creationMode == .generatedBook
                ? textBinding(for: .sourceBookSummary, value: $sourceBookSummary)
                : textBinding(for: .bookSummary, value: $bookSummary),
            bookYear: textBinding(for: .bookYear, value: $bookYear),
            bookIsbn: textBinding(for: .bookIsbn, value: $bookIsbn),
            bookCoverFile: textBinding(for: .bookCoverFile, value: $bookCoverFile)
        )
    }

    private var narrationSection: some View {
        AppleBookCreateNarrationSection(
            creationMode: creationMode,
            inputLanguage: languageBinding(for: .inputLanguage, value: $inputLanguage),
            targetLanguage: languageBinding(for: .targetLanguage, value: $targetLanguage),
            additionalTargetLanguages: textBinding(
                for: .additionalTargetLanguages,
                value: $additionalTargetLanguages
            ),
            voice: voiceBinding,
            targetVoice: targetVoiceBinding,
            languageVoiceOverrides: voiceOverridesBinding,
            availableInputLanguages: availableInputLanguages,
            availableTargetLanguages: availableTargetLanguages,
            availableVoices: availableVoices,
            availableTargetVoices: availableTargetVoices,
            languageVoiceOptions: languageVoiceOptions,
            targetLanguagesForVoiceOverrides: targetLanguagesForVoiceOverrides,
            isLoadingVoiceInventory: viewModel.isLoadingVoiceInventory,
            voiceInventoryErrorMessage: viewModel.voiceInventoryErrorMessage,
            voicePreviewStates: viewModel.voicePreviewStates,
            voicePreviewErrorMessages: viewModel.voicePreviewErrorMessages,
            onRefreshVoiceInventory: refreshVoiceInventory,
            onPreviewVoice: previewVoice
        )
    }

    @ViewBuilder
    private var jobTypeSection: some View {
        AppleBookCreateJobTypeSection(
            creationMode: $creationMode,
            availableCreateModes: availableCreateModes,
            showsInlineJobTypePicker: showsInlineJobTypePicker
        )
    }

    private var templateSection: some View {
        AppleBookCreateTemplateSection(
            templates: compatibleCreationTemplates,
            selectedTemplateID: selectedCompatibleTemplateIDBinding,
            isLoading: viewModel.isLoadingCreationTemplates,
            isSaving: viewModel.isSavingCreationTemplate,
            isDeleting: viewModel.isDeletingCreationTemplate,
            errorMessage: viewModel.creationTemplatesErrorMessage,
            message: viewModel.creationTemplateMessage,
            onRefresh: refreshCreationTemplatesFromSection,
            onSave: saveCurrentCreationTemplate,
            onApply: applySelectedCreationTemplate,
            onDelete: requestDeleteSelectedCreationTemplate
        )
    }

    @ViewBuilder
    private var jobSettingsSection: some View {
        AppleBookCreateJobSettingsSection(
            creationMode: creationMode,
            sentenceBounds: sentenceBounds,
            sentenceCount: sentenceCountBinding,
            sourceBaseOutput: textBinding(for: .sourceBaseOutput, value: $sourceBaseOutput),
            sourceStartSentence: textBinding(for: .sourceStartSentence, value: $sourceStartSentence),
            sourceEndSentence: textBinding(for: .sourceEndSentence, value: $sourceEndSentence),
            narrateSourcePath: sourcePath,
            selectedNarrateSourceEntry: selectedNarrateServerEbook,
            narrateChapterOptions: viewModel.narrateChapterOptions,
            selectedNarrateStartChapterID: $selectedNarrateStartChapterID,
            selectedNarrateEndChapterID: $selectedNarrateEndChapterID,
            isLoadingNarrateChapters: viewModel.isLoadingNarrateChapters,
            narrateChaptersErrorMessage: viewModel.narrateChaptersErrorMessage,
            onLoadNarrateChapters: loadNarrateChapters
        )
    }

    private var selectedNarrateServerEbook: PipelineFileEntry? {
        AppleBookCreatePresentation.selectedPipelineEbook(
            sourcePath: sourcePath,
            files: viewModel.pipelineFiles
        )
    }

    private var outputSection: some View {
        AppleBookCreateOutputSection(
            creationMode: creationMode,
            derivedBaseOutput: derivedBaseOutput,
            subtitleOutputFormat: subtitleOutputFormatBinding,
            selectedSubtitleOutputFormat: subtitleOutputFormat,
            subtitleAssFontSize: subtitleAssFontSizeBinding,
            clampedSubtitleAssFontSize: clampedAssFontSize,
            subtitleAssEmphasisScale: subtitleAssEmphasisScaleBinding,
            formattedSubtitleAssEmphasisScale: formattedAssEmphasisScale,
            subtitleStartTime: textBinding(for: .subtitleStartTime, value: $subtitleStartTime),
            subtitleEndTime: textBinding(for: .subtitleEndTime, value: $subtitleEndTime),
            subtitleEnableTransliteration: boolBinding(
                for: .subtitleEnableTransliteration,
                value: $subtitleEnableTransliteration
            ),
            isSubtitleTransliterationEnabled: subtitleEnableTransliteration,
            subtitleTransliterationMode: subtitleTransliterationModeBinding,
            selectedSubtitleTransliterationMode: subtitleTransliterationMode,
            subtitleTransliterationModel: textBinding(
                for: .subtitleTransliterationModel,
                value: $subtitleTransliterationModel
            ),
            availableSubtitleTransliterationModels: availableSubtitleTransliterationModels,
            subtitleHighlight: boolBinding(for: .subtitleHighlight, value: $subtitleHighlight),
            subtitleShowOriginal: boolBinding(for: .subtitleShowOriginal, value: $subtitleShowOriginal),
            subtitleGenerateAudioBook: boolBinding(
                for: .subtitleGenerateAudioBook,
                value: $subtitleGenerateAudioBook
            ),
            subtitleMirrorBatchesToSourceDir: boolBinding(
                for: .subtitleMirrorBatchesToSourceDir,
                value: $subtitleMirrorBatchesToSourceDir
            ),
            subtitleTranslationProvider: subtitleTranslationProviderBinding,
            selectedSubtitleTranslationProvider: subtitleTranslationProvider,
            subtitleWorkerCount: subtitleWorkerCountBinding,
            clampedSubtitleWorkerCount: clampedSubtitleWorkerCount,
            subtitleBatchSize: subtitleBatchSizeBinding,
            clampedSubtitleBatchSize: clampedSubtitleBatchSize,
            subtitleLlmModel: textBinding(for: .subtitleLlmModel, value: $subtitleLlmModel),
            availableSubtitleLlmModels: availableSubtitleLlmModels,
            subtitleTranslationBatchSize: subtitleTranslationBatchSizeBinding,
            clampedSubtitleTranslationBatchSize: clampedSubtitleTranslationBatchSize,
            youtubeTargetHeight: youtubeTargetHeightBinding,
            youtubeStartOffset: textBinding(for: .youtubeStartOffset, value: $youtubeStartOffset),
            youtubeEndOffset: textBinding(for: .youtubeEndOffset, value: $youtubeEndOffset),
            youtubeOriginalMixPercent: youtubeOriginalMixPercentBinding,
            formattedYoutubeOriginalMixPercent: formattedYoutubeOriginalMixPercent,
            youtubeFlushSentences: youtubeFlushSentencesBinding,
            clampedYoutubeFlushSentences: clampedYoutubeFlushSentences,
            youtubeSplitBatches: boolBinding(for: .youtubeSplitBatches, value: $youtubeSplitBatches),
            isYoutubeSplitBatchesEnabled: youtubeSplitBatches,
            youtubeStitchBatches: boolBinding(for: .youtubeStitchBatches, value: $youtubeStitchBatches),
            youtubePreserveAspectRatio: boolBinding(
                for: .youtubePreserveAspectRatio,
                value: $youtubePreserveAspectRatio
            ),
            youtubeIncludeTransliteration: boolBinding(
                for: .youtubeIncludeTransliteration,
                value: $youtubeIncludeTransliteration
            ),
            youtubeEnableLookupCache: boolBinding(
                for: .youtubeEnableLookupCache,
                value: $youtubeEnableLookupCache
            ),
            generateAudio: boolBinding(for: .generateAudio, value: $generateAudio),
            audioMode: textBinding(for: .audioMode, value: $audioMode),
            audioBitrateKbps: textBinding(for: .audioBitrateKbps, value: $audioBitrateKbps),
            writtenMode: textBinding(for: .writtenMode, value: $writtenMode),
            tempo: tempoBinding,
            formattedTempo: formattedTempo,
            estimatedAudioDurationLabel: estimatedAudioDurationLabel,
            sentencesPerOutputFile: bookSentencesPerOutputFileBinding,
            clampedSentencesPerOutputFile: clampedBookSentencesPerOutputFile,
            sentenceSplitterOptions: sentenceSplitterOptions,
            sentenceSplitterMode: bookSentenceSplitterModeBinding,
            stitchFull: boolBinding(for: .stitchFull, value: $stitchFull),
            includeTransliteration: boolBinding(for: .includeTransliteration, value: $includeTransliteration),
            bookTranslationProvider: bookTranslationProviderBinding,
            selectedBookTranslationProvider: bookTranslationProvider,
            bookLlmModel: textBinding(for: .bookLlmModel, value: $bookLlmModel),
            bookTranslationBatchSize: bookTranslationBatchSizeBinding,
            clampedBookTranslationBatchSize: clampedBookTranslationBatchSize,
            bookTransliterationMode: bookTransliterationModeBinding,
            selectedBookTransliterationMode: bookTransliterationMode,
            bookTransliterationModel: textBinding(
                for: .bookTransliterationModel,
                value: $bookTransliterationModel
            ),
            availableBookTransliterationModels: availableBookTransliterationModels,
            enableLookupCache: boolBinding(for: .enableLookupCache, value: $enableLookupCache),
            bookLookupCacheBatchSize: bookLookupCacheBatchSizeBinding,
            clampedBookLookupCacheBatchSize: clampedBookLookupCacheBatchSize,
            outputHtml: boolBinding(for: .outputHtml, value: $outputHtml),
            outputPdf: boolBinding(for: .outputPdf, value: $outputPdf),
            includeImages: boolBinding(for: .includeImages, value: $includeImages),
            imagePromptPipeline: imagePromptPipelineBinding,
            imageStyleTemplate: imageStyleTemplateBinding,
            imagePromptBatchingEnabled: boolBinding(
                for: .imagePromptBatchingEnabled,
                value: $imagePromptBatchingEnabled
            ),
            imagePromptBatchSize: imagePromptBatchSizeBinding,
            clampedImagePromptBatchSize: clampedImagePromptBatchSize,
            imagePromptPlanBatchSize: imagePromptPlanBatchSizeBinding,
            clampedImagePromptPlanBatchSize: clampedImagePromptPlanBatchSize,
            imagePromptContextSentences: imagePromptContextSentencesBinding,
            clampedImagePromptContextSentences: clampedImagePromptContextSentences,
            imageWidth: textBinding(for: .imageWidth, value: $imageWidth),
            imageHeight: textBinding(for: .imageHeight, value: $imageHeight),
            imageSteps: textBinding(for: .imageSteps, value: $imageSteps),
            imageCfgScale: textBinding(for: .imageCfgScale, value: $imageCfgScale),
            imageSamplerName: textBinding(for: .imageSamplerName, value: $imageSamplerName),
            imageSeedWithPreviousImage: boolBinding(
                for: .imageSeedWithPreviousImage,
                value: $imageSeedWithPreviousImage
            ),
            imageBlankDetectionEnabled: boolBinding(
                for: .imageBlankDetectionEnabled,
                value: $imageBlankDetectionEnabled
            ),
            imageApiBaseURLs: textBinding(for: .imageApiBaseURLs, value: $imageApiBaseURLs),
            imageConcurrency: textBinding(for: .imageConcurrency, value: $imageConcurrency),
            imageApiTimeoutSeconds: textBinding(
                for: .imageApiTimeoutSeconds,
                value: $imageApiTimeoutSeconds
            ),
            threadCount: textBinding(for: .threadCount, value: $bookThreadCount),
            queueSize: textBinding(for: .queueSize, value: $bookQueueSize),
            jobMaxWorkers: textBinding(for: .jobMaxWorkers, value: $bookJobMaxWorkers),
            supportsImages: creationMode == .generatedBook,
            isCheckingImageNodes: viewModel.isCheckingImageNodes,
            imageNodeAvailabilityMessage: viewModel.imageNodeAvailabilityMessage,
            imageNodeAvailabilityErrorMessage: viewModel.imageNodeAvailabilityErrorMessage,
            onCheckImageNodes: checkImageNodes
        )
    }

    private var youtubeMetadataSection: some View {
        AppleBookCreateYoutubeMetadataSection(
            isLoadingTvMetadata: viewModel.isLoadingYoutubeTvMetadata,
            isLoadingYoutubeMetadata: viewModel.isLoadingYoutubeVideoMetadata,
            isClearingTvMetadataCache: viewModel.isClearingYoutubeTvMetadataCache,
            isClearingYoutubeMetadataCache: viewModel.isClearingYoutubeMetadataCache,
            canClearTvMetadataCache: !youtubeMetadataTvSourceName.isEmpty,
            canClearYoutubeMetadataCache: !youtubeMetadataVideoSourceName.isEmpty,
            tvPosterURL: youtubeMetadataNestedTextBinding(section: "show", nestedKey: "image", key: "medium"),
            tvEpisodeStillURL: youtubeMetadataNestedTextBinding(section: "episode", nestedKey: "image", key: "medium"),
            youtubeThumbnailURL: youtubeMetadataTextBinding(section: "youtube", key: "thumbnail"),
            message: viewModel.youtubeMetadataMessage,
            errorMessage: viewModel.youtubeMetadataErrorMessage,
            title: youtubeMetadataTextBinding(section: "youtube", key: "title"),
            channel: youtubeMetadataTextBinding(section: "youtube", key: "channel"),
            showName: youtubeMetadataTextBinding(section: "show", key: "name"),
            tmdbId: youtubeMetadataNumberBinding(section: "show", key: "tmdb_id"),
            imdbId: youtubeMetadataTextBinding(section: "show", key: "imdb_id"),
            episodeName: youtubeMetadataTextBinding(section: "episode", key: "name"),
            advancedMetadataJSON: $viewModel.youtubeMediaMetadataJSONText,
            advancedMetadataErrorMessage: viewModel.youtubeMediaMetadataJSONErrorMessage,
            onLoadTvMetadata: loadYoutubeTvMetadata,
            onLoadYoutubeMetadata: loadYoutubeVideoMetadata,
            onClearTvMetadataCache: clearYoutubeTvMetadataCache,
            onClearYoutubeMetadataCache: clearYoutubeVideoMetadataCache,
            onApplyAdvancedMetadataJSON: applyYoutubeAdvancedMetadataJSON,
            onSyncAdvancedMetadataJSON: syncYoutubeAdvancedMetadataJSON
        )
    }

    private var subtitleMetadataSection: some View {
        AppleBookCreateSubtitleMetadataSection(
            sourceName: subtitleMetadataSourceName,
            lookupSourceName: $subtitleMetadataLookupSourceName,
            isLoading: viewModel.isLoadingSubtitleTvMetadata,
            isClearingCache: viewModel.isClearingSubtitleTvMetadataCache,
            showPosterURL: subtitleMetadataNestedTextBinding(section: "show", nestedKey: "image", key: "medium"),
            episodeStillURL: subtitleMetadataNestedTextBinding(section: "episode", nestedKey: "image", key: "medium"),
            message: viewModel.subtitleMetadataMessage,
            errorMessage: viewModel.subtitleMetadataErrorMessage,
            jobLabel: subtitleMetadataTextBinding(section: nil, key: "job_label"),
            showName: subtitleMetadataTextBinding(section: "show", key: "name"),
            tmdbId: subtitleMetadataNumberBinding(section: "show", key: "tmdb_id"),
            imdbId: subtitleMetadataTextBinding(section: "show", key: "imdb_id"),
            season: subtitleMetadataNumberBinding(section: "episode", key: "season"),
            episode: subtitleMetadataNumberBinding(section: "episode", key: "number"),
            episodeName: subtitleMetadataTextBinding(section: "episode", key: "name"),
            airdate: subtitleMetadataTextBinding(section: "episode", key: "airdate"),
            advancedMetadataJSON: $viewModel.subtitleMediaMetadataJSONText,
            advancedMetadataErrorMessage: viewModel.subtitleMediaMetadataJSONErrorMessage,
            onLookup: lookupSubtitleMetadata,
            onRefresh: refreshSubtitleMetadata,
            onClear: clearSubtitleMetadata,
            onClearCache: clearSubtitleMetadataCache,
            onApplyAdvancedMetadataJSON: applySubtitleAdvancedMetadataJSON,
            onSyncAdvancedMetadataJSON: syncSubtitleAdvancedMetadataJSON
        )
    }

    @ViewBuilder
    private var statusSection: some View {
        AppleBookCreateStatusSection(
            isLoadingOptions: viewModel.isLoadingOptions,
            optionsErrorMessage: viewModel.optionsErrorMessage,
            errorMessage: viewModel.errorMessage,
            intakeStatus: viewModel.intakeStatus,
            isLoadingIntakeStatus: viewModel.isLoadingIntakeStatus,
            submittedJobId: viewModel.submittedJobId,
            onRetryDefaults: retryCreationOptions,
            onOpenJobs: onOpenJobs
        )
    }

    private var submitSection: some View {
        AppleBookCreateSubmitSection(
            creationMode: creationMode,
            isSubmitting: viewModel.isSubmitting,
            canSubmit: canSubmit,
            isIntakeAtCapacity: isIntakeAtCapacity,
            webCreateHandoffURL: webCreateHandoffURL,
            onSubmit: submit,
            onOpenWebCreate: { url in
                openURL(url)
            }
        )
    }

    private func loadCreateDependencies() async {
        applyStoredSubtitleShowOriginal()
        await refreshCreationOptions()
        _ = await viewModel.loadAcquisitionProviders(using: appState, cacheKey: creationOptionsLoadKey)
        await refreshIntakeStatus()
        await refreshPipelineFiles()
        await refreshCreationTemplates()
        await refreshSubtitleSources()
        applyStoredYoutubeBaseDir()
        await refreshYoutubeLibrary()
        _ = await viewModel.loadVoiceInventory(using: appState, cacheKey: creationOptionsLoadKey)
        await viewModel.loadSubtitleModels(using: appState, cacheKey: creationOptionsLoadKey)
        refreshHistoryDefaults()
    }

    private func refreshHistoryDefaults() {
        applyHistoryDefaultsForCurrentMode()
    }

    func refreshIntakeStatus(force: Bool = false) async {
        await viewModel.loadIntakeStatus(
            using: appState,
            cacheKey: creationOptionsLoadKey,
            force: force
        )
    }

    func trimmed(_ value: String) -> String {
        value.trimmingCharacters(in: .whitespacesAndNewlines)
    }

}
