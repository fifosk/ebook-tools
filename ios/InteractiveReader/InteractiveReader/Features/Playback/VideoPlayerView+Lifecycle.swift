import SwiftUI

extension VideoPlayerView {
    func handleVideoAppear() {
        isTearingDown = false
        configureLinguistVM()
        loadLlmModelsIfNeeded()
        refreshBookmarks()
        coordinator.onPlaybackEnded = { [weak coordinator] in
            guard let coordinator else { return }
            let duration = coordinator.duration.isFinite && coordinator.duration > 0
                ? coordinator.duration
                : coordinator.currentTime
            onPlaybackEnded?(duration)
        }
        prepareVideoLoad(
            url: videoURL,
            clearSubtitleState: false,
            loadSubtitleData: false,
            configureNowPlayingBeforeMetadata: true
        )
    }

    func clearPlaybackEndedHandler() {
        coordinator.onPlaybackEnded = nil
    }

    func handleVideoURLChange(_ newURL: URL) {
        prepareVideoLoad(
            url: newURL,
            clearSubtitleState: true,
            loadSubtitleData: true,
            configureNowPlayingBeforeMetadata: false
        )
    }

    func handleResumeActionChange() {
        pendingResumeTime = resumeTime ?? 0
        applyPendingResumeIfPossible()
    }

    func handleMetadataChange() {
        updateNowPlayingMetadata()
    }

    func handleResumeTimeChange(_ newValue: Double?) {
        guard newValue != nil else { return }
        pendingResumeTime = newValue
        applyPendingResumeIfPossible()
    }

    func handlePlaybackRateChange(_ newValue: Double) {
        let resolvedRate = Self.clampPlaybackRate(newValue)
        if resolvedRate != newValue {
            playbackRateValue = resolvedRate
        }
        coordinator.setPlaybackRate(resolvedRate)
    }

    func handleSelectedSegmentChange() {
        applyPendingBookmarkIfPossible()
    }

    func handleBookmarkIdentityChange() {
        refreshBookmarks()
    }

    func handleBookmarkStoreChange(_ notification: Notification) {
        guard let jobId = resolvedBookmarkJobId else { return }
        let userId = resolvedBookmarkUserId
        if let changedUser = notification.userInfo?["userId"] as? String, changedUser != userId {
            return
        }
        bookmarks = PlaybackBookmarkStore.shared.bookmarks(for: jobId, userId: userId)
    }

    func handleSubtitleTracksChange() {
        selectDefaultTrackIfNeeded()
        loadSubtitles()
    }

    func handleSelectedTrackChange() {
        loadSubtitles()
    }

    func handleSubtitleVisibilityChange() {
        if !coordinator.isPlaying {
            syncSubtitleSelectionIfNeeded(force: true)
        }
    }

    func handleSubtitleSettingsVisibilityChange(_ isVisible: Bool) {
        #if os(tvOS)
        if isVisible {
            showTVControls = true
            controlsHideTask?.cancel()
        } else {
            showTVControls = false
        }
        #endif
    }

    func handleScrubbingChange(_ scrubbing: Bool) {
        #if os(tvOS)
        if scrubbing {
            showTVControls = true
            controlsHideTask?.cancel()
        } else {
            showTVControls = false
        }
        #endif
    }

    func handleCurrentTimeChange() {
        guard !isTearingDown else { return }
        updateNowPlayingPlayback()
        if !isScrubbing {
            scrubberValue = coordinator.currentTime
        }
        if !coordinator.isPlaying {
            syncSubtitleSelectionIfNeeded()
        }
        reportPlaybackProgress(time: coordinator.currentTime, isPlaying: coordinator.isPlaying)
    }

    func handlePlayingChange(_ isPlaying: Bool) {
        guard !isTearingDown else { return }
        updateNowPlayingPlayback()
        updateTVControlsForPlayback(isPlaying)
        if isPlaying {
            isManualSubtitleNavigation = false
            subtitleActiveCueID = nil
            subtitleSelection = nil
            subtitleSelectionRange = nil
            closeSubtitleBubble()
        } else {
            syncSubtitleSelectionIfNeeded(force: true)
        }
        reportPlaybackProgress(time: coordinator.currentTime, isPlaying: isPlaying)
    }

    func handleDurationChange() {
        guard !isTearingDown else { return }
        updateNowPlayingPlayback()
        if coordinator.duration.isFinite, coordinator.duration > 0 {
            scrubberValue = min(scrubberValue, coordinator.duration)
        } else {
            scrubberValue = 0
        }
        applyPendingResumeIfPossible()
        applyPendingBookmarkIfPossible()
    }

    func handleVideoDisappear() {
        subtitleTask?.cancel()
        subtitleTask = nil
        showSubtitleSettings = false
        controlsHideTask?.cancel()
        controlsHideTask = nil
        isTearingDown = true
        reportPlaybackProgress(time: resolvedPlaybackTime(), isPlaying: false, force: true)
        coordinator.reset()
        nowPlaying.clear()
    }

    private func prepareVideoLoad(
        url: URL,
        clearSubtitleState: Bool,
        loadSubtitleData: Bool,
        configureNowPlayingBeforeMetadata: Bool
    ) {
        isTearingDown = false
        if clearSubtitleState {
            subtitleSelection = nil
            subtitleSelectionRange = nil
            subtitleCache.removeAll()
        }
        pendingResumeTime = resumeTime
        let resolvedRate = Self.clampPlaybackRate(playbackRateValue)
        if resolvedRate != playbackRateValue {
            playbackRateValue = resolvedRate
        }
        coordinator.setPlaybackRate(resolvedRate)
        coordinator.load(url: url, autoPlay: autoPlay && resumeTime == nil)
        if configureNowPlayingBeforeMetadata {
            configureNowPlaying()
        }
        updateNowPlayingMetadata()
        updateNowPlayingPlayback()
        selectDefaultTrackIfNeeded()
        if loadSubtitleData {
            loadSubtitles()
        }
        resetVideoControlsForLoad()
        applyPendingResumeIfPossible()
        applyPendingBookmarkIfPossible()
    }

    private func resetVideoControlsForLoad() {
        scrubberValue = 0
        isScrubbing = false
        #if os(tvOS)
        showTVControls = false
        #else
        showTVControls = true
        scheduleControlsAutoHide()
        #endif
    }

    private func updateTVControlsForPlayback(_ isPlaying: Bool) {
        #if os(tvOS)
        if isPlaying {
            controlsHideTask?.cancel()
            withAnimation(.easeInOut(duration: 0.2)) {
                showTVControls = false
            }
        } else {
            controlsHideTask?.cancel()
        }
        #endif
    }
}
