import Foundation
import OSLog

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
    let logger = Logger(subsystem: "InteractiveReader", category: "APIClient")

    init(configuration: APIClientConfiguration, urlSession: URLSession = .shared) {
        self.configuration = configuration
        self.urlSession = urlSession
    }

    func decode<T: Decodable>(_ type: T.Type, from data: Data) throws -> T {
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601
        do {
            return try decoder.decode(T.self, from: data)
        } catch {
            if type == MediaSearchResponse.self {
                logger.error(
                    "Media search decode failed bytes=\(data.count, privacy: .public) error=\(String(describing: error), privacy: .public)"
                )
            }
            throw APIClientError.decoding(error)
        }
    }

    func sendRequest(
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

    func sendJSONRequest<T: Encodable>(path: String, method: String, payload: T) async throws -> Data {
        let encoder = JSONEncoder()
        let data = try encoder.encode(payload)
        return try await sendRequest(path: path, method: method, body: data, contentType: "application/json")
    }

    func sendRequestAllowingNotFound(path: String) async throws -> Data? {
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
        var basePath = components.percentEncodedPath
        if !basePath.hasSuffix("/") {
            basePath += "/"
        }
        let trimmed = normalizedPath.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        // Use percentEncodedPath to avoid double-encoding already percent-encoded characters
        components.percentEncodedPath = basePath + trimmed
        if let query {
            components.percentEncodedQuery = query
        }
        if let fragment {
            components.fragment = fragment
        }
        return components.url ?? configuration.apiBaseURL.appendingPathComponent(trimmed)
    }
}
