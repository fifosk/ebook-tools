import SwiftUI

struct LibraryShellView: View {
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
    @State private var navigationPath = NavigationPath()
    #if !os(tvOS)
    @State private var columnVisibility: NavigationSplitViewVisibility = .all
    #endif
    @Environment(\.horizontalSizeClass) private var horizontalSizeClass
    @Environment(\.colorScheme) private var colorScheme

    private enum BrowseSection: String, CaseIterable, Identifiable {
        case jobs = "Jobs"
        case library = "Library"
        case settings = "Settings"
        case search = "Search"

        var id: String { rawValue }
    }

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
        ZStack {
            if usesDarkBackground {
                AppTheme.lightBackground
                    .ignoresSafeArea()
            }
            Group {
                if isSplitLayout {
                    NavigationSplitView(columnVisibility: $columnVisibility) {
                        browseList()
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
                LibraryPlaybackView(item: selectedItem, autoPlayOnLoad: $libraryAutoPlay, playbackMode: libraryPlaybackMode)
                    .id(selectedItem.jobId)
            } else {
                placeholderView(
                    title: "Select a library entry",
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
                    subtitle: "Use the search field to find items across your library and jobs."
                )
            }
        case .settings:
            PlaybackSettingsView(sectionPicker: sectionPickerForHeader, usesDarkBackground: usesDarkBackground)
        }
    }

    @ViewBuilder
    private func placeholderView(title: String, subtitle: String) -> some View {
        VStack(spacing: 12) {
            Text(title)
                .font(.title3)
                .foregroundStyle(usesDarkBackground ? .white : .primary)
            Text(subtitle)
                .foregroundStyle(usesDarkBackground ? .white.opacity(0.7) : .secondary)
        }
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
                    onRefresh: {
                        Task { await viewModel.load(using: appState) }
                    },
                    onSignOut: {
                        appState.signOut()
                    },
                    onSelect: { item, mode in
                        selectedItem = item
                        libraryAutoPlay = true
                        libraryPlaybackMode = mode
                        if isSplitLayout {
                            collapseSidebar()
                        } else {
                            navigationPath.append(item)
                        }
                    },
                    coverResolver: coverURL(for:),
                    resumeUserId: resumeUserId,
                    sectionPicker: sectionPickerForHeader,
                    onCollapseSidebar: isSplitLayout ? { collapseSidebar() } : nil,
                    onSearchRequested: { activeSection = .search },
                    usesDarkBackground: usesDarkBackground
                )
            case .jobs:
                JobsView(
                    viewModel: jobsViewModel,
                    onRefresh: {
                        Task { await jobsViewModel.load(using: appState) }
                    },
                    onSignOut: {
                        appState.signOut()
                    },
                    onSelect: { job, mode in
                        selectedJob = job
                        jobsAutoPlay = true
                        jobsPlaybackMode = mode
                        if isSplitLayout {
                            collapseSidebar()
                        } else {
                            navigationPath.append(job)
                        }
                    },
                    sectionPicker: sectionPickerForHeader,
                    resumeUserId: resumeUserId,
                    onCollapseSidebar: isSplitLayout ? { collapseSidebar() } : nil,
                    onSearchRequested: { activeSection = .search },
                    usesDarkBackground: usesDarkBackground
                )
            case .search:
                CombinedSearchView(
                    libraryViewModel: viewModel,
                    jobsViewModel: jobsViewModel,
                    onRefresh: {
                        Task {
                            await viewModel.load(using: appState)
                            await jobsViewModel.load(using: appState)
                        }
                    },
                    onSignOut: {
                        appState.signOut()
                    },
                    onSelectItem: { item, mode in
                        selectedItem = item
                        libraryAutoPlay = true
                        libraryPlaybackMode = mode
                        if isSplitLayout {
                            collapseSidebar()
                        } else {
                            navigationPath.append(item)
                        }
                    },
                    onSelectJob: { job, mode in
                        selectedJob = job
                        jobsAutoPlay = true
                        jobsPlaybackMode = mode
                        if isSplitLayout {
                            collapseSidebar()
                        } else {
                            navigationPath.append(job)
                        }
                    },
                    coverResolver: coverURL(for:),
                    resumeUserId: resumeUserId,
                    sectionPicker: sectionPickerForHeader
                )
            case .settings:
                if isSplitLayout {
                    placeholderView(
                        title: "Settings",
                        subtitle: "Adjust playback options in the detail panel."
                    )
                } else {
                    PlaybackSettingsView(
                        sectionPicker: sectionPickerForHeader,
                        backTitle: isCompactLayout ? lastBrowseSection.rawValue : nil,
                        onBack: isCompactLayout ? { activeSection = lastBrowseSection } : nil,
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

    private var sectionPicker: some View {
        Picker("Browse", selection: $activeSection) {
            ForEach(orderedSections) { section in
                sectionPickerLabel(for: section)
                    .tag(section)
            }
        }
        #if os(tvOS)
        .pickerStyle(.automatic)
        .onLongPressGesture(minimumDuration: 0.6) {
            handleSectionRefresh()
        }
        #elseif os(iOS)
        .pickerStyle(.segmented)
        .colorScheme(usesDarkBackground ? .dark : colorScheme)
        #else
        .pickerStyle(.segmented)
        #endif
        .padding(.horizontal)
    }

    private var sectionPickerForHeader: AnyView? {
        return AnyView(sectionPicker)
    }

    private var orderedSections: [BrowseSection] {
        return [.jobs, .library, .settings, .search]
    }

    private func coverURL(for item: LibraryItem) -> URL? {
        guard let apiBaseURL = appState.apiBaseURL else { return nil }
        let resolver = LibraryCoverResolver(apiBaseURL: apiBaseURL, accessToken: appState.authToken)
        return resolver.resolveCoverURL(for: item)
    }

    private var resumeUserId: String? {
        appState.resumeUserKey
    }

    private func handleSectionChange(_ newValue: BrowseSection) {
        if newValue != .settings {
            lastBrowseSection = newValue
        }
        switch newValue {
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

    private func collapseSidebar() {
        #if !os(tvOS)
        guard isSplitLayout else { return }
        withAnimation(.easeInOut(duration: 0.2)) {
            columnVisibility = .detailOnly
        }
        #endif
    }

    @ViewBuilder
    private func sectionPickerLabel(for section: BrowseSection) -> some View {
        switch section {
        case .library:
            Text(section.rawValue)
        case .jobs:
            Text(section.rawValue)
        case .search:
            Image(systemName: "magnifyingglass")
                .accessibilityLabel("Search")
        case .settings:
            Image(systemName: "gearshape")
                .accessibilityLabel("Settings")
        }
    }
}

struct SidebarSwipeDismissLayer: View {
    let onCollapse: () -> Void
    var minimumDistance: CGFloat = 24
    var requiredTranslation: CGFloat = 70
    var maxVerticalTranslation: CGFloat = 50

    var body: some View {
        #if os(tvOS)
        Color.clear
            .accessibilityHidden(true)
        #else
        Color.clear
            .contentShape(Rectangle())
            .gesture(
                DragGesture(minimumDistance: minimumDistance, coordinateSpace: .local)
                    .onEnded { value in
                        let horizontal = value.translation.width
                        let vertical = value.translation.height
                        guard abs(horizontal) > abs(vertical) else { return }
                        guard horizontal < -requiredTranslation else { return }
                        guard abs(vertical) < maxVerticalTranslation else { return }
                        onCollapse()
                    }
            )
            .accessibilityHidden(true)
        #endif
    }
}

private struct PlaybackSettingsView: View {
    let sectionPicker: AnyView?
    let backTitle: String?
    let onBack: (() -> Void)?
    let usesDarkBackground: Bool
    @AppStorage("interactive.autoScaleEnabled") private var autoScaleEnabled: Bool = true
    @EnvironmentObject private var appState: AppState
    @StateObject private var notificationManager = NotificationManager.shared
    @State private var isRequestingPermission = false
    @State private var isSendingTestNotification = false
    @State private var showTestAlert = false
    @State private var testAlertMessage = ""

    init(sectionPicker: AnyView? = nil, backTitle: String? = nil, onBack: (() -> Void)? = nil, usesDarkBackground: Bool = false) {
        self.sectionPicker = sectionPicker
        self.backTitle = backTitle
        self.onBack = onBack
        self.usesDarkBackground = usesDarkBackground
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            if let onBack, let backTitle {
                Button(action: onBack) {
                    Label("Back to \(backTitle)", systemImage: "chevron.left")
                }
                .padding(.horizontal)
            }
            if let sectionPicker {
                sectionPicker
            } else {
                Text("Settings")
                    .font(.title3)
                    .foregroundStyle(usesDarkBackground ? .white : .primary)
                    .padding(.horizontal)
            }
            List {
                Section("Playback") {
                    Toggle(isOn: $autoScaleEnabled) {
                        VStack(alignment: .leading, spacing: 4) {
                            Text("Auto-fit transcript")
                                .foregroundStyle(usesDarkBackground ? .white : .primary)
                            Text("Scale active sentences to fit the screen on rotation or font changes.")
                                .font(.caption)
                                .foregroundStyle(usesDarkBackground ? .white.opacity(0.7) : .secondary)
                        }
                    }
                }

                #if os(iOS)
                Section("Notifications") {
                    if notificationManager.isAuthorized {
                        Toggle(isOn: $notificationManager.notificationsEnabled) {
                            VStack(alignment: .leading, spacing: 4) {
                                Text("Job Notifications")
                                    .foregroundStyle(usesDarkBackground ? .white : .primary)
                                Text("Receive alerts when jobs complete or fail.")
                                    .font(.caption)
                                    .foregroundStyle(usesDarkBackground ? .white.opacity(0.7) : .secondary)
                            }
                        }

                        Button {
                            sendTestNotification()
                        } label: {
                            HStack {
                                VStack(alignment: .leading, spacing: 4) {
                                    Text("Send Test Notification")
                                        .foregroundStyle(usesDarkBackground ? .white : .primary)
                                    Text("Verify push notifications are working.")
                                        .font(.caption)
                                        .foregroundStyle(usesDarkBackground ? .white.opacity(0.7) : .secondary)
                                }
                                Spacer()
                                if isSendingTestNotification {
                                    ProgressView()
                                        .controlSize(.small)
                                } else {
                                    Image(systemName: "bell.badge")
                                        .foregroundStyle(usesDarkBackground ? .white : .accentColor)
                                }
                            }
                        }
                        .disabled(isSendingTestNotification || !notificationManager.notificationsEnabled)
                    } else {
                        Button {
                            requestNotificationPermission()
                        } label: {
                            HStack {
                                VStack(alignment: .leading, spacing: 4) {
                                    Text("Enable Notifications")
                                        .foregroundStyle(usesDarkBackground ? .white : .primary)
                                    Text("Get alerts when jobs complete or fail.")
                                        .font(.caption)
                                        .foregroundStyle(usesDarkBackground ? .white.opacity(0.7) : .secondary)
                                }
                                Spacer()
                                if isRequestingPermission {
                                    ProgressView()
                                        .controlSize(.small)
                                } else {
                                    Image(systemName: "bell")
                                        .foregroundStyle(usesDarkBackground ? .white : .accentColor)
                                }
                            }
                        }
                        .disabled(isRequestingPermission)
                    }
                }
                #endif
            }
            #if os(tvOS)
            .listStyle(.plain)
            #else
            .listStyle(.insetGrouped)
            .scrollContentBackground(usesDarkBackground ? .hidden : .automatic)
            #endif
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
        .background(usesDarkBackground ? AppTheme.lightBackground : Color.clear)
        #if os(iOS)
        .toolbarBackground(usesDarkBackground ? AppTheme.lightBackground : Color.clear, for: .navigationBar)
        .toolbarBackground(usesDarkBackground ? .visible : .automatic, for: .navigationBar)
        .toolbarColorScheme(usesDarkBackground ? .dark : nil, for: .navigationBar)
        .alert("Test Notification", isPresented: $showTestAlert) {
            Button("OK", role: .cancel) {}
        } message: {
            Text(testAlertMessage)
        }
        #endif
    }

    #if os(iOS)
    private func requestNotificationPermission() {
        isRequestingPermission = true
        Task {
            _ = await notificationManager.requestAuthorization()
            isRequestingPermission = false
        }
    }

    private func sendTestNotification() {
        guard let config = appState.configuration else {
            testAlertMessage = "Not signed in. Please log in first."
            showTestAlert = true
            return
        }

        isSendingTestNotification = true
        Task {
            do {
                let result = try await notificationManager.sendTestNotification(using: config)
                if result.sent > 0 {
                    testAlertMessage = "Test notification sent to \(result.sent) device(s)!"
                } else if let message = result.message {
                    testAlertMessage = message
                } else {
                    testAlertMessage = "No devices registered. Make sure notifications are enabled on this device."
                }
            } catch {
                testAlertMessage = "Failed to send: \(error.localizedDescription)"
            }
            isSendingTestNotification = false
            showTestAlert = true
        }
    }
    #endif
}

private struct CombinedSearchView: View {
    @ObservedObject var libraryViewModel: LibraryViewModel
    @ObservedObject var jobsViewModel: JobsViewModel
    let onRefresh: () -> Void
    let onSignOut: () -> Void
    let onSelectItem: ((LibraryItem, PlaybackStartMode) -> Void)?
    let onSelectJob: ((PipelineStatusResponse, PlaybackStartMode) -> Void)?
    let coverResolver: (LibraryItem) -> URL?
    let resumeUserId: String?
    let sectionPicker: AnyView?

    @State private var query: String = ""
    @FocusState private var isSearchFocused: Bool
    @Environment(\.colorScheme) private var colorScheme
    #if os(iOS)
    @Environment(\.horizontalSizeClass) private var horizontalSizeClass
    #endif
    @State private var iCloudStatus = PlaybackResumeStore.shared.iCloudStatus()
    @State private var resumeAvailability: [String: PlaybackResumeAvailability] = [:]

    /// Whether to use dark background (iPad in light mode, matching tvOS style)
    private var usesDarkListBackground: Bool {
        #if os(iOS)
        return horizontalSizeClass != .compact && colorScheme == .light
        #else
        return false
        #endif
    }

    private enum SearchResult: Identifiable {
        case library(LibraryItem)
        case job(PipelineStatusResponse)

        var id: String {
            switch self {
            case let .library(item):
                return "library-\(item.jobId)"
            case let .job(job):
                return "job-\(job.jobId)"
            }
        }
    }

    var body: some View {
        VStack(spacing: 12) {
            header
            List {
                if trimmedQuery.isEmpty {
                    Text("Type to search across jobs and library items.")
                        .foregroundStyle(usesDarkListBackground ? .white.opacity(0.7) : .secondary)
                } else if results.isEmpty {
                    Text("No matches found.")
                        .foregroundStyle(usesDarkListBackground ? .white.opacity(0.7) : .secondary)
                } else {
                    ForEach(results) { result in
                        switch result {
                        case let .library(item):
                            libraryRow(for: item)
                        case let .job(job):
                            jobRow(for: job)
                        }
                    }
                }
            }
            .listStyle(.plain)
            #if os(tvOS)
            .background(AppTheme.background(for: colorScheme))
            #elseif os(iOS)
            .background(usesDarkListBackground ? AppTheme.lightBackground : Color.clear)
            .scrollContentBackground(usesDarkListBackground ? .hidden : .automatic)
            .environment(\.colorScheme, usesDarkListBackground ? .dark : colorScheme)
            #endif
        }
        #if os(iOS)
        .background(usesDarkListBackground ? AppTheme.lightBackground : Color.clear)
        #endif
        .onAppear {
            isSearchFocused = true
            iCloudStatus = PlaybackResumeStore.shared.iCloudStatus()
            refreshResumeStatus()
        }
        .onReceive(NotificationCenter.default.publisher(for: PlaybackResumeStore.didChangeNotification)) { notification in
            guard let resumeUserId else { return }
            let userId = notification.userInfo?["userId"] as? String
            guard userId == resumeUserId else { return }
            iCloudStatus = PlaybackResumeStore.shared.iCloudStatus()
            refreshResumeStatus()
        }
    }

    private var trimmedQuery: String {
        query.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private var loweredQuery: String {
        trimmedQuery.lowercased()
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 12) {
            actionRow
            if let sectionPicker { sectionPicker }
            searchRow
        }
        .padding(.top, 8)
        #if os(tvOS)
        .font(tvOSHeaderFont)
        #endif
    }

    private var actionRow: some View {
        let status = iCloudStatus
        let userLabel = resumeUserId ?? "Log In"
        let statusLabel = status.isAvailable ? "Online" : "Offline"
        let iconSize: CGFloat = {
            #if os(tvOS)
            return 20
            #else
            return 18
            #endif
        }()
        return HStack(spacing: 12) {
            HStack(spacing: 6) {
                Image(systemName: "globe")
                    .font(.system(size: iconSize, weight: .semibold))
                    .foregroundStyle(usesDarkListBackground ? .cyan : .blue)
                Text("Language Tools")
                    .lineLimit(1)
                    .foregroundStyle(usesDarkListBackground ? .white : .primary)
                AppVersionBadge()
            }
            HStack(spacing: 6) {
                Image(systemName: status.isAvailable ? "icloud" : "icloud.slash")
                    .font(.system(size: iconSize, weight: .semibold))
                    .foregroundStyle(status.isAvailable ? (usesDarkListBackground ? .cyan : .blue) : (usesDarkListBackground ? .white.opacity(0.6) : .secondary))
            }
            .accessibilityLabel(statusLabel)
            Button(action: onRefresh) {
                Image(systemName: "arrow.clockwise")
            }
            .disabled(libraryViewModel.isLoading || jobsViewModel.isLoading)
            .accessibilityLabel("Refresh")
            .tint(usesDarkListBackground ? .white : nil)
            Menu {
                Button("Log Out", action: onSignOut)
            } label: {
                HStack(spacing: 6) {
                    Image(systemName: "person.crop.circle")
                    Text(userLabel)
                        .lineLimit(1)
                        .truncationMode(.middle)
                }
            }
            .tint(usesDarkListBackground ? .white : nil)
            Spacer()
        }
        .padding(.horizontal)
    }

    #if os(tvOS)
    private var tvOSHeaderFont: Font {
        let size = UIFont.preferredFont(forTextStyle: .body).pointSize * 0.5
        return .system(size: size)
    }
    #endif

    private var searchRow: some View {
        HStack(spacing: 8) {
            TextField("Search jobs and library", text: $query)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
                .focused($isSearchFocused)
                .submitLabel(.search)
                .foregroundStyle(usesDarkListBackground ? .white : .primary)
            Button {
                isSearchFocused = true
            } label: {
                Image(systemName: "magnifyingglass")
            }
            .tint(usesDarkListBackground ? .white : nil)
        }
        .padding(.horizontal)
    }

    private var results: [SearchResult] {
        guard !loweredQuery.isEmpty else { return [] }
        let jobMatches = jobsViewModel.jobs.filter { matches(job: $0, query: loweredQuery) }
        let libraryMatches = libraryViewModel.items.filter { matches(item: $0, query: loweredQuery) }
        let merged = jobMatches.map { SearchResult.job($0) }
            + libraryMatches.map { SearchResult.library($0) }
        return merged.sorted { lhs, rhs in
            let leftDate = createdAt(for: lhs) ?? .distantPast
            let rightDate = createdAt(for: rhs) ?? .distantPast
            return leftDate > rightDate
        }
    }

    @ViewBuilder
    private func jobRow(for job: PipelineStatusResponse) -> some View {
        // Always use programmatic navigation to support context menu actions
        #if os(tvOS)
        Button {
            onSelectJob?(job, .resume)
        } label: {
            JobRowView(job: job, resumeStatus: resumeStatus(for: job))
        }
        .buttonStyle(.plain)
        .contextMenu {
            playbackContextMenu(for: job)
        }
        #else
        JobRowView(job: job, resumeStatus: resumeStatus(for: job), usesDarkBackground: usesDarkListBackground)
            .contentShape(Rectangle())
            .listRowBackground(usesDarkListBackground ? Color.clear : nil)
            .onTapGesture {
                onSelectJob?(job, .resume)
            }
            .contextMenu {
                playbackContextMenu(for: job)
            }
        #endif
    }

    @ViewBuilder
    private func libraryRow(for item: LibraryItem) -> some View {
        // Always use programmatic navigation to support context menu actions
        #if os(tvOS)
        Button {
            onSelectItem?(item, .resume)
        } label: {
            LibraryRowView(
                item: item,
                coverURL: coverResolver(item),
                resumeStatus: resumeStatus(for: item)
            )
        }
        .buttonStyle(.plain)
        .contextMenu {
            playbackContextMenu(for: item)
        }
        #else
        LibraryRowView(
            item: item,
            coverURL: coverResolver(item),
            resumeStatus: resumeStatus(for: item),
            usesDarkBackground: usesDarkListBackground
        )
        .contentShape(Rectangle())
        .listRowBackground(usesDarkListBackground ? Color.clear : nil)
        .onTapGesture {
            onSelectItem?(item, .resume)
        }
        .contextMenu {
            playbackContextMenu(for: item)
        }
        #endif
    }

    @ViewBuilder
    private func playbackContextMenu(for item: LibraryItem) -> some View {
        let availability = resumeAvailability[item.jobId]
        let hasResume = availability?.hasCloud == true || availability?.hasLocal == true

        Button {
            onSelectItem?(item, .resume)
        } label: {
            if hasResume {
                Label(resumeMenuLabel(for: item), systemImage: "play.fill")
            } else {
                Label("Play", systemImage: "play.fill")
            }
        }

        if hasResume {
            Button {
                onSelectItem?(item, .startOver)
            } label: {
                Label("Start from Beginning", systemImage: "arrow.counterclockwise")
            }
        }
    }

    @ViewBuilder
    private func playbackContextMenu(for job: PipelineStatusResponse) -> some View {
        let availability = resumeAvailability[job.jobId]
        let hasResume = availability?.hasCloud == true || availability?.hasLocal == true

        Button {
            onSelectJob?(job, .resume)
        } label: {
            if hasResume {
                Label(resumeMenuLabel(for: job), systemImage: "play.fill")
            } else {
                Label("Play", systemImage: "play.fill")
            }
        }

        if hasResume {
            Button {
                onSelectJob?(job, .startOver)
            } label: {
                Label("Start from Beginning", systemImage: "arrow.counterclockwise")
            }
        }
    }

    private func resumeMenuLabel(for item: LibraryItem) -> String {
        guard let availability = resumeAvailability[item.jobId] else {
            return "Resume"
        }
        let entry = availability.cloudEntry ?? availability.localEntry
        guard let entry else { return "Resume" }
        switch entry.kind {
        case .sentence:
            if let sentence = entry.sentenceNumber, sentence > 0 {
                return "Resume from Sentence \(sentence)"
            }
        case .time:
            if let time = entry.playbackTime, time > 0 {
                return "Resume from \(formatPlaybackTime(time))"
            }
        }
        return "Resume"
    }

    private func resumeMenuLabel(for job: PipelineStatusResponse) -> String {
        guard let availability = resumeAvailability[job.jobId] else {
            return "Resume"
        }
        let entry = availability.cloudEntry ?? availability.localEntry
        guard let entry else { return "Resume" }
        switch entry.kind {
        case .sentence:
            if let sentence = entry.sentenceNumber, sentence > 0 {
                return "Resume from Sentence \(sentence)"
            }
        case .time:
            if let time = entry.playbackTime, time > 0 {
                return "Resume from \(formatPlaybackTime(time))"
            }
        }
        return "Resume"
    }

    private func matches(job: PipelineStatusResponse, query: String) -> Bool {
        jobSearchFields(job).contains { $0.contains(query) }
    }

    private func matches(item: LibraryItem, query: String) -> Bool {
        librarySearchFields(item).contains { $0.contains(query) }
    }

    private func jobSearchFields(_ job: PipelineStatusResponse) -> [String] {
        var fields: [String] = [job.jobId.lowercased(), job.jobType.lowercased()]
        if let label = job.jobLabel?.nonEmptyValue {
            fields.append(label.lowercased())
        }
        if let title = jobTitle(from: job)?.lowercased() {
            fields.append(title)
        }
        return fields
    }

    private func librarySearchFields(_ item: LibraryItem) -> [String] {
        var fields: [String] = [
            item.jobId.lowercased(),
            item.bookTitle.lowercased(),
            item.author.lowercased(),
            item.itemType.lowercased()
        ]
        if let genre = item.genre?.lowercased() {
            fields.append(genre)
        }
        return fields
    }

    private func jobTitle(from job: PipelineStatusResponse) -> String? {
        if let label = job.jobLabel?.nonEmptyValue {
            return label
        }
        guard let resultObject = job.result?.objectValue else { return nil }
        if let title = resultObject["title"]?.stringValue?.nonEmptyValue {
            return title
        }
        if let book = resultObject["book_metadata"]?.objectValue,
           let title = book["title"]?.stringValue?.nonEmptyValue {
            return title
        }
        return nil
    }

    private func createdAt(for result: SearchResult) -> Date? {
        switch result {
        case let .library(item):
            return parseDate(item.createdAt)
        case let .job(job):
            return parseDate(job.createdAt)
        }
    }

    private func parseDate(_ value: String) -> Date? {
        Self.dateFormatterWithFractional.date(from: value) ?? Self.dateFormatter.date(from: value)
    }

    private static let dateFormatter: ISO8601DateFormatter = {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime]
        return formatter
    }()

    private static let dateFormatterWithFractional: ISO8601DateFormatter = {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return formatter
    }()

    private func resumeStatus(for job: PipelineStatusResponse) -> LibraryRowView.ResumeStatus {
        guard let availability = resumeAvailability[job.jobId] else { return .none() }
        let entry = availability.hasCloud ? availability.cloudEntry : nil
        guard let entry else { return .none() }
        let label = resumeLabel(prefix: "C", entry: entry)
        return .cloud(label: label)
    }

    private func resumeStatus(for item: LibraryItem) -> LibraryRowView.ResumeStatus {
        guard let availability = resumeAvailability[item.jobId] else { return .none() }
        let entry = availability.hasCloud ? availability.cloudEntry : nil
        guard let entry else { return .none() }
        let label = resumeLabel(prefix: "C", entry: entry)
        return .cloud(label: label)
    }

    private func refreshResumeStatus() {
        guard let resumeUserId else {
            resumeAvailability = [:]
            return
        }
        resumeAvailability = PlaybackResumeStore.shared.availabilitySnapshot(for: resumeUserId)
    }

    private func resumeLabel(prefix: String, entry: PlaybackResumeEntry?) -> String {
        guard let entry else { return "\(prefix)" }
        switch entry.kind {
        case .sentence:
            if let sentence = entry.sentenceNumber, sentence > 0 {
                return "\(prefix):\(sentence)"
            }
        case .time:
            if let time = entry.playbackTime, time > 0 {
                return "\(prefix):\(formatPlaybackTime(time))"
            }
        }
        return "\(prefix)"
    }

    private func formatPlaybackTime(_ time: Double) -> String {
        let formatter = DateComponentsFormatter()
        formatter.allowedUnits = time >= 3600 ? [.hour, .minute, .second] : [.minute, .second]
        formatter.zeroFormattingBehavior = .pad
        return formatter.string(from: time) ?? "0:00"
    }
}
