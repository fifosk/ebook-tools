import Foundation
import UserNotifications
#if canImport(UIKit)
import UIKit
#endif

/// Manages push notification registration, preferences, and navigation handling.
@MainActor
final class NotificationManager: ObservableObject {

    /// Shared singleton instance.
    static let shared = NotificationManager()

    /// Whether push notifications are authorized by the user.
    @Published private(set) var isAuthorized: Bool = false

    /// Whether the user has enabled notifications in app settings.
    @Published var notificationsEnabled: Bool {
        didSet {
            UserDefaults.standard.set(notificationsEnabled, forKey: "notifications.enabled")
        }
    }

    /// Job ID from a tapped notification, to be handled by the UI.
    @Published var pendingJobId: String?

    /// The current device token (hex string).
    private var deviceToken: String?

    /// Track whether we've attempted registration this session.
    private var hasAttemptedRegistration = false

    private init() {
        notificationsEnabled = UserDefaults.standard.object(forKey: "notifications.enabled") as? Bool ?? true
        Task {
            await checkAuthorizationStatus()
        }
    }

    // MARK: - Authorization

    /// Check current notification authorization status.
    func checkAuthorizationStatus() async {
        let settings = await UNUserNotificationCenter.current().notificationSettings()
        isAuthorized = settings.authorizationStatus == .authorized
    }

    /// Request notification permission from the user.
    /// - Returns: Whether permission was granted.
    @discardableResult
    func requestAuthorization() async -> Bool {
        do {
            let granted = try await UNUserNotificationCenter.current().requestAuthorization(
                options: [.alert, .sound, .badge]
            )
            isAuthorized = granted

            if granted {
                #if canImport(UIKit) && !os(tvOS)
                UIApplication.shared.registerForRemoteNotifications()
                #endif
            }

            return granted
        } catch {
            print("[NotificationManager] Failed to request authorization: \(error)")
            return false
        }
    }

    // MARK: - Device Token Registration

    /// Called by AppDelegate when device token is received.
    func handleDeviceTokenRegistration(_ token: String) async {
        self.deviceToken = token
        hasAttemptedRegistration = true

        // If we have an API configuration, register with the backend
        await registerTokenWithBackend()
    }

    /// Register the device token with the backend API.
    /// Call this after authentication is complete.
    func registerTokenWithBackend() async {
        guard let token = deviceToken else {
            print("[NotificationManager] No device token to register")
            return
        }

        guard notificationsEnabled else {
            print("[NotificationManager] Notifications disabled, skipping registration")
            return
        }

        // Get API configuration from somewhere accessible
        // This will be called from AppState when auth is ready
        guard let config = await getAPIConfiguration() else {
            print("[NotificationManager] No API configuration available")
            return
        }

        let client = APIClient(configuration: config)
        do {
            #if canImport(UIKit)
            let deviceName = UIDevice.current.name
            #else
            let deviceName = "Apple TV"
            #endif

            try await client.registerDeviceToken(
                token: token,
                deviceName: deviceName,
                bundleId: Bundle.main.bundleIdentifier ?? "com.ebook-tools.interactivereader"
            )
            print("[NotificationManager] Successfully registered device token with backend")
        } catch {
            print("[NotificationManager] Failed to register device token: \(error)")
        }
    }

    /// Attempt to register for push notifications if authorized.
    func registerForPushNotificationsIfNeeded() {
        guard isAuthorized else { return }
        guard !hasAttemptedRegistration else { return }

        #if canImport(UIKit) && !os(tvOS)
        UIApplication.shared.registerForRemoteNotifications()
        #endif
    }

    // MARK: - Notification Handling

    /// Handle a tap on a notification.
    func handleNotificationTap(jobId: String) {
        print("[NotificationManager] Handling notification tap for job: \(jobId)")
        pendingJobId = jobId
    }

    /// Clear the pending job ID after it has been handled.
    func clearPendingJobId() {
        pendingJobId = nil
    }

    // MARK: - Test Notification

    /// Send a test notification via the backend.
    func sendTestNotification(using config: APIClientConfiguration) async throws -> (sent: Int, failed: Int, message: String?) {
        let client = APIClient(configuration: config)
        let response = try await client.sendTestNotification()
        return (response.sent, response.failed, response.message)
    }

    // MARK: - Helpers

    /// Get the current API configuration.
    /// This is a placeholder - the actual implementation should access AppState.
    private func getAPIConfiguration() async -> APIClientConfiguration? {
        // This will be set by the app when authentication is ready
        // For now, return nil - the registration will be triggered from AppState
        return nil
    }
}

// MARK: - Notification Manager API Configuration

extension NotificationManager {
    /// Set up notification registration with the given API configuration.
    /// Call this after the user logs in.
    func configure(with configuration: APIClientConfiguration) {
        Task {
            // Re-register token with new configuration
            guard let token = deviceToken else { return }

            let client = APIClient(configuration: configuration)
            do {
                #if canImport(UIKit)
                let deviceName = UIDevice.current.name
                #else
                let deviceName = "Apple TV"
                #endif

                try await client.registerDeviceToken(
                    token: token,
                    deviceName: deviceName,
                    bundleId: Bundle.main.bundleIdentifier ?? "com.ebook-tools.interactivereader"
                )
                print("[NotificationManager] Re-registered device token after login")
            } catch {
                print("[NotificationManager] Failed to re-register device token: \(error)")
            }
        }
    }
}
