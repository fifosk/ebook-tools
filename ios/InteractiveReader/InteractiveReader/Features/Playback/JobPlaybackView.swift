import Foundation
import SwiftUI

struct JobPlaybackView: View {
    @EnvironmentObject var appState: AppState
    @EnvironmentObject var offlineStore: OfflineMediaStore
    @Environment(\.scenePhase) private var scenePhase
    @Environment(\.dismiss) private var dismiss
    @Environment(\.colorScheme) private var colorScheme
    #if !os(tvOS)
    @Environment(\.horizontalSizeClass) private var horizontalSizeClass
    @Environment(\.verticalSizeClass) private var verticalSizeClass
    #endif
    let job: PipelineStatusResponse
    @Binding var autoPlayOnLoad: Bool
    let playbackMode: PlaybackStartMode

    @StateObject var viewModel = InteractivePlayerViewModel()
    @StateObject var nowPlaying = NowPlayingCoordinator()
    @State var sentenceIndex: Int?
    @State var showImageReel = true
    @State var videoResumeTime: Double?
    @State var videoResumeActionID = UUID()
    @State var videoAutoPlay = false
    @State var activeVideoSegmentID: String?
    @State var jobStatus: PipelineStatusResponse?
    @State var subtitleTvMetadata: SubtitleTvMetadataResponse?
    @State var youtubeVideoMetadata: YoutubeVideoMetadataResponse?
    @State var jobRefreshTask: Task<Void, Never>?
    @State var completedSegmentDurations: [String: Double] = [:]
    @State var segmentDurations: [String: Double] = [:]
    @State var segmentDurationTask: Task<Void, Never>?
    @State var lastRecordedSentence: Int?
    @State var lastRecordedTimeBucket: Int?
    @State var lastVideoTime: Double = 0
    @State var resumeDecisionPending = false
    #if !os(tvOS)
    @State var showVideoPlayer = false
    #endif
    #if os(iOS)
    @AppStorage("videoPreviewVerticalOffset") private var videoVerticalOffset: Double = 80
    @State private var dragOffset: CGFloat = 0
    #endif

    let jobRefreshInterval: UInt64 = 6_000_000_000
    let summaryLengthLimit: Int = 320

    init(job: PipelineStatusResponse, autoPlayOnLoad: Binding<Bool> = .constant(true), playbackMode: PlaybackStartMode = .resume) {
        self.job = job
        self._autoPlayOnLoad = autoPlayOnLoad
        self.playbackMode = playbackMode
    }

