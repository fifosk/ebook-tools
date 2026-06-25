import SwiftUI
import OSLog

struct LibraryShellView: View {
    private static let sidebarColumnMinWidth: CGFloat = 240
    private static let sidebarColumnIdealWidth: CGFloat = 280
    private static let sidebarColumnMaxWidth: CGFloat = 320
    private static let createDetailColumnMinWidth: CGFloat = 760
    private static let createDetailColumnIdealWidth: CGFloat = 940

    @EnvironmentObject var appState: AppState
    @StateObject private var viewModel = LibraryViewModel()
    @StateObject private var jobsViewModel = JobsViewModel()
    @State private var selectedItem: LibraryItem?
    @State private var selectedJob: PipelineStatusResponse?
    @State private var libraryAutoPlay = false
    @State private var jobsAutoPlay = false
    @State private var libraryPlaybackMode: PlaybackStartMode = .resume
    @State private var jobsPlaybackMode: PlaybackStartMode = .resume
    @State private var activeSection: BrowseSection = .jobs
    @State private var lastBrowseSection: BrowseSection = .jobs
    @State private var createMode = AppleCreateMode.generatedBook
    @State private var navigationPath = NavigationPath()
    #if !os(tvOS)
    @State private var columnVisibility: NavigationSplitViewVisibility = .all
    #endif
    @Environment(\.horizontalSizeClass) private var horizontalSizeClass
    @Environment(\.colorScheme) private var colorScheme
    private let logger = Logger(subsystem: "InteractiveReader", category: "LibraryShell")

    private var isSplitLayout: Bool {
        #if !os(tvOS)
        return horizontalSizeClass == .regular
        #else
        return false
        #endif
    }

    private var isCompactLayout: Bool {
        #if !os(tvOS)
        return horizontalSizeClass == .compact
        #else
        return false
        #endif
    }

    /// Whether to use dark background (iOS in light mode, matching tvOS style)
    private var usesDarkBackground: Bool {
        #if os(iOS)
        return colorScheme == .light
        #else
        return false
        #endif
    }

    var body: some View {
        #if os(tvOS)
        NavigationStack(path: $navigationPath) {
            browseList()
                .navigationDestination(for: LibraryItem.self) { item in
                    LibraryPlaybackView(item: item, autoPlayOnLoad: $libraryAutoPlay, playbackMode: libraryPlaybackMode)
                }
                .navigationDestination(for: PipelineStatusResponse.self) { job in
                    JobPlaybackView(job: job, autoPlayOnLoad: $jobsAutoPlay, playbackMode: jobsPlaybackMode)
                }
        }
        .onAppear(perform: loadBrowseDataIfNeeded)
        .onChange(of: activeSection) { _, newValue in
            handleSectionChange(newValue)
        }
        .accessibilityIdentifier("libraryShellView")
        #else
        ZStack {
            if usesDarkBackground {
                AppTheme.lightBackground
                    .ignoresSafeArea()
            }
            Group {
                if isSplitLayout {
                    NavigationSplitView(columnVisibility: $columnVisibility) {
                        browseList()
                            .navigationSplitViewColumnWidth(
                                min: Self.sidebarColumnMinWidth,
                                ideal: Self.sidebarColumnIdealWidth,
                                max: Self.sidebarColumnMaxWidth
                            )
                            .background(usesDarkBackground ? AppTheme.lightBackground : Color.clear)
                            .toolbarBackground(usesDarkBackground ? AppTheme.lightBackground : Color.clear, for: .navigationBar)
                            .toolbarBackground(usesDarkBackground ? .visible : .automatic, for: .navigationBar)
                            .toolbarColorScheme(usesDarkBackground ? .dark : nil, for: .navigationBar)
                    } detail: {
                        detailView
                    }
                    .navigationSplitViewStyle(.balanced)
                    .tint(usesDarkBackground ? .white : nil)
                } else {
                    NavigationStack(path: $navigationPath) {
                        browseList()
                            .navigationDestination(for: LibraryItem.self) { item in
                                LibraryPlaybackView(item: item, autoPlayOnLoad: $libraryAutoPlay, playbackMode: libraryPlaybackMode)
                            }
                            .navigationDestination(for: PipelineStatusResponse.self) { job in
                                JobPlaybackView(job: job, autoPlayOnLoad: $jobsAutoPlay, playbackMode: jobsPlaybackMode)
                            }
                    }
                }
            }
        }
        .onAppear(perform: loadBrowseDataIfNeeded)
        .onChange(of: activeSection) { _, newValue in
            handleSectionChange(newValue)
        }
        .onReceive(NotificationManager.shared.$pendingJobId) { jobId in
            handleNotificationTap(jobId: jobId)
        }
        .accessibilityIdentifier("libraryShellView")
        #endif
    }

