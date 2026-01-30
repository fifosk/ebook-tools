import AVFoundation
import Foundation

enum AudioPlaybackRole {
    case primary
    case ambient
}

@MainActor
final class AudioPlayerCoordinator: ObservableObject, PlayerCoordinating {
    @Published private(set) var isPlaying = false
    @Published private(set) var isPlaybackRequested = false
    @Published private(set) var currentTime: Double = 0
    @Published private(set) var duration: Double = 0
    @Published private(set) var isReady = false
    @Published private(set) var playbackRate: Double = 1.0
    @Published private(set) var volume: Double = 1.0
    @Published private(set) var activeURL: URL?
    @Published private(set) var activeURLs: [URL] = []
    var onPlaybackEnded: (() -> Void)?

    let role: AudioPlaybackRole
    private var shouldLoop = false
    private var player: AVPlayer?
    private var timeObserverToken: Any?
    private var endObserver: NSObjectProtocol?
    private var statusObservation: NSKeyValueObservation?
    private var timeControlObservation: NSKeyValueObservation?
    private var failureObserver: NSObjectProtocol?
    private var errorLogObserver: NSObjectProtocol?
    private var interruptionObserver: NSObjectProtocol?
    private var shouldResumeAfterInterruption = false
    private var itemURLMap: [ObjectIdentifier: URL] = [:]
    private var itemOrder: [ObjectIdentifier: Int] = [:]

    init(role: AudioPlaybackRole = .primary) {
        self.role = role
        configureAudioSession()
        installInterruptionObserver()
    }

    func load(url: URL, autoPlay: Bool = false) {
        load(urls: [url], autoPlay: autoPlay)
    }

    func load(urls: [URL], autoPlay: Bool = false) {
        let sanitized = urls
        guard !sanitized.isEmpty else {
            reset()
            return
        }
        print("[AudioPlayer] Loading URLs: \(sanitized.map { $0.absoluteString })")
        let shouldAutoPlay = autoPlay || isPlaybackRequested
        if activeURLs == sanitized {
            if player?.currentItem == nil {
                tearDownPlayer()
            } else {
                if shouldAutoPlay {
                    play()
                }
                return
            }
        }
        tearDownPlayer()
        activeURLs = sanitized
        activeURL = sanitized.first
        itemURLMap = [:]
        let items = sanitized.enumerated().map { index, url -> AVPlayerItem in
            let item = AVPlayerItem(url: url)
            item.audioTimePitchAlgorithm = .timeDomain
            let identifier = ObjectIdentifier(item)
            itemURLMap[identifier] = url
            itemOrder[identifier] = index
            return item
        }
        let player: AVPlayer
        if items.count > 1 {
            player = AVQueuePlayer(items: items)
        } else {
            player = AVPlayer(playerItem: items[0])
        }
        self.player = player
        player.volume = Float(volume)
        observeTimeControlStatus(for: player)
        if let first = items.first {
            observeStatus(for: first)
            installErrorObservers(for: first)
        }
        installTimeObserver(on: player)
        installEndObserver(for: player)
        isPlaybackRequested = shouldAutoPlay
        if shouldAutoPlay {
            play()
        } else {
            isPlaying = false
        }
    }

