import SwiftUI

struct RootView: View {
    @EnvironmentObject var appState: AppState

    var body: some View {
        Group {
            if appState.isRestoring {
                VStack(spacing: 12) {
                    ProgressView()
                    Text("Checking session…")
                        .font(.callout)
                        .foregroundStyle(.secondary)
                }
            } else if appState.session != nil {
                LibraryShellView()
            } else {
                LoginView()
            }
        }
        .task {
            await appState.restoreSessionIfNeeded()
        }
    }
}
