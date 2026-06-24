import Foundation

extension AppleBookCreatePresentation {
    static func narrationHistoryDefaults(
        from jobs: [PipelineStatusResponse],
        currentInputFile: String
    ) -> AppleNarrationHistoryDefaults? {
        guard !jobs.isEmpty else { return nil }
        let latest = latestNarrationJob(from: jobs)
        let inputFile = latest.flatMap { narrationString($0, keys: ["input_file", "inputFile"]) }
        let baseOutput = latest.flatMap { narrationString($0, keys: ["base_output_file", "baseOutputFile"]) }
        let startInput = (inputFile ?? currentInputFile).trimmingCharacters(in: .whitespacesAndNewlines)
        let startSentence = narrationStartSentence(inputFile: startInput, from: jobs)

        let inputLanguage = latest
            .flatMap { narrationString($0, keys: ["input_language", "inputLanguage", "source_language", "sourceLanguage"]) }
            .flatMap(AppleBookCreateLanguage.init(backendValue:))
        let targetLanguages = latest
            .flatMap { narrationStringArray($0, keys: ["target_languages", "targetLanguages"]) } ?? []
        let normalizedTargets = normalizedLanguageList(targetLanguages)
        let targetLanguage = normalizedTargets.first.flatMap(AppleBookCreateLanguage.init(backendValue:))
        let additionalTargetLanguages = normalizedTargets.dropFirst().joined(separator: ", ")
        let voice = latest
            .flatMap { narrationString($0, keys: ["voice", "selected_voice", "selectedVoice"]) }
            .flatMap(AppleBookCreateVoiceOption.init(backendValue:))
        let generateAudio = latest.flatMap { narrationBool($0, keys: ["generate_audio", "generateAudio"]) }
        let audioMode = latest.flatMap { narrationString($0, keys: ["audio_mode", "audioMode"]) }
        let audioBitrateKbps = latest
            .flatMap { narrationInt($0, keys: ["audio_bitrate_kbps", "audioBitrateKbps"]) }
            .map { "\(max(32, $0))" }
        let writtenMode = latest.flatMap { narrationString($0, keys: ["written_mode", "writtenMode"]) }
        let tempo = latest
            .flatMap { historyDouble($0, keys: ["tempo"]) }
            .map(clampTempo)
        let sentencesPerOutputFile = latest
            .flatMap { narrationInt($0, keys: ["sentences_per_output_file", "sentencesPerOutputFile"]) }
            .map(clampBookSentencesPerOutputFile)
        let stitchFull = latest.flatMap { narrationBool($0, keys: ["stitch_full", "stitchFull"]) }
        let includeTransliteration = latest.flatMap { narrationBool($0, keys: ["include_transliteration", "includeTransliteration"]) }
        let translationProvider = latest
            .flatMap { narrationString($0, keys: ["translation_provider", "translationProvider"]) }
            .flatMap(AppleSubtitleTranslationProvider.init(backendValue:))
        let llmModel = latest.flatMap { narrationString($0, keys: ["llm_model", "llmModel"]) }
        let translationBatchSize = latest
            .flatMap { narrationInt($0, keys: ["translation_batch_size", "translationBatchSize"]) }
            .map(clampSubtitleTranslationBatchSize)
        let transliterationMode = latest
            .flatMap { narrationString($0, keys: ["transliteration_mode", "transliterationMode"]) }
            .flatMap(AppleSubtitleTransliterationMode.init(backendValue:))
        let transliterationModel = latest.flatMap { narrationString($0, keys: ["transliteration_model", "transliterationModel"]) }
        let lookupCache = latest.flatMap { narrationBool($0, keys: ["enable_lookup_cache", "enableLookupCache"]) }
        let lookupCacheBatchSize = latest
            .flatMap { narrationInt($0, keys: ["lookup_cache_batch_size", "lookupCacheBatchSize"]) }
            .map(clampSubtitleTranslationBatchSize)
        let outputHtml = latest.flatMap { narrationBool($0, keys: ["output_html", "outputHtml"]) }
        let outputPdf = latest.flatMap { narrationBool($0, keys: ["output_pdf", "outputPdf"]) }

        guard inputFile != nil
            || baseOutput != nil
            || startSentence != nil
            || inputLanguage != nil
            || targetLanguage != nil
            || !additionalTargetLanguages.isEmpty
            || voice != nil
            || generateAudio != nil
            || audioMode != nil
            || audioBitrateKbps != nil
            || writtenMode != nil
            || tempo != nil
            || sentencesPerOutputFile != nil
            || stitchFull != nil
            || includeTransliteration != nil
            || translationProvider != nil
            || llmModel != nil
            || translationBatchSize != nil
            || transliterationMode != nil
            || transliterationModel != nil
            || lookupCache != nil
            || lookupCacheBatchSize != nil
            || outputHtml != nil
            || outputPdf != nil
        else {
            return nil
        }

        return AppleNarrationHistoryDefaults(
            inputFile: inputFile,
            baseOutput: baseOutput,
            startSentence: startSentence,
            inputLanguage: inputLanguage,
            targetLanguage: targetLanguage,
            additionalTargetLanguages: additionalTargetLanguages.isEmpty ? nil : additionalTargetLanguages,
            voice: voice,
            generateAudio: generateAudio,
            audioMode: audioMode,
            audioBitrateKbps: audioBitrateKbps,
            writtenMode: writtenMode,
            tempo: tempo,
            sentencesPerOutputFile: sentencesPerOutputFile,
            stitchFull: stitchFull,
            includeTransliteration: includeTransliteration,
            translationProvider: translationProvider,
            llmModel: llmModel,
            translationBatchSize: translationBatchSize,
            transliterationMode: transliterationMode,
            transliterationModel: transliterationModel,
            enableLookupCache: lookupCache,
            lookupCacheBatchSize: lookupCacheBatchSize,
            outputHtml: outputHtml,
            outputPdf: outputPdf
        )
    }

