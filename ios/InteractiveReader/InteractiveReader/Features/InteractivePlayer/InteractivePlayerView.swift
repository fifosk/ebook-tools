import AVFoundation
import SwiftUI

private enum InteractivePlayerFocusArea: Hashable {
    case controls
    case transcript
}

struct InteractivePlayerView: View {
    @ObservedObject var viewModel: InteractivePlayerViewModel
    @ObservedObject var audioCoordinator: AudioPlayerCoordinator
    let showImageReel: Binding<Bool>?
    let showsScrubber: Bool
    let linguistInputLanguage: String
    let linguistLookupLanguage: String
    @State private var readingBedCoordinator = AudioPlayerCoordinator()
    @State private var readingBedEnabled = true
    @State private var scrubbedTime: Double?
    @State private var visibleTracks: Set<TextPlayerVariantKind> = [.original, .translation, .transliteration]
    @State private var selectedSentenceID: Int?
    @State private var linguistSelection: TextPlayerWordSelection?
    @State private var linguistBubble: MyLinguistBubbleState?
    @State private var linguistLookupTask: Task<Void, Never>?
    @State private var linguistSpeechTask: Task<Void, Never>?
    @StateObject private var pronunciationSpeaker = PronunciationSpeaker()
    #if os(tvOS)
    @State private var didSetInitialFocus = false
    #endif
    @FocusState private var focusedArea: InteractivePlayerFocusArea?

    private let playbackRates: [Double] = [0.7, 0.85, 1.0, 1.15, 1.3, 1.5]
    private let readingBedVolume: Double = 0.08

