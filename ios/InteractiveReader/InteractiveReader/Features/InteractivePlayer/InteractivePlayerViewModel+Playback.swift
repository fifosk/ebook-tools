import Foundation
import OSLog

private let interactivePlaybackLogger = Logger(subsystem: "InteractiveReader", category: "InteractivePlayback")

extension InteractivePlayerViewModel {
    var highlightingSummary: String? {
        guard let context = jobContext else { return nil }
        if let policy = context.highlightingPolicy?.capitalized, !policy.isEmpty {
            if context.hasEstimatedSegments {
                return "Highlighting policy: \(policy) (estimated segments present)"
            }
            return "Highlighting policy: \(policy)"
        }
        if context.hasEstimatedSegments {
            return "Estimated timings detected"
        }
        return nil
    }

    var chunkCountLabel: String {
        guard let context = jobContext else { return "No chunks" }
        return "Chunks: \(context.chunks.count)"
    }

    var highlightingTime: Double {
        guard let chunk = selectedChunk else {
            return audioCoordinator.currentTime
        }

        // During sequence transitions, use the current segment's start time
        // to prevent stale time values from causing incorrect highlighting
        if sequenceController.isEnabled && sequenceController.isTransitioning {
            if let segment = sequenceController.currentSegment {
                return segment.start
            }
        }

        // Right after a transition ends, use the expected position if available.
        // This provides a stable time value before audioCoordinator.currentTime settles,
        // preventing visual flicker on track switches.
        if sequenceController.isEnabled, let expected = sequenceController.expectedPosition {
            return expected
        }

        // NOTE: Sequence playback updates are now triggered by the time observer
        // in AudioPlayerCoordinator, NOT here. Calling updateSequencePlayback from
        // within a computed property caused side effects during view rendering,
        // leading to flickering on track switches.

        // In sequence mode, use the segment-relative time directly from audioCoordinator
        // The timeline is built per-track (original or translation), so the time should be
        // relative to the current track's segment, not an accumulated elapsed time
        let time: Double
        if isSequenceModeActive {
            // Return the position within the current audio file (segment-relative)
            // The timeline for the current track is built starting from 0 for the current sentence
            time = audioCoordinator.currentTime
        } else if usesCombinedQueue(for: chunk) {
            time = combinedQueuePlaybackTime(for: chunk)
        } else {
            time = playbackTime(for: chunk)
        }
        return time.isFinite ? time : audioCoordinator.currentTime
    }

    func recordAudioDuration(_ duration: Double, for url: URL?) {
        guard let url else { return }
        guard duration.isFinite, duration > 0 else { return }
        audioDurationByURL[url] = duration
    }

    func playbackTime(for chunk: InteractiveChunk) -> Double {
        let baseTime = audioCoordinator.currentTime
        guard let track = selectedAudioOption(for: chunk) else { return baseTime }
        if usesCombinedQueue(for: chunk) {
            return combinedQueuePlaybackTime(for: chunk)
        }
        let urls = track.streamURLs
        guard urls.count > 1,
              let activeURL = audioCoordinator.activeURL,
              let activeIndex = urls.firstIndex(of: activeURL) else {
            return baseTime
        }
        let offset = urls.prefix(activeIndex).reduce(0.0) { partial, url in
            partial + (durationForURL(url, in: chunk) ?? 0)
        }
        return offset + baseTime
    }

