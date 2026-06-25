import Foundation
import SwiftUI
#if os(iOS)
import UniformTypeIdentifiers
#endif

enum PlaybackStartMode {
    case resume
    case startOver
}

struct LibraryView: View {
    @EnvironmentObject var appState: AppState
    @EnvironmentObject var offlineStore: OfflineMediaStore
    @Environment(\.openURL) private var openURL
    @ObservedObject var viewModel: LibraryViewModel
    let onRefresh: () -> Void
    let onSelect: ((LibraryItem, PlaybackStartMode) -> Void)?
    let coverResolver: (LibraryItem) -> URL?
    let resumeUserId: String?
    let sectionPicker: BrowseSectionPicker?
    let onCollapseSidebar: (() -> Void)?
    let onSearchRequested: (() -> Void)?
    var usesDarkBackground: Bool = false

    @FocusState private var isSearchFocused: Bool
    @State private var resumeAvailability: [String: PlaybackResumeAvailability] = [:]
    @State private var sourceDiagnosticsItem: LibrarySourceDiagnosticsDraft?
    #if os(iOS)
    @State private var rowFrames: [CGRect] = []
    @State private var sourceUploadItem: LibraryItem?
    @State private var sourceUploadDraft: LibrarySourceUploadDraft?
    @State private var isImportingLibrarySource = false
    @State private var metadataEditDraft: LibraryMetadataEditDraft?
    @State private var isbnMetadataDraft: LibraryIsbnMetadataDraft?
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
        .onAppear(perform: handleLibraryAppear)
        .onChange(of: resumeUserId, initial: false, handleResumeUserChange)
        .onReceive(
            NotificationCenter.default.publisher(for: PlaybackResumeStore.didChangeNotification),
            perform: handleResumeStoreChange
        )
        .sheet(item: $sourceDiagnosticsItem) { draft in
            LibrarySourceDiagnosticsSheet(draft: draft)
        }
        #if os(iOS)
        .fileImporter(
            isPresented: $isImportingLibrarySource,
            allowedContentTypes: Self.librarySourceContentTypes,
            allowsMultipleSelection: false,
            onCompletion: handleLibrarySourceImport
        )
        .sheet(item: $isbnMetadataDraft) { draft in
            LibraryIsbnMetadataSheet(item: draft.item, viewModel: viewModel)
                .environmentObject(appState)
        }
        .sheet(item: $metadataEditDraft) { draft in
            LibraryMetadataEditSheet(item: draft.item, viewModel: viewModel)
                .environmentObject(appState)
        }
        .sheet(item: $sourceUploadDraft) { draft in
            LibrarySourceUploadReviewSheet(draft: draft, viewModel: viewModel)
                .environmentObject(appState)
        }
        #endif
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
                sourceDiagnosticsAction(for: item)
                enrichMetadataAction(for: item)
                offlineExportAction(for: item)
                deleteItemAction(for: item)
            }
            #else
            LibraryRowView(
                item: item,
                coverURL: coverResolver(item),
                resumeStatus: resumeStatus(for: item),
                usesDarkBackground: usesDarkListBackground
            )
            .background(BrowseListRowFrameCapture(coordinateSpaceName: listCoordinateSpace))
            .contentShape(Rectangle())
            .listRowBackground(usesDarkListBackground ? Color.clear : nil)
            .onTapGesture {
                handleLibraryRowTap(item)
            }
            .contextMenu {
                playbackContextMenu(for: item)
                sourceDiagnosticsAction(for: item)
                enrichMetadataAction(for: item)
                offlineExportAction(for: item)
                metadataEditAction(for: item)
                sourceUploadAction(for: item)
                isbnMetadataAction(for: item)
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

    private var listOverlay: some View {
        Group {
            if viewModel.isLoading {
                ProgressView("Loading library…")
                    .padding()
                    .background(.thinMaterial, in: RoundedRectangle(cornerRadius: 12))
                    .accessibilityIdentifier("libraryLoadingView")
            } else if viewModel.isUploadingSource {
                ProgressView("Uploading source…")
                    .padding()
                    .background(.thinMaterial, in: RoundedRectangle(cornerRadius: 12))
                    .accessibilityIdentifier("librarySourceUploadLoadingView")
            } else if viewModel.isApplyingIsbn {
                ProgressView("Updating metadata…")
                    .padding()
                    .background(.thinMaterial, in: RoundedRectangle(cornerRadius: 12))
                    .accessibilityIdentifier("libraryIsbnLoadingView")
            } else if viewModel.isCreatingExport {
                ProgressView("Creating offline export…")
                    .padding()
                    .background(.thinMaterial, in: RoundedRectangle(cornerRadius: 12))
                    .accessibilityIdentifier("libraryOfflineExportLoadingView")
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

    private func handleSourceDiagnosticsRequest(_ item: LibraryItem) {
        sourceDiagnosticsItem = LibrarySourceDiagnosticsDraft(item: item)
    }

    private func sourceDiagnosticsAction(for item: LibraryItem) -> some View {
        Button(action: { handleSourceDiagnosticsRequest(item) }) {
            Label("Source Details", systemImage: "info.circle")
        }
    }

    private func handleLibraryAppear() {
        refreshResumeStatus()
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

    private func handleDeleteItemRequest(_ item: LibraryItem) {
        Task { await handleDelete(item) }
    }

    private func deleteItemAction(for item: LibraryItem) -> some View {
        Button(role: .destructive, action: { handleDeleteItemRequest(item) }) {
            Label("Delete", systemImage: "trash")
        }
    }

    private func handleOfflineExportRequest(_ item: LibraryItem) {
        Task {
            let url = await viewModel.createOfflineExport(for: item, using: appState)
            await MainActor.run {
                if let url {
                    openURL(url)
                }
            }
        }
    }

    private func offlineExportAction(for item: LibraryItem) -> some View {
        Button(action: { handleOfflineExportRequest(item) }) {
            Label("Export Offline Player", systemImage: "square.and.arrow.down")
        }
        .disabled(!item.mediaCompleted || viewModel.isCreatingExport || appState.configuration == nil)
    }

    private func handleEnrichMetadataRequest(_ item: LibraryItem) {
        Task {
            let enriched = await viewModel.enrichMetadata(for: item, using: appState)
            await MainActor.run {
                if enriched {
                    refreshResumeStatus()
                }
            }
        }
    }

    private func enrichMetadataAction(for item: LibraryItem) -> some View {
        Button(action: { handleEnrichMetadataRequest(item) }) {
            Label("Enrich Metadata", systemImage: "sparkles")
        }
        .disabled(isMetadataMutationInProgress || appState.configuration == nil)
    }

    private var isMetadataMutationInProgress: Bool {
        viewModel.isUploadingSource
            || viewModel.isLookingUpIsbn
            || viewModel.isApplyingIsbn
            || viewModel.isEnrichingMetadata
            || viewModel.isUpdatingMetadata
    }

    #if os(iOS)
    private func handleMetadataEditRequest(_ item: LibraryItem) {
        metadataEditDraft = LibraryMetadataEditDraft(item: item)
    }

    private func metadataEditAction(for item: LibraryItem) -> some View {
        Button(action: { handleMetadataEditRequest(item) }) {
            Label("Edit Metadata", systemImage: "pencil")
        }
        .disabled(isMetadataMutationInProgress || appState.configuration == nil)
    }

    private func handleSourceUploadRequest(_ item: LibraryItem) {
        sourceUploadItem = item
        isImportingLibrarySource = true
    }

    private func sourceUploadAction(for item: LibraryItem) -> some View {
        Button(action: { handleSourceUploadRequest(item) }) {
            Label("Replace Source File", systemImage: "square.and.arrow.up")
        }
        .disabled(isMetadataMutationInProgress)
    }

    private func handleIsbnMetadataRequest(_ item: LibraryItem) {
        isbnMetadataDraft = LibraryIsbnMetadataDraft(item: item)
    }

    private func isbnMetadataAction(for item: LibraryItem) -> some View {
        Button(action: { handleIsbnMetadataRequest(item) }) {
            Label("Preview ISBN Metadata", systemImage: "barcode.viewfinder")
        }
        .disabled(isMetadataMutationInProgress)
    }

    private func handleLibrarySourceImport(_ result: Result<[URL], Error>) {
        switch result {
        case let .success(urls):
            guard let item = sourceUploadItem, let url = urls.first else {
                sourceUploadItem = nil
                return
            }
            sourceUploadDraft = LibrarySourceUploadDraft(item: item, fileURL: url)
            sourceUploadItem = nil
        case let .failure(error):
            sourceUploadItem = nil
            viewModel.errorMessage = error.localizedDescription
        }
    }

    private static var librarySourceContentTypes: [UTType] {
        [
            UTType(filenameExtension: "epub") ?? UTType(importedAs: "org.idpf.epub-container"),
            UTType.pdf,
            UTType.movie,
            UTType.mpeg4Movie,
            UTType(filenameExtension: "mkv") ?? UTType(importedAs: "org.matroska.mkv"),
            UTType(filenameExtension: "webm") ?? UTType(importedAs: "org.webmproject.webm")
        ]
    }
    #else
    private func metadataEditAction(for item: LibraryItem) -> some View {
        EmptyView()
    }

    private func sourceUploadAction(for item: LibraryItem) -> some View {
        EmptyView()
    }

    private func isbnMetadataAction(for item: LibraryItem) -> some View {
        EmptyView()
    }
    #endif

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
        viewModel.filteredItems.reduce(into: [:]) { result, item in
            result[item.jobId] = item.itemType
        }
    }

    private func applyResumeSnapshot(_ snapshot: BrowseResumeSnapshot) {
        resumeAvailability = snapshot.availabilityByJobID
    }

    private func resumeStatus(for item: LibraryItem) -> LibraryRowView.ResumeStatus {
        BrowseResumeStatusFormatter.rowStatus(
            for: item.jobId,
            availabilityByJobID: resumeAvailability
        )
    }

    @ViewBuilder
    private func playbackContextMenu(for item: LibraryItem) -> some View {
        let hasResume = BrowseResumeStatusFormatter.hasResume(
            for: item.jobId,
            availabilityByJobID: resumeAvailability
        )

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
            Button(role: .destructive, action: { handleRemoveOfflineCopyMenuTap(item) }) {
                Label("Remove Offline Copy", systemImage: "trash.circle")
            }
        } else if status.isSyncing {
            Button(action: handleOfflineStatusTap) {
                Label("Downloading...", systemImage: "arrow.down.circle")
            }
            .disabled(true)
        } else {
            Button(action: { handleDownloadWithLookupCacheMenuTap(item) }) {
                Label("Download with Dictionary", systemImage: "arrow.down.circle")
            }
            .disabled(!offlineStore.isAvailable || appState.configuration == nil)
            Button(action: { handleDownloadWithoutLookupCacheMenuTap(item) }) {
                Label("Download without Dictionary", systemImage: "arrow.down.circle.dotted")
            }
            .disabled(!offlineStore.isAvailable || appState.configuration == nil)
        }
    }

    private func handleOfflineStatusTap() {}

    private func handleRemoveOfflineCopyMenuTap(_ item: LibraryItem) {
        handleRemoveOfflineCopy(item)
    }

    private func handleDownloadWithLookupCacheMenuTap(_ item: LibraryItem) {
        handleDownloadOfflineCopy(item, includeLookupCache: true)
    }

    private func handleDownloadWithoutLookupCacheMenuTap(_ item: LibraryItem) {
        handleDownloadOfflineCopy(item, includeLookupCache: false)
    }

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
        BrowseResumeStatusFormatter.menuLabel(
            for: item.jobId,
            availabilityByJobID: resumeAvailability
        )
    }

    @MainActor
    private func handleDelete(_ item: LibraryItem) async {
        let didDelete = await viewModel.delete(jobId: item.jobId, using: appState)
        guard didDelete else { return }
        offlineStore.remove(jobId: item.jobId, kind: .library)
        resumeAvailability.removeValue(forKey: item.jobId)
    }
}

private struct LibrarySourceDiagnosticsDraft: Identifiable {
    let item: LibraryItem

    var id: String { item.jobId }

    var sourcePath: String? {
        item.sourcePath?.trimmingCharacters(in: .whitespacesAndNewlines).nonEmptyValue
    }

    var sourceFilename: String? {
        guard let sourcePath else { return nil }
        return URL(fileURLWithPath: sourcePath).lastPathComponent.nonEmptyValue ?? sourcePath
    }

    var sourceTypeLabel: String {
        guard let sourceFilename else { return "Missing" }
        let extensionValue = URL(fileURLWithPath: sourceFilename).pathExtension
            .trimmingCharacters(in: .whitespacesAndNewlines)
        return extensionValue.isEmpty ? "Unknown" : extensionValue.uppercased()
    }
}

private struct LibrarySourceDiagnosticsSheet: View {
    let draft: LibrarySourceDiagnosticsDraft
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            Form {
                Section("Library Item") {
                    LabeledContent("Title", value: draft.item.bookTitle)
                    LabeledContent("Author", value: draft.item.author)
                    LabeledContent("Type", value: draft.item.itemType)
                    LabeledContent("Status", value: draft.item.status)
                    LabeledContent("Media", value: draft.item.mediaCompleted ? "Complete" : "Incomplete")
                }

                Section("Source") {
                    LabeledContent("Stored", value: draft.sourcePath == nil ? "No" : "Yes")
                        .accessibilityIdentifier("librarySourceDiagnosticsStoredLabel")
                    LabeledContent("File", value: draft.sourceFilename ?? "No source file stored")
                        .accessibilityIdentifier("librarySourceDiagnosticsFilenameLabel")
                    LabeledContent("Type", value: draft.sourceTypeLabel)
                        .accessibilityIdentifier("librarySourceDiagnosticsTypeLabel")
                    if let sourcePath = draft.sourcePath {
                        LabeledContent("Relative path", value: sourcePath)
                            .accessibilityIdentifier("librarySourceDiagnosticsPathLabel")
                    }
                    LabeledContent("Updated", value: draft.item.updatedAt)
                }
            }
            .navigationTitle("Source Details")
            #if !os(tvOS)
            .navigationBarTitleDisplayMode(.inline)
            #endif
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Done") {
                        dismiss()
                    }
                }
            }
        }
    }
}

