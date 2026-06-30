import Foundation
import Combine
import OSLog
#if canImport(MusicKit)
import MusicKit
#endif
#if os(tvOS)
import UIKit
#endif

/// Keys for persisting music preferences.
enum MusicPreferences {
    static let useAppleMusicKey = "player.useAppleMusicForBed"
    static let musicVolumeKey = "player.musicVolume"
    static let appleMusicMixInitializedKey = "player.appleMusicMixInitialized"
    static let readingBedEnabledKey = "player.readingBedEnabled"
    static let shuffleModeKey = "player.shuffleMode"
    static let repeatModeKey = "player.repeatMode"
    static let lastReadingBedIDKey = "player.lastReadingBedID"
    static let lastAppleMusicKindKey = "player.appleMusic.lastKind"
    static let lastAppleMusicIDKey = "player.appleMusic.lastID"
    static let lastAppleMusicTitleKey = "player.appleMusic.lastTitle"
    static let lastAppleMusicSubtitleKey = "player.appleMusic.lastSubtitle"
    static let lastAppleMusicArtworkURLKey = "player.appleMusic.lastArtworkURL"
    static let defaultMusicVolume: Double = 0.15
    static let defaultAppleMusicMix: Double = 0.60
}

/// Platform-agnostic shuffle mode (mirrors MusicPlayer.ShuffleMode).
enum MusicKitShuffleMode: String {
    case off, songs
}

/// Platform-agnostic repeat mode (mirrors MusicPlayer.RepeatMode).
enum MusicKitRepeatMode: String {
    case off, one, all
}

/// Who currently owns the lock screen / Control Centre Now Playing info.
enum AudioOwnership: Equatable {
    case narration       // Lock screen shows book info + sentence controls
    case appleMusic      // Lock screen shows Apple Music track + controls
    case appleMusicBed   // Apple Music plays underneath reader-owned sentence controls
    case transitioning   // During handoff - neither side should assert
}

/// Wraps MusicKit's ApplicationMusicPlayer for controlling Apple Music playback
/// as a reading bed alternative.
@MainActor
final class MusicKitCoordinator: ObservableObject {
    static let shared = MusicKitCoordinator()

    @Published private(set) var isAuthorized = false
    @Published private(set) var isPlaying = false
    @Published private(set) var currentSongTitle: String?
    @Published private(set) var currentArtist: String?
    @Published private(set) var currentArtworkURL: URL?
    @Published private(set) var playbackSurfaceRevision = 0
    @Published private(set) var ownershipState: AudioOwnership = .narration
    @Published private(set) var isManuallyPaused = false
    @Published private(set) var isPausedByReaderTransport = false
    @Published private(set) var hasAutoResumeIntent = false
    @Published private(set) var isSuppressingMusicPlaybackSurface = false
    @Published private(set) var readerTransportPauseAdoptionRevision = 0
    #if DEBUG
    @Published private(set) var e2eMusicBedSyncPhase = "idle"
    @Published private(set) var e2eMusicBedAlreadyPlayingResumeSkipCount = 0
    #endif
    @Published var shuffleMode: MusicKitShuffleMode = .off
    @Published var repeatMode: MusicKitRepeatMode = .off

    // Playback progress for timeline UI
    @Published private(set) var playbackTime: TimeInterval = 0
    @Published private(set) var playbackDuration: TimeInterval = 0

    /// Whether Apple Music is actively serving as the reading bed.
    var isBackgroundMode: Bool { ownershipState == .appleMusic || ownershipState == .appleMusicBed }
    var isSystemPlaybackPlaying: Bool {
        #if canImport(MusicKit)
        ApplicationMusicPlayer.shared.state.playbackStatus == .playing
        #else
        isPlaying
        #endif
    }
    var canAutoResumeReadingBed: Bool {
        hasQueuedMusicForAutoResume &&
            !isReaderTransportPauseHoldActive &&
            (!isManuallyPaused || isPausedByReaderTransport) &&
            (hasAutoResumeIntent || isPausedByReaderTransport)
    }
    private var hasQueuedMusicForAutoResume: Bool {
        #if canImport(MusicKit)
        return ApplicationMusicPlayer.shared.queue.currentEntry != nil
            || hasRestoredQueueForAutoResume
            || hasPersistedAppleMusicSelection
        #else
        return currentSongTitle != nil
        #endif
    }
    private var hasPersistedAppleMusicSelection: Bool {
        let defaults = UserDefaults.standard
        guard defaults.string(forKey: MusicPreferences.lastAppleMusicKindKey) != nil,
              let rawID = defaults.string(forKey: MusicPreferences.lastAppleMusicIDKey)
        else {
            return false
        }
        return !rawID.isEmpty
    }
    #if DEBUG
    private var isE2EMusicBedSyncTest: Bool {
        ProcessInfo.processInfo.environment["E2E_MUSIC_BED_SYNC_TEST"] == "1"
    }
    #endif
    private let logger = Logger(subsystem: "InteractiveReader", category: "MusicKit")
    private var readerTransportPauseHoldUntil = Date.distantPast
    private var readerTransportPauseDuplicateHoldUntil = Date.distantPast
    private let readerTransportPauseHoldDuration: TimeInterval = 0.75
    private let readerTransportPauseDuplicateHoldDuration: TimeInterval = 0.75
    private var readerTransportResumeBarrier = 0
    private var readerTransportPauseAdoptionHandlerOwner: ObjectIdentifier?
    private var readerTransportPauseAdoptionHandler: ((String, String) -> Void)?

    private var isReaderTransportPauseHoldActive: Bool {
        Date() < readerTransportPauseHoldUntil
    }
    private var isReaderTransportPauseDuplicateHoldActive: Bool {
        Date() < readerTransportPauseDuplicateHoldUntil
    }
    var readerTransportResumeBarrierValue: Int { readerTransportResumeBarrier }
    var isReaderTransportPauseGuardActive: Bool {
        isReaderTransportPauseHoldActive || isReaderTransportPauseSuppressionActive
    }
    var isReaderTransportEchoGuardActive: Bool {
        isReaderTransportPauseHoldActive || isReaderTransportPauseDuplicateHoldActive
    }
    var isReaderTransportPauseHoldWindowActive: Bool {
        isReaderTransportPauseHoldActive
    }
    var shouldRejectReaderTransportResumeAfterPause: Bool {
        isReaderTransportPauseDuplicateHoldActive && isPausedByReaderTransport
    }
    var isReaderPlaybackSurfaceActive: Bool {
        isSuppressingMusicPlaybackSurface || ownershipState == .appleMusicBed
    }
    var isFullscreenMusicArtworkSuppressed: Bool {
        #if os(tvOS)
        return isReaderPlaybackSurfaceActive && PlaybackIdleTimerCoordinator.shared.isMusicSurfaceSuppressed
        #else
        return isReaderPlaybackSurfaceActive
        #endif
    }
    private var isReaderTransportPauseSuppressionActive: Bool {
        ownershipState == .appleMusicBed &&
            isPausedByReaderTransport &&
            isManuallyPaused
    }

    #if canImport(MusicKit)
    private var playbackStateTask: Task<Void, Never>?
    private var observedNonPlayingTask: Task<Void, Never>?
    private var playbackSurfaceReassertionTask: Task<Void, Never>?
    private var readerTransportPauseConfirmationTask: Task<Void, Never>?
    private var readerTransportResumeTask: Task<Void, Never>?
    private var readerTransportResumeTaskID = 0
    private var shouldIgnoreNextNonPlayingStatus = false
    private var hasRestoredQueueForAutoResume = false
    private var observedPlayingAsReadingBed = false
    private var isReaderNarrationActiveForMusicBed = false
    private var lastReadingBedRecoveryAttempt = Date.distantPast
    private let readingBedRecoveryInterval: TimeInterval = 3
    #if os(tvOS)
    private var didDisableIdleTimerForMusicSurface = false
    private var tvOSMusicSurfaceSuppressionWatchdogTask: Task<Void, Never>?
    private var tvOSSystemSurfaceSuppressionTask: Task<Void, Never>?
    #endif

    private init() {
        isAuthorized = MusicAuthorization.currentStatus == .authorized
        restorePersistedState()
        applyPersistedModesToPlayer()
        observePlaybackState()
    }

