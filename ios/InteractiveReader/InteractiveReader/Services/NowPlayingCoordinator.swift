import Foundation
import OSLog

#if canImport(MediaPlayer)
import AVFoundation
import MediaPlayer
import UIKit
#endif

@MainActor
final class NowPlayingCoordinator: ObservableObject {
    private let logger = Logger(subsystem: "InteractiveReader", category: "NowPlaying")

    #if canImport(MediaPlayer)
    private var metadata: [String: Any] = [:]
    private var lastElapsedUpdate: TimeInterval = 0
    private var lastDuration: TimeInterval = 0
    private var lastArtworkURL: URL?
    private var isConfigured = false
    private var configuredRemoteCommandCenters: [MPRemoteCommandCenter] = []
    private var remoteCommandTargetRegistrations: [RemoteCommandTargetRegistration] = []
    private var currentPlaybackState: MPNowPlayingPlaybackState = .unknown
    #if os(iOS) || os(tvOS)
    private var nowPlayingSession: MPNowPlayingSession?
    private weak var attachedPlayer: AVPlayer?
    #endif
    private var playHandler: (() -> Void)?
    private var pauseHandler: (() -> Void)?
    private var toggleHandler: (() -> Void)?
    private var nextHandler: (() -> Void)?
    private var previousHandler: (() -> Void)?
    private var seekHandler: ((Double) -> Void)?
    private var skipForwardHandler: (() -> Void)?
    private var skipBackwardHandler: (() -> Void)?
    private var bookmarkHandler: (() -> Void)?
    private var skipIntervalSeconds: Double = 15
    private var lastLoggedTransportState: Bool?
    private var lastLoggedRemoteCommandsEnabled: Bool?
    private var lastLoggedSessionActive: Bool?
    private var lastLoggedSessionCanBecomeActive: Bool?
    #endif

    func attachPlayer(_ player: AVPlayer?) {
        #if canImport(MediaPlayer) && (os(iOS) || os(tvOS))
        guard #available(iOS 16.0, tvOS 14.0, *), let player else { return }
        if attachedPlayer === player {
            if !metadata.isEmpty {
                applyNowPlaying()
            } else {
                activateNowPlayingSessionIfPossible()
            }
            return
        }
        attachedPlayer = player
        removeRemoteCommandTargets()
        let session = MPNowPlayingSession(players: [player])
        session.automaticallyPublishesNowPlayingInfo = false
        nowPlayingSession = session
        configuredRemoteCommandCenters = []
        isConfigured = false
        lastLoggedSessionActive = nil
        lastLoggedSessionCanBecomeActive = nil
        if !metadata.isEmpty {
            session.nowPlayingInfoCenter.nowPlayingInfo = metadata
        }
        logger.info("Reader NowPlaying session attached player=true")
        activateNowPlayingSessionIfPossible()
        #endif
    }

    func configureRemoteCommands(
        onPlay: @escaping () -> Void,
        onPause: @escaping () -> Void,
        onNext: (() -> Void)?,
        onPrevious: (() -> Void)?,
        onSeek: @escaping (Double) -> Void,
        onToggle: (() -> Void)? = nil,
        onSkipForward: (() -> Void)? = nil,
        onSkipBackward: (() -> Void)? = nil,
        onBookmark: (() -> Void)? = nil,
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
        bookmarkHandler = onBookmark
        self.skipIntervalSeconds = skipIntervalSeconds

        let centers = remoteCommandCentersForReader
        let staleCenters = configuredRemoteCommandCenters.filter { previous in
            !centers.contains { $0 === previous }
        }
        for stale in staleCenters {
            setRemoteCommands(false, on: stale)
        }
        removeRemoteCommandTargets(on: staleCenters)

        for center in centers where !configuredRemoteCommandCenters.contains(where: { $0 === center }) {
            addRemoteCommandTargets(on: center)
        }
        isConfigured = true
        configuredRemoteCommandCenters = centers

        for center in centers {
            setRemoteCommands(true, on: center)
        }

        #if os(iOS)
        UIApplication.shared.beginReceivingRemoteControlEvents()
        #endif
        #endif
    }

