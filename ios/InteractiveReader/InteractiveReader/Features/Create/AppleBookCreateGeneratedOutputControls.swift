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
    @Binding var sentenceSplitterMode: AppleBookSentenceSplitterMode
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
    let isCheckingImageNodes: Bool
    let imageNodeAvailabilityMessage: String?
    let imageNodeAvailabilityErrorMessage: String?
    let onCheckImageNodes: () -> Void

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
        AppleBookCreateGeneratedImageControls(
            includeImages: $includeImages,
            imagePromptPipeline: $imagePromptPipeline,
            imageStyleTemplate: $imageStyleTemplate,
            imagePromptBatchingEnabled: $imagePromptBatchingEnabled,
            imagePromptBatchSize: $imagePromptBatchSize,
            clampedImagePromptBatchSize: clampedImagePromptBatchSize,
            imagePromptPlanBatchSize: $imagePromptPlanBatchSize,
            clampedImagePromptPlanBatchSize: clampedImagePromptPlanBatchSize,
            imagePromptContextSentences: $imagePromptContextSentences,
            clampedImagePromptContextSentences: clampedImagePromptContextSentences,
            imageWidth: $imageWidth,
            imageHeight: $imageHeight,
            imageSteps: $imageSteps,
            imageCfgScale: $imageCfgScale,
            imageSamplerName: $imageSamplerName,
            imageSeedWithPreviousImage: $imageSeedWithPreviousImage,
            imageBlankDetectionEnabled: $imageBlankDetectionEnabled,
            imageApiBaseURLs: $imageApiBaseURLs,
            imageConcurrency: $imageConcurrency,
            imageApiTimeoutSeconds: $imageApiTimeoutSeconds,
            supportsImages: supportsImages,
            isCheckingImageNodes: isCheckingImageNodes,
            imageNodeAvailabilityMessage: imageNodeAvailabilityMessage,
            imageNodeAvailabilityErrorMessage: imageNodeAvailabilityErrorMessage,
            onCheckImageNodes: onCheckImageNodes
        )
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
        AppleBookCreateDiscreteValueControl(
            value: $sentencesPerOutputFile,
            clampedValue: clampedSentencesPerOutputFile,
            range: AppleBookOutputChunking.sentencesPerOutputFileRange,
            title: "Sentences per file",
            decrementAccessibilityLabel: "Decrease sentences per file",
            incrementAccessibilityLabel: "Increase sentences per file"
        )
        .accessibilityIdentifier("createBookSentencesPerFileControl")
        #endif
        Picker("Sentence splitter", selection: $sentenceSplitterMode) {
            ForEach(AppleBookSentenceSplitterMode.allCases) { mode in
                Text(mode.label).tag(mode)
            }
        }
        .accessibilityIdentifier("createBookSentenceSplitterModePicker")
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
        AppleBookCreateDiscreteValueControl(
            value: $translationBatchSize,
            clampedValue: clampedTranslationBatchSize,
            range: AppleSubtitleTuning.translationBatchSizeRange,
            title: "Translation batch",
            decrementAccessibilityLabel: "Decrease translation batch",
            incrementAccessibilityLabel: "Increase translation batch"
        )
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
            AppleBookCreateDiscreteValueControl(
                value: $lookupCacheBatchSize,
                clampedValue: clampedLookupCacheBatchSize,
                range: AppleSubtitleTuning.translationBatchSizeRange,
                title: "Lookup batch",
                decrementAccessibilityLabel: "Decrease lookup batch",
                incrementAccessibilityLabel: "Increase lookup batch"
            )
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
