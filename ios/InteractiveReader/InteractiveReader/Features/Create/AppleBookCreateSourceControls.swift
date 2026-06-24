import Foundation
import SwiftUI

struct AppleBookCreateNarrateSourceControls: View {
    @Binding var sourcePath: String
    @Binding var sourceStartSentence: String
    @Binding var sourceEndSentence: String
    let pipelineFiles: PipelineFileBrowserResponse?
    let selectedNarrateFileName: String?
    let narrateChapterOptions: [AppleCreateChapterOption]
    @Binding var selectedNarrateStartChapterID: String
    @Binding var selectedNarrateEndChapterID: String
    let showsNarrateRangeControls: Bool
    let isLoadingPipelineFiles: Bool
    let isLoadingNarrateChapters: Bool
    let pipelineFilesErrorMessage: String?
    let narrateChaptersErrorMessage: String?
    let onRefreshPipelineFiles: () -> Void
    let onLoadNarrateChapters: () -> Void
    let onChooseNarrateFile: () -> Void

    var body: some View {
        #if os(iOS)
        AppleBookCreateFileImportControl(
            title: selectedNarrateFileName ?? "Choose EPUB",
            selectedFileName: selectedNarrateFileName,
            systemImage: "doc.badge.plus",
            buttonIdentifier: "createNarrateFileImportButton",
            labelIdentifier: "createNarrateSelectedFileLabel",
            action: onChooseNarrateFile
        )
        #endif
        if !narrateServerEbooks.isEmpty {
            Picker("Server EPUB", selection: $sourcePath) {
                Text("Manual path").tag("")
                if shouldShowCurrentServerPath {
                    Text(sourcePath).tag(sourcePath)
                }
                ForEach(narrateServerEbooks, id: \.path) { entry in
                    Text(entry.name).tag(entry.path)
                }
            }
            .accessibilityIdentifier("createNarrateServerEbookPicker")
        }
        AppleBookCreateSourceActionRow(
            title: "Refresh EPUBs",
            busyTitle: "Refreshing EPUBs",
            systemImage: "arrow.clockwise",
            isBusy: isLoadingPipelineFiles,
            isDisabled: isLoadingPipelineFiles,
            buttonIdentifier: "createNarrateRefreshServerEbooksButton",
            progressIdentifier: "createNarrateServerEbooksProgress",
            action: onRefreshPipelineFiles
        )
        if let pipelineFilesErrorMessage {
            Text(pipelineFilesErrorMessage)
                .font(.footnote)
                .foregroundStyle(.secondary)
                .accessibilityIdentifier("createNarrateServerEbooksMessage")
        }
        TextField("Server EPUB path", text: $sourcePath)
            .textInputAutocapitalization(.never)
            .autocorrectionDisabled()
            .accessibilityIdentifier("createNarrateSourcePathField")
        if showsNarrateRangeControls {
            narrateRangeControls
        }
    }

    @ViewBuilder
    private var narrateRangeControls: some View {
        Button(action: onLoadNarrateChapters) {
            Label(
                isLoadingNarrateChapters ? "Loading Chapters" : "Load Chapters",
                systemImage: "list.bullet.rectangle"
            )
        }
        .disabled(
            isLoadingNarrateChapters
                || sourcePath.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
        )
        .accessibilityIdentifier("createNarrateLoadChaptersButton")
        if isLoadingNarrateChapters {
            ProgressView()
                .accessibilityIdentifier("createNarrateChaptersProgress")
        }
        if let narrateChaptersErrorMessage {
            Text(narrateChaptersErrorMessage)
                .font(.footnote)
                .foregroundStyle(.secondary)
                .accessibilityIdentifier("createNarrateChaptersMessage")
        }
        if !narrateChapterOptions.isEmpty {
            Picker("Start chapter", selection: $selectedNarrateStartChapterID) {
                Text("Manual sentence range").tag("")
                ForEach(narrateChapterOptions) { chapter in
                    Text(chapter.pickerLabel).tag(chapter.id)
                }
            }
            .accessibilityIdentifier("createNarrateStartChapterPicker")
            .onChange(of: selectedNarrateStartChapterID) { _, newValue in
                applyNarrateChapterRangeSelection(startID: newValue, endID: selectedNarrateEndChapterID)
            }

            if !selectedNarrateStartChapterID.isEmpty {
                Picker("End chapter", selection: $selectedNarrateEndChapterID) {
                    ForEach(narrateChapterOptions) { chapter in
                        Text(chapter.pickerLabel).tag(chapter.id)
                    }
                }
                .accessibilityIdentifier("createNarrateEndChapterPicker")
                .onChange(of: selectedNarrateEndChapterID) { _, newValue in
                    applyNarrateChapterRangeSelection(startID: selectedNarrateStartChapterID, endID: newValue)
                }
                if let selection = AppleBookCreatePresentation.chapterRangeSelection(
                    chapters: narrateChapterOptions,
                    startChapterID: selectedNarrateStartChapterID,
                    endChapterID: selectedNarrateEndChapterID
                ) {
                    Text("\(selection.label) · \(selection.sentenceRangeLabel)")
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                        .accessibilityIdentifier("createNarrateChapterRangeSummary")
                }
            }
        }
    }

