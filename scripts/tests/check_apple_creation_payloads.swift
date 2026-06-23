import Foundation

@main
struct AppleCreationPayloadCheck {
    static func main() throws {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys]
        let decoder = JSONDecoder()

        let optionsJSON = """
        {
          "sentence_bounds": {"min": 1, "max": 500, "default": 30},
          "defaults": {
            "topic": "",
            "book_name": "",
            "genre": "",
            "author": "Me",
            "input_language": "English",
            "output_language": "Arabic",
            "voice": "macOS-auto-male"
          },
          "pipeline_defaults": {
            "sentences_per_output_file": 10,
            "audio_mode": "4",
            "audio_bitrate_kbps": 96,
            "written_mode": "4",
            "selected_voice": "macOS-auto-male",
            "generate_audio": true,
            "output_html": false,
            "output_pdf": false,
            "include_transliteration": true,
            "translation_provider": "llm",
            "translation_batch_size": 10,
            "transliteration_mode": "default",
            "enable_lookup_cache": true,
            "lookup_cache_batch_size": 10,
            "tempo": 1.0
          },
          "generated_source_defaults": {
            "add_images": false,
            "image_prompt_pipeline": "prompt_plan",
            "image_style_template": "wireframe",
            "image_prompt_context_sentences": 0,
            "image_width": "256",
            "image_height": "256"
          },
          "supported_input_languages": ["English", "Arabic"],
          "supported_output_languages": ["English", "Arabic"],
          "supported_voices": ["gTTS", "macOS-auto-male", "piper-auto"]
        }
        """.data(using: .utf8)!
        let options = try decoder.decode(BookCreationOptionsResponse.self, from: optionsJSON)
        require(options.sentenceBounds.default == 30, "creation options should decode sentence default")
        require(options.defaults.outputLanguage == "Arabic", "creation options should decode output language")
        require(options.defaults.voice == "macOS-auto-male", "creation options should decode backend default voice")
        require(options.pipelineDefaults.audioMode == "4", "creation options should decode pipeline defaults")
        require(options.pipelineDefaults.selectedVoice == "macOS-auto-male", "creation options should decode pipeline voice")
        require(options.generatedSourceDefaults.imageStyleTemplate == "wireframe", "creation options should decode generated source defaults")
        let voiceOptions = AppleBookCreateVoiceOption.options(
            from: options.supportedVoices,
            selected: AppleBookCreateVoiceOption(backendValue: options.defaults.voice)
        )
        require(
            voiceOptions.map(\.backendValue).contains("macOS-auto-male"),
            "Apple Create voice picker should keep backend-supported macOS auto voices"
        )
        require(
            AppleBookCreateVoiceOption("Samantha - en_US - (Premium) female")?.label == "Samantha",
            "Apple Create voice labels should shorten macOS inventory identifiers"
        )
        require(
            AppleBookCreatePresentation.availableCreateModes(isTV: true) == [.generatedBook],
            "Apple TV Create mode list should remain playback-safe"
        )
        require(
            AppleBookCreatePresentation.availableCreateModes(isTV: false) == AppleCreateMode.allCases,
            "iPhone/iPad Create mode list should expose all native creation modes"
        )
        require(
            AppleBookCreatePresentation.deriveBaseOutputName("  My Book: Arabic/Slovak!  ") == "my-book-arabic-slovak",
            "Apple Create base output names should be filesystem-friendly"
        )
        require(
            AppleBookCreatePresentation.deriveBaseOutputName("   ") == "generated-book",
            "Apple Create base output names should keep the generated-book fallback"
        )
        require(
            AppleBookCreatePresentation.derivedBaseOutput(
                for: .generatedBook,
                topic: "Topic fallback",
                bookName: "",
                sourceBaseOutput: "ignored",
                subtitleSourcePath: "ignored",
                youtubeVideoPath: "ignored"
            ) == "topic-fallback",
            "Generated book output should derive from topic when title is blank"
        )
        require(
            AppleBookCreatePresentation.derivedBaseOutput(
                for: .narrateEbook,
                topic: "ignored",
                bookName: "ignored",
                sourceBaseOutput: "  apple/imported-book  ",
                subtitleSourcePath: "ignored",
                youtubeVideoPath: "ignored"
            ) == "apple/imported-book",
            "Narrate EPUB output should preserve the trimmed explicit output path"
        )
        require(
            AppleBookCreatePresentation.submitButtonPresentation(for: .youtubeDub, isSubmitting: false)
                == AppleCreateSubmitPresentation(title: "Create Dub", systemImage: "video"),
            "YouTube Dub submit button should keep its visible label and icon"
        )
        require(
            AppleBookCreatePresentation.submitButtonPresentation(for: .generatedBook, isSubmitting: true)
                == AppleCreateSubmitPresentation(title: "Submitting", systemImage: "hourglass"),
            "Submitting state should override mode-specific submit labels"
        )
        require(
            AppleBookCreatePresentation.subtitleModelLabel("") == "Backend default",
            "Empty subtitle model should display backend default"
        )
        require(
            AppleBookCreatePresentation.subtitleTransliterationModelLabel("") == "Use translation model",
            "Empty transliteration model should display translation-model fallback"
        )
        require(
            AppleBookCreatePresentation.availableSubtitleLlmModels(
                selected: " gpt-4.1-mini ",
                inventory: ["", "GPT-4.1-MINI", "gpt-4.1"]
            ) == ["gpt-4.1-mini", "gpt-4.1"],
            "Subtitle LLM options should keep selected first and de-duplicate inventory case-insensitively"
        )
        require(
            AppleBookCreatePresentation.availableSubtitleLlmModels(
                selected: " ",
                inventory: ["", "  "]
            ) == [""],
            "Subtitle LLM options should keep backend-default fallback when no model is known"
        )
        require(
            AppleBookCreatePresentation.availableSubtitleTransliterationModels(
                selected: " gpt-4.1 ",
                translationModel: "gpt-4.1-mini",
                inventory: ["GPT-4.1", "gpt-4.1-nano"]
            ) == ["", "gpt-4.1", "gpt-4.1-mini", "gpt-4.1-nano"],
            "Transliteration model options should include blank fallback, selected, translation model, and unique inventory"
        )
        require(
            AppleBookCreatePresentation.clampAssFontSize(4) == AppleSubtitleAssTypography.fontSizeRange.lowerBound,
            "ASS font size should clamp to lower bound"
        )
        require(
            AppleBookCreatePresentation.clampAssEmphasisScale(3.2) == AppleSubtitleAssTypography.emphasisScaleRange.upperBound,
            "ASS emphasis scale should clamp to upper bound"
        )
        require(
            AppleBookCreatePresentation.clampSubtitleTranslationBatchSize(0) == AppleSubtitleTuning.translationBatchSizeRange.lowerBound,
            "Subtitle translation batch size should clamp to lower bound"
        )
        require(
            AppleBookCreatePresentation.clampSubtitleWorkerCount(99) == AppleSubtitleTuning.workerCountRange.upperBound,
            "Subtitle worker count should clamp to upper bound"
        )
        require(
            AppleBookCreatePresentation.clampSubtitleBatchSize(999) == AppleSubtitleTuning.batchSizeRange.upperBound,
            "Subtitle render batch size should clamp to upper bound"
        )
        require(
            AppleBookCreatePresentation.formattedAssEmphasisScale(1.346)
                .replacingOccurrences(of: ",", with: ".") == "1.35",
            "ASS emphasis scale display should use two decimals"
        )
        require(
            AppleBookCreatePresentation.formattedYoutubeOriginalMixPercent(104.2) == "100%",
            "YouTube original mix display should clamp and format as percent"
        )
        require(
            AppleBookCreatePresentation.clampYoutubeFlushSentences(0) == 1,
            "YouTube flush interval should clamp to lower bound"
        )
        require(
            AppleBookCreatePresentation.normalizeYoutubeOffset("") == "",
            "Empty YouTube offset should stay empty"
        )
        require(
            AppleBookCreatePresentation.normalizeYoutubeOffset("45") == "45",
            "Bare numeric YouTube offset should remain seconds"
        )
        require(
            AppleBookCreatePresentation.normalizeYoutubeOffset("1:02") == "01:02",
            "YouTube offset should normalize MM:SS"
        )
        require(
            AppleBookCreatePresentation.normalizeYoutubeOffset("-1") == nil,
            "YouTube offset should reject negative seconds"
        )