    func playbackDuration(for chunk: InteractiveChunk) -> Double? {
        guard let track = selectedAudioOption(for: chunk) else {
            return audioCoordinator.duration > 0 ? audioCoordinator.duration : nil
        }

        // In sequence mode, return total duration of all segments in the plan
        if isSequenceModeActive && track.kind == .combined {
            let plan = sequenceController.plan
            if !plan.isEmpty {
                let totalDuration = plan.reduce(0.0) { $0 + $1.duration }
                if totalDuration > 0 {
                    return totalDuration
                }
            }
            // Fallback to combined track durations
            let originalDuration = combinedTrackDuration(kind: .original, in: chunk)
            let translationDuration = combinedTrackDuration(kind: .translation, in: chunk)
            if let orig = originalDuration, let trans = translationDuration, orig > 0, trans > 0 {
                return orig + trans
            }
            // Fallback to track duration if available
            if let duration = track.duration, duration > 0 {
                return duration
            }
        }

        if track.streamURLs.count == 1 {
            if let activeDuration = activeTrackDuration(for: track) {
                return activeDuration
            }
            if let duration = track.duration, duration > 0 {
                return duration
            }
            if let cached = durationForURL(track.primaryURL, in: chunk), cached > 0 {
                return cached
            }
            return audioCoordinator.duration > 0 ? audioCoordinator.duration : nil
        }
        if useCombinedPhases(for: chunk) {
            let durations = track.streamURLs.map { durationForURL($0, in: chunk) }
            let summed = durations.compactMap { $0 }.reduce(0, +)
            if durations.allSatisfy({ ($0 ?? 0) > 0 }), summed > 0 {
                return summed
            }
            if let fallback = fallbackDuration(for: chunk, kind: .combined), fallback > 0 {
                return fallback
            }
            if let duration = track.duration, duration > 0 {
                return duration
            }
            return summed > 0 ? summed : nil
        }
        if let activeDuration = currentItemDuration(for: track) {
            return activeDuration
        }
        if let activeURL = audioCoordinator.activeURL,
           let activeDuration = durationForURL(activeURL, in: chunk), activeDuration > 0 {
            return activeDuration
        }
        return audioCoordinator.duration > 0 ? audioCoordinator.duration : nil
    }

    func combinedPlaybackDuration(for chunk: InteractiveChunk) -> Double? {
        guard let track = selectedAudioOption(for: chunk) else {
            return playbackDuration(for: chunk)
        }
        guard track.kind == .combined, track.streamURLs.count > 1 else {
            return playbackDuration(for: chunk)
        }
        let originalDuration = combinedTrackDuration(kind: .original, in: chunk)
        let translationDuration = combinedTrackDuration(kind: .translation, in: chunk)
        if let originalDuration, let translationDuration {
            return originalDuration + translationDuration
        }
        if let duration = track.duration, duration > 0 {
            return duration
        }
        if let originalDuration {
            return originalDuration
        }
        if let translationDuration {
            return translationDuration
        }
        let durations = track.streamURLs.map { durationForURL($0, in: chunk) }
        let total = durations.compactMap { $0 }.reduce(0, +)
        if durations.allSatisfy({ ($0 ?? 0) > 0 }), total > 0 {
            return total
        }
        if let fallback = fallbackDuration(for: chunk, kind: .combined), fallback > 0 {
            return fallback
        }
        return total > 0 ? total : nil
    }

    func combinedQueuePlaybackTime(for chunk: InteractiveChunk) -> Double {
        let baseTime = audioCoordinator.currentTime

        // In sequence mode, compute elapsed time through the sequence plan
        // Sum up durations of completed segments + position within current segment
        if isSequenceModeActive {
            let plan = sequenceController.plan
            let currentIndex = sequenceController.currentSegmentIndex

            // Sum durations of all completed segments
            var elapsed: Double = 0
            for i in 0..<currentIndex {
                if plan.indices.contains(i) {
                    elapsed += plan[i].duration
                }
            }

            // Add position within current segment
            if let currentSegment = sequenceController.currentSegment {
                let positionInSegment = max(0, baseTime - currentSegment.start)
                elapsed += min(positionInSegment, currentSegment.duration)
            }

            return elapsed
        }

        guard let track = selectedAudioOption(for: chunk) else { return baseTime }
        guard track.kind == .combined, track.streamURLs.count > 1 else { return baseTime }
        guard let activeURL = audioCoordinator.activeURL,
              let activeIndex = track.streamURLs.firstIndex(of: activeURL) else {
            return baseTime
        }
        guard activeIndex > 0 else { return baseTime }
        let originalDuration = combinedTrackDuration(kind: .original, in: chunk)
            ?? durationForURL(track.streamURLs.first ?? activeURL, in: chunk)
            ?? 0
        return max(0, originalDuration) + baseTime
    }

