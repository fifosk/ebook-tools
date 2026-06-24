import SwiftUI
#if os(iOS)
import UniformTypeIdentifiers
#endif

struct AppleBookCreateView: View {
    private static let setupPaneMinWidth: CGFloat = 220
    private static let setupPaneIdealWidth: CGFloat = 260
    private static let setupPaneMaxWidth: CGFloat = 280
    private static let settingsPaneMinWidth: CGFloat = 480
    private static let settingsPaneIdealWidth: CGFloat = 680

    @EnvironmentObject private var appState: AppState
    @Environment(\.openURL) private var openURL
    #if os(iOS)
    @Environment(\.horizontalSizeClass) private var horizontalSizeClass
    #endif
    @StateObject private var viewModel = AppleBookCreateViewModel()

    let sectionPicker: BrowseSectionPicker?
    @Binding var creationMode: AppleCreateMode
    let showsInlineJobTypePicker: Bool
    let onJobSubmitted: (String) -> Void
    let onOpenJobs: (String) -> Void
    let recentJobs: [PipelineStatusResponse]
    let usesDarkBackground: Bool

    @State private var topic = ""
    @State private var bookName = ""
    @State private var genre = ""
    @State private var author = "Me"
    @State private var sourceBookTitle = ""
    @State private var sourceBookAuthor = ""
    @State private var sourceBookGenre = ""
    @State private var bookSummary = ""
    @State private var bookYear = ""
    @State private var bookIsbn = ""
    @State private var bookCoverFile = ""
    @State private var sourcePath = ""
    @State private var sourceBaseOutput = ""
    @State private var sourceStartSentence = "1"
    @State private var sourceEndSentence = ""
    @State private var selectedNarrateStartChapterID = ""
    @State private var selectedNarrateEndChapterID = ""
    @State private var subtitleSourcePath = ""
    @State private var subtitleMetadataLookupSourceName = ""
    @State private var youtubeBaseDir = ""
    @State private var youtubeVideoPath = ""
    @State private var youtubeSubtitlePath = ""
    @State private var youtubeStartOffset = ""
    @State private var youtubeEndOffset = ""
    @State private var youtubeOriginalMixPercent = 5.0
    @State private var youtubeFlushSentences = 10
    @State private var youtubeTargetHeight = AppleYoutubeDubTargetHeight.p480
    @State private var youtubePreserveAspectRatio = true
    @State private var youtubeSplitBatches = true
    @State private var youtubeStitchBatches = true
    @State private var youtubeSubtitleExtractionLanguages = ""
    @State private var subtitleOutputFormat = AppleSubtitleOutputFormat.ass
    @State private var subtitleStartTime = "00:00"
    @State private var subtitleEndTime = ""
    @State private var subtitleEnableTransliteration = true
    @State private var subtitleHighlight = true
    @State private var subtitleShowOriginal = true
    @State private var subtitleGenerateAudioBook = true
    @State private var subtitleMirrorBatchesToSourceDir = true
    @State private var subtitleTranslationProvider = AppleSubtitleTranslationProvider.llm
    @State private var subtitleLlmModel = ""
    @State private var subtitleTransliterationMode = AppleSubtitleTransliterationMode.default
    @State private var subtitleTransliterationModel = ""
    @State private var subtitleWorkerCount = AppleSubtitleTuning.defaultWorkerCount
    @State private var subtitleBatchSize = AppleSubtitleTuning.defaultBatchSize
    @State private var subtitleTranslationBatchSize = AppleSubtitleTuning.defaultTranslationBatchSize
    @State private var subtitleAssFontSize = AppleSubtitleAssTypography.defaultFontSize
    @State private var subtitleAssEmphasisScale = AppleSubtitleAssTypography.defaultEmphasisScale
    @State private var selectedNarrateFileURL: URL?
    @State private var selectedNarrateFileName: String?
    @State private var isImportingNarrateEbook = false
    @State private var selectedSubtitleFileURL: URL?
    @State private var selectedSubtitleFileName: String?
    @State private var isImportingSubtitleFile = false
    @State private var sentenceCount = 30
    @State private var inputLanguage = AppleBookCreateLanguage.english
    @State private var targetLanguage = AppleBookCreateLanguage.arabic
    @State private var additionalTargetLanguages = ""
    @State private var voice = AppleBookCreateVoiceOption.gtts
    @State private var targetVoice: AppleBookCreateVoiceOption?
    @State private var languageVoiceOverrides = [String: String]()
    @State private var generateAudio = true
    @State private var audioMode = "4"
    @State private var audioBitrateKbps = "96"
    @State private var writtenMode = "4"
    @State private var tempo = 1.0
    @State private var bookSentencesPerOutputFile = AppleBookOutputChunking.defaultSentencesPerOutputFile
    @State private var stitchFull = false
    @State private var includeTransliteration = true
    @State private var bookTranslationProvider = AppleSubtitleTranslationProvider.llm
    @State private var bookLlmModel = ""
    @State private var bookTranslationBatchSize = AppleSubtitleTuning.defaultTranslationBatchSize
    @State private var bookTransliterationMode = AppleSubtitleTransliterationMode.default
    @State private var bookTransliterationModel = ""
    @State private var enableLookupCache = true
    @State private var bookLookupCacheBatchSize = AppleSubtitleTuning.defaultTranslationBatchSize
    @State private var outputHtml = false
    @State private var outputPdf = false
    @State private var includeImages = false
    @State private var imagePromptPipeline = AppleGeneratedBookImagePromptPipeline.promptPlan
    @State private var imageStyleTemplate = AppleGeneratedBookImageStyleTemplate.wireframe
    @State private var imagePromptBatchingEnabled = true
    @State private var imagePromptBatchSize = 10
    @State private var imagePromptPlanBatchSize = 50
    @State private var imagePromptContextSentences = 0
    @State private var imageWidth = "256"
    @State private var imageHeight = "256"
    @State private var imageSteps = ""
    @State private var imageCfgScale = ""
    @State private var imageSamplerName = ""
    @State private var imageSeedWithPreviousImage = false
    @State private var imageBlankDetectionEnabled = false
    @State private var imageApiBaseURLs = ""
    @State private var imageConcurrency = ""
    @State private var imageApiTimeoutSeconds = ""
    @State private var bookThreadCount = ""
    @State private var bookQueueSize = ""
    @State private var bookJobMaxWorkers = ""
    @State private var editedFields = Set<AppleBookCreateEditedField>()
    @State private var youtubeSelectionStorageScope = ""

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            if let sectionPicker {
                sectionPicker
            }

            if usesRegularWidthCreateLayout {
                regularWidthCreateLayout
            } else {
                createList(accessibilityIdentifier: "appleBookCreateSingleColumnList") {
                    createSetupSections
                    createSettingsSections
                }
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
        .background(usesDarkBackground ? AppTheme.lightBackground : Color.clear)
        #if os(iOS)
        .toolbarBackground(usesDarkBackground ? AppTheme.lightBackground : Color.clear, for: .navigationBar)
        .toolbarBackground(usesDarkBackground ? .visible : .automatic, for: .navigationBar)
        .toolbarColorScheme(usesDarkBackground ? .dark : nil, for: .navigationBar)
        #endif
        .task(id: creationOptionsLoadKey) {
            applyStoredSubtitleShowOriginal()
            await refreshCreationOptions()
            await refreshIntakeStatus()
            await refreshPipelineFiles()
            await refreshSubtitleSources()
            applyStoredYoutubeBaseDir()
            await refreshYoutubeLibrary()
            _ = await viewModel.loadVoiceInventory(using: appState, cacheKey: creationOptionsLoadKey)
            await viewModel.loadSubtitleModels(using: appState, cacheKey: creationOptionsLoadKey)
            applyHistoryDefaultsForCurrentMode()
        }
        .onChange(of: recentJobs) { _, _ in
            applyHistoryDefaultsForCurrentMode()
        }
        .onChange(of: creationMode) { _, _ in
            applyHistoryDefaultsForCurrentMode()
        }
        .onChange(of: youtubeBaseDir) { _, newValue in
            persistYoutubeBaseDir(newValue)
        }
        .onChange(of: subtitleSourcePath) { _, _ in
            subtitleMetadataLookupSourceName = defaultSubtitleMetadataLookupSourceName
            viewModel.clearSubtitleMetadata()
        }
        .onChange(of: youtubeVideoPath) { _, newValue in
            youtubeSubtitleExtractionLanguages = ""
            viewModel.resetYoutubeSubtitleExtractionState()
            viewModel.resetYoutubeMetadataState()
            persistYoutubeSelectionPath(newValue, field: "video")
        }
        .onChange(of: youtubeSubtitlePath) { _, newValue in
            persistYoutubeSelectionPath(newValue, field: "subtitle")
        }
        .onChange(of: inputLanguage) { _, _ in
            persistLanguagePreferences()
        }
        .onChange(of: targetLanguage) { _, _ in
            persistLanguagePreferences()
        }
        .onChange(of: additionalTargetLanguages) { _, _ in
            persistLanguagePreferences()
        }
        .onChange(of: enableLookupCache) { _, _ in
            persistLanguagePreferences()
        }
        .onChange(of: subtitleShowOriginal) { _, newValue in
            persistSubtitleShowOriginal(newValue)
        }
        #if os(iOS)
        .fileImporter(
            isPresented: $isImportingNarrateEbook,
            allowedContentTypes: [Self.epubContentType],
            allowsMultipleSelection: false,
            onCompletion: handleNarrateEbookImport
        )
        .fileImporter(
            isPresented: $isImportingSubtitleFile,
            allowedContentTypes: Self.subtitleContentTypes,
            allowsMultipleSelection: false,
            onCompletion: handleSubtitleFileImport
        )
        #endif
        .accessibilityIdentifier("appleBookCreateView")
    }

