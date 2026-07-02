import Foundation

struct JobTimingResponse: Decodable {
    struct TrackPayload: Decodable {
        let track: String
        let segments: [JobTimingEntry]
        let playbackRate: Double?

        init(track: String, segments: [JobTimingEntry] = [], playbackRate: Double? = nil) {
            self.track = track
            self.segments = segments
            self.playbackRate = playbackRate
        }

        init(from decoder: Decoder) throws {
            let container = try decoder.container(keyedBy: DynamicTimingTrackKey.self)
            track = Self.decodeIfPresent(String.self, from: container, keys: ["track"]) ?? ""
            segments = Self.decodeIfPresent([JobTimingEntry].self, from: container, keys: ["segments"]) ?? []
            playbackRate = Self.decodeIfPresent(Double.self, from: container, keys: ["playbackRate", "playback_rate"])
        }

        private static func decodeIfPresent<T: Decodable>(
            _ type: T.Type,
            from container: KeyedDecodingContainer<DynamicTimingTrackKey>,
            keys: [String]
        ) -> T? {
            for key in keys {
                guard let codingKey = DynamicTimingTrackKey(stringValue: key),
                      let value = try? container.decodeIfPresent(type, forKey: codingKey) else {
                    continue
                }
                return value
            }
            return nil
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

        init(from decoder: Decoder) throws {
            let container = try decoder.container(keyedBy: DynamicTimingTrackKey.self)
            var mixPayload: TrackPayload?
            var translationPayload: TrackPayload?
            for key in container.allKeys {
                guard let payload = try? container.decode(TrackPayload.self, forKey: key) else {
                    continue
                }
                switch canonicalTimingTrackKey(key.stringValue) {
                case "mix":
                    mixPayload = mixPayload ?? payload
                case "translation":
                    translationPayload = translationPayload ?? payload
                default:
                    continue
                }
            }
            mix = mixPayload ?? TrackPayload(track: "mix")
            translation = translationPayload ?? TrackPayload(track: "translation")
        }
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: DynamicTimingTrackKey.self)
        jobID = Self.decodeIfPresent(String.self, from: container, keys: ["jobId", "jobID", "job_id"]) ?? ""
        tracks = try Self.decodeRequired(TimingTracks.self, from: container, keys: ["tracks"])
        audio = Self.decodeIfPresent([String: AudioBinding].self, from: container, keys: ["audio"]) ?? [:]
        highlightingPolicy = Self.decodeIfPresent(
            String.self,
            from: container,
            keys: ["highlightingPolicy", "highlighting_policy"]
        )
        hasEstimatedSegments = Self.decodeIfPresent(
            Bool.self,
            from: container,
            keys: ["hasEstimatedSegments", "has_estimated_segments"]
        )
    }

    private static func decodeRequired<T: Decodable>(
        _ type: T.Type,
        from container: KeyedDecodingContainer<DynamicTimingTrackKey>,
        keys: [String]
    ) throws -> T {
        for key in keys {
            guard let codingKey = DynamicTimingTrackKey(stringValue: key),
                  let value = try? container.decode(type, forKey: codingKey) else {
                continue
            }
            return value
        }
        throw DecodingError.keyNotFound(
            DynamicTimingTrackKey(stringValue: keys.first ?? "")!,
            DecodingError.Context(
                codingPath: container.codingPath,
                debugDescription: "No value associated with any of \(keys)"
            )
        )
    }

    private static func decodeIfPresent<T: Decodable>(
        _ type: T.Type,
        from container: KeyedDecodingContainer<DynamicTimingTrackKey>,
        keys: [String]
    ) -> T? {
        for key in keys {
            guard let codingKey = DynamicTimingTrackKey(stringValue: key),
                  let value = try? container.decodeIfPresent(type, forKey: codingKey) else {
                continue
            }
            return value
        }
        return nil
    }
}

private struct DynamicTimingTrackKey: CodingKey {
    let stringValue: String
    let intValue: Int?

    init?(stringValue: String) {
        self.stringValue = stringValue
        intValue = nil
    }

    init?(intValue: Int) {
        stringValue = "\(intValue)"
        self.intValue = intValue
    }
}

private func canonicalTimingTrackKey(_ value: String) -> String {
    let normalized = value
        .trimmingCharacters(in: .whitespacesAndNewlines)
        .lowercased()
        .filter { $0.isLetter || $0.isNumber }
    if ["origtrans", "originaltranslation", "originalandtranslation", "mix"].contains(normalized) {
        return "mix"
    }
    if [
        "translation",
        "translationaudio",
        "translated",
        "translatedaudio",
        "target",
        "targetaudio",
        "dubbed",
        "dubbedaudio",
        "trans",
        "transaudio",
    ].contains(normalized) {
        return "translation"
    }
    return normalized
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
