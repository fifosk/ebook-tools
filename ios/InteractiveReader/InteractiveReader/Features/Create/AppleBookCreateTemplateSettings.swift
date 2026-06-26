import Foundation

struct AppleBookCreateTemplateDiscoveryApplication: Equatable {
    let shouldUseDiscoverySourcePanel: Bool?
    let bookMetadataExtras: [String: JSONValue]?
}

struct AppleBookCreateTemplateBookMetadataApplication: Equatable {
    let title: String?
    let author: String?
    let genre: String?
    let summary: String?
    let year: String?
    let isbn: String?
    let coverFile: String?
}

struct AppleBookCreateTemplateSourceBookContextApplication: Equatable {
    let title: String?
    let author: String?
    let genre: String?
    let summary: String?
}

struct AppleBookCreateTemplateLanguageApplication: Equatable {
    let inputLanguage: AppleBookCreateLanguage?
    let targetLanguages: [AppleBookCreateLanguage]
}

struct AppleBookCreateTemplateVoiceApplication: Equatable {
    let voice: AppleBookCreateVoiceOption?
    let overrides: [String: String]?
}

struct AppleBookCreateTemplateAudioApplication: Equatable {
    let generateAudio: Bool?
    let audioMode: String?
    let audioBitrateKbps: String?
    let writtenMode: String?
    let tempo: Double?
    let stitchFull: Bool?
    let includeTransliteration: Bool?
}

struct AppleBookCreateTemplateBookTranslationApplication: Equatable {
    let provider: AppleSubtitleTranslationProvider?
    let llmModel: String?
    let translationBatchSize: Int?
    let transliterationMode: AppleSubtitleTransliterationMode?
    let transliterationModel: String?
    let enableLookupCache: Bool?
    let lookupCacheBatchSize: Int?
}

struct AppleBookCreateTemplateOutputApplication: Equatable {
    let outputHtml: Bool?
    let outputPdf: Bool?
}

struct AppleBookCreateTemplateImageApplication: Equatable {
    let includeImages: Bool?
    let promptPipeline: AppleGeneratedBookImagePromptPipeline?
    let styleTemplate: AppleGeneratedBookImageStyleTemplate?
    let promptBatchingEnabled: Bool?
    let promptBatchSize: Int?
    let promptPlanBatchSize: Int?
    let promptContextSentences: Int?
    let width: String?
    let height: String?
    let steps: String?
    let cfgScale: String?
    let samplerName: String?
    let seedWithPreviousImage: Bool?
    let blankDetectionEnabled: Bool?
    let apiBaseURLs: [String]
    let apiTimeoutSeconds: String?
}

struct AppleBookCreateTemplateWorkerApplication: Equatable {
    let threadCount: String?
    let queueSize: String?
    let jobMaxWorkers: String?
    let imageConcurrency: String?
}

enum AppleBookCreateTemplateSettings {
    static func mode(for template: CreationTemplateEntry) -> AppleCreateMode? {
        switch template.normalizedMode {
        case "generated_book":
            return .generatedBook
        case "narrate_ebook":
            return .narrateEbook
        case "subtitle_job":
            return .subtitleJob
        case "youtube_dub":
            return .youtubeDub
        default:
            return nil
        }
    }

    static func compatibleTemplates(
        from templates: [CreationTemplateEntry],
        for mode: AppleCreateMode
    ) -> [CreationTemplateEntry] {
        templates.filter { template in
            self.mode(for: template) == mode
        }
    }

    static func selectedCompatibleTemplateID(
        _ selectedTemplateID: String,
        from templates: [CreationTemplateEntry],
        for mode: AppleCreateMode
    ) -> String? {
        let selectedID = selectedTemplateID.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !selectedID.isEmpty else {
            return nil
        }
        return compatibleTemplates(from: templates, for: mode)
            .first { $0.id == selectedID }?
            .id
    }

