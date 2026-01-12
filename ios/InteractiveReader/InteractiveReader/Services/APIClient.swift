import Foundation

struct APIClientConfiguration {
    let apiBaseURL: URL
    let storageBaseURL: URL?
    let authToken: String?
    let userID: String?
    let userRole: String?

    init(apiBaseURL: URL, storageBaseURL: URL? = nil, authToken: String? = nil, userID: String? = nil, userRole: String? = nil) {
        self.apiBaseURL = apiBaseURL
        self.storageBaseURL = storageBaseURL
        self.authToken = authToken?.nonEmptyValue
        self.userID = userID?.nonEmptyValue
        self.userRole = userRole?.nonEmptyValue
    }
}

enum APIClientError: Error, LocalizedError {
    case invalidResponse
    case httpError(Int, String?)
    case decoding(Error)
    case cancelled

    var errorDescription: String? {
        switch self {
        case .invalidResponse:
            return "The server response was invalid."
        case let .httpError(code, message):
            if let message = message, !message.isEmpty {
                return "Request failed with status \(code): \(message)"
            }
            return "Request failed with status \(code)."
        case let .decoding(error):
            return "Unable to decode server response: \(error.localizedDescription)"
        case .cancelled:
            return "The request was cancelled."
        }
    }
}

final class APIClient {
    private let configuration: APIClientConfiguration
    private let urlSession: URLSession

    init(configuration: APIClientConfiguration, urlSession: URLSession = .shared) {
        self.configuration = configuration
        self.urlSession = urlSession
    }

    func fetchJobMedia(jobId: String) async throws -> PipelineMediaResponse {
        let encoded = jobId.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? jobId
        let data = try await sendRequest(path: "/api/pipelines/jobs/\(encoded)/media")
        return try decode(PipelineMediaResponse.self, from: data)
    }

    func fetchJobMediaLive(jobId: String) async throws -> PipelineMediaResponse {
        let encoded = jobId.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? jobId
        let data = try await sendRequest(path: "/api/pipelines/jobs/\(encoded)/media/live")
        return try decode(PipelineMediaResponse.self, from: data)
    }

    func fetchLibraryMedia(jobId: String) async throws -> PipelineMediaResponse {
        let encoded = jobId.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? jobId
        let data = try await sendRequest(path: "/api/library/media/\(encoded)")
        return try decode(PipelineMediaResponse.self, from: data)
    }

    func fetchJobTiming(jobId: String) async throws -> JobTimingResponse? {
        let encoded = jobId.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? jobId
        guard let data = try await sendRequestAllowingNotFound(path: "/api/jobs/\(encoded)/timing") else {
            return nil
        }
        return try decode(JobTimingResponse.self, from: data)
    }

    func fetchSubtitleTvMetadata(jobId: String) async throws -> SubtitleTvMetadataResponse? {
        let encoded = jobId.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? jobId
        guard let data = try await sendRequestAllowingNotFound(path: "/api/subtitles/jobs/\(encoded)/metadata/tv") else {
            return nil
        }
        return try decode(SubtitleTvMetadataResponse.self, from: data)
    }

    func fetchYoutubeVideoMetadata(jobId: String) async throws -> YoutubeVideoMetadataResponse? {
        let encoded = jobId.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? jobId
        guard let data = try await sendRequestAllowingNotFound(path: "/api/subtitles/jobs/\(encoded)/metadata/youtube") else {
            return nil
        }
        return try decode(YoutubeVideoMetadataResponse.self, from: data)
    }

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

    func login(username: String, password: String) async throws -> SessionStatusResponse {
        let payload = LoginRequestPayload(username: username, password: password)
        let data = try await sendJSONRequest(path: "/api/auth/login", method: "POST", payload: payload)
        return try decode(SessionStatusResponse.self, from: data)
    }

    func loginWithOAuth(
        provider: String,
        idToken: String,
        email: String?,
        firstName: String?,
        lastName: String?
    ) async throws -> SessionStatusResponse {
        let payload = OAuthLoginRequestPayload(
            provider: provider,
            idToken: idToken,
            email: email,
            firstName: firstName,
            lastName: lastName
        )
        let data = try await sendJSONRequest(path: "/api/auth/oauth", method: "POST", payload: payload)
        return try decode(SessionStatusResponse.self, from: data)
    }

    func fetchSessionStatus() async throws -> SessionStatusResponse {
        let data = try await sendRequest(path: "/api/auth/session")
        return try decode(SessionStatusResponse.self, from: data)
    }

    func assistantLookup(
        query: String,
        inputLanguage: String,
        lookupLanguage: String,
        llmModel: String? = nil
    ) async throws -> AssistantLookupResponse {
        let payload = AssistantLookupRequest(
            query: query,
            inputLanguage: inputLanguage,
            lookupLanguage: lookupLanguage,
            llmModel: llmModel
        )
        let data = try await sendJSONRequest(path: "/api/assistant/lookup", method: "POST", payload: payload)
        return try decode(AssistantLookupResponse.self, from: data)
    }