    init(
        viewModel: InteractivePlayerViewModel,
        audioCoordinator: AudioPlayerCoordinator,
        showImageReel: Binding<Bool>? = nil,
        showsScrubber: Bool = true,
        linguistInputLanguage: String = "",
        linguistLookupLanguage: String = "English"
    ) {
        self._viewModel = ObservedObject(wrappedValue: viewModel)
        self._audioCoordinator = ObservedObject(wrappedValue: audioCoordinator)
        self.showImageReel = showImageReel
        self.showsScrubber = showsScrubber
        self.linguistInputLanguage = linguistInputLanguage
        self.linguistLookupLanguage = linguistLookupLanguage
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            if let summary = viewModel.highlightingSummary {
                Text(summary)
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }

            if let chunk = viewModel.selectedChunk {
                interactiveContent(for: chunk)
            } else {
                Text("No interactive chunks were returned for this job.")
                    .foregroundStyle(.secondary)
            }
        }
        .padding(.horizontal)
        .padding(.vertical, 12)
        .onAppear {
            guard let chunk = viewModel.selectedChunk else { return }
            applyDefaultTrackSelection(for: chunk)
            syncSelectedSentence(for: chunk)
            configureReadingBed()
            #if os(tvOS)
            if !didSetInitialFocus {
                didSetInitialFocus = true
                Task { @MainActor in
                    focusedArea = .transcript
                }
            }
            #endif
        }
        .onChange(of: viewModel.selectedChunk?.id) { _, _ in
            guard let chunk = viewModel.selectedChunk else { return }
            clearLinguistState()
            applyDefaultTrackSelection(for: chunk)
            syncSelectedSentence(for: chunk)
        }
        .onChange(of: viewModel.highlightingTime) { _, _ in
            guard focusedArea != .controls else { return }
            guard let chunk = viewModel.selectedChunk else { return }
            if audioCoordinator.isPlaying {
                return
            }
            syncSelectedSentence(for: chunk)
        }
        .onChange(of: viewModel.readingBedURL) { _, _ in
            configureReadingBed()
        }
        .onChange(of: readingBedEnabled) { _, _ in
            updateReadingBedPlayback()
        }
        .onChange(of: audioCoordinator.isPlaying) { _, isPlaying in
            updateReadingBedPlayback()
            if isPlaying {
                clearLinguistState()
            }
        }
        .onChange(of: visibleTracks) { _, _ in
            clearLinguistState()
        }
        .onDisappear {
            readingBedCoordinator.reset()
            clearLinguistState()
        }
        #if os(tvOS)
        .onPlayPauseCommand {
            audioCoordinator.togglePlayback()
        }
        .onMoveCommand { direction in
            guard focusedArea == .transcript else { return }
            guard let chunk = viewModel.selectedChunk else { return }
            switch direction {
            case .left:
                if audioCoordinator.isPlaying {
                    viewModel.skipSentence(forward: false)
                } else {
                    handleWordNavigation(-1, in: chunk)
                }
            case .right:
                if audioCoordinator.isPlaying {
                    viewModel.skipSentence(forward: true)
                } else {
                    handleWordNavigation(1, in: chunk)
                }
            case .up:
                if !audioCoordinator.isPlaying {
                    handleTrackNavigation(-1, in: chunk)
                }
            case .down:
                if !audioCoordinator.isPlaying {
                    handleTrackNavigation(1, in: chunk)
                }
            default:
                break
            }
        }
        .onTapGesture {
            guard focusedArea == .transcript else { return }
            guard let chunk = viewModel.selectedChunk else { return }
            handleLinguistLookup(in: chunk)
        }
        #endif
    }

    @ViewBuilder
    private func interactiveContent(for chunk: InteractiveChunk) -> some View {
        let transcriptSentences = transcriptSentences(for: chunk)
        controlBar(chunk)
        Divider()
        InteractiveTranscriptView(
            viewModel: viewModel,
            audioCoordinator: audioCoordinator,
            sentences: transcriptSentences,
            selection: linguistSelection,
            bubble: linguistBubble,
            onNavigateWord: { delta in
                handleWordNavigation(delta, in: chunk)
            },
            onNavigateTrack: { delta in
                handleTrackNavigation(delta, in: chunk)
            },
            onLookup: {
                handleLinguistLookup(in: chunk)
            },
            onCloseBubble: {
                closeLinguistBubble()
            }
        )
        #if os(tvOS)
        .focusable(true)
        .focused($focusedArea, equals: .transcript)
        #endif
    }

    @ViewBuilder
    private func controlBar(_ chunk: InteractiveChunk) -> some View {
        let playbackTime = viewModel.playbackTime(for: chunk)
        let playbackDuration = viewModel.playbackDuration(for: chunk) ?? audioCoordinator.duration
        VStack(alignment: .leading, spacing: 8) {
            HStack(alignment: .center, spacing: 12) {
                chapterPicker()
                sentencePicker(for: chunk)
                textTrackPicker(for: chunk)
                audioPicker(for: chunk)
                readingBedPicker()
                speedPicker()
                Spacer(minLength: 8)
                PlaybackButtonRow(
                    coordinator: audioCoordinator,
                    focusBinding: $focusedArea,
                    onPrevious: { viewModel.skipSentence(forward: false) },
                    onNext: { viewModel.skipSentence(forward: true) }
                )
            }
            #if os(tvOS)
            .transaction { transaction in
                transaction.disablesAnimations = true
            }
            #endif
            if let range = chunk.rangeDescription {
                Text(range)
                    .font(.caption2)
                    .foregroundStyle(.secondary)
            }
            if showsScrubber {
                PlaybackScrubberView(
                    coordinator: audioCoordinator,
                    currentTime: playbackTime,
                    duration: playbackDuration,
                    scrubbedTime: $scrubbedTime,
                    onSeek: { target in
                        viewModel.seekPlayback(to: target, in: chunk)
                    }
                )
            }
        }
    }

    private func menuLabel(_ text: String, leadingSystemImage: String? = nil) -> some View {
        HStack(spacing: 6) {
            if let leadingSystemImage {
                Image(systemName: leadingSystemImage)
                    .font(.caption2)
            }
            Text(text)
                .font(.callout)
                .lineLimit(1)
                .truncationMode(.tail)
                .minimumScaleFactor(0.85)
            Image(systemName: "chevron.down")
                .font(.caption2)
                .foregroundStyle(.secondary)
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 6)
    }

    @ViewBuilder
    private func chapterPicker() -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text("Chapter")
                .font(.caption)
                .foregroundStyle(.secondary)
            Picker("Chapter", selection: viewModel.chunkBinding()) {
                let chunks = viewModel.jobContext?.chunks ?? []
                ForEach(Array(chunks.enumerated()), id: \.element.id) { index, chunk in
                    Text("Chapter \(index + 1)").tag(chunk.id)
                }
            }
            .pickerStyle(.menu)
            .focused($focusedArea, equals: .controls)
        }
    }

    @ViewBuilder
    private func sentencePicker(for chunk: InteractiveChunk) -> some View {
        let entries = sentenceEntries(for: chunk)
        VStack(alignment: .leading, spacing: 4) {
            Text("Sentence")
                .font(.caption)
                .foregroundStyle(.secondary)
            if entries.isEmpty {
                Text("No sentences")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            } else {
                Picker("Sentence", selection: sentenceBinding(entries: entries, chunk: chunk)) {
                    ForEach(entries) { entry in
                        Text(entry.label).tag(entry.id)
                    }
                }
                .pickerStyle(.menu)
                .focused($focusedArea, equals: .controls)
            }
        }
    }

    @ViewBuilder
    private func textTrackPicker(for chunk: InteractiveChunk) -> some View {
        let available = availableTracks(for: chunk)
        let showImageToggle = hasImageReel(for: chunk) && showImageReel != nil
        VStack(alignment: .leading, spacing: 4) {
            Text("Text")
                .font(.caption)
                .foregroundStyle(.secondary)
            Menu {
                ForEach(available, id: \.self) { kind in
                    trackToggle(label: trackLabel(kind), kind: kind)
                }
                if showImageToggle {
                    imageReelToggle()
                }
            } label: {
                menuLabel(textTrackSummary(for: chunk))
            }
            .buttonStyle(.bordered)
            .controlSize(.small)
            .focused($focusedArea, equals: .controls)
        }
    }

    @ViewBuilder
    private func audioPicker(for chunk: InteractiveChunk) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text("Audio")
                .font(.caption)
                .foregroundStyle(.secondary)
            if !chunk.audioOptions.isEmpty {
                #if os(tvOS)
                Menu {
                    ForEach(chunk.audioOptions) { option in
                        Button(option.label) {
                            viewModel.selectAudioTrack(id: option.id)
                        }
                    }
                } label: {
                    menuLabel(selectedAudioLabel(for: chunk))
                }
                .buttonStyle(.bordered)
                .controlSize(.small)
                .focused($focusedArea, equals: .controls)
                #else
                Picker("Audio track", selection: viewModel.audioTrackBinding(defaultID: chunk.audioOptions.first?.id)) {
                    ForEach(chunk.audioOptions) { option in
                        Text(option.label).tag(option.id)
                    }
                }
                .pickerStyle(.menu)
                .focused($focusedArea, equals: .controls)
                #endif
            } else {
                Text("No audio")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
    }

    private func selectedAudioLabel(for chunk: InteractiveChunk) -> String {
        guard let selectedID = viewModel.selectedAudioTrackID else {
            return chunk.audioOptions.first?.label ?? "Audio Mode"
        }
        return chunk.audioOptions.first(where: { $0.id == selectedID })?.label ?? "Audio Mode"
    }

    @ViewBuilder
    private func speedPicker() -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text("Speed")
                .font(.caption)
                .foregroundStyle(.secondary)
            Menu {
                ForEach(playbackRates, id: \.self) { rate in
                    Button {
                        audioCoordinator.setPlaybackRate(rate)
                    } label: {
                        if isCurrentRate(rate) {
                            Label(playbackRateLabel(rate), systemImage: "checkmark")
                        } else {
                            Text(playbackRateLabel(rate))
                        }
                    }
                }
            } label: {
                menuLabel(playbackRateLabel(audioCoordinator.playbackRate))
            }
            .buttonStyle(.bordered)
            .controlSize(.small)
            .focused($focusedArea, equals: .controls)
        }
    }

    @ViewBuilder
    private func readingBedPicker() -> some View {
        if viewModel.readingBedURL != nil {
            let bedLabel = selectedReadingBedLabel
            VStack(alignment: .leading, spacing: 4) {
                Text("Music")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                Menu {
                    Button(action: toggleReadingBed) {
                        if readingBedEnabled {
                            Label("Music On", systemImage: "checkmark")
                        } else {
                            Text("Music Off")
                        }
                    }
                    Divider()
                    Button {
                        viewModel.selectReadingBed(id: nil)
                    } label: {
                        if viewModel.selectedReadingBedID == nil {
                            Label("Default", systemImage: "checkmark")
                        } else {
                            Text("Default")
                        }
                    }
                    ForEach(viewModel.readingBedCatalog?.beds ?? []) { bed in
                        let label = bed.label.isEmpty ? bed.id : bed.label
                        Button {
                            viewModel.selectReadingBed(id: bed.id)
                        } label: {
                            if bed.id == viewModel.selectedReadingBedID {
                                Label(label, systemImage: "checkmark")
                            } else {
                                Text(label)
                            }
                        }
                    }
                } label: {
                    menuLabel(
                        readingBedSummary(label: bedLabel),
                        leadingSystemImage: readingBedEnabled ? "music.note.list" : "music.note"
                    )
                }
                .buttonStyle(.bordered)
                .controlSize(.small)
                .focused($focusedArea, equals: .controls)
            }
        }
    }

    private func toggleReadingBed() {
        withAnimation(.none) {
            readingBedEnabled.toggle()
        }
    }

    private var selectedReadingBedLabel: String {
        if let selectedID = viewModel.selectedReadingBedID,
           let beds = viewModel.readingBedCatalog?.beds,
           let match = beds.first(where: { $0.id == selectedID }) {
            return match.label.isEmpty ? match.id : match.label
        }
        return "Default"
    }

    private func readingBedSummary(label: String) -> String {
        let state = readingBedEnabled ? "On" : "Off"
        if label.isEmpty {
            return state
        }
        return "\(state) / \(label)"
    }

    private func configureReadingBed() {
        readingBedCoordinator.setLooping(true)
        readingBedCoordinator.setVolume(readingBedVolume)
        updateReadingBedPlayback()
    }

    private func updateReadingBedPlayback() {
        guard readingBedEnabled, let url = viewModel.readingBedURL else {
            readingBedCoordinator.pause()
            return
        }
        guard audioCoordinator.isPlaying else {
            readingBedCoordinator.pause()
            return
        }
        if readingBedCoordinator.activeURL != url {
            readingBedCoordinator.load(url: url, autoPlay: true)
        } else if !readingBedCoordinator.isPlaying {
            readingBedCoordinator.play()
        }
    }

    private func trackLabel(_ kind: TextPlayerVariantKind) -> String {
        switch kind {
        case .original:
            return "Original"
        case .transliteration:
            return "Transliteration"
        case .translation:
            return "Translation"
        }
    }

    private func trackSummaryLabel(_ kind: TextPlayerVariantKind) -> String {
        switch kind {
        case .original:
            return "Original"
        case .transliteration:
            return "Translit"
        case .translation:
            return "Translation"
        }
    }

    private func trackToggle(label: String, kind: TextPlayerVariantKind) -> some View {
        Button {
            toggleTrack(kind)
        } label: {
            if visibleTracks.contains(kind) {
                Label(label, systemImage: "checkmark")
            } else {
                Text(label)
            }
        }
    }

    private func imageReelToggle() -> some View {
        let isEnabled = showImageReel?.wrappedValue ?? false
        return Button {
            if let showImageReel {
                showImageReel.wrappedValue.toggle()
            }
        } label: {
            if isEnabled {
                Label("Images", systemImage: "checkmark")
            } else {
                Text("Images")
            }
        }
    }

    private func toggleTrack(_ kind: TextPlayerVariantKind) {
        withAnimation(.none) {
            if visibleTracks.contains(kind) {
                if visibleTracks.count > 1 {
                    visibleTracks.remove(kind)
                }
            } else {
                visibleTracks.insert(kind)
            }
        }
    }

    private func availableTracks(for chunk: InteractiveChunk) -> [TextPlayerVariantKind] {
        var available: [TextPlayerVariantKind] = []
        if chunk.sentences.contains(where: { !$0.originalTokens.isEmpty }) {
            available.append(.original)
        }
        if chunk.sentences.contains(where: { !$0.transliterationTokens.isEmpty }) {
            available.append(.transliteration)
        }
        if chunk.sentences.contains(where: { !$0.translationTokens.isEmpty }) {
            available.append(.translation)
        }
        if available.isEmpty {
            return [.original]
        }
        return available
    }

    private func hasImageReel(for chunk: InteractiveChunk) -> Bool {
        chunk.sentences.contains { sentence in
            if let rawPath = sentence.imagePath, rawPath.nonEmptyValue != nil {
                return true
            }
            return false
        }
    }

    private func applyDefaultTrackSelection(for chunk: InteractiveChunk) {
        let available = Set(availableTracks(for: chunk))
        if visibleTracks.isEmpty {
            visibleTracks = available
        } else {
            let intersection = visibleTracks.intersection(available)
            visibleTracks = intersection.isEmpty ? available : intersection
        }
        if let showImageReel {
            showImageReel.wrappedValue = hasImageReel(for: chunk)
        }
    }

    private func sentenceBinding(entries: [SentenceOption], chunk: InteractiveChunk) -> Binding<Int> {
        Binding(
            get: {
                if let selected = selectedSentenceID,
                   entries.contains(where: { $0.id == selected }) {
                    return selected
                }
                return entries.first?.id ?? 0
            },
            set: { newValue in
                selectedSentenceID = newValue
                guard let target = entries.first(where: { $0.id == newValue }) else { return }
                guard let startTime = target.startTime else { return }
                viewModel.seekPlayback(to: startTime, in: chunk)
            }
        )
    }

    private func sentenceEntries(for chunk: InteractiveChunk) -> [SentenceOption] {
        let sentences = chunk.sentences
        if sentences.isEmpty {
            if let start = chunk.startSentence, let end = chunk.endSentence, start <= end {
                return (start...end).map { SentenceOption(id: $0, label: "\($0)", startTime: nil) }
            }
            return []
        }
        var startTimes: [Int: Double] = [:]
        let activeTimingTrack = viewModel.activeTimingTrack(for: chunk)
        let useCombinedPhases = viewModel.useCombinedPhases(for: chunk)
        let timelineSentences = TextPlayerTimeline.buildTimelineSentences(
            sentences: sentences,
            activeTimingTrack: activeTimingTrack,
            audioDuration: viewModel.playbackDuration(for: chunk),
            useCombinedPhases: useCombinedPhases
        )
        if let timelineSentences {
            for runtime in timelineSentences {
                guard sentences.indices.contains(runtime.index) else { continue }
                let sentence = sentences[runtime.index]
                let id = sentence.displayIndex ?? sentence.id
                startTimes[id] = runtime.startTime
            }
        }
        let entries = sentences.map { sentence -> SentenceOption in
            let id = sentence.displayIndex ?? sentence.id
            let label = "\(id)"
            return SentenceOption(
                id: id,
                label: label,
                startTime: startTimes[id] ?? sentence.startTime
            )
        }
        return entries.sorted { $0.id < $1.id }
    }

    private func syncSelectedSentence(for chunk: InteractiveChunk) {
        let time = viewModel.highlightingTime
        guard time.isFinite else { return }
        guard let sentence = viewModel.activeSentence(at: time) else { return }
        let id = sentence.displayIndex ?? sentence.id
        if selectedSentenceID != id {
            selectedSentenceID = id
        }
    }

    private func textTrackSummary(for chunk: InteractiveChunk) -> String {
        let available = availableTracks(for: chunk)
        let visible = available.filter { visibleTracks.contains($0) }
        var parts = visible.map { trackSummaryLabel($0) }
        let canShowImages = hasImageReel(for: chunk) && showImageReel != nil
        if canShowImages, let showImageReel, showImageReel.wrappedValue {
            parts.append("Images")
        }
        let allTextSelected = visible.count == available.count
        let allSelected = allTextSelected && (!canShowImages || showImageReel?.wrappedValue == true)
        if allSelected {
            return "All"
        }
        if parts.isEmpty {
            return "Text"
        }
        if parts.count == 1 {
            return parts[0]
        }
        return parts.joined(separator: " + ")
    }

    private func playbackRateLabel(_ rate: Double) -> String {
        let rounded = (rate * 100).rounded() / 100
        let formatted = String(format: rounded.truncatingRemainder(dividingBy: 1) == 0 ? "%.0f" : "%.2f", rounded)
        return "\(formatted)x"
    }

    private func isCurrentRate(_ rate: Double) -> Bool {
        abs(rate - audioCoordinator.playbackRate) < 0.01
    }

    private func transcriptSentences(for chunk: InteractiveChunk) -> [TextPlayerSentenceDisplay] {
        let playbackTime = viewModel.playbackTime(for: chunk)
        let activeTimingTrack = viewModel.activeTimingTrack(for: chunk)
        let useCombinedPhases = viewModel.useCombinedPhases(for: chunk)
        let playbackDuration = viewModel.playbackDuration(for: chunk) ?? audioCoordinator.duration
        let timelineDuration = viewModel.timelineDuration(for: chunk)
        let durationValue: Double? = {
            if useCombinedPhases {
                return timelineDuration
            }
            if let timelineDuration {
                return timelineDuration
            }
            return playbackDuration > 0 ? playbackDuration : nil
        }()
        let timelineSentences = TextPlayerTimeline.buildTimelineSentences(
            sentences: chunk.sentences,
            activeTimingTrack: activeTimingTrack,
            audioDuration: durationValue,
            useCombinedPhases: useCombinedPhases
        )
        let isVariantVisible: (TextPlayerVariantKind) -> Bool = { visibleTracks.contains($0) }
        let timelineDisplay = timelineSentences.flatMap { runtime in
            TextPlayerTimeline.buildTimelineDisplay(
                timelineSentences: runtime,
                chunkTime: playbackTime,
                audioDuration: durationValue,
                isVariantVisible: isVariantVisible
            )
        }
        let staticDisplay = TextPlayerTimeline.buildStaticDisplay(
            sentences: chunk.sentences,
            isVariantVisible: isVariantVisible
        )
        return TextPlayerTimeline.selectActiveSentence(
            from: timelineDisplay?.sentences ?? staticDisplay
        )
    }

    private func activeSentenceDisplay(for chunk: InteractiveChunk) -> TextPlayerSentenceDisplay? {
        transcriptSentences(for: chunk).first
    }

    private func preferredNavigationKind(for chunk: InteractiveChunk) -> TextPlayerVariantKind {
        switch viewModel.activeTimingTrack(for: chunk) {
        case .original:
            return .original
        case .translation, .mix:
            return .translation
        }
    }

    private func preferredNavigationVariant(
        for sentence: TextPlayerSentenceDisplay,
        chunk: InteractiveChunk
    ) -> TextPlayerVariantDisplay? {
        let preferredKind = preferredNavigationKind(for: chunk)
        if let preferred = sentence.variants.first(where: { $0.kind == preferredKind }) {
            return preferred
        }
        if let translation = sentence.variants.first(where: { $0.kind == .translation }) {
            return translation
        }
        if let original = sentence.variants.first(where: { $0.kind == .original }) {
            return original
        }
        if let transliteration = sentence.variants.first(where: { $0.kind == .transliteration }) {
            return transliteration
        }
        return sentence.variants.first
    }

    private func resolvedSelection(for chunk: InteractiveChunk) -> TextPlayerWordSelection? {
        guard let sentence = activeSentenceDisplay(for: chunk) else { return nil }
        if let selection = linguistSelection,
           selection.sentenceIndex == sentence.index,
           let variant = sentence.variants.first(where: { $0.kind == selection.variantKind }),
           variant.tokens.indices.contains(selection.tokenIndex) {
            return selection
        }
        guard let variant = preferredNavigationVariant(for: sentence, chunk: chunk),
              !variant.tokens.isEmpty else {
            return nil
        }
        let fallbackIndex = variant.currentIndex ?? 0
        let clampedIndex = max(0, min(fallbackIndex, variant.tokens.count - 1))
        return TextPlayerWordSelection(
            sentenceIndex: sentence.index,
            variantKind: variant.kind,
            tokenIndex: clampedIndex
        )
    }

    private func handleWordNavigation(_ delta: Int, in chunk: InteractiveChunk) {
        if audioCoordinator.isPlaying {
            audioCoordinator.pause()
        }
        guard let sentence = activeSentenceDisplay(for: chunk),
              let selection = resolvedSelection(for: chunk),
              let variant = sentence.variants.first(where: { $0.kind == selection.variantKind }) else {
            return
        }
        let nextIndex = selection.tokenIndex + delta
        let resolvedIndex = variant.tokens.indices.contains(nextIndex) ? nextIndex : selection.tokenIndex
        linguistSelection = TextPlayerWordSelection(
            sentenceIndex: sentence.index,
            variantKind: selection.variantKind,
            tokenIndex: resolvedIndex
        )
        linguistBubble = nil
    }

    private func handleTrackNavigation(_ delta: Int, in chunk: InteractiveChunk) {
        if audioCoordinator.isPlaying {
            audioCoordinator.pause()
        }
        guard let sentence = activeSentenceDisplay(for: chunk) else { return }
        let variants = sentence.variants
        guard !variants.isEmpty else { return }
        let currentSelection = resolvedSelection(for: chunk)
        let currentIndex: Int = {
            if let currentSelection,
               let index = variants.firstIndex(where: { $0.kind == currentSelection.variantKind }) {
                return index
            }
            let preferredKind = preferredNavigationKind(for: chunk)
            if let preferredIndex = variants.firstIndex(where: { $0.kind == preferredKind }) {
                return preferredIndex
            }
            return 0
        }()
        let nextIndex = (currentIndex + delta + variants.count) % variants.count
        let targetVariant = variants[nextIndex]
        let fallbackIndex = targetVariant.currentIndex ?? 0
        let preferredTokenIndex = currentSelection?.tokenIndex ?? fallbackIndex
        let clampedIndex = max(0, min(preferredTokenIndex, max(0, targetVariant.tokens.count - 1)))
        linguistSelection = TextPlayerWordSelection(
            sentenceIndex: sentence.index,
            variantKind: targetVariant.kind,
            tokenIndex: clampedIndex
        )
        linguistBubble = nil
    }

    private func handleLinguistLookup(in chunk: InteractiveChunk) {
        if audioCoordinator.isPlaying {
            audioCoordinator.pause()
        }
        guard let sentence = activeSentenceDisplay(for: chunk),
              let selection = resolvedSelection(for: chunk),
              let variant = sentence.variants.first(where: { $0.kind == selection.variantKind }),
              variant.tokens.indices.contains(selection.tokenIndex) else {
            return
        }
        let rawToken = variant.tokens[selection.tokenIndex]
        guard let query = sanitizeLookupQuery(rawToken) else { return }
        linguistSelection = selection
        startLinguistLookup(query: query, variantKind: selection.variantKind)
    }

    private func startLinguistLookup(query: String, variantKind: TextPlayerVariantKind) {
        linguistLookupTask?.cancel()
        linguistBubble = MyLinguistBubbleState(query: query, status: .loading, answer: nil, model: nil)
        let inputLanguage = linguistInputLanguage.trimmingCharacters(in: .whitespacesAndNewlines)
        let lookupLanguage = linguistLookupLanguage.trimmingCharacters(in: .whitespacesAndNewlines)
        let preferredLanguage = pronunciationLanguage(for: variantKind, inputLanguage: inputLanguage, lookupLanguage: lookupLanguage)
        let fallbackLanguage = resolveSpeechLanguage(preferredLanguage ?? "")
        startPronunciation(text: query, apiLanguage: preferredLanguage, fallbackLanguage: fallbackLanguage)
        linguistLookupTask = Task { @MainActor in
            do {
                let response = try await viewModel.lookupAssistant(
                    query: query,
                    inputLanguage: inputLanguage,
                    lookupLanguage: lookupLanguage.isEmpty ? "English" : lookupLanguage
                )
                linguistBubble = MyLinguistBubbleState(
                    query: query,
                    status: .ready,
                    answer: response.answer,
                    model: response.model
                )
            } catch {
                guard !Task.isCancelled else { return }
                linguistBubble = MyLinguistBubbleState(
                    query: query,
                    status: .error(error.localizedDescription),
                    answer: nil,
                    model: nil
                )
            }
        }
    }

    private func clearLinguistState() {
        linguistLookupTask?.cancel()
        linguistLookupTask = nil
        linguistSpeechTask?.cancel()
        linguistSpeechTask = nil
        linguistBubble = nil
        linguistSelection = nil
        pronunciationSpeaker.stop()
    }

    private func closeLinguistBubble() {
        linguistLookupTask?.cancel()
        linguistLookupTask = nil
        linguistSpeechTask?.cancel()
        linguistSpeechTask = nil
        linguistBubble = nil
        pronunciationSpeaker.stop()
    }

    private func sanitizeLookupQuery(_ value: String) -> String? {
        let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
        let stripped = trimmed.trimmingCharacters(in: .punctuationCharacters.union(.symbols))
        let normalized = stripped.trimmingCharacters(in: .whitespacesAndNewlines)
        return normalized.isEmpty ? nil : normalized
    }

    private func pronunciationLanguage(
        for variantKind: TextPlayerVariantKind,
        inputLanguage: String,
        lookupLanguage: String
    ) -> String? {
        let preferred: String
        switch variantKind {
        case .translation:
            preferred = lookupLanguage
        case .original, .transliteration:
            preferred = inputLanguage
        }
        let trimmed = preferred.trimmingCharacters(in: .whitespacesAndNewlines)
        return trimmed.isEmpty ? nil : trimmed
    }

    private func resolveSpeechLanguage(_ value: String) -> String? {
        let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return nil }
        let normalized = trimmed.replacingOccurrences(of: "_", with: "-")
        if normalized.contains("-") || normalized.count <= 3 {
            return normalized
        }
        switch normalized.lowercased() {
        case "english":
            return "en-US"
        case "japanese":
            return "ja-JP"
        case "spanish":
            return "es-ES"
        case "french":
            return "fr-FR"
        case "german":
            return "de-DE"
        case "italian":
            return "it-IT"
        case "portuguese":
            return "pt-PT"
        case "chinese":
            return "zh-CN"
        case "korean":
            return "ko-KR"
        case "russian":
            return "ru-RU"
        case "arabic":
            return "ar-SA"
        case "hindi":
            return "hi-IN"
        default:
            return nil
        }
    }

    private func startPronunciation(text: String, apiLanguage: String?, fallbackLanguage: String?) {
        linguistSpeechTask?.cancel()
        pronunciationSpeaker.stop()
        linguistSpeechTask = Task { @MainActor in
            do {
                let data = try await viewModel.synthesizePronunciation(text: text, language: apiLanguage)
                guard !Task.isCancelled else { return }
                pronunciationSpeaker.playAudio(data)
            } catch {
                guard !Task.isCancelled else { return }
                if let fallbackLanguage {
                    pronunciationSpeaker.speakFallback(text, language: fallbackLanguage)
                }
            }
        }
    }

}

