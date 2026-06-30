import Foundation
import OSLog
import SwiftUI
#if os(iOS)
import UIKit
#endif

struct LibraryPlaybackView: View {
    let playbackLogger = Logger(subsystem: "InteractiveReader", category: "PlaybackTransport")

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
    @StateObject var musicOwnership = MusicKitCoordinator.shared
    @State var resumeManager: PlaybackResumeManager?
    @State var sentenceIndexTracker = SentenceIndexTracker()
    @State var pendingInteractiveAutoplayID: UUID?
    @State var pendingInteractiveAutoplaySentence: Int?
    @State var nowPlayingReassertionTask: Task<Void, Never>?
    @State var lastReaderTransportCommandTime: TimeInterval = 0
    @State var lastReaderTransportAction = "none"
    @State var lastReaderTransportSource = "none"
    @State var localReaderTransportPauseHoldUntil: TimeInterval = 0
    @State var readerTransportPlaybackRecoveryTask: Task<Void, Never>?
    @State var readerTransportMusicResumeTask: Task<Void, Never>?
    @State var readerTransportResumeGeneration = 0
    #if DEBUG
    @State var e2eReaderTransportCommandCount = 0
    @State var e2eTVPlayPauseCommandCount = 0
    @State var e2eInteractiveAutoplaySettledCount = 0
    #endif
    @AppStorage(MusicPreferences.musicVolumeKey) var musicVolume: Double = MusicPreferences.defaultMusicVolume
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
        .background(alignment: .topLeading) {
            Text("libraryPlaybackView")
                .font(.system(size: 1))
                .foregroundStyle(.clear)
                .frame(width: 1, height: 1)
                .accessibilityIdentifier("libraryPlaybackView")
        }
        .navigationTitle(navigationTitleText)
        #if os(tvOS)
        .onPlayPauseCommand {
            handleTVPlayPauseCommand()
        }
        .onReceive(NotificationCenter.default.publisher(for: .keyboardShortcutPlayPause)) { _ in
            handleTVBrokerPlayPauseCommand()
        }
        #endif
        #if os(iOS)
        .toolbarBackground(shouldUseInteractiveBackground ? Color.black : (usesDarkBackground ? AppTheme.lightBackground : Color.clear), for: .navigationBar)
        .toolbarBackground(.visible, for: .navigationBar)
        .toolbarColorScheme(.dark, for: .navigationBar)
        #endif
        .task(id: item.jobId) {
            @MainActor in
            await handleLibraryLoadTask()
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
        .onReceive(musicOwnership.$readerTransportPauseAdoptionRevision) { _ in
            handleMusicKitReaderTransportPauseAdoption()
        }
        .onReceive(Timer.publish(every: 0.5, on: .main, in: .common).autoconnect()) { _ in
            handleMusicKitReadingBedWatchdogTick()
        }
        #if os(tvOS)
        .onAppear(perform: registerReaderTransportPauseAdoptionHandler)
        .onAppear(perform: refreshTVPlayerShortcutBroker)
        .onChange(of: isVideoPreferred) { _, _ in refreshTVPlayerShortcutBroker() }
        #endif
        .onDisappear(perform: handleLibraryDisappear)
        .onChange(of: scenePhase) { _, newPhase in handleScenePhaseChange(newPhase) }
    }

    #if os(tvOS)
    private func handleTVPlayPauseCommand() {
        guard !isVideoPreferred else {
            playbackLogger.info("Library foreground tvOS Play/Pause ignored videoPreferred=true")
            return
        }
        guard !TVPlayPauseCommandGate.shouldSuppressCurrentPress() else {
            playbackLogger.info("Library foreground tvOS Play/Pause ignored duplicate physical press")
            return
        }
        #if DEBUG
        e2eTVPlayPauseCommandCount += 1
        #endif
        playbackTransportDebugLog("[PlaybackTransport] Library foreground tvOS Play/Pause command")
        playbackLogger.info("Library foreground tvOS Play/Pause command")
        guard !shouldIgnoreTVReaderTransportBrokerEcho() else {
            playbackTransportDebugLog("[PlaybackTransport] Library foreground tvOS Play/Pause ignored reader transport pause echo")
            playbackLogger.info("Library foreground tvOS Play/Pause ignored reader transport pause echo")
            return
        }
        if shouldForceTVReaderNowPlayingResumeAfterHardwareEchoWindow() {
            forcePlayReaderNowPlayingTransport(source: "foregroundHardwareResume")
            return
        }
        if shouldForceTVReaderNowPlayingPause() {
            forcePauseReaderNowPlayingTransport(source: "foregroundPause")
            return
        }
        toggleReaderNowPlayingTransport(source: "foregroundToggle")
    }

