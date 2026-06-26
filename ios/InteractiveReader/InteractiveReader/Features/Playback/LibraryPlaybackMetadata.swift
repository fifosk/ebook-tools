import Foundation
import SwiftUI

extension LibraryPlaybackView {
    var itemTypeLabel: String {
        switch item.itemType {
        case "video":
            return "Video"
        case "narrated_subtitle":
            return "Subtitles"
        default:
            return "Book"
        }
    }

    var bookmarkItemType: String {
        item.itemType.nonEmptyValue ?? itemTypeLabel.lowercased()
    }

    var showsScrubber: Bool {
        item.itemType == "video"
    }

    var linguistInputLanguage: String {
        metadataString(for: [
            "input_language",
            "original_language",
            "source_language",
            "translation_source_language",
            "book_language"
        ]) ?? item.language
    }

    var linguistLookupLanguage: String {
        metadataString(for: [
            "target_language",
            "translation_language",
            "target_languages"
        ]) ?? metadataString(for: ["language"], maxDepth: 0) ?? item.language
    }

    var summaryText: String? {
        if let summary = resolvedYoutubeSummary {
            return summary
        }
        if let summary = resolvedTvSummary {
            return summary
        }
        if let summary = bookSummary {
            return summary
        }
        return nil
    }

    var interactiveHeaderInfo: InteractivePlayerHeaderInfo {
        InteractivePlayerHeaderInfo(
            title: item.bookTitle.isEmpty ? "Untitled" : item.bookTitle,
            author: item.author.isEmpty ? "Unknown author" : item.author,
            itemTypeLabel: itemTypeLabel,
            coverURL: coverURL,
            secondaryCoverURL: secondaryCoverURL,
            languageFlags: languageFlags,
            translationModel: translationModelLabel
        )
    }

    func metadataString(for keys: [String], maxDepth: Int = 4) -> String? {
        guard let metadata = item.metadata else { return nil }
        return PlaybackMetadataHelpers.metadataString(in: metadata, keys: keys, maxDepth: maxDepth)
    }

    func normalizedSummary(_ value: String?) -> String? {
        PlaybackMetadataHelpers.normalizedSummary(value)
    }

    var resolvedTvMetadata: [String: JSONValue]? {
        guard let metadata = item.metadata else { return nil }
        return PlaybackMetadataHelpers.extractTvMediaMetadata(from: metadata)
    }

    var isTvSeriesMetadata: Bool {
        PlaybackMetadataHelpers.isTvSeriesMetadata(resolvedTvMetadata)
    }

    var resolvedYoutubeMetadata: [String: JSONValue]? {
        if let tvMetadata = resolvedTvMetadata,
           let youtube = tvMetadata["youtube"]?.objectValue {
            return youtube
        }
        guard let metadata = item.metadata else { return nil }
        return metadata["youtube"]?.objectValue
    }

    var resolvedYoutubeSummary: String? {
        PlaybackMetadataHelpers.youtubeSummary(from: resolvedYoutubeMetadata)
    }

    var resolvedTvSummary: String? {
        PlaybackMetadataHelpers.tvSummary(from: resolvedTvMetadata)
    }

    var imageReelURLs: [URL] {
        guard let chunk = viewModel.selectedChunk else { return [] }
        let hasExplicitImage = chunk.sentences.contains { sentence in
            if let rawPath = sentence.imagePath, rawPath.nonEmptyValue != nil {
                return true
            }
            return false
        }
        guard hasExplicitImage else { return [] }
        var urls: [URL] = []
        var seen: Set<String> = []
        for sentence in chunk.sentences {
            guard let path = resolveSentenceImagePath(sentence: sentence, chunk: chunk) else { continue }
            guard !seen.contains(path) else { continue }
            seen.insert(path)
            if let url = viewModel.resolvePath(path) {
                urls.append(url)
            }
            if urls.count >= 7 {
                break
            }
        }
        return urls
    }

    func resolveSentenceImagePath(sentence: InteractiveChunk.Sentence, chunk: InteractiveChunk) -> String? {
        if let rawPath = sentence.imagePath, let path = rawPath.nonEmptyValue {
            return path
        }
        guard let rangeFragment = chunk.rangeFragment?.nonEmptyValue else { return nil }
        let sentenceNumber = sentence.displayIndex ?? sentence.id
        guard sentenceNumber > 0 else { return nil }
        let padded = String(format: "%05d", sentenceNumber)
        return "media/images/\(rangeFragment)/sentence_\(padded).png"
    }

