import Foundation
import OSLog

extension LibraryPlaybackView {
    func configureNowPlaying() {
        nowPlaying.attachPlayer(viewModel.audioCoordinator.nowPlayingPlayer)
        nowPlaying.configureRemoteCommands(
            onPlay: { playReaderNowPlayingTransport() },
            onPause: { pauseReaderNowPlayingTransport() },
            onNext: { skipReaderSentence(forward: true) },
            onPrevious: { skipReaderSentence(forward: false) },
            onSeek: { viewModel.audioCoordinator.seek(to: $0) },
            onToggle: { toggleReaderNowPlayingTransport() },
            onSkipForward: { skipReaderSentence(forward: true) },
            onSkipBackward: { skipReaderSentence(forward: false) },
            onBookmark: { addNowPlayingBookmark() }
        )
    }

    func skipReaderSentence(forward: Bool) {
        viewModel.skipSentence(
            forward: forward,
            anchorSentenceNumber: sentenceIndexTracker.value
        )
    }

    func playReaderNowPlayingTransport() {
        lastReaderTransportSource = "playCommand"
        #if os(tvOS)
        guard !shouldRejectUnsolicitedReaderPlayCommand else {
            playbackLogger.info(
                "Library reader transport play command ignored unsolicited reader-pause echo requested=\(viewModel.audioCoordinator.isPlaybackRequested, privacy: .public) playing=\(viewModel.audioCoordinator.isPlaying, privacy: .public) musicPlaying=\(musicOwnership.isPlaying, privacy: .public)"
            )
            cancelReaderTransportPlaybackRecovery()
            viewModel.pauseForReaderTransport()
            publishReaderNowPlayingSnapshot(force: true)
            return
        }
        #endif
        let resolvedAction = resolvedReaderTransportAction(forCommand: "play")
        guard shouldAcceptReaderTransportCommand("play", resolvedAction: resolvedAction) else {
            reinforceReaderTransportPauseIfNeeded(command: "play", resolvedAction: resolvedAction)
            return
        }
        performReaderNowPlayingTransport(action: resolvedAction)
    }

    private var shouldRejectUnsolicitedReaderPlayCommand: Bool {
        ReaderTransportCommandResolver.shouldRejectUnsolicitedPlayCommand(
            ownershipState: musicOwnership.ownershipState,
            previousAction: lastReaderTransportAction,
            isEchoGuardActive: musicOwnership.isReaderTransportEchoGuardActive,
            shouldRejectResumeAfterPause: musicOwnership.shouldRejectReaderTransportResumeAfterPause,
            isPauseHoldWindowActive: musicOwnership.isReaderTransportPauseHoldWindowActive,
            now: ProcessInfo.processInfo.systemUptime,
            localPauseHoldUntil: localReaderTransportPauseHoldUntil
        )
    }

    func pauseReaderNowPlayingTransport() {
        lastReaderTransportSource = "pauseCommand"
        let resolvedAction = resolvedReaderTransportAction(forCommand: "pause")
        guard shouldAcceptReaderTransportCommand("pause", resolvedAction: resolvedAction) else {
            reinforceReaderTransportPauseIfNeeded(command: "pause", resolvedAction: resolvedAction)
            return
        }
        performReaderNowPlayingTransport(action: resolvedAction)
    }

    func toggleReaderNowPlayingTransport(source: String = "toggle") {
        lastReaderTransportSource = source
        let resolvedAction = resolvedReaderTransportAction(forCommand: "toggle")
        guard shouldAcceptReaderTransportCommand(source, resolvedAction: resolvedAction) else {
            reinforceReaderTransportPauseIfNeeded(command: source, resolvedAction: resolvedAction)
            return
        }
        playbackLogger.info(
            "Library reader transport toggle command requested=\(viewModel.audioCoordinator.isPlaybackRequested, privacy: .public) playing=\(viewModel.audioCoordinator.isPlaying, privacy: .public) musicPlaying=\(musicOwnership.isPlaying, privacy: .public)"
        )
        performReaderNowPlayingTransport(action: resolvedAction)
    }