    static func selectedTemplatePickerValue(
        _ selectedTemplateID: String,
        from templates: [CreationTemplateEntry],
        for mode: AppleCreateMode
    ) -> String {
        selectedCompatibleTemplateID(selectedTemplateID, from: templates, for: mode) ?? ""
    }

    static func resolvedTemplateSelection(
        _ selectedTemplateID: String,
        from templates: [CreationTemplateEntry],
        for mode: AppleCreateMode
    ) -> String {
        selectedCompatibleTemplateID(selectedTemplateID, from: templates, for: mode)
            ?? compatibleTemplates(from: templates, for: mode).first?.id
            ?? ""
    }

    static func metadataObject(from formState: [String: JSONValue]) -> [String: JSONValue]? {
        object(from: formState["media_metadata"])
            ?? object(from: formState["media_metadata_json"])
            ?? object(from: formState["youtube_metadata"])
            ?? object(from: formState["book_metadata"])
    }

    static func bookMetadataApplication(
        from formState: [String: JSONValue]
    ) -> AppleBookCreateTemplateBookMetadataApplication? {
        guard let metadata = object(from: formState["book_metadata"]) else {
            return nil
        }

        return AppleBookCreateTemplateBookMetadataApplication(
            title: string(metadata, "book_title") ?? string(metadata, "title"),
            author: string(metadata, "book_author") ?? string(metadata, "author"),
            genre: string(metadata, "book_genre") ?? string(metadata, "genre"),
            summary: string(metadata, "book_summary") ?? string(metadata, "summary"),
            year: string(metadata, "book_year") ?? string(metadata, "year"),
            isbn: string(metadata, "book_isbn") ?? string(metadata, "isbn"),
            coverFile: string(metadata, "book_cover_file") ?? string(metadata, "cover_file")
        )
    }

    static func sourceBookContextApplication(
        from formState: [String: JSONValue]
    ) -> AppleBookCreateTemplateSourceBookContextApplication {
        AppleBookCreateTemplateSourceBookContextApplication(
            title: string(formState, "source_book_title"),
            author: string(formState, "source_book_author"),
            genre: string(formState, "source_book_genre"),
            summary: string(formState, "source_book_summary")
        )
    }

    static func languageApplication(
        from formState: [String: JSONValue]
    ) -> AppleBookCreateTemplateLanguageApplication {
        AppleBookCreateTemplateLanguageApplication(
            inputLanguage: string(formState, "input_language")
                .flatMap(AppleBookCreateLanguage.init(backendValue:)),
            targetLanguages: stringArray(formState, "target_languages")
                .compactMap(AppleBookCreateLanguage.init(backendValue:))
        )
    }

    static func voiceApplication(
        from formState: [String: JSONValue]
    ) -> AppleBookCreateTemplateVoiceApplication {
        AppleBookCreateTemplateVoiceApplication(
            voice: string(formState, "selected_voice")
                .flatMap(AppleBookCreateVoiceOption.init(backendValue:)),
            overrides: stringDictionary(from: formState["voice_overrides"])
        )
    }

    static func audioApplication(
        from formState: [String: JSONValue]
    ) -> AppleBookCreateTemplateAudioApplication {
        AppleBookCreateTemplateAudioApplication(
            generateAudio: bool(formState, "generate_audio"),
            audioMode: string(formState, "audio_mode"),
            audioBitrateKbps: string(formState, "audio_bitrate_kbps"),
            writtenMode: string(formState, "written_mode"),
            tempo: double(formState, "tempo"),
            stitchFull: bool(formState, "stitch_full"),
            includeTransliteration: bool(formState, "include_transliteration")
        )
    }

