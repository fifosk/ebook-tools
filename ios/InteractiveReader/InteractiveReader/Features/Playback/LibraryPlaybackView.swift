import Foundation
import SwiftUI
#if os(iOS)
import UIKit
#endif

struct LibraryPlaybackView: View {
    @EnvironmentObject var appState: AppState
    @EnvironmentObject var offlineStore: OfflineMediaStore
    @Environment(\.scenePhase) private var scenePhase
    @Environment(\.dismiss) var dismiss
    @Environment(\.colorScheme) private var colorScheme
    #if !os(tvOS)
    @Environment(\.horizontalSizeClass) private var horizontalSizeClass
    @Environment(\.verticalSizeClass) private var verticalSizeClass
    #endif
    let item: LibraryItem
    @Binding var autoPlayOnLoad: Bool
    let playbackMode: PlaybackStartMode

    @StateObject var viewModel = InteractivePlayerViewModel()
    @StateObject var nowPlaying = NowPlayingCoordinator()
    @State var resumeManager: PlaybackResumeManager?
    @State private var sentenceIndexTracker = SentenceIndexTracker()
    @State private var showImageReel = true
    #if !os(tvOS)
    @State var showVideoPlayer = false
    #endif
    #if os(iOS)
    @AppStorage("videoPreviewVerticalOffset") var videoVerticalOffset: Double = 80
    @State var dragOffset: CGFloat = 0
    #endif

    init(item: LibraryItem, autoPlayOnLoad: Binding<Bool> = .constant(true), playbackMode: PlaybackStartMode = .resume) {
        self.item = item
        self._autoPlayOnLoad = autoPlayOnLoad
        self.playbackMode = playbackMode
    }

    var body: some View {
        bodyContent
        .accessibilityIdentifier("libraryPlaybackView")
        .navigationTitle(navigationTitleText)
        #if os(iOS)
        .toolbarBackground(shouldUseInteractiveBackground ? Color.black : (usesDarkBackground ? AppTheme.lightBackground : Color.clear), for: .navigationBar)
        .toolbarBackground(.visible, for: .navigationBar)
        .toolbarColorScheme(.dark, for: .navigationBar)
        #endif
        .task(id: item.jobId) {
            @MainActor in
            await handleLibraryLoadTask()
        }
        .onChange(of: playbackMode) { _, newMode in handlePlaybackModeChange(newMode) }
        .onReceive(viewModel.audioCoordinator.$currentTime) { newValue in handleAudioTimeChange(newValue) }
        .onReceive(viewModel.audioCoordinator.$isPlaying) { _ in handleAudioStateChange() }
        .onReceive(viewModel.audioCoordinator.$duration) { _ in handleAudioStateChange() }
        .onReceive(viewModel.audioCoordinator.$isReady) { _ in handleAudioStateChange() }
        .onDisappear(perform: handleLibraryDisappear)
        .onChange(of: scenePhase) { _, newPhase in handleScenePhaseChange(newPhase) }
    }

    @MainActor
    private func handleLibraryLoadTask() async {
        await loadEntry()
    }

    private func handlePlaybackModeChange(_ newMode: PlaybackStartMode) {
        // Re-apply start-over when iPad split layout keeps this view mounted.
        guard newMode == .startOver else { return }
        resumeManager?.clearResumeEntry()
        startPlaybackFromBeginning()
    }

    private func handleAudioTimeChange(_ newValue: Double) {
        updateNowPlayingPlayback(time: newValue)
    }

    private func handleAudioStateChange() {
        updateNowPlayingPlayback(time: viewModel.audioCoordinator.currentTime)
    }

    private func handleLibraryDisappear() {
        persistResumeOnExit()
        // Do not reset audio here; iPad split-view can emit incidental disappear events.
        if scenePhase == .active {
            nowPlaying.clear()
        }
    }

    private func handleScenePhaseChange(_ newPhase: ScenePhase) {
        guard newPhase != .active else { return }
        persistResumeOnExit()
    }

    // Computed properties for resume manager values
    var videoAutoPlay: Bool { resumeManager?.videoAutoPlay ?? false }
    var videoResumeTime: Double? { resumeManager?.videoResumeTime }
    var videoResumeActionID: UUID { resumeManager?.videoResumeActionID ?? UUID() }
    var resumeUserId: String? { appState.resumeUserKey }

