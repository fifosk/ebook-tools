import Foundation
import SwiftUI
import Combine

extension InteractivePlayerViewModel {
    /// Check if chunk sentences have gate data needed for combined (sequence) mode
    private func sentencesHaveGateData(_ sentences: [InteractiveChunk.Sentence]) -> Bool {
        guard let first = sentences.first else { return false }
        // Gate data is required for sequence playback - check if any gate fields are populated
        return first.originalStartGate != nil || first.startGate != nil
    }

    /// Check if chunk sentences have tokens loaded (required for transcript display)
    private func sentencesHaveTokens(_ sentences: [InteractiveChunk.Sentence]) -> Bool {
        guard let first = sentences.first else { return false }
        // Tokens are required for proper transcript display with word highlighting
        return !first.originalTokens.isEmpty || !first.translationTokens.isEmpty
    }

    /// Check if the currently selected track requires gate data (combined mode)
    private func selectedTrackRequiresGates(for chunk: InteractiveChunk) -> Bool {
        guard let trackID = selectedAudioTrackID,
              let track = chunk.audioOptions.first(where: { $0.id == trackID }) else {
            return false
        }
        return track.kind == .combined
    }

    /// Select a chunk for playback
    /// - Parameters:
    ///   - id: The chunk ID to select
    ///   - autoPlay: Whether to start playback automatically
    ///   - targetSentenceIndex: Optional 0-based sentence index to start from. Use -1 to mean "last sentence".
    func selectChunk(id: String, autoPlay: Bool = false, targetSentenceIndex: Int? = nil) {
        guard selectedChunkID != id else { return }
        selectedChunkID = id
        lastPrefetchSentenceNumber = nil
        prefetchDirection = .none
        guard let chunk = selectedChunk else {
            audioCoordinator.reset()
            selectedTimingURL = nil
            return
        }
        if !(chunk.audioOptions.contains { $0.id == selectedAudioTrackID }) {
            let preferred = preferredAudioKind.flatMap { kind in
                chunk.audioOptions.first(where: { $0.kind == kind })
            }
            selectedAudioTrackID = preferred?.id ?? chunk.audioOptions.first?.id
        }
        // If chunk has sentences with complete data, prepare audio immediately
        // For combined mode, we need gate data - if missing, load metadata first
        // Also require tokens to be loaded for proper transcript display
        let hasGates = sentencesHaveGateData(chunk.sentences)
        let hasTokens = sentencesHaveTokens(chunk.sentences)
        let needsGates = selectedTrackRequiresGates(for: chunk)
        print("[ConfigureDefaults] chunk=\(chunk.id), sentences=\(chunk.sentences.count), hasGates=\(hasGates), hasTokens=\(hasTokens), needsGates=\(needsGates)")
        if !chunk.sentences.isEmpty && hasTokens && (!needsGates || hasGates) {
            isTranscriptLoading = false
            // Resolve -1 (meaning "last sentence") to actual index
            let effectiveTargetIndex: Int? = {
                guard let target = targetSentenceIndex else { return nil }
                if target < 0 {
                    return max(0, chunk.sentences.count - 1)
                }
                return target
            }()
            prepareAudio(for: chunk, autoPlay: autoPlay, targetSentenceIndex: effectiveTargetIndex)
            attemptPendingSentenceJump(in: chunk)
            return
        }
        // Mark transcript as loading while we fetch metadata
        isTranscriptLoading = true
        // Load metadata before starting playback to ensure transcript is ready
        Task { [weak self] in
            guard let self else { return }
            await self.loadChunkMetadataIfNeeded(for: chunk.id, force: true)
            // Prepare audio after metadata is loaded
            guard self.selectedChunkID == id else { return }
            // Get the UPDATED chunk after metadata loaded (may have new sentences)
            guard let updatedChunk = self.selectedChunk else { return }
            // Clear loading state now that we have the transcript
            self.isTranscriptLoading = false
            // Only start audio if transcript is now available
            // This ensures audio doesn't play while showing "Waiting for transcript"
            guard !updatedChunk.sentences.isEmpty else { return }
            // Resolve -1 to actual last index now that we know sentence count
            let effectiveTargetIndex: Int? = {
                guard let target = targetSentenceIndex else { return nil }
                if target < 0 {
                    return max(0, updatedChunk.sentences.count - 1)
                }
                return target
            }()
            self.prepareAudio(for: updatedChunk, autoPlay: autoPlay, targetSentenceIndex: effectiveTargetIndex)
            self.attemptPendingSentenceJump(in: updatedChunk)
        }
    }