#if os(iOS)
private struct LibraryMetadataEditDraft: Identifiable {
    let item: LibraryItem

    var id: String { item.jobId }
}

private struct LibrarySourceUploadDraft: Identifiable {
    let item: LibraryItem
    let fileURL: URL

    var id: String {
        "\(item.jobId)-\(fileURL.lastPathComponent)"
    }

    var filename: String {
        fileURL.lastPathComponent
    }

    var fileTypeLabel: String {
        let suffix = fileURL.pathExtension.trimmingCharacters(in: .whitespacesAndNewlines)
        return suffix.isEmpty ? "Unknown type" : suffix.uppercased()
    }

    var fileSizeLabel: String? {
        guard let size = try? fileURL.resourceValues(forKeys: [.fileSizeKey]).fileSize else {
            return nil
        }
        return ByteCountFormatter.string(fromByteCount: Int64(size), countStyle: .file)
    }
}

private struct LibraryIsbnMetadataDraft: Identifiable {
    let item: LibraryItem

    var id: String { item.jobId }
}

private struct LibrarySourceUploadReviewSheet: View {
    let draft: LibrarySourceUploadDraft
    @ObservedObject var viewModel: LibraryViewModel
    @EnvironmentObject private var appState: AppState
    @Environment(\.dismiss) private var dismiss
    @State private var uploadError: String?

