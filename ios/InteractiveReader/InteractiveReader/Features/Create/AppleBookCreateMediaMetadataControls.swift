import SwiftUI

struct AppleBookCreateSubtitleMetadataControls: View {
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

    private var normalizedLookupSourceName: String {
        lookupSourceName.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    var body: some View {
        if sourceName.isEmpty {
            Label("Choose a subtitle to load TV metadata.", systemImage: "captions.bubble")
                .font(.footnote)
                .foregroundStyle(.secondary)
                .accessibilityIdentifier("createSubtitleMetadataEmpty")
        } else {
            TextField("Lookup filename", text: $lookupSourceName)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
                .accessibilityIdentifier("createSubtitleMetadataLookupField")

            HStack(spacing: 12) {
                AppleBookCreateMetadataActionButton(
                    title: "Lookup",
                    busyTitle: "Looking up",
                    systemImage: "tv",
                    isBusy: isLoading,
                    isDisabled: isLoading || normalizedLookupSourceName.isEmpty,
                    accessibilityIdentifier: "createSubtitleMetadataLookupButton",
                    action: onLookup
                )

                AppleBookCreateMetadataActionButton(
                    title: "Refresh",
                    systemImage: "arrow.clockwise",
                    isDisabled: isLoading || normalizedLookupSourceName.isEmpty,
                    accessibilityIdentifier: "createSubtitleMetadataRefreshButton",
                    action: onRefresh
                )

                AppleBookCreateMetadataActionButton(
                    title: "Clear Cache",
                    busyTitle: "Clearing Cache",
                    systemImage: "trash",
                    isBusy: isClearingCache,
                    isDisabled: isLoading || isClearingCache || normalizedLookupSourceName.isEmpty,
                    accessibilityIdentifier: "createSubtitleMetadataClearCacheButton",
                    action: onClearCache
                )

                AppleBookCreateMetadataActionButton(
                    title: "Clear",
                    systemImage: "xmark.circle",
                    isDisabled: isLoading || isClearingCache,
                    accessibilityIdentifier: "createSubtitleMetadataClearButton",
                    action: onClear
                )
            }
        }

        AppleBookCreateMetadataArtworkPreview(
            posterURL: showPosterURL,
            stillURL: episodeStillURL,
            posterLabel: showName.isEmpty ? "Show poster" : "\(showName) poster",
            stillLabel: episodeName.isEmpty ? "Episode still" : "\(episodeName) still"
        )

        AppleBookCreateMetadataStatusMessages(
            message: message,
            errorMessage: errorMessage,
            statusIdentifier: "createSubtitleMetadataStatus",
            errorIdentifier: "createSubtitleMetadataError"
        )

        TextField("Job label", text: $jobLabel)
            .textInputAutocapitalization(.words)
            .autocorrectionDisabled()
            .accessibilityIdentifier("createSubtitleMetadataJobLabelField")
        TextField("Show title", text: $showName)
            .textInputAutocapitalization(.words)
            .autocorrectionDisabled()
            .accessibilityIdentifier("createSubtitleMetadataShowField")
        TextField("TMDB ID", text: $tmdbId)
            .textInputAutocapitalization(.never)
            .autocorrectionDisabled()
            .accessibilityIdentifier("createSubtitleMetadataTmdbIdField")
        TextField("IMDb ID", text: $imdbId)
            .textInputAutocapitalization(.never)
            .autocorrectionDisabled()
            .accessibilityIdentifier("createSubtitleMetadataImdbIdField")
        TextField("Season", text: $season)
            .textInputAutocapitalization(.never)
            .autocorrectionDisabled()
            .accessibilityIdentifier("createSubtitleMetadataSeasonField")
        TextField("Episode", text: $episode)
            .textInputAutocapitalization(.never)
            .autocorrectionDisabled()
            .accessibilityIdentifier("createSubtitleMetadataEpisodeNumberField")
        TextField("Episode title", text: $episodeName)
            .textInputAutocapitalization(.sentences)
            .autocorrectionDisabled()
            .accessibilityIdentifier("createSubtitleMetadataEpisodeTitleField")
        TextField("Airdate", text: $airdate)
            .textInputAutocapitalization(.never)
            .autocorrectionDisabled()
            .accessibilityIdentifier("createSubtitleMetadataAirdateField")

        #if os(tvOS)
        Group {
            Text("Artwork")
                .font(.headline)
            subtitleArtworkFields
        }
        .accessibilityIdentifier("createSubtitleMetadataArtworkDisclosure")
        #else
        DisclosureGroup("Artwork") {
            subtitleArtworkFields
        }
        .accessibilityIdentifier("createSubtitleMetadataArtworkDisclosure")
        #endif

        AppleBookCreateAdvancedMetadataJSONEditor(
            text: $advancedMetadataJSON,
            errorMessage: advancedMetadataErrorMessage,
            disclosureIdentifier: "createSubtitleAdvancedMetadataDisclosure",
            textEditorIdentifier: "createSubtitleAdvancedMetadataJSONEditor",
            applyIdentifier: "createSubtitleAdvancedMetadataApplyButton",
            syncIdentifier: "createSubtitleAdvancedMetadataSyncButton",
            errorIdentifier: "createSubtitleAdvancedMetadataJSONError",
            onApply: onApplyAdvancedMetadataJSON,
            onSync: onSyncAdvancedMetadataJSON
        )
    }

    private var subtitleArtworkFields: some View {
        Group {
            TextField("Show poster URL", text: $showPosterURL)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
                .accessibilityIdentifier("createSubtitleMetadataPosterUrlField")
            TextField("Episode still URL", text: $episodeStillURL)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
                .accessibilityIdentifier("createSubtitleMetadataStillUrlField")
        }
    }
}

struct AppleBookCreateYoutubeMetadataControls: View {
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
        HStack(spacing: 12) {
            AppleBookCreateMetadataActionButton(
                title: "Load TV",
                busyTitle: "Loading TV",
                systemImage: "tv",
                isBusy: isLoadingTvMetadata,
                isDisabled: isLoadingTvMetadata || isLoadingYoutubeMetadata,
                accessibilityIdentifier: "createYoutubeLoadTvMetadataButton",
                action: onLoadTvMetadata
            )

            AppleBookCreateMetadataActionButton(
                title: "Load YouTube",
                busyTitle: "Loading YouTube",
                systemImage: "play.rectangle",
                isBusy: isLoadingYoutubeMetadata,
                isDisabled: isLoadingTvMetadata || isLoadingYoutubeMetadata,
                accessibilityIdentifier: "createYoutubeLoadYoutubeMetadataButton",
                action: onLoadYoutubeMetadata
            )
        }