    func selectAudioTrack(id: String) {
        guard selectedAudioTrackID != id else { return }
        selectedAudioTrackID = id
        guard let chunk = selectedChunk else { return }
        if let track = chunk.audioOptions.first(where: { $0.id == id }) {
            preferredAudioKind = track.kind
            // If switching to combined mode and sentences lack gate data, load metadata first
            if track.kind == .combined && !sentencesHaveGateData(chunk.sentences) {
                Task { [weak self] in
                    guard let self else { return }
                    await self.loadChunkMetadataIfNeeded(for: chunk.id, force: true)
                    guard self.selectedAudioTrackID == id else { return }
                    guard let updatedChunk = self.selectedChunk else { return }
                    self.prepareAudio(for: updatedChunk, autoPlay: self.audioCoordinator.isPlaybackRequested)
                }
                return
            }
        }
        prepareAudio(for: chunk, autoPlay: audioCoordinator.isPlaybackRequested)
    }

    var selectedChunk: InteractiveChunk? {
        guard let context = jobContext else { return nil }
        if let id = selectedChunkID, let chunk = context.chunk(withID: id) {
            return chunk
        }
        return context.chunks.first
    }

    var currentAudioOptions: [InteractiveChunk.AudioOption] {
        selectedChunk?.audioOptions ?? []
    }

    func chunkBinding() -> Binding<String> {
        Binding(
            get: {
                self.selectedChunkID ?? self.jobContext?.chunks.first?.id ?? ""
            },
            set: { newValue in
                self.selectChunk(id: newValue, autoPlay: self.audioCoordinator.isPlaybackRequested)
            }
        )
    }

    func audioTrackBinding(defaultID: String?) -> Binding<String> {
        Binding(
            get: {
                self.selectedAudioTrackID ?? defaultID ?? ""
            },
            set: { newValue in
                self.selectAudioTrack(id: newValue)
            }
        )
    }

    func configureDefaultSelections() {
        guard let context = jobContext else { return }
        lastPrefetchSentenceNumber = nil
        prefetchDirection = .none
        if let chunk = context.chunks.first(where: { !$0.audioOptions.isEmpty }) ?? context.chunks.first {
            selectedChunkID = chunk.id
            if let option = chunk.audioOptions.first {
                selectedAudioTrackID = option.id
                preferredAudioKind = option.kind
            } else {
                selectedAudioTrackID = nil
            }
            // If chunk has sentences with complete data, prepare audio immediately
            // For combined mode (default), we need gate data - if missing, load metadata first
            // Also require tokens to be loaded for proper transcript display
            let hasGates = sentencesHaveGateData(chunk.sentences)
            let hasTokens = sentencesHaveTokens(chunk.sentences)
            let needsGates = selectedTrackRequiresGates(for: chunk)
            print("[ConfigureDefaults] chunk=\(chunk.id), sentences=\(chunk.sentences.count), hasGates=\(hasGates), hasTokens=\(hasTokens), needsGates=\(needsGates)")
            if !chunk.sentences.isEmpty && hasTokens && (!needsGates || hasGates) {
                isTranscriptLoading = false
                prepareAudio(for: chunk, autoPlay: false)
                return
            }
            // Mark transcript as loading while we fetch metadata
            isTranscriptLoading = true
            print("[ConfigureDefaults] Loading metadata for chunk \(chunk.id)")
            // Load metadata before preparing audio to ensure transcript is ready
            let chunkId = chunk.id
            Task { [weak self] in
                guard let self else { return }
                await self.loadChunkMetadataIfNeeded(for: chunkId, force: true)
                guard self.selectedChunkID == chunkId else { return }
                // Get the UPDATED chunk after metadata loaded (may have new sentences)
                guard let updatedChunk = self.selectedChunk else {
                    print("[ConfigureDefaults] No updated chunk after metadata load")
                    return
                }
                print("[ConfigureDefaults] After metadata: sentences=\(updatedChunk.sentences.count)")
                // Clear loading state now that we have the transcript
                self.isTranscriptLoading = false
                // Only prepare audio if transcript is now available
                guard !updatedChunk.sentences.isEmpty else {
                    print("[ConfigureDefaults] Still no sentences after metadata load")
                    return
                }
                self.prepareAudio(for: updatedChunk, autoPlay: false)
            }
        } else {
            selectedChunkID = nil
            selectedAudioTrackID = nil
            audioCoordinator.reset()
            selectedTimingURL = nil
            preferredAudioKind = nil
            isTranscriptLoading = false
        }
    }

