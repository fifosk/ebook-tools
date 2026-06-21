import Foundation
import Combine
import OSLog

private let interactiveSequenceLogger = Logger(subsystem: "InteractiveReader", category: "InteractiveSequence")

extension InteractivePlayerViewModel {
    /// Set to true to enable verbose sequence playback logging
    private static let sequenceDebug = false

    /// Storage key for the readiness cancellable subscription
    private static var readyCancellableKey: UInt8 = 0
    /// Storage key for the transition token
    private static var transitionTokenKey: UInt8 = 0

    /// Cancellable for observing audioCoordinator.isReady during transitions
    private var readyCancellable: AnyCancellable? {
        get { objc_getAssociatedObject(self, &Self.readyCancellableKey) as? AnyCancellable }
        set { objc_setAssociatedObject(self, &Self.readyCancellableKey, newValue, .OBJC_ASSOCIATION_RETAIN_NONATOMIC) }
    }

    /// Token to track which transition is active - incremented each time a new transition starts
    /// Used to invalidate stale transition completions
    var currentTransitionToken: Int {
        get { (objc_getAssociatedObject(self, &Self.transitionTokenKey) as? NSNumber)?.intValue ?? 0 }
        set { objc_setAssociatedObject(self, &Self.transitionTokenKey, NSNumber(value: newValue), .OBJC_ASSOCIATION_RETAIN_NONATOMIC) }
    }

    /// Cancel any pending audio ready subscription and invalidate the current transition
    /// Call this when starting a new transition that should supersede any in-progress transition
    func cancelPendingAudioReadySubscription() {
        readyCancellable?.cancel()
        readyCancellable = nil
        // Increment token to invalidate any in-flight completion callbacks
        currentTransitionToken += 1
    }

