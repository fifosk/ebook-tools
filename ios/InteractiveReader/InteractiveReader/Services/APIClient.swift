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
        let data = try await sendRequest(path: "/api/pipelines/jobs/\(jobId)/media")
        return try decode(PipelineMediaResponse.self, from: data)
    }

    func fetchJobTiming(jobId: String) async throws -> JobTimingResponse? {
        guard let data = try await sendRequestAllowingNotFound(path: "/api/jobs/\(jobId)/timing") else {
            return nil
        }
        return try decode(JobTimingResponse.self, from: data)
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

    private func sendRequest(path: String) async throws -> Data {
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
        return components.url ?? configuration.apiBaseURL.appendingPathComponent(trimmed)
    }
}