    private var narrateServerEbooks: [PipelineFileEntry] {
        pipelineFiles?.ebooks.filter { $0.type == "file" } ?? []
    }

    private var shouldShowCurrentServerPath: Bool {
        let trimmedPath = sourcePath.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmedPath.isEmpty else {
            return false
        }
        return !narrateServerEbooks.contains { $0.path == sourcePath }
    }

    private func applyNarrateChapterRangeSelection(startID: String, endID: String) {
        guard !startID.isEmpty else {
            selectedNarrateEndChapterID = ""
            return
        }
        guard let selection = AppleBookCreatePresentation.chapterRangeSelection(
            chapters: narrateChapterOptions,
            startChapterID: startID,
            endChapterID: endID
        ) else {
            return
        }
        let resolvedEndID = narrateChapterOptions[selection.endIndex].id
        if selectedNarrateEndChapterID != resolvedEndID {
            selectedNarrateEndChapterID = resolvedEndID
        }
        sourceStartSentence = "\(selection.startSentence)"
        sourceEndSentence = "\(selection.endSentence)"
    }
}

struct AppleBookCreateSubtitleSourceControls: View {
    @Binding var subtitleSourcePath: String
    let subtitleSources: SubtitleSourceListResponse?
    let selectedSubtitleFileName: String?
    let isLoadingSubtitleSources: Bool
    let subtitleSourcesErrorMessage: String?
    let onRefreshSubtitleSources: () -> Void
    let onChooseSubtitleFile: () -> Void

    var body: some View {
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
        AppleBookCreateSourceActionRow(
            title: "Refresh Subtitles",
            busyTitle: "Refreshing Subtitles",
            systemImage: "arrow.clockwise",
            isBusy: isLoadingSubtitleSources,
            isDisabled: isLoadingSubtitleSources,
            buttonIdentifier: "createSubtitleRefreshServerSourcesButton",
            progressIdentifier: "createSubtitleServerSourcesProgress",
            action: onRefreshSubtitleSources
        )
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
}

struct AppleBookCreateFileImportControl: View {
    let title: String
    let selectedFileName: String?
    let systemImage: String
    let buttonIdentifier: String
    let labelIdentifier: String
    let action: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Button(action: action) {
                Label(title, systemImage: systemImage)
            }
            .accessibilityIdentifier(buttonIdentifier)

            if let selectedFileName {
                Label(selectedFileName, systemImage: "checkmark.circle")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
                    .lineLimit(2)
                    .accessibilityIdentifier(labelIdentifier)
            }
        }
    }
}

struct AppleBookCreateSourceActionRow: View {
    let title: String
    let busyTitle: String
    let systemImage: String
    let isBusy: Bool
    let isDisabled: Bool
    let buttonIdentifier: String
    let progressIdentifier: String
    let action: () -> Void

    var body: some View {
        HStack {
            Button(action: action) {
                Label(isBusy ? busyTitle : title, systemImage: systemImage)
            }
            .disabled(isDisabled)
            .accessibilityIdentifier(buttonIdentifier)

            if isBusy {
                ProgressView()
                    .accessibilityIdentifier(progressIdentifier)
            }
        }
    }
}
