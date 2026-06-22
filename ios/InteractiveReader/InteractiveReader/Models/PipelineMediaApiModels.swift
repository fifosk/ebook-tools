import Foundation

struct PipelineMediaResponse: Decodable {
    let media: [String: [PipelineMediaFile]]
    let chunks: [PipelineMediaChunk]
    let complete: Bool

    enum CodingKeys: String, CodingKey {
        case media
        case chunks
        case complete
    }

    init(media: [String: [PipelineMediaFile]] = [:], chunks: [PipelineMediaChunk] = [], complete: Bool = false) {
        self.media = media
        self.chunks = chunks
        self.complete = complete
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        media = (try? container.decode([String: [PipelineMediaFile]].self, forKey: .media)) ?? [:]
        chunks = (try? container.decode([PipelineMediaChunk].self, forKey: .chunks)) ?? []
        complete = (try? container.decode(Bool.self, forKey: .complete)) ?? false
    }
}

struct ChunkMetadataPayload: Decodable {
    let sentences: [ChunkSentenceMetadata]

    enum CodingKeys: String, CodingKey {
        case sentences
    }

    init(sentences: [ChunkSentenceMetadata] = []) {
        self.sentences = sentences
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        sentences = (try? container.decode([ChunkSentenceMetadata].self, forKey: .sentences)) ?? []
    }
}

struct PipelineMediaFile: Decodable, Identifiable {
    let id = UUID()
    let name: String
    let url: String?
    let size: Double?
    let updatedAt: Date?
    let source: String
    let relativePath: String?
    let path: String?
    let chunkID: String?
    let rangeFragment: String?
    let startSentence: Int?
    let endSentence: Int?
    let type: String?

    // Note: Using convertFromSnakeCase decoder strategy, so CodingKeys should use
    // camelCase raw values. The decoder converts JSON snake_case to camelCase automatically.
    enum CodingKeys: String, CodingKey {
        case name
        case url
        case size
        case updatedAt
        case source
        case relativePath
        case path
        case chunkID = "chunkId"  // Swift property is chunkID but JSON has chunk_id -> chunkId
        case rangeFragment
        case startSentence
        case endSentence
        case type
    }

    init(
        name: String,
        url: String?,
        size: Double?,
        updatedAt: Date?,
        source: String,
        relativePath: String?,
        path: String?,
        chunkID: String?,
        rangeFragment: String?,
        startSentence: Int?,
        endSentence: Int?,
        type: String?
    ) {
        self.name = name
        self.url = url
        self.size = size
        self.updatedAt = updatedAt
        self.source = source
        self.relativePath = relativePath
        self.path = path
        self.chunkID = chunkID
        self.rangeFragment = rangeFragment
        self.startSentence = startSentence
        self.endSentence = endSentence
        self.type = type
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        name = (try? container.decode(String.self, forKey: .name)) ?? "media"
        url = try? container.decode(String.self, forKey: .url)
        if let sizeValue = try? container.decode(Double.self, forKey: .size) {
            size = sizeValue
        } else if let sizeValue = try? container.decode(Int.self, forKey: .size) {
            size = Double(sizeValue)
        } else {
            size = nil
        }
        if let dateValue = try? container.decode(Date.self, forKey: .updatedAt) {
            updatedAt = dateValue
        } else if let dateString = try? container.decode(String.self, forKey: .updatedAt) {
            updatedAt = ISO8601DateFormatter.withFractionalSeconds.date(from: dateString)
        } else {
            updatedAt = nil
        }
        source = (try? container.decode(String.self, forKey: .source)) ?? "completed"
        relativePath = try? container.decode(String.self, forKey: .relativePath)
        path = try? container.decode(String.self, forKey: .path)
        chunkID = try? container.decode(String.self, forKey: .chunkID)
        rangeFragment = try? container.decode(String.self, forKey: .rangeFragment)
        startSentence = try? container.decode(Int.self, forKey: .startSentence)
        endSentence = try? container.decode(Int.self, forKey: .endSentence)
        type = try? container.decode(String.self, forKey: .type)
    }
}

struct PipelineMediaChunk: Decodable, Identifiable {
    var id: String { chunkID ?? UUID().uuidString }
    let chunkID: String?
    let rangeFragment: String?
    let startSentence: Int?
    let endSentence: Int?
    let files: [PipelineMediaFile]
    let sentences: [ChunkSentenceMetadata]
    let metadataPath: String?
    let metadataURL: String?
    let sentenceCount: Int?
    let audioTracks: [String: AudioTrackMetadata]
    let timingTracks: [String: [[String: JSONValue]]]?
    /// Timing version - "2" means pre-scaled timing from backend (no client-side scaling needed)
    let timingVersion: String?

    enum CodingKeys: String, CodingKey {
        case chunkID = "chunkId"
        case rangeFragment
        case startSentence
        case endSentence
        case files
        case sentences
        case metadataPath
        case metadataURL = "metadataUrl"
        case sentenceCount
        case audioTracks
        case timingTracks
        case timingVersion
    }

