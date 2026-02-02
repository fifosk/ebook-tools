import Foundation
#if os(iOS)
import UIKit
#endif

extension JobPlaybackView {
    var resumeUserId: String? {
        appState.resumeUserKey
    }

    var resumeItemType: String {
        currentJob.jobType.nonEmptyValue ?? itemTypeLabel.lowercased()
    }

    func resetResumeState() {
        videoResumeTime = nil
        videoResumeActionID = UUID()
        videoAutoPlay = false
        resumeDecisionPending = true
        lastRecordedSentence = nil
        lastRecordedTimeBucket = nil
        lastVideoTime = 0
        segmentDurationTask?.cancel()
        segmentDurationTask = nil
        #if !os(tvOS)
        showVideoPlayer = false
        #endif
    }

    func resolveResumeEntry() -> PlaybackResumeEntry? {
        guard let userId = resumeUserId else { return nil }
        guard let entry = PlaybackResumeStore.shared.entry(for: currentJob.jobId, userId: userId) else { return nil }
        guard entry.isMeaningful else { return nil }
        if isVideoPreferred {
            return entry.kind == .time ? entry : nil
        }
        return entry.kind == .sentence ? entry : nil
    }

    func startPlaybackFromBeginning() {
        if isVideoPreferred {
            // Always present the video player - no cover preview needed
            startVideoPlayback(at: nil, presentPlayer: true)
        } else if viewModel.jobContext != nil {
            startInteractivePlayback(at: 1)
        }
    }

    func applyResume(_ entry: PlaybackResumeEntry) {
        resumeDecisionPending = false
        if isVideoPreferred {
            startVideoPlayback(at: entry.playbackTime, presentPlayer: true)
        } else {
            startInteractivePlayback(at: entry.sentenceNumber)
        }
    }

    func startInteractivePlayback(at sentence: Int?) {
        if let sentence, sentence > 0 {
            // jumpToSentence with autoPlay: true handles seeking and starting playback
            // after the audio is loaded and seeked to the target position.
            // Do NOT call play() here as it would start playback from position 0
            // before the async seek operation completes.
            viewModel.jumpToSentence(sentence, autoPlay: true)
        } else {
            // No sentence target - start playback from current position
            if !viewModel.audioCoordinator.isPlaying {
                viewModel.audioCoordinator.play()
            }
        }
    }

    func startVideoPlayback(at absoluteTime: Double?, presentPlayer: Bool) {
        videoAutoPlay = true
        if let target = resolveVideoResumeTarget(absoluteTime) {
            activeVideoSegmentID = target.segmentID
            videoResumeTime = target.localTime
        } else {
            if activeVideoSegmentID == nil {
                activeVideoSegmentID = videoSegments.first?.id
            }
            videoResumeTime = absoluteTime
        }
        videoResumeActionID = UUID()
        #if !os(tvOS)
        if presentPlayer {
            showVideoPlayer = true
        }
        #endif
    }

    #if !os(tvOS)
    func handleVideoPreviewTap() {
        // If there's a resume entry, apply it; otherwise start from beginning
        if let resumeEntry = resolveResumeEntry() {
            applyResume(resumeEntry)
        } else {
            startVideoPlayback(at: nil, presentPlayer: true)
        }
    }
    #endif

    func resolveVideoResumeTarget(_ absoluteTime: Double?) -> VideoResumeTarget? {
        guard let absoluteTime, absoluteTime > 0 else { return nil }
        guard !videoSegments.isEmpty else { return nil }
        if videoSegments.count == 1 {
            return VideoResumeTarget(segmentID: videoSegments[0].id, localTime: absoluteTime)
        }
        var accumulated: Double = 0
        for segment in videoSegments {
            let duration = segmentDurations[segment.id] ?? completedSegmentDurations[segment.id]
            if let duration, duration.isFinite, duration > 0 {
                let end = accumulated + duration
                if absoluteTime < end {
                    return VideoResumeTarget(segmentID: segment.id, localTime: max(0, absoluteTime - accumulated))
                }
                accumulated = end
            }
        }
        if let last = videoSegments.last {
            return VideoResumeTarget(segmentID: last.id, localTime: max(0, absoluteTime - accumulated))
        }
        return nil
    }