    func timelineDuration(for chunk: InteractiveChunk) -> Double? {
        guard let track = selectedAudioOption(for: chunk) else {
            return audioCoordinator.duration > 0 ? audioCoordinator.duration : nil
        }
        if track.streamURLs.count > 1 {
            if useCombinedPhases(for: chunk) {
                let durations = track.streamURLs.map { durationForURL($0, in: chunk) }
                let total = durations.compactMap { $0 }.reduce(0, +)
                if durations.allSatisfy({ ($0 ?? 0) > 0 }), total > 0 {
                    return total
                }
                if let fallback = fallbackDuration(for: chunk, kind: .combined), fallback > 0 {
                    return fallback
                }
                return total > 0 ? total : nil
            }
            if let activeDuration = currentItemDuration(for: track) {
                return activeDuration
            }
            if let activeURL = audioCoordinator.activeURL,
               let activeDuration = durationForURL(activeURL, in: chunk), activeDuration > 0 {
                return activeDuration
            }
            return audioCoordinator.duration > 0 ? audioCoordinator.duration : nil
        }
        if let activeDuration = activeTrackDuration(for: track) {
            return activeDuration
        }
        if let duration = track.duration, duration > 0 {
            return duration
        }
        if let cached = durationForURL(track.primaryURL, in: chunk), cached > 0 {
            return cached
        }
        return audioCoordinator.duration > 0 ? audioCoordinator.duration : nil
    }

    func activeTimingTrack(for chunk: InteractiveChunk) -> TextPlayerTimingTrack {
        if let mgr = audioModeManager {
            return mgr.resolveTimingTrack(
                for: chunk,
                selectedTrackID: selectedAudioTrackID,
                sequenceTrack: sequenceController.currentTrack,
                sequenceEnabled: sequenceController.isEnabled,
                activeURL: audioCoordinator.activeURL
            )
        }
        return .translation
    }

    func useCombinedPhases(for chunk: InteractiveChunk) -> Bool {
        guard let track = selectedAudioOption(for: chunk) else { return false }
        guard track.kind == .combined, track.streamURLs.count == 1 else { return false }
        guard let activeURL = audioCoordinator.activeURL else { return true }
        return activeURL == track.primaryURL
    }

    func usesCombinedQueue(for chunk: InteractiveChunk) -> Bool {
        // When sequence mode is active, use per-sentence switching instead of queue
        if isSequenceModeActive {
            return true
        }
        if let audioModeManager, !audioModeManager.isSequenceMode {
            return false
        }
        guard let track = selectedAudioOption(for: chunk) else { return false }
        return track.kind == .combined && track.streamURLs.count > 1
    }

    func fallbackDuration(
        for chunk: InteractiveChunk,
        kind: InteractiveChunk.AudioOption.Kind
    ) -> Double? {
        func sumPhase(
            _ keyPath: KeyPath<ChunkSentencePhaseDurations, Double?>,
            allowTotalFallback: Bool
        ) -> Double? {
            var total = 0.0
            var hasValue = false
            for sentence in chunk.sentences {
                if let phase = sentence.phaseDurations,
                   let value = phase[keyPath: keyPath],
                   value > 0 {
                    total += value
                    hasValue = true
                    continue
                }
                if allowTotalFallback,
                   let totalDuration = sentence.totalDuration,
                   totalDuration > 0 {
                    total += totalDuration
                    hasValue = true
                }
            }
            return hasValue ? total : nil
        }

        switch kind {
        case .original:
            return sumPhase(\.original, allowTotalFallback: false)
        case .translation:
            return sumPhase(\.translation, allowTotalFallback: true)
        case .combined:
            let original = sumPhase(\.original, allowTotalFallback: false)
            let translation = sumPhase(\.translation, allowTotalFallback: true)
            if let original, let translation {
                return original + translation
            }
            return translation ?? original
        case .other:
            return nil
        }
    }

    func seekPlayback(
        to time: Double,
        in chunk: InteractiveChunk,
        completion: ((Bool) -> Void)? = nil
    ) {
        guard let track = selectedAudioOption(for: chunk) else {
            audioCoordinator.seek(to: time, completion: completion)
            return
        }
        let urls = track.streamURLs
        guard urls.count > 1 else {
            audioCoordinator.seek(to: time, completion: completion)
            return
        }
        if !usesCombinedQueue(for: chunk) {
            audioCoordinator.seek(to: time, completion: completion)
            return
        }

        // Use fileDurations from AudioOption if available, otherwise compute from URLs
        let durations: [Double] = {
            if let fileDurations = track.fileDurations, fileDurations.count == urls.count {
                return fileDurations
            }
            return urls.map { durationForURL($0, in: chunk) ?? 0 }
        }()

        // Use the new seekAcrossFiles method for cleaner multi-file seeking
        audioCoordinator.seekAcrossFiles(to: time, fileDurations: durations, completion: completion)
    }

