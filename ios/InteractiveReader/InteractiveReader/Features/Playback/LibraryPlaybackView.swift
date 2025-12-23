import SwiftUI

struct LibraryPlaybackView: View {
    @EnvironmentObject var appState: AppState
    @Environment(\.scenePhase) private var scenePhase
    #if !os(tvOS)
    @Environment(\.horizontalSizeClass) private var horizontalSizeClass
    #endif
    let item: LibraryItem

    @StateObject private var viewModel = InteractivePlayerViewModel()
    @StateObject private var nowPlaying = NowPlayingCoordinator()
    @State private var sentenceIndexTracker = SentenceIndexTracker()
    @State private var showImageReel = true

    var body: some View {
        VStack(alignment: .leading, spacing: rootSpacing) {
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
                    InteractivePlayerView(
                        viewModel: viewModel,
                        audioCoordinator: viewModel.audioCoordinator,
                        showImageReel: $showImageReel
                    )
                } else {
                    Text("No playable media found for this entry.")
                        .foregroundStyle(.secondary)
                }
            }
        }
        #if os(tvOS)
        .padding(EdgeInsets(top: 8, leading: 16, bottom: 12, trailing: 16))
        #else
        .padding()
        #endif
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
        .navigationTitle(item.bookTitle)
        .task(id: item.jobId) {
            await loadEntry()
        }
        .onReceive(viewModel.audioCoordinator.$currentTime) { newValue in
            updateNowPlayingPlayback(time: newValue)
        }
        .onReceive(viewModel.audioCoordinator.$isPlaying) { _ in
            updateNowPlayingPlayback(time: viewModel.audioCoordinator.currentTime)
        }
        .onReceive(viewModel.audioCoordinator.$duration) { _ in
            updateNowPlayingPlayback(time: viewModel.audioCoordinator.currentTime)
        }
        .onReceive(viewModel.audioCoordinator.$isReady) { _ in
            updateNowPlayingPlayback(time: viewModel.audioCoordinator.currentTime)
        }
        .onDisappear {
            #if os(tvOS)
            viewModel.audioCoordinator.reset()
            #endif
            if scenePhase == .active {
                nowPlaying.clear()
            }
        }
    }

    @ViewBuilder
    private var header: some View {
        #if os(tvOS)
        HStack(alignment: .top, spacing: headerSpacing) {
            headerInfo
            if showImageReel, !imageReelURLs.isEmpty {
                Spacer(minLength: 12)
                LibraryImageReel(urls: imageReelURLs, height: coverHeight)
                    .frame(maxWidth: .infinity, alignment: .trailing)
            } else {
                Spacer()
            }
        }
        #else
        if horizontalSizeClass == .regular {
            HStack(alignment: .top, spacing: headerSpacing) {
                headerInfo
                if showImageReel, !imageReelURLs.isEmpty {
                    Spacer(minLength: 12)
                    LibraryImageReel(urls: imageReelURLs, height: coverHeight)
                        .frame(maxWidth: .infinity, alignment: .trailing)
                } else {
                    Spacer()
                }
            }
        } else {
            VStack(alignment: .leading, spacing: headerSpacing) {
                headerInfo
                if showImageReel, !imageReelURLs.isEmpty {
                    LibraryImageReel(urls: imageReelURLs, height: coverHeight)
                        .frame(maxWidth: .infinity, alignment: .leading)
                }
            }
        }
        #endif
    }

    private var headerInfo: some View {
        HStack(alignment: .top, spacing: headerSpacing) {
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

            VStack(alignment: .leading, spacing: headerTextSpacing) {
                Text(item.bookTitle.isEmpty ? "Untitled" : item.bookTitle)
                    .font(titleFont)
                    .lineLimit(titleLineLimit)
                    .minimumScaleFactor(0.9)
                    .truncationMode(.tail)
                Text(item.author.isEmpty ? "Unknown author" : item.author)
                    .font(authorFont)
                    .lineLimit(1)
                    .minimumScaleFactor(0.85)
                    .foregroundStyle(.secondary)
                Text(itemTypeLabel)
                    .font(metaFont)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(Color.accentColor.opacity(0.2), in: Capsule())
            }
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
        return 96
        #else
        return 64
        #endif
    }

    private var coverHeight: CGFloat {
        #if os(tvOS)
        return 144
        #else
        return 96
        #endif
    }

    private var titleFont: Font {
        #if os(tvOS)
        return .title2
        #else
        return .title2
        #endif
    }

    private var authorFont: Font {
        #if os(tvOS)
        return .callout
        #else
        return .callout
        #endif
    }

    private var metaFont: Font {
        #if os(tvOS)
        return .caption2
        #else
        return .caption
        #endif
    }

    private var titleLineLimit: Int {
        #if os(tvOS)
        return 2
        #else
        return 3
        #endif
    }

    private var rootSpacing: CGFloat {
        #if os(tvOS)
        return 12
        #else
        return 16
        #endif
    }

    private var headerSpacing: CGFloat {
        #if os(tvOS)
        return 10
        #else
        return 12
        #endif
    }

    private var headerTextSpacing: CGFloat {
        #if os(tvOS)
        return 4
        #else
        return 6
        #endif
    }

    private var imageReelURLs: [URL] {
        guard let chunk = viewModel.selectedChunk else { return [] }
        let hasExplicitImage = chunk.sentences.contains { sentence in
            if let rawPath = sentence.imagePath, rawPath.nonEmptyValue != nil {
                return true
            }
            return false
        }
        guard hasExplicitImage else { return [] }
        var urls: [URL] = []
        var seen: Set<String> = []
        for sentence in chunk.sentences {
            guard let path = resolveSentenceImagePath(sentence: sentence, chunk: chunk) else { continue }
            guard !seen.contains(path) else { continue }
            seen.insert(path)
            if let url = viewModel.resolvePath(path) {
                urls.append(url)
            }
            if urls.count >= 7 {
                break
            }
        }
        return urls
    }

    private func resolveSentenceImagePath(sentence: InteractiveChunk.Sentence, chunk: InteractiveChunk) -> String? {
        if let rawPath = sentence.imagePath, let path = rawPath.nonEmptyValue {
            return path
        }
        guard let rangeFragment = chunk.rangeFragment?.nonEmptyValue else { return nil }
        let sentenceNumber = sentence.displayIndex ?? sentence.id
        guard sentenceNumber > 0 else { return nil }
        let padded = String(format: "%05d", sentenceNumber)
        return "media/images/\(rangeFragment)/sentence_\(padded).png"
    }

    private var coverURL: URL? {
        guard let apiBaseURL = appState.apiBaseURL else { return nil }
        let resolver = LibraryCoverResolver(apiBaseURL: apiBaseURL, accessToken: appState.authToken)
        return resolver.resolveCoverURL(for: item)
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

    @MainActor
    private func loadEntry() async {
        guard let configuration = appState.configuration else { return }
        sentenceIndexTracker.value = nil
        await viewModel.loadJob(jobId: item.jobId, configuration: configuration, origin: .library)
        if isVideoPreferred {
            nowPlaying.clear()
        } else {
            configureNowPlaying()
            updateNowPlayingMetadata(sentenceIndex: sentenceIndexTracker.value)
            updateNowPlayingPlayback(time: viewModel.audioCoordinator.currentTime)
            #if os(tvOS)
            if viewModel.jobContext != nil {
                viewModel.audioCoordinator.play()
            }
            #endif
            #if !os(tvOS)
            if viewModel.jobContext != nil {
                viewModel.audioCoordinator.play()
            }
            #endif
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
            onSkipForward: nil,
            onSkipBackward: nil
        )
    }

    private func updateNowPlayingMetadata(sentenceIndex: Int?) {
        let totalSentences = totalSentenceCount
        let sentence = sentenceIndex.flatMap { index -> String? in
            guard index > 0 else { return nil }
            if let totalSentences, totalSentences > 0 {
                return "Sentence \(index) of \(totalSentences)"
            }
            return "Sentence \(index)"
        }
        let baseTitle = item.bookTitle.isEmpty ? "Interactive Reader" : item.bookTitle
        let title = sentence.map { "\(baseTitle) · \($0)" } ?? baseTitle
        nowPlaying.updateMetadata(
            title: title,
            artist: item.author.isEmpty ? nil : item.author,
            album: item.bookTitle.isEmpty ? nil : item.bookTitle,
            artworkURL: coverURL,
            queueIndex: sentenceIndex.map { max($0 - 1, 0) },
            queueCount: totalSentences
        )
    }

    private func updateNowPlayingPlayback(time: Double) {
        guard !isVideoPreferred else { return }
        let highlightTime = viewModel.highlightingTime
        if let sentence = viewModel.activeSentence(at: highlightTime) {
            let index = sentence.displayIndex ?? sentence.id
            if sentenceIndexTracker.value != index {
                sentenceIndexTracker.value = index
                updateNowPlayingMetadata(sentenceIndex: index)
            }
        }
        let playbackDuration = viewModel.selectedChunk.flatMap { viewModel.playbackDuration(for: $0) } ?? viewModel.audioCoordinator.duration
        let playbackTime = highlightTime.isFinite ? highlightTime : time
        nowPlaying.updatePlaybackState(
            isPlaying: viewModel.audioCoordinator.isPlaying,
            position: playbackTime,
            duration: playbackDuration
        )
    }

    private var totalSentenceCount: Int? {
        guard let context = viewModel.jobContext else { return nil }
        var total = 0
        for chunk in context.chunks {
            if let start = chunk.startSentence, let end = chunk.endSentence, end >= start {
                total += end - start + 1
            } else if !chunk.sentences.isEmpty {
                total += chunk.sentences.count
            }
        }
        return total > 0 ? total : nil
    }

}

private final class SentenceIndexTracker {
    var value: Int?
}

private struct LibraryImageReel: View {
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
