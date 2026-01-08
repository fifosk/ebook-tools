import Foundation
import SwiftUI

extension InteractivePlayerViewModel {
    func selectChunk(id: String, autoPlay: Bool = false) {
        guard selectedChunkID != id else { return }
        selectedChunkID = id
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
        prepareAudio(for: chunk, autoPlay: autoPlay)
        attemptPendingSentenceJump(in: chunk)
        Task { [weak self] in
            await self?.loadChunkMetadataIfNeeded(for: chunk.id)
        }
    }

    func selectAudioTrack(id: String) {
        guard selectedAudioTrackID != id else { return }
        selectedAudioTrackID = id
        guard let chunk = selectedChunk else { return }
        if let track = chunk.audioOptions.first(where: { $0.id == id }) {
            preferredAudioKind = track.kind
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
        if let chunk = context.chunks.first(where: { !$0.audioOptions.isEmpty }) ?? context.chunks.first {
            selectedChunkID = chunk.id
            if let option = chunk.audioOptions.first {
                selectedAudioTrackID = option.id
                preferredAudioKind = option.kind
            } else {
                selectedAudioTrackID = nil
            }
            prepareAudio(for: chunk, autoPlay: false)
            Task { [weak self] in
                await self?.loadChunkMetadataIfNeeded(for: chunk.id)
            }
        } else {
            selectedChunkID = nil
            selectedAudioTrackID = nil
            audioCoordinator.reset()
            selectedTimingURL = nil
            preferredAudioKind = nil
        }
    }

    func prepareAudio(for chunk: InteractiveChunk, autoPlay: Bool) {
        guard let trackID = selectedAudioTrackID,
              let track = chunk.audioOptions.first(where: { $0.id == trackID }) else {
            audioCoordinator.reset()
            selectedTimingURL = nil
            return
        }
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
                await self?.loadChunkMetadataIfNeeded(for: targetChunk.id)
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
            useCombinedPhases: useCombinedPhases
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
