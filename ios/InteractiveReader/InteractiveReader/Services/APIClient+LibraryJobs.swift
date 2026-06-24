import Foundation

enum AppleOfflineExportRuntimeContract {
    static let createPath = "/api/exports"
    static let downloadPathTemplate = "/api/exports/{export_id}/download"
    static let playerType = "interactive-text"
    static let supportedSourceKinds = ["job", "library"]
}

enum AppleLibraryRuntimeContract {
    static let itemsPath = "/api/library/items"
    static let itemPathTemplate = "/api/library/items/{job_id}"
    static let sourceUploadPathTemplate = "/api/library/items/{job_id}/upload-source"
    static let isbnLookupPath = "/api/library/isbn/lookup"
    static let isbnApplyPathTemplate = "/api/library/items/{job_id}/isbn"
    static let metadataEnrichPathTemplate = "/api/library/items/{job_id}/enrich"

    static func itemPath(_ encodedJobId: String) -> String {
        "\(itemsPath)/\(encodedJobId)"
    }

    static func sourceUploadPath(_ encodedJobId: String) -> String {
        "\(itemPath(encodedJobId))/upload-source"
    }

    static func isbnApplyPath(_ encodedJobId: String) -> String {
        "\(itemPath(encodedJobId))/isbn"
    }

    static func metadataEnrichPath(_ encodedJobId: String) -> String {
        "\(itemPath(encodedJobId))/enrich"
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
            path: "/api/pipelines/jobs?ts=\(cacheBuster)",
            cachePolicy: .reloadIgnoringLocalCacheData
        )
        return try decode(PipelineJobListResponse.self, from: data)
    }

    func fetchPipelineStatus(jobId: String) async throws -> PipelineStatusResponse {
        let encoded = jobId.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? jobId
        let data = try await sendRequest(path: "/api/pipelines/\(encoded)")
        return try decode(PipelineStatusResponse.self, from: data)
    }

    func deleteJob(jobId: String) async throws {
        let encoded = jobId.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? jobId
        _ = try await sendRequest(path: "/api/pipelines/jobs/\(encoded)/delete", method: "POST")
    }

    func deleteLibraryItem(jobId: String) async throws {
        let encoded = jobId.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? jobId
        _ = try await sendRequest(path: "/api/library/remove/\(encoded)", method: "DELETE")
    }

    func updateLibraryMetadata(
        jobId: String,
        title: String?,
        author: String?,
        genre: String?,
        language: String?,
        isbn: String?
    ) async throws -> LibraryItem {
        let encoded = jobId.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? jobId
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
        let encoded = jobId.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? jobId
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
        let encoded = jobId.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? jobId
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
        let encoded = jobId.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? jobId
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
        let encoded = jobId.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? jobId
        if let statusOverride {
            struct LibraryMoveRequest: Encodable {
                let statusOverride: String
            }
            _ = try await sendJSONRequest(
                path: "/api/library/move/\(encoded)",
                method: "POST",
                payload: LibraryMoveRequest(statusOverride: statusOverride)
            )
        } else {
            _ = try await sendRequest(path: "/api/library/move/\(encoded)", method: "POST")
        }
    }
}