        let input = PipelineInputPayload(
            inputFile: "books/demo.epub",
            baseOutputFile: "demo/sk",
            inputLanguage: "en",
            targetLanguages: ["sk"],
            sentencesPerOutputFile: 12,
            generateAudio: true,
            selectedVoice: "macOS-auto-male",
            bookMetadata: [
                "book_title": .string("Demo Book"),
                "chapter_count": .number(3),
                "indexed": .bool(true),
            ]
        )
        let pipeline = PipelineRequestPayload(
            environmentOverrides: ["BOOKS_DIR": .string("/runtime/books")],
            pipelineOverrides: ["tempo": .number(1.08)],
            inputs: input,
            correlationId: "apple-smoke"
        )
        let pipelineObject = try jsonObject(from: encoder.encode(pipeline))
        require(pipelineObject["environment_overrides"] != nil, "pipeline should encode environment_overrides")
        require(pipelineObject["pipeline_overrides"] != nil, "pipeline should encode pipeline_overrides")
        require(pipelineObject["correlation_id"] as? String == "apple-smoke", "pipeline should encode correlation_id")

        let encodedInputs = pipelineObject["inputs"] as? [String: Any]
        require(encodedInputs?["input_file"] as? String == "books/demo.epub", "pipeline inputs should encode input_file")
        require(encodedInputs?["target_languages"] as? [String] == ["sk"], "pipeline inputs should encode target_languages")
        require(encodedInputs?["sentences_per_output_file"] as? Int == 12, "pipeline inputs should encode sentence count")
        require(encodedInputs?["selected_voice"] as? String == "macOS-auto-male", "pipeline inputs should encode selected_voice")
        let metadata = encodedInputs?["book_metadata"] as? [String: Any]
        require(metadata?["book_title"] as? String == "Demo Book", "pipeline inputs should encode book_metadata")

