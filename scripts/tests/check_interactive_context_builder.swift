import Darwin
import Foundation

enum JSONValue: Codable, Hashable {
    case string(String)
    case number(Double)
    case bool(Bool)
    case object([String: JSONValue])
    case array([JSONValue])
    case null

    init(from decoder: Decoder) throws {
        if let container = try? decoder.singleValueContainer() {
            if container.decodeNil() {
                self = .null
                return
            }
            if let value = try? container.decode(Bool.self) {
                self = .bool(value)
                return
            }
            if let value = try? container.decode(Double.self) {
                self = .number(value)
                return
            }
            if let value = try? container.decode(String.self) {
                self = .string(value)
                return
            }
            if let value = try? container.decode([String: JSONValue].self) {
                self = .object(value)
                return
            }
            if let value = try? container.decode([JSONValue].self) {
                self = .array(value)
                return
            }
        }
        self = .null
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        switch self {
        case .string(let value):
            try container.encode(value)
        case .number(let value):
            try container.encode(value)
        case .bool(let value):
            try container.encode(value)
        case .object(let value):
            try container.encode(value)
        case .array(let value):
            try container.encode(value)
        case .null:
            try container.encodeNil()
        }
    }
}

enum LanguageFlagRole: String {
    case original
    case translation
}

struct LanguageFlagEntry: Identifiable, Equatable {
    let role: LanguageFlagRole
    let emoji: String
    let label: String
    let shortLabel: String
    let accessibilityLabel: String

    var id: String {
        "\(role.rawValue)-\(emoji)"
    }
}

struct MediaURLResolver {
    func resolveAudioURL(jobId _: String, track: AudioTrackMetadata) -> URL? {
        if let url = track.url.flatMap(URL.init(string:)) {
            return url
        }
        if let path = track.path, !path.isEmpty {
            return URL(fileURLWithPath: path)
        }
        return nil
    }

    func resolveFileURL(jobId _: String, file: PipelineMediaFile) -> URL? {
        if let url = file.url.flatMap(URL.init(string:)) {
            return url
        }
        if let path = file.path ?? file.relativePath, !path.isEmpty {
            return URL(fileURLWithPath: path)
        }
        return nil
    }
}

private func fail(_ message: String) -> Never {
    fputs("Interactive context builder check failed: \(message)\n", stderr)
    exit(1)
}

private func require(_ condition: @autoclosure () -> Bool, _ message: String) {
    if !condition() {
        fail(message)
    }
}

private func requireEqual<T: Equatable>(_ actual: T, _ expected: T, _ message: String) {
    if actual != expected {
        fail("\(message). Expected \(expected), got \(actual).")
    }
}

private func requireApprox(_ actual: Double, _ expected: Double, _ message: String, tolerance: Double = 0.0001) {
    if abs(actual - expected) > tolerance {
        fail("\(message). Expected \(expected), got \(actual).")
    }
}

