import SwiftUI

struct PlaybackSettingsView: View {
    @EnvironmentObject private var appState: AppState

    let sectionPicker: BrowseSectionPicker?
    let backTitle: String?
    let onBack: (() -> Void)?
    let usesDarkBackground: Bool

    @AppStorage("interactive.autoScaleEnabled") private var autoScaleEnabled: Bool = true
    @StateObject private var notificationManager = NotificationManager.shared
    @State private var isRequestingPermission = false
    @State private var isSendingTestNotification = false
    @State private var isSendingRichTestNotification = false
    @State private var showTestAlert = false
    @State private var testAlertMessage = ""
    @State private var backendRuntimeState: BackendRuntimeState = .idle

    init(sectionPicker: BrowseSectionPicker? = nil, backTitle: String? = nil, onBack: (() -> Void)? = nil, usesDarkBackground: Bool = false) {
        self.sectionPicker = sectionPicker
        self.backTitle = backTitle
        self.onBack = onBack
        self.usesDarkBackground = usesDarkBackground
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
                    .foregroundStyle(usesDarkBackground ? .white : .primary)
                    .padding(.horizontal)
            }
            List {
                SettingsConnectionSection(
                    apiHostLabel: apiHostLabel,
                    backendRuntimeState: backendRuntimeState,
                    sessionLabel: sessionLabel,
                    syncResumePositions: syncResumePositions,
                    signOut: signOut,
                    canSyncResumePositions: appState.resumeUserKey != nil,
                    canSignOut: appState.session != nil,
                    usesDarkBackground: usesDarkBackground
                )

                PlaybackSettingsSection(
                    autoScaleEnabled: $autoScaleEnabled,
                    usesDarkBackground: usesDarkBackground
                )

                AppChangelogSettingsSection(usesDarkBackground: usesDarkBackground)

                VoiceSettingsSection(usesDarkBackground: usesDarkBackground)

                #if os(iOS)
                NotificationSettingsSection(
                    notificationManager: notificationManager,
                    isRequestingPermission: isRequestingPermission,
                    isSendingTestNotification: isSendingTestNotification,
                    isSendingRichTestNotification: isSendingRichTestNotification,
                    requestNotificationPermission: requestNotificationPermission,
                    sendTestNotification: sendTestNotification,
                    sendRichTestNotification: sendRichTestNotification,
                    usesDarkBackground: usesDarkBackground
                )
                #endif
            }
            #if os(tvOS)
            .listStyle(.plain)
            #else
            .listStyle(.insetGrouped)
            .scrollContentBackground(usesDarkBackground ? .hidden : .automatic)
            #endif
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
        .background(usesDarkBackground ? AppTheme.lightBackground : Color.clear)
        #if os(iOS)
        .toolbarBackground(usesDarkBackground ? AppTheme.lightBackground : Color.clear, for: .navigationBar)
        .toolbarBackground(usesDarkBackground ? .visible : .automatic, for: .navigationBar)
        .toolbarColorScheme(usesDarkBackground ? .dark : nil, for: .navigationBar)
        #endif
        .task(id: apiHostLabel) {
            await refreshBackendRuntimeDescriptor()
        }
        #if os(iOS)
        .alert("Test Notification", isPresented: $showTestAlert) {
            Button("OK", role: .cancel) {}
        } message: {
            Text(testAlertMessage)
        }
        #endif
    }

    private var apiHostLabel: String {
        guard let url = appState.apiBaseURL else { return "Not configured" }
        let scheme = url.scheme?.nonEmptyValue ?? "https"
        let host = url.host?.nonEmptyValue ?? url.absoluteString
        return "\(scheme)://\(host)"
    }

    private var sessionLabel: String {
        guard let user = appState.session?.user else { return "Not signed in" }
        if let role = user.role.nonEmptyValue {
            return "\(user.username) · \(role)"
        }
        return user.username
    }

    private func syncResumePositions() {
        guard let resumeUserId = appState.resumeUserKey else { return }
        Task {
            await PlaybackResumeStore.shared.syncNow(userId: resumeUserId, aliases: appState.resumeUserAliases)
        }
    }

    private func signOut() {
        appState.signOut()
    }

    @MainActor
    private func refreshBackendRuntimeDescriptor() async {
        guard let apiBaseURL = appState.apiBaseURL else {
            backendRuntimeState = .unavailable("API URL missing")
            return
        }

        backendRuntimeState = .checking
        do {
            let client = APIClient(configuration: APIClientConfiguration(apiBaseURL: apiBaseURL))
            let descriptor = try await client.fetchBackendRuntimeDescriptor()
            let status = descriptor.status.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
            guard status == "ok" || status == "healthy" || status == "up" else {
                backendRuntimeState = .unavailable("Status \(descriptor.status)")
                return
            }
            backendRuntimeState = .verified(
                service: descriptor.service,
                version: descriptor.version,
                authContract: Self.authContractState(from: descriptor.auth),
                createContract: Self.createContractState(from: descriptor.creation),
                pipelineJobsContract: Self.pipelineJobsContractState(from: descriptor.pipelineJobs),
                pipelineMediaContract: Self.pipelineMediaContractState(from: descriptor.pipelineMedia),
                linguistContract: Self.linguistContractState(from: descriptor.linguist),
                libraryActionsContract: Self.libraryActionsContractState(from: descriptor.libraryActions),
                offlineExportsContract: Self.offlineExportsContractState(from: descriptor.offlineExports),
                playbackStateContract: Self.playbackStateContractState(from: descriptor.playbackState),
                notificationsContract: Self.notificationsContractState(from: descriptor.notifications)
            )
        } catch is CancellationError {
            return
        } catch {
            backendRuntimeState = .unavailable("Descriptor unavailable")
        }
    }

    private static func authContractState(
        from auth: BackendRuntimeDescriptorResponse.AuthContract?
    ) -> BackendRuntimeContractState {
        guard let auth else {
            return .unavailable
        }
        let expectedPaths: [(String, String?, String)] = [
            ("loginPath", auth.loginPath, AppleAuthRuntimeContract.loginPath),
            ("oauthPath", auth.oauthPath, AppleAuthRuntimeContract.oauthPath),
            ("sessionPath", auth.sessionPath, AppleAuthRuntimeContract.sessionPath),
            ("tokenTransport", auth.tokenTransport, "Authorization: Bearer"),
        ]
        let mismatches = expectedPaths.compactMap { key, actual, expected -> String? in
            let normalized = actual?.nonEmptyValue
            guard normalized == expected else {
                return "\(key)=\(normalized ?? "<missing>") expected \(expected)"
            }
            return nil
        }
        if !mismatches.isEmpty {
            return .mismatch(summary: mismatches.joined(separator: " · "))
        }
        return .ready(
            summary: "\(expectedPaths.count) endpoints · \(AppleAuthRuntimeContract.loginPath) · \(AppleAuthRuntimeContract.oauthPath) · \(AppleAuthRuntimeContract.sessionPath)"
        )
    }

    private static func createContractState(
        from creation: BackendRuntimeDescriptorResponse.CreationContract?
    ) -> BackendRuntimeContractState {
        guard let creation else {
            return .unavailable
        }
        let expectedPaths = [
            ("bookOptionsPath", creation.bookOptionsPath, AppleCreateRuntimeContract.bookOptionsPath),
            ("bookJobsPath", creation.bookJobsPath, AppleCreateRuntimeContract.bookJobsPath),
            ("pipelineFilesPath", creation.pipelineFilesPath, AppleCreateRuntimeContract.pipelineFilesPath),
            ("pipelineContentIndexPath", creation.pipelineContentIndexPath, AppleCreateRuntimeContract.pipelineContentIndexPath),
            ("pipelineUploadPath", creation.pipelineUploadPath, AppleCreateRuntimeContract.pipelineUploadPath),
            ("pipelineJobsPath", creation.pipelineJobsPath, AppleCreateRuntimeContract.pipelineJobsPath),
            ("pipelineIntakeStatusPath", creation.pipelineIntakeStatusPath, AppleCreateRuntimeContract.pipelineIntakeStatusPath),
            ("pipelineDefaultsPath", creation.pipelineDefaultsPath, AppleCreateRuntimeContract.pipelineDefaultsPath),
            ("pipelineLlmModelsPath", creation.pipelineLlmModelsPath, AppleCreateRuntimeContract.pipelineLlmModelsPath),
            ("pipelineSearchPath", creation.pipelineSearchPath, AppleCreateRuntimeContract.pipelineSearchPath),
            ("imageNodeAvailabilityPath", creation.imageNodeAvailabilityPath, AppleCreateRuntimeContract.imageNodeAvailabilityPath),
            ("audioVoicesPath", creation.audioVoicesPath, AppleCreateRuntimeContract.audioVoicesPath),
            ("subtitleSourcesPath", creation.subtitleSourcesPath, AppleCreateRuntimeContract.subtitleSourcesPath),
            ("subtitleDeleteSourcePath", creation.subtitleDeleteSourcePath, AppleCreateRuntimeContract.subtitleDeleteSourcePath),
            ("subtitleModelsPath", creation.subtitleModelsPath, AppleCreateRuntimeContract.subtitleModelsPath),
            ("subtitleJobsPath", creation.subtitleJobsPath, AppleCreateRuntimeContract.subtitleJobsPath),
            ("youtubeLibraryPath", creation.youtubeLibraryPath, AppleCreateRuntimeContract.youtubeLibraryPath),
            ("youtubeSubtitleStreamsPath", creation.youtubeSubtitleStreamsPath, AppleCreateRuntimeContract.youtubeSubtitleStreamsPath),
            ("youtubeExtractSubtitlesPath", creation.youtubeExtractSubtitlesPath, AppleCreateRuntimeContract.youtubeExtractSubtitlesPath),
            ("subtitleTvMetadataPreviewPath", creation.subtitleTvMetadataPreviewPath, AppleCreateRuntimeContract.subtitleTvMetadataPreviewPath),
            ("subtitleTvMetadataCacheClearPath", creation.subtitleTvMetadataCacheClearPath, AppleCreateRuntimeContract.subtitleTvMetadataCacheClearPath),
            ("youtubeMetadataPreviewPath", creation.youtubeMetadataPreviewPath, AppleCreateRuntimeContract.youtubeMetadataPreviewPath),
            ("youtubeMetadataCacheClearPath", creation.youtubeMetadataCacheClearPath, AppleCreateRuntimeContract.youtubeMetadataCacheClearPath),
            ("youtubeDubPath", creation.youtubeDubPath, AppleCreateRuntimeContract.youtubeDubPath),
            ("acquisitionProvidersPath", creation.acquisitionProvidersPath, AppleCreateRuntimeContract.acquisitionProvidersPath),
            ("acquisitionDiscoverPath", creation.acquisitionDiscoverPath, AppleCreateRuntimeContract.acquisitionDiscoverPath),
            ("acquisitionAcquirePath", creation.acquisitionAcquirePath, AppleCreateRuntimeContract.acquisitionAcquirePath),
            ("acquisitionArtifactPreparePathTemplate", creation.acquisitionArtifactPreparePathTemplate, AppleCreateRuntimeContract.acquisitionArtifactPreparePathTemplate),
            ("acquisitionJobsPath", creation.acquisitionJobsPath, AppleCreateRuntimeContract.acquisitionJobsPath),
            ("acquisitionJobPathTemplate", creation.acquisitionJobPathTemplate, AppleCreateRuntimeContract.acquisitionJobPathTemplate),
            ("templateListPath", creation.templateListPath, AppleCreateRuntimeContract.templateListPath),
            ("templatePathTemplate", creation.templatePathTemplate, AppleCreateRuntimeContract.templatePathTemplate),
        ]
        let mismatches = expectedPaths.compactMap { key, actual, expected -> String? in
            let normalized = actual?.nonEmptyValue
            guard normalized == expected else {
                return "\(key)=\(normalized ?? "<missing>") expected \(expected)"
            }
            return nil
        }
        if !mismatches.isEmpty {
            return .mismatch(summary: mismatches.joined(separator: " · "))
        }
        return .ready(
            summary: "\(expectedPaths.count) endpoints · \(AppleCreateRuntimeContract.bookOptionsPath) · \(AppleCreateRuntimeContract.bookJobsPath) · \(AppleCreateRuntimeContract.pipelineFilesPath) · \(AppleCreateRuntimeContract.pipelineDefaultsPath) · \(AppleCreateRuntimeContract.pipelineLlmModelsPath) · \(AppleCreateRuntimeContract.pipelineSearchPath) · \(AppleCreateRuntimeContract.audioVoicesPath) · \(AppleCreateRuntimeContract.subtitleDeleteSourcePath) · \(AppleCreateRuntimeContract.subtitleJobsPath) · \(AppleCreateRuntimeContract.youtubeDubPath) · \(AppleCreateRuntimeContract.acquisitionProvidersPath) · \(AppleCreateRuntimeContract.acquisitionDiscoverPath) · \(AppleCreateRuntimeContract.acquisitionAcquirePath) · \(AppleCreateRuntimeContract.acquisitionArtifactPreparePathTemplate) · \(AppleCreateRuntimeContract.acquisitionJobsPath) · \(AppleCreateRuntimeContract.acquisitionJobPathTemplate) · \(AppleCreateRuntimeContract.templateListPath)"
        )
    }

    private static func libraryActionsContractState(
        from libraryActions: BackendRuntimeDescriptorResponse.LibraryActionsContract?
    ) -> BackendRuntimeContractState {
        guard let libraryActions else {
            return .unavailable
        }
        let expectedPaths = [
            ("itemsPath", libraryActions.itemsPath, AppleLibraryRuntimeContract.itemsPath),
            ("itemMetadataPathTemplate", libraryActions.itemMetadataPathTemplate, AppleLibraryRuntimeContract.itemPathTemplate),
            ("sourceUploadPathTemplate", libraryActions.sourceUploadPathTemplate, AppleLibraryRuntimeContract.sourceUploadPathTemplate),
            ("movePathTemplate", libraryActions.movePathTemplate, AppleLibraryRuntimeContract.movePathTemplate),
            ("removePathTemplate", libraryActions.removePathTemplate, AppleLibraryRuntimeContract.removePathTemplate),
            ("isbnLookupPath", libraryActions.isbnLookupPath, AppleLibraryRuntimeContract.isbnLookupPath),
            ("isbnApplyPathTemplate", libraryActions.isbnApplyPathTemplate, AppleLibraryRuntimeContract.isbnApplyPathTemplate),
            ("metadataEnrichPathTemplate", libraryActions.metadataEnrichPathTemplate, AppleLibraryRuntimeContract.metadataEnrichPathTemplate),
        ]
        let mismatches = expectedPaths.compactMap { key, actual, expected -> String? in
            let normalized = actual.nonEmptyValue
            guard normalized == expected else {
                return "\(key)=\(normalized ?? "<missing>") expected \(expected)"
            }
            return nil
        }
        if !mismatches.isEmpty {
            return .mismatch(summary: mismatches.joined(separator: " · "))
        }
        return .ready(
            summary: "\(expectedPaths.count) endpoints · \(AppleLibraryRuntimeContract.itemsPath) · \(AppleLibraryRuntimeContract.movePathTemplate) · \(AppleLibraryRuntimeContract.removePathTemplate) · \(AppleLibraryRuntimeContract.sourceUploadPathTemplate) · \(AppleLibraryRuntimeContract.isbnLookupPath) · \(AppleLibraryRuntimeContract.metadataEnrichPathTemplate)"
        )
    }

    private static func pipelineJobsContractState(
        from pipelineJobs: BackendRuntimeDescriptorResponse.PipelineJobsContract?
    ) -> BackendRuntimeContractState {
        guard let pipelineJobs else {
            return .unavailable
        }
        let expectedPaths = [
            ("listPath", pipelineJobs.listPath, ApplePipelineJobsRuntimeContract.listPath),
            ("statusPathTemplate", pipelineJobs.statusPathTemplate, ApplePipelineJobsRuntimeContract.statusPathTemplate),
            ("eventStreamPathTemplate", pipelineJobs.eventStreamPathTemplate, ApplePipelineJobsRuntimeContract.eventStreamPathTemplate),
            ("deletePathTemplate", pipelineJobs.deletePathTemplate, ApplePipelineJobsRuntimeContract.deletePathTemplate),
            ("restartPathTemplate", pipelineJobs.restartPathTemplate, ApplePipelineJobsRuntimeContract.restartPathTemplate),
            ("cacheBusterQuery", pipelineJobs.cacheBusterQuery, "ts"),
        ]
        let mismatches = expectedPaths.compactMap { key, actual, expected -> String? in
            let normalized = actual.nonEmptyValue
            guard normalized == expected else {
                return "\(key)=\(normalized ?? "<missing>") expected \(expected)"
            }
            return nil
        }
        if !mismatches.isEmpty {
            return .mismatch(summary: mismatches.joined(separator: " · "))
        }
        return .ready(
            summary: "\(expectedPaths.count) endpoints · \(ApplePipelineJobsRuntimeContract.listPath) · \(ApplePipelineJobsRuntimeContract.statusPathTemplate) · \(ApplePipelineJobsRuntimeContract.eventStreamPathTemplate) · \(ApplePipelineJobsRuntimeContract.restartPathTemplate)"
        )
    }

    private static func offlineExportsContractState(
        from offlineExports: BackendRuntimeDescriptorResponse.OfflineExportContract?
    ) -> BackendRuntimeContractState {
        guard let offlineExports else {
            return .unavailable
        }
        let expectedPaths = [
            ("createPath", offlineExports.createPath, AppleOfflineExportRuntimeContract.createPath),
            ("downloadPathTemplate", offlineExports.downloadPathTemplate, AppleOfflineExportRuntimeContract.downloadPathTemplate),
        ]
        var mismatches = expectedPaths.compactMap { key, actual, expected -> String? in
            let normalized = actual.nonEmptyValue
            guard normalized == expected else {
                return "\(key)=\(normalized ?? "<missing>") expected \(expected)"
            }
            return nil
        }
        if offlineExports.sourceKinds != AppleOfflineExportRuntimeContract.supportedSourceKinds {
            mismatches.append(
                "sourceKinds=\(offlineExports.sourceKinds.joined(separator: ",")) expected \(AppleOfflineExportRuntimeContract.supportedSourceKinds.joined(separator: ","))"
            )
        }
        if offlineExports.playerTypes != [AppleOfflineExportRuntimeContract.playerType] {
            mismatches.append(
                "playerTypes=\(offlineExports.playerTypes.joined(separator: ",")) expected \(AppleOfflineExportRuntimeContract.playerType)"
            )
        }
        if !mismatches.isEmpty {
            return .mismatch(summary: mismatches.joined(separator: " · "))
        }
        return .ready(
            summary: "\(expectedPaths.count) endpoints · \(AppleOfflineExportRuntimeContract.createPath) · \(AppleOfflineExportRuntimeContract.downloadPathTemplate) · \(AppleOfflineExportRuntimeContract.playerType)"
        )
    }

    private static func pipelineMediaContractState(
        from pipelineMedia: BackendRuntimeDescriptorResponse.PipelineMediaContract?
    ) -> BackendRuntimeContractState {
        guard let pipelineMedia else {
            return .unavailable
        }
        let expectedPaths = [
            ("jobMediaPathTemplate", pipelineMedia.jobMediaPathTemplate, ApplePipelineMediaRuntimeContract.jobMediaPathTemplate),
            ("jobMediaLivePathTemplate", pipelineMedia.jobMediaLivePathTemplate, ApplePipelineMediaRuntimeContract.jobMediaLivePathTemplate),
            ("jobMediaChunkPathTemplate", pipelineMedia.jobMediaChunkPathTemplate, ApplePipelineMediaRuntimeContract.jobMediaChunkPathTemplate),
            ("libraryMediaPathTemplate", pipelineMedia.libraryMediaPathTemplate, ApplePipelineMediaRuntimeContract.libraryMediaPathTemplate),
            ("libraryMediaFilePathTemplate", pipelineMedia.libraryMediaFilePathTemplate, ApplePipelineMediaRuntimeContract.libraryMediaFilePathTemplate),
            ("jobTimingPathTemplate", pipelineMedia.jobTimingPathTemplate, ApplePipelineMediaRuntimeContract.jobTimingPathTemplate),
            ("subtitleTvMetadataPathTemplate", pipelineMedia.subtitleTvMetadataPathTemplate, ApplePipelineMediaRuntimeContract.subtitleTvMetadataPathTemplate),
            ("youtubeVideoMetadataPathTemplate", pipelineMedia.youtubeVideoMetadataPathTemplate, ApplePipelineMediaRuntimeContract.youtubeVideoMetadataPathTemplate),
        ]
        let mismatches = expectedPaths.compactMap { key, actual, expected -> String? in
            let normalized = actual.nonEmptyValue
            guard normalized == expected else {
                return "\(key)=\(normalized ?? "<missing>") expected \(expected)"
            }
            return nil
        }
        if !mismatches.isEmpty {
            return .mismatch(summary: mismatches.joined(separator: " · "))
        }
        return .ready(
            summary: "\(expectedPaths.count) endpoints · \(ApplePipelineMediaRuntimeContract.jobMediaPathTemplate) · \(ApplePipelineMediaRuntimeContract.jobMediaLivePathTemplate) · \(ApplePipelineMediaRuntimeContract.libraryMediaPathTemplate) · \(ApplePipelineMediaRuntimeContract.jobTimingPathTemplate)"
        )
    }

    private static func linguistContractState(
        from linguist: BackendRuntimeDescriptorResponse.LinguistContract?
    ) -> BackendRuntimeContractState {
        guard let linguist else {
            return .unavailable
        }
        let expectedPaths = [
            ("assistantLookupPath", linguist.assistantLookupPath, AppleLinguistRuntimeContract.assistantLookupPath),
            ("lookupCachePathTemplate", linguist.lookupCachePathTemplate, AppleLinguistRuntimeContract.lookupCachePathTemplate),
            ("lookupCacheWordPathTemplate", linguist.lookupCacheWordPathTemplate, AppleLinguistRuntimeContract.lookupCacheWordPathTemplate),
            ("lookupCacheBulkPathTemplate", linguist.lookupCacheBulkPathTemplate, AppleLinguistRuntimeContract.lookupCacheBulkPathTemplate),
            ("lookupCacheSummaryPathTemplate", linguist.lookupCacheSummaryPathTemplate, AppleLinguistRuntimeContract.lookupCacheSummaryPathTemplate),
            ("audioSynthesisPath", linguist.audioSynthesisPath, AppleLinguistRuntimeContract.audioSynthesisPath),
        ]
        let mismatches = expectedPaths.compactMap { key, actual, expected -> String? in
            let normalized = actual.nonEmptyValue
            guard normalized == expected else {
                return "\(key)=\(normalized ?? "<missing>") expected \(expected)"
            }
            return nil
        }
        if !mismatches.isEmpty {
            return .mismatch(summary: mismatches.joined(separator: " · "))
        }
        return .ready(
            summary: "\(expectedPaths.count) endpoints · \(AppleLinguistRuntimeContract.assistantLookupPath) · \(AppleLinguistRuntimeContract.lookupCachePathTemplate) · \(AppleLinguistRuntimeContract.audioSynthesisPath)"
        )
    }

    private static func playbackStateContractState(
        from playbackState: BackendRuntimeDescriptorResponse.PlaybackStateContract?
    ) -> BackendRuntimeContractState {
        guard let playbackState else {
            return .unavailable
        }
        let expectedPaths: [(String, String?, String)] = [
            (
                "bookmarksPathTemplate",
                playbackState.bookmarksPathTemplate,
                ApplePlaybackStateRuntimeContract.bookmarksPathTemplate
            ),
            (
                "bookmarkDeletePathTemplate",
                playbackState.bookmarkDeletePathTemplate,
                ApplePlaybackStateRuntimeContract.bookmarkDeletePathTemplate
            ),
            (
                "readingBedsPath",
                playbackState.readingBedsPath,
                ApplePlaybackStateRuntimeContract.readingBedsPath
            ),
            ("resumeListPath", playbackState.resumeListPath, ApplePlaybackStateRuntimeContract.resumeListPath),
            ("resumePathTemplate", playbackState.resumePathTemplate, ApplePlaybackStateRuntimeContract.resumePathTemplate),
            ("resumeFilterQuery", playbackState.resumeFilterQuery, ApplePlaybackStateRuntimeContract.resumeFilterQuery),
        ]
        let mismatches = expectedPaths.compactMap { key, actual, expected -> String? in
            let normalized = actual?.nonEmptyValue
            guard normalized == expected else {
                return "\(key)=\(normalized ?? "<missing>") expected \(expected)"
            }
            return nil
        }
        if !mismatches.isEmpty {
            return .mismatch(summary: mismatches.joined(separator: " · "))
        }
        return .ready(
            summary: "\(expectedPaths.count) endpoints · \(ApplePlaybackStateRuntimeContract.bookmarksPathTemplate) · \(ApplePlaybackStateRuntimeContract.readingBedsPath) · \(ApplePlaybackStateRuntimeContract.resumeListPath) · \(ApplePlaybackStateRuntimeContract.resumeFilterQuery)"
        )
    }

    private static func notificationsContractState(
        from notifications: BackendRuntimeDescriptorResponse.NotificationsContract?
    ) -> BackendRuntimeContractState {
        guard let notifications else {
            return .unavailable
        }
        let expectedPaths = [
            ("deviceRegistrationPath", notifications.deviceRegistrationPath, AppleNotificationsRuntimeContract.deviceRegistrationPath),
            ("deviceRemovalPathTemplate", notifications.deviceRemovalPathTemplate, AppleNotificationsRuntimeContract.deviceRemovalPathTemplate),
            ("testPath", notifications.testPath, AppleNotificationsRuntimeContract.testPath),
            ("richTestPath", notifications.richTestPath, AppleNotificationsRuntimeContract.richTestPath),
            ("preferencesPath", notifications.preferencesPath, AppleNotificationsRuntimeContract.preferencesPath),
        ]
        let mismatches = expectedPaths.compactMap { key, actual, expected -> String? in
            let normalized = actual.nonEmptyValue
            guard normalized == expected else {
                return "\(key)=\(normalized ?? "<missing>") expected \(expected)"
            }
            return nil
        }
        if !mismatches.isEmpty {
            return .mismatch(summary: mismatches.joined(separator: " · "))
        }
        return .ready(
            summary: "\(expectedPaths.count) endpoints · \(AppleNotificationsRuntimeContract.deviceRegistrationPath) · \(AppleNotificationsRuntimeContract.testPath) · \(AppleNotificationsRuntimeContract.preferencesPath)"
        )
    }

    #if os(iOS)
    private func requestNotificationPermission() {
        isRequestingPermission = true
        Task {
            _ = await notificationManager.requestAuthorization()
            isRequestingPermission = false
        }
    }

    private func sendTestNotification() {
        guard let config = appState.configuration else {
            testAlertMessage = "Not signed in. Please log in first."
            showTestAlert = true
            return
        }

        isSendingTestNotification = true
        Task {
            do {
                let result = try await notificationManager.sendTestNotification(using: config)
                if result.sent > 0 {
                    testAlertMessage = "Test notification sent to \(result.sent) device(s)!"
                } else if let message = result.message {
                    testAlertMessage = message
                } else {
                    testAlertMessage = "No devices registered. Make sure notifications are enabled on this device."
                }
            } catch {
                testAlertMessage = "Failed to send: \(error.localizedDescription)"
            }
            isSendingTestNotification = false
            showTestAlert = true
        }
    }

    private func sendRichTestNotification() {
        guard let config = appState.configuration else {
            testAlertMessage = "Not signed in. Please log in first."
            showTestAlert = true
            return
        }

        isSendingRichTestNotification = true
        Task {
            do {
                let result = try await notificationManager.sendRichTestNotification(
                    using: config,
                    title: "Sample Book Title",
                    subtitle: "Sample Author Name"
                )
                if result.sent > 0 {
                    testAlertMessage = "Rich notification sent to \(result.sent) device(s)!"
                } else if let message = result.message {
                    testAlertMessage = message
                } else {
                    testAlertMessage = "No devices registered. Make sure notifications are enabled on this device."
                }
            } catch {
                testAlertMessage = "Failed to send: \(error.localizedDescription)"
            }
            isSendingRichTestNotification = false
            showTestAlert = true
        }
    }
    #endif
}