    /// Configure the sequence controller for a chunk when combined mode is selected
    /// - Parameters:
    ///   - chunk: The chunk to configure playback for
    ///   - autoPlay: Whether to start playing automatically
    ///   - targetSentenceIndex: Optional 0-based sentence index to start from (for resume)
    func configureSequencePlayback(for chunk: InteractiveChunk, autoPlay: Bool, targetSentenceIndex: Int? = nil) {
        if Self.sequenceDebug {
            interactiveSequenceLogger.debug(
                "Configure sequence playback: targetSentenceIndex=\(targetSentenceIndex ?? -1, privacy: .public), autoPlay=\(autoPlay, privacy: .public)"
            )
        }

        guard let trackID = selectedAudioTrackID,
              let track = chunk.audioOptions.first(where: { $0.id == trackID }),
              track.kind == .combined else {
            if Self.sequenceDebug {
                interactiveSequenceLogger.debug(
                    "Configure sequence guard failed: trackID=\(self.selectedAudioTrackID ?? "nil", privacy: .private), track.kind != combined"
                )
            }
            sequenceController.reset()
            return
        }

        // Get the original and translation tracks
        let originalTrack = chunk.audioOptions.first { $0.kind == .original }
        let translationTrack = chunk.audioOptions.first { $0.kind == .translation }

        guard let originalURL = originalTrack?.primaryURL,
              let translationURL = translationTrack?.primaryURL else {
            // No separate tracks available, fallback to combined track's URLs
            if Self.sequenceDebug {
                interactiveSequenceLogger.debug("Configure sequence: no separate tracks available, falling back to combined track URLs")
            }
            sequenceController.reset()
            audioCoordinator.load(urls: track.streamURLs, autoPlay: autoPlay)
            selectedTimingURL = track.timingURL ?? track.streamURLs.first
            return
        }

        // Don't reconfigure if sequence is mid-transition (dwelling or transitioning between tracks)
        // This prevents chunk preloading or SwiftUI re-renders from resetting sequence state
        // while we're waiting to advance from original to translation track
        if sequenceController.isEnabled,
           (sequenceController.isDwelling || sequenceController.isTransitioning),
           targetSentenceIndex == nil {
            if Self.sequenceDebug {
                interactiveSequenceLogger.debug(
                    "Configure sequence: skipping reconfigure mid-sequence dwelling=\(self.sequenceController.isDwelling, privacy: .public), transitioning=\(self.sequenceController.isTransitioning, privacy: .public)"
                )
            }
            return
        }

        // If sequence mode is already active for these same URLs, don't reconfigure
        // UNLESS we have a target sentence (jump/resume), in which case we need to seek
        // This prevents re-entry from SwiftUI re-renders during playback
        if sequenceController.isEnabled,
           sequenceController.originalTrackURL == originalURL,
           sequenceController.translationTrackURL == translationURL,
           targetSentenceIndex == nil {
            return
        }

        // Build the sequence plan from sentences
        sequenceController.buildPlan(
            from: chunk.sentences,
            originalTrackURL: originalURL,
            translationTrackURL: translationURL,
            originalDuration: originalTrack?.duration,
            translationDuration: translationTrack?.duration
        )

        // If sequence mode is enabled, load the appropriate track
        if Self.sequenceDebug {
            interactiveSequenceLogger.debug(
                "Configure sequence: after buildPlan isEnabled=\(self.sequenceController.isEnabled, privacy: .public), targetSentenceIndex=\(targetSentenceIndex ?? -1, privacy: .public), planCount=\(self.sequenceController.plan.count, privacy: .public)"
            )
        }
        if sequenceController.isEnabled {
            // If we have a target sentence (resume), position to that sentence
            if let targetIndex = targetSentenceIndex,
               let target = sequenceController.seekToSentence(targetIndex, preferredTrack: .original) {
                if Self.sequenceDebug {
                    interactiveSequenceLogger.debug(
                        "Configure sequence: seeking targetIndex=\(targetIndex, privacy: .public), track=\(target.track.rawValue, privacy: .public), time=\(target.time, privacy: .public)"
                    )
                }
                // For resume/jump, we're going directly to a target sentence.
                // Set preTransitionSentenceIndex to nil to indicate there's no meaningful "previous"
                // sentence to show (we're not advancing from a prior sentence, we're jumping directly).
                // The view layer will use the initial display for the target sentence.
                preTransitionSentenceIndex = nil
                timeStabilizedAt = nil

                // Fire the pre-transition callback to allow view layer to freeze
                onSequenceWillTransition?()

                // Begin transition to prevent time updates during initial load
                sequenceController.beginTransition()

                // Cancel any existing subscription and increment token
                cancelPendingAudioReadySubscription()
                let token = currentTransitionToken

                // Track whether we've seen the loading state (isReady = false)
                var seenLoadingState = false
                // Track whether this is the first emission (for handling already-loaded case)
                var isFirstEmission = true

                // Load the target track WITHOUT autoPlay - we'll start after seek completes
                // This prevents audio bleed from position 0 before seeking to target
                _ = loadSequenceTrack(target.track, autoPlay: false, seekTime: nil)

                // Subscribe to wait for audio to be ready, then seek and end transition
                readyCancellable = audioCoordinator.$isReady
                    .sink { [weak self] isReady in
                        guard let self else { return }
                        if !isReady {
                            seenLoadingState = true
                            isFirstEmission = false
                            if Self.sequenceDebug { interactiveSequenceLogger.debug("Configure sequence: resume audio loading") }
                        } else if seenLoadingState {
                            if Self.sequenceDebug { interactiveSequenceLogger.debug("Configure sequence: resume audio ready") }
                            self.completeSequenceTransition(seekTime: target.time, shouldPlay: autoPlay, transitionToken: token)
                        } else if isFirstEmission {
                            // Audio was already loaded (same URL), no loading transition occurred
                            // Complete the transition immediately
                            isFirstEmission = false
                            if Self.sequenceDebug { interactiveSequenceLogger.debug("Configure sequence: resume audio already ready, no load needed") }
                            self.completeSequenceTransition(seekTime: target.time, shouldPlay: autoPlay, transitionToken: token)
                        }
                    }
            } else {
                // No target sentence OR seekToSentence failed, start from the beginning
                if Self.sequenceDebug {
                    if let targetIndex = targetSentenceIndex {
                        interactiveSequenceLogger.debug(
                            "Configure sequence: seekToSentence failed targetIndex=\(targetIndex, privacy: .public), falling back to start"
                        )
                    }
                    interactiveSequenceLogger.debug(
                        "Configure sequence: sequence mode enabled, starting track=\(self.sequenceController.currentTrack.rawValue, privacy: .public)"
                    )
                }

                // For initial load, there's no meaningful "previous" sentence.
                // Set preTransitionSentenceIndex to nil so the view layer uses the initial display
                // for sentence 0 rather than trying to show a non-existent previous sentence.
                preTransitionSentenceIndex = nil
                timeStabilizedAt = nil

                // Fire the pre-transition callback to allow view layer to freeze
                // This must happen BEFORE beginTransition() sets isTransitioning = true
                if Self.sequenceDebug { interactiveSequenceLogger.debug("Configure sequence: firing onWillBeginTransition for initial load") }
                onSequenceWillTransition?()

                // Begin transition to prevent time updates during initial load
                sequenceController.beginTransition()

                // Cancel any existing subscription and increment token
                cancelPendingAudioReadySubscription()
                let token = currentTransitionToken

                // Track whether we've seen the loading state (isReady = false)
                var seenLoadingState = false
                // Track whether this is the first emission (for handling already-loaded case)
                var isFirstEmission = true

                // Load the track WITHOUT autoPlay - we'll start after seek completes
                // This prevents audio bleed from position 0 before seeking to target
                let targetSeekTime = loadSequenceTrack(sequenceController.currentTrack, autoPlay: false)

                // Subscribe to wait for audio to be ready, then seek and end transition
                readyCancellable = audioCoordinator.$isReady
                    .sink { [weak self] isReady in
                        guard let self else { return }
                        if !isReady {
                            // Mark that we've entered the loading state
                            seenLoadingState = true
                            isFirstEmission = false
                            if Self.sequenceDebug { interactiveSequenceLogger.debug("Configure sequence: initial audio loading") }
                        } else if seenLoadingState {
                            // We've transitioned from loading to ready - now seek and start playback
                            if Self.sequenceDebug { interactiveSequenceLogger.debug("Configure sequence: initial audio ready") }
                            self.completeSequenceTransition(seekTime: targetSeekTime, shouldPlay: autoPlay, transitionToken: token)
                        } else if isFirstEmission {
                            // Audio was already loaded (same URL), no loading transition occurred
                            // Complete the transition immediately
                            isFirstEmission = false
                            if Self.sequenceDebug { interactiveSequenceLogger.debug("Configure sequence: initial audio already ready, no load needed") }
                            self.completeSequenceTransition(seekTime: targetSeekTime, shouldPlay: autoPlay, transitionToken: token)
                        }
                    }
            }
        } else {
            if Self.sequenceDebug { interactiveSequenceLogger.debug("Configure sequence: sequence mode unavailable, falling back to combined URLs") }
            // Fall back to loading the combined track's URLs directly
            audioCoordinator.load(urls: track.streamURLs, autoPlay: autoPlay)
            selectedTimingURL = track.timingURL ?? track.streamURLs.first
        }
    }