private func decodeFixture() throws -> PipelineMediaResponse {
    let data = Data(
        """
        {
          "complete": true,
          "media": {},
          "chunks": [
            {
              "chunkId": "chunk_0000",
              "rangeFragment": "02180-02181",
              "startSentence": 2180,
              "endSentence": 2181,
              "files": [],
              "sentences": [
                {
                  "sentenceNumber": 2180,
                  "original": {
                    "text": "The atrium fell silent.",
                    "tokens": ["The", "atrium", "fell", "silent."]
                  },
                  "translation": {
                    "text": "Het atrium werd stil.",
                    "tokens": ["Het", "atrium", "werd", "stil."]
                  },
                  "totalDuration": 1.0,
                  "startGate": 0.0,
                  "endGate": 1.0,
                  "originalStartGate": 0.0,
                  "originalEndGate": 0.8
                },
                {
                  "sentenceNumber": 2181,
                  "original": {
                    "text": "Langdon kept moving.",
                    "tokens": ["Langdon", "kept", "moving."]
                  },
                  "translation": {
                    "text": "Langdon bleef lopen.",
                    "tokens": ["Langdon", "bleef", "lopen."]
                  },
                  "totalDuration": 1.2,
                  "startGate": 1.0,
                  "endGate": 2.2,
                  "originalStartGate": 0.8,
                  "originalEndGate": 1.7
                }
              ],
              "audioTracks": {},
              "timingTracks": {
                "translation": [
                  {"sentenceIdx": 0, "wordIdx": 0, "text": "Het", "start": 0.0, "end": 0.2},
                  {"sentenceIdx": 0, "wordIdx": 1, "text": "atrium", "start": 0.2, "end": 0.5},
                  {"sentenceIdx": 0, "wordIdx": 2, "text": "werd", "start": 0.5, "end": 0.75},
                  {"sentenceIdx": 0, "wordIdx": 3, "text": "stil.", "start": 0.75, "end": 1.0},
                  {"sentenceIdx": 1, "wordIdx": 0, "text": "Langdon", "start": 1.0, "end": 1.35},
                  {"sentenceIdx": 1, "wordIdx": 1, "text": "bleef", "start": 1.35, "end": 1.7},
                  {"sentenceIdx": 1, "wordIdx": 2, "text": "lopen.", "start": 1.7, "end": 2.2}
                ],
                "original": [
                  {"sentenceIdx": 0, "wordIdx": 0, "text": "The", "start": 0.0, "end": 0.2},
                  {"sentenceIdx": 0, "wordIdx": 1, "text": "atrium", "start": 0.2, "end": 0.4},
                  {"sentenceIdx": 0, "wordIdx": 2, "text": "fell", "start": 0.4, "end": 0.6},
                  {"sentenceIdx": 0, "wordIdx": 3, "text": "silent.", "start": 0.6, "end": 0.8},
                  {"sentenceIdx": 1, "wordIdx": 0, "text": "Langdon", "start": 0.8, "end": 1.1},
                  {"sentenceIdx": 1, "wordIdx": 1, "text": "kept", "start": 1.1, "end": 1.35},
                  {"sentenceIdx": 1, "wordIdx": 2, "text": "moving.", "start": 1.35, "end": 1.7}
                ]
              }
            }
          ]
        }
        """.utf8
    )
    let decoder = JSONDecoder()
    decoder.keyDecodingStrategy = .convertFromSnakeCase
    return try decoder.decode(PipelineMediaResponse.self, from: data)
}

private func decodeOutOfOrderChunksFixture() throws -> PipelineMediaResponse {
    let data = Data(
        """
        {
          "complete": true,
          "media": {},
          "chunks": [
            {
              "chunkId": "chunk_2230",
              "rangeFragment": "02230-02239",
              "startSentence": 2230,
              "endSentence": 2239,
              "sentenceCount": 10,
              "files": [],
              "sentences": [],
              "audioTracks": {}
            },
            {
              "chunkId": "chunk_2210",
              "rangeFragment": "02210-02219",
              "startSentence": 2210,
              "endSentence": 2219,
              "sentenceCount": 10,
              "files": [],
              "sentences": [],
              "audioTracks": {}
            },
            {
              "chunkId": "chunk_2220",
              "rangeFragment": "02220-02229",
              "startSentence": 2220,
              "endSentence": 2229,
              "sentenceCount": 10,
              "files": [],
              "sentences": [],
              "audioTracks": {}
            }
          ]
        }
        """.utf8
    )
    let decoder = JSONDecoder()
    decoder.keyDecodingStrategy = .convertFromSnakeCase
    return try decoder.decode(PipelineMediaResponse.self, from: data)
}

private func decodeLocalSentenceNumberFixture() throws -> PipelineMediaResponse {
    let data = Data(
        """
        {
          "complete": true,
          "media": {},
          "chunks": [
            {
              "chunkId": "chunk_2220",
              "rangeFragment": "02220-02221",
              "startSentence": 2220,
              "endSentence": 2221,
              "files": [],
              "sentences": [
                {
                  "sentence_number": 0,
                  "original": {"text": "First local row.", "tokens": ["First", "local", "row."]},
                  "translation": {"text": "Eerste lokale rij.", "tokens": ["Eerste", "lokale", "rij."]},
                  "startGate": 0.0,
                  "endGate": 1.0
                },
                {
                  "sentenceNumber": 1,
                  "original": {"text": "Second local row.", "tokens": ["Second", "local", "row."]},
                  "translation": {"text": "Tweede lokale rij.", "tokens": ["Tweede", "lokale", "rij."]},
                  "startGate": 1.0,
                  "endGate": 2.0
                }
              ],
              "audioTracks": {}
            }
          ]
        }
        """.utf8
    )
    let decoder = JSONDecoder()
    decoder.keyDecodingStrategy = .convertFromSnakeCase
    return try decoder.decode(PipelineMediaResponse.self, from: data)
}