    var body: some View {
        NavigationStack {
            Form {
                Section("Library Item") {
                    LabeledContent("Title", value: draft.item.bookTitle)
                    LabeledContent("Author", value: draft.item.author)
                    LabeledContent("Current source", value: currentSourceLabel)
                }

                Section("Replacement Source") {
                    LabeledContent("File", value: draft.filename)
                        .accessibilityIdentifier("librarySourceUploadFilenameLabel")
                    LabeledContent("Type", value: draft.fileTypeLabel)
                    if let fileSizeLabel = draft.fileSizeLabel {
                        LabeledContent("Size", value: fileSizeLabel)
                            .accessibilityIdentifier("librarySourceUploadSizeLabel")
                    }
                }

                if let uploadError {
                    Section {
                        Label(uploadError, systemImage: "exclamationmark.triangle.fill")
                            .foregroundStyle(.red)
                    }
                }

                Section {
                    Button(action: handleUpload) {
                        if viewModel.isUploadingSource {
                            ProgressView()
                        } else {
                            Label("Replace Source File", systemImage: "square.and.arrow.up")
                        }
                    }
                    .disabled(viewModel.isUploadingSource || appState.configuration == nil)
                    .accessibilityIdentifier("librarySourceUploadConfirmButton")
                }
            }
            .navigationTitle("Review Source")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") {
                        dismiss()
                    }
                    .disabled(viewModel.isUploadingSource)
                }
            }
        }
    }

    private var currentSourceLabel: String {
        draft.item.sourcePath?.trimmingCharacters(in: .whitespacesAndNewlines).nonEmptyValue ?? "No source file stored"
    }

    private func handleUpload() {
        uploadError = nil
        Task {
            let uploaded = await viewModel.uploadSource(
                for: draft.item,
                fileURL: draft.fileURL,
                filename: draft.filename,
                using: appState
            )
            await MainActor.run {
                if uploaded {
                    dismiss()
                } else {
                    uploadError = viewModel.errorMessage ?? "Unable to replace the source file."
                }
            }
        }
    }
}

