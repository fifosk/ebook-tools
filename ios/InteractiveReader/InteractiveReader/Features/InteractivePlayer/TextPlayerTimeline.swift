import Foundation

enum TextPlayerTimingTrack {
    case mix
    case translation
    case original
}

enum TextPlayerVariantKind: String {
    case original
    case translation
    case transliteration
}

enum TextPlayerSentenceState {
    case past
    case active
    case future
}

struct TextPlayerVariantDisplay: Identifiable {
    let id: String
    let label: String
    let tokens: [String]
    let revealedCount: Int
    let currentIndex: Int?
    let kind: TextPlayerVariantKind
    let seekTimes: [Double]?
}

struct TextPlayerSentenceDisplay: Identifiable {
    let id: String
    let index: Int
    let sentenceNumber: Int?
    let state: TextPlayerSentenceState
    let variants: [TextPlayerVariantDisplay]
}

struct TimelineVariantRuntime {
    let tokens: [String]
    let revealTimes: [Double]
}

struct TimelineSentenceRuntime {
    let index: Int
    let sentenceNumber: Int?
    let startTime: Double
    let endTime: Double
    let variants: [TextPlayerVariantKind: TimelineVariantRuntime]
}

struct TimelineDisplay {
    let sentences: [TextPlayerSentenceDisplay]
    let activeIndex: Int
    let effectiveTime: Double
}

enum TextPlayerTimeline {
    private static let tokenDuration = 0.35
    private static let fallbackSentenceDuration = 0.5

    private struct SentenceTimingComponents {
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

    private struct ActiveSentenceResolution {
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