    func clearResumeEntry() {
        guard let userId = resumeUserId else { return }
        PlaybackResumeStore.shared.clearEntry(jobId: currentJob.jobId, userId: userId)
    }

    func resumePromptMessage(for entry: PlaybackResumeEntry) -> String {
        let iCloudNote = iCloudResumeNote()
        switch entry.kind {
        case .sentence:
            let sentence = entry.sentenceNumber ?? 1
            return "Continue from sentence \(sentence).\n\(iCloudNote)"
        case .time:
            let time = entry.playbackTime ?? 0
            return "Continue from \(formatPlaybackTime(time)).\n\(iCloudNote)"
        }
    }

    func formatPlaybackTime(_ time: Double) -> String {
        let formatter = DateComponentsFormatter()
        formatter.allowedUnits = time >= 3600 ? [.hour, .minute, .second] : [.minute, .second]
        formatter.zeroFormattingBehavior = .pad
        return formatter.string(from: time) ?? "0:00"
    }

    func iCloudResumeNote() -> String {
        let status = PlaybackResumeStore.shared.iCloudStatus()
        guard status.isAvailable else { return "iCloud: unavailable" }
        if let lastSync = status.lastSyncAttempt {
            return "iCloud sync \(formatRelativeTime(lastSync))"
        }
        return "iCloud: connected"
    }

    func formatRelativeTime(_ timestamp: TimeInterval) -> String {
        let formatter = RelativeDateTimeFormatter()
        formatter.unitsStyle = .short
        let date = Date(timeIntervalSince1970: timestamp)
        return formatter.localizedString(for: date, relativeTo: Date())
    }

    func recordInteractiveResume(sentenceIndex: Int, force: Bool = false) {
        guard !resumeDecisionPending else { return }
        guard let userId = resumeUserId else { return }
        guard sentenceIndex > 0 else { return }
        if !force, sentenceIndex == lastRecordedSentence {
            return
        }
        lastRecordedSentence = sentenceIndex
        let entry = PlaybackResumeEntry(
            jobId: currentJob.jobId,
            itemType: resumeItemType,
            kind: .sentence,
            updatedAt: Date().timeIntervalSince1970,
            sentenceNumber: sentenceIndex,
            playbackTime: nil
        )
        PlaybackResumeStore.shared.updateEntry(entry, userId: userId)
    }

    @discardableResult
    func recordVideoResume(time: Double, isPlaying: Bool) -> Bool {
        guard !resumeDecisionPending else { return false }
        guard let userId = resumeUserId else { return false }
        guard time.isFinite, time >= 0 else { return false }
        if !isPlaying, time < 1, lastVideoTime > 5 {
            return false
        }
        lastVideoTime = time
        let bucket = Int(time / 5)
        if bucket == lastRecordedTimeBucket, isPlaying {
            return true
        }
        lastRecordedTimeBucket = bucket
        let entry = PlaybackResumeEntry(
            jobId: currentJob.jobId,
            itemType: resumeItemType,
            kind: .time,
            updatedAt: Date().timeIntervalSince1970,
            sentenceNumber: nil,
            playbackTime: time
        )
        PlaybackResumeStore.shared.updateEntry(entry, userId: userId)
        return true
    }

    func persistResumeOnExit() {
        if isVideoPreferred {
            recordVideoResume(time: lastVideoTime, isPlaying: false)
        } else if let sentenceIndex {
            recordInteractiveResume(sentenceIndex: sentenceIndex, force: true)
        }
        if let userId = resumeUserId {
            Task {
                await PlaybackResumeStore.shared.syncNow(userId: userId, aliases: appState.resumeUserAliases)
            }
        }
    }

    func resolveResumeSentenceIndex(at highlightTime: Double) -> Int? {
        guard let chunk = viewModel.selectedChunk else { return nil }
        let duration = viewModel.playbackDuration(for: chunk) ?? viewModel.audioCoordinator.duration
        return PlaybackSentenceIndexHelpers.resolveResumeSentenceIndex(
            at: highlightTime,
            chunk: chunk,
            activeSentence: viewModel.activeSentence(at: highlightTime),
            playbackDuration: duration
        )
    }
}