    deinit {
        playbackStateTask?.cancel()
        observedNonPlayingTask?.cancel()
        playbackSurfaceReassertionTask?.cancel()
        readerTransportPauseConfirmationTask?.cancel()
        readerTransportResumeTask?.cancel()
        #if os(tvOS)
        tvOSMusicSurfaceSuppressionWatchdogTask?.cancel()
        tvOSSystemSurfaceSuppressionTask?.cancel()
        #endif
    }

    func requestAuthorization() async -> Bool {
        let status = await MusicAuthorization.request()
        isAuthorized = status == .authorized
        return isAuthorized
    }

    // MARK: - Playback: Song

    func playSong(_ song: Song) async {
        let player = ApplicationMusicPlayer.shared
        player.queue = [song]
        hasRestoredQueueForAutoResume = true
        do {
            try await player.play()
            isManuallyPaused = false
            isPausedByReaderTransport = false
            hasAutoResumeIntent = true
            persistLastAppleMusicSelection(
                kind: .songs,
                id: song.id.rawValue,
                title: song.title,
                subtitle: song.artistName,
                artworkURL: song.artwork?.url(width: 300, height: 300)
            )
            updateCurrentTrackInfo(reason: "playSong")
            schedulePlaybackSurfaceReassertions(reason: "playSong")
        } catch {
            logger.error("Failed to play song: \(String(describing: error), privacy: .private)")
        }
    }

    // MARK: - Playback: Station

    func playStation(_ station: Station) async {
        let player = ApplicationMusicPlayer.shared
        player.queue = ApplicationMusicPlayer.Queue(for: [station])
        hasRestoredQueueForAutoResume = true
        do {
            try await player.play()
            isManuallyPaused = false
            isPausedByReaderTransport = false
            hasAutoResumeIntent = true
            persistLastAppleMusicSelection(
                kind: .stations,
                id: station.id.rawValue,
                title: station.name,
                subtitle: nil,
                artworkURL: station.artwork?.url(width: 300, height: 300)
            )
            updateCurrentTrackInfo(reason: "playStation")
            schedulePlaybackSurfaceReassertions(reason: "playStation")
        } catch {
            logger.error("Failed to play station: \(String(describing: error), privacy: .private)")
        }
    }

    // MARK: - Playback: Album

    func playAlbum(_ album: Album) async {
        let player = ApplicationMusicPlayer.shared
        player.queue = ApplicationMusicPlayer.Queue(for: [album])
        hasRestoredQueueForAutoResume = true
        do {
            try await player.play()
            isManuallyPaused = false
            isPausedByReaderTransport = false
            hasAutoResumeIntent = true
            persistLastAppleMusicSelection(
                kind: .albums,
                id: album.id.rawValue,
                title: album.title,
                subtitle: album.artistName,
                artworkURL: album.artwork?.url(width: 300, height: 300)
            )
            updateCurrentTrackInfo(reason: "playAlbum")
            schedulePlaybackSurfaceReassertions(reason: "playAlbum")
        } catch {
            logger.error("Failed to play album: \(String(describing: error), privacy: .private)")
        }
    }

    // MARK: - Playback: Playlist

    func playPlaylist(_ playlist: Playlist) async {
        let player = ApplicationMusicPlayer.shared
        player.queue = ApplicationMusicPlayer.Queue(for: [playlist])
        hasRestoredQueueForAutoResume = true
        do {
            try await player.play()
            isManuallyPaused = false
            isPausedByReaderTransport = false
            hasAutoResumeIntent = true
            persistLastAppleMusicSelection(
                kind: .playlists,
                id: playlist.id.rawValue,
                title: playlist.name,
                subtitle: playlist.curatorName,
                artworkURL: playlist.artwork?.url(width: 300, height: 300)
            )
            updateCurrentTrackInfo(reason: "playPlaylist")
            schedulePlaybackSurfaceReassertions(reason: "playPlaylist")
        } catch {
            logger.error("Failed to play playlist: \(String(describing: error), privacy: .private)")
        }
    }

    // MARK: - Playback: Artist (top songs)

    func playArtistTopSongs(_ artist: Artist) async {
        do {
            let detailed = try await artist.with([.topSongs])
            guard let topSongs = detailed.topSongs, !topSongs.isEmpty else {
                logger.info("No top songs found for artist")
                return
            }
            let player = ApplicationMusicPlayer.shared
            player.queue = ApplicationMusicPlayer.Queue(for: topSongs)
            hasRestoredQueueForAutoResume = true
            try await player.play()
            isManuallyPaused = false
            isPausedByReaderTransport = false
            hasAutoResumeIntent = true
            persistLastAppleMusicSelection(
                kind: .artists,
                id: artist.id.rawValue,
                title: artist.name,
                subtitle: nil,
                artworkURL: artist.artwork?.url(width: 300, height: 300)
            )
            updateCurrentTrackInfo(reason: "playArtistTopSongs")
            schedulePlaybackSurfaceReassertions(reason: "playArtistTopSongs")
        } catch {
            logger.error("Failed to play artist top songs: \(String(describing: error), privacy: .private)")
        }
    }

    func ensureLastSelectionLoadedForReadingBed() async {
        guard isAuthorized else { return }
        if ApplicationMusicPlayer.shared.queue.currentEntry != nil {
            return
        }
        await restoreLastAppleMusicSelectionToQueue()
    }

    // MARK: - Transport Controls

    func resume(userInitiated: Bool = true, expectedReaderTransportBarrier: Int? = nil) {
        if userInitiated {
            cancelTVOSSystemPlaybackSurfaceSuppression()
        }
        if userInitiated {
            clearReaderTransportPauseHold()
            isManuallyPaused = false
            isPausedByReaderTransport = false
        } else {
            guard canAutoResumeReadingBed else { return }
        }
        let player = ApplicationMusicPlayer.shared
        readerTransportResumeTask?.cancel()
        readerTransportResumeTaskID &+= 1
        let resumeTaskID = readerTransportResumeTaskID
        readerTransportResumeTask = Task { @MainActor in
            defer {
                if self.readerTransportResumeTaskID == resumeTaskID {
                    self.readerTransportResumeTask = nil
                }
            }
            do {
                await self.ensureLastSelectionLoadedForReadingBed()
                guard !Task.isCancelled else { return }
                guard self.isExpectedReaderTransportResumeCurrent(expectedReaderTransportBarrier) else {
                    self.logger.info("Apple Music resume skipped stale reader transport barrier before play")
                    return
                }
                guard self.hasQueuedMusicForAutoResume else {
                    self.logger.info("Apple Music resume skipped queued=false persistedSelection=false")
                    return
                }
                if !userInitiated,
                   self.settleAlreadyPlayingReadingBedForAutoResume(reason: "resumeAlreadyPlaying") {
                    return
                }
                try await player.play()
                guard !Task.isCancelled else { return }
                guard self.isExpectedReaderTransportResumeCurrent(expectedReaderTransportBarrier) else {
                    self.logger.info("Apple Music resume cancelled stale reader transport barrier after play")
                    self.pauseSystemPlayerForReaderTransport(reason: "staleReaderTransportResume")
                    self.isPlaying = false
                    self.observedPlayingAsReadingBed = false
                    self.updateMusicPlaybackSurfaceSuppression(reason: "staleReaderTransportResume")
                    self.markPlaybackSurfaceDidChange(reason: "staleReaderTransportResume")
                    return
                }
                self.cancelObservedNonPlayingPause()
                self.shouldIgnoreNextNonPlayingStatus = false
                self.isManuallyPaused = false
                self.isPausedByReaderTransport = false
                self.hasAutoResumeIntent = true
                self.updateMusicPlaybackSurfaceSuppression(reason: "resume")
                if player.state.playbackStatus == .playing, self.isBackgroundMode {
                    self.isPlaying = true
                    self.observedPlayingAsReadingBed = true
                }
                self.updateCurrentTrackInfo(reason: "resume")
                self.schedulePlaybackSurfaceReassertions(reason: "resume")
            } catch {
                self.logger.error("Failed to resume: \(String(describing: error), privacy: .private)")
            }
        }
    }

    func resumeReadingBedForReaderTransport() {
        advanceReaderTransportResumeBarrier(reason: "readerTransportResume")
        let resumeBarrier = readerTransportResumeBarrier
        ownershipState = .appleMusicBed
        clearReaderTransportPauseHold()
        #if DEBUG
        if isE2EMusicBedSyncTest {
            simulateReadingBedPlayForE2E()
            return
        }
        #endif
        shouldIgnoreNextNonPlayingStatus = false
        isManuallyPaused = false
        isPausedByReaderTransport = false
        hasAutoResumeIntent = true
        updateMusicPlaybackSurfaceSuppression(reason: "readerTransportResume")
        resume(userInitiated: false, expectedReaderTransportBarrier: resumeBarrier)
    }

