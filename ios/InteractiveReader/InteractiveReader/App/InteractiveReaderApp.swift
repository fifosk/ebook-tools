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
