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
                    await NotificationManager.shared.checkAuthorizationStatus()
                    await NotificationManager.shared.registerForPushNotificationsIfNeeded()
                }
                .onChange(of: appState.session) { _, session in
                    // Re-register device token when user logs in
                    if session != nil, let config = appState.configuration {
                        NotificationManager.shared.configure(with: config)
                    }
                }
                #if os(iOS)
                .onAppear {
                    PlayerKeyboardShortcutBroker.shared.setActive(appState.playerKeyboardShortcutsActive)
                }
                .onChange(of: appState.playerKeyboardShortcutsActive) { _, active in
                    PlayerKeyboardShortcutBroker.shared.setActive(active)
                }
                #endif
        }
        #if os(iOS)
        .commands {
            if appState.playerKeyboardShortcutsActive {
                CommandMenu("Player") {
                    Button("Play / Pause") {
                        NotificationCenter.default.post(name: .keyboardShortcutPlayPause, object: nil)
                    }
                    .keyboardShortcut(.space, modifiers: [])

                    Button("Previous") {
                        NotificationCenter.default.post(name: .keyboardShortcutPrevious, object: nil)
                    }
                    .keyboardShortcut(.leftArrow, modifiers: [])

                    Button("Next") {
                        NotificationCenter.default.post(name: .keyboardShortcutNext, object: nil)
                    }
                    .keyboardShortcut(.rightArrow, modifiers: [])

                    Button("Previous Sentence") {
                        NotificationCenter.default.post(name: .keyboardShortcutPreviousSentence, object: nil)
                    }
                    .keyboardShortcut(.leftArrow, modifiers: [.control])

                    Button("Next Sentence") {
                        NotificationCenter.default.post(name: .keyboardShortcutNextSentence, object: nil)
                    }
                    .keyboardShortcut(.rightArrow, modifiers: [.control])

                    Button("Look Up Selection") {
                        NotificationCenter.default.post(name: .keyboardShortcutLookup, object: nil)
                    }
                    .keyboardShortcut(.return, modifiers: [])

                    Button("Show Player Menu") {
                        NotificationCenter.default.post(name: .keyboardShortcutShowMenu, object: nil)
                    }
                    .keyboardShortcut(.downArrow, modifiers: [])

                    Button("Hide Player Menu") {
                        NotificationCenter.default.post(name: .keyboardShortcutHideMenu, object: nil)
                    }
                    .keyboardShortcut(.upArrow, modifiers: [])
                }
            }
        }
        #endif
    }
}
