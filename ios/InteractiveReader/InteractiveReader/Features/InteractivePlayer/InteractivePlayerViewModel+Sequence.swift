import Foundation
import Combine

extension InteractivePlayerViewModel {
    /// Storage key for the readiness cancellable subscription
    private static var readyCancellableKey: UInt8 = 0

    /// Cancellable for observing audioCoordinator.isReady during transitions
    private var readyCancellable: AnyCancellable? {
        get { objc_getAssociatedObject(self, &Self.readyCancellableKey) as? AnyCancellable }
        set { objc_setAssociatedObject(self, &Self.readyCancellableKey, newValue, .OBJC_ASSOCIATION_RETAIN_NONATOMIC) }
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

                // Cancel any existing subscription
                readyCancellable?.cancel()

                // Track whether we've seen the loading state (isReady = false)
                var seenLoadingState = false

                // Load the target track WITHOUT autoPlay - we'll start after seek completes
                // This prevents audio bleed from position 0 before seeking to target
                _ = loadSequenceTrack(target.track, autoPlay: false, seekTime: nil)

                // Subscribe to wait for audio to be ready, then seek and end transition
                readyCancellable = audioCoordinator.$isReady
                    .sink { [weak self] isReady in
                        guard let self else { return }
                        if !isReady {
                            seenLoadingState = true
                            print("[Sequence] Resume audio loading...")
                        } else if seenLoadingState {
                            print("[Sequence] Resume audio ready")
                            self.completeSequenceTransition(seekTime: target.time, shouldPlay: autoPlay)
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

                // Cancel any existing subscription
                readyCancellable?.cancel()

                // Track whether we've seen the loading state (isReady = false)
                var seenLoadingState = false

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
                            print("[Sequence] Initial audio loading...")
                        } else if seenLoadingState {
                            // We've transitioned from loading to ready - now seek and start playback
                            print("[Sequence] Initial audio ready")
                            self.completeSequenceTransition(seekTime: targetSeekTime, shouldPlay: autoPlay)
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

        print("[Sequence] Loading \(track.rawValue) track: \(url.lastPathComponent)")
        // Use forceNoAutoPlay when autoPlay is false to prevent audio bleed during track switches
        // (otherwise isPlaybackRequested would cause auto-play even when we don't want it)
        audioCoordinator.load(url: url, autoPlay: autoPlay, forceNoAutoPlay: !autoPlay)
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
    private func completeSequenceTransition(seekTime: Double?, shouldPlay: Bool = false) {
        if let seekTime {
            print("[Sequence] Seeking to \(String(format: "%.3f", seekTime)), shouldPlay=\(shouldPlay)")
            audioCoordinator.seek(to: seekTime) { [weak self] finished in
                guard let self else { return }
                let actualTime = self.audioCoordinator.currentTime
                print("[Sequence] Seek completed (finished=\(finished)), currentTime=\(String(format: "%.3f", actualTime)), segment=\(self.sequenceController.currentSegmentIndex)")
                // Small delay after seek completes to ensure view has time to render
                // with the correct state before we end the transition and start playback
                DispatchQueue.main.asyncAfter(deadline: .now() + 0.05) { [weak self] in
                    guard let self else { return }
                    // Pass the expected time so updateForTime can validate incoming time values
                    self.sequenceController.endTransition(expectedTime: seekTime)
                    self.readyCancellable?.cancel()
                    self.readyCancellable = nil
                    // Restore volume and start playback AFTER seek completes
                    self.audioCoordinator.setVolume(1)
                    if shouldPlay {
                        self.audioCoordinator.play()
                    }
                }
            }
        } else {
            // No seek needed, just end the transition
            let actualTime = audioCoordinator.currentTime
            print("[Sequence] Completing transition (no seek), currentTime=\(String(format: "%.3f", actualTime)), segment=\(sequenceController.currentSegmentIndex)")
            sequenceController.endTransition(expectedTime: nil)
            readyCancellable?.cancel()
            readyCancellable = nil
            // Restore volume and start playback
            audioCoordinator.setVolume(1)
            if shouldPlay {
                audioCoordinator.play()
            }
        }
    }

    /// Handle track switch during sequence playback
    func handleSequenceTrackSwitch(track: SequenceTrack, seekTime: Double) {
        print("[Sequence] Switching to \(track.rawValue) at \(String(format: "%.3f", seekTime))")

        // Fire pre-transition callback if not already transitioning
        // (advanceToNextSegment already calls this, but manual skips might not have)
        if !sequenceController.isTransitioning {
            onSequenceWillTransition?()
        }

        // Begin transition to prevent re-entrant time updates
        sequenceController.beginTransition()

        // Cancel any existing subscription
        readyCancellable?.cancel()

        // Track whether we've seen the loading state (isReady = false)
        var seenLoadingState = false

        // Load the track WITHOUT autoPlay - we'll start playback after seeking
        // This prevents audio bleed from position 0 before the seek completes
        _ = loadSequenceTrack(track, autoPlay: false, seekTime: nil)

        // Subscribe to wait for audio to be ready, then seek and end transition
        readyCancellable = audioCoordinator.$isReady
            .sink { [weak self] isReady in
                guard let self else { return }
                if !isReady {
                    // Mark that we've entered the loading state
                    seenLoadingState = true
                    print("[Sequence] Audio loading...")
                } else if seenLoadingState {
                    // We've transitioned from loading to ready - now seek and start playback
                    print("[Sequence] Audio ready")
                    self.completeSequenceTransition(seekTime: seekTime, shouldPlay: true)
                }
                // If isReady is true but we haven't seen loading state yet,
                // it's the initial value before load() - ignore it
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
