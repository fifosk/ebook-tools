import Foundation

struct SessionUserPayload: Decodable {
    let username: String
    let role: String
    let email: String?
    let firstName: String?
    let lastName: String?
    let lastLogin: String?
}

struct SessionStatusResponse: Decodable {
    let token: String
    let user: SessionUserPayload
}

struct LoginRequestPayload: Encodable {
    let username: String
    let password: String
}

struct OAuthLoginRequestPayload: Encodable {
    let provider: String
    let idToken: String
    let email: String?
    let firstName: String?
    let lastName: String?

    enum CodingKeys: String, CodingKey {
        case provider
        case idToken = "id_token"
        case email
        case firstName = "first_name"
        case lastName = "last_name"
    }
}

struct AssistantLookupRequest: Encodable {
    let query: String
    let inputLanguage: String
    let lookupLanguage: String
    let llmModel: String?

    enum CodingKeys: String, CodingKey {
        case query
        case inputLanguage = "input_language"
        case lookupLanguage = "lookup_language"
        case llmModel = "llm_model"
    }
}

struct AssistantLookupResponse: Decodable {
    let answer: String
    let model: String
    let tokenUsage: [String: Int]?
    let source: String?
}

struct LLMModelListResponse: Decodable {
    let models: [String]
}

struct AudioSynthesisRequest: Encodable {
    let text: String
    let voice: String?
    let speed: Int?
    let language: String?
}

struct LibrarySearchResponse: Decodable {
    let total: Int
    let page: Int
    let limit: Int
    let view: String
    let items: [LibraryItem]
    let groups: [LibraryGroup]?
}

struct LibraryGroup: Decodable, Identifiable {
    var id: String { "\(title ?? "untitled")-\(count ?? items?.count ?? 0)" }
    let title: String?
    let items: [LibraryItem]?
    let count: Int?
}

struct LibraryItem: Decodable, Identifiable {
    var id: String { jobId }
    let jobId: String
    let author: String
    let bookTitle: String
    let itemType: String
    let genre: String?
    let language: String
    let status: String
    let mediaCompleted: Bool
    let createdAt: String
    let updatedAt: String
    let libraryPath: String
    let coverPath: String?
    let isbn: String?
    let sourcePath: String?
    let metadata: [String: JSONValue]?
}

enum PipelineJobStatus: String, Decodable {
    case pending
    case running
    case pausing
    case paused
    case completed
    case failed
    case cancelled
}

struct ProgressSnapshotPayload: Decodable {
    let completed: Int
    let total: Int?
    let elapsed: Double
    let speed: Double
    let eta: Double?
}

struct ProgressEventPayload: Decodable {
    let eventType: String
    let timestamp: Double
    let metadata: [String: JSONValue]
    let snapshot: ProgressSnapshotPayload
    let error: String?
}

struct PipelineStatusResponse: Decodable, Identifiable, Hashable {
    var id: String { jobId }
    let jobId: String
    let jobType: String
    let status: PipelineJobStatus
    let createdAt: String
    let startedAt: String?
    let completedAt: String?
    let result: JSONValue?
    let error: String?
    let latestEvent: ProgressEventPayload?
    let tuning: [String: JSONValue]?
    let userId: String?
    let userRole: String?
    let generatedFiles: [String: JSONValue]?
    let parameters: JSONValue?
    let mediaCompleted: Bool?
    let retrySummary: [String: [String: Int]]?
    let jobLabel: String?
    let imageGeneration: [String: JSONValue]?

    static func == (lhs: PipelineStatusResponse, rhs: PipelineStatusResponse) -> Bool {
        lhs.jobId == rhs.jobId
    }

    func hash(into hasher: inout Hasher) {
        hasher.combine(jobId)
    }
}

struct PipelineJobListResponse: Decodable {
    let jobs: [PipelineStatusResponse]
}

struct ReadingBedEntry: Decodable, Identifiable {
    let id: String
    let label: String
    let url: String
    let kind: String?
    let contentType: String?
    let isDefault: Bool?
}