    func pauseReadingBedForReaderTransport() {
        #if DEBUG
        if isE2EMusicBedSyncTest {
            simulateReadingBedPauseForE2E()
            return
        }
        #endif
        adoptPauseAsReaderTransport(reason: "readerTransportPause", source: "reader transport")
    }

    func setReaderTransportPauseAdoptionHandler(
        owner: AnyObject,
        handler: @escaping (String, String) -> Void
    ) {
        readerTransportPauseAdoptionHandlerOwner = ObjectIdentifier(owner)
        readerTransportPauseAdoptionHandler = handler
    }

    func clearReaderTransportPauseAdoptionHandler(owner: AnyObject) {
        guard readerTransportPauseAdoptionHandlerOwner == ObjectIdentifier(owner) else { return }
        readerTransportPauseAdoptionHandlerOwner = nil
        readerTransportPauseAdoptionHandler = nil
    }

    @discardableResult
    func settleAlreadyPlayingReadingBedForAutoResume(reason: String) -> Bool {
        guard isReadingBedAlreadyPlayingForAutoResume,
              !isPausedByReaderTransport,
              !isReaderTransportPauseGuardActive
        else {
            return false
        }
        cancelObservedNonPlayingPause()
        shouldIgnoreNextNonPlayingStatus = false
        isManuallyPaused = false
        isPausedByReaderTransport = false
        hasAutoResumeIntent = true
        isPlaying = true
        observedPlayingAsReadingBed = true
        updateMusicPlaybackSurfaceSuppression(reason: reason)
        if currentSongTitle == nil {
            updateCurrentTrackInfo(reason: reason)
        }
        #if DEBUG
        e2eMusicBedAlreadyPlayingResumeSkipCount += 1
        #endif
        logger.debug("Apple Music auto-resume skipped because bed is already playing")
        return true
    }

    private var isReadingBedAlreadyPlayingForAutoResume: Bool {
        #if DEBUG
        if isE2EMusicBedSyncTest, isPlaying, isBackgroundMode {
            return true
        }
        #endif
        return ApplicationMusicPlayer.shared.state.playbackStatus == .playing && isBackgroundMode
    }

    func pause(userInitiated: Bool = true) {
        cancelReaderTransportResumeTask(reason: userInitiated ? "manualPause" : "pause")
        cancelPlaybackSurfaceReassertions()
        cancelObservedNonPlayingPause()
        if userInitiated {
            clearReaderTransportPauseHold()
            isManuallyPaused = true
            isPausedByReaderTransport = false
            hasAutoResumeIntent = false
            observedPlayingAsReadingBed = false
            shouldIgnoreNextNonPlayingStatus = true
            updateMusicPlaybackSurfaceSuppression(reason: "manualPause")
        } else {
            shouldIgnoreNextNonPlayingStatus = true
        }
        ApplicationMusicPlayer.shared.pause()
    }

    func isReaderTransportResumeBarrierCurrent(_ barrier: Int) -> Bool {
        readerTransportResumeBarrier == barrier
    }

    func refreshMusicPlaybackSurfaceSuppression(reason: String) {
        updateMusicPlaybackSurfaceSuppression(reason: reason)
        reassertFullscreenMusicArtworkSuppressionIfNeeded(reason: reason)
    }

    func updateReaderNarrationActivityForMusicBed(isActive: Bool, reason: String) {
        guard ownershipState == .appleMusicBed else {
            isReaderNarrationActiveForMusicBed = false
            return
        }
        guard isReaderNarrationActiveForMusicBed != isActive else { return }
        isReaderNarrationActiveForMusicBed = isActive
        logger.info(
            "Apple Music reader narration activity=\(isActive, privacy: .public) reason=\(reason, privacy: .public)"
        )
    }

    func prepareForNarrationMix() {
        guard hasQueuedMusicForAutoResume else { return }
        if !isManuallyPaused {
            hasAutoResumeIntent = true
        }
    }

    func prepareDeferredReadingBedResumeForReaderTransport() {
        guard ownershipState == .appleMusicBed else { return }
        clearReaderTransportPauseHold()
        cancelObservedNonPlayingPause()
        shouldIgnoreNextNonPlayingStatus = false
        isManuallyPaused = false
        isPausedByReaderTransport = false
        hasAutoResumeIntent = true
        updateMusicPlaybackSurfaceSuppression(reason: "readerTransportDeferredResume")
        markPlaybackSurfaceDidChange(reason: "readerTransportDeferredResume")
    }

    func recoverReadingBedForActiveNarration(reason: String) {
        guard ownershipState == .appleMusicBed else { return }
        guard !isPlaying, !isManuallyPaused, !isPausedByReaderTransport else { return }
        guard !isReaderTransportPauseHoldActive else { return }
        hasAutoResumeIntent = true
        #if DEBUG
        if isE2EMusicBedSyncTest {
            simulateReadingBedPlayForE2E()
            return
        }
        #endif
        guard canAutoResumeReadingBed else { return }
        let now = Date()
        guard now.timeIntervalSince(lastReadingBedRecoveryAttempt) >= readingBedRecoveryInterval else { return }
        lastReadingBedRecoveryAttempt = now
        logger.info("Apple Music reading bed recovery requested reason=\(reason, privacy: .public)")
        resume(userInitiated: false)
    }

    func skipToNext() {
        Task {
            do {
                try await ApplicationMusicPlayer.shared.skipToNextEntry()
                updateCurrentTrackInfo(reason: "skipToNext")
            } catch {
                self.logger.error("Failed to skip next: \(String(describing: error), privacy: .private)")
            }
        }
    }

    func skipToPrevious() {
        Task {
            do {
                try await ApplicationMusicPlayer.shared.skipToPreviousEntry()
                updateCurrentTrackInfo(reason: "skipToPrevious")
            } catch {
                self.logger.error("Failed to skip previous: \(String(describing: error), privacy: .private)")
            }
        }
    }

    func toggleShuffle() {
        let player = ApplicationMusicPlayer.shared
        switch player.state.shuffleMode {
        case .off:
            player.state.shuffleMode = .songs
            shuffleMode = .songs
        default:
            player.state.shuffleMode = .off
            shuffleMode = .off
        }
        persistModes()
    }

    func cycleRepeatMode() {
        let player = ApplicationMusicPlayer.shared
        switch player.state.repeatMode {
        case nil, .some(MusicPlayer.RepeatMode.none):
            player.state.repeatMode = .all
            repeatMode = .all
        case .some(.all):
            player.state.repeatMode = .one
            repeatMode = .one
        default:
            player.state.repeatMode = MusicPlayer.RepeatMode.none
            repeatMode = .off
        }
        persistModes()
    }

    /// Seek to a specific time in the current track.
    func seek(to time: TimeInterval) {
        ApplicationMusicPlayer.shared.playbackTime = time
        playbackTime = time
    }

    private func syncShuffleRepeatFromPlayer() {
        let player = ApplicationMusicPlayer.shared
        switch player.state.shuffleMode {
        case .songs: shuffleMode = .songs
        default: shuffleMode = .off
        }
        switch player.state.repeatMode {
        case .one: repeatMode = .one
        case .all: repeatMode = .all
        default: repeatMode = .off
        }
        persistModes()
    }

    private func persistModes() {
        UserDefaults.standard.set(shuffleMode.rawValue, forKey: MusicPreferences.shuffleModeKey)
        UserDefaults.standard.set(repeatMode.rawValue, forKey: MusicPreferences.repeatModeKey)
    }

    private func restorePersistedState() {
        // Restore shuffle/repeat from UserDefaults
        if let raw = UserDefaults.standard.string(forKey: MusicPreferences.shuffleModeKey),
           let mode = MusicKitShuffleMode(rawValue: raw) {
            shuffleMode = mode
        }
        if let raw = UserDefaults.standard.string(forKey: MusicPreferences.repeatModeKey),
           let mode = MusicKitRepeatMode(rawValue: raw) {
            repeatMode = mode
        }
        // Restore now-playing info from the system player queue
        updateCurrentTrackInfo(reason: "restorePersistedState")
        if currentSongTitle == nil {
            restorePersistedNowPlayingLabel()
        }
    }

