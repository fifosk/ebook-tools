import SwiftUI
#if os(iOS)
import UniformTypeIdentifiers
#endif

struct AppleBookCreateView: View {
    @EnvironmentObject private var appState: AppState
    @StateObject private var viewModel = AppleBookCreateViewModel()

    let sectionPicker: BrowseSectionPicker?
    let onJobSubmitted: (String) -> Void
    let onOpenJobs: (String) -> Void
    let usesDarkBackground: Bool

    @State private var creationMode = AppleCreateMode.generatedBook
    @State private var topic = ""
    @State private var bookName = ""
    @State private var genre = ""
    @State private var author = "Me"
    @State private var sourcePath = ""
    @State private var sourceBaseOutput = ""
    @State private var subtitleSourcePath = ""
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
    @State private var voice = AppleBookCreateVoiceOption.gtts
    @State private var includeTransliteration = true
    @State private var enableLookupCache = true
    @State private var editedFields = Set<AppleBookCreateEditedField>()

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            if let sectionPicker {
                sectionPicker
            }

            List {
                sourceSection
                if creationMode == .generatedBook {
                    promptSection
                }
                narrationSection
                outputSection
                statusSection
                submitSection
            }
            #if os(tvOS)
            .listStyle(.plain)
            #else
            .listStyle(.insetGrouped)
            .scrollContentBackground(usesDarkBackground ? .hidden : .automatic)
            #endif
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
        .background(usesDarkBackground ? AppTheme.lightBackground : Color.clear)
        #if os(iOS)
        .toolbarBackground(usesDarkBackground ? AppTheme.lightBackground : Color.clear, for: .navigationBar)
        .toolbarBackground(usesDarkBackground ? .visible : .automatic, for: .navigationBar)
        .toolbarColorScheme(usesDarkBackground ? .dark : nil, for: .navigationBar)
        #endif
        .task(id: creationOptionsLoadKey) {
            await refreshCreationOptions()
            await viewModel.loadSubtitleModels(using: appState, cacheKey: creationOptionsLoadKey)
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

    private var sourceSection: some View {
        Section("Source") {
            Picker("Job type", selection: $creationMode) {
                ForEach(availableCreateModes) { mode in
                    Text(mode.label).tag(mode)
                }
            }
            #if os(iOS)
            .pickerStyle(.segmented)
            #endif
            .accessibilityIdentifier("createJobTypePicker")

            if creationMode == .narrateEbook {
                #if os(iOS)
                narrateEbookImportControl
                #endif
                TextField("Server EPUB path", text: textBinding(for: .sourcePath, value: $sourcePath))
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                    .accessibilityIdentifier("createNarrateSourcePathField")
                TextField("Output path", text: textBinding(for: .sourceBaseOutput, value: $sourceBaseOutput))
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                    .accessibilityIdentifier("createNarrateOutputPathField")
            } else if creationMode == .subtitleJob {
                #if os(iOS)
                subtitleFileImportControl
                #endif
                TextField("Server subtitle path", text: textBinding(for: .subtitleSourcePath, value: $subtitleSourcePath))
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                    .accessibilityIdentifier("createSubtitleSourcePathField")
            } else if creationMode == .youtubeDub {
                TextField("Video path", text: textBinding(for: .youtubeVideoPath, value: $youtubeVideoPath))
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                    .accessibilityIdentifier("createYoutubeVideoPathField")
                TextField("Subtitle path", text: textBinding(for: .youtubeSubtitlePath, value: $youtubeSubtitlePath))
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                    .accessibilityIdentifier("createYoutubeSubtitlePathField")
            }
        }
    }

    #if os(iOS)
    private var narrateEbookImportControl: some View {
        VStack(alignment: .leading, spacing: 8) {
            Button {
                isImportingNarrateEbook = true
            } label: {
                Label(selectedNarrateFileName ?? "Choose EPUB", systemImage: "doc.badge.plus")
            }
            .accessibilityIdentifier("createNarrateFileImportButton")

            if let selectedNarrateFileName {
                Label(selectedNarrateFileName, systemImage: "checkmark.circle")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
                    .lineLimit(2)
                    .accessibilityIdentifier("createNarrateSelectedFileLabel")
            }
        }
    }

    private var subtitleFileImportControl: some View {
        VStack(alignment: .leading, spacing: 8) {
            Button {
                isImportingSubtitleFile = true
            } label: {
                Label(selectedSubtitleFileName ?? "Choose subtitle file", systemImage: "captions.bubble")
            }
            .accessibilityIdentifier("createSubtitleFileImportButton")

            if let selectedSubtitleFileName {
                Label(selectedSubtitleFileName, systemImage: "checkmark.circle")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
                    .lineLimit(2)
                    .accessibilityIdentifier("createSubtitleSelectedFileLabel")
            }
        }
    }
    #endif

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
            sentenceCountControl
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
        Section(creationMode == .subtitleJob ? "Languages" : "Narration") {
            Picker("Input", selection: languageBinding(for: .inputLanguage, value: $inputLanguage)) {
                ForEach(availableInputLanguages) { language in
                    Text(language.label).tag(language)
                }
            }
            .accessibilityIdentifier("createBookInputLanguagePicker")

            Picker("Target", selection: languageBinding(for: .targetLanguage, value: $targetLanguage)) {
                ForEach(availableTargetLanguages) { language in
                    Text(language.label).tag(language)
                }
            }
            .accessibilityIdentifier("createBookTargetLanguagePicker")

            if creationMode != .subtitleJob {
                Picker("Voice", selection: voiceBinding) {
                    ForEach(availableVoices) { option in
                        Text(option.label).tag(option)
                    }
                }
                .accessibilityIdentifier("createBookVoicePicker")
            }
        }
    }

