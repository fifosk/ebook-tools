import Foundation
import SwiftUI
#if os(tvOS)
import UIKit
#endif

struct LibraryView: View {
    @EnvironmentObject var appState: AppState
    @EnvironmentObject var offlineStore: OfflineMediaStore
    @ObservedObject var viewModel: LibraryViewModel
    let useNavigationLinks: Bool
    let onRefresh: () -> Void
    let onSignOut: () -> Void
    let onSelect: ((LibraryItem) -> Void)?
    let coverResolver: (LibraryItem) -> URL?
    let resumeUserId: String?
    let sectionPicker: AnyView?
    let onCollapseSidebar: (() -> Void)?
    let onSearchRequested: (() -> Void)?

    @FocusState private var isSearchFocused: Bool
    @State private var resumeAvailability: [String: PlaybackResumeAvailability] = [:]
    @State private var iCloudStatus = PlaybackResumeStore.shared.iCloudStatus()
    #if os(iOS)
    @State private var rowFrames: [CGRect] = []
    private let listCoordinateSpace = "libraryList"
    #endif
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
                ForEach(viewModel.filteredItems) { item in
                    if useNavigationLinks {
                        #if os(tvOS)
                        NavigationLink(value: item) {
                            LibraryRowView(
                                item: item,
                                coverURL: coverResolver(item),
                                resumeStatus: resumeStatus(for: item)
                            )
                        }
                        .listRowBackground(Color.clear)
                        .contextMenu {
                            Button(role: .destructive) {
                                Task { await handleDelete(item) }
                            } label: {
                                Label("Delete", systemImage: "trash")
                            }
                        }
                        #else
                        NavigationLink(value: item) {
                            LibraryRowView(
                                item: item,
                                coverURL: coverResolver(item),
                                resumeStatus: resumeStatus(for: item)
                            )
                        }
                        .background(rowFrameCapture())
                        .swipeActions(edge: .trailing, allowsFullSwipe: true) {
                            Button(role: .destructive) {
                                Task { await handleDelete(item) }
                            } label: {
                                Label("Delete", systemImage: "trash")
                            }
                        }
                        #endif
                    } else {
                        #if os(tvOS)
                        Button {
                            onSelect?(item)
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
                            resumeStatus: resumeStatus(for: item)
                        )
                            .background(rowFrameCapture())
                            .contentShape(Rectangle())
                            .onTapGesture {
                                onSelect?(item)
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
            }
            .listStyle(.plain)
            #if os(tvOS)
            .background(AppTheme.background(for: colorScheme))
            #endif
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
        .font(tvOSHeaderFont)
        #endif
    }

    private var searchRow: some View {
        HStack(spacing: 8) {
            TextField("Search library", text: $viewModel.query)
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
            ForEach(LibraryViewModel.LibraryFilter.allCases) { filter in
                Text(filter.rawValue).tag(filter)
            }
        }
        .pickerStyle(.automatic)
        .padding(.horizontal)
        .onLongPressGesture(minimumDuration: 0.6) {
            handleRefresh()
        }
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

    #if os(tvOS)
    private var tvOSHeaderFont: Font {
        let size = UIFont.preferredFont(forTextStyle: .body).pointSize * 0.5
        return .system(size: size)
    }
    #endif

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
            Button(action: handleRefresh) {
                Image(systemName: "arrow.clockwise")
            }
            .disabled(viewModel.isLoading)
            .accessibilityLabel("Refresh")
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
        }
        .padding(.horizontal)
        #if os(tvOS)
        .font(tvOSHeaderFont)
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
