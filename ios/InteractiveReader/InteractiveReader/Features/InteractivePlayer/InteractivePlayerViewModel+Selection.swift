import Foundation
import SwiftUI

extension InteractivePlayerViewModel {
    /// Check if chunk sentences have gate data needed for combined (sequence) mode
    private func sentencesHaveGateData(_ sentences: [InteractiveChunk.Sentence]) -> Bool {
        guard let first = sentences.first else { return false }
        // Gate data is required for sequence playback - check if any gate fields are populated
        return first.originalStartGate != nil || first.startGate != nil
    }

    /// Check if the currently selected track requires gate data (combined mode)
    private func selectedTrackRequiresGates(for chunk: InteractiveChunk) -> Bool {
        guard let trackID = selectedAudioTrackID,
              let track = chunk.audioOptions.first(where: { $0.id == trackID }) else {
            return false
        }
        return track.kind == .combined
    }

    func selectChunk(id: String, autoPlay: Bool = false) {
        guard selectedChunkID != id else { return }
        selectedChunkID = id
        lastPrefetchSentenceNumber = nil
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
        let hasGates = sentencesHaveGateData(chunk.sentences)
        let needsGates = selectedTrackRequiresGates(for: chunk)
        if !chunk.sentences.isEmpty && (!needsGates || hasGates) {
            isTranscriptLoading = false
            prepareAudio(for: chunk, autoPlay: autoPlay)
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
            self.prepareAudio(for: updatedChunk, autoPlay: autoPlay)
            self.attemptPendingSentenceJump(in: updatedChunk)
        }
    }

    func selectAudioTrack(id: String) {
        guard selectedAudioTrackID != id else { return }
        print("[AudioTrack] Selecting track: \(id)")
        selectedAudioTrackID = id
        guard let chunk = selectedChunk else { return }
        if let track = chunk.audioOptions.first(where: { $0.id == id }) {
            print("[AudioTrack] Found track: kind=\(track.kind), label=\(track.label), urls=\(track.streamURLs.map { $0.lastPathComponent })")
            preferredAudioKind = track.kind
            // If switching to combined mode and sentences lack gate data, load metadata first
            if track.kind == .combined && !sentencesHaveGateData(chunk.sentences) {
                print("[AudioTrack] Combined mode selected but sentences lack gate data, loading metadata...")
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
            let hasGates = sentencesHaveGateData(chunk.sentences)
            let needsGates = selectedTrackRequiresGates(for: chunk)
            if !chunk.sentences.isEmpty && (!needsGates || hasGates) {
                isTranscriptLoading = false
                prepareAudio(for: chunk, autoPlay: false)
                return
            }
            // Mark transcript as loading while we fetch metadata
            isTranscriptLoading = true
            // Load metadata before preparing audio to ensure transcript is ready
            let chunkId = chunk.id
            Task { [weak self] in
                guard let self else { return }
                await self.loadChunkMetadataIfNeeded(for: chunkId, force: true)
                guard self.selectedChunkID == chunkId else { return }
                // Get the UPDATED chunk after metadata loaded (may have new sentences)
                guard let updatedChunk = self.selectedChunk else { return }
                // Clear loading state now that we have the transcript
                self.isTranscriptLoading = false
                // Only prepare audio if transcript is now available
                guard !updatedChunk.sentences.isEmpty else { return }
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

    func prepareAudio(for chunk: InteractiveChunk, autoPlay: Bool) {
        guard let trackID = selectedAudioTrackID,
              let track = chunk.audioOptions.first(where: { $0.id == trackID }) else {
            audioCoordinator.reset()
            sequenceController.reset()
            selectedTimingURL = nil
            return
        }

        // For combined mode, try to use sequence playback (per-sentence switching)
        if track.kind == .combined {
            // Check if there's a pending sentence jump - if so, find the target sentence index
            let targetSentenceIndex: Int? = {
                guard let pending = pendingSentenceJump, pending.chunkID == chunk.id else { return nil }
                return chunk.sentences.firstIndex {
                    ($0.displayIndex ?? $0.id) == pending.sentenceNumber
                }
            }()
            configureSequencePlayback(for: chunk, autoPlay: autoPlay, targetSentenceIndex: targetSentenceIndex)
            return
        }

        // For single-track modes, check if we're already playing the correct track
        // This prevents unnecessary reloading from SwiftUI re-renders
        if audioCoordinator.activeURLs == track.streamURLs {
            // Already playing the correct track, just update autoPlay state if needed
            if autoPlay && !audioCoordinator.isPlaying {
                audioCoordinator.play()
            }
            return
        }

        // For single-track modes, use direct loading
        sequenceController.reset()
        audioCoordinator.load(urls: track.streamURLs, autoPlay: autoPlay)
        selectedTimingURL = track.timingURL ?? track.streamURLs.first
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
        selectChunk(id: targetChunk.id, autoPlay: autoPlay)
        attemptPendingSentenceJump(in: targetChunk)
        if selectedChunkID == targetChunk.id {
            Task { [weak self] in
                await self?.loadChunkMetadataIfNeeded(for: targetChunk.id, force: true)
            }
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

        // In sequence mode, the pending jump is handled by configureSequencePlayback
        // via the targetSentenceIndex parameter, so just clear it here
        if isSequenceModeActive {
            print("[Sequence] Pending sentence jump already handled by configureSequencePlayback")
            pendingSentenceJump = nil
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
}
