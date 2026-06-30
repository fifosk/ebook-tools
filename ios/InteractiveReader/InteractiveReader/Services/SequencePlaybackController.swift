import Foundation
import Combine
import OSLog

private let sequencePlaybackLogger = Logger(subsystem: "InteractiveReader", category: "SequencePlayback")

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

// MARK: - PlaybackPhase State Machine

/// Explicit state machine phases for sequence playback.
/// Replaces the implicit state encoded in multiple boolean flags and counters.
private enum PlaybackPhase: CustomStringConvertible {
    case idle
    case playing
    case dwelling(startedAt: Date)
    case transitioning
    case validating(Validation)

    struct Validation: Equatable {
        let expectedPosition: Double
        var staleTimeCount: Int = 0         // ≥maxStaleTimeCount → clear or enter settling
        var settlingCount: Int = 0          // ≥maxSettlingCount → re-seek or give up
        var reseekAttempts: Int = 0         // ≥maxReseekAttempts → accept stale time
        var isSettling: Bool = false        // Substate: waiting for AVPlayer time to reach expected position
    }

    var description: String {
        switch self {
        case .idle: return "idle"
        case .playing: return "playing"
        case .dwelling: return "dwelling"
        case .transitioning: return "transitioning"
        case .validating(let v):
            if v.isSettling {
                return "validating(settling:\(v.settlingCount) reseek:\(v.reseekAttempts))"
            }
            return "validating(stale:\(v.staleTimeCount) expected:\(String(format: "%.3f", v.expectedPosition)))"
        }
    }
}

/// Controller for managing per-sentence sequence playback
/// Mirrors the web app's useInteractiveAudioSequence behavior
@MainActor
final class SequencePlaybackController: ObservableObject {
    /// Set to true to enable verbose sequence playback logging
    private static let debug = false

    private func debugLog(_ message: String) {
        guard Self.debug else { return }
        sequencePlaybackLogger.debug("\(message, privacy: .public)")
    }

    private func logBoundary(_ message: String) {
        sequencePlaybackLogger.debug("\(message, privacy: .public)")
    }

    // MARK: - Published State (observed by SwiftUI / Combine)

    /// Whether sequence mode is enabled (both original and translation tracks available)
    @Published private(set) var isEnabled = false {
        didSet {
            if oldValue != isEnabled {
                debugLog("isEnabled changed: \(oldValue) -> \(isEnabled)")
            }
        }
    }

    /// The sequence plan containing all segments in playback order
    @Published private(set) var plan: [SequenceSegment] = []

    /// Current active track being played
    @Published var currentTrack: SequenceTrack = .original

    /// Current segment index within the plan
    @Published private(set) var currentSegmentIndex: Int = 0

    /// Whether a track transition is in progress (prevents re-entrant time updates).
    /// Kept as stored @Published because ViewModel subscribes via `$isTransitioning`.
    /// Synchronized from `phase.didSet`.
    @Published private(set) var isTransitioning = false

    /// Whether we're currently dwelling at segment end (exposed for view layer to avoid time-based lookup).
    /// Kept as stored @Published for SwiftUI observation.
    /// Synchronized from `phase.didSet`.
    @Published private(set) var isDwelling: Bool = false

    // MARK: - Phase State Machine

    /// The single source of truth for playback state.
    /// Published properties `isTransitioning` and `isDwelling` are synchronized in `didSet`.
    private var phase: PlaybackPhase = .idle {
        didSet {
            // Sync published properties from phase
            let newIsTransitioning: Bool
            if case .transitioning = phase { newIsTransitioning = true } else { newIsTransitioning = false }
            let newIsDwelling: Bool
            if case .dwelling = phase { newIsDwelling = true } else { newIsDwelling = false }

            if isTransitioning != newIsTransitioning {
                isTransitioning = newIsTransitioning
            }
            if isDwelling != newIsDwelling {
                isDwelling = newIsDwelling
            }

            if "\(oldValue)" != "\(phase)" {
                debugLog("Phase: \(oldValue) -> \(phase)")
            }
        }
    }

