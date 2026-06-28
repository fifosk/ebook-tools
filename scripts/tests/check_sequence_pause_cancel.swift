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

    controller.onPauseForDwell = { dwellPauseCount += 1 }
    controller.onCleanupAudioEffects = { cleanupCount += 1 }
    controller.onTrackSwitch = { _, _ in trackSwitchCount += 1 }
    controller.onResumeAfterDwell = { _ in resumeAfterDwellCount += 1 }

    controller.boundaryReached()
    requireEqual(dwellPauseCount, 1, "Boundary should enter dwell and pause audio")
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

@main
struct SequencePauseCancelCheck {
    @MainActor
    static func main() async {
        await runDwellCancellationCheck()
        runTransitionCancellationCheck()
    }
}
