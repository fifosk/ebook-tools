import Foundation

struct SessionUserPayload: Decodable, Equatable {
    let username: String
    let role: String
    let email: String?
    let firstName: String?
    let lastName: String?
    let lastLogin: String?
}

struct SessionStatusResponse: Decodable, Equatable {
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

// MARK: - Structured Linguist Response

enum LinguistLookupType: String, Codable {
    case word
    case phrase
    case sentence
}

struct LinguistRelatedLanguage: Codable, Identifiable {
    let language: String
    let word: String
    let transliteration: String?

    var id: String { "\(language)-\(word)" }
}

struct LinguistLookupResult: Codable {
    let type: LinguistLookupType
    let definition: String
    let partOfSpeech: String?
    let pronunciation: String?
    let etymology: String?
    let example: String?
    let exampleTranslation: String?
    let exampleTransliteration: String?
    let idioms: [String]?
    let relatedLanguages: [LinguistRelatedLanguage]?

    // NOTE: No explicit CodingKeys here!
    // When decoded via APIClient (which uses .convertFromSnakeCase), the decoder
    // automatically maps snake_case JSON keys to camelCase Swift properties.
    // When decoded via parse() for live LLM responses, we use .convertFromSnakeCase too.

    /// Attempt to parse a JSON response from the LLM answer string.
    /// Returns nil if the answer is not valid JSON or doesn't match the expected structure.
    static func parse(from answer: String) -> LinguistLookupResult? {
        // Try to extract JSON from the answer (LLM might include extra text)
        let trimmed = answer.trimmingCharacters(in: .whitespacesAndNewlines)

        // Find JSON object bounds
        guard let startIndex = trimmed.firstIndex(of: "{"),
              let endIndex = trimmed.lastIndex(of: "}") else {
            return nil
        }

        let jsonString = String(trimmed[startIndex...endIndex])
        guard let data = jsonString.data(using: .utf8) else {
            return nil
        }

        do {
            let decoder = JSONDecoder()
            // Use snake_case decoding to match the JSON format from both:
            // - Live LLM responses (snake_case keys like part_of_speech)
            // - Re-encoded cached results (also snake_case via encoder.keyEncodingStrategy)
            decoder.keyDecodingStrategy = .convertFromSnakeCase
            return try decoder.decode(LinguistLookupResult.self, from: data)
        } catch {
            print("LinguistLookupResult parse error: \(error)")
            return nil
        }
    }
}

struct LLMModelListResponse: Decodable {
    let models: [String]
}

struct MacOSVoice: Decodable {
    let name: String
    let lang: String
    let quality: String?
    let gender: String?
}

struct GTTSLanguage: Decodable {
    let code: String
    let name: String
}

struct PiperVoice: Decodable {
    let name: String
    let lang: String
    let quality: String
}

struct VoiceInventoryResponse: Decodable {
    let macos: [MacOSVoice]
    let gtts: [GTTSLanguage]
    let piper: [PiperVoice]
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
            && lhs.status == rhs.status
            && lhs.completedAt == rhs.completedAt
            && lhs.error == rhs.error
            && lhs.progressSignature == rhs.progressSignature
    }

    func hash(into hasher: inout Hasher) {
        hasher.combine(jobId)
        hasher.combine(status.rawValue)
        hasher.combine(completedAt)
        hasher.combine(error)
        if let signature = progressSignature {
            hasher.combine(signature.completed)
            hasher.combine(signature.total ?? -1)
            hasher.combine(signature.timestamp)
        } else {
            hasher.combine(0)
        }
    }

    private struct ProgressSignature: Hashable {
        let completed: Int
        let total: Int?
        let timestamp: Double
    }

    private var progressSignature: ProgressSignature? {
        guard let latestEvent else { return nil }
        return ProgressSignature(
            completed: latestEvent.snapshot.completed,
            total: latestEvent.snapshot.total,
            timestamp: latestEvent.timestamp
        )
    }
}

struct PipelineJobListResponse: Decodable {
    let jobs: [PipelineStatusResponse]
}

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

// MARK: - Resume Position

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

// MARK: - Media Search

enum MediaSearchSource: String, Decodable {
    case pipeline
    case library
}

