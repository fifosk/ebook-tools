import Foundation
import SwiftUI

enum AppleBookCreateNarrateSourcePanel: String, CaseIterable, Identifiable {
    case server
    case discovery

    var id: String { rawValue }

    var label: String {
        switch self {
        case .server:
            return "Server"
        case .discovery:
            return "Discovery"
        }
    }
}

struct AppleBookCreateNarrateSourceControls: View {
    @Binding var sourcePath: String
    @Binding var sourceStartSentence: String
    @Binding var sourceEndSentence: String
    @Binding var sourcePanel: AppleBookCreateNarrateSourcePanel
    let pipelineFiles: PipelineFileBrowserResponse?
    let acquisitionProviders: [AcquisitionProviderEntry]
    let acquisitionDefaultProviderIds: [String: [String]]
    let acquisitionDiscovery: AcquisitionDiscoveryResponse?
    let selectedNarrateFileName: String?
    let narrateChapterOptions: [AppleCreateChapterOption]
    @Binding var selectedNarrateStartChapterID: String
    @Binding var selectedNarrateEndChapterID: String
    let showsNarrateRangeControls: Bool
    let isLoadingPipelineFiles: Bool
    let isUploadingPipelineEbook: Bool
    let isLoadingAcquisitionDiscovery: Bool
    let isAcquiringAcquisitionCandidate: Bool
    let isDeletingPipelineEbook: Bool
    let isLoadingNarrateChapters: Bool
    let pipelineFilesErrorMessage: String?
    let acquisitionDiscoveryErrorMessage: String?
    let acquisitionProvidersErrorMessage: String?
    let narrateChaptersErrorMessage: String?
    let onRefreshPipelineFiles: () -> Void
    let onSearchAcquisitionDiscovery: (String, String) -> Void
    let onSelectAcquisitionCandidate: (AcquisitionCandidate) -> Void
    let onDeletePipelineEbook: (PipelineFileEntry) -> Void
    let onLoadNarrateChapters: () -> Void
    let onChooseNarrateFile: () -> Void
    @State private var acquisitionDiscoveryQuery = ""
    @State private var acquisitionDiscoveryProvider = "local_epub"
    @State private var hasUserSelectedDiscoveryProvider = false
    @State private var didApplyBackendDiscoveryDefault = false

    var body: some View {
        sourcePanelPicker
            .task {
                applyPreferredDiscoveryProviderIfNeeded(preferredDiscoveryProviderID)
            }
            .onChange(of: preferredDiscoveryProviderID ?? "") { _, providerID in
                applyPreferredDiscoveryProviderIfNeeded(providerID.nonEmptyValue)
            }
        switch sourcePanel {
        case .server:
            serverSourceControls
        case .discovery:
            discoverySourceControls
        }
        TextField("Server EPUB path", text: $sourcePath)
            .textInputAutocapitalization(.never)
            .autocorrectionDisabled()
            .accessibilityIdentifier("createNarrateSourcePathField")
        if showsNarrateRangeControls {
            narrateRangeControls
        }
    }

    private var sourcePanelPicker: some View {
        Picker("Source mode", selection: $sourcePanel) {
            ForEach(AppleBookCreateNarrateSourcePanel.allCases) { panel in
                Text(panel.label).tag(panel)
            }
        }
        #if os(iOS)
        .pickerStyle(.segmented)
        #endif
        .accessibilityIdentifier("createNarrateSourceModePicker")
    }

    @ViewBuilder
    private var serverSourceControls: some View {
        #if os(iOS)
        AppleBookCreateFileImportControl(
            title: isUploadingPipelineEbook ? "Importing EPUB" : selectedNarrateFileName ?? "Choose EPUB",
            selectedFileName: selectedNarrateFileName,
            systemImage: "doc.badge.plus",
            isBusy: isUploadingPipelineEbook,
            buttonIdentifier: "createNarrateFileImportButton",
            labelIdentifier: "createNarrateSelectedFileLabel",
            action: onChooseNarrateFile
        )
        #endif
        serverEbookPicker
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
        Button(role: .destructive) {
            if let selectedNarrateServerEbook {
                onDeletePipelineEbook(selectedNarrateServerEbook)
            }
        } label: {
            Label(
                isDeletingPipelineEbook ? "Deleting EPUB" : "Delete Selected EPUB",
                systemImage: "trash"
            )
        }
        .disabled(
            isDeletingPipelineEbook
                || isLoadingPipelineFiles
                || selectedNarrateServerEbook == nil
        )
        .accessibilityIdentifier("createNarrateDeleteServerEbookButton")
        if isDeletingPipelineEbook {
            ProgressView()
                .accessibilityIdentifier("createNarrateDeleteServerEbookProgress")
        }
        if let pipelineFilesErrorMessage {
            Text(pipelineFilesErrorMessage)
                .font(.footnote)
                .foregroundStyle(.secondary)
                .accessibilityIdentifier("createNarrateServerEbooksMessage")
        } else if shouldShowServerEbooksSummary {
            Text(serverEbooksSummaryMessage)
                .font(.footnote)
                .foregroundStyle(.secondary)
                .accessibilityIdentifier("createNarrateServerEbooksSummary")
        } else if shouldShowNoServerEbooksMessage {
            Text(noServerEbooksMessage)
                .font(.footnote)
                .foregroundStyle(.secondary)
                .accessibilityIdentifier("createNarrateServerEbooksMessage")
        }
    }

