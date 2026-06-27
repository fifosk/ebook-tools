import Foundation
import SwiftUI

struct JobsView: View {
    @EnvironmentObject var appState: AppState
    @EnvironmentObject var offlineStore: OfflineMediaStore
    @Environment(\.openURL) private var openURL
    @ObservedObject var viewModel: JobsViewModel
    let onRefresh: () -> Void
    let onSelect: ((PipelineStatusResponse, PlaybackStartMode) -> Void)?
    let sectionPicker: BrowseSectionPicker?
    let resumeUserId: String?
    let onCollapseSidebar: (() -> Void)?
    let onSearchRequested: (() -> Void)?
    var usesDarkBackground: Bool = false

    @FocusState private var isSearchFocused: Bool
    @State private var resumeAvailability: [String: PlaybackResumeAvailability] = [:]
    @State private var restartPendingJob: PipelineStatusResponse?
    #if os(iOS)
    @State private var rowFrames: [CGRect] = []
    private let listCoordinateSpace = "jobsList"
    #endif
    @Environment(\.colorScheme) private var colorScheme
    #if os(iOS)
    @Environment(\.horizontalSizeClass) private var horizontalSizeClass
    #endif
    #if os(tvOS)
    @State private var isSearchPresented = false
    #endif

    var body: some View {
        VStack(spacing: 12) {
            header

            if let error = viewModel.errorMessage {
                errorRow(message: error)
                    .padding(.horizontal)
            }

            List {
                jobRows(viewModel.filteredJobs)
            }
            .listStyle(.plain)
            .platformListBackground(usesDark: usesDarkListBackground, colorScheme: colorScheme)
            #if os(iOS)
            .browseListCollapseInteraction(
                rowFrames: $rowFrames,
                coordinateSpaceName: listCoordinateSpace,
                onCollapse: onCollapseSidebar
            )
            #endif
            .overlay(alignment: .center) {
                listOverlay
            }
            #if os(iOS)
            .refreshable {
                handleRefresh()
            }
            #endif
        }
        #if os(iOS)
        .background(usesDarkListBackground ? AppTheme.lightBackground : Color.clear)
        #endif
        .onAppear(perform: handleJobsAppear)
        .onChange(of: resumeUserId, initial: false, handleResumeUserChange)
        .onReceive(
            NotificationCenter.default.publisher(for: PlaybackResumeStore.didChangeNotification),
            perform: handleResumeStoreChange
        )
        .onDisappear(perform: handleJobsDisappear)
        .confirmationDialog(
            "Restart job?",
            isPresented: Binding(
                get: { restartPendingJob != nil },
                set: { isPresented in
                    if !isPresented {
                        restartPendingJob = nil
                    }
                }
            ),
            titleVisibility: .visible
        ) {
            if let restartPendingJob {
                Button("Restart Job", role: .destructive) {
                    let job = restartPendingJob
                    self.restartPendingJob = nil
                    handleRestartJobRequest(job)
                }
            }
            Button("Cancel", role: .cancel) {
                restartPendingJob = nil
            }
        } message: {
            Text("Generated outputs will be overwritten using the same settings.")
        }
    }

    @ViewBuilder
    private func jobRows(_ jobs: [PipelineStatusResponse]) -> some View {
        ForEach(jobs) { job in
            // Always use programmatic navigation to support context menu actions
            #if os(tvOS)
            Button(action: { handleJobRowTap(job) }) {
                JobRowView(job: job, resumeStatus: resumeStatus(for: job))
                    .accessibilityIdentifier("jobRowButton")
            }
            .accessibilityIdentifier("jobRowButton")
            .buttonStyle(.plain)
            .listRowBackground(Color.clear)
            .contextMenu {
                playbackContextMenu(for: job)
                offlineContextMenu(for: job)
                offlineExportAction(for: job)
                moveToLibraryAction(for: job)
                restartJobAction(for: job)
                deleteJobAction(for: job)
            }
            #else
            JobRowView(job: job, resumeStatus: resumeStatus(for: job), usesDarkBackground: usesDarkListBackground)
                .background(BrowseListRowFrameCapture(coordinateSpaceName: listCoordinateSpace))
                .contentShape(Rectangle())
                .listRowBackground(usesDarkListBackground ? Color.clear : nil)
                .onTapGesture {
                    handleJobRowTap(job)
                }
                .contextMenu {
                    playbackContextMenu(for: job)
                    offlineExportAction(for: job)
                    moveToLibraryAction(for: job)
                    restartJobAction(for: job)
                    deleteJobAction(for: job)
                }
                .swipeActions(edge: .leading, allowsFullSwipe: false) {
                    moveToLibraryAction(for: job)
                }
                .swipeActions(edge: .trailing, allowsFullSwipe: true) {
                    deleteJobAction(for: job)
                }
            #endif
        }
    }

