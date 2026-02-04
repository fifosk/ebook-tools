import Foundation
import Combine
#if canImport(MusicKit)
import MusicKit
#endif

/// Keys for persisting music preferences.
enum MusicPreferences {
    static let useAppleMusicKey = "player.useAppleMusicForBed"
    static let musicVolumeKey = "player.musicVolume"
    static let readingBedEnabledKey = "player.readingBedEnabled"
    static let shuffleModeKey = "player.shuffleMode"
    static let repeatModeKey = "player.repeatMode"
    static let lastReadingBedIDKey = "player.lastReadingBedID"
    static let defaultMusicVolume: Double = 0.15
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
    case narration      // Lock screen shows book info + sentence controls
    case appleMusic     // Lock screen shows Apple Music track + controls
    case transitioning  // During handoff — neither side should assert
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
    @Published var shuffleMode: MusicKitShuffleMode = .off
    @Published var repeatMode: MusicKitRepeatMode = .off

    /// Whether Apple Music is actively serving as the reading bed.
    var isBackgroundMode: Bool { ownershipState == .appleMusic }

    #if canImport(MusicKit)
    private var playbackStateTask: Task<Void, Never>?

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
            updateCurrentTrackInfo()
        } catch {
            print("[MusicKit] Failed to play song: \(error)")
        }
    }

    // MARK: - Playback: Station

    func playStation(_ station: Station) async {
        let player = ApplicationMusicPlayer.shared
        player.queue = ApplicationMusicPlayer.Queue(for: [station])
        do {
            try await player.play()
            updateCurrentTrackInfo()
        } catch {
            print("[MusicKit] Failed to play station: \(error)")
        }
    }

    // MARK: - Playback: Album

    func playAlbum(_ album: Album) async {
        let player = ApplicationMusicPlayer.shared
        player.queue = ApplicationMusicPlayer.Queue(for: [album])
        do {
            try await player.play()
            updateCurrentTrackInfo()
        } catch {
            print("[MusicKit] Failed to play album: \(error)")
        }
    }

    // MARK: - Playback: Playlist

    func playPlaylist(_ playlist: Playlist) async {
        let player = ApplicationMusicPlayer.shared
        player.queue = ApplicationMusicPlayer.Queue(for: [playlist])
        do {
            try await player.play()
            updateCurrentTrackInfo()
        } catch {
            print("[MusicKit] Failed to play playlist: \(error)")
        }
    }

    // MARK: - Playback: Artist (top songs)

    func playArtistTopSongs(_ artist: Artist) async {
        do {
            let detailed = try await artist.with([.topSongs])
            guard let topSongs = detailed.topSongs, !topSongs.isEmpty else {
                print("[MusicKit] No top songs found for artist")
                return
            }
            let player = ApplicationMusicPlayer.shared
            player.queue = ApplicationMusicPlayer.Queue(for: topSongs)
            try await player.play()
            updateCurrentTrackInfo()
        } catch {
            print("[MusicKit] Failed to play artist top songs: \(error)")
        }
    }

    // MARK: - Transport Controls

    func resume() {
        let player = ApplicationMusicPlayer.shared
        Task {
            do {
                try await player.play()
            } catch {
                print("[MusicKit] Failed to resume: \(error)")
            }
        }
    }

    func pause() {
        ApplicationMusicPlayer.shared.pause()
    }

    func skipToNext() {
        Task {
            do {
                try await ApplicationMusicPlayer.shared.skipToNextEntry()
                updateCurrentTrackInfo()
            } catch {
                print("[MusicKit] Failed to skip next: \(error)")
            }
        }
    }

    func skipToPrevious() {
        Task {
            do {
                try await ApplicationMusicPlayer.shared.skipToPreviousEntry()
                updateCurrentTrackInfo()
            } catch {
                print("[MusicKit] Failed to skip previous: \(error)")
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
        let current = player.state.repeatMode
        if current == nil || current == .none {
            player.state.repeatMode = .all
            repeatMode = .all
        } else if current == .all {
            player.state.repeatMode = .one
            repeatMode = .one
        } else {
            player.state.repeatMode = .none
            repeatMode = .off
        }
        persistModes()
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
        case .off: player.state.repeatMode = .none
        }
    }

    func stop() {
        ApplicationMusicPlayer.shared.stop()
        currentSongTitle = nil
        currentArtist = nil
        currentArtworkURL = nil
        ownershipState = .narration
    }

    // MARK: - Ownership Transitions

    /// Activate Apple Music as the reading bed. Sets ownership after playback is confirmed.
    func activateAsReadingBed() async {
        ownershipState = .transitioning
        // If a song is queued, wait for playback to start so Apple Music asserts Now Playing
        if currentSongTitle != nil {
            let player = ApplicationMusicPlayer.shared
            // Poll for playback confirmation (up to 2s)
            for _ in 0..<20 {
                if player.state.playbackStatus == .playing { break }
                try? await Task.sleep(nanoseconds: 100_000_000) // 100ms
            }
        }
        ownershipState = .appleMusic
    }

    /// Deactivate Apple Music as the reading bed. Returns after playback is confirmed stopped.
    func deactivateAsReadingBed() async {
        ownershipState = .transitioning
        let wasPlaying = isPlaying
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
        ownershipState = .narration
    }

    // MARK: - Private

    private func observePlaybackState() {
        playbackStateTask = Task { [weak self] in
            let player = ApplicationMusicPlayer.shared
            var lastStatus: MusicPlayer.PlaybackStatus?
            while !Task.isCancelled {
                let status = player.state.playbackStatus
                if status != lastStatus {
                    lastStatus = status
                    await MainActor.run {
                        self?.isPlaying = status == .playing
                        if status == .playing {
                            self?.updateCurrentTrackInfo()
                            self?.syncShuffleRepeatFromPlayer()
                        }
                    }
                }
                try? await Task.sleep(nanoseconds: 250_000_000) // 250ms
            }
        }
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
    func resume() {}
    func pause() {}
    func skipToNext() {}
    func skipToPrevious() {}
    func toggleShuffle() {}
    func cycleRepeatMode() {}
    func stop() {
        currentSongTitle = nil
        currentArtist = nil
        currentArtworkURL = nil
        ownershipState = .narration
    }
    func activateAsReadingBed() async {
        ownershipState = .appleMusic
    }
    func deactivateAsReadingBed() async {
        ownershipState = .narration
    }
    #endif
}