private func decodeTranslationAudioAliasFixture() throws -> PipelineMediaResponse {
    let data = Data(
        """
        {
          "complete": true,
          "media": {},
          "chunks": [
            {
              "chunkId": "chunk_alias_tracks",
              "rangeFragment": "00001-00001",
              "startSentence": 1,
              "endSentence": 1,
              "files": [],
              "sentences": [],
              "audioTracks": {
                "OriginalAudio": {"url": "https://example.test/original.mp3", "duration": 0.8},
                "translated_audio": {"url": "https://example.test/translated.mp3", "duration": 1.1}
              }
            },
            {
              "chunkId": "chunk_alias_files",
              "rangeFragment": "00002-00002",
              "startSentence": 2,
              "endSentence": 2,
              "files": [
                {
                  "name": "target_audio.mp3",
                  "url": "https://example.test/target_audio.mp3",
                  "relativePath": "chunk_alias_files/target_audio.mp3",
                  "type": "audio"
                }
              ],
              "sentences": [],
              "audioTracks": {}
            },
            {
              "chunkId": "chunk_alias_camel_file",
              "rangeFragment": "00003-00003",
              "startSentence": 3,
              "endSentence": 3,
              "files": [
                {
                  "name": "dubbedAudio.m4a",
                  "url": "https://example.test/dubbedAudio.m4a",
                  "relativePath": "chunk_alias_camel_file/dubbedAudio.m4a",
                  "type": "audio"
                }
              ],
              "sentences": [],
              "audioTracks": {}
            }
          ]
        }
        """.utf8
    )
    let decoder = JSONDecoder()
    decoder.keyDecodingStrategy = .convertFromSnakeCase
    return try decoder.decode(PipelineMediaResponse.self, from: data)
}