            // When on original track with gate times, use absolute audio position
            let useAbsoluteOriginalTiming = isOriginalTrack
                && sentence.originalStartGate != nil
                && sentence.originalEndGate != nil
                && !sentence.originalTimingTokens.isEmpty
            // When on translation track with gate times, use absolute audio position
            let useAbsoluteTranslationTiming = !isOriginalTrack
                && sentence.startGate != nil
                && sentence.endGate != nil
                && !sentence.timingTokens.isEmpty
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
            if useAbsoluteTranslationTiming {
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
            var originalRevealIsAbsolute = false
            if highlightOriginal {
                // Use actual original timing tokens when on the original track
                // and the sentence has word-level timing data
                if isOriginalTrack && !sentence.originalTimingTokens.isEmpty {
                    originalReveal = sentence.originalTimingTokens.map { $0.startTime }
                    // Mark as absolute audio times (should not be scaled later)
                    originalRevealIsAbsolute = true
                    // Ensure we have the right number of reveal times
                    if originalReveal.count != originalTokens.count && !originalTokens.isEmpty {
                        originalReveal = buildUniformRevealTimes(
                            count: originalTokens.count,
                            startTime: sentenceStart,
                            duration: originalPhaseDuration
                        )
                        originalRevealIsAbsolute = false
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
                if useAbsoluteTranslationTiming, let endGate = sentence.endGate {
                    return endGate
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

    static func buildTimelineDisplay(
        timelineSentences: [TimelineSentenceRuntime],
        chunkTime: Double,
        audioDuration: Double?
    ) -> TimelineDisplay? {
        guard !timelineSentences.isEmpty else { return nil }
        let effectiveTime = resolveEffectiveTime(
            timelineSentences: timelineSentences,
            chunkTime: chunkTime,
            audioDuration: audioDuration
        )
        let activeIndex = resolveActiveRuntime(
            timelineSentences: timelineSentences,
            effectiveTime: effectiveTime
        )?.index
        let epsilon = 1e-3
        // Larger tolerance for "force all revealed" at segment end
        // This should be >= the dwell tolerance (0.1s) used in SequencePlaybackController
        // to ensure last word is revealed during the dwell period before advancing
        let forceRevealTolerance = 0.15

        var displaySentences: [TextPlayerSentenceDisplay] = []

        for runtime in timelineSentences {
            let state: TextPlayerSentenceState = {
                guard let activeIndex else { return .future }
                if runtime.index == activeIndex {
                    return .active
                }
                return runtime.index < activeIndex ? .past : .future
            }()

            var variants: [TextPlayerVariantDisplay] = []

            func appendVariant(label: String, kind: TextPlayerVariantKind, variantRuntime: TimelineVariantRuntime?) {
                guard let variantRuntime, !variantRuntime.tokens.isEmpty else { return }

                let tokens = variantRuntime.tokens
                let revealTimes = variantRuntime.revealTimes
                let safeTime = min(max(effectiveTime, runtime.startTime - epsilon), runtime.endTime + epsilon)
                let revealCutoff = min(safeTime, runtime.endTime)
                let progressCount = revealTimes.filter { $0 <= revealCutoff + epsilon }.count

                var revealedCount: Int
                switch state {
                case .past:
                    revealedCount = tokens.count
                case .future:
                    revealedCount = progressCount
                case .active:
                    revealedCount = progressCount
                }

                revealedCount = max(0, min(revealedCount, tokens.count))
                // Force all words revealed when near segment end (using larger tolerance for dwell period)
                if safeTime >= runtime.endTime - forceRevealTolerance {
                    revealedCount = tokens.count
                }
                if !revealTimes.isEmpty,
                   state == .active,
                   safeTime >= runtime.startTime - epsilon,
                   revealedCount == 0 {
                    revealedCount = 1
                }

                var currentIndex: Int? = revealedCount > 0 ? revealedCount - 1 : nil
                // Force last word as current when near segment end (matching forceRevealTolerance)
                if !tokens.isEmpty && (state == .past || safeTime >= runtime.endTime - forceRevealTolerance) {
                    currentIndex = tokens.count - 1
                }

                variants.append(
                    TextPlayerVariantDisplay(
                        id: kind.rawValue,
                        label: label,
                        tokens: tokens,
                        revealedCount: revealedCount,
                        currentIndex: currentIndex,
                        kind: kind,
                        seekTimes: revealTimes
                    )
                )
            }

            appendVariant(label: "Original", kind: .original, variantRuntime: runtime.variants[.original])
            appendVariant(label: "Transliteration", kind: .transliteration, variantRuntime: runtime.variants[.transliteration])
            appendVariant(label: "Translation", kind: .translation, variantRuntime: runtime.variants[.translation])

            guard !variants.isEmpty else { continue }

            displaySentences.append(
                TextPlayerSentenceDisplay(
                    id: "sentence-\(runtime.index)",
                    index: runtime.index,
                    sentenceNumber: runtime.sentenceNumber,
                    state: state,
                    variants: variants
                )
            )
        }

        guard let resolvedActiveIndex = activeIndex else { return nil }
        return TimelineDisplay(sentences: displaySentences, activeIndex: resolvedActiveIndex, effectiveTime: effectiveTime)
    }

    static func buildActiveSentenceDisplay(
        timelineSentences: [TimelineSentenceRuntime],
        chunkTime: Double,
        audioDuration: Double?
    ) -> TextPlayerSentenceDisplay? {
        guard !timelineSentences.isEmpty else { return nil }
        let effectiveTime = resolveEffectiveTime(
            timelineSentences: timelineSentences,
            chunkTime: chunkTime,
            audioDuration: audioDuration
        )
        guard let runtime = resolveActiveRuntime(
            timelineSentences: timelineSentences,
            effectiveTime: effectiveTime
        ) else {
            return nil
        }

        let epsilon = 1e-3
        // Larger tolerance for "force all revealed" at segment end
        // This should be >= the dwell tolerance (0.1s) used in SequencePlaybackController
        let forceRevealTolerance = 0.15
        let state: TextPlayerSentenceState = .active
        var variants: [TextPlayerVariantDisplay] = []

        func appendVariant(label: String, kind: TextPlayerVariantKind, variantRuntime: TimelineVariantRuntime?) {
            guard let variantRuntime, !variantRuntime.tokens.isEmpty else { return }

            let tokens = variantRuntime.tokens
            let revealTimes = variantRuntime.revealTimes
            let safeTime = min(max(effectiveTime, runtime.startTime - epsilon), runtime.endTime + epsilon)
            let revealCutoff = min(safeTime, runtime.endTime)
            let progressCount = revealTimes.filter { $0 <= revealCutoff + epsilon }.count

            var revealedCount: Int
            switch state {
            case .past:
                revealedCount = tokens.count
            case .future:
                revealedCount = progressCount
            case .active:
                revealedCount = progressCount
            }

            revealedCount = max(0, min(revealedCount, tokens.count))
            // Force all words revealed when near segment end (using larger tolerance for dwell period)
            if safeTime >= runtime.endTime - forceRevealTolerance {
                revealedCount = tokens.count
            }
            if !revealTimes.isEmpty,
               state == .active,
               safeTime >= runtime.startTime - epsilon,
               revealedCount == 0 {
                revealedCount = 1
            }

            var currentIndex: Int? = revealedCount > 0 ? revealedCount - 1 : nil
            // Force last word as current when near segment end (matching forceRevealTolerance)
            if !tokens.isEmpty && (state == .past || safeTime >= runtime.endTime - forceRevealTolerance) {
                currentIndex = tokens.count - 1
            }

            variants.append(
                TextPlayerVariantDisplay(
                    id: kind.rawValue,
                    label: label,
                    tokens: tokens,
                    revealedCount: revealedCount,
                    currentIndex: currentIndex,
                    kind: kind,
                    seekTimes: revealTimes
                )
            )
        }

        appendVariant(label: "Original", kind: .original, variantRuntime: runtime.variants[.original])
        appendVariant(label: "Transliteration", kind: .transliteration, variantRuntime: runtime.variants[.transliteration])
        appendVariant(label: "Translation", kind: .translation, variantRuntime: runtime.variants[.translation])

        guard !variants.isEmpty else { return nil }
        return TextPlayerSentenceDisplay(
            id: "sentence-\(runtime.index)",
            index: runtime.index,
            sentenceNumber: runtime.sentenceNumber,
            state: state,
            variants: variants
        )
    }

    static func resolveActiveIndex(
        timelineSentences: [TimelineSentenceRuntime],
        chunkTime: Double,
        audioDuration: Double?
    ) -> Int? {
        guard !timelineSentences.isEmpty else { return nil }
        let effectiveTime = resolveEffectiveTime(
            timelineSentences: timelineSentences,
            chunkTime: chunkTime,
            audioDuration: audioDuration
        )
        return resolveActiveRuntime(
            timelineSentences: timelineSentences,
            effectiveTime: effectiveTime
        )?.index
    }

    static func buildActiveSentenceDisplay(
        sentences: [InteractiveChunk.Sentence],
        activeTimingTrack: TextPlayerTimingTrack,
        chunkTime: Double,
        audioDuration: Double?,
        useCombinedPhases: Bool
    ) -> TextPlayerSentenceDisplay? {
        guard let resolution = resolveActiveSentenceResolution(
            sentences: sentences,
            activeTimingTrack: activeTimingTrack,
            chunkTime: chunkTime,
            audioDuration: audioDuration,
            useCombinedPhases: useCombinedPhases
        ) else {
            return nil
        }

        let sentence = resolution.sentence
        let components = resolution.components
        let scale = resolution.scale
        let effectiveTime = resolution.effectiveTime
        let sentenceStart = resolution.startTime
        let sentenceEnd = resolution.endTime
        let sentenceNumber = sentence.displayIndex
        let isOriginalTrack = components.isOriginalTrack
        let highlightOriginal = components.highlightOriginal
        let originalTokens = sentence.originalTokens
        let translationTokens = sentence.translationTokens
        let transliterationTokens = sentence.transliterationTokens

        let translationTrackStart = sentenceStart + components.translationTrackStartOffset
        let translationPhaseEndAbsolute = translationTrackStart + components.translationTotalDuration

        // Check if we can use absolute translation timing (gate-based word times)
        let useAbsoluteTranslationTiming = !isOriginalTrack
            && sentence.startGate != nil
            && sentence.endGate != nil
            && !sentence.timingTokens.isEmpty

        var translationRevealTimes: [Double] = []
        var translationRevealIsAbsolute = false
        if useAbsoluteTranslationTiming {
            // Use actual word timing from timingTokens (absolute audio times)
            translationRevealTimes = sentence.timingTokens.map { $0.startTime }
            translationRevealIsAbsolute = true
            // Ensure we have the right number of reveal times
            if translationRevealTimes.count != translationTokens.count && !translationTokens.isEmpty {
                translationRevealTimes = buildUniformRevealTimes(
                    count: translationTokens.count,
                    startTime: translationTrackStart,
                    duration: components.translationSpeechDuration
                )
                translationRevealIsAbsolute = false
            }
        } else if !isOriginalTrack {
            var translationDurationsRaw: [Double] = []
            var prevTranslationCount = 0
            for event in sentence.timeline {
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
            if !translationDurationsRaw.isEmpty {
                var cumulativeTranslation = 0.0
                for rawDuration in translationDurationsRaw {
                    translationRevealTimes.append(translationTrackStart + cumulativeTranslation)
                    cumulativeTranslation += rawDuration
                }
            }
            if translationRevealTimes.count != translationTokens.count && !translationTokens.isEmpty {
                translationRevealTimes = buildUniformRevealTimes(
                    count: translationTokens.count,
                    startTime: translationTrackStart,
                    duration: components.translationSpeechDuration
                )
            }
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
                let ratio = transliterationTokens.count > 1
                    ? Double(idx) / Double(transliterationTokens.count - 1)
                    : 0
                let mappedIndex = min(
                    translationRevealTimes.count - 1,
                    Int(round(ratio * Double(translationRevealTimes.count - 1)))
                )
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
        if !translationRevealIsAbsolute && !isOriginalTrack && !adjustedTransliteration.isEmpty {
            adjustedTransliteration[0] = translationTrackStart
            adjustedTransliteration[adjustedTransliteration.count - 1] = translationPhaseEndAbsolute
        }

        var originalReveal: [Double] = []
        var originalRevealIsAbsolute = false
        if highlightOriginal {
            // Use actual original timing tokens when on the original track
            // and the sentence has word-level timing data
            if isOriginalTrack && !sentence.originalTimingTokens.isEmpty {
                originalReveal = sentence.originalTimingTokens.map { $0.startTime }
                // Mark that these are absolute audio times (should not be scaled)
                originalRevealIsAbsolute = true
                // Ensure we have the right number of reveal times
                if originalReveal.count != originalTokens.count && !originalTokens.isEmpty {
                    originalReveal = buildUniformRevealTimes(
                        count: originalTokens.count,
                        startTime: sentenceStart,
                        duration: components.originalPhaseDuration
                    )
                    originalRevealIsAbsolute = false
                }
            } else {
                originalReveal = buildUniformRevealTimes(
                    count: originalTokens.count,
                    startTime: sentenceStart,
                    duration: components.originalPhaseDuration
                )
            }
        }

        // Don't scale times if they come from actual timing tokens (they're already in audio-file time)
        let scaledStart = (useAbsoluteTranslationTiming || originalRevealIsAbsolute) ? sentenceStart : sentenceStart * scale
        let scaledEnd = (useAbsoluteTranslationTiming || originalRevealIsAbsolute) ? sentenceEnd : sentenceEnd * scale
        let scaledTranslationRevealTimes = translationRevealIsAbsolute ? translationRevealTimes : translationRevealTimes.map { $0 * scale }
        let scaledTransliterationRevealTimes = translationRevealIsAbsolute ? adjustedTransliteration : adjustedTransliteration.map { $0 * scale }
        let scaledOriginalReveal = originalRevealIsAbsolute ? originalReveal : originalReveal.map { $0 * scale }

        let epsilon = 1e-3
        // Larger tolerance for "force all revealed" at segment end
        // This should be >= the dwell tolerance (0.1s) used in SequencePlaybackController
        let forceRevealTolerance = 0.15
        let state: TextPlayerSentenceState = .active
        var variants: [TextPlayerVariantDisplay] = []

        func appendVariant(label: String, kind: TextPlayerVariantKind, tokens: [String], revealTimes: [Double]) {
            guard !tokens.isEmpty else { return }
            let safeTime = min(max(effectiveTime, scaledStart - epsilon), scaledEnd + epsilon)
            let revealCutoff = min(safeTime, scaledEnd)
            let progressCount = revealTimes.filter { $0 <= revealCutoff + epsilon }.count

            var revealedCount: Int
            switch state {
            case .past:
                revealedCount = tokens.count
            case .future:
                revealedCount = progressCount
            case .active:
                revealedCount = progressCount
            }

            revealedCount = max(0, min(revealedCount, tokens.count))
            // Force all words revealed when near segment end (using larger tolerance for dwell period)
            if safeTime >= scaledEnd - forceRevealTolerance {
                revealedCount = tokens.count
            }
            if !revealTimes.isEmpty,
               state == .active,
               safeTime >= scaledStart - epsilon,
               revealedCount == 0 {
                revealedCount = 1
            }

            var currentIndex: Int? = revealedCount > 0 ? revealedCount - 1 : nil
            // Force last word as current when near segment end (matching forceRevealTolerance)
            if !tokens.isEmpty && (state == .past || safeTime >= scaledEnd - forceRevealTolerance) {
                currentIndex = tokens.count - 1
            }

            variants.append(
                TextPlayerVariantDisplay(
                    id: kind.rawValue,
                    label: label,
                    tokens: tokens,
                    revealedCount: revealedCount,
                    currentIndex: currentIndex,
                    kind: kind,
                    seekTimes: revealTimes.isEmpty ? nil : revealTimes
                )
            )
        }

        appendVariant(
            label: "Original",
            kind: .original,
            tokens: originalTokens,
            revealTimes: scaledOriginalReveal
        )
        appendVariant(
            label: "Transliteration",
            kind: .transliteration,
            tokens: transliterationTokens,
            revealTimes: scaledTransliterationRevealTimes
        )
        appendVariant(
            label: "Translation",
            kind: .translation,
            tokens: translationTokens,
            revealTimes: scaledTranslationRevealTimes
        )

        guard !variants.isEmpty else { return nil }
        return TextPlayerSentenceDisplay(
            id: "sentence-\(resolution.index)",
            index: resolution.index,
            sentenceNumber: sentenceNumber,
            state: state,
            variants: variants
        )
    }

    static func resolveActiveIndex(
        sentences: [InteractiveChunk.Sentence],
        activeTimingTrack: TextPlayerTimingTrack,
        chunkTime: Double,
        audioDuration: Double?,
        useCombinedPhases: Bool
    ) -> Int? {
        resolveActiveSentenceResolution(
            sentences: sentences,
            activeTimingTrack: activeTimingTrack,
            chunkTime: chunkTime,
            audioDuration: audioDuration,
            useCombinedPhases: useCombinedPhases
        )?.index
    }

    static func buildStaticDisplay(
        sentences: [InteractiveChunk.Sentence],
        activeIndex: Int? = nil
    ) -> [TextPlayerSentenceDisplay] {
        guard !sentences.isEmpty else { return [] }
        let resolvedActiveIndex = activeIndex ?? 0
        return sentences.enumerated().compactMap { index, sentence in
            var variants: [TextPlayerVariantDisplay] = []

            func appendStaticVariant(label: String, kind: TextPlayerVariantKind, tokens: [String]) {
                guard !tokens.isEmpty else { return }
                variants.append(
                    TextPlayerVariantDisplay(
                        id: kind.rawValue,
                        label: label,
                        tokens: tokens,
                        revealedCount: tokens.count,
                        currentIndex: tokens.count - 1,
                        kind: kind,
                        seekTimes: nil
                    )
                )
            }

            appendStaticVariant(label: "Original", kind: .original, tokens: sentence.originalTokens)
            appendStaticVariant(label: "Transliteration", kind: .transliteration, tokens: sentence.transliterationTokens)
            appendStaticVariant(label: "Translation", kind: .translation, tokens: sentence.translationTokens)

            guard !variants.isEmpty else { return nil }
            let state: TextPlayerSentenceState = index == resolvedActiveIndex ? .active : .future
            return TextPlayerSentenceDisplay(
                id: "sentence-\(index)",
                index: index,
                sentenceNumber: sentence.displayIndex,
                state: state,
                variants: variants
            )
        }
    }

    /// Build an initial display for a sentence (first word revealed for the primary track)
    /// Used during sentence changes to show the target sentence starting fresh
    static func buildInitialDisplay(
        sentences: [InteractiveChunk.Sentence],
        activeIndex: Int,
        primaryTrack: TextPlayerTimingTrack
    ) -> TextPlayerSentenceDisplay? {
        guard sentences.indices.contains(activeIndex) else { return nil }
        let sentence = sentences[activeIndex]
        var variants: [TextPlayerVariantDisplay] = []

        let isPrimaryOriginal = primaryTrack == .original

        func appendVariant(label: String, kind: TextPlayerVariantKind, tokens: [String]) {
            guard !tokens.isEmpty else { return }
            // Primary track gets first word revealed, others get none revealed
            let isPrimary = (kind == .original && isPrimaryOriginal) ||
                           (kind != .original && !isPrimaryOriginal)
            let revealedCount = isPrimary ? 1 : 0
            let currentIndex = isPrimary ? 0 : nil
            variants.append(
                TextPlayerVariantDisplay(
                    id: kind.rawValue,
                    label: label,
                    tokens: tokens,
                    revealedCount: revealedCount,
                    currentIndex: currentIndex,
                    kind: kind,
                    seekTimes: nil
                )
            )
        }

        appendVariant(label: "Original", kind: .original, tokens: sentence.originalTokens)
        appendVariant(label: "Transliteration", kind: .transliteration, tokens: sentence.transliterationTokens)
        appendVariant(label: "Translation", kind: .translation, tokens: sentence.translationTokens)

        guard !variants.isEmpty else { return nil }
        return TextPlayerSentenceDisplay(
            id: "sentence-\(activeIndex)",
            index: activeIndex,
            sentenceNumber: sentence.displayIndex,
            state: .active,
            variants: variants
        )
    }

    /// Build a display for same-sentence track switch (e.g., original → translation)
    /// Shows the previous track fully revealed and new track ready to animate
    /// - Original → Translation: original fully revealed, transliteration/translation at 0
    /// - Translation → Original: translation/transliteration fully revealed, original at 0
    static func buildTrackSwitchDisplay(
        sentences: [InteractiveChunk.Sentence],
        activeIndex: Int,
        newPrimaryTrack: TextPlayerTimingTrack
    ) -> TextPlayerSentenceDisplay? {
        guard sentences.indices.contains(activeIndex) else { return nil }
        let sentence = sentences[activeIndex]
        var variants: [TextPlayerVariantDisplay] = []

        // When switching TO translation: original is done (fully revealed), translation starts fresh
        // When switching TO original: translation is done (fully revealed), original starts fresh
        let switchingToTranslation = newPrimaryTrack == .translation

        func appendVariant(label: String, kind: TextPlayerVariantKind, tokens: [String]) {
            guard !tokens.isEmpty else { return }

            let revealedCount: Int
            let currentIndex: Int?

            if switchingToTranslation {
                // Switching to translation track
                if kind == .original {
                    // Original is done - fully revealed
                    revealedCount = tokens.count
                    currentIndex = tokens.count - 1
                } else {
                    // Translation/transliteration start fresh - none revealed
                    revealedCount = 0
                    currentIndex = nil
                }
            } else {
                // Switching to original track
                if kind == .original {
                    // Original starts fresh - none revealed
                    revealedCount = 0
                    currentIndex = nil
                } else {
                    // Translation/transliteration are done - fully revealed
                    revealedCount = tokens.count
                    currentIndex = tokens.count - 1
                }
            }

            variants.append(
                TextPlayerVariantDisplay(
                    id: kind.rawValue,
                    label: label,
                    tokens: tokens,
                    revealedCount: revealedCount,
                    currentIndex: currentIndex,
                    kind: kind,
                    seekTimes: nil
                )
            )
        }

        appendVariant(label: "Original", kind: .original, tokens: sentence.originalTokens)
        appendVariant(label: "Transliteration", kind: .transliteration, tokens: sentence.transliterationTokens)
        appendVariant(label: "Translation", kind: .translation, tokens: sentence.translationTokens)

        guard !variants.isEmpty else { return nil }
        return TextPlayerSentenceDisplay(
            id: "sentence-\(activeIndex)",
            index: activeIndex,
            sentenceNumber: sentence.displayIndex,
            state: .active,
            variants: variants
        )
    }

    /// Build a hybrid display for same-sentence track switch settling
    /// Shows the previous track fully revealed while animating the new track based on current time
    /// - Parameters:
    ///   - sentences: The chunk's sentences
    ///   - activeIndex: The sentence index
    ///   - newPrimaryTrack: The track we switched TO (the one currently playing)
    ///   - chunkTime: Current playback time in the new track
    ///   - audioDuration: Duration of the current audio track
    ///   - timingVersion: Timing version for the chunk
    static func buildSettlingDisplay(
        sentences: [InteractiveChunk.Sentence],
        activeIndex: Int,
        newPrimaryTrack: TextPlayerTimingTrack,
        chunkTime: Double,
        audioDuration: Double?,
        timingVersion: String? = nil
    ) -> TextPlayerSentenceDisplay? {
        guard sentences.indices.contains(activeIndex) else { return nil }
        let sentence = sentences[activeIndex]

        // Build timeline for the NEW track to get proper reveal times
        let timelineSentences = buildTimelineSentences(
            sentences: sentences,
            activeTimingTrack: newPrimaryTrack,
            audioDuration: audioDuration,
            useCombinedPhases: false,
            timingVersion: timingVersion
        )

        guard let targetRuntime = timelineSentences?.first(where: { $0.index == activeIndex }) else {
            // Fallback to static display
            return buildTrackSwitchDisplay(sentences: sentences, activeIndex: activeIndex, newPrimaryTrack: newPrimaryTrack)
        }

        let switchingToTranslation = newPrimaryTrack == .translation
        var variants: [TextPlayerVariantDisplay] = []

        let epsilon = 1e-3
        let forceRevealTolerance = 0.15
        let safeTime = min(max(chunkTime, targetRuntime.startTime - epsilon), targetRuntime.endTime + epsilon)
        let revealCutoff = min(safeTime, targetRuntime.endTime)

        func appendVariant(label: String, kind: TextPlayerVariantKind, tokens: [String]) {
            guard !tokens.isEmpty else { return }

            let revealedCount: Int
            let currentIndex: Int?
            var seekTimes: [Double]? = nil

            if switchingToTranslation {
                // Switching to translation track
                if kind == .original {
                    // Original is DONE - fully revealed (we just finished playing it)
                    revealedCount = tokens.count
                    currentIndex = tokens.count - 1
                } else {
                    // Translation/transliteration - animate based on current time
                    if let variantRuntime = targetRuntime.variants[kind] {
                        let revealTimes = variantRuntime.revealTimes
                        var count = revealTimes.filter { $0 <= revealCutoff + epsilon }.count
                        count = max(0, min(count, tokens.count))
                        // Force all words revealed when near segment end
                        if safeTime >= targetRuntime.endTime - forceRevealTolerance {
                            revealedCount = tokens.count
                        } else if count == 0 && safeTime >= targetRuntime.startTime - epsilon {
                            revealedCount = 1 // At least first word
                        } else {
                            revealedCount = count
                        }
                        currentIndex = revealedCount > 0 ? revealedCount - 1 : nil
                        seekTimes = revealTimes.isEmpty ? nil : revealTimes
                    } else {
                        // No timing data - show first word revealed
                        revealedCount = 1
                        currentIndex = 0
                    }
                }
            } else {
                // Switching to original track
                if kind == .original {
                    // Original - animate based on current time
                    if let variantRuntime = targetRuntime.variants[kind] {
                        let revealTimes = variantRuntime.revealTimes
                        var count = revealTimes.filter { $0 <= revealCutoff + epsilon }.count
                        count = max(0, min(count, tokens.count))
                        // Force all words revealed when near segment end
                        if safeTime >= targetRuntime.endTime - forceRevealTolerance {
                            revealedCount = tokens.count
                        } else if count == 0 && safeTime >= targetRuntime.startTime - epsilon {
                            revealedCount = 1
                        } else {
                            revealedCount = count
                        }
                        currentIndex = revealedCount > 0 ? revealedCount - 1 : nil
                        seekTimes = revealTimes.isEmpty ? nil : revealTimes
                    } else {
                        revealedCount = 1
                        currentIndex = 0
                    }
                } else {
                    // Translation/transliteration are DONE - fully revealed
                    revealedCount = tokens.count
                    currentIndex = tokens.count - 1
                }
            }

            variants.append(
                TextPlayerVariantDisplay(
                    id: kind.rawValue,
                    label: label,
                    tokens: tokens,
                    revealedCount: revealedCount,
                    currentIndex: currentIndex,
                    kind: kind,
                    seekTimes: seekTimes
                )
            )
        }

        appendVariant(label: "Original", kind: .original, tokens: sentence.originalTokens)
        appendVariant(label: "Transliteration", kind: .transliteration, tokens: sentence.transliterationTokens)
        appendVariant(label: "Translation", kind: .translation, tokens: sentence.translationTokens)

        guard !variants.isEmpty else { return nil }
        return TextPlayerSentenceDisplay(
            id: "sentence-\(activeIndex)",
            index: activeIndex,
            sentenceNumber: sentence.displayIndex,
            state: .active,
            variants: variants
        )
    }

    /// Build a fully-revealed display for a single sentence (all variants fully revealed)
    /// Used during sentence-change transitions to show the PREVIOUS sentence while transitioning
    static func buildFullyRevealedDisplay(
        sentences: [InteractiveChunk.Sentence],
        activeIndex: Int
    ) -> TextPlayerSentenceDisplay? {
        guard sentences.indices.contains(activeIndex) else { return nil }
        let sentence = sentences[activeIndex]
        var variants: [TextPlayerVariantDisplay] = []

        func appendVariant(label: String, kind: TextPlayerVariantKind, tokens: [String]) {
            guard !tokens.isEmpty else { return }
            variants.append(
                TextPlayerVariantDisplay(
                    id: kind.rawValue,
                    label: label,
                    tokens: tokens,
                    revealedCount: tokens.count,
                    currentIndex: tokens.count - 1,
                    kind: kind,
                    seekTimes: nil
                )
            )
        }

        appendVariant(label: "Original", kind: .original, tokens: sentence.originalTokens)
        appendVariant(label: "Transliteration", kind: .transliteration, tokens: sentence.transliterationTokens)
        appendVariant(label: "Translation", kind: .translation, tokens: sentence.translationTokens)

        guard !variants.isEmpty else { return nil }
        return TextPlayerSentenceDisplay(
            id: "sentence-\(activeIndex)",
            index: activeIndex,
            sentenceNumber: sentence.displayIndex,
            state: .active,
            variants: variants
        )
    }

    /// Build a display for dwell state (paused at segment end before advancing)
    /// Shows the current track fully revealed (just finished) and the next track at 0 (about to start)
    /// - Parameters:
    ///   - sentences: All sentences in the chunk
    ///   - activeIndex: The current sentence index
    ///   - currentTrack: The track that just finished playing (fully revealed)
    ///   - nextTrack: The track that will play next (at 0, not yet revealed). If nil, shows all fully revealed.
    ///   - isSameSentence: Whether the next segment is for the same sentence (track switch within sentence)
    static func buildDwellDisplay(
        sentences: [InteractiveChunk.Sentence],
        activeIndex: Int,
        currentTrack: TextPlayerTimingTrack,
        nextTrack: TextPlayerTimingTrack?,
        isSameSentence: Bool
    ) -> TextPlayerSentenceDisplay? {
        guard sentences.indices.contains(activeIndex) else { return nil }
        let sentence = sentences[activeIndex]
        var variants: [TextPlayerVariantDisplay] = []

        func appendVariant(label: String, kind: TextPlayerVariantKind, tokens: [String]) {
            guard !tokens.isEmpty else { return }

            let revealedCount: Int
            let currentIndex: Int?

            // Determine if this variant belongs to the current (finished) track or the next track
            let isCurrentTrack: Bool
            let isNextTrack: Bool

            switch currentTrack {
            case .original:
                isCurrentTrack = (kind == .original)
            case .translation, .mix:
                isCurrentTrack = (kind == .translation || kind == .transliteration)
            }

            if let next = nextTrack {
                switch next {
                case .original:
                    isNextTrack = (kind == .original)
                case .translation, .mix:
                    isNextTrack = (kind == .translation || kind == .transliteration)
                }
            } else {
                isNextTrack = false
            }

            if isCurrentTrack {
                // Current track just finished - fully revealed
                revealedCount = tokens.count
                currentIndex = tokens.count - 1
            } else if isNextTrack && isSameSentence {
                // Next track about to start (same sentence) - show at 0 (green/unrevealed)
                revealedCount = 0
                currentIndex = nil
            } else {
                // For sentence changes or unknown next track, show fully revealed
                revealedCount = tokens.count
                currentIndex = tokens.count - 1
            }

            variants.append(
                TextPlayerVariantDisplay(
                    id: kind.rawValue,
                    label: label,
                    tokens: tokens,
                    revealedCount: revealedCount,
                    currentIndex: currentIndex,
                    kind: kind,
                    seekTimes: nil
                )
            )
        }

        appendVariant(label: "Original", kind: .original, tokens: sentence.originalTokens)
        appendVariant(label: "Transliteration", kind: .transliteration, tokens: sentence.transliterationTokens)
        appendVariant(label: "Translation", kind: .translation, tokens: sentence.translationTokens)

        guard !variants.isEmpty else { return nil }
        return TextPlayerSentenceDisplay(
            id: "sentence-\(activeIndex)",
            index: activeIndex,
            sentenceNumber: sentence.displayIndex,
            state: .active,
            variants: variants
        )
    }

    static func selectActiveSentence(from sentences: [TextPlayerSentenceDisplay]) -> [TextPlayerSentenceDisplay] {
        guard !sentences.isEmpty else { return [] }
        if let active = sentences.first(where: { $0.state == .active }) {
            return [active]
        }
        return [sentences[0]]
    }

    private static func resolveActiveSentenceResolution(
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

    private static func computeSentenceTimingComponents(
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

    private static func resolveEffectiveTime(
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

    private static func resolveEffectiveTime(
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

    private static func resolveActiveRuntime(
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

    private static func buildUniformRevealTimes(count: Int, startTime: Double, duration: Double) -> [Double] {
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
