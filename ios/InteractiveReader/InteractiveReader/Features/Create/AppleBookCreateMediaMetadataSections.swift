import SwiftUI

struct AppleBookCreateYoutubeMetadataSection: View {
    let isLoadingTvMetadata: Bool
    let isLoadingYoutubeMetadata: Bool
    let isClearingTvMetadataCache: Bool
    let isClearingYoutubeMetadataCache: Bool
    let canClearTvMetadataCache: Bool
    let canClearYoutubeMetadataCache: Bool
    @Binding var tvPosterURL: String
    @Binding var tvEpisodeStillURL: String
    @Binding var youtubeThumbnailURL: String
    let message: String?
    let errorMessage: String?
    @Binding var title: String
    @Binding var channel: String
    @Binding var showName: String
    @Binding var tmdbId: String
    @Binding var imdbId: String
    @Binding var episodeName: String
    @Binding var advancedMetadataJSON: String
    let advancedMetadataErrorMessage: String?
    let onLoadTvMetadata: () -> Void
    let onLoadYoutubeMetadata: () -> Void
    let onClearTvMetadataCache: () -> Void
    let onClearYoutubeMetadataCache: () -> Void
    let onApplyAdvancedMetadataJSON: () -> Void
    let onSyncAdvancedMetadataJSON: () -> Void

    var body: some View {
        Section("Metadata") {
            AppleBookCreateYoutubeMetadataControls(
                isLoadingTvMetadata: isLoadingTvMetadata,
                isLoadingYoutubeMetadata: isLoadingYoutubeMetadata,
                isClearingTvMetadataCache: isClearingTvMetadataCache,
                isClearingYoutubeMetadataCache: isClearingYoutubeMetadataCache,
                canClearTvMetadataCache: canClearTvMetadataCache,
                canClearYoutubeMetadataCache: canClearYoutubeMetadataCache,
                tvPosterURL: $tvPosterURL,
                tvEpisodeStillURL: $tvEpisodeStillURL,
                youtubeThumbnailURL: $youtubeThumbnailURL,
                message: message,
                errorMessage: errorMessage,
                title: $title,
                channel: $channel,
                showName: $showName,
                tmdbId: $tmdbId,
                imdbId: $imdbId,
                episodeName: $episodeName,
                advancedMetadataJSON: $advancedMetadataJSON,
                advancedMetadataErrorMessage: advancedMetadataErrorMessage,
                onLoadTvMetadata: onLoadTvMetadata,
                onLoadYoutubeMetadata: onLoadYoutubeMetadata,
                onClearTvMetadataCache: onClearTvMetadataCache,
                onClearYoutubeMetadataCache: onClearYoutubeMetadataCache,
                onApplyAdvancedMetadataJSON: onApplyAdvancedMetadataJSON,
                onSyncAdvancedMetadataJSON: onSyncAdvancedMetadataJSON
            )
        }
    }
}

struct AppleBookCreateSubtitleMetadataSection: View {
    let sourceName: String
    @Binding var lookupSourceName: String
    let isLoading: Bool
    let isClearingCache: Bool
    @Binding var showPosterURL: String
    @Binding var episodeStillURL: String
    let message: String?
    let errorMessage: String?
    @Binding var jobLabel: String
    @Binding var showName: String
    @Binding var tmdbId: String
    @Binding var imdbId: String
    @Binding var season: String
    @Binding var episode: String
    @Binding var episodeName: String
    @Binding var airdate: String
    @Binding var advancedMetadataJSON: String
    let advancedMetadataErrorMessage: String?
    let onLookup: () -> Void
    let onRefresh: () -> Void
    let onClear: () -> Void
    let onClearCache: () -> Void
    let onApplyAdvancedMetadataJSON: () -> Void
    let onSyncAdvancedMetadataJSON: () -> Void

    var body: some View {
        Section("Metadata") {
            AppleBookCreateSubtitleMetadataControls(
                sourceName: sourceName,
                lookupSourceName: $lookupSourceName,
                isLoading: isLoading,
                isClearingCache: isClearingCache,
                showPosterURL: $showPosterURL,
                episodeStillURL: $episodeStillURL,
                message: message,
                errorMessage: errorMessage,
                jobLabel: $jobLabel,
                showName: $showName,
                tmdbId: $tmdbId,
                imdbId: $imdbId,
                season: $season,
                episode: $episode,
                episodeName: $episodeName,
                airdate: $airdate,
                advancedMetadataJSON: $advancedMetadataJSON,
                advancedMetadataErrorMessage: advancedMetadataErrorMessage,
                onLookup: onLookup,
                onRefresh: onRefresh,
                onClear: onClear,
                onClearCache: onClearCache,
                onApplyAdvancedMetadataJSON: onApplyAdvancedMetadataJSON,
                onSyncAdvancedMetadataJSON: onSyncAdvancedMetadataJSON
            )
        }
    }
}