    var body: some View {
        bodyContent
            .navigationTitle(navigationTitleText)
            #if os(iOS)
            .toolbarBackground(shouldUseInteractiveBackground ? Color.black : (usesDarkBackground ? AppTheme.lightBackground : Color.clear), for: .navigationBar)
            .toolbarBackground(.visible, for: .navigationBar)
            .toolbarColorScheme(.dark, for: .navigationBar)
            #endif
            .task(id: job.jobId) {
                @MainActor in
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
            .onChange(of: videoSegments.map(\.id)) { _, _ in
                refreshActiveVideoSegment()
                preloadSegmentDurations()
            }
            .onDisappear {
                persistResumeOnExit()
                segmentDurationTask?.cancel()
                segmentDurationTask = nil
                stopJobRefresh()
                viewModel.stopLiveUpdates()
                viewModel.audioCoordinator.reset()
                if scenePhase == .active {
                    nowPlaying.clear()
                }
            }
            .onChange(of: scenePhase) { _, newPhase in
                guard newPhase != .active else { return }
                persistResumeOnExit()
            }
    }

    var navigationTitleText: String {
        shouldHideNavigationTitle ? "" : jobTitle
    }

    var shouldHideNavigationTitle: Bool {
        viewModel.jobContext != nil && !isVideoPreferred
    }

    var shouldUseInteractiveBackground: Bool {
        viewModel.jobContext != nil && !isVideoPreferred
    }

    /// Whether to use dark background (iPad in light mode, matching tvOS style)
    private var usesDarkBackground: Bool {
        #if os(iOS)
        return horizontalSizeClass != .compact && colorScheme == .light
        #else
        return false
        #endif
    }

    #if os(iOS)
    private var shouldHideInteractiveNavigation: Bool {
        shouldUseInteractiveBackground && UIDevice.current.userInterfaceIdiom == .phone
    }
    #endif

    var standardBodyPadding: EdgeInsets {
        #if os(tvOS)
        return shouldUseInteractiveBackground
            ? EdgeInsets()
            : EdgeInsets(top: 8, leading: 16, bottom: 12, trailing: 16)
        #else
        return shouldUseInteractiveBackground
            ? EdgeInsets()
            : EdgeInsets(top: 16, leading: 16, bottom: 16, trailing: 16)
        #endif
    }

    /// Whether video preview position can be adjusted by dragging (iPhone portrait only)
    private var canDragVideoPreview: Bool {
        #if os(iOS)
        return UIDevice.current.userInterfaceIdiom == .phone && verticalSizeClass == .regular
        #else
        return false
        #endif
    }

    /// Extra top padding for video preview on iPhone portrait mode
    private var videoTopPadding: CGFloat {
        #if os(iOS)
        guard canDragVideoPreview else { return 0 }
        return CGFloat(videoVerticalOffset) + dragOffset
        #else
        return 0
        #endif
    }

    @ViewBuilder
    var bodyContent: some View {
        #if os(tvOS)
        if isVideoPreferred {
            tvVideoBody
        } else {
            standardBody
        }
        #else
        standardBody
        #endif
    }

    @ViewBuilder
    var standardBody: some View {
        let base = VStack(alignment: .leading, spacing: 12) {
            switch viewModel.loadState {
            case .idle, .loading:
                loadingView
            case let .error(message):
                errorView(message: message)
            case .loaded:
                if isVideoPreferred, let videoURL {
                    #if os(tvOS)
                    VideoPlayerView(
                        videoURL: videoURL,
                        subtitleTracks: subtitleTracks,
                        metadata: videoMetadata,
                        autoPlay: videoAutoPlay,
                        resumeTime: videoResumeTime,
                        resumeActionID: videoResumeActionID,
                        nowPlaying: nowPlaying,
                        linguistInputLanguage: linguistInputLanguage,
                        linguistLookupLanguage: linguistLookupLanguage,
                        segmentOptions: videoSegmentOptions,
                        selectedSegmentID: activeVideoSegmentID ?? videoSegments.first?.id,
                        onSelectSegment: handleVideoSegmentSelection,
                        jobProgressLabel: jobProgressLabel,
                        jobRemainingLabel: jobRemainingLabel,
                        onPlaybackProgress: handleVideoPlaybackProgress,
                        onPlaybackEnded: handleVideoSegmentEnded,
                        bookmarkUserId: resumeUserId,
                        bookmarkJobId: currentJob.jobId,
                        bookmarkItemType: resumeItemType
                    )
                    .frame(maxWidth: .infinity)
                    .aspectRatio(16 / 9, contentMode: .fit)
                    #else
                    // Show empty placeholder when video player is presenting/presented
                    // This avoids showing the preview briefly before fullscreen cover
                    VStack(spacing: 0) {
                        Spacer()
                            .frame(height: max(0, videoTopPadding))
                        if showVideoPlayer {
                            Color.black
                                .frame(maxWidth: .infinity)
                                .aspectRatio(16 / 9, contentMode: .fit)
                        } else {
                            videoPreview
                                .frame(maxWidth: .infinity)
                                .aspectRatio(16 / 9, contentMode: .fit)
                        }
                        Spacer()
                    }
                    .frame(maxHeight: .infinity)
                    .contentShape(Rectangle())
                    .simultaneousGesture(videoPreviewDragGesture)
                    #endif
                } else if viewModel.jobContext != nil {
                    InteractivePlayerView(
                        viewModel: viewModel,
                        audioCoordinator: viewModel.audioCoordinator,
                        showImageReel: $showImageReel,
                        showsScrubber: false,
                        linguistInputLanguage: linguistInputLanguage,
                        linguistLookupLanguage: linguistLookupLanguage,
                        headerInfo: interactiveHeaderInfo,
                        bookmarkUserId: resumeUserId,
                        bookmarkJobId: currentJob.jobId,
                        bookmarkItemType: resumeItemType
                    )
                } else {
                    Text("No playable media found for this job.")
                        .foregroundStyle(.secondary)
                }
            }
        }
        .padding(standardBodyPadding)
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
        .background {
            if shouldUseInteractiveBackground {
                Color.black.ignoresSafeArea()
            } else if usesDarkBackground {
                AppTheme.lightBackground.ignoresSafeArea()
            }
        }
        #if !os(tvOS)
        .fullScreenCover(isPresented: $showVideoPlayer, onDismiss: {
            // When video player is dismissed, also dismiss this view to go back to menu
            dismiss()
        }) {
            if let videoURL {
                VideoPlayerView(
                    videoURL: videoURL,
                    subtitleTracks: subtitleTracks,
                    metadata: videoMetadata,
                    autoPlay: videoAutoPlay,
                    resumeTime: videoResumeTime,
                    resumeActionID: videoResumeActionID,
                    nowPlaying: nowPlaying,
                    linguistInputLanguage: linguistInputLanguage,
                    linguistLookupLanguage: linguistLookupLanguage,
                    segmentOptions: videoSegmentOptions,
                    selectedSegmentID: activeVideoSegmentID ?? videoSegments.first?.id,
                    onSelectSegment: handleVideoSegmentSelection,
                    jobProgressLabel: jobProgressLabel,
                    jobRemainingLabel: jobRemainingLabel,
                    onPlaybackProgress: handleVideoPlaybackProgress,
                    onPlaybackEnded: handleVideoSegmentEnded,
                    bookmarkUserId: resumeUserId,
                    bookmarkJobId: currentJob.jobId,
                    bookmarkItemType: resumeItemType
                )
                .ignoresSafeArea()
            } else {
                Color.black
                    .ignoresSafeArea()
            }
        }
        #endif
        #if os(iOS)
        if shouldHideInteractiveNavigation {
            base
                .overlay(alignment: .leading) {
                    EdgeSwipeBackOverlay {
                        dismiss()
                    }
                }
                .toolbar(.hidden, for: .navigationBar)
                .navigationBarBackButtonHidden(true)
        } else {
            base
        }
        #else
        base
        #endif
    }

    #if os(tvOS)
    var tvVideoBody: some View {
        ZStack {
            switch viewModel.loadState {
            case .idle, .loading:
                loadingView
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            case let .error(message):
                errorView(message: message)
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            case .loaded:
                if let videoURL {
                    VideoPlayerView(
                        videoURL: videoURL,
                        subtitleTracks: subtitleTracks,
                        metadata: videoMetadata,
                        autoPlay: videoAutoPlay,
                        resumeTime: videoResumeTime,
                        resumeActionID: videoResumeActionID,
                        nowPlaying: nowPlaying,
                        linguistInputLanguage: linguistInputLanguage,
                        linguistLookupLanguage: linguistLookupLanguage,
                        segmentOptions: videoSegmentOptions,
                        selectedSegmentID: activeVideoSegmentID ?? videoSegments.first?.id,
                        onSelectSegment: handleVideoSegmentSelection,
                        jobProgressLabel: jobProgressLabel,
                        jobRemainingLabel: jobRemainingLabel,
                        onPlaybackProgress: handleVideoPlaybackProgress,
                        onPlaybackEnded: handleVideoSegmentEnded,
                        bookmarkUserId: resumeUserId,
                        bookmarkJobId: currentJob.jobId,
                        bookmarkItemType: resumeItemType
                    )
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                } else {
                    Text("No playable media found for this job.")
                        .foregroundStyle(.secondary)
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                }
            }
        }
        .ignoresSafeArea()
        .toolbar(.hidden, for: .navigationBar)
    }
    #endif

    var loadingView: some View {
        VStack(spacing: 12) {
            ProgressView()
                .tint(usesDarkBackground ? .white : nil)
            Text("Loading media…")
                .foregroundStyle(usesDarkBackground ? .white.opacity(0.7) : .secondary)
        }
        .frame(maxWidth: .infinity, minHeight: 200)
    }

    func errorView(message: String) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Label("Unable to load media", systemImage: "exclamationmark.triangle.fill")
                .foregroundStyle(.red)
            Text(message)
                .font(.callout)
                .foregroundStyle(usesDarkBackground ? .white.opacity(0.7) : .secondary)
        }
    }

    #if !os(tvOS)
    var videoPreview: some View {
        Button {
            handleVideoPreviewTap()
        } label: {
            ZStack {
                if let coverURL {
                    AsyncImage(url: coverURL) { phase in
                        if let image = phase.image {
                            image.resizable().scaledToFill()
                        } else {
                            Color.black.opacity(0.2)
                        }
                    }
                } else {
                    Color.black.opacity(0.2)
                }
                Color.black.opacity(0.35)
                VStack(spacing: 10) {
                    Image(systemName: "play.fill")
                        .font(.system(size: 34, weight: .semibold))
                    Text("Play Video")
                        .font(.headline)
                }
                .foregroundStyle(.white)
            }
            .clipShape(RoundedRectangle(cornerRadius: 14))
        }
        .buttonStyle(.plain)
    }

    #if os(iOS)
    var videoPreviewDragGesture: some Gesture {
        DragGesture(minimumDistance: 10)
            .onChanged { value in
                guard canDragVideoPreview else { return }
                dragOffset = value.translation.height
            }
            .onEnded { value in
                guard canDragVideoPreview else { return }
                let newOffset = videoVerticalOffset + Double(value.translation.height)
                // Clamp between 0 and 300 points
                videoVerticalOffset = min(max(newOffset, 0), 300)
                dragOffset = 0
            }
    }
    #else
    var videoPreviewDragGesture: some Gesture {
        DragGesture().onChanged { _ in }
    }
    #endif
    #endif

    var hasInteractiveChunks: Bool {
        guard let chunks = viewModel.jobContext?.chunks else { return false }
        return chunks.contains { !$0.sentences.isEmpty || $0.startSentence != nil || $0.endSentence != nil }
    }

    var hasVideo: Bool {
        guard let media = viewModel.mediaResponse?.media else { return false }
        return !resolveVideoFiles(from: media).isEmpty
    }

    var isVideoPreferred: Bool {
        if jobVariant == .video || jobVariant == .youtube || jobVariant == .dub {
            return true
        }
        return hasVideo && !hasInteractiveChunks
    }

    var jobProgressLabel: String? {
        let statusLabel = jobStatusLabel
        if let percent = jobProgressPercent {
            return "\(statusLabel) · \(percent)%"
        }
        return statusLabel
    }

    var resolvedTvEpisodeLabel: String? {
        guard let tvMetadata = resolvedTvMetadata,
              let episode = tvMetadata["episode"]?.objectValue
        else {
            return nil
        }
        let season = intValue(episode["season"])
        let number = intValue(episode["number"])
        let code: String? = {
            guard let season, let number, season > 0, number > 0 else { return nil }
            return String(format: "S%02dE%02d", season, number)
        }()
        let episodeTitle = episode["name"]?.stringValue?.nonEmptyValue
        let airdate = episode["airdate"]?.stringValue?.nonEmptyValue
        let parts = [code, episodeTitle, airdate].compactMap { $0 }
        return parts.isEmpty ? nil : parts.joined(separator: " · ")
    }

    func updateNowPlayingMetadata(sentenceIndex: Int?) {
        let title: String
        if let sentenceIndex, sentenceIndex > 0 {
            title = "\(jobTitle) · Sentence \(sentenceIndex)"
        } else {
            title = jobTitle
        }
        nowPlaying.updateMetadata(
            title: title,
            artist: jobAuthor.nonEmptyValue,
            album: jobTitle.nonEmptyValue,
            artworkURL: coverURL,
            queueIndex: sentenceIndex.map { max($0 - 1, 0) },
            queueCount: nil
        )
    }

    func segmentLabel(for segment: JobVideoSegment, index: Int) -> String {
        let base = "Chunk \(index + 1)"
        if let chunk = segment.chunk {
            if let start = chunk.startSentence, let end = chunk.endSentence {
                return "\(base) · Sentences \(start)-\(end)"
            }
            if let start = chunk.startSentence {
                return "\(base) · Sentence \(start)"
            }
            if let range = chunk.rangeFragment?.nonEmptyValue {
                return "\(base) · \(range)"
            }
            if let chunkID = chunk.chunkID?.nonEmptyValue {
                return "\(base) · ID \(chunkID)"
            }
        }
        if let start = segment.videoFile.startSentence, let end = segment.videoFile.endSentence {
            return "\(base) · Sentences \(start)-\(end)"
        }
        if let start = segment.videoFile.startSentence {
            return "\(base) · Sentence \(start)"
        }
        if let range = segment.videoFile.rangeFragment?.nonEmptyValue {
            return "\(base) · \(range)"
        }
        if let chunkID = segment.videoFile.chunkID?.nonEmptyValue {
            return "\(base) · ID \(chunkID)"
        }
        return base
    }
}

