import AVFoundation
import Foundation

@MainActor
final class AudioPlayerCoordinator: ObservableObject {
    @Published private(set) var isPlaying = false
    @Published private(set) var currentTime: Double = 0
    @Published private(set) var duration: Double = 0
    @Published private(set) var isReady = false
    @Published private(set) var playbackRate: Double = 1.0
    @Published private(set) var volume: Double = 1.0
    @Published private(set) var activeURL: URL?
    @Published private(set) var activeURLs: [URL] = []
    var onPlaybackEnded: (() -> Void)?

    private var shouldLoop = false
    private var player: AVPlayer?
    private var timeObserverToken: Any?
    private var endObserver: NSObjectProtocol?
    private var statusObservation: NSKeyValueObservation?
    private var failureObserver: NSObjectProtocol?
    private var errorLogObserver: NSObjectProtocol?
    private var itemURLMap: [ObjectIdentifier: URL] = [:]
    private var itemOrder: [ObjectIdentifier: Int] = [:]

    init() {
        configureAudioSession()
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
        if activeURLs == sanitized {
            if player?.currentItem == nil {
                tearDownPlayer()
            } else {
                if autoPlay {
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
        if let first = items.first {
            observeStatus(for: first)
            installErrorObservers(for: first)
        }
        installTimeObserver(on: player)
        installEndObserver(for: player)
        if autoPlay {
            play()
        } else {
            isPlaying = false
        }
    }

    func play() {
        guard let player = player else { return }
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
    }

    func togglePlayback() {
        isPlaying ? pause() : play()
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
        tearDownPlayer()
    }

    deinit {
        tearDownPlayerAsync()
    }

    private func configureAudioSession() {
        #if os(iOS)
        let session = AVAudioSession.sharedInstance()
        try? session.setCategory(.playback, mode: .spokenAudio, options: [.mixWithOthers])
        try? session.setActive(true)
        #endif
    }

    private func observeStatus(for item: AVPlayerItem) {
        statusObservation = item.observe(\.status, options: [.new, .initial]) { [weak self] observedItem, _ in
            guard let self else { return }
            Task { @MainActor in
                switch observedItem.status {
                case .readyToPlay:
                    self.isReady = true
                    if observedItem.duration.isNumeric {
                        self.duration = observedItem.duration.seconds
                    }
                case .failed:
                    self.isReady = false
                    self.isPlaying = false
                default:
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
                        self?.play()
                    }
                    return
                }
                self.updateActiveURL()
                if index < self.activeURLs.count - 1 {
                    self.currentTime = 0
                    return
                }
                self.isPlaying = false
                self.currentTime = 0
                self.onPlaybackEnded?()
                return
            }
        }
    }

    private func installErrorObservers(for item: AVPlayerItem) {
        failureObserver = NotificationCenter.default.addObserver(
            forName: .AVPlayerItemFailedToPlayToEndTime,
            object: item,
            queue: .main
        ) { notification in
            Task { @MainActor in
                if let error = notification.userInfo?[AVPlayerItemFailedToPlayToEndTimeErrorKey] as? NSError {
                    print("Audio playback failed: \(error.domain) (\(error.code)) – \(error.localizedDescription)")
                } else {
                    print("Audio playback failed with unknown error")
                }
            }
        }
        errorLogObserver = NotificationCenter.default.addObserver(
            forName: .AVPlayerItemNewErrorLogEntry,
            object: item,
            queue: .main
        ) { [weak item] _ in
            Task { @MainActor in
                guard let logEvent = item?.errorLog()?.events.last else { return }
                print("AVPlayer error log: status=\(logEvent.errorStatusCode) uri=\(logEvent.uri ?? "n/a") comment=\(logEvent.errorComment ?? "n/a")")
            }
        }
    }

    private func tearDownPlayer() {
        _tearDownPlayerOnMain()
    }

    nonisolated private func tearDownPlayerAsync() {
        Task { @MainActor in
            self._tearDownPlayerOnMain()
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
