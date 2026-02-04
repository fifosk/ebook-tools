import Foundation
import Combine
#if canImport(MusicKit)
import MusicKit
#endif

/// Categories of Apple Music content that can be searched.
enum MusicItemKind: String, CaseIterable, Identifiable {
    case songs, albums, artists, playlists, stations
    var id: String { rawValue }
    var label: String {
        switch self {
        case .songs: return "Songs"
        case .albums: return "Albums"
        case .artists: return "Artists"
        case .playlists: return "Playlists"
        case .stations: return "Stations"
        }
    }
    var systemImage: String {
        switch self {
        case .songs: return "music.note"
        case .albums: return "square.stack"
        case .artists: return "person"
        case .playlists: return "music.note.list"
        case .stations: return "dot.radiowaves.left.and.right"
        }
    }
}

/// Provides search functionality against the Apple Music catalog.
@MainActor
final class MusicSearchService: ObservableObject {
    @Published var searchText = ""
    @Published var activeTab: MusicItemKind = .songs
    @Published var songResults: [MusicSearchResult] = []
    @Published var albumResults: [MusicSearchResult] = []
    @Published var artistResults: [MusicSearchResult] = []
    @Published var playlistResults: [MusicSearchResult] = []
    @Published var stationResults: [MusicSearchResult] = []
    @Published private(set) var isSearching = false

    // Suggestion results shown when search text is empty
    @Published var songSuggestions: [MusicSearchResult] = []
    @Published var albumSuggestions: [MusicSearchResult] = []
    @Published var artistSuggestions: [MusicSearchResult] = []
    @Published var playlistSuggestions: [MusicSearchResult] = []
    @Published var stationSuggestions: [MusicSearchResult] = []
    @Published private(set) var isLoadingSuggestions = false
    @Published private(set) var suggestionsLoaded = false

    private var searchTask: Task<Void, Never>?

    /// Returns search results when searching, or suggestions when idle.
    var activeResults: [MusicSearchResult] {
        let hasQuery = !searchText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
        if hasQuery {
            switch activeTab {
            case .songs: return songResults
            case .albums: return albumResults
            case .artists: return artistResults
            case .playlists: return playlistResults
            case .stations: return stationResults
            }
        } else {
            switch activeTab {
            case .songs: return songSuggestions
            case .albums: return albumSuggestions
            case .artists: return artistSuggestions
            case .playlists: return playlistSuggestions
            case .stations: return stationSuggestions
            }
        }
    }

    /// Whether the active tab has suggestions available.
    var hasSuggestions: Bool {
        !songSuggestions.isEmpty || !albumSuggestions.isEmpty ||
        !artistSuggestions.isEmpty || !playlistSuggestions.isEmpty ||
        !stationSuggestions.isEmpty
    }

    struct MusicSearchResult: Identifiable {
        let id: String
        let title: String
        let subtitle: String
        let artworkURL: URL?
        let kind: MusicItemKind
        #if canImport(MusicKit)
        let song: Song?
        let album: Album?
        let artist: Artist?
        let playlist: Playlist?
        let station: Station?
        #endif
    }

    #if canImport(MusicKit)
    // MARK: - Factory methods

    static func from(_ song: Song) -> MusicSearchResult {
        MusicSearchResult(
            id: song.id.rawValue,
            title: song.title,
            subtitle: song.artistName,
            artworkURL: song.artwork?.url(width: 80, height: 80),
            kind: .songs,
            song: song, album: nil, artist: nil, playlist: nil, station: nil
        )
    }

    static func from(_ album: Album) -> MusicSearchResult {
        MusicSearchResult(
            id: album.id.rawValue,
            title: album.title,
            subtitle: album.artistName,
            artworkURL: album.artwork?.url(width: 80, height: 80),
            kind: .albums,
            song: nil, album: album, artist: nil, playlist: nil, station: nil
        )
    }

    static func from(_ artist: Artist) -> MusicSearchResult {
        MusicSearchResult(
            id: artist.id.rawValue,
            title: artist.name,
            subtitle: "",
            artworkURL: artist.artwork?.url(width: 80, height: 80),
            kind: .artists,
            song: nil, album: nil, artist: artist, playlist: nil, station: nil
        )
    }

    static func from(_ playlist: Playlist) -> MusicSearchResult {
        MusicSearchResult(
            id: playlist.id.rawValue,
            title: playlist.name,
            subtitle: playlist.curatorName ?? "",
            artworkURL: playlist.artwork?.url(width: 80, height: 80),
            kind: .playlists,
            song: nil, album: nil, artist: nil, playlist: playlist, station: nil
        )
    }

    static func from(_ station: Station) -> MusicSearchResult {
        MusicSearchResult(
            id: station.id.rawValue,
            title: station.name,
            subtitle: "",
            artworkURL: station.artwork?.url(width: 80, height: 80),
            kind: .stations,
            song: nil, album: nil, artist: nil, playlist: nil, station: station
        )
    }

    // MARK: - Search

    /// Search the Apple Music catalog with the current `searchText`.
    func search() async {
        let query = searchText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !query.isEmpty else {
            clearAllResults()
            return
        }

        isSearching = true
        defer { isSearching = false }

        do {
            var request = MusicCatalogSearchRequest(
                term: query,
                types: [Song.self, Album.self, Artist.self, Playlist.self, Station.self]
            )
            request.limit = 25
            let response = try await request.response()

            songResults = response.songs.map { Self.from($0) }
            albumResults = response.albums.map { Self.from($0) }
            artistResults = response.artists.map { Self.from($0) }
            playlistResults = response.playlists.map { Self.from($0) }
            stationResults = response.stations.map { Self.from($0) }
        } catch {
            print("[MusicSearch] Search failed: \(error)")
            clearAllResults()
        }
    }