private struct LibraryMetadataEditSheet: View {
    let item: LibraryItem
    @ObservedObject var viewModel: LibraryViewModel
    @EnvironmentObject private var appState: AppState
    @Environment(\.dismiss) private var dismiss
    @State private var title: String
    @State private var author: String
    @State private var genre: String
    @State private var language: String
    @State private var isbn: String
    @State private var saveError: String?

    init(item: LibraryItem, viewModel: LibraryViewModel) {
        self.item = item
        self.viewModel = viewModel
        _title = State(initialValue: item.bookTitle)
        _author = State(initialValue: item.author)
        _genre = State(initialValue: item.genre ?? "")
        _language = State(initialValue: item.language)
        _isbn = State(initialValue: item.isbn ?? "")
    }

    var body: some View {
        NavigationStack {
            Form {
                Section("Metadata") {
                    TextField("Title", text: $title)
                        .textInputAutocapitalization(.words)
                        .accessibilityIdentifier("libraryMetadataTitleField")
                    TextField("Author", text: $author)
                        .textInputAutocapitalization(.words)
                        .accessibilityIdentifier("libraryMetadataAuthorField")
                    TextField("Genre", text: $genre)
                        .textInputAutocapitalization(.words)
                        .accessibilityIdentifier("libraryMetadataGenreField")
                    TextField("Language", text: $language)
                        .textInputAutocapitalization(.words)
                        .accessibilityIdentifier("libraryMetadataLanguageField")
                    TextField("ISBN", text: $isbn)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                        .keyboardType(.numbersAndPunctuation)
                        .accessibilityIdentifier("libraryMetadataIsbnField")
                }

                if let saveError {
                    Section {
                        Label(saveError, systemImage: "exclamationmark.triangle.fill")
                            .foregroundStyle(.red)
                    }
                }

                Section {
                    Button(action: handleSave) {
                        if viewModel.isUpdatingMetadata {
                            ProgressView()
                        } else {
                            Label("Save Metadata", systemImage: "checkmark.circle")
                        }
                    }
                    .disabled(!canSave || viewModel.isUpdatingMetadata)
                    .accessibilityIdentifier("libraryMetadataSaveButton")
                }
            }
            .navigationTitle("Edit Metadata")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") {
                        dismiss()
                    }
                }
            }
        }
    }

    private var canSave: Bool {
        !title.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
            && !author.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
            && !language.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
    }

    private func handleSave() {
        saveError = nil
        Task {
            let saved = await viewModel.updateMetadata(
                for: item,
                title: title,
                author: author,
                genre: genre,
                language: language,
                isbn: isbn,
                using: appState
            )
            await MainActor.run {
                if saved {
                    dismiss()
                } else {
                    saveError = viewModel.errorMessage ?? "Unable to save library metadata."
                }
            }
        }
    }
}