private func runChecks() throws {
    let media = try decodeFixture()
    let context = try JobContextBuilder.build(
        jobId: "local-timing-fixture",
        media: media,
        timing: nil,
        resolver: MediaURLResolver(),
        tokenCache: TokenNormalizationCache()
    )

    requireEqual(context.chunks.count, 1, "Fixture should build one chunk")
    guard let chunk = context.chunks.first else {
        fail("Missing chunk after context build")
    }
    requireEqual(chunk.startSentence, 2180, "Chunk should preserve global start sentence")
    requireEqual(chunk.endSentence, 2181, "Chunk should preserve global end sentence")
    requireEqual(chunk.sentences.count, 2, "Chunk should build both sentences")

    let first = chunk.sentences[0]
    let second = chunk.sentences[1]
    requireEqual(first.id, 2180, "First sentence should keep the global sentence id")
    requireEqual(first.displayIndex, 2180, "First sentence should display the global sentence number")
    requireEqual(second.id, 2181, "Second sentence should keep the global sentence id")
    requireEqual(second.displayIndex, 2181, "Second sentence should display the global sentence number")

    requireEqual(
        first.timingTokens.map(\.text),
        ["Het", "atrium", "werd", "stil."],
        "First global sentence should bind chunk-local translation tokens"
    )
    requireEqual(
        first.timingTokens.compactMap(\.sentenceIndex),
        [0, 0, 0, 0],
        "First translation tokens should remain chunk-local"
    )
    requireEqual(
        second.timingTokens.map(\.text),
        ["Langdon", "bleef", "lopen."],
        "Second global sentence should bind chunk-local translation tokens"
    )
    requireEqual(
        second.timingTokens.compactMap(\.sentenceIndex),
        [1, 1, 1],
        "Second translation tokens should remain chunk-local"
    )

    requireEqual(
        first.originalTimingTokens.map(\.text),
        ["The", "atrium", "fell", "silent."],
        "First global sentence should bind chunk-local original tokens"
    )
    requireEqual(
        second.originalTimingTokens.map(\.text),
        ["Langdon", "kept", "moving."],
        "Second global sentence should bind chunk-local original tokens"
    )

    guard let timeline = TextPlayerTimeline.buildTimelineSentences(
        sentences: chunk.sentences,
        activeTimingTrack: .translation,
        audioDuration: 2.2,
        useCombinedPhases: false,
        timingVersion: chunk.timingVersion
    ) else {
        fail("Timeline builder returned nil for chunk-local timing fixture")
    }
    requireEqual(timeline.count, 2, "Timeline should preserve both sentence rows")
    requireEqual(timeline[0].index, 0, "First timeline row should use local row index")
    requireEqual(timeline[0].sentenceNumber, 2180, "First timeline row should preserve display sentence")
    requireEqual(timeline[1].index, 1, "Second timeline row should use local row index")
    requireEqual(timeline[1].sentenceNumber, 2181, "Second timeline row should preserve display sentence")
    requireApprox(timeline[0].startTime, 0.0, "First timeline row should start at its translation gate")
    requireApprox(timeline[0].endTime, 1.0, "First timeline row should end at its translation gate")
    requireApprox(timeline[1].startTime, 1.0, "Second timeline row should start at its translation gate")
    requireApprox(timeline[1].endTime, 2.2, "Second timeline row should end at its translation gate")

    requireEqual(
        TextPlayerTimeline.resolveActiveIndex(
            timelineSentences: timeline,
            chunkTime: 1.4,
            audioDuration: 2.2
        ),
        1,
        "Chunk-local timing should resolve the active row by rendered sentence order"
    )

    let outOfOrderMedia = try decodeOutOfOrderChunksFixture()
    let outOfOrderContext = try JobContextBuilder.build(
        jobId: "out-of-order-chunk-fixture",
        media: outOfOrderMedia,
        timing: nil,
        resolver: MediaURLResolver(),
        tokenCache: TokenNormalizationCache()
    )
    requireEqual(
        outOfOrderContext.chunks.map(\.id),
        ["chunk_2210", "chunk_2220", "chunk_2230"],
        "Playback context should sort parallel-generated chunks by sentence range"
    )
    requireEqual(
        outOfOrderContext.nextChunk(after: "chunk_2210")?.id,
        "chunk_2220",
        "Next chunk after sentence 2219 should be the 2220 batch"
    )
    requireEqual(
        outOfOrderContext.previousChunk(before: "chunk_2230")?.id,
        "chunk_2220",
        "Previous chunk before 2230 should be the 2220 batch"
    )

    let localNumberMedia = try decodeLocalSentenceNumberFixture()
    let localNumberContext = try JobContextBuilder.build(
        jobId: "local-sentence-number-fixture",
        media: localNumberMedia,
        timing: nil,
        resolver: MediaURLResolver(),
        tokenCache: TokenNormalizationCache()
    )
    guard let localNumberChunk = localNumberContext.chunks.first else {
        fail("Missing local sentence number chunk")
    }
    requireEqual(
        localNumberChunk.sentences.map(\.id),
        [2220, 2221],
        "Chunk-local sentence numbers must normalize to public sentence ids"
    )
    requireEqual(
        localNumberChunk.sentences.map(\.displayIndex),
        [2220, 2221],
        "Chunk-local sentence numbers must display as public sentence ids"
    )

    let translationAliasMedia = try decodeTranslationAudioAliasFixture()
    let translationAliasContext = try JobContextBuilder.build(
        jobId: "translation-audio-alias-fixture",
        media: translationAliasMedia,
        timing: nil,
        resolver: MediaURLResolver(),
        tokenCache: TokenNormalizationCache()
    )
    guard let aliasTrackChunk = translationAliasContext.chunk(withID: "chunk_alias_tracks") else {
        fail("Missing translated_audio alias chunk")
    }
    require(
        aliasTrackChunk.audioOptions.contains { $0.kind == .translation },
        "translated_audio metadata key should become a selectable Translation audio option"
    )
    require(
        aliasTrackChunk.audioOptions.contains { $0.kind == .combined && $0.streamURLs.count == 2 },
        "OriginalAudio plus translated_audio should synthesize a two-stream combined option"
    )
    guard let aliasFileChunk = translationAliasContext.chunk(withID: "chunk_alias_files") else {
        fail("Missing target_audio file alias chunk")
    }
    require(
        aliasFileChunk.audioOptions.contains { $0.kind == .translation && $0.label == "Translation" },
        "target_audio filename should become a selectable Translation audio option"
    )
    guard let aliasCamelFileChunk = translationAliasContext.chunk(withID: "chunk_alias_camel_file") else {
        fail("Missing dubbedAudio file alias chunk")
    }
    require(
        aliasCamelFileChunk.audioOptions.contains { $0.kind == .translation && $0.label == "Translation" },
        "camelCase dubbedAudio filename should become a selectable Translation audio option"
    )
}

@main
private struct InteractiveContextBuilderCheck {
    static func main() {
        do {
            try runChecks()
        } catch {
            fail("Unexpected error: \(error)")
        }
    }
}