struct ReadingBedListResponse: Decodable {
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

extension LibraryItem: Hashable {
    static func == (lhs: LibraryItem, rhs: LibraryItem) -> Bool {
        lhs.jobId == rhs.jobId
    }

    func hash(into hasher: inout Hasher) {
        hasher.combine(jobId)
    }
}

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

    enum CodingKeys: String, CodingKey {
        case name
        case url
        case size
        case updatedAt
        case source
        case relativePath
        case path
        case chunkID = "chunkId"
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
        audioTracks: [String: AudioTrackMetadata]
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
    }
}

struct ChunkSentenceImage: Decodable {
    let path: String?
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

    enum CodingKeys: String, CodingKey {
        case sentenceNumber = "sentence_number"
        case sentenceNumberCamel = "sentenceNumber"
        case original
        case translation
        case transliteration
        case text
        case image
        case imagePath = "image_path"
        case imagePathCamel = "imagePath"
        case timeline
        case totalDuration = "total_duration"
        case highlightGranularity = "highlight_granularity"
        case counts
        case phaseDurations = "phase_durations"
        case totalDurationCamel = "totalDuration"
        case highlightGranularityCamel = "highlightGranularity"
        case phaseDurationsCamel = "phaseDurations"
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
    }

    init(from decoder: Decoder) throws {
        if let singleContainer = try? decoder.singleValueContainer(),
           let textValue = try? singleContainer.decode(String.self) {
            sentenceNumber = nil
            original = ChunkSentenceVariant(text: textValue, tokens: nil)
            translation = nil
            transliteration = nil
            imagePath = nil
            timeline = []
            totalDuration = nil
            highlightGranularity = nil
            counts = [:]
            phaseDurations = nil
            return
        }

        let container = try decoder.container(keyedBy: CodingKeys.self)
        sentenceNumber = (try? container.decode(Int.self, forKey: .sentenceNumber))
            ?? (try? container.decode(Int.self, forKey: .sentenceNumberCamel))

        let originalValue = try? container.decode(ChunkSentenceVariant.self, forKey: .original)
        let translationValue = try? container.decode(ChunkSentenceVariant.self, forKey: .translation)
        let transliterationValue = try? container.decode(ChunkSentenceVariant.self, forKey: .transliteration)

        if let originalValue {
            original = originalValue
        } else if let translationValue {
            original = translationValue
        } else if let textValue = try? container.decode(String.self, forKey: .text) {
            original = ChunkSentenceVariant(text: textValue, tokens: nil)
        } else {
            original = ChunkSentenceVariant(text: "", tokens: nil)
        }

        translation = translationValue
        transliteration = transliterationValue

        let imagePayload = try? container.decode(ChunkSentenceImage.self, forKey: .image)
        let imagePathValue = imagePayload?.path.flatMap { $0.nonEmptyValue }
            ?? (try? container.decode(String.self, forKey: .imagePath))?.nonEmptyValue
            ?? (try? container.decode(String.self, forKey: .imagePathCamel))?.nonEmptyValue
        imagePath = imagePathValue

        timeline = (try? container.decode([ChunkSentenceTimelineEvent].self, forKey: .timeline)) ?? []
        if let rawDuration = try? container.decode(Double.self, forKey: .totalDuration) {
            totalDuration = rawDuration
        } else if let rawDuration = try? container.decode(Double.self, forKey: .totalDurationCamel) {
            totalDuration = rawDuration
        } else {
            totalDuration = nil
        }
        highlightGranularity = (try? container.decode(String.self, forKey: .highlightGranularity))
            ?? (try? container.decode(String.self, forKey: .highlightGranularityCamel))
        counts = (try? container.decode([String: Int].self, forKey: .counts)) ?? [:]
        phaseDurations = (try? container.decode(ChunkSentencePhaseDurations.self, forKey: .phaseDurations))
            ?? (try? container.decode(ChunkSentencePhaseDurations.self, forKey: .phaseDurationsCamel))
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

private extension ISO8601DateFormatter {
    static let withFractionalSeconds: ISO8601DateFormatter = {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return formatter
    }()
}
