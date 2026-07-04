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
        interactivePlayerReadyForAutoplay = false
        pendingInteractivePlaybackStart = false
        pendingInteractivePlaybackAllowsStartWithoutResume = false
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

        if !deferInteractivePlaybackStartIfNeeded(allowStartWithoutResume: shouldAutoPlay) {
            drainInteractivePlaybackStart(allowStartWithoutResume: shouldAutoPlay)
        }
    }

    @discardableResult
    func deferInteractivePlaybackStartIfNeeded(allowStartWithoutResume: Bool) -> Bool {
        guard !isVideoPreferred,
              viewModel.jobContext != nil
        else { return false }
        pendingInteractivePlaybackStart = true
        pendingInteractivePlaybackAllowsStartWithoutResume = allowStartWithoutResume
        playbackTransportDebugLog(
            "[PlaybackTransport] Library deferring interactive autoplay until player ready allowStart=\(allowStartWithoutResume) ready=\(interactivePlayerReadyForAutoplay)"
        )
        if interactivePlayerReadyForAutoplay {
            Task { @MainActor in
                await Task.yield()
                handleInteractivePlayerReadyForPlayback()
            }
        } else {
            scheduleInteractivePlaybackReadinessRetry()
        }
        return true
    }

    func scheduleInteractivePlaybackReadinessRetry() {
        Task { @MainActor in
            let probes: [UInt64] = [
                50_000_000,
                150_000_000,
                350_000_000,
                750_000_000,
                1_250_000_000,
                2_000_000_000
            ]
            for delay in probes {
                try? await Task.sleep(nanoseconds: delay)
                guard pendingInteractivePlaybackStart else { return }
                guard !interactivePlayerReadyForAutoplay else {
                    handleInteractivePlayerReadyForPlayback()
                    return
                }
                guard let chunk = viewModel.selectedChunk,
                      viewModel.isTranscriptReady(for: chunk) else {
                    continue
                }
                playbackTransportDebugLog(
                    "[PlaybackTransport] Library interactive player readiness retry accepted selectedChunk=\(chunk.id)"
                )
                interactivePlayerReadyForAutoplay = true
                handleInteractivePlayerReadyForPlayback()
                return
            }
            if pendingInteractivePlaybackStart {
                playbackTransportDebugLog(
                    "[PlaybackTransport] Library interactive player readiness retry exhausted selectedChunk=\(viewModel.selectedChunkID ?? "nil") transcriptLoading=\(viewModel.isTranscriptLoading)"
                )
            }
        }
    }

    func handleInteractivePlayerReadyForPlayback() {
        let wasPending = pendingInteractivePlaybackStart
        interactivePlayerReadyForAutoplay = true
        playbackTransportDebugLog(
            "[PlaybackTransport] Library interactive player ready pendingStart=\(wasPending)"
        )
        guard wasPending else { return }
        let allowStart = pendingInteractivePlaybackAllowsStartWithoutResume
        pendingInteractivePlaybackStart = false
        pendingInteractivePlaybackAllowsStartWithoutResume = false
        drainInteractivePlaybackStart(allowStartWithoutResume: allowStart)
    }

    func drainInteractivePlaybackStart(allowStartWithoutResume: Bool) {
        guard let manager = resumeManager else { return }
        if let chunk = viewModel.selectedChunk {
            _ = viewModel.reassertSelectedAudioTrackAfterContextRebuild()
            playbackTransportDebugLog(
                "[PlaybackTransport] Library draining interactive autoplay context chunk=\(chunk.id) trackID=\(viewModel.selectedAudioTrackID ?? "nil") sequence=\(viewModel.isSequenceModeActive) transcriptReady=\(viewModel.isTranscriptReady(for: chunk))"
            )
        }
        playbackTransportDebugLog(
            "[PlaybackTransport] Library draining interactive autoplay mode=\(String(describing: playbackMode)) allowStart=\(allowStartWithoutResume) selectedChunk=\(viewModel.selectedChunkID ?? "nil") requested=\(viewModel.audioCoordinator.isPlaybackRequested) playing=\(viewModel.audioCoordinator.isPlaying)"
        )
        switch playbackMode {
        case .resume:
            if let resumeEntry = manager.resolveResumeEntry(isVideoPreferred: isVideoPreferred) {
                applyResume(resumeEntry)
            } else if allowStartWithoutResume {
                startPlaybackFromBeginning()
            }
        case .resumeExisting:
            if let resumeEntry = manager.resolveResumeEntry(isVideoPreferred: isVideoPreferred) {
                applyResume(resumeEntry)
            }
        case .startOver:
            manager.clearResumeEntry()
            if allowStartWithoutResume {
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