private struct TextPlayerWordSelection: Equatable {
    let sentenceIndex: Int
    let variantKind: TextPlayerVariantKind
    let tokenIndex: Int
}

private enum MyLinguistBubbleStatus: Equatable {
    case loading
    case ready
    case error(String)
}

private struct MyLinguistBubbleState: Equatable {
    let query: String
    let status: MyLinguistBubbleStatus
    let answer: String?
    let model: String?
}

private struct MyLinguistBubbleView: View {
    let bubble: MyLinguistBubbleState
    let onClose: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 8) {
                Text("MyLinguist")
                    .font(.headline)
                Spacer(minLength: 8)
                if let model = bubble.model, !model.isEmpty {
                    Text("Model: \(model)")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }
                Button(action: onClose) {
                    Image(systemName: "xmark")
                        .font(.caption.weight(.semibold))
                        .padding(6)
                        .background(.black.opacity(0.3), in: Circle())
                }
                .buttonStyle(.plain)
            }

            Text(bubble.query)
                .font(.title3.weight(.semibold))
                .lineLimit(2)
                .minimumScaleFactor(0.8)

            bubbleContent
        }
        .padding(12)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(bubbleBackground)
        .overlay(
            RoundedRectangle(cornerRadius: bubbleCornerRadius)
                .stroke(Color.white.opacity(0.12), lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: bubbleCornerRadius))
    }

    @ViewBuilder
    private var bubbleContent: some View {
        switch bubble.status {
        case .loading:
            HStack(spacing: 8) {
                ProgressView()
                    .progressViewStyle(.circular)
                Text("Looking up...")
                    .font(.callout)
                    .foregroundStyle(.secondary)
            }
        case let .error(message):
            Text(message)
                .font(.callout)
                .foregroundStyle(.red)
        case .ready:
            ScrollView {
                Text(bubble.answer ?? "")
                    .font(.callout)
                    .foregroundStyle(.primary)
                    .frame(maxWidth: .infinity, alignment: .leading)
            }
            .frame(maxHeight: bubbleMaxHeight)
        }
    }

    private var bubbleBackground: Color {
        Color.black.opacity(0.75)
    }

    private var bubbleCornerRadius: CGFloat {
        #if os(tvOS)
        return 18
        #else
        return 14
        #endif
    }

    private var bubbleMaxHeight: CGFloat {
        #if os(tvOS)
        return 220
        #else
        return 180
        #endif
    }
}

