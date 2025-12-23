import AVKit
import SwiftUI

struct VideoPlayerView: View {
    let videoURL: URL
    let subtitleURL: URL?

    @StateObject private var coordinator = VideoPlayerCoordinator()
    @State private var cues: [SubtitleCue] = []
    @State private var subtitleError: String?

    var body: some View {
        ZStack(alignment: .bottom) {
            if let player = coordinator.playerInstance() {
                VideoPlayer(player: player)
                    .onDisappear {
                        coordinator.reset()
                    }
            } else {
                ProgressView("Preparing video…")
            }

            SubtitleOverlayView(cues: cues, currentTime: coordinator.currentTime)
                .padding(.horizontal)

            if let subtitleError {
                Text(subtitleError)
                    .font(.caption)
                    .foregroundStyle(.white)
                    .padding(8)
                    .background(.black.opacity(0.7), in: RoundedRectangle(cornerRadius: 8))
                    .padding(.bottom, 12)
            }
        }
        .onAppear {
            coordinator.load(url: videoURL)
            loadSubtitles()
        }
        .onChange(of: videoURL) { _, newURL in
            coordinator.load(url: newURL)
            loadSubtitles()
        }
    }

    private func loadSubtitles() {
        cues = []
        subtitleError = nil
        guard let subtitleURL else { return }
        Task {
            do {
                let (data, _) = try await URLSession.shared.data(from: subtitleURL)
                let content = String(data: data, encoding: .utf8) ?? ""
                let parsed = SubtitleParser.parse(from: content)
                await MainActor.run {
                    cues = parsed
                }
            } catch {
                await MainActor.run {
                    subtitleError = "Unable to load subtitles"
                }
            }
        }
    }
}
