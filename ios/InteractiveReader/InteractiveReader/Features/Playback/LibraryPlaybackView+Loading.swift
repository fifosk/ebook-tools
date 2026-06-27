import Foundation

extension LibraryPlaybackView {
    @MainActor
    func loadEntry() async {
        guard let configuration = appState.configuration else { return }

        let manager = PlaybackResumeManager(
            jobId: item.jobId,
            itemType: item.itemType,
            userId: appState.resumeUserKey,
            userAliases: appState.resumeUserAliases
        )
        resumeManager = manager
        manager.resetState()

        let shouldAutoPlay = autoPlayOnLoad
        autoPlayOnLoad = false
        sentenceIndexTracker.value = nil
        #if !os(tvOS)
        showVideoPlayer = false
        #endif

        let offlinePayload = await offlineStore.cachedPayload(for: item.jobId, kind: .library)
        if let offlinePayload,
           let localResolver = offlineStore.localResolver(for: .library, configuration: configuration) {
            let offlineConfig = APIClientConfiguration(
                apiBaseURL: configuration.apiBaseURL,
                storageBaseURL: offlinePayload.storageBaseURL,
                authToken: configuration.authToken,
                userID: configuration.userID,
                userRole: configuration.userRole
            )
            await viewModel.loadJob(
                jobId: item.jobId,
                configuration: offlineConfig,
                origin: .library,
                preferLiveMedia: false,
                mediaOverride: offlinePayload.media,
                timingOverride: offlinePayload.timing,
                resolverOverride: localResolver
            )
            applyOfflineReadingBeds(offlinePayload)
            viewModel.offlineLookupCache = offlinePayload.lookupCache
        } else {
            await viewModel.loadJob(jobId: item.jobId, configuration: configuration, origin: .library)
        }
        await viewModel.updateChapterIndex(from: item.metadata)
        if isVideoPreferred || isAppleMusicOwningLockScreen {
            nowPlaying.clear()
        } else {
            configureNowPlaying()
            updateNowPlayingMetadata(sentenceIndex: sentenceIndexTracker.value)
            updateNowPlayingPlayback(time: viewModel.audioCoordinator.currentTime)
        }
        await manager.syncNow()
        manager.markResumeDecisionComplete()

        switch playbackMode {
        case .resume:
            if let resumeEntry = manager.resolveResumeEntry(isVideoPreferred: isVideoPreferred) {
                applyResume(resumeEntry)
                return
            }
            if shouldAutoPlay {
                startPlaybackFromBeginning()
            }
        case .resumeExisting:
            if let resumeEntry = manager.resolveResumeEntry(isVideoPreferred: isVideoPreferred) {
                applyResume(resumeEntry)
            }
        case .startOver:
            manager.clearResumeEntry()
            if shouldAutoPlay {
                startPlaybackFromBeginning()
            }
        }
    }

    @MainActor
    private func applyOfflineReadingBeds(_ payload: OfflineMediaStore.OfflineMediaPayload) {
        viewModel.readingBedCatalog = payload.readingBeds
        viewModel.readingBedBaseURL = payload.readingBedBaseURL
        viewModel.selectReadingBed(id: viewModel.selectedReadingBedID)
    }
}
