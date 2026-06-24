import Foundation

enum ApplePlaybackStateRuntimeContract {
    static let bookmarksPathTemplate = "/api/bookmarks/{job_id}"
    static let bookmarkDeletePathTemplate = "/api/bookmarks/{job_id}/{bookmark_id}"
    static let resumeListPath = "/api/resume"
    static let resumePathTemplate = "/api/resume/{job_id}"
    static let resumeFilterQuery = "job_id"

    static func bookmarksPath(_ encodedJobId: String) -> String {
        "/api/bookmarks/\(encodedJobId)"
    }

    static func bookmarkDeletePath(_ encodedJobId: String, encodedBookmarkId: String) -> String {
        "\(bookmarksPath(encodedJobId))/\(encodedBookmarkId)"
    }

    static func resumePath(_ encodedJobId: String) -> String {
        "\(resumeListPath)/\(encodedJobId)"
    }

    static func resumeListPath(jobIds: [String]) -> String {
        let cleaned = Array(Set(jobIds.map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }.filter { !$0.isEmpty })).sorted()
        guard !cleaned.isEmpty else { return resumeListPath }
        var components = URLComponents()
        components.queryItems = cleaned.map { URLQueryItem(name: resumeFilterQuery, value: $0) }
        guard let query = components.percentEncodedQuery, !query.isEmpty else {
            return resumeListPath
        }
        return "\(resumeListPath)?\(query)"
    }
}

extension APIClient {
    func fetchReadingBeds() async throws -> ReadingBedListResponse {
        let data = try await sendRequest(path: "/api/reading-beds")
        return try decode(ReadingBedListResponse.self, from: data)
    }

    func fetchPlaybackBookmarks(jobId: String) async throws -> PlaybackBookmarkListResponse {
        let encoded = jobId.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? jobId
        let data = try await sendRequest(path: ApplePlaybackStateRuntimeContract.bookmarksPath(encoded))
        return try decode(PlaybackBookmarkListResponse.self, from: data)
    }

    func createPlaybackBookmark(jobId: String, payload: PlaybackBookmarkCreateRequest) async throws -> PlaybackBookmarkPayload {
        let encoded = jobId.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? jobId
        let data = try await sendJSONRequest(
            path: ApplePlaybackStateRuntimeContract.bookmarksPath(encoded),
            method: "POST",
            payload: payload
        )
        return try decode(PlaybackBookmarkPayload.self, from: data)
    }

    func deletePlaybackBookmark(jobId: String, bookmarkId: String) async throws -> PlaybackBookmarkDeleteResponse {
        let encodedJob = jobId.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? jobId
        let encodedBookmark = bookmarkId.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? bookmarkId
        let data = try await sendRequest(
            path: ApplePlaybackStateRuntimeContract.bookmarkDeletePath(encodedJob, encodedBookmarkId: encodedBookmark),
            method: "DELETE"
        )
        return try decode(PlaybackBookmarkDeleteResponse.self, from: data)
    }

    func fetchResumePosition(jobId: String) async throws -> ResumePositionResponse? {
        let encoded = jobId.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? jobId
        guard let data = try await sendRequestAllowingNotFound(
            path: ApplePlaybackStateRuntimeContract.resumePath(encoded)
        ) else {
            return nil
        }
        return try decode(ResumePositionResponse.self, from: data)
    }

    func fetchResumePositions(jobIds: [String]) async throws -> ResumePositionListResponse {
        let data = try await sendRequest(
            path: ApplePlaybackStateRuntimeContract.resumeListPath(jobIds: jobIds)
        )
        return try decode(ResumePositionListResponse.self, from: data)
    }

    func saveResumePosition(jobId: String, payload: ResumePositionSaveRequest) async throws -> ResumePositionResponse {
        let encoded = jobId.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? jobId
        let data = try await sendJSONRequest(
            path: ApplePlaybackStateRuntimeContract.resumePath(encoded),
            method: "PUT",
            payload: payload
        )
        return try decode(ResumePositionResponse.self, from: data)
    }

    func deleteResumePosition(jobId: String) async throws -> ResumePositionDeleteResponse {
        let encoded = jobId.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? jobId
        let data = try await sendRequest(
            path: ApplePlaybackStateRuntimeContract.resumePath(encoded),
            method: "DELETE"
        )
        return try decode(ResumePositionDeleteResponse.self, from: data)
    }
}
