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
            "stitch_full": true,
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
            AppleBookCreatePresentation.availableCreateModes(isTV: true).isEmpty,
            "Apple TV Create mode list should stay empty and playback-safe"
        )
        require(
            AppleBookCreatePresentation.availableCreateModes(isTV: false) == AppleCreateMode.allCases,
            "iPhone/iPad Create mode list should expose all native creation modes"
        )
        let pipelineFilesJSON = """
        {
          "ebooks": [
            {"name": "Older.epub", "path": "z-older.epub", "type": "file", "modified_at": "2026-06-23T12:00:00Z"},
            {"name": "Folder", "path": "folder", "type": "directory", "modified_at": "2026-06-25T12:00:00Z"},
            {"name": "Newest.epub", "path": "a-newest.epub", "type": "file", "modified_at": "2026-06-24T12:00:00Z"}
          ],
          "outputs": [
            {"name": "generated", "path": "generated", "type": "directory"}
          ],
          "books_root": "/Volumes/Data/Books",
          "output_root": "/Volumes/Data/Output"
        }
        """.data(using: .utf8)!
        let pipelineFiles = try decoder.decode(PipelineFileBrowserResponse.self, from: pipelineFilesJSON)
        require(
            pipelineFiles.booksRoot == "/Volumes/Data/Books",
            "Apple Create should decode pipeline file browser roots"
        )
        require(
            AppleBookCreatePresentation.preferredPipelineEbook(from: pipelineFiles)?.path == "a-newest.epub",
            "Apple Create should prefer the latest modified backend-visible EPUB when auto-filling Narrate EPUB"
        )
        require(
            AppleBookCreatePresentation.preferredPipelineEbook(
                from: PipelineFileBrowserResponse(
                    ebooks: [
                        PipelineFileEntry(
                            name: "Z.epub",
                            path: "Z.epub",
                            type: "file",
                            modifiedAt: "2026-06-24T12:00:00Z"
                        ),
                        PipelineFileEntry(
                            name: "A.epub",
                            path: "A.epub",
                            type: "file",
                            modifiedAt: "2026-06-24T12:00:00Z"
                        ),
                    ],
                    outputs: [],
                    booksRoot: "/books",
                    outputRoot: "/output"
                )
            )?.path == "A.epub",
            "Apple Create should break same-time EPUB preference ties by path"
        )
        let subtitleSourcesJSON = """
        {
          "sources": [
            {
              "name": "older.srt",
              "path": "/subtitles/older.srt",
              "format": "srt",
              "language": "en",
              "modified_at": "2026-06-23T10:00:00Z"
            },
            {
              "name": "newer.ass",
              "path": "/subtitles/newer.ass",
              "format": "ass",
              "language": "en",
              "modified_at": "2026-06-23T12:00:00Z"
            },
            {
              "name": "latest.vtt",
              "path": "/subtitles/latest.vtt",
              "format": "vtt",
              "language": "en",
              "modified_at": "2026-06-23T11:00:00Z"
            }
          ]
        }
        """.data(using: .utf8)!
        let subtitleSources = try decoder.decode(SubtitleSourceListResponse.self, from: subtitleSourcesJSON)
        require(
            subtitleSources.sources.first?.modifiedAt == "2026-06-23T10:00:00Z",
            "Apple Create should decode subtitle source modified_at timestamps"
        )
        require(
            AppleBookCreatePresentation.preferredSubtitleSource(from: subtitleSources)?.path == "/subtitles/latest.vtt",
            "Apple Create should prefer the latest usable SRT/VTT subtitle source and ignore ASS for subtitle jobs"
        )
        let youtubeVideoA = YoutubeNasVideoEntry(
            path: "/nas/video-a.mp4",
            filename: "video-a.mp4",
            folder: "/nas",
            sizeBytes: 120,
            modifiedAt: "2026-06-23T10:00:00Z",
            source: nil,
            linkedJobIds: [],
            subtitles: [
                YoutubeNasSubtitleEntry(
                    path: "/nas/video-a.en.srt",
                    filename: "video-a.en.srt",
                    language: "en",
                    format: "srt"
                )
            ]
        )
        let youtubeVideoB = YoutubeNasVideoEntry(
            path: "/nas/video-b.mp4",
            filename: "video-b.mp4",
            folder: "/nas",
            sizeBytes: 140,
            modifiedAt: "2026-06-23T11:00:00Z",
            source: nil,
            linkedJobIds: [],
            subtitles: [
                YoutubeNasSubtitleEntry(
                    path: "/nas/video-b.sk.vtt",
                    filename: "video-b.sk.vtt",
                    language: "sk",
                    format: "vtt"
                ),
                YoutubeNasSubtitleEntry(
                    path: "/nas/video-b.en.ass",
                    filename: "video-b.en.ass",
                    language: "en",
                    format: "ass"
                )
            ]
        )
        let youtubeLibrary = YoutubeNasLibraryResponse(baseDir: "/nas", videos: [youtubeVideoA, youtubeVideoB])
        let restoredYoutubeSelection = AppleBookCreatePresentation.youtubeSelection(
            from: youtubeLibrary,
            storedVideoPath: " /nas/video-b.mp4 ",
            storedSubtitlePath: " /nas/video-b.sk.vtt "
        )
        require(
            restoredYoutubeSelection?.video.path == "/nas/video-b.mp4"
                && restoredYoutubeSelection?.subtitle?.path == "/nas/video-b.sk.vtt",
            "Apple Create should restore the last valid NAS video/subtitle selection for YouTube dubbing"
        )
        let staleYoutubeSelection = AppleBookCreatePresentation.youtubeSelection(
            from: youtubeLibrary,
            storedVideoPath: "/nas/missing.mp4",
            storedSubtitlePath: "/nas/video-b.sk.vtt"
        )
        require(
            staleYoutubeSelection?.video.path == "/nas/video-a.mp4"
                && staleYoutubeSelection?.subtitle?.path == "/nas/video-a.en.srt",
            "Apple Create should fall back to the preferred NAS video when the stored YouTube source is stale"
        )
        require(
            AppleBookCreatePresentation.youtubeLibraryCacheKey(
                baseKey: "https://api.example.test|editor|editor",
                baseDir: "  "
            ) == "https://api.example.test|editor|editor",
            "Apple Create should use the default YouTube NAS library cache key when no base directory is selected"
        )
        require(
            AppleBookCreatePresentation.youtubeLibraryCacheKey(
                baseKey: "https://api.example.test|editor|editor",
                baseDir: " /Volumes/Data/Download/DStation "
            ) == "https://api.example.test|editor|editor|youtubeBaseDir=/Volumes/Data/Download/DStation",
            "Apple Create should include the selected NAS base directory in YouTube library cache identity"
        )
        let inlineSubtitleStreamsJSON = """
        {
          "video_path": "/nas/video-b.mp4",
          "streams": [
            {
              "index": 3,
              "position": 0,
              "language": "es",
              "codec": "dvd_subtitle",
              "title": "Spanish bitmap",
              "can_extract": false
            },
            {
              "index": 4,
              "position": 1,
              "language": "en",
              "codec": "subrip",
              "title": "English CC",
              "can_extract": true
            }
          ]
        }
        """.data(using: .utf8)!
        let inlineStreams = try decoder.decode(YoutubeInlineSubtitleListResponse.self, from: inlineSubtitleStreamsJSON)
        require(
            inlineStreams.videoPath == "/nas/video-b.mp4"
                && inlineStreams.streams[0].canExtract == false
                && inlineStreams.streams[1].canExtract == true,
            "Apple Create should decode YouTube inline subtitle stream inventory"
        )
        require(
            AppleBookCreatePresentation.defaultYoutubeInlineSubtitleLanguages(from: inlineStreams.streams) == ["en"],
            "Apple Create should default embedded subtitle extraction to English text streams"
        )
        require(
            AppleBookCreatePresentation.normalizedYoutubeInlineSubtitleLanguages(" en, sk\nEN ") == ["en", "sk"],
            "Apple Create should normalize and de-duplicate embedded subtitle extraction language filters"
        )
        require(
            AppleBookCreatePresentation.youtubeInlineSubtitleStreamLabel(inlineStreams.streams[1])
                == "Text subtitle stream 4 · en · subrip · English CC",
            "Apple Create should label embedded subtitle streams with extractability and metadata"
        )
        let extractionJSON = """
        {
          "video_path": "/nas/video-b.mp4",
          "extracted": [
            {
              "path": "/nas/video-b.en.srt",
              "filename": "video-b.en.srt",
              "language": "en",
              "format": "srt"
            }
          ]
        }
        """.data(using: .utf8)!
        let extraction = try decoder.decode(YoutubeSubtitleExtractionResponse.self, from: extractionJSON)
        require(
            extraction.extracted.first?.path == "/nas/video-b.en.srt",
            "Apple Create should decode extracted YouTube subtitle paths"
        )
        let extractionPayload = YoutubeSubtitleExtractionRequestPayload(
            videoPath: "/nas/video-b.mp4",
            languages: ["en"]
        )
        let extractionPayloadJSON = String(data: try encoder.encode(extractionPayload), encoding: .utf8) ?? ""
        let extractionPayloadObject = try JSONSerialization.jsonObject(
            with: Data(extractionPayloadJSON.utf8)
        ) as? [String: Any]
        require(
            extractionPayloadObject?["video_path"] as? String == "/nas/video-b.mp4"
                && (extractionPayloadObject?["languages"] as? [String]) == ["en"],
            "Apple Create should encode YouTube subtitle extraction requests using Web route keys"
        )
        require(
            AppleBookCreatePresentation.subtitleShowOriginalPreferenceKey(
                baseKey: "https://api.example.test|editor|editor"
            ) == "ebookTools.appleCreate.subtitles.showOriginal.https://api.example.test|editor|editor",
            "Apple Create should scope the subtitle show-original preference to the current API/user"
        )
        let narrationJobsJSON = """
        {
          "jobs": [
            {
              "jobId": "subtitle-1",
              "jobType": "subtitle",
              "status": "completed",
              "createdAt": "2026-06-23T10:00:00Z",
              "startedAt": null,
              "completedAt": null,
              "result": null,
              "error": null,
              "latestEvent": null,
              "tuning": null,
              "userId": "editor",
              "userRole": "editor",
              "generatedFiles": null,
              "parameters": {
                "input_file": "ignore-me.srt",
                "end_sentence": 999
              },
              "mediaCompleted": true,
              "retrySummary": null,
              "jobLabel": null,
              "imageGeneration": null
            },
            {
              "jobId": "book-old",
              "jobType": "book",
              "status": "completed",
              "createdAt": "2026-06-23T11:00:00Z",
              "startedAt": null,
              "completedAt": null,
              "result": null,
              "error": null,
              "latestEvent": null,
              "tuning": null,
              "userId": "editor",
              "userRole": "editor",
              "generatedFiles": null,
              "parameters": {
                "input_file": "old.epub",
                "base_output_file": "old-output",
                "target_languages": ["French"],
                "start_sentence": 20
              },
              "mediaCompleted": true,
              "retrySummary": null,
              "jobLabel": null,
              "imageGeneration": null
            },
            {
              "jobId": "book-new",
              "jobType": "book",
              "status": "completed",
              "createdAt": "2026-06-23T12:00:00Z",
              "startedAt": null,
              "completedAt": null,
              "result": null,
              "error": null,
              "latestEvent": null,
              "tuning": null,
              "userId": "editor",
              "userRole": "editor",
              "generatedFiles": null,
              "parameters": {
                "inputs": {
                  "input_file": "latest.epub",
                  "base_output_file": "latest-output",
                  "input_language": "English",
                  "target_languages": ["Arabic", "German", "French"],
                  "end_sentence": 88,
                  "enable_lookup_cache": false
                }
              },
              "mediaCompleted": true,
              "retrySummary": null,
              "jobLabel": null,
              "imageGeneration": null
            }
          ]
        }
        """.data(using: .utf8)!
        let narrationJobs = try decoder.decode(PipelineJobListResponse.self, from: narrationJobsJSON).jobs
        let narrationDefaults = AppleBookCreatePresentation.narrationHistoryDefaults(
            from: narrationJobs,
            currentInputFile: ""
        )
        require(
            narrationDefaults?.inputFile == "latest.epub"
                && narrationDefaults?.baseOutput == "latest-output"
                && narrationDefaults?.startSentence == 83,
            "Apple Create should use the latest narration job input/base and resume near its prior end sentence"
        )
        require(
            narrationDefaults?.inputLanguage == .english
                && narrationDefaults?.targetLanguage == .arabic
                && narrationDefaults?.additionalTargetLanguages == "German, French"
                && narrationDefaults?.enableLookupCache == false,
            "Apple Create should reuse latest narration language and lookup-cache defaults"
        )
        let createHistoryJSON = """
        {
          "jobs": [
            {
              "jobId": "generated-book-latest",
              "jobType": "book",
              "status": "completed",
              "createdAt": "2026-06-23T15:00:00Z",
              "startedAt": null,
              "completedAt": null,
              "result": null,
              "error": null,
              "latestEvent": null,
              "tuning": null,
              "userId": "editor",
              "userRole": "editor",
              "generatedFiles": null,
              "parameters": {
                "book_generation": {
                  "topic": "Portable Apple clients",
                  "book_name": "Native Creation",
                  "genre": "technical",
                  "author": "Codex",
                  "num_sentences": 42,
                  "input_language": "English",
                  "output_language": "Slovak",
                  "voice": "macOS-auto-male"
                },
                "inputs": {
                  "input_language": "English",
                  "target_languages": ["Slovak", "German", "Arabic"],
                  "selected_voice": "macOS-auto-male",
                  "generate_audio": false,
                  "audio_mode": "2",
                  "audio_bitrate_kbps": 31,
                  "written_mode": "3",
                  "tempo": 2.9,
                  "sentences_per_output_file": 0,
                  "stitch_full": true,
                  "include_transliteration": true,
                  "translation_provider": "googletrans",
                  "translation_batch_size": 0,
                  "transliteration_mode": "python",
                  "transliteration_model": "gpt-4.1",
                  "enable_lookup_cache": false,
                  "lookup_cache_batch_size": 99,
                  "output_html": true,
                  "output_pdf": true,
                  "add_images": true
                },
                "pipeline_overrides": {
                  "llm_model": "gpt-4.1-mini",
                  "image_prompt_pipeline": "visual_canon",
                  "image_style_template": "children_book",
                  "image_prompt_context_sentences": 99,
                  "image_width": "63.9",
                  "image_height": "1024.8"
                }
              },
              "mediaCompleted": true,
              "retrySummary": null,
              "jobLabel": null,
              "imageGeneration": null
            },
            {
              "jobId": "subtitle-latest",
              "jobType": "subtitle",
              "status": "completed",
              "createdAt": "2026-06-23T13:00:00Z",
              "startedAt": null,
              "completedAt": null,
              "result": null,
              "error": null,
              "latestEvent": null,
              "tuning": null,
              "userId": "editor",
              "userRole": "editor",
              "generatedFiles": null,
              "parameters": {
                "subtitle_path": "/subtitles/latest.ass",
                "input_language": "English",
                "target_languages": ["German"],
                "start_time_offset_seconds": 75,
                "end_time_offset_seconds": 3723,
                "enable_transliteration": false,
                "show_original": false,
                "translation_provider": "googletrans",
                "llm_model": " qwen2.5:7b ",
                "transliteration_mode": "python",
                "transliteration_model": "ignored",
                "worker_count": 99,
                "batch_size": 0,
                "translation_batch_size": 80
              },
              "mediaCompleted": true,
              "retrySummary": null,
              "jobLabel": null,
              "imageGeneration": null
            },
            {
              "jobId": "youtube-latest",
              "jobType": "youtube_dub",
              "status": "completed",
              "createdAt": "2026-06-23T14:00:00Z",
              "startedAt": null,
              "completedAt": null,
              "result": null,
              "error": null,
              "latestEvent": null,
              "tuning": null,
              "userId": "editor",
              "userRole": "editor",
              "generatedFiles": null,
              "parameters": {
                "request": {
                  "inputs": {
                    "input_file": "/nas/videos/demo.mp4",
                    "subtitle_path": "/nas/videos/demo.en.ass",
                    "target_languages": ["Slovak"],
                    "selected_voice": "piper-auto",
                    "start_time_offset_seconds": 45,
                    "end_time_offset_seconds": 90,
                    "original_mix_percent": 104,
                    "flush_sentences": 0,
                    "translation_provider": "llm",
                    "llm_model": "gpt-4.1-mini",
                    "translation_batch_size": 80,
                    "transliteration_mode": "default",
                    "transliteration_model": "gpt-4.1",
                    "split_batches": false,
                    "stitch_batches": true,
                    "include_transliteration": false,
                    "target_height": 720,
                    "preserve_aspect_ratio": false,
                    "enable_lookup_cache": false
                  }
                }
              },
              "mediaCompleted": true,
              "retrySummary": null,
              "jobLabel": null,
              "imageGeneration": null
            }
          ]
        }
        """.data(using: .utf8)!
        let createHistoryJobs = try decoder.decode(PipelineJobListResponse.self, from: createHistoryJSON).jobs
        let generatedBookHistoryDefaults = AppleBookCreatePresentation.generatedBookHistoryDefaults(
            from: createHistoryJobs
        )
        require(
            generatedBookHistoryDefaults?.topic == "Portable Apple clients"
                && generatedBookHistoryDefaults?.bookName == "Native Creation"
                && generatedBookHistoryDefaults?.genre == "technical"
                && generatedBookHistoryDefaults?.author == "Codex"
                && generatedBookHistoryDefaults?.sentenceCount == 42,
            "Apple Create should reuse latest generated-book prompt defaults"
        )
        require(
            generatedBookHistoryDefaults?.inputLanguage == .english
                && generatedBookHistoryDefaults?.targetLanguage == .slovak
                && generatedBookHistoryDefaults?.additionalTargetLanguages == "German, Arabic"
                && generatedBookHistoryDefaults?.voice?.backendValue == "macOS-auto-male",
            "Apple Create should reuse latest generated-book language and voice defaults"
        )
        require(
            generatedBookHistoryDefaults?.generateAudio == false
                && generatedBookHistoryDefaults?.audioMode == "2"
                && generatedBookHistoryDefaults?.audioBitrateKbps == "32"
                && generatedBookHistoryDefaults?.writtenMode == "3"
                && generatedBookHistoryDefaults?.tempo == 2.0
                && generatedBookHistoryDefaults?.bookSentencesPerOutputFile == 1
                && generatedBookHistoryDefaults?.stitchFull == true
                && generatedBookHistoryDefaults?.includeTransliteration == true
                && generatedBookHistoryDefaults?.bookTranslationProvider == .googleTranslate
                && generatedBookHistoryDefaults?.bookLlmModel == "gpt-4.1-mini"
                && generatedBookHistoryDefaults?.bookTranslationBatchSize == AppleSubtitleTuning.translationBatchSizeRange.lowerBound
                && generatedBookHistoryDefaults?.bookTransliterationMode == .python
                && generatedBookHistoryDefaults?.bookTransliterationModel == "gpt-4.1"
                && generatedBookHistoryDefaults?.enableLookupCache == false
                && generatedBookHistoryDefaults?.bookLookupCacheBatchSize == AppleSubtitleTuning.translationBatchSizeRange.upperBound
                && generatedBookHistoryDefaults?.outputHtml == true
                && generatedBookHistoryDefaults?.outputPdf == true,
            "Apple Create should reuse and clamp latest generated-book pipeline defaults"
        )
        require(
            generatedBookHistoryDefaults?.includeImages == true
                && generatedBookHistoryDefaults?.imagePromptPipeline == .visualCanon
                && generatedBookHistoryDefaults?.imageStyleTemplate == .childrenBook
                && generatedBookHistoryDefaults?.imagePromptContextSentences == 50
                && generatedBookHistoryDefaults?.imageWidth == "64"
                && generatedBookHistoryDefaults?.imageHeight == "1024",
            "Apple Create should reuse and clamp latest generated-book image defaults"
        )
        let subtitleHistoryDefaults = AppleBookCreatePresentation.subtitleHistoryDefaults(from: createHistoryJobs)
        require(
            subtitleHistoryDefaults?.sourcePath == "/subtitles/latest.ass"
                && subtitleHistoryDefaults?.inputLanguage == .english
                && subtitleHistoryDefaults?.targetLanguage == .german
                && subtitleHistoryDefaults?.startTime == "01:15"
                && subtitleHistoryDefaults?.endTime == "01:02:03",
            "Apple Create should reuse latest subtitle source, languages, and formatted time offsets"
        )
        require(
            subtitleHistoryDefaults?.enableTransliteration == false
                && subtitleHistoryDefaults?.showOriginal == false
                && subtitleHistoryDefaults?.translationProvider == .googleTranslate
                && subtitleHistoryDefaults?.llmModel == "qwen2.5:7b"
                && subtitleHistoryDefaults?.transliterationMode == .python
                && subtitleHistoryDefaults?.workerCount == AppleSubtitleTuning.workerCountRange.upperBound
                && subtitleHistoryDefaults?.batchSize == AppleSubtitleTuning.batchSizeRange.lowerBound
                && subtitleHistoryDefaults?.translationBatchSize == AppleSubtitleTuning.translationBatchSizeRange.upperBound,
            "Apple Create should reuse and clamp latest subtitle tuning defaults"
        )
        let youtubeHistoryDefaults = AppleBookCreatePresentation.youtubeHistoryDefaults(from: createHistoryJobs)
        require(
            youtubeHistoryDefaults?.videoPath == "/nas/videos/demo.mp4"
                && youtubeHistoryDefaults?.subtitlePath == "/nas/videos/demo.en.ass"
                && youtubeHistoryDefaults?.targetLanguage == .slovak
                && youtubeHistoryDefaults?.voice?.backendValue == "piper-auto"
                && youtubeHistoryDefaults?.startOffset == "00:45"
                && youtubeHistoryDefaults?.endOffset == "01:30",
            "Apple Create should reuse latest YouTube dubbing source, voice, target language, and offsets"
        )
        require(
            youtubeHistoryDefaults?.originalMixPercent == 100
                && youtubeHistoryDefaults?.flushSentences == 1
                && youtubeHistoryDefaults?.translationProvider == .llm
                && youtubeHistoryDefaults?.llmModel == "gpt-4.1-mini"
                && youtubeHistoryDefaults?.translationBatchSize == AppleSubtitleTuning.translationBatchSizeRange.upperBound
                && youtubeHistoryDefaults?.transliterationMode == .default
                && youtubeHistoryDefaults?.transliterationModel == "gpt-4.1"
                && youtubeHistoryDefaults?.splitBatches == false
                && youtubeHistoryDefaults?.stitchBatches == true
                && youtubeHistoryDefaults?.includeTransliteration == false
                && youtubeHistoryDefaults?.targetHeight == .p720
                && youtubeHistoryDefaults?.preserveAspectRatio == false
                && youtubeHistoryDefaults?.enableLookupCache == false,
            "Apple Create should reuse and clamp latest YouTube dubbing tuning defaults"
        )
        require(
            AppleBookCreatePresentation.narrationHistoryDefaults(
                from: createHistoryJobs,
                currentInputFile: ""
            ) == nil,
            "Apple Create narration history should ignore subtitle and YouTube dubbing jobs"
        )
        require(
            AppleBookCreatePresentation.webCreateViewID(for: .generatedBook) == "books:create",
            "Generated-book Web handoff should target the Web book creation view"
        )
        require(
            AppleBookCreatePresentation.webCreateViewID(for: .narrateEbook) == "pipeline:source",
            "Narrate EPUB Web handoff should target the Web book narration pipeline"
        )
        require(
            AppleBookCreatePresentation.webCreateViewID(for: .subtitleJob) == "subtitles:home",
            "Subtitle Web handoff should target the Web subtitle creation view"
        )
        require(
            AppleBookCreatePresentation.webCreateViewID(for: .youtubeDub) == "subtitles:youtube-dub",
            "YouTube Dub Web handoff should target the Web dubbing creation view"
        )
        let publicWebHandoff = try requireURL(
            AppleBookCreatePresentation.webCreateHandoffURL(
                apiBaseURL: URL(string: "https://api.langtools.fifosk.synology.me/v1"),
                mode: .generatedBook
            ),
            "public Web handoff URL should derive from API base URL"
        )
        require(publicWebHandoff.scheme == "https", "public Web handoff should keep the API scheme")
        require(publicWebHandoff.host == "langtools.fifosk.synology.me", "public Web handoff should strip api host prefix")
        require(
            URLComponents(url: publicWebHandoff, resolvingAgainstBaseURL: false)?
                .queryItems?.first(where: { $0.name == "view" })?.value == "books:create",
            "public Web handoff should encode the target Web view"
        )
        let localWebHandoff = try requireURL(
            AppleBookCreatePresentation.webCreateHandoffURL(
                apiBaseURL: URL(string: "http://127.0.0.1:8000"),
                mode: .youtubeDub
            ),
            "local Web handoff URL should derive from local API base URL"
        )
        require(localWebHandoff.host == "127.0.0.1", "local Web handoff should keep localhost host")
        require(localWebHandoff.port == 5173, "local Web handoff should point local API port 8000 to Vite port 5173")
        require(
            URLComponents(url: localWebHandoff, resolvingAgainstBaseURL: false)?
                .queryItems?.first(where: { $0.name == "view" })?.value == "subtitles:youtube-dub",
            "local Web handoff should encode the YouTube Dub Web view"
        )
        require(
            AppleBookCreatePresentation.deriveBaseOutputName("  My Book: Arabic/Slovak!  ") == "my-book-arabic-slovak",
            "Apple Create base output names should be filesystem-friendly"
        )
        require(
            AppleBookCreatePresentation.deriveBaseOutputName("imports/Demo.epub") == "imports-demo",
            "Apple Create base output names should strip final file extensions like Web"
        )
        require(
            AppleBookCreatePresentation.deriveBaseOutputName("incoming/Demo.Video.mp4") == "incoming-demo-video",
            "Apple Create base output names should keep dotted stems but drop the media extension"
        )
        require(
            AppleBookCreatePresentation.deriveBaseOutputName("   ") == "generated-book",
            "Apple Create base output names should keep the generated-book fallback"
        )
        require(
            AppleGeneratedBookImageStyleTemplate(backendValue: "children_book") == .childrenBook,
            "Apple Create image style should map backend style ids"
        )
        require(
            AppleGeneratedBookImageStyleTemplate(backendValue: "comic panel") == .comics,
            "Apple Create image style should accept backend-normalized aliases"
        )
        require(
            AppleGeneratedBookImagePromptPipeline(backendValue: "visual-canon") == .visualCanon,
            "Apple Create prompt pipeline should accept backend-normalized aliases"
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
        let intakePresentation = AppleBookCreatePresentation.intakeStatusPresentation(
            for: PipelineIntakeStatusResponse(
                acceptingJobs: true,
                isUnderPressure: false,
                queueDepth: 1,
                activeCount: 2,
                softLimit: 3,
                hardLimit: 6,
                delayCount: 4
            )
        )
        require(
            intakePresentation == AppleCreateIntakePresentation(
                label: "Job intake available: 1 pending, 2 running.",
                detailLines: [
                    "Delayed jobs: 4",
                    "Slowdown starts at 3 pending",
                    "Capacity limit is 6 pending",
                ]
            ),
            "Apple Create intake presentation should include queue limits and delayed jobs"
        )
        let capacityPresentation = AppleBookCreatePresentation.intakeStatusPresentation(
            for: PipelineIntakeStatusResponse(
                acceptingJobs: false,
                isUnderPressure: true,
                queueDepth: 6,
                activeCount: 2,
                softLimit: 3,
                hardLimit: 6,
                delayCount: 2
            )
        )
        require(
            capacityPresentation.label == "Queue at capacity: 6 pending of 6. Wait for jobs to clear.",
            "Apple Create intake presentation should keep capacity wording stable"
        )
        require(
            !AppleBookCreatePresentation.canSubmit(
                submitState(
                    hasConfiguration: false,
                    mode: .generatedBook,
                    topic: "Portable Apple clients",
                    bookName: "Native Creation",
                    genre: "technical"
                )
            ),
            "Apple Create submit should stay disabled without backend configuration"
        )
        require(
            AppleBookCreatePresentation.canSubmit(
                submitState(
                    mode: .generatedBook,
                    topic: " Portable Apple clients ",
                    bookName: " Native Creation ",
                    genre: " technical "
                )
            ),
            "Generated book submit should allow complete trimmed topic, title, and genre"
        )
        require(
            !AppleBookCreatePresentation.canSubmit(
                submitState(mode: .generatedBook, topic: "Portable Apple clients", bookName: "", genre: "technical")
            ),
            "Generated book submit should require a title"
        )
        require(
            AppleBookCreatePresentation.canSubmit(
                submitState(mode: .narrateEbook, hasNarrateLocalFile: true, sourceBaseOutput: " apple/import ")
            ),
            "Narrate EPUB submit should allow a local EPUB file plus output path"
        )
        require(
            AppleBookCreatePresentation.canSubmit(
                submitState(mode: .narrateEbook, sourcePath: " imports/book.epub ", sourceBaseOutput: " apple/import ")
            ),
            "Narrate EPUB submit should allow a server EPUB path plus output path"
        )
        require(
            !AppleBookCreatePresentation.canSubmit(
                submitState(mode: .narrateEbook, hasNarrateLocalFile: true, sourceBaseOutput: " ")
            ),
            "Narrate EPUB submit should require an output path"
        )
        require(
            AppleBookCreatePresentation.canSubmit(
                submitState(mode: .subtitleJob, hasSubtitleLocalFile: true)
            ),
            "Subtitle submit should allow a local subtitle file"
        )
        require(
            AppleBookCreatePresentation.canSubmit(
                submitState(mode: .subtitleJob, subtitleSourcePath: " subtitles/demo.srt ")
            ),
            "Subtitle submit should allow a server subtitle path"
        )
        require(
            !AppleBookCreatePresentation.canSubmit(
                submitState(mode: .subtitleJob, subtitleSourcePath: " ")
            ),
            "Subtitle submit should require either a local file or server path"
        )
        require(
            AppleBookCreatePresentation.canSubmit(
                submitState(mode: .youtubeDub, youtubeVideoPath: " incoming/demo.mp4 ", youtubeSubtitlePath: " incoming/demo.srt ")
            ),
            "YouTube Dub submit should require video and subtitle paths"
        )
        require(
            !AppleBookCreatePresentation.canSubmit(
                submitState(mode: .youtubeDub, youtubeVideoPath: "incoming/demo.mp4", youtubeSubtitlePath: " ")
            ),
            "YouTube Dub submit should reject a missing subtitle path"
        )
        require(
            Array(AppleBookCreatePresentation.availableInputLanguages(from: options).prefix(2)) == [.english, .arabic],
            "Input language options should keep backend-supported languages first"
        )
        require(
            Array(AppleBookCreatePresentation.availableTargetLanguages(from: options).prefix(2)) == [.english, .arabic],
            "Target language options should keep backend-supported languages first"
        )
        require(
            AppleBookCreatePresentation.availableTargetLanguages(from: options).contains(AppleBookCreateLanguage("Hindi")!),
            "Target language options should append the broad local language catalog"
        )
        require(
            AppleBookCreatePresentation.availableInputLanguages(from: nil) == AppleBookCreateLanguage.allCases,
            "Missing backend options should fall back to all local languages"
        )
        let customVoice = AppleBookCreateVoiceOption("custom-local-voice")!
        let availableVoices = AppleBookCreatePresentation.availableVoices(from: options, selected: customVoice)
        require(
            availableVoices.first == customVoice,
            "Voice options should preserve the selected voice even when it is absent from backend inventory"
        )
        require(
            availableVoices.map(\.backendValue).contains("macOS-auto-male"),
            "Voice options should include backend-supported voices"
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
        let languagePreferences = AppleBookCreatePresentation.languagePreferences(
            inputLanguage: .english,
            targetLanguage: .arabic,
            additionalTargetLanguages: " German, arabic, French ",
            enableLookupCache: false
        )
        require(
            languagePreferences == AppleCreateLanguagePreferences(
                inputLanguage: "English",
                targetLanguages: ["Arabic", "German", "French"],
                enableLookupCache: false
            ),
            "Apple Create language preferences should persist Web-aligned target language defaults"
        )
        let restoredLanguagePreferences = AppleBookCreatePresentation.resolvedLanguagePreferences(
            from: AppleCreateLanguagePreferences(
                inputLanguage: " German ",
                targetLanguages: [" Spanish ", "Slovak", "Spanish"],
                enableLookupCache: true
            )
        )
        require(
            restoredLanguagePreferences == AppleCreateResolvedLanguagePreferences(
                inputLanguage: .german,
                targetLanguage: .spanish,
                additionalTargetLanguages: "Slovak",
                enableLookupCache: true
            ),
            "Apple Create should restore shared language and lookup-cache defaults from persisted preferences"
        )
        require(
            AppleBookCreatePresentation.normalizedBookGenres(" Adventure, Fantasy, adventure,  ") == ["Adventure", "Fantasy"],
            "Apple Create should normalize edited genre strings into Web-aligned book_genres arrays"
        )
        let contentIndex: JSONValue = .object([
            "chapters": .array([
                .object([
                    "id": .string("intro"),
                    "title": .string("Intro"),
                    "start_sentence": .number(1),
                    "sentence_count": .number(5)
                ]),
                .object([
                    "toc_label": .string("Second"),
                    "startSentence": .string("6"),
                    "endSentence": .number(12)
                ]),
                .object([
                    "title": .string("Bad"),
                    "start_sentence": .number(0)
                ])
            ])
        ])
        let chapters = AppleBookCreatePresentation.contentIndexChapters(from: contentIndex)
        require(chapters.count == 2, "Apple Narrate EPUB chapter picker should skip invalid chapter rows")
        require(
            chapters[0] == AppleCreateChapterOption(
                id: "intro",
                title: "Intro",
                startSentence: 1,
                endSentence: 5
            ),
            "Apple Narrate EPUB chapter parser should derive end sentence from sentence_count"
        )
        require(
            chapters[1] == AppleCreateChapterOption(
                id: "chapter-2",
                title: "Second",
                startSentence: 6,
                endSentence: 12
            ),
            "Apple Narrate EPUB chapter parser should accept camelCase sentence fields and TOC labels"
        )
        let chapterRange = AppleBookCreatePresentation.chapterRangeSelection(
            chapters: chapters,
            startChapterID: "intro",
            endChapterID: "chapter-2"
        )
        require(
            chapterRange == AppleCreateChapterRangeSelection(
                startIndex: 0,
                endIndex: 1,
                startSentence: 1,
                endSentence: 12,
                count: 2,
                label: "Intro - Second"
            ),
            "Apple Narrate EPUB chapter range picker should resolve consecutive chapter windows"
        )
        let clampedChapterRange = AppleBookCreatePresentation.chapterRangeSelection(
            chapters: chapters,
            startChapterID: "chapter-2",
            endChapterID: "intro"
        )
        require(
            clampedChapterRange == AppleCreateChapterRangeSelection(
                startIndex: 1,
                endIndex: 1,
                startSentence: 6,
                endSentence: 12,
                count: 1,
                label: "Second"
            ),
            "Apple Narrate EPUB chapter range picker should clamp end chapters before the start"
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
            AppleBookCreatePresentation.estimatedAudioDurationLabel(sentenceCount: 10)
                == "Estimated audio duration: ~00:01:04 (10 sentences, 6.4s/sentence)",
            "Apple Create estimated audio label should match the Web sentence-duration estimate"
        )
        require(
            AppleBookCreatePresentation.estimatedAudioDurationLabel(sentenceCount: 1)
                == "Estimated audio duration: ~00:00:06 (1 sentence, 6.4s/sentence)",
            "Apple Create estimated audio label should use a singular sentence label"
        )
        require(
            AppleBookCreatePresentation.estimatedAudioDurationLabel(sentenceCount: nil) == nil,
            "Apple Create estimated audio label should stay hidden without a known sentence count"
        )
        require(
            AppleBookCreatePresentation.estimatedNarrateSentenceCount(
                startSentence: "7",
                endSentence: "+10"
            ) == 10,
            "Apple Narrate EPUB estimated sentence count should support Web-aligned +offset end values"
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
        let resolvedDefaults = AppleBookCreatePresentation.resolvedDefaults(
            from: options,
            editedFields: [],
            currentSentenceCount: 999
        )
        require(resolvedDefaults.topic == nil, "Blank backend topic should not overwrite topic")
        require(resolvedDefaults.bookName == nil, "Blank backend title should not overwrite title")
        require(resolvedDefaults.genre == nil, "Blank backend genre should not overwrite genre")
        require(resolvedDefaults.author == "Me", "Blank or backend author should resolve to visible author default")
        require(resolvedDefaults.sentenceCount == 30, "Unedited sentence count should use backend default")
        require(resolvedDefaults.inputLanguage == .english, "Input language default should map from backend options")
        require(resolvedDefaults.targetLanguage == .arabic, "Target language default should map from backend options")
        require(
            resolvedDefaults.additionalTargetLanguages == "",
            "Legacy single-language defaults should leave Apple additional targets blank"
        )
        require(
            resolvedDefaults.voice?.backendValue == "macOS-auto-male",
            "Voice default should map from backend options"
        )
        require(
            resolvedDefaults.generateAudio == true,
            "Generate-audio toggle should use backend pipeline default"
        )
        require(
            resolvedDefaults.audioMode == "4",
            "Audio mode should use backend pipeline default"
        )
        require(
            resolvedDefaults.audioBitrateKbps == "96",
            "Audio bitrate should use backend pipeline default"
        )
        require(
            resolvedDefaults.writtenMode == "4",
            "Written mode should use backend pipeline default"
        )
        require(
            resolvedDefaults.tempo == 1.0,
            "Tempo should use backend pipeline default"
        )
        require(
            resolvedDefaults.bookSentencesPerOutputFile == 10,
            "Sentences-per-file should use backend pipeline default"
        )
        require(
            resolvedDefaults.stitchFull == true,
            "Stitch-full toggle should use backend pipeline default"
        )
        require(
            resolvedDefaults.includeTransliteration == true,
            "Transliteration toggle should use backend pipeline default"
        )
        require(
            resolvedDefaults.enableLookupCache == true,
            "Lookup-cache toggle should use backend pipeline default"
        )
        require(
            resolvedDefaults.outputHtml == false,
            "HTML output toggle should use backend pipeline default"
        )
        require(
            resolvedDefaults.outputPdf == false,
            "PDF output toggle should use backend pipeline default"
        )
        require(
            resolvedDefaults.includeImages == false,
            "Generated-book illustrations toggle should use backend generated-source default"
        )
        require(
            resolvedDefaults.imagePromptPipeline == .promptPlan,
            "Generated-book image prompt pipeline should map from backend generated-source default"
        )
        require(
            resolvedDefaults.imageStyleTemplate == .wireframe,
            "Generated-book image style should map from backend generated-source default"
        )
        require(
            resolvedDefaults.imagePromptContextSentences == 0,
            "Generated-book image prompt context should use backend generated-source default"
        )
        require(
            resolvedDefaults.imageWidth == "256",
            "Generated-book image width should use backend generated-source default"
        )
        require(
            resolvedDefaults.imageHeight == "256",
            "Generated-book image height should use backend generated-source default"
        )
        require(
            resolvedDefaults.subtitleTranslationProvider == .llm,
            "Subtitle provider should map from backend pipeline default"
        )
        let editedDefaults = AppleBookCreatePresentation.resolvedDefaults(
            from: options,
            editedFields: [
                .author,
                .sentenceCount,
                .targetLanguage,
                .voice,
                .generateAudio,
                .audioMode,
                .audioBitrateKbps,
                .writtenMode,
                .tempo,
                .bookSentencesPerOutputFile,
                .stitchFull,
                .enableLookupCache,
                .outputHtml,
                .outputPdf,
                .includeImages,
                .imagePromptPipeline,
                .imageStyleTemplate,
                .imagePromptContextSentences,
                .imageWidth,
                .imageHeight
            ],
            currentSentenceCount: 999
        )
        require(editedDefaults.author == nil, "Edited author should not be overwritten by backend defaults")
        require(editedDefaults.targetLanguage == nil, "Edited target language should not be overwritten")
        require(
            editedDefaults.additionalTargetLanguages == "",
            "Unedited additional targets should still accept backend defaults when only the primary target is edited"
        )
        require(editedDefaults.voice == nil, "Edited voice should not be overwritten")
        require(editedDefaults.generateAudio == nil, "Edited generate-audio toggle should not be overwritten")
        require(editedDefaults.audioMode == nil, "Edited audio mode should not be overwritten")
        require(editedDefaults.audioBitrateKbps == nil, "Edited audio bitrate should not be overwritten")
        require(editedDefaults.writtenMode == nil, "Edited written mode should not be overwritten")
        require(editedDefaults.tempo == nil, "Edited tempo should not be overwritten")
        require(editedDefaults.bookSentencesPerOutputFile == nil, "Edited sentences-per-file should not be overwritten")
        require(editedDefaults.stitchFull == nil, "Edited stitch-full toggle should not be overwritten")
        require(editedDefaults.outputHtml == nil, "Edited HTML output should not be overwritten")
        require(editedDefaults.outputPdf == nil, "Edited PDF output should not be overwritten")
        require(editedDefaults.enableLookupCache == nil, "Edited lookup-cache toggle should not be overwritten")
        require(editedDefaults.includeImages == nil, "Edited illustrations toggle should not be overwritten")
        require(editedDefaults.imagePromptPipeline == nil, "Edited image prompt pipeline should not be overwritten")
        require(editedDefaults.imageStyleTemplate == nil, "Edited image style should not be overwritten")
        require(editedDefaults.imagePromptContextSentences == nil, "Edited image prompt context should not be overwritten")
        require(editedDefaults.imageWidth == nil, "Edited image width should not be overwritten")
        require(editedDefaults.imageHeight == nil, "Edited image height should not be overwritten")
        require(editedDefaults.sentenceCount == 500, "Edited sentence count should still clamp to backend max")
        let multiTargetOptionsJSON = """
        {
          "sentence_bounds": {"min": 1, "max": 500, "default": 30},
          "defaults": {
            "topic": "",
            "book_name": "",
            "genre": "",
            "author": "Me",
            "input_language": "English",
            "output_language": "Arabic",
            "target_languages": [" German ", "French", "german", "", "Italian"],
            "voice": "macOS-auto-male"
          },
          "pipeline_defaults": {
            "sentences_per_output_file": 10,
            "stitch_full": true,
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
          "supported_input_languages": ["English", "German", "French"],
          "supported_output_languages": ["English", "German", "French"],
          "supported_voices": ["gTTS", "macOS-auto-male", "piper-auto"]
        }
        """.data(using: .utf8)!
        let multiTargetOptions = try decoder.decode(BookCreationOptionsResponse.self, from: multiTargetOptionsJSON)
        let multiTargetDefaults = AppleBookCreatePresentation.resolvedDefaults(
            from: multiTargetOptions,
            editedFields: [],
            currentSentenceCount: 30
        )
        require(
            multiTargetDefaults.targetLanguage == .german,
            "Apple Create should use the first backend target language as the primary picker default"
        )
        require(
            multiTargetDefaults.additionalTargetLanguages == "French, Italian",
            "Apple Create should preserve remaining backend target defaults in the Additional targets field"
        )
        let editedAdditionalTargetDefaults = AppleBookCreatePresentation.resolvedDefaults(
            from: multiTargetOptions,
            editedFields: [.additionalTargetLanguages],
            currentSentenceCount: 30
        )
        require(
            editedAdditionalTargetDefaults.targetLanguage == .german,
            "Edited additional targets should not block the primary backend target default"
        )
        require(
            editedAdditionalTargetDefaults.additionalTargetLanguages == nil,
            "Edited additional targets should not be overwritten by backend defaults"
        )
        require(
            AppleBookCreatePresentation.clampSentenceCount(0, bounds: options.sentenceBounds) == 1,
            "Sentence count helper should clamp to backend lower bound"
        )
        require(
            AppleBookCreatePresentation.clampImagePromptContextSentences(99) == 50,
            "Image prompt context should clamp to the Web submission upper bound"
        )
        require(
            AppleBookCreatePresentation.clampImagePromptBatchSize(0) == 1,
            "Image prompt batch size should clamp to the Web submission lower bound"
        )
        require(
            AppleBookCreatePresentation.clampImagePromptBatchSize(99) == 50,
            "Image prompt batch size should clamp to the Web submission upper bound"
        )
        require(
            AppleBookCreatePresentation.clampBookSentencesPerOutputFile(0) == 1,
            "Book sentences-per-file should clamp to the Web submission lower bound"
        )
        require(
            AppleBookCreatePresentation.clampBookSentencesPerOutputFile(999) == 100,
            "Book sentences-per-file should clamp to the Web submission upper bound"
        )
        require(
            AppleBookCreatePresentation.normalizedImageDimension("63.9") == "64",
            "Image dimensions should clamp below-minimum numeric input"
        )
        require(
            AppleBookCreatePresentation.normalizedImageDimension("1024.8") == "1024",
            "Image dimensions should floor decimal input before submit"
        )
        require(
            AppleBookCreatePresentation.normalizedImageDimension("bad") == "512",
            "Image dimensions should fall back for invalid input"
        )
        require(
            AppleBookCreatePresentation.normalizedImageSteps("") == nil,
            "Blank image steps should keep the backend default"
        )
        require(
            AppleBookCreatePresentation.normalizedImageSteps("0.9") == 1,
            "Image steps should clamp below-minimum numeric input"
        )
        require(
            AppleBookCreatePresentation.normalizedImageSteps("24.7") == 24,
            "Image steps should floor decimal input before submit"
        )
        require(
            AppleBookCreatePresentation.normalizedImageCfgScale("") == nil,
            "Blank CFG scale should keep the backend default"
        )
        require(
            AppleBookCreatePresentation.normalizedImageCfgScale("-1") == 0,
            "CFG scale should clamp below-minimum numeric input"
        )
        require(
            AppleBookCreatePresentation.normalizedImageCfgScale("7.25") == 7.25,
            "CFG scale should preserve decimal input before submit"
        )
        switch AppleBookCreatePresentation.normalizedSubtitleTimeRange(start: "", end: "+5") {
        case let .success(range):
            require(range == AppleCreateTimeRange(start: "00:00", end: "+05:00"), "Subtitle range should normalize empty start and relative end")
        case let .failure(error):
            require(false, "Subtitle range should accept empty start and relative end, got \(error)")
        }
        switch AppleBookCreatePresentation.normalizedSubtitleTimeRange(start: "bad", end: "") {
        case .success:
            require(false, "Subtitle range should reject invalid start time")
        case let .failure(error):
            require(
                error == .subtitleStartTime,
                "Subtitle range should report invalid start time"
            )
            require(
                error.message == "Enter a valid start time in MM:SS or HH:MM:SS format.",
                "Subtitle start error should keep visible copy"
            )
        }
        switch AppleBookCreatePresentation.normalizedSubtitleTimeRange(start: "00:00", end: "+bad") {
        case .success:
            require(false, "Subtitle range should reject invalid end time")
        case let .failure(error):
            require(
                error == .subtitleEndTime,
                "Subtitle range should report invalid end time"
            )
        }
        switch AppleBookCreatePresentation.normalizedYoutubeOffsetRange(start: "45", end: "1:30") {
        case let .success(range):
            require(range == AppleCreateOffsetRange(start: "45", end: "01:30"), "YouTube range should normalize numeric and MM:SS offsets")
        case let .failure(error):
            require(false, "YouTube range should accept valid offsets, got \(error)")
        }
        switch AppleBookCreatePresentation.normalizedYoutubeOffsetRange(start: "-1", end: "") {
        case .success:
            require(false, "YouTube range should reject invalid start offset")
        case let .failure(error):
            require(
                error == .youtubeStartOffset,
                "YouTube range should report invalid start offset"
            )
            require(
                error.message == "Enter a valid start offset in seconds, MM:SS, or HH:MM:SS format.",
                "YouTube start error should keep visible copy"
            )
        }
        switch AppleBookCreatePresentation.normalizedYoutubeOffsetRange(start: "", end: "-1") {
        case .success:
            require(false, "YouTube range should reject invalid end offset")
        case let .failure(error):
            require(
                error == .youtubeEndOffset,
                "YouTube range should report invalid end offset"
            )
        }
        let generatedDraft = AppleBookCreatePresentation.generatedBookDraft(
            topic: "  Portable Apple clients  ",
            bookName: " Native Creation ",
            genre: " technical ",
            author: "   ",
            summary: " A portable creation flow. ",
            year: " 2026 ",
            isbn: " 9780140328721 ",
            coverFile: " covers/native.jpg ",
            sourceBookTitle: " Inferno ",
            sourceBookAuthor: " Dan Brown ",
            sourceBookGenre: " thriller ",
            sourceBookSummary: " A symbologist follows clues. ",
            sentenceCount: 42,
            inputLanguage: .english,
            targetLanguage: .slovak,
            additionalTargetLanguages: " German, Arabic\nSlovak , German ",
            voice: AppleBookCreateVoiceOption(" macOS-auto-male ")!,
            targetVoice: AppleBookCreateVoiceOption(" piper-auto ")!,
            languageVoiceOverrides: [
                " German ": " macOS-auto ",
                "Arabic": "",
                "Spanish": "edge-tts",
            ],
            baseOutput: "native-creation",
            generateAudio: false,
            audioMode: " 2 ",
            audioBitrateKbps: "31",
            writtenMode: " 3 ",
            tempo: 2.9,
            sentencesPerOutputFile: 0,
            stitchFull: true,
            includeTransliteration: true,
            translationProvider: .googleTranslate,
            llmModel: " gpt-4.1-mini ",
            translationBatchSize: 0,
            transliterationMode: .python,
            transliterationModel: " gpt-4.1 ",
            enableLookupCache: false,
            lookupCacheBatchSize: 99,
            outputHtml: true,
            outputPdf: false,
            includeImages: true,
            imagePromptPipeline: .visualCanon,
            imageStyleTemplate: .childrenBook,
            imagePromptBatchingEnabled: false,
            imagePromptBatchSize: 0,
            imagePromptPlanBatchSize: 99,
            imagePromptContextSentences: 99,
            imageWidth: "63.9",
            imageHeight: "1024.8",
            imageSteps: "0",
            imageCfgScale: "-1",
            imageSamplerName: " euler_a ",
            imageSeedWithPreviousImage: true,
            imageBlankDetectionEnabled: true,
            imageApiBaseURLs: " http://192.168.1.9:7860/,\nhttp://192.168.1.76:7860 , http://192.168.1.9:7860 ",
            imageConcurrency: "2.9",
            imageApiTimeoutSeconds: "0",
            threadCount: "3.9",
            queueSize: "0",
            jobMaxWorkers: " 5 ",
            pipelineDefaults: options.pipelineDefaults,
            generatedSourceDefaults: options.generatedSourceDefaults
        )
        require(generatedDraft.topic == "Portable Apple clients", "Generated draft should trim topic")
        require(generatedDraft.author == "Me", "Generated draft should default blank author to Me")
        require(generatedDraft.summary == "A portable creation flow.", "Generated draft should trim metadata summary")
        require(generatedDraft.year == "2026", "Generated draft should trim metadata year")
        require(generatedDraft.isbn == "9780140328721", "Generated draft should trim metadata ISBN")
        require(generatedDraft.coverFile == "covers/native.jpg", "Generated draft should trim metadata cover path")
        require(generatedDraft.sourceBookTitle == "Inferno", "Generated draft should trim source book title")
        require(generatedDraft.sourceBookAuthor == "Dan Brown", "Generated draft should trim source book author")
        require(generatedDraft.sourceBookGenre == "thriller", "Generated draft should trim source book genre")
        require(
            generatedDraft.sourceBookSummary == "A symbologist follows clues.",
            "Generated draft should trim source book summary"
        )
        require(generatedDraft.targetLanguage == "Slovak", "Generated draft should map target language")
        require(
            generatedDraft.targetLanguages == ["Slovak", "German", "Arabic"],
            "Generated draft should map primary and deduped additional target languages"
        )
        require(generatedDraft.voice == "macOS-auto-male", "Generated draft should trim and map voice")
        require(
            generatedDraft.voiceOverrides == [
                "Slovak": "piper-auto",
                "German": "macOS-auto",
                "Arabic": "piper-auto",
            ],
            "Generated draft should map selected target voice and Web-shaped per-language overrides"
        )
        require(generatedDraft.generateAudio == false, "Generated draft should keep selected audio toggle")
        require(generatedDraft.audioMode == "2", "Generated draft should trim selected audio mode")
        require(generatedDraft.audioBitrateKbps == 32, "Generated draft should floor selected audio bitrate")
        require(generatedDraft.writtenMode == "3", "Generated draft should trim selected written mode")
        require(generatedDraft.tempo == 2.0, "Generated draft should clamp selected tempo")
        require(generatedDraft.sentencesPerOutputFile == 1, "Generated draft should clamp sentences per file")
        require(generatedDraft.stitchFull == true, "Generated draft should keep stitch-full toggle")
        require(generatedDraft.translationProvider == "googletrans", "Generated draft should map selected provider")
        require(generatedDraft.llmModel == nil, "Generated draft should omit model for non-LLM provider")
        require(generatedDraft.translationBatchSize == 1, "Generated draft should clamp translation batch size")
        require(generatedDraft.transliterationMode == "python", "Generated draft should map transliteration mode")
        require(generatedDraft.transliterationModel == nil, "Generated draft should omit model for Python transliteration")
        require(generatedDraft.lookupCacheBatchSize == 50, "Generated draft should clamp lookup cache batch size")
        require(generatedDraft.outputHtml == true, "Generated draft should keep selected HTML output toggle")
        require(generatedDraft.outputPdf == false, "Generated draft should keep selected PDF output toggle")
        require(generatedDraft.includeImages == true, "Generated draft should keep the native illustrations toggle")
        require(
            generatedDraft.imagePromptPipeline == "visual_canon",
            "Generated draft should keep the selected image prompt pipeline backend id"
        )
        require(
            generatedDraft.imageStyleTemplate == "children_book",
            "Generated draft should keep the selected image style backend id"
        )
        require(
            generatedDraft.imagePromptBatchingEnabled == false,
            "Generated draft should keep the selected image prompt batching toggle"
        )
        require(
            generatedDraft.imagePromptBatchSize == 1,
            "Generated draft should clamp the selected image prompt batch size"
        )
        require(
            generatedDraft.imagePromptPlanBatchSize == 50,
            "Generated draft should clamp the selected image prompt plan batch size"
        )
        require(
            generatedDraft.imagePromptContextSentences == 50,
            "Generated draft should clamp the selected image prompt context"
        )
        require(generatedDraft.imageWidth == "64", "Generated draft should normalize selected image width")
        require(generatedDraft.imageHeight == "1024", "Generated draft should normalize selected image height")
        require(generatedDraft.imageSteps == 1, "Generated draft should normalize selected image steps")
        require(generatedDraft.imageCfgScale == 0, "Generated draft should normalize selected CFG scale")
        require(generatedDraft.imageSamplerName == "euler_a", "Generated draft should trim selected sampler name")
        require(generatedDraft.imageSeedWithPreviousImage, "Generated draft should keep previous-image seed toggle")
        require(generatedDraft.imageBlankDetectionEnabled, "Generated draft should keep blank-detection toggle")
        require(
            generatedDraft.imageApiBaseURLs == ["http://192.168.1.9:7860", "http://192.168.1.76:7860"],
            "Generated draft should normalize selected image API URLs"
        )
        require(generatedDraft.imageConcurrency == 2, "Generated draft should floor selected image concurrency")
        require(generatedDraft.imageApiTimeoutSeconds == 1, "Generated draft should clamp selected image timeout")
        require(generatedDraft.threadCount == 3, "Generated draft should floor selected worker threads")
        require(generatedDraft.queueSize == 1, "Generated draft should clamp selected queue size")
        require(generatedDraft.jobMaxWorkers == 5, "Generated draft should trim selected max job workers")
        require(generatedDraft.pipelineDefaults == options.pipelineDefaults, "Generated draft should carry pipeline defaults")
        require(
            generatedDraft.generatedSourceDefaults == options.generatedSourceDefaults,
            "Generated draft should carry generated-source defaults"
        )

        let narrateDraft = AppleBookCreatePresentation.narrateEbookDraft(
            inputFile: " imports/demo.epub ",
            baseOutput: " apple/demo ",
            title: " Imported Demo ",
            author: " Source Author ",
            genre: " Memoir, Travel, memoir ",
            summary: " Imported EPUB summary. ",
            year: " 2025 ",
            isbn: " 9780000000002 ",
            coverFile: " covers/imported.jpg ",
            startSentence: "7.9",
            endSentence: "3",
            inputLanguage: .english,
            targetLanguage: .arabic,
            additionalTargetLanguages: "German, Arabic\nFrench",
            voice: .gtts,
            targetVoice: AppleBookCreateVoiceOption(" piper-auto ")!,
            languageVoiceOverrides: [
                "French": "macOS-auto-female",
                "Spanish": "edge-tts",
            ],
            generateAudio: true,
            audioMode: "",
            audioBitrateKbps: "",
            writtenMode: "",
            tempo: 0.2,
            sentencesPerOutputFile: 999,
            stitchFull: false,
            includeTransliteration: false,
            translationProvider: .llm,
            llmModel: " gpt-4.1-mini ",
            translationBatchSize: 12,
            transliterationMode: .default,
            transliterationModel: " gpt-4.1 ",
            enableLookupCache: true,
            lookupCacheBatchSize: 2,
            outputHtml: false,
            outputPdf: true,
            threadCount: " 4 ",
            queueSize: "",
            jobMaxWorkers: "2.7",
            pipelineDefaults: options.pipelineDefaults
        )
        require(narrateDraft.inputFile == "imports/demo.epub", "Narrate draft should trim input path")
        require(narrateDraft.baseOutput == "apple/demo", "Narrate draft should trim output path")
        require(narrateDraft.title == "Imported Demo", "Narrate draft should trim optional metadata title")
        require(narrateDraft.author == "Source Author", "Narrate draft should trim optional metadata author")
        require(narrateDraft.genre == "Memoir, Travel, memoir", "Narrate draft should trim optional metadata genre")
        require(
            AppleBookCreatePresentation.normalizedBookGenres(narrateDraft.genre ?? "") == ["Memoir", "Travel"],
            "Narrate draft genre should be convertible to Web-aligned unique book_genres"
        )
        require(narrateDraft.summary == "Imported EPUB summary.", "Narrate draft should trim metadata summary")
        require(narrateDraft.year == "2025", "Narrate draft should trim metadata year")
        require(narrateDraft.isbn == "9780000000002", "Narrate draft should trim metadata ISBN")
        require(narrateDraft.coverFile == "covers/imported.jpg", "Narrate draft should trim metadata cover path")
        require(
            narrateDraft.targetLanguages == ["Arabic", "German", "French"],
            "Narrate draft should map primary and deduped additional target languages"
        )
        require(narrateDraft.startSentence == 7, "Narrate draft should floor selected start sentence")
        require(narrateDraft.endSentence == 7, "Narrate draft should clamp end sentence to start sentence")
        require(narrateDraft.audioMode == "4", "Narrate draft should use fallback audio mode for blank selection")
        require(narrateDraft.audioBitrateKbps == nil, "Narrate draft should preserve backend-default audio bitrate")
        require(narrateDraft.writtenMode == "4", "Narrate draft should use fallback written mode for blank selection")
        require(narrateDraft.tempo == 0.5, "Narrate draft should clamp low tempo")
        require(narrateDraft.sentencesPerOutputFile == 100, "Narrate draft should clamp sentences per file")
        require(narrateDraft.stitchFull == false, "Narrate draft should keep stitch-full toggle")
        require(
            narrateDraft.voiceOverrides == [
                "Arabic": "piper-auto",
                "German": "piper-auto",
                "French": "macOS-auto-female",
            ],
            "Narrate draft should map selected target voice and Web-shaped per-language overrides"
        )
        let voiceOverrideValue = AppleBookCreatePresentation.voiceOverridePipelineValue([
            " Arabic ": " piper-auto ",
            "German": "",
            "French": " macOS-auto "
        ])
        require(
            voiceOverrideValue == .object([
                "Arabic": .string("piper-auto"),
                "French": .string("macOS-auto"),
            ]),
            "Apple voice override pipeline value should trim entries and omit blanks"
        )
        require(narrateDraft.includeTransliteration == false, "Narrate draft should keep transliteration toggle")
        require(narrateDraft.translationProvider == "llm", "Narrate draft should map selected provider")
        require(narrateDraft.llmModel == "gpt-4.1-mini", "Narrate draft should include trimmed LLM model override")
        require(narrateDraft.translationBatchSize == 12, "Narrate draft should keep selected translation batch size")
        require(narrateDraft.transliterationMode == "default", "Narrate draft should reset mode when transliteration is off")
        require(narrateDraft.transliterationModel == nil, "Narrate draft should omit model when transliteration is off")
        require(narrateDraft.lookupCacheBatchSize == 2, "Narrate draft should keep selected lookup cache batch size")
        require(narrateDraft.outputPdf == true, "Narrate draft should keep selected PDF output toggle")
        require(narrateDraft.threadCount == 4, "Narrate draft should trim selected worker threads")
        require(narrateDraft.queueSize == nil, "Narrate draft should omit blank queue size")
        require(narrateDraft.jobMaxWorkers == 2, "Narrate draft should floor selected max job workers")

        let narrateOffsetDraft = AppleBookCreatePresentation.narrateEbookDraft(
            inputFile: "imports/demo.epub",
            baseOutput: "apple/demo",
            title: "",
            author: "",
            genre: "",
            summary: "",
            year: "",
            isbn: "",
            coverFile: "",
            startSentence: "7",
            endSentence: "+10",
            inputLanguage: .english,
            targetLanguage: .arabic,
            additionalTargetLanguages: "",
            voice: .gtts,
            targetVoice: AppleBookCreateVoiceOption("macOS-auto-male")!,
            generateAudio: true,
            audioMode: "",
            audioBitrateKbps: "",
            writtenMode: "",
            tempo: options.pipelineDefaults.tempo,
            sentencesPerOutputFile: options.pipelineDefaults.sentencesPerOutputFile,
            stitchFull: options.pipelineDefaults.stitchFull,
            includeTransliteration: options.pipelineDefaults.includeTransliteration,
            translationProvider: .googleTranslate,
            llmModel: "",
            translationBatchSize: options.pipelineDefaults.translationBatchSize,
            transliterationMode: .default,
            transliterationModel: "",
            enableLookupCache: options.pipelineDefaults.enableLookupCache,
            lookupCacheBatchSize: options.pipelineDefaults.lookupCacheBatchSize,
            outputHtml: options.pipelineDefaults.outputHtml,
            outputPdf: options.pipelineDefaults.outputPdf,
            threadCount: "",
            queueSize: "",
            jobMaxWorkers: "",
            pipelineDefaults: options.pipelineDefaults
        )
        require(
            narrateOffsetDraft.endSentence == 16,
            "Narrate draft should support Web-aligned +offset end sentence values"
        )

        let subtitleDraft = AppleBookCreatePresentation.subtitleJobDraft(
            sourcePath: " Subtitles/demo.srt ",
            mediaMetadata: [
                "job_label": .string("Pilot"),
                "episode": .object(["season": .number(1), "number": .number(2)])
            ],
            inputLanguage: .english,
            targetLanguage: .arabic,
            outputFormat: .ass,
            startTime: "00:00",
            endTime: "",
            enableTransliteration: true,
            highlight: true,
            showOriginal: false,
            generateAudioBook: true,
            mirrorBatchesToSourceDir: false,
            translationProvider: .googleTranslate,
            llmModel: " gpt-4.1-mini ",
            transliterationMode: .python,
            transliterationModel: " gpt-4.1 ",
            workerCount: 99,
            batchSize: 0,
            translationBatchSize: 999,
            assFontSize: 4,
            assEmphasisScale: 3.2
        )
        require(subtitleDraft.sourcePath == "Subtitles/demo.srt", "Subtitle draft should trim source path")
        require(subtitleDraft.mediaMetadata?["source"] == .string("apple"), "Subtitle draft should label Apple metadata source")
        require(
            subtitleDraft.mediaMetadata?["job_label"] == .string("Pilot"),
            "Subtitle draft should preserve job label metadata"
        )
        require(
            subtitleDraft.mediaMetadata?["episode"] == .object(["season": .number(1), "number": .number(2)]),
            "Subtitle draft should preserve episode metadata"
        )
        require(subtitleDraft.endTime == nil, "Subtitle draft should omit blank end time")
        require(subtitleDraft.translationProvider == "googletrans", "Subtitle draft should map Google Translate provider")
        require(subtitleDraft.llmModel == nil, "Subtitle draft should omit LLM model for non-LLM provider")
        require(subtitleDraft.transliterationMode == "python", "Subtitle draft should include enabled transliteration mode")
        require(
            subtitleDraft.transliterationModel == nil,
            "Subtitle draft should omit transliteration model when mode disallows override"
        )
        require(
            subtitleDraft.workerCount == AppleSubtitleTuning.workerCountRange.upperBound,
            "Subtitle draft should clamp worker count"
        )
        require(
            subtitleDraft.batchSize == AppleSubtitleTuning.batchSizeRange.lowerBound,
            "Subtitle draft should clamp subtitle batch size"
        )
        require(
            subtitleDraft.translationBatchSize == AppleSubtitleTuning.translationBatchSizeRange.upperBound,
            "Subtitle draft should clamp translation batch size"
        )
        require(
            subtitleDraft.assFontSize == AppleSubtitleAssTypography.fontSizeRange.lowerBound,
            "Subtitle draft should clamp ASS font size"
        )
        require(
            subtitleDraft.assEmphasisScale == AppleSubtitleAssTypography.emphasisScaleRange.upperBound,
            "Subtitle draft should clamp ASS emphasis scale"
        )

        let youtubeDraft = AppleBookCreatePresentation.youtubeDubDraft(
            videoPath: " incoming/demo.mp4 ",
            subtitlePath: " incoming/demo.srt ",
            sourceLanguage: .english,
            subtitleLanguage: " es ",
            targetLanguage: .slovak,
            voice: .gtts,
            mediaMetadata: [
                "source": .string("fixture"),
                "youtube": .object(["title": .string("Demo video")])
            ],
            startTimeOffset: "",
            endTimeOffset: "01:30",
            originalMixPercent: 104.2,
            flushSentences: 0,
            translationProvider: .llm,
            llmModel: " gpt-4.1-mini ",
            translationBatchSize: 0,
            transliterationMode: .default,
            transliterationModel: " gpt-4.1 ",
            splitBatches: false,
            stitchBatches: true,
            includeTransliteration: true,
            targetHeight: .p720,
            preserveAspectRatio: true,
            enableLookupCache: true
        )
        require(youtubeDraft.videoPath == "incoming/demo.mp4", "YouTube draft should trim video path")
        require(youtubeDraft.sourceLanguage == "es", "YouTube draft should prefer selected subtitle language")
        require(youtubeDraft.startTimeOffset == nil, "YouTube draft should omit blank start offset")
        require(youtubeDraft.originalMixPercent == 100, "YouTube draft should clamp original mix")
        require(youtubeDraft.flushSentences == 1, "YouTube draft should clamp flush interval")
        require(youtubeDraft.llmModel == "gpt-4.1-mini", "YouTube draft should include trimmed LLM model")
        require(youtubeDraft.translationBatchSize == 1, "YouTube draft should clamp translation batch size")
        require(youtubeDraft.stitchBatches == false, "YouTube draft should not stitch when split batches is disabled")
        require(youtubeDraft.targetHeight == 720, "YouTube draft should map target height")
        require(youtubeDraft.mediaMetadata["source"] == .string("apple"), "YouTube draft should label Apple metadata source")
        require(
            youtubeDraft.mediaMetadata["youtube"] == .object(["title": .string("Demo video")]),
            "YouTube draft should preserve enriched media metadata"
        )

        let youtubeFallbackDraft = AppleBookCreatePresentation.youtubeDubDraft(
            videoPath: "incoming/demo.mp4",
            subtitlePath: "incoming/demo.srt",
            sourceLanguage: .english,
            subtitleLanguage: " ",
            targetLanguage: .slovak,
            voice: .gtts,
            mediaMetadata: [:],
            startTimeOffset: "",
            endTimeOffset: "",
            originalMixPercent: 5,
            flushSentences: 10,
            translationProvider: .llm,
            llmModel: "gpt-4.1-mini",
            translationBatchSize: 8,
            transliterationMode: .default,
            transliterationModel: "",
            splitBatches: true,
            stitchBatches: true,
            includeTransliteration: false,
            targetHeight: .p480,
            preserveAspectRatio: true,
            enableLookupCache: true
        )
        require(
            youtubeFallbackDraft.sourceLanguage == "English",
            "YouTube draft should fall back to global input language without subtitle language"
        )

        let input = PipelineInputPayload(
            inputFile: "books/demo.epub",
            baseOutputFile: "demo/sk",
            inputLanguage: "en",
            targetLanguages: ["sk", "de", "fr"],
            sentencesPerOutputFile: 12,
            stitchFull: true,
            generateAudio: false,
            audioMode: "2",
            audioBitrateKbps: 32,
            writtenMode: "3",
            selectedVoice: "macOS-auto-male",
            voiceOverrides: [
                "sk": "piper-auto",
                "de": "piper-auto",
                "fr": "piper-auto",
            ],
            outputHtml: true,
            outputPdf: true,
            includeTransliteration: true,
            translationProvider: "googletrans",
            translationBatchSize: 6,
            transliterationMode: "python",
            enableLookupCache: true,
            lookupCacheBatchSize: 8,
            tempo: 1.7,
            bookMetadata: [
                "book_title": .string("Demo Book"),
                "book_genre": .string("technical, reference"),
                "book_genres": .array([.string("technical"), .string("reference")]),
                "book_language": .string("English"),
                "language": .string("English"),
                "book_year": .string("2026"),
                "isbn": .string("9780140328721"),
                "book_isbn": .string("9780140328721"),
                "book_summary": .string("A portable creation flow."),
                "book_cover_file": .string("covers/native.jpg"),
                "chapter_count": .number(3),
                "indexed": .bool(true),
            ]
        )
        let pipeline = PipelineRequestPayload(
            config: [
                "book_title": .string("Demo Book"),
                "book_genre": .string("technical, reference"),
                "book_genres": .array([.string("technical"), .string("reference")]),
                "book_language": .string("English"),
                "book_year": .string("2026"),
                "book_isbn": .string("9780140328721"),
                "book_summary": .string("A portable creation flow."),
                "book_cover_file": .string("covers/native.jpg")
            ],
            environmentOverrides: ["BOOKS_DIR": .string("/runtime/books")],
            pipelineOverrides: [
                "image_prompt_context_sentences": .number(4),
                "image_prompt_pipeline": .string("visual_canon"),
                "image_prompt_batching_enabled": .bool(false),
                "image_prompt_batch_size": .number(8),
                "image_prompt_plan_batch_size": .number(16),
                "image_style_template": .string("children_book"),
                "image_width": .string("768"),
                "image_height": .string("512"),
                "image_steps": .number(28),
                "image_cfg_scale": .number(7.5),
                "image_sampler_name": .string("dpmpp_2m"),
                "image_seed_with_previous_image": .bool(true),
                "image_blank_detection_enabled": .bool(true),
                "image_api_base_urls": .array([
                    .string("http://192.168.1.9:7860"),
                    .string("http://192.168.1.76:7860"),
                ]),
                "image_api_base_url": .string("http://192.168.1.9:7860"),
                "image_concurrency": .number(4),
                "image_api_timeout_seconds": .number(300),
                "thread_count": .number(3),
                "queue_size": .number(5),
                "job_max_workers": .number(2),
                "ollama_model": .string("gpt-4.1-mini"),
                "voice_overrides": .object([
                    "sk": .string("piper-auto"),
                    "de": .string("piper-auto"),
                    "fr": .string("piper-auto"),
                ]),
                "tempo": .number(1.08)
            ],
            inputs: input,
            correlationId: "apple-smoke"
        )
        let pipelineObject = try jsonObject(from: encoder.encode(pipeline))
        require(pipelineObject["environment_overrides"] != nil, "pipeline should encode environment_overrides")
        require(pipelineObject["pipeline_overrides"] != nil, "pipeline should encode pipeline_overrides")
        require(pipelineObject["correlation_id"] as? String == "apple-smoke", "pipeline should encode correlation_id")
        let config = pipelineObject["config"] as? [String: Any]
        require(config?["book_genre"] as? String == "technical, reference", "pipeline config should encode metadata genre")
        require(
            config?["book_genres"] as? [String] == ["technical", "reference"],
            "pipeline config should encode metadata genre list"
        )
        require(config?["book_language"] as? String == "English", "pipeline config should encode metadata language")
        require(config?["book_summary"] as? String == "A portable creation flow.", "pipeline config should encode metadata summary")
        require(config?["book_year"] as? String == "2026", "pipeline config should encode metadata year")
        require(config?["book_isbn"] as? String == "9780140328721", "pipeline config should encode metadata ISBN")
        require(config?["book_cover_file"] as? String == "covers/native.jpg", "pipeline config should encode cover file")
        let pipelineOverrides = pipelineObject["pipeline_overrides"] as? [String: Any]
        require(
            pipelineOverrides?["image_style_template"] as? String == "children_book",
            "pipeline overrides should encode selected image style"
        )
        require(
            pipelineOverrides?["image_prompt_pipeline"] as? String == "visual_canon",
            "pipeline overrides should encode selected image prompt pipeline"
        )
        require(
            pipelineOverrides?["image_prompt_context_sentences"] as? Int == 4,
            "pipeline overrides should encode selected image prompt context"
        )
        require(
            pipelineOverrides?["image_prompt_batching_enabled"] as? Bool == false,
            "pipeline overrides should encode selected image prompt batching toggle"
        )
        require(
            pipelineOverrides?["image_prompt_batch_size"] as? Int == 8,
            "pipeline overrides should encode selected image prompt batch size"
        )
        require(
            pipelineOverrides?["image_prompt_plan_batch_size"] as? Int == 16,
            "pipeline overrides should encode selected image prompt plan batch size"
        )
        require(
            pipelineOverrides?["image_width"] as? String == "768",
            "pipeline overrides should encode selected image width"
        )
        require(
            pipelineOverrides?["image_height"] as? String == "512",
            "pipeline overrides should encode selected image height"
        )
        require(
            pipelineOverrides?["image_steps"] as? Int == 28,
            "pipeline overrides should encode selected image steps"
        )
        require(
            (pipelineOverrides?["image_cfg_scale"] as? NSNumber)?.doubleValue == 7.5,
            "pipeline overrides should encode selected CFG scale"
        )
        require(
            pipelineOverrides?["image_sampler_name"] as? String == "dpmpp_2m",
            "pipeline overrides should encode selected sampler name"
        )
        require(
            pipelineOverrides?["image_seed_with_previous_image"] as? Bool == true,
            "pipeline overrides should encode previous-image seed toggle"
        )
        require(
            pipelineOverrides?["image_blank_detection_enabled"] as? Bool == true,
            "pipeline overrides should encode blank-detection toggle"
        )
        require(
            pipelineOverrides?["image_api_base_urls"] as? [String] == [
                "http://192.168.1.9:7860",
                "http://192.168.1.76:7860",
            ],
            "pipeline overrides should encode selected image API URLs"
        )
        require(
            pipelineOverrides?["image_api_base_url"] as? String == "http://192.168.1.9:7860",
            "pipeline overrides should encode primary image API URL"
        )
        require(
            pipelineOverrides?["image_concurrency"] as? Int == 4,
            "pipeline overrides should encode selected image concurrency"
        )
        require(
            pipelineOverrides?["image_api_timeout_seconds"] as? Int == 300,
            "pipeline overrides should encode selected image API timeout"
        )
        require(
            pipelineOverrides?["thread_count"] as? Int == 3,
            "pipeline overrides should encode selected worker threads"
        )
        require(
            pipelineOverrides?["queue_size"] as? Int == 5,
            "pipeline overrides should encode selected queue size"
        )
        require(
            pipelineOverrides?["job_max_workers"] as? Int == 2,
            "pipeline overrides should encode selected job worker cap"
        )
        require(
            pipelineOverrides?["ollama_model"] as? String == "gpt-4.1-mini",
            "pipeline overrides should encode selected book LLM model"
        )
        require(
            pipelineOverrides?["voice_overrides"] as? [String: String] == [
                "sk": "piper-auto",
                "de": "piper-auto",
                "fr": "piper-auto",
            ],
            "pipeline overrides should encode target-language voice overrides"
        )

        let encodedInputs = pipelineObject["inputs"] as? [String: Any]
        require(encodedInputs?["input_file"] as? String == "books/demo.epub", "pipeline inputs should encode input_file")
        require(
            encodedInputs?["target_languages"] as? [String] == ["sk", "de", "fr"],
            "pipeline inputs should encode multiple target_languages"
        )
        require(encodedInputs?["sentences_per_output_file"] as? Int == 12, "pipeline inputs should encode sentence count")
        require(encodedInputs?["stitch_full"] as? Bool == true, "pipeline inputs should encode stitch_full")
        require(encodedInputs?["generate_audio"] as? Bool == false, "pipeline inputs should encode generate_audio")
        require(encodedInputs?["audio_mode"] as? String == "2", "pipeline inputs should encode audio_mode")
        require(encodedInputs?["audio_bitrate_kbps"] as? Int == 32, "pipeline inputs should encode audio_bitrate_kbps")
        require(encodedInputs?["written_mode"] as? String == "3", "pipeline inputs should encode written_mode")
        require(encodedInputs?["selected_voice"] as? String == "macOS-auto-male", "pipeline inputs should encode selected_voice")
        require(
            encodedInputs?["voice_overrides"] as? [String: String] == [
                "sk": "piper-auto",
                "de": "piper-auto",
                "fr": "piper-auto",
            ],
            "pipeline inputs should encode target-language voice overrides"
        )
        require(encodedInputs?["output_html"] as? Bool == true, "pipeline inputs should encode output_html")
        require(encodedInputs?["output_pdf"] as? Bool == true, "pipeline inputs should encode output_pdf")
        require(encodedInputs?["translation_provider"] as? String == "googletrans", "pipeline inputs should encode provider")
        require(encodedInputs?["translation_batch_size"] as? Int == 6, "pipeline inputs should encode translation batch")
        require(encodedInputs?["transliteration_mode"] as? String == "python", "pipeline inputs should encode transliteration mode")
        require(encodedInputs?["lookup_cache_batch_size"] as? Int == 8, "pipeline inputs should encode lookup batch")
        require((encodedInputs?["tempo"] as? NSNumber)?.doubleValue == 1.7, "pipeline inputs should encode tempo")
        let metadata = encodedInputs?["book_metadata"] as? [String: Any]
        require(metadata?["book_title"] as? String == "Demo Book", "pipeline inputs should encode book_metadata")
        require(metadata?["book_genre"] as? String == "technical, reference", "pipeline inputs should encode metadata genre")
        require(
            metadata?["book_genres"] as? [String] == ["technical", "reference"],
            "pipeline inputs should encode metadata genre list"
        )
        require(metadata?["book_language"] as? String == "English", "pipeline inputs should encode metadata language")
        require(metadata?["language"] as? String == "English", "pipeline inputs should encode language alias")
        require(metadata?["book_year"] as? String == "2026", "pipeline inputs should encode metadata year")
        require(metadata?["isbn"] as? String == "9780140328721", "pipeline inputs should encode ISBN")
        require(metadata?["book_isbn"] as? String == "9780140328721", "pipeline inputs should encode metadata ISBN")
        require(metadata?["book_cover_file"] as? String == "covers/native.jpg", "pipeline inputs should encode cover file")

        let narrateInput = PipelineInputPayload(
            inputFile: "ebooks/imports/demo.epub",
            baseOutputFile: "apple/demo-narration",
            inputLanguage: "English",
            targetLanguages: ["Arabic"],
            sentencesPerOutputFile: options.pipelineDefaults.sentencesPerOutputFile,
            startSentence: narrateDraft.startSentence,
            endSentence: narrateDraft.endSentence,
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
                "book_language": .string("English"),
                "language": .string("English"),
                "book_summary": .string("Imported EPUB summary."),
                "book_year": .string("2025"),
                "isbn": .string("9780000000002"),
                "book_isbn": .string("9780000000002"),
                "book_cover_file": .string("covers/imported.jpg"),
            ]
        )
        let narratePipeline = PipelineRequestPayload(
            config: [
                "book_language": .string("English"),
                "book_summary": .string("Imported EPUB summary."),
                "book_year": .string("2025"),
                "book_isbn": .string("9780000000002"),
                "book_cover_file": .string("covers/imported.jpg"),
            ],
            inputs: narrateInput,
            correlationId: "apple-narrate-ebook"
        )
        let narrateObject = try jsonObject(from: encoder.encode(narratePipeline))
        require(
            narrateObject["correlation_id"] as? String == "apple-narrate-ebook",
            "narrate pipeline should encode correlation_id"
        )
        let narrateConfig = narrateObject["config"] as? [String: Any]
        require(
            narrateConfig?["book_language"] as? String == "English",
            "narrate pipeline config should encode metadata language"
        )
        require(
            narrateConfig?["book_summary"] as? String == "Imported EPUB summary.",
            "narrate pipeline config should encode metadata summary"
        )
        require(
            narrateConfig?["book_year"] as? String == "2025",
            "narrate pipeline config should encode metadata year"
        )
        require(
            narrateConfig?["book_isbn"] as? String == "9780000000002",
            "narrate pipeline config should encode metadata ISBN"
        )
        require(
            narrateConfig?["book_cover_file"] as? String == "covers/imported.jpg",
            "narrate pipeline config should encode cover file"
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
            narrateInputs?["start_sentence"] as? Int == 7,
            "narrate pipeline should encode selected start sentence"
        )
        require(
            narrateInputs?["end_sentence"] as? Int == 7,
            "narrate pipeline should encode selected end sentence"
        )
        require(
            narrateInputs?["selected_voice"] as? String == "macOS-auto-male",
            "narrate pipeline should keep backend default voice"
        )
        require(
            narrateInputs?["enable_lookup_cache"] as? Bool == true,
            "narrate pipeline should keep backend lookup-cache default"
        )
        let narrateMetadata = narrateInputs?["book_metadata"] as? [String: Any]
        require(
            narrateMetadata?["book_language"] as? String == "English",
            "narrate pipeline metadata should encode language"
        )
        require(
            narrateMetadata?["language"] as? String == "English",
            "narrate pipeline metadata should encode language alias"
        )
        require(
            narrateMetadata?["book_summary"] as? String == "Imported EPUB summary.",
            "narrate pipeline metadata should encode summary"
        )
        require(
            narrateMetadata?["book_year"] as? String == "2025",
            "narrate pipeline metadata should encode year"
        )
        require(
            narrateMetadata?["isbn"] as? String == "9780000000002",
            "narrate pipeline metadata should encode ISBN"
        )
        require(
            narrateMetadata?["book_isbn"] as? String == "9780000000002",
            "narrate pipeline metadata should encode book_isbn"
        )
        require(
            narrateMetadata?["book_cover_file"] as? String == "covers/imported.jpg",
            "narrate pipeline metadata should encode cover file"
        )

        let book = BookGenerationJobSubmission(
            generator: BookGenerationRequest(
                topic: "Portable Apple clients",
                bookName: "Native Creation",
                genre: "technical",
                outputLanguage: "sk",
                sourceBookTitle: "Inferno",
                sourceBookAuthor: "Dan Brown",
                sourceBookGenre: "Conspiracy thriller",
                sourceBookSummary: "A symbologist follows clues across Europe."
            ),
            pipeline: pipeline
        )
        let bookObject = try jsonObject(from: encoder.encode(book))
        let generator = bookObject["generator"] as? [String: Any]
        require(generator?["book_name"] as? String == "Native Creation", "book generator should encode book_name")
        require(generator?["num_sentences"] as? Int == 10, "book generator should keep default sentence count")
        require(generator?["source_book_title"] as? String == "Inferno", "book generator should encode source_book_title")
        require(generator?["source_book_author"] as? String == "Dan Brown", "book generator should encode source_book_author")
        require(generator?["source_book_genre"] as? String == "Conspiracy thriller", "book generator should encode source_book_genre")
        require(
            generator?["source_book_summary"] as? String == "A symbologist follows clues across Europe.",
            "book generator should encode source_book_summary"
        )
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

    private static func submitState(
        hasConfiguration: Bool = true,
        mode: AppleCreateMode,
        topic: String = "",
        bookName: String = "",
        genre: String = "",
        hasNarrateLocalFile: Bool = false,
        sourcePath: String = "",
        sourceBaseOutput: String = "",
        hasSubtitleLocalFile: Bool = false,
        subtitleSourcePath: String = "",
        youtubeVideoPath: String = "",
        youtubeSubtitlePath: String = ""
    ) -> AppleCreateSubmitState {
        AppleCreateSubmitState(
            hasConfiguration: hasConfiguration,
            mode: mode,
            topic: topic,
            bookName: bookName,
            genre: genre,
            hasNarrateLocalFile: hasNarrateLocalFile,
            sourcePath: sourcePath,
            sourceBaseOutput: sourceBaseOutput,
            hasSubtitleLocalFile: hasSubtitleLocalFile,
            subtitleSourcePath: subtitleSourcePath,
            youtubeVideoPath: youtubeVideoPath,
            youtubeSubtitlePath: youtubeSubtitlePath
        )
    }

    private static func require(_ condition: Bool, _ message: String) {
        if !condition {
            fputs("check failed: \(message)\n", stderr)
            exit(1)
        }
    }

    private static func requireURL(_ url: URL?, _ message: String) throws -> URL {
        guard let url else {
            throw CheckFailure(message)
        }
        return url
    }
}

private struct CheckFailure: Error, CustomStringConvertible {
    let description: String

    init(_ description: String) {
        self.description = description
    }
}
