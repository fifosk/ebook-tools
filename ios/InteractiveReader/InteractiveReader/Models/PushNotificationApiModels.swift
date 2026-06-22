struct DeviceRegistrationRequest: Encodable {
    let token: String
    let deviceName: String
    let bundleId: String
    let environment: String

    enum CodingKeys: String, CodingKey {
        case token
        case deviceName = "device_name"
        case bundleId = "bundle_id"
        case environment
    }
}

struct DeviceRegistrationResponse: Decodable {
    let registered: Bool
    let deviceId: String?
}

struct DeviceInfo: Decodable {
    let deviceName: String
    let bundleId: String
    let environment: String
    let registeredAt: String
    let lastUsedAt: String
}

struct NotificationPreferencesRequest: Encodable {
    var jobCompleted: Bool
    var jobFailed: Bool

    enum CodingKeys: String, CodingKey {
        case jobCompleted = "job_completed"
        case jobFailed = "job_failed"
    }
}

struct NotificationPreferencesResponse: Decodable {
    let jobCompleted: Bool
    let jobFailed: Bool
    let devices: [DeviceInfo]
}

struct TestNotificationResponse: Decodable {
    let sent: Int
    let failed: Int
    let message: String?
}
