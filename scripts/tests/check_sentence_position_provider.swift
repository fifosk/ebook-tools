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
    fputs("SentencePositionProvider check failed: \(message)\n", stderr)
    exit(1)
}

@MainActor
private func requireEqual<T: Equatable>(_ actual: T, _ expected: T, _ message: String) {
    if actual != expected {
        fail("\(message). Expected \(expected), got \(actual).")
    }
}

@MainActor
private func requireNil<T>(_ actual: T?, _ message: String) {
    if let actual {
        fail("\(message). Expected nil, got \(actual).")
    }
}

@MainActor
private func requireResult(
    _ result: SentencePositionProvider.Result?,
    index expectedIndex: Int,
    strategy expectedStrategy: SentencePositionProvider.Result.Strategy,
    _ message: String
) {
    guard let result else {
        fail("\(message). Expected a result.")
    }
    requireEqual(result.index, expectedIndex, "\(message) index")
    requireEqual(result.strategy, expectedStrategy, "\(message) strategy")
}

@MainActor
private func runChecks() {
    let sequenceController = SequencePlaybackController(isEnabled: true, currentSentenceIndex: 7)
    var transcriptCalls = 0
    var timeCalls = 0

    let provider = SentencePositionProvider.from(
        sequenceController: sequenceController,
        transcriptDisplayIndex: {
            transcriptCalls += 1
            return 3
        },
        timeBasedIndex: {
            timeCalls += 1
            return 2
        }
    )

    requireResult(
        provider.currentSentenceIndex(),
        index: 7,
        strategy: .sequenceController,
        "Enabled sequence controller should win over UI and time state"
    )
    requireEqual(transcriptCalls, 0, "Sequence result should not query transcript fallback")
    requireEqual(timeCalls, 0, "Sequence result should not query time fallback")

    sequenceController.isEnabled = false
    requireResult(
        provider.currentSentenceIndex(),
        index: 3,
        strategy: .transcriptDisplay,
        "Transcript state should win when sequence mode is inactive"
    )
    requireEqual(transcriptCalls, 1, "Transcript fallback should be queried once")
    requireEqual(timeCalls, 0, "Transcript result should not query time fallback")

    let timeOnlyProvider = SentencePositionProvider.from(
        sequenceController: sequenceController,
        transcriptDisplayIndex: { nil },
        timeBasedIndex: { 11 }
    )
    requireResult(
        timeOnlyProvider.currentSentenceIndex(),
        index: 11,
        strategy: .timeBased,
        "Time state should be used when sequence and transcript state are unavailable"
    )
    requireEqual(timeOnlyProvider.index, 11, "Index shortcut should return the resolved sentence index")

    sequenceController.isEnabled = true
    sequenceController.currentSentenceIndex = nil
    let nilProvider = SentencePositionProvider.from(
        sequenceController: sequenceController,
        transcriptDisplayIndex: { nil },
        timeBasedIndex: { nil }
    )
    requireNil(nilProvider.currentSentenceIndex(), "Provider should return nil when every strategy is unavailable")
    requireNil(nilProvider.index, "Index shortcut should return nil when every strategy is unavailable")

    let chunk = InteractiveChunk(
        id: "chapter-1",
        startSentence: nil,
        sentences: [
            .init(id: 0, displayIndex: 41, startGate: 10.5, originalStartGate: 2.25),
            .init(id: 1, displayIndex: nil, startGate: 12.0, originalStartGate: 4.0),
            .init(id: 2, displayIndex: 43, startGate: -1.0, originalStartGate: .infinity)
        ]
    )
    requireEqual(
        SentencePositionProvider.sentenceNumber(for: chunk.sentences[0]),
        41,
        "Display index should be the public sentence number when present"
    )
    requireEqual(
        SentencePositionProvider.sentenceNumber(for: chunk.sentences[1]),
        1,
        "Sentence id should be the fallback sentence number"
    )
    requireEqual(
        SentencePositionProvider.sentenceIndex(in: chunk, matching: 43),
        2,
        "Sentence index lookup should match display index"
    )
    requireEqual(
        SentencePositionProvider.sentenceIndex(in: chunk, matching: 1),
        1,
        "Sentence index lookup should match id fallback"
    )
    requireNil(
        SentencePositionProvider.pendingSentenceIndex(
            in: chunk,
            pendingJump: .init(chunkID: "other", sentenceNumber: 43)
        ),
        "Pending jump for another chunk should not resolve"
    )
    requireEqual(
        SentencePositionProvider.pendingSentenceIndex(
            in: chunk,
            pendingJump: .init(chunkID: "chapter-1", sentenceNumber: 43)
        ),
        2,
        "Pending jump for the same chunk should resolve"
    )
    requireEqual(
        SentencePositionProvider.targetSentenceIndex(
            in: chunk,
            explicitIndex: 0,
            pendingJump: .init(chunkID: "chapter-1", sentenceNumber: 43)
        ),
        0,
        "Explicit target should win over pending jump"
    )
    requireEqual(
        SentencePositionProvider.targetSentenceIndex(
            in: chunk,
            explicitIndex: nil,
            pendingJump: .init(chunkID: "chapter-1", sentenceNumber: 43)
        ),
        2,
        "Pending jump should provide the target when no explicit index is available"
    )
    let rangeChunk = InteractiveChunk(
        id: "chapter-220",
        startSentence: 2190,
        sentences: [
            .init(id: 0, displayIndex: nil),
            .init(id: 1, displayIndex: nil),
            .init(id: 2, displayIndex: nil)
        ]
    )
    requireEqual(
        SentencePositionProvider.sentenceNumber(in: rangeChunk, at: 1),
        2191,
        "Chunk-range sentence numbering should derive visible numbers from startSentence"
    )
    requireEqual(
        SentencePositionProvider.sentenceIndex(in: rangeChunk, matching: 2191),
        1,
        "Chunk-range lookup should map visible sentence numbers back to local row indexes"
    )
    requireNil(
        SentencePositionProvider.sentenceIndex(in: rangeChunk, matching: 1),
        "Chunk-range lookup must not treat local row ids as visible sentence numbers"
    )
    requireEqual(
        SentencePositionProvider.gateStartTime(
            for: chunk.sentences[0],
            activeTimingTrack: .translation
        ),
        10.5,
        "Translation timing should use the translation start gate"
    )
    requireEqual(
        SentencePositionProvider.gateStartTime(
            for: chunk.sentences[0],
            activeTimingTrack: .original
        ),
        2.25,
        "Original timing should use the original start gate"
    )
    requireNil(
        SentencePositionProvider.gateStartTime(
            for: chunk.sentences[0],
            activeTimingTrack: .mix
        ),
        "Mixed timing should not pick a single-track gate"
    )
    requireEqual(
        SentencePositionProvider.gateStartTime(
            in: chunk,
            at: 1,
            activeTimingTrack: .translation
        ),
        12.0,
        "Chunk gate lookup should resolve by local row index"
    )
    requireEqual(
        SentencePositionProvider.sentenceIndex(
            in: chunk,
            atTime: 11.25,
            activeTimingTrack: .translation
        ),
        0,
        "Translation time lookup should use the nearest preceding translation gate"
    )
    requireEqual(
        SentencePositionProvider.sentenceNumber(
            in: chunk,
            atTime: 12.25,
            activeTimingTrack: .translation
        ),
        1,
        "Translation time lookup should resolve the visible sentence number for single-track anchors"
    )
    requireEqual(
        SentencePositionProvider.sentenceNumber(
            in: rangeChunk,
            atTime: 0,
            activeTimingTrack: .translation
        ),
        nil,
        "Time lookup should ignore tracks that have no gate timings"
    )
    requireNil(
        SentencePositionProvider.sentenceIndex(
            in: chunk,
            atTime: 12.25,
            activeTimingTrack: .mix
        ),
        "Mixed timing should not create a single-track time anchor"
    )
    requireNil(
        SentencePositionProvider.gateStartTime(
            in: chunk,
            at: 2,
            activeTimingTrack: .translation
        ),
        "Negative translation gates should be ignored"
    )
    requireNil(
        SentencePositionProvider.gateStartTime(
            in: chunk,
            at: 2,
            activeTimingTrack: .original
        ),
        "Non-finite original gates should be ignored"
    )
    requireNil(
        SentencePositionProvider.gateStartTime(
            in: chunk,
            at: 99,
            activeTimingTrack: .translation
        ),
        "Out-of-range gate lookup should return nil"
    )
}

@main
private struct SentencePositionProviderCheck {
    static func main() async {
        await MainActor.run {
            runChecks()
        }
    }
}
