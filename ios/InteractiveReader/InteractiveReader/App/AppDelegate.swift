import UIKit
import UserNotifications
import OSLog

/// Application delegate for handling push notification lifecycle events.
/// Inherits from UIResponder (not NSObject) so we can override
/// `buildMenu(with:)` and register app-level keyboard shortcuts that are
/// reachable from any view via the responder chain.
class AppDelegate: UIResponder, UIApplicationDelegate, UNUserNotificationCenterDelegate {
    private let logger = Logger(subsystem: "InteractiveReader", category: "AppDelegate")

    #if os(iOS)
    override var canBecomeFirstResponder: Bool {
        true
    }

    override var keyCommands: [UIKeyCommand]? {
        [
            appPlayerCommand(input: " ", action: #selector(handlePlayerPlayPauseCommand)),
            appPlayerCommand(input: UIKeyCommand.inputLeftArrow, action: #selector(handlePlayerPreviousCommand)),
            appPlayerCommand(input: UIKeyCommand.inputRightArrow, action: #selector(handlePlayerNextCommand)),
            appPlayerCommand(
                input: UIKeyCommand.inputLeftArrow,
                modifiers: [.control],
                action: #selector(handlePlayerPreviousSentenceCommand)
            ),
            appPlayerCommand(
                input: UIKeyCommand.inputRightArrow,
                modifiers: [.control],
                action: #selector(handlePlayerNextSentenceCommand)
            ),
            appPlayerCommand(input: "\r", action: #selector(handlePlayerLookupCommand)),
            appPlayerCommand(input: "\n", action: #selector(handlePlayerLookupCommand))
        ]
    }
    #endif

    func application(
        _ application: UIApplication,
        didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]? = nil
    ) -> Bool {
        // Set ourselves as the notification center delegate
        UNUserNotificationCenter.current().delegate = self
        resetKeyboardShortcutDebugLog()
        #if os(iOS)
        UIApplication.installInteractiveReaderKeyboardEventInterceptor()
        #endif

        #if DEBUG
        // Suppress constraint warning spam from iOS keyboard system in simulator
        // These are Apple bugs in _UIRemoteKeyboardPlaceholderView, not our code
        UserDefaults.standard.set(false, forKey: "_UIConstraintBasedLayoutLogUnsatisfiable")
        #endif

        return true
    }

    #if os(iOS)
    private func appPlayerCommand(
        input: String,
        modifiers: UIKeyModifierFlags = [],
        action: Selector
    ) -> UIKeyCommand {
        let command = UIKeyCommand(input: input, modifierFlags: modifiers, action: action)
        command.wantsPriorityOverSystemBehavior = true
        return command
    }

    @objc private func handlePlayerPlayPauseCommand() {
        PlayerKeyboardShortcutBroker.shared.handleCommand(.keyboardShortcutPlayPause)
    }

    @objc private func handlePlayerPreviousCommand() {
        PlayerKeyboardShortcutBroker.shared.handleCommand(.keyboardShortcutPrevious)
    }

    @objc private func handlePlayerNextCommand() {
        PlayerKeyboardShortcutBroker.shared.handleCommand(.keyboardShortcutNext)
    }

    @objc private func handlePlayerPreviousSentenceCommand() {
        PlayerKeyboardShortcutBroker.shared.handleCommand(.keyboardShortcutPreviousSentence)
    }

    @objc private func handlePlayerNextSentenceCommand() {
        PlayerKeyboardShortcutBroker.shared.handleCommand(.keyboardShortcutNextSentence)
    }

    @objc private func handlePlayerLookupCommand() {
        PlayerKeyboardShortcutBroker.shared.handleCommand(.keyboardShortcutLookup)
    }
    #endif

    // MARK: - Remote Notification Registration

    func application(
        _ application: UIApplication,
        didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data
    ) {
        // Convert device token to hex string
        let tokenString = deviceToken.map { String(format: "%02x", $0) }.joined()
        logger.info("Registered for remote notifications tokenBytes=\(deviceToken.count, privacy: .public)")

        // Send to notification manager
        Task {
            await NotificationManager.shared.handleDeviceTokenRegistration(tokenString)
        }
    }

    func application(
        _ application: UIApplication,
        didFailToRegisterForRemoteNotificationsWithError error: Error
    ) {
        logger.error("Failed to register for remote notifications: \(error.localizedDescription, privacy: .public)")
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
        logger.info("User tapped notification payloadKeys=\(userInfo.keys.count, privacy: .public)")

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
