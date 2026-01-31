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
        // This prevents re-entry from SwiftUI re-renders during playback
        if sequenceController.isEnabled,
           sequenceController.originalTrackURL == originalURL,
           sequenceController.translationTrackURL == translationURL {
            print("[Sequence] Sequence already active for these tracks, skipping reconfiguration")
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
                print("[Sequence] Sequence mode enabled, resuming at sentence \(targetIndex) on \(target.track.rawValue) track at \(String(format: "%.3f", target.time))")

                // Fire the pre-transition callback to allow view layer to freeze
                print("[Sequence] Firing onWillBeginTransition for resume load")
                onSequenceWillTransition?()

                // Begin transition to prevent time updates during initial load
                sequenceController.beginTransition()

                // Cancel any existing subscription
                readyCancellable?.cancel()

                // Track whether we've seen the loading state (isReady = false)
                var seenLoadingState = false

                // Load the target track
                _ = loadSequenceTrack(target.track, autoPlay: autoPlay, seekTime: nil)

                // Subscribe to wait for audio to be ready, then seek and end transition
                readyCancellable = audioCoordinator.$isReady
                    .sink { [weak self] isReady in
                        guard let self else { return }
                        if !isReady {
                            seenLoadingState = true
                            print("[Sequence] Resume audio loading...")
                        } else if seenLoadingState {
                            print("[Sequence] Resume audio ready")
                            self.completeSequenceTransition(seekTime: target.time)
                        }
                    }
            } else {
                // No target sentence, start from the beginning
                print("[Sequence] Sequence mode enabled, starting with \(sequenceController.currentTrack.rawValue) track")

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

                // Load the track first to get the seek time
                let targetSeekTime = loadSequenceTrack(sequenceController.currentTrack, autoPlay: autoPlay)

                // Subscribe to wait for audio to be ready, then seek and end transition
                readyCancellable = audioCoordinator.$isReady
                    .sink { [weak self] isReady in
                        guard let self else { return }
                        if !isReady {
                            // Mark that we've entered the loading state
                            seenLoadingState = true
                            print("[Sequence] Initial audio loading...")
                        } else if seenLoadingState {
                            // We've transitioned from loading to ready - now seek and end transition
                            print("[Sequence] Initial audio ready")
                            self.completeSequenceTransition(seekTime: targetSeekTime)
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

        print("[Sequence] Loading \(track.rawValue) track: \(url.lastPathComponent)")
        audioCoordinator.load(url: url, autoPlay: autoPlay)
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
    private func completeSequenceTransition(seekTime: Double?) {
        if let seekTime {
            print("[Sequence] Seeking to \(String(format: "%.3f", seekTime))")
            audioCoordinator.seek(to: seekTime)
        }
        // Small delay to ensure seek takes effect before ending transition
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.1) { [weak self] in
            guard let self else { return }
            let actualTime = self.audioCoordinator.currentTime
            print("[Sequence] Completing transition, currentTime=\(String(format: "%.3f", actualTime)), segment=\(self.sequenceController.currentSegmentIndex)")
            // Pass the expected time so updateForTime can validate incoming time values
            self.sequenceController.endTransition(expectedTime: seekTime)
            self.readyCancellable?.cancel()
            self.readyCancellable = nil
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

        // Load the track first (pass nil for seekTime since we'll use the explicit one)
        _ = loadSequenceTrack(track, autoPlay: true, seekTime: nil)

        // Subscribe to wait for audio to be ready, then seek and end transition
        readyCancellable = audioCoordinator.$isReady
            .sink { [weak self] isReady in
                guard let self else { return }
                if !isReady {
                    // Mark that we've entered the loading state
                    seenLoadingState = true
                    print("[Sequence] Audio loading...")
                } else if seenLoadingState {
                    // We've transitioned from loading to ready - now seek and end transition
                    print("[Sequence] Audio ready")
                    self.completeSequenceTransition(seekTime: seekTime)
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
