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
        pendingInteractiveAutoplaySentence = nil
        lastRecordedSentence = nil
        lastRecordedSentenceTimeBucket = nil
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
            startInteractivePlayback(at: firstInteractiveSentenceNumber())
        }
    }

    func applyResume(_ entry: PlaybackResumeEntry) {
        resumeDecisionPending = false
        if isVideoPreferred {
            startVideoPlayback(at: entry.playbackTime, presentPlayer: true)
        } else {
            startInteractivePlayback(
                at: entry.sentenceNumber,
                playbackTime: entry.playbackTime,
                preferredTrack: entry.resumeSequenceTrack
            )
        }
    }

    func startInteractivePlayback(
        at sentence: Int?,
        playbackTime: Double? = nil,
        preferredTrack: SequenceTrack? = nil
    ) {
        let resolvedSentence = resolvedInteractiveStartSentence(sentence)
        viewModel.prepareResumeSingleTrack(preferredTrack)
        if let sentence = resolvedSentence, sentence > 0 {
            pendingInteractiveAutoplayID = UUID()
            pendingInteractiveAutoplaySentence = sentence
            if let resumeTime = validatedInteractiveResumePlaybackTime(playbackTime, sentenceNumber: sentence) {
                playbackTransportDebugLog(
                    "[PlaybackTransport] Job resume offset requested sentence=\(sentence) time=\(String(format: "%.3f", resumeTime.time)) sequence=\(viewModel.isSequenceModeActive)"
                )
                viewModel.jumpToTime(
                    resumeTime.time,
                    in: resumeTime.chunk,
                    autoPlay: true,
                    matchingSentenceNumber: sentence,
                    preferredTrack: preferredTrack
                )
            } else {
                if let playbackTime, playbackTime.isFinite {
                    playbackTransportDebugLog(
                        "[PlaybackTransport] Job resume offset fallback=sentenceStart sentence=\(sentence) time=\(String(format: "%.3f", playbackTime))"
                    )
                }
                // jumpToSentence with autoPlay: true handles seeking and starting playback
                // after the audio is loaded and seeked to the target position.
                // Do NOT call play() here as it would start playback from position 0
                // before the async seek operation completes.
                viewModel.jumpToSentence(sentence, autoPlay: true)
            }
            resumeAppleMusicBedAfterInteractiveStartIfNeeded()
            scheduleInteractiveAutoplayRetry(
                sentence: sentence,
                requestID: pendingInteractiveAutoplayID,
                playbackTime: playbackTime,
                preferredTrack: preferredTrack
            )
        } else {
            // No sentence target - start playback from current position
            pendingInteractiveAutoplaySentence = nil
            if !viewModel.audioCoordinator.isPlaying {
                viewModel.audioCoordinator.play()
            }
            resumeAppleMusicBedAfterInteractiveStartIfNeeded()
        }
    }

    func resumeAppleMusicBedAfterInteractiveStartIfNeeded() {
        guard musicOwnership.ownershipState == .appleMusicBed else { return }
        guard lastReaderTransportAction != "play" else { return }
        #if os(tvOS)
        #if DEBUG
        e2eTVInteractiveMusicDeferredResumeCount += 1
        #endif
        resumeAppleMusicBedFromReaderTransportIfNeeded(deferUntilReaderActive: true)
        #else
        musicOwnership.resumeReadingBedForReaderTransport()
        #endif
    }

    func scheduleInteractiveAutoplayRetry(
        sentence: Int,
        requestID: UUID?,
        playbackTime: Double? = nil,
        preferredTrack: SequenceTrack? = nil
    ) {
        guard let requestID else { return }
        keyboardShortcutDebugLog("[KeyboardShortcut] Job autoplay requested sentence=\(sentence)")
        Task { @MainActor in
            for delay in InteractiveAutoplayRetrySchedule.nanosecondDelays {
                try? await Task.sleep(nanoseconds: delay)
                guard pendingInteractiveAutoplayID == requestID else { return }
                guard viewModel.jobContext != nil else { continue }
                if isInteractiveAutoplaySettled(for: sentence) {
                    #if DEBUG
                    e2eInteractiveAutoplaySettledCount += 1
                    #endif
                    pendingInteractiveAutoplayID = nil
                    pendingInteractiveAutoplaySentence = nil
                    return
                }
                keyboardShortcutDebugLog("[KeyboardShortcut] Job autoplay retry sentence=\(sentence)")
                if let resumeTime = validatedInteractiveResumePlaybackTime(playbackTime, sentenceNumber: sentence) {
                    playbackTransportDebugLog(
                        "[PlaybackTransport] Job resume offset retry sentence=\(sentence) time=\(String(format: "%.3f", resumeTime.time)) sequence=\(viewModel.isSequenceModeActive)"
                    )
                    viewModel.jumpToTime(
                        resumeTime.time,
                        in: resumeTime.chunk,
                        autoPlay: true,
                        matchingSentenceNumber: sentence,
                        preferredTrack: preferredTrack
                    )
                } else {
                    viewModel.jumpToSentence(sentence, autoPlay: true)
                }
            }
        }
    }

    func isInteractiveAutoplaySettled(for sentence: Int) -> Bool {
        guard viewModel.audioCoordinator.isPlaying else { return false }
        guard let chunk = viewModel.selectedChunk,
              let targetIndex = SentencePositionProvider.sentenceIndex(in: chunk, matching: sentence)
        else { return false }
        if let resolvedSentence = resolveResumeSentenceIndex(at: viewModel.highlightingTime) {
            return resolvedSentence == sentence
        }
        if viewModel.isSequenceModeActive,
           viewModel.sequenceController.currentSegment?.sentenceIndex == targetIndex {
            return true
        }
        return false
    }

    func firstInteractiveSentenceNumber() -> Int? {
        guard let context = viewModel.jobContext else { return nil }
        for chunk in context.chunks {
            if let sentence = chunk.sentences.first {
                return SentencePositionProvider.sentenceNumber(for: sentence)
            }
            if let start = chunk.startSentence, start > 0 {
                return start
            }
        }
        return nil
    }

    func resolvedInteractiveStartSentence(_ sentence: Int?) -> Int? {
        guard let context = viewModel.jobContext else { return sentence }
        if let sentence, sentence > 0,
           viewModel.resolveChunk(containing: sentence, in: context) != nil {
            return sentence
        }
        return firstInteractiveSentenceNumber()
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
            if let time = entry.playbackTime, time.isFinite, time > 1 {
                return "Continue from sentence \(sentence) at \(formatPlaybackTime(time)).\n\(iCloudNote)"
            }
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

    func recordInteractiveResume(
        sentenceIndex: Int,
        playbackTime: Double? = nil,
        playbackTrack: String? = nil,
        force: Bool = false
    ) {
        guard !resumeDecisionPending else { return }
        guard let userId = resumeUserId else { return }
        guard sentenceIndex > 0 else { return }
        let normalizedPlaybackTime = normalizedInteractiveResumePlaybackTime(playbackTime)
        let timeBucket = normalizedPlaybackTime.map { Int($0.rounded(.down)) }
        if !force,
           sentenceIndex == lastRecordedSentence,
           timeBucket == lastRecordedSentenceTimeBucket,
           playbackTrack == lastRecordedSentenceTrack {
            return
        }
        lastRecordedSentence = sentenceIndex
        lastRecordedSentenceTimeBucket = timeBucket
        lastRecordedSentenceTrack = playbackTrack
        let entry = PlaybackResumeEntry(
            jobId: currentJob.jobId,
            itemType: resumeItemType,
            kind: .sentence,
            updatedAt: Date().timeIntervalSince1970,
            sentenceNumber: sentenceIndex,
            playbackTime: normalizedPlaybackTime,
            playbackTrack: playbackTrack
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
            playbackTime: time,
            playbackTrack: nil
        )
        PlaybackResumeStore.shared.updateEntry(entry, userId: userId)
        return true
    }

    func persistResumeOnExit() {
        if isVideoPreferred {
            recordVideoResume(time: lastVideoTime, isPlaying: false)
        } else if let sentenceIndex {
            recordInteractiveResume(
                sentenceIndex: sentenceIndex,
                playbackTime: currentInteractiveResumePlaybackTime(),
                playbackTrack: currentInteractiveResumePlaybackTrack(),
                force: true
            )
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

    func currentInteractiveResumePlaybackTime() -> Double? {
        let highlightTime = viewModel.highlightingTime
        let playerTime = viewModel.audioCoordinator.currentTime
        if !viewModel.isSequenceModeActive, playerTime.isFinite, playerTime >= 0 {
            if playerTime > 0 || !highlightTime.isFinite || highlightTime < 0 {
                return playerTime
            }
        }
        guard highlightTime.isFinite, highlightTime >= 0 else { return nil }
        return highlightTime
    }

    func currentInteractiveResumePlaybackTrack() -> String? {
        if viewModel.isSequenceModeActive {
            return nil
        }
        return viewModel.audioModeManager?.preferredTrack.rawValue
    }

    func normalizedInteractiveResumePlaybackTime(_ time: Double?) -> Double? {
        guard let time, time.isFinite, time >= 0 else { return nil }
        return time
    }

    func validatedInteractiveResumePlaybackTime(
        _ playbackTime: Double?,
        sentenceNumber: Int
    ) -> (time: Double, chunk: InteractiveChunk)? {
        guard let time = normalizedInteractiveResumePlaybackTime(playbackTime),
              let context = viewModel.jobContext,
              let chunk = viewModel.resolveChunk(containing: sentenceNumber, in: context),
              viewModel.resumePlaybackTime(time, matches: sentenceNumber, in: chunk) else {
            return nil
        }
        return (time, chunk)
    }
}
