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

    static func buildTimelineSentences(
        sentences: [InteractiveChunk.Sentence],
        activeTimingTrack: TextPlayerTimingTrack,
        audioDuration: Double?,
        useCombinedPhases: Bool
    ) -> [TimelineSentenceRuntime]? {
        guard !sentences.isEmpty else { return nil }

        var offset = 0.0
        var result: [TimelineSentenceRuntime] = []

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

            let sentenceStart = offset

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
            if !isOriginalTrack && !translationDurationsRaw.isEmpty {
                var cumulativeTranslation = 0.0
                for rawDuration in translationDurationsRaw {
                    translationRevealTimes.append(translationTrackStart + cumulativeTranslation)
                    cumulativeTranslation += rawDuration
                }
            }

            if !isOriginalTrack && translationRevealTimes.count != translationTokens.count && !translationTokens.isEmpty {
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

            if !isOriginalTrack && !translationRevealTimes.isEmpty {
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
                originalReveal = buildUniformRevealTimes(
                    count: originalTokens.count,
                    startTime: sentenceStart,
                    duration: originalPhaseDuration
                )
            }

            let sentenceDuration: Double = {
                if useCombinedPhases {
                    return originalPhaseDuration + gapBeforeTranslation + translationTotalDuration
                }
                if isOriginalTrack {
                    return originalPhaseDuration
                }
                return translationTotalDuration
            }()
            let endTime = sentenceStart + sentenceDuration

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

        if !useCombinedPhases,
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

        let timelineTotalDuration = timelineSentences.last?.endTime
        let effectiveTime: Double = {
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

        let epsilon = 1e-3
        var activeIndex: Int? = nil
        for runtime in timelineSentences {
            if effectiveTime >= runtime.startTime - epsilon && effectiveTime <= runtime.endTime + epsilon {
                activeIndex = runtime.index
                break
            }
        }
        if activeIndex == nil {
            for runtime in timelineSentences.reversed() {
                if effectiveTime > runtime.endTime + epsilon {
                    activeIndex = runtime.index
                    break
                }
            }
        }
        if activeIndex == nil {
            activeIndex = timelineSentences.first?.index ?? 0
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
                if safeTime >= runtime.endTime - epsilon {
                    revealedCount = tokens.count
                }
                if !revealTimes.isEmpty,
                   state == .active,
                   safeTime >= runtime.startTime - epsilon,
                   revealedCount == 0 {
                    revealedCount = 1
                }

                var currentIndex: Int? = revealedCount > 0 ? revealedCount - 1 : nil
                if !tokens.isEmpty && (state == .past || safeTime >= runtime.endTime - epsilon) {
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

    static func buildStaticDisplay(
        sentences: [InteractiveChunk.Sentence],
        activeIndex: Int? = nil,
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

    static func selectActiveSentence(from sentences: [TextPlayerSentenceDisplay]) -> [TextPlayerSentenceDisplay] {
        guard !sentences.isEmpty else { return [] }
        if let active = sentences.first(where: { $0.state == .active }) {
            return [active]
        }
        return [sentences[0]]
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
