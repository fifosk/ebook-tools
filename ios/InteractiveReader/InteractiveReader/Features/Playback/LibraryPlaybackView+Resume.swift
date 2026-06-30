import Foundation

extension LibraryPlaybackView {
    func startPlaybackFromBeginning() {
        if isVideoPreferred {
            startVideoPlayback(at: 0, presentPlayer: true)
        } else if viewModel.jobContext != nil {
            startInteractivePlayback(at: firstInteractiveSentenceNumber())
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

    func startInteractivePlayback(at sentence: Int?) {
        if let sentence, sentence > 0 {
            pendingInteractiveAutoplayID = UUID()
            pendingInteractiveAutoplaySentence = sentence
            viewModel.jumpToSentence(sentence, autoPlay: true)
            resumeAppleMusicBedAfterInteractiveStartIfNeeded()
            scheduleInteractiveAutoplayRetry(sentence: sentence, requestID: pendingInteractiveAutoplayID)
        } else if !viewModel.audioCoordinator.isPlaying {
            pendingInteractiveAutoplaySentence = nil
            viewModel.audioCoordinator.play()
            resumeAppleMusicBedAfterInteractiveStartIfNeeded()
        }
    }

    private func resumeAppleMusicBedAfterInteractiveStartIfNeeded() {
        guard musicOwnership.ownershipState == .appleMusicBed else { return }
        guard lastReaderTransportAction != "play" else { return }
        musicOwnership.resumeReadingBedForReaderTransport()
    }

    private func scheduleInteractiveAutoplayRetry(sentence: Int, requestID: UUID?) {
        guard let requestID else { return }
        keyboardShortcutDebugLog("[KeyboardShortcut] Library autoplay requested sentence=\(sentence)")
        Task { @MainActor in
            for delay in [350_000_000, 900_000_000, 1_600_000_000] as [UInt64] {
                try? await Task.sleep(nanoseconds: delay)
                guard pendingInteractiveAutoplayID == requestID else { return }
                guard viewModel.jobContext != nil else { continue }
                if isInteractiveAutoplaySettled(for: sentence) {
                    #if DEBUG
                    e2eInteractiveAutoplaySettledCount += 1
                    #endif
                    pendingInteractiveAutoplayID = nil
                    pendingInteractiveAutoplaySentence = nil
                    return
                }
                keyboardShortcutDebugLog("[KeyboardShortcut] Library autoplay retry sentence=\(sentence)")
                viewModel.jumpToSentence(sentence, autoPlay: true)
            }
        }
    }

    func isInteractiveAutoplaySettled(for sentence: Int) -> Bool {
        guard viewModel.audioCoordinator.isPlaying else { return false }
        guard let chunk = viewModel.selectedChunk,
              let targetIndex = SentencePositionProvider.sentenceIndex(in: chunk, matching: sentence)
        else { return false }
        if let resolvedSentence = resolveResumeSentenceIndex(at: viewModel.highlightingTime) {
            return resolvedSentence == sentence
        }
        if viewModel.isSequenceModeActive,
           viewModel.sequenceController.currentSegment?.sentenceIndex == targetIndex {
            return true
        }
        return false
    }

    func firstInteractiveSentenceNumber() -> Int? {
        guard let context = viewModel.jobContext else { return nil }
        for chunk in context.chunks {
            if let sentence = chunk.sentences.first {
                return SentencePositionProvider.sentenceNumber(for: sentence)
            }
            if let start = chunk.startSentence, start > 0 {
                return start
            }
        }
        return nil
    }

    func startVideoPlayback(at time: Double?, presentPlayer: Bool) {
        resumeManager?.prepareVideoResume(at: time)
        #if !os(tvOS)
        if presentPlayer {
            showVideoPlayer = true
        }
        #endif
    }

    func resolveResumeSentenceIndex(at highlightTime: Double) -> Int? {
        guard let chunk = viewModel.selectedChunk else { return nil }
        let duration = viewModel.playbackDuration(for: chunk) ?? viewModel.audioCoordinator.duration
        return PlaybackSentenceIndexHelpers.resolveResumeSentenceIndex(
            at: highlightTime,
            chunk: chunk,
            activeSentence: viewModel.activeSentence(at: highlightTime),
            playbackDuration: duration
        )
    }

    func persistResumeOnExit() {
        resumeManager?.persistOnExit(isVideoPreferred: isVideoPreferred, sentenceIndex: sentenceIndexTracker.value)
    }
}
