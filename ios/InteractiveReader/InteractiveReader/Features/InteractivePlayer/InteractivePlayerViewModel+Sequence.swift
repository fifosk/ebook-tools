import Foundation
import Combine

extension InteractivePlayerViewModel {
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
        guard let trackID = selectedAudioTrackID,
              let track = chunk.audioOptions.first(where: { $0.id == trackID }),
              track.kind == .combined else {
            sequenceController.reset()
            return
        }

        // Get the original and translation tracks
        let originalTrack = chunk.audioOptions.first { $0.kind == .original }
        let translationTrack = chunk.audioOptions.first { $0.kind == .translation }

        guard let originalURL = originalTrack?.primaryURL,
              let translationURL = translationTrack?.primaryURL else {
            // No separate tracks available, fallback to combined track's URLs
            print("[Sequence] No separate tracks available, falling back to combined track URLs")
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
            print("[Sequence] Skipping reconfigure - mid-sequence (dwelling=\(sequenceController.isDwelling), transitioning=\(sequenceController.isTransitioning))")
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
        if sequenceController.isEnabled {
            // If we have a target sentence (resume), position to that sentence
            if let targetIndex = targetSentenceIndex,
               let target = sequenceController.seekToSentence(targetIndex, preferredTrack: .original) {
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
                            print("[Sequence] Resume audio loading...")
                        } else if seenLoadingState {
                            print("[Sequence] Resume audio ready")
                            self.completeSequenceTransition(seekTime: target.time, shouldPlay: autoPlay, transitionToken: token)
                        } else if isFirstEmission {
                            // Audio was already loaded (same URL), no loading transition occurred
                            // Complete the transition immediately
                            isFirstEmission = false
                            print("[Sequence] Resume audio already ready (no load needed)")
                            self.completeSequenceTransition(seekTime: target.time, shouldPlay: autoPlay, transitionToken: token)
                        }
                    }
            } else {
                // No target sentence, start from the beginning
                print("[Sequence] Sequence mode enabled, starting with \(sequenceController.currentTrack.rawValue) track")

                // For initial load, there's no meaningful "previous" sentence.
                // Set preTransitionSentenceIndex to nil so the view layer uses the initial display
                // for sentence 0 rather than trying to show a non-existent previous sentence.
                preTransitionSentenceIndex = nil
                timeStabilizedAt = nil

                // Fire the pre-transition callback to allow view layer to freeze
                // This must happen BEFORE beginTransition() sets isTransitioning = true
                print("[Sequence] Firing onWillBeginTransition for initial load")
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
                            print("[Sequence] Initial audio loading...")
                        } else if seenLoadingState {
                            // We've transitioned from loading to ready - now seek and start playback
                            print("[Sequence] Initial audio ready")
                            self.completeSequenceTransition(seekTime: targetSeekTime, shouldPlay: autoPlay, transitionToken: token)
                        } else if isFirstEmission {
                            // Audio was already loaded (same URL), no loading transition occurred
                            // Complete the transition immediately
                            isFirstEmission = false
                            print("[Sequence] Initial audio already ready (no load needed)")
                            self.completeSequenceTransition(seekTime: targetSeekTime, shouldPlay: autoPlay, transitionToken: token)
                        }
                    }
            }
        } else {
            print("[Sequence] Sequence mode not available, falling back to combined URLs")
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
            print("[Sequence] No URL for track \(track.rawValue)")
            return nil
        }

        // Mute BEFORE loading to prevent audio bleed from the old track
        // NOTE: We don't call pause() here because it sets isPlaybackRequested = false,
        // which would cause the reading bed to stop during track switches.
        // The load() call will tear down the old player anyway.
        audioCoordinator.setVolume(0)

        print("[Sequence] Load \(track.rawValue): \(url.lastPathComponent)")
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
            print("[Sequence] Ignoring stale transition completion (token \(transitionToken) != current \(currentTransitionToken))")
            return
        }

        if let seekTime {
            audioCoordinator.seek(to: seekTime) { [weak self] finished in
                guard let self else { return }
                DispatchQueue.main.asyncAfter(deadline: .now() + 0.05) { [weak self] in
                    guard let self else { return }
                    // Re-check token after async delay
                    guard transitionToken == self.currentTransitionToken else {
                        print("[Sequence] Ignoring stale transition completion after seek (token \(transitionToken) != current \(self.currentTransitionToken))")
                        return
                    }
                    self.sequenceController.endTransition(expectedTime: seekTime)
                    self.readyCancellable?.cancel()
                    self.readyCancellable = nil
                    self.audioCoordinator.setVolume(1)
                    if shouldPlay {
                        self.audioCoordinator.play()
                    }
                }
            }
        } else {
            sequenceController.endTransition(expectedTime: nil)
            readyCancellable?.cancel()
            readyCancellable = nil
            audioCoordinator.setVolume(1)
            if shouldPlay {
                audioCoordinator.play()
            }
        }
    }

    /// Handle track switch during sequence playback
    func handleSequenceTrackSwitch(track: SequenceTrack, seekTime: Double) {
        print("[Sequence] Switch to \(track.rawValue)")

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
