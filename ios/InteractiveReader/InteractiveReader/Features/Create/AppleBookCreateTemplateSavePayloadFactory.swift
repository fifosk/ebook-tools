import Foundation

enum AppleBookCreateTemplateSavePayloadFactory {
    static func makeGeneratedBookRequest(from draft: AppleBookCreateDraft) -> CreationTemplateSaveRequest {
        var formState = makeBookFormState(
            inputFile: "\(draft.baseOutput).epub",
            baseOutput: draft.baseOutput,
            startSentence: 1,
            endSentence: nil,
            targetLanguages: draft.targetLanguages,
            selectedVoice: draft.voice,
            voiceOverrides: draft.voiceOverrides,
            inputLanguage: draft.inputLanguage,
            generateAudio: draft.generateAudio,
            audioMode: draft.audioMode,
            audioBitrateKbps: draft.audioBitrateKbps,
            writtenMode: draft.writtenMode,
            tempo: draft.tempo,
            sentencesPerOutputFile: draft.sentencesPerOutputFile,
            sentenceSplitterMode: draft.sentenceSplitterMode,
            stitchFull: draft.stitchFull,
            includeTransliteration: draft.includeTransliteration,
            translationProvider: draft.translationProvider,
            llmModel: draft.llmModel,
            translationBatchSize: draft.translationBatchSize,
            transliterationMode: draft.transliterationMode,
            transliterationModel: draft.transliterationModel,
            enableLookupCache: draft.enableLookupCache,
            lookupCacheBatchSize: draft.lookupCacheBatchSize,
            outputHtml: draft.outputHtml,
            outputPdf: draft.outputPdf,
            addImages: draft.includeImages,
            imagePromptPipeline: draft.imagePromptPipeline,
            imageStyleTemplate: draft.imageStyleTemplate,
            imagePromptBatchingEnabled: draft.imagePromptBatchingEnabled,
            imagePromptBatchSize: draft.imagePromptBatchSize,
            imagePromptPlanBatchSize: draft.imagePromptPlanBatchSize,
            imagePromptContextSentences: draft.imagePromptContextSentences,
            imageWidth: draft.imageWidth,
            imageHeight: draft.imageHeight,
            imageSteps: draft.imageSteps.map(String.init),
            imageCfgScale: draft.imageCfgScale.map(formatDecimal),
            imageSamplerName: draft.imageSamplerName,
            imageSeedWithPreviousImage: draft.imageSeedWithPreviousImage,
            imageBlankDetectionEnabled: draft.imageBlankDetectionEnabled,
            imageApiBaseURLs: draft.imageApiBaseURLs,
            imageConcurrency: draft.imageConcurrency.map(String.init),
            imageApiTimeoutSeconds: draft.imageApiTimeoutSeconds.map(formatDecimal),
            threadCount: draft.threadCount.map(String.init),
            queueSize: draft.queueSize.map(String.init),
            jobMaxWorkers: draft.jobMaxWorkers.map(String.init),
            bookMetadata: makeBookMetadata(
                title: draft.bookName,
                author: draft.author,
                genre: draft.genre,
                language: draft.inputLanguage,
                summary: draft.summary,
                year: draft.year,
                isbn: draft.isbn,
                coverFile: draft.coverFile,
                extraMetadata: draft.bookMetadataExtras
            )
        )
        add(draft.sourceBookTitle, named: "source_book_title", to: &formState)
        add(draft.sourceBookAuthor, named: "source_book_author", to: &formState)
        add(draft.sourceBookGenre, named: "source_book_genre", to: &formState)
        add(draft.sourceBookSummary, named: "source_book_summary", to: &formState)
        var payload = makeBookPayload(
            sourceMode: "generated",
            formState: formState,
            activeSection: "submit",
            discoveryState: makeBookDiscoveryState(from: draft.bookMetadataExtras)
        )
        payload["generator_state"] = .object([
            "topic": .string(draft.topic),
            "book_name": .string(draft.bookName),
            "genre": .string(draft.genre),
            "author": .string(draft.author),
            "num_sentences": .number(Double(draft.sentenceCount)),
        ])
        add(draft.sourceBookTitle, named: "source_book_title", to: &payload)
        add(draft.sourceBookAuthor, named: "source_book_author", to: &payload)
        add(draft.sourceBookGenre, named: "source_book_genre", to: &payload)
        add(draft.sourceBookSummary, named: "source_book_summary", to: &payload)

        return CreationTemplateSaveRequest(
            id: nil,
            name: templateName(primary: draft.bookName, fallback: draft.topic, suffix: "Generated book"),
            mode: "generated_book",
            payload: payload
        )
    }

