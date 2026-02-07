import AVFoundation
import Combine
import Foundation

/// Protocol defining the common interface for audio and video player coordinators.
///
/// This protocol allows views to work with either coordinator type through a common interface,
/// enabling code reuse across playback views without coupling to a specific implementation.
@MainActor
protocol PlayerCoordinating: AnyObject, ObservableObject {
    // MARK: - Published State

    /// Current playback position in seconds
    var currentTime: Double { get }

    /// Total duration in seconds (0 if unknown)
    var duration: Double { get }

    /// Whether media is currently playing
    var isPlaying: Bool { get }

    /// Current playback rate (1.0 = normal speed)
    var playbackRate: Double { get }

    // MARK: - Callbacks

    /// Called when playback reaches the end
    var onPlaybackEnded: (() -> Void)? { get set }

    // MARK: - Playback Control

    /// Start or resume playback
    func play()

    /// Pause playback
    func pause()

    /// Toggle between play and pause states
    func togglePlayback()

    /// Seek to a specific time in seconds
    func seek(to time: Double)

    /// Set the playback speed
    func setPlaybackRate(_ rate: Double)

    /// Reset the player state
    func reset()
}

/// Extension providing default implementations and computed properties
extension PlayerCoordinating {
    /// Computed progress value (0.0 - 1.0)
    var progress: Double {
        guard duration > 0 else { return 0 }
        return currentTime / duration
    }

    /// Skip forward or backward by a time delta
    func skip(by delta: Double) {
        seek(to: currentTime + delta)
    }

    /// Whether playback is paused (not playing)
    var isPaused: Bool {
        !isPlaying
    }
}
