import Foundation

enum AppleOfflineExportRuntimeContract {
    static let createPath = "/api/exports"
    static let downloadPathTemplate = "/api/exports/{export_id}/download"
    static let supportedPlayerTypes = ["interactive-text"]
    static let playerType = supportedPlayerTypes[0]
    static let supportedSourceKinds = ["job", "library"]

    static func downloadPath(_ encodedExportId: String) -> String {
        downloadPathTemplate.replacingOccurrences(of: "{export_id}", with: encodedExportId)
    }
}

enum AppleLibraryRuntimeContract {
    static let itemsPath = "/api/library/items"
    static let itemPathTemplate = "/api/library/items/{job_id}"
    static let accessPathTemplate = "/api/library/items/{job_id}/access"
    static let sourceUploadPathTemplate = "/api/library/items/{job_id}/upload-source"
    static let movePathTemplate = "/api/library/move/{job_id}"
    static let removePathTemplate = "/api/library/remove/{job_id}"
    static let removeMediaPathTemplate = "/api/library/remove-media/{job_id}"
    static let isbnLookupPath = "/api/library/isbn/lookup"
    static let isbnApplyPathTemplate = "/api/library/items/{job_id}/isbn"
    static let metadataRefreshPathTemplate = "/api/library/items/{job_id}/refresh"
    static let metadataEnrichPathTemplate = "/api/library/items/{job_id}/enrich"
    static let reindexPath = "/api/library/reindex"

    static func itemPath(_ encodedJobId: String) -> String {
        itemPathTemplate.replacingOccurrences(of: "{job_id}", with: encodedJobId)
    }

    static func sourceUploadPath(_ encodedJobId: String) -> String {
        sourceUploadPathTemplate.replacingOccurrences(of: "{job_id}", with: encodedJobId)
    }

    static func accessPath(_ encodedJobId: String) -> String {
        accessPathTemplate.replacingOccurrences(of: "{job_id}", with: encodedJobId)
    }

    static func movePath(_ encodedJobId: String) -> String {
        movePathTemplate.replacingOccurrences(of: "{job_id}", with: encodedJobId)
    }

    static func removePath(_ encodedJobId: String) -> String {
        removePathTemplate.replacingOccurrences(of: "{job_id}", with: encodedJobId)
    }

    static func removeMediaPath(_ encodedJobId: String) -> String {
        removeMediaPathTemplate.replacingOccurrences(of: "{job_id}", with: encodedJobId)
    }

    static func isbnApplyPath(_ encodedJobId: String) -> String {
        isbnApplyPathTemplate.replacingOccurrences(of: "{job_id}", with: encodedJobId)
    }

    static func metadataRefreshPath(_ encodedJobId: String) -> String {
        metadataRefreshPathTemplate.replacingOccurrences(of: "{job_id}", with: encodedJobId)
    }

    static func metadataEnrichPath(_ encodedJobId: String) -> String {
        metadataEnrichPathTemplate.replacingOccurrences(of: "{job_id}", with: encodedJobId)
    }
}

enum ApplePipelineJobsRuntimeContract {
    static let listPath = "/api/pipelines/jobs"
    static let statusPathTemplate = "/api/pipelines/{job_id}"
    static let eventStreamPathTemplate = "/api/pipelines/{job_id}/events"
    static let pausePathTemplate = "/api/pipelines/jobs/{job_id}/pause"
    static let resumePathTemplate = "/api/pipelines/jobs/{job_id}/resume"
    static let cancelPathTemplate = "/api/pipelines/jobs/{job_id}/cancel"
    static let deletePathTemplate = "/api/pipelines/jobs/{job_id}/delete"
    static let restartPathTemplate = "/api/pipelines/jobs/{job_id}/restart"
    static let accessPathTemplate = "/api/pipelines/{job_id}/access"
    static let metadataRefreshPathTemplate = "/api/pipelines/{job_id}/metadata/refresh"
    static let metadataEnrichPathTemplate = "/api/pipelines/{job_id}/metadata/enrich"
    static let bookMetadataPathTemplate = "/api/pipelines/{job_id}/metadata/book"
    static let bookMetadataLookupPathTemplate = "/api/pipelines/{job_id}/metadata/book/lookup"
    static let coverPathTemplate = "/api/pipelines/{job_id}/cover"
    static let cacheBusterQuery = "ts"

    static func listPath(cacheBuster: Int) -> String {
        var components = URLComponents()
        components.path = listPath
        components.queryItems = [
            URLQueryItem(name: cacheBusterQuery, value: "\(cacheBuster)")
        ]
        return components.string ?? "\(listPath)?\(cacheBusterQuery)=\(cacheBuster)"
    }

