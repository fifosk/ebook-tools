import Foundation

extension VideoPlayerView {
    func configureNowPlaying() {
        nowPlaying.configureRemoteCommands(
            onPlay: { coordinator.play() },
            onPause: { coordinator.pause() },
            onNext: nil,
            onPrevious: nil,
            onSeek: { coordinator.seek(to: $0) },
            onToggle: { coordinator.togglePlayback() },
            onSkipForward: { coordinator.skip(by: 15) },
            onSkipBackward: { coordinator.skip(by: -15) },
            skipIntervalSeconds: 15
        )
    }

    func updateNowPlayingMetadata() {
        nowPlaying.updateMetadata(
            title: metadata.title,
            artist: metadata.artist,
            album: metadata.album,
            artworkURL: metadata.artworkURL ?? metadata.secondaryArtworkURL,
            mediaType: .video
        )
    }

    func updateNowPlayingPlayback() {
        nowPlaying.updatePlaybackState(
            isPlaying: coordinator.isPlaying,
            position: coordinator.currentTime,
            duration: coordinator.duration
        )
    }
}