        let narrateInput = PipelineInputPayload(
            inputFile: "ebooks/imports/demo.epub",
            baseOutputFile: "apple/demo-narration",
            inputLanguage: "English",
            targetLanguages: ["Arabic"],
            sentencesPerOutputFile: options.pipelineDefaults.sentencesPerOutputFile,
            generateAudio: options.pipelineDefaults.generateAudio,
            audioMode: options.pipelineDefaults.audioMode,
            audioBitrateKbps: options.pipelineDefaults.audioBitrateKbps,
            writtenMode: options.pipelineDefaults.writtenMode,
            selectedVoice: options.pipelineDefaults.selectedVoice,
            outputHtml: options.pipelineDefaults.outputHtml,
            outputPdf: options.pipelineDefaults.outputPdf,
            includeTransliteration: options.pipelineDefaults.includeTransliteration,
            translationProvider: options.pipelineDefaults.translationProvider,
            translationBatchSize: options.pipelineDefaults.translationBatchSize,
            transliterationMode: options.pipelineDefaults.transliterationMode,
            enableLookupCache: options.pipelineDefaults.enableLookupCache,
            lookupCacheBatchSize: options.pipelineDefaults.lookupCacheBatchSize,
            tempo: options.pipelineDefaults.tempo,
            bookMetadata: [
                "job_label": .string("apple/demo-narration"),
                "source": .string("apple"),
            ]
        )
        let narratePipeline = PipelineRequestPayload(
            inputs: narrateInput,
            correlationId: "apple-narrate-ebook"
        )
        let narrateObject = try jsonObject(from: encoder.encode(narratePipeline))
        require(
            narrateObject["correlation_id"] as? String == "apple-narrate-ebook",
            "narrate pipeline should encode correlation_id"
        )
        let narrateInputs = narrateObject["inputs"] as? [String: Any]
        require(
            narrateInputs?["input_file"] as? String == "ebooks/imports/demo.epub",
            "narrate pipeline should encode server EPUB path"
        )
        require(
            narrateInputs?["base_output_file"] as? String == "apple/demo-narration",
            "narrate pipeline should encode base output"
        )
        require(
            narrateInputs?["selected_voice"] as? String == "macOS-auto-male",
            "narrate pipeline should keep backend default voice"
        )
        require(
            narrateInputs?["enable_lookup_cache"] as? Bool == true,
            "narrate pipeline should keep backend lookup-cache default"
        )

        let book = BookGenerationJobSubmission(
            generator: BookGenerationRequest(
                topic: "Portable Apple clients",
                bookName: "Native Creation",
                genre: "technical",
                outputLanguage: "sk"
            ),
            pipeline: pipeline
        )
        let bookObject = try jsonObject(from: encoder.encode(book))
        let generator = bookObject["generator"] as? [String: Any]
        require(generator?["book_name"] as? String == "Native Creation", "book generator should encode book_name")
        require(generator?["num_sentences"] as? Int == 10, "book generator should keep default sentence count")
        require(bookObject["pipeline"] != nil, "book job should include pipeline payload")