    /// Enable or disable remote command center controls.
    /// Disable when Apple Music should own the lock screen; re-enable when narration takes over.
    func setRemoteCommandsEnabled(_ enabled: Bool) {
        #if canImport(MediaPlayer)
        guard isConfigured else { return }
        let centers = configuredRemoteCommandCenters.isEmpty
            ? remoteCommandCentersForReader
            : configuredRemoteCommandCenters
        for center in centers {
            setRemoteCommands(enabled, on: center)
        }
        if lastLoggedRemoteCommandsEnabled != enabled {
            logger.info("Reader NowPlaying remoteCommandsEnabled=\(enabled, privacy: .public)")
            lastLoggedRemoteCommandsEnabled = enabled
        }
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
        logger.debug(
            "Reader NowPlaying metadata published titlePresent=\((!title.isEmpty), privacy: .public) artistPresent=\((artist?.isEmpty == false), privacy: .public) albumPresent=\((album?.isEmpty == false), privacy: .public) queueIndex=\((queueIndex ?? -1), privacy: .public) queueCount=\((queueCount ?? -1), privacy: .public)"
        )

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

    func updatePlaybackState(isPlaying: Bool, position: Double, duration: Double, force: Bool = false) {
        #if canImport(MediaPlayer)
        let clamped = max(0, position)
        var didUpdate = false
        if force || abs(clamped - lastElapsedUpdate) > 0.5 || duration != lastDuration {
            metadata[MPNowPlayingInfoPropertyElapsedPlaybackTime] = clamped
            metadata[MPMediaItemPropertyPlaybackDuration] = max(duration, 0)
            lastElapsedUpdate = clamped
            lastDuration = duration
            didUpdate = true
        }
        let playbackRate = isPlaying ? 1.0 : 0.0
        let storedRate = (metadata[MPNowPlayingInfoPropertyPlaybackRate] as? NSNumber)?.doubleValue
        if force || storedRate != playbackRate {
            metadata[MPNowPlayingInfoPropertyPlaybackRate] = playbackRate
            didUpdate = true
        }
        if didUpdate || force {
            applyNowPlaying()
        }
        applyPlaybackState(isPlaying ? .playing : .paused)
        if force || lastLoggedTransportState != isPlaying {
            let stateLabel = isPlaying ? "playing" : "paused"
            logger.info(
                "Reader NowPlaying transport=\(stateLabel, privacy: .public) playbackRate=\(playbackRate, privacy: .public) force=\(force, privacy: .public) position=\(clamped, privacy: .public) duration=\(duration, privacy: .public)"
            )
            lastLoggedTransportState = isPlaying
        }
        #endif
    }

    func reassertReaderSession() {
        #if canImport(MediaPlayer)
        if !metadata.isEmpty {
            applyNowPlaying()
        }
        #if os(iOS) || os(tvOS)
        activateNowPlayingSessionIfPossible(forceLog: true)
        #endif
        #if os(iOS)
        UIApplication.shared.beginReceivingRemoteControlEvents()
        #endif
        logger.info(
            "Reader NowPlaying session reassert requested metadata=\((!self.metadata.isEmpty), privacy: .public) stateKnown=\((self.currentPlaybackState != .unknown), privacy: .public)"
        )
        #endif
    }

    func clear() {
        #if canImport(MediaPlayer)
        metadata = [:]
        lastElapsedUpdate = -1
        lastDuration = -1
        lastArtworkURL = nil
        lastLoggedTransportState = nil
        lastLoggedRemoteCommandsEnabled = nil
        lastLoggedSessionActive = nil
        lastLoggedSessionCanBecomeActive = nil
        currentPlaybackState = .unknown
        setRemoteCommandsEnabled(false)
        removeRemoteCommandTargets()
        configuredRemoteCommandCenters = []
        isConfigured = false
        clearNowPlayingInfo()
        logger.info("Reader NowPlaying cleared")
        #endif
    }

    private func applyNowPlaying() {
        #if canImport(MediaPlayer)
        MPNowPlayingInfoCenter.default().nowPlayingInfo = metadata
        applyPlaybackState(currentPlaybackState)
        #if os(iOS) || os(tvOS)
        if #available(iOS 16.0, tvOS 14.0, *), let nowPlayingSession {
            nowPlayingSession.nowPlayingInfoCenter.nowPlayingInfo = metadata
            activateNowPlayingSessionIfPossible()
        }
        #endif
        #endif
    }

