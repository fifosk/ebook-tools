import Foundation
import Combine

/// Represents a track type for sequence playback
enum SequenceTrack: String {
    case original
    case translation
}

/// A segment in the sequence playback plan
struct SequenceSegment: Identifiable, Equatable {
    let id = UUID()
    let track: SequenceTrack
    let start: Double
    let end: Double
    let sentenceIndex: Int

    var duration: Double {
        max(end - start, 0)
    }
}

/// Controller for managing per-sentence sequence playback
/// Mirrors the web app's useInteractiveAudioSequence behavior
@MainActor
final class SequencePlaybackController: ObservableObject {
    /// Whether sequence mode is enabled (both original and translation tracks available)
    @Published private(set) var isEnabled = false

    /// The sequence plan containing all segments in playback order
    @Published private(set) var plan: [SequenceSegment] = []

    /// Current active track being played
    @Published var currentTrack: SequenceTrack = .original

    /// Current segment index within the plan
    @Published private(set) var currentSegmentIndex: Int = 0

    /// Whether a track transition is in progress (prevents re-entrant time updates)
    @Published private(set) var isTransitioning = false

    /// Whether the current/recent transition is a same-sentence track switch
    /// This is set when advancing segments and cleared when transition ends
    /// Used by the view layer to show static (fully revealed) display during track switches
    private(set) var isSameSentenceTrackSwitch = false

    /// The expected playback position after a seek (used to validate time updates and for stable highlighting)
    /// This is exposed publicly so that highlightingTime can use it when available, providing a stable
    /// time value right after track transitions end (before audioCoordinator.currentTime settles)
    private(set) var expectedPosition: Double?

    /// Counter for consecutive stale time updates (used to auto-clear expectedPosition)
    private var staleTimeCount: Int = 0

    /// Maximum consecutive stale times before we clear expectedPosition and trust the current time
    private let maxStaleTimeCount: Int = 10

    /// Whether we're waiting for playback to settle after initial load
    private var isSettling: Bool = false

    /// Counter for settling updates (wait for time to stabilize)
    private var settlingCount: Int = 0

    /// Maximum settling updates before we trust the current time
    private let maxSettlingCount: Int = 30

    /// Counter for re-seek attempts (to prevent infinite loops)
    private var reseekAttempts: Int = 0

    /// Maximum re-seek attempts before giving up and accepting stale time
    private let maxReseekAttempts: Int = 3

    /// The URLs for the audio tracks
    private(set) var originalTrackURL: URL?
    private(set) var translationTrackURL: URL?

    /// Callbacks
    var onTrackSwitch: ((SequenceTrack, Double) -> Void)?
    var onSequenceEnded: (() -> Void)?
    /// Called when a re-seek is requested (e.g., after settling timeout due to stale times)
    var onSeekRequest: ((Double) -> Void)?
    /// Called BEFORE a transition begins, allowing the view layer to freeze state synchronously
    var onWillBeginTransition: (() -> Void)?