    func seekSingleTrackSentence(
        atIndex targetIndex: Int,
        in chunk: InteractiveChunk,
        timelineSentences: [TimelineSentenceRuntime]? = nil,
        autoPlay: Bool
    ) {
        guard chunk.sentences.indices.contains(targetIndex),
              let targetTime = startTimeForSentence(
                atIndex: targetIndex,
                in: chunk,
                timelineSentences: timelineSentences
        ) else {
            return
        }
        cancelPendingAudioReadySubscription()
        let token = currentTransitionToken
        rememberSingleTrackSentenceAnchor(in: chunk, targetIndex: targetIndex)
        audioCoordinator.setVolume(0)
        seekPlayback(to: targetTime, in: chunk) { [weak self] _ in
            guard let self else { return }
            guard self.selectedChunkID == chunk.id else { return }
            guard token == self.currentTransitionToken else {
                interactivePlaybackLogger.debug(
                    "Single-track sentence seek: ignoring stale completion token=\(token, privacy: .public), current=\(self.currentTransitionToken, privacy: .public)"
                )
                return
            }
            let observed = self.audioCoordinator.currentTime
            if abs(observed - targetTime) > 0.1 {
                interactivePlaybackLogger.debug(
                    "Single-track sentence seek: drift observed=\(String(format: "%.3f", observed), privacy: .public), expected=\(String(format: "%.3f", targetTime), privacy: .public), re-seeking"
                )
                self.seekPlayback(to: targetTime, in: chunk) { [weak self] _ in
                    guard let self else { return }
                    guard self.selectedChunkID == chunk.id else { return }
                    guard token == self.currentTransitionToken else { return }
                    self.finalizeSingleTrackSentenceSeek(
                        targetIndex: targetIndex,
                        in: chunk,
                        autoPlay: autoPlay
                    )
                }
                return
            }
            self.finalizeSingleTrackSentenceSeek(
                targetIndex: targetIndex,
                in: chunk,
                autoPlay: autoPlay
            )
        }
    }

    private func finalizeSingleTrackSentenceSeek(
        targetIndex: Int,
        in chunk: InteractiveChunk,
        autoPlay: Bool
    ) {
        rememberSingleTrackSentenceAnchor(in: chunk, targetIndex: targetIndex)
        audioCoordinator.restoreVolume()
        if autoPlay && !audioCoordinator.isPlaying {
            audioCoordinator.play()
        }
    }

    func activeSentence(at time: Double) -> InteractiveChunk.Sentence? {
        guard time.isFinite else { return nil }
        guard let chunk = selectedChunk else { return nil }
        let playbackDuration = playbackDuration(for: chunk)
        if let activeIndex = TextPlayerTimeline.resolveActiveIndex(
            sentences: chunk.sentences,
            activeTimingTrack: activeTimingTrack(for: chunk),
            chunkTime: time,
            audioDuration: playbackDuration,
            useCombinedPhases: useCombinedPhases(for: chunk)
        ),
        chunk.sentences.indices.contains(activeIndex) {
            return chunk.sentences[activeIndex]
        }
        if let match = chunk.sentences.first(where: { $0.contains(time: time) }) {
            return match
        }
        let sorted = chunk.sentences
            .compactMap { sentence -> (InteractiveChunk.Sentence, Double)? in
                guard let start = sentence.startTime else { return nil }
                return (sentence, start)
            }
            .sorted { $0.1 < $1.1 }
        return sorted.last(where: { $0.1 <= time })?.0
    }