    @ViewBuilder
    private var detailView: some View {
        switch activeSection {
        case .create:
            AppleBookCreateView(
                sectionPicker: nil,
                creationMode: $createMode,
                showsInlineJobTypePicker: true,
                onJobSubmitted: handleCreatedJob,
                onOpenJobs: openCreatedJob,
                recentJobs: jobsViewModel.jobs,
                usesDarkBackground: usesDarkBackground
            )
            .navigationSplitViewColumnWidth(
                min: Self.createDetailColumnMinWidth,
                ideal: Self.createDetailColumnIdealWidth
            )
        case .library:
            if let selectedItem {
                LibraryPlaybackView(item: selectedItem, autoPlayOnLoad: $libraryAutoPlay, playbackMode: libraryPlaybackMode)
                    .id(selectedItem.jobId)
            } else {
                placeholderView(
                    title: "Select a library entry",
                    systemImage: "books.vertical",
                    subtitle: "Choose a book, subtitle, or video to start playback."
                )
            }
        case .jobs:
            if let selectedJob {
                JobPlaybackView(job: selectedJob, autoPlayOnLoad: $jobsAutoPlay, playbackMode: jobsPlaybackMode)
                    .id(selectedJob.jobId)
            } else {
                placeholderView(
                    title: "Select a job",
                    systemImage: "tray.full",
                    subtitle: "Choose an active or finished job to start playback."
                )
            }
        case .search:
            if let selectedItem {
                LibraryPlaybackView(item: selectedItem, autoPlayOnLoad: $libraryAutoPlay, playbackMode: libraryPlaybackMode)
                    .id(selectedItem.jobId)
            } else if let selectedJob {
                JobPlaybackView(job: selectedJob, autoPlayOnLoad: $jobsAutoPlay, playbackMode: jobsPlaybackMode)
                    .id(selectedJob.jobId)
            } else {
                placeholderView(
                    title: "Search jobs and library",
                    systemImage: "magnifyingglass",
                    subtitle: "Use the search field to find items across your library and jobs."
                )
            }
        case .settings:
            PlaybackSettingsView(sectionPicker: sectionPickerForHeader, usesDarkBackground: usesDarkBackground)
        }
    }

    @ViewBuilder
    private func placeholderView(title: String, systemImage: String, subtitle: String) -> some View {
        ContentUnavailableView {
            Label(title, systemImage: systemImage)
        } description: {
            Text(subtitle)
        }
        .foregroundStyle(usesDarkBackground ? .white : .primary)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(usesDarkBackground ? AppTheme.lightBackground : Color.clear)
        #if os(iOS)
        .toolbarBackground(usesDarkBackground ? AppTheme.lightBackground : Color.clear, for: .navigationBar)
        .toolbarBackground(usesDarkBackground ? .visible : .automatic, for: .navigationBar)
        .toolbarColorScheme(usesDarkBackground ? .dark : nil, for: .navigationBar)
        #endif
    }

