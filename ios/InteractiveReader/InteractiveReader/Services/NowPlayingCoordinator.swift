import Foundation

#if canImport(MediaPlayer)
import MediaPlayer
import UIKit
#endif

@MainActor
final class NowPlayingCoordinator: ObservableObject {
    #if canImport(MediaPlayer)
    private var metadata: [String: Any] = [:]
    private var lastElapsedUpdate: TimeInterval = 0
    private var lastDuration: TimeInterval = 0
    private var lastArtworkURL: URL?
    private var isConfigured = false
    private var playHandler: (() -> Void)?
    private var pauseHandler: (() -> Void)?
    private var toggleHandler: (() -> Void)?
    private var nextHandler: (() -> Void)?
    private var previousHandler: (() -> Void)?
    private var seekHandler: ((Double) -> Void)?
    private var skipForwardHandler: (() -> Void)?
    private var skipBackwardHandler: (() -> Void)?
    private var skipIntervalSeconds: Double = 15
    #endif

    func configureRemoteCommands(
        onPlay: @escaping () -> Void,
        onPause: @escaping () -> Void,
        onNext: (() -> Void)?,
        onPrevious: (() -> Void)?,
        onSeek: @escaping (Double) -> Void,
        onToggle: (() -> Void)? = nil,
        onSkipForward: (() -> Void)? = nil,
        onSkipBackward: (() -> Void)? = nil,
        skipIntervalSeconds: Double = 15
    ) {
        #if canImport(MediaPlayer)
        playHandler = onPlay
        pauseHandler = onPause
        toggleHandler = onToggle
        nextHandler = onNext
        previousHandler = onPrevious
        seekHandler = onSeek
        skipForwardHandler = onSkipForward
        skipBackwardHandler = onSkipBackward
        self.skipIntervalSeconds = skipIntervalSeconds

        if !isConfigured {
            isConfigured = true
            let center = MPRemoteCommandCenter.shared()

            center.playCommand.addTarget { [weak self] _ in
                self?.invokeHandler(self?.playHandler)
                return .success
            }
            center.pauseCommand.addTarget { [weak self] _ in
                self?.invokeHandler(self?.pauseHandler)
                return .success
            }
            center.togglePlayPauseCommand.addTarget { [weak self] _ in
                if let handler = self?.toggleHandler {
                    self?.invokeHandler(handler)
                } else {
                    self?.invokeHandler(self?.playHandler)
                }
                return .success
            }
            center.nextTrackCommand.addTarget { [weak self] _ in
                self?.invokeHandler(self?.nextHandler)
                return .success
            }
            center.previousTrackCommand.addTarget { [weak self] _ in
                self?.invokeHandler(self?.previousHandler)
                return .success
            }
            center.changePlaybackPositionCommand.addTarget { [weak self] event in
                guard let event = event as? MPChangePlaybackPositionCommandEvent else {
                    return .commandFailed
                }
                Task { @MainActor [weak self] in
                    self?.seekHandler?(event.positionTime)
                }
                return .success
            }
            center.skipForwardCommand.addTarget { [weak self] _ in
                self?.invokeHandler(self?.skipForwardHandler)
                return .success
            }
            center.skipBackwardCommand.addTarget { [weak self] _ in
                self?.invokeHandler(self?.skipBackwardHandler)
                return .success
            }
        }

        let center = MPRemoteCommandCenter.shared()
        center.playCommand.isEnabled = true
        center.pauseCommand.isEnabled = true
        center.togglePlayPauseCommand.isEnabled = true
        center.nextTrackCommand.isEnabled = onNext != nil
        center.previousTrackCommand.isEnabled = onPrevious != nil
        center.changePlaybackPositionCommand.isEnabled = true
        let skipInterval = max(skipIntervalSeconds, 1)
        center.skipForwardCommand.isEnabled = onSkipForward != nil
        center.skipBackwardCommand.isEnabled = onSkipBackward != nil
        center.skipForwardCommand.preferredIntervals = [NSNumber(value: skipInterval)]
        center.skipBackwardCommand.preferredIntervals = [NSNumber(value: skipInterval)]

        #if os(iOS)
        UIApplication.shared.beginReceivingRemoteControlEvents()
        #endif
        #endif
    }

    func updateMetadata(
        title: String,
        artist: String?,
        album: String?,
        artworkURL: URL?,
        queueIndex: Int? = nil,
        queueCount: Int? = nil,
        mediaType: MPNowPlayingInfoMediaType? = nil
    ) {
        #if canImport(MediaPlayer)
        metadata[MPMediaItemPropertyTitle] = title
        if let artist {
            metadata[MPMediaItemPropertyArtist] = artist
        }
        if let album {
            metadata[MPMediaItemPropertyAlbumTitle] = album
        }
        if let mediaType {
            metadata[MPNowPlayingInfoPropertyMediaType] = mediaType.rawValue
        } else {
            metadata.removeValue(forKey: MPNowPlayingInfoPropertyMediaType)
        }
        if let queueIndex, queueIndex >= 0 {
            metadata[MPNowPlayingInfoPropertyPlaybackQueueIndex] = queueIndex
        } else {
            metadata.removeValue(forKey: MPNowPlayingInfoPropertyPlaybackQueueIndex)
        }
        if let queueCount, queueCount > 0 {
            metadata[MPNowPlayingInfoPropertyPlaybackQueueCount] = queueCount
        } else {
            metadata.removeValue(forKey: MPNowPlayingInfoPropertyPlaybackQueueCount)
        }
        applyNowPlaying()

        guard let artworkURL else { return }
        if lastArtworkURL == artworkURL {
            return
        }
        lastArtworkURL = artworkURL
        Task.detached { [weak self] in
            guard let self else { return }
            do {
                let (data, _) = try await URLSession.shared.data(from: artworkURL)
                if let image = UIImage(data: data) {
                    let artwork = MPMediaItemArtwork(boundsSize: image.size) { _ in image }
                    await MainActor.run {
                        self.metadata[MPMediaItemPropertyArtwork] = artwork
                        self.applyNowPlaying()
                    }
                }
            } catch {
                return
            }
        }
        #endif
    }

    func updatePlaybackState(isPlaying: Bool, position: Double, duration: Double) {
        #if canImport(MediaPlayer)
        let clamped = max(0, position)
        if abs(clamped - lastElapsedUpdate) > 0.5 || duration != lastDuration {
            metadata[MPNowPlayingInfoPropertyElapsedPlaybackTime] = clamped
            metadata[MPMediaItemPropertyPlaybackDuration] = max(duration, 0)
            lastElapsedUpdate = clamped
            lastDuration = duration
        }
        metadata[MPNowPlayingInfoPropertyPlaybackRate] = isPlaying ? 1.0 : 0.0
        applyNowPlaying()
        #endif
    }

    func clear() {
        #if canImport(MediaPlayer)
        metadata = [:]
        lastArtworkURL = nil
        MPNowPlayingInfoCenter.default().nowPlayingInfo = nil
        #endif
    }

    private func applyNowPlaying() {
        #if canImport(MediaPlayer)
        MPNowPlayingInfoCenter.default().nowPlayingInfo = metadata
        #endif
    }

    #if canImport(MediaPlayer)
    private func invokeHandler(_ handler: (() -> Void)?) {
        guard let handler else { return }
        Task { @MainActor in
            handler()
        }
    }
    #endif
}
