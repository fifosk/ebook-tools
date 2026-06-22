import Foundation
import OSLog

private let apiModelsLogger = Logger(subsystem: "InteractiveReader", category: "ApiModels")

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

struct BackendRuntimeDescriptorResponse: Decodable, Equatable {
    struct AuthContract: Decodable, Equatable {
        let loginPath: String
        let sessionPath: String
        let tokenTransport: String
    }

    struct ClientConfig: Decodable, Equatable {
        let apiBaseUrlEnvironment: [String]
        let sessionTokenStorage: String
    }

    let status: String
    let app: String
    let service: String
    let version: String
    let healthPath: String
    let auth: AuthContract
    let clientConfig: ClientConfig
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
            apiModelsLogger.error("LinguistLookupResult parse error: \(String(describing: error), privacy: .private)")
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