    @ViewBuilder
    private func browseList() -> some View {
        VStack(spacing: 10) {
            switch activeSection {
            case .library:
                LibraryView(
                    viewModel: viewModel,
                    onRefresh: refreshLibrary,
                    onSelect: selectLibraryItem,
                    coverResolver: coverURL(for:),
                    resumeUserId: resumeUserId,
                    sectionPicker: sectionPickerForHeader,
                    onCollapseSidebar: isSplitLayout ? { collapseSidebar() } : nil,
                    onSearchRequested: showSearch,
                    usesDarkBackground: usesDarkBackground
                )
            case .jobs:
                JobsView(
                    viewModel: jobsViewModel,
                    onRefresh: refreshJobs,
                    onSelect: selectJob,
                    sectionPicker: sectionPickerForHeader,
                    resumeUserId: resumeUserId,
                    onCollapseSidebar: isSplitLayout ? { collapseSidebar() } : nil,
                    onSearchRequested: showSearch,
                    usesDarkBackground: usesDarkBackground
                )
            case .create:
                if isSplitLayout {
                    createSidebarPlaceholder
                } else {
                    AppleBookCreateView(
                        sectionPicker: sectionPickerForHeader,
                        creationMode: $createMode,
                        showsInlineJobTypePicker: true,
                        onJobSubmitted: handleCreatedJob,
                        onOpenJobs: openCreatedJob,
                        recentJobs: jobsViewModel.jobs,
                        usesDarkBackground: usesDarkBackground
                    )
                }
            case .search:
                CombinedSearchView(
                    libraryViewModel: viewModel,
                    jobsViewModel: jobsViewModel,
                    onSelectItem: selectLibraryItem,
                    onSelectJob: selectJob,
                    coverResolver: coverURL(for:),
                    resumeUserId: resumeUserId,
                    sectionPicker: sectionPickerForHeader,
                    usesDarkBackground: usesDarkBackground
                )
            case .settings:
                if isSplitLayout {
                    placeholderView(
                        title: "Settings",
                        systemImage: "gearshape",
                        subtitle: "Adjust playback options in the detail panel."
                    )
                } else {
                    PlaybackSettingsView(
                        sectionPicker: sectionPickerForHeader,
                        backTitle: isCompactLayout ? lastBrowseSection.rawValue : nil,
                        onBack: isCompactLayout ? returnToLastBrowseSection : nil,
                        usesDarkBackground: usesDarkBackground
                    )
                }
            }
        }
        #if !os(tvOS)
        .navigationTitle(isCompactLayout ? "" : activeSection.rawValue)
        .navigationBarTitleDisplayMode(isCompactLayout ? .inline : .automatic)
        .toolbarBackground(usesDarkBackground ? AppTheme.lightBackground : Color.clear, for: .navigationBar)
        .toolbarBackground(usesDarkBackground ? .visible : .automatic, for: .navigationBar)
        .toolbarColorScheme(usesDarkBackground ? .dark : nil, for: .navigationBar)
        #else
        .navigationTitle("")
        #endif
    }

