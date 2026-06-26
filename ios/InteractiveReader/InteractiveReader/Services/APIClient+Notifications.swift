import Foundation

enum AppleNotificationsRuntimeContract {
    static let deviceRegistrationPath = "/api/notifications/devices"
    static let deviceRemovalPathTemplate = "/api/notifications/devices/{device_id}"
    static let testPath = "/api/notifications/test"
    static let richTestPath = "/api/notifications/test/rich"
    static let preferencesPath = "/api/notifications/preferences"

    static func deviceRemovalPath(_ encodedDeviceId: String) -> String {
        deviceRemovalPathTemplate.replacingOccurrences(of: "{device_id}", with: encodedDeviceId)
    }

    static func richTestRequestPath(queryItems: [URLQueryItem]) -> String {
        guard !queryItems.isEmpty else { return richTestPath }
        var components = URLComponents()
        components.path = richTestPath
        components.queryItems = queryItems
        return components.string ?? richTestPath
    }
}

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
            path: AppleNotificationsRuntimeContract.deviceRegistrationPath,
            method: "POST",
            payload: payload
        )
    }

    func unregisterDeviceToken(_ token: String) async throws {
        let encoded = AppleAPIPathComponentEncoding.encode(token)
        _ = try await sendRequest(
            path: AppleNotificationsRuntimeContract.deviceRemovalPath(encoded),
            method: "DELETE"
        )
    }

    func sendTestNotification() async throws -> TestNotificationResponse {
        let data = try await sendRequest(
            path: AppleNotificationsRuntimeContract.testPath,
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

        let path = AppleNotificationsRuntimeContract.richTestRequestPath(queryItems: queryItems)
        let data = try await sendRequest(path: path, method: "POST")
        return try decode(TestNotificationResponse.self, from: data)
    }

    func fetchNotificationPreferences() async throws -> NotificationPreferencesResponse {
        let data = try await sendRequest(path: AppleNotificationsRuntimeContract.preferencesPath)
        return try decode(NotificationPreferencesResponse.self, from: data)
    }

    func updateNotificationPreferences(_ preferences: NotificationPreferencesRequest) async throws {
        _ = try await sendJSONRequest(
            path: AppleNotificationsRuntimeContract.preferencesPath,
            method: "PUT",
            payload: preferences
        )
    }
}
