import UIKit
import UserNotifications

/// Application delegate for handling push notification lifecycle events.
class AppDelegate: NSObject, UIApplicationDelegate, UNUserNotificationCenterDelegate {

    func application(
        _ application: UIApplication,
        didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]? = nil
    ) -> Bool {
        // Set ourselves as the notification center delegate
        UNUserNotificationCenter.current().delegate = self

        #if DEBUG
        // Suppress constraint warning spam from iOS keyboard system in simulator
        // These are Apple bugs in _UIRemoteKeyboardPlaceholderView, not our code
        UserDefaults.standard.set(false, forKey: "_UIConstraintBasedLayoutLogUnsatisfiable")
        #endif

        return true
    }

    // MARK: - Remote Notification Registration

    func application(
        _ application: UIApplication,
        didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data
    ) {
        // Convert device token to hex string
        let tokenString = deviceToken.map { String(format: "%02x", $0) }.joined()
        print("[AppDelegate] Registered for remote notifications with token: \(tokenString.prefix(16))...")

        // Send to notification manager
        Task {
            await NotificationManager.shared.handleDeviceTokenRegistration(tokenString)
        }
    }

    func application(
        _ application: UIApplication,
        didFailToRegisterForRemoteNotificationsWithError error: Error
    ) {
        print("[AppDelegate] Failed to register for remote notifications: \(error.localizedDescription)")
    }

    // MARK: - UNUserNotificationCenterDelegate

    /// Called when a notification is delivered while the app is in the foreground.
    func userNotificationCenter(
        _ center: UNUserNotificationCenter,
        willPresent notification: UNNotification
    ) async -> UNNotificationPresentationOptions {
        // Show banner and play sound even when app is in foreground
        return [.banner, .sound, .badge]
    }

    #if !os(tvOS)
    /// Called when the user interacts with a notification (taps on it).
    func userNotificationCenter(
        _ center: UNUserNotificationCenter,
        didReceive response: UNNotificationResponse
    ) async {
        let userInfo = response.notification.request.content.userInfo
        print("[AppDelegate] User tapped notification: \(userInfo)")

        // Pass full userInfo to notification manager for extraction
        await MainActor.run {
            NotificationManager.shared.handleNotificationTap(userInfo: userInfo)
        }
    }
    #endif
}