    var coverURL: URL? {
        guard let apiBaseURL = appState.apiBaseURL else { return nil }
        let resolver = LibraryCoverResolver(apiBaseURL: apiBaseURL, accessToken: appState.authToken)
        return resolver.resolveCoverURL(for: item)
    }

    var secondaryCoverURL: URL? {
        guard let apiBaseURL = appState.apiBaseURL else { return nil }
        let resolver = LibraryCoverResolver(apiBaseURL: apiBaseURL, accessToken: appState.authToken)
        return resolver.resolveSecondaryCoverURL(for: item)
    }

    var languageFlags: [LanguageFlagEntry] {
        LanguageFlagResolver.resolveFlags(
            originalLanguage: linguistInputLanguage,
            translationLanguage: linguistLookupLanguage
        )
    }

    var translationModelLabel: String? {
        metadataString(for: ["llm_model", "ollama_model"])?.nonEmptyValue
    }

    var bookSummary: String? {
        let summary = metadataString(for: ["book_summary"], maxDepth: 4)
            ?? metadataString(for: ["summary"], maxDepth: 4)
        return normalizedSummary(summary)
    }

    var hasInteractiveChunks: Bool {
        guard let chunks = viewModel.jobContext?.chunks else { return false }
        return chunks.contains { !$0.sentences.isEmpty || $0.startSentence != nil || $0.endSentence != nil }
    }

    var hasVideo: Bool {
        !(viewModel.mediaResponse?.media["video"] ?? []).isEmpty
    }

    var isVideoPreferred: Bool {
        if item.itemType == "video" {
            return true
        }
        return hasVideo && !hasInteractiveChunks
    }

    var videoURL: URL? {
        guard let files = viewModel.mediaResponse?.media["video"] else { return nil }
        for file in files {
            if let url = viewModel.resolveMediaURL(for: file) {
                return url
            }
        }
        return nil
    }

    var subtitleTracks: [VideoSubtitleTrack] {
        guard let files = viewModel.mediaResponse?.media["text"] else { return [] }
        var tracks: [VideoSubtitleTrack] = []
        var seen: Set<String> = []
        for file in files {
            guard let url = viewModel.resolveMediaURL(for: file) else { continue }
            let sourcePath = file.relativePath ?? file.path ?? file.name
            let format = SubtitleParser.format(for: sourcePath)
            let id = sourcePath.nonEmptyValue ?? url.absoluteString
            guard !seen.contains(id) else { continue }
            seen.insert(id)
            let label = subtitleTrackLabel(for: file, fallback: "Subtitle \(tracks.count + 1)")
            tracks.append(VideoSubtitleTrack(id: id, url: url, format: format, label: label))
        }
        return tracks
    }

    func subtitleTrackLabel(for file: PipelineMediaFile, fallback: String) -> String {
        let raw = file.name.nonEmptyValue ?? file.relativePath?.nonEmptyValue ?? file.path?.nonEmptyValue
        let filename = raw?.split(whereSeparator: { $0 == "/" || $0 == "\\" }).last.map(String.init) ?? fallback
        if let dotIndex = filename.lastIndex(of: ".") {
            let stem = filename[..<dotIndex]
            if !stem.isEmpty {
                return String(stem)
            }
        }
        return filename
    }

    var videoMetadata: VideoPlaybackMetadata {
        let title = item.bookTitle.isEmpty ? "Video" : item.bookTitle
        let subtitle = item.author.isEmpty ? nil : item.author
        let isYoutubeVideo = resolvedYoutubeMetadata != nil
        let isTvSeries = isTvSeriesMetadata
        let channelVariant: PlayerChannelVariant = {
            if isTvSeries {
                return .tv
            }
            if isYoutubeVideo {
                return .youtube
            }
            switch item.itemType {
            case "narrated_subtitle":
                return .subtitles
            default:
                return .video
            }
        }()
        let channelLabel = isTvSeries
            ? "TV"
            : isYoutubeVideo
                ? "YouTube"
                : (item.itemType == "narrated_subtitle" ? "Subtitles" : "Video")
        return VideoPlaybackMetadata(
            title: title,
            subtitle: subtitle,
            artist: subtitle,
            album: item.bookTitle.isEmpty ? nil : item.bookTitle,
            artworkURL: coverURL,
            secondaryArtworkURL: secondaryCoverURL,
            languageFlags: languageFlags,
            translationModel: translationModelLabel,
            summary: summaryText,
            channelVariant: channelVariant,
            channelLabel: channelLabel
        )
    }
}
