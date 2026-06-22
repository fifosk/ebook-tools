import Foundation
import SwiftUI
#if os(tvOS)
import UIKit
#endif

struct JobsView: View {
    @EnvironmentObject var appState: AppState
    @EnvironmentObject var offlineStore: OfflineMediaStore
    @ObservedObject var viewModel: JobsViewModel
    let onRefresh: () -> Void
    let onSignOut: () -> Void
    let onSelect: ((PipelineStatusResponse, PlaybackStartMode) -> Void)?
    let sectionPicker: BrowseSectionPicker?
    let resumeUserId: String?
    let onCollapseSidebar: (() -> Void)?
    let onSearchRequested: (() -> Void)?
    var usesDarkBackground: Bool = false

    @FocusState private var isSearchFocused: Bool
    @State private var resumeAvailability: [String: PlaybackResumeAvailability] = [:]
    @State private var iCloudStatus = PlaybackResumeStore.shared.iCloudStatus()
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
            .coordinateSpace(name: listCoordinateSpace)
            .onPreferenceChange(RowFramePreferenceKey.self, perform: updateRowFrames)
            .simultaneousGesture(
                DragGesture(minimumDistance: 24, coordinateSpace: .named(listCoordinateSpace))
                    .onEnded(handleListDragEnd)
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
    }