    private func errorRow(message: String) -> some View {
        Label(message, systemImage: "exclamationmark.triangle.fill")
            .foregroundStyle(.red)
            .font(.callout)
    }

    /// Whether to use dark background for list (iPad in light mode, aligned with tvOS style)
    private var usesDarkListBackground: Bool {
        usesDarkBackground
    }

    private var listOverlay: some View {
        Group {
            if viewModel.isLoading {
                ProgressView("Loading jobs…")
                    .padding()
                    .background(.thinMaterial, in: RoundedRectangle(cornerRadius: 12))
                    .accessibilityIdentifier("jobsLoadingView")
            } else if viewModel.isCreatingExport {
                ProgressView("Creating offline export…")
                    .padding()
                    .background(.thinMaterial, in: RoundedRectangle(cornerRadius: 12))
                    .accessibilityIdentifier("jobsOfflineExportLoadingView")
            } else if viewModel.filteredJobs.isEmpty {
                ContentUnavailableView {
                    Label("No jobs found", systemImage: "tray")
                } description: {
                    Text(viewModel.query.isEmpty ? "Finished and running jobs will appear here." : "Try a different search term.")
                }
                .foregroundStyle(usesDarkListBackground ? .white : .primary)
                .accessibilityIdentifier("jobsEmptyView")
            }
        }
    }

    @ViewBuilder
    private func moveToLibraryAction(for job: PipelineStatusResponse) -> some View {
        Button(action: { handleMoveToLibraryRequest(job) }) {
            Label("Move to Library", systemImage: "books.vertical")
        }
        .tint(.blue)
        .disabled(!job.isFinishedForDisplay)
    }

    private func deleteJobAction(for job: PipelineStatusResponse) -> some View {
        Button(role: .destructive, action: { handleDeleteJobRequest(job) }) {
            Label("Delete", systemImage: "trash")
        }
    }

    private func restartJobAction(for job: PipelineStatusResponse) -> some View {
        Button(action: { restartPendingJob = job }) {
            Label("Restart Job", systemImage: "arrow.clockwise")
        }
        .disabled(!canRestartJob(job) || viewModel.restartingJobId != nil)
    }

    private func canRestartJob(_ job: PipelineStatusResponse) -> Bool {
        let type = job.jobType.lowercased()
        let supportedType = type == "pipeline" || type == "book"
        return supportedType && (job.status == .failed || job.status == .cancelled)
    }

    private func offlineExportAction(for job: PipelineStatusResponse) -> some View {
        Button(action: { handleOfflineExportRequest(job) }) {
            Label("Export Offline Player", systemImage: "square.and.arrow.down")
        }
        .disabled(!canExportOfflinePlayer(job) || viewModel.isCreatingExport(for: job) || appState.configuration == nil)
    }

