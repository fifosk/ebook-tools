import Foundation
import OSLog

extension JobPlaybackView {
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
            anchorSentenceNumber: sentenceIndex
        )
    }

    func playReaderNowPlayingTransport() {
        guard shouldAcceptReaderTransportCommand("play") else { return }
        performReaderNowPlayingPlayTransport()
    }

    func pauseReaderNowPlayingTransport() {
        guard shouldAcceptReaderTransportCommand("pause") else { return }
        performReaderNowPlayingPauseTransport()
    }

    func toggleReaderNowPlayingTransport() {
        guard shouldAcceptReaderTransportCommand("toggle") else { return }
        playbackLogger.info(
            "Job reader transport toggle command requested=\(viewModel.audioCoordinator.isPlaybackRequested, privacy: .public) playing=\(viewModel.audioCoordinator.isPlaying, privacy: .public) musicPlaying=\(musicOwnership.isPlaying, privacy: .public)"
        )
        if viewModel.audioCoordinator.isPlaybackRequested ||
            viewModel.audioCoordinator.isPlaying ||
            musicOwnership.isPlaying {
            performReaderNowPlayingPauseTransport()
        } else {
            performReaderNowPlayingPlayTransport()
        }
    }

    private func shouldAcceptReaderTransportCommand(_ command: String) -> Bool {
        let now = ProcessInfo.processInfo.systemUptime
        guard now - lastReaderTransportToggleTime >= 0.25 else {
            playbackLogger.info("Job reader transport \(command, privacy: .public) command ignored duplicate")
            return false
        }
        lastReaderTransportToggleTime = now
        return true
    }

    private func performReaderNowPlayingPlayTransport() {
        #if DEBUG
        e2eReaderTransportCommandCount += 1
        #endif
        playbackLogger.info(
            "Job reader transport play command requested=\(viewModel.audioCoordinator.isPlaybackRequested, privacy: .public) playing=\(viewModel.audioCoordinator.isPlaying, privacy: .public) musicPlaying=\(musicOwnership.isPlaying, privacy: .public)"
        )
        viewModel.audioCoordinator.play()
        resumeAppleMusicBedFromReaderTransportIfNeeded()
        publishReaderNowPlayingSnapshot(force: true)
    }

    private func performReaderNowPlayingPauseTransport() {
        #if DEBUG
        e2eReaderTransportCommandCount += 1
        #endif
        playbackLogger.info(
            "Job reader transport pause command requested=\(viewModel.audioCoordinator.isPlaybackRequested, privacy: .public) playing=\(viewModel.audioCoordinator.isPlaying, privacy: .public) musicPlaying=\(musicOwnership.isPlaying, privacy: .public)"
        )
        viewModel.audioCoordinator.pause()
        pauseAppleMusicBedFromReaderTransportIfNeeded()
        publishReaderNowPlayingSnapshot(force: true)
    }

    private func resumeAppleMusicBedFromReaderTransportIfNeeded() {
        guard musicOwnership.ownershipState == .appleMusicBed else { return }
        Task { @MainActor in
            await musicOwnership.ensureLastSelectionLoadedForReadingBed()
            musicOwnership.prepareForNarrationMix()
            musicOwnership.resumeReadingBedForReaderTransport()
            publishReaderNowPlayingSnapshot(force: true)
            scheduleAppleMusicBedNowPlayingReassertion()
        }
    }

    private func pauseAppleMusicBedFromReaderTransportIfNeeded() {
        guard musicOwnership.ownershipState == .appleMusicBed else { return }
        musicOwnership.pauseReadingBedForReaderTransport()
        nowPlayingReassertionTask?.cancel()
        nowPlayingReassertionTask = nil
        scheduleAppleMusicBedNowPlayingReassertion()
    }

    func updateNowPlayingPlayback(time: Double) {
        guard !isVideoPreferred else { return }
        guard !isAppleMusicOwningLockScreen else { return }
        nowPlaying.attachPlayer(viewModel.audioCoordinator.nowPlayingPlayer)
        let highlightTime = viewModel.highlightingTime
        if let resolvedIndex = resolveResumeSentenceIndex(at: highlightTime) {
            if sentenceIndex != resolvedIndex {
                sentenceIndex = resolvedIndex
                updateNowPlayingMetadata(sentenceIndex: resolvedIndex)
            }
            recordInteractiveResume(sentenceIndex: resolvedIndex)
        } else if let sentence = viewModel.activeSentence(at: highlightTime) {
            let index = sentence.displayIndex ?? sentence.id
            if sentenceIndex != index {
                sentenceIndex = index
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

    func publishReaderNowPlayingSnapshot(force: Bool = false) {
        guard !isVideoPreferred else { return }
        guard !isAppleMusicOwningLockScreen else { return }
        viewModel.audioCoordinator.reassertAudioSession()
        nowPlaying.attachPlayer(viewModel.audioCoordinator.nowPlayingPlayer)
        nowPlaying.setRemoteCommandsEnabled(true)
        configureNowPlaying()
        updateNowPlayingMetadata(sentenceIndex: sentenceIndex)
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

    func addNowPlayingBookmark() {
        guard let chunk = viewModel.selectedChunk else { return }
        let jobId = currentJob.jobId
        let userId = resumeUserId?.nonEmptyValue ?? "anonymous"
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
            itemType: resumeItemType,
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

    func formatBookmarkTime(_ seconds: Double) -> String {
        let total = max(0, Int(seconds.rounded()))
        let hours = total / 3600
        let minutes = (total % 3600) / 60
        let remainingSeconds = total % 60
        if hours > 0 {
            return String(format: "%d:%02d:%02d", hours, minutes, remainingSeconds)
        }
        return String(format: "%02d:%02d", minutes, remainingSeconds)
    }
}
