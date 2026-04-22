import UIKit
import UserNotifications

/// Application delegate for handling push notification lifecycle events.
/// Inherits from UIResponder (not NSObject) so we can override
/// `buildMenu(with:)` and register app-level keyboard shortcuts that are
/// reachable from any view via the responder chain.
class AppDelegate: UIResponder, UIApplicationDelegate, UNUserNotificationCenterDelegate {

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

    // NOTE: App-level keyboard shortcuts are registered via SwiftUI's
    // `.commands { CommandMenu }` in InteractiveReaderApp, NOT here. An
    // earlier buildMenu(with:) override registered the same shortcuts and
    // produced "Keyboard Shortcut duplicate" warnings in the console,
    // causing iPadOS to drop dispatch for Space / arrows / Return. The
    // SwiftUI CommandMenu path is the canonical iPadOS mechanism and
    // survives Magic Keyboard focus routing; we rely on it exclusively.
}