    static func makeNarrateEbookRequest(from draft: AppleNarrateEbookDraft) -> CreationTemplateSaveRequest {
        let metadata = makeBookMetadata(
            title: draft.title ?? draft.baseOutput,
            author: draft.author,
            genre: draft.genre,
            language: draft.inputLanguage,
            summary: draft.summary,
            year: draft.year,
            isbn: draft.isbn,
            coverFile: draft.coverFile,
            extraMetadata: draft.bookMetadataExtras
        )
        let formState = makeBookFormState(
            inputFile: draft.inputFile,
            baseOutput: draft.baseOutput,
            startSentence: draft.startSentence,
            endSentence: draft.endSentence,
            targetLanguages: draft.targetLanguages,
            selectedVoice: draft.voice,
            voiceOverrides: draft.voiceOverrides,
            inputLanguage: draft.inputLanguage,
            generateAudio: draft.generateAudio,
            audioMode: draft.audioMode,
            audioBitrateKbps: draft.audioBitrateKbps,
            writtenMode: draft.writtenMode,
            tempo: draft.tempo,
            sentencesPerOutputFile: draft.sentencesPerOutputFile,
            sentenceSplitterMode: draft.sentenceSplitterMode,
            stitchFull: draft.stitchFull,
            includeTransliteration: draft.includeTransliteration,
            translationProvider: draft.translationProvider,
            llmModel: draft.llmModel,
            translationBatchSize: draft.translationBatchSize,
            transliterationMode: draft.transliterationMode,
            transliterationModel: draft.transliterationModel,
            enableLookupCache: draft.enableLookupCache,
            lookupCacheBatchSize: draft.lookupCacheBatchSize,
            outputHtml: draft.outputHtml,
            outputPdf: draft.outputPdf,
            addImages: false,
            imagePromptPipeline: "",
            imageStyleTemplate: "",
            imagePromptBatchingEnabled: true,
            imagePromptBatchSize: 10,
            imagePromptPlanBatchSize: 50,
            imagePromptContextSentences: 0,
            imageWidth: "",
            imageHeight: "",
            imageSteps: nil,
            imageCfgScale: nil,
            imageSamplerName: nil,
            imageSeedWithPreviousImage: false,
            imageBlankDetectionEnabled: false,
            imageApiBaseURLs: [],
            imageConcurrency: nil,
            imageApiTimeoutSeconds: nil,
            threadCount: draft.threadCount.map(String.init),
            queueSize: draft.queueSize.map(String.init),
            jobMaxWorkers: draft.jobMaxWorkers.map(String.init),
            bookMetadata: metadata
        )
        return CreationTemplateSaveRequest(
            id: nil,
            name: templateName(primary: draft.title, fallback: draft.baseOutput, suffix: "Narrate Ebook"),
            mode: "narrate_ebook",
            payload: makeBookPayload(
                sourceMode: "upload",
                formState: formState,
                activeSection: "submit",
                discoveryState: makeBookDiscoveryState(
                    from: draft.bookMetadataExtras,
                    selectedPath: draft.inputFile,
                    selectedProvider: draft.bookDiscoveryProvider,
                    query: draft.bookDiscoveryQuery
                )
            )
        )
    }

