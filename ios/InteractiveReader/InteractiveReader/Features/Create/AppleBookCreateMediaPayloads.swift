import Foundation

extension AppleBookCreatePayloadFactory {
    static func makeSubtitlePayload(from draft: AppleSubtitleJobDraft) -> SubtitleJobFormPayload {
        SubtitleJobFormPayload(
            inputLanguage: draft.inputLanguage,
            targetLanguage: draft.targetLanguage,
            sourcePath: draft.sourcePath,
            originalLanguage: draft.inputLanguage,
            llmModel: draft.llmModel,
            translationProvider: draft.translationProvider,
            transliterationMode: draft.transliterationMode ?? "default",
            transliterationModel: draft.transliterationModel,
            enableTransliteration: draft.enableTransliteration,
            highlight: draft.highlight,
            showOriginal: draft.showOriginal,
            generateAudioBook: draft.generateAudioBook,
            batchSize: draft.batchSize,
            translationBatchSize: draft.translationBatchSize,
            workerCount: draft.workerCount,
            startTime: draft.startTime,
            endTime: draft.endTime,
            assFontSize: draft.assFontSize,
            assEmphasisScale: draft.assEmphasisScale,
            mediaMetadataJSON: mediaMetadataJSONString(from: draft.mediaMetadata),
            mirrorBatchesToSourceDir: draft.mirrorBatchesToSourceDir,
            outputFormat: draft.outputFormat
        )
    }

    static func makeYoutubeDubPayload(from draft: AppleYoutubeDubDraft) -> YoutubeDubRequestPayload {
        YoutubeDubRequestPayload(
            videoPath: draft.videoPath,
            subtitlePath: draft.subtitlePath,
            mediaMetadata: draft.mediaMetadata,
            sourceLanguage: draft.sourceLanguage,
            targetLanguage: draft.targetLanguage,
            voice: draft.voice,
            startTimeOffset: draft.startTimeOffset,
            endTimeOffset: draft.endTimeOffset,
            originalMixPercent: draft.originalMixPercent,
            flushSentences: draft.flushSentences,
            llmModel: draft.llmModel,
            translationProvider: draft.translationProvider,
            translationBatchSize: draft.translationBatchSize,
            transliterationMode: draft.transliterationMode,
            transliterationModel: draft.transliterationModel,
            splitBatches: draft.splitBatches,
            stitchBatches: draft.stitchBatches,
            includeTransliteration: draft.includeTransliteration,
            targetHeight: draft.targetHeight,
            preserveAspectRatio: draft.preserveAspectRatio,
            enableLookupCache: draft.enableLookupCache
        )
    }

    private static func mediaMetadataJSONString(from metadata: [String: JSONValue]?) -> String? {
        guard let metadata, !metadata.isEmpty else {
            return nil
        }
        guard let data = try? JSONEncoder().encode(metadata) else {
            return nil
        }
        return String(data: data, encoding: .utf8)
    }
}
