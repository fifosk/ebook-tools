import Foundation
import SwiftUI

struct AppleBookCreateYoutubeSourceControls: View {
    @Binding var youtubeBaseDir: String
    @Binding var youtubeVideoPath: String
    @Binding var youtubeSubtitlePath: String
    @Binding var youtubeSubtitleExtractionLanguages: String
    let acquisitionProviders: [AcquisitionProviderEntry]
    let acquisitionDefaultProviderIds: [String: [String]]
    let acquisitionDiscovery: AcquisitionDiscoveryResponse?
    let videoDiscoveryState: [String: JSONValue]?
    let downloadStationJob: AcquisitionJobStatusResponse?
    let youtubeLibrary: YoutubeNasLibraryResponse?
    let youtubeInlineSubtitleStreams: [YoutubeInlineSubtitleStream]
    let isLoadingAcquisitionDiscovery: Bool
    let isPreparingAcquisitionCandidate: Bool
    let isLoadingYoutubeLibrary: Bool
    let isLoadingYoutubeSubtitleStreams: Bool
    let isExtractingYoutubeSubtitles: Bool
    let isSubmittingDownloadStation: Bool
    let isPollingDownloadStation: Bool
    let acquisitionDiscoveryErrorMessage: String?
    let downloadStationMessage: String?
    let downloadStationErrorMessage: String?
    let acquisitionProvidersErrorMessage: String?
    let youtubeSearchUnavailableMessage: String?
    let isYoutubeSearchAvailable: Bool
    let downloadStationUnavailableMessage: String?
    let isDownloadStationAvailable: Bool
    let youtubeLibraryErrorMessage: String?
    let youtubeSubtitleExtractionMessage: String?
    let youtubeSubtitleExtractionErrorMessage: String?
    let onRefreshYoutubeLibrary: () -> Void
    let onSearchYoutubeAcquisitionDiscovery: (String, String) -> Void
    let onSelectYoutubeAcquisitionCandidate: (AcquisitionCandidate, String, String) -> Void
    let onSubmitDownloadStation: (String?, String?, String?, Bool) -> Void
    let onPollDownloadStation: () -> Void
    let onInspectYoutubeSubtitles: () -> Void
    let onExtractYoutubeSubtitles: () -> Void
    @State private var videoDiscoveryQuery = ""
    @State private var videoDiscoveryProvider = AppleBookCreatePresentation.defaultVideoDiscoveryProviderID
    @State private var hasUserSelectedVideoDiscoveryProvider = false
    @State private var didApplyBackendVideoDiscoveryDefault = false
    @State private var appliedVideoDiscoveryStateSignature = ""
    @State private var downloadStationSourceURI = ""
    @State private var downloadStationCandidate: AcquisitionCandidate?
    @State private var downloadStationDestination = ""
    @State private var downloadStationConfirmed = false

