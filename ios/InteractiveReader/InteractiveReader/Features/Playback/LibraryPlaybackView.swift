import SwiftUI

struct LibraryPlaybackView: View {
    @EnvironmentObject var appState: AppState
    @Environment(\.scenePhase) private var scenePhase
    let item: LibraryItem

    @StateObject private var viewModel = InteractivePlayerViewModel()
    @StateObject private var nowPlaying = NowPlayingCoordinator()
    @State private var activeSentenceIndex: Int?

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                header

                switch viewModel.loadState {
                case .idle, .loading:
                    loadingView
                case let .error(message):
                    errorView(message: message)
                case .loaded:
                    if isVideoPreferred, let videoURL {
                        VideoPlayerView(videoURL: videoURL, subtitleURL: subtitleURL)
                            .frame(maxWidth: .infinity)
                            .aspectRatio(16 / 9, contentMode: .fit)
                    } else if viewModel.jobContext != nil {
                        InteractivePlayerView(viewModel: viewModel, audioCoordinator: viewModel.audioCoordinator)
                    } else {
                        Text("No playable media found for this entry.")
                            .foregroundStyle(.secondary)
                    }
                }
            }
            .padding()
        }
        .navigationTitle(item.bookTitle)
        .task(id: item.jobId) {
            await loadEntry()
        }
        .onChange(of: viewModel.audioCoordinator.currentTime) { _, newValue in
            updateNowPlayingPlayback(time: newValue)
        }
        .onChange(of: viewModel.audioCoordinator.isPlaying) { _, _ in
            updateNowPlayingPlayback(time: viewModel.audioCoordinator.currentTime)
        }
        .onChange(of: viewModel.audioCoordinator.duration) { _, _ in
            updateNowPlayingPlayback(time: viewModel.audioCoordinator.currentTime)
        }
        .onChange(of: viewModel.audioCoordinator.isReady) { _, _ in
            updateNowPlayingPlayback(time: viewModel.audioCoordinator.currentTime)
        }
        .onDisappear {
            if scenePhase == .active {
                nowPlaying.clear()
            }
        }
    }

    private var header: some View {
        HStack(alignment: .top, spacing: 16) {
            AsyncImage(url: coverURL) { phase in
                if let image = phase.image {
                    image.resizable().scaledToFill()
                } else {
                    Color.gray.opacity(0.2)
                }
            }
            .frame(width: coverWidth, height: coverHeight)
            .clipShape(RoundedRectangle(cornerRadius: 10))
            .overlay(
                RoundedRectangle(cornerRadius: 10)
                    .stroke(Color.secondary.opacity(0.2), lineWidth: 1)
            )

            VStack(alignment: .leading, spacing: 6) {
                Text(item.bookTitle.isEmpty ? "Untitled" : item.bookTitle)
                    .font(titleFont)
                Text(item.author.isEmpty ? "Unknown author" : item.author)
                    .foregroundStyle(.secondary)
                Text(itemTypeLabel)
                    .font(.caption)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(Color.accentColor.opacity(0.2), in: Capsule())
            }
            Spacer()
        }
    }

    private var loadingView: some View {
        VStack(spacing: 12) {
            ProgressView()
            Text("Loading media…")
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, minHeight: 200)
    }

    private func errorView(message: String) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Label("Unable to load media", systemImage: "exclamationmark.triangle.fill")
                .foregroundStyle(.red)
            Text(message)
                .font(.callout)
        }
    }

    private var itemTypeLabel: String {
        switch item.itemType {
        case "video":
            return "Video"
        case "narrated_subtitle":
            return "Subtitles"
        default:
            return "Book"
        }
    }

    private var coverWidth: CGFloat {
        #if os(tvOS)
        return 140
        #else
        return 84
        #endif
    }

    private var coverHeight: CGFloat {
        #if os(tvOS)
        return 200
        #else
        return 120
        #endif
    }

    private var titleFont: Font {
        #if os(tvOS)
        return .title
        #else
        return .title2
        #endif
    }

    private var coverURL: URL? {
        guard let path = item.coverPath else { return nil }
        guard let apiBaseURL = appState.apiBaseURL else { return nil }
        let resolver = MediaURLResolver(origin: .library(apiBaseURL: apiBaseURL, accessToken: appState.authToken))
        return resolver.resolvePath(jobId: item.jobId, relativePath: path)
    }

    private var hasInteractiveChunks: Bool {
        guard let chunks = viewModel.jobContext?.chunks else { return false }
        return chunks.contains { !$0.sentences.isEmpty || $0.startSentence != nil || $0.endSentence != nil }
    }

    private var hasVideo: Bool {
        !(viewModel.mediaResponse?.media["video"] ?? []).isEmpty
    }

    private var isVideoPreferred: Bool {
        if item.itemType == "video" {
            return true
        }
        return hasVideo && !hasInteractiveChunks
    }

    private var videoURL: URL? {
        guard let files = viewModel.mediaResponse?.media["video"] else { return nil }
        for file in files {
            if let url = viewModel.resolveMediaURL(for: file) {
                return url
            }
        }
        return nil
    }

    private var subtitleURL: URL? {
        guard let files = viewModel.mediaResponse?.media["text"] else { return nil }
        for file in files {
            let name = (file.relativePath ?? file.path ?? file.name).lowercased()
            if name.hasSuffix(".vtt") || name.hasSuffix(".srt") {
                if let url = viewModel.resolveMediaURL(for: file) {
                    return url
                }
            }
        }
        return nil
    }

    private func loadEntry() async {
        guard let configuration = appState.configuration else { return }
        activeSentenceIndex = nil
        await viewModel.loadJob(jobId: item.jobId, configuration: configuration, origin: .library)
        if isVideoPreferred {
            nowPlaying.clear()
        } else {
            configureNowPlaying()
            updateNowPlayingMetadata()
            updateNowPlayingPlayback(time: viewModel.audioCoordinator.currentTime)
        }
    }

    private func configureNowPlaying() {
        nowPlaying.configureRemoteCommands(
            onPlay: { viewModel.audioCoordinator.play() },
            onPause: { viewModel.audioCoordinator.pause() },
            onNext: { viewModel.skipSentence(forward: true) },
            onPrevious: { viewModel.skipSentence(forward: false) },
            onSeek: { viewModel.audioCoordinator.seek(to: $0) },
            onToggle: { viewModel.audioCoordinator.togglePlayback() },
            onSkipForward: {
                viewModel.skipSentence(forward: true)
            },
            onSkipBackward: {
                viewModel.skipSentence(forward: false)
            },
            skipIntervalSeconds: 15
        )
    }

    private func updateNowPlayingMetadata() {
        let sentence = activeSentenceIndex.map { "Sentence \($0)" }
        let baseTitle = item.bookTitle.isEmpty ? "Interactive Reader" : item.bookTitle
        let title = sentence.map { "\(baseTitle) · \($0)" } ?? baseTitle
        nowPlaying.updateMetadata(
            title: title,
            artist: item.author.isEmpty ? nil : item.author,
            album: item.bookTitle.isEmpty ? nil : item.bookTitle,
            artworkURL: coverURL
        )
    }

    private func updateNowPlayingPlayback(time: Double) {
        guard !isVideoPreferred else { return }
        let highlightTime = viewModel.highlightingTime
        if let sentence = viewModel.activeSentence(at: highlightTime) {
            let index = sentence.displayIndex ?? sentence.id
            if activeSentenceIndex != index {
                activeSentenceIndex = index
                updateNowPlayingMetadata()
            }
        }
        nowPlaying.updatePlaybackState(
            isPlaying: viewModel.audioCoordinator.isPlaying,
            position: time,
            duration: viewModel.audioCoordinator.duration
        )
    }
}