    static func statusPath(_ encodedJobId: String) -> String {
        statusPathTemplate.replacingOccurrences(of: "{job_id}", with: encodedJobId)
    }

    static func eventStreamPath(_ encodedJobId: String) -> String {
        eventStreamPathTemplate.replacingOccurrences(of: "{job_id}", with: encodedJobId)
    }

    static func pausePath(_ encodedJobId: String) -> String {
        pausePathTemplate.replacingOccurrences(of: "{job_id}", with: encodedJobId)
    }

    static func resumePath(_ encodedJobId: String) -> String {
        resumePathTemplate.replacingOccurrences(of: "{job_id}", with: encodedJobId)
    }

    static func cancelPath(_ encodedJobId: String) -> String {
        cancelPathTemplate.replacingOccurrences(of: "{job_id}", with: encodedJobId)
    }

    static func deletePath(_ encodedJobId: String) -> String {
        deletePathTemplate.replacingOccurrences(of: "{job_id}", with: encodedJobId)
    }

    static func restartPath(_ encodedJobId: String) -> String {
        restartPathTemplate.replacingOccurrences(of: "{job_id}", with: encodedJobId)
    }

    static func accessPath(_ encodedJobId: String) -> String {
        accessPathTemplate.replacingOccurrences(of: "{job_id}", with: encodedJobId)
    }

    static func metadataRefreshPath(_ encodedJobId: String) -> String {
        metadataRefreshPathTemplate.replacingOccurrences(of: "{job_id}", with: encodedJobId)
    }

    static func metadataEnrichPath(_ encodedJobId: String) -> String {
        metadataEnrichPathTemplate.replacingOccurrences(of: "{job_id}", with: encodedJobId)
    }

    static func bookMetadataPath(_ encodedJobId: String) -> String {
        bookMetadataPathTemplate.replacingOccurrences(of: "{job_id}", with: encodedJobId)
    }

    static func bookMetadataLookupPath(_ encodedJobId: String) -> String {
        bookMetadataLookupPathTemplate.replacingOccurrences(of: "{job_id}", with: encodedJobId)
    }

    static func coverPath(_ encodedJobId: String) -> String {
        coverPathTemplate.replacingOccurrences(of: "{job_id}", with: encodedJobId)
    }
}