    static func makeSubtitleJobRequest(from draft: AppleSubtitleJobDraft) -> CreationTemplateSaveRequest {
        var formState: [String: JSONValue] = [
            "source_mode": .string(draft.sourcePath?.nonEmptyValue == nil ? "upload" : "server"),
            "input_language": .string(draft.inputLanguage),
            "original_language": .string(draft.inputLanguage),
            "target_language": .string(draft.targetLanguage),
            "enable_transliteration": .bool(draft.enableTransliteration),
            "highlight": .bool(draft.highlight),
            "show_original": .bool(draft.showOriginal),
            "generate_audio_book": .bool(draft.generateAudioBook),
            "output_format": .string(draft.outputFormat),
            "mirror_batches_to_source_dir": .bool(draft.mirrorBatchesToSourceDir),
            "start_time": .string(draft.startTime),
            "worker_count": .number(Double(draft.workerCount)),
            "batch_size": .number(Double(draft.batchSize)),
            "translation_batch_size": .number(Double(draft.translationBatchSize)),
        ]
        add(draft.endTime, named: "end_time", to: &formState)
        add(draft.sourcePath, named: "source_path", to: &formState)
        add(draft.llmModel, named: "llm_model", to: &formState)
        add(draft.translationProvider, named: "translation_provider", to: &formState)
        add(draft.transliterationMode, named: "transliteration_mode", to: &formState)
        add(draft.transliterationModel, named: "transliteration_model", to: &formState)
        add(draft.assFontSize, named: "ass_font_size", to: &formState)
        add(draft.assEmphasisScale, named: "ass_emphasis_scale", to: &formState)
        if let mediaMetadata = draft.mediaMetadata, !mediaMetadata.isEmpty {
            formState["media_metadata"] = .object(mediaMetadata)
        }

        return CreationTemplateSaveRequest(
            id: nil,
            name: templateName(primary: draft.mediaMetadata?["title"]?.stringValue, fallback: draft.sourcePath, suffix: "Subtitle job"),
            mode: "subtitle_job",
            payload: [
                "kind": .string("subtitle_job_form"),
                "source": .string("apple"),
                "version": .number(1),
                "source_mode": formState["source_mode"] ?? .string("server"),
                "form_state": .object(formState),
            ]
        )
    }

    static func makeYoutubeDubRequest(from draft: AppleYoutubeDubDraft) -> CreationTemplateSaveRequest {
        var formState: [String: JSONValue] = [
            "video_path": .string(draft.videoPath),
            "subtitle_path": .string(draft.subtitlePath),
            "voice": .string(draft.voice),
            "original_mix_percent": .number(draft.originalMixPercent),
            "flush_sentences": .number(Double(draft.flushSentences)),
            "translation_provider": .string(draft.translationProvider),
            "translation_batch_size": .number(Double(draft.translationBatchSize)),
            "split_batches": .bool(draft.splitBatches),
            "stitch_batches": .bool(draft.stitchBatches),
            "include_transliteration": .bool(draft.includeTransliteration),
            "target_height": .number(Double(draft.targetHeight)),
            "preserve_aspect_ratio": .bool(draft.preserveAspectRatio),
            "enable_lookup_cache": .bool(draft.enableLookupCache),
            "media_metadata": .object(draft.mediaMetadata),
        ]
        add(draft.sourceLanguage, named: "source_language", to: &formState)
        add(draft.targetLanguage, named: "target_language", to: &formState)
        add(draft.startTimeOffset, named: "start_time_offset", to: &formState)
        add(draft.endTimeOffset, named: "end_time_offset", to: &formState)
        add(draft.llmModel, named: "llm_model", to: &formState)
        add(draft.transliterationMode, named: "transliteration_mode", to: &formState)
        add(draft.transliterationModel, named: "transliteration_model", to: &formState)

        var payload: [String: JSONValue] = [
            "kind": .string("youtube_dub_form"),
            "source": .string("apple"),
            "version": .number(1),
            "form_state": .object(formState),
        ]
        if let discoveryState = makeVideoDiscoveryState(from: draft.videoDiscoveryState) {
            payload["discovery_state"] = .object(discoveryState)
        }

        return CreationTemplateSaveRequest(
            id: nil,
            name: templateName(primary: draft.mediaMetadata["title"]?.stringValue, fallback: draft.videoPath, suffix: "YouTube dub"),
            mode: "youtube_dub",
            payload: payload
        )
    }