    func skipSentence(
        forward: Bool,
        preferredTrack: SequenceTrack? = nil,
        anchorSentenceNumber: Int? = nil
    ) {
        guard let chunk = selectedChunk else { return }

        // In sequence mode, use sentence-level navigation (skip both tracks per sentence)
        if isSequenceModeActive {
            skipSentenceInSequenceMode(
                forward: forward,
                chunk: chunk,
                preferredTrack: preferredTrack,
                anchorSentenceNumber: anchorSentenceNumber
            )
            return
        }

        let currentTime = highlightingTime.isFinite ? highlightingTime : audioCoordinator.currentTime
        guard currentTime.isFinite else { return }
        let activeTimingTrack = activeTimingTrack(for: chunk)
        let playbackDuration = playbackDuration(for: chunk)
        let useCombinedPhases = useCombinedPhases(for: chunk)
        let timelineSentences = TextPlayerTimeline.buildTimelineSentences(
            sentences: chunk.sentences,
            activeTimingTrack: activeTimingTrack,
            audioDuration: playbackDuration,
            useCombinedPhases: useCombinedPhases,
            timingVersion: chunk.timingVersion
        )
        guard !chunk.sentences.isEmpty else {
            if let targetSentence = adjacentSentenceNumber(
                from: anchorSentenceNumber,
                forward: forward
            ) {
                jumpToSentence(targetSentence, autoPlay: audioCoordinator.isPlaybackRequested)
                return
            }
            if forward {
                if let nextChunk = jobContext?.nextChunk(after: chunk.id) {
                    selectChunk(id: nextChunk.id, autoPlay: audioCoordinator.isPlaybackRequested)
                }
            } else {
                if let previousChunk = jobContext?.previousChunk(before: chunk.id) {
                    // When skipping backward, start from the last sentence of the previous chunk
                    selectChunk(id: previousChunk.id, autoPlay: audioCoordinator.isPlaybackRequested, targetSentenceIndex: -1)
                }
            }
            return
        }

        let anchoredIndex = anchorSentenceNumber.flatMap {
            SentencePositionProvider.sentenceIndex(in: chunk, matching: $0)
        } ?? recentSingleTrackSentenceAnchorIndex(in: chunk)
        let resolvedActiveIndex = anchoredIndex ?? activeSentenceIndex(
            in: chunk,
            at: currentTime,
            timelineSentences: timelineSentences,
            playbackDuration: playbackDuration
        )

        guard let activeIndex = resolvedActiveIndex else {
            let boundaryIndex = forward ? 0 : max(0, chunk.sentences.count - 1)
            if let boundaryTime = startTimeForSentence(
                atIndex: boundaryIndex,
                in: chunk,
                timelineSentences: timelineSentences
            ) {
                seekPlayback(to: boundaryTime, in: chunk)
                return
            }
            if forward {
                if let nextChunk = jobContext?.nextChunk(after: chunk.id) {
                    selectChunk(id: nextChunk.id, autoPlay: audioCoordinator.isPlaybackRequested)
                }
            } else if let previousChunk = jobContext?.previousChunk(before: chunk.id) {
                selectChunk(id: previousChunk.id, autoPlay: audioCoordinator.isPlaybackRequested, targetSentenceIndex: -1)
            }
            return
        }

        if forward {
            let targetIndex = activeIndex + 1
            if chunk.sentences.indices.contains(targetIndex) {
                seekSingleTrackSentence(
                    atIndex: targetIndex,
                    in: chunk,
                    timelineSentences: timelineSentences,
                    autoPlay: audioCoordinator.isPlaybackRequested
                )
                return
            }
            if let nextChunk = jobContext?.nextChunk(after: chunk.id) {
                selectChunk(id: nextChunk.id, autoPlay: audioCoordinator.isPlaybackRequested)
            }
        } else {
            let targetIndex = activeIndex - 1
            if chunk.sentences.indices.contains(targetIndex) {
                seekSingleTrackSentence(
                    atIndex: targetIndex,
                    in: chunk,
                    timelineSentences: timelineSentences,
                    autoPlay: audioCoordinator.isPlaybackRequested
                )
                return
            }
            if let previousChunk = jobContext?.previousChunk(before: chunk.id) {
                // When skipping backward, start from the last sentence of the previous chunk
                selectChunk(id: previousChunk.id, autoPlay: audioCoordinator.isPlaybackRequested, targetSentenceIndex: -1)
            }
        }
    }

    private func adjacentSentenceNumber(from anchorSentenceNumber: Int?, forward: Bool) -> Int? {
        guard let anchorSentenceNumber else { return nil }
        let target = anchorSentenceNumber + (forward ? 1 : -1)
        guard target > 0 else { return nil }
        if let context = jobContext,
           resolveChunk(containing: target, in: context) == nil {
            return nil
        }
        return target
    }