    func toggleInteractiveReaderPlaybackTransport() {
        if shouldForceInteractiveReaderTransportResume {
            forcePlayReaderNowPlayingTransport(source: "interactiveOverride")
            return
        }
        if viewModel.audioCoordinator.isPlaybackRequested ||
            viewModel.audioCoordinator.isPlaying {
            forcePauseReaderNowPlayingTransport(source: "interactiveOverride")
            return
        }
        toggleReaderNowPlayingTransport()
    }

    private var shouldForceInteractiveReaderTransportResume: Bool {
        if musicOwnership.isPausedByReaderTransport || musicOwnership.isReaderTransportPauseGuardActive {
            return true
        }
        return musicOwnership.ownershipState == .appleMusicBed &&
            !musicOwnership.isPlaying
    }

    func shouldForceTVReaderNowPlayingPause() -> Bool {
        if shouldForceTVReaderNowPlayingResume() {
            return false
        }
        return ReaderTransportCommandResolver.shouldForceNowPlayingPause(
            ownershipState: musicOwnership.ownershipState,
            isReaderPlaybackRequested: viewModel.audioCoordinator.isPlaybackRequested,
            isReaderPlaying: viewModel.audioCoordinator.isPlaying,
            previousAction: lastReaderTransportAction,
            now: ProcessInfo.processInfo.systemUptime,
            localPauseHoldUntil: localReaderTransportPauseHoldUntil,
            shouldRejectResumeAfterPause: musicOwnership.shouldRejectReaderTransportResumeAfterPause,
            isPauseHoldWindowActive: musicOwnership.isReaderTransportPauseHoldWindowActive
        )
    }

    func shouldForceTVReaderNowPlayingResume(ignorePauseHold: Bool = false) -> Bool {
        ReaderTransportCommandResolver.shouldForceNowPlayingResume(
            ownershipState: musicOwnership.ownershipState,
            previousAction: lastReaderTransportAction,
            ignorePauseHold: ignorePauseHold,
            now: ProcessInfo.processInfo.systemUptime,
            localPauseHoldUntil: localReaderTransportPauseHoldUntil,
            isReaderPlaybackRequested: viewModel.audioCoordinator.isPlaybackRequested,
            isReaderPlaying: viewModel.audioCoordinator.isPlaying,
            isMusicPausedByReaderTransport: musicOwnership.isPausedByReaderTransport,
            isMusicPlaying: musicOwnership.isPlaying
        )
    }

    func forcePauseReaderNowPlayingTransport(source: String) {
        lastReaderTransportCommandTime = ProcessInfo.processInfo.systemUptime
        lastReaderTransportAction = "pause"
        lastReaderTransportSource = source
        playbackTransportDebugLog(
            "[PlaybackTransport] Library forced pause source=\(source) requested=\(viewModel.audioCoordinator.isPlaybackRequested) playing=\(viewModel.audioCoordinator.isPlaying) musicPlaying=\(musicOwnership.isPlaying) systemMusicPlaying=\(musicOwnership.isSystemPlaybackPlaying)"
        )
        playbackLogger.info(
            "Library reader transport forced pause source=\(source, privacy: .public) requested=\(viewModel.audioCoordinator.isPlaybackRequested, privacy: .public) playing=\(viewModel.audioCoordinator.isPlaying, privacy: .public) musicPlaying=\(musicOwnership.isPlaying, privacy: .public) systemMusicPlaying=\(musicOwnership.isSystemPlaybackPlaying, privacy: .public)"
        )
        performReaderNowPlayingPauseTransport()
    }

