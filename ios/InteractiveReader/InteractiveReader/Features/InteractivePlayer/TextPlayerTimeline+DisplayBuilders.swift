import Foundation

// MARK: - Static Display Builders

extension TextPlayerTimeline {

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
    /// Shows the current track fully revealed (just finished) and other tracks at 0 (unrevealed)
    /// - Parameters:
    ///   - sentences: All sentences in the chunk
    ///   - activeIndex: The current sentence index
    ///   - currentTrack: The track that just finished playing (fully revealed)
    static func buildDwellDisplay(
        sentences: [InteractiveChunk.Sentence],
        activeIndex: Int,
        currentTrack: TextPlayerTimingTrack
    ) -> TextPlayerSentenceDisplay? {
        guard sentences.indices.contains(activeIndex) else { return nil }
        let sentence = sentences[activeIndex]
        var variants: [TextPlayerVariantDisplay] = []

        func appendVariant(label: String, kind: TextPlayerVariantKind, tokens: [String]) {
            guard !tokens.isEmpty else { return }

            let revealedCount: Int
            let currentIndex: Int?

            // Determine if this variant belongs to the current (finished) track
            let isCurrentTrack: Bool
            switch currentTrack {
            case .original:
                isCurrentTrack = (kind == .original)
            case .translation, .mix:
                isCurrentTrack = (kind == .translation || kind == .transliteration)
            }

            if isCurrentTrack {
                // Current track just finished - fully revealed with last word highlighted
                revealedCount = tokens.count
                currentIndex = tokens.count - 1
            } else {
                // Not the current track - show at 0 (unrevealed/green) to avoid any highlighting
                // This applies to:
                // - Same sentence: next track about to start (will animate when it plays)
                // - Next sentence: the other track shouldn't be highlighted during dwell
                // Setting revealedCount = 0 ensures the fallback in playbackPrimaryTokenIndex()
                // won't return a highlight index
                revealedCount = 0
                currentIndex = nil
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
}