    static func generatedBookHistoryDefaults(from jobs: [PipelineStatusResponse]) -> AppleGeneratedBookHistoryDefaults? {
        guard let latest = latestGeneratedBookJob(from: jobs),
              let parameters = latest.parameters?.objectValue
        else {
            return nil
        }
        let sources = generatedBookParameterSources(parameters)
        let targetLanguages = historyStringArray(in: sources, keys: ["target_languages", "targetLanguages"]) ?? []
        let normalizedTargets = normalizedLanguageList(targetLanguages)
        let targetLanguage = (normalizedTargets.first
            ?? historyString(in: sources, keys: ["output_language", "outputLanguage", "target_language", "targetLanguage"]))
            .flatMap(AppleBookCreateLanguage.init(backendValue:))
        let additionalTargetLanguages = normalizedTargets.dropFirst().joined(separator: ", ")
        let sentenceCount = historyInt(in: sources, keys: ["num_sentences", "numSentences", "sentence_count", "sentenceCount"])
            .map { max(1, $0) }

        let defaults = AppleGeneratedBookHistoryDefaults(
            topic: historyString(in: sources, keys: ["topic", "book_topic", "bookTopic"]),
            bookName: historyString(in: sources, keys: ["book_name", "bookName", "book_title", "bookTitle"]),
            genre: historyString(in: sources, keys: ["genre", "book_genre", "bookGenre"]),
            author: historyString(in: sources, keys: ["author", "book_author", "bookAuthor"]),
            sentenceCount: sentenceCount,
            inputLanguage: historyString(in: sources, keys: ["input_language", "inputLanguage", "source_language", "sourceLanguage"])
                .flatMap(AppleBookCreateLanguage.init(backendValue:)),
            targetLanguage: targetLanguage,
            additionalTargetLanguages: additionalTargetLanguages.isEmpty ? nil : additionalTargetLanguages,
            voice: historyString(in: sources, keys: ["voice", "selected_voice", "selectedVoice"])
                .flatMap(AppleBookCreateVoiceOption.init(backendValue:)),
            generateAudio: historyBool(in: sources, keys: ["generate_audio", "generateAudio"]),
            audioMode: historyString(in: sources, keys: ["audio_mode", "audioMode"]),
            audioBitrateKbps: historyInt(in: sources, keys: ["audio_bitrate_kbps", "audioBitrateKbps"])
                .map { "\(max(32, $0))" },
            writtenMode: historyString(in: sources, keys: ["written_mode", "writtenMode"]),
            tempo: historyDouble(in: sources, keys: ["tempo"])
                .map(clampTempo),
            bookSentencesPerOutputFile: historyInt(in: sources, keys: ["sentences_per_output_file", "sentencesPerOutputFile"])
                .map(clampBookSentencesPerOutputFile),
            stitchFull: historyBool(in: sources, keys: ["stitch_full", "stitchFull"]),
            includeTransliteration: historyBool(in: sources, keys: ["include_transliteration", "includeTransliteration"]),
            bookTranslationProvider: historyString(in: sources, keys: ["translation_provider", "translationProvider"])
                .flatMap(AppleSubtitleTranslationProvider.init(backendValue:)),
            bookLlmModel: historyString(in: sources, keys: ["llm_model", "llmModel"]),
            bookTranslationBatchSize: historyInt(in: sources, keys: ["translation_batch_size", "translationBatchSize"])
                .map(clampSubtitleTranslationBatchSize),
            bookTransliterationMode: historyString(in: sources, keys: ["transliteration_mode", "transliterationMode"])
                .flatMap(AppleSubtitleTransliterationMode.init(backendValue:)),
            bookTransliterationModel: historyString(in: sources, keys: ["transliteration_model", "transliterationModel"]),
            enableLookupCache: historyBool(in: sources, keys: ["enable_lookup_cache", "enableLookupCache"]),
            bookLookupCacheBatchSize: historyInt(in: sources, keys: ["lookup_cache_batch_size", "lookupCacheBatchSize"])
                .map(clampSubtitleTranslationBatchSize),
            outputHtml: historyBool(in: sources, keys: ["output_html", "outputHtml"]),
            outputPdf: historyBool(in: sources, keys: ["output_pdf", "outputPdf"]),
            includeImages: historyBool(in: sources, keys: ["add_images", "addImages"]),
            imagePromptPipeline: historyString(in: sources, keys: ["image_prompt_pipeline", "imagePromptPipeline"])
                .flatMap(AppleGeneratedBookImagePromptPipeline.init(backendValue:)),
            imageStyleTemplate: historyString(in: sources, keys: ["image_style_template", "imageStyleTemplate"])
                .flatMap(AppleGeneratedBookImageStyleTemplate.init(backendValue:)),
            imagePromptContextSentences: historyInt(in: sources, keys: ["image_prompt_context_sentences", "imagePromptContextSentences"])
                .map(clampImagePromptContextSentences),
            imageWidth: historyString(in: sources, keys: ["image_width", "imageWidth"])
                .map(normalizedImageDimension),
            imageHeight: historyString(in: sources, keys: ["image_height", "imageHeight"])
                .map(normalizedImageDimension)
        )

        guard defaults.topic != nil
            || defaults.bookName != nil
            || defaults.genre != nil
            || defaults.author != nil
            || defaults.sentenceCount != nil
            || defaults.inputLanguage != nil
            || defaults.targetLanguage != nil
            || defaults.additionalTargetLanguages != nil
            || defaults.voice != nil
            || defaults.generateAudio != nil
            || defaults.audioMode != nil
            || defaults.audioBitrateKbps != nil
            || defaults.writtenMode != nil
            || defaults.tempo != nil
            || defaults.bookSentencesPerOutputFile != nil
            || defaults.stitchFull != nil
            || defaults.includeTransliteration != nil
            || defaults.bookTranslationProvider != nil
            || defaults.bookLlmModel != nil
            || defaults.bookTranslationBatchSize != nil
            || defaults.bookTransliterationMode != nil
            || defaults.bookTransliterationModel != nil
            || defaults.enableLookupCache != nil
            || defaults.bookLookupCacheBatchSize != nil
            || defaults.outputHtml != nil
            || defaults.outputPdf != nil
            || defaults.includeImages != nil
            || defaults.imagePromptPipeline != nil
            || defaults.imageStyleTemplate != nil
            || defaults.imagePromptContextSentences != nil
            || defaults.imageWidth != nil
            || defaults.imageHeight != nil
        else {
            return nil
        }

        return defaults
    }