    var body: some View {
        TextField("NAS directory", text: $youtubeBaseDir)
            .textInputAutocapitalization(.never)
            .autocorrectionDisabled()
            .accessibilityIdentifier("createYoutubeBaseDirField")
            .task {
                applyVideoDiscoveryStateIfNeeded()
                applyPreferredVideoDiscoveryProviderIfNeeded(preferredVideoDiscoveryProviderID)
            }
            .onChange(of: videoDiscoveryStateSignature) { _, _ in
                applyVideoDiscoveryStateIfNeeded()
            }
            .onChange(of: preferredVideoDiscoveryProviderID ?? "") { _, providerID in
                applyPreferredVideoDiscoveryProviderIfNeeded(providerID.nonEmptyValue)
            }
            .onChange(of: videoDiscoveryProviderOptionsSignature) { _, _ in
                applyPreferredVideoDiscoveryProviderIfNeeded(preferredVideoDiscoveryProviderID)
            }
        if let baseDir = youtubeLibrary?.baseDir,
           !baseDir.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            Text("Base path: \(baseDir)")
                .font(.footnote)
                .foregroundStyle(.secondary)
                .accessibilityIdentifier("createYoutubeBaseDirLabel")
        }
        if !youtubeVideos.isEmpty {
            Picker("NAS video", selection: $youtubeVideoPath) {
                Text("Manual path").tag("")
                if shouldShowCurrentYoutubeVideoPath {
                    Text(youtubeVideoPath).tag(youtubeVideoPath)
                }
                ForEach(youtubeVideos, id: \.path) { video in
                    Text(AppleBookCreatePresentation.youtubeVideoLabel(video)).tag(video.path)
                }
            }
            .accessibilityIdentifier("createYoutubeNasVideoPicker")
            .onChange(of: youtubeVideoPath) { _, newValue in
                applyYoutubeVideoSelection(newValue)
            }
        }
        AppleBookCreateSourceActionRow(
            title: "Refresh Videos",
            busyTitle: "Refreshing Videos",
            systemImage: "arrow.clockwise",
            isBusy: isLoadingYoutubeLibrary,
            isDisabled: isLoadingYoutubeLibrary,
            buttonIdentifier: "createYoutubeRefreshNasVideosButton",
            progressIdentifier: "createYoutubeNasVideosProgress",
            action: onRefreshYoutubeLibrary
        )
        AppleBookCreateYoutubeDiscoveryControls(
            videoDiscoveryQuery: $videoDiscoveryQuery,
            videoDiscoveryProvider: videoDiscoveryProviderBinding,
            downloadStationSourceURI: $downloadStationSourceURI,
            downloadStationCandidate: $downloadStationCandidate,
            videoDiscoveryProviderOptions: videoDiscoveryProviderOptions,
            videoDiscoveryQueryPlaceholder: videoDiscoveryQueryPlaceholder,
            videoDiscoveryCandidates: videoDiscoveryCandidates,
            videoDiscoveryPolicyNotes: videoDiscoveryPolicyNotes,
            isLoadingAcquisitionDiscovery: isLoadingAcquisitionDiscovery,
            isPreparingAcquisitionCandidate: isPreparingAcquisitionCandidate,
            isSelectedVideoDiscoveryProviderAvailable: isSelectedVideoDiscoveryProviderAvailable,
            acquisitionDiscoveryErrorMessage: acquisitionDiscoveryErrorMessage,
            acquisitionProvidersErrorMessage: acquisitionProvidersErrorMessage,
            selectedVideoDiscoveryProviderUnavailableMessage: selectedVideoDiscoveryProviderUnavailableMessage,
            shouldShowNoVideoDiscoveryCandidatesMessage: shouldShowNoVideoDiscoveryCandidatesMessage,
            noVideoDiscoveryCandidatesMessage: noVideoDiscoveryCandidatesMessage,
            onSearchYoutubeAcquisitionDiscovery: onSearchYoutubeAcquisitionDiscovery,
            onSelectYoutubeAcquisitionCandidate: onSelectYoutubeAcquisitionCandidate
        )
        AppleBookCreateYoutubeDownloadStationControls(
            downloadStationJob: downloadStationJob,
            downloadStationMessage: downloadStationMessage,
            downloadStationErrorMessage: downloadStationErrorMessage,
            downloadStationUnavailableMessage: downloadStationUnavailableMessage,
            isDownloadStationAvailable: isDownloadStationAvailable,
            isSubmittingDownloadStation: isSubmittingDownloadStation,
            isPollingDownloadStation: isPollingDownloadStation,
            downloadStationSourceURI: $downloadStationSourceURI,
            downloadStationCandidate: $downloadStationCandidate,
            downloadStationDestination: $downloadStationDestination,
            downloadStationConfirmed: $downloadStationConfirmed,
            videoDiscoveryProvider: $videoDiscoveryProvider,
            videoDiscoveryQuery: $videoDiscoveryQuery,
            onSubmitDownloadStation: onSubmitDownloadStation,
            onPollDownloadStation: onPollDownloadStation
        )
        if let youtubeLibraryErrorMessage {
            Text(youtubeLibraryErrorMessage)
                .font(.footnote)
                .foregroundStyle(.secondary)
                .accessibilityIdentifier("createYoutubeNasVideosMessage")
        }
        TextField("Video path", text: $youtubeVideoPath)
            .textInputAutocapitalization(.never)
            .autocorrectionDisabled()
            .accessibilityIdentifier("createYoutubeVideoPathField")
        AppleBookCreateYoutubeEmbeddedSubtitleControls(
            youtubeSubtitleExtractionLanguages: $youtubeSubtitleExtractionLanguages,
            youtubeInlineSubtitleStreams: youtubeInlineSubtitleStreams,
            hasYoutubeVideoPath: hasYoutubeVideoPath,
            isLoadingYoutubeSubtitleStreams: isLoadingYoutubeSubtitleStreams,
            isExtractingYoutubeSubtitles: isExtractingYoutubeSubtitles,
            youtubeSubtitleExtractionMessage: youtubeSubtitleExtractionMessage,
            youtubeSubtitleExtractionErrorMessage: youtubeSubtitleExtractionErrorMessage,
            onInspectYoutubeSubtitles: onInspectYoutubeSubtitles,
            onExtractYoutubeSubtitles: onExtractYoutubeSubtitles
        )
        if !youtubeSubtitleEntries.isEmpty {
            Picker("Subtitle", selection: $youtubeSubtitlePath) {
                Text("Manual path").tag("")
                if shouldShowCurrentYoutubeSubtitlePath {
                    Text(youtubeSubtitlePath).tag(youtubeSubtitlePath)
                }
                ForEach(youtubeSubtitleEntries, id: \.path) { subtitle in
                    Text(AppleBookCreatePresentation.youtubeSubtitleLabel(subtitle)).tag(subtitle.path)
                }
            }
            .accessibilityIdentifier("createYoutubeNasSubtitlePicker")
        }
        TextField("Subtitle path", text: $youtubeSubtitlePath)
            .textInputAutocapitalization(.never)
            .autocorrectionDisabled()
            .accessibilityIdentifier("createYoutubeSubtitlePathField")
    }

    private var youtubeVideos: [YoutubeNasVideoEntry] {
        youtubeLibrary?.videos ?? []
    }

    private var videoDiscoveryCandidates: [AcquisitionCandidate] {
        AppleBookCreatePresentation.videoDiscoveryCandidates(
            from: acquisitionDiscovery,
            providerID: videoDiscoveryProvider,
            providers: acquisitionProviders
        )
    }

    private var shouldShowNoVideoDiscoveryCandidatesMessage: Bool {
        acquisitionDiscovery != nil && videoDiscoveryCandidates.isEmpty && !isLoadingAcquisitionDiscovery
    }

    private var videoDiscoveryPolicyNotes: [String] {
        AppleBookCreatePresentation.discoveryPolicyNotes(from: acquisitionDiscovery)
    }

    private var videoDiscoveryQueryPlaceholder: String {
        AppleBookCreatePresentation.videoDiscoveryQueryPlaceholder(providerID: videoDiscoveryProvider)
    }

    private var noVideoDiscoveryCandidatesMessage: String {
        AppleBookCreatePresentation.noVideoDiscoveryCandidatesMessage(providerID: videoDiscoveryProvider)
    }

    private var selectedVideoDiscoveryProvider: AcquisitionProviderEntry? {
        videoDiscoveryProviderEntry(for: videoDiscoveryProvider)
    }

    private var videoDiscoveryProviderOptions: [AppleBookCreateVideoDiscoveryProviderOption] {
        AppleBookCreatePresentation.videoDiscoveryProviderOptions(
            from: acquisitionProviders,
            defaultProviderIds: acquisitionDefaultProviderIds
        )
    }

    private var preferredVideoDiscoveryProviderID: String? {
        AppleBookCreatePresentation.defaultDiscoveryProviderID(
            for: "video",
            defaultProviderIds: acquisitionDefaultProviderIds,
            optionIds: videoDiscoveryProviderOptions.map(\.id),
            availableOptionIds: videoDiscoveryProviderOptions.filter(\.available).map(\.id),
            providers: acquisitionProviders,
            fallback: "nas_video"
        )
    }

    private var videoDiscoveryProviderOptionsSignature: String {
        videoDiscoveryProviderOptions
            .map { "\($0.id):\($0.available)" }
            .joined(separator: "|")
    }

    private var videoDiscoveryStateSignature: String {
        [
            videoDiscoveryStateText("selected_provider"),
            videoDiscoveryStateText("provider"),
            videoDiscoveryStateText("query")
        ]
        .map { $0 ?? "" }
        .joined(separator: "\u{1f}")
    }

    private var videoDiscoveryProviderBinding: Binding<String> {
        Binding(
            get: { videoDiscoveryProvider },
            set: { providerID in
                hasUserSelectedVideoDiscoveryProvider = true
                videoDiscoveryProvider = providerID
            }
        )
    }

    private func applyVideoDiscoveryStateIfNeeded() {
        let signature = videoDiscoveryStateSignature
        guard !signature.isEmpty, appliedVideoDiscoveryStateSignature != signature else {
            return
        }
        appliedVideoDiscoveryStateSignature = signature
        if let provider = videoDiscoveryStateText("selected_provider") ?? videoDiscoveryStateText("provider") {
            videoDiscoveryProvider = provider
            hasUserSelectedVideoDiscoveryProvider = true
        }
        if let query = videoDiscoveryStateText("query") {
            videoDiscoveryQuery = query
        }
    }

    private func videoDiscoveryStateText(_ key: String) -> String? {
        videoDiscoveryState?[key]?.stringValue?
            .trimmingCharacters(in: .whitespacesAndNewlines)
            .nonEmptyValue
    }

    private var isSelectedVideoDiscoveryProviderAvailable: Bool {
        if let option = videoDiscoveryProviderOptions.first(where: { $0.id == videoDiscoveryProvider }) {
            return option.available
        }
        if videoDiscoveryProvider == "youtube_search", !isYoutubeSearchAvailable {
            return false
        }
        if videoDiscoveryProvider == "newznab_torznab" {
            return selectedVideoDiscoveryProvider?.available == true
        }
        if !acquisitionProviders.isEmpty, selectedVideoDiscoveryProvider == nil {
            return false
        }
        return selectedVideoDiscoveryProvider?.available != false
    }

    private var selectedVideoDiscoveryProviderUnavailableMessage: String? {
        if !AppleBookCreatePresentation.isDefaultVideoDiscoveryProviderID(videoDiscoveryProvider),
           !acquisitionProviders.isEmpty,
           selectedVideoDiscoveryProvider == nil {
            return "\(selectedVideoDiscoveryProviderLabel) is unavailable on this backend. Choose another discovery source."
        }
        return AppleBookCreatePresentation.videoDiscoveryProviderUnavailableMessage(
            for: selectedVideoDiscoveryProvider,
            youtubeSearchUnavailableMessage: youtubeSearchUnavailableMessage
        )
    }

    private var selectedVideoDiscoveryProviderLabel: String {
        videoDiscoveryProviderOptions.first { $0.id == videoDiscoveryProvider }?.label
            ?? AppleBookCreatePresentation.videoDiscoveryProviderFallbackLabel(for: videoDiscoveryProvider)
    }

    private func videoDiscoveryProviderEntry(for providerID: String) -> AcquisitionProviderEntry? {
        acquisitionProviders.first { $0.id == providerID }
    }

    private func applyPreferredVideoDiscoveryProviderIfNeeded(_ providerID: String?) {
        guard !hasUserSelectedVideoDiscoveryProvider,
              let providerID,
              !providerID.isEmpty else {
            return
        }
        didApplyBackendVideoDiscoveryDefault = true
        let currentProviderIsKnown = videoDiscoveryProviderOptions.contains {
            $0.id == videoDiscoveryProvider
        }
        guard videoDiscoveryProvider != providerID || !currentProviderIsKnown else {
            return
        }
        videoDiscoveryProvider = providerID
    }

    private var selectedYoutubeVideo: YoutubeNasVideoEntry? {
        youtubeVideos.first { $0.path == youtubeVideoPath }
    }

    private var hasYoutubeVideoPath: Bool {
        !youtubeVideoPath.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
    }

    private var youtubeSubtitleEntries: [YoutubeNasSubtitleEntry] {
        AppleBookCreatePresentation.playableYoutubeSubtitles(for: selectedYoutubeVideo)
    }

    private var shouldShowCurrentYoutubeVideoPath: Bool {
        let trimmedPath = youtubeVideoPath.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmedPath.isEmpty else {
            return false
        }
        return !youtubeVideos.contains { $0.path == youtubeVideoPath }
    }

    private var shouldShowCurrentYoutubeSubtitlePath: Bool {
        let trimmedPath = youtubeSubtitlePath.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmedPath.isEmpty else {
            return false
        }
        return !youtubeSubtitleEntries.contains { $0.path == youtubeSubtitlePath }
    }

    private func applyYoutubeVideoSelection(_ videoPath: String) {
        guard let video = youtubeVideos.first(where: { $0.path == videoPath }) else {
            return
        }
        let candidates = AppleBookCreatePresentation.playableYoutubeSubtitles(for: video)
        if candidates.contains(where: { $0.path == youtubeSubtitlePath }) {
            return
        }
        youtubeSubtitlePath = AppleBookCreatePresentation.preferredYoutubeSubtitle(for: video)?.path ?? ""
    }
}