    /// Load the audio for a specific sequence track
    /// Returns the target seek time if a seek will be performed
    @discardableResult
    func loadSequenceTrack(_ track: SequenceTrack, autoPlay: Bool, seekTime: Double? = nil) -> Double? {
        let url: URL?
        switch track {
        case .original:
            url = sequenceController.originalTrackURL
        case .translation:
            url = sequenceController.translationTrackURL
        }

        guard let url else {
            if Self.sequenceDebug {
                interactiveSequenceLogger.debug("Load sequence track: no URL for track=\(track.rawValue, privacy: .public)")
            }
            return nil
        }

        // Mute BEFORE loading to prevent audio bleed from the old track
        // NOTE: We don't call pause() here because it sets isPlaybackRequested = false,
        // which would cause the reading bed to stop during track switches.
        // The load() call will tear down the old player anyway.
        audioCoordinator.setVolume(0)

        if Self.sequenceDebug {
            interactiveSequenceLogger.debug(
                "Load sequence track: track=\(track.rawValue, privacy: .public), file=\(url.lastPathComponent, privacy: .private)"
            )
        }
        // Use forceNoAutoPlay when autoPlay is false to prevent audio bleed during track switches
        // (otherwise isPlaybackRequested would cause auto-play even when we don't want it)
        // Use preservePlaybackRequested to keep isPlaybackRequested = true during transitions
        // so that reading bed doesn't pause/jitter when we switch tracks
        audioCoordinator.load(url: url, autoPlay: autoPlay, forceNoAutoPlay: !autoPlay, preservePlaybackRequested: true)
        selectedTimingURL = url

        // Determine the seek target
        let targetSeekTime: Double?
        if let seekTime {
            targetSeekTime = seekTime
        } else if let segment = sequenceController.currentSegment {
            targetSeekTime = segment.start
        } else {
            targetSeekTime = nil
        }

        // NOTE: Don't seek here - the caller will seek after audio is ready
        return targetSeekTime
    }