    private static func makeBookPayload(
        sourceMode: String,
        formState: [String: JSONValue],
        activeSection: String,
        discoveryState: [String: JSONValue]? = nil
    ) -> [String: JSONValue] {
        var payload: [String: JSONValue] = [
            "kind": .string("book_narration_form"),
            "source": .string("apple"),
            "version": .number(1),
            "source_mode": .string(sourceMode),
            "active_section": .string(activeSection),
            "form_state": .object(formState),
        ]
        if let discoveryState, !discoveryState.isEmpty {
            payload["discovery_state"] = .object(discoveryState)
        }
        return payload
    }

    private static func makeBookFormState(
        inputFile: String,
        baseOutput: String,
        startSentence: Int,
        endSentence: Int?,
        targetLanguages: [String],
        selectedVoice: String,
        voiceOverrides: [String: String],
        inputLanguage: String,
        generateAudio: Bool,
        audioMode: String,
        audioBitrateKbps: Int?,
        writtenMode: String,
        tempo: Double,
        sentencesPerOutputFile: Int,
        sentenceSplitterMode: String,
        stitchFull: Bool,
        includeTransliteration: Bool,
        translationProvider: String,
        llmModel: String?,
        translationBatchSize: Int,
        transliterationMode: String,
        transliterationModel: String?,
        enableLookupCache: Bool,
        lookupCacheBatchSize: Int,
        outputHtml: Bool,
        outputPdf: Bool,
        addImages: Bool,
        imagePromptPipeline: String,
        imageStyleTemplate: String,
        imagePromptBatchingEnabled: Bool,
        imagePromptBatchSize: Int,
        imagePromptPlanBatchSize: Int,
        imagePromptContextSentences: Int,
        imageWidth: String,
        imageHeight: String,
        imageSteps: String?,
        imageCfgScale: String?,
        imageSamplerName: String?,
        imageSeedWithPreviousImage: Bool,
        imageBlankDetectionEnabled: Bool,
        imageApiBaseURLs: [String],
        imageConcurrency: String?,
        imageApiTimeoutSeconds: String?,
        threadCount: String?,
        queueSize: String?,
        jobMaxWorkers: String?,
        bookMetadata: [String: JSONValue]
    ) -> [String: JSONValue] {
        let formState: [String: JSONValue] = [
            "input_file": .string(inputFile),
            "base_output_file": .string(baseOutput),
            "input_language": .string(inputLanguage),
            "target_languages": .array(targetLanguages.map { .string($0) }),
            "custom_target_languages": .string(""),
            "ollama_model": .string(llmModel ?? ""),
            "sentences_per_output_file": .number(Double(sentencesPerOutputFile)),
            "sentence_splitter_mode": .string(
                AppleBookSentenceSplitterMode(backendValue: sentenceSplitterMode).backendValue
            ),
            "start_sentence": .number(Double(startSentence)),
            "end_sentence": endSentence.map { .string(String($0)) } ?? .string(""),
            "stitch_full": .bool(stitchFull),
            "generate_audio": .bool(generateAudio),
            "audio_mode": .string(audioMode),
            "audio_bitrate_kbps": .string(audioBitrateKbps.map(String.init) ?? ""),
            "written_mode": .string(writtenMode),
            "selected_voice": .string(selectedVoice),
            "voice_overrides": .object(voiceOverrides.reduce(into: [String: JSONValue]()) { result, entry in
                result[entry.key] = .string(entry.value)
            }),
            "output_html": .bool(outputHtml),
            "output_pdf": .bool(outputPdf),
            "add_images": .bool(addImages),
            "image_prompt_pipeline": .string(imagePromptPipeline),
            "image_style_template": .string(imageStyleTemplate),
            "image_prompt_batching_enabled": .bool(imagePromptBatchingEnabled),
            "image_prompt_batch_size": .number(Double(imagePromptBatchSize)),
            "image_prompt_plan_batch_size": .number(Double(imagePromptPlanBatchSize)),
            "image_prompt_context_sentences": .number(Double(imagePromptContextSentences)),
            "image_seed_with_previous_image": .bool(imageSeedWithPreviousImage),
            "image_blank_detection_enabled": .bool(imageBlankDetectionEnabled),
            "image_api_base_urls": .array(imageApiBaseURLs.map { .string($0) }),
            "image_width": .string(imageWidth),
            "image_height": .string(imageHeight),
            "image_steps": .string(imageSteps ?? ""),
            "image_cfg_scale": .string(imageCfgScale ?? ""),
            "image_sampler_name": .string(imageSamplerName ?? ""),
            "image_api_timeout_seconds": .string(imageApiTimeoutSeconds ?? ""),
            "include_transliteration": .bool(includeTransliteration),
            "translation_provider": .string(translationProvider),
            "translation_batch_size": .number(Double(translationBatchSize)),
            "transliteration_mode": .string(transliterationMode),
            "transliteration_model": .string(transliterationModel ?? ""),
            "enable_lookup_cache": .bool(enableLookupCache),
            "lookup_cache_batch_size": .number(Double(lookupCacheBatchSize)),
            "tempo": .number(tempo),
            "thread_count": .string(threadCount ?? ""),
            "queue_size": .string(queueSize ?? ""),
            "job_max_workers": .string(jobMaxWorkers ?? ""),
            "image_concurrency": .string(imageConcurrency ?? ""),
            "config": .string("{}"),
            "environment_overrides": .string("{}"),
            "pipeline_overrides": .string("{}"),
            "book_metadata": .string(jsonString(from: bookMetadata)),
        ]
        return formState
    }