    private func canExportOfflinePlayer(_ job: PipelineStatusResponse) -> Bool {
        job.isFinishedForDisplay && job.mediaCompleted == true
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 12) {
            #if os(tvOS)
            if isSearchPresented {
                searchRow
            }
            #else
            if onSearchRequested == nil {
                searchRow
            }
            #endif
            if let sectionPicker {
                sectionPicker
            }
            JobsFilterPicker(
                activeFilter: $viewModel.activeFilter,
                usesDarkListBackground: usesDarkListBackground,
                colorScheme: colorScheme,
                onRefresh: handleRefresh
            )
        }
        .padding(.top, 8)
        #if os(tvOS)
        .font(PlatformTypography.sectionHeaderFont)
        #endif
    }

    private func selectJob(_ job: PipelineStatusResponse, mode: PlaybackStartMode) {
        onSelect?(job, mode)
    }

    private func handleResumeJobSelection(_ job: PipelineStatusResponse) {
        selectJob(job, mode: .resume)
    }

    private func handleJobRowTap(_ job: PipelineStatusResponse) {
        handleResumeJobSelection(job)
    }

    private func handleStartOverJobSelection(_ job: PipelineStatusResponse) {
        selectJob(job, mode: .startOver)
    }

    private func handleJobsAppear() {
        refreshResumeStatus()
        viewModel.startAutoRefresh(using: appState)
    }

    private func handleJobsDisappear() {
        viewModel.stopAutoRefresh()
    }

    private func handleResumeUserChange() {
        refreshResumeStatus()
    }

    private func handleResumeStoreChange(_ notification: Notification) {
        guard BrowseResumeNotificationFilter.matches(notification, resumeUserId: resumeUserId),
              let resumeUserId else { return }
        Task { @MainActor in
            refreshResumeEvidence(for: resumeUserId)
        }
    }

    private func handleDeleteJobRequest(_ job: PipelineStatusResponse) {
        Task { await handleDelete(job) }
    }

    private func handleMoveToLibraryRequest(_ job: PipelineStatusResponse) {
        Task { await handleMoveToLibrary(job) }
    }

    private func handleRestartJobRequest(_ job: PipelineStatusResponse) {
        Task { await handleRestartJob(job) }
    }

    private func handleOfflineExportRequest(_ job: PipelineStatusResponse) {
        Task {
            let url = await viewModel.createOfflineExport(for: job, using: appState)
            await MainActor.run {
                if let url {
                    openURL(url)
                }
            }
        }
    }

    private func handleMoveToLibrary(_ job: PipelineStatusResponse) async {
        _ = await viewModel.moveToLibrary(jobId: job.jobId, using: appState)
    }

    private func handleRestartJob(_ job: PipelineStatusResponse) async {
        let didRestart = await viewModel.restart(jobId: job.jobId, using: appState)
        guard didRestart else { return }
        refreshResumeStatus()
    }

    private var searchRow: some View {
        HStack(spacing: 8) {
            TextField("Search jobs", text: $viewModel.query)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
                .focused($isSearchFocused)
                .submitLabel(.search)
                .foregroundStyle(usesDarkListBackground ? .white : .primary)
                .onSubmit(handleSearchSubmit)
            Button(action: handleRefresh) {
                Image(systemName: "magnifyingglass")
            }
            .disabled(viewModel.isLoading)
            .tint(usesDarkListBackground ? .white : nil)
            #if os(tvOS)
            Button("Cancel", action: handleSearchCancel)
            #endif
        }
        .padding(.horizontal)
        #if os(tvOS)
        .onAppear(perform: focusSearchFieldSoon)
        .onExitCommand {
            dismissSearch()
        }
        #endif
    }

    private func handleRefresh() {
        refreshResumeStatus()
        onRefresh()
    }

    private func handleSearchSubmit() {
        handleRefresh()
        #if os(tvOS)
        dismissSearch()
        #endif
    }

    #if os(tvOS)
    private func presentSearch() {
        isSearchPresented = true
        focusSearchFieldSoon()
    }

    private func dismissSearch() {
        isSearchFocused = false
        isSearchPresented = false
    }

    private func handleSearchCancel() {
        dismissSearch()
    }

    private func focusSearchFieldSoon() {
        DispatchQueue.main.async {
            isSearchFocused = true
        }
    }
    #endif

    private func refreshResumeEvidence(for userId: String) {
        applyResumeSnapshot(BrowseResumeSnapshotProvider.snapshot(for: userId))
    }

    private func refreshResumeStatus() {
        applyResumeSnapshot(BrowseResumeSnapshotProvider.snapshot(for: resumeUserId))
        Task {
            let snapshot = await BrowseResumeSnapshotProvider.refreshedSnapshot(
                for: resumeUserId,
                aliases: appState.resumeUserAliases,
                visibleItemTypesByJobID: visibleResumeItemTypesByJobID()
            )
            await MainActor.run {
                applyResumeSnapshot(snapshot)
            }
        }
    }

    private func visibleResumeItemTypesByJobID() -> [String: String] {
        viewModel.filteredJobs.reduce(into: [:]) { result, job in
            result[job.jobId] = job.jobType
        }
    }

    private func applyResumeSnapshot(_ snapshot: BrowseResumeSnapshot) {
        resumeAvailability = snapshot.availabilityByJobID
    }

    private func resumeStatus(for job: PipelineStatusResponse) -> LibraryRowView.ResumeStatus {
        BrowseResumeStatusFormatter.rowStatus(
            for: job.jobId,
            availabilityByJobID: resumeAvailability
        )
    }

    @ViewBuilder
    private func playbackContextMenu(for job: PipelineStatusResponse) -> some View {
        let hasResume = BrowseResumeStatusFormatter.hasResume(
            for: job.jobId,
            availabilityByJobID: resumeAvailability
        )

        Button {
            handleResumeJobSelection(job)
        } label: {
            if hasResume {
                Label(resumeMenuLabel(for: job), systemImage: "play.fill")
            } else {
                Label("Play", systemImage: "play.fill")
            }
        }

        if hasResume {
            Button {
                handleStartOverJobSelection(job)
            } label: {
                Label("Start from Beginning", systemImage: "arrow.counterclockwise")
            }
        }
    }

    private func resumeMenuLabel(for job: PipelineStatusResponse) -> String {
        BrowseResumeStatusFormatter.menuLabel(
            for: job.jobId,
            availabilityByJobID: resumeAvailability
        )
    }

    @MainActor
    private func handleDelete(_ job: PipelineStatusResponse) async {
        let didDelete = await viewModel.delete(jobId: job.jobId, using: appState)
        guard didDelete else { return }
        offlineStore.remove(jobId: job.jobId, kind: .job)
        resumeAvailability.removeValue(forKey: job.jobId)
    }
}
