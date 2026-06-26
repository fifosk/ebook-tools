import Darwin
import Foundation

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
    }

    let id: String
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
        sentences: [
            .init(id: 0, displayIndex: 41),
            .init(id: 1, displayIndex: nil),
            .init(id: 2, displayIndex: 43)
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
}

@main
private struct SentencePositionProviderCheck {
    static func main() async {
        await MainActor.run {
            runChecks()
        }
    }
}