        let youtube = YoutubeDubRequestPayload(
            videoPath: "incoming/demo.mp4",
            subtitlePath: "incoming/demo.srt",
            mediaMetadata: ["source": .string("apple")],
            sourceLanguage: "English",
            targetLanguage: "sk",
            voice: "gTTS",
            startTimeOffset: "00:45",
            endTimeOffset: "01:30",
            originalMixPercent: 5,
            flushSentences: 10,
            llmModel: "gpt-4.1-mini",
            translationProvider: "llm",
            translationBatchSize: 10,
            transliterationMode: "default",
            splitBatches: true,
            stitchBatches: true,
            includeTransliteration: true,
            targetHeight: 720,
            preserveAspectRatio: true,
            enableLookupCache: true
        )
        let youtubeObject = try jsonObject(from: encoder.encode(youtube))
        require(youtubeObject["video_path"] as? String == "incoming/demo.mp4", "youtube dub should encode video_path")
        require(youtubeObject["subtitle_path"] as? String == "incoming/demo.srt", "youtube dub should encode subtitle_path")
        require(youtubeObject["source_language"] as? String == "English", "youtube dub should encode source_language")
        require(youtubeObject["target_language"] as? String == "sk", "youtube dub should encode target_language")
        require(youtubeObject["voice"] as? String == "gTTS", "youtube dub should encode voice")
        require(youtubeObject["start_time_offset"] as? String == "00:45", "youtube dub should encode start_time_offset")
        require(youtubeObject["end_time_offset"] as? String == "01:30", "youtube dub should encode end_time_offset")
        require((youtubeObject["original_mix_percent"] as? NSNumber)?.doubleValue == 5, "youtube dub should encode original_mix_percent")
        require(youtubeObject["flush_sentences"] as? Int == 10, "youtube dub should encode flush_sentences")
        require(youtubeObject["translation_provider"] as? String == "llm", "youtube dub should encode translation_provider")
        require(youtubeObject["translation_batch_size"] as? Int == 10, "youtube dub should encode translation_batch_size")
        require(youtubeObject["split_batches"] as? Bool == true, "youtube dub should encode split_batches")
        require(youtubeObject["stitch_batches"] as? Bool == true, "youtube dub should encode stitch_batches")
        require(youtubeObject["include_transliteration"] as? Bool == true, "youtube dub should encode include_transliteration")
        require(youtubeObject["target_height"] as? Int == 720, "youtube dub should encode target_height")
        require(youtubeObject["preserve_aspect_ratio"] as? Bool == true, "youtube dub should encode preserve_aspect_ratio")
        require(youtubeObject["enable_lookup_cache"] as? Bool == true, "youtube dub should encode enable_lookup_cache")

        let subtitle = SubtitleJobFormPayload(
            inputLanguage: "en",
            targetLanguage: "sk",
            sourcePath: "incoming/demo.srt",
            translationBatchSize: 6,
            mediaMetadataJSON: #"{"title":"Demo"}"#
        )
        require(subtitle.multipartFields["input_language"] == "en", "subtitle form should include input_language")
        require(subtitle.multipartFields["target_language"] == "sk", "subtitle form should include target_language")
        require(subtitle.multipartFields["source_path"] == "incoming/demo.srt", "subtitle form should include source_path")
        require(subtitle.multipartFields["translation_batch_size"] == "6", "subtitle form should stringify translation_batch_size")
        require(subtitle.multipartFields["mirror_batches_to_source_dir"] == "true", "subtitle form should include mirror default")

