import Foundation

// MARK: - Private Helpers

extension TextPlayerTimeline {

    static func resolveActiveSentenceResolution(
        sentences: [InteractiveChunk.Sentence],
        activeTimingTrack: TextPlayerTimingTrack,
        chunkTime: Double,
        audioDuration: Double?,
        useCombinedPhases: Bool
    ) -> ActiveSentenceResolution? {
        guard !sentences.isEmpty else { return nil }

        let isOriginalTrack = activeTimingTrack == .original

        // Check if we're using gate-based timing (absolute audio times)
        let useAbsoluteOriginalTiming = isOriginalTrack && sentences.allSatisfy { sentence in
            sentence.originalStartGate != nil
                && sentence.originalEndGate != nil
                && !sentence.originalTimingTokens.isEmpty
        }
        let useAbsoluteTranslationTiming = !isOriginalTrack && sentences.allSatisfy { sentence in
            sentence.startGate != nil
                && sentence.endGate != nil
                && !sentence.timingTokens.isEmpty
        }

        var totalDuration = 0.0
        for sentence in sentences {
            let components = computeSentenceTimingComponents(
                sentence: sentence,
                activeTimingTrack: activeTimingTrack,
                useCombinedPhases: useCombinedPhases
            )
            totalDuration += components.duration
        }

        let audioDurationValue = audioDuration ?? 0
        // Skip scaling when using absolute timing (timeline is already in audio time)
        let shouldScale = !useCombinedPhases && !useAbsoluteOriginalTiming && !useAbsoluteTranslationTiming && audioDurationValue > 0 && totalDuration > 0
        let scale: Double = {
            guard shouldScale else { return 1.0 }
            let computed = audioDurationValue / totalDuration
            guard computed.isFinite, computed > 0 else { return 1.0 }
            return computed
        }()
        let effectiveTime: Double = {
            if shouldScale {
                let scaledTotal = totalDuration * scale
                return min(max(chunkTime, 0), scaledTotal)
            }
            // When using absolute timing, use chunkTime directly (it's already in audio time)
            if useAbsoluteOriginalTiming || useAbsoluteTranslationTiming {
                return max(chunkTime, 0)
            }
            return resolveEffectiveTime(
                timelineTotalDuration: totalDuration,
                chunkTime: chunkTime,
                audioDuration: audioDuration
            )
        }()

        let epsilon = 1e-3
        var offset = 0.0
        var lastPast: ActiveSentenceResolution? = nil
        var firstResolution: ActiveSentenceResolution? = nil

        for (index, sentence) in sentences.enumerated() {
            let components = computeSentenceTimingComponents(
                sentence: sentence,
                activeTimingTrack: activeTimingTrack,
                useCombinedPhases: useCombinedPhases
            )
            // Use absolute gate times when available for the current track
            let startTime: Double
            let endTime: Double
            if useAbsoluteOriginalTiming, let gateStart = sentence.originalStartGate, let gateEnd = sentence.originalEndGate {
                startTime = gateStart
                endTime = gateEnd
            } else if useAbsoluteTranslationTiming, let gateStart = sentence.startGate, let gateEnd = sentence.endGate {
                startTime = gateStart
                endTime = gateEnd
            } else {
                startTime = offset
                endTime = offset + components.duration
            }
            let scaledStart = startTime * scale
            let scaledEnd = endTime * scale
            let resolution = ActiveSentenceResolution(
                index: index,
                sentence: sentence,
                components: components,
                startTime: startTime,
                endTime: endTime,
                scale: scale,
                effectiveTime: effectiveTime
            )
            if firstResolution == nil {
                firstResolution = resolution
            }
            if effectiveTime >= scaledStart - epsilon && effectiveTime <= scaledEnd + epsilon {
                return resolution
            }
            if effectiveTime > scaledEnd + epsilon {
                lastPast = resolution
            }
            // Only update offset for non-absolute timing
            if !useAbsoluteOriginalTiming && !useAbsoluteTranslationTiming {
                offset = endTime
            }
        }

        return lastPast ?? firstResolution
    }

