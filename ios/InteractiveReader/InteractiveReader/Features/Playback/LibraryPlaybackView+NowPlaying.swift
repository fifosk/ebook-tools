import Foundation

extension LibraryPlaybackView {
    func configureNowPlaying() {
        nowPlaying.attachPlayer(viewModel.audioCoordinator.nowPlayingPlayer)
        nowPlaying.configureRemoteCommands(
            onPlay: { playReaderNowPlayingTransport() },
            onPause: { pauseReaderNowPlayingTransport() },
            onNext: { viewModel.skipSentence(forward: true) },
            onPrevious: { viewModel.skipSentence(forward: false) },
            onSeek: { viewModel.audioCoordinator.seek(to: $0) },
            onToggle: { toggleReaderNowPlayingTransport() },
            onSkipForward: { viewModel.skipSentence(forward: true) },
            onSkipBackward: { viewModel.skipSentence(forward: false) },
            onBookmark: { addNowPlayingBookmark() }
        )
    }

    func playReaderNowPlayingTransport() {
        viewModel.audioCoordinator.play()
        resumeAppleMusicBedFromReaderTransportIfNeeded()
        publishReaderNowPlayingSnapshot(force: true)
    }

    func pauseReaderNowPlayingTransport() {
        viewModel.audioCoordinator.pause()
        pauseAppleMusicBedFromReaderTransportIfNeeded()
        publishReaderNowPlayingSnapshot(force: true)
    }

    func toggleReaderNowPlayingTransport() {
        if viewModel.audioCoordinator.isPlaybackRequested ||
            viewModel.audioCoordinator.isPlaying ||
            musicOwnership.isPlaying {
            pauseReaderNowPlayingTransport()
        } else {
            playReaderNowPlayingTransport()
        }
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
