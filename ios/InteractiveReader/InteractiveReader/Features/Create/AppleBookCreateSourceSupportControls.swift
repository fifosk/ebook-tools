import Foundation
import SwiftUI

struct AppleBookCreateNarrateChapterRangeControls: View {
    let sourcePath: String
    let selectedSourceEntry: PipelineFileEntry?
    @Binding var sourceStartSentence: String
    @Binding var sourceEndSentence: String
    let narrateChapterOptions: [AppleCreateChapterOption]
    @Binding var selectedNarrateStartChapterID: String
    @Binding var selectedNarrateEndChapterID: String
    let isLoadingNarrateChapters: Bool
    let narrateChaptersErrorMessage: String?
    let onLoadNarrateChapters: () -> Void

    var body: some View {
        HStack {
            Button(action: onLoadNarrateChapters) {
                Label(loadChaptersTitle, systemImage: "list.bullet.rectangle")
            }
            .disabled(isLoadChaptersDisabled)
            .accessibilityIdentifier("createNarrateLoadChaptersButton")

            if isLoadingNarrateChapters {
                ProgressView()
                    .accessibilityIdentifier("createNarrateChaptersProgress")
            }
        }
        if let narrateChaptersErrorMessage {
            Text(narrateChaptersErrorMessage)
                .font(.footnote)
                .foregroundStyle(.secondary)
                .accessibilityIdentifier("createNarrateChaptersMessage")
        } else if let selectedSourceEntry {
            Text("Selected EPUB: \(AppleBookCreatePresentation.pipelineEbookDetailLabel(selectedSourceEntry))")
                .font(.footnote)
                .foregroundStyle(.secondary)
                .accessibilityIdentifier("createNarrateSelectedEbookDetail")
        } else if !hasNarrateSource {
            Text("Choose an EPUB source before loading chapters.")
                .font(.footnote)
                .foregroundStyle(.secondary)
                .accessibilityIdentifier("createNarrateChaptersMessage")
        } else if narrateChapterOptions.isEmpty && !isLoadingNarrateChapters {
            Text("No chapter data loaded.")
                .font(.footnote)
                .foregroundStyle(.secondary)
                .accessibilityIdentifier("createNarrateChaptersMessage")
        }
        if !narrateChapterOptions.isEmpty {
            HStack(alignment: .firstTextBaseline) {
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

                Picker("End chapter", selection: $selectedNarrateEndChapterID) {
                    Text("Same as start").tag("")
                    ForEach(narrateChapterOptions) { chapter in
                        Text(chapter.pickerLabel).tag(chapter.id)
                    }
                }
                .disabled(selectedNarrateStartChapterID.isEmpty)
                .accessibilityIdentifier("createNarrateEndChapterPicker")
                .onChange(of: selectedNarrateEndChapterID) { _, newValue in
                    applyNarrateChapterRangeSelection(startID: selectedNarrateStartChapterID, endID: newValue)
                }
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
            } else {
                Text("\(narrateChapterOptions.count) chapters loaded.")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
                    .accessibilityIdentifier("createNarrateChapterRangeSummary")
            }
        }
    }

    private var hasNarrateSource: Bool {
        !sourcePath.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
    }

    private var isLoadChaptersDisabled: Bool {
        isLoadingNarrateChapters || !hasNarrateSource
    }

    private var loadChaptersTitle: String {
        isLoadingNarrateChapters ? "Loading Chapters" : "Load Chapters"
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
    let isDeletingSubtitleSource: Bool
    let subtitleSourcesErrorMessage: String?
    let onRefreshSubtitleSources: () -> Void
    let onDeleteSubtitleSource: (SubtitleSourceEntry) -> Void
    let onChooseSubtitleFile: () -> Void

    var body: some View {
        #if os(iOS)
        AppleBookCreateFileImportControl(
            title: selectedSubtitleFileName ?? "Choose subtitle file",
            selectedFileName: selectedSubtitleFileName,
            systemImage: "captions.bubble",
            isBusy: false,
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
        Button(role: .destructive) {
            if let selectedSubtitleSourceEntry {
                onDeleteSubtitleSource(selectedSubtitleSourceEntry)
            }
        } label: {
            Label(
                isDeletingSubtitleSource ? "Deleting Subtitle" : "Delete Selected Subtitle",
                systemImage: "trash"
            )
        }
        .disabled(
            isDeletingSubtitleSource
                || isLoadingSubtitleSources
                || selectedSubtitleSourceEntry == nil
        )
        .accessibilityIdentifier("createSubtitleDeleteServerSourceButton")
        if isDeletingSubtitleSource {
            ProgressView()
                .accessibilityIdentifier("createSubtitleDeleteServerSourceProgress")
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

    private var subtitleSourceEntries: [SubtitleSourceEntry] {
        AppleBookCreatePresentation.subtitleJobSources(from: subtitleSources)
    }

    private var selectedSubtitleSourceEntry: SubtitleSourceEntry? {
        subtitleSourceEntries.first { $0.path == subtitleSourcePath }
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
    let isBusy: Bool
    let buttonIdentifier: String
    let labelIdentifier: String
    let action: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Button(action: action) {
                Label(title, systemImage: systemImage)
            }
            .disabled(isBusy)
            .accessibilityIdentifier(buttonIdentifier)

            if isBusy {
                ProgressView()
                    .accessibilityIdentifier("\(buttonIdentifier).progress")
            }

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
            AppleBookCreateBusyActionButton(
                title: title,
                busyTitle: busyTitle,
                systemImage: systemImage,
                isBusy: isBusy,
                isDisabled: isDisabled,
                accessibilityIdentifier: buttonIdentifier,
                action: action
            )

            if isBusy {
                ProgressView()
                    .accessibilityIdentifier(progressIdentifier)
            }
        }
    }
}
