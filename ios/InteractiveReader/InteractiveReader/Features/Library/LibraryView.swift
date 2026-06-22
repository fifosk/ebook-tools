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
    let sectionPicker: BrowseSectionPicker?
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
                libraryRows(viewModel.filteredItems)
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
        .onAppear(perform: handleLibraryAppear)
        .onChange(of: resumeUserId, initial: false, handleResumeUserChange)
        .onReceive(
            NotificationCenter.default.publisher(for: PlaybackResumeStore.didChangeNotification),
            perform: handleResumeStoreChange
        )
    }

    @ViewBuilder
    private func libraryRows(_ items: [LibraryItem]) -> some View {
        ForEach(items) { item in
            // Always use programmatic navigation to support context menu actions.
            #if os(tvOS)
            Button(action: { handleLibraryRowTap(item) }) {
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
                deleteItemAction(for: item)
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
                handleLibraryRowTap(item)
            }
            .contextMenu {
                playbackContextMenu(for: item)
                deleteItemAction(for: item)
            }
            .swipeActions(edge: .trailing, allowsFullSwipe: true) {
                deleteItemAction(for: item)
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
                ProgressView("Loading library…")
                    .padding()
                    .background(.thinMaterial, in: RoundedRectangle(cornerRadius: 12))
                    .accessibilityIdentifier("libraryLoadingView")
            } else if viewModel.filteredItems.isEmpty {
                ContentUnavailableView {
                    Label("No library items found", systemImage: "books.vertical")
                } description: {
                    Text(viewModel.query.isEmpty ? "Move a completed job to the library to keep it here." : "Try a different search term.")
                }
                .foregroundStyle(usesDarkListBackground ? .white : .primary)
                .accessibilityIdentifier("libraryEmptyView")
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
            LibraryFilterPicker(
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

    private var searchRow: some View {
        HStack(spacing: 8) {
            TextField("Search library", text: $viewModel.query)
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

    private var actionRow: some View {
        BrowseActionRow(
            iCloudStatus: iCloudStatus,
            resumeUserId: resumeUserId,
            isLoading: viewModel.isLoading,
            usesDarkListBackground: usesDarkListBackground,
            onRefresh: handleRefresh,
            onSignOut: onSignOut,
            onSync: handleSync
        )
    }

    private func selectItem(_ item: LibraryItem, mode: PlaybackStartMode) {
        onSelect?(item, mode)
    }

    private func handleResumeItemSelection(_ item: LibraryItem) {
        selectItem(item, mode: .resume)
    }

    private func handleLibraryRowTap(_ item: LibraryItem) {
        handleResumeItemSelection(item)
    }

    private func handleStartOverItemSelection(_ item: LibraryItem) {
        selectItem(item, mode: .startOver)
    }

    private func handleLibraryAppear() {
        refreshResumeStatus()
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

    private func handleDeleteItemRequest(_ item: LibraryItem) {
        Task { await handleDelete(item) }
    }

    private func deleteItemAction(for item: LibraryItem) -> some View {
        Button(role: .destructive, action: { handleDeleteItemRequest(item) }) {
            Label("Delete", systemImage: "trash")
        }
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
            handleResumeItemSelection(item)
        } label: {
            if hasResume {
                Label(resumeMenuLabel(for: item), systemImage: "play.fill")
            } else {
                Label("Play", systemImage: "play.fill")
            }
        }

        if hasResume {
            Button {
                handleStartOverItemSelection(item)
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
            Button(role: .destructive, action: { handleRemoveOfflineCopy(item) }) {
                Label("Remove Offline Copy", systemImage: "trash.circle")
            }
        } else if status.isSyncing {
            Button(action: handleOfflineStatusTap) {
                Label("Downloading...", systemImage: "arrow.down.circle")
            }
            .disabled(true)
        } else {
            Button(action: { handleDownloadOfflineCopy(item, includeLookupCache: true) }) {
                Label("Download with Dictionary", systemImage: "arrow.down.circle")
            }
            .disabled(!offlineStore.isAvailable || appState.configuration == nil)
            Button(action: { handleDownloadOfflineCopy(item, includeLookupCache: false) }) {
                Label("Download without Dictionary", systemImage: "arrow.down.circle.dotted")
            }
            .disabled(!offlineStore.isAvailable || appState.configuration == nil)
        }
    }

    private func handleOfflineStatusTap() {}

    private func handleRemoveOfflineCopy(_ item: LibraryItem) {
        offlineStore.remove(jobId: item.jobId, kind: .library)
    }

    private func handleDownloadOfflineCopy(_ item: LibraryItem, includeLookupCache: Bool) {
        guard let configuration = appState.configuration else { return }
        offlineStore.sync(
            jobId: item.jobId,
            kind: .library,
            configuration: configuration,
            includeLookupCache: includeLookupCache
        )
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

private struct LibraryFilterPicker: View {
    @Binding var activeFilter: LibraryViewModel.LibraryFilter
    let usesDarkListBackground: Bool
    let colorScheme: ColorScheme
    let onRefresh: () -> Void

    var body: some View {
        Picker("Filter", selection: $activeFilter) {
            ForEach(LibraryViewModel.LibraryFilter.allCases) { filter in
                Text(filter.rawValue).tag(filter)
            }
        }
        .libraryFilterPickerStyle(
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
    func libraryFilterPickerStyle(
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