    private func handleTVBrokerPlayPauseCommand() {
        guard !isVideoPreferred else {
            playbackLogger.info("Library broker tvOS Play/Pause ignored videoPreferred=true")
            return
        }
        guard !TVPlayPauseCommandGate.shouldSuppressCurrentPress() else {
            playbackLogger.info("Library broker tvOS Play/Pause ignored duplicate physical press")
            return
        }
        #if DEBUG
        e2eTVPlayPauseCommandCount += 1
        #endif
        playbackTransportDebugLog("[PlaybackTransport] Library broker tvOS Play/Pause command")
        playbackLogger.info("Library broker tvOS Play/Pause command")
        guard !shouldIgnoreTVReaderTransportBrokerEcho() else {
            playbackTransportDebugLog("[PlaybackTransport] Library broker tvOS Play/Pause ignored reader transport pause echo")
            playbackLogger.info("Library broker tvOS Play/Pause ignored reader transport pause echo")
            return
        }
        if shouldForceTVReaderNowPlayingResumeAfterHardwareEchoWindow() {
            forcePlayReaderNowPlayingTransport(source: "brokerHardwareResume")
            return
        }
        if shouldForceTVReaderNowPlayingResume(ignorePauseHold: true) {
            forcePlayReaderNowPlayingTransport(source: "brokerResume")
            return
        }
        if shouldForceTVReaderNowPlayingPause() {
            forcePauseReaderNowPlayingTransport(source: "brokerPause")
            return
        }
        toggleReaderNowPlayingTransport(source: "brokerToggle")
    }
    #endif

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

    private func handleAutoPlayIntentChange(_ shouldAutoPlay: Bool) {
        guard shouldAutoPlay, viewModel.loadState == .loaded else { return }
        autoPlayOnLoad = false
        applyPlaybackStartIntent()
    }

    private func applyPlaybackStartIntent() {
        switch playbackMode {
        case .resume:
            if let resumeEntry = resumeManager?.resolveResumeEntry(isVideoPreferred: isVideoPreferred) {
                applyResume(resumeEntry)
            } else {
                startPlaybackFromBeginning()
            }
        case .resumeExisting:
            if let resumeEntry = resumeManager?.resolveResumeEntry(isVideoPreferred: isVideoPreferred) {
                applyResume(resumeEntry)
            }
        case .startOver:
            resumeManager?.clearResumeEntry()
            startPlaybackFromBeginning()
        }
    }

    private func handleAudioTimeChange(_ newValue: Double) {
        updateNowPlayingPlayback(time: newValue)
    }

    private func handleAudioStateChange() {
        if let pendingSentence = pendingInteractiveAutoplaySentence,
           isInteractiveAutoplaySettled(for: pendingSentence) {
            #if DEBUG
            e2eInteractiveAutoplaySettledCount += 1
            #endif
            pendingInteractiveAutoplayID = nil
            pendingInteractiveAutoplaySentence = nil
        } else if pendingInteractiveAutoplaySentence == nil, viewModel.audioCoordinator.isPlaying {
            pendingInteractiveAutoplayID = nil
        }
        updateNowPlayingPlayback(time: viewModel.audioCoordinator.currentTime)
        guard musicOwnership.ownershipState == .appleMusicBed else { return }
        musicOwnership.updateReaderNarrationActivityForMusicBed(
            isActive: viewModel.audioCoordinator.isPlaybackRequested || viewModel.audioCoordinator.isPlaying,
            reason: "libraryAudioState"
        )
        publishReaderNowPlayingSnapshot(force: true)
        scheduleAppleMusicBedNowPlayingReassertion()
    }

