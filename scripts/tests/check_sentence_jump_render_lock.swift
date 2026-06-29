import Darwin
import Foundation

enum TextPlayerTimingTrack: Equatable {
    case mix
    case translation
    case original
}

@MainActor
final class SequencePlaybackController {
    var isEnabled: Bool
    var currentSentenceIndex: Int?

    init(isEnabled: Bool = false, currentSentenceIndex: Int? = nil) {
        self.isEnabled = isEnabled
        self.currentSentenceIndex = currentSentenceIndex
    }
}

struct InteractiveChunk: Identifiable {
    struct Sentence: Identifiable {
        let id: Int
        let displayIndex: Int?
        let startGate: Double?
        let originalStartGate: Double?

        init(
            id: Int,
            displayIndex: Int?,
            startGate: Double? = nil,
            originalStartGate: Double? = nil
        ) {
            self.id = id
            self.displayIndex = displayIndex
            self.startGate = startGate
            self.originalStartGate = originalStartGate
        }
    }

    let id: String
    let startSentence: Int?
    let sentences: [Sentence]
}

struct PendingSentenceJump {
    let chunkID: String
    let sentenceNumber: Int
}

@MainActor
private func fail(_ message: String) -> Never {
    fputs("Sentence jump render lock check failed: \(message)\n", stderr)
    exit(1)
}

@MainActor
private func require(_ condition: Bool, _ message: String) {
    if !condition {
        fail(message)
    }
}

@MainActor
private func requireFalse(_ condition: Bool, _ message: String) {
    if condition {
        fail(message)
    }
}

@MainActor
private func runChecks() {
    let chunk = InteractiveChunk(
        id: "chunk_2220",
        startSentence: 2220,
        sentences: (0..<10).map { offset in
            .init(
                id: offset,
                displayIndex: nil,
                startGate: Double(offset) * 2.0,
                originalStartGate: Double(offset) * 4.0
            )
        }
    )

    let startTimeForSentence: (Int, InteractiveChunk) -> Double? = { sentenceNumber, chunk in
        guard let index = SentencePositionProvider.sentenceIndex(in: chunk, matching: sentenceNumber) else {
            return nil
        }
        return chunk.sentences[index].startGate
    }

    require(
        InteractiveSentenceJumpRenderLock.applies(
            pendingChunkID: "chunk_2220",
            to: chunk
        ),
        "Render lock should apply to its target chunk"
    )
    requireFalse(
        InteractiveSentenceJumpRenderLock.applies(
            pendingChunkID: "chunk_2210",
            to: chunk
        ),
        "Render lock must not apply to stale chunks"
    )
    require(
        InteractiveSentenceJumpRenderLock.isExpired(
            startedAt: Date(timeIntervalSince1970: 10),
            now: Date(timeIntervalSince1970: 23.5)
        ),
        "Render lock should expire after the default timeout"
    )
    requireFalse(
        InteractiveSentenceJumpRenderLock.isExpired(
            startedAt: Date(timeIntervalSince1970: 10),
            now: Date(timeIntervalSince1970: 20)
        ),
        "Render lock should remain active inside the default timeout"
    )

    requireFalse(
        InteractiveSentenceJumpRenderLock.reachedLivePlayback(
            pendingSentenceNumber: 2225,
            pendingChunkID: "chunk_2220",
            in: chunk,
            highlightingTime: 10.0,
            currentChunkAudioIsActive: false,
            startTimeForSentence: startTimeForSentence
        ),
        "Stale audio from another chunk must not unlock a translation-only slider jump"
    )
    requireFalse(
        InteractiveSentenceJumpRenderLock.reachedLivePlayback(
            pendingSentenceNumber: 2225,
            pendingChunkID: "chunk_2210",
            in: chunk,
            highlightingTime: 10.0,
            currentChunkAudioIsActive: true,
            startTimeForSentence: startTimeForSentence
        ),
        "A pending lock for another chunk must not unlock rendering"
    )
    require(
        InteractiveSentenceJumpRenderLock.reachedLivePlayback(
            pendingSentenceNumber: 2225,
            pendingChunkID: "chunk_2220",
            in: chunk,
            highlightingTime: 10.0,
            currentChunkAudioIsActive: true,
            startTimeForSentence: startTimeForSentence
        ),
        "Translation-only slider lock should unlock when live audio reaches the visible target sentence"
    )
    requireFalse(
        InteractiveSentenceJumpRenderLock.reachedLivePlayback(
            pendingSentenceNumber: 2225,
            pendingChunkID: "chunk_2220",
            in: chunk,
            highlightingTime: 12.25,
            currentChunkAudioIsActive: true,
            startTimeForSentence: startTimeForSentence
        ),
        "The next visible sentence window must not unlock the previous slider target"
    )
}

@main
private struct SentenceJumpRenderLockCheck {
    static func main() async {
        await MainActor.run {
            runChecks()
        }
    }
}
