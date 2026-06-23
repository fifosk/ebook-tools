import SwiftUI

struct AppleBookCreateSourceSection: View {
    @Binding var creationMode: AppleCreateMode
    let availableCreateModes: [AppleCreateMode]
    @Binding var sourcePath: String
    @Binding var sourceBaseOutput: String
    @Binding var subtitleSourcePath: String
    @Binding var youtubeVideoPath: String
    @Binding var youtubeSubtitlePath: String
    let selectedNarrateFileName: String?
    let selectedSubtitleFileName: String?
    let onChooseNarrateFile: () -> Void
    let onChooseSubtitleFile: () -> Void

    var body: some View {
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

            switch creationMode {
            case .generatedBook:
                EmptyView()
            case .narrateEbook:
                narrateEbookSourceControls
            case .subtitleJob:
                subtitleSourceControls
            case .youtubeDub:
                youtubeSourceControls
            }
        }
    }

    @ViewBuilder
    private var narrateEbookSourceControls: some View {
        #if os(iOS)
        fileImportControl(
            title: selectedNarrateFileName ?? "Choose EPUB",
            selectedFileName: selectedNarrateFileName,
            systemImage: "doc.badge.plus",
            buttonIdentifier: "createNarrateFileImportButton",
            labelIdentifier: "createNarrateSelectedFileLabel",
            action: onChooseNarrateFile
        )
        #endif
        TextField("Server EPUB path", text: $sourcePath)
            .textInputAutocapitalization(.never)
            .autocorrectionDisabled()
            .accessibilityIdentifier("createNarrateSourcePathField")
        TextField("Output path", text: $sourceBaseOutput)
            .textInputAutocapitalization(.never)
            .autocorrectionDisabled()
            .accessibilityIdentifier("createNarrateOutputPathField")
    }

    @ViewBuilder
    private var subtitleSourceControls: some View {
        #if os(iOS)
        fileImportControl(
            title: selectedSubtitleFileName ?? "Choose subtitle file",
            selectedFileName: selectedSubtitleFileName,
            systemImage: "captions.bubble",
            buttonIdentifier: "createSubtitleFileImportButton",
            labelIdentifier: "createSubtitleSelectedFileLabel",
            action: onChooseSubtitleFile
        )
        #endif
        TextField("Server subtitle path", text: $subtitleSourcePath)
            .textInputAutocapitalization(.never)
            .autocorrectionDisabled()
            .accessibilityIdentifier("createSubtitleSourcePathField")
    }

    private var youtubeSourceControls: some View {
        Group {
            TextField("Video path", text: $youtubeVideoPath)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
                .accessibilityIdentifier("createYoutubeVideoPathField")
            TextField("Subtitle path", text: $youtubeSubtitlePath)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
                .accessibilityIdentifier("createYoutubeSubtitlePathField")
        }
    }

    #if os(iOS)
    private func fileImportControl(
        title: String,
        selectedFileName: String?,
        systemImage: String,
        buttonIdentifier: String,
        labelIdentifier: String,
        action: @escaping () -> Void
    ) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Button(action: action) {
                Label(title, systemImage: systemImage)
            }
            .accessibilityIdentifier(buttonIdentifier)

            if let selectedFileName {
                Label(selectedFileName, systemImage: "checkmark.circle")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
                    .lineLimit(2)
                    .accessibilityIdentifier(labelIdentifier)
            }
        }
    }
    #endif
}

struct AppleBookCreateNarrationSection: View {
    let creationMode: AppleCreateMode
    @Binding var inputLanguage: AppleBookCreateLanguage
    @Binding var targetLanguage: AppleBookCreateLanguage
    @Binding var voice: AppleBookCreateVoiceOption
    let availableInputLanguages: [AppleBookCreateLanguage]
    let availableTargetLanguages: [AppleBookCreateLanguage]
    let availableVoices: [AppleBookCreateVoiceOption]

