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
    /// Current file index in multi-file playback (0-based)
    @Published private(set) var currentFileIndex: Int = 0
    /// Target volume level that should be restored after temporary muting (e.g., during track switches).
    /// This preserves the user's volume mix setting across sentence/track transitions.
    private(set) var targetVolume: Double = 1.0
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
    /// Per-file durations for multi-file playback (set via setFileDurations)
    private var fileDurations: [Double]?

    init(role: AudioPlaybackRole = .primary) {
        self.role = role
        configureAudioSession()
        installInterruptionObserver()
    }

    func load(url: URL, autoPlay: Bool = false, forceNoAutoPlay: Bool = false, preservePlaybackRequested: Bool = false) {
        load(urls: [url], autoPlay: autoPlay, forceNoAutoPlay: forceNoAutoPlay, preservePlaybackRequested: preservePlaybackRequested)
    }

    func load(urls: [URL], autoPlay: Bool = false, forceNoAutoPlay: Bool = false, preservePlaybackRequested: Bool = false) {
        let sanitized = urls
        guard !sanitized.isEmpty else {
            reset()
            return
        }
        print("[AudioPlayer] Loading URLs: \(sanitized.map { $0.absoluteString })")
        // forceNoAutoPlay overrides isPlaybackRequested to prevent audio bleed during track switches
        let shouldAutoPlay = forceNoAutoPlay ? false : (autoPlay || isPlaybackRequested)
        // preservePlaybackRequested keeps isPlaybackRequested = true during sequence transitions
        // so that reading bed doesn't pause when we switch tracks
        let wasPlaybackRequested = isPlaybackRequested
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
        // Preserve isPlaybackRequested during sequence transitions to prevent reading bed from pausing
        isPlaybackRequested = preservePlaybackRequested ? wasPlaybackRequested : shouldAutoPlay
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

    /// Pause playback temporarily without clearing isPlaybackRequested.
    /// Used during sequence dwell periods to prevent audio bleed while keeping
    /// the reading bed playing (which monitors isPlaybackRequested).
    func pauseForDwell() {
        player?.pause()
        isPlaying = false
        // NOTE: Intentionally NOT clearing isPlaybackRequested
        // This keeps reading bed playing during the brief dwell period
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

    /// Set the target volume that will be restored after temporary muting.
    /// Use this to persist volume mix settings across track/sentence transitions.
    func setTargetVolume(_ value: Double) {
        let clamped = min(max(value, 0), 1)
        targetVolume = clamped
        // Also apply immediately if not currently muted
        if volume > 0 {
            setVolume(clamped)
        }
    }

    /// Restore volume to the target level after temporary muting.
    /// Call this instead of setVolume(1) to respect the user's volume mix setting.
    func restoreVolume() {
        setVolume(targetVolume)
    }

    func setLooping(_ loop: Bool) {
        shouldLoop = loop
    }

    /// Set per-file durations for multi-file playback
    func setFileDurations(_ durations: [Double]?) {
        fileDurations = durations
    }

    /// Get the absolute time position across all files
    /// Returns currentTime offset by cumulative duration of previous files
    func absoluteTime(forFileDurations durations: [Double]?) -> Double {
        guard let durations = durations ?? fileDurations,
              currentFileIndex > 0,
              currentFileIndex < durations.count else {
            return currentTime
        }
        let previousDurations = durations.prefix(currentFileIndex).reduce(0, +)
        return previousDurations + currentTime
    }

    func seek(to time: Double) {
        seek(to: time, completion: nil)
    }

    func seek(to time: Double, completion: ((Bool) -> Void)?) {
        guard let player = player else {
            completion?(false)
            return
        }
        // Get the actual duration from the current item to avoid using stale cached value
        // This is important during track switches where self.duration may still have the old track's duration
        let actualDuration: Double = {
            if let item = player.currentItem, item.duration.isNumeric {
                return item.duration.seconds
            }
            return duration
        }()
        let clamped = max(0, min(time, actualDuration))
        let cmTime = CMTime(seconds: clamped, preferredTimescale: 600)
        // Optimistically update currentTime for immediate UI feedback
        currentTime = clamped
        player.seek(to: cmTime, toleranceBefore: .zero, toleranceAfter: .zero) { finished in
            DispatchQueue.main.async {
                completion?(finished)
            }
        }
    }

    /// Seek to an absolute time across multiple files using per-file durations.
    /// - Parameters:
    ///   - absoluteTime: The absolute time position in the combined audio timeline
    ///   - fileDurations: Array of durations for each file in order
    ///   - completion: Optional callback when seek completes
    func seekAcrossFiles(to absoluteTime: Double, fileDurations: [Double], completion: ((Bool) -> Void)? = nil) {
        guard let queuePlayer = player as? AVQueuePlayer else {
            // Fallback: single-file seek
            seek(to: absoluteTime)
            completion?(true)
            return
        }

        guard !fileDurations.isEmpty else {
            seek(to: absoluteTime)
            completion?(true)
            return
        }

        // Find which file contains the target time
        var accumulated = 0.0
        var targetFileIndex = 0
        var offsetWithinFile = absoluteTime

        for (index, fileDuration) in fileDurations.enumerated() {
            if absoluteTime < accumulated + fileDuration {
                targetFileIndex = index
                offsetWithinFile = absoluteTime - accumulated
                break
            }
            accumulated += fileDuration
            // If we're past all files, seek to end of last file
            if index == fileDurations.count - 1 {
                targetFileIndex = index
                offsetWithinFile = fileDuration
            }
        }

        print("[AudioPlayer] seekAcrossFiles: absoluteTime=\(absoluteTime), targetFile=\(targetFileIndex), offsetInFile=\(offsetWithinFile)")

        // Get current file index
        guard let currentItem = queuePlayer.currentItem else {
            completion?(false)
            return
        }

        let currentIdentifier = ObjectIdentifier(currentItem)
        let currentFileIndex = itemOrder[currentIdentifier] ?? 0

        if currentFileIndex == targetFileIndex {
            // Same file: just seek within current item
            let cmTime = CMTime(seconds: offsetWithinFile, preferredTimescale: 600)
            queuePlayer.seek(to: cmTime, toleranceBefore: .zero, toleranceAfter: .zero) { [weak self] finished in
                Task { @MainActor [weak self] in
                    if finished {
                        self?.currentTime = offsetWithinFile
                    }
                    completion?(finished)
                }
            }
        } else if targetFileIndex > currentFileIndex {
            // Need to advance to a later file - use advanceToNextItem until we reach target
            // This requires rebuilding the queue or using a different approach
            // For now, we'll reload with the target file's URL
            loadFileAndSeek(at: targetFileIndex, seekTo: offsetWithinFile, completion: completion)
        } else {
            // Need to go backward - must reload from target file
            loadFileAndSeek(at: targetFileIndex, seekTo: offsetWithinFile, completion: completion)
        }
    }

    /// Load starting from a specific file index and seek to position
    private func loadFileAndSeek(at fileIndex: Int, seekTo time: Double, completion: ((Bool) -> Void)?) {
        guard fileIndex < activeURLs.count else {
            completion?(false)
            return
        }

        let wasPlaying = isPlaying
        let urlsFromTarget = Array(activeURLs[fileIndex...])

        // Tear down current player and rebuild from target file
        tearDownPlayer()

        // Restore activeURLs (they were cleared by tearDownPlayer)
        let allURLs = activeURLs.isEmpty ? [] : activeURLs
        guard !urlsFromTarget.isEmpty else {
            completion?(false)
            return
        }

        // Manually rebuild the queue starting from target file
        itemURLMap = [:]
        itemOrder = [:]
        let items = urlsFromTarget.enumerated().map { offset, url -> AVPlayerItem in
            let item = AVPlayerItem(url: url)
            item.audioTimePitchAlgorithm = .timeDomain
            let identifier = ObjectIdentifier(item)
            itemURLMap[identifier] = url
            itemOrder[identifier] = fileIndex + offset
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

        // Restore activeURLs and activeURL
        // Note: We keep track of ALL URLs for multi-file duration calculations
        // but the queue starts from targetFileIndex
        if activeURLs.isEmpty {
            activeURLs = urlsFromTarget
        }
        activeURL = urlsFromTarget.first

        // Seek to target position within the first (target) file
        let cmTime = CMTime(seconds: time, preferredTimescale: 600)
        player.seek(to: cmTime, toleranceBefore: .zero, toleranceAfter: .zero) { [weak self] finished in
            Task { @MainActor [weak self] in
                guard let self else {
                    completion?(false)
                    return
                }
                self.currentTime = time
                if wasPlaying {
                    self.play()
                }
                completion?(finished)
            }
        }
    }

    func reset() {
        pause()
        currentTime = 0
        duration = 0
        isReady = false
        activeURL = nil
        activeURLs = []
        currentFileIndex = 0
        fileDurations = nil
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

    /// Whether audio session is configured to mix with other audio sources (e.g., Apple Music).
    private var isMixingEnabled = false

    /// Flag to ignore audio session interruptions triggered by our own session configuration changes.
    /// When we change the audio session category, iOS may send an interruption notification,
    /// but we don't want to pause playback for changes we initiated ourselves.
    private var isIgnoringInterruption = false

    /// Configure audio session to allow mixing with other audio sources.
    /// When `mixing` is true, narration coexists with Apple Music (ducking its volume).
    /// When false, narration takes exclusive audio session control.
    func configureAudioSessionForMixing(_ mixing: Bool) {
        #if os(iOS) || os(tvOS)
        guard role == .primary else { return }
        isMixingEnabled = mixing

        // Set flag to ignore interruptions caused by our own session changes
        isIgnoringInterruption = true

        let session = AVAudioSession.sharedInstance()
        do {
            let options: AVAudioSession.CategoryOptions = mixing
                ? [.mixWithOthers, .duckOthers]
                : []
            try session.setCategory(.playback, mode: .spokenAudio, options: options)
            try session.setActive(true)
            print("[AudioSession] Configured: mixing=\(mixing)")
        } catch {
            print("[AudioSession] Failed to configure mixing: \(error)")
        }

        // Clear the flag after a short delay to allow any pending interruption notifications to be ignored
        Task { @MainActor in
            try? await Task.sleep(nanoseconds: 100_000_000) // 100ms
            self.isIgnoringInterruption = false
        }
        #endif
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
            // Preserve current mixing state so Apple Music integration isn't disrupted
            let options: AVAudioSession.CategoryOptions = isMixingEnabled
                ? [.mixWithOthers, .duckOthers]
                : []
            try session.setCategory(.playback, mode: .spokenAudio, options: options)
            try session.setActive(true)
            let label = isMixingEnabled ? "mixing" : "exclusive"
            print("[AudioSession] Configured: category=playback, mode=spokenAudio (\(label))")
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
                    print("[AudioSession] Interruption BEGAN - wasPlaying=\(self.isPlaying), isPlaybackRequested=\(self.isPlaybackRequested), ignoring=\(self.isIgnoringInterruption)")
                    // Ignore interruptions caused by our own audio session changes (e.g., enabling mixing mode)
                    if self.isIgnoringInterruption {
                        print("[AudioSession] Ignoring self-initiated interruption")
                        return
                    }
                    self.shouldResumeAfterInterruption = self.isPlaying
                    self.isPlaying = false
                case .ended:
                    print("[AudioSession] Interruption ENDED - shouldResume=\(self.shouldResumeAfterInterruption), ignoring=\(self.isIgnoringInterruption)")
                    // If we're ignoring interruptions, don't try to resume either
                    if self.isIgnoringInterruption {
                        return
                    }
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
        currentFileIndex = 0
    }

    private func updateActiveURL() {
        guard let item = player?.currentItem else { return }
        let identifier = ObjectIdentifier(item)
        guard let url = itemURLMap[identifier] else { return }
        if activeURL != url {
            activeURL = url
        }
        if let index = itemOrder[identifier], currentFileIndex != index {
            currentFileIndex = index
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