    /// Build a sequence plan from the chunk's sentences
    /// This mirrors the web app's sequencePlan useMemo logic
    func buildPlan(
        from sentences: [InteractiveChunk.Sentence],
        originalTrackURL: URL?,
        translationTrackURL: URL?,
        originalDuration: Double?,
        translationDuration: Double?
    ) {
        self.originalTrackURL = originalTrackURL
        self.translationTrackURL = translationTrackURL

        var segments: [SequenceSegment] = []
        var hasOriginalGate = false
        var hasTranslationGate = false

        print("[SequencePlayback] Building plan from \(sentences.count) sentences")

        // Build segments from sentence gates
        for (index, sentence) in sentences.enumerated() {
            // Debug: log gate values for first few sentences
            if index < 3 {
                print("[SequencePlayback]   sentence[\(index)] originalGates=\(sentence.originalStartGate.map { String(format: "%.3f", $0) } ?? "nil")...\(sentence.originalEndGate.map { String(format: "%.3f", $0) } ?? "nil"), translationGates=\(sentence.startGate.map { String(format: "%.3f", $0) } ?? "nil")...\(sentence.endGate.map { String(format: "%.3f", $0) } ?? "nil")")
            }

            // Original track segment
            if let originalStart = sentence.originalStartGate,
               let originalEnd = sentence.originalEndGate,
               originalEnd > originalStart {
                hasOriginalGate = true
                segments.append(SequenceSegment(
                    track: .original,
                    start: originalStart,
                    end: originalEnd,
                    sentenceIndex: index
                ))
            }

            // Translation track segment (comes after original in combined mode)
            if let translationStart = sentence.startGate,
               let translationEnd = sentence.endGate,
               translationEnd > translationStart {
                hasTranslationGate = true
                segments.append(SequenceSegment(
                    track: .translation,
                    start: translationStart,
                    end: translationEnd,
                    sentenceIndex: index
                ))
            }
        }

        // Fallback for single-sentence chunks without gate data
        if sentences.count == 1 && (!hasOriginalGate || !hasTranslationGate) {
            if !hasOriginalGate, let duration = originalDuration, duration > 0 {
                segments.insert(SequenceSegment(
                    track: .original,
                    start: 0,
                    end: duration,
                    sentenceIndex: 0
                ), at: 0)
            }
            if !hasTranslationGate, let duration = translationDuration, duration > 0 {
                segments.append(SequenceSegment(
                    track: .translation,
                    start: 0,
                    end: duration,
                    sentenceIndex: 0
                ))
            }
        }

        plan = segments

        // Sequence mode requires both tracks and segments for both
        let hasOriginalSegments = segments.contains { $0.track == .original }
        let hasTranslationSegments = segments.contains { $0.track == .translation }
        isEnabled = originalTrackURL != nil
            && translationTrackURL != nil
            && hasOriginalSegments
            && hasTranslationSegments

        // Reset to beginning
        currentSegmentIndex = 0
        currentTrack = hasOriginalSegments ? .original : .translation

        print("[SequencePlayback] Built plan with \(segments.count) segments, enabled=\(isEnabled)")
        for (i, segment) in segments.enumerated() {
            print("[SequencePlayback]   [\(i)] \(segment.track.rawValue) sentenceIdx=\(segment.sentenceIndex) start=\(String(format: "%.3f", segment.start)) end=\(String(format: "%.3f", segment.end))")
        }
    }

    /// Get the current active URL based on the current track
    var effectiveURL: URL? {
        guard isEnabled else { return translationTrackURL ?? originalTrackURL }
        return currentTrack == .original ? originalTrackURL : translationTrackURL
    }

    /// Get the current segment
    var currentSegment: SequenceSegment? {
        guard plan.indices.contains(currentSegmentIndex) else { return nil }
        return plan[currentSegmentIndex]
    }

