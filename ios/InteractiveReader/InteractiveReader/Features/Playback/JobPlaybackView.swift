import Foundation
import OSLog
import SwiftUI

struct JobPlaybackView: View {
    let playbackLogger = Logger(subsystem: "InteractiveReader", category: "PlaybackTransport")

    @EnvironmentObject var appState: AppState
    @EnvironmentObject var offlineStore: OfflineMediaStore
    @Environment(\.scenePhase) private var scenePhase
    @Environment(\.dismiss) var dismiss
    @Environment(\.colorScheme) private var colorScheme
    #if !os(tvOS)
    @Environment(\.horizontalSizeClass) private var horizontalSizeClass
    @Environment(\.verticalSizeClass) var verticalSizeClass
    #endif
    let job: PipelineStatusResponse
    @Binding var autoPlayOnLoad: Bool
    let playbackMode: PlaybackStartMode

    @StateObject var viewModel = InteractivePlayerViewModel()
    @StateObject var nowPlaying = NowPlayingCoordinator()
    @StateObject var musicOwnership = MusicKitCoordinator.shared
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
    @State var pendingInteractiveAutoplayID: UUID?
    @State var nowPlayingReassertionTask: Task<Void, Never>?
    @State var lastReaderTransportCommandTime: TimeInterval = 0
    @State var lastReaderTransportAction = "none"
    #if DEBUG
    @State var e2eReaderTransportCommandCount = 0
    @State var e2eTVPlayPauseCommandCount = 0
    #endif
    #if !os(tvOS)
    @State var showVideoPlayer = false
    #endif
    #if os(iOS)
    @AppStorage("videoPreviewVerticalOffset") var videoVerticalOffset: Double = 80
    @State var dragOffset: CGFloat = 0
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
            #if os(tvOS)
            .onPlayPauseCommand {
                handleTVPlayPauseCommand()
            }
            #endif
            #if os(iOS)
            .toolbarBackground(shouldUseInteractiveBackground ? Color.black : (usesDarkBackground ? AppTheme.lightBackground : Color.clear), for: .navigationBar)
            .toolbarBackground(.visible, for: .navigationBar)
            .toolbarColorScheme(.dark, for: .navigationBar)
            #endif
            .task(id: job.jobId) {
                @MainActor in
                await handleJobLoadTask()
            }
            .onChange(of: autoPlayOnLoad) { _, newValue in handleAutoPlayIntentChange(newValue) }
            .onChange(of: playbackMode) { _, newMode in handlePlaybackModeChange(newMode) }
            .onReceive(viewModel.audioCoordinator.$currentTime) { newValue in handleAudioTimeChange(newValue) }
            .onReceive(viewModel.audioCoordinator.$isPlaying) { _ in handleAudioStateChange() }
            .onReceive(viewModel.audioCoordinator.$duration) { _ in handleAudioStateChange() }
            .onReceive(viewModel.audioCoordinator.$isReady) { _ in handleAudioStateChange() }
            .onChange(of: musicOwnership.ownershipState) { _, state in handleAudioOwnershipChange(state) }
            .onReceive(musicOwnership.$isPlaying) { _ in handleMusicKitPlaybackSurfaceChange() }
            .onReceive(musicOwnership.$isManuallyPaused) { _ in handleMusicKitPlaybackSurfaceChange() }
            .onReceive(musicOwnership.$isPausedByReaderTransport) { _ in handleMusicKitPlaybackSurfaceChange() }
            .onReceive(musicOwnership.$isSuppressingMusicPlaybackSurface) { _ in handleMusicKitPlaybackSurfaceChange() }
            .onReceive(musicOwnership.$currentSongTitle) { _ in handleMusicKitPlaybackSurfaceChange() }
            .onReceive(musicOwnership.$playbackSurfaceRevision) { _ in handleMusicKitPlaybackSurfaceChange() }
            .onReceive(Timer.publish(every: 0.5, on: .main, in: .common).autoconnect()) { _ in
                handleMusicKitReadingBedWatchdogTick()
            }
            .onChange(of: videoSegments.map(\.id)) { _, _ in handleVideoSegmentsChange() }
            .onDisappear(perform: handleJobDisappear)
            .onChange(of: scenePhase) { _, newPhase in handleScenePhaseChange(newPhase) }
    }

    #if os(tvOS)
    private func handleTVPlayPauseCommand() {
        guard !isVideoPreferred else {
            playbackLogger.info("Job foreground tvOS Play/Pause ignored videoPreferred=true")
            return
        }
        #if DEBUG
        e2eTVPlayPauseCommandCount += 1
        #endif
        playbackLogger.info("Job foreground tvOS Play/Pause command")
        toggleReaderNowPlayingTransport(source: "foreground")
    }
    #endif

    @MainActor
    private func handleJobLoadTask() async {
        await loadEntry()
    }

    private func handlePlaybackModeChange(_ newMode: PlaybackStartMode) {
        // Re-apply start-over when iPad split layout keeps this view mounted.
        guard newMode == .startOver else { return }
        clearResumeEntry()
        startPlaybackFromBeginning()
    }

    private func handleAutoPlayIntentChange(_ shouldAutoPlay: Bool) {
        guard shouldAutoPlay, viewModel.loadState == .loaded else { return }
        autoPlayOnLoad = false
        applyPlaybackStartIntent()
    }

    private func applyPlaybackStartIntent() {
        switch playbackMode {
        case .resume:
            if let resumeEntry = resolveResumeEntry() {
                applyResume(resumeEntry)
            } else {
                startPlaybackFromBeginning()
            }
        case .resumeExisting:
            if let resumeEntry = resolveResumeEntry() {
                applyResume(resumeEntry)
            }
        case .startOver:
            clearResumeEntry()
            startPlaybackFromBeginning()
        }
    }

    private func handleAudioTimeChange(_ newValue: Double) {
        updateNowPlayingPlayback(time: newValue)
    }

    private func handleAudioStateChange() {
        if viewModel.audioCoordinator.isPlaying {
            pendingInteractiveAutoplayID = nil
        }
        updateNowPlayingPlayback(time: viewModel.audioCoordinator.currentTime)
        guard musicOwnership.ownershipState == .appleMusicBed else { return }
        publishReaderNowPlayingSnapshot(force: true)
        scheduleAppleMusicBedNowPlayingReassertion()
    }

    private func handleAudioOwnershipChange(_ state: AudioOwnership) {
        switch state {
        case .narration:
            nowPlayingReassertionTask?.cancel()
            nowPlayingReassertionTask = nil
            publishReaderNowPlayingSnapshot(force: true)
        case .appleMusicBed:
            publishReaderNowPlayingSnapshot(force: true)
            scheduleAppleMusicBedNowPlayingReassertion()
        case .appleMusic:
            nowPlayingReassertionTask?.cancel()
            nowPlayingReassertionTask = nil
            nowPlaying.setRemoteCommandsEnabled(false)
            nowPlaying.clear()
        case .transitioning:
            break
        }
    }

    private func handleMusicKitPlaybackSurfaceChange() {
        guard musicOwnership.ownershipState == .appleMusicBed else { return }
        if shouldMirrorAppleMusicPlayToNarration {
            playbackLogger.info(
                "Job playback mirroring Apple Music play to narration requested=\(viewModel.audioCoordinator.isPlaybackRequested, privacy: .public) playing=\(viewModel.audioCoordinator.isPlaying, privacy: .public) musicPlaying=\(musicOwnership.isPlaying, privacy: .public) manual=\(musicOwnership.isManuallyPaused, privacy: .public) readerPause=\(musicOwnership.isPausedByReaderTransport, privacy: .public)"
            )
            viewModel.audioCoordinator.play()
            publishReaderNowPlayingSnapshot(force: true)
            scheduleAppleMusicBedNowPlayingReassertion()
            return
        }
        if shouldMirrorAppleMusicPauseToNarration {
            playbackLogger.info(
                "Job playback mirroring Apple Music pause to narration requested=\(viewModel.audioCoordinator.isPlaybackRequested, privacy: .public) playing=\(viewModel.audioCoordinator.isPlaying, privacy: .public) musicPlaying=\(musicOwnership.isPlaying, privacy: .public) manual=\(musicOwnership.isManuallyPaused, privacy: .public) readerPause=\(musicOwnership.isPausedByReaderTransport, privacy: .public)"
            )
            viewModel.audioCoordinator.pause()
            publishReaderNowPlayingSnapshot(force: true)
            return
        }
        publishReaderNowPlayingSnapshot(force: true)
        scheduleAppleMusicBedNowPlayingReassertion()
    }

    private func handleMusicKitReadingBedWatchdogTick() {
        guard musicOwnership.ownershipState == .appleMusicBed else { return }
        musicOwnership.refreshMusicPlaybackSurfaceSuppression(reason: "jobWatchdog")
        guard !musicOwnership.isReaderTransportPauseGuardActive else { return }
        guard viewModel.audioCoordinator.isPlaybackRequested || viewModel.audioCoordinator.isPlaying else { return }
        if shouldMirrorAppleMusicPauseToNarration {
            playbackLogger.info(
                "Job playback watchdog pausing narration requested=\(viewModel.audioCoordinator.isPlaybackRequested, privacy: .public) playing=\(viewModel.audioCoordinator.isPlaying, privacy: .public) musicPlaying=\(musicOwnership.isPlaying, privacy: .public) manual=\(musicOwnership.isManuallyPaused, privacy: .public) readerPause=\(musicOwnership.isPausedByReaderTransport, privacy: .public)"
            )
            viewModel.audioCoordinator.pause()
            publishReaderNowPlayingSnapshot(force: true)
            return
        }
        musicOwnership.reconcileReadingBedSystemPlayback()
        musicOwnership.recoverReadingBedForActiveNarration(reason: "jobWatchdog")
    }

    func scheduleAppleMusicBedNowPlayingReassertion() {
        guard nowPlayingReassertionTask == nil else { return }
        nowPlayingReassertionTask = Task { @MainActor in
            defer { nowPlayingReassertionTask = nil }
            let reassertionDelays: [UInt64] = [
                75_000_000,
                150_000_000,
                300_000_000,
                500_000_000,
                850_000_000,
                1_200_000_000,
                1_800_000_000,
                2_500_000_000,
                5_000_000_000
            ]
            for delay in reassertionDelays {
                try? await Task.sleep(nanoseconds: delay)
                guard !Task.isCancelled else { return }
                guard shouldKeepReaderNowPlayingReassertionAlive else { return }
                musicOwnership.refreshMusicPlaybackSurfaceSuppression(reason: "jobNowPlayingReassertion")
                publishReaderNowPlayingSnapshot(force: true)
            }
            while !Task.isCancelled {
                try? await Task.sleep(nanoseconds: 1_000_000_000)
                guard shouldKeepReaderNowPlayingReassertionAlive else { return }
                musicOwnership.refreshMusicPlaybackSurfaceSuppression(reason: "jobNowPlayingReassertion")
                publishReaderNowPlayingSnapshot(force: true)
            }
        }
    }

    private var shouldKeepReaderNowPlayingReassertionAlive: Bool {
        musicOwnership.ownershipState == .appleMusicBed &&
            (musicOwnership.isSuppressingMusicPlaybackSurface ||
             (!musicOwnership.isManuallyPaused &&
              !musicOwnership.isPausedByReaderTransport &&
              (viewModel.audioCoordinator.isPlaybackRequested ||
               viewModel.audioCoordinator.isPlaying ||
               musicOwnership.isPlaying)))
    }

    private var shouldMirrorAppleMusicPauseToNarration: Bool {
        musicOwnership.isPausedByReaderTransport &&
            (viewModel.audioCoordinator.isPlaybackRequested || viewModel.audioCoordinator.isPlaying)
    }

    private var shouldMirrorAppleMusicPlayToNarration: Bool {
        musicOwnership.isPlaying &&
            !musicOwnership.isManuallyPaused &&
            !musicOwnership.isPausedByReaderTransport &&
            !musicOwnership.isReaderTransportPauseGuardActive &&
            !viewModel.audioCoordinator.isPlaybackRequested &&
            !viewModel.audioCoordinator.isPlaying
    }

    private func handleVideoSegmentsChange() {
        refreshActiveVideoSegment()
        preloadSegmentDurations()
    }

    private func handleJobDisappear() {
        persistResumeOnExit()
        segmentDurationTask?.cancel()
        segmentDurationTask = nil
        if shouldKeepReaderNowPlayingReassertionAlive {
            publishReaderNowPlayingSnapshot(force: true)
            scheduleAppleMusicBedNowPlayingReassertion()
        } else {
            nowPlayingReassertionTask?.cancel()
            nowPlayingReassertionTask = nil
        }
        stopJobRefresh()
        viewModel.stopLiveUpdates()
        // Do not reset audio here; iPad split-view can emit incidental disappear events.
        if shouldClearNowPlayingOnDisappear {
            nowPlaying.clear()
        }
    }

    private var shouldClearNowPlayingOnDisappear: Bool {
        scenePhase == .active &&
            !viewModel.audioCoordinator.isPlaybackRequested &&
            !viewModel.audioCoordinator.isPlaying &&
            musicOwnership.ownershipState != .appleMusicBed
    }

    private func handleScenePhaseChange(_ newPhase: ScenePhase) {
        if musicOwnership.ownershipState == .appleMusicBed {
            publishReaderNowPlayingSnapshot(force: true)
            scheduleAppleMusicBedNowPlayingReassertion()
        }
        guard newPhase != .active else { return }
        persistResumeOnExit()
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
            MediaDiagnosticsStripView(
                diagnostics: viewModel.mediaResponse?.diagnostics,
                usesDarkBackground: usesDarkBackground || shouldUseInteractiveBackground
            )
            switch viewModel.loadState {
            case .idle, .loading:
                loadingView
            case let .error(message):
                errorView(message: message)
            case .loaded:
                if isVideoPreferred, let videoURL {
                    #if os(tvOS)
                    jobVideoPlayer(videoURL: videoURL)
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
                        bookmarkItemType: resumeItemType,
                        playbackToggleOverride: {
                            toggleReaderNowPlayingTransport()
                        }
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
        .fullScreenCover(isPresented: $showVideoPlayer, onDismiss: handleVideoPlayerDismiss) {
            fullscreenVideoPlayer
        }
        #endif
        #if DEBUG
        .overlay(alignment: .bottomLeading) {
            MusicBedSyncE2EControls(
                musicOwnership: musicOwnership,
                audioCoordinator: viewModel.audioCoordinator,
                readerTransportCommandCount: e2eReaderTransportCommandCount,
                foregroundPlayPauseCount: e2eTVPlayPauseCommandCount,
                lastReaderTransportAction: lastReaderTransportAction,
                onReaderPlayCommand: { playReaderNowPlayingTransport() },
                onReaderPauseCommand: { pauseReaderNowPlayingTransport() }
            )
        }
        #endif
        #if os(iOS)
        if shouldHideInteractiveNavigation {
            base
                .overlay(alignment: .leading) {
                    EdgeSwipeBackOverlay(onBack: handleEdgeSwipeBack)
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

    /// Whether Apple Music owns the lock screen.
    /// Apple Music used as the reading bed keeps reader-owned sentence controls.
    var isAppleMusicOwningLockScreen: Bool {
        musicOwnership.ownershipState == .appleMusic
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

    var totalSentenceCount: Int? {
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

    func updateNowPlayingMetadata(sentenceIndex: Int?) {
        guard !isAppleMusicOwningLockScreen else { return }
        let totalSentences = totalSentenceCount
        let sentence = sentenceIndex.flatMap { index -> String? in
            guard index > 0 else { return nil }
            if let totalSentences, totalSentences > 0 {
                return "Sentence \(index) of \(totalSentences)"
            }
            return "Sentence \(index)"
        }
        let title = sentence.map { "\(jobTitle) · \($0)" } ?? jobTitle
        nowPlaying.updateMetadata(
            title: title,
            artist: jobAuthor.nonEmptyValue,
            album: jobTitle.nonEmptyValue,
            artworkURL: coverURL,
            queueIndex: sentenceIndex.map { max($0 - 1, 0) },
            queueCount: totalSentences
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
