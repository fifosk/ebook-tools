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
    }
}