private struct InteractiveTranscriptView: View {
    let viewModel: InteractivePlayerViewModel
    @ObservedObject var audioCoordinator: AudioPlayerCoordinator
    let sentences: [TextPlayerSentenceDisplay]
    let selection: TextPlayerWordSelection?
    let bubble: MyLinguistBubbleState?
    let onNavigateWord: (Int) -> Void
    let onNavigateTrack: (Int) -> Void
    let onLookup: () -> Void
    let onCloseBubble: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            TextPlayerFrame(sentences: sentences, selection: selection)
                .frame(maxWidth: .infinity, alignment: .top)
            #if !os(tvOS)
                .contentShape(Rectangle())
                .gesture(swipeGesture)
                .onLongPressGesture(minimumDuration: 0.4, perform: onLookup)
            #endif

            if let bubble {
                MyLinguistBubbleView(bubble: bubble, onClose: onCloseBubble)
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
        #if os(tvOS)
        .onPlayPauseCommand {
            audioCoordinator.togglePlayback()
        }
        #endif
        .onChange(of: audioCoordinator.duration) { _, newValue in
            viewModel.recordAudioDuration(newValue, for: audioCoordinator.activeURL)
        }
        .onChange(of: audioCoordinator.activeURL) { _, _ in
            viewModel.recordAudioDuration(audioCoordinator.duration, for: audioCoordinator.activeURL)
        }
        .onAppear {
            viewModel.recordAudioDuration(audioCoordinator.duration, for: audioCoordinator.activeURL)
        }
    }

