import SwiftUI

struct LibraryShellView: View {
    @EnvironmentObject var appState: AppState
    @StateObject private var viewModel = LibraryViewModel()
    @StateObject private var jobsViewModel = JobsViewModel()
    @State private var selectedItem: LibraryItem?
    @State private var selectedJob: PipelineStatusResponse?
    @State private var libraryAutoPlay = false
    @State private var jobsAutoPlay = false
    @State private var activeSection: BrowseSection = .jobs
    @State private var lastBrowseSection: BrowseSection = .jobs
    #if !os(tvOS)
    @State private var columnVisibility: NavigationSplitViewVisibility = .all
    #endif
    @Environment(\.horizontalSizeClass) private var horizontalSizeClass

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
                NavigationSplitView(columnVisibility: $columnVisibility) {
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
        case .search:
            if let selectedItem {
                LibraryPlaybackView(item: selectedItem, autoPlayOnLoad: $libraryAutoPlay)
            } else if let selectedJob {
                JobPlaybackView(job: selectedJob, autoPlayOnLoad: $jobsAutoPlay)
            } else {
                VStack(spacing: 12) {
                    Text("Search jobs and library")
                        .font(.title3)
                    Text("Use the search field to find items across your library and jobs.")
                        .foregroundStyle(.secondary)
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            }
        case .settings:
            PlaybackSettingsView()
        }
    }

    @ViewBuilder
    private func browseList(useNavigationLinks: Bool) -> some View {
        VStack(spacing: 10) {
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
                    sectionPicker: sectionPickerForHeader,
                    onCollapseSidebar: isSplitLayout ? { collapseSidebar() } : nil,
                    onSearchRequested: { activeSection = .search }
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
                    resumeUserId: resumeUserId,
                    onCollapseSidebar: isSplitLayout ? { collapseSidebar() } : nil,
                    onSearchRequested: { activeSection = .search }
                )
            case .search:
                CombinedSearchView(
                    libraryViewModel: viewModel,
                    jobsViewModel: jobsViewModel,
                    useNavigationLinks: useNavigationLinks,
                    onRefresh: {
                        Task {
                            await viewModel.load(using: appState)
                            await jobsViewModel.load(using: appState)
                        }
                    },
                    onSignOut: {
                        appState.signOut()
                    },
                    onSelectItem: { item in
                        selectedItem = item
                        libraryAutoPlay = true
                    },
                    onSelectJob: { job in
                        selectedJob = job
                        jobsAutoPlay = true
                    },
                    coverResolver: coverURL(for:),
                    resumeUserId: resumeUserId,
                    sectionPicker: sectionPickerForHeader
                )
            case .settings:
                if isSplitLayout {
                    VStack(spacing: 12) {
                        Text("Settings")
                            .font(.title3)
                        Text("Adjust playback options in the detail panel.")
                            .foregroundStyle(.secondary)
                    }
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                } else {
                    PlaybackSettingsView(
                        sectionPicker: sectionPickerForHeader,
                        backTitle: isCompactLayout ? lastBrowseSection.rawValue : nil,
                        onBack: isCompactLayout ? { activeSection = lastBrowseSection } : nil
                    )
                }
            }
        }
        #if !os(tvOS)
        .navigationTitle(isCompactLayout ? "" : activeSection.rawValue)
        .navigationBarTitleDisplayMode(isCompactLayout ? .inline : .automatic)
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
    @AppStorage("interactive.autoScaleEnabled") private var autoScaleEnabled: Bool = true

    init(sectionPicker: AnyView? = nil, backTitle: String? = nil, onBack: (() -> Void)? = nil) {
        self.sectionPicker = sectionPicker
        self.backTitle = backTitle
        self.onBack = onBack
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
                    .padding(.horizontal)
            }
            List {
                Section("Playback") {
                    Toggle(isOn: $autoScaleEnabled) {
                        VStack(alignment: .leading, spacing: 4) {
                            Text("Auto-fit transcript")
                            Text("Scale active sentences to fit the screen on rotation or font changes.")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    }
                }
            }
            #if os(tvOS)
            .listStyle(.plain)
            #else
            .listStyle(.insetGrouped)
            #endif
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
    }
}

