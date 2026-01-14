import SwiftUI

@main
struct InteractiveReaderApp: App {
    @StateObject private var appState = AppState()
    @StateObject private var offlineStore = OfflineMediaStore()

    var body: some Scene {
        WindowGroup {
            RootView()
                .environmentObject(appState)
                .environmentObject(offlineStore)
        }
    }
}
