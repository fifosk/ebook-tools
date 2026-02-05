import Foundation
import SwiftUI
#if os(tvOS)
import UIKit
#endif

enum PlaybackStartMode {
    case resume
    case startOver
}

struct LibraryView: View {
    @EnvironmentObject var appState: AppState
    @EnvironmentObject var offlineStore: OfflineMediaStore
    @ObservedObject var viewModel: LibraryViewModel
    let onRefresh: () -> Void
    let onSignOut: () -> Void
    let onSelect: ((LibraryItem, PlaybackStartMode) -> Void)?
    let coverResolver: (LibraryItem) -> URL?
    let resumeUserId: String?
    let sectionPicker: AnyView?
    let onCollapseSidebar: (() -> Void)?
    let onSearchRequested: (() -> Void)?
    var usesDarkBackground: Bool = false

    @FocusState private var isSearchFocused: Bool
    @State private var resumeAvailability: [String: PlaybackResumeAvailability] = [:]
    @State private var iCloudStatus = PlaybackResumeStore.shared.iCloudStatus()
    #if os(iOS)
    @State private var rowFrames: [CGRect] = []
    private let listCoordinateSpace = "libraryList"
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
                ForEach(viewModel.filteredItems) { item in
                    // Always use programmatic navigation to support context menu actions
                    #if os(tvOS)
                    Button {
                        onSelect?(item, .resume)
                    } label: {
                        LibraryRowView(
                            item: item,
                            coverURL: coverResolver(item),
                            resumeStatus: resumeStatus(for: item)
                        )
                    }
                    .buttonStyle(.plain)
                    .listRowBackground(Color.clear)
                    .contextMenu {
                        playbackContextMenu(for: item)
                        offlineContextMenu(for: item)
                        Button(role: .destructive) {
                            Task { await handleDelete(item) }
                        } label: {
                            Label("Delete", systemImage: "trash")
                        }
                    }
                    #else
                    LibraryRowView(
                        item: item,
                        coverURL: coverResolver(item),
                        resumeStatus: resumeStatus(for: item),
                        usesDarkBackground: usesDarkListBackground
                    )
                    .background(rowFrameCapture())
                    .contentShape(Rectangle())
                    .listRowBackground(usesDarkListBackground ? Color.clear : nil)
                    .onTapGesture {
                        onSelect?(item, .resume)
                    }
                    .contextMenu {
                        playbackContextMenu(for: item)
                        Button(role: .destructive) {
                            Task { await handleDelete(item) }
                        } label: {
                            Label("Delete", systemImage: "trash")
                        }
                    }
                    .swipeActions(edge: .trailing, allowsFullSwipe: true) {
                        Button(role: .destructive) {
                            Task { await handleDelete(item) }
                        } label: {
                            Label("Delete", systemImage: "trash")
                        }
                    }
                    #endif
                }
            }
            .listStyle(.plain)
            .platformListBackground(usesDark: usesDarkListBackground, colorScheme: colorScheme)
            #if os(iOS)
            .coordinateSpace(name: listCoordinateSpace)
            .onPreferenceChange(RowFramePreferenceKey.self) { frames in
                rowFrames = frames
            }
            .simultaneousGesture(
                DragGesture(minimumDistance: 24, coordinateSpace: .named(listCoordinateSpace))
                    .onEnded { value in
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
        .onAppear {
            refreshResumeStatus()
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
                ProgressView("Loading library…")
                    .padding()
                    .background(.thinMaterial, in: RoundedRectangle(cornerRadius: 12))
            } else if viewModel.filteredItems.isEmpty {
                Text("No items found.")
                    .foregroundStyle(.secondary)
            }
        }
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 12) {
            actionRow
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
            filterPicker
        }
        .padding(.top, 8)
        #if os(tvOS)
        .font(PlatformTypography.sectionHeaderFont)
        #endif
    }

    private var searchRow: some View {
        HStack(spacing: 8) {
            TextField("Search library", text: $viewModel.query)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
                .focused($isSearchFocused)
                .submitLabel(.search)
                .foregroundStyle(usesDarkListBackground ? .white : .primary)
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
            .tint(usesDarkListBackground ? .white : nil)
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
            ForEach(LibraryViewModel.LibraryFilter.allCases) { filter in
                Text(filter.rawValue).tag(filter)
            }
        }
        .pickerStyle(.automatic)
        .padding(.horizontal)
        .onLongPressGesture(minimumDuration: 0.6) {
            handleRefresh()
        }
        #elseif os(iOS)
        Picker("Filter", selection: $viewModel.activeFilter) {
            ForEach(LibraryViewModel.LibraryFilter.allCases) { filter in
                Text(filter.rawValue).tag(filter)
            }
        }
        .pickerStyle(.segmented)
        .colorScheme(usesDarkListBackground ? .dark : colorScheme)
        .padding(.horizontal)
        #else
        Picker("Filter", selection: $viewModel.activeFilter) {
            ForEach(LibraryViewModel.LibraryFilter.allCases) { filter in
                Text(filter.rawValue).tag(filter)
            }
        }
        .pickerStyle(.segmented)
        .padding(.horizontal)
        #endif
    }


    private var actionRow: some View {
        let status = iCloudStatus
        let userLabel = resumeUserId ?? "Log In"
        let statusLabel = status.isAvailable ? "Online" : "Offline"
        let iconSize = PlatformMetrics.listIconSize
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
            Button(action: handleRefresh) {
                Image(systemName: "arrow.clockwise")
            }
            .disabled(viewModel.isLoading)
            .accessibilityLabel("Refresh")
            .tint(usesDarkListBackground ? .white : nil)
            Spacer()
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
        }
        .padding(.horizontal)
        #if os(tvOS)
        .font(PlatformTypography.sectionHeaderFont)
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
            await PlaybackResumeStore.shared.syncNow(userId: resumeUserId, aliases: appState.resumeUserAliases)
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
            await PlaybackResumeStore.shared.refreshCloudEntries(
                userId: resumeUserId,
                aliases: appState.resumeUserAliases
            )
            await MainActor.run {
                resumeAvailability = PlaybackResumeStore.shared.availabilitySnapshot(for: resumeUserId)
                iCloudStatus = PlaybackResumeStore.shared.iCloudStatus()
            }
        }
    }

    private func resumeStatus(for item: LibraryItem) -> LibraryRowView.ResumeStatus {
        guard let availability = resumeAvailability[item.jobId] else {
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
    private func playbackContextMenu(for item: LibraryItem) -> some View {
        let availability = resumeAvailability[item.jobId]
        let hasResume = availability?.hasCloud == true || availability?.hasLocal == true

        Button {
            onSelect?(item, .resume)
        } label: {
            if hasResume {
                Label(resumeMenuLabel(for: item), systemImage: "play.fill")
            } else {
                Label("Play", systemImage: "play.fill")
            }
        }

        if hasResume {
            Button {
                onSelect?(item, .startOver)
            } label: {
                Label("Start from Beginning", systemImage: "arrow.counterclockwise")
            }
        }
    }

    #if os(tvOS)
    @ViewBuilder
    private func offlineContextMenu(for item: LibraryItem) -> some View {
        let status = offlineStore.status(for: item.jobId, kind: .library)

        if status.isSynced {
            Button(role: .destructive) {
                offlineStore.remove(jobId: item.jobId, kind: .library)
            } label: {
                Label("Remove Offline Copy", systemImage: "trash.circle")
            }
        } else if status.isSyncing {
            Button {
                // No-op, just shows status
            } label: {
                Label("Downloading...", systemImage: "arrow.down.circle")
            }
            .disabled(true)
        } else {
            Button {
                guard let configuration = appState.configuration else { return }
                offlineStore.sync(jobId: item.jobId, kind: .library, configuration: configuration, includeLookupCache: true)
            } label: {
                Label("Download with Dictionary", systemImage: "arrow.down.circle")
            }
            .disabled(!offlineStore.isAvailable || appState.configuration == nil)
            Button {
                guard let configuration = appState.configuration else { return }
                offlineStore.sync(jobId: item.jobId, kind: .library, configuration: configuration, includeLookupCache: false)
            } label: {
                Label("Download without Dictionary", systemImage: "arrow.down.circle.dotted")
            }
            .disabled(!offlineStore.isAvailable || appState.configuration == nil)
        }
    }
    #else
    @ViewBuilder
    private func offlineContextMenu(for item: LibraryItem) -> some View {
        EmptyView()
    }
    #endif

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

    @MainActor
    private func handleDelete(_ item: LibraryItem) async {
        let didDelete = await viewModel.delete(jobId: item.jobId, using: appState)
        guard didDelete else { return }
        offlineStore.remove(jobId: item.jobId, kind: .library)
        resumeAvailability.removeValue(forKey: item.jobId)
        iCloudStatus = PlaybackResumeStore.shared.iCloudStatus()
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