    func prepareAudio(for chunk: InteractiveChunk, autoPlay: Bool, targetSentenceIndex: Int? = nil) {
        print("[PrepareAudio] Called with targetSentenceIndex=\(targetSentenceIndex ?? -1), autoPlay=\(autoPlay)")

        guard let mgr = audioModeManager,
              let instruction = mgr.resolveAudioInstruction(for: chunk, selectedTrackID: selectedAudioTrackID) else {
            print("[PrepareAudio] Guard failed - no track found or no audioModeManager")
            audioCoordinator.reset()
            sequenceController.reset()
            selectedTimingURL = nil
            return
        }

        print("[PrepareAudio] instruction=\(instruction), mode=\(mgr.currentMode.description)")

        switch instruction {
        case .sequence:
            let effectiveTargetIndex: Int? = targetSentenceIndex ?? {
                guard let pending = pendingSentenceJump, pending.chunkID == chunk.id else { return nil }
                return chunk.sentences.firstIndex {
                    ($0.displayIndex ?? $0.id) == pending.sentenceNumber
                }
            }()
            print("[PrepareAudio] Taking SEQUENCE path, effectiveTargetIndex=\(effectiveTargetIndex ?? -1)")
            configureSequencePlayback(for: chunk, autoPlay: autoPlay, targetSentenceIndex: effectiveTargetIndex)

        case .singleOption(let option, _):
            // Check if already playing the same URLs (prevent unnecessary reload from SwiftUI re-renders)
            if audioCoordinator.activeURLs == option.streamURLs {
                handleSameURLPlayback(autoPlay: autoPlay, targetSentenceIndex: targetSentenceIndex, chunk: chunk)
                return
            }
            loadSingleTrack(
                urls: option.streamURLs,
                timingURL: option.timingURL ?? option.streamURLs.first,
                autoPlay: autoPlay,
                targetSentenceIndex: targetSentenceIndex,
                chunk: chunk
            )

        case .singleURL(let url, _):
            loadSingleTrack(
                urls: [url],
                timingURL: url,
                autoPlay: autoPlay,
                targetSentenceIndex: targetSentenceIndex,
                chunk: chunk
            )
        }
    }

    /// Handle the case where the same URLs are already loaded (prevent unnecessary reload).
    private func handleSameURLPlayback(autoPlay: Bool, targetSentenceIndex: Int?, chunk: InteractiveChunk) {
        if sequenceController.isEnabled {
            print("[PrepareAudio] Resetting sequence controller for same-URL single-track mode")
            sequenceController.reset()
        }
        if autoPlay && !audioCoordinator.isPlaying {
            audioCoordinator.play()
        }
        if let targetIndex = targetSentenceIndex,
           targetIndex >= 0,
           targetIndex < chunk.sentences.count,
           let startTime = startTimeForSentence(atIndex: targetIndex, in: chunk) {
            seekPlayback(to: startTime, in: chunk)
        }
    }

    /// Load a single track (non-sequence mode) with optional seek to target sentence.
    private func loadSingleTrack(
        urls: [URL],
        timingURL: URL?,
        autoPlay: Bool,
        targetSentenceIndex: Int?,
        chunk: InteractiveChunk
    ) {
        sequenceController.reset()
        let needsSeek = targetSentenceIndex != nil && targetSentenceIndex! >= 0 && targetSentenceIndex! < chunk.sentences.count
        audioCoordinator.load(urls: urls, autoPlay: needsSeek ? false : autoPlay)
        selectedTimingURL = timingURL
        if needsSeek, let targetIndex = targetSentenceIndex {
            seekToSentenceAfterLoad(targetIndex, in: chunk, autoPlay: autoPlay)
        }
    }

    func handlePlaybackEnded() {
        guard let chunk = selectedChunk,
              let nextChunk = jobContext?.nextChunk(after: chunk.id) else {
            return
        }
        selectChunk(id: nextChunk.id, autoPlay: true)
    }

