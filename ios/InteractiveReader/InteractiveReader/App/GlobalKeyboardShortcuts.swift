import Foundation

/// Notification names for app-level keyboard shortcuts.
///
/// Shortcuts are registered on `AppDelegate` via `buildMenu(with:)` so they
/// sit at the very top of the UIResponder chain and fire regardless of
/// which SwiftUI view currently has focus. When the user presses a
/// shortcut, `AppDelegate` receives the action selector and posts one of
/// these notifications. Any view that cares observes the notification and
/// runs its own handler.
///
/// Using notifications rather than a dedicated first-responder controller
/// sidesteps the recurring problem where SwiftUI Buttons / ScrollViews
/// take first responder away from us after user interaction, leaving
/// Space/arrows silently dead until the next tap.
extension Notification.Name {
    static let keyboardShortcutPlayPause = Notification.Name(
        "com.interactivereader.keyboard.playPause"
    )
    static let keyboardShortcutPrevious = Notification.Name(
        "com.interactivereader.keyboard.previous"
    )
    static let keyboardShortcutNext = Notification.Name(
        "com.interactivereader.keyboard.next"
    )
    static let keyboardShortcutPreviousSentence = Notification.Name(
        "com.interactivereader.keyboard.previousSentence"
    )
    static let keyboardShortcutNextSentence = Notification.Name(
        "com.interactivereader.keyboard.nextSentence"
    )
    static let keyboardShortcutLookup = Notification.Name(
        "com.interactivereader.keyboard.lookup"
    )
    static let keyboardShortcutShowMenu = Notification.Name(
        "com.interactivereader.keyboard.showMenu"
    )
    static let keyboardShortcutHideMenu = Notification.Name(
        "com.interactivereader.keyboard.hideMenu"
    )
}