    private static func makeBookMetadata(
        title: String,
        author: String?,
        genre: String?,
        language: String?,
        summary: String?,
        year: String?,
        isbn: String?,
        coverFile: String?,
        extraMetadata: [String: JSONValue]
    ) -> [String: JSONValue] {
        let normalizedTitle = title.trimmingCharacters(in: .whitespacesAndNewlines)
        var metadata: [String: JSONValue] = [
            "title": .string(normalizedTitle),
            "book_title": .string(normalizedTitle),
            "job_label": .string(normalizedTitle),
            "source": .string("apple"),
        ]
        add(author, named: "author", to: &metadata)
        add(author, named: "book_author", to: &metadata)
        add(genre, named: "genre", to: &metadata)
        add(genre, named: "book_genre", to: &metadata)
        if let genre {
            let genres = AppleBookCreatePresentation.normalizedBookGenres(genre)
            if !genres.isEmpty {
                metadata["book_genres"] = .array(genres.map { .string($0) })
            }
        }
        add(language, named: "language", to: &metadata)
        add(language, named: "book_language", to: &metadata)
        add(summary, named: "book_summary", to: &metadata)
        add(year, named: "book_year", to: &metadata)
        add(isbn, named: "isbn", to: &metadata)
        add(isbn, named: "book_isbn", to: &metadata)
        addBookCover(coverFile, to: &metadata)
        mergeExtraBookMetadata(extraMetadata, into: &metadata)
        return metadata
    }

    private static func mergeExtraBookMetadata(
        _ extraMetadata: [String: JSONValue],
        into metadata: inout [String: JSONValue]
    ) {
        let normalized = AppleBookCreatePresentation.normalizedBookMetadataExtras(extraMetadata)
        for (key, value) in normalized where metadata[key] == nil {
            metadata[key] = value
        }
    }

    private static func makeBookDiscoveryState(
        from extraMetadata: [String: JSONValue],
        selectedPath: String? = nil,
        selectedProvider: String? = nil,
        query: String? = nil
    ) -> [String: JSONValue]? {
        let normalized = AppleBookCreatePresentation.normalizedBookMetadataExtras(extraMetadata)
        guard let provider = normalizedString(normalized["acquisition_provider"]) else {
            return nil
        }
        var state: [String: JSONValue] = [
            "media_kind": .string("book"),
            "provider": .string(provider),
        ]
        add(firstString(in: normalized, keys: "book_title", "title"), named: "title", to: &state)
        add(firstString(in: normalized, keys: "rights"), named: "rights", to: &state)
        add(firstString(in: normalized, keys: "language", "book_language"), named: "language", to: &state)
        add(firstJSONValue(in: normalized, keys: "book_year", "year"), named: "year", to: &state)
        add(firstJSONValue(in: normalized, keys: "capabilities"), named: "capabilities", to: &state)
        add(normalizedString(normalized["acquisition_candidate_id"]), named: "candidate_id", to: &state)
        add(normalizedString(normalized["source_url"]), named: "source_url", to: &state)
        add(normalizedString(normalized["cover_url"]), named: "cover_url", to: &state)
        add(normalizedString(normalized["source_kind"]), named: "source_kind", to: &state)
        add(selectedPath, named: "selected_path", to: &state)
        add(selectedPath, named: "local_path", to: &state)
        add(selectedProvider, named: "selected_provider", to: &state)
        add(query, named: "query", to: &state)
        return state
    }

