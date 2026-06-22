struct SubtitleTvMetadataParse: Decodable {
    let series: String
    let season: Int
    let episode: Int
    let pattern: String
}

struct SubtitleTvMetadataResponse: Decodable {
    let jobId: String
    let sourceName: String?
    let parsed: SubtitleTvMetadataParse?
    let mediaMetadata: [String: JSONValue]?
}

struct YoutubeVideoMetadataParse: Decodable {
    let videoId: String
    let pattern: String
}

struct YoutubeVideoMetadataResponse: Decodable {
    let jobId: String
    let sourceName: String?
    let parsed: YoutubeVideoMetadataParse?
    let youtubeMetadata: [String: JSONValue]?
}

enum JSONValue: Decodable, Hashable {
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
}
