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
        .rootSessionLifecycle(appState: appState, offlineStore: offlineStore)
    }

    private var mainContent: some View {
        Group {
            if appState.isRestoring {
                RestoringSessionView()
            } else if appState.session != nil {
                LibraryShellView()
            } else {
                LoginView()
            }
        }
    }
}

private extension View {
    func rootSessionLifecycle(appState: AppState, offlineStore: OfflineMediaStore) -> some View {
        modifier(RootSessionLifecycleModifier(appState: appState, offlineStore: offlineStore))
    }
}

private struct RootSessionLifecycleModifier: ViewModifier {
    @ObservedObject var appState: AppState
    @ObservedObject var offlineStore: OfflineMediaStore

    func body(content: Content) -> some View {
        content
            .task {
                await appState.restoreSessionIfNeeded()
            }
            .task(id: appState.session?.token) {
                guard let configuration = appState.configuration else { return }
                offlineStore.syncSharedReadingBedsIfNeeded(configuration: configuration)
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

    /// In debug builds, keep fresh-login iteration fast, but avoid flashing the
    /// login form when a saved token is actively being validated.
    private var shouldShowRestoringScreen: Bool {
        #if DEBUG
        return appState.isRestoring && appState.authToken != nil
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
                RestoringSessionView()
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
                RestoringSessionView()
            } else if appState.session != nil {
                LibraryShellView()
            } else {
                LoginView()
            }
        }
    }
}
#endif

private struct RestoringSessionView: View {
    var body: some View {
        VStack(spacing: 12) {
            ProgressView()
            Text("Checking session…")
                .font(.callout)
                .foregroundStyle(.secondary)
        }
        .accessibilityIdentifier("restoringSessionView")
    }
}