    private var navigationTitleText: String {
        shouldHideNavigationTitle ? "" : item.bookTitle
    }

    private var shouldHideNavigationTitle: Bool {
        viewModel.jobContext != nil && !isVideoPreferred
    }

    private var shouldUseInteractiveBackground: Bool {
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

    private var standardBodyPadding: EdgeInsets {
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
    var canDragVideoPreview: Bool {
        #if os(iOS)
        return UIDevice.current.userInterfaceIdiom == .phone && verticalSizeClass == .regular
        #else
        return false
        #endif
    }

    /// Extra top padding for video preview on iPhone portrait mode
    var videoTopPadding: CGFloat {
        #if os(iOS)
        guard canDragVideoPreview else { return 0 }
        return CGFloat(videoVerticalOffset) + dragOffset
        #else
        return 0
        #endif
    }

    @ViewBuilder
    private var bodyContent: some View {
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
    private var standardBody: some View {
        let base = VStack(alignment: .leading, spacing: rootSpacing) {
            if isVideoPreferred {
                header
            }

            switch viewModel.loadState {
            case .idle, .loading:
                loadingView
            case let .error(message):
                errorView(message: message)
            case .loaded:
                if isVideoPreferred, let videoURL {
                    #if os(tvOS)
                    libraryVideoPlayer(videoURL: videoURL)
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
                        showsScrubber: showsScrubber,
                        linguistInputLanguage: linguistInputLanguage,
                        linguistLookupLanguage: linguistLookupLanguage,
                        headerInfo: interactiveHeaderInfo,
                        bookmarkUserId: resumeUserId,
                        bookmarkJobId: item.jobId,
                        bookmarkItemType: bookmarkItemType
                    )
                } else {
                    LibraryPlaybackUnavailableView(usesDarkBackground: usesDarkBackground)
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

    @ViewBuilder
    private var header: some View {
        LibraryPlaybackHeader(
            item: item,
            coverURL: coverURL,
            itemTypeLabel: itemTypeLabel,
            showImageReel: showImageReel,
            imageReelURLs: imageReelURLs,
            coverWidth: coverWidth,
            coverHeight: coverHeight,
            titleFont: titleFont,
            authorFont: authorFont,
            metaFont: metaFont,
            titleLineLimit: titleLineLimit,
            headerSpacing: headerSpacing,
            headerTextSpacing: headerTextSpacing
        )
    }

    var loadingView: some View {
        LibraryPlaybackLoadingView(usesDarkBackground: usesDarkBackground)
    }

    func errorView(message: String) -> some View {
        LibraryPlaybackErrorView(message: message, usesDarkBackground: usesDarkBackground)
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

    @MainActor
    private func loadEntry() async {
        guard let configuration = appState.configuration else { return }

        // Initialize resume manager
        let manager = PlaybackResumeManager(
            jobId: item.jobId,
            itemType: item.itemType,
            userId: appState.resumeUserKey,
            userAliases: appState.resumeUserAliases
        )
        resumeManager = manager
        manager.resetState()

        let shouldAutoPlay = autoPlayOnLoad
        autoPlayOnLoad = false
        sentenceIndexTracker.value = nil
        #if !os(tvOS)
        showVideoPlayer = false
        #endif

        let offlinePayload = await offlineStore.cachedPayload(for: item.jobId, kind: .library)
        if let offlinePayload,
           let localResolver = offlineStore.localResolver(for: .library, configuration: configuration) {
            let offlineConfig = APIClientConfiguration(
                apiBaseURL: configuration.apiBaseURL,
                storageBaseURL: offlinePayload.storageBaseURL,
                authToken: configuration.authToken,
                userID: configuration.userID,
                userRole: configuration.userRole
            )
            await viewModel.loadJob(
                jobId: item.jobId,
                configuration: offlineConfig,
                origin: .library,
                preferLiveMedia: false,
                mediaOverride: offlinePayload.media,
                timingOverride: offlinePayload.timing,
                resolverOverride: localResolver
            )
            applyOfflineReadingBeds(offlinePayload)
            // Set offline lookup cache for local word lookups
            viewModel.offlineLookupCache = offlinePayload.lookupCache
        } else {
            await viewModel.loadJob(jobId: item.jobId, configuration: configuration, origin: .library)
        }
        await viewModel.updateChapterIndex(from: item.metadata)
        if isVideoPreferred {
            nowPlaying.clear()
        } else {
            configureNowPlaying()
            updateNowPlayingMetadata(sentenceIndex: sentenceIndexTracker.value)
            updateNowPlayingPlayback(time: viewModel.audioCoordinator.currentTime)
        }
        await manager.syncNow()
        manager.markResumeDecisionComplete()

        // Handle playback based on mode from context menu selection
        switch playbackMode {
        case .resume:
            // Auto-resume from last position if available
            if let resumeEntry = manager.resolveResumeEntry(isVideoPreferred: isVideoPreferred) {
                applyResume(resumeEntry)
                return
            }
            // No resume position, start from beginning
            if shouldAutoPlay {
                startPlaybackFromBeginning()
            }
        case .startOver:
            // Clear resume position and start from beginning
            manager.clearResumeEntry()
            if shouldAutoPlay {
                startPlaybackFromBeginning()
            }
        }
    }

    @MainActor
    private func applyOfflineReadingBeds(_ payload: OfflineMediaStore.OfflineMediaPayload) {
        viewModel.readingBedCatalog = payload.readingBeds
        viewModel.readingBedBaseURL = payload.readingBedBaseURL
        viewModel.selectReadingBed(id: viewModel.selectedReadingBedID)
    }

    private func configureNowPlaying() {
        nowPlaying.configureRemoteCommands(
            onPlay: { viewModel.audioCoordinator.play() },
            onPause: { viewModel.audioCoordinator.pause() },
            onNext: { viewModel.skipSentence(forward: true) },
            onPrevious: { viewModel.skipSentence(forward: false) },
            onSeek: { viewModel.audioCoordinator.seek(to: $0) },
            onToggle: { viewModel.audioCoordinator.togglePlayback() },
            onSkipForward: { viewModel.skipSentence(forward: true) },
            onSkipBackward: { viewModel.skipSentence(forward: false) },
            onBookmark: { addNowPlayingBookmark() }
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
        if let resolvedIndex = resolveResumeSentenceIndex(at: highlightTime) {
            if sentenceIndexTracker.value != resolvedIndex {
                sentenceIndexTracker.value = resolvedIndex
                updateNowPlayingMetadata(sentenceIndex: resolvedIndex)
            }
            resumeManager?.recordInteractiveResume(sentenceIndex: resolvedIndex)
        }
        let playbackDuration = viewModel.selectedChunk.flatMap { viewModel.playbackDuration(for: $0) } ?? viewModel.audioCoordinator.duration
        let playbackTime = highlightTime.isFinite ? highlightTime : time
        nowPlaying.updatePlaybackState(
            isPlaying: viewModel.audioCoordinator.isPlaying,
            position: playbackTime,
            duration: playbackDuration
        )
    }

    private func addNowPlayingBookmark() {
        guard let chunk = viewModel.selectedChunk else { return }
        let jobId = item.jobId
        let userId = appState.resumeUserKey?.nonEmptyValue ?? "anonymous"
        let playbackTime = viewModel.playbackTime(for: chunk)
        let activeSentence = viewModel.activeSentence(at: viewModel.highlightingTime)
        let sentenceNumber = activeSentence?.displayIndex ?? activeSentence?.id
        let labelParts: [String] = {
            var parts: [String] = []
            if let sentenceNumber, sentenceNumber > 0 {
                parts.append("Sentence \(sentenceNumber)")
            }
            if playbackTime.isFinite {
                parts.append(formatBookmarkTime(playbackTime))
            }
            return parts
        }()
        let label = labelParts.isEmpty ? "Bookmark" : labelParts.joined(separator: " · ")
        let entry = PlaybackBookmarkEntry(
            id: UUID().uuidString,
            jobId: jobId,
            itemType: bookmarkItemType,
            kind: sentenceNumber != nil ? .sentence : .time,
            createdAt: Date().timeIntervalSince1970,
            label: label,
            playbackTime: playbackTime.isFinite ? playbackTime : nil,
            sentenceNumber: sentenceNumber,
            chunkId: chunk.id,
            segmentId: nil
        )
        guard let configuration = appState.configuration else {
            PlaybackBookmarkStore.shared.addBookmark(entry, userId: userId)
            return
        }
        Task {
            let client = APIClient(configuration: configuration)
            let payload = PlaybackBookmarkCreateRequest(
                id: entry.id,
                label: entry.label,
                kind: entry.kind,
                createdAt: entry.createdAt,
                position: entry.playbackTime,
                sentence: entry.sentenceNumber,
                mediaType: entry.kind == .sentence ? "text" : "audio",
                mediaId: nil,
                baseId: nil,
                segmentId: entry.segmentId,
                chunkId: entry.chunkId,
                itemType: entry.itemType
            )
            do {
                let response = try await client.createPlaybackBookmark(jobId: jobId, payload: payload)
                let stored = PlaybackBookmarkEntry(
                    id: response.id,
                    jobId: response.jobId,
                    itemType: response.itemType ?? entry.itemType,
                    kind: response.kind,
                    createdAt: response.createdAt,
                    label: response.label,
                    playbackTime: response.position,
                    sentenceNumber: response.sentence,
                    chunkId: response.chunkId,
                    segmentId: response.segmentId
                )
                PlaybackBookmarkStore.shared.addBookmark(stored, userId: userId)
            } catch {
                PlaybackBookmarkStore.shared.addBookmark(entry, userId: userId)
            }
        }
    }

    private func formatBookmarkTime(_ seconds: Double) -> String {
        let total = max(0, Int(seconds.rounded()))
        let hours = total / 3600
        let minutes = (total % 3600) / 60
        let remainingSeconds = total % 60
        if hours > 0 {
            return String(format: "%d:%02d:%02d", hours, minutes, remainingSeconds)
        }
        return String(format: "%02d:%02d", minutes, remainingSeconds)
    }

    // MARK: - Resume Actions

    private func startPlaybackFromBeginning() {
        if isVideoPreferred {
            // Always present the video player - no cover preview needed
            startVideoPlayback(at: 0, presentPlayer: true)
        } else if viewModel.jobContext != nil {
            startInteractivePlayback(at: 1)
        }
    }

    func applyResume(_ entry: PlaybackResumeEntry) {
        resumeManager?.applyResume(entry)
        if isVideoPreferred {
            startVideoPlayback(at: entry.playbackTime ?? 0, presentPlayer: true)
        } else {
            startInteractivePlayback(at: entry.sentenceNumber)
        }
    }

    private func startInteractivePlayback(at sentence: Int?) {
        if let sentence, sentence > 0 {
            // jumpToSentence with autoPlay: true handles seeking and starting playback
            // after the audio is loaded and seeked to the target position.
            // Do NOT call play() here as it would start playback from position 0
            // before the async seek operation completes.
            viewModel.jumpToSentence(sentence, autoPlay: true)
        } else {
            // No sentence target - start playback from current position
            if !viewModel.audioCoordinator.isPlaying {
                viewModel.audioCoordinator.play()
            }
        }
    }

    func startVideoPlayback(at time: Double?, presentPlayer: Bool) {
        resumeManager?.prepareVideoResume(at: time)
        #if !os(tvOS)
        if presentPlayer {
            showVideoPlayer = true
        }
        #endif
    }

    private func resolveResumeSentenceIndex(at highlightTime: Double) -> Int? {
        guard let chunk = viewModel.selectedChunk else { return nil }
        let duration = viewModel.playbackDuration(for: chunk) ?? viewModel.audioCoordinator.duration
        return PlaybackSentenceIndexHelpers.resolveResumeSentenceIndex(
            at: highlightTime,
            chunk: chunk,
            activeSentence: viewModel.activeSentence(at: highlightTime),
            playbackDuration: duration
        )
    }

    private func persistResumeOnExit() {
        resumeManager?.persistOnExit(isVideoPreferred: isVideoPreferred, sentenceIndex: sentenceIndexTracker.value)
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