    /// Debounced search triggered by text changes.
    func searchDebounced() {
        searchTask?.cancel()
        searchTask = Task {
            try? await Task.sleep(nanoseconds: 400_000_000) // 400ms
            guard !Task.isCancelled else { return }
            await search()
        }
    }

    func clearAllResults() {
        songResults = []
        albumResults = []
        artistResults = []
        playlistResults = []
        stationResults = []
    }

    // MARK: - Suggestions (preloaded from user history and recommendations)

    /// Load personalized suggestions from recently played items and recommendations.
    /// Call once when the picker appears to populate tabs before the user searches.
    func loadSuggestions() {
        guard !suggestionsLoaded, !isLoadingSuggestions else { return }
        isLoadingSuggestions = true
        Task {
            defer {
                isLoadingSuggestions = false
                suggestionsLoaded = true
            }
            // Load recently played and recommendations in parallel
            async let recentSongs = loadRecentlyPlayedSongs()
            async let recentContainers = loadRecentlyPlayedContainers()
            async let recommendations = loadPersonalRecommendations()

            let (songs, containers, recs) = await (recentSongs, recentContainers, recommendations)

            songSuggestions = songs
            // Merge recently played containers with recommendation items
            albumSuggestions = dedup(containers.albums + recs.albums)
            playlistSuggestions = dedup(containers.playlists + recs.playlists)
            stationSuggestions = dedup(containers.stations + recs.stations)
            // Artists: extract from recently played songs
            artistSuggestions = dedup(extractArtists(from: songs))
        }
    }

    private func loadRecentlyPlayedSongs() async -> [MusicSearchResult] {
        do {
            let request = MusicRecentlyPlayedRequest<Song>()
            let response = try await request.response()
            return response.items.prefix(25).map { Self.from($0) }
        } catch {
            print("[MusicSearch] Recently played songs failed: \(error)")
            return []
        }
    }

    private struct ContainerResults {
        var albums: [MusicSearchResult] = []
        var playlists: [MusicSearchResult] = []
        var stations: [MusicSearchResult] = []
    }

    private func loadRecentlyPlayedContainers() async -> ContainerResults {
        // Album and Playlist don't conform to MusicRecentlyPlayedRequestable,
        // so use MusicLibraryRequest sorted by lastPlayedDate instead.
        // Station supports MusicRecentlyPlayedRequest directly.
        async let recentAlbums = loadLibraryAlbums()
        async let recentPlaylists = loadLibraryPlaylists()
        async let recentStations = loadRecentStations()

        let (albums, playlists, stations) = await (recentAlbums, recentPlaylists, recentStations)
        return ContainerResults(albums: albums, playlists: playlists, stations: stations)
    }

    private func loadLibraryAlbums() async -> [MusicSearchResult] {
        do {
            var request = MusicLibraryRequest<Album>()
            request.sort(by: \.lastPlayedDate, ascending: false)
            request.limit = 15
            let response = try await request.response()
            return response.items.map { Self.from($0) }
        } catch {
            print("[MusicSearch] Library albums failed: \(error)")
            return []
        }
    }

    private func loadLibraryPlaylists() async -> [MusicSearchResult] {
        do {
            var request = MusicLibraryRequest<Playlist>()
            request.sort(by: \.lastPlayedDate, ascending: false)
            request.limit = 15
            let response = try await request.response()
            return response.items.map { Self.from($0) }
        } catch {
            print("[MusicSearch] Library playlists failed: \(error)")
            return []
        }
    }

    private func loadRecentStations() async -> [MusicSearchResult] {
        do {
            let request = MusicRecentlyPlayedRequest<Station>()
            let response = try await request.response()
            return response.items.prefix(15).map { Self.from($0) }
        } catch {
            print("[MusicSearch] Recently played stations failed: \(error)")
            return []
        }
    }

    private func loadPersonalRecommendations() async -> ContainerResults {
        do {
            var request = MusicPersonalRecommendationsRequest()
            request.limit = 10
            let response = try await request.response()
            var result = ContainerResults()
            for recommendation in response.recommendations {
                for album in recommendation.albums {
                    result.albums.append(Self.from(album))
                }
                for playlist in recommendation.playlists {
                    result.playlists.append(Self.from(playlist))
                }
                for station in recommendation.stations {
                    result.stations.append(Self.from(station))
                }
            }
            return result
        } catch {
            print("[MusicSearch] Personal recommendations failed: \(error)")
            return ContainerResults()
        }
    }

    /// Extract unique artists from song results.
    private func extractArtists(from songs: [MusicSearchResult]) -> [MusicSearchResult] {
        var seen = Set<String>()
        var artists: [MusicSearchResult] = []
        for song in songs {
            let artistName = song.subtitle
            guard !artistName.isEmpty, !seen.contains(artistName) else { continue }
            seen.insert(artistName)
            // Create an artist-like entry from song info (no Artist object, but useful for display)
            artists.append(MusicSearchResult(
                id: "artist-\(artistName)",
                title: artistName,
                subtitle: "",
                artworkURL: song.artworkURL,
                kind: .artists,
                song: nil, album: nil, artist: nil, playlist: nil, station: nil
            ))
        }
        return artists
    }

    /// Remove duplicate results by id, keeping the first occurrence.
    private func dedup(_ items: [MusicSearchResult]) -> [MusicSearchResult] {
        var seen = Set<String>()
        return items.filter { seen.insert($0.id).inserted }
    }

    #else
    // Stubs for platforms without MusicKit
    func search() async { clearAllResults() }
    func searchDebounced() {}
    func loadSuggestions() { suggestionsLoaded = true }
    func clearAllResults() {
        songResults = []
        albumResults = []
        artistResults = []
        playlistResults = []
        stationResults = []
    }
    #endif
}