    static func subtitleHistoryDefaults(from jobs: [PipelineStatusResponse]) -> AppleSubtitleHistoryDefaults? {
        guard let latest = latestSubtitleJob(from: jobs) else { return nil }

        let sourcePath = narrationString(latest, keys: ["subtitle_path", "subtitlePath", "input_file", "inputFile"])
        let inputLanguage = narrationString(latest, keys: ["input_language", "inputLanguage", "source_language", "sourceLanguage"])
            .flatMap(AppleBookCreateLanguage.init(backendValue:))
        let targetLanguage = (narrationStringArray(latest, keys: ["target_languages", "targetLanguages"])?.first
            ?? narrationString(latest, keys: ["target_language", "targetLanguage"]))
            .flatMap(AppleBookCreateLanguage.init(backendValue:))
        let startTime = historyOffset(
            latest,
            stringKeys: ["start_time", "startTime", "start_time_offset", "startTimeOffset"],
            secondsKeys: ["start_time_offset_seconds", "startTimeOffsetSeconds"],
            allowRelative: false
        )
        let endTime = historyOffset(
            latest,
            stringKeys: ["end_time", "endTime", "end_time_offset", "endTimeOffset"],
            secondsKeys: ["end_time_offset_seconds", "endTimeOffsetSeconds"],
            allowRelative: true
        )
        let enableTransliteration = narrationBool(latest, keys: ["enable_transliteration", "enableTransliteration"])
        let showOriginal = narrationBool(latest, keys: ["show_original", "showOriginal"])
        let translationProvider = narrationString(latest, keys: ["translation_provider", "translationProvider"])
            .flatMap(AppleSubtitleTranslationProvider.init(backendValue:))
        let llmModel = narrationString(latest, keys: ["llm_model", "llmModel", "selected_model", "selectedModel"])
        let transliterationMode = narrationString(latest, keys: ["transliteration_mode", "transliterationMode"])
            .flatMap(AppleSubtitleTransliterationMode.init(backendValue:))
        let transliterationModel = narrationString(latest, keys: ["transliteration_model", "transliterationModel"])
        let workerCount = narrationInt(latest, keys: ["worker_count", "workerCount"])
            .map(clampSubtitleWorkerCount)
        let batchSize = narrationInt(latest, keys: ["batch_size", "batchSize"])
            .map(clampSubtitleBatchSize)
        let translationBatchSize = narrationInt(latest, keys: ["translation_batch_size", "translationBatchSize"])
            .map(clampSubtitleTranslationBatchSize)

        guard sourcePath != nil
            || inputLanguage != nil
            || targetLanguage != nil
            || startTime != nil
            || endTime != nil
            || enableTransliteration != nil
            || showOriginal != nil
            || translationProvider != nil
            || llmModel != nil
            || transliterationMode != nil
            || transliterationModel != nil
            || workerCount != nil
            || batchSize != nil
            || translationBatchSize != nil
        else {
            return nil
        }

        return AppleSubtitleHistoryDefaults(
            sourcePath: sourcePath,
            inputLanguage: inputLanguage,
            targetLanguage: targetLanguage,
            startTime: startTime,
            endTime: endTime,
            enableTransliteration: enableTransliteration,
            showOriginal: showOriginal,
            translationProvider: translationProvider,
            llmModel: llmModel,
            transliterationMode: transliterationMode,
            transliterationModel: transliterationModel,
            workerCount: workerCount,
            batchSize: batchSize,
            translationBatchSize: translationBatchSize
        )
    }

