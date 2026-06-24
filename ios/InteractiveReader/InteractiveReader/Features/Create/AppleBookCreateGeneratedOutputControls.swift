import SwiftUI

struct AppleBookCreateGeneratedOutputControls: View {
    let derivedBaseOutput: String
    @Binding var generateAudio: Bool
    @Binding var audioMode: String
    @Binding var audioBitrateKbps: String
    @Binding var writtenMode: String
    @Binding var tempo: Double
    let formattedTempo: String
    let estimatedAudioDurationLabel: String?
    @Binding var sentencesPerOutputFile: Int
    let clampedSentencesPerOutputFile: Int
    @Binding var stitchFull: Bool
    @Binding var includeTransliteration: Bool
    @Binding var translationProvider: AppleSubtitleTranslationProvider
    let selectedTranslationProvider: AppleSubtitleTranslationProvider
    @Binding var llmModel: String
    let availableLlmModels: [String]
    @Binding var translationBatchSize: Int
    let clampedTranslationBatchSize: Int
    @Binding var transliterationMode: AppleSubtitleTransliterationMode
    let selectedTransliterationMode: AppleSubtitleTransliterationMode
    @Binding var transliterationModel: String
    let availableTransliterationModels: [String]
    @Binding var enableLookupCache: Bool
    @Binding var lookupCacheBatchSize: Int
    let clampedLookupCacheBatchSize: Int
    @Binding var outputHtml: Bool
    @Binding var outputPdf: Bool
    @Binding var includeImages: Bool
    @Binding var imagePromptPipeline: AppleGeneratedBookImagePromptPipeline
    @Binding var imageStyleTemplate: AppleGeneratedBookImageStyleTemplate
    @Binding var imagePromptBatchingEnabled: Bool
    @Binding var imagePromptBatchSize: Int
    let clampedImagePromptBatchSize: Int
    @Binding var imagePromptPlanBatchSize: Int
    let clampedImagePromptPlanBatchSize: Int
    @Binding var imagePromptContextSentences: Int
    let clampedImagePromptContextSentences: Int
    @Binding var imageWidth: String
    @Binding var imageHeight: String
    @Binding var imageSteps: String
    @Binding var imageCfgScale: String
    @Binding var imageSamplerName: String
    @Binding var imageSeedWithPreviousImage: Bool
    @Binding var imageBlankDetectionEnabled: Bool
    @Binding var imageApiBaseURLs: String
    @Binding var imageConcurrency: String
    @Binding var imageApiTimeoutSeconds: String
    @Binding var threadCount: String
    @Binding var queueSize: String
    @Binding var jobMaxWorkers: String
    let supportsImages: Bool