    func jumpToSentence(_ sentenceNumber: Int, autoPlay: Bool = false) {
        guard let context = jobContext else { return }
        guard sentenceNumber > 0 else { return }
        guard let targetChunk = resolveChunk(containing: sentenceNumber, in: context) else { return }

        pendingSentenceJump = PendingSentenceJump(chunkID: targetChunk.id, sentenceNumber: sentenceNumber)

        // Check if we're jumping within the same chunk
        let isSameChunk = selectedChunkID == targetChunk.id

        if isSameChunk {
            // Same chunk - reconfigure audio to start at target sentence
            Task { [weak self] in
                guard let self else { return }
                await self.loadChunkMetadataIfNeeded(for: targetChunk.id, force: false)
                guard self.selectedChunkID == targetChunk.id else { return }
                guard let updatedChunk = self.selectedChunk else { return }
                // Find the 0-based index of the target sentence
                let targetIndex = updatedChunk.sentences.firstIndex {
                    ($0.displayIndex ?? $0.id) == sentenceNumber
                }
                self.prepareAudio(for: updatedChunk, autoPlay: autoPlay, targetSentenceIndex: targetIndex)
                // Clear pending jump since we're passing target index directly
                self.pendingSentenceJump = nil
            }
        } else {
            // Different chunk - selectChunk will handle loading and audio setup
            selectChunk(id: targetChunk.id, autoPlay: autoPlay)
        }
    }

    func resolveChunk(containing sentenceNumber: Int, in context: JobContext) -> InteractiveChunk? {
        if let match = context.chunks.first(where: { chunk in
            chunk.sentences.contains { sentence in
                let id = sentence.displayIndex ?? sentence.id
                return id == sentenceNumber
            }
        }) {
            return match
        }
        return context.chunks.first(where: { chunk in
            guard let start = chunk.startSentence, let end = chunk.endSentence else { return false }
            return sentenceNumber >= start && sentenceNumber <= end
        })
    }

    func attemptPendingSentenceJump(in chunk: InteractiveChunk) {
        guard let pending = pendingSentenceJump, pending.chunkID == chunk.id else { return }

        // In sequence mode, use the sequence controller for seeking
        if isSequenceModeActive {
            // Find the target sentence index
            guard let targetSentenceIndex = chunk.sentences.firstIndex(where: {
                ($0.displayIndex ?? $0.id) == pending.sentenceNumber
            }) else {
                print("[Sequence] Could not find sentence index for sentenceNumber \(pending.sentenceNumber)")
                pendingSentenceJump = nil
                return
            }

            // Check if we're already at this sentence (might have been handled by configureSequencePlayback)
            if let currentIdx = sequenceController.currentSentenceIndex, currentIdx == targetSentenceIndex {
                print("[Sequence] Already at target sentence \(targetSentenceIndex), clearing pending jump")
                pendingSentenceJump = nil
                return
            }

            // Use seekToSentence for within-chunk jumps in sequence mode
            print("[Sequence] Within-chunk jump to sentence \(targetSentenceIndex) (number \(pending.sentenceNumber))")
            pendingSentenceJump = nil

            // Capture current track BEFORE updating state
            let previousTrack = sequenceController.currentTrack

            guard let target = sequenceController.seekToSentence(targetSentenceIndex, preferredTrack: .original) else {
                print("[Sequence] seekToSentence returned nil for index \(targetSentenceIndex)")
                return
            }

            // Mute immediately to prevent audio bleed during the transition
            audioCoordinator.setVolume(0)

            // Cancel any pending audio ready subscription from initial load
            // This prevents the old transition from completing with wrong position
            cancelPendingAudioReadySubscription()
            let token = currentTransitionToken

            // Fire pre-transition callback
            onSequenceWillTransition?()
            sequenceController.beginTransition()

            // Check if we need to switch tracks (compare target with PREVIOUS track)
            if target.track != previousTrack {
                handleSequenceTrackSwitch(track: target.track, seekTime: target.time)
            } else {
                // Same track, just seek - mute during seek to prevent audio bleed
                // NOTE: We don't pause here to avoid triggering reading bed pause
                let wasPlaying = audioCoordinator.isPlaying
                audioCoordinator.setVolume(0)
                audioCoordinator.seek(to: target.time) { [weak self] finished in
                    guard let self else { return }
                    print("[Sequence] Within-chunk seek completed (finished=\(finished))")
                    DispatchQueue.main.asyncAfter(deadline: .now() + 0.05) { [weak self] in
                        guard let self else { return }
                        // Check if this transition has been superseded
                        guard token == self.currentTransitionToken else {
                            print("[Sequence] Ignoring stale within-chunk seek completion (token \(token) != current \(self.currentTransitionToken))")
                            return
                        }
                        self.sequenceController.endTransition(expectedTime: target.time)
                        // Restore volume to target level (respects music mix setting)
                        self.audioCoordinator.restoreVolume()
                        // Resume playback if it was playing (in case seek caused a pause)
                        if wasPlaying && !self.audioCoordinator.isPlaying {
                            self.audioCoordinator.play()
                        }
                    }
                }
            }
            return
        }

        // Non-sequence mode: use timeline-based seeking
        guard let startTime = startTimeForSentence(pending.sentenceNumber, in: chunk) else { return }
        pendingSentenceJump = nil
        seekPlayback(to: startTime, in: chunk)
    }