    private func applyPersistedModesToPlayer() {
        let player = ApplicationMusicPlayer.shared
        switch shuffleMode {
        case .songs: player.state.shuffleMode = .songs
        case .off: player.state.shuffleMode = .off
        }
        switch repeatMode {
        case .all: player.state.repeatMode = .all
        case .one: player.state.repeatMode = .one
        case .off: player.state.repeatMode = MusicPlayer.RepeatMode.none
        }
    }

    func stop() {
        cancelReaderTransportResumeTask(reason: "stop")
        cancelTVOSSystemPlaybackSurfaceSuppression()
        cancelPlaybackSurfaceReassertions()
        cancelObservedNonPlayingPause()
        shouldIgnoreNextNonPlayingStatus = true
        ApplicationMusicPlayer.shared.stop()
        hasRestoredQueueForAutoResume = false
        currentSongTitle = nil
        currentArtist = nil
        currentArtworkURL = nil
        markPlaybackSurfaceDidChange(reason: "stop")
        isManuallyPaused = false
        isPausedByReaderTransport = false
        hasAutoResumeIntent = false
        observedPlayingAsReadingBed = false
        isReaderNarrationActiveForMusicBed = false
        clearReaderTransportPauseHold()
        ownershipState = .narration
        updateMusicPlaybackSurfaceSuppression(reason: "stop")
    }

    private func persistLastAppleMusicSelection(
        kind: MusicItemKind,
        id: String,
        title: String,
        subtitle: String?,
        artworkURL: URL?
    ) {
        let defaults = UserDefaults.standard
        defaults.set(kind.rawValue, forKey: MusicPreferences.lastAppleMusicKindKey)
        defaults.set(id, forKey: MusicPreferences.lastAppleMusicIDKey)
        defaults.set(title, forKey: MusicPreferences.lastAppleMusicTitleKey)
        if let subtitle, !subtitle.isEmpty {
            defaults.set(subtitle, forKey: MusicPreferences.lastAppleMusicSubtitleKey)
        } else {
            defaults.removeObject(forKey: MusicPreferences.lastAppleMusicSubtitleKey)
        }
        if let artworkURL {
            defaults.set(artworkURL.absoluteString, forKey: MusicPreferences.lastAppleMusicArtworkURLKey)
        } else {
            defaults.removeObject(forKey: MusicPreferences.lastAppleMusicArtworkURLKey)
        }
    }

    private func restorePersistedNowPlayingLabel() {
        let defaults = UserDefaults.standard
        currentSongTitle = defaults.string(forKey: MusicPreferences.lastAppleMusicTitleKey)
        currentArtist = defaults.string(forKey: MusicPreferences.lastAppleMusicSubtitleKey)
        if let rawURL = defaults.string(forKey: MusicPreferences.lastAppleMusicArtworkURLKey) {
            currentArtworkURL = URL(string: rawURL)
        } else {
            currentArtworkURL = nil
        }
        markPlaybackSurfaceDidChange(reason: "restorePersistedLabel")
    }

    private func restoreLastAppleMusicSelectionToQueue() async {
        let defaults = UserDefaults.standard
        guard let rawKind = defaults.string(forKey: MusicPreferences.lastAppleMusicKindKey),
              let kind = MusicItemKind(rawValue: rawKind),
              let rawID = defaults.string(forKey: MusicPreferences.lastAppleMusicIDKey),
              !rawID.isEmpty
        else {
            return
        }
        let itemID = MusicItemID(rawID)
        let player = ApplicationMusicPlayer.shared
        do {
            switch kind {
            case .songs:
                var request = MusicCatalogResourceRequest<Song>(matching: \.id, equalTo: itemID)
                request.limit = 1
                if let song = try await request.response().items.first {
                    player.queue = [song]
                    hasRestoredQueueForAutoResume = true
                }
            case .albums:
                var request = MusicCatalogResourceRequest<Album>(matching: \.id, equalTo: itemID)
                request.limit = 1
                if let album = try await request.response().items.first {
                    player.queue = ApplicationMusicPlayer.Queue(for: [album])
                    hasRestoredQueueForAutoResume = true
                }
            case .artists:
                var request = MusicCatalogResourceRequest<Artist>(matching: \.id, equalTo: itemID)
                request.limit = 1
                if let artist = try await request.response().items.first {
                    let detailed = try await artist.with([.topSongs])
                    if let topSongs = detailed.topSongs, !topSongs.isEmpty {
                        player.queue = ApplicationMusicPlayer.Queue(for: topSongs)
                        hasRestoredQueueForAutoResume = true
                    }
                }
            case .playlists:
                var request = MusicCatalogResourceRequest<Playlist>(matching: \.id, equalTo: itemID)
                request.limit = 1
                if let playlist = try await request.response().items.first {
                    player.queue = ApplicationMusicPlayer.Queue(for: [playlist])
                    hasRestoredQueueForAutoResume = true
                }
            case .stations:
                var request = MusicCatalogResourceRequest<Station>(matching: \.id, equalTo: itemID)
                request.limit = 1
                if let station = try await request.response().items.first {
                    player.queue = ApplicationMusicPlayer.Queue(for: [station])
                    hasRestoredQueueForAutoResume = true
                }
            }
            hasAutoResumeIntent = true
            updateCurrentTrackInfo(reason: "restoreQueue")
            if currentSongTitle == nil {
                restorePersistedNowPlayingLabel()
            }
            logger.info("Apple Music restored reading bed queue persistedSelection=true")
        } catch {
            logger.error("Failed to restore Apple Music reading bed selection: \(String(describing: error), privacy: .private)")
            restorePersistedNowPlayingLabel()
        }
    }

    // MARK: - Ownership Transitions

    /// Activate Apple Music as the reading bed. Sentence playback keeps Now Playing ownership.
    func activateAsReadingBed() async {
        ownershipState = .transitioning
        cancelObservedNonPlayingPause()
        observedPlayingAsReadingBed = false
        let player = ApplicationMusicPlayer.shared
        logger.info("Apple Music reading bed activating queued=\((self.currentSongTitle != nil || player.queue.currentEntry != nil), privacy: .public) playing=\(self.isPlaying, privacy: .public)")
        // If a song is queued, wait for playback to start before the reader reasserts Now Playing.
        if currentSongTitle != nil {
            // Poll for playback confirmation (up to 2s)
            for _ in 0..<20 {
                if player.state.playbackStatus == .playing { break }
                try? await Task.sleep(nanoseconds: 100_000_000) // 100ms
            }
        }
        if player.state.playbackStatus == .playing {
            isPlaying = true
            observedPlayingAsReadingBed = true
        }
        ownershipState = .appleMusicBed
        updateMusicPlaybackSurfaceSuppression(reason: "activateReadingBed")
        logger.info("Apple Music reading bed ownership=appleMusicBed playing=\(self.isPlaying, privacy: .public) observedAsBed=\(self.observedPlayingAsReadingBed, privacy: .public)")
    }

    /// Deactivate Apple Music as the reading bed. Returns after playback is confirmed stopped.
    func deactivateAsReadingBed() async {
        ownershipState = .transitioning
        cancelReaderTransportResumeTask(reason: "deactivateReadingBed")
        cancelPlaybackSurfaceReassertions()
        let wasPlaying = isPlaying
        shouldIgnoreNextNonPlayingStatus = true
        logger.info("Apple Music reading bed deactivating wasPlaying=\(wasPlaying, privacy: .public)")
        ApplicationMusicPlayer.shared.stop()
        if wasPlaying {
            // Wait for stop to propagate so Apple Music releases Now Playing
            let player = ApplicationMusicPlayer.shared
            for _ in 0..<15 {
                if player.state.playbackStatus != .playing { break }
                try? await Task.sleep(nanoseconds: 100_000_000) // 100ms
            }
        }
        currentSongTitle = nil
        currentArtist = nil
        currentArtworkURL = nil
        isManuallyPaused = false
        isPausedByReaderTransport = false
        hasAutoResumeIntent = false
        isReaderNarrationActiveForMusicBed = false
        ownershipState = .narration
        updateMusicPlaybackSurfaceSuppression(reason: "deactivateReadingBed")
        logger.info("Apple Music reading bed ownership=narration")
    }

    // MARK: - Private