    /// Perform seek and end transition after audio is ready
    /// - Parameters:
    ///   - seekTime: The time to seek to, or nil for no seek
    ///   - shouldPlay: Whether to start playback after seek completes (used during track switches)
    ///   - transitionToken: The token for this transition - if it doesn't match currentTransitionToken, the completion is stale
    private func completeSequenceTransition(seekTime: Double?, shouldPlay: Bool = false, transitionToken: Int) {
        // Check if this transition has been superseded by a newer one
        guard transitionToken == currentTransitionToken else {
            if Self.sequenceDebug {
                interactiveSequenceLogger.debug(
                    "Complete sequence transition: ignoring stale completion token=\(transitionToken, privacy: .public), current=\(self.currentTransitionToken, privacy: .public)"
                )
            }
            return
        }

        if let seekTime {
            audioCoordinator.seek(to: seekTime) { [weak self] finished in
                guard let self else { return }
                guard transitionToken == self.currentTransitionToken else {
                    if Self.sequenceDebug {
                        interactiveSequenceLogger.debug(
                            "Complete sequence transition: ignoring stale completion after seek token=\(transitionToken, privacy: .public), current=\(self.currentTransitionToken, privacy: .public)"
                        )
                    }
                    return
                }
                // Verify the playhead actually landed at seekTime before starting playback.
                // AVPlayer's seek completion with zero tolerance should guarantee this, but
                // on initial-load and cross-file seeks we've observed the read head linger
                // at a stale position briefly. If the reported position is off by more than
                // 100ms, re-seek once to force alignment. This prevents the "audio lags
                // behind highlighted text" desync on resume/first-play.
                let observed = self.audioCoordinator.currentTime
                let drift = abs(observed - seekTime)
                if drift > 0.1 {
                    if Self.sequenceDebug {
                        interactiveSequenceLogger.debug(
                            "Complete sequence transition: seek drift observed=\(String(format: "%.3f", observed), privacy: .public), expected=\(String(format: "%.3f", seekTime), privacy: .public), drift=\(String(format: "%.3f", drift), privacy: .public)s, re-seeking"
                        )
                    }
                    self.audioCoordinator.seek(to: seekTime) { [weak self] _ in
                        guard let self else { return }
                        guard transitionToken == self.currentTransitionToken else { return }
                        self.sequenceController.endTransition(expectedTime: seekTime)
                        self.readyCancellable?.cancel()
                        self.readyCancellable = nil
                        self.audioCoordinator.restoreVolume()
                        if shouldPlay {
                            self.audioCoordinator.play()
                        }
                    }
                    return
                }
                self.sequenceController.endTransition(expectedTime: seekTime)
                self.readyCancellable?.cancel()
                self.readyCancellable = nil
                self.audioCoordinator.restoreVolume()
                if shouldPlay {
                    self.audioCoordinator.play()
                }
            }
        } else {
            sequenceController.endTransition(expectedTime: nil)
            readyCancellable?.cancel()
            readyCancellable = nil
            audioCoordinator.restoreVolume()
            if shouldPlay {
                audioCoordinator.play()
            }
        }
    }

    /// Handle track switch during sequence playback
    func handleSequenceTrackSwitch(track: SequenceTrack, seekTime: Double) {
        if Self.sequenceDebug {
            interactiveSequenceLogger.debug("Sequence track switch: track=\(track.rawValue, privacy: .public)")
        }

        if !sequenceController.isTransitioning {
            onSequenceWillTransition?()
        }
        sequenceController.beginTransition()

        // Cancel any existing subscription and increment token
        cancelPendingAudioReadySubscription()
        let token = currentTransitionToken

        var seenLoadingState = false
        var isFirstEmission = true

        _ = loadSequenceTrack(track, autoPlay: false, seekTime: nil)

        readyCancellable = audioCoordinator.$isReady
            .sink { [weak self] isReady in
                guard let self else { return }
                if !isReady {
                    seenLoadingState = true
                    isFirstEmission = false
                } else if seenLoadingState {
                    self.completeSequenceTransition(seekTime: seekTime, shouldPlay: true, transitionToken: token)
                } else if isFirstEmission {
                    isFirstEmission = false
                    self.completeSequenceTransition(seekTime: seekTime, shouldPlay: true, transitionToken: token)
                }
            }
    }

    /// Update sequence playback based on current time
    /// This should be called from the time observer
    func updateSequencePlayback(currentTime: Double, isPlaying: Bool) {
        guard sequenceController.isEnabled, isPlaying else { return }

        // Check if we need to switch to the next segment
        if sequenceController.updateForTime(currentTime, isPlaying: isPlaying) {
            // Track switch will be handled by onTrackSwitch callback
        }
    }

    /// Whether sequence mode is currently active for the selected track
    var isSequenceModeActive: Bool {
        guard let chunk = selectedChunk,
              let trackID = selectedAudioTrackID,
              let track = chunk.audioOptions.first(where: { $0.id == trackID }) else {
            return false
        }
        return track.kind == .combined && sequenceController.isEnabled
    }
}