        HStack(spacing: 12) {
            AppleBookCreateMetadataActionButton(
                title: "Clear TV Cache",
                busyTitle: "Clearing TV",
                systemImage: "trash",
                isBusy: isClearingTvMetadataCache,
                isDisabled: !canClearTvMetadataCache ||
                    isLoadingTvMetadata ||
                    isLoadingYoutubeMetadata ||
                    isClearingTvMetadataCache,
                accessibilityIdentifier: "createYoutubeClearTvMetadataCacheButton",
                action: onClearTvMetadataCache
            )

            AppleBookCreateMetadataActionButton(
                title: "Clear YouTube Cache",
                busyTitle: "Clearing YouTube",
                systemImage: "trash",
                isBusy: isClearingYoutubeMetadataCache,
                isDisabled: !canClearYoutubeMetadataCache ||
                    isLoadingTvMetadata ||
                    isLoadingYoutubeMetadata ||
                    isClearingYoutubeMetadataCache,
                accessibilityIdentifier: "createYoutubeClearYoutubeMetadataCacheButton",
                action: onClearYoutubeMetadataCache
            )
        }

        AppleBookCreateMetadataArtworkPreview(
            posterURL: tvPosterURL,
            stillURL: tvEpisodeStillURL,
            thumbnailURL: youtubeThumbnailURL,
            posterLabel: showName.isEmpty ? "Series poster" : "\(showName) poster",
            stillLabel: episodeName.isEmpty ? "Episode still" : "\(episodeName) still",
            thumbnailLabel: title.isEmpty ? "YouTube thumbnail" : "\(title) thumbnail"
        )

        AppleBookCreateMetadataStatusMessages(
            message: message,
            errorMessage: errorMessage,
            statusIdentifier: "createYoutubeMetadataStatus",
            errorIdentifier: "createYoutubeMetadataError"
        )

        TextField("YouTube title", text: $title)
            .textInputAutocapitalization(.sentences)
            .autocorrectionDisabled()
            .accessibilityIdentifier("createYoutubeMetadataTitleField")
        TextField("Channel", text: $channel)
            .textInputAutocapitalization(.words)
            .autocorrectionDisabled()
            .accessibilityIdentifier("createYoutubeMetadataChannelField")
        TextField("Series", text: $showName)
            .textInputAutocapitalization(.words)
            .autocorrectionDisabled()
            .accessibilityIdentifier("createYoutubeMetadataSeriesField")
        TextField("TMDB ID", text: $tmdbId)
            .textInputAutocapitalization(.never)
            .autocorrectionDisabled()
            .accessibilityIdentifier("createYoutubeMetadataTmdbIdField")
        TextField("IMDb ID", text: $imdbId)
            .textInputAutocapitalization(.never)
            .autocorrectionDisabled()
            .accessibilityIdentifier("createYoutubeMetadataImdbIdField")
        TextField("Episode", text: $episodeName)
            .textInputAutocapitalization(.sentences)
            .autocorrectionDisabled()
            .accessibilityIdentifier("createYoutubeMetadataEpisodeField")

        #if os(tvOS)
        Group {
            Text("Artwork")
                .font(.headline)
            youtubeArtworkFields
        }
        .accessibilityIdentifier("createYoutubeMetadataArtworkDisclosure")
        #else
        DisclosureGroup("Artwork") {
            youtubeArtworkFields
        }
        .accessibilityIdentifier("createYoutubeMetadataArtworkDisclosure")
        #endif

        AppleBookCreateAdvancedMetadataJSONEditor(
            text: $advancedMetadataJSON,
            errorMessage: advancedMetadataErrorMessage,
            disclosureIdentifier: "createYoutubeAdvancedMetadataDisclosure",
            textEditorIdentifier: "createYoutubeAdvancedMetadataJSONEditor",
            applyIdentifier: "createYoutubeAdvancedMetadataApplyButton",
            syncIdentifier: "createYoutubeAdvancedMetadataSyncButton",
            errorIdentifier: "createYoutubeAdvancedMetadataJSONError",
            onApply: onApplyAdvancedMetadataJSON,
            onSync: onSyncAdvancedMetadataJSON
        )
    }

    private var youtubeArtworkFields: some View {
        Group {
            TextField("Series poster URL", text: $tvPosterURL)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
                .accessibilityIdentifier("createYoutubeMetadataPosterUrlField")
            TextField("Episode still URL", text: $tvEpisodeStillURL)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
                .accessibilityIdentifier("createYoutubeMetadataStillUrlField")
            TextField("YouTube thumbnail URL", text: $youtubeThumbnailURL)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
                .accessibilityIdentifier("createYoutubeMetadataThumbnailUrlField")
        }
    }
}
