import SwiftUI

private enum InteractivePlayerFocusArea: Hashable {
    case controls
    case transcript
}

struct InteractivePlayerView: View {
    @ObservedObject var viewModel: InteractivePlayerViewModel
    let audioCoordinator: AudioPlayerCoordinator
    let showImageReel: Binding<Bool>?
    @StateObject private var readingBedCoordinator = AudioPlayerCoordinator()
    @State private var readingBedEnabled = true
    @State private var scrubbedTime: Double?
    @State private var visibleTracks: Set<TextPlayerVariantKind> = [.original, .translation, .transliteration]
    @State private var selectedSentenceID: Int?
    @FocusState private var focusedArea: InteractivePlayerFocusArea?

    private let playbackRates: [Double] = [0.7, 0.85, 1.0, 1.15, 1.3, 1.5]
    private let readingBedVolume: Double = 0.08

    init(
        viewModel: InteractivePlayerViewModel,
        audioCoordinator: AudioPlayerCoordinator,
        showImageReel: Binding<Bool>? = nil
    ) {
        self._viewModel = ObservedObject(wrappedValue: viewModel)
        self.audioCoordinator = audioCoordinator
        self.showImageReel = showImageReel
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            if let summary = viewModel.highlightingSummary {
                Text(summary)
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }

            if let chunk = viewModel.selectedChunk {
                controlBar(chunk)
                Divider()
                InteractiveTranscriptView(
                    viewModel: viewModel,
                    audioCoordinator: audioCoordinator,
                    chunk: chunk,
                    visibleTracks: visibleTracks
                )
                #if os(tvOS)
                .focusable(true)
                .focused($focusedArea, equals: .transcript)
                #endif
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
        }
        .onChange(of: viewModel.selectedChunk?.id) { _, _ in
            guard let chunk = viewModel.selectedChunk else { return }
            applyDefaultTrackSelection(for: chunk)
            syncSelectedSentence(for: chunk)
        }
        .onChange(of: viewModel.highlightingTime) { _, _ in
            guard focusedArea != .controls else { return }
            guard let chunk = viewModel.selectedChunk else { return }
            syncSelectedSentence(for: chunk)
        }
        .onChange(of: viewModel.readingBedURL) { _, _ in
            configureReadingBed()
        }
        .onChange(of: readingBedEnabled) { _, _ in
            updateReadingBedPlayback()
        }
        .onDisappear {
            readingBedCoordinator.reset()
        }
        #if os(tvOS)
        .onPlayPauseCommand {
            audioCoordinator.togglePlayback()
        }
        .onMoveCommand { direction in
            guard focusedArea == .transcript else { return }
            switch direction {
            case .left:
                viewModel.skipSentence(forward: false)
            case .right:
                viewModel.skipSentence(forward: true)
            default:
                break
            }
        }
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
                    focusBinding: $focusedArea
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
        visibleTracks = Set(availableTracks(for: chunk))
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

}

private struct InteractiveTranscriptView: View {
    let viewModel: InteractivePlayerViewModel
    @ObservedObject var audioCoordinator: AudioPlayerCoordinator
    let chunk: InteractiveChunk
    let visibleTracks: Set<TextPlayerVariantKind>

    var body: some View {
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
        let displaySentences = TextPlayerTimeline.selectActiveSentence(
            from: timelineDisplay?.sentences ?? staticDisplay
        )
        VStack(alignment: .leading, spacing: 8) {
            Text("Interactive transcript")
                .font(.caption)
                .foregroundStyle(.secondary)
            TextPlayerFrame(sentences: displaySentences)
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
}

private struct PlaybackButtonRow: View {
    @ObservedObject var coordinator: AudioPlayerCoordinator
    let focusBinding: FocusState<InteractivePlayerFocusArea?>.Binding

    var body: some View {
        #if os(tvOS)
        HStack(spacing: 12) {
            Button(action: coordinator.togglePlayback) {
                Image(systemName: coordinator.isPlaying ? "pause.fill" : "play.fill")
                    .font(.title2)
            }
            .buttonStyle(.borderedProminent)
            .controlSize(.small)
            .focused(focusBinding, equals: .controls)
        }
        #else
        HStack(spacing: 12) {
            Button(action: coordinator.togglePlayback) {
                Image(systemName: coordinator.isPlaying ? "pause.fill" : "play.fill")
                    .font(.title2)
                    .padding(10)
                    .background(.thinMaterial, in: Circle())
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

    var body: some View {
        VStack(spacing: 10) {
            if sentences.isEmpty {
                Text("Waiting for transcript...")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .frame(maxWidth: .infinity)
            } else {
                ForEach(sentences) { sentence in
                    TextPlayerSentenceView(sentence: sentence)
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

    var body: some View {
        VStack(spacing: 8) {
            ForEach(sentence.variants) { variant in
                TextPlayerVariantView(variant: variant, sentenceState: sentence.state)
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
}

private struct TextPlayerVariantView: View {
    let variant: TextPlayerVariantDisplay
    let sentenceState: TextPlayerSentenceState

    var body: some View {
        VStack(spacing: 6) {
            Text(variant.label)
                .font(labelFont)
                .foregroundStyle(TextPlayerTheme.lineLabel)
                .textCase(.uppercase)
                .tracking(1.2)
                .frame(maxWidth: .infinity)
            tokenLine
                .font(lineFont)
                .multilineTextAlignment(.center)
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
        var result = Text("")
        let displayIndices = shouldReverseTokens
            ? Array(variant.tokens.indices.reversed())
            : Array(variant.tokens.indices)
        for (position, index) in displayIndices.enumerated() {
            let token = variant.tokens[index]
            let tokenState = tokenState(for: index)
            let color = tokenColor(for: tokenState)
            let segment = Text(token).foregroundColor(color)
            result = result + segment
            if position < displayIndices.count - 1 {
                result = result + Text(" ").foregroundColor(color)
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
    static let originalCurrent = Color.white
    static let translationCurrent = Color(red: 0.996, green: 0.941, blue: 0.541)
    static let transliterationCurrent = Color(red: 0.996, green: 0.976, blue: 0.765)
}
