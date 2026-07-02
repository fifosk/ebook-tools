import Foundation

// MARK: - Active Display Resolution

extension TextPlayerTimeline {

    static func buildTimelineDisplay(
        timelineSentences: [TimelineSentenceRuntime],
        chunkTime: Double,
        audioDuration: Double?,
        activeTimingTrack: TextPlayerTimingTrack? = nil,
        usesAbsoluteTiming: Bool = false
    ) -> TimelineDisplay? {
        guard !timelineSentences.isEmpty else { return nil }
        let effectiveTime = resolveEffectiveTime(
            timelineSentences: timelineSentences,
            chunkTime: chunkTime,
            audioDuration: audioDuration,
            usesAbsoluteTiming: usesAbsoluteTiming
        )
        let activeIndex = resolveActiveRuntime(
            timelineSentences: timelineSentences,
            effectiveTime: effectiveTime
        )?.index
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
                let revealState = resolveVariantRevealState(
                    tokens: tokens,
                    revealTimes: revealTimes,
                    sentenceState: state,
                    effectiveTime: effectiveTime,
                    startTime: runtime.startTime,
                    endTime: runtime.endTime,
                    isActiveTrack: isActiveTrack
                )

                variants.append(
                    TextPlayerVariantDisplay(
                        id: kind.rawValue,
                        label: label,
                        tokens: tokens,
                        revealedCount: revealState.revealedCount,
                        currentIndex: revealState.currentIndex,
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
        activeTimingTrack: TextPlayerTimingTrack? = nil,
        usesAbsoluteTiming: Bool = false
    ) -> TextPlayerSentenceDisplay? {
        guard !timelineSentences.isEmpty else { return nil }
        let effectiveTime = resolveEffectiveTime(
            timelineSentences: timelineSentences,
            chunkTime: chunkTime,
            audioDuration: audioDuration,
            usesAbsoluteTiming: usesAbsoluteTiming
        )
        guard let runtime = resolveActiveRuntime(
            timelineSentences: timelineSentences,
            effectiveTime: effectiveTime
        ) else {
            return nil
        }

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
            let revealState = resolveVariantRevealState(
                tokens: tokens,
                revealTimes: revealTimes,
                sentenceState: state,
                effectiveTime: effectiveTime,
                startTime: runtime.startTime,
                endTime: runtime.endTime,
                isActiveTrack: isActiveTrack
            )

            variants.append(
                TextPlayerVariantDisplay(
                    id: kind.rawValue,
                    label: label,
                    tokens: tokens,
                    revealedCount: revealState.revealedCount,
                    currentIndex: revealState.currentIndex,
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
        audioDuration: Double?,
        usesAbsoluteTiming: Bool = false
    ) -> Int? {
        guard !timelineSentences.isEmpty else { return nil }
        let effectiveTime = resolveEffectiveTime(
            timelineSentences: timelineSentences,
            chunkTime: chunkTime,
            audioDuration: audioDuration,
            usesAbsoluteTiming: usesAbsoluteTiming
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
        useCombinedPhases: Bool,
        timingVersion: String? = nil
    ) -> TextPlayerSentenceDisplay? {
        let usesAbsoluteTimeline = usesAbsoluteTiming(
            sentences: sentences,
            activeTimingTrack: activeTimingTrack
        ) || timingVersion == "2"
        if let timelineSentences = buildTimelineSentences(
            sentences: sentences,
            activeTimingTrack: activeTimingTrack,
            audioDuration: audioDuration,
            useCombinedPhases: useCombinedPhases,
            timingVersion: timingVersion
        ),
           let display = buildActiveSentenceDisplay(
               timelineSentences: timelineSentences,
               chunkTime: chunkTime,
               audioDuration: audioDuration,
               activeTimingTrack: activeTimingTrack,
               usesAbsoluteTiming: usesAbsoluteTimeline
           ) {
            return display
        }

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

        // Gates are absolute sentence boundaries. Word timing tokens refine the
        // per-word reveal, but they are not required for sentence selection.
        let useAbsoluteOriginalTiming = isOriginalTrack && sentence.originalStartGate != nil
        let useAbsoluteTranslationTiming = !isOriginalTrack && sentence.startGate != nil
        let translationTrackStart = sentenceStart + components.translationTrackStartOffset
        let translationPhaseEndAbsolute = useAbsoluteTranslationTiming
            ? sentenceEnd
            : translationTrackStart + components.translationTotalDuration

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
        let usesAbsoluteSentenceBounds = useAbsoluteOriginalTiming || useAbsoluteTranslationTiming || originalRevealIsAbsolute
        let scaledStart = usesAbsoluteSentenceBounds ? sentenceStart : sentenceStart * scale
        let scaledEnd = usesAbsoluteSentenceBounds ? sentenceEnd : sentenceEnd * scale
        let scaledTranslationRevealTimes = translationRevealIsAbsolute ? translationRevealTimes : translationRevealTimes.map { $0 * scale }
        let scaledTransliterationRevealTimes = translationRevealIsAbsolute ? adjustedTransliteration : adjustedTransliteration.map { $0 * scale }
        let scaledOriginalReveal = originalRevealIsAbsolute ? originalReveal : originalReveal.map { $0 * scale }

        let state: TextPlayerSentenceState = .active
        var variants: [TextPlayerVariantDisplay] = []

        func appendVariant(label: String, kind: TextPlayerVariantKind, tokens: [String], revealTimes: [Double], isActiveTrack: Bool) {
            guard !tokens.isEmpty else { return }
            let revealState = resolveVariantRevealState(
                tokens: tokens,
                revealTimes: revealTimes,
                sentenceState: state,
                effectiveTime: effectiveTime,
                startTime: scaledStart,
                endTime: scaledEnd,
                isActiveTrack: isActiveTrack
            )

            variants.append(
                TextPlayerVariantDisplay(
                    id: kind.rawValue,
                    label: label,
                    tokens: tokens,
                    revealedCount: revealState.revealedCount,
                    currentIndex: revealState.currentIndex,
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
        useCombinedPhases: Bool,
        timingVersion: String? = nil
    ) -> Int? {
        let usesAbsoluteTimeline = usesAbsoluteTiming(
            sentences: sentences,
            activeTimingTrack: activeTimingTrack
        ) || timingVersion == "2"
        if let timelineSentences = buildTimelineSentences(
            sentences: sentences,
            activeTimingTrack: activeTimingTrack,
            audioDuration: audioDuration,
            useCombinedPhases: useCombinedPhases,
            timingVersion: timingVersion
        ),
           let activeIndex = resolveActiveIndex(
               timelineSentences: timelineSentences,
               chunkTime: chunkTime,
               audioDuration: audioDuration,
               usesAbsoluteTiming: usesAbsoluteTimeline
           ) {
            return activeIndex
        }
        return resolveActiveSentenceResolution(
            sentences: sentences,
            activeTimingTrack: activeTimingTrack,
            chunkTime: chunkTime,
            audioDuration: audioDuration,
            useCombinedPhases: useCombinedPhases
        )?.index
    }
}
