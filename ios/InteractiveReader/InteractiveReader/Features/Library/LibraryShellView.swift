import SwiftUI

struct LibraryShellView: View {
    @EnvironmentObject var appState: AppState
    @StateObject private var viewModel = LibraryViewModel()
    @StateObject private var jobsViewModel = JobsViewModel()
    @State private var selectedItem: LibraryItem?
    @State private var selectedJob: PipelineStatusResponse?
    @State private var libraryAutoPlay = false
    @State private var jobsAutoPlay = false
    @State private var activeSection: BrowseSection = .library
    @Environment(\.horizontalSizeClass) private var horizontalSizeClass

    private enum BrowseSection: String, CaseIterable, Identifiable {
        case library = "Library"
        case jobs = "Jobs"

        var id: String { rawValue }
    }

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
            browseList(useNavigationLinks: true)
                .navigationDestination(for: LibraryItem.self) { item in
                    LibraryPlaybackView(item: item)
                }
                .navigationDestination(for: PipelineStatusResponse.self) { job in
                    JobPlaybackView(job: job)
                }
        }
        .onAppear {
            if viewModel.items.isEmpty {
                Task { await viewModel.load(using: appState) }
            }
            if jobsViewModel.jobs.isEmpty {
                Task { await jobsViewModel.load(using: appState) }
            }
            handleSectionChange(activeSection)
        }
        .onChange(of: activeSection) { _, newValue in
            handleSectionChange(newValue)
        }
        #else
        Group {
            if isSplitLayout {
                NavigationSplitView {
                    browseList(useNavigationLinks: false)
                } detail: {
                    detailView
                }
            } else {
                NavigationStack {
                    browseList(useNavigationLinks: true)
                        .navigationDestination(for: LibraryItem.self) { item in
                            LibraryPlaybackView(item: item)
                        }
                        .navigationDestination(for: PipelineStatusResponse.self) { job in
                            JobPlaybackView(job: job)
                        }
                }
            }
        }
        .onAppear {
            if viewModel.items.isEmpty {
                Task { await viewModel.load(using: appState) }
            }
            if jobsViewModel.jobs.isEmpty {
                Task { await jobsViewModel.load(using: appState) }
            }
            handleSectionChange(activeSection)
        }
        .onChange(of: activeSection) { _, newValue in
            handleSectionChange(newValue)
        }
        #endif
    }

    @ViewBuilder
    private var detailView: some View {
        switch activeSection {
        case .library:
            if let selectedItem {
                LibraryPlaybackView(item: selectedItem, autoPlayOnLoad: $libraryAutoPlay)
            } else {
                VStack(spacing: 12) {
                    Text("Select a library entry")
                        .font(.title3)
                    Text("Choose a book, subtitle, or video to start playback.")
                        .foregroundStyle(.secondary)
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            }
        case .jobs:
            if let selectedJob {
                JobPlaybackView(job: selectedJob, autoPlayOnLoad: $jobsAutoPlay)
            } else {
                VStack(spacing: 12) {
                    Text("Select a job")
                        .font(.title3)
                    Text("Choose an active or finished job to start playback.")
                        .foregroundStyle(.secondary)
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            }
        }
    }

    @ViewBuilder
    private func browseList(useNavigationLinks: Bool) -> some View {
        VStack(spacing: 10) {
            #if !os(tvOS)
            sectionPicker
            #endif
            switch activeSection {
            case .library:
                LibraryView(
                    viewModel: viewModel,
                    useNavigationLinks: useNavigationLinks,
                    onRefresh: {
                        Task { await viewModel.load(using: appState) }
                    },
                    onSignOut: {
                        appState.signOut()
                    },
                    onSelect: { item in
                        selectedItem = item
                        libraryAutoPlay = true
                    },
                    coverResolver: coverURL(for:),
                    resumeUserId: resumeUserId,
                    sectionPicker: sectionPickerForHeader
                )
            case .jobs:
                JobsView(
                    viewModel: jobsViewModel,
                    useNavigationLinks: useNavigationLinks,
                    onRefresh: {
                        Task { await jobsViewModel.load(using: appState) }
                    },
                    onSignOut: {
                        appState.signOut()
                    },
                    onSelect: { job in
                        selectedJob = job
                        jobsAutoPlay = true
                    },
                    sectionPicker: sectionPickerForHeader,
                    resumeUserId: resumeUserId
                )
            }
        }
        .navigationTitle(activeSection.rawValue)
    }

    private var sectionPicker: some View {
        Picker("Browse", selection: $activeSection) {
            ForEach(BrowseSection.allCases) { section in
                Text(section.rawValue).tag(section)
            }
        }
        #if os(tvOS)
        .pickerStyle(.automatic)
        #else
        .pickerStyle(.segmented)
        #endif
        .padding(.horizontal)
    }

    private var sectionPickerForHeader: AnyView? {
        #if os(tvOS)
        return AnyView(sectionPicker)
        #else
        return nil
        #endif
    }

    private func coverURL(for item: LibraryItem) -> URL? {
        guard let apiBaseURL = appState.apiBaseURL else { return nil }
        let resolver = LibraryCoverResolver(apiBaseURL: apiBaseURL, accessToken: appState.authToken)
        return resolver.resolveCoverURL(for: item)
    }

    private var resumeUserId: String? {
        appState.session?.user.username.nonEmptyValue ?? appState.lastUsername.nonEmptyValue
    }

    private func handleSectionChange(_ newValue: BrowseSection) {
        switch newValue {
        case .library:
            jobsViewModel.stopAutoRefresh()
            jobsAutoPlay = false
        case .jobs:
            jobsViewModel.startAutoRefresh(using: appState)
            libraryAutoPlay = false
        }
    }
}
