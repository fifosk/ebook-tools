import SwiftUI

struct InteractivePlayerView: View {
    @ObservedObject var viewModel: InteractivePlayerViewModel
    @ObservedObject var audioCoordinator: AudioPlayerCoordinator
    @State private var scrubbedTime: Double?

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            if let summary = viewModel.highlightingSummary {
                Text(summary)
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }

            if let chunk = viewModel.selectedChunk {
                chunkHeader(chunk)
                audioControls(sectionTitle: "Audio", chunk: chunk)
                Divider()
                sentenceScroller(for: chunk)
            } else {
                Text("No interactive chunks were returned for this job.")
                    .foregroundStyle(.secondary)
            }
        }
        .padding()
    }

    @ViewBuilder
    private func chunkHeader(_ chunk: InteractiveChunk) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                VStack(alignment: .leading) {
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
                Spacer()
                if let range = chunk.rangeDescription {
                    Text(range)
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }
            }
        }
    }

    @ViewBuilder
    private func audioControls(sectionTitle: String, chunk: InteractiveChunk) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(sectionTitle)
                .font(.caption)
                .foregroundStyle(.secondary)

            if !chunk.audioOptions.isEmpty {
                Picker("Audio track", selection: viewModel.audioTrackBinding(defaultID: chunk.audioOptions.first?.id)) {
                    ForEach(chunk.audioOptions) { option in
                        Text(option.label).tag(option.id)
                    }
                }
                .pickerStyle(.segmented)
            } else {
                Text("No audio files available for this chunk.")
                    .foregroundStyle(.secondary)
            }

            PlaybackControlsView(
                coordinator: audioCoordinator,
                scrubbedTime: $scrubbedTime
            )
        }
    }

    @ViewBuilder
    private func sentenceScroller(for chunk: InteractiveChunk) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Interactive transcript")
                .font(.caption)
                .foregroundStyle(.secondary)
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 12) {
                    ForEach(chunk.sentences) { sentence in
                        InteractiveSentenceCard(
                            sentence: sentence,
                            isActive: sentence.tokens.contains { $0.isActive(at: audioCoordinator.currentTime) },
                            currentTime: audioCoordinator.currentTime
                        )
                    }
                }
                .padding(.vertical, 4)
            }
        }
    }
}

private struct PlaybackControlsView: View {
    @ObservedObject var coordinator: AudioPlayerCoordinator
    @Binding var scrubbedTime: Double?
    @State private var isEditing = false

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 16) {
                Button(action: coordinator.togglePlayback) {
                    Image(systemName: coordinator.isPlaying ? "pause.fill" : "play.fill")
                        .font(.title2)
                        .padding(12)
                        .background(.thinMaterial, in: Circle())
                }
                VStack(alignment: .leading, spacing: 4) {
                    Text("Elapsed: \(formatTime(currentValue))")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    Text("Duration: \(formatTime(coordinator.duration))")
                        .font(.caption2)
                        .foregroundStyle(.tertiary)
                }
            }

            let upperBound = max(coordinator.duration, scrubbedTime ?? coordinator.currentTime, 0.1)

            Slider(
                value: Binding(
                    get: { scrubbedTime ?? coordinator.currentTime },
                    set: { newValue in
                        scrubbedTime = newValue
                    }
                ),
                in: 0...upperBound,
                onEditingChanged: handleEditingChanged
            )
        }
    }

    private var currentValue: Double {
        scrubbedTime ?? coordinator.currentTime
    }

    private func handleEditingChanged(_ editing: Bool) {
        isEditing = editing
        if !editing {
            let target = currentValue
            scrubbedTime = nil
            coordinator.seek(to: target)
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

private struct InteractiveSentenceCard: View {
    let sentence: InteractiveChunk.Sentence
    let isActive: Bool
    let currentTime: Double

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text(sentenceLabel)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                Spacer()
            }
            Text(sentence.originalText)
                .font(.subheadline)
                .foregroundStyle(.tertiary)
            if !sentence.tokens.isEmpty {
                Text(attributedTranslation)
                    .font(.title3)
                    .multilineTextAlignment(.leading)
            } else {
                Text(sentence.translationText)
                    .font(.title3)
            }
        }
        .padding(12)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(isActive ? Color.accentColor.opacity(0.1) : Color(.secondarySystemBackground))
        )
    }

    private var attributedTranslation: AttributedString {
        guard !sentence.tokens.isEmpty else {
            return AttributedString(sentence.translationText)
        }

        var result = AttributedString("")
        for (index, token) in sentence.tokens.enumerated() {
            var text = token.displayText
            if index < sentence.tokens.count - 1 {
                text.append(" ")
            }
            var attributed = AttributedString(text)
            if token.isActive(at: currentTime) {
                attributed.backgroundColor = Color.accentColor.opacity(0.35)
                attributed.foregroundColor = .primary
            }
            result += attributed
        }
        return result
    }

    private var sentenceLabel: String {
        if let index = sentence.displayIndex {
            return "Sentence \(index)"
        }
        return "Sentence \(sentence.id)"
    }
}