    /// Check playback time and advance to next segment if needed
    /// Returns true if a track switch occurred
    func updateForTime(_ time: Double, isPlaying: Bool) -> Bool {
        guard isEnabled, isPlaying, !isTransitioning else { return false }
        guard let segment = currentSegment else { return false }

        let tolerance = 0.1 // 100ms tolerance

        // If we're in settling state after initial load, wait for time to reach near segment start
        if isSettling {
            settlingCount += 1
            // Check if time has settled near the segment start
            if time >= segment.start - tolerance && time <= segment.start + 1.0 {
                print("[SequencePlayback] Settling complete, time=\(String(format: "%.3f", time)) is near segment start \(String(format: "%.3f", segment.start))")
                isSettling = false
                settlingCount = 0
                reseekAttempts = 0
            } else if settlingCount >= maxSettlingCount {
                // Timeout - AVPlayer is still reporting stale times
                isSettling = false
                settlingCount = 0
                // Ensure we're at segment 0
                currentSegmentIndex = 0
                currentTrack = plan.first?.track ?? .original

                reseekAttempts += 1
                if reseekAttempts <= maxReseekAttempts {
                    // Request a re-seek to segment start
                    // Fire pre-transition callback BEFORE setting isTransitioning
                    print("[SequencePlayback] Settling timeout at time=\(String(format: "%.3f", time)), requesting re-seek (attempt \(reseekAttempts)/\(maxReseekAttempts))")
                    onWillBeginTransition?()
                    isTransitioning = true
                    onSeekRequest?(segment.start)
                } else {
                    // Give up - accept that time may be stale but proceed anyway
                    // This prevents infinite loops if AVPlayer never reports correct time
                    print("[SequencePlayback] Max re-seek attempts reached, accepting stale time=\(String(format: "%.3f", time))")
                    expectedPosition = nil
                    reseekAttempts = 0
                }
                return false
            } else {
                // Still settling - don't process time updates yet
                if settlingCount <= 3 {
                    print("[SequencePlayback] Settling (\(settlingCount)/\(maxSettlingCount)), waiting for time to reach \(String(format: "%.3f", segment.start))")
                }
                return false
            }
        }

        // If we have an expected position, validate that we're near it
        // This prevents false triggers from stale time values after track switches
        if let expected = expectedPosition {
            let deviation = abs(time - expected)
            // Also check if time is past the segment end - this catches cases where stale time
            // is close to expected but already past the boundary (e.g., skip back within same segment)
            let isPastSegmentEnd = time >= segment.end - tolerance
            let isBeforeSegmentStart = time < segment.start - tolerance

            if deviation > 1.0 || (isPastSegmentEnd && time > expected + 0.5) || isBeforeSegmentStart {
                // Time is more than 1 second away from expected, or past segment end, or before segment start
                // - likely stale value
                staleTimeCount += 1
                if staleTimeCount >= maxStaleTimeCount {
                    // Too many stale times - the seek may not have worked or AVPlayer is reporting
                    // different time than expected. Clear expected position.
                    print("[SequencePlayback] Clearing expectedPosition after \(staleTimeCount) stale updates, time=\(String(format: "%.3f", time))")
                    expectedPosition = nil
                    staleTimeCount = 0

                    // If we're at the start (segment 0, expected position ~0), this is likely initial load
                    // with stale time from a previous audio file. Enter settling state to wait for
                    // the actual playback time to stabilize.
                    if currentSegmentIndex == 0 && expected < 0.5 {
                        print("[SequencePlayback] Initial load detected, entering settling state")
                        isSettling = true
                        settlingCount = 0
                        return false
                    }

                    // After max stale times, simply trust the current segment index.
                    // The segment was already set correctly by intentional navigation
                    // (skipSentence, seekToSentence, etc). Don't try to recalculate it
                    // from stale time values - that causes jumps to wrong segments.
                    print("[SequencePlayback] Trusting current segment \(currentSegmentIndex) after stale timeout")
                    // Don't advance yet - let the next time update handle it normally
                    return false
                } else {
                    // Still waiting for valid time
                    if staleTimeCount <= 3 {
                        print("[SequencePlayback] Ignoring stale time \(String(format: "%.3f", time)), expected ~\(String(format: "%.3f", expected)), segment=\(segment.start)-\(segment.end) (\(staleTimeCount)/\(maxStaleTimeCount))")
                    }
                    return false
                }
            } else {
                // Clear expected position once we've seen a reasonable time value
                expectedPosition = nil
                staleTimeCount = 0
            }
        }

        // Check if we've reached the end of the current segment
        if time >= segment.end - tolerance {
            print("[SequencePlayback] Time \(String(format: "%.3f", time)) >= segment[\(currentSegmentIndex)] end \(String(format: "%.3f", segment.end)) - triggering advance")
            return advanceToNextSegment()
        }

        return false
    }

    /// Find the segment index that contains the given time for the specified track
    private func findSegmentIndex(forTime time: Double, track: SequenceTrack) -> Int? {
        // Find the last segment of the current track that starts before or at the given time
        var bestIndex: Int? = nil
        for (index, segment) in plan.enumerated() {
            if segment.track == track && time >= segment.start {
                bestIndex = index
            }
        }
        return bestIndex
    }

    /// Mark transition as started (call before switching tracks)
    func beginTransition() {
        isTransitioning = true
        print("[SequencePlayback] Transition started")
    }

