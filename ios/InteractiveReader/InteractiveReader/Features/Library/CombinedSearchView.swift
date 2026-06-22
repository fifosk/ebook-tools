import SwiftUI

struct CombinedSearchView: View {
    @Environment(\.colorScheme) private var colorScheme
    @ObservedObject var libraryViewModel: LibraryViewModel
    @ObservedObject var jobsViewModel: JobsViewModel

    let onRefresh: () -> Void
    let onSignOut: () -> Void
    let onSelectItem: ((LibraryItem, PlaybackStartMode) -> Void)?
    let onSelectJob: ((PipelineStatusResponse, PlaybackStartMode) -> Void)?
    let coverResolver: (LibraryItem) -> URL?
    let resumeUserId: String?
    let sectionPicker: BrowseSectionPicker?
    let usesDarkBackground: Bool

    @State private var query: String = ""
    @State private var iCloudStatus = PlaybackResumeStore.shared.iCloudStatus()
    @State private var resumeAvailability: [String: PlaybackResumeAvailability] = [:]
    @FocusState private var isSearchFocused: Bool

    /// Whether to use dark background, matching the parent shell's split-view styling.
    private var usesDarkListBackground: Bool {
        usesDarkBackground
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
                if !trimmedQuery.isEmpty {
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
            .platformListBackground(usesDark: usesDarkListBackground, colorScheme: colorScheme)
            .overlay(alignment: .center) {
                searchOverlay
            }
        }
        #if os(iOS)
        .background(usesDarkListBackground ? AppTheme.lightBackground : Color.clear)
        #endif
        .onAppear(perform: handleSearchAppear)
        .onReceive(
            NotificationCenter.default.publisher(for: PlaybackResumeStore.didChangeNotification),
            perform: handleResumeStoreChange
        )
    }

    private var trimmedQuery: String {
        query.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private var loweredQuery: String {
        trimmedQuery.lowercased()
    }

    @ViewBuilder
    private var searchOverlay: some View {
        if trimmedQuery.isEmpty {
            SearchEmptyStateView(
                title: "Search jobs and library",
                message: "Type to search across jobs and library items.",
                usesDarkListBackground: usesDarkListBackground
            )
            .accessibilityIdentifier("combinedSearchPromptView")
        } else if results.isEmpty {
            SearchEmptyStateView(
                title: "No matches found",
                message: "Try a different search term.",
                usesDarkListBackground: usesDarkListBackground
            )
            .accessibilityIdentifier("combinedSearchEmptyView")
        }
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 12) {
            actionRow
            if let sectionPicker { sectionPicker }
            searchRow
        }
        .padding(.top, 8)
        #if os(tvOS)
        .font(PlatformTypography.sectionHeaderFont)
        #endif
    }

    private var actionRow: some View {
        BrowseActionRow(
            iCloudStatus: iCloudStatus,
            resumeUserId: resumeUserId,
            isLoading: libraryViewModel.isLoading || jobsViewModel.isLoading,
            usesDarkListBackground: usesDarkListBackground,
            onRefresh: onRefresh,
            onSignOut: onSignOut
        )
    }

    private var searchRow: some View {
        HStack(spacing: 8) {
            TextField("Search jobs and library", text: $query)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
                .focused($isSearchFocused)
                .submitLabel(.search)
                .foregroundStyle(usesDarkListBackground ? .white : .primary)
                .accessibilityIdentifier("combinedSearchField")
            Button(action: handleSearchFieldAction) {
                Image(systemName: trimmedQuery.isEmpty ? "magnifyingglass" : "xmark.circle.fill")
            }
            .tint(usesDarkListBackground ? .white : nil)
            .accessibilityIdentifier("combinedSearchFieldActionButton")
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
            selectJob(job, mode: .resume)
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
                selectJob(job, mode: .resume)
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
            selectItem(item, mode: .resume)
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
            selectItem(item, mode: .resume)
        }
        .contextMenu {
            playbackContextMenu(for: item)
        }
        #endif
    }

