import SwiftUI

struct AppleBookCreateLifecycleModifier: ViewModifier {
    let creationOptionsLoadKey: String
    let recentJobs: [PipelineStatusResponse]
    let creationMode: AppleCreateMode
    let youtubeBaseDir: String
    let subtitleSourcePath: String
    let youtubeVideoPath: String
    let youtubeSubtitlePath: String
    let inputLanguage: AppleBookCreateLanguage
    let targetLanguage: AppleBookCreateLanguage
    let additionalTargetLanguages: String
    let enableLookupCache: Bool
    let subtitleShowOriginal: Bool
    @Binding var pendingEbookDelete: PipelineFileEntry?
    @Binding var pendingSubtitleDelete: SubtitleSourceEntry?
    @Binding var pendingTemplateDelete: CreationTemplateEntry?
    let onLoadCreateDependencies: () async -> Void
    let onRefreshHistoryDefaults: () -> Void
    let onYoutubeBaseDirChange: (String) -> Void
    let onSubtitleSourcePathChange: () -> Void
    let onYoutubeVideoPathChange: (String) -> Void
    let onYoutubeSubtitlePathChange: (String) -> Void
    let onLanguagePreferenceChange: () -> Void
    let onSubtitleShowOriginalChange: (Bool) -> Void
    let onDeleteEbook: (PipelineFileEntry) async -> Void
    let onDeleteSubtitleSource: (SubtitleSourceEntry) async -> Void
    let onDeleteCreationTemplate: (CreationTemplateEntry) async -> Void

    func body(content: Content) -> some View {
        content
            .task(id: creationOptionsLoadKey) {
                await onLoadCreateDependencies()
            }
            .onChange(of: recentJobs) { _, _ in
                onRefreshHistoryDefaults()
            }
            .onChange(of: creationMode) { _, _ in
                onRefreshHistoryDefaults()
            }
            .onChange(of: youtubeBaseDir) { _, newValue in
                onYoutubeBaseDirChange(newValue)
            }
            .onChange(of: subtitleSourcePath) { _, _ in
                onSubtitleSourcePathChange()
            }
            .onChange(of: youtubeVideoPath) { _, newValue in
                onYoutubeVideoPathChange(newValue)
            }
            .onChange(of: youtubeSubtitlePath) { _, newValue in
                onYoutubeSubtitlePathChange(newValue)
            }
            .onChange(of: inputLanguage) { _, _ in
                onLanguagePreferenceChange()
            }
            .onChange(of: targetLanguage) { _, _ in
                onLanguagePreferenceChange()
            }
            .onChange(of: additionalTargetLanguages) { _, _ in
                onLanguagePreferenceChange()
            }
            .onChange(of: enableLookupCache) { _, _ in
                onLanguagePreferenceChange()
            }
            .onChange(of: subtitleShowOriginal) { _, newValue in
                onSubtitleShowOriginalChange(newValue)
            }
            .modifier(
                AppleBookCreateEbookDeleteConfirmationModifier(
                    pendingDelete: $pendingEbookDelete,
                    onDelete: { entry in
                        Task { await onDeleteEbook(entry) }
                    }
                )
            )
            .modifier(
                AppleBookCreateSubtitleDeleteConfirmationModifier(
                    pendingDelete: $pendingSubtitleDelete,
                    onDelete: { entry in
                        Task { await onDeleteSubtitleSource(entry) }
                    }
                )
            )
            .modifier(
                AppleBookCreateTemplateDeleteConfirmationModifier(
                    pendingDelete: $pendingTemplateDelete,
                    onDelete: { template in
                        Task { await onDeleteCreationTemplate(template) }
                    }
                )
            )
    }
}

private struct AppleBookCreateEbookDeleteConfirmationModifier: ViewModifier {
    @Binding var pendingDelete: PipelineFileEntry?
    let onDelete: (PipelineFileEntry) -> Void

    func body(content: Content) -> some View {
        content.confirmationDialog(
            "Delete EPUB Source?",
            isPresented: isPresented,
            titleVisibility: .visible
        ) {
            if let pendingDelete {
                Button("Delete \(pendingDelete.name)", role: .destructive) {
                    onDelete(pendingDelete)
                }
                .accessibilityIdentifier("confirmDeletePipelineEbookButton")
            }
            Button("Cancel", role: .cancel) {
                pendingDelete = nil
            }
        } message: {
            if let pendingDelete {
                Text("This removes \(pendingDelete.name) from the backend books directory.")
            }
        }
    }

