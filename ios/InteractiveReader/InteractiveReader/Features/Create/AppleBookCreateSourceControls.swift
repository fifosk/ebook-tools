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
    @Binding var discoveryQuery: String
    @Binding var discoveryProvider: String
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
    @State private var hasUserSelectedDiscoveryProvider = false
    @State private var didApplyBackendDiscoveryDefault = false
    @State private var lastAutomaticDiscoverySearchSignature: String?

    var body: some View {
        sourcePanelPicker
            .task {
                applyPreferredDiscoveryProviderIfNeeded(preferredDiscoveryProviderID)
                triggerAutomaticDiscoverySearchIfReady()
            }
            .onChange(of: preferredDiscoveryProviderID ?? "") { _, providerID in
                applyPreferredDiscoveryProviderIfNeeded(providerID.nonEmptyValue)
                triggerAutomaticDiscoverySearchIfReady()
            }
            .onChange(of: discoveryProviderOptionsSignature) { _, _ in
                applyPreferredDiscoveryProviderIfNeeded(preferredDiscoveryProviderID)
                triggerAutomaticDiscoverySearchIfReady()
            }
            .onChange(of: sourcePanel) { _, _ in
                triggerAutomaticDiscoverySearchIfReady()
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
        TextField("Search title or filename", text: $discoveryQuery)
            .textInputAutocapitalization(.never)
            .autocorrectionDisabled()
            .accessibilityIdentifier("createNarrateDiscoveryQueryField")
        Button {
            onSearchAcquisitionDiscovery(discoveryQuery, acquisitionDiscoveryProvider)
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
        ForEach(acquisitionDiscoveryPolicyNotes, id: \.self) { note in
            Text(note)
                .font(.footnote)
                .foregroundStyle(.secondary)
                .accessibilityIdentifier("createNarrateDiscoveryPolicyNote")
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
        AppleBookCreatePresentation.bookDiscoveryCandidates(
            from: acquisitionDiscovery,
            providerID: acquisitionDiscoveryProvider,
            providers: acquisitionProviders
        )
    }

    private var shouldShowNoDiscoveryCandidatesMessage: Bool {
        acquisitionDiscovery != nil && discoveryEbookCandidates.isEmpty && !isLoadingAcquisitionDiscovery
    }

    private var acquisitionDiscoveryPolicyNotes: [String] {
        AppleBookCreatePresentation.discoveryPolicyNotes(from: acquisitionDiscovery)
    }

    private var selectedDiscoveryProvider: AcquisitionProviderEntry? {
        acquisitionProviders.first { $0.id == acquisitionDiscoveryProvider }
    }

    private var selectedDiscoveryProviderOption: AppleBookCreateDiscoveryProviderOption? {
        discoveryProviderOptions.first { $0.id == acquisitionDiscoveryProvider }
    }

    private var discoveryProviderOptions: [AppleBookCreateDiscoveryProviderOption] {
        AppleBookCreatePresentation.bookDiscoveryProviderOptions(
            from: acquisitionProviders,
            defaultProviderIds: acquisitionDefaultProviderIds
        )
    }

    private var preferredDiscoveryProviderID: String? {
        AppleBookCreatePresentation.defaultDiscoveryProviderID(
            for: "book",
            defaultProviderIds: acquisitionDefaultProviderIds,
            optionIds: discoveryProviderOptions.map(\.id),
            availableOptionIds: discoveryProviderOptions.filter(\.available).map(\.id),
            providers: acquisitionProviders,
            fallback: "local_epub"
        )
    }

    private var discoveryProviderOptionsSignature: String {
        discoveryProviderOptions
            .map { "\($0.id):\($0.available)" }
            .joined(separator: "|")
    }

    private var acquisitionDiscoveryProviderBinding: Binding<String> {
        Binding(
            get: { acquisitionDiscoveryProvider },
            set: { providerID in
                hasUserSelectedDiscoveryProvider = true
                acquisitionDiscoveryProvider = providerID
                triggerAutomaticDiscoverySearchIfReady(providerID: providerID, force: true)
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
        guard !hasUserSelectedDiscoveryProvider,
              let providerID,
              !providerID.isEmpty else {
            return
        }
        didApplyBackendDiscoveryDefault = true
        let currentProviderIsKnown = discoveryProviderOptions.contains {
            $0.id == acquisitionDiscoveryProvider
        }
        guard acquisitionDiscoveryProvider != providerID || !currentProviderIsKnown else {
            return
        }
        acquisitionDiscoveryProvider = providerID
    }

    private func triggerAutomaticDiscoverySearchIfReady(
        providerID: String? = nil,
        force: Bool = false
    ) {
        guard sourcePanel == .discovery else {
            return
        }
        let providerID = providerID ?? acquisitionDiscoveryProvider
        guard isDiscoveryProviderAvailable(providerID) else {
            return
        }
        let signature = [
            providerID,
            discoveryQuery.trimmingCharacters(in: .whitespacesAndNewlines),
            discoveryProviderOptionsSignature,
        ].joined(separator: "::")
        guard force || lastAutomaticDiscoverySearchSignature != signature else {
            return
        }
        lastAutomaticDiscoverySearchSignature = signature
        onSearchAcquisitionDiscovery(discoveryQuery, providerID)
    }

    private func isDiscoveryProviderAvailable(_ providerID: String) -> Bool {
        let selectedProvider = acquisitionProviders.first { $0.id == providerID }
        let selectedOption = discoveryProviderOptions.first { $0.id == providerID }
        return selectedProvider?.available != false
            && selectedOption?.available != false
    }

    private var acquisitionDiscoveryProvider: String {
        get { discoveryProvider }
        nonmutating set { discoveryProvider = newValue }
    }
}
