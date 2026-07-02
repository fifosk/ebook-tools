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
            startInteractivePlayback(
                at: entry.sentenceNumber,
                playbackTime: entry.playbackTime,
                preferredTrack: entry.resumeSequenceTrack
            )
        }
    }

    func startInteractivePlayback(
        at sentence: Int?,
        playbackTime: Double? = nil,
        preferredTrack: SequenceTrack? = nil
    ) {
        let resolvedSentence = resolvedInteractiveStartSentence(sentence)
        viewModel.prepareResumeSingleTrack(preferredTrack)
        if let sentence = resolvedSentence, sentence > 0 {
            pendingInteractiveAutoplayID = UUID()
            pendingInteractiveAutoplaySentence = sentence
            if let resumeTime = validatedInteractiveResumePlaybackTime(playbackTime, sentenceNumber: sentence) {
                playbackTransportDebugLog(
                    "[PlaybackTransport] Library resume offset requested sentence=\(sentence) time=\(String(format: "%.3f", resumeTime.time)) sequence=\(viewModel.isSequenceModeActive)"
                )
                viewModel.jumpToTime(
                    resumeTime.time,
                    in: resumeTime.chunk,
                    autoPlay: true,
                    matchingSentenceNumber: sentence,
                    preferredTrack: preferredTrack
                )
            } else {
                if let playbackTime, playbackTime.isFinite {
                    playbackTransportDebugLog(
                        "[PlaybackTransport] Library resume offset fallback=sentenceStart sentence=\(sentence) time=\(String(format: "%.3f", playbackTime))"
                    )
                }
                viewModel.jumpToSentence(sentence, autoPlay: true)
            }
            resumeAppleMusicBedAfterInteractiveStartIfNeeded()
            scheduleInteractiveAutoplayRetry(
                sentence: sentence,
                requestID: pendingInteractiveAutoplayID,
                playbackTime: playbackTime,
                preferredTrack: preferredTrack
            )
        } else if !viewModel.audioCoordinator.isPlaying {
            pendingInteractiveAutoplaySentence = nil
            viewModel.audioCoordinator.play()
            resumeAppleMusicBedAfterInteractiveStartIfNeeded()
        }
    }

    func resumeAppleMusicBedAfterInteractiveStartIfNeeded() {
        guard musicOwnership.ownershipState == .appleMusicBed else { return }
        guard lastReaderTransportAction != "play" else { return }
        #if os(tvOS)
        #if DEBUG
        e2eTVInteractiveMusicDeferredResumeCount += 1
        #endif
        resumeAppleMusicBedFromReaderTransportIfNeeded(deferUntilReaderActive: true)
        #else
        musicOwnership.resumeReadingBedForReaderTransport()
        #endif
    }

    private func scheduleInteractiveAutoplayRetry(
        sentence: Int,
        requestID: UUID?,
        playbackTime: Double? = nil,
        preferredTrack: SequenceTrack? = nil
    ) {
        guard let requestID else { return }
        keyboardShortcutDebugLog("[KeyboardShortcut] Library autoplay requested sentence=\(sentence)")
        Task { @MainActor in
            for delay in InteractiveAutoplayRetrySchedule.nanosecondDelays {
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
                if let resumeTime = validatedInteractiveResumePlaybackTime(playbackTime, sentenceNumber: sentence) {
                    playbackTransportDebugLog(
                        "[PlaybackTransport] Library resume offset retry sentence=\(sentence) time=\(String(format: "%.3f", resumeTime.time)) sequence=\(viewModel.isSequenceModeActive)"
                    )
                    viewModel.jumpToTime(
                        resumeTime.time,
                        in: resumeTime.chunk,
                        autoPlay: true,
                        matchingSentenceNumber: sentence,
                        preferredTrack: preferredTrack
                    )
                } else {
                    viewModel.jumpToSentence(sentence, autoPlay: true)
                }
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

    func resolvedInteractiveStartSentence(_ sentence: Int?) -> Int? {
        guard let context = viewModel.jobContext else { return sentence }
        if let sentence, sentence > 0,
           viewModel.resolveChunk(containing: sentence, in: context) != nil {
            return sentence
        }
        return firstInteractiveSentenceNumber()
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
        resumeManager?.persistOnExit(
            isVideoPreferred: isVideoPreferred,
            sentenceIndex: sentenceIndexTracker.value,
            playbackTime: currentInteractiveResumePlaybackTime(),
            playbackTrack: currentInteractiveResumePlaybackTrack()
        )
    }

    func currentInteractiveResumePlaybackTime() -> Double? {
        let highlightTime = viewModel.highlightingTime
        let playerTime = viewModel.audioCoordinator.currentTime
        if !viewModel.isSequenceModeActive, playerTime.isFinite, playerTime >= 0 {
            if playerTime > 0 || !highlightTime.isFinite || highlightTime < 0 {
                return playerTime
            }
        }
        guard highlightTime.isFinite, highlightTime >= 0 else { return nil }
        return highlightTime
    }

    func currentInteractiveResumePlaybackTrack() -> String? {
        if viewModel.isSequenceModeActive {
            return nil
        }
        return viewModel.audioModeManager?.preferredTrack.rawValue
    }

    func validatedInteractiveResumePlaybackTime(
        _ playbackTime: Double?,
        sentenceNumber: Int
    ) -> (time: Double, chunk: InteractiveChunk)? {
        guard let time = playbackTime,
              time.isFinite,
              time >= 0,
              let context = viewModel.jobContext,
              let chunk = viewModel.resolveChunk(containing: sentenceNumber, in: context),
              viewModel.resumePlaybackTime(time, matches: sentenceNumber, in: chunk) else {
            return nil
        }
        return (time, chunk)
    }
}