    func forcePlayReaderNowPlayingTransport(source: String) {
        lastReaderTransportCommandTime = ProcessInfo.processInfo.systemUptime
        lastReaderTransportAction = "play"
        lastReaderTransportSource = source
        playbackTransportDebugLog(
            "[PlaybackTransport] Library forced play source=\(source) requested=\(viewModel.audioCoordinator.isPlaybackRequested) playing=\(viewModel.audioCoordinator.isPlaying) musicPlaying=\(musicOwnership.isPlaying) systemMusicPlaying=\(musicOwnership.isSystemPlaybackPlaying)"
        )
        playbackLogger.info(
            "Library reader transport forced play source=\(source, privacy: .public) requested=\(viewModel.audioCoordinator.isPlaybackRequested, privacy: .public) playing=\(viewModel.audioCoordinator.isPlaying, privacy: .public) musicPlaying=\(musicOwnership.isPlaying, privacy: .public) systemMusicPlaying=\(musicOwnership.isSystemPlaybackPlaying, privacy: .public)"
        )
        performReaderNowPlayingPlayTransport()
    }

    private func resolvedReaderTransportAction(forCommand command: String) -> String {
        ReaderTransportCommandResolver.resolvedAction(
            for: command,
            ownershipState: musicOwnership.ownershipState,
            isReaderPlaybackRequested: viewModel.audioCoordinator.isPlaybackRequested,
            isReaderPlaying: viewModel.audioCoordinator.isPlaying,
            isMusicPlaying: musicOwnership.isPlaying,
            isMusicPausedByReaderTransport: musicOwnership.isPausedByReaderTransport
        )
    }

    func shouldIgnoreTVReaderTransportBrokerEcho() -> Bool {
        let elapsed = ProcessInfo.processInfo.systemUptime - lastReaderTransportCommandTime
        return ReaderTransportCommandResolver.shouldIgnoreBrokerEcho(
            canForceResume: shouldForceTVReaderNowPlayingResume(ignorePauseHold: true),
            elapsed: elapsed,
            previousAction: lastReaderTransportAction,
            previousSource: lastReaderTransportSource,
            shouldRejectResumeAfterPause: musicOwnership.shouldRejectReaderTransportResumeAfterPause,
            isPauseHoldWindowActive: musicOwnership.isReaderTransportPauseHoldWindowActive
        )
    }

    private func shouldAcceptReaderTransportCommand(_ command: String, resolvedAction: String) -> Bool {
        let now = ProcessInfo.processInfo.systemUptime
        let elapsed = now - lastReaderTransportCommandTime
        if ReaderTransportCommandResolver.shouldReapplyDuplicateCommand(
            elapsed: elapsed,
            resolvedAction: resolvedAction,
            previousAction: lastReaderTransportAction
        ) {
            playbackLogger.info(
                "Library reader transport \(command, privacy: .public) command reapplying duplicate action=\(resolvedAction, privacy: .public) elapsed=\(elapsed, privacy: .public)"
            )
            return true
        }
        #if os(tvOS)
        if ReaderTransportCommandResolver.shouldAcceptActiveReaderDuplicatePause(
            elapsed: elapsed,
            resolvedAction: resolvedAction,
            previousAction: lastReaderTransportAction,
            isReaderPlaybackRequested: viewModel.audioCoordinator.isPlaybackRequested,
            isReaderPlaying: viewModel.audioCoordinator.isPlaying
        ) {
            playbackLogger.info(
                "Library reader transport \(command, privacy: .public) command accepting duplicate pause for active reader elapsed=\(elapsed, privacy: .public)"
            )
            lastReaderTransportCommandTime = now
            lastReaderTransportAction = resolvedAction
            return true
        }
        #endif
        guard !ReaderTransportCommandResolver.shouldRejectDuplicateCommand(
            elapsed: elapsed,
            resolvedAction: resolvedAction,
            previousAction: lastReaderTransportAction
        ) else {
            playbackLogger.info(
                "Library reader transport \(command, privacy: .public) command ignored duplicate action=\(resolvedAction, privacy: .public) previous=\(lastReaderTransportAction, privacy: .public) elapsed=\(elapsed, privacy: .public)"
            )
            return false
        }
        if shouldBlockReaderTransportResumeAfterPause(resolvedAction: resolvedAction, elapsed: elapsed, now: now) {
            playbackLogger.info(
                "Library reader transport \(command, privacy: .public) command ignored reader-pause-guard action=\(resolvedAction, privacy: .public) previous=\(lastReaderTransportAction, privacy: .public) elapsed=\(elapsed, privacy: .public)"
            )
            return false
        }
        lastReaderTransportCommandTime = now
        lastReaderTransportAction = resolvedAction
        return true
    }