extension APIClient {
    func fetchLibraryItems(query: String? = nil, page: Int = 1, limit: Int = 100) async throws -> LibrarySearchResponse {
        var components = URLComponents()
        var items: [URLQueryItem] = [
            URLQueryItem(name: "page", value: "\(page)"),
            URLQueryItem(name: "limit", value: "\(limit)"),
        ]
        if let query, !query.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            items.append(URLQueryItem(name: "q", value: query))
        }
        components.queryItems = items
        let suffix = components.percentEncodedQuery.map { "?\($0)" } ?? ""
        let data = try await sendRequest(path: "\(AppleLibraryRuntimeContract.itemsPath)\(suffix)")
        return try decode(LibrarySearchResponse.self, from: data)
    }

    func fetchPipelineJobs() async throws -> PipelineJobListResponse {
        let cacheBuster = Int(Date().timeIntervalSince1970)
        let data = try await sendRequest(
            path: ApplePipelineJobsRuntimeContract.listPath(cacheBuster: cacheBuster),
            cachePolicy: .reloadIgnoringLocalCacheData
        )
        return try decode(PipelineJobListResponse.self, from: data)
    }

    func fetchPipelineStatus(jobId: String) async throws -> PipelineStatusResponse {
        let encoded = AppleAPIPathComponentEncoding.encode(jobId)
        let data = try await sendRequest(path: ApplePipelineJobsRuntimeContract.statusPath(encoded))
        return try decode(PipelineStatusResponse.self, from: data)
    }

    func deleteJob(jobId: String) async throws {
        let encoded = AppleAPIPathComponentEncoding.encode(jobId)
        _ = try await sendRequest(path: ApplePipelineJobsRuntimeContract.deletePath(encoded), method: "POST")
    }

    func restartJob(jobId: String) async throws -> PipelineStatusResponse {
        let encoded = AppleAPIPathComponentEncoding.encode(jobId)
        let data = try await sendRequest(path: ApplePipelineJobsRuntimeContract.restartPath(encoded), method: "POST")
        return try decode(PipelineJobActionResponse.self, from: data).job
    }

    func deleteLibraryItem(jobId: String) async throws {
        let encoded = AppleAPIPathComponentEncoding.encode(jobId)
        _ = try await sendRequest(path: AppleLibraryRuntimeContract.removePath(encoded), method: "DELETE")
    }

    func updateLibraryMetadata(
        jobId: String,
        title: String?,
        author: String?,
        genre: String?,
        language: String?,
        isbn: String?
    ) async throws -> LibraryItem {
        let encoded = AppleAPIPathComponentEncoding.encode(jobId)
        struct LibraryMetadataUpdateRequest: Encodable {
            let title: String?
            let author: String?
            let genre: String?
            let language: String?
            let isbn: String?
        }
        let data = try await sendJSONRequest(
            path: AppleLibraryRuntimeContract.itemPath(encoded),
            method: "PATCH",
            payload: LibraryMetadataUpdateRequest(
                title: title,
                author: author,
                genre: genre,
                language: language,
                isbn: isbn
            )
        )
        return try decode(LibraryItem.self, from: data)
    }

    func uploadLibrarySource(
        jobId: String,
        fileURL: URL,
        filename: String? = nil
    ) async throws -> LibraryItem {
        let encoded = AppleAPIPathComponentEncoding.encode(jobId)
        let didAccessSecurityScope = fileURL.startAccessingSecurityScopedResource()
        defer {
            if didAccessSecurityScope {
                fileURL.stopAccessingSecurityScopedResource()
            }
        }
        let upload = try MultipartUploadFile(
            fieldName: "file",
            fileURL: fileURL,
            filename: filename,
            contentType: "application/octet-stream"
        )
        let multipart = MultipartFormDataBuilder.makeBody(fields: [:], file: upload)
        let data = try await sendRequest(
            path: AppleLibraryRuntimeContract.sourceUploadPath(encoded),
            method: "POST",
            body: multipart.body,
            contentType: multipart.contentType
        )
        return try decode(LibraryItem.self, from: data)
    }

    func applyLibraryIsbn(jobId: String, isbn: String) async throws -> LibraryItem {
        let encoded = AppleAPIPathComponentEncoding.encode(jobId)
        struct LibraryIsbnUpdateRequest: Encodable {
            let isbn: String
        }
        let data = try await sendJSONRequest(
            path: AppleLibraryRuntimeContract.isbnApplyPath(encoded),
            method: "POST",
            payload: LibraryIsbnUpdateRequest(isbn: isbn)
        )
        return try decode(LibraryItem.self, from: data)
    }

    func lookupLibraryIsbnMetadata(isbn: String) async throws -> LibraryIsbnLookupResponse {
        var components = URLComponents()
        components.queryItems = [
            URLQueryItem(name: "isbn", value: isbn)
        ]
        let suffix = components.percentEncodedQuery.map { "?\($0)" } ?? ""
        let data = try await sendRequest(path: "\(AppleLibraryRuntimeContract.isbnLookupPath)\(suffix)")
        return try decode(LibraryIsbnLookupResponse.self, from: data)
    }

    func enrichLibraryMetadata(jobId: String, force: Bool = false) async throws -> LibraryMetadataEnrichResponse {
        let encoded = AppleAPIPathComponentEncoding.encode(jobId)
        struct LibraryMetadataEnrichRequest: Encodable {
            let force: Bool
        }
        let data = try await sendJSONRequest(
            path: AppleLibraryRuntimeContract.metadataEnrichPath(encoded),
            method: "POST",
            payload: LibraryMetadataEnrichRequest(force: force)
        )
        return try decode(LibraryMetadataEnrichResponse.self, from: data)
    }

    func createOfflineExport(sourceKind: String, sourceId: String) async throws -> OfflineExportResponse {
        struct ExportRequest: Encodable {
            let sourceKind: String
            let sourceId: String
            let playerType: String

            enum CodingKeys: String, CodingKey {
                case sourceKind = "source_kind"
                case sourceId = "source_id"
                case playerType = "player_type"
            }
        }

        let data = try await sendJSONRequest(
            path: AppleOfflineExportRuntimeContract.createPath,
            method: "POST",
            payload: ExportRequest(
                sourceKind: sourceKind,
                sourceId: sourceId,
                playerType: AppleOfflineExportRuntimeContract.playerType
            )
        )
        return try decode(OfflineExportResponse.self, from: data)
    }

    func moveJobToLibrary(jobId: String, statusOverride: String? = nil) async throws {
        let encoded = AppleAPIPathComponentEncoding.encode(jobId)
        if let statusOverride {
            struct LibraryMoveRequest: Encodable {
                let statusOverride: String
            }
            _ = try await sendJSONRequest(
                path: AppleLibraryRuntimeContract.movePath(encoded),
                method: "POST",
                payload: LibraryMoveRequest(statusOverride: statusOverride)
            )
        } else {
            _ = try await sendRequest(path: AppleLibraryRuntimeContract.movePath(encoded), method: "POST")
        }
    }
}