    @ViewBuilder
    private var discoverySourceControls: some View {
        VStack(alignment: .leading, spacing: 8) {
            Label("Discover Sources", systemImage: "sparkle.magnifyingglass")
            acquisitionDiscoveryControls
        }
        .accessibilityIdentifier("createNarrateDiscoveryPanel")
    }

    @ViewBuilder
    private var narrateRangeControls: some View {
        AppleBookCreateNarrateChapterRangeControls(
            sourcePath: sourcePath,
            selectedSourceEntry: selectedNarrateServerEbook,
            sourceStartSentence: $sourceStartSentence,
            sourceEndSentence: $sourceEndSentence,
            narrateChapterOptions: narrateChapterOptions,
            selectedNarrateStartChapterID: $selectedNarrateStartChapterID,
            selectedNarrateEndChapterID: $selectedNarrateEndChapterID,
            isLoadingNarrateChapters: isLoadingNarrateChapters,
            narrateChaptersErrorMessage: narrateChaptersErrorMessage,
            onLoadNarrateChapters: onLoadNarrateChapters
        )
    }

    private var serverEbookPicker: some View {
        Picker("Server EPUB", selection: $sourcePath) {
            Text("Manual path").tag("")
            if shouldShowCurrentServerPath {
                Text(sourcePath).tag(sourcePath)
            }
            ForEach(narrateServerEbooks, id: \.path) { entry in
                Text(AppleBookCreatePresentation.pipelineEbookPickerLabel(entry)).tag(entry.path)
            }
        }
        .disabled(isLoadingPipelineFiles)
        .accessibilityIdentifier("createNarrateServerEbookPicker")
    }

    private var narrateServerEbooks: [PipelineFileEntry] {
        AppleBookCreatePresentation.pipelineEbookEntries(from: pipelineFiles)
    }

    private var shouldShowNoServerEbooksMessage: Bool {
        pipelineFiles != nil && narrateServerEbooks.isEmpty && !isLoadingPipelineFiles
    }

    private var shouldShowServerEbooksSummary: Bool {
        pipelineFiles != nil && !narrateServerEbooks.isEmpty && !isLoadingPipelineFiles
    }

    @ViewBuilder
    private var acquisitionDiscoveryControls: some View {
        Picker("Discovery source", selection: acquisitionDiscoveryProviderBinding) {
            ForEach(discoveryProviderOptions) { option in
                Text(option.label).tag(option.id)
            }
        }
        #if os(iOS)
        .pickerStyle(.menu)
        #endif
        .disabled(isLoadingAcquisitionDiscovery || isAcquiringAcquisitionCandidate)
        .accessibilityIdentifier("createNarrateDiscoveryProviderPicker")
        TextField("Search title or filename", text: $acquisitionDiscoveryQuery)
            .textInputAutocapitalization(.never)
            .autocorrectionDisabled()
            .accessibilityIdentifier("createNarrateDiscoveryQueryField")
        Button {
            onSearchAcquisitionDiscovery(acquisitionDiscoveryQuery, acquisitionDiscoveryProvider)
        } label: {
            Label(
                isLoadingAcquisitionDiscovery ? "Searching Sources" : "Search Sources",
                systemImage: "magnifyingglass"
            )
        }
        .disabled(
            isLoadingAcquisitionDiscovery
                || isAcquiringAcquisitionCandidate
                || !isSelectedDiscoveryProviderAvailable
        )
        .accessibilityIdentifier("createNarrateDiscoverySearchButton")
        if isLoadingAcquisitionDiscovery {
            ProgressView()
                .accessibilityIdentifier("createNarrateDiscoveryProgress")
        }
        if isAcquiringAcquisitionCandidate {
            ProgressView("Acquiring EPUB")
                .accessibilityIdentifier("createNarrateDiscoveryAcquireProgress")
        }
        if let selectedDiscoveryProviderUnavailableMessage {
            Text(selectedDiscoveryProviderUnavailableMessage)
                .font(.footnote)
                .foregroundStyle(.secondary)
                .accessibilityIdentifier("createNarrateDiscoveryMessage")
        } else if let acquisitionDiscoveryErrorMessage {
            Text(acquisitionDiscoveryErrorMessage)
                .font(.footnote)
                .foregroundStyle(.secondary)
                .accessibilityIdentifier("createNarrateDiscoveryMessage")
        } else if let acquisitionProvidersErrorMessage {
            Text(acquisitionProvidersErrorMessage)
                .font(.footnote)
                .foregroundStyle(.secondary)
                .accessibilityIdentifier("createNarrateDiscoveryMessage")
        } else if shouldShowNoDiscoveryCandidatesMessage {
            Text("No EPUB sources matched this discovery search.")
                .font(.footnote)
                .foregroundStyle(.secondary)
                .accessibilityIdentifier("createNarrateDiscoveryMessage")
        }
        ForEach(discoveryEbookCandidates) { candidate in
            Button {
                onSelectAcquisitionCandidate(candidate)
            } label: {
                HStack(alignment: .top) {
                    VStack(alignment: .leading, spacing: 3) {
                        Text(candidate.title)
                            .font(.body)
                        Text(AppleBookCreatePresentation.bookDiscoveryCandidateDetail(candidate))
                            .font(.footnote)
                            .foregroundStyle(.secondary)
                    }
                    Spacer(minLength: 8)
                    Text(AppleBookCreatePresentation.bookDiscoveryCandidateAction(candidate))
                        .font(.footnote)
                        .fontWeight(.semibold)
                        .foregroundStyle(.tint)
                        .multilineTextAlignment(.trailing)
                }
            }
            .disabled(
                isAcquiringAcquisitionCandidate
                    || !AppleBookCreatePresentation.canSelectBookDiscoveryCandidate(candidate)
            )
            .accessibilityIdentifier("createNarrateDiscoveryCandidate.\(candidate.id)")
        }
    }

