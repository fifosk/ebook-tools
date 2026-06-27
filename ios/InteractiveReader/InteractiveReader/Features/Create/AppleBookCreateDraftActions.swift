import Foundation

extension AppleBookCreateView {
    func currentGeneratedBookDraft() -> AppleBookCreateDraft {
        AppleBookCreatePresentation.generatedBookDraft(
            topic: trimmed(topic),
            bookName: trimmed(bookName),
            genre: trimmed(genre),
            author: author,
            summary: bookSummary,
            year: bookYear,
            isbn: bookIsbn,
            coverFile: bookCoverFile,
            bookMetadataExtras: bookMetadataExtras,
            sourceBookTitle: sourceBookTitle,
            sourceBookAuthor: sourceBookAuthor,
            sourceBookGenre: sourceBookGenre,
            sourceBookSummary: sourceBookSummary,
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
            sentenceSplitterMode: bookSentenceSplitterMode,
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
    }

    func currentNarrateEbookDraft() -> AppleNarrateEbookDraft {
        AppleBookCreatePresentation.narrateEbookDraft(
            inputFile: sourcePath,
            baseOutput: sourceBaseOutput,
            title: sourceBookTitle,
            author: sourceBookAuthor,
            genre: sourceBookGenre,
            summary: bookSummary,
            year: bookYear,
            isbn: bookIsbn,
            coverFile: bookCoverFile,
            bookMetadataExtras: bookMetadataExtras,
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
            sentenceSplitterMode: bookSentenceSplitterMode,
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
    }

    func currentSubtitleJobDraft() -> AppleSubtitleJobDraft? {
        let timeRange: AppleCreateTimeRange
        switch AppleBookCreatePresentation.normalizedSubtitleTimeRange(
            start: subtitleStartTime,
            end: subtitleEndTime
        ) {
        case let .success(normalizedRange):
            timeRange = normalizedRange
        case let .failure(error):
            viewModel.errorMessage = error.message
            return nil
        }
        subtitleStartTime = timeRange.start
        subtitleEndTime = timeRange.end

        return AppleBookCreatePresentation.subtitleJobDraft(
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
    }

    func currentYoutubeDubDraft() -> AppleYoutubeDubDraft? {
        let offsetRange: AppleCreateOffsetRange
        switch AppleBookCreatePresentation.normalizedYoutubeOffsetRange(
            start: youtubeStartOffset,
            end: youtubeEndOffset
        ) {
        case let .success(normalizedRange):
            offsetRange = normalizedRange
        case let .failure(error):
            viewModel.errorMessage = error.message
            return nil
        }
        youtubeStartOffset = offsetRange.start
        youtubeEndOffset = offsetRange.end

        return AppleBookCreatePresentation.youtubeDubDraft(
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
            videoDiscoveryState: youtubeDiscoveryState,
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
            includeTransliteration: youtubeIncludeTransliteration,
            targetHeight: youtubeTargetHeight,
            preserveAspectRatio: youtubePreserveAspectRatio,
            enableLookupCache: youtubeEnableLookupCache
        )
    }
}