    // MARK: - Transition Metadata (not part of phase)

    /// Whether the current/recent transition is a same-sentence track switch.
    /// This is sticky metadata — set during advanceToNextSegment, cleared at next transition start.
    /// Used by the view layer to show static (fully revealed) display during track switches.
    private(set) var isSameSentenceTrackSwitch = false

    /// The expected playback position after a seek (used to validate time updates and for stable highlighting).
    /// Computed from phase — non-nil only in `.validating` state.
    var expectedPosition: Double? {
        if case .validating(let state) = phase {
            return state.expectedPosition
        }
        return nil
    }

    // MARK: - Dwell Support

    /// Duration to dwell at segment end to ensure last word highlight is visible (seconds)
    private let segmentEndDwellDuration: TimeInterval = 0.25

    /// Work item for scheduled dwell completion (since time observer stops when player is paused).
    /// Kept as separate stored property because it needs cancellation from multiple call sites.
    private var dwellWorkItem: DispatchWorkItem?

    // MARK: - Validation Constants

    /// Maximum consecutive stale times before we clear expectedPosition and trust the current time
    private let maxStaleTimeCount: Int = 10

    /// Maximum settling updates before we trust the current time
    private let maxSettlingCount: Int = 30

    /// Maximum re-seek attempts before giving up and accepting stale time
    private let maxReseekAttempts: Int = 3

    // MARK: - Audio Track State

    /// The URLs for the audio tracks
    private(set) var originalTrackURL: URL?
    private(set) var translationTrackURL: URL?

    // MARK: - Callbacks

    var onTrackSwitch: ((SequenceTrack, Double) -> Void)?
    var onSequenceEnded: (() -> Void)?
    /// Called when a re-seek is requested (e.g., after settling timeout due to stale times)
    var onSeekRequest: ((Double) -> Void)?
    /// Called BEFORE a transition begins, allowing the view layer to freeze state synchronously
    var onWillBeginTransition: (() -> Void)?
    /// Called when segment end is reached to pause audio during dwell period.
    /// Carries the active segment end so the audio player can pin the muted
    /// playhead at the intended boundary on output-buffer-heavy devices.
    /// This prevents audio bleed from the next sentence
    var onPauseForDwell: ((Double?) -> Void)?
    /// Called after dwell completes to resume playback for same-track advances
    /// (track switches resume via onTrackSwitch callback instead)
    var onResumeAfterDwell: ((Double) -> Void)?
    /// Called when time has stabilized after a transition (expectedPosition cleared)
    /// This signals the view layer to clear any transition-related state
    var onTimeStabilized: (() -> Void)?
    /// Called when a new segment becomes active, providing the segment end time
    /// for installing a precise boundary time observer on the AVPlayer.
    /// This replaces polling-based segment-end detection to prevent audio bleed.
    var onInstallBoundary: ((Double) -> Void)?
    /// Called to apply a decode-level fade-out on the current audio item.
    /// Parameters: (fadeStartTime, fadeEndTime) in seconds within the audio file.
    /// This prevents audio bleed through HDMI output buffers.
    var onApplySegmentFade: ((Double, Double) -> Void)?
    /// Called when the controller resets, to clear fade mix and boundary observer
    /// from the audio player (prevents stale fade-outs silencing audio in non-sequence modes).
    var onCleanupAudioEffects: (() -> Void)?

    /// Called to check if a track should be skipped during automatic playback progression
    /// Returns true if the track should be skipped (e.g., because it's hidden in the UI)
    var shouldSkipTrack: ((SequenceTrack) -> Bool)?

    // MARK: - Audio Mode