    @ViewBuilder
    private var regularWidthCreateLayout: some View {
        HStack(alignment: .top, spacing: 0) {
            createList(accessibilityIdentifier: "appleBookCreateSetupPane") {
                createSetupSections
            }
            .frame(
                minWidth: Self.setupPaneMinWidth,
                idealWidth: Self.setupPaneIdealWidth,
                maxWidth: Self.setupPaneMaxWidth,
                maxHeight: .infinity
            )
            .layoutPriority(0)

            Divider()

            createList(accessibilityIdentifier: "appleBookCreateSettingsPane") {
                createSettingsSections
            }
            .frame(
                minWidth: Self.settingsPaneMinWidth,
                idealWidth: Self.settingsPaneIdealWidth,
                maxWidth: .infinity,
                maxHeight: .infinity
            )
            .layoutPriority(2)
        }
        .accessibilityIdentifier("appleBookCreateRegularWidthLayout")
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
        if creationMode == .generatedBook {
            promptSection
        }
        if creationMode == .generatedBook || creationMode == .narrateEbook {
            metadataSection
        }
    }

    @ViewBuilder
    private var createSettingsSections: some View {
        jobSettingsSection
        narrationSection
        if creationMode == .subtitleJob {
            subtitleMetadataSection
        }
        if creationMode == .youtubeDub {
            youtubeMetadataSection
        }
        outputSection
        statusSection
        submitSection
    }

    private func createList<Content: View>(
        accessibilityIdentifier: String,
        @ViewBuilder content: () -> Content
    ) -> some View {
        List {
            content()
        }
        #if os(tvOS)
        .listStyle(.plain)
        #else
        .listStyle(.insetGrouped)
        .scrollContentBackground(usesDarkBackground ? .hidden : .automatic)
        #endif
        .accessibilityIdentifier(accessibilityIdentifier)
    }

    private var sourceSection: some View {
        AppleBookCreateSourceSection(
            creationMode: $creationMode,
            availableCreateModes: availableCreateModes,
            showsJobTypePicker: showsInlineJobTypePicker,
            sourcePath: narrateSourcePathBinding,
            sourceStartSentence: textBinding(for: .sourceStartSentence, value: $sourceStartSentence),
            sourceEndSentence: textBinding(for: .sourceEndSentence, value: $sourceEndSentence),
            subtitleSourcePath: textBinding(for: .subtitleSourcePath, value: $subtitleSourcePath),
            youtubeBaseDir: $youtubeBaseDir,
            youtubeVideoPath: textBinding(for: .youtubeVideoPath, value: $youtubeVideoPath),
            youtubeSubtitlePath: textBinding(for: .youtubeSubtitlePath, value: $youtubeSubtitlePath),
            youtubeSubtitleExtractionLanguages: $youtubeSubtitleExtractionLanguages,
            pipelineFiles: viewModel.pipelineFiles,
            subtitleSources: viewModel.subtitleSources,
            youtubeLibrary: viewModel.youtubeLibrary,
            youtubeInlineSubtitleStreams: viewModel.youtubeInlineSubtitleStreams,
            selectedNarrateFileName: selectedNarrateFileName,
            selectedSubtitleFileName: selectedSubtitleFileName,
            narrateChapterOptions: viewModel.narrateChapterOptions,
            selectedNarrateStartChapterID: $selectedNarrateStartChapterID,
            selectedNarrateEndChapterID: $selectedNarrateEndChapterID,
            isLoadingPipelineFiles: viewModel.isLoadingPipelineFiles,
            isLoadingNarrateChapters: viewModel.isLoadingNarrateChapters,
            isLoadingSubtitleSources: viewModel.isLoadingSubtitleSources,
            isLoadingYoutubeLibrary: viewModel.isLoadingYoutubeLibrary,
            isLoadingYoutubeSubtitleStreams: viewModel.isLoadingYoutubeSubtitleStreams,
            isExtractingYoutubeSubtitles: viewModel.isExtractingYoutubeSubtitles,
            pipelineFilesErrorMessage: viewModel.pipelineFilesErrorMessage,
            narrateChaptersErrorMessage: viewModel.narrateChaptersErrorMessage,
            subtitleSourcesErrorMessage: viewModel.subtitleSourcesErrorMessage,
            youtubeLibraryErrorMessage: viewModel.youtubeLibraryErrorMessage,
            youtubeSubtitleExtractionMessage: viewModel.youtubeSubtitleExtractionMessage,
            youtubeSubtitleExtractionErrorMessage: viewModel.youtubeSubtitleExtractionErrorMessage,
            onRefreshPipelineFiles: {
                Task { await refreshPipelineFiles(force: true) }
            },
            onRefreshSubtitleSources: {
                Task { await refreshSubtitleSources(force: true) }
            },
            onRefreshYoutubeLibrary: {
                Task { await refreshYoutubeLibrary(force: true) }
            },
            onInspectYoutubeSubtitles: inspectYoutubeSubtitles,
            onExtractYoutubeSubtitles: extractYoutubeSubtitles,
            onLoadNarrateChapters: loadNarrateChapters,
            onChooseNarrateFile: { isImportingNarrateEbook = true },
            onChooseSubtitleFile: { isImportingSubtitleFile = true }
        )
    }

    private var promptSection: some View {
        Section("Book") {
            TextField("Topic", text: textBinding(for: .topic, value: $topic))
                .textInputAutocapitalization(.sentences)
                .accessibilityIdentifier("createBookTopicField")
            TextField("Title", text: textBinding(for: .bookName, value: $bookName))
                .textInputAutocapitalization(.words)
                .accessibilityIdentifier("createBookTitleField")
            TextField("Genre", text: textBinding(for: .genre, value: $genre))
                .textInputAutocapitalization(.words)
                .accessibilityIdentifier("createBookGenreField")
            TextField("Author", text: textBinding(for: .author, value: $author))
                .textInputAutocapitalization(.words)
                .accessibilityIdentifier("createBookAuthorField")
        }
    }

    private var metadataSection: some View {
        Section(creationMode == .generatedBook ? "Source Book" : "Metadata") {
            if creationMode == .generatedBook || creationMode == .narrateEbook {
                TextField(
                    creationMode == .generatedBook ? "Source title" : "Title",
                    text: textBinding(for: .sourceBookTitle, value: $sourceBookTitle)
                )
                    .textInputAutocapitalization(.words)
                    .accessibilityIdentifier(
                        creationMode == .generatedBook
                            ? "createGeneratedSourceBookTitleField"
                            : "createNarrateBookTitleField"
                    )
                TextField(
                    creationMode == .generatedBook ? "Source author" : "Author",
                    text: textBinding(for: .sourceBookAuthor, value: $sourceBookAuthor)
                )
                    .textInputAutocapitalization(.words)
                    .accessibilityIdentifier(
                        creationMode == .generatedBook
                            ? "createGeneratedSourceBookAuthorField"
                            : "createNarrateBookAuthorField"
                    )
                TextField(
                    creationMode == .generatedBook ? "Source genre" : "Genre",
                    text: textBinding(for: .sourceBookGenre, value: $sourceBookGenre)
                )
                    .textInputAutocapitalization(.words)
                    .accessibilityIdentifier(
                        creationMode == .generatedBook
                            ? "createGeneratedSourceBookGenreField"
                            : "createNarrateBookGenreField"
                    )
            }
            TextField(
                creationMode == .generatedBook ? "Source summary" : "Summary",
                text: textBinding(for: .bookSummary, value: $bookSummary),
                axis: .vertical
            )
                .lineLimit(2...5)
                .textInputAutocapitalization(.sentences)
                .accessibilityIdentifier("createBookSummaryField")
            TextField("Year", text: textBinding(for: .bookYear, value: $bookYear))
                #if os(iOS)
                .keyboardType(.numberPad)
                #endif
                .accessibilityIdentifier("createBookYearField")
            TextField("ISBN", text: textBinding(for: .bookIsbn, value: $bookIsbn))
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
                .accessibilityIdentifier("createBookIsbnField")
            TextField("Cover file path", text: textBinding(for: .bookCoverFile, value: $bookCoverFile))
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
                .accessibilityIdentifier("createBookCoverFileField")
        }
    }