    #if !os(tvOS)
    private var swipeGesture: some Gesture {
        DragGesture(minimumDistance: 24, coordinateSpace: .local)
            .onEnded { value in
                let horizontal = value.translation.width
                let vertical = value.translation.height
                if abs(horizontal) > abs(vertical) {
                    if horizontal < 0 {
                        onNavigateWord(1)
                    } else if horizontal > 0 {
                        onNavigateWord(-1)
                    }
                } else {
                    if vertical < 0 {
                        onNavigateTrack(-1)
                    } else if vertical > 0 {
                        onNavigateTrack(1)
                    }
                }
            }
    }
    #endif
}

private final class PronunciationSpeaker: NSObject, ObservableObject, AVAudioPlayerDelegate {
    private let synthesizer = AVSpeechSynthesizer()
    private var audioPlayer: AVAudioPlayer?

    func playAudio(_ data: Data) {
        stop()
        configureAudioSession()
        do {
            let player = try AVAudioPlayer(data: data)
            player.delegate = self
            player.prepareToPlay()
            player.play()
            audioPlayer = player
        } catch {
            audioPlayer = nil
        }
    }

    func speakFallback(_ text: String, language: String?) {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }
        stop()
        configureAudioSession()
        let utterance = AVSpeechUtterance(string: trimmed)
        if let language, let voice = AVSpeechSynthesisVoice(language: language) {
            utterance.voice = voice
        }
        utterance.rate = AVSpeechUtteranceDefaultSpeechRate
        synthesizer.speak(utterance)
    }

    func stop() {
        if synthesizer.isSpeaking {
            synthesizer.stopSpeaking(at: .immediate)
        }
        audioPlayer?.stop()
        audioPlayer = nil
    }

    func audioPlayerDidFinishPlaying(_ player: AVAudioPlayer, successfully flag: Bool) {
        audioPlayer = nil
    }

    private func configureAudioSession() {
        #if os(iOS)
        let session = AVAudioSession.sharedInstance()
        let options: AVAudioSession.CategoryOptions = [.allowAirPlay]
        try? session.setCategory(.playback, mode: .spokenAudio, options: options)
        try? session.setActive(true)
        #endif
    }
}