struct EdgeSwipeBackOverlay: View {
    let onBack: () -> Void
    var edgeWidth: CGFloat = 28
    var minimumDistance: CGFloat = 18
    var requiredTranslation: CGFloat = 60
    var maxVerticalTranslation: CGFloat = 40
    #if os(iOS)
    @Environment(\.verticalSizeClass) private var verticalSizeClass
    #endif

    private var resolvedEdgeWidth: CGFloat {
        #if os(iOS)
        guard UIDevice.current.userInterfaceIdiom == .phone else { return edgeWidth }
        if verticalSizeClass == .compact {
            return max(edgeWidth, 44)
        }
        return edgeWidth
        #else
        return edgeWidth
        #endif
    }

    var body: some View {
        #if os(tvOS)
        Color.clear
            .frame(width: resolvedEdgeWidth)
            .frame(maxHeight: .infinity, alignment: .leading)
            .accessibilityHidden(true)
        #else
        Color.clear
            .contentShape(Rectangle())
            .gesture(
                DragGesture(minimumDistance: minimumDistance, coordinateSpace: .local)
                    .onEnded { value in
                        guard value.translation.width > requiredTranslation else { return }
                        guard abs(value.translation.height) < maxVerticalTranslation else { return }
                        onBack()
                    }
            )
            .frame(width: resolvedEdgeWidth)
            .frame(maxHeight: .infinity, alignment: .leading)
            .accessibilityHidden(true)
            .ignoresSafeArea(edges: .leading)
        #endif
    }
}
