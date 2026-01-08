import SwiftUI

struct PlaybackButtonRow: View {
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

struct InteractivePlayerImageReel: View {
    let urls: [URL]
    let height: CGFloat

    private let spacing: CGFloat = 8
    private let maxImages = 7
    private let minImages = 1

    var body: some View {
        GeometryReader { proxy in
            let itemHeight = height
            let itemWidth = itemHeight * 0.78
            let maxVisible = max(
                minImages,
                min(maxImages, Int((proxy.size.width + spacing) / (itemWidth + spacing)))
            )
            let visible = Array(urls.prefix(maxVisible))
            HStack(spacing: spacing) {
                ForEach(visible.indices, id: \.self) { index in
                    AsyncImage(url: visible[index]) { phase in
                        if let image = phase.image {
                            image
                                .resizable()
                                .scaledToFill()
                        } else {
                            Color.gray.opacity(0.2)
                        }
                    }
                    .frame(width: itemWidth, height: itemHeight)
                    .clipShape(RoundedRectangle(cornerRadius: 10))
                    .overlay(
                        RoundedRectangle(cornerRadius: 10)
                            .stroke(Color.secondary.opacity(0.2), lineWidth: 1)
                    )
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .trailing)
        }
        .frame(height: height)
    }
}

struct PlaybackScrubberView: View {
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
