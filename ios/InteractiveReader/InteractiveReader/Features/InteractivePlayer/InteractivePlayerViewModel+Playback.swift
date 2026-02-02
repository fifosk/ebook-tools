import Foundation

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
        // In sequence mode, use the current sequence track for timing
        if isSequenceModeActive {
            switch sequenceController.currentTrack {
            case .original:
                return .original
            case .translation:
                return .translation
            }
        }

        guard let track = selectedAudioOption(for: chunk) else { return .translation }
        switch track.kind {
        case .combined:
            if track.streamURLs.count > 1 {
                if let activeURL = audioCoordinator.activeURL {
                    if activeURL == track.streamURLs.first {
                        return .original
                    }
                    return .translation
                }
                return .original
            }
            return .mix
        case .original:
            return .original
        case .translation:
            return .translation
        case .other:
            return .translation
        }
    }

    func useCombinedPhases(for chunk: InteractiveChunk) -> Bool {
        guard let track = selectedAudioOption(for: chunk) else { return false }
        return track.kind == .combined && track.streamURLs.count == 1
    }

    func usesCombinedQueue(for chunk: InteractiveChunk) -> Bool {
        // When sequence mode is active, use per-sentence switching instead of queue
        if isSequenceModeActive {
            return true
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

    func seekPlayback(to time: Double, in chunk: InteractiveChunk) {
        guard let track = selectedAudioOption(for: chunk) else {
            audioCoordinator.seek(to: time)
            return
        }
        let urls = track.streamURLs
        guard urls.count > 1 else {
            audioCoordinator.seek(to: time)
            return
        }
        if !usesCombinedQueue(for: chunk) {
            audioCoordinator.seek(to: time)
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
        audioCoordinator.seekAcrossFiles(to: time, fileDurations: durations)
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

    func skipSentence(forward: Bool, preferredTrack: SequenceTrack? = nil) {
        guard let chunk = selectedChunk else { return }

        // In sequence mode, use sentence-level navigation (skip both tracks per sentence)
        if isSequenceModeActive {
            skipSentenceInSequenceMode(forward: forward, chunk: chunk, preferredTrack: preferredTrack)
            return
        }

        let currentTime = highlightingTime.isFinite ? highlightingTime : audioCoordinator.currentTime
        guard currentTime.isFinite else { return }
        let epsilon = 0.05
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
        let sorted: [(Int, Double)] = {
            if let timelineSentences {
                return timelineSentences.map { ($0.index, $0.startTime) }.sorted { $0.1 < $1.1 }
            }
            let entries = chunk.sentences.compactMap { sentence -> (Int, Double)? in
                guard let start = sentence.startTime else { return nil }
                return (sentence.id, start)
            }
            return entries.sorted { $0.1 < $1.1 }
        }()

        if sorted.isEmpty {
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

        if forward {
            if let next = sorted.first(where: { $0.1 > currentTime + epsilon }) {
                seekPlayback(to: next.1, in: chunk)
                return
            }
            if let nextChunk = jobContext?.nextChunk(after: chunk.id) {
                selectChunk(id: nextChunk.id, autoPlay: audioCoordinator.isPlaybackRequested)
            }
        } else {
            let anchorTime: Double = {
                if let timelineSentences,
                   let activeIndex = TextPlayerTimeline.resolveActiveIndex(
                       timelineSentences: timelineSentences,
                       chunkTime: currentTime,
                       audioDuration: playbackDuration
                   ),
                   let activeRuntime = timelineSentences.first(where: { $0.index == activeIndex }) {
                    return activeRuntime.startTime - epsilon
                }
                if let activeSentence = activeSentence(at: currentTime),
                   let start = activeSentence.startTime {
                    return start - epsilon
                }
                return currentTime - epsilon
            }()
            if let previous = sorted.last(where: { $0.1 < anchorTime }) {
                seekPlayback(to: previous.1, in: chunk)
                return
            }
            if let previousChunk = jobContext?.previousChunk(before: chunk.id) {
                // When skipping backward, start from the last sentence of the previous chunk
                selectChunk(id: previousChunk.id, autoPlay: audioCoordinator.isPlaybackRequested, targetSentenceIndex: -1)
            }
        }
    }

    /// Skip to next/previous sentence in sequence mode
    /// This navigates by sentence rather than by track segment
    /// - Parameters:
    ///   - forward: Whether to skip forward (true) or backward (false)
    ///   - chunk: The current chunk
    ///   - preferredTrack: The preferred track based on visibility settings. If nil, uses current track.
    private func skipSentenceInSequenceMode(forward: Bool, chunk: InteractiveChunk, preferredTrack: SequenceTrack? = nil) {
        // Find the target FIRST, without updating state yet
        // This allows us to fire the callback with the OLD state still in place
        let target: (segmentIndex: Int, track: SequenceTrack, time: Double)?
        if forward {
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

        print("[Sequence] Skipping to \(forward ? "next" : "previous") sentence: track=\(target.track.rawValue), time=\(String(format: "%.3f", target.time))")

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
            handleSequenceTrackSwitch(track: target.track, seekTime: target.time)
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
                    // Restore volume
                    self.audioCoordinator.setVolume(1)
                    // Resume playback if it was playing (in case seek caused a pause)
                    if wasPlaying && !self.audioCoordinator.isPlaying {
                        self.audioCoordinator.play()
                    }
                }
            }
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
