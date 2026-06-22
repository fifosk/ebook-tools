extension LibraryPlaybackView {
    func startPlaybackFromBeginning() {
        if isVideoPreferred {
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
            viewModel.jumpToSentence(sentence, autoPlay: true)
        } else if !viewModel.audioCoordinator.isPlaying {
            viewModel.audioCoordinator.play()
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