    static func computeSentenceTimingComponents(
        sentence: InteractiveChunk.Sentence,
        activeTimingTrack: TextPlayerTimingTrack,
        useCombinedPhases: Bool
    ) -> SentenceTimingComponents {
        let originalTokens = sentence.originalTokens
        let translationTokens = sentence.translationTokens
        let transliterationTokens = sentence.transliterationTokens
        let events = sentence.timeline
        let isOriginalTrack = activeTimingTrack == .original
        let phaseDurations = useCombinedPhases ? sentence.phaseDurations : nil

        let originalPhaseDuration: Double = {
            if let value = phaseDurations?.original {
                return max(value, 0)
            }
            // When on original track with gate times, use actual audio duration
            if isOriginalTrack,
               let startGate = sentence.originalStartGate,
               let endGate = sentence.originalEndGate,
               endGate > startGate {
                return endGate - startGate
            }
            if !originalTokens.isEmpty {
                return Double(originalTokens.count) * tokenDuration
            }
            return 0
        }()
        let gapBeforeTranslation: Double = {
            if let value = phaseDurations?.gap {
                return max(value, 0)
            }
            return 0
        }()
        let tailPhaseDuration: Double = {
            if let value = phaseDurations?.tail {
                return max(value, 0)
            }
            return 0
        }()
        let translationPhaseDurationOverride: Double? = {
            if let value = phaseDurations?.translation {
                return max(value, 0)
            }
            return nil
        }()
        let highlightOriginal = (useCombinedPhases || isOriginalTrack)
            && !originalTokens.isEmpty
            && originalPhaseDuration > 0

        let eventDurationTotal = events.reduce(0.0) { partial, event in
            let duration = event.duration > 0 ? event.duration : 0
            return partial + duration
        }

        let declaredDuration: Double = {
            if let total = sentence.totalDuration, total > 0 {
                return total
            }
            if eventDurationTotal > 0 {
                return eventDurationTotal
            }
            let fallbackTokens = max(originalTokens.count, max(translationTokens.count, transliterationTokens.count))
            if fallbackTokens > 0 {
                return Double(fallbackTokens) * tokenDuration
            }
            return fallbackSentenceDuration
        }()

        let translationPhaseDuration: Double = {
            if isOriginalTrack {
                return 0
            }
            if let override = translationPhaseDurationOverride, override > 0 {
                return override
            }
            if declaredDuration > 0 {
                return declaredDuration
            }
            if !translationTokens.isEmpty || !transliterationTokens.isEmpty {
                return Double(max(translationTokens.count, transliterationTokens.count)) * tokenDuration
            }
            return fallbackSentenceDuration
        }()

        var totalTranslationDurationRaw = 0.0
        if !isOriginalTrack {
            var prevTranslationCount = 0
            for event in events {
                let baseDuration = event.duration > 0 ? event.duration : 0
                if baseDuration <= 0 {
                    continue
                }
                let targetTranslationIndex = max(0, event.translationIndex)
                let nextTranslationCount = min(
                    translationTokens.count,
                    max(prevTranslationCount, targetTranslationIndex)
                )
                let delta = nextTranslationCount - prevTranslationCount
                if delta <= 0 {
                    continue
                }
                totalTranslationDurationRaw += baseDuration
                prevTranslationCount = nextTranslationCount
            }
        }

        let translationSpeechDuration = totalTranslationDurationRaw > 0
            ? totalTranslationDurationRaw
            : translationPhaseDuration
        let translationTotalDuration = translationSpeechDuration + tailPhaseDuration
        let translationTrackStartOffset = useCombinedPhases
            ? originalPhaseDuration + gapBeforeTranslation
            : 0

        let sentenceDuration: Double = {
            if useCombinedPhases {
                return originalPhaseDuration + gapBeforeTranslation + translationTotalDuration
            }
            if isOriginalTrack {
                return originalPhaseDuration
            }
            return translationTotalDuration
        }()

        return SentenceTimingComponents(
            isOriginalTrack: isOriginalTrack,
            originalPhaseDuration: originalPhaseDuration,
            gapBeforeTranslation: gapBeforeTranslation,
            tailPhaseDuration: tailPhaseDuration,
            translationPhaseDuration: translationPhaseDuration,
            translationSpeechDuration: translationSpeechDuration,
            translationTotalDuration: translationTotalDuration,
            translationTrackStartOffset: translationTrackStartOffset,
            highlightOriginal: highlightOriginal,
            duration: sentenceDuration
        )
    }

    static func resolveEffectiveTime(
        timelineSentences: [TimelineSentenceRuntime],
        chunkTime: Double,
        audioDuration: Double?
    ) -> Double {
        resolveEffectiveTime(
            timelineTotalDuration: timelineSentences.last?.endTime,
            chunkTime: chunkTime,
            audioDuration: audioDuration
        )
    }

    static func resolveEffectiveTime(
        timelineTotalDuration: Double?,
        chunkTime: Double,
        audioDuration: Double?
    ) -> Double {
        return {
            guard let timelineTotalDuration,
                  let audioDuration,
                  audioDuration > 0,
                  timelineTotalDuration > 0 else {
                return max(chunkTime, 0)
            }
            let ratio = timelineTotalDuration / audioDuration
            if ratio > 0.98 && ratio < 1.02 {
                return min(chunkTime, timelineTotalDuration)
            }
            let scaled = (chunkTime / audioDuration) * timelineTotalDuration
            if !scaled.isFinite || scaled < 0 {
                return 0
            }
            return min(scaled, timelineTotalDuration)
        }()
    }

    static func resolveActiveRuntime(
        timelineSentences: [TimelineSentenceRuntime],
        effectiveTime: Double
    ) -> TimelineSentenceRuntime? {
        let epsilon = 1e-3
        for runtime in timelineSentences {
            if effectiveTime >= runtime.startTime - epsilon && effectiveTime <= runtime.endTime + epsilon {
                return runtime
            }
        }
        for runtime in timelineSentences.reversed() {
            if effectiveTime > runtime.endTime + epsilon {
                return runtime
            }
        }
        return timelineSentences.first
    }

    static func buildUniformRevealTimes(count: Int, startTime: Double, duration: Double) -> [Double] {
        let tokenCount = max(0, count)
        guard tokenCount > 0 else { return [] }
        let safeDuration = duration > 0 ? duration : 0
        if safeDuration == 0 {
            return Array(repeating: startTime, count: tokenCount)
        }
        let step = safeDuration / Double(tokenCount)
        var reveals: [Double] = []
        for index in 1...tokenCount {
            let offset = step > 0 ? step * Double(index - 1) : 0
            let reveal = startTime + max(0, min(safeDuration, offset))
            reveals.append(reveal)
        }
        return reveals
    }
}