    var body: some View {
        Section(creationMode == .subtitleJob ? "Languages" : "Narration") {
            Picker("Input", selection: $inputLanguage) {
                ForEach(availableInputLanguages) { language in
                    Text(language.label).tag(language)
                }
            }
            .accessibilityIdentifier("createBookInputLanguagePicker")

            Picker("Target", selection: $targetLanguage) {
                ForEach(availableTargetLanguages) { language in
                    Text(language.label).tag(language)
                }
            }
            .accessibilityIdentifier("createBookTargetLanguagePicker")

            if creationMode != .subtitleJob {
                Picker("Voice", selection: $voice) {
                    ForEach(availableVoices) { option in
                        Text(option.label).tag(option)
                    }
                }
                .accessibilityIdentifier("createBookVoicePicker")
            }
        }
    }
}

struct AppleBookCreateSubtitleOutputControls: View {
    @Binding var outputFormat: AppleSubtitleOutputFormat
    let selectedOutputFormat: AppleSubtitleOutputFormat
    @Binding var assFontSize: Int
    let clampedAssFontSize: Int
    @Binding var assEmphasisScale: Double
    let formattedAssEmphasisScale: String
    @Binding var startTime: String
    @Binding var endTime: String
    @Binding var enableTransliteration: Bool
    let isTransliterationEnabled: Bool
    @Binding var transliterationMode: AppleSubtitleTransliterationMode
    let selectedTransliterationMode: AppleSubtitleTransliterationMode
    @Binding var transliterationModel: String
    let availableTransliterationModels: [String]
    @Binding var highlight: Bool
    @Binding var showOriginal: Bool
    @Binding var generateAudioBook: Bool
    @Binding var mirrorBatchesToSourceDir: Bool
    @Binding var translationProvider: AppleSubtitleTranslationProvider
    let selectedTranslationProvider: AppleSubtitleTranslationProvider
    @Binding var workerCount: Int
    let clampedWorkerCount: Int
    @Binding var batchSize: Int
    let clampedBatchSize: Int
    @Binding var llmModel: String
    let availableLlmModels: [String]
    @Binding var translationBatchSize: Int
    let clampedTranslationBatchSize: Int