        let appleSubtitle = SubtitleJobFormPayload(
            inputLanguage: "English",
            targetLanguage: "Arabic",
            sourcePath: "Subtitles/demo.srt",
            originalLanguage: "English",
            llmModel: "gpt-4.1-mini",
            translationProvider: "llm",
            transliterationMode: "default",
            transliterationModel: "gpt-4.1",
            enableTransliteration: true,
            highlight: true,
            showOriginal: true,
            generateAudioBook: true,
            batchSize: 20,
            translationBatchSize: 10,
            workerCount: 10,
            startTime: "00:00",
            endTime: "+02:00",
            assFontSize: 56,
            assEmphasisScale: 1.3,
            mediaMetadataJSON: #"{"source":"apple"}"#,
            mirrorBatchesToSourceDir: false,
            outputFormat: "ass"
        )
        require(
            appleSubtitle.multipartFields["source_path"] == "Subtitles/demo.srt",
            "Apple subtitle form should submit server subtitle path"
        )
        require(
            appleSubtitle.multipartFields["original_language"] == "English",
            "Apple subtitle form should include original_language"
        )
        require(
            appleSubtitle.multipartFields["output_format"] == "ass",
            "Apple subtitle form should keep ASS default"
        )
        require(
            appleSubtitle.multipartFields["llm_model"] == "gpt-4.1-mini",
            "Apple subtitle form should include selected LLM model"
        )
        require(
            appleSubtitle.multipartFields["translation_provider"] == "llm",
            "Apple subtitle form should include selected translation provider"
        )
        require(
            appleSubtitle.multipartFields["transliteration_mode"] == "default",
            "Apple subtitle form should include selected transliteration mode"
        )
        require(
            appleSubtitle.multipartFields["transliteration_model"] == "gpt-4.1",
            "Apple subtitle form should include selected transliteration model"
        )
        require(
            appleSubtitle.multipartFields["translation_batch_size"] == "10",
            "Apple subtitle form should include selected LLM batch size"
        )
        require(
            appleSubtitle.multipartFields["worker_count"] == "10",
            "Apple subtitle form should include selected worker count"
        )
        require(
            appleSubtitle.multipartFields["batch_size"] == "20",
            "Apple subtitle form should include selected subtitle batch size"
        )
        require(
            appleSubtitle.multipartFields["ass_font_size"] == "56",
            "Apple subtitle form should include ASS font size"
        )
        require(
            appleSubtitle.multipartFields["ass_emphasis_scale"] == "1.30",
            "Apple subtitle form should include ASS emphasis scale"
        )
        require(
            appleSubtitle.multipartFields["end_time"] == "+02:00",
            "Apple subtitle form should include relative end time"
        )
        require(
            appleSubtitle.multipartFields["media_metadata_json"] == #"{"source":"apple"}"#,
            "Apple subtitle form should mark Apple source metadata"
        )
        require(
            appleSubtitle.multipartFields["mirror_batches_to_source_dir"] == "false",
            "Apple subtitle form should include selected mirror-to-source setting"
        )

        let appleSubtitleUpload = SubtitleJobFormPayload(
            inputLanguage: "English",
            targetLanguage: "Arabic",
            sourcePath: nil,
            originalLanguage: "English",
            translationProvider: "googletrans",
            transliterationMode: "default",
            enableTransliteration: true,
            startTime: "00:00",
            mediaMetadataJSON: #"{"source":"apple"}"#,
            outputFormat: "ass"
        )
        require(
            appleSubtitleUpload.multipartFields["source_path"] == nil,
            "Apple subtitle upload form should omit source_path when using a local file"
        )
        require(
            appleSubtitleUpload.multipartFields["translation_provider"] == "googletrans",
            "Apple subtitle upload form should keep translation provider"
        )
        require(
            SubtitleTimecodeInput.normalize("1:02") == "01:02",
            "Subtitle timecode should normalize MM:SS"
        )
        require(
            SubtitleTimecodeInput.normalize("1:02:03") == "01:02:03",
            "Subtitle timecode should normalize HH:MM:SS"
        )
        require(
            SubtitleTimecodeInput.normalize("", emptyValue: "00:00") == "00:00",
            "Empty subtitle start time should use default"
        )
        require(
            SubtitleTimecodeInput.normalize("+5", allowRelative: true) == "+05:00",
            "Relative subtitle end time should treat bare values as minutes"
        )
        require(
            SubtitleTimecodeInput.normalize("+1:02:03", allowRelative: true) == "+01:02:03",
            "Relative subtitle end time should normalize HH:MM:SS offsets"
        )
        require(
            SubtitleTimecodeInput.normalize("1:70") == nil,
            "Subtitle timecode should reject invalid seconds"
        )
        require(
            SubtitleTimecodeInput.normalize("+bad", allowRelative: true) == nil,
            "Subtitle timecode should reject invalid relative offsets"
        )

        print("apple creation payload checks passed")
    }

    private static func jsonObject(from data: Data) throws -> [String: Any] {
        guard let object = try JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            throw CheckFailure("Encoded payload was not a JSON object")
        }
        return object
    }

    private static func require(_ condition: Bool, _ message: String) {
        if !condition {
            fputs("check failed: \(message)\n", stderr)
            exit(1)
        }
    }
}

private struct CheckFailure: Error, CustomStringConvertible {
    let description: String

    init(_ description: String) {
        self.description = description
    }
}