    private func shouldBlockReaderTransportResumeAfterPause(
        resolvedAction: String,
        elapsed: TimeInterval,
        now: TimeInterval
    ) -> Bool {
        ReaderTransportCommandResolver.shouldBlockResumeAfterPause(
            resolvedAction: resolvedAction,
            now: now,
            localPauseHoldUntil: localReaderTransportPauseHoldUntil,
            shouldRejectResumeAfterPause: musicOwnership.shouldRejectReaderTransportResumeAfterPause,
            isPauseHoldWindowActive: musicOwnership.isReaderTransportPauseHoldWindowActive
        )
    }

    private func reinforceReaderTransportPauseIfNeeded(command: String, resolvedAction: String) {
        let now = ProcessInfo.processInfo.systemUptime
        guard ReaderTransportCommandResolver.shouldReinforcePauseAfterRejectedPlay(
            ownershipState: musicOwnership.ownershipState,
            resolvedAction: resolvedAction,
            previousAction: lastReaderTransportAction,
            now: now,
            localPauseHoldUntil: localReaderTransportPauseHoldUntil,
            shouldRejectResumeAfterPause: musicOwnership.shouldRejectReaderTransportResumeAfterPause,
            isPauseHoldWindowActive: musicOwnership.isReaderTransportPauseHoldWindowActive,
            isPauseGuardActive: musicOwnership.isReaderTransportPauseGuardActive
        )
        else { return }
        playbackLogger.info(
            "Library reader transport \(command, privacy: .public) rejected play reinforced pause requested=\(viewModel.audioCoordinator.isPlaybackRequested, privacy: .public) playing=\(viewModel.audioCoordinator.isPlaying, privacy: .public) musicPlaying=\(musicOwnership.isPlaying, privacy: .public) systemMusicPlaying=\(musicOwnership.isSystemPlaybackPlaying, privacy: .public)"
        )
        invalidateReaderTransportResumeTasks()
        viewModel.pauseForReaderTransport()
        pauseAppleMusicBedFromReaderTransportIfNeeded()
        publishReaderNowPlayingSnapshot(force: true)
    }

    private func performReaderNowPlayingTransport(action: String) {
        if action == "pause" {
            performReaderNowPlayingPauseTransport()
        } else {
            performReaderNowPlayingPlayTransport()
        }
    }

    private func performReaderNowPlayingPlayTransport() {
        #if DEBUG
        e2eReaderTransportCommandCount += 1
        #endif
        readerTransportResumeGeneration &+= 1
        cancelReaderTransportPlaybackRecovery()
        localReaderTransportPauseHoldUntil = 0
        reassertReaderTransportAudioSessionForPlay()
        let shouldDeferMusicResume = shouldDeferAppleMusicBedResumeUntilReaderActive
        if shouldDeferMusicResume {
            musicOwnership.prepareDeferredReadingBedResumeForReaderTransport()
        }
        restoreReaderTransportNarrationPlaybackRequestIfNeeded()
        viewModel.playForReaderTransport()
        restoreReaderTransportNarrationPlaybackRequestIfNeeded()
        playbackTransportDebugLog(
            "[PlaybackTransport] Library play command accepted requested=\(viewModel.audioCoordinator.isPlaybackRequested) playing=\(viewModel.audioCoordinator.isPlaying) musicPlaying=\(musicOwnership.isPlaying) deferredMusic=\(shouldDeferMusicResume)"
        )
        playbackLogger.info(
            "Library reader transport play command requested=\(viewModel.audioCoordinator.isPlaybackRequested, privacy: .public) playing=\(viewModel.audioCoordinator.isPlaying, privacy: .public) musicPlaying=\(musicOwnership.isPlaying, privacy: .public) deferredMusic=\(shouldDeferMusicResume, privacy: .public)"
        )
        resumeAppleMusicBedFromReaderTransportIfNeeded(deferUntilReaderActive: shouldDeferMusicResume)
        scheduleReaderTransportPlaybackRecovery()
        publishReaderNowPlayingSnapshot(force: true)
    }

