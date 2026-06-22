import Foundation
import OSLog

private let mediaSearchApiModelsLogger = Logger(subsystem: "InteractiveReader", category: "MediaSearchApiModels")

enum MediaSearchSource: String, Decodable {
    case pipeline
    case library
}

struct MediaSearchResult: Decodable, Identifiable {
    var id: String {
        // Create unique ID using multiple fields to handle video cue results.
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
        // Library fields come as camelCase from API (alias in Python model).
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
        // Try to decode results, fall back to empty array if it fails.
        // This helps detect decode issues when count > 0 but results is empty.
        do {
            results = try container.decode([MediaSearchResult].self, forKey: .results)
        } catch {
            mediaSearchApiModelsLogger.error("MediaSearchResponse failed to decode results: \(String(describing: error), privacy: .private)")
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
