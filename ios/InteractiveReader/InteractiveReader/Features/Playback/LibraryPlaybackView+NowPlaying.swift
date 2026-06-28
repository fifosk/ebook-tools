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
        let resolvedAction = resolvedReaderTransportAction(forCommand: "play")
        guard shouldAcceptReaderTransportCommand("play", resolvedAction: resolvedAction) else {
            reinforceReaderTransportPauseIfNeeded(command: "play", resolvedAction: resolvedAction)
            return
        }
        performReaderNowPlayingTransport(action: resolvedAction)
    }

    func pauseReaderNowPlayingTransport() {
        let resolvedAction = resolvedReaderTransportAction(forCommand: "pause")
        guard shouldAcceptReaderTransportCommand("pause", resolvedAction: resolvedAction) else {
            reinforceReaderTransportPauseIfNeeded(command: "pause", resolvedAction: resolvedAction)
            return
        }
        performReaderNowPlayingTransport(action: resolvedAction)
    }

    func toggleReaderNowPlayingTransport(source: String = "toggle") {
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

    func shouldForceTVReaderNowPlayingPause() -> Bool {
        viewModel.audioCoordinator.isPlaybackRequested ||
            viewModel.audioCoordinator.isPlaying ||
            (
                musicOwnership.ownershipState == .appleMusicBed &&
                !musicOwnership.isPausedByReaderTransport &&
                !musicOwnership.isManuallyPaused
            )
    }

    func forcePauseReaderNowPlayingTransport(source: String) {
        lastReaderTransportCommandTime = ProcessInfo.processInfo.systemUptime
        lastReaderTransportAction = "pause"
        playbackLogger.info(
            "Library reader transport forced pause source=\(source, privacy: .public) requested=\(viewModel.audioCoordinator.isPlaybackRequested, privacy: .public) playing=\(viewModel.audioCoordinator.isPlaying, privacy: .public) musicPlaying=\(musicOwnership.isPlaying, privacy: .public) systemMusicPlaying=\(musicOwnership.isSystemPlaybackPlaying, privacy: .public)"
        )
        performReaderNowPlayingPauseTransport()
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

    private var readerTransportDuplicateWindow: TimeInterval {
        ReaderTransportCommandResolver.duplicateWindow
    }

    private func shouldAcceptReaderTransportCommand(_ command: String, resolvedAction: String) -> Bool {
        let now = ProcessInfo.processInfo.systemUptime
        if ReaderTransportCommandResolver.shouldHoldReaderResumeAfterPause {
            if resolvedAction == "play", now < localReaderTransportPauseHoldUntil {
                playbackLogger.info(
                    "Library reader transport \(command, privacy: .public) command ignored local-pause-guard action=\(resolvedAction, privacy: .public)"
                )
                return false
            }
            if resolvedAction == "play", musicOwnership.shouldRejectReaderTransportResumeAfterPause {
                playbackLogger.info(
                    "Library reader transport \(command, privacy: .public) command ignored pause-duplicate action=\(resolvedAction, privacy: .public)"
                )
                return false
            }
            if resolvedAction == "play", musicOwnership.isReaderTransportPauseHoldWindowActive {
                playbackLogger.info(
                    "Library reader transport \(command, privacy: .public) command ignored reader-pause-guard action=\(resolvedAction, privacy: .public)"
                )
                return false
            }
        }
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
        lastReaderTransportCommandTime = now
        lastReaderTransportAction = resolvedAction
        return true
    }

    private func reinforceReaderTransportPauseIfNeeded(command: String, resolvedAction: String) {
        guard ReaderTransportCommandResolver.shouldHoldReaderResumeAfterPause else { return }
        guard resolvedAction == "play" else { return }
        guard musicOwnership.ownershipState == .appleMusicBed else { return }
        let now = ProcessInfo.processInfo.systemUptime
        let shouldReinforcePause = now < localReaderTransportPauseHoldUntil ||
            musicOwnership.shouldRejectReaderTransportResumeAfterPause ||
            musicOwnership.isReaderTransportPauseGuardActive
        guard shouldReinforcePause else { return }
        playbackLogger.info(
            "Library reader transport \(command, privacy: .public) rejected play reinforced pause requested=\(viewModel.audioCoordinator.isPlaybackRequested, privacy: .public) playing=\(viewModel.audioCoordinator.isPlaying, privacy: .public) musicPlaying=\(musicOwnership.isPlaying, privacy: .public) systemMusicPlaying=\(musicOwnership.isSystemPlaybackPlaying, privacy: .public)"
        )
        pauseAppleMusicBedFromReaderTransportIfNeeded()
        viewModel.pauseForReaderTransport()
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
        playbackLogger.info(
            "Library reader transport play command requested=\(viewModel.audioCoordinator.isPlaybackRequested, privacy: .public) playing=\(viewModel.audioCoordinator.isPlaying, privacy: .public) musicPlaying=\(musicOwnership.isPlaying, privacy: .public)"
        )
        localReaderTransportPauseHoldUntil = 0
        viewModel.playForReaderTransport()
        recoverReaderTransportPlaybackIfNeeded()
        scheduleReaderTransportPlaybackRecovery()
        resumeAppleMusicBedFromReaderTransportIfNeeded()
        publishReaderNowPlayingSnapshot(force: true)
    }

    private func recoverReaderTransportPlaybackIfNeeded() {
        guard !isVideoPreferred else { return }
        guard !viewModel.audioCoordinator.isPlaying else { return }
        let trackedSentence = sentenceIndexTracker.value
        let currentSentence = (trackedSentence ?? 0) > 0 ? trackedSentence : nil
        keyboardShortcutDebugLog(
            "[KeyboardShortcut] Library reader transport recovery requested=\(viewModel.audioCoordinator.isPlaybackRequested) playing=\(viewModel.audioCoordinator.isPlaying) sentence=\(currentSentence ?? -1)"
        )
        if let currentSentence {
            startInteractivePlayback(at: currentSentence)
        } else {
            startPlaybackFromBeginning()
        }
    }

    private func scheduleReaderTransportPlaybackRecovery() {
        guard !isVideoPreferred else { return }
        Task { @MainActor in
            for delay in [180_000_000, 600_000_000, 1_200_000_000] as [UInt64] {
                try? await Task.sleep(nanoseconds: delay)
                guard !isVideoPreferred else { return }
                if viewModel.audioCoordinator.isPlaying {
                    return
                }
                recoverReaderTransportPlaybackIfNeeded()
            }
        }
    }

    private func performReaderNowPlayingPauseTransport() {
        #if DEBUG
        e2eReaderTransportCommandCount += 1
        #endif
        playbackLogger.info(
            "Library reader transport pause command requested=\(viewModel.audioCoordinator.isPlaybackRequested, privacy: .public) playing=\(viewModel.audioCoordinator.isPlaying, privacy: .public) musicPlaying=\(musicOwnership.isPlaying, privacy: .public)"
        )
        localReaderTransportPauseHoldUntil = ProcessInfo.processInfo.systemUptime + ReaderTransportCommandResolver.pauseHoldWindow
        pauseAppleMusicBedFromReaderTransportIfNeeded()
        viewModel.pauseForReaderTransport()
        publishReaderNowPlayingSnapshot(force: true)
    }

    private func resumeAppleMusicBedFromReaderTransportIfNeeded() {
        guard musicOwnership.ownershipState == .appleMusicBed else { return }
        musicOwnership.prepareForNarrationMix()
        musicOwnership.resumeReadingBedForReaderTransport()
        publishReaderNowPlayingSnapshot(force: true)
        scheduleAppleMusicBedNowPlayingReassertion()
    }

    private func pauseAppleMusicBedFromReaderTransportIfNeeded() {
        guard musicOwnership.ownershipState == .appleMusicBed else { return }
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