    /// Mark transition as completed (call after audio is loaded and ready)
    /// - Parameter expectedTime: The expected playback position after the seek
    func endTransition(expectedTime: Double? = nil) {
        expectedPosition = expectedTime
        staleTimeCount = 0
        isSettling = false
        settlingCount = 0
        reseekAttempts = 0
        // NOTE: We intentionally do NOT clear isSameSentenceTrackSwitch here.
        // The flag persists briefly after transition ends so the view can still
        // show static display until the next segment advance clears it.
        // This covers the window between transition end and audio settling.
        let sameSentenceSwitch = isSameSentenceTrackSwitch
        isTransitioning = false
        print("[SequencePlayback] Transition ended, expectedPosition=\(expectedTime.map { String(format: "%.3f", $0) } ?? "nil"), sameSentenceSwitch=\(sameSentenceSwitch)")
    }

    /// Advance to the next segment in the plan
    /// Returns true if a track switch occurred
    @discardableResult
    func advanceToNextSegment() -> Bool {
        // Clear the previous same-sentence flag immediately to prevent it from
        // affecting renders during the next transition
        isSameSentenceTrackSwitch = false

        let nextIndex = currentSegmentIndex + 1

        if nextIndex >= plan.count {
            // End of sequence
            print("[SequencePlayback] End of sequence reached")
            onSequenceEnded?()
            return false
        }

        let nextSegment = plan[nextIndex]
        let previousTrack = currentTrack
        let previousSentenceIndex = currentSegment?.sentenceIndex
        let didSwitchTrack = previousTrack != nextSegment.track

        // Detect same-sentence track switch (for view layer to show static display)
        let isSameSentence = previousSentenceIndex == nextSegment.sentenceIndex
        isSameSentenceTrackSwitch = didSwitchTrack && isSameSentence

        if didSwitchTrack {
            // Call onWillBeginTransition BEFORE updating any state
            // This allows the view layer to capture/freeze the current state synchronously
            print("[SequencePlayback] Calling onWillBeginTransition BEFORE state change (current segment=\(currentSegmentIndex)), sameSentenceSwitch=\(isSameSentenceTrackSwitch)")
            onWillBeginTransition?()

            // Block further time updates IMMEDIATELY
            // This prevents stale time values from triggering additional advances
            isTransitioning = true
        }

        // NOW update the state after callback has had a chance to capture the old state
        currentSegmentIndex = nextIndex
        currentTrack = nextSegment.track

        print("[SequencePlayback] Advancing to segment \(nextIndex): \(nextSegment.track.rawValue) at \(String(format: "%.3f", nextSegment.start)), transitioning=\(isTransitioning), sameSentenceSwitch=\(isSameSentenceTrackSwitch)")

        if didSwitchTrack {
            onTrackSwitch?(nextSegment.track, nextSegment.start)
        }

        return didSwitchTrack
    }

    /// Find the segment at a given time and track
    func findSegment(at time: Double, for track: SequenceTrack) -> SequenceSegment? {
        let tolerance = 0.05
        return plan.first { segment in
            segment.track == track && time >= segment.start - tolerance && time <= segment.end + tolerance
        }
    }

    /// Find the segment index for a given sentence and track
    func findSegmentIndex(sentenceIndex: Int, track: SequenceTrack) -> Int? {
        plan.firstIndex { $0.sentenceIndex == sentenceIndex && $0.track == track }
    }

    /// Seek to a specific sentence, optionally preferring a specific track
    /// - Parameters:
    ///   - sentenceIndex: The sentence index to seek to
    ///   - preferredTrack: The preferred track based on visibility settings. If nil, defaults to original.
    /// - Returns: The track and time to seek to, or nil if not found
    func seekToSentence(_ sentenceIndex: Int, preferredTrack: SequenceTrack? = nil) -> (track: SequenceTrack, time: Double)? {
        guard let target = findSentenceTarget(sentenceIndex, preferredTrack: preferredTrack) else {
            return nil
        }
        currentSegmentIndex = target.segmentIndex
        currentTrack = target.track
        return (target.track, target.time)
    }