    @ViewBuilder
    private var sentenceCountControl: some View {
        #if os(tvOS)
        LabeledContent("Sentences") {
            HStack(spacing: 12) {
                Button {
                    markEdited(.sentenceCount)
                    sentenceCount = max(sentenceBounds.min, sentenceCount - 5)
                } label: {
                    Image(systemName: "minus")
                }
                .disabled(sentenceCount <= sentenceBounds.min)
                .accessibilityLabel("Decrease sentences")

                Text("\(sentenceCount)")
                    .monospacedDigit()
                    .frame(minWidth: 48)

                Button {
                    markEdited(.sentenceCount)
                    sentenceCount = min(sentenceBounds.max, sentenceCount + 5)
                } label: {
                    Image(systemName: "plus")
                }
                .disabled(sentenceCount >= sentenceBounds.max)
                .accessibilityLabel("Increase sentences")
            }
        }
        .accessibilityIdentifier("createBookSentenceControl")
        #else
        Stepper(value: sentenceCountBinding, in: sentenceBounds.min...sentenceBounds.max, step: 5) {
            LabeledContent("Sentences", value: "\(sentenceCount)")
        }
        .accessibilityIdentifier("createBookSentenceStepper")
        #endif
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
            onRefreshVoiceInventory: {
                Task {
                    await viewModel.loadVoiceInventory(
                        using: appState,
                        cacheKey: creationOptionsLoadKey,
                        force: true
                    )
                }
            },
            onPreviewVoice: { language, label, selectedVoice in
                viewModel.previewVoice(
                    language: language,
                    languageLabel: label,
                    voice: selectedVoice,
                    using: appState
                )
            }
        )
    }

    @ViewBuilder
    private var jobSettingsSection: some View {
        if creationMode == .generatedBook {
            Section("Job Settings") {
                sentenceCountControl
            }
        } else if creationMode == .narrateEbook {
            Section("Job Settings") {
                TextField("Output path", text: textBinding(for: .sourceBaseOutput, value: $sourceBaseOutput))
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                    .accessibilityIdentifier("createNarrateOutputPathField")
                TextField("Start sentence", text: textBinding(for: .sourceStartSentence, value: $sourceStartSentence))
                    #if os(iOS)
                    .keyboardType(.numberPad)
                    #endif
                    .accessibilityIdentifier("createNarrateStartSentenceField")
                TextField("End sentence", text: textBinding(for: .sourceEndSentence, value: $sourceEndSentence))
                    #if os(iOS)
                    .keyboardType(.numbersAndPunctuation)
                    #endif
                    .accessibilityIdentifier("createNarrateEndSentenceField")
            }
        }
    }

    private var outputSection: some View {
        Section("Output") {
            if creationMode == .subtitleJob {
                AppleBookCreateSubtitleOutputControls(
                    outputFormat: subtitleOutputFormatBinding,
                    selectedOutputFormat: subtitleOutputFormat,
                    assFontSize: subtitleAssFontSizeBinding,
                    clampedAssFontSize: clampedAssFontSize,
                    assEmphasisScale: subtitleAssEmphasisScaleBinding,
                    formattedAssEmphasisScale: formattedAssEmphasisScale,
                    startTime: textBinding(for: .subtitleStartTime, value: $subtitleStartTime),
                    endTime: textBinding(for: .subtitleEndTime, value: $subtitleEndTime),
                    enableTransliteration: boolBinding(for: .subtitleEnableTransliteration, value: $subtitleEnableTransliteration),
                    isTransliterationEnabled: subtitleEnableTransliteration,
                    transliterationMode: subtitleTransliterationModeBinding,
                    selectedTransliterationMode: subtitleTransliterationMode,
                    transliterationModel: textBinding(for: .subtitleTransliterationModel, value: $subtitleTransliterationModel),
                    availableTransliterationModels: availableSubtitleTransliterationModels,
                    highlight: boolBinding(for: .subtitleHighlight, value: $subtitleHighlight),
                    showOriginal: boolBinding(for: .subtitleShowOriginal, value: $subtitleShowOriginal),
                    generateAudioBook: boolBinding(for: .subtitleGenerateAudioBook, value: $subtitleGenerateAudioBook),
                    mirrorBatchesToSourceDir: boolBinding(for: .subtitleMirrorBatchesToSourceDir, value: $subtitleMirrorBatchesToSourceDir),
                    translationProvider: subtitleTranslationProviderBinding,
                    selectedTranslationProvider: subtitleTranslationProvider,
                    workerCount: subtitleWorkerCountBinding,
                    clampedWorkerCount: clampedSubtitleWorkerCount,
                    batchSize: subtitleBatchSizeBinding,
                    clampedBatchSize: clampedSubtitleBatchSize,
                    llmModel: textBinding(for: .subtitleLlmModel, value: $subtitleLlmModel),
                    availableLlmModels: availableSubtitleLlmModels,
                    translationBatchSize: subtitleTranslationBatchSizeBinding,
                    clampedTranslationBatchSize: clampedSubtitleTranslationBatchSize
                )
            } else if creationMode == .youtubeDub {
                AppleBookCreateYoutubeOutputControls(
                    translationProvider: subtitleTranslationProviderBinding,
                    selectedTranslationProvider: subtitleTranslationProvider,
                    llmModel: textBinding(for: .subtitleLlmModel, value: $subtitleLlmModel),
                    availableSubtitleLlmModels: availableSubtitleLlmModels,
                    targetHeight: youtubeTargetHeightBinding,
                    startOffset: textBinding(for: .youtubeStartOffset, value: $youtubeStartOffset),
                    endOffset: textBinding(for: .youtubeEndOffset, value: $youtubeEndOffset),
                    originalMixPercent: youtubeOriginalMixPercentBinding,
                    formattedOriginalMixPercent: formattedYoutubeOriginalMixPercent,
                    flushSentences: youtubeFlushSentencesBinding,
                    clampedFlushSentences: clampedYoutubeFlushSentences,
                    translationBatchSize: subtitleTranslationBatchSizeBinding,
                    clampedTranslationBatchSize: clampedSubtitleTranslationBatchSize,
                    splitBatches: boolBinding(for: .youtubeSplitBatches, value: $youtubeSplitBatches),
                    isSplitBatchesEnabled: youtubeSplitBatches,
                    stitchBatches: boolBinding(for: .youtubeStitchBatches, value: $youtubeStitchBatches),
                    preserveAspectRatio: boolBinding(for: .youtubePreserveAspectRatio, value: $youtubePreserveAspectRatio),
                    includeTransliteration: boolBinding(for: .includeTransliteration, value: $includeTransliteration),
                    enableLookupCache: boolBinding(for: .enableLookupCache, value: $enableLookupCache)
                )
            } else {
                AppleBookCreateGeneratedOutputControls(
                    derivedBaseOutput: derivedBaseOutput,
                    generateAudio: boolBinding(for: .generateAudio, value: $generateAudio),
                    audioMode: textBinding(for: .audioMode, value: $audioMode),
                    audioBitrateKbps: textBinding(for: .audioBitrateKbps, value: $audioBitrateKbps),
                    writtenMode: textBinding(for: .writtenMode, value: $writtenMode),
                    tempo: tempoBinding,
                    formattedTempo: formattedTempo,
                    estimatedAudioDurationLabel: estimatedAudioDurationLabel,
                    sentencesPerOutputFile: bookSentencesPerOutputFileBinding,
                    clampedSentencesPerOutputFile: clampedBookSentencesPerOutputFile,
                    stitchFull: boolBinding(for: .stitchFull, value: $stitchFull),
                    includeTransliteration: boolBinding(for: .includeTransliteration, value: $includeTransliteration),
                    translationProvider: bookTranslationProviderBinding,
                    selectedTranslationProvider: bookTranslationProvider,
                    llmModel: textBinding(for: .bookLlmModel, value: $bookLlmModel),
                    availableLlmModels: availableSubtitleLlmModels,
                    translationBatchSize: bookTranslationBatchSizeBinding,
                    clampedTranslationBatchSize: clampedBookTranslationBatchSize,
                    transliterationMode: bookTransliterationModeBinding,
                    selectedTransliterationMode: bookTransliterationMode,
                    transliterationModel: textBinding(
                        for: .bookTransliterationModel,
                        value: $bookTransliterationModel
                    ),
                    availableTransliterationModels: availableBookTransliterationModels,
                    enableLookupCache: boolBinding(for: .enableLookupCache, value: $enableLookupCache),
                    lookupCacheBatchSize: bookLookupCacheBatchSizeBinding,
                    clampedLookupCacheBatchSize: clampedBookLookupCacheBatchSize,
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
                    supportsImages: creationMode == .generatedBook
                )
            }
        }
    }

    private var youtubeMetadataSection: some View {
        Section("Metadata") {
            AppleBookCreateYoutubeMetadataControls(
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
                onLoadTvMetadata: {
                    Task {
                        await viewModel.lookupYoutubeTvMetadata(
                            sourceName: youtubeMetadataTvSourceName,
                            using: appState
                        )
                    }
                },
                onLoadYoutubeMetadata: {
                    Task {
                        await viewModel.lookupYoutubeVideoMetadata(
                            sourceName: youtubeMetadataVideoSourceName,
                            using: appState
                        )
                    }
                },
                onClearTvMetadataCache: {
                    Task {
                        await viewModel.clearYoutubeTvMetadataCache(
                            query: youtubeMetadataTvSourceName,
                            using: appState
                        )
                    }
                },
                onClearYoutubeMetadataCache: {
                    Task {
                        await viewModel.clearYoutubeVideoMetadataCache(
                            query: youtubeMetadataVideoSourceName,
                            using: appState
                        )
                    }
                }
            )
        }
    }

    private var subtitleMetadataSection: some View {
        Section("Metadata") {
            AppleBookCreateSubtitleMetadataControls(
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
                onLookup: {
                    Task {
                        await viewModel.lookupSubtitleTvMetadata(
                            sourceName: subtitleMetadataLookupSourceName,
                            using: appState
                        )
                    }
                },
                onRefresh: {
                    Task {
                        await viewModel.lookupSubtitleTvMetadata(
                            sourceName: subtitleMetadataLookupSourceName,
                            force: true,
                            using: appState
                        )
                    }
                },
                onClear: {
                    viewModel.clearSubtitleMetadata()
                },
                onClearCache: {
                    Task {
                        await viewModel.clearSubtitleTvMetadataCache(
                            query: subtitleMetadataLookupSourceName,
                            using: appState
                        )
                    }
                }
            )
        }
    }

    @ViewBuilder
    private var statusSection: some View {
        if viewModel.isLoadingOptions {
            Section {
                Label("Loading backend creation defaults", systemImage: "arrow.triangle.2.circlepath")
                    .foregroundStyle(.secondary)
                    .accessibilityIdentifier("createBookOptionsLoadingLabel")
            }
        } else if let optionsErrorMessage = viewModel.optionsErrorMessage {
            Section {
                Label("Using built-in defaults", systemImage: "exclamationmark.arrow.triangle.2.circlepath")
                    .foregroundStyle(.secondary)
                    .accessibilityIdentifier("createBookOptionsFallbackLabel")
                Text(optionsErrorMessage)
                    .font(.footnote)
                    .foregroundStyle(.secondary)
                    .accessibilityIdentifier("createBookOptionsErrorLabel")
                Button {
                    Task { await refreshCreationOptions(force: true) }
                } label: {
                    Label("Retry Defaults", systemImage: "arrow.clockwise")
                }
                .accessibilityIdentifier("createBookOptionsRetryButton")
            }
        }

        if let errorMessage = viewModel.errorMessage {
            Section {
                Label(errorMessage, systemImage: "exclamationmark.triangle.fill")
                    .foregroundStyle(.red)
                    .accessibilityIdentifier("createBookErrorLabel")
            }
        }

        if let intakeStatus = viewModel.intakeStatus {
            Section {
                let presentation = AppleBookCreatePresentation.intakeStatusPresentation(for: intakeStatus)
                Label(presentation.label, systemImage: intakeStatusSystemImage(for: intakeStatus))
                    .foregroundStyle(intakeStatusForegroundStyle(for: intakeStatus))
                    .accessibilityIdentifier("createBookIntakeStatusLabel")
                ForEach(presentation.detailLines, id: \.self) { detailLine in
                    Text(detailLine)
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }
            }
        } else if viewModel.isLoadingIntakeStatus {
            Section {
                Label("Checking job intake...", systemImage: "clock.arrow.circlepath")
                    .foregroundStyle(.secondary)
                    .accessibilityIdentifier("createBookIntakeStatusLoadingLabel")
            }
        }

        if let submittedJobId = viewModel.submittedJobId {
            Section {
                Label("Job \(submittedJobId)", systemImage: "checkmark.circle.fill")
                    .foregroundStyle(.green)
                    .accessibilityIdentifier("createBookSubmittedJobLabel")
                Button {
                    onOpenJobs(submittedJobId)
                } label: {
                    Label("Open Jobs", systemImage: "tray.full")
                }
                .accessibilityIdentifier("createBookOpenJobsButton")
            }
        }
    }

    private var submitSection: some View {
        Section {
            Button {
                submit()
            } label: {
                let presentation = AppleBookCreatePresentation.submitButtonPresentation(
                    for: creationMode,
                    isSubmitting: viewModel.isSubmitting
                )
                Label(presentation.title, systemImage: presentation.systemImage)
            }
            .disabled(!canSubmit || viewModel.isSubmitting || isIntakeAtCapacity)
            .accessibilityIdentifier("createBookSubmitButton")
            #if !os(tvOS)
            if let handoffURL = webCreateHandoffURL {
                Button {
                    openURL(handoffURL)
                } label: {
                    Label("Open Web Create", systemImage: "safari")
                }
                .accessibilityIdentifier("createBookOpenWebCreateButton")
            }
            #endif
        }
    }

    private var canSubmit: Bool {
        AppleBookCreatePresentation.canSubmit(submitState)
    }

    private var isIntakeAtCapacity: Bool {
        viewModel.intakeStatus?.acceptingJobs == false
    }

    private var submitState: AppleCreateSubmitState {
        AppleCreateSubmitState(
            hasConfiguration: appState.configuration != nil,
            mode: creationMode,
            topic: topic,
            bookName: bookName,
            genre: genre,
            hasNarrateLocalFile: selectedNarrateFileURL != nil,
            sourcePath: sourcePath,
            sourceBaseOutput: sourceBaseOutput,
            hasSubtitleLocalFile: selectedSubtitleFileURL != nil,
            subtitleSourcePath: subtitleSourcePath,
            youtubeVideoPath: youtubeVideoPath,
            youtubeSubtitlePath: youtubeSubtitlePath
        )
    }

    private var availableCreateModes: [AppleCreateMode] {
        AppleBookCreatePresentation.availableCreateModes(isTV: Self.isTVPlatform)
    }

    private var webCreateHandoffURL: URL? {
        AppleBookCreatePresentation.webCreateHandoffURL(
            apiBaseURL: appState.apiBaseURL,
            mode: creationMode
        )
    }

    private func intakeStatusSystemImage(for status: PipelineIntakeStatusResponse) -> String {
        if !status.acceptingJobs {
            return "pause.circle.fill"
        }
        if status.isUnderPressure {
            return "clock.badge.exclamationmark"
        }
        return "checkmark.circle.fill"
    }

    private func intakeStatusForegroundStyle(for status: PipelineIntakeStatusResponse) -> Color {
        if !status.acceptingJobs {
            return .red
        }
        if status.isUnderPressure {
            return .orange
        }
        return .green
    }

    private var derivedBaseOutput: String {
        AppleBookCreatePresentation.derivedBaseOutput(
            for: creationMode,
            topic: topic,
            bookName: bookName,
            sourceBaseOutput: sourceBaseOutput,
            subtitleSourcePath: subtitleSourcePath,
            youtubeVideoPath: youtubeVideoPath
        )
    }

    private var youtubeMetadataTvSourceName: String {
        trimmed(youtubeSubtitlePath).nonEmptyValue ?? trimmed(youtubeVideoPath)
    }

    private var youtubeMetadataVideoSourceName: String {
        trimmed(youtubeVideoPath)
    }

    private var subtitleMetadataSourceName: String {
        defaultSubtitleMetadataLookupSourceName
    }

    private var defaultSubtitleMetadataLookupSourceName: String {
        if let fileName = selectedSubtitleFileName?.nonEmptyValue {
            return fileName
        }
        let selectedPath = trimmed(subtitleSourcePath)
        if let entryName = viewModel.subtitleSources?.sources.first(where: { $0.path == selectedPath })?.name.nonEmptyValue {
            return entryName
        }
        guard !selectedPath.isEmpty else {
            return ""
        }
        return URL(fileURLWithPath: selectedPath).lastPathComponent
    }

    private static var isTVPlatform: Bool {
        #if os(tvOS)
        return true
        #else
        return false
        #endif
    }

    private func submit() {
        switch creationMode {
        case .generatedBook:
            submitGeneratedBook()
        case .narrateEbook:
            submitNarrateEbook()
        case .subtitleJob:
            submitSubtitleJob()
        case .youtubeDub:
            submitYoutubeDub()
        }
    }

    private func submitGeneratedBook() {
        let draft = AppleBookCreatePresentation.generatedBookDraft(
            topic: trimmed(topic),
            bookName: trimmed(bookName),
            genre: trimmed(genre),
            author: author,
            summary: bookSummary,
            year: bookYear,
            isbn: bookIsbn,
            coverFile: bookCoverFile,
            sourceBookTitle: sourceBookTitle,
            sourceBookAuthor: sourceBookAuthor,
            sourceBookGenre: sourceBookGenre,
            sourceBookSummary: bookSummary,
            sentenceCount: sentenceCount,
            inputLanguage: inputLanguage,
            targetLanguage: targetLanguage,
            additionalTargetLanguages: additionalTargetLanguages,
            voice: voice,
            targetVoice: targetVoice,
            languageVoiceOverrides: languageVoiceOverrides,
            baseOutput: derivedBaseOutput,
            generateAudio: generateAudio,
            audioMode: audioMode,
            audioBitrateKbps: audioBitrateKbps,
            writtenMode: writtenMode,
            tempo: tempo,
            sentencesPerOutputFile: bookSentencesPerOutputFile,
            stitchFull: stitchFull,
            includeTransliteration: includeTransliteration,
            translationProvider: bookTranslationProvider,
            llmModel: bookLlmModel,
            translationBatchSize: bookTranslationBatchSize,
            transliterationMode: bookTransliterationMode,
            transliterationModel: bookTransliterationModel,
            enableLookupCache: enableLookupCache,
            lookupCacheBatchSize: bookLookupCacheBatchSize,
            outputHtml: outputHtml,
            outputPdf: outputPdf,
            includeImages: includeImages,
            imagePromptPipeline: imagePromptPipeline,
            imageStyleTemplate: imageStyleTemplate,
            imagePromptBatchingEnabled: imagePromptBatchingEnabled,
            imagePromptBatchSize: imagePromptBatchSize,
            imagePromptPlanBatchSize: imagePromptPlanBatchSize,
            imagePromptContextSentences: imagePromptContextSentences,
            imageWidth: imageWidth,
            imageHeight: imageHeight,
            imageSteps: imageSteps,
            imageCfgScale: imageCfgScale,
            imageSamplerName: imageSamplerName,
            imageSeedWithPreviousImage: imageSeedWithPreviousImage,
            imageBlankDetectionEnabled: imageBlankDetectionEnabled,
            imageApiBaseURLs: imageApiBaseURLs,
            imageConcurrency: imageConcurrency,
            imageApiTimeoutSeconds: imageApiTimeoutSeconds,
            threadCount: bookThreadCount,
            queueSize: bookQueueSize,
            jobMaxWorkers: bookJobMaxWorkers,
            pipelineDefaults: viewModel.creationOptions?.pipelineDefaults,
            generatedSourceDefaults: viewModel.creationOptions?.generatedSourceDefaults
        )

        Task {
            if let jobId = await viewModel.submitGeneratedBook(draft, using: appState) {
                await refreshIntakeStatus(force: true)
                onJobSubmitted(jobId)
            }
        }
    }

    private func submitSubtitleJob() {
        let timeRange: AppleCreateTimeRange
        switch AppleBookCreatePresentation.normalizedSubtitleTimeRange(
            start: subtitleStartTime,
            end: subtitleEndTime
        ) {
        case let .success(normalizedRange):
            timeRange = normalizedRange
        case let .failure(error):
            viewModel.errorMessage = error.message
            return
        }
        subtitleStartTime = timeRange.start
        subtitleEndTime = timeRange.end

        let draft = AppleBookCreatePresentation.subtitleJobDraft(
            sourcePath: subtitleSourcePath,
            mediaMetadata: viewModel.subtitleMediaMetadataDraft,
            inputLanguage: inputLanguage,
            targetLanguage: targetLanguage,
            outputFormat: subtitleOutputFormat,
            startTime: timeRange.start,
            endTime: timeRange.end,
            enableTransliteration: subtitleEnableTransliteration,
            highlight: subtitleHighlight,
            showOriginal: subtitleShowOriginal,
            generateAudioBook: subtitleGenerateAudioBook,
            mirrorBatchesToSourceDir: subtitleMirrorBatchesToSourceDir,
            translationProvider: subtitleTranslationProvider,
            llmModel: subtitleLlmModel,
            transliterationMode: subtitleTransliterationMode,
            transliterationModel: subtitleTransliterationModel,
            workerCount: subtitleWorkerCount,
            batchSize: subtitleBatchSize,
            translationBatchSize: subtitleTranslationBatchSize,
            assFontSize: subtitleAssFontSize,
            assEmphasisScale: subtitleAssEmphasisScale
        )

        Task {
            if let jobId = await viewModel.submitSubtitleJob(
                draft,
                localFileURL: selectedSubtitleFileURL,
                localFilename: selectedSubtitleFileName,
                using: appState
            ) {
                await refreshIntakeStatus(force: true)
                onJobSubmitted(jobId)
            }
        }
    }

    private func submitYoutubeDub() {
        let offsetRange: AppleCreateOffsetRange
        switch AppleBookCreatePresentation.normalizedYoutubeOffsetRange(
            start: youtubeStartOffset,
            end: youtubeEndOffset
        ) {
        case let .success(normalizedRange):
            offsetRange = normalizedRange
        case let .failure(error):
            viewModel.errorMessage = error.message
            return
        }
        youtubeStartOffset = offsetRange.start
        youtubeEndOffset = offsetRange.end

        let draft = AppleBookCreatePresentation.youtubeDubDraft(
            videoPath: youtubeVideoPath,
            subtitlePath: youtubeSubtitlePath,
            sourceLanguage: inputLanguage,
            subtitleLanguage: AppleBookCreatePresentation.youtubeSubtitleLanguage(
                from: viewModel.youtubeLibrary,
                videoPath: youtubeVideoPath,
                subtitlePath: youtubeSubtitlePath
            ),
            targetLanguage: targetLanguage,
            voice: voice,
            mediaMetadata: viewModel.youtubeMediaMetadataDraft,
            startTimeOffset: offsetRange.start,
            endTimeOffset: offsetRange.end,
            originalMixPercent: youtubeOriginalMixPercent,
            flushSentences: youtubeFlushSentences,
            translationProvider: subtitleTranslationProvider,
            llmModel: subtitleLlmModel,
            translationBatchSize: subtitleTranslationBatchSize,
            transliterationMode: subtitleTransliterationMode,
            transliterationModel: subtitleTransliterationModel,
            splitBatches: youtubeSplitBatches,
            stitchBatches: youtubeStitchBatches,
            includeTransliteration: includeTransliteration,
            targetHeight: youtubeTargetHeight,
            preserveAspectRatio: youtubePreserveAspectRatio,
            enableLookupCache: enableLookupCache
        )

        Task {
            if let jobId = await viewModel.submitYoutubeDub(draft, using: appState) {
                await refreshIntakeStatus(force: true)
                onJobSubmitted(jobId)
            }
        }
    }

    private func submitNarrateEbook() {
        let draft = AppleBookCreatePresentation.narrateEbookDraft(
            inputFile: sourcePath,
            baseOutput: sourceBaseOutput,
            title: sourceBookTitle,
            author: sourceBookAuthor,
            genre: sourceBookGenre,
            summary: bookSummary,
            year: bookYear,
            isbn: bookIsbn,
            coverFile: bookCoverFile,
            startSentence: sourceStartSentence,
            endSentence: sourceEndSentence,
            inputLanguage: inputLanguage,
            targetLanguage: targetLanguage,
            additionalTargetLanguages: additionalTargetLanguages,
            voice: voice,
            targetVoice: targetVoice,
            languageVoiceOverrides: languageVoiceOverrides,
            generateAudio: generateAudio,
            audioMode: audioMode,
            audioBitrateKbps: audioBitrateKbps,
            writtenMode: writtenMode,
            tempo: tempo,
            sentencesPerOutputFile: bookSentencesPerOutputFile,
            stitchFull: stitchFull,
            includeTransliteration: includeTransliteration,
            translationProvider: bookTranslationProvider,
            llmModel: bookLlmModel,
            translationBatchSize: bookTranslationBatchSize,
            transliterationMode: bookTransliterationMode,
            transliterationModel: bookTransliterationModel,
            enableLookupCache: enableLookupCache,
            lookupCacheBatchSize: bookLookupCacheBatchSize,
            outputHtml: outputHtml,
            outputPdf: outputPdf,
            threadCount: bookThreadCount,
            queueSize: bookQueueSize,
            jobMaxWorkers: bookJobMaxWorkers,
            pipelineDefaults: viewModel.creationOptions?.pipelineDefaults
        )

        Task {
            if let jobId = await viewModel.submitNarrateEbook(
                draft,
                localFileURL: selectedNarrateFileURL,
                localFilename: selectedNarrateFileName,
                using: appState
            ) {
                await refreshIntakeStatus(force: true)
                onJobSubmitted(jobId)
            }
        }
    }

    private func loadNarrateChapters() {
        Task {
            selectedNarrateStartChapterID = ""
            selectedNarrateEndChapterID = ""
            await viewModel.loadNarrateChapters(inputFile: sourcePath, using: appState)
        }
    }

    private func refreshIntakeStatus(force: Bool = false) async {
        await viewModel.loadIntakeStatus(
            using: appState,
            cacheKey: creationOptionsLoadKey,
            force: force
        )
    }

    private func refreshPipelineFiles(force: Bool = false) async {
        guard !Self.isTVPlatform else { return }
        let files = await viewModel.loadPipelineFiles(
            using: appState,
            cacheKey: creationOptionsLoadKey,
            force: force
        )
        applyPreferredNarrateSource(from: files)
    }

    private func refreshSubtitleSources(force: Bool = false) async {
        guard !Self.isTVPlatform else { return }
        let sources = await viewModel.loadSubtitleSources(
            using: appState,
            cacheKey: creationOptionsLoadKey,
            force: force
        )
        applyPreferredSubtitleSource(from: sources)
    }

    private func refreshYoutubeLibrary(force: Bool = false) async {
        guard !Self.isTVPlatform else { return }
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
        guard
            selectedNarrateFileURL == nil,
            !editedFields.contains(.sourcePath),
            trimmed(sourcePath).isEmpty,
            let entry = AppleBookCreatePresentation.preferredPipelineEbook(from: files)
        else {
            return
        }

        sourcePath = entry.path
        if trimmed(sourceBaseOutput).isEmpty && !editedFields.contains(.sourceBaseOutput) {
            sourceBaseOutput = AppleBookCreatePresentation.deriveBaseOutputName(entry.name)
        }
    }

    private func applyPreferredSubtitleSource(from sources: SubtitleSourceListResponse?) {
        guard
            selectedSubtitleFileURL == nil,
            !editedFields.contains(.subtitleSourcePath),
            trimmed(subtitleSourcePath).isEmpty,
            let entry = AppleBookCreatePresentation.preferredSubtitleSource(from: sources)
        else {
            return
        }

        subtitleSourcePath = entry.path
        subtitleMetadataLookupSourceName = entry.name
    }

    private func applyPreferredYoutubeSource(from library: YoutubeNasLibraryResponse?) {
        let scopeChanged = youtubeSelectionStorageScope != youtubeLibraryLoadKey
        youtubeSelectionStorageScope = youtubeLibraryLoadKey
        guard let selection = AppleBookCreatePresentation.youtubeSelection(
            from: library,
            storedVideoPath: storedYoutubeSelectionPath(field: "video"),
            storedSubtitlePath: storedYoutubeSelectionPath(field: "subtitle")
        ) else {
            return
        }

        if !editedFields.contains(.youtubeVideoPath), trimmed(youtubeVideoPath).isEmpty || scopeChanged {
            youtubeVideoPath = selection.video.path
        }
        if !editedFields.contains(.youtubeSubtitlePath), trimmed(youtubeSubtitlePath).isEmpty || scopeChanged {
            youtubeSubtitlePath = selection.subtitle?.path ?? ""
        }
    }

    private func applyHistoryDefaultsForCurrentMode() {
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
            sourcePath = inputFile
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
           let videoPath = defaults.videoPath?.nonEmptyValue {
            youtubeVideoPath = videoPath
        }
        if !editedFields.contains(.youtubeSubtitlePath),
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
        if !editedFields.contains(.includeTransliteration),
           let includeTransliteration = defaults.includeTransliteration {
            self.includeTransliteration = includeTransliteration
        }
        if !editedFields.contains(.youtubeTargetHeight),
           let targetHeight = defaults.targetHeight {
            youtubeTargetHeight = targetHeight
        }
        if !editedFields.contains(.youtubePreserveAspectRatio),
           let preserveAspectRatio = defaults.preserveAspectRatio {
            youtubePreserveAspectRatio = preserveAspectRatio
        }
        if !editedFields.contains(.enableLookupCache),
           let enableLookupCache = defaults.enableLookupCache {
            self.enableLookupCache = enableLookupCache
        }
    }

    private func clearNarrateChapterSelection() {
        selectedNarrateStartChapterID = ""
        selectedNarrateEndChapterID = ""
        viewModel.clearNarrateChapters()
    }

    private func trimmed(_ value: String) -> String {
        value.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private func storedYoutubeSelectionPath(field: String) -> String? {
        UserDefaults.standard.string(forKey: youtubeSelectionStorageKey(field: field))?.nonEmptyValue
    }

    private func applyStoredYoutubeBaseDir() {
        guard let baseDir = UserDefaults.standard.string(forKey: youtubeBaseDirStorageKey)?.nonEmptyValue else {
            return
        }
        youtubeBaseDir = baseDir
    }

    private func persistYoutubeBaseDir(_ baseDir: String) {
        if let value = baseDir.nonEmptyValue {
            UserDefaults.standard.set(value, forKey: youtubeBaseDirStorageKey)
        } else {
            UserDefaults.standard.removeObject(forKey: youtubeBaseDirStorageKey)
        }
    }

    private func persistYoutubeSelectionPath(_ path: String, field: String) {
        let key = youtubeSelectionStorageKey(field: field)
        if let value = path.nonEmptyValue {
            UserDefaults.standard.set(value, forKey: key)
        } else {
            UserDefaults.standard.removeObject(forKey: key)
        }
    }

    private func youtubeSelectionStorageKey(field: String) -> String {
        "ebookTools.appleCreate.youtubeDub.\(field).\(creationOptionsLoadKey)"
    }

    private func applyStoredSubtitleShowOriginal() {
        guard UserDefaults.standard.object(forKey: subtitleShowOriginalStorageKey) != nil else {
            return
        }
        subtitleShowOriginal = UserDefaults.standard.bool(forKey: subtitleShowOriginalStorageKey)
    }

    private func persistSubtitleShowOriginal(_ value: Bool) {
        UserDefaults.standard.set(value, forKey: subtitleShowOriginalStorageKey)
    }

    private var subtitleShowOriginalStorageKey: String {
        AppleBookCreatePresentation.subtitleShowOriginalPreferenceKey(baseKey: creationOptionsLoadKey)
    }

    private var youtubeBaseDirStorageKey: String {
        "ebookTools.appleCreate.youtubeDub.baseDir.\(creationOptionsLoadKey)"
    }

    private var youtubeLibraryLoadKey: String {
        AppleBookCreatePresentation.youtubeLibraryCacheKey(
            baseKey: creationOptionsLoadKey,
            baseDir: youtubeBaseDir
        )
    }

    #if os(iOS)
    private func handleNarrateEbookImport(_ result: Result<[URL], Error>) {
        switch result {
        case let .success(urls):
            guard let url = urls.first else { return }
            selectedNarrateFileURL = url
            selectedNarrateFileName = url.lastPathComponent
            sourcePath = ""
            clearNarrateChapterSelection()
            markEdited(.sourcePath)
            if trimmed(sourceBaseOutput).isEmpty && !editedFields.contains(.sourceBaseOutput) {
                sourceBaseOutput = AppleBookCreatePresentation.deriveBaseOutputName(
                    url.deletingPathExtension().lastPathComponent
                )
            }
        case let .failure(error):
            selectedNarrateFileURL = nil
            selectedNarrateFileName = nil
            viewModel.errorMessage = error.localizedDescription
        }
    }

    private func handleSubtitleFileImport(_ result: Result<[URL], Error>) {
        switch result {
        case let .success(urls):
            guard let url = urls.first else { return }
            selectedSubtitleFileURL = url
            selectedSubtitleFileName = url.lastPathComponent
            subtitleMetadataLookupSourceName = url.lastPathComponent
            viewModel.clearSubtitleMetadata()
            markEdited(.subtitleSourcePath)
        case let .failure(error):
            selectedSubtitleFileURL = nil
            selectedSubtitleFileName = nil
            viewModel.errorMessage = error.localizedDescription
        }
    }

    private static var epubContentType: UTType {
        UTType(filenameExtension: "epub") ?? UTType(importedAs: "org.idpf.epub-container")
    }

    private static var subtitleContentTypes: [UTType] {
        [
            UTType(filenameExtension: "srt") ?? UTType(importedAs: "com.subrip.srt"),
            UTType(filenameExtension: "vtt") ?? UTType(importedAs: "org.webvtt"),
            UTType.plainText
        ]
    }
    #endif

    private var creationOptionsLoadKey: String {
        guard let configuration = appState.configuration else { return "missing" }
        return [
            configuration.apiBaseURL.absoluteString,
            configuration.userID ?? "",
            configuration.userRole ?? ""
        ].joined(separator: "|")
    }

    private var sentenceBounds: BookCreationSentenceBounds {
        viewModel.creationOptions?.sentenceBounds ?? BookCreationSentenceBounds(min: 1, max: 500, default: 30)
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
        var result = [String: [AppleBookCreateVoiceOption]]()
        for language in targetLanguagesForVoiceOverrides {
            let selected = languageVoiceOverrides[language].flatMap(AppleBookCreateVoiceOption.init(backendValue:))
            result[language] = AppleBookCreatePresentation.availableVoices(
                from: viewModel.creationOptions,
                inventory: viewModel.voiceInventory,
                language: language,
                selected: selected ?? targetVoice ?? voice
            )
        }
        return result
    }

    private var targetLanguagesForVoiceOverrides: [String] {
        switch creationMode {
        case .generatedBook, .narrateEbook:
            return AppleBookCreatePresentation.normalizedTargetLanguages(
                primary: targetLanguage.backendValue,
                additionalTargets: additionalTargetLanguages
            )
        case .subtitleJob, .youtubeDub:
            return []
        }
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

    private var clampedAssFontSize: Int {
        AppleBookCreatePresentation.clampAssFontSize(subtitleAssFontSize)
    }

    private var clampedAssEmphasisScale: Double {
        AppleBookCreatePresentation.clampAssEmphasisScale(subtitleAssEmphasisScale)
    }

    private var clampedSubtitleTranslationBatchSize: Int {
        AppleBookCreatePresentation.clampSubtitleTranslationBatchSize(subtitleTranslationBatchSize)
    }

    private var clampedBookTranslationBatchSize: Int {
        AppleBookCreatePresentation.clampSubtitleTranslationBatchSize(bookTranslationBatchSize)
    }

    private var clampedBookSentencesPerOutputFile: Int {
        AppleBookCreatePresentation.clampBookSentencesPerOutputFile(bookSentencesPerOutputFile)
    }

    private var clampedBookLookupCacheBatchSize: Int {
        AppleBookCreatePresentation.clampSubtitleTranslationBatchSize(bookLookupCacheBatchSize)
    }

    private var clampedSubtitleWorkerCount: Int {
        AppleBookCreatePresentation.clampSubtitleWorkerCount(subtitleWorkerCount)
    }

    private var clampedSubtitleBatchSize: Int {
        AppleBookCreatePresentation.clampSubtitleBatchSize(subtitleBatchSize)
    }

    private var clampedYoutubeOriginalMixPercent: Double {
        AppleBookCreatePresentation.clampYoutubeOriginalMixPercent(youtubeOriginalMixPercent)
    }

    private var clampedYoutubeFlushSentences: Int {
        AppleBookCreatePresentation.clampYoutubeFlushSentences(youtubeFlushSentences)
    }

    private var clampedImagePromptContextSentences: Int {
        AppleBookCreatePresentation.clampImagePromptContextSentences(imagePromptContextSentences)
    }

    private var clampedImagePromptBatchSize: Int {
        AppleBookCreatePresentation.clampImagePromptBatchSize(imagePromptBatchSize)
    }

    private var clampedImagePromptPlanBatchSize: Int {
        AppleBookCreatePresentation.clampImagePromptBatchSize(imagePromptPlanBatchSize)
    }

    private var sentenceCountBinding: Binding<Int> {
        Binding(
            get: { sentenceCount },
            set: { newValue in
                markEdited(.sentenceCount)
                sentenceCount = clampSentenceCount(newValue)
            }
        )
    }

    private var voiceBinding: Binding<AppleBookCreateVoiceOption> {
        Binding(
            get: { voice },
            set: { newValue in
                markEdited(.voice)
                voice = newValue
            }
        )
    }

    private var targetVoiceBinding: Binding<AppleBookCreateVoiceOption?> {
        Binding(
            get: { targetVoice },
            set: { newValue in
                markEdited(.targetVoice)
                targetVoice = newValue
            }
        )
    }

    private var voiceOverridesBinding: Binding<[String: String]> {
        Binding(
            get: { languageVoiceOverrides },
            set: { newValue in
                markEdited(.languageVoiceOverrides)
                languageVoiceOverrides = newValue
            }
        )
    }

    private var subtitleOutputFormatBinding: Binding<AppleSubtitleOutputFormat> {
        Binding(
            get: { subtitleOutputFormat },
            set: { newValue in
                markEdited(.subtitleOutputFormat)
                subtitleOutputFormat = newValue
            }
        )
    }

    private var subtitleTranslationProviderBinding: Binding<AppleSubtitleTranslationProvider> {
        Binding(
            get: { subtitleTranslationProvider },
            set: { newValue in
                markEdited(.subtitleTranslationProvider)
                subtitleTranslationProvider = newValue
            }
        )
    }

    private var bookTranslationProviderBinding: Binding<AppleSubtitleTranslationProvider> {
        Binding(
            get: { bookTranslationProvider },
            set: { newValue in
                markEdited(.bookTranslationProvider)
                bookTranslationProvider = newValue
                if newValue != .llm {
                    bookLlmModel = ""
                }
            }
        )
    }

    private var subtitleTransliterationModeBinding: Binding<AppleSubtitleTransliterationMode> {
        Binding(
            get: { subtitleTransliterationMode },
            set: { newValue in
                markEdited(.subtitleTransliterationMode)
                subtitleTransliterationMode = newValue
                if !newValue.allowsModelOverride {
                    subtitleTransliterationModel = ""
                }
            }
        )
    }

    private var bookTransliterationModeBinding: Binding<AppleSubtitleTransliterationMode> {
        Binding(
            get: { bookTransliterationMode },
            set: { newValue in
                markEdited(.bookTransliterationMode)
                bookTransliterationMode = newValue
                if !newValue.allowsModelOverride {
                    bookTransliterationModel = ""
                }
            }
        )
    }

    private var subtitleTranslationBatchSizeBinding: Binding<Int> {
        Binding(
            get: { clampedSubtitleTranslationBatchSize },
            set: { newValue in
                markEdited(.subtitleTranslationBatchSize)
                subtitleTranslationBatchSize = min(
                    AppleSubtitleTuning.translationBatchSizeRange.upperBound,
                    max(AppleSubtitleTuning.translationBatchSizeRange.lowerBound, newValue)
                )
            }
        )
    }

    private var bookTranslationBatchSizeBinding: Binding<Int> {
        Binding(
            get: { clampedBookTranslationBatchSize },
            set: { newValue in
                markEdited(.bookTranslationBatchSize)
                bookTranslationBatchSize = min(
                    AppleSubtitleTuning.translationBatchSizeRange.upperBound,
                    max(AppleSubtitleTuning.translationBatchSizeRange.lowerBound, newValue)
                )
            }
        )
    }

    private var bookSentencesPerOutputFileBinding: Binding<Int> {
        Binding(
            get: { clampedBookSentencesPerOutputFile },
            set: { newValue in
                markEdited(.bookSentencesPerOutputFile)
                bookSentencesPerOutputFile = min(
                    AppleBookOutputChunking.sentencesPerOutputFileRange.upperBound,
                    max(AppleBookOutputChunking.sentencesPerOutputFileRange.lowerBound, newValue)
                )
            }
        )
    }

    private var bookLookupCacheBatchSizeBinding: Binding<Int> {
        Binding(
            get: { clampedBookLookupCacheBatchSize },
            set: { newValue in
                markEdited(.bookLookupCacheBatchSize)
                bookLookupCacheBatchSize = min(
                    AppleSubtitleTuning.translationBatchSizeRange.upperBound,
                    max(AppleSubtitleTuning.translationBatchSizeRange.lowerBound, newValue)
                )
            }
        )
    }

    private var subtitleWorkerCountBinding: Binding<Int> {
        Binding(
            get: { clampedSubtitleWorkerCount },
            set: { newValue in
                markEdited(.subtitleWorkerCount)
                subtitleWorkerCount = min(
                    AppleSubtitleTuning.workerCountRange.upperBound,
                    max(AppleSubtitleTuning.workerCountRange.lowerBound, newValue)
                )
            }
        )
    }

    private var subtitleBatchSizeBinding: Binding<Int> {
        Binding(
            get: { clampedSubtitleBatchSize },
            set: { newValue in
                markEdited(.subtitleBatchSize)
                subtitleBatchSize = min(
                    AppleSubtitleTuning.batchSizeRange.upperBound,
                    max(AppleSubtitleTuning.batchSizeRange.lowerBound, newValue)
                )
            }
        )
    }

    private var subtitleAssFontSizeBinding: Binding<Int> {
        Binding(
            get: { clampedAssFontSize },
            set: { newValue in
                markEdited(.subtitleAssFontSize)
                subtitleAssFontSize = min(
                    AppleSubtitleAssTypography.fontSizeRange.upperBound,
                    max(AppleSubtitleAssTypography.fontSizeRange.lowerBound, newValue)
                )
            }
        )
    }

    private var subtitleAssEmphasisScaleBinding: Binding<Double> {
        Binding(
            get: { clampedAssEmphasisScale },
            set: { newValue in
                markEdited(.subtitleAssEmphasisScale)
                let rounded = (newValue * 100).rounded() / 100
                subtitleAssEmphasisScale = min(
                    AppleSubtitleAssTypography.emphasisScaleRange.upperBound,
                    max(AppleSubtitleAssTypography.emphasisScaleRange.lowerBound, rounded)
                )
            }
        )
    }

    private var tempoBinding: Binding<Double> {
        Binding(
            get: { AppleBookCreatePresentation.clampTempo(tempo) },
            set: { newValue in
                markEdited(.tempo)
                let rounded = (newValue * 10).rounded() / 10
                tempo = AppleBookCreatePresentation.clampTempo(rounded)
            }
        )
    }

    private var youtubeTargetHeightBinding: Binding<AppleYoutubeDubTargetHeight> {
        Binding(
            get: { youtubeTargetHeight },
            set: { newValue in
                markEdited(.youtubeTargetHeight)
                youtubeTargetHeight = newValue
            }
        )
    }

    private var youtubeOriginalMixPercentBinding: Binding<Double> {
        Binding(
            get: { clampedYoutubeOriginalMixPercent },
            set: { newValue in
                markEdited(.youtubeOriginalMixPercent)
                youtubeOriginalMixPercent = min(100, max(0, (newValue / 5).rounded() * 5))
            }
        )
    }

    private var youtubeFlushSentencesBinding: Binding<Int> {
        Binding(
            get: { clampedYoutubeFlushSentences },
            set: { newValue in
                markEdited(.youtubeFlushSentences)
                youtubeFlushSentences = min(200, max(1, newValue))
            }
        )
    }

    private func textBinding(for field: AppleBookCreateEditedField, value: Binding<String>) -> Binding<String> {
        Binding(
            get: { value.wrappedValue },
            set: { newValue in
                markEdited(field)
                value.wrappedValue = newValue
            }
        )
    }

    private func youtubeMetadataTextBinding(section: String?, key: String) -> Binding<String> {
        Binding(
            get: {
                viewModel.youtubeMediaMetadataText(section: section, key: key)
            },
            set: { newValue in
                viewModel.updateYoutubeMediaMetadata(section: section, key: key, value: newValue)
            }
        )
    }

    private func youtubeMetadataNumberBinding(section: String, key: String) -> Binding<String> {
        Binding(
            get: {
                viewModel.youtubeMediaMetadataText(section: section, key: key)
            },
            set: { newValue in
                viewModel.updateYoutubeMediaMetadataNumber(section: section, key: key, value: newValue)
            }
        )
    }

    private func youtubeMetadataNestedTextBinding(section: String, nestedKey: String, key: String) -> Binding<String> {
        Binding(
            get: {
                viewModel.youtubeMediaMetadataNestedText(
                    section: section,
                    nestedKey: nestedKey,
                    keys: key == "medium" ? [key, "original"] : [key]
                )
            },
            set: { newValue in
                viewModel.updateYoutubeMediaMetadataNestedText(
                    section: section,
                    nestedKey: nestedKey,
                    key: key,
                    value: newValue
                )
            }
        )
    }

    private func subtitleMetadataTextBinding(section: String?, key: String) -> Binding<String> {
        Binding(
            get: {
                viewModel.subtitleMediaMetadataText(section: section, key: key)
            },
            set: { newValue in
                viewModel.updateSubtitleMediaMetadata(section: section, key: key, value: newValue)
            }
        )
    }

    private func subtitleMetadataNumberBinding(section: String, key: String) -> Binding<String> {
        Binding(
            get: {
                viewModel.subtitleMediaMetadataText(section: section, key: key)
            },
            set: { newValue in
                viewModel.updateSubtitleMediaMetadataNumber(section: section, key: key, value: newValue)
            }
        )
    }

    private func subtitleMetadataNestedTextBinding(section: String, nestedKey: String, key: String) -> Binding<String> {
        Binding(
            get: {
                viewModel.subtitleMediaMetadataNestedText(
                    section: section,
                    nestedKey: nestedKey,
                    keys: key == "medium" ? [key, "original"] : [key]
                )
            },
            set: { newValue in
                viewModel.updateSubtitleMediaMetadataNestedText(
                    section: section,
                    nestedKey: nestedKey,
                    key: key,
                    value: newValue
                )
            }
        )
    }

    private var narrateSourcePathBinding: Binding<String> {
        Binding(
            get: { sourcePath },
            set: { newValue in
                markEdited(.sourcePath)
                if newValue != sourcePath {
                    selectedNarrateFileURL = nil
                    selectedNarrateFileName = nil
                    clearNarrateChapterSelection()
                }
                sourcePath = newValue
                if trimmed(sourceBaseOutput).isEmpty && !editedFields.contains(.sourceBaseOutput) {
                    sourceBaseOutput = AppleBookCreatePresentation.deriveBaseOutputName(newValue)
                }
            }
        )
    }

    private func languageBinding(
        for field: AppleBookCreateEditedField,
        value: Binding<AppleBookCreateLanguage>
    ) -> Binding<AppleBookCreateLanguage> {
        Binding(
            get: { value.wrappedValue },
            set: { newValue in
                markEdited(field)
                value.wrappedValue = newValue
            }
        )
    }

    private func boolBinding(for field: AppleBookCreateEditedField, value: Binding<Bool>) -> Binding<Bool> {
        Binding(
            get: { value.wrappedValue },
            set: { newValue in
                markEdited(field)
                value.wrappedValue = newValue
            }
        )
    }

    private var imageStyleTemplateBinding: Binding<AppleGeneratedBookImageStyleTemplate> {
        Binding(
            get: { imageStyleTemplate },
            set: { newValue in
                markEdited(.imageStyleTemplate)
                imageStyleTemplate = newValue
            }
        )
    }

    private var imagePromptPipelineBinding: Binding<AppleGeneratedBookImagePromptPipeline> {
        Binding(
            get: { imagePromptPipeline },
            set: { newValue in
                markEdited(.imagePromptPipeline)
                imagePromptPipeline = newValue
            }
        )
    }

    private var imagePromptContextSentencesBinding: Binding<Int> {
        Binding(
            get: { clampedImagePromptContextSentences },
            set: { newValue in
                markEdited(.imagePromptContextSentences)
                imagePromptContextSentences = AppleBookCreatePresentation.clampImagePromptContextSentences(newValue)
            }
        )
    }

    private var imagePromptBatchSizeBinding: Binding<Int> {
        Binding(
            get: { clampedImagePromptBatchSize },
            set: { newValue in
                markEdited(.imagePromptBatchSize)
                imagePromptBatchSize = AppleBookCreatePresentation.clampImagePromptBatchSize(newValue)
            }
        )
    }

    private var imagePromptPlanBatchSizeBinding: Binding<Int> {
        Binding(
            get: { clampedImagePromptPlanBatchSize },
            set: { newValue in
                markEdited(.imagePromptPlanBatchSize)
                imagePromptPlanBatchSize = AppleBookCreatePresentation.clampImagePromptBatchSize(newValue)
            }
        )
    }

    private func markEdited(_ field: AppleBookCreateEditedField) {
        editedFields.insert(field)
    }

    private func refreshCreationOptions(force: Bool = false) async {
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

    private func applyStoredLanguagePreferences() {
        guard
            let data = UserDefaults.standard.data(forKey: languagePreferencesStorageKey),
            let preferences = try? JSONDecoder().decode(AppleCreateLanguagePreferences.self, from: data),
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

    private func persistLanguagePreferences() {
        let preferences = AppleBookCreatePresentation.languagePreferences(
            inputLanguage: inputLanguage,
            targetLanguage: targetLanguage,
            additionalTargetLanguages: additionalTargetLanguages,
            enableLookupCache: enableLookupCache
        )
        guard let data = try? JSONEncoder().encode(preferences) else {
            return
        }
        UserDefaults.standard.set(data, forKey: languagePreferencesStorageKey)
    }

    private var languagePreferencesStorageKey: String {
        "ebookTools.appleCreate.bookJobDefaults.v1.\(creationOptionsLoadKey)"
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
        if let value = defaults.stitchFull {
            stitchFull = value
        }
        if let value = defaults.includeTransliteration {
            includeTransliteration = value
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
    }

    private func clampSentenceCount(_ value: Int) -> Int {
        AppleBookCreatePresentation.clampSentenceCount(value, bounds: sentenceBounds)
    }
}
