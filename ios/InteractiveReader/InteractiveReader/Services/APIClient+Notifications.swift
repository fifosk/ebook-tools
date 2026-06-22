import Foundation

extension APIClient {
    func registerDeviceToken(token: String, deviceName: String, bundleId: String) async throws {
        #if DEBUG
        let environment = "development"
        #else
        let environment = "production"
        #endif

        let payload = DeviceRegistrationRequest(
            token: token,
            deviceName: deviceName,
            bundleId: bundleId,
            environment: environment
        )
        _ = try await sendJSONRequest(
            path: "/api/notifications/devices",
            method: "POST",
            payload: payload
        )
    }

    func unregisterDeviceToken(_ token: String) async throws {
        let encoded = token.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? token
        _ = try await sendRequest(
            path: "/api/notifications/devices/\(encoded)",
            method: "DELETE"
        )
    }

    func sendTestNotification() async throws -> TestNotificationResponse {
        let data = try await sendRequest(
            path: "/api/notifications/test",
            method: "POST"
        )
        return try decode(TestNotificationResponse.self, from: data)
    }

    func sendRichTestNotification(
        title: String? = nil,
        subtitle: String? = nil,
        coverURL: String? = nil
    ) async throws -> TestNotificationResponse {
        var queryItems: [URLQueryItem] = []
        if let title { queryItems.append(URLQueryItem(name: "title", value: title)) }
        if let subtitle { queryItems.append(URLQueryItem(name: "subtitle", value: subtitle)) }
        if let coverURL { queryItems.append(URLQueryItem(name: "cover_url", value: coverURL)) }

        var path = "/api/notifications/test/rich"
        if !queryItems.isEmpty {
            var components = URLComponents(string: path)!
            components.queryItems = queryItems
            path = components.string ?? path
        }

        let data = try await sendRequest(path: path, method: "POST")
        return try decode(TestNotificationResponse.self, from: data)
    }

    func fetchNotificationPreferences() async throws -> NotificationPreferencesResponse {
        let data = try await sendRequest(path: "/api/notifications/preferences")
        return try decode(NotificationPreferencesResponse.self, from: data)
    }

    func updateNotificationPreferences(_ preferences: NotificationPreferencesRequest) async throws {
        _ = try await sendJSONRequest(
            path: "/api/notifications/preferences",
            method: "PUT",
            payload: preferences
        )
    }
}
