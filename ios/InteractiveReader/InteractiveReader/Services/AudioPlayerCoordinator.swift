import AVFoundation
import Foundation

@MainActor
final class AudioPlayerCoordinator: ObservableObject {
    @Published private(set) var isPlaying = false
    @Published private(set) var currentTime: Double = 0
    @Published private(set) var duration: Double = 0
    @Published private(set) var isReady = false
    @Published private(set) var activeURL: URL?
    var onPlaybackEnded: (() -> Void)?

    private var player: AVPlayer?
    private var timeObserverToken: Any?
    private var endObserver: NSObjectProtocol?
    private var statusObservation: NSKeyValueObservation?
    private var failureObserver: NSObjectProtocol?
    private var errorLogObserver: NSObjectProtocol?

    init() {
        configureAudioSession()
    }

    func load(url: URL, autoPlay: Bool = false) {
        if activeURL == url {
            if autoPlay {
                play()
            }
            return
        }
        tearDownPlayer()
        activeURL = url
        let item = AVPlayerItem(url: url)
        let player = AVPlayer(playerItem: item)
        self.player = player
        observeStatus(for: item)
        installTimeObserver(on: player)
        installEndObserver(for: item)
        installErrorObservers(for: item)
        if autoPlay {
            play()
        } else {
            isPlaying = false
        }
    }

    func play() {
        guard let player = player else { return }
        player.play()
        isPlaying = true
    }

    func pause() {
        player?.pause()
        isPlaying = false
    }

    func togglePlayback() {
        isPlaying ? pause() : play()
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
                self.currentTime = time.seconds
                if let duration = self.player?.currentItem?.duration, duration.isNumeric {
                    self.duration = duration.seconds
                }
            }
        }
        timeObserverToken = token
    }

    private func installEndObserver(for item: AVPlayerItem) {
        endObserver = NotificationCenter.default.addObserver(
            forName: .AVPlayerItemDidPlayToEndTime,
            object: item,
            queue: .main
        ) { [weak self] _ in
            Task { @MainActor [weak self] in
                guard let self else { return }
                self.isPlaying = false
                self.currentTime = 0
                self.onPlaybackEnded?()
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
    }
}
