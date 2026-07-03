import Darwin
import Foundation

enum AudioMode: Equatable {
    case singleTrack(SequenceTrack)
    case sequence

    var description: String {
        switch self {
        case .singleTrack(let track):
            return "singleTrack(\(track.rawValue))"
        case .sequence:
            return "sequence"
        }
    }
}

struct ChunkSentencePhaseDurations {
    let original: Double?
    let translation: Double?
    let gap: Double?
    let tail: Double?
}

struct InteractiveChunk {
    struct Sentence {
        let phaseDurations: ChunkSentencePhaseDurations?
        let totalDuration: Double?
        let startGate: Double?
        let endGate: Double?
        let originalStartGate: Double?
        let originalEndGate: Double?
    }
}

@MainActor
private func fail(_ message: String) -> Never {
    fputs("Sequence pause cancellation check failed: \(message)\n", stderr)
    exit(1)
}

@MainActor
private func requireEqual<T: Equatable>(_ actual: T, _ expected: T, _ message: String) {
    if actual != expected {
        fail("\(message). Expected \(expected), got \(actual).")
    }
}

@MainActor
private func requireClose(_ actual: Double?, _ expected: Double, _ message: String) {
    guard let actual, abs(actual - expected) <= 0.000_001 else {
        fail("\(message). Expected \(expected), got \(String(describing: actual)).")
    }
}

@MainActor
private func requireTrue(_ value: Bool, _ message: String) {
    if !value {
        fail(message)
    }
}

private func sentence(
    originalStart: Double,
    originalEnd: Double,
    translationStart: Double,
    translationEnd: Double
) -> InteractiveChunk.Sentence {
    InteractiveChunk.Sentence(
        phaseDurations: nil,
        totalDuration: nil,
        startGate: translationStart,
        endGate: translationEnd,
        originalStartGate: originalStart,
        originalEndGate: originalEnd
    )
}

@MainActor
private func configuredController() -> SequencePlaybackController {
    let controller = SequencePlaybackController()
    controller.buildPlan(
        from: [
            sentence(originalStart: 0.0, originalEnd: 1.0, translationStart: 0.0, translationEnd: 1.0),
            sentence(originalStart: 1.0, originalEnd: 2.0, translationStart: 1.0, translationEnd: 2.0)
        ],
        originalTrackURL: URL(fileURLWithPath: "/tmp/original.m4a"),
        translationTrackURL: URL(fileURLWithPath: "/tmp/translation.m4a"),
        originalDuration: nil,
        translationDuration: nil,
        mode: .sequence
    )
    requireTrue(controller.isEnabled, "Controller should enable sequence mode with both tracks")
    requireEqual(controller.currentSegmentIndex, 0, "Initial segment index")
    requireEqual(controller.currentTrack, .original, "Initial track")
    return controller
}

@MainActor
private func runDwellCancellationCheck() async {
    let controller = configuredController()
    var dwellPauseCount = 0
    var cleanupCount = 0
    var trackSwitchCount = 0
    var resumeAfterDwellCount = 0
    var dwellPinTime: Double?
    var shouldDetachCurrentItem: Bool?

    controller.onPauseForDwell = { pinTime, detachCurrentItem in
        dwellPauseCount += 1
        dwellPinTime = pinTime
        shouldDetachCurrentItem = detachCurrentItem
    }
    controller.onCleanupAudioEffects = { cleanupCount += 1 }
    controller.onTrackSwitch = { _, _ in trackSwitchCount += 1 }
    controller.onResumeAfterDwell = { _ in resumeAfterDwellCount += 1 }

    controller.boundaryReached()
    requireEqual(dwellPauseCount, 1, "Boundary should enter dwell and pause audio")
    requireClose(
        dwellPinTime,
        0.828,
        "Boundary pause should never pin after the early boundary handoff point"
    )
    requireEqual(
        shouldDetachCurrentItem,
        true,
        "Cross-track dwell should detach the outgoing AVPlayer item"
    )
    requireTrue(controller.isDwelling, "Boundary should put the controller into dwell state")

    controller.cancelPendingAutomaticAdvanceForPause()
    requireEqual(cleanupCount, 1, "Pause cancellation should clean up boundary/fade audio effects")
    requireTrue(!controller.isDwelling, "Pause cancellation should leave dwell state")
    requireTrue(!controller.isTransitioning, "Pause cancellation should not leave transition state active")

    try? await Task.sleep(nanoseconds: 400_000_000)

    requireEqual(controller.currentSegmentIndex, 0, "Cancelled dwell should not advance after its timer fires")
    requireEqual(controller.currentTrack, .original, "Cancelled dwell should keep the current track")
    requireEqual(trackSwitchCount, 0, "Cancelled dwell should not switch tracks")
    requireEqual(resumeAfterDwellCount, 0, "Cancelled dwell should not resume after dwell")
}

@MainActor
private func runTransitionCancellationCheck() {
    let controller = configuredController()
    var cleanupCount = 0
    controller.onCleanupAudioEffects = { cleanupCount += 1 }

    controller.beginTransition()
    requireTrue(controller.isTransitioning, "beginTransition should enter transition state")
    controller.cancelPendingAutomaticAdvanceForPause()

    requireTrue(!controller.isTransitioning, "Pause cancellation should clear an in-flight transition")
    requireEqual(controller.currentSegmentIndex, 0, "Transition cancellation should preserve segment")
    requireEqual(controller.currentTrack, .original, "Transition cancellation should preserve track")
    requireEqual(cleanupCount, 1, "Transition cancellation should clean up audio effects")
}