    var body: some View {
        Picker("Format", selection: $outputFormat) {
            ForEach(AppleSubtitleOutputFormat.allCases) { option in
                Text(option.label).tag(option)
            }
        }
        .accessibilityIdentifier("createSubtitleOutputFormatPicker")

        #if os(iOS)
        if selectedOutputFormat == .ass {
            Stepper(value: $assFontSize, in: AppleSubtitleAssTypography.fontSizeRange, step: 2) {
                LabeledContent("ASS font size", value: "\(clampedAssFontSize)")
            }
            .accessibilityIdentifier("createSubtitleAssFontSizeStepper")

            Stepper(value: $assEmphasisScale, in: AppleSubtitleAssTypography.emphasisScaleRange, step: 0.05) {
                LabeledContent("ASS emphasis", value: formattedAssEmphasisScale)
            }
            .accessibilityIdentifier("createSubtitleAssEmphasisStepper")
        }
        #endif

        TextField("Start time", text: $startTime)
            .textInputAutocapitalization(.never)
            .autocorrectionDisabled()
            .accessibilityIdentifier("createSubtitleStartTimeField")
        TextField("End time", text: $endTime)
            .textInputAutocapitalization(.never)
            .autocorrectionDisabled()
            .accessibilityIdentifier("createSubtitleEndTimeField")

        Toggle("Transliteration", isOn: $enableTransliteration)
            .accessibilityIdentifier("createSubtitleTransliterationToggle")
        if isTransliterationEnabled {
            Picker("Transliteration Mode", selection: $transliterationMode) {
                ForEach(AppleSubtitleTransliterationMode.allCases) { option in
                    Text(option.label).tag(option)
                }
            }
            .accessibilityIdentifier("createSubtitleTransliterationModePicker")

            Picker("Transliteration Model", selection: $transliterationModel) {
                ForEach(availableTransliterationModels, id: \.self) { option in
                    Text(AppleBookCreatePresentation.subtitleTransliterationModelLabel(option)).tag(option)
                }
            }
            .disabled(!selectedTransliterationMode.allowsModelOverride)
            .accessibilityIdentifier("createSubtitleTransliterationModelPicker")
        }
        Toggle("Highlight", isOn: $highlight)
            .accessibilityIdentifier("createSubtitleHighlightToggle")
        Toggle("Show Original", isOn: $showOriginal)
            .accessibilityIdentifier("createSubtitleShowOriginalToggle")
        Toggle("Generate Audiobook", isOn: $generateAudioBook)
            .accessibilityIdentifier("createSubtitleGenerateAudioToggle")
        #if os(iOS)
        Toggle("Mirror batches to source", isOn: $mirrorBatchesToSourceDir)
            .accessibilityIdentifier("createSubtitleMirrorBatchesToggle")
        #endif

        Picker("Provider", selection: $translationProvider) {
            ForEach(AppleSubtitleTranslationProvider.allCases) { option in
                Text(option.label).tag(option)
            }
        }
        .accessibilityIdentifier("createSubtitleTranslationProviderPicker")

        #if os(iOS)
        Stepper(
            value: $workerCount,
            in: AppleSubtitleTuning.workerCountRange,
            step: 1
        ) {
            LabeledContent("Worker threads", value: "\(clampedWorkerCount)")
        }
        .accessibilityIdentifier("createSubtitleWorkerCountStepper")

        Stepper(
            value: $batchSize,
            in: AppleSubtitleTuning.batchSizeRange,
            step: 5
        ) {
            LabeledContent("Subtitle batch size", value: "\(clampedBatchSize)")
        }
        .accessibilityIdentifier("createSubtitleBatchSizeStepper")
        #endif

        if selectedTranslationProvider == .llm {
            Picker("Model", selection: $llmModel) {
                ForEach(availableLlmModels, id: \.self) { option in
                    Text(AppleBookCreatePresentation.subtitleModelLabel(option)).tag(option)
                }
            }
            .accessibilityIdentifier("createSubtitleLlmModelPicker")

            #if os(iOS)
            Stepper(
                value: $translationBatchSize,
                in: AppleSubtitleTuning.translationBatchSizeRange,
                step: 1
            ) {
                LabeledContent("LLM batch size", value: "\(clampedTranslationBatchSize)")
            }
            .accessibilityIdentifier("createSubtitleTranslationBatchSizeStepper")
            #endif
        }
    }
}

struct AppleBookCreateYoutubeOutputControls: View {
    @Binding var translationProvider: AppleSubtitleTranslationProvider
    let selectedTranslationProvider: AppleSubtitleTranslationProvider
    @Binding var llmModel: String
    let availableSubtitleLlmModels: [String]
    @Binding var targetHeight: AppleYoutubeDubTargetHeight
    @Binding var startOffset: String
    @Binding var endOffset: String
    @Binding var originalMixPercent: Double
    let formattedOriginalMixPercent: String
    @Binding var flushSentences: Int
    let clampedFlushSentences: Int
    @Binding var translationBatchSize: Int
    let clampedTranslationBatchSize: Int
    @Binding var splitBatches: Bool
    let isSplitBatchesEnabled: Bool
    @Binding var stitchBatches: Bool
    @Binding var preserveAspectRatio: Bool
    @Binding var includeTransliteration: Bool
    @Binding var enableLookupCache: Bool

