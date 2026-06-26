import Foundation
import SwiftUI

struct AppleBookCreateSourceSection: View {
    @Binding var creationMode: AppleCreateMode
    let availableCreateModes: [AppleCreateMode]
    let showsJobTypePicker: Bool
    let showsNarrateRangeControls: Bool
    @Binding var sourcePath: String
    @Binding var sourceStartSentence: String
    @Binding var sourceEndSentence: String
    @Binding var narrateSourcePanel: AppleBookCreateNarrateSourcePanel
    @Binding var subtitleSourcePath: String
    @Binding var youtubeBaseDir: String
    @Binding var youtubeVideoPath: String
    @Binding var youtubeSubtitlePath: String
    @Binding var youtubeSubtitleExtractionLanguages: String
    let pipelineFiles: PipelineFileBrowserResponse?
    let acquisitionProviders: [AcquisitionProviderEntry]
    let acquisitionDefaultProviderIds: [String: [String]]
    let ebookAcquisitionDiscovery: AcquisitionDiscoveryResponse?
    let youtubeAcquisitionDiscovery: AcquisitionDiscoveryResponse?
    let downloadStationJob: AcquisitionJobStatusResponse?
    let subtitleSources: SubtitleSourceListResponse?
    let youtubeLibrary: YoutubeNasLibraryResponse?
    let youtubeInlineSubtitleStreams: [YoutubeInlineSubtitleStream]
    let selectedNarrateFileName: String?
    let selectedSubtitleFileName: String?
    let narrateChapterOptions: [AppleCreateChapterOption]
    @Binding var selectedNarrateStartChapterID: String
    @Binding var selectedNarrateEndChapterID: String
    let isLoadingPipelineFiles: Bool
    let isUploadingPipelineEbook: Bool
    let isLoadingEbookAcquisitionDiscovery: Bool
    let isAcquiringEbookAcquisitionCandidate: Bool
    let isLoadingYoutubeAcquisitionDiscovery: Bool
    let isLoadingNarrateChapters: Bool
    let isSubmittingDownloadStation: Bool
    let isPollingDownloadStation: Bool
    let isDeletingPipelineEbook: Bool
    let isLoadingSubtitleSources: Bool
    let isDeletingSubtitleSource: Bool
    let isLoadingYoutubeLibrary: Bool
    let isLoadingYoutubeSubtitleStreams: Bool
    let isExtractingYoutubeSubtitles: Bool
    let pipelineFilesErrorMessage: String?
    let narrateChaptersErrorMessage: String?
    let subtitleSourcesErrorMessage: String?
    let youtubeLibraryErrorMessage: String?
    let ebookAcquisitionDiscoveryErrorMessage: String?
    let youtubeAcquisitionDiscoveryErrorMessage: String?
    let downloadStationMessage: String?
    let downloadStationErrorMessage: String?
    let acquisitionProvidersErrorMessage: String?
    let youtubeSearchUnavailableMessage: String?
    let isYoutubeSearchAvailable: Bool
    let downloadStationUnavailableMessage: String?
    let isDownloadStationAvailable: Bool
    let youtubeSubtitleExtractionMessage: String?
    let youtubeSubtitleExtractionErrorMessage: String?
    let onRefreshPipelineFiles: () -> Void
    let onSearchAcquisitionDiscovery: (String, String) -> Void
    let onSelectAcquisitionCandidate: (AcquisitionCandidate) -> Void
    let onDeletePipelineEbook: (PipelineFileEntry) -> Void
    let onRefreshSubtitleSources: () -> Void
    let onDeleteSubtitleSource: (SubtitleSourceEntry) -> Void
    let onRefreshYoutubeLibrary: () -> Void
    let onSearchYoutubeAcquisitionDiscovery: (String, String) -> Void
    let onSelectYoutubeAcquisitionCandidate: (AcquisitionCandidate) -> Void
    let onSubmitDownloadStation: (String?, String?, String?, Bool) -> Void
    let onPollDownloadStation: () -> Void
    let onInspectYoutubeSubtitles: () -> Void
    let onExtractYoutubeSubtitles: () -> Void
    let onLoadNarrateChapters: () -> Void
    let onChooseNarrateFile: () -> Void
    let onChooseSubtitleFile: () -> Void

    var body: some View {
        if showsJobTypePicker || creationMode != .generatedBook {
            Section("Source") {
                if showsJobTypePicker {
                    Picker("Job type", selection: $creationMode) {
                        ForEach(availableCreateModes) { mode in
                            Text(mode.label).tag(mode)
                        }
                    }
                    #if os(iOS)
                    .pickerStyle(.segmented)
                    #endif
                    .accessibilityIdentifier("createJobTypePicker")
                }

                switch creationMode {
                case .generatedBook:
                    EmptyView()
                case .narrateEbook:
                    narrateEbookSourceControls
                case .subtitleJob:
                    subtitleSourceControls
                case .youtubeDub:
                    youtubeSourceControls
                }
            }
        }
    }

