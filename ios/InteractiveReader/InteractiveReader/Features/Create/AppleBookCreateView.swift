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
    @State private var isImportingNarrateEbook = false
    @State private var pipelineEbookPendingDelete: PipelineFileEntry?
    @State var creationTemplatePendingDelete: CreationTemplateEntry?
    @State var selectedSubtitleFileURL: URL?
    @State var selectedSubtitleFileName: String?
    @State private var isImportingSubtitleFile = false
    @State private var subtitleSourcePendingDelete: SubtitleSourceEntry?
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
    @State private var youtubeSelectionStorageScope = ""
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

    private var sourceSection: some View {
        AppleBookCreateSourceSection(
            creationMode: $creationMode,
            availableCreateModes: availableCreateModes,
            showsJobTypePicker: false,
            showsNarrateRangeControls: false,
            sourcePath: narrateSourcePathBinding,
            sourceStartSentence: textBinding(for: .sourceStartSentence, value: $sourceStartSentence),
            sourceEndSentence: textBinding(for: .sourceEndSentence, value: $sourceEndSentence),
            narrateSourcePanel: $narrateSourcePanel,
            subtitleSourcePath: textBinding(for: .subtitleSourcePath, value: $subtitleSourcePath),
            youtubeBaseDir: $youtubeBaseDir,
            youtubeVideoPath: textBinding(for: .youtubeVideoPath, value: $youtubeVideoPath),
            youtubeSubtitlePath: textBinding(for: .youtubeSubtitlePath, value: $youtubeSubtitlePath),
            youtubeSubtitleExtractionLanguages: $youtubeSubtitleExtractionLanguages,
            pipelineFiles: viewModel.pipelineFiles,
            acquisitionProviders: viewModel.acquisitionProviders,
            acquisitionDefaultProviderIds: viewModel.acquisitionDefaultProviderIds,
            ebookAcquisitionDiscovery: viewModel.ebookAcquisitionDiscovery,
            youtubeAcquisitionDiscovery: viewModel.youtubeAcquisitionDiscovery,
            downloadStationJob: viewModel.downloadStationJob,
            subtitleSources: viewModel.subtitleSources,
            youtubeLibrary: viewModel.youtubeLibrary,
            youtubeInlineSubtitleStreams: viewModel.youtubeInlineSubtitleStreams,
            selectedNarrateFileName: selectedNarrateFileName,
            selectedSubtitleFileName: selectedSubtitleFileName,
            narrateChapterOptions: viewModel.narrateChapterOptions,
            selectedNarrateStartChapterID: $selectedNarrateStartChapterID,
            selectedNarrateEndChapterID: $selectedNarrateEndChapterID,
            isLoadingPipelineFiles: viewModel.isLoadingPipelineFiles,
            isUploadingPipelineEbook: viewModel.isUploadingPipelineEbook,
            isLoadingEbookAcquisitionDiscovery: viewModel.isLoadingEbookAcquisitionDiscovery,
            isAcquiringEbookAcquisitionCandidate: viewModel.isAcquiringEbookDiscoveryCandidate,
            isLoadingYoutubeAcquisitionDiscovery: viewModel.isLoadingYoutubeAcquisitionDiscovery,
            isPreparingYoutubeAcquisitionCandidate: viewModel.isPreparingYoutubeAcquisitionCandidate,
            isLoadingNarrateChapters: viewModel.isLoadingNarrateChapters,
            isSubmittingDownloadStation: viewModel.isSubmittingDownloadStation,
            isPollingDownloadStation: viewModel.isPollingDownloadStation,
            isDeletingPipelineEbook: viewModel.isDeletingPipelineEbook,
            isLoadingSubtitleSources: viewModel.isLoadingSubtitleSources,
            isDeletingSubtitleSource: viewModel.isDeletingSubtitleSource,
            isLoadingYoutubeLibrary: viewModel.isLoadingYoutubeLibrary,
            isLoadingYoutubeSubtitleStreams: viewModel.isLoadingYoutubeSubtitleStreams,
            isExtractingYoutubeSubtitles: viewModel.isExtractingYoutubeSubtitles,
            pipelineFilesErrorMessage: viewModel.pipelineFilesErrorMessage,
            narrateChaptersErrorMessage: viewModel.narrateChaptersErrorMessage,
            subtitleSourcesErrorMessage: viewModel.subtitleSourcesErrorMessage,
            youtubeLibraryErrorMessage: viewModel.youtubeLibraryErrorMessage,
            ebookAcquisitionDiscoveryErrorMessage: viewModel.ebookAcquisitionDiscoveryErrorMessage,
            youtubeAcquisitionDiscoveryErrorMessage: viewModel.youtubeAcquisitionDiscoveryErrorMessage,
            downloadStationMessage: viewModel.downloadStationMessage,
            downloadStationErrorMessage: viewModel.downloadStationErrorMessage,
            acquisitionProvidersErrorMessage: viewModel.acquisitionProvidersErrorMessage,
            youtubeSearchUnavailableMessage: videoDiscoveryAvailability.youtubeSearchUnavailableMessage,
            isYoutubeSearchAvailable: videoDiscoveryAvailability.isYoutubeSearchAvailable,
            downloadStationUnavailableMessage: videoDiscoveryAvailability.downloadStationUnavailableMessage,
            isDownloadStationAvailable: videoDiscoveryAvailability.isDownloadStationAvailable,
            youtubeSubtitleExtractionMessage: viewModel.youtubeSubtitleExtractionMessage,
            youtubeSubtitleExtractionErrorMessage: viewModel.youtubeSubtitleExtractionErrorMessage,
            onRefreshPipelineFiles: refreshPipelineFilesFromSourceSection,
            onSearchAcquisitionDiscovery: searchAcquisitionDiscovery,
            onSelectAcquisitionCandidate: applyAcquisitionDiscoveryCandidate,
            onDeletePipelineEbook: requestDeletePipelineEbook,
            onRefreshSubtitleSources: refreshSubtitleSourcesFromSourceSection,
            onDeleteSubtitleSource: requestDeleteSubtitleSource,
            onRefreshYoutubeLibrary: refreshYoutubeLibraryFromSourceSection,
            onSearchYoutubeAcquisitionDiscovery: searchYoutubeAcquisitionDiscovery,
            onSelectYoutubeAcquisitionCandidate: applyYoutubeAcquisitionDiscoveryCandidate,
            onSubmitDownloadStation: submitDownloadStation,
            onPollDownloadStation: pollDownloadStation,
            onInspectYoutubeSubtitles: inspectYoutubeSubtitles,
            onExtractYoutubeSubtitles: extractYoutubeSubtitles,
            onLoadNarrateChapters: loadNarrateChapters,
            onChooseNarrateFile: chooseNarrateFile,
            onChooseSubtitleFile: chooseSubtitleFile
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

    private func handleYoutubeBaseDirChange(_ value: String) {
        persistYoutubeBaseDir(value)
    }

    private func handleSubtitleSourcePathChange() {
        subtitleMetadataLookupSourceName = subtitleMetadataSourceName
        viewModel.clearSubtitleMetadata()
    }

    private func requestDeleteSubtitleSource(_ entry: SubtitleSourceEntry) {
        subtitleSourcePendingDelete = entry
    }

    private func deleteSubtitleSource(_ entry: SubtitleSourceEntry) async {
        subtitleSourcePendingDelete = nil
        let didDelete = await viewModel.deleteSubtitleSource(path: entry.path, using: appState)
        guard didDelete else { return }
        if subtitleSourcePath == entry.path {
            subtitleSourcePath = ""
        }
        await refreshSubtitleSources(force: true)
    }

    private func handleYoutubeVideoPathChange(_ path: String) {
        youtubeDiscoveryState = nil
        youtubeSubtitleExtractionLanguages = ""
        viewModel.resetYoutubeSubtitleExtractionState()
        viewModel.resetYoutubeMetadataState()
        persistYoutubeSelectionPath(path, field: "video")
    }

    private func handleYoutubeSubtitlePathChange(_ path: String) {
        youtubeDiscoveryState = AppleBookCreatePresentation.videoDiscoveryState(
            youtubeDiscoveryState,
            replacingSelectedSubtitlePath: path
        )
        persistYoutubeSelectionPath(path, field: "subtitle")
    }

    private func handleLanguagePreferenceChange() {
        persistLanguagePreferences()
    }

    private func handleSubtitleShowOriginalChange(_ value: Bool) {
        persistSubtitleShowOriginal(value)
    }

    private func refreshPipelineFilesFromSourceSection() {
        Task { await refreshPipelineFiles(force: true) }
    }

    private func refreshSubtitleSourcesFromSourceSection() {
        Task { await refreshSubtitleSources(force: true) }
    }

    private func refreshYoutubeLibraryFromSourceSection() {
        Task { await refreshYoutubeLibrary(force: true) }
    }

    private func chooseNarrateFile() {
        isImportingNarrateEbook = true
    }

    private func chooseSubtitleFile() {
        isImportingSubtitleFile = true
    }

    private func refreshVoiceInventory() {
        Task {
            await viewModel.loadVoiceInventory(
                using: appState,
                cacheKey: creationOptionsLoadKey,
                force: true
            )
        }
    }

    private func checkImageNodes() {
        Task {
            await viewModel.checkImageNodeAvailability(
                baseURLsText: imageApiBaseURLs,
                using: appState
            )
        }
    }

    private func previewVoice(_ language: String, _ label: String, _ selectedVoice: AppleBookCreateVoiceOption) {
        viewModel.previewVoice(
            language: language,
            languageLabel: label,
            voice: selectedVoice,
            using: appState
        )
    }

    private func loadYoutubeTvMetadata() {
        Task {
            await viewModel.lookupYoutubeTvMetadata(
                sourceName: youtubeMetadataTvSourceName,
                using: appState
            )
        }
    }

    private func loadYoutubeVideoMetadata() {
        Task {
            await viewModel.lookupYoutubeVideoMetadata(
                sourceName: youtubeMetadataVideoSourceName,
                using: appState
            )
        }
    }

    private func clearYoutubeTvMetadataCache() {
        Task {
            await viewModel.clearYoutubeTvMetadataCache(
                query: youtubeMetadataTvSourceName,
                using: appState
            )
        }
    }

    private func clearYoutubeVideoMetadataCache() {
        Task {
            await viewModel.clearYoutubeVideoMetadataCache(
                query: youtubeMetadataVideoSourceName,
                using: appState
            )
        }
    }

    private func applyYoutubeAdvancedMetadataJSON() {
        viewModel.applyYoutubeMediaMetadataJSONText()
    }

    private func syncYoutubeAdvancedMetadataJSON() {
        viewModel.syncYoutubeMediaMetadataJSONText()
    }

    private func lookupSubtitleMetadata() {
        Task {
            await viewModel.lookupSubtitleTvMetadata(
                sourceName: subtitleMetadataLookupSourceName,
                using: appState
            )
        }
    }

    private func refreshSubtitleMetadata() {
        Task {
            await viewModel.lookupSubtitleTvMetadata(
                sourceName: subtitleMetadataLookupSourceName,
                force: true,
                using: appState
            )
        }
    }

    private func clearSubtitleMetadata() {
        viewModel.clearSubtitleMetadata()
    }

    private func clearSubtitleMetadataCache() {
        Task {
            await viewModel.clearSubtitleTvMetadataCache(
                query: subtitleMetadataLookupSourceName,
                using: appState
            )
        }
    }

    private func applySubtitleAdvancedMetadataJSON() {
        viewModel.applySubtitleMediaMetadataJSONText()
    }

    private func syncSubtitleAdvancedMetadataJSON() {
        viewModel.syncSubtitleMediaMetadataJSONText()
    }

    private func retryCreationOptions() {
        Task { await refreshCreationOptions(force: true) }
    }

    private func loadNarrateChapters() {
        Task {
            selectedNarrateStartChapterID = ""
            selectedNarrateEndChapterID = ""
            await viewModel.loadNarrateChapters(inputFile: sourcePath, using: appState)
        }
    }

    func clearNarrateSourceMetadata() {
        sourceBookTitle = ""
        sourceBookAuthor = ""
        sourceBookGenre = ""
        sourceBookSummary = ""
        bookSummary = ""
        bookYear = ""
        bookIsbn = ""
        bookCoverFile = ""
        bookMetadataExtras = [:]
        editedFields.subtract([
            .sourceBookTitle,
            .sourceBookAuthor,
            .sourceBookGenre,
            .sourceBookSummary,
            .bookSummary,
            .bookYear,
            .bookIsbn,
            .bookCoverFile,
        ])
    }

    func refreshIntakeStatus(force: Bool = false) async {
        await viewModel.loadIntakeStatus(
            using: appState,
            cacheKey: creationOptionsLoadKey,
            force: force
        )
    }

    func refreshPipelineFiles(force: Bool = false) async {
        let files = await viewModel.loadPipelineFiles(
            using: appState,
            cacheKey: creationOptionsLoadKey,
            force: force
        )
        applyPreferredNarrateSource(from: files)
    }

    private func searchAcquisitionDiscovery(_ query: String, provider: String) {
        Task {
            _ = await viewModel.loadEbookDiscovery(
                using: appState,
                cacheKey: creationOptionsLoadKey,
                query: query,
                provider: provider,
                force: true
            )
        }
    }

    private func applyAcquisitionDiscoveryCandidate(_ candidate: AcquisitionCandidate) {
        if let localPath = candidate.localPath?.trimmingCharacters(in: .whitespacesAndNewlines), !localPath.isEmpty {
            Task {
                guard let preparedPath = await viewModel.prepareEbookDiscoveryCandidate(
                    using: appState,
                    candidate: candidate
                ) else {
                    return
                }
                applyAcquisitionDiscoveryPath(preparedPath)
                _ = applyAcquisitionDiscoveryMetadata(candidate)
            }
            return
        }

        if !candidate.capabilities.contains("acquire") {
            let sourceIds = AppleBookCreatePresentation.internetArchiveSourceIDs(candidate)
            if !sourceIds.isEmpty {
                Task {
                    _ = await viewModel.loadEbookDiscovery(
                        using: appState,
                        cacheKey: creationOptionsLoadKey,
                        query: candidate.title,
                        provider: "internet_archive",
                        sourceIds: sourceIds,
                        force: true
                    )
                }
                return
            }
            _ = applyAcquisitionDiscoveryMetadata(candidate)
            return
        }

        Task {
            guard let acquiredPath = await viewModel.acquireEbookDiscoveryCandidate(
                using: appState,
                candidate: candidate
            ) else {
                return
            }
            applyAcquisitionDiscoveryPath(acquiredPath)
            _ = applyAcquisitionDiscoveryMetadata(candidate)
            _ = await viewModel.loadPipelineFiles(
                using: appState,
                cacheKey: creationOptionsLoadKey,
                force: true
            )
        }
    }

    @discardableResult
    private func applyAcquisitionDiscoveryMetadata(_ candidate: AcquisitionCandidate) -> Bool {
        guard let metadataApplication = AppleBookCreatePresentation.bookDiscoveryMetadataApplication(candidate) else {
            return false
        }

        var applied = false
        if let title = metadataApplication.sourceBookTitle {
            sourceBookTitle = title
            editedFields.insert(.sourceBookTitle)
            applied = true
        }
        if let author = metadataApplication.sourceBookAuthor {
            sourceBookAuthor = author
            editedFields.insert(.sourceBookAuthor)
            applied = true
        }
        if let genre = metadataApplication.sourceBookGenre {
            sourceBookGenre = genre
            editedFields.insert(.sourceBookGenre)
            applied = true
        }
        if let summary = metadataApplication.bookSummary {
            bookSummary = summary
            editedFields.insert(.bookSummary)
            applied = true
        }
        if let year = metadataApplication.bookYear {
            bookYear = year
            editedFields.insert(.bookYear)
            applied = true
        }
        if let isbn = metadataApplication.bookIsbn {
            bookIsbn = isbn
            editedFields.insert(.bookIsbn)
            applied = true
        }
        if let cover = metadataApplication.bookCoverFile {
            bookCoverFile = cover
            editedFields.insert(.bookCoverFile)
            applied = true
        }
        bookMetadataExtras = metadataApplication.bookMetadataExtras
        return applied
    }

    private func applyAcquisitionDiscoveryPath(_ localPath: String) {
        markEdited(.sourcePath)
        let previousSourcePath = sourcePath
        selectedNarrateFileURL = nil
        selectedNarrateFileName = nil
        clearNarrateChapterSelection()
        clearNarrateSourceMetadata()
        sourcePath = localPath
        refreshNarrateBaseOutputIfNeeded(for: localPath, replacing: previousSourcePath)
    }

    func refreshNarrateBaseOutputIfNeeded(for newSourcePath: String, replacing oldSourcePath: String) {
        guard shouldRefreshNarrateBaseOutput(replacing: oldSourcePath) else {
            return
        }
        sourceBaseOutput = derivedNarrateBaseOutputName(for: newSourcePath)
    }

    private func shouldRefreshNarrateBaseOutput(replacing oldSourcePath: String) -> Bool {
        guard !editedFields.contains(.sourceBaseOutput) else {
            return false
        }
        let currentBaseOutput = trimmed(sourceBaseOutput)
        if currentBaseOutput.isEmpty {
            return true
        }
        let previousSourcePath = trimmed(oldSourcePath)
        guard !previousSourcePath.isEmpty else {
            return false
        }
        return currentBaseOutput == derivedNarrateBaseOutputName(for: previousSourcePath)
    }

    private func derivedNarrateBaseOutputName(for sourcePath: String) -> String {
        if let entry = AppleBookCreatePresentation.selectedPipelineEbook(
            sourcePath: sourcePath,
            files: viewModel.pipelineFiles
        ) {
            return AppleBookCreatePresentation.deriveBaseOutputName(entry.name)
        }
        return AppleBookCreatePresentation.deriveBaseOutputName(sourcePath)
    }

    private func searchYoutubeAcquisitionDiscovery(_ query: String, provider: String) {
        Task {
            _ = await viewModel.loadVideoDiscovery(
                using: appState,
                cacheKey: creationOptionsLoadKey,
                query: query,
                provider: provider,
                force: true
            )
        }
    }

    private func applyYoutubeAcquisitionDiscoveryCandidate(_ candidate: AcquisitionCandidate) {
        if AppleBookCreatePresentation.isYoutubeMetadataVideoDiscoveryProviderID(candidate.provider) {
            guard let sourceURL = AppleBookCreatePresentation.youtubeMetadataSourceURL(for: candidate) else {
                viewModel.youtubeMetadataErrorMessage = "Selected YouTube discovery result did not include a reviewable URL."
                return
            }
            youtubeDiscoveryState = AppleBookCreatePresentation.videoDiscoveryStatePayload(
                from: candidate,
                selectedVideoPath: nil,
                selectedSubtitlePath: nil
            )
            viewModel.youtubeMetadataMessage = "Selected YouTube discovery result \(candidate.title). Review metadata before downloading or dubbing."
            Task {
                await viewModel.lookupYoutubeVideoMetadata(
                    sourceName: sourceURL,
                    using: appState
                )
            }
            return
        }

        if candidate.provider == "newznab_torznab" {
            youtubeDiscoveryState = AppleBookCreatePresentation.videoDiscoveryStatePayload(
                from: candidate,
                selectedVideoPath: nil,
                selectedSubtitlePath: nil
            )
            viewModel.youtubeMetadataMessage = "Selected indexer result \(candidate.title). Confirm lawful access before any downloader handoff."
            return
        }

        Task {
            guard let prepared = await viewModel.prepareVideoDiscoveryCandidate(
                using: appState,
                candidate: candidate
            ) else {
                return
            }
            applyPreparedVideoDiscoveryCandidate(prepared, source: candidate)
        }
    }

    private func applyPreparedVideoDiscoveryCandidate(
        _ prepared: AcquisitionPreparedArtifactResponse,
        source candidate: AcquisitionCandidate
    ) {
        guard let videoPath = prepared.videoPath?.trimmingCharacters(in: .whitespacesAndNewlines).nonEmptyValue
                ?? prepared.localPath.trimmingCharacters(in: .whitespacesAndNewlines).nonEmptyValue
                ?? candidate.localPath?.trimmingCharacters(in: .whitespacesAndNewlines).nonEmptyValue else {
            return
        }
        let preferredSubtitlePath = prepared.subtitlePath?.trimmingCharacters(in: .whitespacesAndNewlines).nonEmptyValue
            ?? prepared.subtitles.first?.path.trimmingCharacters(in: .whitespacesAndNewlines).nonEmptyValue
            ?? candidate.subtitles.first?.path.trimmingCharacters(in: .whitespacesAndNewlines).nonEmptyValue

        markEdited(.youtubeVideoPath)
        youtubeVideoPath = videoPath
        handleYoutubeVideoPathChange(videoPath)
        youtubeDiscoveryState = AppleBookCreatePresentation.videoDiscoveryStatePayload(
            from: candidate,
            selectedVideoPath: videoPath,
            selectedSubtitlePath: preferredSubtitlePath
        )

        if let subtitlePath = preferredSubtitlePath {
            markEdited(.youtubeSubtitlePath)
            youtubeSubtitlePath = subtitlePath
            handleYoutubeSubtitlePathChange(subtitlePath)
            youtubeDiscoveryState = AppleBookCreatePresentation.videoDiscoveryStatePayload(
                from: candidate,
                selectedVideoPath: videoPath,
                selectedSubtitlePath: subtitlePath
            )
        }
    }

    private func submitDownloadStation(
        sourceURI: String?,
        candidateToken: String?,
        destination: String?,
        confirmed: Bool
    ) {
        Task {
            _ = await viewModel.submitDownloadStationTask(
                using: appState,
                sourceURI: sourceURI,
                candidateToken: candidateToken,
                destination: destination,
                confirmed: confirmed
            )
        }
    }

    private func pollDownloadStation() {
        Task {
            let completed = await viewModel.pollDownloadStationTask(using: appState)
            guard completed else {
                return
            }
            let discovery = await viewModel.loadVideoDiscovery(
                using: appState,
                cacheKey: creationOptionsLoadKey,
                provider: "manual_downloads",
                force: true
            )
            _ = await viewModel.loadYoutubeLibrary(
                using: appState,
                cacheKey: youtubeLibraryLoadKey,
                baseDir: youtubeBaseDir,
                force: true
            )
            if let candidate = AppleBookCreatePresentation.downloadStationCompletedCandidate(
                from: discovery,
                job: viewModel.downloadStationJob
            ) {
                applyYoutubeAcquisitionDiscoveryCandidate(candidate)
            }
        }
    }

    private func requestDeletePipelineEbook(_ entry: PipelineFileEntry) {
        pipelineEbookPendingDelete = entry
    }

    private func deletePipelineEbook(_ entry: PipelineFileEntry) async {
        pipelineEbookPendingDelete = nil
        let didDelete = await viewModel.deletePipelineEbook(path: entry.path, using: appState)
        guard didDelete else { return }
        if sourcePath == entry.path {
            sourcePath = ""
            sourceBaseOutput = ""
            clearNarrateChapterSelection()
            clearNarrateSourceMetadata()
            viewModel.clearNarrateChapters()
        }
        await refreshPipelineFiles(force: true)
    }

    private func refreshSubtitleSources(force: Bool = false) async {
        let sources = await viewModel.loadSubtitleSources(
            using: appState,
            cacheKey: creationOptionsLoadKey,
            force: force
        )
        applyPreferredSubtitleSource(from: sources)
    }

    private func refreshYoutubeLibrary(force: Bool = false) async {
        let library = await viewModel.loadYoutubeLibrary(
            using: appState,
            cacheKey: youtubeLibraryLoadKey,
            baseDir: youtubeBaseDir,
            force: force
        )
        if trimmed(youtubeBaseDir).isEmpty,
           let resolvedBaseDir = library?.baseDir.nonEmptyValue {
            youtubeBaseDir = resolvedBaseDir
        }
        applyPreferredYoutubeSource(from: library)
    }

    private func inspectYoutubeSubtitles() {
        Task {
            guard let response = await viewModel.loadYoutubeSubtitleStreams(
                videoPath: youtubeVideoPath,
                using: appState
            ) else {
                return
            }
            let defaults = AppleBookCreatePresentation.defaultYoutubeInlineSubtitleLanguages(
                from: response.streams
            )
            youtubeSubtitleExtractionLanguages = defaults.joined(separator: ", ")
        }
    }

    private func extractYoutubeSubtitles() {
        Task {
            let languages = AppleBookCreatePresentation.normalizedYoutubeInlineSubtitleLanguages(
                youtubeSubtitleExtractionLanguages
            )
            guard let response = await viewModel.extractYoutubeSubtitles(
                videoPath: youtubeVideoPath,
                languages: languages,
                using: appState
            ) else {
                return
            }
            let selectedVideoPath = youtubeVideoPath
            let extractedSubtitlePath = response.extracted.first?.path
            let library = await viewModel.loadYoutubeLibrary(
                using: appState,
                cacheKey: youtubeLibraryLoadKey,
                baseDir: youtubeBaseDir,
                force: true
            )
            if !trimmed(selectedVideoPath).isEmpty {
                youtubeVideoPath = selectedVideoPath
            }
            if let extractedSubtitlePath, !trimmed(extractedSubtitlePath).isEmpty {
                youtubeSubtitlePath = extractedSubtitlePath
            } else {
                applyPreferredYoutubeSource(from: library)
            }
        }
    }

    private func applyPreferredNarrateSource(from files: PipelineFileBrowserResponse?) {
        guard let defaults = AppleBookCreatePresentation.narrateSourceDefaults(
            selectedLocalFile: selectedNarrateFileURL != nil,
            didEditSourcePath: editedFields.contains(.sourcePath),
            sourcePath: sourcePath,
            sourceBaseOutput: sourceBaseOutput,
            didEditBaseOutput: editedFields.contains(.sourceBaseOutput),
            files: files
        ) else {
            return
        }

        if sourcePath != defaults.path {
            sourcePath = defaults.path
            clearNarrateSourceMetadata()
        }
        if let baseOutput = defaults.baseOutput {
            sourceBaseOutput = baseOutput
        }
    }

    private func applyPreferredSubtitleSource(from sources: SubtitleSourceListResponse?) {
        guard let defaults = AppleBookCreatePresentation.subtitleSourceDefaults(
            selectedLocalFile: selectedSubtitleFileURL != nil,
            didEditSourcePath: editedFields.contains(.subtitleSourcePath),
            sourcePath: subtitleSourcePath,
            sources: sources
        ) else {
            return
        }

        subtitleSourcePath = defaults.path
        subtitleMetadataLookupSourceName = defaults.metadataLookupSourceName
    }

    private func applyPreferredYoutubeSource(from library: YoutubeNasLibraryResponse?) {
        guard let defaults = AppleBookCreatePresentation.youtubeSourceDefaults(
            library: library,
            currentStorageScope: youtubeSelectionStorageScope,
            nextStorageScope: youtubeLibraryLoadKey,
            didEditVideoPath: editedFields.contains(.youtubeVideoPath),
            currentVideoPath: youtubeVideoPath,
            didEditSubtitlePath: editedFields.contains(.youtubeSubtitlePath),
            currentSubtitlePath: youtubeSubtitlePath,
            storedVideoPath: storedYoutubeSelectionPath(field: "video"),
            storedSubtitlePath: storedYoutubeSelectionPath(field: "subtitle")
        ) else {
            return
        }

        youtubeSelectionStorageScope = defaults.nextStorageScope
        if let videoPath = defaults.videoPath {
            youtubeVideoPath = videoPath
        }
        if let subtitlePath = defaults.subtitlePath {
            youtubeSubtitlePath = subtitlePath
        }
    }

    func clearNarrateChapterSelection() {
        selectedNarrateStartChapterID = ""
        selectedNarrateEndChapterID = ""
        viewModel.clearNarrateChapters()
    }

    func trimmed(_ value: String) -> String {
        value.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private var availableInputLanguages: [AppleBookCreateLanguage] {
        AppleBookCreatePresentation.availableInputLanguages(from: viewModel.creationOptions)
    }

    private var availableTargetLanguages: [AppleBookCreateLanguage] {
        AppleBookCreatePresentation.availableTargetLanguages(from: viewModel.creationOptions)
    }

    private var availableVoices: [AppleBookCreateVoiceOption] {
        AppleBookCreatePresentation.availableVoices(
            from: viewModel.creationOptions,
            inventory: viewModel.voiceInventory,
            language: inputLanguage.backendValue,
            selected: voice
        )
    }

    private var availableTargetVoices: [AppleBookCreateVoiceOption] {
        AppleBookCreatePresentation.availableVoices(
            from: viewModel.creationOptions,
            inventory: viewModel.voiceInventory,
            language: targetLanguage.backendValue,
            selected: targetVoice ?? voice
        )
    }

    private var languageVoiceOptions: [String: [AppleBookCreateVoiceOption]] {
        AppleBookCreatePresentation.languageVoiceOptions(
            from: viewModel.creationOptions,
            inventory: viewModel.voiceInventory,
            languages: targetLanguagesForVoiceOverrides,
            selectedOverrides: languageVoiceOverrides,
            fallbackVoice: targetVoice ?? voice
        )
    }

    private var targetLanguagesForVoiceOverrides: [String] {
        AppleBookCreatePresentation.targetLanguagesForVoiceOverrides(
            mode: creationMode,
            primary: targetLanguage.backendValue,
            additionalTargets: additionalTargetLanguages
        )
    }

    private var availableSubtitleLlmModels: [String] {
        AppleBookCreatePresentation.availableSubtitleLlmModels(
            selected: subtitleLlmModel,
            inventory: viewModel.subtitleLlmModels
        )
    }

    private var availableSubtitleTransliterationModels: [String] {
        AppleBookCreatePresentation.availableSubtitleTransliterationModels(
            selected: subtitleTransliterationModel,
            translationModel: subtitleLlmModel,
            inventory: viewModel.subtitleLlmModels
        )
    }

    private var availableBookTransliterationModels: [String] {
        AppleBookCreatePresentation.availableSubtitleTransliterationModels(
            selected: bookTransliterationModel,
            translationModel: "",
            inventory: viewModel.subtitleLlmModels
        )
    }

    private var formattedAssEmphasisScale: String {
        AppleBookCreatePresentation.formattedAssEmphasisScale(subtitleAssEmphasisScale)
    }

    private var formattedYoutubeOriginalMixPercent: String {
        AppleBookCreatePresentation.formattedYoutubeOriginalMixPercent(youtubeOriginalMixPercent)
    }

    private var formattedTempo: String {
        AppleBookCreatePresentation.clampTempo(tempo).formatted(.number.precision(.fractionLength(1)))
    }

    private var estimatedAudioDurationLabel: String? {
        switch creationMode {
        case .generatedBook:
            return AppleBookCreatePresentation.estimatedAudioDurationLabel(sentenceCount: sentenceCount)
        case .narrateEbook:
            return AppleBookCreatePresentation.estimatedAudioDurationLabel(
                sentenceCount: AppleBookCreatePresentation.estimatedNarrateSentenceCount(
                    startSentence: sourceStartSentence,
                    endSentence: sourceEndSentence
                )
            )
        case .subtitleJob, .youtubeDub:
            return nil
        }
    }

}
