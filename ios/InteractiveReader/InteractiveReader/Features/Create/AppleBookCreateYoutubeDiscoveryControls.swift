import Foundation
import SwiftUI

struct AppleBookCreateYoutubeDiscoveryControls: View {
    @Binding var videoDiscoveryQuery: String
    @Binding var videoDiscoveryProvider: String
    @Binding var downloadStationSourceURI: String
    @Binding var downloadStationCandidate: AcquisitionCandidate?
    let videoDiscoveryProviderOptions: [AppleBookCreateVideoDiscoveryProviderOption]
    let videoDiscoveryQueryPlaceholder: String
    let videoDiscoveryCandidates: [AcquisitionCandidate]
    let videoDiscoveryPolicyNotes: [String]
    let isLoadingAcquisitionDiscovery: Bool
    let isPreparingAcquisitionCandidate: Bool
    let isSelectedVideoDiscoveryProviderAvailable: Bool
    let acquisitionDiscoveryErrorMessage: String?
    let acquisitionProvidersErrorMessage: String?
    let selectedVideoDiscoveryProviderUnavailableMessage: String?
    let shouldShowNoVideoDiscoveryCandidatesMessage: Bool
    let noVideoDiscoveryCandidatesMessage: String
    let onSearchYoutubeAcquisitionDiscovery: (String, String) -> Void
    let onSelectYoutubeAcquisitionCandidate: (AcquisitionCandidate, String, String) -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Label("Discover Video Sources", systemImage: "sparkle.magnifyingglass")
                .accessibilityIdentifier("createYoutubeDiscoveryLabel")
            Picker("Discovery source", selection: $videoDiscoveryProvider) {
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
            } else if isPreparingAcquisitionCandidate {
                ProgressView()
                    .accessibilityIdentifier("createYoutubeDiscoveryPrepareProgress")
            }
            discoveryStatusMessage
            ForEach(videoDiscoveryPolicyNotes, id: \.self) { note in
                Text(note)
                    .font(.footnote)
                    .foregroundStyle(.secondary)
                    .accessibilityIdentifier("createYoutubeDiscoveryPolicyNote")
            }
            ForEach(videoDiscoveryCandidates) { candidate in
                Button {
                    selectCandidate(candidate)
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
                .disabled(isPreparingAcquisitionCandidate)
            }
        }
        .accessibilityIdentifier("createYoutubeDiscoveryControls")
    }

    @ViewBuilder
    private var discoveryStatusMessage: some View {
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
    }

    private func selectCandidate(_ candidate: AcquisitionCandidate) {
        if AppleBookCreatePresentation.isDownloadStationHandoffCandidate(candidate) {
            downloadStationCandidate = candidate
            downloadStationSourceURI = ""
        }
        onSelectYoutubeAcquisitionCandidate(candidate, videoDiscoveryQuery, videoDiscoveryProvider)
    }
}
