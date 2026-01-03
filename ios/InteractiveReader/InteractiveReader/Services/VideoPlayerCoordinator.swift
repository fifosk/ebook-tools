import AVFoundation
import Foundation

@MainActor
final class VideoPlayerCoordinator: ObservableObject {
    @Published private(set) var currentTime: Double = 0
    @Published private(set) var duration: Double = 0
    @Published private(set) var isPlaying: Bool = false

    var onPlaybackEnded: (() -> Void)?

    private var player: AVPlayer?
    private var timeObserverToken: Any?
    private var statusObservation: NSKeyValueObservation?
    private var timeControlObservation: NSKeyValueObservation?
    private var endObserver: NSObjectProtocol?

    func load(url: URL, autoPlay: Bool = false) {
        tearDownPlayer()
        currentTime = 0
        duration = 0
        isPlaying = false
        configureAudioSession()
        let item = AVPlayerItem(url: url)
        let player = AVPlayer(playerItem: item)
        #if os(iOS)
        player.allowsExternalPlayback = true
        player.usesExternalPlaybackWhileExternalScreenIsActive = true
        #endif
        self.player = player
        observeStatus(for: item)
        observeTimeControl(for: player)
        installTimeObserver(on: player)
        installEndObserver(for: item)
        if autoPlay {
            play()
        }
    }

    func playerInstance() -> AVPlayer? {
        player
    }

    func play() {
        configureAudioSession()
        player?.play()
    }

    func pause() {
        player?.pause()
    }

    func togglePlayback() {
        guard let player = player else {
            play()
            return
        }
        if player.timeControlStatus == .playing || player.rate > 0 {
            pause()
        } else {
            play()
        }
    }

    func seek(to time: Double) {
        guard let player = player else { return }
        let clamped = max(0, min(time, duration))
        let cmTime = CMTime(seconds: clamped, preferredTimescale: 600)
        player.seek(to: cmTime, toleranceBefore: .zero, toleranceAfter: .zero)
        currentTime = clamped
    }

    func skip(by delta: Double) {
        seek(to: currentTime + delta)
    }

    func reset() {
        tearDownPlayer()
        currentTime = 0
        duration = 0
        isPlaying = false
    }

    private func observeStatus(for item: AVPlayerItem) {
        statusObservation = item.observe(\.status, options: [.new, .initial]) { [weak self] observedItem, _ in
            guard let self else { return }
            Task { @MainActor in
                switch observedItem.status {
                case .readyToPlay:
                    if observedItem.duration.isNumeric {
                        self.duration = observedItem.duration.seconds
                    }
                case .failed:
                    print("AVPlayerItem failed: \(String(describing: observedItem.error))")
                    if let errorLog = observedItem.errorLog() {
                        for event in errorLog.events {
                            let status = event.errorStatusCode
                            let comment = event.errorComment ?? ""
                            print("AVPlayerItem ErrorLog: status=\(status) comment=\(comment)")
                        }
                    }
                default:
                    break
                }
            }
        }
    }

    private func observeTimeControl(for player: AVPlayer) {
        timeControlObservation = player.observe(\.timeControlStatus, options: [.new, .initial]) { [weak self] player, _ in
            guard let self else { return }
            Task { @MainActor in
                self.isPlaying = player.timeControlStatus == .playing
            }
        }
    }

    private func installTimeObserver(on player: AVPlayer) {
        let token = player.addPeriodicTimeObserver(
            forInterval: CMTime(seconds: 0.1, preferredTimescale: 600),
            queue: .main
        ) { [weak self] time in
            guard let self else { return }
            Task { @MainActor in
                self.currentTime = time.seconds
                if let duration = player.currentItem?.duration, duration.isNumeric {
                    self.duration = duration.seconds
                }
            }
        }
        timeObserverToken = token
    }

    private func configureAudioSession() {
        #if os(iOS)
        let session = AVAudioSession.sharedInstance()
        let options: AVAudioSession.CategoryOptions = [.allowAirPlay]
        try? session.setCategory(.playback, mode: .moviePlayback, options: options)
        try? session.setActive(true)
        #endif
    }

    private func installEndObserver(for item: AVPlayerItem) {
        endObserver = NotificationCenter.default.addObserver(
            forName: .AVPlayerItemDidPlayToEndTime,
            object: item,
            queue: .main
        ) { [weak self] _ in
            Task { @MainActor in
                guard let self else { return }
                self.isPlaying = false
                self.onPlaybackEnded?()
            }
        }
    }

    private func tearDownPlayer() {
        if let token = timeObserverToken {
            player?.removeTimeObserver(token)
            timeObserverToken = nil
        }
        if let observer = endObserver {
            NotificationCenter.default.removeObserver(observer)
            endObserver = nil
        }
        statusObservation = nil
        timeControlObservation = nil
        player?.pause()
        player = nil
    }
}