    private var createSidebarPlaceholder: some View {
        VStack(spacing: 12) {
            sectionPickerForHeader
            ContentUnavailableView {
                Label("Create", systemImage: "square.and.pencil")
            }
            .foregroundStyle(usesDarkBackground ? .white : .primary)
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
        .background(usesDarkBackground ? AppTheme.lightBackground : Color.clear)
        #if os(iOS)
        .toolbarBackground(usesDarkBackground ? AppTheme.lightBackground : Color.clear, for: .navigationBar)
        .toolbarBackground(usesDarkBackground ? .visible : .automatic, for: .navigationBar)
        .toolbarColorScheme(usesDarkBackground ? .dark : nil, for: .navigationBar)
        #endif
    }

    private var sectionPickerForHeader: BrowseSectionPicker {
        BrowseSectionPicker(
            activeSection: $activeSection,
            usesDarkBackground: usesDarkBackground,
            colorScheme: colorScheme,
            onRefresh: handleSectionRefresh
        )
    }

    private func coverURL(for item: LibraryItem) -> URL? {
        guard let apiBaseURL = appState.apiBaseURL else { return nil }
        let resolver = LibraryCoverResolver(apiBaseURL: apiBaseURL, accessToken: appState.authToken)
        return resolver.resolveCoverURL(for: item)
    }

    private var resumeUserId: String? {
        appState.resumeUserKey
    }

    private func loadBrowseDataIfNeeded() {
        if viewModel.items.isEmpty {
            refreshLibrary()
        }
        if jobsViewModel.jobs.isEmpty {
            refreshJobs()
        }
        handleSectionChange(activeSection)
    }

    private func refreshLibrary() {
        Task { await viewModel.load(using: appState) }
    }

    private func refreshJobs() {
        Task { await jobsViewModel.load(using: appState) }
    }

    private func signOut() {
        appState.signOut()
    }

    private func showSearch() {
        activeSection = .search
    }

    private func returnToLastBrowseSection() {
        activeSection = lastBrowseSection
    }

    private func selectLibraryItem(_ item: LibraryItem, mode: PlaybackStartMode) {
        selectedItem = item
        libraryAutoPlay = true
        libraryPlaybackMode = mode
        pushOrReveal(item)
    }

    private func selectJob(_ job: PipelineStatusResponse, mode: PlaybackStartMode) {
        selectedJob = job
        jobsAutoPlay = true
        jobsPlaybackMode = mode
        pushOrReveal(job)
    }

    private func handleSectionChange(_ newValue: BrowseSection) {
        if newValue != .settings {
            lastBrowseSection = newValue
        }
        switch newValue {
        case .create:
            jobsViewModel.stopAutoRefresh()
            libraryAutoPlay = false
            jobsAutoPlay = false
        case .library:
            jobsViewModel.stopAutoRefresh()
            jobsAutoPlay = false
        case .jobs:
            jobsViewModel.startAutoRefresh(using: appState)
            libraryAutoPlay = false
        case .search:
            jobsViewModel.stopAutoRefresh()
            libraryAutoPlay = false
            jobsAutoPlay = false
        case .settings:
            jobsViewModel.stopAutoRefresh()
            libraryAutoPlay = false
            jobsAutoPlay = false
        }
    }

    private func handleSectionRefresh() {
        switch activeSection {
        case .create:
            return
        case .jobs:
            Task { await jobsViewModel.load(using: appState) }
        case .library:
            Task { await viewModel.load(using: appState) }
        case .search:
            Task {
                await viewModel.load(using: appState)
                await jobsViewModel.load(using: appState)
            }
        case .settings:
            return
        }
    }

    private func handleCreatedJob(_ jobId: String) {
        activeSection = .jobs
        jobsAutoPlay = false
        jobsPlaybackMode = .resume
        Task { await focusCreatedJob(jobId) }
    }

    private func openCreatedJob(_ jobId: String) {
        activeSection = .jobs
        jobsAutoPlay = false
        jobsPlaybackMode = .resume
        Task {
            await focusCreatedJob(jobId)
        }
    }

    @MainActor
    private func focusCreatedJob(_ jobId: String) async {
        await jobsViewModel.load(using: appState)
        guard let job = jobsViewModel.jobs.first(where: { $0.jobId == jobId }) else {
            jobsViewModel.startAutoRefresh(using: appState)
            return
        }
        navigateToJob(job, autoPlay: false)
        jobsViewModel.startAutoRefresh(using: appState)
    }

    /// Handle notification tap - navigate to job and start playback
    private func handleNotificationTap(jobId: String?) {
        guard let jobId else { return }
        logger.info("Handling notification tap jobId=\(jobId, privacy: .private)")

        // Clear the pending ID immediately to prevent re-triggering
        NotificationManager.shared.clearPendingJobId()

        // First, try to find the job in the jobs list
        if let job = jobsViewModel.jobs.first(where: { $0.jobId == jobId }) {
            navigateToJob(job, autoPlay: true)
            return
        }

        // If not in jobs, try library
        if let item = viewModel.items.first(where: { $0.jobId == jobId }) {
            navigateToLibraryItem(item, autoPlay: true)
            return
        }

        // Job not found in cache - refresh and try again
        Task {
            // Refresh jobs list
            await jobsViewModel.load(using: appState)

            if let job = jobsViewModel.jobs.first(where: { $0.jobId == jobId }) {
                await MainActor.run {
                    navigateToJob(job, autoPlay: true)
                }
                return
            }

            // Try library
            await viewModel.load(using: appState)

            if let item = viewModel.items.first(where: { $0.jobId == jobId }) {
                await MainActor.run {
                    navigateToLibraryItem(item, autoPlay: true)
                }
            }
        }
    }

    private func navigateToJob(_ job: PipelineStatusResponse, autoPlay: Bool) {
        // Switch to jobs section
        activeSection = .jobs
        jobsViewModel.activeFilter = jobsViewModel.jobCategory(for: job)

        // Set auto-play mode
        jobsAutoPlay = autoPlay
        jobsPlaybackMode = .resume

        #if os(tvOS)
        // On tvOS, use navigation path
        navigationPath.append(job)
        #else
        // On iOS/iPadOS, set selected job
        selectedJob = job
        if isSplitLayout {
            collapseSidebar()
        } else {
            navigationPath.append(job)
        }
        #endif
    }

    private func navigateToLibraryItem(_ item: LibraryItem, autoPlay: Bool) {
        // Switch to library section
        activeSection = .library

        // Set auto-play mode
        libraryAutoPlay = autoPlay
        libraryPlaybackMode = .resume

        #if os(tvOS)
        // On tvOS, use navigation path
        navigationPath.append(item)
        #else
        // On iOS/iPadOS, set selected item
        selectedItem = item
        if isSplitLayout {
            collapseSidebar()
        } else {
            navigationPath.append(item)
        }
        #endif
    }

    private func pushOrReveal<Value: Hashable>(_ value: Value) {
        if isSplitLayout {
            collapseSidebar()
        } else {
            navigationPath.append(value)
        }
    }

    private func collapseSidebar() {
        #if !os(tvOS)
        guard isSplitLayout else { return }
        withAnimation(.easeInOut(duration: 0.2)) {
            columnVisibility = .detailOnly
        }
        #endif
    }
}
