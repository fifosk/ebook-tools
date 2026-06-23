import Foundation

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
        let data = try await sendRequest(path: "/api/library/items\(suffix)")
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
            path: "/api/library/items/\(encoded)/upload-source",
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
            path: "/api/library/items/\(encoded)/isbn",
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
        let data = try await sendRequest(path: "/api/library/isbn/lookup\(suffix)")
        return try decode(LibraryIsbnLookupResponse.self, from: data)
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
            path: "/api/exports",
            method: "POST",
            payload: ExportRequest(
                sourceKind: sourceKind,
                sourceId: sourceId,
                playerType: "interactive-text"
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
