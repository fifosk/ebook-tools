import Foundation

@MainActor
enum InteractiveSentenceJumpRenderLock {
    static let defaultTimeout: TimeInterval = 12.0

    static func isExpired(
        startedAt: Date?,
        now: Date = Date(),
        timeout: TimeInterval = 12.0
    ) -> Bool {
        guard let startedAt else { return true }
        return now.timeIntervalSince(startedAt) > timeout
    }

    static func applies(pendingChunkID: String?, to chunk: InteractiveChunk) -> Bool {
        guard let pendingChunkID else { return true }
        return pendingChunkID == chunk.id
    }

    static func reachedLivePlayback(
        pendingSentenceNumber: Int?,
        pendingChunkID: String?,
        in chunk: InteractiveChunk,
        highlightingTime: Double,
        currentChunkAudioIsActive: Bool,
        startTimeForSentence: (Int, InteractiveChunk) -> Double?
    ) -> Bool {
        guard let pendingSentenceNumber else { return false }
        guard applies(pendingChunkID: pendingChunkID, to: chunk) else { return false }
        guard currentChunkAudioIsActive else { return false }
        guard highlightingTime.isFinite else { return false }
        guard let targetIndex = SentencePositionProvider.sentenceIndex(
            in: chunk,
            matching: pendingSentenceNumber
        ) else {
            return false
        }
        guard let start = startTimeForSentence(pendingSentenceNumber, chunk),
              start.isFinite else {
            return false
        }

        let tolerance = 0.18
        if chunk.sentences.indices.contains(targetIndex + 1),
           let nextNumber = SentencePositionProvider.sentenceNumber(in: chunk, at: targetIndex + 1),
           let nextStart = startTimeForSentence(nextNumber, chunk),
           nextStart > start {
            return highlightingTime >= start - tolerance && highlightingTime < nextStart + tolerance
        }
        return highlightingTime >= start - tolerance && highlightingTime <= start + 2.5
    }
}
