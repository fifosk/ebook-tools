import SwiftUI

@main
struct InteractiveReaderApp: App {
    #if os(iOS)
    @UIApplicationDelegateAdaptor(AppDelegate.self) var appDelegate
    #endif

    @StateObject private var appState = AppState()
    @StateObject private var offlineStore = OfflineMediaStore()

    var body: some Scene {
        WindowGroup {
            RootView()
                .environmentObject(appState)
                .environmentObject(offlineStore)
                .task {
                    // Request notification permission after app launch
                    await NotificationManager.shared.requestAuthorization()
                }
                .onChange(of: appState.session) { _, session in
                    // Re-register device token when user logs in
                    if let session, let config = appState.configuration {
                        NotificationManager.shared.configure(with: config)
                    }
                }
                .onReceive(NotificationManager.shared.$pendingJobId) { jobId in
                    // Handle notification tap - navigate to job
                    // This will be handled by LibraryShellView
                    if let jobId {
                        print("[App] Received pending job ID from notification: \(jobId)")
                    }
                }
        }
        #if os(iOS)
        // App-level command registration is iPadOS's canonical way to
        // publish hardware-keyboard shortcuts into the menu system. Magic
        // Keyboard events go through this dispatcher BEFORE SwiftUI's
        // focus-aware keyboard routing consumes them for button activation
        // or scroll navigation, so these shortcuts win against all the
        // usual focus contenders.
        .commands {
            CommandMenu("Playback") {
                Button("Play / Pause") {
                    print("[Commands] Play/Pause shortcut fired")
                    NotificationCenter.default.post(
                        name: .keyboardShortcutPlayPause, object: nil
                    )
                }
                .keyboardShortcut(" ", modifiers: [])

                Button("Previous") {
                    print("[Commands] Previous shortcut fired")
                    NotificationCenter.default.post(
                        name: .keyboardShortcutPrevious, object: nil
                    )
                }
                .keyboardShortcut(.leftArrow, modifiers: [])

                Button("Next") {
                    print("[Commands] Next shortcut fired")
                    NotificationCenter.default.post(
                        name: .keyboardShortcutNext, object: nil
                    )
                }
                .keyboardShortcut(.rightArrow, modifiers: [])

                Button("Previous Sentence") {
                    NotificationCenter.default.post(
                        name: .keyboardShortcutPreviousSentence, object: nil
                    )
                }
                .keyboardShortcut(.leftArrow, modifiers: [.control])

                Button("Next Sentence") {
                    NotificationCenter.default.post(
                        name: .keyboardShortcutNextSentence, object: nil
                    )
                }
                .keyboardShortcut(.rightArrow, modifiers: [.control])

                Button("Look Up Highlighted Word") {
                    print("[Commands] Lookup shortcut fired")
                    NotificationCenter.default.post(
                        name: .keyboardShortcutLookup, object: nil
                    )
                }
                .keyboardShortcut(.return, modifiers: [])

                Button("Show Menu") {
                    NotificationCenter.default.post(
                        name: .keyboardShortcutShowMenu, object: nil
                    )
                }
                .keyboardShortcut(.downArrow, modifiers: [])

                Button("Hide Menu") {
                    NotificationCenter.default.post(
                        name: .keyboardShortcutHideMenu, object: nil
                    )
                }
                .keyboardShortcut(.upArrow, modifiers: [])
            }
        }
        #endif
    }
}