    private func activeSentenceIndex(
        in chunk: InteractiveChunk,
        at time: Double,
        timelineSentences: [TimelineSentenceRuntime]?,
        playbackDuration: Double?
    ) -> Int? {
        let activeTimingTrack = activeTimingTrack(for: chunk)
        let useCombinedPhases = useCombinedPhases(for: chunk)
        if let activeIndex = TextPlayerTimeline.resolveActiveIndex(
            sentences: chunk.sentences,
            activeTimingTrack: activeTimingTrack,
            chunkTime: time,
            audioDuration: playbackDuration,
            useCombinedPhases: useCombinedPhases
        ),
        chunk.sentences.indices.contains(activeIndex) {
            return activeIndex
        }
        if let timelineSentences,
           let activeIndex = TextPlayerTimeline.resolveActiveIndex(
               timelineSentences: timelineSentences,
               chunkTime: time,
               audioDuration: playbackDuration
           ),
           chunk.sentences.indices.contains(activeIndex) {
            return activeIndex
        }
        if let activeSentence = activeSentence(at: time),
           let index = chunk.sentences.firstIndex(where: { $0.id == activeSentence.id }) {
            return index
        }
        return nearestSentenceIndex(in: chunk, at: time, timelineSentences: timelineSentences)
    }

    private func nearestSentenceIndex(
        in chunk: InteractiveChunk,
        at time: Double,
        timelineSentences: [TimelineSentenceRuntime]?
    ) -> Int? {
        if let timelineSentences, !timelineSentences.isEmpty {
            let sorted = timelineSentences.sorted { $0.startTime < $1.startTime }
            return sorted.last(where: { $0.startTime <= time })?.index ?? sorted.first?.index
        }
        let sorted = chunk.sentences.enumerated()
            .compactMap { index, sentence -> (index: Int, startTime: Double)? in
                guard let startTime = sentence.startTime else { return nil }
                return (index, startTime)
            }
            .sorted { $0.startTime < $1.startTime }
        return sorted.last(where: { $0.startTime <= time })?.index ?? sorted.first?.index
    }

    private func startTimeForSentence(
        atIndex index: Int,
        in chunk: InteractiveChunk,
        timelineSentences: [TimelineSentenceRuntime]?
    ) -> Double? {
        guard chunk.sentences.indices.contains(index) else { return nil }
        if !useCombinedPhases(for: chunk),
           let gate = gateStartTimeForSentence(
               atIndex: index,
               in: chunk,
               activeTimingTrack: activeTimingTrack(for: chunk)
           ) {
            return gate
        }
        if let timelineSentences,
           let runtime = timelineSentences.first(where: { $0.index == index }) {
            return runtime.startTime
        }
        return startTimeForSentence(atIndex: index, in: chunk)
    }

