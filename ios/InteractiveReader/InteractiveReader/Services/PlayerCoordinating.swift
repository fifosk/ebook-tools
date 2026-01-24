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

// MARK: - Type Erasure

/// Type-erased wrapper for PlayerCoordinating to allow storing different coordinator types
@MainActor
final class AnyPlayerCoordinator: ObservableObject {
    @Published private(set) var currentTime: Double = 0
    @Published private(set) var duration: Double = 0
    @Published private(set) var isPlaying: Bool = false
    @Published private(set) var playbackRate: Double = 1.0

    var onPlaybackEnded: (() -> Void)?

    private let _play: () -> Void
    private let _pause: () -> Void
    private let _togglePlayback: () -> Void
    private let _seek: (Double) -> Void
    private let _setPlaybackRate: (Double) -> Void
    private let _reset: () -> Void

    private var cancellables = Set<AnyCancellable>()

    init<T: PlayerCoordinating>(_ coordinator: T) {
        _play = { coordinator.play() }
        _pause = { coordinator.pause() }
        _togglePlayback = { coordinator.togglePlayback() }
        _seek = { coordinator.seek(to: $0) }
        _setPlaybackRate = { coordinator.setPlaybackRate($0) }
        _reset = { coordinator.reset() }

        // Forward published values
        coordinator.objectWillChange
            .receive(on: DispatchQueue.main)
            .sink { [weak self, weak coordinator] _ in
                guard let self, let coordinator else { return }
                self.currentTime = coordinator.currentTime
                self.duration = coordinator.duration
                self.isPlaying = coordinator.isPlaying
                self.playbackRate = coordinator.playbackRate
            }
            .store(in: &cancellables)

        // Initialize with current values
        currentTime = coordinator.currentTime
        duration = coordinator.duration
        isPlaying = coordinator.isPlaying
        playbackRate = coordinator.playbackRate
    }

    func play() { _play() }
    func pause() { _pause() }
    func togglePlayback() { _togglePlayback() }
    func seek(to time: Double) { _seek(time) }
    func setPlaybackRate(_ rate: Double) { _setPlaybackRate(rate) }
    func reset() { _reset() }

    var progress: Double {
        guard duration > 0 else { return 0 }
        return currentTime / duration
    }

    func skip(by delta: Double) {
        seek(to: currentTime + delta)
    }
}