private struct LibraryIsbnMetadataSheet: View {
    let item: LibraryItem
    @ObservedObject var viewModel: LibraryViewModel
    @EnvironmentObject private var appState: AppState
    @Environment(\.dismiss) private var dismiss
    @State private var isbn: String
    @State private var previewMetadata: [String: JSONValue]?
    @State private var lookupError: String?

    init(item: LibraryItem, viewModel: LibraryViewModel) {
        self.item = item
        self.viewModel = viewModel
        _isbn = State(initialValue: item.isbn ?? "")
    }

    var body: some View {
        NavigationStack {
            Form {
                Section("Library Item") {
                    LabeledContent("Title", value: item.bookTitle)
                    LabeledContent("Author", value: item.author)
                }

                Section("ISBN") {
                    TextField("ISBN", text: $isbn)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                        .keyboardType(.numbersAndPunctuation)
                        .accessibilityIdentifier("libraryIsbnMetadataInput")
                    Button(action: handleLookup) {
                        if viewModel.isLookingUpIsbn {
                            ProgressView()
                        } else {
                            Label("Preview Metadata", systemImage: "magnifyingglass")
                        }
                    }
                    .disabled(trimmedIsbn.isEmpty || viewModel.isLookingUpIsbn || viewModel.isApplyingIsbn)
                    .accessibilityIdentifier("libraryIsbnPreviewButton")
                }

                if let lookupError {
                    Section {
                        Label(lookupError, systemImage: "exclamationmark.triangle.fill")
                            .foregroundStyle(.red)
                    }
                }

                Section("Preview") {
                    if let previewMetadata {
                        let rows = previewRows(from: previewMetadata)
                        if rows.isEmpty {
                            Text("No display metadata was returned for this ISBN.")
                                .foregroundStyle(.secondary)
                        } else {
                            ForEach(rows) { row in
                                LabeledContent(row.label, value: row.value)
                            }
                        }
                        DisclosureGroup("Raw Metadata") {
                            ForEach(previewMetadata.keys.sorted(), id: \.self) { key in
                                VStack(alignment: .leading, spacing: 3) {
                                    Text(key)
                                        .font(.caption)
                                        .foregroundStyle(.secondary)
                                    Text(metadataDisplayValue(previewMetadata[key]))
                                        .font(.caption)
                                        .textSelection(.enabled)
                                }
                            }
                        }
                    } else {
                        Text("Preview metadata before applying it to this library item.")
                            .foregroundStyle(.secondary)
                    }
                }

                Section {
                    Button(action: handleApply) {
                        if viewModel.isApplyingIsbn {
                            ProgressView()
                        } else {
                            Label("Apply ISBN Metadata", systemImage: "checkmark.circle")
                        }
                    }
                    .disabled(trimmedIsbn.isEmpty || viewModel.isLookingUpIsbn || viewModel.isApplyingIsbn)
                    .accessibilityIdentifier("libraryIsbnApplyButton")
                }
            }
            .navigationTitle("ISBN Metadata")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") {
                        dismiss()
                    }
                }
            }
        }
    }

    private var trimmedIsbn: String {
        isbn.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private func handleLookup() {
        lookupError = nil
        Task {
            let metadata = await viewModel.lookupIsbnMetadata(trimmedIsbn, using: appState)
            await MainActor.run {
                if let metadata {
                    previewMetadata = metadata
                    lookupError = nil
                } else {
                    previewMetadata = nil
                    lookupError = viewModel.errorMessage ?? "Unable to fetch metadata from ISBN."
                }
            }
        }
    }

    private func handleApply() {
        lookupError = nil
        Task {
            let applied = await viewModel.applyIsbn(trimmedIsbn, to: item, using: appState)
            await MainActor.run {
                if applied {
                    dismiss()
                } else {
                    lookupError = viewModel.errorMessage ?? "Unable to apply ISBN metadata."
                }
            }
        }
    }

    private func previewRows(from metadata: [String: JSONValue]) -> [LibraryIsbnMetadataPreviewRow] {
        [
            ("Title", metadataString(in: metadata, keys: ["book_title", "title", "book_name"])),
            ("Author", metadataString(in: metadata, keys: ["book_author", "author", "creator"])),
            ("Genre", metadataString(in: metadata, keys: ["book_genre", "genre"])),
            ("Language", metadataString(in: metadata, keys: ["book_language", "language"])),
            ("ISBN", metadataString(in: metadata, keys: ["isbn", "isbn_13", "isbn_10"])),
            ("Cover", metadataString(in: metadata, keys: ["book_cover_file", "cover_url"])),
            ("Summary", metadataString(in: metadata, keys: ["book_summary", "summary", "description"]))
        ]
        .compactMap { label, candidate in
            guard let value = candidate?.nonEmptyValue else { return nil }
            return LibraryIsbnMetadataPreviewRow(label: label, value: value)
        }
    }

    private func metadataString(in metadata: [String: JSONValue], keys: [String]) -> String? {
        for key in keys {
            if let value = metadata[key]?.stringValue?.nonEmptyValue {
                return value
            }
        }
        return nil
    }

    private func metadataDisplayValue(_ value: JSONValue?) -> String {
        guard let value else { return "null" }
        switch value {
        case let .string(string):
            return string
        case let .number(number):
            return String(number)
        case let .bool(boolean):
            return boolean ? "true" : "false"
        case let .array(values):
            return values.map { metadataDisplayValue($0) }.joined(separator: ", ")
        case let .object(object):
            return object.keys.sorted()
                .map { "\($0): \(metadataDisplayValue(object[$0]))" }
                .joined(separator: ", ")
        case .null:
            return "null"
        }
    }
}

private struct LibraryIsbnMetadataPreviewRow: Identifiable {
    let label: String
    let value: String

    var id: String { label }
}
#endif

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
