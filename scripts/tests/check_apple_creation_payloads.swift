import Foundation

@main
struct AppleCreationPayloadCheck {
    static func main() throws {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys]

        let input = PipelineInputPayload(
            inputFile: "books/demo.epub",
            baseOutputFile: "demo/sk",
            inputLanguage: "en",
            targetLanguages: ["sk"],
            sentencesPerOutputFile: 12,
            generateAudio: true,
            selectedVoice: "gTTS",
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
        let metadata = encodedInputs?["book_metadata"] as? [String: Any]
        require(metadata?["book_title"] as? String == "Demo Book", "pipeline inputs should encode book_metadata")

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
            targetLanguage: "sk",
            targetHeight: 720,
            preserveAspectRatio: true,
            enableLookupCache: true
        )
        let youtubeObject = try jsonObject(from: encoder.encode(youtube))
        require(youtubeObject["video_path"] as? String == "incoming/demo.mp4", "youtube dub should encode video_path")
        require(youtubeObject["subtitle_path"] as? String == "incoming/demo.srt", "youtube dub should encode subtitle_path")
        require(youtubeObject["target_height"] as? Int == 720, "youtube dub should encode target_height")
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