    private func observePlaybackState() {
        playbackStateTask = Task { [weak self] in
            let player = ApplicationMusicPlayer.shared
            var lastStatus: MusicPlayer.PlaybackStatus?
            var lastEntryID: MusicPlayer.Queue.Entry.ID?
            while !Task.isCancelled {
                let status = player.state.playbackStatus
                let currentEntryID = player.queue.currentEntry?.id

                // Detect status change OR track change
                let statusChanged = status != lastStatus
                let trackChanged = currentEntryID != lastEntryID

                if statusChanged || trackChanged {
                    lastStatus = status
                    lastEntryID = currentEntryID
                    await MainActor.run {
                        if statusChanged {
                            self?.logger.debug("Apple Music observed playbackStatus=\(String(describing: status), privacy: .public)")
                        }
                        if status == .playing,
                           self?.shouldSuppressObservedPlayDuringReaderPause == true {
                            self?.suppressObservedPlaybackDuringReaderPause(
                                reason: trackChanged && !statusChanged
                                    ? "suppressedObservedTrackChangeDuringReaderPause"
                                    : "suppressedObservedPlayDuringReaderPause"
                            )
                            return
                        }
                        if status != .playing,
                           self?.shouldDeferObservedNonPlayingDuringActiveReadingBed == true {
                            if statusChanged {
                                self?.handleObservedNonPlayingStatus()
                            }
                            self?.logger.info("Apple Music observed transient non-playing deferred during active reading bed")
                            return
                        }
                        self?.isPlaying = status == .playing
                        if status == .playing, self?.isBackgroundMode == true {
                            self?.observedPlayingAsReadingBed = true
                        }
                        if trackChanged || status == .playing {
                            self?.updateCurrentTrackInfo(reason: trackChanged ? "trackChanged" : "playbackStatus")
                        }
                        if statusChanged && status == .playing {
                            self?.shouldIgnoreNextNonPlayingStatus = false
                            if self?.isPausedByReaderTransport == true {
                                self?.logger.info("Apple Music observed reader transport resume from system playback")
                                self?.isManuallyPaused = false
                                self?.isPausedByReaderTransport = false
                                self?.hasAutoResumeIntent = true
                                self?.markPlaybackSurfaceDidChange(reason: "observedReaderTransportResume")
                            }
                            self?.cancelObservedNonPlayingPause()
                            self?.syncShuffleRepeatFromPlayer()
                        }
                        if statusChanged && status != .playing {
                            self?.handleObservedNonPlayingStatus()
                        }
                    }
                }

                // Update playback progress when playing
                if status == .playing {
                    await MainActor.run {
                        self?.updatePlaybackProgress()
                    }
                }

                try? await Task.sleep(nanoseconds: 250_000_000) // 250ms
            }
        }
    }

    private func updatePlaybackProgress() {
        let player = ApplicationMusicPlayer.shared
        playbackTime = player.playbackTime
        if let entry = player.queue.currentEntry {
            // Duration is available from entry's item
            switch entry.item {
            case .song(let song):
                playbackDuration = song.duration ?? 0
            default:
                // For other types, try to get duration from the state if available
                playbackDuration = 0
            }
        } else {
            playbackDuration = 0
        }
    }

    private func handleObservedNonPlayingStatus(allowE2E: Bool = false) {
        #if DEBUG
        guard allowE2E || !isE2EMusicBedSyncTest else { return }
        #endif
        if shouldIgnoreNextNonPlayingStatus {
            if shouldAdoptIgnoredObservedNonPlayingAsReaderPause {
                logger.info("Apple Music ignored non-playing converted to reader transport pause during active tvOS narration")
                shouldIgnoreNextNonPlayingStatus = false
            } else {
                shouldIgnoreNextNonPlayingStatus = false
                return
            }
        }
        guard isBackgroundMode else { return }
        guard shouldTreatObservedNonPlayingAsReaderPause else {
            logger.info(
                "Apple Music observed non-playing ignored observedAsBed=false autoResume=\(self.hasAutoResumeIntent, privacy: .public) isPlaying=\(self.isPlaying, privacy: .public) manual=\(self.isManuallyPaused, privacy: .public) readerPause=\(self.isPausedByReaderTransport, privacy: .public)"
            )
            return
        }
        observedNonPlayingTask?.cancel()
        logger.info(
            "Apple Music observed non-playing candidate observedAsBed=\(self.observedPlayingAsReadingBed, privacy: .public) isPlaying=\(self.isPlaying, privacy: .public) manual=\(self.isManuallyPaused, privacy: .public) readerPause=\(self.isPausedByReaderTransport, privacy: .public)"
        )
        if shouldAdoptObservedNonPlayingImmediately {
            adoptPauseAsReaderTransport(reason: "observedNonPlaying", source: "observed non-playing")
            return
        }
        if shouldDeferObservedNonPlayingDuringActiveReadingBed {
            deferObservedNonPlayingDuringActiveReadingBed(reason: "observedNonPlaying")
            return
        }
        observedNonPlayingTask = Task { @MainActor in
            try? await Task.sleep(nanoseconds: 600_000_000)
            guard !Task.isCancelled else { return }
            guard self.isBackgroundMode else { return }
            guard ApplicationMusicPlayer.shared.state.playbackStatus != .playing else { return }
            guard self.shouldTreatObservedNonPlayingAsReaderPause else {
                self.logger.info("Apple Music observed non-playing confirmation ignored after state changed")
                self.observedNonPlayingTask = nil
                return
            }
            self.observedNonPlayingTask = nil
            self.adoptPauseAsReaderTransport(reason: "observedNonPlaying", source: "observed non-playing")
        }
    }

    private var shouldAdoptIgnoredObservedNonPlayingAsReaderPause: Bool {
        #if os(tvOS)
        return ownershipState == .appleMusicBed &&
            isReaderNarrationActiveForMusicBed &&
            !isPausedByReaderTransport
        #else
        return false
        #endif
    }

    private var shouldAdoptObservedNonPlayingImmediately: Bool {
        #if os(tvOS)
        return ownershipState == .appleMusicBed &&
            !isPausedByReaderTransport &&
            shouldTreatObservedNonPlayingAsReaderPause
        #else
        return false
        #endif
    }

    private func deferObservedNonPlayingDuringActiveReadingBed(reason: String) {
        observedNonPlayingTask?.cancel()
        hasAutoResumeIntent = true
        logger.info("Apple Music observed non-playing deferred for active reading bed reason=\(reason, privacy: .public)")
        observedNonPlayingTask = Task { @MainActor in
            try? await Task.sleep(nanoseconds: 600_000_000)
            guard !Task.isCancelled else { return }
            guard self.isBackgroundMode else { return }
            guard self.shouldDeferObservedNonPlayingDuringActiveReadingBed else {
                self.logger.info("Apple Music deferred non-playing ignored after state changed")
                self.observedNonPlayingTask = nil
                return
            }
            guard ApplicationMusicPlayer.shared.state.playbackStatus != .playing else {
                self.isPlaying = true
                self.observedPlayingAsReadingBed = true
                self.observedNonPlayingTask = nil
                return
            }
            self.observedNonPlayingTask = nil
            self.isPlaying = false
            self.observedPlayingAsReadingBed = false
            self.logger.info("Apple Music deferred non-playing recovering active reading bed")
            self.recoverReadingBedForActiveNarration(reason: "deferredObservedNonPlaying")
        }
    }

    private func cancelObservedNonPlayingPause() {
        observedNonPlayingTask?.cancel()
        observedNonPlayingTask = nil
    }

    private func cancelPlaybackSurfaceReassertions() {
        playbackSurfaceReassertionTask?.cancel()
        playbackSurfaceReassertionTask = nil
    }

    private var shouldReassertPlaybackSurface: Bool {
        isBackgroundMode &&
            !isManuallyPaused &&
            (isPlaying || hasAutoResumeIntent)
    }

    func reconcileReadingBedSystemPlayback() {
        #if DEBUG
        guard !isE2EMusicBedSyncTest else { return }
        #endif
        guard isBackgroundMode else { return }
        guard !isReaderTransportPauseSuppressionActive else {
            logger.info("Apple Music reconcile suppressed during reader transport pause")
            pauseSystemPlayerForReaderTransport(reason: "reconcileReaderPause")
            isPlaying = false
            observedPlayingAsReadingBed = false
            updateMusicPlaybackSurfaceSuppression(reason: "reconcileReaderPause")
            return
        }
        let isSystemPlaying = ApplicationMusicPlayer.shared.state.playbackStatus == .playing
        if isSystemPlaying {
            isPlaying = true
            observedPlayingAsReadingBed = true
            cancelObservedNonPlayingPause()
            return
        }
        logger.info(
            "Apple Music reconcile found system non-playing observedAsBed=\(self.observedPlayingAsReadingBed, privacy: .public) isPlaying=\(self.isPlaying, privacy: .public) manual=\(self.isManuallyPaused, privacy: .public) readerPause=\(self.isPausedByReaderTransport, privacy: .public)"
        )
        if shouldDeferObservedNonPlayingDuringActiveReadingBed {
            logger.info("Apple Music reconcile deferred transient non-playing during active reading bed")
            handleObservedNonPlayingStatus()
            return
        }
        isPlaying = false
        handleObservedNonPlayingStatus()
    }

