import AVFoundation
import Foundation

@MainActor
final class VideoPlayerCoordinator: ObservableObject {
    @Published private(set) var currentTime: Double = 0
    @Published private(set) var duration: Double = 0
    @Published private(set) var isPlaying: Bool = false

    private var player: AVPlayer?
    private var timeObserverToken: Any?
    private var statusObservation: NSKeyValueObservation?
    private var timeControlObservation: NSKeyValueObservation?
    private var endObserver: NSObjectProtocol?

    func load(url: URL) {
        tearDownPlayer()
        let item = AVPlayerItem(url: url)
        let player = AVPlayer(playerItem: item)
        self.player = player
        observeStatus(for: item)
        observeTimeControl(for: player)
        installTimeObserver(on: player)
        installEndObserver(for: item)
    }

    func playerInstance() -> AVPlayer? {
        player
    }

    func play() {
        player?.play()
    }

    func pause() {
        player?.pause()
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
            forInterval: CMTime(seconds: 0.25, preferredTimescale: 600),
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

    private func installEndObserver(for item: AVPlayerItem) {
        endObserver = NotificationCenter.default.addObserver(
            forName: .AVPlayerItemDidPlayToEndTime,
            object: item,
            queue: .main
        ) { [weak self] _ in
            Task { @MainActor in
                self?.isPlaying = false
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