    private func restoreReaderTransportNarrationPlaybackRequestIfNeeded() {
        guard !isVideoPreferred else { return }
        guard !viewModel.audioCoordinator.isPlaybackRequested else { return }
        let trackedSentence = sentenceIndexTracker.value
        let targetSentence = (trackedSentence ?? 0) > 0 ? trackedSentence : firstInteractiveSentenceNumber()
        playbackTransportDebugLog(
            "[PlaybackTransport] Library restoring narration playback request source=\(lastReaderTransportSource) sentence=\(targetSentence ?? -1)"
        )
        playbackLogger.info(
            "Library reader transport restoring narration playback request source=\(lastReaderTransportSource, privacy: .public) sentence=\(targetSentence ?? -1, privacy: .public)"
        )
        startInteractivePlayback(
            at: targetSentence,
            playbackTime: currentInteractiveResumePlaybackTime()
        )
    }

    private var shouldDeferAppleMusicBedResumeUntilReaderActive: Bool {
        #if os(tvOS)
        return musicOwnership.ownershipState == .appleMusicBed &&
            (
                musicOwnership.isPausedByReaderTransport ||
                (
                    !musicOwnership.isPlaying &&
                    (
                        lastReaderTransportSource == "brokerResume" ||
                        lastReaderTransportSource == "interactiveOverride"
                    )
                )
            )
        #else
        return false
        #endif
    }

    private func reassertReaderTransportAudioSessionForPlay() {
        guard musicOwnership.ownershipState == .appleMusicBed else {
            viewModel.audioCoordinator.reassertAudioSession(force: true)
            return
        }
        viewModel.audioCoordinator.configureAudioSessionForMixing(
            true,
            duckOthers: musicVolume < 0.35
        )
    }

    private func recoverReaderTransportPlaybackIfNeeded() {
        guard !isVideoPreferred else { return }
        guard viewModel.audioCoordinator.isPlaybackRequested else { return }
        guard !viewModel.audioCoordinator.isPlaying else { return }
        let trackedSentence = sentenceIndexTracker.value
        let currentSentence = (trackedSentence ?? 0) > 0 ? trackedSentence : nil
        if canResumeReaderTransportInPlace {
            keyboardShortcutDebugLog(
                "[KeyboardShortcut] Library reader transport in-place recovery requested=\(viewModel.audioCoordinator.isPlaybackRequested) playing=\(viewModel.audioCoordinator.isPlaying) time=\(String(format: "%.3f", viewModel.audioCoordinator.currentTime))"
            )
            viewModel.playForReaderTransport()
            return
        }
        keyboardShortcutDebugLog(
            "[KeyboardShortcut] Library reader transport recovery requested=\(viewModel.audioCoordinator.isPlaybackRequested) playing=\(viewModel.audioCoordinator.isPlaying) sentence=\(currentSentence ?? -1)"
        )
        if let currentSentence {
            startInteractivePlayback(
                at: currentSentence,
                playbackTime: currentInteractiveResumePlaybackTime()
            )
        } else {
            startPlaybackFromBeginning()
        }
    }

    private var canResumeReaderTransportInPlace: Bool {
        viewModel.audioCoordinator.nowPlayingPlayer != nil &&
            (
                viewModel.audioCoordinator.activeURL != nil ||
                !viewModel.audioCoordinator.activeURLs.isEmpty
            )
    }

    private func scheduleReaderTransportPlaybackRecovery() {
        guard !isVideoPreferred else { return }
        cancelReaderTransportPlaybackRecovery()
        let scheduledAction = lastReaderTransportAction
        let scheduledGeneration = readerTransportResumeGeneration
        readerTransportPlaybackRecoveryTask = Task { @MainActor in
            defer { readerTransportPlaybackRecoveryTask = nil }
            for delay in [180_000_000, 600_000_000, 1_200_000_000] as [UInt64] {
                try? await Task.sleep(nanoseconds: delay)
                guard !Task.isCancelled else { return }
                guard !isVideoPreferred else { return }
                guard readerTransportResumeGeneration == scheduledGeneration else { return }
                guard lastReaderTransportAction == scheduledAction, scheduledAction == "play" else { return }
                if !viewModel.audioCoordinator.isPlaybackRequested {
                    restoreReaderTransportNarrationPlaybackRequestIfNeeded()
                }
                guard viewModel.audioCoordinator.isPlaybackRequested else { return }
                if viewModel.audioCoordinator.isPlaying {
                    return
                }
                recoverReaderTransportPlaybackIfNeeded()
            }
        }
    }

