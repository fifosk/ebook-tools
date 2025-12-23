import SwiftUI

struct LibraryShellView: View {
    @EnvironmentObject var appState: AppState
    @StateObject private var viewModel = LibraryViewModel()
    @State private var selectedItem: LibraryItem?
    @Environment(\.horizontalSizeClass) private var horizontalSizeClass

    private var isSplitLayout: Bool {
        #if !os(tvOS)
        return horizontalSizeClass == .regular
        #else
        return false
        #endif
    }

    var body: some View {
        #if os(tvOS)
        NavigationStack {
            libraryList(useNavigationLinks: true)
                .navigationDestination(for: LibraryItem.self) { item in
                    LibraryPlaybackView(item: item)
                }
        }
        .onAppear {
            if viewModel.items.isEmpty {
                Task { await viewModel.load(using: appState) }
            }
        }
        #else
        Group {
            if isSplitLayout {
                NavigationSplitView {
                    libraryList(useNavigationLinks: false)
                } detail: {
                    detailView
                }
            } else {
                NavigationStack {
                    libraryList(useNavigationLinks: true)
                        .navigationDestination(for: LibraryItem.self) { item in
                            LibraryPlaybackView(item: item)
                        }
                }
            }
        }
        .onAppear {
            if viewModel.items.isEmpty {
                Task { await viewModel.load(using: appState) }
            }
        }
        .onChange(of: viewModel.filteredItems) { _, newItems in
            if isSplitLayout && selectedItem == nil {
                selectedItem = newItems.first
            }
        }
        #endif
    }

    @ViewBuilder
    private var detailView: some View {
        if let selectedItem {
            LibraryPlaybackView(item: selectedItem)
        } else {
            VStack(spacing: 12) {
                Text("Select a library entry")
                    .font(.title3)
                Text("Choose a book, subtitle, or video to start playback.")
                    .foregroundStyle(.secondary)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
    }

    @ViewBuilder
    private func libraryList(useNavigationLinks: Bool) -> some View {
        LibraryView(
            viewModel: viewModel,
            useNavigationLinks: useNavigationLinks,
            onRefresh: {
                Task { await viewModel.load(using: appState) }
            },
            onSignOut: {
                appState.signOut()
            },
            onSelect: { selectedItem = $0 },
            coverResolver: coverURL(for:)
        )
        .navigationTitle("Library")
    }

    private func coverURL(for item: LibraryItem) -> URL? {
        guard let apiBaseURL = appState.apiBaseURL else { return nil }
        let resolver = LibraryCoverResolver(apiBaseURL: apiBaseURL, accessToken: appState.authToken)
        return resolver.resolveCoverURL(for: item)
    }
}