    /// Skip to the next/previous sequence segment.
    /// - Parameters:
    ///   - forward: Whether to skip forward (true) or backward (false)
    ///   - chunk: The current chunk
    ///   - preferredTrack: Kept for call-site compatibility; sequence order decides the target.
    private func skipSentenceInSequenceMode(
        forward: Bool,
        chunk: InteractiveChunk,
        preferredTrack: SequenceTrack? = nil,
        anchorSentenceNumber: Int? = nil
    ) {
        // Find the target FIRST, without updating state yet
        // This allows us to fire the callback with the OLD state still in place
        let target: (segmentIndex: Int, track: SequenceTrack, time: Double)?
        if let anchoredTarget = sequenceSentenceTarget(
            forward: forward,
            from: anchorSentenceNumber,
            in: chunk,
            preferredTrack: preferredTrack
        ) {
            target = anchoredTarget
        } else if forward {
            target = sequenceController.nextSentenceTarget(preferredTrack: preferredTrack)
        } else {
            target = sequenceController.previousSentenceTarget(preferredTrack: preferredTrack)
        }

        guard let target else {
            // No more sentences in this direction, try next/previous chunk
            if forward {
                if let nextChunk = jobContext?.nextChunk(after: chunk.id) {
                    selectChunk(id: nextChunk.id, autoPlay: audioCoordinator.isPlaybackRequested)
                }
            } else {
                if let previousChunk = jobContext?.previousChunk(before: chunk.id) {
                    // When skipping backward to previous chunk, start from the LAST sentence
                    selectChunk(id: previousChunk.id, autoPlay: audioCoordinator.isPlaybackRequested, targetSentenceIndex: -1)
                }
            }
            return
        }

        interactivePlaybackLogger.debug(
            "Skipping to \(forward ? "next" : "previous", privacy: .public) sentence: track=\(target.track.rawValue, privacy: .public), time=\(target.time, privacy: .public)"
        )

        // Check if we need to switch tracks BEFORE committing state
        let needsTrackSwitch = target.track != sequenceController.currentTrack

        // Mute immediately to prevent audio bleed during the transition
        audioCoordinator.setVolume(0)

        // Fire pre-transition callback BEFORE updating any state
        // This allows the view to freeze with the current (old) sentence displayed
        onSequenceWillTransition?()
        sequenceController.beginTransition()

        // NOW commit the state change
        sequenceController.commitSentenceTarget(target)

        // Handle track switch if needed, otherwise just seek
        if needsTrackSwitch {
            // handleSequenceTrackSwitch will load new audio and seek
            handleSequenceTrackSwitch(
                track: target.track,
                seekTime: target.time,
                shouldPlay: audioCoordinator.isPlaybackRequested
            )
        } else {
            // Same track, just seek - mute during seek to prevent audio bleed
            // NOTE: We don't pause here to avoid triggering reading bed pause
            let wasPlaying = audioCoordinator.isPlaying
            audioCoordinator.setVolume(0)
            audioCoordinator.seek(to: target.time) { [weak self] _ in
                guard let self else { return }
                // Small delay after seek completes to ensure proper rendering
                DispatchQueue.main.asyncAfter(deadline: .now() + 0.05) { [weak self] in
                    guard let self else { return }
                    self.sequenceController.endTransition(expectedTime: target.time)
                    // Restore volume to target level (respects music mix setting)
                    self.audioCoordinator.restoreVolume()
                    // Resume playback if it was playing (in case seek caused a pause)
                    if wasPlaying,
                       self.audioCoordinator.isPlaybackRequested,
                       !self.audioCoordinator.isPlaying {
                        self.audioCoordinator.play()
                    }
                }
            }
        }
    }

    private func sequenceSentenceTarget(
        forward: Bool,
        from anchorSentenceNumber: Int?,
        in chunk: InteractiveChunk,
        preferredTrack: SequenceTrack?
    ) -> (segmentIndex: Int, track: SequenceTrack, time: Double)? {
        guard let anchorSentenceNumber,
              let anchorIndex = SentencePositionProvider.sentenceIndex(
                in: chunk,
                matching: anchorSentenceNumber
              ) else {
            return nil
        }
        let orderedIndices = sequenceController.sentenceIndices
        let candidates: [Int]
        if forward {
            candidates = orderedIndices.filter { $0 > anchorIndex }
        } else {
            candidates = Array(orderedIndices.filter { $0 < anchorIndex }.reversed())
        }
        for candidate in candidates {
            if let target = sequenceController.findSentenceTarget(
                candidate,
                preferredTrack: preferredTrack ?? audioModeManager?.preferredTrack
            ) {
                return target
            }
        }
        return nil
    }