    func cancelReaderTransportPlaybackRecovery() {
        readerTransportPlaybackRecoveryTask?.cancel()
        readerTransportPlaybackRecoveryTask = nil
    }

    private func cancelReaderTransportMusicResume() {
        readerTransportMusicResumeTask?.cancel()
        readerTransportMusicResumeTask = nil
    }

    private func invalidateReaderTransportResumeTasks() {
        readerTransportResumeGeneration &+= 1
        cancelReaderTransportPlaybackRecovery()
        cancelReaderTransportMusicResume()
    }

    private func performReaderNowPlayingPauseTransport() {
        #if DEBUG
        e2eReaderTransportCommandCount += 1
        #endif
        playbackTransportDebugLog(
            "[PlaybackTransport] Library pause command accepted requested=\(viewModel.audioCoordinator.isPlaybackRequested) playing=\(viewModel.audioCoordinator.isPlaying) musicPlaying=\(musicOwnership.isPlaying)"
        )
        playbackLogger.info(
            "Library reader transport pause command requested=\(viewModel.audioCoordinator.isPlaybackRequested, privacy: .public) playing=\(viewModel.audioCoordinator.isPlaying, privacy: .public) musicPlaying=\(musicOwnership.isPlaying, privacy: .public)"
        )
        invalidateReaderTransportResumeTasks()
        localReaderTransportPauseHoldUntil = ProcessInfo.processInfo.systemUptime + ReaderTransportCommandResolver.pauseHoldWindow
        viewModel.pauseForReaderTransport()
        pauseAppleMusicBedFromReaderTransportIfNeeded()
        publishReaderNowPlayingSnapshot(force: true)
    }

    func resumeAppleMusicBedFromReaderTransportIfNeeded(deferUntilReaderActive: Bool = false) {
        guard musicOwnership.ownershipState == .appleMusicBed ||
            musicOwnership.ownershipState == .appleMusic
        else { return }
        musicOwnership.prepareForNarrationMix()
        guard deferUntilReaderActive else {
            cancelReaderTransportMusicResume()
            musicOwnership.resumeReadingBedForReaderTransport()
            publishReaderNowPlayingSnapshot(force: true)
            scheduleAppleMusicBedNowPlayingReassertion()
            return
        }
        scheduleAppleMusicBedResumeAfterReaderActive()
    }