    func play() {
        guard let player = player else { return }
        configureAudioSession()
        AudioPlaybackRegistry.shared.beginPlayback(for: self)
        isPlaybackRequested = true
        print("[AudioPlayer] play() called for URL: \(activeURL?.absoluteString ?? "nil")")
        if #available(iOS 10.0, tvOS 10.0, *) {
            player.playImmediately(atRate: Float(playbackRate))
        } else {
            player.play()
            player.rate = Float(playbackRate)
        }
        isPlaying = true
    }

    func pause() {
        player?.pause()
        isPlaying = false
        isPlaybackRequested = false
        AudioPlaybackRegistry.shared.endPlayback(for: self)
    }

    func togglePlayback() {
        isPlaybackRequested ? pause() : play()
    }

    func setPlaybackRate(_ rate: Double) {
        guard rate.isFinite, rate > 0 else { return }
        playbackRate = rate
        if isPlaying {
            player?.rate = Float(rate)
        }
    }

    func setVolume(_ value: Double) {
        let clamped = min(max(value, 0), 1)
        volume = clamped
        player?.volume = Float(clamped)
    }

    func setLooping(_ loop: Bool) {
        shouldLoop = loop
    }

    func seek(to time: Double) {
        guard let player = player else { return }
        let clamped = max(0, min(time, duration))
        let cmTime = CMTime(seconds: clamped, preferredTimescale: 600)
        player.seek(to: cmTime, toleranceBefore: .zero, toleranceAfter: .zero)
        currentTime = clamped
    }

    func reset() {
        pause()
        currentTime = 0
        duration = 0
        isReady = false
        activeURL = nil
        activeURLs = []
        isPlaybackRequested = false
        tearDownPlayer()
    }

    deinit {
        if let observer = interruptionObserver {
            NotificationCenter.default.removeObserver(observer)
            interruptionObserver = nil
        }
        tearDownPlayerAsync()
    }

    private func configureAudioSession() {
        #if os(iOS) || os(tvOS)
        // Only configure audio session for primary role to avoid conflicts
        // The ambient player will piggyback on the primary player's session
        guard role == .primary else { return }

        let session = AVAudioSession.sharedInstance()
        do {
            // Use playback category with spokenAudio mode for the main player
            // This allows background playback and proper audio routing
            try session.setCategory(.playback, mode: .spokenAudio, options: [])
            try session.setActive(true)
            print("[AudioSession] Configured: category=playback, mode=spokenAudio")
        } catch {
            print("[AudioSession] Failed to configure: \(error)")
        }
        #endif
    }

    private func installInterruptionObserver() {
        #if os(iOS) || os(tvOS)
        interruptionObserver = NotificationCenter.default.addObserver(
            forName: AVAudioSession.interruptionNotification,
            object: AVAudioSession.sharedInstance(),
            queue: .main
        ) { [weak self] notification in
            Task { @MainActor [weak self] in
                guard let self else { return }
                let info = notification.userInfo
                let rawType = info?[AVAudioSessionInterruptionTypeKey] as? UInt
                let type = rawType.flatMap { AVAudioSession.InterruptionType(rawValue: $0) }
                switch type {
                case .began:
                    self.shouldResumeAfterInterruption = self.isPlaying
                    self.isPlaying = false
                case .ended:
                    let optionsValue = info?[AVAudioSessionInterruptionOptionKey] as? UInt
                    let options = optionsValue.flatMap { AVAudioSession.InterruptionOptions(rawValue: $0) } ?? []
                    if self.shouldResumeAfterInterruption && options.contains(.shouldResume) {
                        self.play()
                    }
                    self.shouldResumeAfterInterruption = false
                default:
                    break
                }
            }
        }
        #endif
    }

    private func observeStatus(for item: AVPlayerItem) {
        statusObservation = item.observe(\.status, options: [.new, .initial]) { [weak self] observedItem, _ in
            guard let self else { return }
            Task { @MainActor in
                switch observedItem.status {
                case .readyToPlay:
                    print("[AudioPlayer] Item ready to play, duration: \(observedItem.duration.seconds)")
                    self.isReady = true
                    if observedItem.duration.isNumeric {
                        self.duration = observedItem.duration.seconds
                    }
                case .failed:
                    if let error = observedItem.error as NSError? {
                        print("[AudioPlayer] Item failed: \(error.domain) (\(error.code)) – \(error.localizedDescription)")
                        if let underlyingError = error.userInfo[NSUnderlyingErrorKey] as? NSError {
                            print("[AudioPlayer] Underlying: \(underlyingError.domain) (\(underlyingError.code)) – \(underlyingError.localizedDescription)")
                        }
                    } else {
                        print("[AudioPlayer] Item failed with unknown error")
                    }
                    self.isReady = false
                    self.isPlaying = false
                default:
                    break
                }
            }
        }
    }

    private func observeTimeControlStatus(for player: AVPlayer) {
        timeControlObservation = player.observe(\.timeControlStatus, options: [.new, .initial]) { [weak self] player, _ in
            guard let self else { return }
            Task { @MainActor in
                switch player.timeControlStatus {
                case .playing:
                    self.isPlaying = true
                case .paused:
                    self.isPlaying = false
                case .waitingToPlayAtSpecifiedRate:
                    break
                @unknown default:
                    break
                }
            }
        }
    }

    private func installTimeObserver(on player: AVPlayer) {
        let token = player.addPeriodicTimeObserver(forInterval: CMTime(seconds: 0.1, preferredTimescale: 600), queue: .main) {
            [weak self] time in
            Task { @MainActor [weak self] in
                guard let self else { return }
                self.updateActiveURL()
                self.currentTime = time.seconds
                if let duration = self.player?.currentItem?.duration, duration.isNumeric {
                    self.duration = duration.seconds
                }
            }
        }
        timeObserverToken = token
    }

    private func installEndObserver(for player: AVPlayer) {
        endObserver = NotificationCenter.default.addObserver(
            forName: .AVPlayerItemDidPlayToEndTime,
            object: nil,
            queue: .main
        ) { [weak self] notification in
            Task { @MainActor [weak self] in
                guard let self else { return }
                guard let endedItem = notification.object as? AVPlayerItem else { return }
                let identifier = ObjectIdentifier(endedItem)
                guard let index = self.itemOrder[identifier] else { return }
                if self.shouldLoop {
                    self.currentTime = 0
                    self.player?.seek(to: .zero, toleranceBefore: .zero, toleranceAfter: .zero) { [weak self] _ in
                        Task { @MainActor [weak self] in
                            self?.play()
                        }
                    }
                    return
                }
                self.updateActiveURL()
                if index < self.activeURLs.count - 1 {
                    self.currentTime = 0
                    return
                }
                self.isPlaying = false
                self.isPlaybackRequested = false
                self.currentTime = 0
                AudioPlaybackRegistry.shared.endPlayback(for: self)
                self.onPlaybackEnded?()
                return
            }
        }
    }

    private func installErrorObservers(for item: AVPlayerItem) {
        // Observe failures for ANY item (not just the first one) by passing nil as object
        failureObserver = NotificationCenter.default.addObserver(
            forName: .AVPlayerItemFailedToPlayToEndTime,
            object: nil,
            queue: .main
        ) { [weak self] notification in
            Task { @MainActor in
                guard let self else { return }
                // Verify the item belongs to our player
                guard let failedItem = notification.object as? AVPlayerItem,
                      self.itemURLMap[ObjectIdentifier(failedItem)] != nil else {
                    return
                }
                let failedURL = self.itemURLMap[ObjectIdentifier(failedItem)]
                if let error = notification.userInfo?[AVPlayerItemFailedToPlayToEndTimeErrorKey] as? NSError {
                    print("[AudioPlayer] Playback failed for URL \(failedURL?.absoluteString ?? "unknown"): \(error.domain) (\(error.code)) – \(error.localizedDescription)")
                } else {
                    print("[AudioPlayer] Playback failed for URL \(failedURL?.absoluteString ?? "unknown") with unknown error")
                }
            }
        }
        // Observe error logs for ANY item
        errorLogObserver = NotificationCenter.default.addObserver(
            forName: .AVPlayerItemNewErrorLogEntry,
            object: nil,
            queue: .main
        ) { [weak self] notification in
            Task { @MainActor in
                guard let self else { return }
                guard let errorItem = notification.object as? AVPlayerItem,
                      self.itemURLMap[ObjectIdentifier(errorItem)] != nil else {
                    return
                }
                guard let logEvent = errorItem.errorLog()?.events.last else { return }
                let errorURL = self.itemURLMap[ObjectIdentifier(errorItem)]
                print("[AudioPlayer] Error log for \(errorURL?.absoluteString ?? "unknown"): status=\(logEvent.errorStatusCode) uri=\(logEvent.uri ?? "n/a") comment=\(logEvent.errorComment ?? "n/a")")
            }
        }
    }

    private func tearDownPlayer() {
        _tearDownPlayerOnMain()
    }

    nonisolated private func tearDownPlayerAsync() {
        Task { @MainActor [weak self] in
            self?._tearDownPlayerOnMain()
        }
    }

    @MainActor
    private func _tearDownPlayerOnMain() {
        if let token = timeObserverToken {
            player?.removeTimeObserver(token)
            timeObserverToken = nil
        }
        if let observer = endObserver {
            NotificationCenter.default.removeObserver(observer)
            endObserver = nil
        }
        if let observer = failureObserver {
            NotificationCenter.default.removeObserver(observer)
            failureObserver = nil
        }
        if let observer = errorLogObserver {
            NotificationCenter.default.removeObserver(observer)
            errorLogObserver = nil
        }
        statusObservation = nil
        timeControlObservation = nil
        player?.pause()
        player = nil
        isPlaying = false
        isReady = false
        itemURLMap = [:]
        itemOrder = [:]
        activeURL = nil
        activeURLs = []
    }

    private func updateActiveURL() {
        guard let item = player?.currentItem else { return }
        let identifier = ObjectIdentifier(item)
        guard let url = itemURLMap[identifier] else { return }
        if activeURL != url {
            activeURL = url
        }
    }
}

@MainActor
private final class AudioPlaybackRegistry {
    static let shared = AudioPlaybackRegistry()
    private weak var activePrimary: AudioPlayerCoordinator?

    func beginPlayback(for coordinator: AudioPlayerCoordinator) {
        guard coordinator.role == .primary else { return }
        if let active = activePrimary, active !== coordinator {
            active.pause()
        }
        activePrimary = coordinator
    }

    func endPlayback(for coordinator: AudioPlayerCoordinator) {
        guard activePrimary === coordinator else { return }
        activePrimary = nil
    }
}