    /// The current audio mode (set by the View layer from AudioModeManager)
    /// This determines whether sequence mode is enabled and which tracks are active
    var audioMode: AudioMode = .sequence {
        didSet {
            if oldValue != audioMode {
                debugLog("audioMode changed: \(oldValue.description) -> \(audioMode.description)")
            }
        }
    }

    /// Whether original audio is enabled (computed from audioMode)
    var isOriginalAudioEnabled: Bool {
        switch audioMode {
        case .sequence:
            return true
        case .singleTrack(let track):
            return track == .original
        }
    }

    /// Whether translation audio is enabled (computed from audioMode)
    var isTranslationAudioEnabled: Bool {
        switch audioMode {
        case .sequence:
            return true
        case .singleTrack(let track):
            return track == .translation
        }
    }

    // MARK: - Plan Building

    /// Build a sequence plan from the chunk's sentences
    /// This mirrors the web app's sequencePlan useMemo logic
    /// - Parameters:
    ///   - sentences: The sentences to build the plan from
    ///   - originalTrackURL: URL for the original audio track
    ///   - translationTrackURL: URL for the translation audio track
    ///   - originalDuration: Duration of the original track (fallback for single-sentence chunks)
    ///   - translationDuration: Duration of the translation track (fallback for single-sentence chunks)
    ///   - mode: The audio mode determining whether sequence mode is enabled (defaults to current audioMode)
    func buildPlan(
        from sentences: [InteractiveChunk.Sentence],
        originalTrackURL: URL?,
        translationTrackURL: URL?,
        originalDuration: Double?,
        translationDuration: Double?,
        mode: AudioMode? = nil
    ) {
        // Update audioMode if provided
        if let mode {
            self.audioMode = mode
        }
        self.originalTrackURL = originalTrackURL
        self.translationTrackURL = translationTrackURL

        var segments: [SequenceSegment] = []
        var hasOriginalSegment = false
        var hasTranslationSegment = false
        var origCursor = 0.0
        var transCursor = 0.0

        // Build segments from sentence gates, falling back to per-sentence
        // phase durations only when that sentence is missing a gate.
        for (index, sentence) in sentences.enumerated() {
            let origDur = sentence.phaseDurations?.original ?? 0
            let transDur = sentence.phaseDurations?.translation
                ?? sentence.totalDuration ?? 0

            // Original track segment
            if let originalStart = sentence.originalStartGate,
               let originalEnd = sentence.originalEndGate,
               originalEnd > originalStart {
                hasOriginalSegment = true
                segments.append(SequenceSegment(
                    track: .original,
                    start: originalStart,
                    end: originalEnd,
                    sentenceIndex: index
                ))
                origCursor = originalEnd
            } else if origDur > 0 {
                hasOriginalSegment = true
                segments.append(SequenceSegment(
                    track: .original,
                    start: origCursor,
                    end: origCursor + origDur,
                    sentenceIndex: index
                ))
                origCursor += origDur
            }

            // Translation track segment (comes after original in combined mode)
            if let translationStart = sentence.startGate,
               let translationEnd = sentence.endGate,
               translationEnd > translationStart {
                hasTranslationSegment = true
                segments.append(SequenceSegment(
                    track: .translation,
                    start: translationStart,
                    end: translationEnd,
                    sentenceIndex: index
                ))
                transCursor = translationEnd
            } else if transDur > 0 {
                hasTranslationSegment = true
                segments.append(SequenceSegment(
                    track: .translation,
                    start: transCursor,
                    end: transCursor + transDur,
                    sentenceIndex: index
                ))
                transCursor += transDur
            }
        }

        // Fallback for single-sentence chunks without gate data
        if sentences.count == 1 && (!hasOriginalSegment || !hasTranslationSegment) {
            if !hasOriginalSegment, let duration = originalDuration, duration > 0 {
                segments.insert(SequenceSegment(
                    track: .original,
                    start: 0,
                    end: duration,
                    sentenceIndex: 0
                ), at: 0)
            }
            if !hasTranslationSegment, let duration = translationDuration, duration > 0 {
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
        // AND both audio toggles must be enabled (matching Web UI behavior)
        let hasOriginalSegments = segments.contains { $0.track == .original }
        let hasTranslationSegments = segments.contains { $0.track == .translation }
        let bothTogglesEnabled = isOriginalAudioEnabled && isTranslationAudioEnabled
        isEnabled = originalTrackURL != nil
            && translationTrackURL != nil
            && hasOriginalSegments
            && hasTranslationSegments
            && bothTogglesEnabled

        // Reset to beginning
        currentSegmentIndex = 0
        currentTrack = hasOriginalSegments ? .original : .translation
        phase = isEnabled ? .playing : .idle

        // Install boundary observer for the first segment
        if isEnabled {
            installBoundaryForCurrentSegment()
        }

        debugLog("Plan: \(segments.count) segs, enabled=\(isEnabled), origToggle=\(isOriginalAudioEnabled), transToggle=\(isTranslationAudioEnabled)")
    }

    // MARK: - Computed Properties

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

    /// Get the next segment (if any)
    var nextSegment: SequenceSegment? {
        let nextIndex = currentSegmentIndex + 1
        guard plan.indices.contains(nextIndex) else { return nil }
        return plan[nextIndex]
    }

    // MARK: - Boundary Observer

    /// Install a boundary observer for the current segment's end time.
    /// Called whenever a new segment becomes the active playback segment.
    /// How far before segment.end to place the boundary observer (seconds).
    private var boundaryHeadroom: Double {
        #if os(tvOS)
        return 0.18
        #else
        return 0.05
        #endif
    }

    /// Duration of the fade-out ramp applied at the decode level (seconds).
    /// This must be long enough to cover HDMI output buffer depth (~100-200ms).
    private let fadeOutDuration: Double = 0.20

    private func installBoundaryForCurrentSegment() {
        guard let segment = currentSegment else { return }
        // Install boundary slightly before segment end to beat HDMI buffer latency.
        let boundaryTime = max(segment.start + 0.01, segment.end - boundaryHeadroom)
        logBoundary("Installing boundary at \(String(format: "%.3f", boundaryTime)) (end=\(String(format: "%.3f", segment.end))) for seg[\(currentSegmentIndex)] \(segment.track.rawValue)")
        onInstallBoundary?(boundaryTime)

        // Apply decode-level fade-out to guarantee silence at segment boundary,
        // regardless of HDMI/Core Audio output buffer depth.
        let fadeStart = max(segment.start + 0.01, segment.end - fadeOutDuration)
        onApplySegmentFade?(fadeStart, segment.end)
    }

    /// Called by the view layer when the AVPlayer boundary time observer fires.
    /// Triggers the dwell/advance flow with zero latency.
    func boundaryReached() {
        guard isEnabled else { return }
        // Only react if we're in playing phase (not already dwelling/transitioning)
        guard case .playing = phase else {
            logBoundary("Boundary ignored phase=\(phase)")
            return
        }
        guard let segment = currentSegment else { return }

        logBoundary("Boundary triggered seg[\(currentSegmentIndex)] end=\(String(format: "%.3f", segment.end)) \(segment.track.rawValue)")
        phase = .dwelling(startedAt: Date())

        // Pause during dwell to prevent audio bleed
        onPauseForDwell?(segment.end)

        // Schedule dwell completion
        dwellWorkItem?.cancel()
        let workItem = DispatchWorkItem { [weak self] in
            Task { @MainActor [weak self] in
                self?.completeDwell()
            }
        }
        dwellWorkItem = workItem
        DispatchQueue.main.asyncAfter(deadline: .now() + segmentEndDwellDuration, execute: workItem)
    }

    // MARK: - Time Update Loop

    /// Check playback time and advance to next segment if needed
    /// Returns true if a track switch occurred
    func updateForTime(_ time: Double, isPlaying: Bool) -> Bool {
        guard isEnabled else { return false }
        guard isPlaying else { return false }

        // Phase-based guard: only process time updates in playing or validating phases
        switch phase {
        case .idle, .transitioning:
            return false
        case .dwelling:
            // Dwell completion handled by scheduled work item
            return false
        case .validating, .playing:
            break
        }

        guard let segment = currentSegment else {
            debugLog("updateForTime: no current segment")
            return false
        }

        let tolerance = 0.1 // 100ms tolerance

        // Handle validation phase (settling + stale time detection)
        if case .validating(var state) = phase {
            // Sub-state: settling (waiting for AVPlayer time to reach expected position after initial load)
            if state.isSettling {
                state.settlingCount += 1
                // Check if time has settled near the segment start
                if time >= segment.start - tolerance && time <= segment.start + 1.0 {
                    debugLog("Settling complete, time=\(String(format: "%.3f", time)) is near segment start \(String(format: "%.3f", segment.start))")
                    phase = .playing
                } else if state.settlingCount >= maxSettlingCount {
                    // Timeout — AVPlayer time hasn't reached the expected position.
                    // Do NOT reset currentSegmentIndex/currentTrack — they were set
                    // correctly by seekToSentence() or advanceToNextSegment().
                    // Resetting to segment 0 was the root cause of the desync on resume.
                    state.reseekAttempts += 1
                    if state.reseekAttempts <= maxReseekAttempts {
                        // Request a re-seek to segment start
                        debugLog("Settling timeout at time=\(String(format: "%.3f", time)), requesting re-seek (attempt \(state.reseekAttempts)/\(maxReseekAttempts))")
                        onWillBeginTransition?()
                        phase = .transitioning
                        onSeekRequest?(segment.start)
                    } else {
                        // Give up - accept that time may be stale but proceed anyway
                        debugLog("Max re-seek attempts reached, accepting stale time=\(String(format: "%.3f", time))")
                        phase = .playing
                        onTimeStabilized?()
                    }
                } else {
                    // Still settling - update count and wait
                    phase = .validating(state)
                    if state.settlingCount <= 3 {
                        debugLog("Settling (\(state.settlingCount)/\(maxSettlingCount)), waiting for time to reach \(String(format: "%.3f", segment.start))")
                    }
                }
                return false
            }

            // Normal validation: check if time matches expected position
            let expected = state.expectedPosition
            let deviation = abs(time - expected)
            // Also check if time is past the segment end - this catches cases where stale time
            // is close to expected but already past the boundary (e.g., skip back within same segment)
            let isPastSegmentEnd = time >= segment.end - tolerance
            let isBeforeSegmentStart = time < segment.start - tolerance
            let isStale = deviation > 1.0 || (isPastSegmentEnd && time > expected + 0.5) || isBeforeSegmentStart

            if isStale && state.staleTimeCount <= 1 {
                debugLog("Stale time t=\(String(format: "%.3f", time)) expected=\(String(format: "%.3f", expected))")
            }

            if isStale {
                // Time is more than 1 second away from expected, or past segment end, or before segment start
                state.staleTimeCount += 1
                if state.staleTimeCount >= maxStaleTimeCount {
                    // Too many stale times - clear expected position
                    // NOTE: Do NOT clear isSameSentenceTrackSwitch here - it will be cleared
                    // when the next transition starts (advanceToNextSegment or commitSentenceTarget)
                    debugLog("Clearing expectedPosition after \(state.staleTimeCount) stale updates, time=\(String(format: "%.3f", time))")
                    phase = .playing
                    onTimeStabilized?()

                    // If we're at the start (segment 0, expected position ~0), this is likely initial load
                    // with stale time from a previous audio file. Enter settling state.
                    if currentSegmentIndex == 0 && expected < 0.5 {
                        debugLog("Initial load detected, entering settling state")
                        phase = .validating(PlaybackPhase.Validation(
                            expectedPosition: expected,
                            isSettling: true
                        ))
                        return false
                    }

                    // After max stale times, simply trust the current segment index.
                    debugLog("Trusting current segment \(currentSegmentIndex) after stale timeout")
                    return false
                } else {
                    // Still waiting for valid time
                    phase = .validating(state)
                    if state.staleTimeCount <= 3 {
                        debugLog("Ignoring stale time \(String(format: "%.3f", time)), expected ~\(String(format: "%.3f", expected)), segment=\(segment.start)-\(segment.end) (\(state.staleTimeCount)/\(maxStaleTimeCount))")
                    }
                    return false
                }
            } else {
                // Track consecutive valid time values before clearing expectedPosition
                // This prevents a race condition where a valid time update is followed by a stale one
                // (AVPlayer can deliver buffered time updates out of order)
                state.staleTimeCount -= 1  // Use staleTimeCount as a countdown for valid times
                if state.staleTimeCount <= -3 {
                    // We've seen 3 consecutive valid times - safe to clear expected position
                    // NOTE: Do NOT clear isSameSentenceTrackSwitch here - it will be cleared
                    // when the next transition starts (advanceToNextSegment or commitSentenceTarget)
                    debugLog("Clearing expectedPosition after 3 valid time updates")
                    phase = .playing
                    onTimeStabilized?()
                } else {
                    phase = .validating(state)
                }
            }
        }

        // Fallback segment-end check: catches cases where the boundary observer missed
        // (e.g., time jumped past the boundary due to seeking or buffering).
        // Primary segment-end detection is handled by boundaryReached() via AVPlayer boundary observer.
        if time >= segment.end - tolerance {
            if case .playing = phase {
                logBoundary("Fallback triggered t=\(String(format: "%.3f", time)) seg[\(currentSegmentIndex)] end=\(String(format: "%.3f", segment.end)) \(segment.track.rawValue)")
                boundaryReached()
            }
            // Whether we just entered dwelling or are already in it, don't process further
            return false
        }

        // Not at segment end - if somehow still in dwelling state, cancel and return to playing
        if case .dwelling = phase {
            dwellWorkItem?.cancel()
            dwellWorkItem = nil
            phase = .playing
        }

        return false
    }

    // MARK: - Dwell Completion

    /// Complete the dwell period and advance to the next segment
    /// Called by the scheduled work item after segmentEndDwellDuration
    private func completeDwell() {
        guard case .dwelling(let startedAt) = phase else {
            // Dwell was cancelled (e.g., user skipped or paused)
            return
        }

        let dwellElapsed = Date().timeIntervalSince(startedAt)
        debugLog("Dwell complete (\(String(format: "%.3f", dwellElapsed))s) - advancing from segment[\(currentSegmentIndex)]")

        dwellWorkItem = nil
        // Phase will be set by advanceToNextSegment (to .transitioning)
        _ = advanceToNextSegment()
    }

    // MARK: - Segment Navigation

    /// Find the segment index that contains the given time for the specified track
    private func findSegmentIndex(forTime time: Double, track: SequenceTrack) -> Int? {
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
        phase = .transitioning
        debugLog("Transition started")
    }

    /// Cancel pending automatic dwell/transition work when the reader is explicitly paused.
    /// Keeps the current plan and segment so playback can resume from the same place, but
    /// invalidates scheduled advances that would otherwise restart audio after pause.
    func cancelPendingAutomaticAdvanceForPause() {
        dwellWorkItem?.cancel()
        dwellWorkItem = nil
        let hadExpectedPosition = expectedPosition != nil
        switch phase {
        case .dwelling, .transitioning, .validating:
            phase = .playing
        case .idle, .playing:
            break
        }
        if hadExpectedPosition {
            onTimeStabilized?()
        }
        onCleanupAudioEffects?()
        debugLog("Cancelled pending automatic advance for explicit pause")
    }

    /// Mark transition as completed (call after audio is loaded and ready)
    /// - Parameter expectedTime: The expected playback position after the seek
    func endTransition(expectedTime: Double? = nil) {
        // NOTE: We intentionally do NOT clear isSameSentenceTrackSwitch here.
        // The flag persists briefly after transition ends so the view can still
        // show static display until the next segment advance clears it.
        let sameSentenceSwitch = isSameSentenceTrackSwitch

        if let expectedTime {
            phase = .validating(PlaybackPhase.Validation(expectedPosition: expectedTime))
        } else {
            phase = .playing
        }

        // Install boundary observer for the new segment
        installBoundaryForCurrentSegment()

        debugLog("Transition ended, expectedPosition=\(expectedTime.map { String(format: "%.3f", $0) } ?? "nil"), sameSentenceSwitch=\(sameSentenceSwitch)")
    }

    /// Advance to the next segment in the plan
    /// Returns true if a track switch occurred
    @discardableResult
    func advanceToNextSegment() -> Bool {
        // CRITICAL: Set phase to .transitioning FIRST before any other state changes
        // to prevent race conditions where a SwiftUI render sees intermediate state
        phase = .transitioning

        // Clear the previous same-sentence flag immediately to prevent it from
        // affecting renders during the next transition
        isSameSentenceTrackSwitch = false
        // Clear dwell state when advancing to new segment
        dwellWorkItem?.cancel()
        dwellWorkItem = nil

        // Find the next segment, skipping any segments for hidden tracks
        var nextIndex = currentSegmentIndex + 1
        while nextIndex < plan.count {
            let candidate = plan[nextIndex]
            if let shouldSkip = shouldSkipTrack, shouldSkip(candidate.track) {
                debugLog("SKIP \(candidate.track.rawValue) seg[\(nextIndex)]")
                nextIndex += 1
                continue
            }
            break
        }

        if nextIndex >= plan.count {
            // End of sequence - disable immediately to prevent re-entering dwell
            debugLog("End of sequence reached")
            isEnabled = false
            phase = .idle  // Reset since we're not actually transitioning
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
            onWillBeginTransition?()
        }

        currentSegmentIndex = nextIndex
        currentTrack = nextSegment.track

        if Self.debug {
            debugLog("Advance: \(previousTrack.rawValue)->\(nextSegment.track.rawValue) seg[\(nextIndex)] sent[\(nextSegment.sentenceIndex)]")
        }

        if didSwitchTrack {
            onTrackSwitch?(nextSegment.track, nextSegment.start)
        } else {
            onResumeAfterDwell?(nextSegment.start)
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
            if Self.debug {
                let sentenceIndices = Set(plan.map { $0.sentenceIndex }).sorted()
                debugLog("seekToSentence(\(sentenceIndex)) failed: no target found in plan with \(plan.count) segments")
                debugLog("Available sentence indices: \(sentenceIndices)")
            }
            return nil
        }
        debugLog("seekToSentence(\(sentenceIndex)) found: segment[\(target.segmentIndex)], track=\(target.track), time=\(String(format: "%.3f", target.time))")
        currentSegmentIndex = target.segmentIndex
        currentTrack = target.track
        return (target.track, target.time)
    }

    /// Find the target segment for a sentence without updating state
    func findSentenceTarget(_ sentenceIndex: Int, preferredTrack: SequenceTrack? = nil) -> (segmentIndex: Int, track: SequenceTrack, time: Double)? {
        let preferred = preferredTrack ?? .original
        let fallback: SequenceTrack = preferred == .original ? .translation : .original

        if let index = findSegmentIndex(sentenceIndex: sentenceIndex, track: preferred) {
            return (index, preferred, plan[index].start)
        }
        if let index = findSegmentIndex(sentenceIndex: sentenceIndex, track: fallback) {
            return (index, fallback, plan[index].start)
        }
        return nil
    }

    /// Commit a state change for a previously found sentence target
    /// This is used for sentence skips (next/previous) which always target a different sentence
    func commitSentenceTarget(_ target: (segmentIndex: Int, track: SequenceTrack, time: Double)) {
        // Sentence skips always go to a different sentence, so clear the same-sentence flag
        isSameSentenceTrackSwitch = false
        // Clear dwell state when seeking to a new sentence
        dwellWorkItem?.cancel()
        dwellWorkItem = nil
        currentSegmentIndex = target.segmentIndex
        currentTrack = target.track
    }

    /// Commit a direct word-level seek target.
    /// Unlike sentence navigation, a token tap can intentionally switch tracks inside
    /// the same sentence, so preserve that transition metadata for the transcript.
    func commitTokenSeekTarget(_ target: (segmentIndex: Int, track: SequenceTrack, time: Double)) {
        let previousTrack = currentTrack
        let previousSentenceIndex = currentSegment?.sentenceIndex
        let targetSentenceIndex = plan.indices.contains(target.segmentIndex)
            ? plan[target.segmentIndex].sentenceIndex
            : nil
        isSameSentenceTrackSwitch = previousTrack != target.track && previousSentenceIndex == targetSentenceIndex
        dwellWorkItem?.cancel()
        dwellWorkItem = nil
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

    /// Navigate to the next sequence segment.
    func nextSentence(preferredTrack: SequenceTrack? = nil) -> (track: SequenceTrack, time: Double)? {
        guard let target = nextSentenceTarget(preferredTrack: preferredTrack) else { return nil }
        commitSentenceTarget(target)
        return (target.track, target.time)
    }

    /// Find the next sequence segment without updating state.
    func nextSentenceTarget(preferredTrack: SequenceTrack? = nil) -> (segmentIndex: Int, track: SequenceTrack, time: Double)? {
        guard let currentSentence = currentSentenceIndex else { return nil }
        let preferred = preferredTrack ?? currentTrack
        let candidates = sentenceIndices.filter { $0 > currentSentence }
        for sentenceIndex in candidates {
            if let target = findSentenceTarget(sentenceIndex, preferredTrack: preferred) {
                return target
            }
        }
        return nil
    }

    /// Navigate to the previous sequence segment.
    func previousSentence(preferredTrack: SequenceTrack? = nil) -> (track: SequenceTrack, time: Double)? {
        guard let target = previousSentenceTarget(preferredTrack: preferredTrack) else { return nil }
        commitSentenceTarget(target)
        return (target.track, target.time)
    }

    /// Find the previous sequence segment without updating state.
    func previousSentenceTarget(preferredTrack: SequenceTrack? = nil) -> (segmentIndex: Int, track: SequenceTrack, time: Double)? {
        guard let currentSentence = currentSentenceIndex else { return nil }
        let preferred = preferredTrack ?? currentTrack
        let candidates = sentenceIndices.filter { $0 < currentSentence }.reversed()
        for sentenceIndex in candidates {
            if let target = findSentenceTarget(sentenceIndex, preferredTrack: preferred) {
                return target
            }
        }
        return nil
    }

    // MARK: - Reset

    /// Reset the controller state
    func reset() {
        isEnabled = false
        isSameSentenceTrackSwitch = false
        dwellWorkItem?.cancel()
        dwellWorkItem = nil
        let hadExpectedPosition = expectedPosition != nil
        phase = .idle
        if hadExpectedPosition {
            onTimeStabilized?()
        }
        plan = []
        currentSegmentIndex = 0
        currentTrack = .original
        originalTrackURL = nil
        translationTrackURL = nil
        // Clear fade-out mix and boundary observer to prevent stale effects
        // silencing audio when switching away from sequence mode
        onCleanupAudioEffects?()
    }
}