    func fetchLlmModels() async throws -> LLMModelListResponse {
        let data = try await sendRequest(path: "/api/pipelines/llm-models")
        return try decode(LLMModelListResponse.self, from: data)
    }

    func synthesizeAudio(text: String, language: String?) async throws -> Data {
        let payload = AudioSynthesisRequest(text: text, voice: nil, speed: nil, language: language)
        let encoder = JSONEncoder()
        let body = try encoder.encode(payload)
        return try await sendRequest(
            path: "/api/audio",
            method: "POST",
            body: body,
            contentType: "application/json",
            accept: "audio/mpeg"
        )
    }

    private func decode<T: Decodable>(_ type: T.Type, from data: Data) throws -> T {
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601
        do {
            return try decoder.decode(T.self, from: data)
        } catch {
            throw APIClientError.decoding(error)
        }
    }

    private func sendRequest(
        path: String,
        method: String = "GET",
        body: Data? = nil,
        contentType: String? = nil,
        accept: String = "application/json",
        cachePolicy: URLRequest.CachePolicy = .useProtocolCachePolicy
    ) async throws -> Data {
        guard !Task.isCancelled else {
            throw APIClientError.cancelled
        }

        let requestURL = buildURL(with: path)
        var request = URLRequest(url: requestURL)
        request.httpMethod = method
        request.cachePolicy = cachePolicy
        request.setValue(accept, forHTTPHeaderField: "Accept")
        if let body {
            request.httpBody = body
        }
        if let contentType {
            request.setValue(contentType, forHTTPHeaderField: "Content-Type")
        }
        if let token = configuration.authToken {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        if let userID = configuration.userID {
            request.setValue(userID, forHTTPHeaderField: "X-User-Id")
        }
        if let userRole = configuration.userRole {
            request.setValue(userRole, forHTTPHeaderField: "X-User-Role")
        }

        let (data, response) = try await urlSession.data(for: request, delegate: nil)

        guard !Task.isCancelled else {
            throw APIClientError.cancelled
        }

        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIClientError.invalidResponse
        }

        guard (200..<300).contains(httpResponse.statusCode) else {
            let message = String(data: data, encoding: .utf8)
            throw APIClientError.httpError(httpResponse.statusCode, message)
        }
        return data
    }

    private func sendJSONRequest<T: Encodable>(path: String, method: String, payload: T) async throws -> Data {
        let encoder = JSONEncoder()
        let data = try encoder.encode(payload)
        return try await sendRequest(path: path, method: method, body: data, contentType: "application/json")
    }

    private func sendRequestAllowingNotFound(path: String) async throws -> Data? {
        guard !Task.isCancelled else {
            throw APIClientError.cancelled
        }

        let requestURL = buildURL(with: path)
        var request = URLRequest(url: requestURL)
        request.httpMethod = "GET"
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        if let token = configuration.authToken {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        if let userID = configuration.userID {
            request.setValue(userID, forHTTPHeaderField: "X-User-Id")
        }
        if let userRole = configuration.userRole {
            request.setValue(userRole, forHTTPHeaderField: "X-User-Role")
        }

        let (data, response) = try await urlSession.data(for: request, delegate: nil)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIClientError.invalidResponse
        }

        if httpResponse.statusCode == 404 {
            return nil
        }

        guard (200..<300).contains(httpResponse.statusCode) else {
            let message = String(data: data, encoding: .utf8)
            throw APIClientError.httpError(httpResponse.statusCode, message)
        }
        return data
    }

    private func buildURL(with path: String) -> URL {
        var normalizedPath = path
        var query: String?
        var fragment: String?

        if let fragmentRange = normalizedPath.range(of: "#") {
            fragment = String(normalizedPath[fragmentRange.upperBound...])
            normalizedPath = String(normalizedPath[..<fragmentRange.lowerBound])
        }
        if let queryRange = normalizedPath.range(of: "?") {
            query = String(normalizedPath[queryRange.upperBound...])
            normalizedPath = String(normalizedPath[..<queryRange.lowerBound])
        }
        if !normalizedPath.hasPrefix("/") {
            normalizedPath = "/" + normalizedPath
        }

        var components = URLComponents(url: configuration.apiBaseURL, resolvingAgainstBaseURL: false) ?? URLComponents()
        var basePath = components.path
        if !basePath.hasSuffix("/") {
            basePath += "/"
        }
        let trimmed = normalizedPath.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        components.path = basePath + trimmed
        if let query {
            components.percentEncodedQuery = query
        }
        if let fragment {
            components.fragment = fragment
        }
        return components.url ?? configuration.apiBaseURL.appendingPathComponent(trimmed)
    }
}