    private var outputSection: some View {
        Section("Output") {
            if creationMode == .subtitleJob {
                Picker("Format", selection: subtitleOutputFormatBinding) {
                    ForEach(AppleSubtitleOutputFormat.allCases) { option in
                        Text(option.label).tag(option)
                    }
                }
                .accessibilityIdentifier("createSubtitleOutputFormatPicker")

                #if os(iOS)
                if subtitleOutputFormat == .ass {
                    Stepper(value: subtitleAssFontSizeBinding, in: AppleSubtitleAssTypography.fontSizeRange, step: 2) {
                        LabeledContent("ASS font size", value: "\(clampedAssFontSize)")
                    }
                    .accessibilityIdentifier("createSubtitleAssFontSizeStepper")

                    Stepper(value: subtitleAssEmphasisScaleBinding, in: AppleSubtitleAssTypography.emphasisScaleRange, step: 0.05) {
                        LabeledContent("ASS emphasis", value: formattedAssEmphasisScale)
                    }
                    .accessibilityIdentifier("createSubtitleAssEmphasisStepper")
                }
                #endif

                TextField("Start time", text: textBinding(for: .subtitleStartTime, value: $subtitleStartTime))
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                    .accessibilityIdentifier("createSubtitleStartTimeField")
                TextField("End time", text: textBinding(for: .subtitleEndTime, value: $subtitleEndTime))
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                    .accessibilityIdentifier("createSubtitleEndTimeField")

                Toggle("Transliteration", isOn: boolBinding(for: .subtitleEnableTransliteration, value: $subtitleEnableTransliteration))
                    .accessibilityIdentifier("createSubtitleTransliterationToggle")
                if subtitleEnableTransliteration {
                    Picker("Transliteration Mode", selection: subtitleTransliterationModeBinding) {
                        ForEach(AppleSubtitleTransliterationMode.allCases) { option in
                            Text(option.label).tag(option)
                        }
                    }
                    .accessibilityIdentifier("createSubtitleTransliterationModePicker")

                    Picker(
                        "Transliteration Model",
                        selection: textBinding(for: .subtitleTransliterationModel, value: $subtitleTransliterationModel)
                    ) {
                        ForEach(availableSubtitleTransliterationModels, id: \.self) { option in
                            Text(AppleBookCreatePresentation.subtitleTransliterationModelLabel(option)).tag(option)
                        }
                    }
                    .disabled(!subtitleTransliterationMode.allowsModelOverride)
                    .accessibilityIdentifier("createSubtitleTransliterationModelPicker")
                }
                Toggle("Highlight", isOn: boolBinding(for: .subtitleHighlight, value: $subtitleHighlight))
                    .accessibilityIdentifier("createSubtitleHighlightToggle")
                Toggle("Show Original", isOn: boolBinding(for: .subtitleShowOriginal, value: $subtitleShowOriginal))
                    .accessibilityIdentifier("createSubtitleShowOriginalToggle")
                Toggle("Generate Audiobook", isOn: boolBinding(for: .subtitleGenerateAudioBook, value: $subtitleGenerateAudioBook))
                    .accessibilityIdentifier("createSubtitleGenerateAudioToggle")
                #if os(iOS)
                Toggle("Mirror batches to source", isOn: boolBinding(for: .subtitleMirrorBatchesToSourceDir, value: $subtitleMirrorBatchesToSourceDir))
                    .accessibilityIdentifier("createSubtitleMirrorBatchesToggle")
                #endif

                Picker("Provider", selection: subtitleTranslationProviderBinding) {
                    ForEach(AppleSubtitleTranslationProvider.allCases) { option in
                        Text(option.label).tag(option)
                    }
                }
                .accessibilityIdentifier("createSubtitleTranslationProviderPicker")

                #if os(iOS)
                Stepper(
                    value: subtitleWorkerCountBinding,
                    in: AppleSubtitleTuning.workerCountRange,
                    step: 1
                ) {
                    LabeledContent("Worker threads", value: "\(clampedSubtitleWorkerCount)")
                }
                .accessibilityIdentifier("createSubtitleWorkerCountStepper")

                Stepper(
                    value: subtitleBatchSizeBinding,
                    in: AppleSubtitleTuning.batchSizeRange,
                    step: 5
                ) {
                    LabeledContent("Subtitle batch size", value: "\(clampedSubtitleBatchSize)")
                }
                .accessibilityIdentifier("createSubtitleBatchSizeStepper")
                #endif

                if subtitleTranslationProvider == .llm {
                    Picker("Model", selection: textBinding(for: .subtitleLlmModel, value: $subtitleLlmModel)) {
                        ForEach(availableSubtitleLlmModels, id: \.self) { option in
                            Text(AppleBookCreatePresentation.subtitleModelLabel(option)).tag(option)
                        }
                    }
                    .accessibilityIdentifier("createSubtitleLlmModelPicker")

                    #if os(iOS)
                    Stepper(
                        value: subtitleTranslationBatchSizeBinding,
                        in: AppleSubtitleTuning.translationBatchSizeRange,
                        step: 1
                    ) {
                        LabeledContent("LLM batch size", value: "\(clampedSubtitleTranslationBatchSize)")
                    }
                        .accessibilityIdentifier("createSubtitleTranslationBatchSizeStepper")
                    #endif
                }
            } else if creationMode == .youtubeDub {
                Picker("Provider", selection: subtitleTranslationProviderBinding) {
                    ForEach(AppleSubtitleTranslationProvider.allCases) { option in
                        Text(option.label).tag(option)
                    }
                }
                .accessibilityIdentifier("createYoutubeTranslationProviderPicker")

                if subtitleTranslationProvider == .llm {
                    Picker("Model", selection: textBinding(for: .subtitleLlmModel, value: $subtitleLlmModel)) {
                        ForEach(availableSubtitleLlmModels, id: \.self) { option in
                            Text(AppleBookCreatePresentation.subtitleModelLabel(option)).tag(option)
                        }
                    }
                    .accessibilityIdentifier("createYoutubeLlmModelPicker")
                }

                Picker("Target resolution", selection: youtubeTargetHeightBinding) {
                    ForEach(AppleYoutubeDubTargetHeight.allCases) { option in
                        Text(option.label).tag(option)
                    }
                }
                .accessibilityIdentifier("createYoutubeTargetHeightPicker")

                TextField("Start offset", text: textBinding(for: .youtubeStartOffset, value: $youtubeStartOffset))
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                    .accessibilityIdentifier("createYoutubeStartOffsetField")
                TextField("End offset", text: textBinding(for: .youtubeEndOffset, value: $youtubeEndOffset))
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                    .accessibilityIdentifier("createYoutubeEndOffsetField")

                #if os(iOS)
                Stepper(value: youtubeOriginalMixPercentBinding, in: 0...100, step: 5) {
                    LabeledContent("Original audio mix", value: formattedYoutubeOriginalMixPercent)
                }
                .accessibilityIdentifier("createYoutubeOriginalMixStepper")

                Stepper(value: youtubeFlushSentencesBinding, in: 1...200, step: 1) {
                    LabeledContent("Flush interval", value: "\(clampedYoutubeFlushSentences)")
                }
                .accessibilityIdentifier("createYoutubeFlushSentencesStepper")

                Stepper(
                    value: subtitleTranslationBatchSizeBinding,
                    in: AppleSubtitleTuning.translationBatchSizeRange,
                    step: 1
                ) {
                    LabeledContent("LLM batch size", value: "\(clampedSubtitleTranslationBatchSize)")
                }
                .accessibilityIdentifier("createYoutubeTranslationBatchSizeStepper")
                #endif

                Toggle("Split batches", isOn: boolBinding(for: .youtubeSplitBatches, value: $youtubeSplitBatches))
                    .accessibilityIdentifier("createYoutubeSplitBatchesToggle")
                Toggle("Stitch batches", isOn: boolBinding(for: .youtubeStitchBatches, value: $youtubeStitchBatches))
                    .disabled(!youtubeSplitBatches)
                    .accessibilityIdentifier("createYoutubeStitchBatchesToggle")
                Toggle("Keep aspect ratio", isOn: boolBinding(for: .youtubePreserveAspectRatio, value: $youtubePreserveAspectRatio))
                    .accessibilityIdentifier("createYoutubePreserveAspectRatioToggle")
                Toggle("Transliteration track", isOn: boolBinding(for: .includeTransliteration, value: $includeTransliteration))
                    .accessibilityIdentifier("createYoutubeTransliterationToggle")
                Toggle("Lookup Cache", isOn: boolBinding(for: .enableLookupCache, value: $enableLookupCache))
                    .accessibilityIdentifier("createYoutubeLookupCacheToggle")
            } else {
                LabeledContent("Path", value: derivedBaseOutput)
                    .accessibilityIdentifier("createBookBaseOutputLabel")
                Toggle("Transliteration", isOn: boolBinding(for: .includeTransliteration, value: $includeTransliteration))
                    .accessibilityIdentifier("createBookTransliterationToggle")
                Toggle("Lookup Cache", isOn: boolBinding(for: .enableLookupCache, value: $enableLookupCache))
                    .accessibilityIdentifier("createBookLookupCacheToggle")
            }
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
            .disabled(!canSubmit || viewModel.isSubmitting)
            .accessibilityIdentifier("createBookSubmitButton")
        }
    }

