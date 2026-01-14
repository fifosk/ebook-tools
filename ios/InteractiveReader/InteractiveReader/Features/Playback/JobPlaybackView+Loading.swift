import Foundation
import AVFoundation

extension JobPlaybackView {
    @MainActor
    func loadEntry() async {
        guard let configuration = appState.configuration else { return }
        sentenceIndex = nil
        resetResumeState()
        let shouldAutoPlay = autoPlayOnLoad
        autoPlayOnLoad = false
        activeVideoSegmentID = nil
        completedSegmentDurations = [:]
        segmentDurations = [:]
        subtitleTvMetadata = nil
        youtubeVideoMetadata = nil
        jobStatus = job
        let offlinePayload = offlineStore.cachedPayload(for: job.jobId, kind: .job)
        if let offlinePayload,
           let localResolver = offlineStore.localResolver(for: .job, configuration: configuration) {
            let offlineConfig = APIClientConfiguration(
                apiBaseURL: configuration.apiBaseURL,
                storageBaseURL: offlinePayload.storageBaseURL,
                authToken: configuration.authToken,
                userID: configuration.userID,
                userRole: configuration.userRole
            )
            await viewModel.loadJob(
                jobId: job.jobId,
                configuration: offlineConfig,
                origin: .job,
                preferLiveMedia: false,
                mediaOverride: offlinePayload.media,
                timingOverride: offlinePayload.timing,
                resolverOverride: localResolver
            )
        } else {
            await viewModel.loadJob(
                jobId: job.jobId,
                configuration: configuration,
                origin: .job,
                preferLiveMedia: currentJob.status.isActive
            )
        }
        await viewModel.updateChapterIndex(from: jobMetadata)
        await loadVideoMetadata()
        refreshActiveVideoSegment()
        preloadSegmentDurations()
        if isVideoPreferred {
            nowPlaying.clear()
        } else {
            configureNowPlaying()
            updateNowPlayingMetadata(sentenceIndex: sentenceIndex)
            updateNowPlayingPlayback(time: viewModel.audioCoordinator.currentTime)
        }
        if let userId = resumeUserId {
            await PlaybackResumeStore.shared.refreshCloudEntries(userId: userId)
        }
        if let resumeEntry = resolveResumeEntry() {
            pendingResumeEntry = resumeEntry
            showResumePrompt = true
            if isVideoPreferred {
                videoAutoPlay = false
            }
            return
        }
        resumeDecisionPending = false
        if shouldAutoPlay {
            startPlaybackFromBeginning()
        }
        await refreshJobStatus()
        startJobRefresh()
        if currentJob.status.isActive {
            viewModel.startLiveUpdates()
        }
    }

    @MainActor
    func loadVideoMetadata() async {
        guard let configuration = appState.configuration else { return }
        let client = APIClient(configuration: configuration)
        if shouldFetchTvMetadata {
            do {
                subtitleTvMetadata = try await client.fetchSubtitleTvMetadata(jobId: currentJob.jobId)
            } catch {
                subtitleTvMetadata = nil
            }
        }
        if shouldFetchYoutubeMetadata {
            do {
                youtubeVideoMetadata = try await client.fetchYoutubeVideoMetadata(jobId: currentJob.jobId)
            } catch {
                youtubeVideoMetadata = nil
            }
        }
    }

    func startJobRefresh() {
        stopJobRefresh()
        jobRefreshTask = Task {
            while !Task.isCancelled {
                await refreshJobStatus()
                try? await Task.sleep(nanoseconds: jobRefreshInterval)
            }
        }
    }

    func stopJobRefresh() {
        jobRefreshTask?.cancel()
        jobRefreshTask = nil
    }

    @MainActor
    func refreshJobStatus() async {
        guard let configuration = appState.configuration else { return }
        do {
            let client = APIClient(configuration: configuration)
            let status = try await client.fetchPipelineStatus(jobId: job.jobId)
            jobStatus = status
            if !status.status.isActive {
                viewModel.stopLiveUpdates()
            }
        } catch {
            return
        }
    }

    func refreshActiveVideoSegment() {
        guard !videoSegments.isEmpty else {
            activeVideoSegmentID = nil
            return
        }
        if let activeVideoSegmentID,
           videoSegments.contains(where: { $0.id == activeVideoSegmentID }) {
            return
        }
        activeVideoSegmentID = videoSegments.first?.id
    }

    func preloadSegmentDurations() {
        segmentDurationTask?.cancel()
        segmentDurationTask = nil
        guard isVideoPreferred else { return }
        guard !videoSegments.isEmpty else { return }
        let pending = videoSegments.compactMap { segment -> (String, URL)? in
            guard segmentDurations[segment.id] == nil else { return nil }
            guard let url = viewModel.resolveMediaURL(for: segment.videoFile) else { return nil }
            return (segment.id, url)
        }
        guard !pending.isEmpty else { return }
        segmentDurationTask = Task { @MainActor in
            for (segmentID, url) in pending {
                if Task.isCancelled { return }
                let asset = AVURLAsset(url: url)
                do {
                    let duration = try await asset.load(.duration)
                    let seconds = duration.seconds
                    if seconds.isFinite, seconds > 0 {
                        segmentDurations[segmentID] = seconds
                    }
                } catch {
                    continue
                }
            }
        }
    }

    func handleVideoSegmentEnded(duration: Double) {
        guard !videoSegments.isEmpty else { return }
        guard let activeID = activeVideoSegmentID ?? videoSegments.first?.id else { return }
        if duration.isFinite, duration > 0 {
            completedSegmentDurations[activeID] = duration
            segmentDurations[activeID] = duration
        }
        guard let currentIndex = videoSegments.firstIndex(where: { $0.id == activeID }) else { return }
        let nextIndex = currentIndex + 1
        guard videoSegments.indices.contains(nextIndex) else { return }
        activeVideoSegmentID = videoSegments[nextIndex].id
        videoResumeTime = nil
        videoAutoPlay = true
        videoResumeActionID = UUID()
    }

    func handleVideoSegmentSelection(_ segmentID: String) {
        guard activeVideoSegmentID != segmentID else { return }
        activeVideoSegmentID = segmentID
        videoResumeTime = nil
        videoAutoPlay = true
        videoResumeActionID = UUID()
    }

    func handleVideoPlaybackProgress(time: Double, isPlaying: Bool) {
        let absoluteTime = absoluteVideoTime(for: activeVideoSegmentID ?? videoSegments.first?.id, segmentTime: time)
        lastVideoTime = absoluteTime
        recordVideoResume(time: absoluteTime, isPlaying: isPlaying)
    }

    func absoluteVideoTime(for segmentID: String?, segmentTime: Double) -> Double {
        guard segmentTime.isFinite else { return 0 }
        return max(0, segmentOffset(for: segmentID) + segmentTime)
    }

    func segmentOffset(for segmentID: String?) -> Double {
        guard let segmentID,
              let index = videoSegments.firstIndex(where: { $0.id == segmentID })
        else {
            return 0
        }
        var offset: Double = 0
        for segment in videoSegments.prefix(index) {
            if let duration = segmentDurations[segment.id] ?? completedSegmentDurations[segment.id],
               duration.isFinite,
               duration > 0
            {
                offset += duration
            }
        }
        return offset
    }
}
