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
        audioDuration: Double?,
        activeTimingTrack: TextPlayerTimingTrack? = nil
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

        // Determine which track is currently active (for force reveal logic)
        let isOriginalTrackActive: Bool
        if let track = activeTimingTrack {
            isOriginalTrackActive = (track == .original)
        } else {
            // Default: assume original track for backwards compatibility
            isOriginalTrackActive = true
        }

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

            func appendVariant(label: String, kind: TextPlayerVariantKind, variantRuntime: TimelineVariantRuntime?, isActiveTrack: Bool) {
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
                // ONLY for the currently active track - prevents other tracks from being force-revealed
                if isActiveTrack && safeTime >= runtime.endTime - forceRevealTolerance {
                    revealedCount = tokens.count
                }
                // Ensure at least first word is revealed for the ACTIVE track when playback starts
                // Only apply to active track to prevent non-playing tracks from getting orange highlight
                if isActiveTrack,
                   !revealTimes.isEmpty,
                   state == .active,
                   safeTime >= runtime.startTime - epsilon,
                   revealedCount == 0 {
                    revealedCount = 1
                }

                var currentIndex: Int? = revealedCount > 0 ? revealedCount - 1 : nil
                // Force last word as current when near segment end (matching forceRevealTolerance)
                // ONLY for the currently active track - prevents other tracks from getting highlight
                if isActiveTrack && !tokens.isEmpty && (state == .past || safeTime >= runtime.endTime - forceRevealTolerance) {
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

            appendVariant(label: "Original", kind: .original, variantRuntime: runtime.variants[.original], isActiveTrack: isOriginalTrackActive)
            appendVariant(label: "Transliteration", kind: .transliteration, variantRuntime: runtime.variants[.transliteration], isActiveTrack: !isOriginalTrackActive)
            appendVariant(label: "Translation", kind: .translation, variantRuntime: runtime.variants[.translation], isActiveTrack: !isOriginalTrackActive)

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
        audioDuration: Double?,
        activeTimingTrack: TextPlayerTimingTrack? = nil
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

        // Determine which track is currently active (for force reveal logic)
        let isOriginalTrackActive: Bool
        if let track = activeTimingTrack {
            isOriginalTrackActive = (track == .original)
        } else {
            // Default: assume original track for backwards compatibility
            isOriginalTrackActive = true
        }

        func appendVariant(label: String, kind: TextPlayerVariantKind, variantRuntime: TimelineVariantRuntime?, isActiveTrack: Bool) {
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
            // ONLY for the currently active track - prevents other tracks from being force-revealed
            if isActiveTrack && safeTime >= runtime.endTime - forceRevealTolerance {
                revealedCount = tokens.count
            }
            // Ensure at least first word is revealed for the ACTIVE track when playback starts
            // Only apply to active track to prevent non-playing tracks from getting orange highlight
            if isActiveTrack,
               !revealTimes.isEmpty,
               state == .active,
               safeTime >= runtime.startTime - epsilon,
               revealedCount == 0 {
                revealedCount = 1
            }

            var currentIndex: Int? = revealedCount > 0 ? revealedCount - 1 : nil
            // Force last word as current when near segment end (matching forceRevealTolerance)
            // ONLY for the currently active track - prevents other tracks from getting highlight
            if isActiveTrack && !tokens.isEmpty && (state == .past || safeTime >= runtime.endTime - forceRevealTolerance) {
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

        appendVariant(label: "Original", kind: .original, variantRuntime: runtime.variants[.original], isActiveTrack: isOriginalTrackActive)
        appendVariant(label: "Transliteration", kind: .transliteration, variantRuntime: runtime.variants[.transliteration], isActiveTrack: !isOriginalTrackActive)
        appendVariant(label: "Translation", kind: .translation, variantRuntime: runtime.variants[.translation], isActiveTrack: !isOriginalTrackActive)

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

        func appendVariant(label: String, kind: TextPlayerVariantKind, tokens: [String], revealTimes: [Double], isActiveTrack: Bool) {
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
            // ONLY for the currently active track - prevents other tracks from being force-revealed
            if isActiveTrack && safeTime >= scaledEnd - forceRevealTolerance {
                revealedCount = tokens.count
            }
            // Ensure at least first word is revealed for the ACTIVE track when playback starts
            // Only apply to active track to prevent non-playing tracks from getting orange highlight
            if isActiveTrack,
               !revealTimes.isEmpty,
               state == .active,
               safeTime >= scaledStart - epsilon,
               revealedCount == 0 {
                revealedCount = 1
            }

            var currentIndex: Int? = revealedCount > 0 ? revealedCount - 1 : nil
            // Force last word as current when near segment end (matching forceRevealTolerance)
            // ONLY for the currently active track - prevents other tracks from getting highlight
            if isActiveTrack && !tokens.isEmpty && (state == .past || safeTime >= scaledEnd - forceRevealTolerance) {
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
            revealTimes: scaledOriginalReveal,
            isActiveTrack: isOriginalTrack
        )
        appendVariant(
            label: "Transliteration",
            kind: .transliteration,
            tokens: transliterationTokens,
            revealTimes: scaledTransliterationRevealTimes,
            isActiveTrack: !isOriginalTrack
        )
        appendVariant(
            label: "Translation",
            kind: .translation,
            tokens: translationTokens,
            revealTimes: scaledTranslationRevealTimes,
            isActiveTrack: !isOriginalTrack
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
}