    @ViewBuilder
    private func playbackContextMenu(for item: LibraryItem) -> some View {
        let hasResume = BrowseResumeStatusFormatter.hasResume(
            for: item.jobId,
            availabilityByJobID: resumeAvailability
        )

        Button {
            selectItem(item, mode: .resume)
        } label: {
            if hasResume {
                Label(resumeMenuLabel(for: item), systemImage: "play.fill")
            } else {
                Label("Play", systemImage: "play.fill")
            }
        }

        if hasResume {
            Button {
                selectItem(item, mode: .startOver)
            } label: {
                Label("Start from Beginning", systemImage: "arrow.counterclockwise")
            }
        }
    }

    @ViewBuilder
    private func playbackContextMenu(for job: PipelineStatusResponse) -> some View {
        let hasResume = BrowseResumeStatusFormatter.hasResume(
            for: job.jobId,
            availabilityByJobID: resumeAvailability
        )

        Button {
            selectJob(job, mode: .resume)
        } label: {
            if hasResume {
                Label(resumeMenuLabel(for: job), systemImage: "play.fill")
            } else {
                Label("Play", systemImage: "play.fill")
            }
        }

        if hasResume {
            Button {
                selectJob(job, mode: .startOver)
            } label: {
                Label("Start from Beginning", systemImage: "arrow.counterclockwise")
            }
        }
    }

    private func handleSearchAppear() {
        isSearchFocused = true
        refreshResumeEvidence()
    }

    private func handleResumeStoreChange(_ notification: Notification) {
        guard BrowseResumeNotificationFilter.matches(notification, resumeUserId: resumeUserId) else { return }
        refreshResumeEvidence()
    }

    private func refreshResumeEvidence() {
        applyResumeSnapshot(BrowseResumeSnapshotProvider.snapshot(for: resumeUserId))
    }

    private func handleSearchFieldAction() {
        if !trimmedQuery.isEmpty {
            query = ""
        }
        isSearchFocused = true
    }

    private func selectItem(_ item: LibraryItem, mode: PlaybackStartMode) {
        onSelectItem?(item, mode)
    }

    private func selectJob(_ job: PipelineStatusResponse, mode: PlaybackStartMode) {
        onSelectJob?(job, mode)
    }

    private func resumeMenuLabel(for item: LibraryItem) -> String {
        BrowseResumeStatusFormatter.menuLabel(
            for: item.jobId,
            availabilityByJobID: resumeAvailability
        )
    }

    private func resumeMenuLabel(for job: PipelineStatusResponse) -> String {
        BrowseResumeStatusFormatter.menuLabel(
            for: job.jobId,
            availabilityByJobID: resumeAvailability
        )
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
        if let book = (resultObject["media_metadata"] ?? resultObject["book_metadata"])?.objectValue,
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
        BrowseResumeStatusFormatter.rowStatus(
            for: job.jobId,
            availabilityByJobID: resumeAvailability
        )
    }

    private func resumeStatus(for item: LibraryItem) -> LibraryRowView.ResumeStatus {
        BrowseResumeStatusFormatter.rowStatus(
            for: item.jobId,
            availabilityByJobID: resumeAvailability
        )
    }

    private func refreshResumeStatus() {
        applyResumeSnapshot(BrowseResumeSnapshotProvider.snapshot(for: resumeUserId))
    }

    private func applyResumeSnapshot(_ snapshot: BrowseResumeSnapshot) {
        resumeAvailability = snapshot.availabilityByJobID
        iCloudStatus = snapshot.iCloudStatus
    }

}

private struct SearchEmptyStateView: View {
    let title: String
    let message: String
    let usesDarkListBackground: Bool

    private var primaryColor: Color {
        usesDarkListBackground ? .white : .primary
    }

    private var secondaryColor: Color {
        usesDarkListBackground ? Color.white.opacity(0.74) : .secondary
    }

    var body: some View {
        VStack(spacing: 12) {
            Image(systemName: "magnifyingglass")
                .font(.system(size: 42, weight: .medium))
                .foregroundStyle(secondaryColor)
                .accessibilityHidden(true)

            Text(title)
                .font(.title3.weight(.semibold))
                .foregroundStyle(primaryColor)
                .multilineTextAlignment(.center)
                .fixedSize(horizontal: false, vertical: true)

            Text(message)
                .font(.subheadline)
                .foregroundStyle(secondaryColor)
                .multilineTextAlignment(.center)
                .fixedSize(horizontal: false, vertical: true)
        }
        .padding(.horizontal, 24)
        .frame(maxWidth: 360)
    }
}