    func startTimeForSentence(_ sentenceNumber: Int, in chunk: InteractiveChunk) -> Double? {
        let activeTimingTrack = activeTimingTrack(for: chunk)
        let useCombinedPhases = useCombinedPhases(for: chunk)
        let timelineSentences = TextPlayerTimeline.buildTimelineSentences(
            sentences: chunk.sentences,
            activeTimingTrack: activeTimingTrack,
            audioDuration: playbackDuration(for: chunk),
            useCombinedPhases: useCombinedPhases,
            timingVersion: chunk.timingVersion
        )
        if let timelineSentences {
            for runtime in timelineSentences {
                guard chunk.sentences.indices.contains(runtime.index) else { continue }
                let sentence = chunk.sentences[runtime.index]
                let id = sentence.displayIndex ?? sentence.id
                if id == sentenceNumber {
                    return runtime.startTime
                }
            }
        }
        if let sentence = chunk.sentences.first(where: { ( $0.displayIndex ?? $0.id ) == sentenceNumber }) {
            return sentence.startTime
        }
        return nil
    }

    /// Get start time for a sentence by its 0-based array index
    func startTimeForSentence(atIndex index: Int, in chunk: InteractiveChunk) -> Double? {
        guard chunk.sentences.indices.contains(index) else { return nil }
        let activeTimingTrack = activeTimingTrack(for: chunk)
        let useCombinedPhases = useCombinedPhases(for: chunk)
        let timelineSentences = TextPlayerTimeline.buildTimelineSentences(
            sentences: chunk.sentences,
            activeTimingTrack: activeTimingTrack,
            audioDuration: playbackDuration(for: chunk),
            useCombinedPhases: useCombinedPhases,
            timingVersion: chunk.timingVersion
        )
        if let timelineSentences,
           let runtime = timelineSentences.first(where: { $0.index == index }) {
            return runtime.startTime
        }
        // Fallback to sentence's start time
        return chunk.sentences[index].startTime
    }

    /// Helper to seek to a sentence after audio finishes loading.
    /// Observes audioCoordinator.isReady and seeks once the audio is ready.
    /// Handles both cases: audio needs to load, or audio is already loaded.
    func seekToSentenceAfterLoad(_ targetIndex: Int, in chunk: InteractiveChunk, autoPlay: Bool) {
        let chunkId = chunk.id

        // If audio is already ready, seek immediately
        if audioCoordinator.isReady {
            if let startTime = startTimeForSentence(atIndex: targetIndex, in: chunk) {
                print("[SingleToggle] Audio already ready, seeking immediately to sentence[\(targetIndex)] at time \(String(format: "%.3f", startTime))")
                seekPlayback(to: startTime, in: chunk)
                if autoPlay && !audioCoordinator.isPlaying {
                    audioCoordinator.play()
                }
            }
            return
        }

        // Audio not ready yet - wait for it
        var seenLoadingState = false
        var isFirstEmission = true
        var cancellable: AnyCancellable?

        cancellable = audioCoordinator.$isReady
            .sink { [weak self] isReady in
                guard let self else { return }
                guard let currentChunk = self.selectedChunk, currentChunk.id == chunkId else {
                    cancellable?.cancel()
                    return
                }

                if !isReady {
                    seenLoadingState = true
                    isFirstEmission = false
                    print("[SingleToggle] Audio loading...")
                } else if seenLoadingState || isFirstEmission {
                    // Either we saw loading->ready transition, or audio was already ready on first emit
                    isFirstEmission = false
                    if let startTime = self.startTimeForSentence(atIndex: targetIndex, in: currentChunk) {
                        print("[SingleToggle] Audio ready, seeking to sentence[\(targetIndex)] at time \(String(format: "%.3f", startTime))")
                        self.seekPlayback(to: startTime, in: currentChunk)
                        if autoPlay && !self.audioCoordinator.isPlaying {
                            self.audioCoordinator.play()
                        }
                    }
                    cancellable?.cancel()
                }
            }
    }
}