    init(
        chunkID: String?,
        rangeFragment: String?,
        startSentence: Int?,
        endSentence: Int?,
        files: [PipelineMediaFile],
        sentences: [ChunkSentenceMetadata],
        metadataPath: String?,
        metadataURL: String?,
        sentenceCount: Int?,
        audioTracks: [String: AudioTrackMetadata],
        timingTracks: [String: [[String: JSONValue]]]? = nil,
        timingVersion: String? = nil
    ) {
        self.chunkID = chunkID
        self.rangeFragment = rangeFragment
        self.startSentence = startSentence
        self.endSentence = endSentence
        self.files = files
        self.sentences = sentences
        self.metadataPath = metadataPath
        self.metadataURL = metadataURL
        self.sentenceCount = sentenceCount
        self.audioTracks = audioTracks
        self.timingTracks = timingTracks
        self.timingVersion = timingVersion
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        chunkID = try? container.decode(String.self, forKey: .chunkID)
        rangeFragment = try? container.decode(String.self, forKey: .rangeFragment)
        startSentence = try? container.decode(Int.self, forKey: .startSentence)
        endSentence = try? container.decode(Int.self, forKey: .endSentence)
        files = (try? container.decode([PipelineMediaFile].self, forKey: .files)) ?? []
        sentences = (try? container.decode([ChunkSentenceMetadata].self, forKey: .sentences)) ?? []
        metadataPath = try? container.decode(String.self, forKey: .metadataPath)
        metadataURL = try? container.decode(String.self, forKey: .metadataURL)
        sentenceCount = try? container.decode(Int.self, forKey: .sentenceCount)
        audioTracks = (try? container.decode([String: AudioTrackMetadata].self, forKey: .audioTracks)) ?? [:]
        timingTracks = try? container.decode([String: [[String: JSONValue]]].self, forKey: .timingTracks)
        timingVersion = try? container.decode(String.self, forKey: .timingVersion)
    }
}

struct ChunkSentenceMetadata: Decodable, Identifiable {
    var id: Int { sentenceNumber ?? UUID().hashValue }
    let sentenceNumber: Int?
    let original: ChunkSentenceVariant
    let translation: ChunkSentenceVariant?
    let transliteration: ChunkSentenceVariant?
    let imagePath: String?
    let timeline: [ChunkSentenceTimelineEvent]
    let totalDuration: Double?
    let highlightGranularity: String?
    let counts: [String: Int]
    let phaseDurations: ChunkSentencePhaseDurations?
    // Sentence gate fields for sequence playback
    let startGate: Double?
    let endGate: Double?
    let originalStartGate: Double?
    let originalEndGate: Double?

    enum CodingKeys: String, CodingKey {
        case sentenceNumber = "sentenceNumber"
        case original
        case translation
        case transliteration
        case imagePath = "imagePath"
        case timeline
        case totalDuration = "totalDuration"
        case highlightGranularity = "highlightGranularity"
        case counts
        case phaseDurations = "phaseDurations"
        case startGate = "startGate"
        case endGate = "endGate"
        case originalStartGate = "originalStartGate"
        case originalEndGate = "originalEndGate"
    }

    init(sentenceNumber: Int?, original: ChunkSentenceVariant, translation: ChunkSentenceVariant?, transliteration: ChunkSentenceVariant?) {
        self.sentenceNumber = sentenceNumber
        self.original = original
        self.translation = translation
        self.transliteration = transliteration
        imagePath = nil
        timeline = []
        totalDuration = nil
        highlightGranularity = nil
        counts = [:]
        phaseDurations = nil
        startGate = nil
        endGate = nil
        originalStartGate = nil
        originalEndGate = nil
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        sentenceNumber = try? container.decode(Int.self, forKey: .sentenceNumber)

        let originalValue = try? container.decode(ChunkSentenceVariant.self, forKey: .original)
        let translationValue = try? container.decode(ChunkSentenceVariant.self, forKey: .translation)
        let transliterationValue = try? container.decode(ChunkSentenceVariant.self, forKey: .transliteration)

        if let originalValue {
            original = originalValue
        } else if let translationValue {
            original = translationValue
        } else {
            original = ChunkSentenceVariant(text: "", tokens: nil)
        }

        translation = translationValue
        transliteration = transliterationValue

        imagePath = (try? container.decode(String.self, forKey: .imagePath))?.nonEmptyValue

        timeline = (try? container.decode([ChunkSentenceTimelineEvent].self, forKey: .timeline)) ?? []
        totalDuration = try? container.decode(Double.self, forKey: .totalDuration)
        highlightGranularity = try? container.decode(String.self, forKey: .highlightGranularity)
        counts = (try? container.decode([String: Int].self, forKey: .counts)) ?? [:]
        phaseDurations = try? container.decode(ChunkSentencePhaseDurations.self, forKey: .phaseDurations)
        startGate = try? container.decode(Double.self, forKey: .startGate)
        endGate = try? container.decode(Double.self, forKey: .endGate)
        originalStartGate = try? container.decode(Double.self, forKey: .originalStartGate)
        originalEndGate = try? container.decode(Double.self, forKey: .originalEndGate)
    }
}

