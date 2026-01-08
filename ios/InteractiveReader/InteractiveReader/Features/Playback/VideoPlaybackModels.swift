import Foundation

struct VideoPlaybackMetadata {
    let title: String
    let subtitle: String?
    let artist: String?
    let album: String?
    let artworkURL: URL?
    let secondaryArtworkURL: URL?
    let languageFlags: [LanguageFlagEntry]
    let translationModel: String?
    let summary: String?
    let channelVariant: PlayerChannelVariant
    let channelLabel: String
}

struct VideoSegmentOption: Identifiable, Hashable {
    let id: String
    let label: String
}

struct PendingVideoBookmarkSeek: Equatable {
    let time: Double
    let shouldPlay: Bool
    let segmentId: String?
}
