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
        let time = usesCombinedQueue(for: chunk) ? audioCoordinator.currentTime : playbackTime(for: chunk)
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
        let durations = urls.map { durationForURL($0, in: chunk) ?? 0 }
        var remaining = time
        var targetIndex = 0
        for (index, duration) in durations.enumerated() {
            if duration <= 0 {
                continue
            }
            if remaining <= duration || index == durations.count - 1 {
                targetIndex = index
                break
            }
            remaining -= duration
            targetIndex = index + 1
        }
        if targetIndex >= urls.count {
            targetIndex = urls.count - 1
        }
        let targetURL = urls[targetIndex]
        if audioCoordinator.activeURL != targetURL {
            let subset = Array(urls[targetIndex...])
            audioCoordinator.load(urls: subset, autoPlay: audioCoordinator.isPlaybackRequested)
        }
        audioCoordinator.seek(to: remaining)
    }

    func activeSentence(at time: Double) -> InteractiveChunk.Sentence? {
        guard time.isFinite else { return nil }
        guard let chunk = selectedChunk else { return nil }
        if let timelineSentences = TextPlayerTimeline.buildTimelineSentences(
            sentences: chunk.sentences,
            activeTimingTrack: activeTimingTrack(for: chunk),
            audioDuration: playbackDuration(for: chunk),
            useCombinedPhases: useCombinedPhases(for: chunk)
        ),
        let display = TextPlayerTimeline.buildTimelineDisplay(
            timelineSentences: timelineSentences,
            chunkTime: time,
            audioDuration: playbackDuration(for: chunk)
        ),
        chunk.sentences.indices.contains(display.activeIndex) {
            return chunk.sentences[display.activeIndex]
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

    func skipSentence(forward: Bool) {
        guard let chunk = selectedChunk else { return }
        let currentTime = highlightingTime.isFinite ? highlightingTime : audioCoordinator.currentTime
        guard currentTime.isFinite else { return }
        let epsilon = 0.05
        let sorted: [(Int, Double)] = {
            if let timelineSentences = TextPlayerTimeline.buildTimelineSentences(
                sentences: chunk.sentences,
                activeTimingTrack: activeTimingTrack(for: chunk),
                audioDuration: playbackDuration(for: chunk),
                useCombinedPhases: useCombinedPhases(for: chunk)
            ) {
                return timelineSentences.map { ($0.index, $0.startTime) }.sorted { $0.1 < $1.1 }
            }
            let entries = chunk.sentences.compactMap { sentence -> (Int, Double)? in
                guard let start = sentence.startTime else { return nil }
                return (sentence.id, start)
            }
            return entries.sorted { $0.1 < $1.1 }
        }()

        if sorted.isEmpty {
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
            if let previous = sorted.last(where: { $0.1 < currentTime - epsilon }) {
                seekPlayback(to: previous.1, in: chunk)
                return
            }
            if let previousChunk = jobContext?.previousChunk(before: chunk.id) {
                selectChunk(id: previousChunk.id, autoPlay: audioCoordinator.isPlaybackRequested)
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