struct MediaSearchResult: Decodable, Identifiable {
    var id: String {
        // Create unique ID using multiple fields to handle video cue results
        let chunkPart = chunkId ?? "default"
        let sentencePart = startSentence.map { String($0) } ?? "nil"
        let cuePart = cueStartSeconds.map { String(format: "%.3f", $0) } ?? "nil"
        let matchPart = matchStart.map { String($0) } ?? "nil"
        return "\(jobId)-\(chunkPart)-\(sentencePart)-\(cuePart)-\(matchPart)"
    }
    let jobId: String
    let jobLabel: String?
    let baseId: String?
    let chunkId: String?
    let chunkIndex: Int?
    let chunkTotal: Int?
    let rangeFragment: String?
    let startSentence: Int?
    let endSentence: Int?
    let snippet: String
    let occurrenceCount: Int
    let matchStart: Int?
    let matchEnd: Int?
    let textLength: Int?
    let offsetRatio: Double?
    let approximateTimeSeconds: Double?
    let cueStartSeconds: Double?
    let cueEndSeconds: Double?
    let media: [String: [PipelineMediaFile]]?
    let source: MediaSearchSource
    let libraryAuthor: String?
    let libraryGenre: String?
    let libraryLanguage: String?
    let coverPath: String?
    let libraryPath: String?

    // Note: Using convertFromSnakeCase decoder strategy, so CodingKeys should use
    // camelCase raw values (or omit explicit raw values to use case names as-is).
    // The decoder automatically converts JSON snake_case keys to camelCase before matching.
    enum CodingKeys: String, CodingKey {
        case jobId
        case jobLabel
        case baseId
        case chunkId
        case chunkIndex
        case chunkTotal
        case rangeFragment
        case startSentence
        case endSentence
        case snippet
        case occurrenceCount
        case matchStart
        case matchEnd
        case textLength
        case offsetRatio
        case approximateTimeSeconds
        case cueStartSeconds
        case cueEndSeconds
        case media
        case source
        // Library fields come as camelCase from API (alias in Python model)
        case libraryAuthor
        case libraryGenre
        case libraryLanguage
        case coverPath
        case libraryPath
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        jobId = try container.decode(String.self, forKey: .jobId)
        jobLabel = try? container.decode(String.self, forKey: .jobLabel)
        baseId = try? container.decode(String.self, forKey: .baseId)
        chunkId = try? container.decode(String.self, forKey: .chunkId)
        chunkIndex = try? container.decode(Int.self, forKey: .chunkIndex)
        chunkTotal = try? container.decode(Int.self, forKey: .chunkTotal)
        rangeFragment = try? container.decode(String.self, forKey: .rangeFragment)
        startSentence = try? container.decode(Int.self, forKey: .startSentence)
        endSentence = try? container.decode(Int.self, forKey: .endSentence)
        snippet = (try? container.decode(String.self, forKey: .snippet)) ?? ""
        occurrenceCount = (try? container.decode(Int.self, forKey: .occurrenceCount)) ?? 1
        matchStart = try? container.decode(Int.self, forKey: .matchStart)
        matchEnd = try? container.decode(Int.self, forKey: .matchEnd)
        textLength = try? container.decode(Int.self, forKey: .textLength)
        offsetRatio = try? container.decode(Double.self, forKey: .offsetRatio)
        approximateTimeSeconds = try? container.decode(Double.self, forKey: .approximateTimeSeconds)
        cueStartSeconds = try? container.decode(Double.self, forKey: .cueStartSeconds)
        cueEndSeconds = try? container.decode(Double.self, forKey: .cueEndSeconds)
        media = try? container.decode([String: [PipelineMediaFile]].self, forKey: .media)
        source = (try? container.decode(MediaSearchSource.self, forKey: .source)) ?? .pipeline
        libraryAuthor = try? container.decode(String.self, forKey: .libraryAuthor)
        libraryGenre = try? container.decode(String.self, forKey: .libraryGenre)
        libraryLanguage = try? container.decode(String.self, forKey: .libraryLanguage)
        coverPath = try? container.decode(String.self, forKey: .coverPath)
        libraryPath = try? container.decode(String.self, forKey: .libraryPath)
    }
}

struct MediaSearchResponse: Decodable {
    let query: String
    let limit: Int
    let count: Int
    let results: [MediaSearchResult]