    private var isPresented: Binding<Bool> {
        Binding(
            get: { pendingDelete != nil },
            set: { isPresented in
                if !isPresented {
                    pendingDelete = nil
                }
            }
        )
    }
}

private struct AppleBookCreateSubtitleDeleteConfirmationModifier: ViewModifier {
    @Binding var pendingDelete: SubtitleSourceEntry?
    let onDelete: (SubtitleSourceEntry) -> Void

    func body(content: Content) -> some View {
        content.confirmationDialog(
            "Delete Subtitle Source?",
            isPresented: isPresented,
            titleVisibility: .visible
        ) {
            if let pendingDelete {
                Button("Delete \(pendingDelete.name)", role: .destructive) {
                    onDelete(pendingDelete)
                }
                .accessibilityIdentifier("confirmDeleteSubtitleSourceButton")
            }
            Button("Cancel", role: .cancel) {
                pendingDelete = nil
            }
        } message: {
            if let pendingDelete {
                Text("This removes \(pendingDelete.name) and any mirrored HTML transcript copies.")
            }
        }
    }

    private var isPresented: Binding<Bool> {
        Binding(
            get: { pendingDelete != nil },
            set: { isPresented in
                if !isPresented {
                    pendingDelete = nil
                }
            }
        )
    }
}

private struct AppleBookCreateTemplateDeleteConfirmationModifier: ViewModifier {
    @Binding var pendingDelete: CreationTemplateEntry?
    let onDelete: (CreationTemplateEntry) -> Void

    func body(content: Content) -> some View {
        content.confirmationDialog(
            "Delete Saved Template?",
            isPresented: isPresented,
            titleVisibility: .visible
        ) {
            if let pendingDelete {
                Button("Delete \(pendingDelete.displayName)", role: .destructive) {
                    onDelete(pendingDelete)
                }
                .accessibilityIdentifier("confirmDeleteCreationTemplateButton")
            }
            Button("Cancel", role: .cancel) {
                pendingDelete = nil
            }
        } message: {
            if let pendingDelete {
                Text("This removes \(pendingDelete.displayName) from saved creation templates.")
            }
        }
    }

    private var isPresented: Binding<Bool> {
        Binding(
            get: { pendingDelete != nil },
            set: { isPresented in
                if !isPresented {
                    pendingDelete = nil
                }
            }
        )
    }
}

extension AppleBookCreateView {
    var creationOptionsLoadKey: String {
        AppleBookCreateStorageKeys.loadScope(
            apiBaseURL: appState.configuration?.apiBaseURL,
            userID: appState.configuration?.userID,
            userRole: appState.configuration?.userRole
        )
    }

    var preferenceScope: AppleBookCreatePreferenceScope {
        AppleBookCreatePreferenceScope(
            baseKey: creationOptionsLoadKey,
            youtubeBaseDir: youtubeBaseDir
        )
    }

    func storedYoutubeSelectionPath(field: String) -> String? {
        preferenceScope.storedYoutubeSelectionPath(field: field)
    }

    func applyStoredYoutubeBaseDir() {
        guard let baseDir = preferenceScope.storedYoutubeBaseDir() else {
            return
        }
        youtubeBaseDir = baseDir
    }

    func persistYoutubeBaseDir(_ baseDir: String) {
        preferenceScope.persistYoutubeBaseDir(baseDir)
    }

    func persistYoutubeSelectionPath(_ path: String, field: String) {
        preferenceScope.persistYoutubeSelectionPath(path, field: field)
    }

    func applyStoredSubtitleShowOriginal() {
        guard let showOriginal = preferenceScope.storedSubtitleShowOriginal() else {
            return
        }
        subtitleShowOriginal = showOriginal
    }

    func persistSubtitleShowOriginal(_ value: Bool) {
        preferenceScope.persistSubtitleShowOriginal(value)
    }

    var youtubeLibraryLoadKey: String {
        preferenceScope.youtubeLibraryLoadKey
    }
}
