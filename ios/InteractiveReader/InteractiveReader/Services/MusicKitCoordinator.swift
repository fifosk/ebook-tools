import Foundation
import Combine
import OSLog
#if canImport(MusicKit)
import MusicKit
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
    @Published private(set) var ownershipState: AudioOwnership = .narration
    @Published private(set) var isManuallyPaused = false
    @Published private(set) var hasAutoResumeIntent = false
    @Published var shuffleMode: MusicKitShuffleMode = .off
    @Published var repeatMode: MusicKitRepeatMode = .off

    // Playback progress for timeline UI
    @Published private(set) var playbackTime: TimeInterval = 0
    @Published private(set) var playbackDuration: TimeInterval = 0

    /// Whether Apple Music is actively serving as the reading bed.
    var isBackgroundMode: Bool { ownershipState == .appleMusic || ownershipState == .appleMusicBed }
    var canAutoResumeReadingBed: Bool {
        hasQueuedMusicForAutoResume && !isManuallyPaused && hasAutoResumeIntent
    }
    private var hasQueuedMusicForAutoResume: Bool {
        #if canImport(MusicKit)
        return currentSongTitle != nil || ApplicationMusicPlayer.shared.queue.currentEntry != nil
        #else
        return currentSongTitle != nil
        #endif
    }
    private let logger = Logger(subsystem: "InteractiveReader", category: "MusicKit")

    #if canImport(MusicKit)
    private var playbackStateTask: Task<Void, Never>?
    private var shouldIgnoreNextNonPlayingStatus = false

    private init() {
        isAuthorized = MusicAuthorization.currentStatus == .authorized
        restorePersistedState()
        applyPersistedModesToPlayer()
        observePlaybackState()
    }

    deinit {
        playbackStateTask?.cancel()
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
        do {
            try await player.play()
            isManuallyPaused = false
            hasAutoResumeIntent = true
            persistLastAppleMusicSelection(
                kind: .songs,
                id: song.id.rawValue,
                title: song.title,
                subtitle: song.artistName,
                artworkURL: song.artwork?.url(width: 300, height: 300)
            )
            updateCurrentTrackInfo()
        } catch {
            logger.error("Failed to play song: \(String(describing: error), privacy: .private)")
        }
    }

    // MARK: - Playback: Station

    func playStation(_ station: Station) async {
        let player = ApplicationMusicPlayer.shared
        player.queue = ApplicationMusicPlayer.Queue(for: [station])
        do {
            try await player.play()
            isManuallyPaused = false
            hasAutoResumeIntent = true
            persistLastAppleMusicSelection(
                kind: .stations,
                id: station.id.rawValue,
                title: station.name,
                subtitle: nil,
                artworkURL: station.artwork?.url(width: 300, height: 300)
            )
            updateCurrentTrackInfo()
        } catch {
            logger.error("Failed to play station: \(String(describing: error), privacy: .private)")
        }
    }

    // MARK: - Playback: Album

    func playAlbum(_ album: Album) async {
        let player = ApplicationMusicPlayer.shared
        player.queue = ApplicationMusicPlayer.Queue(for: [album])
        do {
            try await player.play()
            isManuallyPaused = false
            hasAutoResumeIntent = true
            persistLastAppleMusicSelection(
                kind: .albums,
                id: album.id.rawValue,
                title: album.title,
                subtitle: album.artistName,
                artworkURL: album.artwork?.url(width: 300, height: 300)
            )
            updateCurrentTrackInfo()
        } catch {
            logger.error("Failed to play album: \(String(describing: error), privacy: .private)")
        }
    }

    // MARK: - Playback: Playlist

    func playPlaylist(_ playlist: Playlist) async {
        let player = ApplicationMusicPlayer.shared
        player.queue = ApplicationMusicPlayer.Queue(for: [playlist])
        do {
            try await player.play()
            isManuallyPaused = false
            hasAutoResumeIntent = true
            persistLastAppleMusicSelection(
                kind: .playlists,
                id: playlist.id.rawValue,
                title: playlist.name,
                subtitle: playlist.curatorName,
                artworkURL: playlist.artwork?.url(width: 300, height: 300)
            )
            updateCurrentTrackInfo()
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
            try await player.play()
            isManuallyPaused = false
            hasAutoResumeIntent = true
            persistLastAppleMusicSelection(
                kind: .artists,
                id: artist.id.rawValue,
                title: artist.name,
                subtitle: nil,
                artworkURL: artist.artwork?.url(width: 300, height: 300)
            )
            updateCurrentTrackInfo()
        } catch {
            logger.error("Failed to play artist top songs: \(String(describing: error), privacy: .private)")
        }
    }

    func ensureLastSelectionLoadedForReadingBed() async {
        guard isAuthorized else { return }
        if currentSongTitle != nil || ApplicationMusicPlayer.shared.queue.currentEntry != nil {
            return
        }
        await restoreLastAppleMusicSelectionToQueue()
    }

    // MARK: - Transport Controls

    func resume(userInitiated: Bool = true) {
        if userInitiated {
            isManuallyPaused = false
        } else {
            guard canAutoResumeReadingBed else { return }
        }
        let player = ApplicationMusicPlayer.shared
        Task {
            do {
                try await player.play()
                self.hasAutoResumeIntent = true
            } catch {
                self.logger.error("Failed to resume: \(String(describing: error), privacy: .private)")
            }
        }
    }

    func pause(userInitiated: Bool = true) {
        if userInitiated {
            isManuallyPaused = true
            hasAutoResumeIntent = false
        } else {
            shouldIgnoreNextNonPlayingStatus = true
        }
        ApplicationMusicPlayer.shared.pause()
    }

    func prepareForNarrationMix() {
        guard hasQueuedMusicForAutoResume else { return }
        shouldIgnoreNextNonPlayingStatus = true
        if !isManuallyPaused {
            hasAutoResumeIntent = true
        }
    }

    func skipToNext() {
        Task {
            do {
                try await ApplicationMusicPlayer.shared.skipToNextEntry()
                updateCurrentTrackInfo()
            } catch {
                self.logger.error("Failed to skip next: \(String(describing: error), privacy: .private)")
            }
        }
    }

    func skipToPrevious() {
        Task {
            do {
                try await ApplicationMusicPlayer.shared.skipToPreviousEntry()
                updateCurrentTrackInfo()
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
        updateCurrentTrackInfo()
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
        shouldIgnoreNextNonPlayingStatus = true
        ApplicationMusicPlayer.shared.stop()
        currentSongTitle = nil
        currentArtist = nil
        currentArtworkURL = nil
        isManuallyPaused = false
        hasAutoResumeIntent = false
        ownershipState = .narration
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
        }
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
                }
            case .albums:
                var request = MusicCatalogResourceRequest<Album>(matching: \.id, equalTo: itemID)
                request.limit = 1
                if let album = try await request.response().items.first {
                    player.queue = ApplicationMusicPlayer.Queue(for: [album])
                }
            case .artists:
                var request = MusicCatalogResourceRequest<Artist>(matching: \.id, equalTo: itemID)
                request.limit = 1
                if let artist = try await request.response().items.first {
                    let detailed = try await artist.with([.topSongs])
                    if let topSongs = detailed.topSongs, !topSongs.isEmpty {
                        player.queue = ApplicationMusicPlayer.Queue(for: topSongs)
                    }
                }
            case .playlists:
                var request = MusicCatalogResourceRequest<Playlist>(matching: \.id, equalTo: itemID)
                request.limit = 1
                if let playlist = try await request.response().items.first {
                    player.queue = ApplicationMusicPlayer.Queue(for: [playlist])
                }
            case .stations:
                var request = MusicCatalogResourceRequest<Station>(matching: \.id, equalTo: itemID)
                request.limit = 1
                if let station = try await request.response().items.first {
                    player.queue = ApplicationMusicPlayer.Queue(for: [station])
                }
            }
            hasAutoResumeIntent = true
            updateCurrentTrackInfo()
            if currentSongTitle == nil {
                restorePersistedNowPlayingLabel()
            }
        } catch {
            logger.error("Failed to restore Apple Music reading bed selection: \(String(describing: error), privacy: .private)")
            restorePersistedNowPlayingLabel()
        }
    }

    // MARK: - Ownership Transitions

    /// Activate Apple Music as the reading bed. Sentence playback keeps Now Playing ownership.
    func activateAsReadingBed() async {
        ownershipState = .transitioning
        // If a song is queued, wait for playback to start before the reader reasserts Now Playing.
        if currentSongTitle != nil {
            let player = ApplicationMusicPlayer.shared
            // Poll for playback confirmation (up to 2s)
            for _ in 0..<20 {
                if player.state.playbackStatus == .playing { break }
                try? await Task.sleep(nanoseconds: 100_000_000) // 100ms
            }
        }
        ownershipState = .appleMusicBed
    }

    /// Deactivate Apple Music as the reading bed. Returns after playback is confirmed stopped.
    func deactivateAsReadingBed() async {
        ownershipState = .transitioning
        let wasPlaying = isPlaying
        shouldIgnoreNextNonPlayingStatus = true
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
        hasAutoResumeIntent = false
        ownershipState = .narration
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
                        self?.isPlaying = status == .playing
                        if trackChanged || status == .playing {
                            self?.updateCurrentTrackInfo()
                        }
                        if statusChanged && status == .playing {
                            // Do not clear isManuallyPaused from passive MusicKit observation.
                            // App-initiated play/resume paths clear it explicitly; keeping
                            // observation read-only prevents sentence switches from reviving
                            // Apple Music after a user or system pause.
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

    private func handleObservedNonPlayingStatus() {
        if shouldIgnoreNextNonPlayingStatus {
            shouldIgnoreNextNonPlayingStatus = false
            return
        }
        guard isBackgroundMode else { return }
        guard currentSongTitle != nil else { return }
        isManuallyPaused = true
        hasAutoResumeIntent = false
    }

    private func updateCurrentTrackInfo() {
        guard let entry = ApplicationMusicPlayer.shared.queue.currentEntry else {
            currentSongTitle = nil
            currentArtist = nil
            currentArtworkURL = nil
            return
        }
        currentSongTitle = entry.title
        currentArtist = entry.subtitle
        if let artwork = entry.artwork {
            currentArtworkURL = artwork.url(width: 300, height: 300)
        } else {
            currentArtworkURL = nil
        }
    }

    #else
    // Stubs for platforms without MusicKit
    private init() {}
    func requestAuthorization() async -> Bool { false }
    func resume(userInitiated: Bool = true) {
        if userInitiated {
            isManuallyPaused = false
        }
    }
    func pause(userInitiated: Bool = true) {
        if userInitiated {
            isManuallyPaused = true
        }
    }
    func prepareForNarrationMix() {}
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
        ownershipState = .narration
        playbackTime = 0
        playbackDuration = 0
    }
    func activateAsReadingBed() async {
        ownershipState = .appleMusicBed
    }
    func deactivateAsReadingBed() async {
        ownershipState = .narration
    }
    #endif
}