    #if canImport(MediaPlayer)
    private func applyPlaybackState(_ state: MPNowPlayingPlaybackState) {
        currentPlaybackState = state
        if #available(iOS 13.0, tvOS 13.0, *) {
            MPNowPlayingInfoCenter.default().playbackState = state
            #if os(iOS) || os(tvOS)
            if let nowPlayingSession {
                nowPlayingSession.nowPlayingInfoCenter.playbackState = state
            }
            #endif
        }
    }

    private var activeRemoteCommandCenter: MPRemoteCommandCenter {
        #if os(iOS) || os(tvOS)
        if #available(iOS 16.0, tvOS 14.0, *), let nowPlayingSession {
            return nowPlayingSession.remoteCommandCenter
        }
        #endif
        return MPRemoteCommandCenter.shared()
    }

    private var remoteCommandCentersForReader: [MPRemoteCommandCenter] {
        let active = activeRemoteCommandCenter
        let shared = MPRemoteCommandCenter.shared()
        if active === shared {
            return [active]
        }
        return [active, shared]
    }

    private func addRemoteCommandTargets(on center: MPRemoteCommandCenter) {
        let playTarget = center.playCommand.addTarget { [weak self] _ in
            self?.logger.debug("Remote play command fired")
            self?.invokeHandler(self?.playHandler)
            return .success
        }
        remoteCommandTargetRegistrations.append(
            RemoteCommandTargetRegistration(center: center, command: center.playCommand, target: playTarget)
        )
        let pauseTarget = center.pauseCommand.addTarget { [weak self] _ in
            self?.logger.debug("Remote pause command fired")
            self?.invokeHandler(self?.pauseHandler)
            return .success
        }
        remoteCommandTargetRegistrations.append(
            RemoteCommandTargetRegistration(center: center, command: center.pauseCommand, target: pauseTarget)
        )
        let toggleTarget = center.togglePlayPauseCommand.addTarget { [weak self] _ in
            self?.logger.debug("Remote toggle play/pause command fired")
            if let handler = self?.toggleHandler {
                self?.invokeHandler(handler)
            } else {
                self?.invokeHandler(self?.playHandler)
            }
            return .success
        }
        remoteCommandTargetRegistrations.append(
            RemoteCommandTargetRegistration(center: center, command: center.togglePlayPauseCommand, target: toggleTarget)
        )
        let nextTarget = center.nextTrackCommand.addTarget { [weak self] _ in
            self?.invokeHandler(self?.nextHandler)
            return .success
        }
        remoteCommandTargetRegistrations.append(
            RemoteCommandTargetRegistration(center: center, command: center.nextTrackCommand, target: nextTarget)
        )
        let previousTarget = center.previousTrackCommand.addTarget { [weak self] _ in
            self?.invokeHandler(self?.previousHandler)
            return .success
        }
        remoteCommandTargetRegistrations.append(
            RemoteCommandTargetRegistration(center: center, command: center.previousTrackCommand, target: previousTarget)
        )
        let positionTarget = center.changePlaybackPositionCommand.addTarget { [weak self] event in
            guard let event = event as? MPChangePlaybackPositionCommandEvent else {
                return .commandFailed
            }
            Task { @MainActor [weak self] in
                self?.seekHandler?(event.positionTime)
            }
            return .success
        }
        remoteCommandTargetRegistrations.append(
            RemoteCommandTargetRegistration(center: center, command: center.changePlaybackPositionCommand, target: positionTarget)
        )
        let skipForwardTarget = center.skipForwardCommand.addTarget { [weak self] _ in
            self?.invokeHandler(self?.skipForwardHandler)
            return .success
        }
        remoteCommandTargetRegistrations.append(
            RemoteCommandTargetRegistration(center: center, command: center.skipForwardCommand, target: skipForwardTarget)
        )
        let skipBackwardTarget = center.skipBackwardCommand.addTarget { [weak self] _ in
            self?.invokeHandler(self?.skipBackwardHandler)
            return .success
        }
        remoteCommandTargetRegistrations.append(
            RemoteCommandTargetRegistration(center: center, command: center.skipBackwardCommand, target: skipBackwardTarget)
        )
        #if os(iOS)
        let bookmarkTarget = center.bookmarkCommand.addTarget { [weak self] _ in
            self?.invokeHandler(self?.bookmarkHandler)
            return .success
        }
        remoteCommandTargetRegistrations.append(
            RemoteCommandTargetRegistration(center: center, command: center.bookmarkCommand, target: bookmarkTarget)
        )
        #endif
    }

    private func removeRemoteCommandTargets(on centers: [MPRemoteCommandCenter]? = nil) {
        guard !remoteCommandTargetRegistrations.isEmpty else { return }
        remoteCommandTargetRegistrations.removeAll { registration in
            let shouldRemove: Bool
            if let centers {
                guard let center = registration.center else {
                    shouldRemove = true
                    registration.command.removeTarget(registration.target)
                    return shouldRemove
                }
                shouldRemove = centers.contains { $0 === center }
            } else {
                shouldRemove = true
            }
            if shouldRemove {
                registration.command.removeTarget(registration.target)
            }
            return shouldRemove
        }
    }

    private func setRemoteCommands(_ enabled: Bool, on center: MPRemoteCommandCenter) {
        center.playCommand.isEnabled = enabled
        center.pauseCommand.isEnabled = enabled
        center.togglePlayPauseCommand.isEnabled = enabled
        center.nextTrackCommand.isEnabled = enabled && nextHandler != nil
        center.previousTrackCommand.isEnabled = enabled && previousHandler != nil
        center.changePlaybackPositionCommand.isEnabled = enabled
        let skipInterval = max(skipIntervalSeconds, 1)
        center.skipForwardCommand.isEnabled = enabled && skipForwardHandler != nil
        center.skipBackwardCommand.isEnabled = enabled && skipBackwardHandler != nil
        center.skipForwardCommand.preferredIntervals = [NSNumber(value: skipInterval)]
        center.skipBackwardCommand.preferredIntervals = [NSNumber(value: skipInterval)]
        #if os(iOS)
        center.bookmarkCommand.isEnabled = enabled && bookmarkHandler != nil
        if bookmarkHandler != nil {
            center.bookmarkCommand.localizedTitle = "Bookmark"
            center.bookmarkCommand.localizedShortTitle = "Bookmark"
        }
        if enabled {
            UIApplication.shared.beginReceivingRemoteControlEvents()
        } else {
            UIApplication.shared.endReceivingRemoteControlEvents()
        }
        #endif
    }

    private func clearNowPlayingInfo() {
        MPNowPlayingInfoCenter.default().nowPlayingInfo = nil
        applyPlaybackState(.unknown)
        #if os(iOS) || os(tvOS)
        if #available(iOS 16.0, tvOS 14.0, *), let nowPlayingSession {
            nowPlayingSession.nowPlayingInfoCenter.nowPlayingInfo = nil
        }
        #endif
    }

    private func activateNowPlayingSessionIfPossible(forceLog: Bool = false) {
        #if os(iOS) || os(tvOS)
        guard #available(iOS 16.0, tvOS 14.0, *), let nowPlayingSession else { return }
        let canBecomeActive = nowPlayingSession.canBecomeActive
        nowPlayingSession.becomeActiveIfPossible { [weak self] isActive in
            Task { @MainActor in
                guard let self else { return }
                guard forceLog ||
                    self.lastLoggedSessionActive != isActive ||
                    self.lastLoggedSessionCanBecomeActive != canBecomeActive
                else {
                    return
                }
                self.logger.info(
                    "Reader NowPlaying session active=\(isActive, privacy: .public) canBecomeActive=\(canBecomeActive, privacy: .public)"
                )
                self.lastLoggedSessionActive = isActive
                self.lastLoggedSessionCanBecomeActive = canBecomeActive
            }
        }
        #endif
    }

    private func invokeHandler(_ handler: (() -> Void)?) {
        guard let handler else { return }
        Task { @MainActor in
            handler()
        }
    }
    #endif
}

#if canImport(MediaPlayer)
private final class RemoteCommandTargetRegistration {
    weak var center: MPRemoteCommandCenter?
    let command: MPRemoteCommand
    let target: Any

    init(center: MPRemoteCommandCenter, command: MPRemoteCommand, target: Any) {
        self.center = center
        self.command = command
        self.target = target
    }
}
#endif