    private func handleAudioOwnershipChange(_ state: AudioOwnership) {
        switch state {
        case .narration:
            nowPlayingReassertionTask?.cancel()
            nowPlayingReassertionTask = nil
            viewModel.audioCoordinator.configureAudioSessionForMixing(false)
            publishReaderNowPlayingSnapshot(force: true)
        case .appleMusicBed:
            configureAppleMusicBedAudioSession()
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

    private var appleMusicDuckingMixThreshold: Double { 0.35 }

    private func configureAppleMusicBedAudioSession() {
        viewModel.audioCoordinator.configureAudioSessionForMixing(
            true,
            duckOthers: musicVolume < appleMusicDuckingMixThreshold
        )
    }

    private func handleMusicKitPlaybackSurfaceChange() {
        guard musicOwnership.ownershipState == .appleMusicBed else { return }
        if shouldMirrorAppleMusicPlayToNarration {
            playbackLogger.info(
                "Library playback mirroring Apple Music play to narration requested=\(viewModel.audioCoordinator.isPlaybackRequested, privacy: .public) playing=\(viewModel.audioCoordinator.isPlaying, privacy: .public) musicPlaying=\(musicOwnership.isPlaying, privacy: .public) manual=\(musicOwnership.isManuallyPaused, privacy: .public) readerPause=\(musicOwnership.isPausedByReaderTransport, privacy: .public)"
            )
            viewModel.audioCoordinator.play()
            publishReaderNowPlayingSnapshot(force: true)
            scheduleAppleMusicBedNowPlayingReassertion()
            return
        }
        if shouldMirrorAppleMusicPauseToNarration {
            playbackLogger.info(
                "Library playback mirroring Apple Music pause to narration requested=\(viewModel.audioCoordinator.isPlaybackRequested, privacy: .public) playing=\(viewModel.audioCoordinator.isPlaying, privacy: .public) musicPlaying=\(musicOwnership.isPlaying, privacy: .public) manual=\(musicOwnership.isManuallyPaused, privacy: .public) readerPause=\(musicOwnership.isPausedByReaderTransport, privacy: .public)"
            )
            mirrorAppleMusicPauseToReaderTransport(source: "musicSurface")
            return
        }
        publishReaderNowPlayingSnapshot(force: true)
        scheduleAppleMusicBedNowPlayingReassertion()
    }

    private func handleMusicKitReaderTransportPauseAdoption() {
        guard musicOwnership.ownershipState == .appleMusicBed else { return }
        guard musicOwnership.isPausedByReaderTransport else { return }
        #if os(tvOS)
        if shouldIgnoreStaleAppleMusicPauseAfterReaderPlay {
            playbackTransportDebugLog(
                "[PlaybackTransport] Library ignored stale adopted Apple Music pause after reader play source=\(lastReaderTransportSource)"
            )
            playbackLogger.info(
                "Library playback ignored stale adopted Apple Music pause after reader play source=\(lastReaderTransportSource, privacy: .public)"
            )
            resumeAppleMusicBedFromReaderTransportIfNeeded(deferUntilReaderActive: true)
            return
        }
        #endif
        guard viewModel.audioCoordinator.isPlaybackRequested || viewModel.audioCoordinator.isPlaying else {
            publishReaderNowPlayingSnapshot(force: true)
            scheduleAppleMusicBedNowPlayingReassertion()
            return
        }
        playbackTransportDebugLog(
            "[PlaybackTransport] Library mirroring adopted Apple Music pause requested=\(viewModel.audioCoordinator.isPlaybackRequested) playing=\(viewModel.audioCoordinator.isPlaying) musicPlaying=\(musicOwnership.isPlaying)"
        )
        playbackLogger.info(
            "Library playback mirroring adopted Apple Music pause to narration requested=\(viewModel.audioCoordinator.isPlaybackRequested, privacy: .public) playing=\(viewModel.audioCoordinator.isPlaying, privacy: .public) musicPlaying=\(musicOwnership.isPlaying, privacy: .public)"
        )
        mirrorAppleMusicPauseToReaderTransport(source: "musicAdoption")
    }

    private func handleMusicKitReadingBedWatchdogTick() {
        guard musicOwnership.ownershipState == .appleMusicBed else { return }
        musicOwnership.refreshMusicPlaybackSurfaceSuppression(reason: "libraryWatchdog")
        musicOwnership.updateReaderNarrationActivityForMusicBed(
            isActive: viewModel.audioCoordinator.isPlaybackRequested || viewModel.audioCoordinator.isPlaying,
            reason: "libraryWatchdog"
        )
        guard viewModel.audioCoordinator.isPlaybackRequested || viewModel.audioCoordinator.isPlaying else { return }
        if shouldMirrorAppleMusicPauseToNarration {
            playbackLogger.info(
                "Library playback watchdog pausing narration requested=\(viewModel.audioCoordinator.isPlaybackRequested, privacy: .public) playing=\(viewModel.audioCoordinator.isPlaying, privacy: .public) musicPlaying=\(musicOwnership.isPlaying, privacy: .public) manual=\(musicOwnership.isManuallyPaused, privacy: .public) readerPause=\(musicOwnership.isPausedByReaderTransport, privacy: .public)"
            )
            mirrorAppleMusicPauseToReaderTransport(source: "watchdog")
            return
        }
        guard !musicOwnership.isReaderTransportPauseGuardActive else { return }
        musicOwnership.reconcileReadingBedSystemPlayback()
        musicOwnership.recoverReadingBedForActiveNarration(reason: "libraryWatchdog")
    }

    private func mirrorAppleMusicPauseToReaderTransport(source: String) {
        readerTransportResumeGeneration &+= 1
        cancelReaderTransportPlaybackRecovery()
        readerTransportMusicResumeTask?.cancel()
        readerTransportMusicResumeTask = nil
        lastReaderTransportCommandTime = ProcessInfo.processInfo.systemUptime
        lastReaderTransportAction = "pause"
        lastReaderTransportSource = source
        localReaderTransportPauseHoldUntil = ProcessInfo.processInfo.systemUptime + ReaderTransportCommandResolver.pauseHoldWindow
        playbackTransportDebugLog(
            "[PlaybackTransport] Library accepted Apple Music pause as reader transport source=\(source) requested=\(viewModel.audioCoordinator.isPlaybackRequested) playing=\(viewModel.audioCoordinator.isPlaying) musicPlaying=\(musicOwnership.isPlaying) readerPause=\(musicOwnership.isPausedByReaderTransport)"
        )
        playbackLogger.info(
            "Library playback accepted Apple Music pause as reader transport source=\(source, privacy: .public)"
        )
        viewModel.pauseForReaderTransport()
        if !musicOwnership.isPausedByReaderTransport {
            musicOwnership.pauseReadingBedForReaderTransport()
        }
        publishReaderNowPlayingSnapshot(force: true)
        scheduleAppleMusicBedNowPlayingReassertion()
    }

    #if os(tvOS)
    private func registerReaderTransportPauseAdoptionHandler() {
        musicOwnership.setReaderTransportPauseAdoptionHandler(owner: viewModel) { _, _ in
            handleMusicKitReaderTransportPauseAdoption()
        }
    }
    #endif

    func scheduleAppleMusicBedNowPlayingReassertion() {
        guard shouldKeepReaderNowPlayingReassertionAlive else { return }
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
                musicOwnership.refreshMusicPlaybackSurfaceSuppression(reason: "libraryNowPlayingReassertion")
                publishReaderNowPlayingSnapshot(force: true)
            }
            while !Task.isCancelled {
                try? await Task.sleep(nanoseconds: 1_000_000_000)
                guard shouldKeepReaderNowPlayingReassertionAlive else { return }
                musicOwnership.refreshMusicPlaybackSurfaceSuppression(reason: "libraryNowPlayingReassertion")
                publishReaderNowPlayingSnapshot(force: true)
            }
        }
    }

