import Foundation

/// Shared sentence index resolution utilities for playback views.
/// Consolidates duplicate sentence number estimation logic.
enum PlaybackSentenceIndexHelpers {
    /// Resolves the sentence index at a given highlight time.
    /// Uses active sentence lookup with fallback to time-based estimation.
    static func resolveResumeSentenceIndex(
        at highlightTime: Double,
        chunk: InteractiveChunk?,
        activeSentence: InteractiveChunk.Sentence?,
        playbackDuration: Double?
    ) -> Int? {
        guard let chunk else { return nil }
        let resolved = activeSentence.flatMap { sentence in
            resolveSentenceNumber(for: sentence, in: chunk)
        }
        let fallback = estimateSentenceNumber(for: chunk, at: highlightTime, duration: playbackDuration)
        guard let resolved else { return fallback }
        guard let fallback else { return resolved }
        if resolved == fallback {
            return resolved
        }
        if shouldPreferEstimatedIndex(for: chunk, resolved: resolved, estimated: fallback, time: highlightTime, duration: playbackDuration) {
            return fallback
        }
        return resolved
    }

    /// Resolves the sentence number for a given sentence in a chunk.
    static func resolveSentenceNumber(for sentence: InteractiveChunk.Sentence, in chunk: InteractiveChunk) -> Int? {
        if let displayIndex = sentence.displayIndex {
            return displayIndex
        }
        if let index = chunk.sentences.firstIndex(where: { $0.id == sentence.id && $0.displayIndex == sentence.displayIndex }) {
            if let start = chunk.startSentence {
                return start + index
            }
            if let first = chunk.sentences.first?.id {
                return first + index
            }
        }
        return sentence.id
    }

    /// Estimates the sentence number based on playback time progress.
    static func estimateSentenceNumber(for chunk: InteractiveChunk, at time: Double, duration: Double?) -> Int? {
        let count = sentenceCount(for: chunk)
        guard count > 0 else { return nil }
        let base = baseSentenceNumber(for: chunk)
        guard let base else { return nil }
        guard count > 1 else { return base }
        guard let duration, duration.isFinite, duration > 0 else { return base }
        let progress = min(max(time / duration, 0), 1)
        let offset = Int((Double(count - 1) * progress).rounded(.down))
        return base + offset
    }

    /// Determines if the estimated index should be preferred over the resolved index.
    static func shouldPreferEstimatedIndex(
        for chunk: InteractiveChunk,
        resolved: Int,
        estimated: Int,
        time: Double,
        duration: Double?
    ) -> Bool {
        let count = sentenceCount(for: chunk)
        guard count > 1 else { return false }
        let base = chunk.startSentence ?? chunk.sentences.first?.displayIndex ?? chunk.sentences.first?.id
        guard let base, resolved == base else { return false }
        guard let duration, duration.isFinite, duration > 0 else { return false }
        let progress = min(max(time / duration, 0), 1)
        return progress > 0.1 && estimated > resolved
    }

    // MARK: - Private Helpers

    private static func sentenceCount(for chunk: InteractiveChunk) -> Int {
        if let start = chunk.startSentence, let end = chunk.endSentence, end >= start {
            return end - start + 1
        }
        return chunk.sentences.count
    }

    private static func baseSentenceNumber(for chunk: InteractiveChunk) -> Int? {
        if let start = chunk.startSentence {
            return start
        }
        if let first = chunk.sentences.first?.displayIndex {
            return first
        }
        return chunk.sentences.first?.id
    }
}