    private var discoveryEbookCandidates: [AcquisitionCandidate] {
        AppleBookCreatePresentation.bookDiscoveryCandidates(from: acquisitionDiscovery)
    }

    private var shouldShowNoDiscoveryCandidatesMessage: Bool {
        acquisitionDiscovery != nil && discoveryEbookCandidates.isEmpty && !isLoadingAcquisitionDiscovery
    }

    private var selectedDiscoveryProvider: AcquisitionProviderEntry? {
        acquisitionProviders.first { $0.id == acquisitionDiscoveryProvider }
    }

    private var selectedDiscoveryProviderOption: AppleBookCreateDiscoveryProviderOption? {
        discoveryProviderOptions.first { $0.id == acquisitionDiscoveryProvider }
    }

    private var discoveryProviderOptions: [AppleBookCreateDiscoveryProviderOption] {
        AppleBookCreatePresentation.bookDiscoveryProviderOptions(from: acquisitionProviders)
    }

    private var preferredDiscoveryProviderID: String? {
        AppleBookCreatePresentation.defaultDiscoveryProviderID(
            for: "book",
            defaultProviderIds: acquisitionDefaultProviderIds,
            optionIds: discoveryProviderOptions.map(\.id),
            availableOptionIds: discoveryProviderOptions.filter(\.available).map(\.id),
            fallback: "local_epub"
        )
    }

    private var acquisitionDiscoveryProviderBinding: Binding<String> {
        Binding(
            get: { acquisitionDiscoveryProvider },
            set: { providerID in
                hasUserSelectedDiscoveryProvider = true
                acquisitionDiscoveryProvider = providerID
            }
        )
    }

    private var isSelectedDiscoveryProviderAvailable: Bool {
        selectedDiscoveryProviderOption?.available != false
            && selectedDiscoveryProvider?.available != false
    }

    private var selectedDiscoveryProviderUnavailableMessage: String? {
        AppleBookCreatePresentation.bookDiscoveryProviderUnavailableMessage(
            for: selectedDiscoveryProvider,
            selectedOption: selectedDiscoveryProviderOption
        )
    }

    private var noServerEbooksMessage: String {
        let root = pipelineFiles?.booksRoot.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        guard !root.isEmpty else {
            return "No server EPUBs found. Check the backend EPUB folder and refresh."
        }
        return "No server EPUBs found in \(root). Check the backend EPUB folder and refresh."
    }

    private var serverEbooksSummaryMessage: String {
        let count = narrateServerEbooks.count
        let noun = count == 1 ? "server EPUB" : "server EPUBs"
        let root = pipelineFiles?.booksRoot.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        guard !root.isEmpty else {
            return "\(count) \(noun) loaded."
        }
        return "\(count) \(noun) loaded from \(root)."
    }

    private var selectedNarrateServerEbook: PipelineFileEntry? {
        AppleBookCreatePresentation.selectedPipelineEbook(
            sourcePath: sourcePath,
            files: pipelineFiles
        )
    }

    private var shouldShowCurrentServerPath: Bool {
        let trimmedPath = sourcePath.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmedPath.isEmpty else {
            return false
        }
        return !narrateServerEbooks.contains { $0.path == trimmedPath }
    }

    private func applyPreferredDiscoveryProviderIfNeeded(_ providerID: String?) {
        guard !didApplyBackendDiscoveryDefault,
              !hasUserSelectedDiscoveryProvider,
              let providerID,
              !providerID.isEmpty else {
            return
        }
        didApplyBackendDiscoveryDefault = true
        guard acquisitionDiscoveryProvider != providerID else {
            return
        }
        acquisitionDiscoveryProvider = providerID
    }
}

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