    private var shouldKeepReaderNowPlayingReassertionAlive: Bool {
        musicOwnership.ownershipState == .appleMusicBed &&
            (
                musicOwnership.isReaderTransportPauseGuardActive ||
                musicOwnership.isPausedByReaderTransport ||
                (
                    !musicOwnership.isManuallyPaused &&
                    (viewModel.audioCoordinator.isPlaybackRequested ||
                     viewModel.audioCoordinator.isPlaying ||
                     musicOwnership.isPlaying)
                )
            )
    }

    private var shouldMirrorAppleMusicPauseToNarration: Bool {
        #if os(tvOS)
        if shouldIgnoreStaleAppleMusicPauseAfterReaderPlay {
            return false
        }
        #endif
        if musicOwnership.isPausedByReaderTransport {
            return viewModel.audioCoordinator.isPlaybackRequested ||
                viewModel.audioCoordinator.isPlaying
        }
        guard viewModel.audioCoordinator.isPlaybackRequested || viewModel.audioCoordinator.isPlaying else {
            return false
        }
        #if os(tvOS)
        return musicOwnership.isManuallyPaused && musicOwnership.ownershipState == .appleMusicBed
        #else
        return false
        #endif
    }

    private var shouldIgnoreStaleAppleMusicPauseAfterReaderPlay: Bool {
        if ReaderTransportCommandResolver.shouldIgnoreObservedPauseAfterReaderPlay(
            previousAction: lastReaderTransportAction,
            now: ProcessInfo.processInfo.systemUptime,
            lastCommandTime: lastReaderTransportCommandTime
        ) {
            return true
        }
        guard lastReaderTransportAction == "play" else { return false }
        return musicOwnership.isPausedByReaderTransport ||
            musicOwnership.isReaderTransportPauseGuardActive ||
            readerTransportMusicResumeTask != nil
    }

