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
                .interactiveReaderLifecycle(appState: appState)
        }
        #if os(iOS)
        .commands {
            if appState.playerKeyboardShortcutsActive {
                CommandMenu("Player") {
                    Button("Play / Pause") {
                        PlayerKeyboardShortcutBroker.shared.handleCommand(.keyboardShortcutPlayPause)
                    }
                    .keyboardShortcut(.space, modifiers: [])

                    Button("Previous") {
                        PlayerKeyboardShortcutBroker.shared.handleCommand(.keyboardShortcutPrevious)
                    }
                    .keyboardShortcut(.leftArrow, modifiers: [])

                    Button("Next") {
                        PlayerKeyboardShortcutBroker.shared.handleCommand(.keyboardShortcutNext)
                    }
                    .keyboardShortcut(.rightArrow, modifiers: [])

                    Button("Previous Sentence") {
                        PlayerKeyboardShortcutBroker.shared.handleCommand(.keyboardShortcutPreviousSentence)
                    }
                    .keyboardShortcut(.leftArrow, modifiers: [.control])

                    Button("Next Sentence") {
                        PlayerKeyboardShortcutBroker.shared.handleCommand(.keyboardShortcutNextSentence)
                    }
                    .keyboardShortcut(.rightArrow, modifiers: [.control])

                    Button("Look Up Selection") {
                        PlayerKeyboardShortcutBroker.shared.handleCommand(.keyboardShortcutLookup)
                    }
                    .keyboardShortcut(.return, modifiers: [])

                    Button("Show Player Menu") {
                        PlayerKeyboardShortcutBroker.shared.handleCommand(.keyboardShortcutShowMenu)
                    }
                    .keyboardShortcut(.downArrow, modifiers: [])

                    Button("Hide Player Menu") {
                        PlayerKeyboardShortcutBroker.shared.handleCommand(.keyboardShortcutHideMenu)
                    }
                    .keyboardShortcut(.upArrow, modifiers: [])
                }
            }
        }
        #endif
    }
}

private extension View {
    func interactiveReaderLifecycle(appState: AppState) -> some View {
        modifier(InteractiveReaderLifecycleModifier(appState: appState))
    }
}

private struct InteractiveReaderLifecycleModifier: ViewModifier {
    @ObservedObject var appState: AppState

    func body(content: Content) -> some View {
        content
            .task {
                await NotificationManager.shared.checkAuthorizationStatus()
                NotificationManager.shared.registerForPushNotificationsIfNeeded()
            }
            .onChange(of: appState.session) { _, session in
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
}
