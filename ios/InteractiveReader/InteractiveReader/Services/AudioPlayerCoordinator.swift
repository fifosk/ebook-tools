import AVFoundation
import Foundation
import OSLog
#if os(iOS) || os(tvOS)
import UIKit
#endif

enum AudioPlaybackRole {
    case primary
    case ambient
}

#if os(iOS) || os(tvOS)
@MainActor
final class PlaybackIdleTimerCoordinator {
    static let shared = PlaybackIdleTimerCoordinator()

    private var isReaderPlaybackDisablingIdleTimer = false
    private var isMusicSurfaceDisablingIdleTimer = false

    var isMusicSurfaceSuppressed: Bool {
        isMusicSurfaceDisablingIdleTimer && UIApplication.shared.isIdleTimerDisabled
    }

    func setReaderPlaybackIdleDisabled(_ disabled: Bool) {
        isReaderPlaybackDisablingIdleTimer = disabled
        apply()
    }

    func setMusicSurfaceIdleDisabled(_ disabled: Bool) {
        isMusicSurfaceDisablingIdleTimer = disabled
        apply()
    }

    func reassertMusicSurfaceIdleDisabled() {
        guard isMusicSurfaceDisablingIdleTimer else { return }
        apply(force: true)
    }

    private func apply(force: Bool = false) {
        let shouldDisable = isReaderPlaybackDisablingIdleTimer || isMusicSurfaceDisablingIdleTimer
        guard force || UIApplication.shared.isIdleTimerDisabled != shouldDisable else { return }
        UIApplication.shared.isIdleTimerDisabled = shouldDisable
    }
}
#endif

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
    #if DEBUG
    @Published private(set) var audioSessionApplyCount = 0
    @Published private(set) var audioSessionSkipCount = 0
    @Published private(set) var audioSessionLastLabel = "unconfigured"
    @Published private(set) var e2eRequestedTransitionPauseCount = 0

    var isAudioSessionStableForMusicBed: Bool {
        let isMixingLabel = audioSessionLastLabel == "mixing" || audioSessionLastLabel == "mixing-ducked"
        return isMixingLabel && audioSessionApplyCount <= 2
    }

    func simulateRequestedTransitionPauseForMusicBedE2E() {
        guard ProcessInfo.processInfo.environment["E2E_MUSIC_BED_SYNC_TEST"] == "1" else { return }
        e2eRequestedTransitionPauseCount += 1
        isPlaybackRequested = true
        isPlaying = true
        setIdleTimerDisabled(true)
        DispatchQueue.main.async {
            self.isPlaying = false
            self.setIdleTimerDisabled(true)
        }
    }

    func simulateRequestedTransitionResumeForMusicBedE2E() {
        guard ProcessInfo.processInfo.environment["E2E_MUSIC_BED_SYNC_TEST"] == "1" else { return }
        isPlaybackRequested = true
        isPlaying = true
        setIdleTimerDisabled(true)
    }
    #endif
    /// Target volume level that should be restored after temporary muting (e.g., during track switches).
    /// This preserves the user's volume mix setting across sentence/track transitions.
    private(set) var targetVolume: Double = 1.0
    var onPlaybackEnded: (() -> Void)?
    /// Called when playback has been stalled (buffer starved) for an extended
    /// period without recovery. The view layer can use this to force-advance
    /// the sequence so the user isn't stuck on a broken segment.
    var onPersistentStall: (() -> Void)?
    // Stall recovery tracking
    private var firstStallAt: Date?
    private var stallCountAtCurrentTime: Int = 0
    private var lastStallCurrentTime: Double = -1
    private var stallRecoveryTask: Task<Void, Never>?

    let role: AudioPlaybackRole
    private var shouldLoop = false
    private var player: AVPlayer?
    private var timeObserverToken: Any?
    private var boundaryObserverToken: Any?
    private var endObserver: NSObjectProtocol?
    private var statusObservation: NSKeyValueObservation?
    private var timeControlObservation: NSKeyValueObservation?
    private var failureObserver: NSObjectProtocol?
    private var errorLogObserver: NSObjectProtocol?
    private var stallObserver: NSObjectProtocol?
    private var interruptionObserver: NSObjectProtocol?
    private var shouldResumeAfterInterruption = false
    private var itemURLMap: [ObjectIdentifier: URL] = [:]
    private var itemOrder: [ObjectIdentifier: Int] = [:]
    private var streamFailureRetryCountByURL: [URL: Int] = [:]
    /// Per-file durations for multi-file playback (set via setFileDurations)
    private var fileDurations: [Double]?
    private let logger = Logger(subsystem: "InteractiveReader", category: "AudioPlayer")
    private let maxStreamFailureRetriesPerURL = 1

    var nowPlayingPlayer: AVPlayer? {
        player
    }

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
        logger.debug("Loading audio urls count=\(sanitized.count, privacy: .public)")
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
        streamFailureRetryCountByURL = [:]
        tearDownPlayer()
        activeURLs = sanitized
        activeURL = sanitized.first
        itemURLMap = [:]
        let items = sanitized.enumerated().map { index, url -> AVPlayerItem in
            let item = AVPlayerItem(url: url)
            item.audioTimePitchAlgorithm = .timeDomain
            // Force AVPlayer to buffer the whole ~30s MP3 instead of stalling 500ms
            // before EOF waiting for the tail. Our sentences are short; buffering
            // the full file costs ~500KB per item and eliminates end-of-file stalls.
            item.preferredForwardBufferDuration = 60
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
        // Disable built-in stall-avoidance waits: we prefer playImmediately() to
        // proceed with whatever buffer we have, combined with the larger
        // preferredForwardBufferDuration above to keep the buffer full.
        player.automaticallyWaitsToMinimizeStalling = false
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
        logger.debug("Play requested role=\(String(describing: self.role), privacy: .public) hasActiveURL=\((self.activeURL != nil), privacy: .public)")
        if #available(iOS 10.0, tvOS 10.0, *) {
            player.playImmediately(atRate: Float(playbackRate))
        } else {
            player.play()
            player.rate = Float(playbackRate)
        }
        isPlaying = true
        setIdleTimerDisabled(true)
    }

    func pause() {
        // Log call stack to identify unexpected pause sources. Filter out our own
        // frame and show the first ~4 app frames after it.
        let frames = Thread.callStackSymbols
            .dropFirst(1) // drop the pause() frame itself
            .prefix(4)
            .compactMap { frame -> String? in
                // Extract just the symbol from full frame line
                let components = frame.split(separator: " ", omittingEmptySubsequences: true)
                guard components.count >= 4 else { return frame }
                return components.dropFirst(3).joined(separator: " ")
            }
        logger.debug("Pause role=\(String(describing: self.role), privacy: .public) isPlaying=\(self.isPlaying, privacy: .public) time=\(String(format: "%.3f", self.currentTime), privacy: .public) caller=\(frames.joined(separator: " <- "), privacy: .private)")
        player?.pause()
        isPlaying = false
        isPlaybackRequested = false
        AudioPlaybackRegistry.shared.endPlayback(for: self)
        setIdleTimerDisabled(false)
    }

    /// Pause playback temporarily without clearing isPlaybackRequested.
    /// Used during sequence dwell periods to prevent audio bleed while keeping
    /// the reading bed playing (which monitors isPlaybackRequested).
    func pauseForDwell() {
        // Mute FIRST — volume change takes effect in the audio rendering pipeline
        // immediately, whereas pause() must drain the output buffer (especially
        // noticeable on tvOS where HDMI adds ~50-100ms of buffered audio).
        player?.volume = 0
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
        guard !fileDurations.isEmpty else {
            seek(to: absoluteTime, completion: completion)
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

        logger.debug("Seek across files absoluteTime=\(absoluteTime, privacy: .public) targetFile=\(targetFileIndex, privacy: .public) offset=\(offsetWithinFile, privacy: .public)")

        guard let queuePlayer = player as? AVQueuePlayer else {
            guard activeURLs.count > 1 else {
                seek(to: offsetWithinFile, completion: completion)
                return
            }
            loadFileAndSeek(at: targetFileIndex, seekTo: offsetWithinFile, completion: completion)
            return
        }

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
        let allActiveURLs = activeURLs
        let urlsFromTarget = Array(allActiveURLs[fileIndex...])

        // Tear down current player and rebuild from target file
        tearDownPlayer()

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
            item.preferredForwardBufferDuration = 60
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
        player.automaticallyWaitsToMinimizeStalling = false
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
        activeURLs = allActiveURLs
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
        streamFailureRetryCountByURL = [:]
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
    private var isDuckingOthersEnabled = false
    private var appliedAudioSessionConfiguration: AudioSessionConfiguration?

    private struct AudioSessionConfiguration: Equatable {
        let mixing: Bool
        let duckOthers: Bool

        var label: String {
            if !mixing {
                return "exclusive"
            }
            return duckOthers ? "mixing-ducked" : "mixing"
        }

        var mode: AVAudioSession.Mode {
            mixing ? .default : .spokenAudio
        }
    }

    /// Flag to ignore audio session interruptions triggered by our own session configuration changes.
    /// When we change the audio session category, iOS may send an interruption notification,
    /// but we don't want to pause playback for changes we initiated ourselves.
    private var isIgnoringInterruption = false

    /// Configure audio session to allow mixing with other audio sources.
    /// When `mixing` is true, narration coexists with Apple Music while the app's
    /// own mix slider controls narration volume and can request system ducking at low Music mix values.
    /// When false, narration takes exclusive audio session control.
    func configureAudioSessionForMixing(_ mixing: Bool, duckOthers: Bool = false) {
        #if os(iOS) || os(tvOS)
        guard role == .primary else { return }
        isMixingEnabled = mixing
        isDuckingOthersEnabled = mixing && duckOthers

        configureAudioSession()
        #endif
    }

    func reassertAudioSession() {
        configureAudioSession()
    }

    private func audioSessionOptions(mixing: Bool, duckOthers: Bool) -> AVAudioSession.CategoryOptions {
        guard mixing else { return [] }
        return duckOthers ? [.mixWithOthers, .duckOthers] : [.mixWithOthers]
    }

    @discardableResult
    private func configureAudioSession(force: Bool = false) -> Bool {
        #if os(iOS) || os(tvOS)
        // Only configure audio session for primary role to avoid conflicts
        // The ambient player will piggyback on the primary player's session
        guard role == .primary else { return false }

        let configuration = AudioSessionConfiguration(
            mixing: isMixingEnabled,
            duckOthers: isDuckingOthersEnabled
        )
        guard force || appliedAudioSessionConfiguration != configuration else {
            #if DEBUG
            audioSessionSkipCount += 1
            audioSessionLastLabel = configuration.label
            #endif
            logger.debug("Skipped unchanged audio session label=\(configuration.label, privacy: .public)")
            return false
        }

        // Set flag to ignore interruptions caused by our own session changes.
        isIgnoringInterruption = true

        let session = AVAudioSession.sharedInstance()
        do {
            // Use neutral playback mode while mixing with Apple Music. Spoken audio
            // mode can cause MusicKit to yield instead of bedding under narration.
            let options = audioSessionOptions(mixing: configuration.mixing, duckOthers: configuration.duckOthers)
            let mode = configuration.mode
            try session.setCategory(.playback, mode: mode, options: options)
            try session.setActive(true)
            appliedAudioSessionConfiguration = configuration
            #if DEBUG
            audioSessionApplyCount += 1
            audioSessionLastLabel = configuration.label
            #endif
            logger.debug("Configured audio session category=playback mode=\(mode.rawValue, privacy: .public) label=\(configuration.label, privacy: .public)")
        } catch {
            appliedAudioSessionConfiguration = nil
            #if DEBUG
            audioSessionLastLabel = "failed-\(configuration.label)"
            #endif
            logger.error("Failed to configure audio session: \(String(describing: error), privacy: .public)")
        }

        // Clear the flag after a short delay to allow any pending interruption notifications to be ignored.
        Task { @MainActor in
            try? await Task.sleep(nanoseconds: 100_000_000) // 100ms
            self.isIgnoringInterruption = false
        }
        return true
        #else
        return false
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
                    self.logger.debug("Audio interruption began wasPlaying=\(self.isPlaying, privacy: .public) requested=\(self.isPlaybackRequested, privacy: .public) ignoring=\(self.isIgnoringInterruption, privacy: .public)")
                    // Ignore interruptions caused by our own audio session changes (e.g., enabling mixing mode)
                    if self.isIgnoringInterruption {
                        self.logger.debug("Ignoring self-initiated audio interruption")
                        return
                    }
                    self.appliedAudioSessionConfiguration = nil
                    self.shouldResumeAfterInterruption = self.isPlaying
                    self.isPlaying = false
                case .ended:
                    self.logger.debug("Audio interruption ended shouldResume=\(self.shouldResumeAfterInterruption, privacy: .public) ignoring=\(self.isIgnoringInterruption, privacy: .public)")
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
                    self.logger.debug("Audio item ready duration=\(observedItem.duration.seconds, privacy: .public)")
                    self.isReady = true
                    if observedItem.duration.isNumeric {
                        self.duration = observedItem.duration.seconds
                    }
                case .failed:
                    if let error = observedItem.error as NSError? {
                        self.logger.error("Audio item failed domain=\(error.domain, privacy: .public) code=\(error.code, privacy: .public) message=\(error.localizedDescription, privacy: .public)")
                        if let underlyingError = error.userInfo[NSUnderlyingErrorKey] as? NSError {
                            self.logger.error("Underlying audio item failure domain=\(underlyingError.domain, privacy: .public) code=\(underlyingError.code, privacy: .public) message=\(underlyingError.localizedDescription, privacy: .public)")
                        }
                    } else {
                        self.logger.error("Audio item failed with unknown error")
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
        // Observe only `.new` — NOT `.initial`. The initial state of a freshly-created
        // AVPlayer is .paused, which (fired asynchronously via Task) races with play()'s
        // synchronous isPlaying=true assignment and can overwrite it back to false.
        // The practical symptom was that the sequence time observer silently skipped
        // updates (guarded on isPlaying), so the boundary observer for seg[0] never
        // fired and audio played past its segment boundary while the view stayed frozen.
        timeControlObservation = player.observe(\.timeControlStatus, options: [.new]) { [weak self] player, _ in
            guard let self else { return }
            Task { @MainActor in
                // Also guard against stale async updates: only accept the transition
                // if it still matches the player's current status when the task runs.
                let current = player.timeControlStatus
                switch current {
                case .playing:
                    if !self.isPlaying {
                        self.logger.debug("KVO playing role=\(String(describing: self.role), privacy: .public) time=\(String(format: "%.3f", self.currentTime), privacy: .public)")
                    }
                    self.isPlaying = true
                case .paused:
                    // Do NOT unset isPlaying if play() was explicitly requested.
                    // AVPlayer transiently reports .paused during rate changes / seeks
                    // even when playback is intended. Only treat .paused as a real
                    // pause when playback wasn't requested.
                    self.logger.debug("KVO paused role=\(String(describing: self.role), privacy: .public) time=\(String(format: "%.3f", self.currentTime), privacy: .public) requested=\(self.isPlaybackRequested, privacy: .public) wasPlaying=\(self.isPlaying, privacy: .public)")
                    if !self.isPlaybackRequested {
                        self.isPlaying = false
                    }
                case .waitingToPlayAtSpecifiedRate:
                    self.logger.debug("KVO waiting role=\(String(describing: self.role), privacy: .public) time=\(String(format: "%.3f", self.currentTime), privacy: .public) reason=\(String(describing: player.reasonForWaitingToPlay?.rawValue ?? "nil"), privacy: .public)")
                @unknown default:
                    break
                }
            }
        }
    }

    // MARK: - Boundary Time Observer

    /// Callback fired when the boundary time observer triggers
    var onBoundaryReached: (() -> Void)?

    /// Install a boundary time observer that fires once when playback reaches the given time.
    /// Used for precise segment-end detection to prevent audio bleed into the next sentence.
    func installBoundaryObserver(at time: Double) {
        removeBoundaryObserver()
        guard let player = player else {
            logger.debug("Boundary not installed; no player time=\(String(format: "%.3f", time), privacy: .public)")
            return
        }
        guard time > 0 else { return }
        let boundaryTime = CMTime(seconds: time, preferredTimescale: 600)
        let token = player.addBoundaryTimeObserver(
            forTimes: [NSValue(time: boundaryTime)],
            queue: .main
        ) { [weak self] in
            Task { @MainActor [weak self] in
                self?.logger.debug("Boundary observer fired time=\(String(format: "%.3f", time), privacy: .public)")
                self?.onBoundaryReached?()
            }
        }
        boundaryObserverToken = token
        logger.debug("Boundary installed time=\(String(format: "%.3f", time), privacy: .public)")
    }

    /// Remove the current boundary time observer
    func removeBoundaryObserver() {
        if let token = boundaryObserverToken {
            player?.removeTimeObserver(token)
            boundaryObserverToken = nil
        }
    }

    // MARK: - Audio Mix (Segment Fade-Out)

    /// Apply an AVAudioMix that fades volume to 0 at the segment end time.
    /// This operates at the decode level — before Core Audio and HDMI output buffers —
    /// guaranteeing no audio bleed regardless of output pipeline latency.
    /// - Parameters:
    ///   - fadeStartTime: When to start fading (seconds into the audio file)
    ///   - fadeEndTime: When volume should reach 0 (seconds into the audio file)
    func applySegmentFadeOut(fadeStartTime: Double, fadeEndTime: Double) {
        guard let item = player?.currentItem else {
            logger.debug("Fade not applied; no current item")
            return
        }

        // Load audio tracks asynchronously (required for remote URLs)
        Task { @MainActor [weak self] in
            guard let self else { return }
            let tracks: [AVAssetTrack]
            if #available(iOS 15.0, tvOS 15.0, *) {
                guard let loaded = try? await item.asset.loadTracks(withMediaType: .audio) else {
                    self.logger.debug("Fade not applied; no async audio track")
                    return
                }
                tracks = loaded
            } else {
                tracks = item.asset.tracks(withMediaType: .audio)
            }
            guard let audioTrack = tracks.first else {
                self.logger.debug("Fade not applied; no audio track")
                return
            }

            let params = AVMutableAudioMixInputParameters(track: audioTrack)
            let start = CMTime(seconds: fadeStartTime, preferredTimescale: 600)
            let end = CMTime(seconds: fadeEndTime, preferredTimescale: 600)
            params.setVolumeRamp(fromStartVolume: Float(self.targetVolume), toEndVolume: 0, timeRange: CMTimeRange(start: start, end: end))

            let mix = AVMutableAudioMix()
            mix.inputParameters = [params]
            item.audioMix = mix
            self.logger.debug("Fade applied start=\(String(format: "%.3f", fadeStartTime), privacy: .public) end=\(String(format: "%.3f", fadeEndTime), privacy: .public)")
        }
    }

    /// Remove any audio mix from the current item (restores normal playback volume).
    func clearAudioMix() {
        player?.currentItem?.audioMix = nil
    }

    private func installTimeObserver(on player: AVPlayer) {
        let token = player.addPeriodicTimeObserver(forInterval: CMTime(seconds: 0.1, preferredTimescale: 600), queue: .main) {
            [weak self] time in
            Task { @MainActor [weak self] in
                guard let self else { return }
                self.updateActiveURL()
                let newTime = time.seconds
                // If playback progressed since the last stall, cancel any pending
                // stall-recovery watchdog — AVPlayer recovered on its own.
                if self.firstStallAt != nil, newTime > self.lastStallCurrentTime + 0.05 {
                    self.firstStallAt = nil
                    self.stallCountAtCurrentTime = 0
                    self.stallRecoveryTask?.cancel()
                    self.stallRecoveryTask = nil
                }
                self.currentTime = newTime
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
                self.setIdleTimerDisabled(false)
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
                    self.logger.error("Playback failed url=\(failedURL?.absoluteString ?? "unknown", privacy: .private) domain=\(error.domain, privacy: .public) code=\(error.code, privacy: .public) message=\(error.localizedDescription, privacy: .public)")
                } else {
                    self.logger.error("Playback failed url=\(failedURL?.absoluteString ?? "unknown", privacy: .private) with unknown error")
                }
                self.retryFailedStreamIfPossible(failedItem)
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
                self.logger.error("Playback error log url=\(errorURL?.absoluteString ?? "unknown", privacy: .private) status=\(logEvent.errorStatusCode, privacy: .public) uri=\(logEvent.uri ?? "n/a", privacy: .private) comment=\(logEvent.errorComment ?? "n/a", privacy: .public)")
            }
        }
        // Observe playback stalls — fires when streaming buffer runs dry and
        // playback is paused waiting for more data. Common cause of random
        // mid-sentence pauses on slow networks.
        stallObserver = NotificationCenter.default.addObserver(
            forName: .AVPlayerItemPlaybackStalled,
            object: nil,
            queue: .main
        ) { [weak self] notification in
            Task { @MainActor in
                guard let self else { return }
                guard let stalledItem = notification.object as? AVPlayerItem,
                      self.itemURLMap[ObjectIdentifier(stalledItem)] != nil else {
                    return
                }
                let stalledURL = self.itemURLMap[ObjectIdentifier(stalledItem)]
                self.logger.warning("Playback stalled role=\(String(describing: self.role), privacy: .public) time=\(String(format: "%.3f", self.currentTime), privacy: .public) file=\(stalledURL?.lastPathComponent ?? "unknown", privacy: .private) requested=\(self.isPlaybackRequested, privacy: .public)")
                self.handleStall()
            }
        }
    }

    /// Track stall events and schedule a recovery if playback remains stuck at the
    /// same position for more than 3 seconds. The stall notification fires repeatedly
    /// while AVPlayer can't recover the stream (common near end-of-file when the last
    /// bytes are slow to arrive), so we coalesce them into a single recovery trigger.
    private func handleStall() {
        // Only primary (narration) coordinator recovers; reading bed just drops.
        guard role == .primary else { return }
        guard isPlaybackRequested else { return }

        if firstStallAt == nil || currentTime != lastStallCurrentTime {
            // First stall for this position. Start a recovery watchdog.
            firstStallAt = Date()
            lastStallCurrentTime = currentTime
            stallCountAtCurrentTime = 1
            stallRecoveryTask?.cancel()
            stallRecoveryTask = Task { @MainActor [weak self] in
                try? await Task.sleep(nanoseconds: 3_000_000_000) // 3 seconds
                guard let self else { return }
                guard !Task.isCancelled else { return }
                // Still stuck at same time? Trigger recovery.
                if self.lastStallCurrentTime == self.currentTime,
                   self.isPlaybackRequested {
                    self.logger.warning("Persistent stall recovery time=\(String(format: "%.3f", self.currentTime), privacy: .public)")
                    self.firstStallAt = nil
                    self.stallCountAtCurrentTime = 0
                    self.onPersistentStall?()
                }
            }
        } else {
            stallCountAtCurrentTime += 1
        }
    }

    private func retryFailedStreamIfPossible(_ failedItem: AVPlayerItem) {
        guard role == .primary else { return }
        guard isPlaybackRequested else { return }
        let identifier = ObjectIdentifier(failedItem)
        guard let failedURL = itemURLMap[identifier] else { return }
        let attempts = streamFailureRetryCountByURL[failedURL, default: 0]
        guard attempts < maxStreamFailureRetriesPerURL else {
            logger.error("Playback stream retry exhausted role=\(String(describing: self.role), privacy: .public) file=\(failedURL.lastPathComponent, privacy: .private)")
            return
        }
        streamFailureRetryCountByURL[failedURL] = attempts + 1
        let failedIndex = itemOrder[identifier] ?? currentFileIndex
        let resumeTime = max(currentTime, 0)
        logger.warning("Retrying failed playback stream role=\(String(describing: self.role), privacy: .public) fileIndex=\(failedIndex, privacy: .public) time=\(String(format: "%.3f", resumeTime), privacy: .public)")
        loadFileAndSeek(at: failedIndex, seekTo: resumeTime) { [weak self] finished in
            Task { @MainActor [weak self] in
                guard let self else { return }
                guard finished, self.isPlaybackRequested else { return }
                self.play()
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
        if let token = boundaryObserverToken {
            player?.removeTimeObserver(token)
            boundaryObserverToken = nil
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
        if let observer = stallObserver {
            NotificationCenter.default.removeObserver(observer)
            stallObserver = nil
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

    /// Prevent the screen from auto-locking while narration is playing.
    /// Only the primary (narration) coordinator toggles this — ambient players
    /// (reading bed) ignore it so they don't fight the primary. On tvOS this
    /// also prevents idle promotion into full-screen Music/Now Playing artwork.
    private func setIdleTimerDisabled(_ disabled: Bool) {
        #if os(iOS) || os(tvOS)
        guard role == .primary else { return }
        PlaybackIdleTimerCoordinator.shared.setReaderPlaybackIdleDisabled(disabled)
        #endif
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
