import SwiftUI

struct RootView: View {
    @EnvironmentObject var appState: AppState
    @EnvironmentObject var offlineStore: OfflineMediaStore

    var body: some View {
        Group {
            #if os(tvOS)
            TVRootView(appState: appState)
            #elseif os(iOS)
            IOSRootView(appState: appState)
            #else
            mainContent
            #endif
        }
        .task {
            await appState.restoreSessionIfNeeded()
        }
        .task(id: appState.session?.token) {
            guard let configuration = appState.configuration else { return }
            offlineStore.syncSharedReadingBedsIfNeeded(configuration: configuration)
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

#if os(iOS)
private struct IOSRootView: View {
    @Environment(\.colorScheme) private var colorScheme
    @Environment(\.horizontalSizeClass) private var horizontalSizeClass
    @ObservedObject var appState: AppState

    /// Whether to use dark background (iPad in light mode, matching tvOS style)
    private var usesDarkBackground: Bool {
        horizontalSizeClass != .compact && colorScheme == .light
    }

    /// In debug builds, skip the "checking session" screen to speed up development
    /// Show login immediately while session restore happens in background
    private var shouldShowRestoringScreen: Bool {
        #if DEBUG
        return false  // Skip loading screen in debug - go straight to login
        #else
        return appState.isRestoring
        #endif
    }

    var body: some View {
        ZStack {
            if usesDarkBackground {
                AppTheme.lightBackground
                    .ignoresSafeArea()
            }
            if shouldShowRestoringScreen {
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
