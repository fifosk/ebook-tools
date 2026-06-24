import SwiftUI

struct AppleBookCreateGeneratedImageControls: View {
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
    let supportsImages: Bool

    var body: some View {
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
    }
}