    private var shouldMirrorAppleMusicPlayToNarration: Bool {
        musicOwnership.isPlaying &&
            !musicOwnership.isManuallyPaused &&
            !musicOwnership.isPausedByReaderTransport &&
            !musicOwnership.isReaderTransportPauseGuardActive &&
            !viewModel.audioCoordinator.isPlaybackRequested &&
            !viewModel.audioCoordinator.isPlaying
    }

    #if os(tvOS)
    private func refreshTVPlayerShortcutBroker() {
        guard !isVideoPreferred else {
            PlayerKeyboardShortcutBroker.shared.clearActions(owner: viewModel)
            return
        }
        PlayerKeyboardShortcutBroker.shared.setActions(
            PlayerKeyboardShortcutActions(
                playPause: { handleTVBrokerPlayPauseCommand() },
                previous: { skipReaderSentence(forward: false) },
                next: { skipReaderSentence(forward: true) },
                previousSentence: { skipReaderSentence(forward: false) },
                nextSentence: { skipReaderSentence(forward: true) },
                lookup: {},
                showMenu: {},
                hideMenu: {}
            ),
            owner: viewModel
        )
    }
    #endif

    private func handleLibraryDisappear() {
        persistResumeOnExit()
        #if os(tvOS)
        PlayerKeyboardShortcutBroker.shared.clearActions(owner: viewModel)
        musicOwnership.clearReaderTransportPauseAdoptionHandler(owner: viewModel)
        #endif
        readerTransportPlaybackRecoveryTask?.cancel()
        readerTransportPlaybackRecoveryTask = nil
        readerTransportMusicResumeTask?.cancel()
        readerTransportMusicResumeTask = nil
        if shouldKeepReaderNowPlayingReassertionAlive {
            publishReaderNowPlayingSnapshot(force: true)
            scheduleAppleMusicBedNowPlayingReassertion()
        } else {
            nowPlayingReassertionTask?.cancel()
            nowPlayingReassertionTask = nil
        }
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
        readerTransportMusicResumeTask?.cancel()
        readerTransportMusicResumeTask = nil
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

    /// Whether Apple Music owns the lock screen.
    /// Apple Music used as the reading bed keeps reader-owned sentence controls.
    var isAppleMusicOwningLockScreen: Bool {
        musicOwnership.ownershipState == .appleMusic
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
                        bookmarkItemType: bookmarkItemType,
                        playbackToggleOverride: {
                            toggleInteractiveReaderPlaybackTransport()
                        }
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
        #if DEBUG
        .overlay(alignment: .bottomLeading) {
            MusicBedSyncE2EControls(
                musicOwnership: musicOwnership,
                audioCoordinator: viewModel.audioCoordinator,
                readerTransportCommandCount: e2eReaderTransportCommandCount,
                foregroundPlayPauseCount: e2eTVPlayPauseCommandCount,
                interactiveAutoplayPendingSentence: pendingInteractiveAutoplaySentence,
                interactiveAutoplaySettledCount: e2eInteractiveAutoplaySettledCount,
                lastReaderTransportAction: lastReaderTransportAction,
                lastReaderTransportSource: lastReaderTransportSource,
                hasReaderContext: viewModel.jobContext != nil,
                isVideoPreferred: isVideoPreferred,
                isNarrationAudibleForReaderTransport: viewModel.isNarrationAudibleForReaderTransport,
                isReaderSequenceTransitioning: viewModel.isSequenceTransitioning,
                onReaderPlayCommand: { playReaderNowPlayingTransport() },
                onReaderPauseCommand: { pauseReaderNowPlayingTransport() },
                onReaderToggleCommand: { toggleReaderNowPlayingTransport() }
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

}

final class SentenceIndexTracker {
    var value: Int?
}