    private func scheduleAppleMusicBedResumeAfterReaderActive() {
        cancelReaderTransportMusicResume()
        let scheduledAction = lastReaderTransportAction
        let scheduledGeneration = readerTransportResumeGeneration
        let scheduledBarrier = musicOwnership.readerTransportResumeBarrierValue
        readerTransportMusicResumeTask = Task { @MainActor in
            defer { readerTransportMusicResumeTask = nil }
            for delay in [120_000_000, 260_000_000, 520_000_000, 900_000_000, 1_500_000_000] as [UInt64] {
                try? await Task.sleep(nanoseconds: delay)
                guard !Task.isCancelled else { return }
                guard readerTransportResumeGeneration == scheduledGeneration else { return }
                guard lastReaderTransportAction == scheduledAction, scheduledAction == "play" else { return }
                guard musicOwnership.isReaderTransportResumeBarrierCurrent(scheduledBarrier) else { return }
                guard viewModel.audioCoordinator.isPlaybackRequested else {
                    playbackLogger.info(
                        "Library reader transport deferred Music resume waiting; narration request inactive"
                    )
                    restoreReaderTransportNarrationPlaybackRequestIfNeeded()
                    continue
                }
                if !viewModel.isNarrationAudibleForReaderTransport {
                    reassertReaderTransportAudioSessionForPlay()
                    viewModel.playForReaderTransport()
                    continue
                }
                musicOwnership.resumeReadingBedForReaderTransport()
                publishReaderNowPlayingSnapshot(force: true)
                scheduleAppleMusicBedNowPlayingReassertion()
                return
            }
            guard !Task.isCancelled else { return }
            guard readerTransportResumeGeneration == scheduledGeneration else { return }
            guard lastReaderTransportAction == scheduledAction, scheduledAction == "play" else { return }
            guard musicOwnership.isReaderTransportResumeBarrierCurrent(scheduledBarrier) else { return }
            guard viewModel.audioCoordinator.isPlaybackRequested else {
                playbackLogger.info(
                    "Library reader transport deferred Music resume held; narration request inactive"
                )
                restoreReaderTransportNarrationPlaybackRequestIfNeeded()
                return
            }
            guard viewModel.isNarrationAudibleForReaderTransport else {
                playbackLogger.info(
                    "Library reader transport deferred Music resume held; narration is not active requested=\(viewModel.audioCoordinator.isPlaybackRequested, privacy: .public)"
                )
                return
            }
            musicOwnership.resumeReadingBedForReaderTransport()
            publishReaderNowPlayingSnapshot(force: true)
            scheduleAppleMusicBedNowPlayingReassertion()
        }
    }

    private func pauseAppleMusicBedFromReaderTransportIfNeeded() {
        guard musicOwnership.ownershipState == .appleMusicBed else { return }
        cancelReaderTransportMusicResume()
        musicOwnership.pauseReadingBedForReaderTransport()
        nowPlayingReassertionTask?.cancel()
        nowPlayingReassertionTask = nil
        scheduleAppleMusicBedNowPlayingReassertion()
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

    func updateNowPlayingPlayback(time: Double) {
        guard !isVideoPreferred else { return }
        guard !isAppleMusicOwningLockScreen else { return }
        nowPlaying.attachPlayer(viewModel.audioCoordinator.nowPlayingPlayer)
        let highlightTime = viewModel.highlightingTime
        if let resolvedIndex = resolveResumeSentenceIndex(at: highlightTime) {
            if sentenceIndexTracker.value != resolvedIndex {
                sentenceIndexTracker.value = resolvedIndex
                updateNowPlayingMetadata(sentenceIndex: resolvedIndex)
            }
            resumeManager?.recordInteractiveResume(sentenceIndex: resolvedIndex, playbackTime: highlightTime)
        }
        let playbackDuration = viewModel.selectedChunk.flatMap { viewModel.playbackDuration(for: $0) } ?? viewModel.audioCoordinator.duration
        let playbackTime = highlightTime.isFinite ? highlightTime : time
        nowPlaying.updatePlaybackState(
            isPlaying: viewModel.audioCoordinator.isPlaying,
            position: playbackTime,
            duration: playbackDuration
        )
    }

    func publishReaderNowPlayingSnapshot(force: Bool = false) {
        guard !isVideoPreferred else { return }
        guard !isAppleMusicOwningLockScreen else { return }
        viewModel.audioCoordinator.reassertAudioSession()
        nowPlaying.attachPlayer(viewModel.audioCoordinator.nowPlayingPlayer)
        nowPlaying.setRemoteCommandsEnabled(true)
        configureNowPlaying()
        updateNowPlayingMetadata(sentenceIndex: sentenceIndexTracker.value)
        let highlightTime = viewModel.highlightingTime
        let playbackDuration = viewModel.selectedChunk.flatMap {
            viewModel.playbackDuration(for: $0)
        } ?? viewModel.audioCoordinator.duration
        let playbackTime = highlightTime.isFinite ? highlightTime : viewModel.audioCoordinator.currentTime
        nowPlaying.updatePlaybackState(
            isPlaying: viewModel.audioCoordinator.isPlaying,
            position: playbackTime,
            duration: playbackDuration,
            force: force
        )
        nowPlaying.reassertReaderSession()
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
