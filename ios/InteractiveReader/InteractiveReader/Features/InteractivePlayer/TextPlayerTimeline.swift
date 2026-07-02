import Foundation

enum TextPlayerTimeline {
    static let tokenDuration = 0.35
    static let fallbackSentenceDuration = 0.5

    struct SentenceTimingComponents {
        let isOriginalTrack: Bool
        let originalPhaseDuration: Double
        let gapBeforeTranslation: Double
        let tailPhaseDuration: Double
        let translationPhaseDuration: Double
        let translationSpeechDuration: Double
        let translationTotalDuration: Double
        let translationTrackStartOffset: Double
        let highlightOriginal: Bool
        let duration: Double
    }

    struct ActiveSentenceResolution {
        let index: Int
        let sentence: InteractiveChunk.Sentence
        let components: SentenceTimingComponents
        let startTime: Double
        let endTime: Double
        let scale: Double
        let effectiveTime: Double
    }

    static func buildTimelineSentences(
        sentences: [InteractiveChunk.Sentence],
        activeTimingTrack: TextPlayerTimingTrack,
        audioDuration: Double?,
        useCombinedPhases: Bool,
        timingVersion: String? = nil
    ) -> [TimelineSentenceRuntime]? {
        guard !sentences.isEmpty else { return nil }

        // Skip all scaling when timing version is "2" (pre-scaled from backend)
        let skipScaling = timingVersion == "2"

        var offset = 0.0
        var result: [TimelineSentenceRuntime] = []
        var usedAbsoluteOriginalTiming = false
        var usedAbsoluteTranslationTiming = false

        for (index, sentence) in sentences.enumerated() {
            let originalTokens = sentence.originalTokens
            let translationTokens = sentence.translationTokens
            let transliterationTokens = sentence.transliterationTokens
            let events = sentence.timeline
            let isOriginalTrack = activeTimingTrack == .original
            let nextOriginalStartGate = sentences
                .dropFirst(index + 1)
                .compactMap { $0.originalStartGate }
                .first
            let nextTranslationStartGate = sentences
                .dropFirst(index + 1)
                .compactMap { $0.startGate }
                .first

            let phaseDurations = useCombinedPhases ? sentence.phaseDurations : nil
            let originalPhaseDuration: Double = {
                if let value = phaseDurations?.original {
                    return max(value, 0)
                }
                // When on original track with gate timings, use actual audio duration
                if isOriginalTrack,
                   let startGate = sentence.originalStartGate,
                   let endGate = sentence.originalEndGate,
                   endGate > startGate {
                    return endGate - startGate
                }
                if isOriginalTrack,
                   let startGate = sentence.originalStartGate,
                   let nextStart = nextOriginalStartGate,
                   nextStart > startGate {
                    return nextStart - startGate
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

            // When gates are present, use absolute audio position for sentence
            // boundaries even if the backend did not emit per-word timings.
            let useAbsoluteOriginalTiming = isOriginalTrack && sentence.originalStartGate != nil
            let useAbsoluteTranslationTiming = !isOriginalTrack && sentence.startGate != nil
            if useAbsoluteOriginalTiming {
                usedAbsoluteOriginalTiming = true
            }
            if useAbsoluteTranslationTiming {
                usedAbsoluteTranslationTiming = true
            }
            let sentenceStart: Double
            if useAbsoluteOriginalTiming {
                sentenceStart = sentence.originalStartGate ?? offset
            } else if useAbsoluteTranslationTiming {
                sentenceStart = sentence.startGate ?? offset
            } else {
                sentenceStart = offset
            }

            let translationPhaseDuration: Double = {
                if isOriginalTrack {
                    return 0
                }
                if let startGate = sentence.startGate,
                   let endGate = sentence.endGate,
                   endGate > startGate {
                    return endGate - startGate
                }
                if let startGate = sentence.startGate,
                   let nextStart = nextTranslationStartGate,
                   nextStart > startGate {
                    return nextStart - startGate
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

            let translationTrackStart = sentenceStart + (useCombinedPhases ? originalPhaseDuration + gapBeforeTranslation : 0)

            var translationDurationsRaw: [Double] = []
            var prevTranslationCount = 0
            if !isOriginalTrack {
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
                    let perToken = baseDuration / Double(delta)
                    if perToken > 0 {
                        for _ in 0..<delta {
                            translationDurationsRaw.append(perToken)
                        }
                    }
                    prevTranslationCount = nextTranslationCount
                }
            }

            let totalTranslationDurationRaw = translationDurationsRaw.reduce(0, +)
            let translationSpeechDuration = totalTranslationDurationRaw > 0 ? totalTranslationDurationRaw : translationPhaseDuration
            let translationTotalDuration = translationSpeechDuration + tailPhaseDuration
            let translationPhaseEndAbsolute = translationTrackStart + translationTotalDuration

            var translationRevealTimes: [Double] = []
            var translationRevealIsAbsolute = false
            // Use actual translation timing tokens when on the translation track
            // and the sentence has word-level timing data (similar to originalTimingTokens handling)
            if useAbsoluteTranslationTiming || (!isOriginalTrack && skipScaling && !sentence.timingTokens.isEmpty) {
                translationRevealTimes = sentence.timingTokens.map { $0.startTime }
                translationRevealIsAbsolute = true
                // Ensure we have the right number of reveal times
                if translationRevealTimes.count != translationTokens.count && !translationTokens.isEmpty {
                    translationRevealTimes = buildUniformRevealTimes(
                        count: translationTokens.count,
                        startTime: translationTrackStart,
                        duration: translationSpeechDuration
                    )
                    translationRevealIsAbsolute = false
                }
            } else if !isOriginalTrack && !translationDurationsRaw.isEmpty {
                var cumulativeTranslation = 0.0
                for rawDuration in translationDurationsRaw {
                    translationRevealTimes.append(translationTrackStart + cumulativeTranslation)
                    cumulativeTranslation += rawDuration
                }
            }

            if !translationRevealIsAbsolute && !isOriginalTrack && translationRevealTimes.count != translationTokens.count && !translationTokens.isEmpty {
                translationRevealTimes = buildUniformRevealTimes(
                    count: translationTokens.count,
                    startTime: translationTrackStart,
                    duration: translationSpeechDuration
                )
            }

            let transliterationRevealTimes: [Double] = {
                guard !isOriginalTrack, !transliterationTokens.isEmpty else { return [] }
                if translationRevealTimes.isEmpty {
                    return Array(repeating: translationTrackStart, count: transliterationTokens.count)
                }
                if translationRevealTimes.count == 1 {
                    return Array(repeating: translationRevealTimes[0], count: transliterationTokens.count)
                }
                return transliterationTokens.enumerated().map { idx, _ in
                    let ratio = transliterationTokens.count > 1 ? Double(idx) / Double(transliterationTokens.count - 1) : 0
                    let mappedIndex = min(translationRevealTimes.count - 1, Int(round(ratio * Double(translationRevealTimes.count - 1))))
                    return translationRevealTimes[mappedIndex]
                }
            }()

            // Don't override reveal times when they come from actual timing tokens
            // (they're already in audio-file time)
            if !translationRevealIsAbsolute && !isOriginalTrack && !translationRevealTimes.isEmpty {
                translationRevealTimes[0] = translationTrackStart
                translationRevealTimes[translationRevealTimes.count - 1] = translationPhaseEndAbsolute
            }
            var adjustedTransliteration = transliterationRevealTimes
            if !isOriginalTrack && !adjustedTransliteration.isEmpty {
                adjustedTransliteration[0] = translationTrackStart
                adjustedTransliteration[adjustedTransliteration.count - 1] = translationPhaseEndAbsolute
            }

            var originalReveal: [Double] = []
            if highlightOriginal {
                // Use actual original timing tokens when on the original track
                // and the sentence has word-level timing data
                if isOriginalTrack && !sentence.originalTimingTokens.isEmpty {
                    originalReveal = sentence.originalTimingTokens.map { $0.startTime }
                    // Ensure we have the right number of reveal times
                    if originalReveal.count != originalTokens.count && !originalTokens.isEmpty {
                        originalReveal = buildUniformRevealTimes(
                            count: originalTokens.count,
                            startTime: sentenceStart,
                            duration: originalPhaseDuration
                        )
                    }
                } else {
                    originalReveal = buildUniformRevealTimes(
                        count: originalTokens.count,
                        startTime: sentenceStart,
                        duration: originalPhaseDuration
                    )
                }
            }

            let sentenceDuration: Double = {
                if useCombinedPhases {
                    return originalPhaseDuration + gapBeforeTranslation + translationTotalDuration
                }
                if isOriginalTrack {
                    return originalPhaseDuration
                }
                // When using absolute translation timing, use gate-based duration
                if useAbsoluteTranslationTiming,
                   let startGate = sentence.startGate,
                   let endGate = sentence.endGate,
                   endGate > startGate {
                    return endGate - startGate
                }
                return translationTotalDuration
            }()
            let endTime: Double = {
                // When using absolute timing, use the gate end time directly
                if useAbsoluteOriginalTiming,
                   let startGate = sentence.originalStartGate {
                    if let endGate = sentence.originalEndGate, endGate > startGate {
                        return endGate
                    }
                    if let nextStart = nextOriginalStartGate, nextStart > startGate {
                        return nextStart
                    }
                }
                if useAbsoluteTranslationTiming,
                   let startGate = sentence.startGate {
                    if let endGate = sentence.endGate, endGate > startGate {
                        return endGate
                    }
                    if let nextStart = nextTranslationStartGate, nextStart > startGate {
                        return nextStart
                    }
                }
                return sentenceStart + sentenceDuration
            }()

            var variants: [TextPlayerVariantKind: TimelineVariantRuntime] = [:]
            if !originalTokens.isEmpty {
                variants[.original] = TimelineVariantRuntime(tokens: originalTokens, revealTimes: originalReveal)
            }
            if !translationTokens.isEmpty {
                variants[.translation] = TimelineVariantRuntime(tokens: translationTokens, revealTimes: translationRevealTimes)
            }
            if !transliterationTokens.isEmpty {
                variants[.transliteration] = TimelineVariantRuntime(tokens: transliterationTokens, revealTimes: adjustedTransliteration)
            }

            if !variants.isEmpty {
                result.append(
                    TimelineSentenceRuntime(
                        index: index,
                        sentenceNumber: sentence.displayIndex,
                        startTime: sentenceStart,
                        endTime: endTime,
                        variants: variants
                    )
                )
            }

            offset = endTime
        }

        // Skip scaling when:
        // 1. Using timing version 2 (pre-scaled from backend)
        // 2. Using absolute original timing (times are already in audio space)
        // 3. Using absolute translation timing (times are already in audio space)
        // 4. Using combined phases
        if skipScaling {
            return result
        }

        if !useCombinedPhases,
           !usedAbsoluteOriginalTiming,
           !usedAbsoluteTranslationTiming,
           let audioDuration,
           audioDuration > 0,
           let totalTimelineDuration = result.last?.endTime,
           totalTimelineDuration > 0 {
            let scale = audioDuration / totalTimelineDuration
            let scaled = result.map { runtime -> TimelineSentenceRuntime in
                let variants = runtime.variants.mapValues { variant in
                    TimelineVariantRuntime(
                        tokens: variant.tokens,
                        revealTimes: variant.revealTimes.map { $0 * scale }
                    )
                }
                return TimelineSentenceRuntime(
                    index: runtime.index,
                    sentenceNumber: runtime.sentenceNumber,
                    startTime: runtime.startTime * scale,
                    endTime: runtime.endTime * scale,
                    variants: variants
                )
            }
            return scaled
        }

        return result
    }
}