private struct PlaybackButtonRow: View {
    @ObservedObject var coordinator: AudioPlayerCoordinator
    let focusBinding: FocusState<InteractivePlayerFocusArea?>.Binding
    let onPrevious: (() -> Void)?
    let onNext: (() -> Void)?

    var body: some View {
        #if os(tvOS)
        HStack(spacing: 12) {
            if let onPrevious {
                Button(action: onPrevious) {
                    Image(systemName: "backward.end.fill")
                        .font(.title3)
                }
                .buttonStyle(.bordered)
                .controlSize(.small)
                .focused(focusBinding, equals: .controls)
            }
            Button(action: coordinator.togglePlayback) {
                Image(systemName: coordinator.isPlaying ? "pause.fill" : "play.fill")
                    .font(.title2)
            }
            .buttonStyle(.borderedProminent)
            .controlSize(.small)
            .focused(focusBinding, equals: .controls)
            if let onNext {
                Button(action: onNext) {
                    Image(systemName: "forward.end.fill")
                        .font(.title3)
                }
                .buttonStyle(.bordered)
                .controlSize(.small)
                .focused(focusBinding, equals: .controls)
            }
        }
        #else
        HStack(spacing: 14) {
            if let onPrevious {
                Button(action: onPrevious) {
                    Image(systemName: "backward.end.fill")
                        .font(.title3)
                        .padding(8)
                        .background(.thinMaterial, in: Circle())
                }
            }
            Button(action: coordinator.togglePlayback) {
                Image(systemName: coordinator.isPlaying ? "pause.fill" : "play.fill")
                    .font(.title2)
                    .padding(10)
                    .background(.thinMaterial, in: Circle())
            }
            if let onNext {
                Button(action: onNext) {
                    Image(systemName: "forward.end.fill")
                        .font(.title3)
                        .padding(8)
                        .background(.thinMaterial, in: Circle())
                }
            }
        }
        #endif
    }
}

