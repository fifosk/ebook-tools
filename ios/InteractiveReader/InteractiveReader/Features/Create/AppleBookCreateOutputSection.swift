import SwiftUI

struct AppleBookCreateOutputSection: View {
    let creationMode: AppleCreateMode
    let derivedBaseOutput: String
    @Binding var subtitleOutputFormat: AppleSubtitleOutputFormat
    let selectedSubtitleOutputFormat: AppleSubtitleOutputFormat
    @Binding var subtitleAssFontSize: Int
    let clampedSubtitleAssFontSize: Int
    @Binding var subtitleAssEmphasisScale: Double
    let formattedSubtitleAssEmphasisScale: String
    @Binding var subtitleStartTime: String
    @Binding var subtitleEndTime: String
    @Binding var subtitleEnableTransliteration: Bool
    let isSubtitleTransliterationEnabled: Bool
    @Binding var subtitleTransliterationMode: AppleSubtitleTransliterationMode
    let selectedSubtitleTransliterationMode: AppleSubtitleTransliterationMode
    @Binding var subtitleTransliterationModel: String
    let availableSubtitleTransliterationModels: [String]
    @Binding var subtitleHighlight: Bool
    @Binding var subtitleShowOriginal: Bool
    @Binding var subtitleGenerateAudioBook: Bool
    @Binding var subtitleMirrorBatchesToSourceDir: Bool
    @Binding var subtitleTranslationProvider: AppleSubtitleTranslationProvider
    let selectedSubtitleTranslationProvider: AppleSubtitleTranslationProvider
    @Binding var subtitleWorkerCount: Int
    let clampedSubtitleWorkerCount: Int
    @Binding var subtitleBatchSize: Int
    let clampedSubtitleBatchSize: Int
    @Binding var subtitleLlmModel: String
    let availableSubtitleLlmModels: [String]
    @Binding var subtitleTranslationBatchSize: Int
    let clampedSubtitleTranslationBatchSize: Int
    @Binding var youtubeTargetHeight: AppleYoutubeDubTargetHeight
    @Binding var youtubeStartOffset: String
    @Binding var youtubeEndOffset: String
    @Binding var youtubeOriginalMixPercent: Double
    let formattedYoutubeOriginalMixPercent: String
    @Binding var youtubeFlushSentences: Int
    let clampedYoutubeFlushSentences: Int
    @Binding var youtubeSplitBatches: Bool
    let isYoutubeSplitBatchesEnabled: Bool
    @Binding var youtubeStitchBatches: Bool
    @Binding var youtubePreserveAspectRatio: Bool
    @Binding var youtubeIncludeTransliteration: Bool
    @Binding var youtubeEnableLookupCache: Bool
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
    @Binding var bookTranslationProvider: AppleSubtitleTranslationProvider
    let selectedBookTranslationProvider: AppleSubtitleTranslationProvider
    @Binding var bookLlmModel: String
    @Binding var bookTranslationBatchSize: Int
    let clampedBookTranslationBatchSize: Int
    @Binding var bookTransliterationMode: AppleSubtitleTransliterationMode
    let selectedBookTransliterationMode: AppleSubtitleTransliterationMode
    @Binding var bookTransliterationModel: String
    let availableBookTransliterationModels: [String]
    @Binding var enableLookupCache: Bool
    @Binding var bookLookupCacheBatchSize: Int
    let clampedBookLookupCacheBatchSize: Int
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
        Section("Output") {
            if creationMode == .subtitleJob {
                subtitleOutputControls
            } else if creationMode == .youtubeDub {
                youtubeOutputControls
            } else {
                generatedOutputControls
            }
        }
    }

    private var subtitleOutputControls: some View {
        AppleBookCreateSubtitleOutputControls(
            outputFormat: $subtitleOutputFormat,
            selectedOutputFormat: selectedSubtitleOutputFormat,
            assFontSize: $subtitleAssFontSize,
            clampedAssFontSize: clampedSubtitleAssFontSize,
            assEmphasisScale: $subtitleAssEmphasisScale,
            formattedAssEmphasisScale: formattedSubtitleAssEmphasisScale,
            startTime: $subtitleStartTime,
            endTime: $subtitleEndTime,
            enableTransliteration: $subtitleEnableTransliteration,
            isTransliterationEnabled: isSubtitleTransliterationEnabled,
            transliterationMode: $subtitleTransliterationMode,
            selectedTransliterationMode: selectedSubtitleTransliterationMode,
            transliterationModel: $subtitleTransliterationModel,
            availableTransliterationModels: availableSubtitleTransliterationModels,
            highlight: $subtitleHighlight,
            showOriginal: $subtitleShowOriginal,
            generateAudioBook: $subtitleGenerateAudioBook,
            mirrorBatchesToSourceDir: $subtitleMirrorBatchesToSourceDir,
            translationProvider: $subtitleTranslationProvider,
            selectedTranslationProvider: selectedSubtitleTranslationProvider,
            workerCount: $subtitleWorkerCount,
            clampedWorkerCount: clampedSubtitleWorkerCount,
            batchSize: $subtitleBatchSize,
            clampedBatchSize: clampedSubtitleBatchSize,
            llmModel: $subtitleLlmModel,
            availableLlmModels: availableSubtitleLlmModels,
            translationBatchSize: $subtitleTranslationBatchSize,
            clampedTranslationBatchSize: clampedSubtitleTranslationBatchSize
        )
    }

    private var youtubeOutputControls: some View {
        AppleBookCreateYoutubeOutputControls(
            translationProvider: $subtitleTranslationProvider,
            selectedTranslationProvider: selectedSubtitleTranslationProvider,
            llmModel: $subtitleLlmModel,
            availableSubtitleLlmModels: availableSubtitleLlmModels,
            targetHeight: $youtubeTargetHeight,
            startOffset: $youtubeStartOffset,
            endOffset: $youtubeEndOffset,
            originalMixPercent: $youtubeOriginalMixPercent,
            formattedOriginalMixPercent: formattedYoutubeOriginalMixPercent,
            flushSentences: $youtubeFlushSentences,
            clampedFlushSentences: clampedYoutubeFlushSentences,
            translationBatchSize: $subtitleTranslationBatchSize,
            clampedTranslationBatchSize: clampedSubtitleTranslationBatchSize,
            splitBatches: $youtubeSplitBatches,
            isSplitBatchesEnabled: isYoutubeSplitBatchesEnabled,
            stitchBatches: $youtubeStitchBatches,
            preserveAspectRatio: $youtubePreserveAspectRatio,
            includeTransliteration: $youtubeIncludeTransliteration,
            enableLookupCache: $youtubeEnableLookupCache
        )
    }

    private var generatedOutputControls: some View {
        AppleBookCreateGeneratedOutputControls(
            derivedBaseOutput: derivedBaseOutput,
            generateAudio: $generateAudio,
            audioMode: $audioMode,
            audioBitrateKbps: $audioBitrateKbps,
            writtenMode: $writtenMode,
            tempo: $tempo,
            formattedTempo: formattedTempo,
            estimatedAudioDurationLabel: estimatedAudioDurationLabel,
            sentencesPerOutputFile: $sentencesPerOutputFile,
            clampedSentencesPerOutputFile: clampedSentencesPerOutputFile,
            sentenceSplitterMode: $sentenceSplitterMode,
            stitchFull: $stitchFull,
            includeTransliteration: $includeTransliteration,
            translationProvider: $bookTranslationProvider,
            selectedTranslationProvider: selectedBookTranslationProvider,
            llmModel: $bookLlmModel,
            availableLlmModels: availableSubtitleLlmModels,
            translationBatchSize: $bookTranslationBatchSize,
            clampedTranslationBatchSize: clampedBookTranslationBatchSize,
            transliterationMode: $bookTransliterationMode,
            selectedTransliterationMode: selectedBookTransliterationMode,
            transliterationModel: $bookTransliterationModel,
            availableTransliterationModels: availableBookTransliterationModels,
            enableLookupCache: $enableLookupCache,
            lookupCacheBatchSize: $bookLookupCacheBatchSize,
            clampedLookupCacheBatchSize: clampedBookLookupCacheBatchSize,
            outputHtml: $outputHtml,
            outputPdf: $outputPdf,
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
            threadCount: $threadCount,
            queueSize: $queueSize,
            jobMaxWorkers: $jobMaxWorkers,
            supportsImages: supportsImages,
            isCheckingImageNodes: isCheckingImageNodes,
            imageNodeAvailabilityMessage: imageNodeAvailabilityMessage,
            imageNodeAvailabilityErrorMessage: imageNodeAvailabilityErrorMessage,
            onCheckImageNodes: onCheckImageNodes
        )
    }
}
