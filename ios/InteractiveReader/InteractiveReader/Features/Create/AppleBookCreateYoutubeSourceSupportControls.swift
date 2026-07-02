import Foundation
import SwiftUI

struct AppleBookCreateYoutubeDownloadStationControls: View {
    let downloadStationJob: AcquisitionJobStatusResponse?
    let downloadStationMessage: String?
    let downloadStationErrorMessage: String?
    let downloadStationUnavailableMessage: String?
    let isDownloadStationAvailable: Bool
    let isSubmittingDownloadStation: Bool
    let isPollingDownloadStation: Bool
    @Binding var downloadStationSourceURI: String
    @Binding var downloadStationCandidate: AcquisitionCandidate?
    @Binding var downloadStationDestination: String
    @Binding var downloadStationConfirmed: Bool
    @Binding var videoDiscoveryProvider: String
    @Binding var videoDiscoveryQuery: String
    let onSubmitDownloadStation: (String?, String?, String?, Bool) -> Void
    let onPollDownloadStation: () -> Void

    var body: some View {
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
}

struct AppleBookCreateYoutubeEmbeddedSubtitleControls: View {
    @Binding var youtubeSubtitleExtractionLanguages: String
    let youtubeInlineSubtitleStreams: [YoutubeInlineSubtitleStream]
    let hasYoutubeVideoPath: Bool
    let isLoadingYoutubeSubtitleStreams: Bool
    let isExtractingYoutubeSubtitles: Bool
    let youtubeSubtitleExtractionMessage: String?
    let youtubeSubtitleExtractionErrorMessage: String?
    let onInspectYoutubeSubtitles: () -> Void
    let onExtractYoutubeSubtitles: () -> Void

    var body: some View {
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
}
