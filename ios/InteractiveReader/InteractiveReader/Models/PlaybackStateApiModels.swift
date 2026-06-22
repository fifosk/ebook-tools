struct ReadingBedEntry: Codable, Identifiable {
    let id: String
    let label: String
    let url: String
    let kind: String?
    let contentType: String?
    let isDefault: Bool?
}

struct ReadingBedListResponse: Codable {
    let defaultId: String?
    let beds: [ReadingBedEntry]
}

struct PlaybackBookmarkPayload: Decodable, Identifiable {
    let id: String
    let jobId: String
    let itemType: String?
    let kind: PlaybackBookmarkKind
    let createdAt: Double
    let label: String
    let position: Double?
    let sentence: Int?
    let mediaType: String?
    let mediaId: String?
    let baseId: String?
    let segmentId: String?
    let chunkId: String?
}

struct PlaybackBookmarkListResponse: Decodable {
    let jobId: String
    let bookmarks: [PlaybackBookmarkPayload]
}

struct PlaybackBookmarkCreateRequest: Encodable {
    let id: String?
    let label: String
    let kind: PlaybackBookmarkKind
    let createdAt: Double?
    let position: Double?
    let sentence: Int?
    let mediaType: String?
    let mediaId: String?
    let baseId: String?
    let segmentId: String?
    let chunkId: String?
    let itemType: String?

    enum CodingKeys: String, CodingKey {
        case id
        case label
        case kind
        case createdAt = "created_at"
        case position
        case sentence
        case mediaType = "media_type"
        case mediaId = "media_id"
        case baseId = "base_id"
        case segmentId = "segment_id"
        case chunkId = "chunk_id"
        case itemType = "item_type"
    }
}

struct PlaybackBookmarkDeleteResponse: Decodable {
    let deleted: Bool
    let bookmarkId: String
}

struct ResumePositionEntry: Decodable {
    let jobId: String
    let kind: String
    let updatedAt: Double
    let position: Double?
    let sentence: Int?
    let chunkId: String?
    let mediaType: String?
    let baseId: String?
}

struct ResumePositionResponse: Decodable {
    let jobId: String
    let entry: ResumePositionEntry?
}

struct ResumePositionSaveRequest: Encodable {
    let kind: String
    let position: Double?
    let sentence: Int?
    let chunkId: String?
    let mediaType: String?
    let baseId: String?

    enum CodingKeys: String, CodingKey {
        case kind
        case position
        case sentence
        case chunkId = "chunk_id"
        case mediaType = "media_type"
        case baseId = "base_id"
    }
}

struct ResumePositionDeleteResponse: Decodable {
    let deleted: Bool
}
