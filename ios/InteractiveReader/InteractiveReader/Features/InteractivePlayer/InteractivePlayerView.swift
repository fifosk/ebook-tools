import SwiftUI

struct InteractivePlayerView: View {
    @ObservedObject var viewModel: InteractivePlayerViewModel
    let audioCoordinator: AudioPlayerCoordinator
    @State private var scrubbedTime: Double?

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
                    chunk: chunk
                )
            } else {
                Text("No interactive chunks were returned for this job.")
                    .foregroundStyle(.secondary)
            }
        }
        .padding(.horizontal)
        .padding(.vertical, 12)
    }

    @ViewBuilder
    private func controlBar(_ chunk: InteractiveChunk) -> some View {
        let playbackTime = viewModel.playbackTime(for: chunk)
        let playbackDuration = viewModel.playbackDuration(for: chunk) ?? audioCoordinator.duration
        VStack(alignment: .leading, spacing: 8) {
            HStack(alignment: .center, spacing: 12) {
                chunkPicker()
                audioPicker(for: chunk)
                Spacer(minLength: 8)
                PlaybackButtonRow(
                    coordinator: audioCoordinator,
                    onPrevious: { viewModel.skipSentence(forward: false) },
                    onNext: { viewModel.skipSentence(forward: true) }
                )
            }
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

    @ViewBuilder
    private func chunkPicker() -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text("Chunk")
                .font(.caption)
                .foregroundStyle(.secondary)
            Picker("Chunk", selection: viewModel.chunkBinding()) {
                ForEach(viewModel.jobContext?.chunks ?? []) { chunk in
                    Text(chunk.label).tag(chunk.id)
                }
            }
            .pickerStyle(.menu)
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
                    HStack(spacing: 6) {
                        Text(selectedAudioLabel(for: chunk))
                            .font(.callout)
                            .lineLimit(1)
                        Image(systemName: "chevron.down")
                            .font(.caption2)
                            .foregroundStyle(.secondary)
                    }
                    .padding(.horizontal, 10)
                    .padding(.vertical, 6)
                }
                .buttonStyle(.bordered)
                .controlSize(.small)
                #else
                Picker("Audio track", selection: viewModel.audioTrackBinding(defaultID: chunk.audioOptions.first?.id)) {
                    ForEach(chunk.audioOptions) { option in
                        Text(option.label).tag(option.id)
                    }
                }
                .pickerStyle(.menu)
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
}

private struct InteractiveTranscriptView: View {
    let viewModel: InteractivePlayerViewModel
    @ObservedObject var audioCoordinator: AudioPlayerCoordinator
    let chunk: InteractiveChunk

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
        let timelineDisplay = timelineSentences.flatMap { runtime in
            TextPlayerTimeline.buildTimelineDisplay(
                timelineSentences: runtime,
                chunkTime: playbackTime,
                audioDuration: durationValue,
                isVariantVisible: { _ in true }
            )
        }
        let staticDisplay = TextPlayerTimeline.buildStaticDisplay(
            sentences: chunk.sentences,
            isVariantVisible: { _ in true }
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
    let onPrevious: (() -> Void)?
    let onNext: (() -> Void)?

    var body: some View {
        #if os(tvOS)
        HStack(spacing: 12) {
            if let onPrevious {
                Button(action: onPrevious) {
                    Image(systemName: "backward.fill")
                        .font(.title3)
                }
                .buttonStyle(.bordered)
                .controlSize(.small)
            }
            Button(action: coordinator.togglePlayback) {
                Image(systemName: coordinator.isPlaying ? "pause.fill" : "play.fill")
                    .font(.title2)
            }
            .buttonStyle(.borderedProminent)
            .controlSize(.small)
            if let onNext {
                Button(action: onNext) {
                    Image(systemName: "forward.fill")
                        .font(.title3)
                }
                .buttonStyle(.bordered)
                .controlSize(.small)
            }
        }
        #else
        HStack(spacing: 12) {
            if let onPrevious {
                Button(action: onPrevious) {
                    Image(systemName: "backward.fill")
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
                    Image(systemName: "forward.fill")
                        .font(.title3)
                        .padding(8)
                        .background(.thinMaterial, in: Circle())
                }
            }
        }
        #endif
    }
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
        for index in variant.tokens.indices {
            let token = variant.tokens[index]
            let tokenState = tokenState(for: index)
            let color = tokenColor(for: tokenState)
            let segment = Text(token).foregroundColor(color)
            result = result + segment
            if index < variant.tokens.count - 1 {
                result = result + Text(" ").foregroundColor(color)
            }
        }
        return result
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