    var body: some View {
        LabeledContent("Path", value: derivedBaseOutput)
            .accessibilityIdentifier("createBookBaseOutputLabel")
        Toggle("Narration tracks", isOn: $generateAudio)
            .accessibilityIdentifier("createBookGenerateAudioToggle")
        Picker("Audio mode", selection: $audioMode) {
            ForEach(["1", "2", "3", "4"], id: \.self) { option in
                Text("Mode \(option)").tag(option)
            }
        }
        .accessibilityIdentifier("createBookAudioModePicker")
        Picker("Audio quality", selection: $audioBitrateKbps) {
            Text("Backend default").tag("")
            Text("Ultra (320 kbps)").tag("320")
            Text("High (192 kbps)").tag("192")
            Text("High (160 kbps)").tag("160")
            Text("Standard (128 kbps)").tag("128")
            Text("Compact (96 kbps)").tag("96")
            Text("Tiny (64 kbps)").tag("64")
        }
        .accessibilityIdentifier("createBookAudioBitratePicker")
        Picker("Written mode", selection: $writtenMode) {
            ForEach(["1", "2", "3", "4"], id: \.self) { option in
                Text("Mode \(option)").tag(option)
            }
        }
        .accessibilityIdentifier("createBookWrittenModePicker")
        #if os(iOS)
        Stepper(value: $tempo, in: 0.5...2.0, step: 0.1) {
            LabeledContent("Tempo", value: formattedTempo)
        }
        .accessibilityIdentifier("createBookTempoStepper")
        #endif
        if let estimatedAudioDurationLabel {
            Text(estimatedAudioDurationLabel)
                .font(.footnote)
                .foregroundStyle(.secondary)
                .accessibilityIdentifier("createBookEstimatedAudioDurationLabel")
        }
        if supportsImages {
            Toggle("Illustrations", isOn: $includeImages)
                .accessibilityIdentifier("createBookIllustrationsToggle")
            if includeImages {
                Picker("Pipeline", selection: $imagePromptPipeline) {
                    ForEach(AppleGeneratedBookImagePromptPipeline.allCases) { pipeline in
                        Text(pipeline.label).tag(pipeline)
                    }
                }
                .accessibilityIdentifier("createBookImagePromptPipelinePicker")
                if imagePromptPipeline == .promptPlan {
                    Picker("Style", selection: $imageStyleTemplate) {
                        ForEach(AppleGeneratedBookImageStyleTemplate.allCases) { style in
                            Text(style.label).tag(style)
                        }
                    }
                    .accessibilityIdentifier("createBookImageStylePicker")
                    #if os(iOS)
                    Toggle("Shared images", isOn: $imagePromptBatchingEnabled)
                        .accessibilityIdentifier("createBookImagePromptBatchingToggle")
                    if imagePromptBatchingEnabled {
                        Stepper(
                            value: $imagePromptBatchSize,
                            in: 1...50,
                            step: 1
                        ) {
                            LabeledContent("Sentences per image", value: "\(clampedImagePromptBatchSize)")
                        }
                        .accessibilityIdentifier("createBookImagePromptBatchSizeStepper")
                    }
                    Stepper(
                        value: $imagePromptPlanBatchSize,
                        in: 1...50,
                        step: 1
                    ) {
                        LabeledContent("Prompt plan batch", value: "\(clampedImagePromptPlanBatchSize)")
                    }
                    .accessibilityIdentifier("createBookImagePromptPlanBatchSizeStepper")
                    Stepper(
                        value: $imagePromptContextSentences,
                        in: 0...50,
                        step: 1
                    ) {
                        LabeledContent("Prompt context", value: "\(clampedImagePromptContextSentences)")
                    }
                    .accessibilityIdentifier("createBookImagePromptContextStepper")
                    #endif
                }
                #if os(iOS)
                TextField("Width", text: $imageWidth)
                    .keyboardType(.numberPad)
                    .accessibilityIdentifier("createBookImageWidthField")
                TextField("Height", text: $imageHeight)
                    .keyboardType(.numberPad)
                    .accessibilityIdentifier("createBookImageHeightField")
                TextField("Steps", text: $imageSteps)
                    .keyboardType(.numberPad)
                    .accessibilityIdentifier("createBookImageStepsField")
                TextField("CFG scale", text: $imageCfgScale)
                    .keyboardType(.decimalPad)
                    .accessibilityIdentifier("createBookImageCfgScaleField")
                TextField("Sampler", text: $imageSamplerName)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                    .accessibilityIdentifier("createBookImageSamplerField")
                Toggle("Seed from previous image", isOn: $imageSeedWithPreviousImage)
                    .accessibilityIdentifier("createBookImageSeedPreviousToggle")
                Toggle("Blank detection", isOn: $imageBlankDetectionEnabled)
                    .accessibilityIdentifier("createBookImageBlankDetectionToggle")
                TextField("Image API URLs", text: $imageApiBaseURLs, axis: .vertical)
                    .lineLimit(1...3)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                    .accessibilityIdentifier("createBookImageApiBaseURLsField")
                TextField("Image workers", text: $imageConcurrency)
                    .keyboardType(.numberPad)
                    .accessibilityIdentifier("createBookImageConcurrencyField")
                TextField("API timeout seconds", text: $imageApiTimeoutSeconds)
                    .keyboardType(.decimalPad)
                    .accessibilityIdentifier("createBookImageTimeoutField")
                #endif
            }
        }
        Toggle("HTML output", isOn: $outputHtml)
            .accessibilityIdentifier("createBookOutputHtmlToggle")
        Toggle("PDF output", isOn: $outputPdf)
            .accessibilityIdentifier("createBookOutputPdfToggle")
        #if os(iOS)
        Stepper(
            value: $sentencesPerOutputFile,
            in: AppleBookOutputChunking.sentencesPerOutputFileRange,
            step: 1
        ) {
            LabeledContent("Sentences per file", value: "\(clampedSentencesPerOutputFile)")
        }
        .accessibilityIdentifier("createBookSentencesPerFileStepper")
        #else
        LabeledContent("Sentences per file") {
            HStack(spacing: 12) {
                Button {
                    sentencesPerOutputFile = max(
                        AppleBookOutputChunking.sentencesPerOutputFileRange.lowerBound,
                        clampedSentencesPerOutputFile - 1
                    )
                } label: {
                    Image(systemName: "minus")
                }
                .disabled(
                    clampedSentencesPerOutputFile <= AppleBookOutputChunking.sentencesPerOutputFileRange.lowerBound
                )
                .accessibilityLabel("Decrease sentences per file")

                Text("\(clampedSentencesPerOutputFile)")
                    .monospacedDigit()
                    .frame(minWidth: 48)

                Button {
                    sentencesPerOutputFile = min(
                        AppleBookOutputChunking.sentencesPerOutputFileRange.upperBound,
                        clampedSentencesPerOutputFile + 1
                    )
                } label: {
                    Image(systemName: "plus")
                }
                .disabled(
                    clampedSentencesPerOutputFile >= AppleBookOutputChunking.sentencesPerOutputFileRange.upperBound
                )
                .accessibilityLabel("Increase sentences per file")
            }
        }
        .accessibilityIdentifier("createBookSentencesPerFileControl")
        #endif
        Toggle("Stitch full book", isOn: $stitchFull)
            .accessibilityIdentifier("createBookStitchFullToggle")
        Toggle("Transliteration", isOn: $includeTransliteration)
            .accessibilityIdentifier("createBookTransliterationToggle")
        Picker("Translation provider", selection: $translationProvider) {
            ForEach(AppleSubtitleTranslationProvider.allCases) { provider in
                Text(provider.label).tag(provider)
            }
        }
        .accessibilityIdentifier("createBookTranslationProviderPicker")
        if selectedTranslationProvider == .llm {
            Picker("Translation model", selection: $llmModel) {
                ForEach(availableLlmModels, id: \.self) { model in
                    Text(AppleBookCreatePresentation.subtitleModelLabel(model)).tag(model)
                }
            }
            .accessibilityIdentifier("createBookLlmModelPicker")
        }
        #if os(iOS)
        Stepper(
            value: $translationBatchSize,
            in: AppleSubtitleTuning.translationBatchSizeRange,
            step: 1
        ) {
            LabeledContent("Translation batch", value: "\(clampedTranslationBatchSize)")
        }
        .accessibilityIdentifier("createBookTranslationBatchSizeStepper")
        #else
        LabeledContent("Translation batch") {
            HStack(spacing: 12) {
                Button {
                    translationBatchSize = max(
                        AppleSubtitleTuning.translationBatchSizeRange.lowerBound,
                        clampedTranslationBatchSize - 1
                    )
                } label: {
                    Image(systemName: "minus")
                }
                .disabled(clampedTranslationBatchSize <= AppleSubtitleTuning.translationBatchSizeRange.lowerBound)
                .accessibilityLabel("Decrease translation batch")

                Text("\(clampedTranslationBatchSize)")
                    .monospacedDigit()
                    .frame(minWidth: 48)

                Button {
                    translationBatchSize = min(
                        AppleSubtitleTuning.translationBatchSizeRange.upperBound,
                        clampedTranslationBatchSize + 1
                    )
                } label: {
                    Image(systemName: "plus")
                }
                .disabled(clampedTranslationBatchSize >= AppleSubtitleTuning.translationBatchSizeRange.upperBound)
                .accessibilityLabel("Increase translation batch")
            }
        }
        .accessibilityIdentifier("createBookTranslationBatchSizeControl")
        #endif
        if includeTransliteration {
            Picker("Transliteration mode", selection: $transliterationMode) {
                ForEach(AppleSubtitleTransliterationMode.allCases) { mode in
                    Text(mode.label).tag(mode)
                }
            }
            .accessibilityIdentifier("createBookTransliterationModePicker")
            if selectedTransliterationMode.allowsModelOverride {
                Picker("Transliteration model", selection: $transliterationModel) {
                    ForEach(availableTransliterationModels, id: \.self) { model in
                        Text(AppleBookCreatePresentation.subtitleTransliterationModelLabel(model)).tag(model)
                    }
                }
                .accessibilityIdentifier("createBookTransliterationModelPicker")
            }
        }
        Toggle("Lookup Cache", isOn: $enableLookupCache)
            .accessibilityIdentifier("createBookLookupCacheToggle")
        #if os(iOS)
        if enableLookupCache {
            Stepper(
                value: $lookupCacheBatchSize,
                in: AppleSubtitleTuning.translationBatchSizeRange,
                step: 1
            ) {
                LabeledContent("Lookup batch", value: "\(clampedLookupCacheBatchSize)")
            }
            .accessibilityIdentifier("createBookLookupCacheBatchSizeStepper")
        }
        #else
        if enableLookupCache {
            LabeledContent("Lookup batch") {
                HStack(spacing: 12) {
                    Button {
                        lookupCacheBatchSize = max(
                            AppleSubtitleTuning.translationBatchSizeRange.lowerBound,
                            clampedLookupCacheBatchSize - 1
                        )
                    } label: {
                        Image(systemName: "minus")
                    }
                    .disabled(clampedLookupCacheBatchSize <= AppleSubtitleTuning.translationBatchSizeRange.lowerBound)
                    .accessibilityLabel("Decrease lookup batch")

                    Text("\(clampedLookupCacheBatchSize)")
                        .monospacedDigit()
                        .frame(minWidth: 48)

                    Button {
                        lookupCacheBatchSize = min(
                            AppleSubtitleTuning.translationBatchSizeRange.upperBound,
                            clampedLookupCacheBatchSize + 1
                        )
                    } label: {
                        Image(systemName: "plus")
                    }
                    .disabled(clampedLookupCacheBatchSize >= AppleSubtitleTuning.translationBatchSizeRange.upperBound)
                    .accessibilityLabel("Increase lookup batch")
                }
            }
            .accessibilityIdentifier("createBookLookupCacheBatchSizeControl")
        }
        #endif
        TextField("Worker threads", text: $threadCount)
            #if os(iOS)
            .keyboardType(.numberPad)
            #endif
            .accessibilityIdentifier("createBookThreadCountField")
        TextField("Queue size", text: $queueSize)
            #if os(iOS)
            .keyboardType(.numberPad)
            #endif
            .accessibilityIdentifier("createBookQueueSizeField")
        TextField("Max job workers", text: $jobMaxWorkers)
            #if os(iOS)
            .keyboardType(.numberPad)
            #endif
            .accessibilityIdentifier("createBookJobMaxWorkersField")
    }
}