struct ChunkSentenceVariant: Decodable {
    let text: String
    let tokens: [String]?

    enum CodingKeys: String, CodingKey {
        case text
        case tokens
    }

    init(text: String, tokens: [String]?) {
        self.text = text
        self.tokens = tokens
    }

    init(from decoder: Decoder) throws {
        if let singleContainer = try? decoder.singleValueContainer(),
           let textValue = try? singleContainer.decode(String.self) {
            text = textValue
            tokens = nil
            return
        }

        let container = try decoder.container(keyedBy: CodingKeys.self)
        text = (try? container.decode(String.self, forKey: .text)) ?? ""
        tokens = try? container.decode([String].self, forKey: .tokens)
    }
}

struct ChunkSentenceTimelineEvent: Decodable {
    let duration: Double
    let originalIndex: Int
    let translationIndex: Int
    let transliterationIndex: Int

    enum CodingKeys: String, CodingKey {
        case duration
        case originalIndex = "original_index"
        case translationIndex = "translation_index"
        case transliterationIndex = "transliteration_index"
        case originalIndexCamel = "originalIndex"
        case translationIndexCamel = "translationIndex"
        case transliterationIndexCamel = "transliterationIndex"
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        duration = (try? container.decode(Double.self, forKey: .duration)) ?? 0
        originalIndex = (try? container.decode(Int.self, forKey: .originalIndex))
            ?? (try? container.decode(Int.self, forKey: .originalIndexCamel))
            ?? 0
        translationIndex = (try? container.decode(Int.self, forKey: .translationIndex))
            ?? (try? container.decode(Int.self, forKey: .translationIndexCamel))
            ?? 0
        transliterationIndex = (try? container.decode(Int.self, forKey: .transliterationIndex))
            ?? (try? container.decode(Int.self, forKey: .transliterationIndexCamel))
            ?? 0
    }
}

struct ChunkSentencePhaseDurations: Decodable {
    let original: Double?
    let translation: Double?
    let gap: Double?
    let tail: Double?

    enum CodingKeys: String, CodingKey {
        case original
        case translation
        case gap
        case tail
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        original = try? container.decode(Double.self, forKey: .original)
        translation = try? container.decode(Double.self, forKey: .translation)
        gap = try? container.decode(Double.self, forKey: .gap)
        tail = try? container.decode(Double.self, forKey: .tail)
    }
}

struct AudioTrackMetadata: Decodable {
    let path: String?
    let url: String?
    let duration: Double?
    let sampleRate: Int?

    enum CodingKeys: String, CodingKey {
        case path
        case url
        case duration
        case sampleRate = "sampleRate"
    }
}

struct JobTimingResponse: Decodable {
    struct TrackPayload: Decodable {
        let track: String
        let segments: [JobTimingEntry]
        let playbackRate: Double?

        enum CodingKeys: String, CodingKey {
            case track
            case segments
            case playbackRate = "playback_rate"
        }
    }

    struct AudioBinding: Decodable {
        let track: String
        let available: Bool?
    }

    let jobID: String
    let tracks: TimingTracks
    let audio: [String: AudioBinding]
    let highlightingPolicy: String?
    let hasEstimatedSegments: Bool?

    struct TimingTracks: Decodable {
        let mix: TrackPayload
        let translation: TrackPayload
    }

    enum CodingKeys: String, CodingKey {
        case jobID = "job_id"
        case tracks
        case audio
        case highlightingPolicy = "highlighting_policy"
        case hasEstimatedSegments = "has_estimated_segments"
    }
}

struct JobTimingEntry: Decodable, Identifiable {
    var id: String { rawID ?? UUID().uuidString }
    let rawID: String?
    let sentenceID: String?
    let sentenceIdx: Int?
    let token: String?
    let text: String?
    let t0: Double?
    let t1: Double?
    let start: Double?
    let end: Double?
    let time: Double?
    let begin: Double?
    let stop: Double?
    let startGate: Double?
    let endGate: Double?
    let pauseBefore: Double?
    let pauseAfter: Double?

    enum CodingKeys: String, CodingKey {
        case rawID = "id"
        case sentenceID = "sentenceId"
        case sentenceIdx
        case token
        case text
        case t0
        case t1
        case start
        case end
        case time
        case begin
        case stop
        case startGate = "startGate"
        case endGate = "endGate"
        case pauseBefore = "pauseBeforeMs"
        case pauseAfter = "pauseAfterMs"
    }
}

private extension ISO8601DateFormatter {
    static let withFractionalSeconds: ISO8601DateFormatter = {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return formatter
    }()
}
