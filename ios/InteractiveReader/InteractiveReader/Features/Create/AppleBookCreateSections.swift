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
        #if os(iOS)
        fileImportControl(
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
        HStack {
            Button(action: onRefreshPipelineFiles) {
                Label(
                    isLoadingPipelineFiles ? "Refreshing EPUBs" : "Refresh EPUBs",
                    systemImage: "arrow.clockwise"
                )
            }
            .disabled(isLoadingPipelineFiles)
            .accessibilityIdentifier("createNarrateRefreshServerEbooksButton")

            if isLoadingPipelineFiles {
                ProgressView()
                    .accessibilityIdentifier("createNarrateServerEbooksProgress")
            }
        }
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

    @ViewBuilder
    private var subtitleSourceControls: some View {
        #if os(iOS)
        fileImportControl(
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

    #if os(iOS)
    private func fileImportControl(
        title: String,
        selectedFileName: String?,
        systemImage: String,
        buttonIdentifier: String,
        labelIdentifier: String,
        action: @escaping () -> Void
    ) -> some View {
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
    #endif
}

struct AppleBookCreateNarrationSection: View {
    let creationMode: AppleCreateMode
    @Binding var inputLanguage: AppleBookCreateLanguage
    @Binding var targetLanguage: AppleBookCreateLanguage
    @Binding var additionalTargetLanguages: String
    @Binding var voice: AppleBookCreateVoiceOption
    @Binding var targetVoice: AppleBookCreateVoiceOption?
    @Binding var languageVoiceOverrides: [String: String]
    let availableInputLanguages: [AppleBookCreateLanguage]
    let availableTargetLanguages: [AppleBookCreateLanguage]
    let availableVoices: [AppleBookCreateVoiceOption]
    let availableTargetVoices: [AppleBookCreateVoiceOption]
    let languageVoiceOptions: [String: [AppleBookCreateVoiceOption]]
    let targetLanguagesForVoiceOverrides: [String]
    let isLoadingVoiceInventory: Bool
    let voiceInventoryErrorMessage: String?
    let voicePreviewStates: [String: AppleVoicePreviewState]
    let voicePreviewErrorMessages: [String: String]
    let onRefreshVoiceInventory: () -> Void
    let onPreviewVoice: (String, String, AppleBookCreateVoiceOption) -> Void

    var body: some View {
        Section(creationMode == .subtitleJob ? "Languages" : "Narration") {
            #if os(tvOS)
            Picker("Input", selection: $inputLanguage) {
                ForEach(availableInputLanguages) { language in
                    Text(language.label).tag(language)
                }
            }
            .accessibilityIdentifier("createBookInputLanguagePicker")

            Picker("Target", selection: $targetLanguage) {
                ForEach(availableTargetLanguages) { language in
                    Text(language.label).tag(language)
                }
            }
            .accessibilityIdentifier("createBookTargetLanguagePicker")
            #else
            AppleBookCreateLanguageSelector(
                title: "Input",
                selection: $inputLanguage,
                options: availableInputLanguages,
                accessibilityIdentifier: "createBookInputLanguagePicker"
            )

            AppleBookCreateLanguageSelector(
                title: "Target",
                selection: $targetLanguage,
                options: availableTargetLanguages,
                accessibilityIdentifier: "createBookTargetLanguagePicker"
            )
            #endif

            if creationMode == .generatedBook || creationMode == .narrateEbook {
                TextField("Additional targets", text: $additionalTargetLanguages)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                    .accessibilityIdentifier("createBookAdditionalTargetLanguagesField")
            }

            if creationMode != .subtitleJob {
                Picker("Voice", selection: $voice) {
                    ForEach(availableVoices) { option in
                        Text(option.label).tag(option)
                    }
                }
                .accessibilityIdentifier("createBookVoicePicker")

                voicePreviewControl(
                    language: inputLanguage.backendValue,
                    label: inputLanguage.label,
                    selectedVoice: voice,
                    buttonIdentifier: "createBookVoicePreviewButton",
                    errorIdentifier: "createBookVoicePreviewErrorLabel"
                )

                if creationMode == .generatedBook || creationMode == .narrateEbook {
                    Picker("Target voice", selection: $targetVoice) {
                        Text("Same as voice").tag(nil as AppleBookCreateVoiceOption?)
                        ForEach(availableTargetVoices) { option in
                            Text(option.label).tag(Optional(option))
                        }
                    }
                    .accessibilityIdentifier("createBookTargetVoicePicker")

                    voicePreviewControl(
                        language: targetLanguage.backendValue,
                        label: targetLanguage.label,
                        selectedVoice: targetVoice ?? voice,
                        buttonIdentifier: "createBookTargetVoicePreviewButton",
                        errorIdentifier: "createBookTargetVoicePreviewErrorLabel"
                    )

                    if !targetLanguagesForVoiceOverrides.isEmpty {
                        ForEach(targetLanguagesForVoiceOverrides, id: \.self) { language in
                            let options = languageVoiceOptions[language] ?? availableTargetVoices
                            let selectedOverride = languageVoiceOverrides[language]
                                .flatMap(AppleBookCreateVoiceOption.init(backendValue:)) ?? targetVoice ?? voice
                            Picker(
                                "\(language) voice",
                                selection: voiceOverrideBinding(for: language)
                            ) {
                                Text("Default").tag("")
                                ForEach(options) { option in
                                    Text(option.label).tag(option.backendValue)
                                }
                            }
                            .accessibilityIdentifier("createBookVoiceOverridePicker-\(language)")

                            voicePreviewControl(
                                language: language,
                                label: language,
                                selectedVoice: selectedOverride,
                                buttonIdentifier: "createBookVoiceOverridePreviewButton-\(language)",
                                errorIdentifier: "createBookVoiceOverridePreviewErrorLabel-\(language)"
                            )
                        }
                    }
                }

                voiceInventoryStatusControl
            }
        }
    }

    @ViewBuilder
    private var voiceInventoryStatusControl: some View {
        if isLoadingVoiceInventory {
            Label("Loading voice inventory", systemImage: "arrow.triangle.2.circlepath")
                .foregroundStyle(.secondary)
                .accessibilityIdentifier("createBookVoiceInventoryLoadingLabel")
        } else if let voiceInventoryErrorMessage {
            Text(voiceInventoryErrorMessage)
                .font(.footnote)
                .foregroundStyle(.secondary)
                .accessibilityIdentifier("createBookVoiceInventoryErrorLabel")
            Button(action: onRefreshVoiceInventory) {
                Label("Retry Voices", systemImage: "arrow.clockwise")
            }
            .accessibilityIdentifier("createBookVoiceInventoryRetryButton")
        }
    }

    private func voicePreviewControl(
        language: String,
        label: String,
        selectedVoice: AppleBookCreateVoiceOption,
        buttonIdentifier: String,
        errorIdentifier: String
    ) -> some View {
        let key = AppleBookCreatePresentation.voicePreviewKey(language: language)
        let state = voicePreviewStates[key] ?? .idle
        return VStack(alignment: .leading, spacing: 6) {
            HStack {
                Button {
                    onPreviewVoice(language, label, selectedVoice)
                } label: {
                    Label(voicePreviewTitle(for: state), systemImage: voicePreviewSystemImage(for: state))
                }
                .disabled(state == .loading)
                .accessibilityIdentifier(buttonIdentifier)

                if state == .loading {
                    ProgressView()
                        .accessibilityIdentifier("\(buttonIdentifier)-progress")
                }
            }

            if let message = voicePreviewErrorMessages[key] {
                Text(message)
                    .font(.footnote)
                    .foregroundStyle(.secondary)
                    .accessibilityIdentifier(errorIdentifier)
            }
        }
    }

    private func voicePreviewTitle(for state: AppleVoicePreviewState) -> String {
        switch state {
        case .idle:
            return "Preview Voice"
        case .loading:
            return "Loading Preview"
        case .playing:
            return "Playing Preview"
        }
    }

    private func voicePreviewSystemImage(for state: AppleVoicePreviewState) -> String {
        switch state {
        case .idle:
            return "play.circle"
        case .loading:
            return "hourglass"
        case .playing:
            return "speaker.wave.2"
        }
    }

    private func voiceOverrideBinding(for language: String) -> Binding<String> {
        Binding(
            get: {
                languageVoiceOverrides[language] ?? ""
            },
            set: { newValue in
                let normalizedValue = newValue.trimmingCharacters(in: .whitespacesAndNewlines)
                if normalizedValue.isEmpty {
                    languageVoiceOverrides.removeValue(forKey: language)
                } else {
                    languageVoiceOverrides[language] = normalizedValue
                }
            }
        )
    }
}

#if !os(tvOS)
private struct AppleBookCreateLanguageSelector: View {
    let title: String
    @Binding var selection: AppleBookCreateLanguage
    let options: [AppleBookCreateLanguage]
    let accessibilityIdentifier: String

    @State private var selectedLanguage: AppleBookCreateLanguage?
    @State private var searchText = ""

    private var filteredOptions: [AppleBookCreateLanguage] {
        let query = searchText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !query.isEmpty else { return options }
        return options.filter { language in
            language.label.localizedCaseInsensitiveContains(query)
                || language.backendValue.localizedCaseInsensitiveContains(query)
        }
    }

    var body: some View {
        Button {
            searchText = ""
            selectedLanguage = selection
        } label: {
            HStack {
                Text(title)
                Spacer()
                VStack(alignment: .trailing, spacing: 2) {
                    Text(selection.label)
                        .foregroundStyle(.secondary)
                    Text("\(options.count) available")
                        .font(.caption2)
                        .foregroundStyle(.tertiary)
                }
            }
        }
        .accessibilityIdentifier(accessibilityIdentifier)
        .accessibilityValue("\(selection.label), \(options.count) available")
        .sheet(item: $selectedLanguage) { _ in
            NavigationStack {
                List(filteredOptions) { language in
                    Button {
                        selection = language
                        searchText = ""
                        selectedLanguage = nil
                    } label: {
                        HStack {
                            Text(language.label)
                            Spacer()
                            if language == selection {
                                Image(systemName: "checkmark")
                                    .foregroundStyle(.accent)
                            }
                        }
                    }
                    .accessibilityIdentifier("\(accessibilityIdentifier).\(language.id)")
                }
                .searchable(text: $searchText, prompt: "Search Languages")
                .navigationTitle(title)
                #if os(iOS)
                .navigationBarTitleDisplayMode(.inline)
                #endif
                .toolbar {
                    ToolbarItem(placement: .cancellationAction) {
                        Button("Done") {
                            searchText = ""
                            selectedLanguage = nil
                        }
                    }
                }
            }
        }
    }
}
#endif

struct AppleBookCreateSubtitleMetadataControls: View {
    let sourceName: String
    @Binding var lookupSourceName: String
    let isLoading: Bool
    let isClearingCache: Bool
    @Binding var showPosterURL: String
    @Binding var episodeStillURL: String
    let message: String?
    let errorMessage: String?
    @Binding var jobLabel: String
    @Binding var showName: String
    @Binding var tmdbId: String
    @Binding var imdbId: String
    @Binding var season: String
    @Binding var episode: String
    @Binding var episodeName: String
    @Binding var airdate: String
    @Binding var advancedMetadataJSON: String
    let advancedMetadataErrorMessage: String?
    let onLookup: () -> Void
    let onRefresh: () -> Void
    let onClear: () -> Void
    let onClearCache: () -> Void
    let onApplyAdvancedMetadataJSON: () -> Void
    let onSyncAdvancedMetadataJSON: () -> Void

    var body: some View {
        if sourceName.isEmpty {
            Label("Choose a subtitle to load TV metadata.", systemImage: "captions.bubble")
                .font(.footnote)
                .foregroundStyle(.secondary)
                .accessibilityIdentifier("createSubtitleMetadataEmpty")
        } else {
            TextField("Lookup filename", text: $lookupSourceName)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
                .accessibilityIdentifier("createSubtitleMetadataLookupField")

            HStack(spacing: 12) {
                Button(action: onLookup) {
                    Label(isLoading ? "Looking up" : "Lookup", systemImage: isLoading ? "hourglass" : "tv")
                }
                .disabled(isLoading || lookupSourceName.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                .accessibilityIdentifier("createSubtitleMetadataLookupButton")

                Button(action: onRefresh) {
                    Label("Refresh", systemImage: "arrow.clockwise")
                }
                .disabled(isLoading || lookupSourceName.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                .accessibilityIdentifier("createSubtitleMetadataRefreshButton")

                Button(action: onClearCache) {
                    Label(
                        isClearingCache ? "Clearing Cache" : "Clear Cache",
                        systemImage: isClearingCache ? "hourglass" : "trash"
                    )
                }
                .disabled(
                    isLoading ||
                    isClearingCache ||
                    lookupSourceName.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
                )
                .accessibilityIdentifier("createSubtitleMetadataClearCacheButton")

                Button(action: onClear) {
                    Label("Clear", systemImage: "xmark.circle")
                }
                .disabled(isLoading || isClearingCache)
                .accessibilityIdentifier("createSubtitleMetadataClearButton")
            }
        }

        AppleBookCreateMetadataArtworkPreview(
            posterURL: showPosterURL,
            stillURL: episodeStillURL,
            posterLabel: showName.isEmpty ? "Show poster" : "\(showName) poster",
            stillLabel: episodeName.isEmpty ? "Episode still" : "\(episodeName) still"
        )

        if let message, !message.isEmpty {
            Label(message, systemImage: "checkmark.circle")
                .font(.footnote)
                .foregroundStyle(.secondary)
                .accessibilityIdentifier("createSubtitleMetadataStatus")
        }
        if let errorMessage, !errorMessage.isEmpty {
            Label(errorMessage, systemImage: "exclamationmark.triangle")
                .font(.footnote)
                .foregroundStyle(.red)
                .accessibilityIdentifier("createSubtitleMetadataError")
        }

        TextField("Job label", text: $jobLabel)
            .textInputAutocapitalization(.words)
            .autocorrectionDisabled()
            .accessibilityIdentifier("createSubtitleMetadataJobLabelField")
        TextField("Show title", text: $showName)
            .textInputAutocapitalization(.words)
            .autocorrectionDisabled()
            .accessibilityIdentifier("createSubtitleMetadataShowField")
        TextField("TMDB ID", text: $tmdbId)
            .textInputAutocapitalization(.never)
            .autocorrectionDisabled()
            .accessibilityIdentifier("createSubtitleMetadataTmdbIdField")
        TextField("IMDb ID", text: $imdbId)
            .textInputAutocapitalization(.never)
            .autocorrectionDisabled()
            .accessibilityIdentifier("createSubtitleMetadataImdbIdField")
        TextField("Season", text: $season)
            .textInputAutocapitalization(.never)
            .autocorrectionDisabled()
            .accessibilityIdentifier("createSubtitleMetadataSeasonField")
        TextField("Episode", text: $episode)
            .textInputAutocapitalization(.never)
            .autocorrectionDisabled()
            .accessibilityIdentifier("createSubtitleMetadataEpisodeNumberField")
        TextField("Episode title", text: $episodeName)
            .textInputAutocapitalization(.sentences)
            .autocorrectionDisabled()
            .accessibilityIdentifier("createSubtitleMetadataEpisodeTitleField")
        TextField("Airdate", text: $airdate)
            .textInputAutocapitalization(.never)
            .autocorrectionDisabled()
            .accessibilityIdentifier("createSubtitleMetadataAirdateField")

        #if os(tvOS)
        Group {
            Text("Artwork")
                .font(.headline)
            subtitleArtworkFields
        }
        .accessibilityIdentifier("createSubtitleMetadataArtworkDisclosure")
        #else
        DisclosureGroup("Artwork") {
            subtitleArtworkFields
        }
        .accessibilityIdentifier("createSubtitleMetadataArtworkDisclosure")
        #endif

        AppleBookCreateAdvancedMetadataJSONEditor(
            text: $advancedMetadataJSON,
            errorMessage: advancedMetadataErrorMessage,
            disclosureIdentifier: "createSubtitleAdvancedMetadataDisclosure",
            textEditorIdentifier: "createSubtitleAdvancedMetadataJSONEditor",
            applyIdentifier: "createSubtitleAdvancedMetadataApplyButton",
            syncIdentifier: "createSubtitleAdvancedMetadataSyncButton",
            errorIdentifier: "createSubtitleAdvancedMetadataJSONError",
            onApply: onApplyAdvancedMetadataJSON,
            onSync: onSyncAdvancedMetadataJSON
        )
    }

    private var subtitleArtworkFields: some View {
        Group {
            TextField("Show poster URL", text: $showPosterURL)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
                .accessibilityIdentifier("createSubtitleMetadataPosterUrlField")
            TextField("Episode still URL", text: $episodeStillURL)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
                .accessibilityIdentifier("createSubtitleMetadataStillUrlField")
        }
    }
}

struct AppleBookCreateYoutubeMetadataControls: View {
    let isLoadingTvMetadata: Bool
    let isLoadingYoutubeMetadata: Bool
    let isClearingTvMetadataCache: Bool
    let isClearingYoutubeMetadataCache: Bool
    let canClearTvMetadataCache: Bool
    let canClearYoutubeMetadataCache: Bool
    @Binding var tvPosterURL: String
    @Binding var tvEpisodeStillURL: String
    @Binding var youtubeThumbnailURL: String
    let message: String?
    let errorMessage: String?
    @Binding var title: String
    @Binding var channel: String
    @Binding var showName: String
    @Binding var tmdbId: String
    @Binding var imdbId: String
    @Binding var episodeName: String
    @Binding var advancedMetadataJSON: String
    let advancedMetadataErrorMessage: String?
    let onLoadTvMetadata: () -> Void
    let onLoadYoutubeMetadata: () -> Void
    let onClearTvMetadataCache: () -> Void
    let onClearYoutubeMetadataCache: () -> Void
    let onApplyAdvancedMetadataJSON: () -> Void
    let onSyncAdvancedMetadataJSON: () -> Void

    var body: some View {
        HStack(spacing: 12) {
            Button(action: onLoadTvMetadata) {
                Label(
                    isLoadingTvMetadata ? "Loading TV" : "Load TV",
                    systemImage: isLoadingTvMetadata ? "hourglass" : "tv"
                )
            }
            .disabled(isLoadingTvMetadata || isLoadingYoutubeMetadata)
            .accessibilityIdentifier("createYoutubeLoadTvMetadataButton")

            Button(action: onLoadYoutubeMetadata) {
                Label(
                    isLoadingYoutubeMetadata ? "Loading YouTube" : "Load YouTube",
                    systemImage: isLoadingYoutubeMetadata ? "hourglass" : "play.rectangle"
                )
            }
            .disabled(isLoadingTvMetadata || isLoadingYoutubeMetadata)
            .accessibilityIdentifier("createYoutubeLoadYoutubeMetadataButton")
        }

        HStack(spacing: 12) {
            Button(action: onClearTvMetadataCache) {
                Label(
                    isClearingTvMetadataCache ? "Clearing TV" : "Clear TV Cache",
                    systemImage: isClearingTvMetadataCache ? "hourglass" : "trash"
                )
            }
            .disabled(
                !canClearTvMetadataCache ||
                isLoadingTvMetadata ||
                isLoadingYoutubeMetadata ||
                isClearingTvMetadataCache
            )
            .accessibilityIdentifier("createYoutubeClearTvMetadataCacheButton")

            Button(action: onClearYoutubeMetadataCache) {
                Label(
                    isClearingYoutubeMetadataCache ? "Clearing YouTube" : "Clear YouTube Cache",
                    systemImage: isClearingYoutubeMetadataCache ? "hourglass" : "trash"
                )
            }
            .disabled(
                !canClearYoutubeMetadataCache ||
                isLoadingTvMetadata ||
                isLoadingYoutubeMetadata ||
                isClearingYoutubeMetadataCache
            )
            .accessibilityIdentifier("createYoutubeClearYoutubeMetadataCacheButton")
        }

        AppleBookCreateMetadataArtworkPreview(
            posterURL: tvPosterURL,
            stillURL: tvEpisodeStillURL,
            thumbnailURL: youtubeThumbnailURL,
            posterLabel: showName.isEmpty ? "Series poster" : "\(showName) poster",
            stillLabel: episodeName.isEmpty ? "Episode still" : "\(episodeName) still",
            thumbnailLabel: title.isEmpty ? "YouTube thumbnail" : "\(title) thumbnail"
        )

        if let message, !message.isEmpty {
            Label(message, systemImage: "checkmark.circle")
                .font(.footnote)
                .foregroundStyle(.secondary)
                .accessibilityIdentifier("createYoutubeMetadataStatus")
        }
        if let errorMessage, !errorMessage.isEmpty {
            Label(errorMessage, systemImage: "exclamationmark.triangle")
                .font(.footnote)
                .foregroundStyle(.red)
                .accessibilityIdentifier("createYoutubeMetadataError")
        }

        TextField("YouTube title", text: $title)
            .textInputAutocapitalization(.sentences)
            .autocorrectionDisabled()
            .accessibilityIdentifier("createYoutubeMetadataTitleField")
        TextField("Channel", text: $channel)
            .textInputAutocapitalization(.words)
            .autocorrectionDisabled()
            .accessibilityIdentifier("createYoutubeMetadataChannelField")
        TextField("Series", text: $showName)
            .textInputAutocapitalization(.words)
            .autocorrectionDisabled()
            .accessibilityIdentifier("createYoutubeMetadataSeriesField")
        TextField("TMDB ID", text: $tmdbId)
            .textInputAutocapitalization(.never)
            .autocorrectionDisabled()
            .accessibilityIdentifier("createYoutubeMetadataTmdbIdField")
        TextField("IMDb ID", text: $imdbId)
            .textInputAutocapitalization(.never)
            .autocorrectionDisabled()
            .accessibilityIdentifier("createYoutubeMetadataImdbIdField")
        TextField("Episode", text: $episodeName)
            .textInputAutocapitalization(.sentences)
            .autocorrectionDisabled()
            .accessibilityIdentifier("createYoutubeMetadataEpisodeField")

        #if os(tvOS)
        Group {
            Text("Artwork")
                .font(.headline)
            youtubeArtworkFields
        }
        .accessibilityIdentifier("createYoutubeMetadataArtworkDisclosure")
        #else
        DisclosureGroup("Artwork") {
            youtubeArtworkFields
        }
        .accessibilityIdentifier("createYoutubeMetadataArtworkDisclosure")
        #endif

        AppleBookCreateAdvancedMetadataJSONEditor(
            text: $advancedMetadataJSON,
            errorMessage: advancedMetadataErrorMessage,
            disclosureIdentifier: "createYoutubeAdvancedMetadataDisclosure",
            textEditorIdentifier: "createYoutubeAdvancedMetadataJSONEditor",
            applyIdentifier: "createYoutubeAdvancedMetadataApplyButton",
            syncIdentifier: "createYoutubeAdvancedMetadataSyncButton",
            errorIdentifier: "createYoutubeAdvancedMetadataJSONError",
            onApply: onApplyAdvancedMetadataJSON,
            onSync: onSyncAdvancedMetadataJSON
        )
    }

    private var youtubeArtworkFields: some View {
        Group {
            TextField("Series poster URL", text: $tvPosterURL)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
                .accessibilityIdentifier("createYoutubeMetadataPosterUrlField")
            TextField("Episode still URL", text: $tvEpisodeStillURL)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
                .accessibilityIdentifier("createYoutubeMetadataStillUrlField")
            TextField("YouTube thumbnail URL", text: $youtubeThumbnailURL)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
                .accessibilityIdentifier("createYoutubeMetadataThumbnailUrlField")
        }
    }
}
