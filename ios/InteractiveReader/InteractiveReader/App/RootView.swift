import SwiftUI

struct RootView: View {
    @EnvironmentObject var appState: AppState

    var body: some View {
        Group {
            #if os(tvOS)
            TVRootView(appState: appState)
            #else
            mainContent
            #endif
        }
        .task {
            await appState.restoreSessionIfNeeded()
        }
    }

    private var mainContent: some View {
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
    }
}

#if os(tvOS)
private struct TVRootView: View {
    @Environment(\.colorScheme) private var colorScheme
    @ObservedObject var appState: AppState

    var body: some View {
        ZStack {
            AppTheme.background(for: colorScheme)
                .ignoresSafeArea()
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
    }
}
#endif