private struct SentenceOption: Identifiable {
    let id: Int
    let label: String
    let startTime: Double?
}

private struct PlaybackScrubberView: View {
    @ObservedObject var coordinator: AudioPlayerCoordinator
    let currentTime: Double
    let duration: Double
    @Binding var scrubbedTime: Double?
    let onSeek: ((Double) -> Void)?

    var body: some View {
        let upperBound = max(duration, scrubbedTime ?? currentTime, 0.1)
        VStack(alignment: .leading, spacing: 4) {
            #if os(tvOS)
            // tvOS does not support Slider. Show a progress bar instead.
            ProgressView(value: min(currentValue / max(upperBound, 0.0001), 1.0))
                .progressViewStyle(.linear)
                .tint(TextPlayerTheme.progress)
            #else
            Slider(
                value: Binding(
                    get: { scrubbedTime ?? currentTime },
                    set: { newValue in
                        scrubbedTime = newValue
                    }
                ),
                in: 0...upperBound,
                onEditingChanged: handleEditingChanged
            )
            .tint(TextPlayerTheme.progress)
            #endif
            Text("\(formatTime(currentValue)) / \(formatTime(duration))")
                .font(.caption2)
                .foregroundStyle(.secondary)
        }
    }

    private var currentValue: Double {
        scrubbedTime ?? currentTime
    }

    private func handleEditingChanged(_ editing: Bool) {
        if !editing {
            let target = currentValue
            scrubbedTime = nil
            if let onSeek {
                onSeek(target)
            } else {
                coordinator.seek(to: target)
            }
        }
    }

    private func formatTime(_ value: Double) -> String {
        guard value.isFinite else { return "--:--" }
        let totalSeconds = Int(value.rounded())
        let minutes = totalSeconds / 60
        let seconds = totalSeconds % 60
        return String(format: "%02d:%02d", minutes, seconds)
    }
}

private struct TextPlayerFrame: View {
    let sentences: [TextPlayerSentenceDisplay]
    let selection: TextPlayerWordSelection?

    var body: some View {
        VStack(spacing: 10) {
            if sentences.isEmpty {
                Text("Waiting for transcript...")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .frame(maxWidth: .infinity)
            } else {
                ForEach(sentences) { sentence in
                    TextPlayerSentenceView(sentence: sentence, selection: selection)
                }
            }
        }
        .padding(framePadding)
        .frame(maxWidth: .infinity)
        .background(TextPlayerTheme.frameBackground)
        .clipShape(RoundedRectangle(cornerRadius: 16))
    }

    private var framePadding: CGFloat {
        #if os(tvOS)
        return 20
        #else
        return 14
        #endif
    }
}

private struct TextPlayerSentenceView: View {
    let sentence: TextPlayerSentenceDisplay
    let selection: TextPlayerWordSelection?

    var body: some View {
        VStack(spacing: 8) {
            ForEach(sentence.variants) { variant in
                TextPlayerVariantView(
                    variant: variant,
                    sentenceState: sentence.state,
                    selectedTokenIndex: selectedTokenIndex(for: variant)
                )
            }
        }
        .padding(.vertical, 10)
        .padding(.horizontal, 12)
        .frame(maxWidth: .infinity)
        .background(sentenceBackground)
        .clipShape(RoundedRectangle(cornerRadius: 12))
        .shadow(color: sentenceShadow, radius: sentenceShadowRadius, x: 0, y: 6)
        .opacity(sentenceOpacity)
    }

