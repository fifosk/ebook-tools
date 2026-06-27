import Darwin
import Foundation

enum SequenceTrack: String {
    case original
    case translation
}

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

    struct AudioOption: Identifiable {
        enum Kind: String {
            case combined
            case translation
            case original
            case other
        }

        let id: String
        let label: String
        let kind: Kind
        let streamURLs: [URL]
        let timingURL: URL?
        let duration: Double?
        let fileDurations: [Double]?

        var primaryURL: URL {
            streamURLs[0]
        }
    }

    let id: String
    let sentences: [Sentence]
    let audioOptions: [AudioOption]
}

struct PendingSentenceJump {
    let chunkID: String
    let sentenceNumber: Int
}

@MainActor
private func fail(_ message: String) -> Never {
    fputs("Playback mode switch integration check failed: \(message)\n", stderr)
    exit(1)
}

@MainActor
private func requireEqual<T: Equatable>(_ actual: T, _ expected: T, _ message: String) {
    if actual != expected {
        fail("\(message). Expected \(expected), got \(actual).")
    }
}

@MainActor
private func requireInstruction(
    _ instruction: ResolvedAudioInstruction?,
    optionID expectedID: String,
    timing expectedTiming: TextPlayerTimingTrack,
    _ message: String
) {
    guard case .singleOption(let option, let timing)? = instruction else {
        fail("\(message). Expected single option instruction.")
    }
    requireEqual(option.id, expectedID, "\(message) option id")
    requireEqual(timing, expectedTiming, "\(message) timing")
}

@MainActor
private func requireSequenceInstruction(
    _ instruction: ResolvedAudioInstruction?,
    optionID expectedID: String,
    _ message: String
) {
    guard case .sequence(let option)? = instruction else {
        fail("\(message). Expected sequence instruction.")
    }
    requireEqual(option.id, expectedID, "\(message) option id")
}

private func audioOption(
    _ id: String,
    kind: InteractiveChunk.AudioOption.Kind,
    urls: [URL]
) -> InteractiveChunk.AudioOption {
    InteractiveChunk.AudioOption(
        id: id,
        label: id,
        kind: kind,
        streamURLs: urls,
        timingURL: nil,
        duration: nil,
        fileDurations: nil
    )
}

@MainActor
private func runChecks() {
    let originalURL = URL(string: "https://example.invalid/original.m4a")!
    let translationURL = URL(string: "https://example.invalid/translation.m4a")!
    let chunk = InteractiveChunk(
        id: "chapter-1",
        sentences: [
            .init(id: 0, displayIndex: 100),
            .init(id: 1, displayIndex: nil),
            .init(id: 2, displayIndex: 102),
            .init(id: 3, displayIndex: 103)
        ],
        audioOptions: [
            audioOption("combined", kind: .combined, urls: [originalURL, translationURL]),
            audioOption("original", kind: .original, urls: [originalURL]),
            audioOption("translation", kind: .translation, urls: [translationURL])
        ]
    )

    let sequenceController = SequencePlaybackController(isEnabled: true, currentSentenceIndex: 14)
    let manager = AudioModeManager()
    var modeEvents: [(AudioMode, Int?)] = []
    manager.onModeChange = { mode, sentenceIndex in
        modeEvents.append((mode, sentenceIndex))
    }

    let sequenceProvider = SentencePositionProvider.from(
        sequenceController: sequenceController,
        transcriptDisplayIndex: { 6 },
        timeBasedIndex: { 5 }
    )
    manager.toggle(.original, preservingPosition: sequenceProvider.index)
    requireEqual(modeEvents.count, 1, "Track toggle should emit one mode event")
    requireEqual(modeEvents[0].0, .singleTrack(.translation), "Original toggle should switch to translation-only")
    requireEqual(modeEvents[0].1, 14, "Sequence-controller position should be preserved")
    requireEqual(manager.resolvePreferredTrackID(for: chunk), "translation", "Translation-only mode should prefer translation")
    requireInstruction(
        manager.resolveAudioInstruction(for: chunk, selectedTrackID: "combined"),
        optionID: "translation",
        timing: .translation,
        "Translation-only mode should route combined selection to translation audio"
    )

    sequenceController.isEnabled = false
    let transcriptProvider = SentencePositionProvider.from(
        sequenceController: sequenceController,
        transcriptDisplayIndex: { 6 },
        timeBasedIndex: { 5 }
    )
    manager.toggle(.translation, preservingPosition: transcriptProvider.index)
    requireEqual(modeEvents.count, 2, "Second track toggle should emit a mode event")
    requireEqual(modeEvents[1].0, .singleTrack(.original), "Translation-only toggle should switch to original-only")
    requireEqual(modeEvents[1].1, 6, "Transcript display position should be preserved")
    requireEqual(manager.resolvePreferredTrackID(for: chunk), "original", "Original-only mode should prefer original")
    requireInstruction(
        manager.resolveAudioInstruction(for: chunk, selectedTrackID: "combined"),
        optionID: "original",
        timing: .original,
        "Original-only mode should route combined selection to original audio"
    )

    let pendingTarget = SentencePositionProvider.targetSentenceIndex(
        in: chunk,
        explicitIndex: nil,
        pendingJump: .init(chunkID: "chapter-1", sentenceNumber: 102)
    )
    manager.enableSequenceMode(preservingPosition: pendingTarget)
    requireEqual(modeEvents.count, 3, "Sequence restore should emit a mode event")
    requireEqual(modeEvents[2].0, .sequence, "Pending jump restore should return to sequence mode")
    requireEqual(modeEvents[2].1, 2, "Pending jump should preserve the resolved local sentence index")
    requireEqual(manager.resolvePreferredTrackID(for: chunk), "combined", "Sequence mode should prefer combined audio")
    requireSequenceInstruction(
        manager.resolveAudioInstruction(for: chunk, selectedTrackID: "combined"),
        optionID: "combined",
        "Sequence mode should keep combined audio selected"
    )

    manager.setTracks(original: false, translation: true, preservingPosition: 17)
    let timeProvider = SentencePositionProvider.from(
        sequenceController: sequenceController,
        transcriptDisplayIndex: { nil },
        timeBasedIndex: { 3 }
    )
    manager.toggle(kind: .combined, preservingPosition: timeProvider.index)
    requireEqual(modeEvents.count, 5, "Single-track to combined restore should emit a mode event")
    requireEqual(modeEvents[4].0, .sequence, "Combined kind should restore sequence mode")
    requireEqual(modeEvents[4].1, 3, "Time fallback position should be preserved")

    let explicitTarget = SentencePositionProvider.targetSentenceIndex(
        in: chunk,
        explicitIndex: 1,
        pendingJump: .init(chunkID: "chapter-1", sentenceNumber: 103)
    )
    requireEqual(explicitTarget, 1, "Explicit sentence target should win over pending jump")
}

@main
private struct PlaybackModeSwitchIntegrationCheck {
    static func main() async {
        await MainActor.run {
            runChecks()
        }
    }
}
