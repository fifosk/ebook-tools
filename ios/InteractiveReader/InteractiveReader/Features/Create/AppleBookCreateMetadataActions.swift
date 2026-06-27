import Foundation

extension AppleBookCreateView {
    func refreshVoiceInventory() {
        Task {
            await viewModel.loadVoiceInventory(
                using: appState,
                cacheKey: creationOptionsLoadKey,
                force: true
            )
        }
    }

    func checkImageNodes() {
        Task {
            await viewModel.checkImageNodeAvailability(
                baseURLsText: imageApiBaseURLs,
                using: appState
            )
        }
    }

    func previewVoice(_ language: String, _ label: String, _ selectedVoice: AppleBookCreateVoiceOption) {
        viewModel.previewVoice(
            language: language,
            languageLabel: label,
            voice: selectedVoice,
            using: appState
        )
    }

    func loadYoutubeTvMetadata() {
        Task {
            await viewModel.lookupYoutubeTvMetadata(
                sourceName: youtubeMetadataTvSourceName,
                using: appState
            )
        }
    }

    func loadYoutubeVideoMetadata() {
        Task {
            await viewModel.lookupYoutubeVideoMetadata(
                sourceName: youtubeMetadataVideoSourceName,
                using: appState
            )
        }
    }

    func clearYoutubeTvMetadataCache() {
        Task {
            await viewModel.clearYoutubeTvMetadataCache(
                query: youtubeMetadataTvSourceName,
                using: appState
            )
        }
    }

    func clearYoutubeVideoMetadataCache() {
        Task {
            await viewModel.clearYoutubeVideoMetadataCache(
                query: youtubeMetadataVideoSourceName,
                using: appState
            )
        }
    }

    func applyYoutubeAdvancedMetadataJSON() {
        viewModel.applyYoutubeMediaMetadataJSONText()
    }

    func syncYoutubeAdvancedMetadataJSON() {
        viewModel.syncYoutubeMediaMetadataJSONText()
    }

    func lookupSubtitleMetadata() {
        Task {
            await viewModel.lookupSubtitleTvMetadata(
                sourceName: subtitleMetadataLookupSourceName,
                using: appState
            )
        }
    }

    func refreshSubtitleMetadata() {
        Task {
            await viewModel.lookupSubtitleTvMetadata(
                sourceName: subtitleMetadataLookupSourceName,
                force: true,
                using: appState
            )
        }
    }

    func clearSubtitleMetadata() {
        viewModel.clearSubtitleMetadata()
    }

    func clearSubtitleMetadataCache() {
        Task {
            await viewModel.clearSubtitleTvMetadataCache(
                query: subtitleMetadataLookupSourceName,
                using: appState
            )
        }
    }

    func applySubtitleAdvancedMetadataJSON() {
        viewModel.applySubtitleMediaMetadataJSONText()
    }

    func syncSubtitleAdvancedMetadataJSON() {
        viewModel.syncSubtitleMediaMetadataJSONText()
    }

    func retryCreationOptions() {
        Task { await refreshCreationOptions(force: true) }
    }
}