    private func updateCurrentTrackInfo(reason: String) {
        guard let entry = ApplicationMusicPlayer.shared.queue.currentEntry else {
            currentSongTitle = nil
            currentArtist = nil
            currentArtworkURL = nil
            markPlaybackSurfaceDidChange(reason: reason)
            return
        }
        currentSongTitle = entry.title
        currentArtist = entry.subtitle
        if let artwork = entry.artwork {
            currentArtworkURL = artwork.url(width: 300, height: 300)
        } else {
            currentArtworkURL = nil
        }
        markPlaybackSurfaceDidChange(reason: reason)
    }

    private func markPlaybackSurfaceDidChange(reason: String) {
        playbackSurfaceRevision &+= 1
        logger.debug("Apple Music playback surface changed reason=\(reason, privacy: .public) revision=\(self.playbackSurfaceRevision, privacy: .public)")
    }

    private var shouldSuppressObservedPlayDuringReaderPause: Bool {
        isReaderTransportPauseGuardActive
    }

    private var shouldTreatObservedNonPlayingAsReaderPause: Bool {
        #if os(tvOS)
        if ownershipState == .appleMusicBed && isReaderNarrationActiveForMusicBed {
            return true
        }
        #endif
        return observedPlayingAsReadingBed ||
            hasAutoResumeIntent ||
            isPausedByReaderTransport
    }

    private var shouldDeferObservedNonPlayingDuringActiveReadingBed: Bool {
        return ownershipState == .appleMusicBed &&
            isReaderNarrationActiveForMusicBed &&
            !isManuallyPaused &&
            !isPausedByReaderTransport &&
            !isReaderTransportPauseGuardActive
    }

    private func suppressObservedPlaybackDuringReaderPause(reason: String) {
        logger.info("Apple Music observed play suppressed during reader transport pause")
        isPlaying = false
        observedPlayingAsReadingBed = false
        isManuallyPaused = true
        isPausedByReaderTransport = true
        hasAutoResumeIntent = false
        shouldIgnoreNextNonPlayingStatus = true
        updateMusicPlaybackSurfaceSuppression(reason: "suppressedObservedPlay")
        ApplicationMusicPlayer.shared.pause()
        markPlaybackSurfaceDidChange(reason: reason)
    }

    private func adoptPauseAsReaderTransport(reason: String, source: String) {
        advanceReaderTransportResumeBarrier(reason: reason)
        cancelReaderTransportResumeTask(reason: reason)
        cancelPlaybackSurfaceReassertions()
        cancelObservedNonPlayingPause()
        logger.info(
            "Apple Music reader transport pause adopted source=\(source, privacy: .public) reason=\(reason, privacy: .public)"
        )
        isManuallyPaused = true
        isPausedByReaderTransport = true
        hasAutoResumeIntent = false
        observedPlayingAsReadingBed = false
        shouldIgnoreNextNonPlayingStatus = true
        beginReaderTransportPauseHold()
        isPlaying = false
        updateMusicPlaybackSurfaceSuppression(reason: reason)
        pauseSystemPlayerForReaderTransport(reason: reason)
        readerTransportPauseAdoptionRevision &+= 1
        notifyReaderTransportPauseAdoptionIfNeeded(reason: reason, source: source)
        markPlaybackSurfaceDidChange(reason: reason)
        scheduleReaderTransportPauseConfirmation()
    }

    private func notifyReaderTransportPauseAdoptionIfNeeded(reason: String, source: String) {
        guard source != "reader transport" else { return }
        readerTransportPauseAdoptionHandler?(reason, source)
    }

    private func beginReaderTransportPauseHold() {
        readerTransportPauseConfirmationTask?.cancel()
        readerTransportPauseConfirmationTask = nil
        readerTransportPauseHoldUntil = Date().addingTimeInterval(readerTransportPauseHoldDuration)
        readerTransportPauseDuplicateHoldUntil = Date().addingTimeInterval(readerTransportPauseDuplicateHoldDuration)
    }

    private func clearReaderTransportPauseHold() {
        readerTransportPauseHoldUntil = Date.distantPast
        readerTransportPauseDuplicateHoldUntil = Date.distantPast
        readerTransportPauseConfirmationTask?.cancel()
        readerTransportPauseConfirmationTask = nil
    }

    private func cancelReaderTransportResumeTask(reason: String) {
        guard readerTransportResumeTask != nil else { return }
        readerTransportResumeTask?.cancel()
        readerTransportResumeTask = nil
        readerTransportResumeTaskID &+= 1
        logger.info("Apple Music reader transport resume task cancelled reason=\(reason, privacy: .public)")
    }

    private func isExpectedReaderTransportResumeCurrent(_ expectedBarrier: Int?) -> Bool {
        guard let expectedBarrier else { return true }
        return readerTransportResumeBarrier == expectedBarrier &&
            !isReaderTransportPauseGuardActive &&
            !isPausedByReaderTransport
    }

    private func advanceReaderTransportResumeBarrier(reason: String) {
        readerTransportResumeBarrier &+= 1
        logger.debug(
            "Apple Music reader transport barrier advanced reason=\(reason, privacy: .public) value=\(self.readerTransportResumeBarrier, privacy: .public)"
        )
    }

    private func scheduleReaderTransportPauseConfirmation() {
        readerTransportPauseConfirmationTask?.cancel()
        readerTransportPauseConfirmationTask = Task { @MainActor in
            while !Task.isCancelled {
                try? await Task.sleep(nanoseconds: 250_000_000)
                guard !Task.isCancelled else { return }
                guard self.shouldSuppressObservedPlayDuringReaderPause else {
                    self.readerTransportPauseConfirmationTask = nil
                    return
                }
                guard ApplicationMusicPlayer.shared.state.playbackStatus == .playing else {
                    continue
                }
                self.logger.info("Apple Music reader transport pause confirmation re-pausing stray system playback")
                self.shouldIgnoreNextNonPlayingStatus = true
                self.isPlaying = false
                self.observedPlayingAsReadingBed = false
                self.updateMusicPlaybackSurfaceSuppression(reason: "readerTransportPauseConfirmation")
                self.pauseSystemPlayerForReaderTransport(reason: "readerTransportPauseConfirmation")
                self.markPlaybackSurfaceDidChange(reason: "readerTransportPauseConfirmation")
            }
        }
    }

    private func pauseSystemPlayerForReaderTransport(reason: String) {
        #if os(tvOS)
        ApplicationMusicPlayer.shared.pause()
        scheduleTVOSSystemPlaybackSurfaceSuppression(reason: reason)
        logger.info(
            "Apple Music reader transport paused tvOS system playback surface reason=\(reason, privacy: .public)"
        )
        #else
        ApplicationMusicPlayer.shared.pause()
        #endif
    }

    private func cancelTVOSSystemPlaybackSurfaceSuppression() {
        #if os(tvOS)
        tvOSSystemSurfaceSuppressionTask?.cancel()
        tvOSSystemSurfaceSuppressionTask = nil
        #endif
    }

    private func startTVOSMusicSurfaceSuppressionWatchdog(reason: String) {
        #if os(tvOS)
        guard tvOSMusicSurfaceSuppressionWatchdogTask == nil else { return }
        tvOSMusicSurfaceSuppressionWatchdogTask = Task { @MainActor in
            self.logger.info(
                "Apple Music fullscreen artwork suppression watchdog started reason=\(reason, privacy: .public)"
            )
            while !Task.isCancelled {
                try? await Task.sleep(nanoseconds: 1_000_000_000)
                guard !Task.isCancelled else { return }
                guard self.shouldKeepFullscreenMusicArtworkSuppressed else {
                    self.tvOSMusicSurfaceSuppressionWatchdogTask = nil
                    return
                }
                self.reassertFullscreenMusicArtworkSuppressionIfNeeded(reason: "tvOSFullscreenWatchdog")
            }
        }
        #endif
    }

