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
    let isLoadingSubtitleSources: Bool
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
    let onRefreshSubtitleSources: () -> Void
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
            isLoadingNarrateChapters: isLoadingNarrateChapters,
            pipelineFilesErrorMessage: pipelineFilesErrorMessage,
            narrateChaptersErrorMessage: narrateChaptersErrorMessage,
            onRefreshPipelineFiles: onRefreshPipelineFiles,
            onLoadNarrateChapters: onLoadNarrateChapters,
            onChooseNarrateFile: onChooseNarrateFile
        )
    }

    @ViewBuilder
    private var subtitleSourceControls: some View {
        #if os(iOS)
        AppleBookCreateFileImportControl(
            title: selectedSubtitleFileName ?? "Choose subtitle file",
            selectedFileName: selectedSubtitleFileName,
            systemImage: "captions.bubble",
            buttonIdentifier: "createSubtitleFileImportButton",
            labelIdentifier: "createSubtitleSelectedFileLabel",
            action: onChooseSubtitleFile
        )
        #endif
        if !subtitleSourceEntries.isEmpty {
            Picker("Server subtitle", selection: $subtitleSourcePath) {
                Text("Manual path").tag("")
                if shouldShowCurrentSubtitlePath {
                    Text(subtitleSourcePath).tag(subtitleSourcePath)
                }
                ForEach(subtitleSourceEntries, id: \.path) { entry in
                    Text(subtitleEntryLabel(entry)).tag(entry.path)
                }
            }
            .accessibilityIdentifier("createSubtitleServerSourcePicker")
        }
        HStack {
            Button(action: onRefreshSubtitleSources) {
                Label(
                    isLoadingSubtitleSources ? "Refreshing Subtitles" : "Refresh Subtitles",
                    systemImage: "arrow.clockwise"
                )
            }
            .disabled(isLoadingSubtitleSources)
            .accessibilityIdentifier("createSubtitleRefreshServerSourcesButton")

            if isLoadingSubtitleSources {
                ProgressView()
                    .accessibilityIdentifier("createSubtitleServerSourcesProgress")
            }
        }
        if let subtitleSourcesErrorMessage {
            Text(subtitleSourcesErrorMessage)
                .font(.footnote)
                .foregroundStyle(.secondary)
                .accessibilityIdentifier("createSubtitleServerSourcesMessage")
        }
        TextField("Server subtitle path", text: $subtitleSourcePath)
            .textInputAutocapitalization(.never)
            .autocorrectionDisabled()
            .accessibilityIdentifier("createSubtitleSourcePathField")
    }

    private var youtubeSourceControls: some View {
        Group {
            TextField("NAS directory", text: $youtubeBaseDir)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
                .accessibilityIdentifier("createYoutubeBaseDirField")
            if let baseDir = youtubeLibrary?.baseDir, !baseDir.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
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
                        Text(youtubeVideoLabel(video)).tag(video.path)
                    }
                }
                .accessibilityIdentifier("createYoutubeNasVideoPicker")
                .onChange(of: youtubeVideoPath) { _, newValue in
                    applyYoutubeVideoSelection(newValue)
                }
            }
            HStack {
                Button(action: onRefreshYoutubeLibrary) {
                    Label(
                        isLoadingYoutubeLibrary ? "Refreshing Videos" : "Refresh Videos",
                        systemImage: "arrow.clockwise"
                    )
                }
                .disabled(isLoadingYoutubeLibrary)
                .accessibilityIdentifier("createYoutubeRefreshNasVideosButton")

                if isLoadingYoutubeLibrary {
                    ProgressView()
                        .accessibilityIdentifier("createYoutubeNasVideosProgress")
                }
            }
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
                        Text(youtubeSubtitleLabel(subtitle)).tag(subtitle.path)
                    }
                }
                .accessibilityIdentifier("createYoutubeNasSubtitlePicker")
            }
            TextField("Subtitle path", text: $youtubeSubtitlePath)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
                .accessibilityIdentifier("createYoutubeSubtitlePathField")
        }
    }

    @ViewBuilder
    private var embeddedYoutubeSubtitleControls: some View {
        HStack {
            Button(action: onInspectYoutubeSubtitles) {
                Label(
                    isLoadingYoutubeSubtitleStreams ? "Inspecting Embedded Subtitles" : "Inspect Embedded Subtitles",
                    systemImage: "magnifyingglass"
                )
            }
            .disabled(!hasYoutubeVideoPath || isLoadingYoutubeSubtitleStreams || isExtractingYoutubeSubtitles)
            .accessibilityIdentifier("createYoutubeInspectEmbeddedSubtitlesButton")

            if isLoadingYoutubeSubtitleStreams {
                ProgressView()
                    .accessibilityIdentifier("createYoutubeEmbeddedSubtitlesProgress")
            }
        }

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

        HStack {
            Button(action: onExtractYoutubeSubtitles) {
                Label(
                    isExtractingYoutubeSubtitles ? "Extracting Subtitles" : "Extract Embedded Subtitles",
                    systemImage: "square.and.arrow.down"
                )
            }
            .disabled(!hasYoutubeVideoPath || isLoadingYoutubeSubtitleStreams || isExtractingYoutubeSubtitles)
            .accessibilityIdentifier("createYoutubeExtractEmbeddedSubtitlesButton")

            if isExtractingYoutubeSubtitles {
                ProgressView()
                    .accessibilityIdentifier("createYoutubeExtractEmbeddedSubtitlesProgress")
            }
        }

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

    private var subtitleSourceEntries: [SubtitleSourceEntry] {
        AppleBookCreatePresentation.subtitleJobSources(from: subtitleSources)
    }

    private var shouldShowCurrentSubtitlePath: Bool {
        let trimmedPath = subtitleSourcePath.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmedPath.isEmpty else {
            return false
        }
        return !subtitleSourceEntries.contains { $0.path == subtitleSourcePath }
    }

    private func subtitleEntryLabel(_ entry: SubtitleSourceEntry) -> String {
        let suffix = [entry.format.uppercased(), entry.language]
            .compactMap { value -> String? in
                guard let value = value?.trimmingCharacters(in: .whitespacesAndNewlines), !value.isEmpty else {
                    return nil
                }
                return value
            }
            .joined(separator: " · ")
        return suffix.isEmpty ? entry.name : "\(entry.name) · \(suffix)"
    }

    private var youtubeVideos: [YoutubeNasVideoEntry] {
        youtubeLibrary?.videos ?? []
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

    private func youtubeVideoLabel(_ video: YoutubeNasVideoEntry) -> String {
        let subtitleCount = AppleBookCreatePresentation.playableYoutubeSubtitles(for: video).count
        let label = subtitleCount == 1 ? "1 subtitle" : "\(subtitleCount) subtitles"
        return "\(video.filename) · \(label)"
    }

    private func youtubeSubtitleLabel(_ subtitle: YoutubeNasSubtitleEntry) -> String {
        let language = subtitle.language?.trimmingCharacters(in: .whitespacesAndNewlines)
        let suffix = [subtitle.format.uppercased(), language]
            .compactMap { value -> String? in
                guard let value, !value.isEmpty else { return nil }
                return value
            }
            .joined(separator: " · ")
        return suffix.isEmpty ? subtitle.filename : "\(subtitle.filename) · \(suffix)"
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
