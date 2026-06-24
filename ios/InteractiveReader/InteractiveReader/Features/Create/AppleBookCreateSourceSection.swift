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
    @Binding var subtitleSourcePath: String
    @Binding var youtubeBaseDir: String
    @Binding var youtubeVideoPath: String
    @Binding var youtubeSubtitlePath: String
    @Binding var youtubeSubtitleExtractionLanguages: String
    let pipelineFiles: PipelineFileBrowserResponse?
    let subtitleSources: SubtitleSourceListResponse?
    let youtubeLibrary: YoutubeNasLibraryResponse?
    let youtubeInlineSubtitleStreams: [YoutubeInlineSubtitleStream]
    let selectedNarrateFileName: String?
    let selectedSubtitleFileName: String?
    let narrateChapterOptions: [AppleCreateChapterOption]
    @Binding var selectedNarrateStartChapterID: String
    @Binding var selectedNarrateEndChapterID: String
    let isLoadingPipelineFiles: Bool
    let isLoadingNarrateChapters: Bool
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
    let youtubeSubtitleExtractionMessage: String?
    let youtubeSubtitleExtractionErrorMessage: String?
    let onRefreshPipelineFiles: () -> Void
    let onDeletePipelineEbook: (PipelineFileEntry) -> Void
    let onRefreshSubtitleSources: () -> Void
    let onDeleteSubtitleSource: (SubtitleSourceEntry) -> Void
    let onRefreshYoutubeLibrary: () -> Void
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
            pipelineFiles: pipelineFiles,
            selectedNarrateFileName: selectedNarrateFileName,
            narrateChapterOptions: narrateChapterOptions,
            selectedNarrateStartChapterID: $selectedNarrateStartChapterID,
            selectedNarrateEndChapterID: $selectedNarrateEndChapterID,
            showsNarrateRangeControls: showsNarrateRangeControls,
            isLoadingPipelineFiles: isLoadingPipelineFiles,
            isDeletingPipelineEbook: isDeletingPipelineEbook,
            isLoadingNarrateChapters: isLoadingNarrateChapters,
            pipelineFilesErrorMessage: pipelineFilesErrorMessage,
            narrateChaptersErrorMessage: narrateChaptersErrorMessage,
            onRefreshPipelineFiles: onRefreshPipelineFiles,
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
            youtubeLibrary: youtubeLibrary,
            youtubeInlineSubtitleStreams: youtubeInlineSubtitleStreams,
            isLoadingYoutubeLibrary: isLoadingYoutubeLibrary,
            isLoadingYoutubeSubtitleStreams: isLoadingYoutubeSubtitleStreams,
            isExtractingYoutubeSubtitles: isExtractingYoutubeSubtitles,
            youtubeLibraryErrorMessage: youtubeLibraryErrorMessage,
            youtubeSubtitleExtractionMessage: youtubeSubtitleExtractionMessage,
            youtubeSubtitleExtractionErrorMessage: youtubeSubtitleExtractionErrorMessage,
            onRefreshYoutubeLibrary: onRefreshYoutubeLibrary,
            onInspectYoutubeSubtitles: onInspectYoutubeSubtitles,
            onExtractYoutubeSubtitles: onExtractYoutubeSubtitles
        )
    }

}
