import Foundation

/// A dedicated helper for determining the current sentence position regardless of playback mode.
/// This centralizes the logic for finding the current sentence index, which is needed when:
/// - Toggling audio tracks (switching between sequence and single-track modes)
/// - Resuming playback after pause
/// - Seeking within a chunk
///
/// The provider uses multiple strategies in priority order:
/// 1. Sequence controller (if sequence mode is active)
/// 2. Transcript display state (most reliable for UI consistency)
/// 3. Time-based lookup (fallback)
@MainActor
struct SentencePositionProvider {
    /// The sequence controller for sequence mode position
    let sequenceController: SequencePlaybackController

    /// Callback to get the transcript display sentence index
    let transcriptDisplayIndex: () -> Int?

    /// Callback to get sentence index from playback time
    let timeBasedIndex: () -> Int?

    /// Result of sentence position lookup
    struct Result {
        let index: Int
        let strategy: Strategy

        enum Strategy: String {
            case sequenceController = "sequenceController"
            case transcriptDisplay = "transcriptDisplay"
            case timeBased = "timeBased"
            case none = "none"
        }
    }

    /// Get the current sentence index using the best available strategy
    func currentSentenceIndex() -> Result? {
        // Strategy 1: From sequence controller (only valid if sequence mode is active)
        if sequenceController.isEnabled, let seqIndex = sequenceController.currentSentenceIndex {
            return Result(index: seqIndex, strategy: .sequenceController)
        }

        // Strategy 2: From transcript display (most reliable for UI state)
        if let displayIndex = transcriptDisplayIndex() {
            return Result(index: displayIndex, strategy: .transcriptDisplay)
        }

        // Strategy 3: Time-based lookup (fallback)
        if let timeIndex = timeBasedIndex() {
            return Result(index: timeIndex, strategy: .timeBased)
        }

        return nil
    }

    /// Get just the index value, or nil if not found
    var index: Int? {
        currentSentenceIndex()?.index
    }
}

/// Extension to create a SentencePositionProvider from a view context
extension SentencePositionProvider {
    /// Create a provider that uses the given closures for lookup
    /// This is the preferred way to create a provider from InteractivePlayerView
    static func from(
        sequenceController: SequencePlaybackController,
        transcriptDisplayIndex: @escaping () -> Int?,
        timeBasedIndex: @escaping () -> Int?
    ) -> SentencePositionProvider {
        SentencePositionProvider(
            sequenceController: sequenceController,
            transcriptDisplayIndex: transcriptDisplayIndex,
            timeBasedIndex: timeBasedIndex
        )
    }
}
