import Foundation

/// SSE event representing a job status update.
struct JobSSEEvent {
    let eventType: String
    let data: Data
}

/// Client for consuming Server-Sent Events (SSE) from a specific job's events endpoint.
/// Use this for real-time updates when viewing a single job's details.
actor JobEventStreamClient {
    enum StreamError: Error, LocalizedError {
        case invalidConfiguration
        case connectionFailed(Error)
        case invalidEventData

        var errorDescription: String? {
            switch self {
            case .invalidConfiguration:
                return "Invalid API configuration for SSE connection."
            case let .connectionFailed(error):
                return "SSE connection failed: \(error.localizedDescription)"
            case .invalidEventData:
                return "Received invalid event data from server."
            }
        }
    }

    private let configuration: APIClientConfiguration
    private let jobId: String
    private var activeTask: Task<Void, Never>?
    private var isConnected = false

    init(configuration: APIClientConfiguration, jobId: String) {
        self.configuration = configuration
        self.jobId = jobId
    }

    /// Connect to job events SSE stream.
    /// - Parameters:
    ///   - onEvent: Callback for each received event
    ///   - onError: Callback for connection errors
    ///   - onDisconnect: Callback when stream disconnects
    func connect(
        onEvent: @escaping @Sendable (JobSSEEvent) async -> Void,
        onError: @escaping @Sendable (Error) async -> Void,
        onDisconnect: @escaping @Sendable () async -> Void
    ) async {
        await disconnect()

        let task = Task { [weak self] in
            guard let self else { return }

            do {
                try await self.startStream(
                    onEvent: onEvent,
                    onError: onError,
                    onDisconnect: onDisconnect
                )
            } catch {
                await onError(error)
                await onDisconnect()
            }
        }

        activeTask = task
    }

    /// Disconnect from the SSE stream.
    func disconnect() async {
        activeTask?.cancel()
        activeTask = nil
        isConnected = false
    }

    /// Check if currently connected.
    func connected() -> Bool {
        isConnected
    }

    private func startStream(
        onEvent: @escaping @Sendable (JobSSEEvent) async -> Void,
        onError: @escaping @Sendable (Error) async -> Void,
        onDisconnect: @escaping @Sendable () async -> Void
    ) async throws {
        let url = buildSSEURL()

        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        request.setValue("text/event-stream", forHTTPHeaderField: "Accept")
        request.setValue("no-cache", forHTTPHeaderField: "Cache-Control")
        request.timeoutInterval = 300 // 5 minute timeout for long-polling

        if let token = configuration.authToken {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        if let userID = configuration.userID {
            request.setValue(userID, forHTTPHeaderField: "X-User-Id")
        }
        if let userRole = configuration.userRole {
            request.setValue(userRole, forHTTPHeaderField: "X-User-Role")
        }

        let session = URLSession(configuration: .default)

        do {
            let (bytes, response) = try await session.bytes(for: request)

            guard let httpResponse = response as? HTTPURLResponse,
                  (200..<300).contains(httpResponse.statusCode) else {
                throw StreamError.connectionFailed(
                    NSError(domain: "SSE", code: -1, userInfo: [
                        NSLocalizedDescriptionKey: "Server returned non-success status"
                    ])
                )
            }

            isConnected = true

            var currentEventType = "message"
            var currentData = ""

            for try await line in bytes.lines {
                guard !Task.isCancelled else { break }

                if line.isEmpty {
                    // End of event - process it
                    if !currentData.isEmpty {
                        if let data = currentData.data(using: .utf8) {
                            let event = JobSSEEvent(
                                eventType: currentEventType,
                                data: data
                            )
                            await onEvent(event)
                        }
                    }
                    // Reset for next event
                    currentEventType = "message"
                    currentData = ""
                    continue
                }

                if line.hasPrefix("event:") {
                    currentEventType = String(line.dropFirst(6)).trimmingCharacters(in: .whitespaces)
                } else if line.hasPrefix("data:") {
                    let dataLine = String(line.dropFirst(5)).trimmingCharacters(in: .whitespaces)
                    if currentData.isEmpty {
                        currentData = dataLine
                    } else {
                        currentData += "\n" + dataLine
                    }
                }
                // Ignore id:, retry:, and comment lines
            }
        } catch {
            if !Task.isCancelled {
                await onError(StreamError.connectionFailed(error))
            }
        }

        isConnected = false
        await onDisconnect()
    }

    private func buildSSEURL() -> URL {
        var components = URLComponents(url: configuration.apiBaseURL, resolvingAgainstBaseURL: false) ?? URLComponents()

        var basePath = components.path
        if !basePath.hasSuffix("/") {
            basePath += "/"
        }

        let encoded = jobId.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? jobId
        components.path = basePath + "api/pipelines/\(encoded)/events"

        // Add auth token as query param for SSE (EventSource compatibility)
        if let token = configuration.authToken {
            components.queryItems = [URLQueryItem(name: "access_token", value: token)]
        }

        return components.url ?? configuration.apiBaseURL
    }
}