    func seekSequencePlayback(
        segmentIndex: Int,
        track: SequenceTrack,
        time: Double,
        autoPlay: Bool
    ) {
        guard time.isFinite, sequenceController.plan.indices.contains(segmentIndex) else { return }
        let target = (segmentIndex: segmentIndex, track: track, time: time)
        let needsTrackSwitch = track != sequenceController.currentTrack

        audioCoordinator.setVolume(0)
        cancelPendingAudioReadySubscription()
        let token = currentTransitionToken
        onSequenceWillTransition?()
        sequenceController.beginTransition()
        sequenceController.commitTokenSeekTarget(target)

        if needsTrackSwitch {
            handleSequenceTrackSwitch(track: track, seekTime: time, shouldPlay: autoPlay)
            return
        }

        audioCoordinator.seek(to: time) { [weak self] _ in
            guard let self else { return }
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.05) { [weak self] in
                guard let self else { return }
                guard token == self.currentTransitionToken else {
                    interactivePlaybackLogger.debug(
                        "Token sequence seek: ignoring stale same-track completion token=\(token, privacy: .public), current=\(self.currentTransitionToken, privacy: .public)"
                    )
                    return
                }
                let observed = self.audioCoordinator.currentTime
                let drift = abs(observed - time)
                if drift > 0.1 {
                    interactivePlaybackLogger.debug(
                        "Token sequence seek: same-track drift observed=\(String(format: "%.3f", observed), privacy: .public), expected=\(String(format: "%.3f", time), privacy: .public), re-seeking"
                    )
                    self.audioCoordinator.seek(to: time) { [weak self] _ in
                        guard let self else { return }
                        guard token == self.currentTransitionToken else { return }
                        self.finalizeSameTrackTokenSeek(at: time, autoPlay: autoPlay)
                    }
                    return
                }
                self.finalizeSameTrackTokenSeek(at: time, autoPlay: autoPlay)
            }
        }
    }

    private func finalizeSameTrackTokenSeek(at time: Double, autoPlay: Bool) {
        sequenceController.endTransition(expectedTime: time)
        audioCoordinator.restoreVolume()
        if autoPlay {
            if !audioCoordinator.isPlaying {
                audioCoordinator.play()
            }
        } else if audioCoordinator.isPlaying {
            audioCoordinator.pause()
        }
    }

    func selectedAudioOption(for chunk: InteractiveChunk) -> InteractiveChunk.AudioOption? {
        guard let selectedID = selectedAudioTrackID else {
            return chunk.audioOptions.first
        }
        return chunk.audioOptions.first(where: { $0.id == selectedID }) ?? chunk.audioOptions.first
    }

    func durationForURL(_ url: URL, in chunk: InteractiveChunk) -> Double? {
        let matchingOptions = chunk.audioOptions.filter { $0.primaryURL == url }
        if let option = matchingOptions.first(where: { $0.kind != .combined }), let duration = option.duration, duration > 0 {
            return duration
        }
        if let option = matchingOptions.first, let duration = option.duration, duration > 0 {
            return duration
        }
        if let option = matchingOptions.first,
           let fallback = fallbackDuration(for: chunk, kind: option.kind),
           fallback > 0 {
            return fallback
        }
        if let cached = audioDurationByURL[url], cached > 0 {
            return cached
        }
        return nil
    }

    func durationForOption(
        kind: InteractiveChunk.AudioOption.Kind,
        in chunk: InteractiveChunk
    ) -> Double? {
        guard let option = chunk.audioOptions.first(where: { $0.kind == kind }) else {
            return nil
        }
        if let duration = option.duration, duration > 0 {
            return duration
        }
        return nil
    }

    func combinedTrackDuration(
        kind: InteractiveChunk.AudioOption.Kind,
        in chunk: InteractiveChunk
    ) -> Double? {
        guard let option = chunk.audioOptions.first(where: { $0.kind == kind }) else {
            return nil
        }
        if let duration = option.duration, duration > 0 {
            return duration
        }
        let total = chunk.sentences.reduce(0.0) { partial, sentence in
            let value: Double? = {
                switch kind {
                case .original:
                    return sentence.phaseDurations?.original
                case .translation:
                    return sentence.phaseDurations?.translation
                case .combined, .other:
                    return nil
                }
            }()
            guard let value, value > 0 else { return partial }
            return partial + value
        }
        if total > 0 {
            return total
        }
        if let fallback = fallbackDuration(for: chunk, kind: kind), fallback > 0 {
            return fallback
        }
        if let cached = audioDurationByURL[option.primaryURL], cached > 0 {
            return cached
        }
        return nil
    }

    func activeTrackDuration(for track: InteractiveChunk.AudioOption) -> Double? {
        guard track.streamURLs.count == 1,
              let activeURL = audioCoordinator.activeURL,
              activeURL == track.primaryURL else {
            return nil
        }
        let duration = audioCoordinator.duration
        guard duration.isFinite, duration > 0 else { return nil }
        return duration
    }

    func currentItemDuration(for track: InteractiveChunk.AudioOption) -> Double? {
        guard let activeURL = audioCoordinator.activeURL,
              track.streamURLs.contains(activeURL) else {
            return nil
        }
        let duration = audioCoordinator.duration
        guard duration.isFinite, duration > 0 else { return nil }
        return duration
    }
}