    private func stopTVOSMusicSurfaceSuppressionWatchdog() {
        #if os(tvOS)
        tvOSMusicSurfaceSuppressionWatchdogTask?.cancel()
        tvOSMusicSurfaceSuppressionWatchdogTask = nil
        #endif
    }

    private func scheduleTVOSSystemPlaybackSurfaceSuppression(reason: String) {
        #if os(tvOS)
        tvOSSystemSurfaceSuppressionTask?.cancel()
        tvOSSystemSurfaceSuppressionTask = Task { @MainActor in
            defer { self.tvOSSystemSurfaceSuppressionTask = nil }
            let suppressionDelays: [UInt64] = [
                250_000_000,
                750_000_000,
                1_500_000_000,
                2_500_000_000,
                4_000_000_000,
                6_000_000_000,
                9_000_000_000,
                12_500_000_000,
                15_000_000_000
            ]
            for delay in suppressionDelays {
                try? await Task.sleep(nanoseconds: delay)
                guard !Task.isCancelled else { return }
                guard self.shouldSuppressObservedPlayDuringReaderPause else {
                    return
                }
                self.updateFullscreenMusicArtworkSuppression(true, reason: "\(reason)-tvOSSurfaceSuppression")
                if ApplicationMusicPlayer.shared.state.playbackStatus == .playing {
                    self.logger.info("Apple Music tvOS playback surface suppression re-pausing stray playback")
                    self.shouldIgnoreNextNonPlayingStatus = true
                    ApplicationMusicPlayer.shared.pause()
                    self.isPlaying = false
                    self.observedPlayingAsReadingBed = false
                    self.markPlaybackSurfaceDidChange(reason: "\(reason)-tvOSSurfaceRepaused")
                } else {
                    self.markPlaybackSurfaceDidChange(reason: "\(reason)-tvOSSurfaceSuppressed")
                }
            }
            self.logger.info(
                "Apple Music reader transport kept tvOS playback surface suppressed reason=\(reason, privacy: .public)"
            )
        }
        logger.info(
            "Apple Music reader transport scheduled tvOS system playback surface suppression reason=\(reason, privacy: .public)"
        )
        #endif
    }

    private func updateMusicPlaybackSurfaceSuppression(reason: String) {
        let shouldSuppress = ownershipState == .appleMusicBed || isReaderTransportPauseSuppressionActive
        updateFullscreenMusicArtworkSuppression(shouldSuppress, reason: reason)
        guard isSuppressingMusicPlaybackSurface != shouldSuppress else { return }
        isSuppressingMusicPlaybackSurface = shouldSuppress
        logger.info(
            "Apple Music playback surface suppression=\(shouldSuppress, privacy: .public) reason=\(reason, privacy: .public)"
        )
    }

    private func updateFullscreenMusicArtworkSuppression(_ shouldSuppress: Bool, reason: String) {
        #if os(tvOS)
        if shouldSuppress {
            startTVOSMusicSurfaceSuppressionWatchdog(reason: reason)
        } else {
            stopTVOSMusicSurfaceSuppressionWatchdog()
        }
        let wasSuppressed = PlaybackIdleTimerCoordinator.shared.isMusicSurfaceSuppressed
        guard didDisableIdleTimerForMusicSurface != shouldSuppress || wasSuppressed != shouldSuppress else { return }
        didDisableIdleTimerForMusicSurface = shouldSuppress
        PlaybackIdleTimerCoordinator.shared.setMusicSurfaceIdleDisabled(shouldSuppress)
        logger.info(
            "Apple Music fullscreen artwork suppression=\(shouldSuppress, privacy: .public) reason=\(reason, privacy: .public)"
        )
        #endif
    }

    private var shouldKeepFullscreenMusicArtworkSuppressed: Bool {
        ownershipState == .appleMusicBed || isReaderTransportPauseSuppressionActive || isSuppressingMusicPlaybackSurface
    }

    private func reassertFullscreenMusicArtworkSuppressionIfNeeded(reason: String) {
        #if os(tvOS)
        guard shouldKeepFullscreenMusicArtworkSuppressed else { return }
        let wasSuppressed = PlaybackIdleTimerCoordinator.shared.isMusicSurfaceSuppressed
        PlaybackIdleTimerCoordinator.shared.reassertMusicSurfaceIdleDisabled()
        guard !wasSuppressed, PlaybackIdleTimerCoordinator.shared.isMusicSurfaceSuppressed else { return }
        logger.info(
            "Apple Music fullscreen artwork suppression reasserted reason=\(reason, privacy: .public)"
        )
        markPlaybackSurfaceDidChange(reason: "\(reason)-fullscreenSuppressionReasserted")
        #endif
    }

    #if DEBUG
    func simulateObservedNonPlayingPauseForE2E() {
        guard ProcessInfo.processInfo.environment["E2E_MUSIC_BED_SYNC_TEST"] == "1" else { return }
        if isPausedByReaderTransport {
            simulateReadingBedPlayForE2E()
            return
        }
        ownershipState = .appleMusicBed
        isPlaying = false
        isManuallyPaused = false
        isPausedByReaderTransport = false
        shouldIgnoreNextNonPlayingStatus = false
        #if os(tvOS)
        hasAutoResumeIntent = false
        observedPlayingAsReadingBed = false
        #else
        hasAutoResumeIntent = true
        observedPlayingAsReadingBed = true
        #endif
        isReaderNarrationActiveForMusicBed = true
        e2eMusicBedSyncPhase = "observedPause"
        updateMusicPlaybackSurfaceSuppression(reason: "e2eObservedPause")
        logger.info("Apple Music E2E simulated observed non-playing pause")
        handleObservedNonPlayingStatus(allowE2E: true)
        if isPausedByReaderTransport {
            e2eMusicBedSyncPhase = "observedPauseImmediate"
        }
        #if os(tvOS)
        Task { @MainActor in
            try? await Task.sleep(nanoseconds: 8_000_000_000)
            guard self.e2eMusicBedSyncPhase == "observedPauseImmediate" else { return }
            self.simulateReadingBedPlayForE2E()
        }
        #endif
        markPlaybackSurfaceDidChange(reason: "e2eObservedNonPlayingPause")
    }

    func simulateReadingBedPauseForE2E() {
        guard ProcessInfo.processInfo.environment["E2E_MUSIC_BED_SYNC_TEST"] == "1" else { return }
        isAuthorized = true
        persistAppleMusicBedPreferenceForE2E()
        advanceReaderTransportResumeBarrier(reason: "e2ePause")
        cancelReaderTransportResumeTask(reason: "e2ePause")
        cancelPlaybackSurfaceReassertions()
        cancelObservedNonPlayingPause()
        ownershipState = .appleMusicBed
        isPlaying = false
        isManuallyPaused = true
        isPausedByReaderTransport = true
        shouldIgnoreNextNonPlayingStatus = true
        hasAutoResumeIntent = false
        observedPlayingAsReadingBed = false
        beginReaderTransportPauseHold()
        #if os(tvOS)
        e2eMusicBedSyncPhase = "observedPauseImmediate"
        #else
        e2eMusicBedSyncPhase = "pause"
        #endif
        updateMusicPlaybackSurfaceSuppression(reason: "e2ePause")
        logger.info("Apple Music E2E simulated bed pause")
        markPlaybackSurfaceDidChange(reason: "e2eSimulatedBedPause")
        scheduleReaderTransportPauseConfirmation()
    }

    func simulateReadingBedPlayForE2E() {
        guard ProcessInfo.processInfo.environment["E2E_MUSIC_BED_SYNC_TEST"] == "1" else { return }
        isAuthorized = true
        persistAppleMusicBedPreferenceForE2E()
        advanceReaderTransportResumeBarrier(reason: "e2ePlay")
        clearReaderTransportPauseHold()
        ownershipState = .appleMusicBed
        isManuallyPaused = false
        isPausedByReaderTransport = false
        shouldIgnoreNextNonPlayingStatus = false
        hasAutoResumeIntent = true
        isPlaying = true
        observedPlayingAsReadingBed = true
        e2eMusicBedSyncPhase = "play"
        isSuppressingMusicPlaybackSurface = true
        updateFullscreenMusicArtworkSuppression(true, reason: "e2ePlay")
        updateMusicPlaybackSurfaceSuppression(reason: "e2ePlay")
        logger.info("Apple Music E2E simulated bed play")
        markPlaybackSurfaceDidChange(reason: "e2eSimulatedBedPlay")
    }