    static func bookTranslationApplication(
        from formState: [String: JSONValue]
    ) -> AppleBookCreateTemplateBookTranslationApplication {
        AppleBookCreateTemplateBookTranslationApplication(
            provider: string(formState, "translation_provider")
                .flatMap(AppleSubtitleTranslationProvider.init(backendValue:)),
            llmModel: string(formState, "ollama_model"),
            translationBatchSize: int(formState, "translation_batch_size"),
            transliterationMode: string(formState, "transliteration_mode")
                .flatMap(AppleSubtitleTransliterationMode.init(backendValue:)),
            transliterationModel: string(formState, "transliteration_model"),
            enableLookupCache: bool(formState, "enable_lookup_cache"),
            lookupCacheBatchSize: int(formState, "lookup_cache_batch_size")
        )
    }

    static func outputApplication(
        from formState: [String: JSONValue]
    ) -> AppleBookCreateTemplateOutputApplication {
        AppleBookCreateTemplateOutputApplication(
            outputHtml: bool(formState, "output_html"),
            outputPdf: bool(formState, "output_pdf")
        )
    }

    static func imageApplication(
        from formState: [String: JSONValue]
    ) -> AppleBookCreateTemplateImageApplication {
        AppleBookCreateTemplateImageApplication(
            includeImages: bool(formState, "add_images"),
            promptPipeline: string(formState, "image_prompt_pipeline")
                .flatMap(AppleGeneratedBookImagePromptPipeline.init(backendValue:)),
            styleTemplate: string(formState, "image_style_template")
                .flatMap(AppleGeneratedBookImageStyleTemplate.init(backendValue:)),
            promptBatchingEnabled: bool(formState, "image_prompt_batching_enabled"),
            promptBatchSize: int(formState, "image_prompt_batch_size"),
            promptPlanBatchSize: int(formState, "image_prompt_plan_batch_size"),
            promptContextSentences: int(formState, "image_prompt_context_sentences"),
            width: string(formState, "image_width"),
            height: string(formState, "image_height"),
            steps: string(formState, "image_steps"),
            cfgScale: string(formState, "image_cfg_scale"),
            samplerName: string(formState, "image_sampler_name"),
            seedWithPreviousImage: bool(formState, "image_seed_with_previous_image"),
            blankDetectionEnabled: bool(formState, "image_blank_detection_enabled"),
            apiBaseURLs: stringArray(formState, "image_api_base_urls"),
            apiTimeoutSeconds: string(formState, "image_api_timeout_seconds")
        )
    }

    static func workerApplication(
        from formState: [String: JSONValue]
    ) -> AppleBookCreateTemplateWorkerApplication {
        AppleBookCreateTemplateWorkerApplication(
            threadCount: string(formState, "thread_count"),
            queueSize: string(formState, "queue_size"),
            jobMaxWorkers: string(formState, "job_max_workers"),
            imageConcurrency: string(formState, "image_concurrency")
        )
    }

    static func formState(from template: CreationTemplateEntry) -> [String: JSONValue]? {
        template.payload["form_state"]?.objectValue
            ?? template.payload["formState"]?.objectValue
            ?? template.payload["payload"]?.objectValue?["form_state"]?.objectValue
    }

    static func settings(from template: CreationTemplateEntry) -> [String: JSONValue]? {
        formState(from: template) ?? template.payload
    }

    static func discoveryState(from template: CreationTemplateEntry) -> [String: JSONValue]? {
        object(from: template.payload["discovery_state"])
            ?? object(from: template.payload["discoveryState"])
            ?? object(from: template.payload["payload"]?.objectValue?["discovery_state"])
            ?? object(from: template.payload["payload"]?.objectValue?["discoveryState"])
    }