    enum CodingKeys: String, CodingKey {
        case query
        case limit
        case count
        case results
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        query = (try? container.decode(String.self, forKey: .query)) ?? ""
        limit = (try? container.decode(Int.self, forKey: .limit)) ?? 25
        count = (try? container.decode(Int.self, forKey: .count)) ?? 0
        // Try to decode results, fall back to empty array if it fails
        // This helps detect decode issues when count > 0 but results is empty
        do {
            results = try container.decode([MediaSearchResult].self, forKey: .results)
        } catch {
            // Log the error for debugging
            print("[MediaSearchResponse] Failed to decode results: \(error)")
            results = []
        }
    }

    init(query: String, limit: Int, count: Int, results: [MediaSearchResult]) {
        self.query = query
        self.limit = limit
        self.count = count
        self.results = results
    }
}

private extension ISO8601DateFormatter {
    static let withFractionalSeconds: ISO8601DateFormatter = {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return formatter
    }()
}

// MARK: - Push Notifications

struct DeviceRegistrationRequest: Encodable {
    let token: String
    let deviceName: String
    let bundleId: String
    let environment: String

    enum CodingKeys: String, CodingKey {
        case token
        case deviceName = "device_name"
        case bundleId = "bundle_id"
        case environment
    }
}

struct DeviceRegistrationResponse: Decodable {
    let registered: Bool
    let deviceId: String?
}

struct DeviceInfo: Decodable {
    let deviceName: String
    let bundleId: String
    let environment: String
    let registeredAt: String
    let lastUsedAt: String
}

struct NotificationPreferencesRequest: Encodable {
    var jobCompleted: Bool
    var jobFailed: Bool

    enum CodingKeys: String, CodingKey {
        case jobCompleted = "job_completed"
        case jobFailed = "job_failed"
    }
}

struct NotificationPreferencesResponse: Decodable {
    let jobCompleted: Bool
    let jobFailed: Bool
    let devices: [DeviceInfo]
}

struct TestNotificationResponse: Decodable {
    let sent: Int
    let failed: Int
    let message: String?
}

// MARK: - Lookup Cache

struct LookupCacheAudioRef: Decodable, Equatable {
    let chunkId: String
    let sentenceIdx: Int
    let tokenIdx: Int
    let track: String
    let t0: Double
    let t1: Double

    enum CodingKeys: String, CodingKey {
        case chunkId
        case sentenceIdx
        case tokenIdx
        case track
        case t0
        case t1
    }
}

struct LookupCacheEntryResponse: Decodable {
    let word: String
    let wordNormalized: String
    let cached: Bool
    let lookupResult: LinguistLookupResult?
    let audioReferences: [LookupCacheAudioRef]

    enum CodingKeys: String, CodingKey {
        case word
        case wordNormalized
        case cached
        case lookupResult
        case audioReferences
    }

    /// Convenience initializer for creating cache miss responses
    init(word: String, wordNormalized: String, cached: Bool, lookupResult: LinguistLookupResult?, audioReferences: [LookupCacheAudioRef]) {
        self.word = word
        self.wordNormalized = wordNormalized
        self.cached = cached
        self.lookupResult = lookupResult
        self.audioReferences = audioReferences
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        word = try container.decode(String.self, forKey: .word)
        wordNormalized = (try? container.decode(String.self, forKey: .wordNormalized)) ?? word
        cached = (try? container.decode(Bool.self, forKey: .cached)) ?? false
        audioReferences = (try? container.decode([LookupCacheAudioRef].self, forKey: .audioReferences)) ?? []

        // Decode lookupResult directly - it should match LinguistLookupResult structure
        lookupResult = try? container.decode(LinguistLookupResult.self, forKey: .lookupResult)
    }
}

struct LookupCacheBulkResponse: Decodable {
    let jobId: String
    let words: [String]
    let entries: [LookupCacheEntryResponse]

    enum CodingKeys: String, CodingKey {
        case jobId
        case words
        case entries
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        jobId = try container.decode(String.self, forKey: .jobId)
        words = (try? container.decode([String].self, forKey: .words)) ?? []
        entries = (try? container.decode([LookupCacheEntryResponse].self, forKey: .entries)) ?? []
    }
}

struct LookupCacheSummaryResponse: Decodable {
    let jobId: String
    let totalEntries: Int
    let inputLanguage: String?
    let definitionLanguage: String?
    let cacheVersion: String?

    enum CodingKeys: String, CodingKey {
        case jobId
        case totalEntries
        case inputLanguage
        case definitionLanguage
        case cacheVersion
    }
}