    static func youtubeHistoryDefaults(from jobs: [PipelineStatusResponse]) -> AppleYoutubeHistoryDefaults? {
        guard let latest = latestYoutubeJob(from: jobs) else { return nil }

        let targetLanguage = (narrationStringArray(latest, keys: ["target_languages", "targetLanguages"])?.first
            ?? narrationString(latest, keys: ["target_language", "targetLanguage"]))
            .flatMap(AppleBookCreateLanguage.init(backendValue:))
        let targetHeight = narrationInt(latest, keys: ["target_height", "targetHeight"])
            .flatMap(AppleYoutubeDubTargetHeight.init(rawValue:))

        let defaults = AppleYoutubeHistoryDefaults(
            videoPath: narrationString(latest, keys: ["input_file", "inputFile", "video_path", "videoPath"]),
            subtitlePath: narrationString(latest, keys: ["subtitle_path", "subtitlePath"]),
            targetLanguage: targetLanguage,
            voice: narrationString(latest, keys: ["selected_voice", "selectedVoice", "voice"])
                .flatMap(AppleBookCreateVoiceOption.init(backendValue:)),
            startOffset: historyOffset(
                latest,
                stringKeys: ["start_time_offset", "startTimeOffset", "start_offset", "startOffset"],
                secondsKeys: ["start_time_offset_seconds", "startTimeOffsetSeconds"],
                allowRelative: false
            ),
            endOffset: historyOffset(
                latest,
                stringKeys: ["end_time_offset", "endTimeOffset", "end_offset", "endOffset"],
                secondsKeys: ["end_time_offset_seconds", "endTimeOffsetSeconds"],
                allowRelative: false
            ),
            originalMixPercent: historyDouble(latest, keys: ["original_mix_percent", "originalMixPercent"])
                .map(clampYoutubeOriginalMixPercent),
            flushSentences: narrationInt(latest, keys: ["flush_sentences", "flushSentences"])
                .map(clampYoutubeFlushSentences),
            translationProvider: narrationString(latest, keys: ["translation_provider", "translationProvider"])
                .flatMap(AppleSubtitleTranslationProvider.init(backendValue:)),
            llmModel: narrationString(latest, keys: ["llm_model", "llmModel"]),
            translationBatchSize: narrationInt(latest, keys: ["translation_batch_size", "translationBatchSize"])
                .map(clampSubtitleTranslationBatchSize),
            transliterationMode: narrationString(latest, keys: ["transliteration_mode", "transliterationMode"])
                .flatMap(AppleSubtitleTransliterationMode.init(backendValue:)),
            transliterationModel: narrationString(latest, keys: ["transliteration_model", "transliterationModel"]),
            splitBatches: narrationBool(latest, keys: ["split_batches", "splitBatches"]),
            stitchBatches: narrationBool(latest, keys: ["stitch_batches", "stitchBatches"]),
            includeTransliteration: narrationBool(latest, keys: ["include_transliteration", "includeTransliteration"]),
            targetHeight: targetHeight,
            preserveAspectRatio: narrationBool(latest, keys: ["preserve_aspect_ratio", "preserveAspectRatio"]),
            enableLookupCache: narrationBool(latest, keys: ["enable_lookup_cache", "enableLookupCache"])
        )

        guard defaults.videoPath != nil
            || defaults.subtitlePath != nil
            || defaults.targetLanguage != nil
            || defaults.voice != nil
            || defaults.startOffset != nil
            || defaults.endOffset != nil
            || defaults.originalMixPercent != nil
            || defaults.flushSentences != nil
            || defaults.translationProvider != nil
            || defaults.llmModel != nil
            || defaults.translationBatchSize != nil
            || defaults.transliterationMode != nil
            || defaults.transliterationModel != nil
            || defaults.splitBatches != nil
            || defaults.stitchBatches != nil
            || defaults.includeTransliteration != nil
            || defaults.targetHeight != nil
            || defaults.preserveAspectRatio != nil
            || defaults.enableLookupCache != nil
        else {
            return nil
        }

        return defaults
    }

    static func narrationStartSentence(
        inputFile: String,
        from jobs: [PipelineStatusResponse]
    ) -> Int? {
        let normalizedInput = normalizedNarrationPath(inputFile)
        guard let normalizedInput, !jobs.isEmpty else { return nil }

        var latest: (createdAt: Date, anchor: Int)?
        for job in jobs where isReusableNarrationJob(job) {
            guard let createdAt = parseJobDate(job.createdAt),
                  let candidate = normalizedNarrationPath(
                    narrationString(job, keys: ["input_file", "inputFile", "base_output_file", "baseOutputFile"])
                  ),
                  candidate == normalizedInput
            else {
                continue
            }
            let anchor = narrationInt(job, keys: ["end_sentence", "endSentence"])
                ?? narrationInt(job, keys: ["start_sentence", "startSentence"])
            guard let anchor else { continue }
            if latest == nil || createdAt > latest!.createdAt {
                latest = (createdAt, anchor)
            }
        }

        guard let latest else { return nil }
        return max(1, latest.anchor - 5)
    }
}