    /// Find the target segment for a sentence without updating state
    /// This is used when we need to fire callbacks BEFORE updating state
    func findSentenceTarget(_ sentenceIndex: Int, preferredTrack: SequenceTrack? = nil) -> (segmentIndex: Int, track: SequenceTrack, time: Double)? {
        let preferred = preferredTrack ?? .original
        let fallback: SequenceTrack = preferred == .original ? .translation : .original

        // First try to find the preferred track segment for this sentence
        if let index = findSegmentIndex(sentenceIndex: sentenceIndex, track: preferred) {
            return (index, preferred, plan[index].start)
        }
        // Fall back to the other track
        if let index = findSegmentIndex(sentenceIndex: sentenceIndex, track: fallback) {
            return (index, fallback, plan[index].start)
        }
        return nil
    }

    /// Commit a state change for a previously found sentence target
    func commitSentenceTarget(_ target: (segmentIndex: Int, track: SequenceTrack, time: Double)) {
        currentSegmentIndex = target.segmentIndex
        currentTrack = target.track
    }

    /// Get the current sentence index from the current segment
    var currentSentenceIndex: Int? {
        currentSegment?.sentenceIndex
    }

    /// Get all unique sentence indices in the plan, sorted
    var sentenceIndices: [Int] {
        Array(Set(plan.map { $0.sentenceIndex })).sorted()
    }

    /// Navigate to the next sentence (skips track changes within the same sentence)
    /// NOTE: This method updates state immediately. Use nextSentenceTarget() if you need to
    /// fire callbacks before updating state.
    /// - Parameter preferredTrack: The preferred track based on visibility settings. If nil, uses current track.
    /// - Returns: The track and time to seek to, or nil if at the last sentence
    func nextSentence(preferredTrack: SequenceTrack? = nil) -> (track: SequenceTrack, time: Double)? {
        guard let target = nextSentenceTarget(preferredTrack: preferredTrack) else { return nil }
        commitSentenceTarget(target)
        return (target.track, target.time)
    }

    /// Find the next sentence target without updating state
    func nextSentenceTarget(preferredTrack: SequenceTrack? = nil) -> (segmentIndex: Int, track: SequenceTrack, time: Double)? {
        guard let currentIdx = currentSentenceIndex else { return nil }
        let indices = sentenceIndices
        guard let currentPos = indices.firstIndex(of: currentIdx) else { return nil }
        let nextPos = currentPos + 1
        guard nextPos < indices.count else { return nil }
        return findSentenceTarget(indices[nextPos], preferredTrack: preferredTrack ?? currentTrack)
    }

    /// Navigate to the previous sentence (skips track changes within the same sentence)
    /// NOTE: This method updates state immediately. Use previousSentenceTarget() if you need to
    /// fire callbacks before updating state.
    /// - Parameter preferredTrack: The preferred track based on visibility settings. If nil, uses current track.
    /// - Returns: The track and time to seek to, or nil if at the first sentence
    func previousSentence(preferredTrack: SequenceTrack? = nil) -> (track: SequenceTrack, time: Double)? {
        guard let target = previousSentenceTarget(preferredTrack: preferredTrack) else { return nil }
        commitSentenceTarget(target)
        return (target.track, target.time)
    }

    /// Find the previous sentence target without updating state
    func previousSentenceTarget(preferredTrack: SequenceTrack? = nil) -> (segmentIndex: Int, track: SequenceTrack, time: Double)? {
        guard let currentIdx = currentSentenceIndex else { return nil }
        let indices = sentenceIndices
        guard let currentPos = indices.firstIndex(of: currentIdx) else { return nil }
        let prevPos = currentPos - 1
        guard prevPos >= 0 else { return nil }
        return findSentenceTarget(indices[prevPos], preferredTrack: preferredTrack ?? currentTrack)
    }

    /// Reset the controller state
    func reset() {
        isEnabled = false
        isTransitioning = false
        isSameSentenceTrackSwitch = false
        expectedPosition = nil
        staleTimeCount = 0
        isSettling = false
        settlingCount = 0
        reseekAttempts = 0
        plan = []
        currentSegmentIndex = 0
        currentTrack = .original
        originalTrackURL = nil
        translationTrackURL = nil
    }
}
