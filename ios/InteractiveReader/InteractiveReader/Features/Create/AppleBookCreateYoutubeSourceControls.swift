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
    let downloadStationJob: AcquisitionJobStatusResponse?
    let youtubeLibrary: YoutubeNasLibraryResponse?
    let youtubeInlineSubtitleStreams: [YoutubeInlineSubtitleStream]
    let isLoadingAcquisitionDiscovery: Bool
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
    let onSelectYoutubeAcquisitionCandidate: (AcquisitionCandidate) -> Void
    let onSubmitDownloadStation: (String?, String?, String?, Bool) -> Void
    let onPollDownloadStation: () -> Void
    let onInspectYoutubeSubtitles: () -> Void
    let onExtractYoutubeSubtitles: () -> Void
    @State private var videoDiscoveryQuery = ""
    @State private var videoDiscoveryProvider = "nas_video"
    @State private var hasUserSelectedVideoDiscoveryProvider = false
    @State private var didApplyBackendVideoDiscoveryDefault = false
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
                applyPreferredVideoDiscoveryProviderIfNeeded(preferredVideoDiscoveryProviderID)
            }
            .onChange(of: preferredVideoDiscoveryProviderID ?? "") { _, providerID in
                applyPreferredVideoDiscoveryProviderIfNeeded(providerID.nonEmptyValue)
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
        videoDiscoveryControls
        downloadStationControls
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
        embeddedYoutubeSubtitleControls
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

    @ViewBuilder
    private var videoDiscoveryControls: some View {
        VStack(alignment: .leading, spacing: 8) {
            Label("Discover Video Sources", systemImage: "sparkle.magnifyingglass")
                .accessibilityIdentifier("createYoutubeDiscoveryLabel")
            Picker("Discovery source", selection: videoDiscoveryProviderBinding) {
                ForEach(videoDiscoveryProviderOptions) { option in
                    Text(option.label).tag(option.id)
                }
            }
            .pickerStyle(.segmented)
            .accessibilityIdentifier("createYoutubeDiscoveryProviderPicker")
            TextField(videoDiscoveryQueryPlaceholder, text: $videoDiscoveryQuery)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
                .accessibilityIdentifier("createYoutubeDiscoveryQueryField")
            Button {
                onSearchYoutubeAcquisitionDiscovery(videoDiscoveryQuery, videoDiscoveryProvider)
            } label: {
                Label(
                    isLoadingAcquisitionDiscovery ? "Searching Sources" : "Search Sources",
                    systemImage: "magnifyingglass"
                )
            }
            .disabled(isLoadingAcquisitionDiscovery || !isSelectedVideoDiscoveryProviderAvailable)
            .accessibilityIdentifier("createYoutubeDiscoverySearchButton")
            if isLoadingAcquisitionDiscovery {
                ProgressView()
                    .accessibilityIdentifier("createYoutubeDiscoveryProgress")
            }
            if let acquisitionDiscoveryErrorMessage {
                Text(acquisitionDiscoveryErrorMessage)
                    .font(.footnote)
                    .foregroundStyle(.secondary)
                    .accessibilityIdentifier("createYoutubeDiscoveryMessage")
            } else if let acquisitionProvidersErrorMessage {
                Text(acquisitionProvidersErrorMessage)
                    .font(.footnote)
                    .foregroundStyle(.secondary)
                    .accessibilityIdentifier("createYoutubeDiscoveryMessage")
            } else if let selectedVideoDiscoveryProviderUnavailableMessage {
                Text(selectedVideoDiscoveryProviderUnavailableMessage)
                    .font(.footnote)
                    .foregroundStyle(.secondary)
                    .accessibilityIdentifier("createYoutubeDiscoveryMessage")
            } else if shouldShowNoVideoDiscoveryCandidatesMessage {
                Text(noVideoDiscoveryCandidatesMessage)
                    .font(.footnote)
                    .foregroundStyle(.secondary)
                    .accessibilityIdentifier("createYoutubeDiscoveryMessage")
            }
            ForEach(videoDiscoveryCandidates) { candidate in
                Button {
                    if AppleBookCreatePresentation.isDownloadStationHandoffCandidate(candidate) {
                        downloadStationCandidate = candidate
                        downloadStationSourceURI = ""
                    }
                    onSelectYoutubeAcquisitionCandidate(candidate)
                } label: {
                    VStack(alignment: .leading, spacing: 3) {
                        Text(candidate.title)
                            .font(.body)
                        Text(AppleBookCreatePresentation.videoDiscoveryCandidateDetail(candidate))
                            .font(.footnote)
                            .foregroundStyle(.secondary)
                    }
                }
                .accessibilityIdentifier("createYoutubeDiscoveryCandidate.\(candidate.id)")
            }
        }
        .accessibilityIdentifier("createYoutubeDiscoveryControls")
    }

    @ViewBuilder
    private var downloadStationControls: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(alignment: .firstTextBaseline) {
                Label("Download Station", systemImage: "arrow.down.circle")
                Spacer()
                if let status = downloadStationStatusLabel {
                    Text(status)
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                        .accessibilityIdentifier("createYoutubeDownloadStationStatus")
                }
            }
            Text("Queue a reviewed URL or magnet link, then pick the completed file from manual downloads.")
                .font(.footnote)
                .foregroundStyle(.secondary)
                .accessibilityIdentifier("createYoutubeDownloadStationHint")
            if let downloadStationUnavailableMessage {
                Text(downloadStationUnavailableMessage)
                    .font(.footnote)
                    .foregroundStyle(.secondary)
                    .accessibilityIdentifier("createYoutubeDownloadStationMessage")
            }
            if let downloadStationCandidate {
                HStack(alignment: .firstTextBaseline) {
                    Text("Selected indexer result: \(downloadStationCandidate.title)")
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                    Button("Clear") {
                        self.downloadStationCandidate = nil
                    }
                    .disabled(isSubmittingDownloadStation)
                    .accessibilityIdentifier("createYoutubeDownloadStationClearCandidateButton")
                }
                .accessibilityIdentifier("createYoutubeDownloadStationCandidate")
            }
            TextField("URL or magnet link", text: $downloadStationSourceURI)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
                .onChange(of: downloadStationSourceURI) { _, newValue in
                    if !newValue.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                        downloadStationCandidate = nil
                    }
                }
                .disabled(!isDownloadStationAvailable || isSubmittingDownloadStation)
                .accessibilityIdentifier("createYoutubeDownloadStationSourceField")
            TextField("Destination", text: $downloadStationDestination)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
                .disabled(!isDownloadStationAvailable || isSubmittingDownloadStation)
                .accessibilityIdentifier("createYoutubeDownloadStationDestinationField")
            Toggle("I am authorized to download and process this source.", isOn: $downloadStationConfirmed)
                .disabled(!isDownloadStationAvailable || isSubmittingDownloadStation)
                .accessibilityIdentifier("createYoutubeDownloadStationConfirmToggle")
            HStack {
                Button {
                    onSubmitDownloadStation(
                        downloadStationSourceURI,
                        downloadStationCandidate?.candidateToken,
                        downloadStationDestination.nonEmptyValue,
                        downloadStationConfirmed
                    )
                } label: {
                    Label(
                        isSubmittingDownloadStation ? "Submitting Download" : "Send to Download Station",
                        systemImage: "paperplane"
                    )
                }
                .disabled(!canSubmitDownloadStation)
                .accessibilityIdentifier("createYoutubeDownloadStationSubmitButton")

                Button {
                    onPollDownloadStation()
                    if downloadStationJob?.status == "completed" {
                        videoDiscoveryProvider = "manual_downloads"
                        videoDiscoveryQuery = ""
                    }
                } label: {
                    Label(
                        isPollingDownloadStation ? "Polling Download" : "Poll",
                        systemImage: "arrow.clockwise"
                    )
                }
                .disabled(downloadStationJob == nil || isPollingDownloadStation)
                .accessibilityIdentifier("createYoutubeDownloadStationPollButton")
            }
            if isSubmittingDownloadStation || isPollingDownloadStation {
                ProgressView()
                    .accessibilityIdentifier("createYoutubeDownloadStationProgress")
            }
            if let downloadStationErrorMessage {
                Text(downloadStationErrorMessage)
                    .font(.footnote)
                    .foregroundStyle(.secondary)
                    .accessibilityIdentifier("createYoutubeDownloadStationError")
            } else if let downloadStationMessage {
                Text(downloadStationMessage)
                    .font(.footnote)
                    .foregroundStyle(.secondary)
                    .accessibilityIdentifier("createYoutubeDownloadStationMessage")
            }
            if let completedFilesLabel {
                Text(completedFilesLabel)
                    .font(.footnote)
                    .foregroundStyle(.secondary)
                    .accessibilityIdentifier("createYoutubeDownloadStationCompletedFiles")
            }
        }
        .onChange(of: downloadStationJob?.status ?? "") { _, newStatus in
            if newStatus == "completed" {
                videoDiscoveryProvider = "manual_downloads"
                videoDiscoveryQuery = ""
            }
        }
        .accessibilityIdentifier("createYoutubeDownloadStationControls")
    }

    @ViewBuilder
    private var embeddedYoutubeSubtitleControls: some View {
        AppleBookCreateSourceActionRow(
            title: "Inspect Embedded Subtitles",
            busyTitle: "Inspecting Embedded Subtitles",
            systemImage: "magnifyingglass",
            isBusy: isLoadingYoutubeSubtitleStreams,
            isDisabled: !hasYoutubeVideoPath || isLoadingYoutubeSubtitleStreams || isExtractingYoutubeSubtitles,
            buttonIdentifier: "createYoutubeInspectEmbeddedSubtitlesButton",
            progressIdentifier: "createYoutubeEmbeddedSubtitlesProgress",
            action: onInspectYoutubeSubtitles
        )

        if !youtubeInlineSubtitleStreams.isEmpty {
            ForEach(youtubeInlineSubtitleStreams) { stream in
                Label(
                    AppleBookCreatePresentation.youtubeInlineSubtitleStreamLabel(stream),
                    systemImage: stream.canExtract ? "captions.bubble" : "photo"
                )
                .font(.footnote)
                .foregroundStyle(.secondary)
                .accessibilityIdentifier("createYoutubeEmbeddedSubtitleStream.\(stream.index)")
            }

            TextField("Languages to extract", text: $youtubeSubtitleExtractionLanguages)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
                .accessibilityIdentifier("createYoutubeEmbeddedSubtitleLanguagesField")
        }

        AppleBookCreateSourceActionRow(
            title: "Extract Embedded Subtitles",
            busyTitle: "Extracting Subtitles",
            systemImage: "square.and.arrow.down",
            isBusy: isExtractingYoutubeSubtitles,
            isDisabled: !hasYoutubeVideoPath || isLoadingYoutubeSubtitleStreams || isExtractingYoutubeSubtitles,
            buttonIdentifier: "createYoutubeExtractEmbeddedSubtitlesButton",
            progressIdentifier: "createYoutubeExtractEmbeddedSubtitlesProgress",
            action: onExtractYoutubeSubtitles
        )

        if let youtubeSubtitleExtractionMessage {
            Text(youtubeSubtitleExtractionMessage)
                .font(.footnote)
                .foregroundStyle(.secondary)
                .accessibilityIdentifier("createYoutubeEmbeddedSubtitlesMessage")
        }
        if let youtubeSubtitleExtractionErrorMessage {
            Text(youtubeSubtitleExtractionErrorMessage)
                .font(.footnote)
                .foregroundStyle(.secondary)
                .accessibilityIdentifier("createYoutubeEmbeddedSubtitlesError")
        }
    }

    private var youtubeVideos: [YoutubeNasVideoEntry] {
        youtubeLibrary?.videos ?? []
    }

    private var videoDiscoveryCandidates: [AcquisitionCandidate] {
        AppleBookCreatePresentation.videoDiscoveryCandidates(
            from: acquisitionDiscovery,
            providerID: videoDiscoveryProvider
        )
    }

    private var shouldShowNoVideoDiscoveryCandidatesMessage: Bool {
        acquisitionDiscovery != nil && videoDiscoveryCandidates.isEmpty && !isLoadingAcquisitionDiscovery
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
        AppleBookCreatePresentation.videoDiscoveryProviderOptions(from: acquisitionProviders)
    }

    private var preferredVideoDiscoveryProviderID: String? {
        AppleBookCreatePresentation.defaultDiscoveryProviderID(
            for: "video",
            defaultProviderIds: acquisitionDefaultProviderIds,
            optionIds: videoDiscoveryProviderOptions.map(\.id),
            fallback: "nas_video"
        )
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

    private var canSubmitDownloadStation: Bool {
        isDownloadStationAvailable
            && !isSubmittingDownloadStation
            && downloadStationConfirmed
            && (
                !downloadStationSourceURI.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
                || downloadStationCandidate?.candidateToken.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty == false
            )
    }

    private var downloadStationStatusLabel: String? {
        guard let downloadStationJob else {
            return nil
        }
        if let progress = downloadStationJob.progress {
            return "\(downloadStationJob.status) - \(Int((progress * 100).rounded()))%"
        }
        return downloadStationJob.status
    }

    private var completedFilesLabel: String? {
        let filenames = AppleBookCreatePresentation.downloadStationCompletedFiles(from: downloadStationJob)
            .map(AppleBookCreatePresentation.filenameFromPath)
            .filter { !$0.isEmpty }
        guard !filenames.isEmpty else {
            return nil
        }
        return "Completed: \(filenames.joined(separator: ", "))"
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
        if !acquisitionProviders.isEmpty, selectedVideoDiscoveryProvider == nil {
            return "\(selectedVideoDiscoveryProviderLabel) is unavailable on this backend. Choose another discovery source."
        }
        return AppleBookCreatePresentation.videoDiscoveryProviderUnavailableMessage(
            for: selectedVideoDiscoveryProvider,
            youtubeSearchUnavailableMessage: youtubeSearchUnavailableMessage
        )
    }

    private var selectedVideoDiscoveryProviderLabel: String {
        videoDiscoveryProviderOptions.first { $0.id == videoDiscoveryProvider }?.label
            ?? fallbackVideoDiscoveryProviderLabel(for: videoDiscoveryProvider)
    }

    private func videoDiscoveryProviderEntry(for providerID: String) -> AcquisitionProviderEntry? {
        acquisitionProviders.first { $0.id == providerID }
    }

    private func fallbackVideoDiscoveryProviderLabel(for providerID: String) -> String {
        switch providerID {
        case "nas_video":
            return "NAS videos"
        case "manual_downloads":
            return "Manual downloads"
        case "youtube_search":
            return "YouTube search"
        case "newznab_torznab":
            return "Indexers"
        default:
            return providerID
        }
    }

    private func applyPreferredVideoDiscoveryProviderIfNeeded(_ providerID: String?) {
        guard !didApplyBackendVideoDiscoveryDefault,
              !hasUserSelectedVideoDiscoveryProvider,
              let providerID,
              !providerID.isEmpty else {
            return
        }
        didApplyBackendVideoDiscoveryDefault = true
        guard videoDiscoveryProvider != providerID else {
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
