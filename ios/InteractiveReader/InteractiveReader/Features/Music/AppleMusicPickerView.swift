import SwiftUI

/// Sheet UI for searching and selecting Apple Music content as a reading bed.
struct AppleMusicPickerView: View {
    @ObservedObject var searchService: MusicSearchService
    @ObservedObject var musicCoordinator: MusicKitCoordinator
    let onSelect: () -> Void
    let onDismiss: () -> Void

    var body: some View {
        #if os(iOS)
        NavigationStack {
            pickerContent
                .navigationTitle("Apple Music")
                .navigationBarTitleDisplayMode(.inline)
                .toolbar {
                    ToolbarItem(placement: .cancellationAction) {
                        Button("Done") { onDismiss() }
                    }
                }
        }
        #elseif os(tvOS)
        NavigationStack {
            pickerContent
                .navigationTitle("Apple Music")
        }
        #else
        VStack {
            Text("Apple Music is not available on this platform.")
                .foregroundStyle(.secondary)
            Button("Done") { onDismiss() }
        }
        #endif
    }

    @ViewBuilder
    private var pickerContent: some View {
        VStack(spacing: 0) {
            if !musicCoordinator.isAuthorized {
                authorizationPrompt
            } else {
                searchContent
            }
        }
    }

    private var authorizationPrompt: some View {
        VStack(spacing: 16) {
            Spacer()
            Image(systemName: "music.note")
                .font(.system(size: 48))
                .foregroundStyle(.secondary)
            Text("Apple Music Access Required")
                .font(.headline)
            Text("Allow access to search and play music from your Apple Music library.")
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 32)
            Button("Allow Access") {
                Task {
                    _ = await musicCoordinator.requestAuthorization()
                }
            }
            .buttonStyle(.borderedProminent)
            Spacer()
        }
    }

    @ViewBuilder
    private var searchContent: some View {
        #if canImport(MusicKit)
        VStack(spacing: 0) {
            // Search field
            HStack {
                Image(systemName: "magnifyingglass")
                    .foregroundStyle(.secondary)
                TextField("Search music...", text: $searchService.searchText)
                    .textFieldStyle(.plain)
                    #if os(iOS)
                    .autocorrectionDisabled()
                    #endif
                    .onChange(of: searchService.searchText) { _, _ in
                        searchService.searchDebounced()
                    }
                if !searchService.searchText.isEmpty {
                    Button {
                        searchService.searchText = ""
                        searchService.clearAllResults()
                    } label: {
                        Image(systemName: "xmark.circle.fill")
                            .foregroundStyle(.secondary)
                    }
                    #if os(tvOS)
                    .buttonStyle(.plain)
                    #endif
                }
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 10)
            #if os(iOS)
            .background(Color(.systemGray6))
            #else
            .background(Color.gray.opacity(0.2))
            #endif
            .clipShape(RoundedRectangle(cornerRadius: 10))
            .padding(.horizontal, 16)
            .padding(.top, 8)

            // Tab bar
            tabBar

            // Now playing indicator
            if let title = musicCoordinator.currentSongTitle {
                HStack(spacing: 8) {
                    Image(systemName: "music.note")
                        .foregroundStyle(Color.accentColor)
                    Text("Now: \(title)")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .lineLimit(1)
                    Spacer()
                    if musicCoordinator.isPlaying {
                        Button("Stop") {
                            musicCoordinator.stop()
                        }
                        .font(.caption)
                        .buttonStyle(.bordered)
                        .controlSize(.mini)
                    }
                }
                .padding(.horizontal, 16)
                .padding(.top, 8)
            }

            // Results
            if searchService.isSearching {
                Spacer()
                ProgressView("Searching...")
                Spacer()
            } else if searchService.activeResults.isEmpty && !searchService.searchText.isEmpty {
                Spacer()
                Text("No \(searchService.activeTab.label.lowercased()) found")
                    .foregroundStyle(.secondary)
                Spacer()
            } else if searchService.isLoadingSuggestions && searchService.searchText.isEmpty {
                Spacer()
                ProgressView("Loading suggestions...")
                Spacer()
            } else if searchService.activeResults.isEmpty && searchService.searchText.isEmpty {
                Spacer()
                Text("Search for \(searchService.activeTab.label.lowercased())...")
                    .foregroundStyle(.secondary)
                Spacer()
            } else {
                let isSuggestion = searchService.searchText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
                List {
                    if isSuggestion {
                        Section {
                            ForEach(searchService.activeResults) { result in
                                Button {
                                    selectResult(result)
                                } label: {
                                    resultRow(result)
                                }
                                #if os(iOS)
                                .listRowBackground(Color.clear)
                                #endif
                            }
                        } header: {
                            Text(suggestionHeader)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                                .textCase(nil)
                        }
                    } else {
                        ForEach(searchService.activeResults) { result in
                            Button {
                                selectResult(result)
                            } label: {
                                resultRow(result)
                            }
                            #if os(iOS)
                            .listRowBackground(Color.clear)
                            #endif
                        }
                    }
                }
                .listStyle(.plain)
            }
        }
        .onAppear {
            searchService.loadSuggestions()
        }
        #else
        Text("Apple Music search is not available on this platform.")
            .foregroundStyle(.secondary)
        #endif
    }

    // MARK: - Tab Bar

    private var tabBar: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 6) {
                ForEach(MusicItemKind.allCases) { kind in
                    let isSelected = searchService.activeTab == kind
                    Button {
                        searchService.activeTab = kind
                    } label: {
                        HStack(spacing: 4) {
                            Image(systemName: kind.systemImage)
                                .font(.caption2)
                            Text(kind.label)
                                .font(.caption)
                        }
                        .padding(.horizontal, 10)
                        .padding(.vertical, 6)
                        .background(
                            Capsule()
                                .fill(isSelected ? Color.accentColor : Color.gray.opacity(0.2))
                        )
                        .foregroundStyle(isSelected ? Color.white : Color.primary)
                    }
                    #if os(tvOS)
                    .buttonStyle(.plain)
                    #else
                    .buttonStyle(.plain)
                    #endif
                }
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 8)
        }
    }

    // MARK: - Suggestion Header

    private var suggestionHeader: String {
        switch searchService.activeTab {
        case .songs: return "Recently Played"
        case .albums: return "For You"
        case .artists: return "Recent Artists"
        case .playlists: return "For You"
        case .stations: return "Suggested Stations"
        }
    }

    // MARK: - Result Rows

    @ViewBuilder
    private func resultRow(_ result: MusicSearchService.MusicSearchResult) -> some View {
        HStack(spacing: 12) {
            if let url = result.artworkURL {
                AsyncImage(url: url) { phase in
                    if let image = phase.image {
                        image.resizable().scaledToFill()
                    } else {
                        Color.gray.opacity(0.3)
                    }
                }
                .frame(width: 44, height: 44)
                .clipShape(RoundedRectangle(cornerRadius: result.kind == .artists ? 22 : 6))
            }
            VStack(alignment: .leading, spacing: 2) {
                Text(result.title)
                    .font(.body)
                    .lineLimit(1)
                if !result.subtitle.isEmpty {
                    Text(result.subtitle)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .lineLimit(1)
                }
            }
            Spacer()
            Image(systemName: result.kind.systemImage)
                .font(.caption)
                .foregroundStyle(.tertiary)
        }
    }

    // MARK: - Selection

    #if canImport(MusicKit)
    private func selectResult(_ result: MusicSearchService.MusicSearchResult) {
        Task {
            switch result.kind {
            case .songs:
                guard let song = result.song else { return }
                await musicCoordinator.playSong(song)
            case .albums:
                guard let album = result.album else { return }
                await musicCoordinator.playAlbum(album)
            case .artists:
                guard let artist = result.artist else { return }
                await musicCoordinator.playArtistTopSongs(artist)
            case .playlists:
                guard let playlist = result.playlist else { return }
                await musicCoordinator.playPlaylist(playlist)
            case .stations:
                guard let station = result.station else { return }
                await musicCoordinator.playStation(station)
            }
            onSelect()
        }
    }
    #endif
}
