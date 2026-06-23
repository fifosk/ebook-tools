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

struct LibraryIsbnLookupResponse: Decodable, Equatable {
    let metadata: [String: JSONValue]
}

struct LibraryMetadataEnrichResponse: Decodable, Equatable {
    let item: LibraryItem
    let enriched: Bool
    let confidence: String?
    let source: String?
}

struct OfflineExportResponse: Decodable, Equatable {
    let exportId: String
    let downloadUrl: String
    let filename: String
    let createdAt: String
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

extension LibraryItem: Hashable {
    static func == (lhs: LibraryItem, rhs: LibraryItem) -> Bool {
        lhs.jobId == rhs.jobId
    }

    func hash(into hasher: inout Hasher) {
        hasher.combine(jobId)
    }
}