    static func discoveryApplication(
        from template: CreationTemplateEntry,
        formState: [String: JSONValue],
        mode: AppleCreateMode
    ) -> AppleBookCreateTemplateDiscoveryApplication {
        guard let discoveryState = discoveryState(from: template),
              let provider = string(discoveryState, "provider") else {
            return AppleBookCreateTemplateDiscoveryApplication(
                shouldUseDiscoverySourcePanel: mode == .narrateEbook ? false : nil,
                bookMetadataExtras: nil
            )
        }

        var extras = object(from: formState["book_metadata"]) ?? [:]
        extras["acquisition_provider"] = .string(provider)
        if let value = string(discoveryState, "candidate_id") {
            extras["acquisition_candidate_id"] = .string(value)
        }
        if let value = string(discoveryState, "source_url") {
            extras["source_url"] = .string(value)
        }
        if let value = string(discoveryState, "cover_url") {
            extras["cover_url"] = .string(value)
        }
        if let value = string(discoveryState, "source_kind") {
            extras["source_kind"] = .string(value)
        } else if extras["source_kind"] == nil {
            extras["source_kind"] = .string(provider)
        }

        return AppleBookCreateTemplateDiscoveryApplication(
            shouldUseDiscoverySourcePanel: mode == .narrateEbook ? true : nil,
            bookMetadataExtras: AppleBookCreatePresentation.normalizedBookMetadataExtras(extras)
        )
    }

    static func youtubeVideoPath(
        formState: [String: JSONValue],
        discoveryState: [String: JSONValue]?
    ) -> String? {
        string(formState, "video_path")
            ?? string(discoveryState ?? [:], "selected_video_path")
            ?? string(discoveryState ?? [:], "local_path")
    }

    static func subtitleSourcePath(formState: [String: JSONValue]) -> String? {
        string(formState, "source_path") ?? string(formState, "subtitle_path")
    }

    static func youtubeSubtitlePath(
        formState: [String: JSONValue],
        discoveryState: [String: JSONValue]?
    ) -> String? {
        string(formState, "subtitle_path")
            ?? string(discoveryState ?? [:], "selected_subtitle_path")
    }

    static func object(from value: JSONValue?) -> [String: JSONValue]? {
        guard let value else { return nil }
        if let object = value.objectValue {
            return object
        }
        guard case let .string(text) = value,
              let data = text.data(using: .utf8),
              let object = try? JSONDecoder().decode([String: JSONValue].self, from: data) else {
            return nil
        }
        return object
    }

    static func stringDictionary(from value: JSONValue?) -> [String: String]? {
        guard let object = object(from: value) else {
            return nil
        }
        return object.reduce(into: [String: String]()) { result, element in
            if let value = element.value.stringValue {
                result[element.key] = value
            }
        }
    }

    static func string(_ object: [String: JSONValue], _ key: String) -> String? {
        object[key]?.stringValue?.trimmingCharacters(in: .whitespacesAndNewlines).nonEmptyValue
    }

    static func stringArray(_ object: [String: JSONValue], _ key: String) -> [String] {
        guard let value = object[key] else { return [] }
        if let array = value.arrayValue {
            return array.compactMap { $0.stringValue?.trimmingCharacters(in: .whitespacesAndNewlines).nonEmptyValue }
        }
        return value.stringValue?
            .split(separator: ",")
            .compactMap { String($0).trimmingCharacters(in: .whitespacesAndNewlines).nonEmptyValue } ?? []
    }

    static func int(_ object: [String: JSONValue], _ key: String) -> Int? {
        object[key]?.intValue
    }

    static func double(_ object: [String: JSONValue], _ key: String) -> Double? {
        switch object[key] {
        case let .number(value):
            return value.isFinite ? value : nil
        case let .string(value):
            return Double(value.trimmingCharacters(in: .whitespacesAndNewlines))
        case let .bool(value):
            return value ? 1 : 0
        default:
            return nil
        }
    }

    static func bool(_ object: [String: JSONValue], _ key: String) -> Bool? {
        switch object[key] {
        case let .bool(value):
            return value
        case let .number(value):
            return value != 0
        case let .string(value):
            switch value.trimmingCharacters(in: .whitespacesAndNewlines).lowercased() {
            case "1", "true", "yes", "on":
                return true
            case "0", "false", "no", "off":
                return false
            default:
                return nil
            }
        default:
            return nil
        }
    }

    static func endSentenceText(from value: JSONValue?) -> String? {
        switch value {
        case .null, nil:
            return ""
        default:
            return value?.stringValue?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        }
    }
}
