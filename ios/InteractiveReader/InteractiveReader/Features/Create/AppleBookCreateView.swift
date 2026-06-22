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
    @State private var subtitleOutputFormat = AppleSubtitleOutputFormat.ass
    @State private var subtitleStartTime = "00:00"
    @State private var subtitleEndTime = ""
    @State private var subtitleEnableTransliteration = true
    @State private var subtitleHighlight = true
    @State private var subtitleShowOriginal = true
    @State private var subtitleGenerateAudioBook = true
    @State private var subtitleTranslationProvider = AppleSubtitleTranslationProvider.llm
    @State private var subtitleLlmModel = ""
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
                Toggle("Highlight", isOn: boolBinding(for: .subtitleHighlight, value: $subtitleHighlight))
                    .accessibilityIdentifier("createSubtitleHighlightToggle")
                Toggle("Show Original", isOn: boolBinding(for: .subtitleShowOriginal, value: $subtitleShowOriginal))
                    .accessibilityIdentifier("createSubtitleShowOriginalToggle")
                Toggle("Generate Audiobook", isOn: boolBinding(for: .subtitleGenerateAudioBook, value: $subtitleGenerateAudioBook))
                    .accessibilityIdentifier("createSubtitleGenerateAudioToggle")

                Picker("Provider", selection: subtitleTranslationProviderBinding) {
                    ForEach(AppleSubtitleTranslationProvider.allCases) { option in
                        Text(option.label).tag(option)
                    }
                }
                .accessibilityIdentifier("createSubtitleTranslationProviderPicker")

                if subtitleTranslationProvider == .llm {
                    Picker("Model", selection: textBinding(for: .subtitleLlmModel, value: $subtitleLlmModel)) {
                        ForEach(availableSubtitleLlmModels, id: \.self) { option in
                            Text(subtitleModelLabel(option)).tag(option)
                        }
                    }
                    .accessibilityIdentifier("createSubtitleLlmModelPicker")
                }
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
                if viewModel.isSubmitting {
                    Label("Submitting", systemImage: "hourglass")
                } else if creationMode == .narrateEbook {
                    Label("Narrate EPUB", systemImage: "book")
                } else if creationMode == .subtitleJob {
                    Label("Create Subtitles", systemImage: "captions.bubble")
                } else {
                    Label("Generate Audiobook", systemImage: "sparkles")
                }
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
        }
    }

    private var availableCreateModes: [AppleCreateMode] {
        #if os(tvOS)
        return [.generatedBook]
        #else
        return AppleCreateMode.allCases
        #endif
    }

    private var derivedBaseOutput: String {
        switch creationMode {
        case .generatedBook:
            return Self.deriveBaseOutputName(bookName.isEmpty ? topic : bookName)
        case .narrateEbook:
            return trimmed(sourceBaseOutput)
        case .subtitleJob:
            return Self.deriveBaseOutputName(subtitleSourcePath)
        }
    }

    private func submit() {
        switch creationMode {
        case .generatedBook:
            submitGeneratedBook()
        case .narrateEbook:
            submitNarrateEbook()
        case .subtitleJob:
            submitSubtitleJob()
        }
    }

    private func submitGeneratedBook() {
        let draft = AppleBookCreateDraft(
            topic: trimmed(topic),
            bookName: trimmed(bookName),
            genre: trimmed(genre),
            author: trimmed(author).nonEmptyValue ?? "Me",
            sentenceCount: sentenceCount,
            inputLanguage: inputLanguage.backendValue,
            targetLanguage: targetLanguage.backendValue,
            voice: voice.backendValue,
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
        guard let normalizedStartTime = SubtitleTimecodeInput.normalize(
            subtitleStartTime,
            emptyValue: "00:00"
        ) else {
            viewModel.errorMessage = "Enter a valid start time in MM:SS or HH:MM:SS format."
            return
        }
        guard let normalizedEndTime = SubtitleTimecodeInput.normalize(
            subtitleEndTime,
            allowRelative: true
        ) else {
            viewModel.errorMessage = "Enter a valid end time in MM:SS, HH:MM:SS, or +offset format."
            return
        }
        subtitleStartTime = normalizedStartTime
        subtitleEndTime = normalizedEndTime

        let draft = AppleSubtitleJobDraft(
            sourcePath: trimmed(subtitleSourcePath).nonEmptyValue,
            inputLanguage: inputLanguage.backendValue,
            targetLanguage: targetLanguage.backendValue,
            outputFormat: subtitleOutputFormat.rawValue,
            startTime: normalizedStartTime,
            endTime: normalizedEndTime.nonEmptyValue,
            enableTransliteration: subtitleEnableTransliteration,
            highlight: subtitleHighlight,
            showOriginal: subtitleShowOriginal,
            generateAudioBook: subtitleGenerateAudioBook,
            translationProvider: subtitleTranslationProvider.backendValue,
            llmModel: subtitleTranslationProvider == .llm ? trimmed(subtitleLlmModel).nonEmptyValue : nil,
            assFontSize: subtitleOutputFormat == .ass ? clampedAssFontSize : nil,
            assEmphasisScale: subtitleOutputFormat == .ass ? clampedAssEmphasisScale : nil
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

    private func submitNarrateEbook() {
        let draft = AppleNarrateEbookDraft(
            inputFile: trimmed(sourcePath),
            baseOutput: trimmed(sourceBaseOutput),
            inputLanguage: inputLanguage.backendValue,
            targetLanguage: targetLanguage.backendValue,
            voice: voice.backendValue,
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
                sourceBaseOutput = Self.deriveBaseOutputName(url.deletingPathExtension().lastPathComponent)
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
        let selected = trimmed(subtitleLlmModel)
        var seen = Set<String>()
        var options: [String] = []

        if !selected.isEmpty {
            seen.insert(selected.lowercased())
            options.append(selected)
        }

        for model in viewModel.subtitleLlmModels {
            let trimmedModel = trimmed(model)
            guard !trimmedModel.isEmpty else { continue }
            if seen.insert(trimmedModel.lowercased()).inserted {
                options.append(trimmedModel)
            }
        }

        if options.isEmpty {
            options.append("")
        }
        return options
    }

    private var formattedAssEmphasisScale: String {
        clampedAssEmphasisScale.formatted(.number.precision(.fractionLength(2)))
    }

    private var clampedAssFontSize: Int {
        min(
            AppleSubtitleAssTypography.fontSizeRange.upperBound,
            max(AppleSubtitleAssTypography.fontSizeRange.lowerBound, subtitleAssFontSize)
        )
    }

    private var clampedAssEmphasisScale: Double {
        min(
            AppleSubtitleAssTypography.emphasisScaleRange.upperBound,
            max(AppleSubtitleAssTypography.emphasisScaleRange.lowerBound, subtitleAssEmphasisScale)
        )
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

    private func subtitleModelLabel(_ model: String) -> String {
        let trimmedModel = trimmed(model)
        return trimmedModel.isEmpty ? "Backend default" : trimmedModel
    }

    private func clampSentenceCount(_ value: Int) -> Int {
        max(sentenceBounds.min, min(sentenceBounds.max, value))
    }

    private static func deriveBaseOutputName(_ value: String) -> String {
        let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
        let scalars = trimmed.unicodeScalars.map { scalar -> Character in
            CharacterSet.alphanumerics.contains(scalar) ? Character(scalar) : "-"
        }
        let collapsed = String(scalars)
            .split(separator: "-", omittingEmptySubsequences: true)
            .joined(separator: "-")
            .lowercased()
        return collapsed.nonEmptyValue ?? "generated-book"
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
    case subtitleOutputFormat
    case subtitleStartTime
    case subtitleEndTime
    case subtitleEnableTransliteration
    case subtitleHighlight
    case subtitleShowOriginal
    case subtitleGenerateAudioBook
    case subtitleTranslationProvider
    case subtitleLlmModel
    case subtitleAssFontSize
    case subtitleAssEmphasisScale
    case sentenceCount
    case inputLanguage
    case targetLanguage
    case voice
    case includeTransliteration
    case enableLookupCache
}

private enum AppleCreateMode: String, CaseIterable, Identifiable {
    case generatedBook
    case narrateEbook
    case subtitleJob

    var id: String { rawValue }

    var label: String {
        switch self {
        case .generatedBook:
            return "Generate"
        case .narrateEbook:
            return "Narrate EPUB"
        case .subtitleJob:
            return "Subtitles"
        }
    }
}

private enum AppleSubtitleOutputFormat: String, CaseIterable, Identifiable {
    case ass
    case srt

    var id: String { rawValue }

    var label: String {
        switch self {
        case .ass:
            return "ASS"
        case .srt:
            return "SRT"
        }
    }
}

private enum AppleSubtitleTranslationProvider: String, CaseIterable, Identifiable {
    case llm
    case googleTranslate

    var id: String { rawValue }

    var backendValue: String {
        switch self {
        case .llm:
            return "llm"
        case .googleTranslate:
            return "googletrans"
        }
    }

    var label: String {
        switch self {
        case .llm:
            return "LLM"
        case .googleTranslate:
            return "Google Translate"
        }
    }

    init?(backendValue: String) {
        let normalized = backendValue.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        switch normalized {
        case "llm":
            self = .llm
        case "googletrans", "google", "google_translate", "google-translate":
            self = .googleTranslate
        default:
            return nil
        }
    }
}

private enum AppleSubtitleAssTypography {
    static let defaultFontSize = 56
    static let fontSizeRange = 12...120
    static let defaultEmphasisScale = 1.3
    static let emphasisScaleRange = 1.0...2.5
}
