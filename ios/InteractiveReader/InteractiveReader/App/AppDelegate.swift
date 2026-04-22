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

    // MARK: - Global keyboard shortcuts
    //
    // Register the player's hardware-keyboard shortcuts at UIApplication /
    // UIApplicationDelegate level via the main menu builder. Menu commands
    // registered here are consulted from the TOP of the responder chain on
    // every key press — which means Space / arrows / Return always reach us
    // regardless of which SwiftUI view currently holds first responder.
    // We forward to NotificationCenter so any view currently on screen can
    // react with its own handler without needing to be first responder.

    #if !os(tvOS)
    override func buildMenu(with builder: UIMenuBuilder) {
        super.buildMenu(with: builder)
        guard builder.system == .main else { return }

        let commands: [UIKeyCommand] = [
            makePriorityCommand(" ",
                                action: #selector(handleKeyboardPlayPause),
                                title: "Play / Pause"),
            makePriorityCommand(UIKeyCommand.inputLeftArrow,
                                action: #selector(handleKeyboardPrevious),
                                title: "Previous Word"),
            makePriorityCommand(UIKeyCommand.inputRightArrow,
                                action: #selector(handleKeyboardNext),
                                title: "Next Word"),
            makePriorityCommand(UIKeyCommand.inputLeftArrow,
                                modifiers: [.control],
                                action: #selector(handleKeyboardPreviousSentence),
                                title: "Previous Sentence"),
            makePriorityCommand(UIKeyCommand.inputRightArrow,
                                modifiers: [.control],
                                action: #selector(handleKeyboardNextSentence),
                                title: "Next Sentence"),
            makePriorityCommand("\r",
                                action: #selector(handleKeyboardLookup),
                                title: "Look Up Highlighted Word"),
            makePriorityCommand(UIKeyCommand.inputDownArrow,
                                action: #selector(handleKeyboardShowMenu),
                                title: "Show Menu"),
            makePriorityCommand(UIKeyCommand.inputUpArrow,
                                action: #selector(handleKeyboardHideMenu),
                                title: "Hide Menu"),
        ]

        let menu = UIMenu(title: "Playback",
                          options: .displayInline,
                          children: commands)
        builder.insertChild(menu, atStartOfMenu: .application)
    }

    private func makePriorityCommand(_ input: String,
                                     modifiers: UIKeyModifierFlags = [],
                                     action: Selector,
                                     title: String) -> UIKeyCommand {
        let command = UIKeyCommand(input: input,
                                   modifierFlags: modifiers,
                                   action: action)
        command.wantsPriorityOverSystemBehavior = true
        command.title = title
        return command
    }

    @objc private func handleKeyboardPlayPause() {
        NotificationCenter.default.post(name: .keyboardShortcutPlayPause, object: nil)
    }

    @objc private func handleKeyboardPrevious() {
        NotificationCenter.default.post(name: .keyboardShortcutPrevious, object: nil)
    }

    @objc private func handleKeyboardNext() {
        NotificationCenter.default.post(name: .keyboardShortcutNext, object: nil)
    }

    @objc private func handleKeyboardPreviousSentence() {
        NotificationCenter.default.post(name: .keyboardShortcutPreviousSentence, object: nil)
    }

    @objc private func handleKeyboardNextSentence() {
        NotificationCenter.default.post(name: .keyboardShortcutNextSentence, object: nil)
    }

    @objc private func handleKeyboardLookup() {
        NotificationCenter.default.post(name: .keyboardShortcutLookup, object: nil)
    }

    @objc private func handleKeyboardShowMenu() {
        NotificationCenter.default.post(name: .keyboardShortcutShowMenu, object: nil)
    }

    @objc private func handleKeyboardHideMenu() {
        NotificationCenter.default.post(name: .keyboardShortcutHideMenu, object: nil)
    }
    #endif
}