    private var canSubmit: Bool {
        guard appState.configuration != nil else { return false }
        switch creationMode {
        case .generatedBook:
            return !trimmed(topic).isEmpty
                && !trimmed(bookName).isEmpty
                && !trimmed(genre).isEmpty
        case .narrateEbook:
            return (selectedNarrateFileURL != nil || !trimmed(sourcePath).isEmpty)
                && !trimmed(sourceBaseOutput).isEmpty
        case .subtitleJob:
            return selectedSubtitleFileURL != nil || !trimmed(subtitleSourcePath).isEmpty
        case .youtubeDub:
            return !trimmed(youtubeVideoPath).isEmpty
                && !trimmed(youtubeSubtitlePath).isEmpty
        }
    }

    private var availableCreateModes: [AppleCreateMode] {
        AppleBookCreatePresentation.availableCreateModes(isTV: Self.isTVPlatform)
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
            sentenceCount: sentenceCount,
            inputLanguage: inputLanguage,
            targetLanguage: targetLanguage,
            voice: voice,
            baseOutput: derivedBaseOutput,
            includeTransliteration: includeTransliteration,
            enableLookupCache: enableLookupCache,
            pipelineDefaults: viewModel.creationOptions?.pipelineDefaults,
            generatedSourceDefaults: viewModel.creationOptions?.generatedSourceDefaults
        )