    @ViewBuilder
    private var narrateEbookSourceControls: some View {
        AppleBookCreateNarrateSourceControls(
            sourcePath: $sourcePath,
            sourceStartSentence: $sourceStartSentence,
            sourceEndSentence: $sourceEndSentence,
            sourcePanel: $narrateSourcePanel,
            pipelineFiles: pipelineFiles,
            acquisitionProviders: acquisitionProviders,
            acquisitionDefaultProviderIds: acquisitionDefaultProviderIds,
            acquisitionDiscovery: ebookAcquisitionDiscovery,
            selectedNarrateFileName: selectedNarrateFileName,
            narrateChapterOptions: narrateChapterOptions,
            selectedNarrateStartChapterID: $selectedNarrateStartChapterID,
            selectedNarrateEndChapterID: $selectedNarrateEndChapterID,
            showsNarrateRangeControls: showsNarrateRangeControls,
            isLoadingPipelineFiles: isLoadingPipelineFiles,
            isUploadingPipelineEbook: isUploadingPipelineEbook,
            isLoadingAcquisitionDiscovery: isLoadingEbookAcquisitionDiscovery,
            isAcquiringAcquisitionCandidate: isAcquiringEbookAcquisitionCandidate,
            isDeletingPipelineEbook: isDeletingPipelineEbook,
            isLoadingNarrateChapters: isLoadingNarrateChapters,
            pipelineFilesErrorMessage: pipelineFilesErrorMessage,
            acquisitionDiscoveryErrorMessage: ebookAcquisitionDiscoveryErrorMessage,
            acquisitionProvidersErrorMessage: acquisitionProvidersErrorMessage,
            narrateChaptersErrorMessage: narrateChaptersErrorMessage,
            onRefreshPipelineFiles: onRefreshPipelineFiles,
            onSearchAcquisitionDiscovery: onSearchAcquisitionDiscovery,
            onSelectAcquisitionCandidate: onSelectAcquisitionCandidate,
            onDeletePipelineEbook: onDeletePipelineEbook,
            onLoadNarrateChapters: onLoadNarrateChapters,
            onChooseNarrateFile: onChooseNarrateFile
        )
    }

    @ViewBuilder
    private var subtitleSourceControls: some View {
        AppleBookCreateSubtitleSourceControls(
            subtitleSourcePath: $subtitleSourcePath,
            subtitleSources: subtitleSources,
            selectedSubtitleFileName: selectedSubtitleFileName,
            isLoadingSubtitleSources: isLoadingSubtitleSources,
            isDeletingSubtitleSource: isDeletingSubtitleSource,
            subtitleSourcesErrorMessage: subtitleSourcesErrorMessage,
            onRefreshSubtitleSources: onRefreshSubtitleSources,
            onDeleteSubtitleSource: onDeleteSubtitleSource,
            onChooseSubtitleFile: onChooseSubtitleFile
        )
    }

    private var youtubeSourceControls: some View {
        AppleBookCreateYoutubeSourceControls(
            youtubeBaseDir: $youtubeBaseDir,
            youtubeVideoPath: $youtubeVideoPath,
            youtubeSubtitlePath: $youtubeSubtitlePath,
            youtubeSubtitleExtractionLanguages: $youtubeSubtitleExtractionLanguages,
            acquisitionProviders: acquisitionProviders,
            acquisitionDefaultProviderIds: acquisitionDefaultProviderIds,
            acquisitionDiscovery: youtubeAcquisitionDiscovery,
            downloadStationJob: downloadStationJob,
            youtubeLibrary: youtubeLibrary,
            youtubeInlineSubtitleStreams: youtubeInlineSubtitleStreams,
            isLoadingAcquisitionDiscovery: isLoadingYoutubeAcquisitionDiscovery,
            isLoadingYoutubeLibrary: isLoadingYoutubeLibrary,
            isLoadingYoutubeSubtitleStreams: isLoadingYoutubeSubtitleStreams,
            isExtractingYoutubeSubtitles: isExtractingYoutubeSubtitles,
            isSubmittingDownloadStation: isSubmittingDownloadStation,
            isPollingDownloadStation: isPollingDownloadStation,
            acquisitionDiscoveryErrorMessage: youtubeAcquisitionDiscoveryErrorMessage,
            downloadStationMessage: downloadStationMessage,
            downloadStationErrorMessage: downloadStationErrorMessage,
            acquisitionProvidersErrorMessage: acquisitionProvidersErrorMessage,
            youtubeSearchUnavailableMessage: youtubeSearchUnavailableMessage,
            isYoutubeSearchAvailable: isYoutubeSearchAvailable,
            downloadStationUnavailableMessage: downloadStationUnavailableMessage,
            isDownloadStationAvailable: isDownloadStationAvailable,
            youtubeLibraryErrorMessage: youtubeLibraryErrorMessage,
            youtubeSubtitleExtractionMessage: youtubeSubtitleExtractionMessage,
            youtubeSubtitleExtractionErrorMessage: youtubeSubtitleExtractionErrorMessage,
            onRefreshYoutubeLibrary: onRefreshYoutubeLibrary,
            onSearchYoutubeAcquisitionDiscovery: onSearchYoutubeAcquisitionDiscovery,
            onSelectYoutubeAcquisitionCandidate: onSelectYoutubeAcquisitionCandidate,
            onSubmitDownloadStation: onSubmitDownloadStation,
            onPollDownloadStation: onPollDownloadStation,
            onInspectYoutubeSubtitles: onInspectYoutubeSubtitles,
            onExtractYoutubeSubtitles: onExtractYoutubeSubtitles
        )
    }

}
