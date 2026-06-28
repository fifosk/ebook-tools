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

enum SingleTrackNavigationTarget: Equatable, CustomStringConvertible {
    case sentence(chunkID: String, localIndex: Int, startTime: Double)
    case chunkStart(chunkID: String)
    case chunkEnd(chunkID: String)

    var description: String {
        switch self {
        case .sentence(let chunkID, let localIndex, let startTime):
            return "sentence(\(chunkID), \(localIndex), \(startTime))"
        case .chunkStart(let chunkID):
            return "chunkStart(\(chunkID))"
        case .chunkEnd(let chunkID):
            return "chunkEnd(\(chunkID))"
        }
    }
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

private func activeSentenceIndex(
    in chunk: InteractiveChunk,
    at time: Double,
    track: SequenceTrack
) -> Int? {
    for (index, sentence) in chunk.sentences.enumerated() {
        let start = track == .translation ? sentence.startGate : sentence.originalStartGate
        let nextStart: Double? = {
            let nextIndex = index + 1
            guard chunk.sentences.indices.contains(nextIndex) else { return nil }
            let next = chunk.sentences[nextIndex]
            return track == .translation ? next.startGate : next.originalStartGate
        }()
        guard let start else { continue }
        if let nextStart {
            if time >= start && time < nextStart {
                return index
            }
        } else if time >= start {
            return index
        }
    }
    return nil
}

private func startTime(
    in chunk: InteractiveChunk,
    at index: Int,
    track: SequenceTrack
) -> Double? {
    guard chunk.sentences.indices.contains(index) else { return nil }
    let sentence = chunk.sentences[index]
    return track == .translation ? sentence.startGate : sentence.originalStartGate
}

private func singleTrackNavigationTarget(
    chunks: [InteractiveChunk],
    currentChunkID: String,
    currentTime: Double,
    track: SequenceTrack,
    forward: Bool,
    anchorSentenceNumber: Int? = nil
) -> SingleTrackNavigationTarget? {
    guard let chunkIndex = chunks.firstIndex(where: { $0.id == currentChunkID }) else { return nil }
    let chunk = chunks[chunkIndex]
    let activeIndex = anchorSentenceNumber.flatMap { sentenceNumber in
        chunk.sentences.firstIndex { $0.displayIndex == sentenceNumber || $0.id == sentenceNumber }
    } ?? activeSentenceIndex(in: chunk, at: currentTime, track: track)

    guard let activeIndex else { return nil }
    let targetIndex = forward ? activeIndex + 1 : activeIndex - 1
    if chunk.sentences.indices.contains(targetIndex),
       let start = startTime(in: chunk, at: targetIndex, track: track) {
        return .sentence(chunkID: chunk.id, localIndex: targetIndex, startTime: start)
    }
    if forward {
        let nextIndex = chunkIndex + 1
        guard chunks.indices.contains(nextIndex) else { return nil }
        return .chunkStart(chunkID: chunks[nextIndex].id)
    }
    let previousIndex = chunkIndex - 1
    guard chunks.indices.contains(previousIndex) else { return nil }
    return .chunkEnd(chunkID: chunks[previousIndex].id)
}

@MainActor
private func usesCombinedQueue(
    isSequenceModeActive: Bool,
    audioModeManager: AudioModeManager?,
    selectedOption: InteractiveChunk.AudioOption?
) -> Bool {
    if isSequenceModeActive {
        return true
    }
    if let audioModeManager, !audioModeManager.isSequenceMode {
        return false
    }
    guard let selectedOption else { return false }
    return selectedOption.kind == .combined && selectedOption.streamURLs.count > 1
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
    requireEqual(
        usesCombinedQueue(
            isSequenceModeActive: false,
            audioModeManager: manager,
            selectedOption: chunk.audioOptions.first { $0.id == "combined" }
        ),
        false,
        "Translation-only mode should not add combined queue offsets"
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
    requireEqual(
        usesCombinedQueue(
            isSequenceModeActive: false,
            audioModeManager: manager,
            selectedOption: chunk.audioOptions.first { $0.id == "combined" }
        ),
        false,
        "Original-only mode should not add combined queue offsets"
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
    requireEqual(
        usesCombinedQueue(
            isSequenceModeActive: true,
            audioModeManager: manager,
            selectedOption: chunk.audioOptions.first { $0.id == "combined" }
        ),
        true,
        "Sequence mode should keep combined queue timing enabled"
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

    let dutchOnlyChunks = [
        InteractiveChunk(
            id: "chunk_2210",
            sentences: (0..<10).map { offset in
                .init(
                    id: offset,
                    displayIndex: 2210 + offset,
                    startGate: Double(offset) * 2.0,
                    originalStartGate: Double(offset) * 4.0
                )
            },
            audioOptions: [
                audioOption("combined", kind: .combined, urls: [originalURL, translationURL]),
                audioOption("translation", kind: .translation, urls: [translationURL])
            ]
        ),
        InteractiveChunk(
            id: "chunk_2220",
            sentences: (0..<10).map { offset in
                .init(
                    id: offset,
                    displayIndex: 2220 + offset,
                    startGate: Double(offset) * 2.0,
                    originalStartGate: Double(offset) * 4.0
                )
            },
            audioOptions: [
                audioOption("combined", kind: .combined, urls: [originalURL, translationURL]),
                audioOption("translation", kind: .translation, urls: [translationURL])
            ]
        ),
        InteractiveChunk(
            id: "chunk_2230",
            sentences: (0..<10).map { offset in
                .init(
                    id: offset,
                    displayIndex: 2230 + offset,
                    startGate: Double(offset) * 2.0,
                    originalStartGate: Double(offset) * 4.0
                )
            },
            audioOptions: [
                audioOption("combined", kind: .combined, urls: [originalURL, translationURL]),
                audioOption("translation", kind: .translation, urls: [translationURL])
            ]
        )
    ]
    requireEqual(
        singleTrackNavigationTarget(
            chunks: dutchOnlyChunks,
            currentChunkID: "chunk_2210",
            currentTime: 18.25,
            track: .translation,
            forward: true
        ),
        .chunkStart(chunkID: "chunk_2220"),
        "Translation-only next sentence at a chunk boundary should advance to the next displayed batch, not skip a batch"
    )
    requireEqual(
        singleTrackNavigationTarget(
            chunks: dutchOnlyChunks,
            currentChunkID: "chunk_2220",
            currentTime: 0.10,
            track: .translation,
            forward: false
        ),
        .chunkEnd(chunkID: "chunk_2210"),
        "Translation-only previous sentence at a chunk boundary should return to the previous displayed batch"
    )
    requireEqual(
        singleTrackNavigationTarget(
            chunks: dutchOnlyChunks,
            currentChunkID: "chunk_2220",
            currentTime: 4.25,
            track: .translation,
            forward: true,
            anchorSentenceNumber: 2222
        ),
        .sentence(chunkID: "chunk_2220", localIndex: 3, startTime: 6.0),
        "Translation-only anchored next sentence should use visible sentence numbers on the active track"
    )
    requireEqual(
        singleTrackNavigationTarget(
            chunks: dutchOnlyChunks,
            currentChunkID: "chunk_2220",
            currentTime: 18.25,
            track: .translation,
            forward: true,
            anchorSentenceNumber: 2225
        ),
        .sentence(chunkID: "chunk_2220", localIndex: 6, startTime: 12.0),
        "Translation-only slider anchor should beat stale end-of-chunk time so next moves one sentence, not one batch"
    )
    let sliderJumpTargetIndex = SentencePositionProvider.targetSentenceIndex(
        in: dutchOnlyChunks[1],
        explicitIndex: nil,
        pendingJump: .init(chunkID: "chunk_2220", sentenceNumber: 2225)
    )
    requireEqual(
        sliderJumpTargetIndex,
        5,
        "Cross-chunk translation-only slider jumps should resolve the visible sentence to the new chunk's local index before audio loads"
    )
    requireEqual(
        sliderJumpTargetIndex.flatMap {
            startTime(in: dutchOnlyChunks[1], at: $0, track: .translation)
        },
        10.0,
        "Cross-chunk translation-only slider jumps should seek to the target sentence gate, not the start of the 10-sentence batch"
    )
}

@main
private struct PlaybackModeSwitchIntegrationCheck {
    static func main() async {
        await MainActor.run {
            runChecks()
        }
    }
}