        Task {
            if let jobId = await viewModel.submitGeneratedBook(draft, using: appState) {
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
            targetLanguage: targetLanguage,
            voice: voice,
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
                onJobSubmitted(jobId)
            }
        }
    }

    private func submitNarrateEbook() {
        let draft = AppleBookCreatePresentation.narrateEbookDraft(
            inputFile: sourcePath,
            baseOutput: sourceBaseOutput,
            inputLanguage: inputLanguage,
            targetLanguage: targetLanguage,
            voice: voice,
            includeTransliteration: includeTransliteration,
            enableLookupCache: enableLookupCache,
            pipelineDefaults: viewModel.creationOptions?.pipelineDefaults
        )

        Task {
            if let jobId = await viewModel.submitNarrateEbook(
                draft,
                localFileURL: selectedNarrateFileURL,
                localFilename: selectedNarrateFileName,
                using: appState
            ) {
                onJobSubmitted(jobId)
            }
        }
    }

    private func trimmed(_ value: String) -> String {
        value.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    #if os(iOS)
    private func handleNarrateEbookImport(_ result: Result<[URL], Error>) {
        switch result {
        case let .success(urls):
            guard let url = urls.first else { return }
            selectedNarrateFileURL = url
            selectedNarrateFileName = url.lastPathComponent
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
            UTType(filenameExtension: "ass") ?? UTType(importedAs: "org.aegisub.ass"),
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
        let supported = viewModel.creationOptions?.supportedInputLanguages ?? []
        let mapped = supported.compactMap(AppleBookCreateLanguage.init(backendValue:))
        return mapped.isEmpty ? AppleBookCreateLanguage.allCases : mapped
    }

    private var availableTargetLanguages: [AppleBookCreateLanguage] {
        let supported = viewModel.creationOptions?.supportedOutputLanguages ?? []
        let mapped = supported.compactMap(AppleBookCreateLanguage.init(backendValue:))
        return mapped.isEmpty ? AppleBookCreateLanguage.allCases : mapped
    }

    private var availableVoices: [AppleBookCreateVoiceOption] {
        AppleBookCreateVoiceOption.options(
            from: viewModel.creationOptions?.supportedVoices ?? [],
            selected: voice
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

    private var formattedAssEmphasisScale: String {
        AppleBookCreatePresentation.formattedAssEmphasisScale(subtitleAssEmphasisScale)
    }

    private var formattedYoutubeOriginalMixPercent: String {
        AppleBookCreatePresentation.formattedYoutubeOriginalMixPercent(youtubeOriginalMixPercent)
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
    }

    private func applyCreationOptions(_ options: BookCreationOptionsResponse) {
        if !editedFields.contains(.topic), let value = options.defaults.topic.nonEmptyValue {
            topic = value
        }
        if !editedFields.contains(.bookName), let value = options.defaults.bookName.nonEmptyValue {
            bookName = value
        }
        if !editedFields.contains(.genre), let value = options.defaults.genre.nonEmptyValue {
            genre = value
        }
        if !editedFields.contains(.author) {
            author = options.defaults.author.nonEmptyValue ?? "Me"
        }
        if !editedFields.contains(.sentenceCount) {
            sentenceCount = clampSentenceCount(options.sentenceBounds.default)
        } else {
            sentenceCount = clampSentenceCount(sentenceCount)
        }
        if !editedFields.contains(.inputLanguage),
           let language = AppleBookCreateLanguage(backendValue: options.defaults.inputLanguage) {
            inputLanguage = language
        }
        if !editedFields.contains(.targetLanguage),
           let language = AppleBookCreateLanguage(backendValue: options.defaults.outputLanguage) {
            targetLanguage = language
        }
        if !editedFields.contains(.voice),
           let option = AppleBookCreateVoiceOption(backendValue: options.defaults.voice) {
            voice = option
        }
        if !editedFields.contains(.includeTransliteration) {
            includeTransliteration = options.pipelineDefaults.includeTransliteration
        }
        if !editedFields.contains(.enableLookupCache) {
            enableLookupCache = options.pipelineDefaults.enableLookupCache
        }
        if !editedFields.contains(.subtitleTranslationProvider),
           let provider = AppleSubtitleTranslationProvider(backendValue: options.pipelineDefaults.translationProvider) {
            subtitleTranslationProvider = provider
        }
    }

    private func clampSentenceCount(_ value: Int) -> Int {
        max(sentenceBounds.min, min(sentenceBounds.max, value))
    }
}

private enum AppleBookCreateEditedField: Hashable {
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
}
