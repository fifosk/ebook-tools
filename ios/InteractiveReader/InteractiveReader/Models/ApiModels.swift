import Foundation

struct PipelineMediaResponse: Decodable {
    let media: [String: [PipelineMediaFile]]
    let chunks: [PipelineMediaChunk]
    let complete: Bool
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

    enum CodingKeys: String, CodingKey {
        case name
        case url
        case size
        case updatedAt = "updated_at"
        case source
        case relativePath = "relative_path"
        case path
        case chunkID = "chunk_id"
        case rangeFragment = "range_fragment"
        case startSentence = "start_sentence"
        case endSentence = "end_sentence"
        case type
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

    enum CodingKeys: String, CodingKey {
        case chunkID = "chunk_id"
        case rangeFragment = "range_fragment"
        case startSentence = "start_sentence"
        case endSentence = "end_sentence"
        case files
        case sentences
        case metadataPath = "metadata_path"
        case metadataURL = "metadata_url"
        case sentenceCount = "sentence_count"
        case audioTracks = "audio_tracks"
    }
}

struct ChunkSentenceMetadata: Decodable, Identifiable {
    var id: Int { sentenceNumber ?? UUID().hashValue }
    let sentenceNumber: Int?
    let original: ChunkSentenceVariant
    let translation: ChunkSentenceVariant?
    let transliteration: ChunkSentenceVariant?

    enum CodingKeys: String, CodingKey {
        case sentenceNumber = "sentence_number"
        case original
        case translation
        case transliteration
    }
}

struct ChunkSentenceVariant: Decodable {
    let text: String
    let tokens: [String]?
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
    let sentenceIdMixed: Int?
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
        case sentenceID = "sentence_id"
        case sentenceIdx
        case sentenceIdMixed = "sentenceId"
        case token
        case text
        case t0
        case t1
        case start
        case end
        case time
        case begin
        case stop
        case startGate = "start_gate"
        case endGate = "end_gate"
        case pauseBefore = "pause_before_ms"
        case pauseAfter = "pause_after_ms"
    }
}