    @ViewBuilder
    private func jobRows(_ jobs: [PipelineStatusResponse]) -> some View {
        ForEach(jobs) { job in
            // Always use programmatic navigation to support context menu actions
            #if os(tvOS)
            Button(action: { handleJobRowTap(job) }) {
                JobRowView(job: job, resumeStatus: resumeStatus(for: job))
            }
            .buttonStyle(.plain)
            .listRowBackground(Color.clear)
            .contextMenu {
                playbackContextMenu(for: job)
                offlineContextMenu(for: job)
                moveToLibraryAction(for: job)
                deleteJobAction(for: job)
            }
            #else
            JobRowView(job: job, resumeStatus: resumeStatus(for: job), usesDarkBackground: usesDarkListBackground)
                .background(rowFrameCapture())
                .contentShape(Rectangle())
                .listRowBackground(usesDarkListBackground ? Color.clear : nil)
                .onTapGesture {
                    handleJobRowTap(job)
                }
                .contextMenu {
                    playbackContextMenu(for: job)
                    moveToLibraryAction(for: job)
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

    #if os(iOS)
    private func rowFrameCapture() -> some View {
        GeometryReader { proxy in
            Color.clear.preference(
                key: RowFramePreferenceKey.self,
                value: [proxy.frame(in: .named(listCoordinateSpace))]
            )
        }
    }
    #else
    private func rowFrameCapture() -> some View {
        Color.clear
    }
    #endif

    private var listOverlay: some View {
        Group {
            if viewModel.isLoading {
                ProgressView("Loading jobs…")
                    .padding()
                    .background(.thinMaterial, in: RoundedRectangle(cornerRadius: 12))
                    .accessibilityIdentifier("jobsLoadingView")
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

    private var header: some View {
        VStack(alignment: .leading, spacing: 12) {
            BrowseActionRow(
                iCloudStatus: iCloudStatus,
                resumeUserId: resumeUserId,
                isLoading: viewModel.isLoading,
                usesDarkListBackground: usesDarkListBackground,
                onRefresh: handleRefresh,
                onSignOut: onSignOut,
                onSync: handleSync
            )
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
        guard let resumeUserId else { return }
        let userId = notification.userInfo?["userId"] as? String
        guard userId == resumeUserId else { return }
        Task { @MainActor in
            refreshResumeEvidence(for: resumeUserId)
        }
    }

    #if os(iOS)
    private func updateRowFrames(_ frames: [CGRect]) {
        rowFrames = frames
    }

    private func handleListDragEnd(_ value: DragGesture.Value) {
        guard let onCollapseSidebar else { return }
        let start = value.startLocation
        guard !rowFrames.contains(where: { $0.contains(start) }) else { return }
        let horizontal = value.translation.width
        let vertical = value.translation.height
        guard abs(horizontal) > abs(vertical) else { return }
        guard horizontal < -70 else { return }
        guard abs(vertical) < 50 else { return }
        onCollapseSidebar()
    }
    #endif

    private func handleDeleteJobRequest(_ job: PipelineStatusResponse) {
        Task { await handleDelete(job) }
    }

    private func handleMoveToLibraryRequest(_ job: PipelineStatusResponse) {
        Task { await handleMoveToLibrary(job) }
    }

    private func handleMoveToLibrary(_ job: PipelineStatusResponse) async {
        _ = await viewModel.moveToLibrary(jobId: job.jobId, using: appState)
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

    private func handleSync() {
        guard let resumeUserId else { return }
        Task {
            await PlaybackResumeStore.shared.syncNow(userId: resumeUserId, aliases: appState.resumeUserAliases)
            await MainActor.run {
                refreshResumeEvidence(for: resumeUserId)
            }
        }
    }

    private func refreshResumeEvidence(for userId: String) {
        resumeAvailability = PlaybackResumeStore.shared.availabilitySnapshot(for: userId)
        iCloudStatus = PlaybackResumeStore.shared.iCloudStatus()
    }

    private func refreshResumeStatus() {
        guard let resumeUserId else {
            resumeAvailability = [:]
            iCloudStatus = PlaybackResumeStore.shared.iCloudStatus()
            Task {
                await PlaybackResumeStore.shared.refreshCloudEntries(userId: "anonymous")
                await MainActor.run {
                    iCloudStatus = PlaybackResumeStore.shared.iCloudStatus()
                }
            }
            return
        }
        refreshResumeEvidence(for: resumeUserId)
        Task {
            await PlaybackResumeStore.shared.refreshCloudEntries(
                userId: resumeUserId,
                aliases: appState.resumeUserAliases
            )
            await MainActor.run {
                refreshResumeEvidence(for: resumeUserId)
            }
        }
    }

    private func resumeStatus(for job: PipelineStatusResponse) -> LibraryRowView.ResumeStatus {
        guard let availability = resumeAvailability[job.jobId] else {
            return .none()
        }
        let cloudEntry = availability.hasCloud ? availability.cloudEntry : nil
        guard let cloudEntry else {
            return .none()
        }
        let label = resumeLabel(prefix: "C", entry: cloudEntry)
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

    @ViewBuilder
    private func playbackContextMenu(for job: PipelineStatusResponse) -> some View {
        let availability = resumeAvailability[job.jobId]
        let hasResume = availability?.hasCloud == true || availability?.hasLocal == true

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

    #if os(tvOS)
    @ViewBuilder
    private func offlineContextMenu(for job: PipelineStatusResponse) -> some View {
        let status = offlineStore.status(for: job.jobId, kind: .job)
        let isEligible = job.isFinishedForDisplay

        if status.isSynced {
            Button(role: .destructive, action: { handleRemoveOfflineCopyMenuTap(job) }) {
                Label("Remove Offline Copy", systemImage: "trash.circle")
            }
        } else if status.isSyncing {
            Button(action: handleOfflineStatusTap) {
                Label("Downloading...", systemImage: "arrow.down.circle")
            }
            .disabled(true)
        } else if isEligible {
            Button(action: { handleDownloadWithLookupCacheMenuTap(job) }) {
                Label("Download with Dictionary", systemImage: "arrow.down.circle")
            }
            .disabled(!offlineStore.isAvailable || appState.configuration == nil)
            Button(action: { handleDownloadWithoutLookupCacheMenuTap(job) }) {
                Label("Download without Dictionary", systemImage: "arrow.down.circle.dotted")
            }
            .disabled(!offlineStore.isAvailable || appState.configuration == nil)
        }
    }

    private func handleOfflineStatusTap() {}

    private func handleRemoveOfflineCopyMenuTap(_ job: PipelineStatusResponse) {
        handleRemoveOfflineCopy(job)
    }

    private func handleDownloadWithLookupCacheMenuTap(_ job: PipelineStatusResponse) {
        handleDownloadOfflineCopy(job, includeLookupCache: true)
    }

    private func handleDownloadWithoutLookupCacheMenuTap(_ job: PipelineStatusResponse) {
        handleDownloadOfflineCopy(job, includeLookupCache: false)
    }

    private func handleRemoveOfflineCopy(_ job: PipelineStatusResponse) {
        offlineStore.remove(jobId: job.jobId, kind: .job)
    }

    private func handleDownloadOfflineCopy(_ job: PipelineStatusResponse, includeLookupCache: Bool) {
        guard let configuration = appState.configuration else { return }
        offlineStore.sync(
            jobId: job.jobId,
            kind: .job,
            configuration: configuration,
            includeLookupCache: includeLookupCache
        )
    }
    #else
    @ViewBuilder
    private func offlineContextMenu(for job: PipelineStatusResponse) -> some View {
        EmptyView()
    }
    #endif

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

    @MainActor
    private func handleDelete(_ job: PipelineStatusResponse) async {
        let didDelete = await viewModel.delete(jobId: job.jobId, using: appState)
        guard didDelete else { return }
        offlineStore.remove(jobId: job.jobId, kind: .job)
        resumeAvailability.removeValue(forKey: job.jobId)
        iCloudStatus = PlaybackResumeStore.shared.iCloudStatus()
    }
}

private struct JobsFilterPicker: View {
    @Binding var activeFilter: JobsViewModel.JobFilter
    let usesDarkListBackground: Bool
    let colorScheme: ColorScheme
    let onRefresh: () -> Void

    var body: some View {
        Picker("Filter", selection: $activeFilter) {
            ForEach(JobsViewModel.JobFilter.allCases) { filter in
                Text(filter.rawValue).tag(filter)
            }
        }
        .jobsFilterPickerStyle(
            usesDarkListBackground: usesDarkListBackground,
            colorScheme: colorScheme,
            onRefresh: handleFilterRefreshLongPress
        )
    }

    private func handleFilterRefreshLongPress() {
        onRefresh()
    }
}

private extension View {
    @ViewBuilder
    func jobsFilterPickerStyle(
        usesDarkListBackground: Bool,
        colorScheme: ColorScheme,
        onRefresh: @escaping () -> Void
    ) -> some View {
        #if os(tvOS)
        self
            .pickerStyle(.automatic)
            .padding(.horizontal)
            .onLongPressGesture(minimumDuration: 0.6, perform: onRefresh)
        #elseif os(iOS)
        self
            .pickerStyle(.segmented)
            .colorScheme(usesDarkListBackground ? .dark : colorScheme)
            .padding(.horizontal)
        #else
        self
            .pickerStyle(.segmented)
            .padding(.horizontal)
        #endif
    }
}

#if os(iOS)
private struct RowFramePreferenceKey: PreferenceKey {
    static var defaultValue: [CGRect] = []

    static func reduce(value: inout [CGRect], nextValue: () -> [CGRect]) {
        value.append(contentsOf: nextValue())
    }
}
#endif
