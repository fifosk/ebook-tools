import Foundation

extension APIClient {
    func fetchReadingBeds() async throws -> ReadingBedListResponse {
        let data = try await sendRequest(path: "/api/reading-beds")
        return try decode(ReadingBedListResponse.self, from: data)
    }

    func fetchPlaybackBookmarks(jobId: String) async throws -> PlaybackBookmarkListResponse {
        let encoded = jobId.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? jobId
        let data = try await sendRequest(path: "/api/bookmarks/\(encoded)")
        return try decode(PlaybackBookmarkListResponse.self, from: data)
    }

    func createPlaybackBookmark(jobId: String, payload: PlaybackBookmarkCreateRequest) async throws -> PlaybackBookmarkPayload {
        let encoded = jobId.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? jobId
        let data = try await sendJSONRequest(path: "/api/bookmarks/\(encoded)", method: "POST", payload: payload)
        return try decode(PlaybackBookmarkPayload.self, from: data)
    }

    func deletePlaybackBookmark(jobId: String, bookmarkId: String) async throws -> PlaybackBookmarkDeleteResponse {
        let encodedJob = jobId.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? jobId
        let encodedBookmark = bookmarkId.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? bookmarkId
        let data = try await sendRequest(path: "/api/bookmarks/\(encodedJob)/\(encodedBookmark)", method: "DELETE")
        return try decode(PlaybackBookmarkDeleteResponse.self, from: data)
    }

    func fetchResumePosition(jobId: String) async throws -> ResumePositionResponse? {
        let encoded = jobId.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? jobId
        guard let data = try await sendRequestAllowingNotFound(path: "/api/resume/\(encoded)") else {
            return nil
        }
        return try decode(ResumePositionResponse.self, from: data)
    }

    func saveResumePosition(jobId: String, payload: ResumePositionSaveRequest) async throws -> ResumePositionResponse {
        let encoded = jobId.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? jobId
        let data = try await sendJSONRequest(path: "/api/resume/\(encoded)", method: "PUT", payload: payload)
        return try decode(ResumePositionResponse.self, from: data)
    }

    func deleteResumePosition(jobId: String) async throws -> ResumePositionDeleteResponse {
        let encoded = jobId.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? jobId
        let data = try await sendRequest(path: "/api/resume/\(encoded)", method: "DELETE")
        return try decode(ResumePositionDeleteResponse.self, from: data)
    }
}