    private static func makeVideoDiscoveryState(
        from state: [String: JSONValue]?
    ) -> [String: JSONValue]? {
        guard let state else { return nil }
        var normalized = [String: JSONValue]()
        for (key, value) in state {
            let trimmedKey = key.trimmingCharacters(in: .whitespacesAndNewlines)
            guard !trimmedKey.isEmpty else { continue }
            guard !trimmedKey.lowercased().contains("token") else { continue }
            guard let normalizedValue = AppleBookCreatePresentation.normalizedVideoDiscoveryState([trimmedKey: value])?[trimmedKey] else {
                continue
            }
            normalized[trimmedKey] = normalizedValue
        }
        guard normalized["provider"] != nil else {
            return nil
        }
        if normalized["media_kind"] == nil {
            normalized["media_kind"] = .string("video")
        }
        return normalized
    }

    private static func normalizedString(_ value: JSONValue?) -> String? {
        guard case let .string(raw)? = value else {
            return nil
        }
        let trimmed = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        return trimmed.isEmpty ? nil : trimmed
    }

    private static func firstString(in object: [String: JSONValue], keys: String...) -> String? {
        for key in keys {
            if let value = normalizedString(object[key]) {
                return value
            }
        }
        return nil
    }

    private static func firstJSONValue(in object: [String: JSONValue], keys: String...) -> JSONValue? {
        for key in keys {
            guard let value = object[key] else { continue }
            switch value {
            case let .string(text):
                let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
                if !trimmed.isEmpty {
                    return .string(trimmed)
                }
            case let .number(number):
                if number.isFinite {
                    return .number(number)
                }
            case .bool, .object, .array:
                return value
            case .null:
                continue
            }
        }
        return nil
    }

    private static func add(_ value: String?, named key: String, to object: inout [String: JSONValue]) {
        guard let trimmed = value?.trimmingCharacters(in: .whitespacesAndNewlines), !trimmed.isEmpty else {
            return
        }
        object[key] = .string(trimmed)
    }

    private static func add(_ value: JSONValue?, named key: String, to object: inout [String: JSONValue]) {
        guard let value else { return }
        object[key] = value
    }

    private static func addBookCover(_ value: String?, to object: inout [String: JSONValue]) {
        guard let trimmed = value?.trimmingCharacters(in: .whitespacesAndNewlines), !trimmed.isEmpty else {
            return
        }
        if trimmed.hasPrefix("http://") || trimmed.hasPrefix("https://") {
            object["cover_url"] = .string(trimmed)
        } else {
            object["book_cover_file"] = .string(trimmed)
        }
    }

    private static func add(_ value: Int?, named key: String, to object: inout [String: JSONValue]) {
        guard let value else { return }
        object[key] = .number(Double(value))
    }

    private static func add(_ value: Double?, named key: String, to object: inout [String: JSONValue]) {
        guard let value, value.isFinite else { return }
        object[key] = .number(value)
    }

    private static func templateName(primary: String?, fallback: String?, suffix: String) -> String {
        let source = primary?.trimmingCharacters(in: .whitespacesAndNewlines).nonEmptyValue
            ?? fallback?.trimmingCharacters(in: .whitespacesAndNewlines).nonEmptyValue
        guard let source else {
            return suffix
        }
        return "\(source) \(suffix)"
    }

    private static func jsonString(from object: [String: JSONValue]) -> String {
        guard let data = try? JSONEncoder().encode(object),
              let string = String(data: data, encoding: .utf8) else {
            return "{}"
        }
        return string
    }

    private static func formatDecimal(_ value: Double) -> String {
        guard value.isFinite else { return "" }
        let rounded = (value * 100).rounded() / 100
        if rounded.rounded() == rounded {
            return String(Int(rounded))
        }
        return String(format: "%.2f", rounded)
    }
}