private struct CombinedSearchView: View {
    @ObservedObject var libraryViewModel: LibraryViewModel
    @ObservedObject var jobsViewModel: JobsViewModel
    let useNavigationLinks: Bool
    let onRefresh: () -> Void
    let onSignOut: () -> Void
    let onSelectItem: ((LibraryItem) -> Void)?
    let onSelectJob: ((PipelineStatusResponse) -> Void)?
    let coverResolver: (LibraryItem) -> URL?
    let resumeUserId: String?
    let sectionPicker: AnyView?

    @State private var query: String = ""
    @FocusState private var isSearchFocused: Bool
    @Environment(\.colorScheme) private var colorScheme
    @State private var iCloudStatus = PlaybackResumeStore.shared.iCloudStatus()

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
                        .foregroundStyle(.secondary)
                } else if results.isEmpty {
                    Text("No matches found.")
                        .foregroundStyle(.secondary)
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
            #endif
        }
        .onAppear {
            isSearchFocused = true
            iCloudStatus = PlaybackResumeStore.shared.iCloudStatus()
        }
        .onReceive(NotificationCenter.default.publisher(for: PlaybackResumeStore.didChangeNotification)) { _ in
            iCloudStatus = PlaybackResumeStore.shared.iCloudStatus()
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
                    .foregroundStyle(Color.blue)
                Text("Language Tools")
                    .lineLimit(1)
                AppVersionBadge()
            }
            HStack(spacing: 6) {
                Image(systemName: status.isAvailable ? "icloud" : "icloud.slash")
                    .font(.system(size: iconSize, weight: .semibold))
                    .foregroundStyle(status.isAvailable ? Color.blue : Color.secondary)
            }
            .accessibilityLabel(statusLabel)
            Button(action: onRefresh) {
                Image(systemName: "arrow.clockwise")
            }
            .disabled(libraryViewModel.isLoading || jobsViewModel.isLoading)
            .accessibilityLabel("Refresh")
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
            Button {
                isSearchFocused = true
            } label: {
                Image(systemName: "magnifyingglass")
            }
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
        if useNavigationLinks {
            NavigationLink(value: job) {
                JobRowView(job: job, resumeStatus: resumeStatus(for: job))
            }
        } else {
            JobRowView(job: job, resumeStatus: resumeStatus(for: job))
                .contentShape(Rectangle())
                .onTapGesture {
                    onSelectJob?(job)
                }
        }
    }

    @ViewBuilder
    private func libraryRow(for item: LibraryItem) -> some View {
        if useNavigationLinks {
            NavigationLink(value: item) {
                LibraryRowView(
                    item: item,
                    coverURL: coverResolver(item),
                    resumeStatus: resumeStatus(for: item)
                )
            }
        } else {
            LibraryRowView(
                item: item,
                coverURL: coverResolver(item),
                resumeStatus: resumeStatus(for: item)
            )
            .contentShape(Rectangle())
            .onTapGesture {
                onSelectItem?(item)
            }
        }
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
        guard let resumeUserId else { return .none() }
        let availability = PlaybackResumeStore.shared.availability(for: job.jobId, userId: resumeUserId)
        let entry = availability.hasCloud ? availability.cloudEntry : nil
        guard let entry else { return .none() }
        let label = resumeLabel(prefix: "C", entry: entry)
        return .cloud(label: label)
    }

    private func resumeStatus(for item: LibraryItem) -> LibraryRowView.ResumeStatus {
        guard let resumeUserId else { return .none() }
        let availability = PlaybackResumeStore.shared.availability(for: item.jobId, userId: resumeUserId)
        let entry = availability.hasCloud ? availability.cloudEntry : nil
        guard let entry else { return .none() }
        let label = resumeLabel(prefix: "C", entry: entry)
        return .cloud(label: label)
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