    var body: some View {
        Picker("Provider", selection: $translationProvider) {
            ForEach(AppleSubtitleTranslationProvider.allCases) { option in
                Text(option.label).tag(option)
            }
        }
        .accessibilityIdentifier("createYoutubeTranslationProviderPicker")

        if selectedTranslationProvider == .llm {
            Picker("Model", selection: $llmModel) {
                ForEach(availableSubtitleLlmModels, id: \.self) { option in
                    Text(AppleBookCreatePresentation.subtitleModelLabel(option)).tag(option)
                }
            }
            .accessibilityIdentifier("createYoutubeLlmModelPicker")
        }

        Picker("Target resolution", selection: $targetHeight) {
            ForEach(AppleYoutubeDubTargetHeight.allCases) { option in
                Text(option.label).tag(option)
            }
        }
        .accessibilityIdentifier("createYoutubeTargetHeightPicker")

        TextField("Start offset", text: $startOffset)
            .textInputAutocapitalization(.never)
            .autocorrectionDisabled()
            .accessibilityIdentifier("createYoutubeStartOffsetField")
        TextField("End offset", text: $endOffset)
            .textInputAutocapitalization(.never)
            .autocorrectionDisabled()
            .accessibilityIdentifier("createYoutubeEndOffsetField")

        #if os(iOS)
        Stepper(value: $originalMixPercent, in: 0...100, step: 5) {
            LabeledContent("Original audio mix", value: formattedOriginalMixPercent)
        }
        .accessibilityIdentifier("createYoutubeOriginalMixStepper")

        Stepper(value: $flushSentences, in: 1...200, step: 1) {
            LabeledContent("Flush interval", value: "\(clampedFlushSentences)")
        }
        .accessibilityIdentifier("createYoutubeFlushSentencesStepper")

        Stepper(
            value: $translationBatchSize,
            in: AppleSubtitleTuning.translationBatchSizeRange,
            step: 1
        ) {
            LabeledContent("LLM batch size", value: "\(clampedTranslationBatchSize)")
        }
        .accessibilityIdentifier("createYoutubeTranslationBatchSizeStepper")
        #endif

        Toggle("Split batches", isOn: $splitBatches)
            .accessibilityIdentifier("createYoutubeSplitBatchesToggle")
        Toggle("Stitch batches", isOn: $stitchBatches)
            .disabled(!isSplitBatchesEnabled)
            .accessibilityIdentifier("createYoutubeStitchBatchesToggle")
        Toggle("Keep aspect ratio", isOn: $preserveAspectRatio)
            .accessibilityIdentifier("createYoutubePreserveAspectRatioToggle")
        Toggle("Transliteration track", isOn: $includeTransliteration)
            .accessibilityIdentifier("createYoutubeTransliterationToggle")
        Toggle("Lookup Cache", isOn: $enableLookupCache)
            .accessibilityIdentifier("createYoutubeLookupCacheToggle")
    }
}

struct AppleBookCreateGeneratedOutputControls: View {
    let derivedBaseOutput: String
    @Binding var includeTransliteration: Bool
    @Binding var enableLookupCache: Bool
    @Binding var includeImages: Bool
    @Binding var imageStyleTemplate: AppleGeneratedBookImageStyleTemplate
    let supportsImages: Bool

    var body: some View {
        LabeledContent("Path", value: derivedBaseOutput)
            .accessibilityIdentifier("createBookBaseOutputLabel")
        if supportsImages {
            Toggle("Illustrations", isOn: $includeImages)
                .accessibilityIdentifier("createBookIllustrationsToggle")
            if includeImages {
                Picker("Style", selection: $imageStyleTemplate) {
                    ForEach(AppleGeneratedBookImageStyleTemplate.allCases) { style in
                        Text(style.label).tag(style)
                    }
                }
                .accessibilityIdentifier("createBookImageStylePicker")
            }
        }
        Toggle("Transliteration", isOn: $includeTransliteration)
            .accessibilityIdentifier("createBookTransliterationToggle")
        Toggle("Lookup Cache", isOn: $enableLookupCache)
            .accessibilityIdentifier("createBookLookupCacheToggle")
    }
}