    private func persistAppleMusicBedPreferenceForE2E() {
        UserDefaults.standard.set(true, forKey: MusicPreferences.useAppleMusicKey)
        UserDefaults.standard.set(true, forKey: MusicPreferences.readingBedEnabledKey)
    }

    func ensureReadingBedPlayStateForE2E() {
        guard ProcessInfo.processInfo.environment["E2E_MUSIC_BED_SYNC_TEST"] == "1" else { return }
        guard e2eMusicBedSyncPhase == "play" else { return }
        guard ownershipState != .appleMusicBed || !isSuppressingMusicPlaybackSurface else { return }
        ownershipState = .appleMusicBed
        isSuppressingMusicPlaybackSurface = true
        updateFullscreenMusicArtworkSuppression(true, reason: "e2ePlayStateReassert")
        markPlaybackSurfaceDidChange(reason: "e2ePlayStateReassert")
    }

    func simulateAlreadyPlayingAutoResumeForE2E() {
        guard ProcessInfo.processInfo.environment["E2E_MUSIC_BED_SYNC_TEST"] == "1" else { return }
        ownershipState = .appleMusicBed
        isManuallyPaused = false
        isPausedByReaderTransport = false
        shouldIgnoreNextNonPlayingStatus = false
        hasAutoResumeIntent = true
        isPlaying = true
        observedPlayingAsReadingBed = true
        isReaderNarrationActiveForMusicBed = true
        clearReaderTransportPauseHold()
        if settleAlreadyPlayingReadingBedForAutoResume(reason: "e2eAlreadyPlayingAutoResume") {
            e2eMusicBedSyncPhase = "alreadyPlayingAutoResume"
        } else {
            e2eMusicBedSyncPhase = "alreadyPlayingAutoResumeMissed"
        }
        logger.info("Apple Music E2E simulated already-playing auto-resume")
        markPlaybackSurfaceDidChange(reason: "e2eAlreadyPlayingAutoResume")
    }

    func simulateSentenceTransitionForE2E(phase: String = "sentenceTransition") {
        guard ProcessInfo.processInfo.environment["E2E_MUSIC_BED_SYNC_TEST"] == "1" else { return }
        ownershipState = .appleMusicBed
        isManuallyPaused = false
        isPausedByReaderTransport = false
        shouldIgnoreNextNonPlayingStatus = false
        hasAutoResumeIntent = true
        isPlaying = true
        observedPlayingAsReadingBed = true
        isReaderNarrationActiveForMusicBed = true
        clearReaderTransportPauseHold()
        e2eMusicBedSyncPhase = phase
        updateMusicPlaybackSurfaceSuppression(reason: "e2eSentenceTransition")
        logger.info("Apple Music E2E simulated sentence transition phase=\(phase, privacy: .public)")
        markPlaybackSurfaceDidChange(reason: "e2eSentenceTransition")
    }

    #endif

    private func schedulePlaybackSurfaceReassertions(reason: String) {
        cancelPlaybackSurfaceReassertions()
        playbackSurfaceReassertionTask = Task { @MainActor in
            for delay in [300_000_000, 900_000_000, 1_800_000_000] as [UInt64] {
                try? await Task.sleep(nanoseconds: delay)
                guard !Task.isCancelled else { return }
                guard self.shouldReassertPlaybackSurface else { return }
                self.updateCurrentTrackInfo(reason: "\(reason)-reader-reassert")
            }
            self.playbackSurfaceReassertionTask = nil
        }
    }

    #else
    // Stubs for platforms without MusicKit
    private init() {}
    func requestAuthorization() async -> Bool { false }
    func resume(userInitiated: Bool = true) {
        if userInitiated {
            isManuallyPaused = false
            isPausedByReaderTransport = false
        }
    }
    func resumeReadingBedForReaderTransport() {
        isManuallyPaused = false
        isPausedByReaderTransport = false
        isSuppressingMusicPlaybackSurface = ownershipState == .appleMusicBed
    }
    func isReaderTransportResumeBarrierCurrent(_ barrier: Int) -> Bool { barrier == 0 }
    func refreshMusicPlaybackSurfaceSuppression(reason: String) {
        isSuppressingMusicPlaybackSurface = ownershipState == .appleMusicBed
    }
    func pauseReadingBedForReaderTransport() {
        isManuallyPaused = true
        isPausedByReaderTransport = true
        isSuppressingMusicPlaybackSurface = true
    }
    func settleAlreadyPlayingReadingBedForAutoResume(reason: String) -> Bool {
        guard isPlaying, ownershipState == .appleMusicBed else { return false }
        isManuallyPaused = false
        isPausedByReaderTransport = false
        hasAutoResumeIntent = true
        isSuppressingMusicPlaybackSurface = true
        #if DEBUG
        e2eMusicBedAlreadyPlayingResumeSkipCount += 1
        #endif
        return true
    }
    func recoverReadingBedForActiveNarration(reason: String) {}
    func pause(userInitiated: Bool = true) {
        if userInitiated {
            isManuallyPaused = true
            isPausedByReaderTransport = false
            isSuppressingMusicPlaybackSurface = ownershipState == .appleMusicBed
        }
    }
    func prepareForNarrationMix() {}
    func prepareDeferredReadingBedResumeForReaderTransport() {}
    func reconcileReadingBedSystemPlayback() {}
    func skipToNext() {}
    func skipToPrevious() {}
    func toggleShuffle() {}
    func cycleRepeatMode() {}
    func seek(to time: TimeInterval) {}
    func stop() {
        currentSongTitle = nil
        currentArtist = nil
        currentArtworkURL = nil
        isManuallyPaused = false
        isPausedByReaderTransport = false
        ownershipState = .narration
        isSuppressingMusicPlaybackSurface = false
        playbackTime = 0
        playbackDuration = 0
    }
    func activateAsReadingBed() async {
        ownershipState = .appleMusicBed
        isSuppressingMusicPlaybackSurface = true
    }
    func deactivateAsReadingBed() async {
        ownershipState = .narration
        isSuppressingMusicPlaybackSurface = false
    }

    #if DEBUG
    func simulateReadingBedPauseForE2E() {
        guard ProcessInfo.processInfo.environment["E2E_MUSIC_BED_SYNC_TEST"] == "1" else { return }
        ownershipState = .appleMusicBed
        isPlaying = false
        isManuallyPaused = true
        isPausedByReaderTransport = true
        hasAutoResumeIntent = false
        #if os(tvOS)
        e2eMusicBedSyncPhase = "observedPauseImmediate"
        #else
        e2eMusicBedSyncPhase = "pause"
        #endif
        isSuppressingMusicPlaybackSurface = true
        playbackSurfaceRevision &+= 1
    }

    func simulateReadingBedPlayForE2E() {
        guard ProcessInfo.processInfo.environment["E2E_MUSIC_BED_SYNC_TEST"] == "1" else { return }
        ownershipState = .appleMusicBed
        isManuallyPaused = false
        isPausedByReaderTransport = false
        readerTransportPauseHoldUntil = Date.distantPast
        readerTransportPauseDuplicateHoldUntil = Date.distantPast
        hasAutoResumeIntent = true
        isPlaying = true
        e2eMusicBedSyncPhase = "play"
        isSuppressingMusicPlaybackSurface = true
        playbackSurfaceRevision &+= 1
    }

    func simulateAlreadyPlayingAutoResumeForE2E() {
        guard ProcessInfo.processInfo.environment["E2E_MUSIC_BED_SYNC_TEST"] == "1" else { return }
        ownershipState = .appleMusicBed
        isPlaying = true
        isManuallyPaused = false
        isPausedByReaderTransport = false
        hasAutoResumeIntent = true
        isSuppressingMusicPlaybackSurface = true
        _ = settleAlreadyPlayingReadingBedForAutoResume(reason: "e2eAlreadyPlayingAutoResume")
        e2eMusicBedSyncPhase = "alreadyPlayingAutoResume"
        playbackSurfaceRevision &+= 1
    }

    func simulateSentenceTransitionForE2E(phase: String = "sentenceTransition") {
        guard ProcessInfo.processInfo.environment["E2E_MUSIC_BED_SYNC_TEST"] == "1" else { return }
        ownershipState = .appleMusicBed
        isPlaying = true
        isManuallyPaused = false
        isPausedByReaderTransport = false
        hasAutoResumeIntent = true
        isSuppressingMusicPlaybackSurface = true
        e2eMusicBedSyncPhase = phase
        playbackSurfaceRevision &+= 1
    }

    #endif
    #endif
}
