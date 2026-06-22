import Foundation

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