@MainActor
private func runReaderTransportPauseCancellationCheck() {
    let controller = configuredController()
    var cleanupCount = 0
    controller.onCleanupAudioEffects = { cleanupCount += 1 }

    controller.beginTransition()
    requireTrue(controller.isTransitioning, "beginTransition should enter transition state before reader pause")
    controller.cancelPendingAutomaticAdvanceForReaderTransportPause()

    requireTrue(!controller.isTransitioning, "Reader transport pause should clear an in-flight transition")
    requireTrue(!controller.isDwelling, "Reader transport pause should clear dwell state")
    requireEqual(controller.currentSegmentIndex, 0, "Reader transport pause should preserve segment")
    requireEqual(controller.currentTrack, .original, "Reader transport pause should preserve track")
    requireEqual(cleanupCount, 1, "Reader transport pause should clean up audio effects")
}

@MainActor
private func runSingleTrackPlanInitialLaneCheck() {
    let controller = SequencePlaybackController()
    controller.buildPlan(
        from: [
            sentence(originalStart: 0.0, originalEnd: 1.0, translationStart: 0.0, translationEnd: 1.0),
            sentence(originalStart: 1.0, originalEnd: 2.0, translationStart: 1.0, translationEnd: 2.0)
        ],
        originalTrackURL: URL(fileURLWithPath: "/tmp/original.m4a"),
        translationTrackURL: URL(fileURLWithPath: "/tmp/translation.m4a"),
        originalDuration: nil,
        translationDuration: nil,
        mode: .singleTrack(.translation)
    )

    requireTrue(!controller.isEnabled, "Translation-only plan should not enable sequence mode")
    requireEqual(
        controller.currentTrack,
        .translation,
        "Translation-only plan should keep the disabled sequence state on the selected lane"
    )
    requireEqual(
        controller.currentSegmentIndex,
        1,
        "Translation-only plan should point at the first translation segment, not the first original segment"
    )
    requireEqual(
        controller.currentSegment?.sentenceIndex,
        0,
        "Translation-only plan should still begin at the first sentence"
    )
}

@MainActor
private func runOverlappingGateTrimCheck() {
    let controller = SequencePlaybackController()
    controller.buildPlan(
        from: [
            sentence(originalStart: 0.0, originalEnd: 2.25, translationStart: 0.0, translationEnd: 1.35),
            sentence(originalStart: 2.0, originalEnd: 3.0, translationStart: 1.2, translationEnd: 2.2)
        ],
        originalTrackURL: URL(fileURLWithPath: "/tmp/original.m4a"),
        translationTrackURL: URL(fileURLWithPath: "/tmp/translation.m4a"),
        originalDuration: nil,
        translationDuration: nil,
        mode: .sequence
    )

    let firstOriginal = controller.plan.first { $0.track == .original && $0.sentenceIndex == 0 }
    let firstTranslation = controller.plan.first { $0.track == .translation && $0.sentenceIndex == 0 }
    requireClose(
        firstOriginal?.end,
        1.92,
        "Original segment should end just before the next original start when gates overlap"
    )
    requireClose(
        firstTranslation?.end,
        1.12,
        "Translation segment should end just before the next translation start when gates overlap"
    )
}

@MainActor
private func runTightAdjacentGateTrimCheck() {
    let controller = SequencePlaybackController()
    controller.buildPlan(
        from: [
            sentence(originalStart: 0.0, originalEnd: 2.0, translationStart: 0.0, translationEnd: 1.2),
            sentence(originalStart: 2.0, originalEnd: 3.0, translationStart: 1.2, translationEnd: 2.2)
        ],
        originalTrackURL: URL(fileURLWithPath: "/tmp/original.m4a"),
        translationTrackURL: URL(fileURLWithPath: "/tmp/translation.m4a"),
        originalDuration: nil,
        translationDuration: nil,
        mode: .sequence
    )

    let firstOriginal = controller.plan.first { $0.track == .original && $0.sentenceIndex == 0 }
    let firstTranslation = controller.plan.first { $0.track == .translation && $0.sentenceIndex == 0 }
    requireClose(
        firstOriginal?.end,
        1.92,
        "Original segment should trim tightly adjacent gates before possible next-sentence preroll"
    )
    requireClose(
        firstTranslation?.end,
        1.12,
        "Translation segment should trim tightly adjacent gates before possible next-sentence preroll"
    )
}

@MainActor
private func runWideGapGateTrimCheck() {
    let controller = SequencePlaybackController()
    controller.buildPlan(
        from: [
            sentence(originalStart: 0.0, originalEnd: 1.85, translationStart: 0.0, translationEnd: 1.05),
            sentence(originalStart: 2.0, originalEnd: 3.0, translationStart: 1.2, translationEnd: 2.2)
        ],
        originalTrackURL: URL(fileURLWithPath: "/tmp/original.m4a"),
        translationTrackURL: URL(fileURLWithPath: "/tmp/translation.m4a"),
        originalDuration: nil,
        translationDuration: nil,
        mode: .sequence
    )

    let firstOriginal = controller.plan.first { $0.track == .original && $0.sentenceIndex == 0 }
    let firstTranslation = controller.plan.first { $0.track == .translation && $0.sentenceIndex == 0 }
    requireEqual(
        firstOriginal?.end,
        Optional(1.85),
        "Original segment should keep wider non-overlapping gates intact"
    )
    requireEqual(
        firstTranslation?.end,
        Optional(1.05),
        "Translation segment should keep wider non-overlapping gates intact"
    )
}

@main
struct SequencePauseCancelCheck {
    @MainActor
    static func main() async {
        await runDwellCancellationCheck()
        runTransitionCancellationCheck()
        runReaderTransportPauseCancellationCheck()
        runSingleTrackPlanInitialLaneCheck()
        runOverlappingGateTrimCheck()
        runTightAdjacentGateTrimCheck()
        runWideGapGateTrimCheck()
    }
}
