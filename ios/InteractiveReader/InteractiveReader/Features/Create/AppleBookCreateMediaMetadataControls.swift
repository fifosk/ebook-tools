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
                Button(action: onLookup) {
                    Label(isLoading ? "Looking up" : "Lookup", systemImage: isLoading ? "hourglass" : "tv")
                }
                .disabled(isLoading || lookupSourceName.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                .accessibilityIdentifier("createSubtitleMetadataLookupButton")

                Button(action: onRefresh) {
                    Label("Refresh", systemImage: "arrow.clockwise")
                }
                .disabled(isLoading || lookupSourceName.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                .accessibilityIdentifier("createSubtitleMetadataRefreshButton")

                Button(action: onClearCache) {
                    Label(
                        isClearingCache ? "Clearing Cache" : "Clear Cache",
                        systemImage: isClearingCache ? "hourglass" : "trash"
                    )
                }
                .disabled(
                    isLoading ||
                    isClearingCache ||
                    lookupSourceName.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
                )
                .accessibilityIdentifier("createSubtitleMetadataClearCacheButton")

                Button(action: onClear) {
                    Label("Clear", systemImage: "xmark.circle")
                }
                .disabled(isLoading || isClearingCache)
                .accessibilityIdentifier("createSubtitleMetadataClearButton")
            }
        }

        AppleBookCreateMetadataArtworkPreview(
            posterURL: showPosterURL,
            stillURL: episodeStillURL,
            posterLabel: showName.isEmpty ? "Show poster" : "\(showName) poster",
            stillLabel: episodeName.isEmpty ? "Episode still" : "\(episodeName) still"
        )

        if let message, !message.isEmpty {
            Label(message, systemImage: "checkmark.circle")
                .font(.footnote)
                .foregroundStyle(.secondary)
                .accessibilityIdentifier("createSubtitleMetadataStatus")
        }
        if let errorMessage, !errorMessage.isEmpty {
            Label(errorMessage, systemImage: "exclamationmark.triangle")
                .font(.footnote)
                .foregroundStyle(.red)
                .accessibilityIdentifier("createSubtitleMetadataError")
        }

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
            Button(action: onLoadTvMetadata) {
                Label(
                    isLoadingTvMetadata ? "Loading TV" : "Load TV",
                    systemImage: isLoadingTvMetadata ? "hourglass" : "tv"
                )
            }
            .disabled(isLoadingTvMetadata || isLoadingYoutubeMetadata)
            .accessibilityIdentifier("createYoutubeLoadTvMetadataButton")

            Button(action: onLoadYoutubeMetadata) {
                Label(
                    isLoadingYoutubeMetadata ? "Loading YouTube" : "Load YouTube",
                    systemImage: isLoadingYoutubeMetadata ? "hourglass" : "play.rectangle"
                )
            }
            .disabled(isLoadingTvMetadata || isLoadingYoutubeMetadata)
            .accessibilityIdentifier("createYoutubeLoadYoutubeMetadataButton")
        }

        HStack(spacing: 12) {
            Button(action: onClearTvMetadataCache) {
                Label(
                    isClearingTvMetadataCache ? "Clearing TV" : "Clear TV Cache",
                    systemImage: isClearingTvMetadataCache ? "hourglass" : "trash"
                )
            }
            .disabled(
                !canClearTvMetadataCache ||
                isLoadingTvMetadata ||
                isLoadingYoutubeMetadata ||
                isClearingTvMetadataCache
            )
            .accessibilityIdentifier("createYoutubeClearTvMetadataCacheButton")

            Button(action: onClearYoutubeMetadataCache) {
                Label(
                    isClearingYoutubeMetadataCache ? "Clearing YouTube" : "Clear YouTube Cache",
                    systemImage: isClearingYoutubeMetadataCache ? "hourglass" : "trash"
                )
            }
            .disabled(
                !canClearYoutubeMetadataCache ||
                isLoadingTvMetadata ||
                isLoadingYoutubeMetadata ||
                isClearingYoutubeMetadataCache
            )
            .accessibilityIdentifier("createYoutubeClearYoutubeMetadataCacheButton")
        }

        AppleBookCreateMetadataArtworkPreview(
            posterURL: tvPosterURL,
            stillURL: tvEpisodeStillURL,
            thumbnailURL: youtubeThumbnailURL,
            posterLabel: showName.isEmpty ? "Series poster" : "\(showName) poster",
            stillLabel: episodeName.isEmpty ? "Episode still" : "\(episodeName) still",
            thumbnailLabel: title.isEmpty ? "YouTube thumbnail" : "\(title) thumbnail"
        )

        if let message, !message.isEmpty {
            Label(message, systemImage: "checkmark.circle")
                .font(.footnote)
                .foregroundStyle(.secondary)
                .accessibilityIdentifier("createYoutubeMetadataStatus")
        }
        if let errorMessage, !errorMessage.isEmpty {
            Label(errorMessage, systemImage: "exclamationmark.triangle")
                .font(.footnote)
                .foregroundStyle(.red)
                .accessibilityIdentifier("createYoutubeMetadataError")
        }

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
