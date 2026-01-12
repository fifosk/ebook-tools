import Foundation
import SwiftUI
#if os(tvOS)
import UIKit
#endif

struct JobsView: View {
    @EnvironmentObject var appState: AppState
    @ObservedObject var viewModel: JobsViewModel
    let useNavigationLinks: Bool
    let onRefresh: () -> Void
    let onSignOut: () -> Void
    let onSelect: ((PipelineStatusResponse) -> Void)?
    let sectionPicker: AnyView?
    let resumeUserId: String?

    @FocusState private var isSearchFocused: Bool
    @State private var resumeAvailability: [String: PlaybackResumeAvailability] = [:]
    @State private var iCloudStatus = PlaybackResumeStore.shared.iCloudStatus()
    @Environment(\.colorScheme) private var colorScheme
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
                if viewModel.activeJobs.isEmpty {
                    Section("Active jobs") {
                        Text("No active jobs.")
                            .foregroundStyle(.secondary)
                            #if os(tvOS)
                            .listRowBackground(Color.clear)
                            #endif
                    }
                } else {
                    Section("Active jobs") {
                        jobRows(viewModel.activeJobs)
                    }
                }

                if viewModel.finishedJobs.isEmpty {
                    Section("Finished jobs") {
                        Text("No finished jobs yet.")
                            .foregroundStyle(.secondary)
                            #if os(tvOS)
                            .listRowBackground(Color.clear)
                            #endif
                    }
                } else {
                    Section("Finished jobs") {
                        jobRows(viewModel.finishedJobs)
                    }
                }
            }
            .listStyle(.plain)
            #if os(tvOS)
            .background(AppTheme.background(for: colorScheme))
            #endif
            .overlay(alignment: .center) {
                listOverlay
            }
        }
        .onAppear {
            refreshResumeStatus()
            #if os(tvOS)
            viewModel.startAutoRefresh(using: appState)
            #endif
        }
        .onChange(of: resumeUserId) { _, _ in
            refreshResumeStatus()
        }
        .onReceive(NotificationCenter.default.publisher(for: PlaybackResumeStore.didChangeNotification)) { notification in
            guard let resumeUserId else { return }
            let userId = notification.userInfo?["userId"] as? String
            guard userId == resumeUserId else { return }
            Task { @MainActor in
                resumeAvailability = PlaybackResumeStore.shared.availabilitySnapshot(for: resumeUserId)
                iCloudStatus = PlaybackResumeStore.shared.iCloudStatus()
            }
        }
        #if os(tvOS)
        .onDisappear {
            viewModel.stopAutoRefresh()
        }
        #endif
        #if !os(tvOS)
        .toolbar {
            ToolbarItemGroup(placement: .topBarLeading) {
                Button("Refresh", action: handleRefresh)
                    .disabled(viewModel.isLoading)
                Button("Sync", action: handleSync)
                    .disabled(resumeUserId == nil)
            }
            ToolbarItem(placement: .topBarTrailing) {
                Button("Sign Out", action: onSignOut)
            }
        }
        #endif
    }

    @ViewBuilder
    private func jobRows(_ jobs: [PipelineStatusResponse]) -> some View {
        ForEach(jobs) { job in
            if useNavigationLinks {
                NavigationLink(value: job) {
                    JobRowView(job: job, resumeStatus: resumeStatus(for: job))
                }
                #if os(tvOS)
                .listRowBackground(Color.clear)
                #endif
            } else {
                #if os(tvOS)
                Button {
                    onSelect?(job)
                } label: {
                    JobRowView(job: job, resumeStatus: resumeStatus(for: job))
                }
                .buttonStyle(.plain)
                .listRowBackground(Color.clear)
                #else
                JobRowView(job: job, resumeStatus: resumeStatus(for: job))
                    .contentShape(Rectangle())
                    .onTapGesture {
                        onSelect?(job)
                    }
                #endif
            }
        }
    }

    private func errorRow(message: String) -> some View {
        Label(message, systemImage: "exclamationmark.triangle.fill")
            .foregroundStyle(.red)
            .font(.callout)
    }

    private var listOverlay: some View {
        Group {
            if viewModel.isLoading {
                ProgressView("Loading jobs…")
                    .padding()
                    .background(.thinMaterial, in: RoundedRectangle(cornerRadius: 12))
            } else if viewModel.filteredJobs.isEmpty {
                Text("No jobs found.")
                    .foregroundStyle(.secondary)
            }
        }
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 12) {
            #if os(tvOS)
            headerButtons
            if isSearchPresented {
                searchRow
            }
            if let sectionPicker {
                sectionPicker
            }
            filterPicker
            #else
            searchRow
            filterPicker
            #endif
            iCloudStatusRow
        }
        .padding(.top, 8)
        #if os(tvOS)
        .font(tvOSHeaderFont)
        #endif
    }

    private var searchRow: some View {
        HStack(spacing: 8) {
            TextField("Search jobs", text: $viewModel.query)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
                .focused($isSearchFocused)
                .submitLabel(.search)
                .onSubmit {
                    handleRefresh()
                    #if os(tvOS)
                    dismissSearch()
                    #endif
                }
            Button(action: handleRefresh) {
                Image(systemName: "magnifyingglass")
            }
            .disabled(viewModel.isLoading)
            #if os(tvOS)
            Button("Cancel") {
                dismissSearch()
            }
            #endif
        }
        .padding(.horizontal)
        #if os(tvOS)
        .onAppear {
            DispatchQueue.main.async {
                isSearchFocused = true
            }
        }
        .onExitCommand {
            dismissSearch()
        }
        #endif
    }

    @ViewBuilder
    private var filterPicker: some View {
        #if os(tvOS)
        Picker("Filter", selection: $viewModel.activeFilter) {
            ForEach(JobsViewModel.JobFilter.allCases) { filter in
                Text(filter.rawValue).tag(filter)
            }
        }
        .pickerStyle(.automatic)
        .padding(.horizontal)
        #else
        Picker("Filter", selection: $viewModel.activeFilter) {
            ForEach(JobsViewModel.JobFilter.allCases) { filter in
                Text(filter.rawValue).tag(filter)
            }
        }
        .pickerStyle(.segmented)
        .padding(.horizontal)
        #endif
    }

    #if os(tvOS)
    private var headerButtons: some View {
        HStack(spacing: 16) {
            Button("Refresh", action: handleRefresh)
                .disabled(viewModel.isLoading)
            Button {
                presentSearch()
            } label: {
                Image(systemName: "magnifyingglass")
            }
            Button("Sync", action: handleSync)
                .disabled(resumeUserId == nil)
            Button("Sign Out", action: onSignOut)
        }
        .padding(.horizontal)
    }
    #endif

    #if os(tvOS)
    private var tvOSHeaderFont: Font {
        let size = UIFont.preferredFont(forTextStyle: .body).pointSize * 0.5
        return .system(size: size)
    }
    #endif

    private var iCloudStatusRow: some View {
        let status = iCloudStatus
        let label = status.isAvailable ? "iCloud: connected" : "iCloud: unavailable"
        let detail = status.lastSyncAttempt.map { "Last sync \(formatRelativeTime($0))" }
        return HStack(spacing: 8) {
            Image(systemName: status.isAvailable ? "icloud" : "icloud.slash")
                .foregroundStyle(status.isAvailable ? Color.blue : Color.secondary)
            Text(label)
                .foregroundStyle(status.isAvailable ? Color.primary : Color.secondary)
            if let detail {
                Text(detail)
                    .foregroundStyle(.secondary)
            }
            Spacer()
        }
        .font(iCloudStatusFont)
        .padding(.horizontal)
    }

    private var iCloudStatusFont: Font {
        #if os(tvOS)
        return tvOSHeaderFont
        #else
        return .caption
        #endif
    }

    private func handleRefresh() {
        refreshResumeStatus()
        onRefresh()
    }

    #if os(tvOS)
    private func presentSearch() {
        isSearchPresented = true
        DispatchQueue.main.async {
            isSearchFocused = true
        }
    }

    private func dismissSearch() {
        isSearchFocused = false
        isSearchPresented = false
    }
    #endif

    private func handleSync() {
        guard let resumeUserId else { return }
        Task {
            await PlaybackResumeStore.shared.syncNow(userId: resumeUserId)
            await MainActor.run {
                resumeAvailability = PlaybackResumeStore.shared.availabilitySnapshot(for: resumeUserId)
                iCloudStatus = PlaybackResumeStore.shared.iCloudStatus()
            }
        }
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
        resumeAvailability = PlaybackResumeStore.shared.availabilitySnapshot(for: resumeUserId)
        iCloudStatus = PlaybackResumeStore.shared.iCloudStatus()
        Task {
            await PlaybackResumeStore.shared.refreshCloudEntries(userId: resumeUserId)
            await MainActor.run {
                resumeAvailability = PlaybackResumeStore.shared.availabilitySnapshot(for: resumeUserId)
                iCloudStatus = PlaybackResumeStore.shared.iCloudStatus()
            }
        }
    }

    private func resumeStatus(for job: PipelineStatusResponse) -> LibraryRowView.ResumeStatus {
        guard let availability = resumeAvailability[job.jobId] else {
            return .none()
        }
        let localEntry = availability.hasLocal ? availability.localEntry : nil
        let cloudEntry = availability.hasCloud ? availability.cloudEntry : nil
        if localEntry == nil && cloudEntry == nil {
            return .none()
        }
        if let localEntry, let cloudEntry {
            let localLabel = resumeLabel(prefix: "L", entry: localEntry)
            let cloudLabel = resumeLabel(prefix: "C", entry: cloudEntry)
            let label = "\(localLabel) \(cloudLabel)"
            return .both(label: label)
        }
        if let localEntry {
            let label = resumeLabel(prefix: "L", entry: localEntry)
            return .local(label: label)
        }
        let label = resumeLabel(prefix: "C", entry: cloudEntry)
        return .cloud(label: label)
    }

    private func formatRelativeTime(_ timestamp: TimeInterval) -> String {
        let formatter = RelativeDateTimeFormatter()
        formatter.unitsStyle = .short
        let date = Date(timeIntervalSince1970: timestamp)
        return formatter.localizedString(for: date, relativeTo: Date())
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