    private var sentenceBackground: Color {
        sentence.state == .active ? TextPlayerTheme.sentenceActiveBackground : TextPlayerTheme.sentenceBackground
    }

    private var sentenceShadow: Color {
        sentence.state == .active ? TextPlayerTheme.sentenceActiveShadow : .clear
    }

    private var sentenceShadowRadius: CGFloat {
        sentence.state == .active ? 18 : 0
    }

    private var sentenceOpacity: Double {
        switch sentence.state {
        case .past:
            return 0.9
        case .future:
            return 0.85
        case .active:
            return 1.0
        }
    }

    private func selectedTokenIndex(for variant: TextPlayerVariantDisplay) -> Int? {
        guard let selection, selection.sentenceIndex == sentence.index else { return nil }
        guard selection.variantKind == variant.kind else { return nil }
        return selection.tokenIndex
    }
}

private struct TextPlayerVariantView: View {
    let variant: TextPlayerVariantDisplay
    let sentenceState: TextPlayerSentenceState
    let selectedTokenIndex: Int?

    var body: some View {
        VStack(spacing: 6) {
            Text(variant.label)
                .font(labelFont)
                .foregroundStyle(TextPlayerTheme.lineLabel)
                .textCase(.uppercase)
                .tracking(1.2)
                .lineLimit(1)
                .minimumScaleFactor(0.7)
                .allowsTightening(true)
                .frame(maxWidth: .infinity)
            tokenLine
                .font(lineFont)
                .multilineTextAlignment(.center)
                .lineLimit(nil)
                .minimumScaleFactor(0.65)
                .allowsTightening(true)
                .fixedSize(horizontal: false, vertical: true)
                .layoutPriority(1)
                .frame(maxWidth: .infinity)
        }
    }

    private var labelFont: Font {
        #if os(tvOS)
        return .caption
        #else
        return .caption2
        #endif
    }

    private var lineFont: Font {
        #if os(tvOS)
        return sentenceState == .active ? .title2 : .title3
        #else
        return sentenceState == .active ? .title3 : .body
        #endif
    }

    private var tokenLine: Text {
        Text(tokenAttributedString)
    }

    private var tokenAttributedString: AttributedString {
        var result = AttributedString("")
        let displayIndices = shouldReverseTokens
            ? Array(variant.tokens.indices.reversed())
            : Array(variant.tokens.indices)
        for (position, index) in displayIndices.enumerated() {
            let token = variant.tokens[index]
            let tokenState = tokenState(for: index)
            let baseColor = tokenColor(for: tokenState)
            var segment = AttributedString(token)
            if index == selectedTokenIndex {
                segment.foregroundColor = TextPlayerTheme.selectionText
                segment.backgroundColor = TextPlayerTheme.selectionGlow
            } else {
                segment.foregroundColor = baseColor
            }
            result.append(segment)
            if position < displayIndices.count - 1 {
                var space = AttributedString(" ")
                space.foregroundColor = baseColor
                result.append(space)
            }
        }
        return result
    }

    private var shouldReverseTokens: Bool {
        guard variant.kind == .translation else { return false }
        return variant.tokens.contains(where: containsRTLCharacters)
    }

    private func containsRTLCharacters(_ value: String) -> Bool {
        for scalar in value.unicodeScalars {
            let point = scalar.value
            if (0x0590...0x08FF).contains(point) || (0xFB1D...0xFEFF).contains(point) {
                return true
            }
        }
        return false
    }

    private func tokenState(for index: Int) -> TokenState {
        if sentenceState == .future {
            return .future
        }
        if sentenceState == .past {
            return .past
        }
        if variant.revealedCount == 0 {
            return .future
        }
        if index < variant.revealedCount - 1 {
            return .past
        }
        if index == variant.revealedCount - 1 {
            return .current
        }
        return .future
    }

    private func tokenColor(for state: TokenState) -> Color {
        switch state {
        case .past:
            return TextPlayerTheme.progress
        case .current:
            switch variant.kind {
            case .original:
                return TextPlayerTheme.originalCurrent
            case .translation:
                return TextPlayerTheme.translationCurrent
            case .transliteration:
                return TextPlayerTheme.transliterationCurrent
            }
        case .future:
            switch variant.kind {
            case .original:
                return TextPlayerTheme.original
            case .translation:
                return TextPlayerTheme.translation
            case .transliteration:
                return TextPlayerTheme.transliteration
            }
        }
    }

    private var highlightShadowColor: Color {
        switch variant.kind {
        case .original:
            return TextPlayerTheme.progress.opacity(0.7)
        case .translation:
            return TextPlayerTheme.translation.opacity(0.55)
        case .transliteration:
            return TextPlayerTheme.transliteration.opacity(0.55)
        }
    }

    private enum TokenState {
        case past
        case current
        case future
    }
}

private enum TextPlayerTheme {
    static let frameBackground = Color.black
    static let sentenceBackground = Color(red: 1.0, green: 0.878, blue: 0.521).opacity(0.04)
    static let sentenceActiveBackground = Color(red: 1.0, green: 0.647, blue: 0.0).opacity(0.16)
    static let sentenceActiveShadow = Color(red: 1.0, green: 0.549, blue: 0.0).opacity(0.18)
    static let lineLabel = Color.white.opacity(0.45)
    static let original = Color(red: 1.0, green: 0.831, blue: 0.0)
    static let translation = Color(red: 0.204, green: 0.827, blue: 0.6)
    static let transliteration = Color(red: 0.176, green: 0.831, blue: 0.749)
    static let progress = Color(red: 1.0, green: 0.549, blue: 0.0)
    static let selectionGlow = Color(red: 1.0, green: 0.549, blue: 0.0).opacity(0.6)
    static let selectionText = Color.black
    static let originalCurrent = Color.white
    static let translationCurrent = Color(red: 0.996, green: 0.941, blue: 0.541)
    static let transliterationCurrent = Color(red: 0.996, green: 0.976, blue: 0.765)
}
