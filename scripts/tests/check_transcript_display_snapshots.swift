import Darwin
import Foundation

struct WordTimingToken {
    let id: String
    let text: String
    let sentenceIndex: Int?
    let startTime: Double
    let endTime: Double
    let fileIndex: Int?
}

struct ChunkSentenceTimelineEvent {
    let duration: Double
    let originalIndex: Int
    let translationIndex: Int
    let transliterationIndex: Int
}

struct ChunkSentencePhaseDurations {
    let original: Double?
    let translation: Double?
    let gap: Double?
    let tail: Double?
}

struct InteractiveChunk {
    struct Sentence: Identifiable {
        let id: Int
        let displayIndex: Int?
        let originalText: String
        let translationText: String
        let transliterationText: String?
        let originalTokens: [String]
        let translationTokens: [String]
        let transliterationTokens: [String]
        let imagePath: String?
        let timingTokens: [WordTimingToken]
        let originalTimingTokens: [WordTimingToken]
        let timeline: [ChunkSentenceTimelineEvent]
        let totalDuration: Double?
        let phaseDurations: ChunkSentencePhaseDurations?
        let startGate: Double?
        let endGate: Double?
        let originalStartGate: Double?
        let originalEndGate: Double?
    }
}

private func fail(_ message: String) -> Never {
    fputs("Transcript display snapshot check failed: \(message)\n", stderr)
    exit(1)
}

private func requireEqual(_ actual: String, _ expected: String, _ message: String) {
    if actual != expected {
        fail("\(message).\nExpected:\n\(expected)\n\nGot:\n\(actual)")
    }
}

private func requireEqual<T: Equatable>(_ actual: T, _ expected: T, _ message: String) {
    if actual != expected {
        fail("\(message). Expected \(expected), got \(actual).")
    }
}

private func requireNil<T>(_ actual: T?, _ message: String) {
    if let actual {
        fail("\(message). Expected nil, got \(actual).")
    }
}

private func token(
    _ text: String,
    start: Double,
    end: Double,
    sentenceIndex: Int? = nil
) -> WordTimingToken {
    WordTimingToken(
        id: "\(text)-\(start)",
        text: text,
        sentenceIndex: sentenceIndex,
        startTime: start,
        endTime: end,
        fileIndex: nil
    )
}

private func event(
    duration: Double,
    originalIndex: Int,
    translationIndex: Int,
    transliterationIndex: Int
) -> ChunkSentenceTimelineEvent {
    ChunkSentenceTimelineEvent(
        duration: duration,
        originalIndex: originalIndex,
        translationIndex: translationIndex,
        transliterationIndex: transliterationIndex
    )
}

private func sentence(
    id: Int,
    displayIndex: Int?,
    originalTokens: [String] = ["one", "two", "three"],
    transliterationTokens: [String] = ["bir", "iki"],
    translationTokens: [String] = ["uno", "dos", "tres"],
    timingTokens: [WordTimingToken] = [],
    originalTimingTokens: [WordTimingToken] = [],
    timeline: [ChunkSentenceTimelineEvent] = [],
    totalDuration: Double? = nil,
    phaseDurations: ChunkSentencePhaseDurations? = nil,
    startGate: Double? = nil,
    endGate: Double? = nil,
    originalStartGate: Double? = nil,
    originalEndGate: Double? = nil
) -> InteractiveChunk.Sentence {
    InteractiveChunk.Sentence(
        id: id,
        displayIndex: displayIndex,
        originalText: originalTokens.joined(separator: " "),
        translationText: translationTokens.joined(separator: " "),
        transliterationText: transliterationTokens.joined(separator: " "),
        originalTokens: originalTokens,
        translationTokens: translationTokens,
        transliterationTokens: transliterationTokens,
        imagePath: nil,
        timingTokens: timingTokens,
        originalTimingTokens: originalTimingTokens,
        timeline: timeline,
        totalDuration: totalDuration,
        phaseDurations: phaseDurations,
        startGate: startGate,
        endGate: endGate,
        originalStartGate: originalStartGate,
        originalEndGate: originalEndGate
    )
}

private func snapshot(_ display: TextPlayerSentenceDisplay) -> String {
    let variants = display.variants
        .map { variant in
            let current = variant.currentIndex.map(String.init) ?? "-"
            let seekTimes = variant.seekTimes?.map { String(format: "%.2f", $0) }.joined(separator: ",") ?? "-"
            return "\(variant.kind.rawValue):\(variant.revealedCount)/\(variant.tokens.count)@\(current){\(seekTimes)}"
        }
        .joined(separator: "|")
    let sentenceNumber = display.sentenceNumber.map(String.init) ?? "-"
    return "\(display.id)#\(display.index)#\(sentenceNumber)#\(display.state)#\(variants)"
}

private func snapshot(_ displays: [TextPlayerSentenceDisplay]) -> String {
    displays.map(snapshot).joined(separator: "\n")
}

private func runChecks() {
    let sentences = [
        sentence(id: 10, displayIndex: 100),
        sentence(
            id: 11,
            displayIndex: 101,
            originalTokens: ["alpha", "beta"],
            transliterationTokens: ["alfa"],
            translationTokens: ["a", "b"]
        )
    ]

    requireEqual(
        snapshot(TextPlayerTimeline.buildStaticDisplay(sentences: sentences, activeIndex: 1)),
        """
        sentence-0#0#100#future#original:3/3@2{-}|transliteration:2/2@1{-}|translation:3/3@2{-}
        sentence-1#1#101#active#original:2/2@1{-}|transliteration:1/1@0{-}|translation:2/2@1{-}
        """,
        "Static display should fully reveal all available variants and mark the requested active sentence"
    )

    requireEqual(
        snapshot(TextPlayerTimeline.buildInitialDisplay(sentences: sentences, activeIndex: 0, primaryTrack: .original)!),
        "sentence-0#0#100#active#original:1/3@0{-}|transliteration:0/2@-{-}|translation:0/3@-{-}",
        "Initial original display should reveal only the first original token"
    )
    requireEqual(
        snapshot(TextPlayerTimeline.buildInitialDisplay(sentences: sentences, activeIndex: 0, primaryTrack: .translation)!),
        "sentence-0#0#100#active#original:0/3@-{-}|transliteration:1/2@0{-}|translation:1/3@0{-}",
        "Initial translation display should reveal the first translation-side tokens"
    )

    requireEqual(
        snapshot(TextPlayerTimeline.buildTrackSwitchDisplay(sentences: sentences, activeIndex: 0, newPrimaryTrack: .translation)!),
        "sentence-0#0#100#active#original:3/3@2{-}|transliteration:0/2@-{-}|translation:0/3@-{-}",
        "Switching to translation should leave original fully revealed and reset translation-side variants"
    )
    requireEqual(
        snapshot(TextPlayerTimeline.buildTrackSwitchDisplay(sentences: sentences, activeIndex: 0, newPrimaryTrack: .original)!),
        "sentence-0#0#100#active#original:0/3@-{-}|transliteration:2/2@1{-}|translation:3/3@2{-}",
        "Switching to original should reset original and leave translation-side variants fully revealed"
    )

    requireEqual(
        snapshot(TextPlayerTimeline.buildDwellDisplay(sentences: sentences, activeIndex: 0, currentTrack: .translation)!),
        "sentence-0#0#100#active#original:0/3@-{-}|transliteration:2/2@1{-}|translation:3/3@2{-}",
        "Translation dwell should show only translation-side variants as finished"
    )
    requireEqual(
        snapshot(TextPlayerTimeline.buildFullyRevealedDisplay(sentences: sentences, activeIndex: 1)!),
        "sentence-1#1#101#active#original:2/2@1{-}|transliteration:1/1@0{-}|translation:2/2@1{-}",
        "Fully revealed display should reveal every variant in the selected sentence"
    )

    let settlingSentence = sentence(
        id: 20,
        displayIndex: 200,
        timingTokens: [
            token("uno", start: 0.0, end: 0.3),
            token("dos", start: 0.5, end: 0.8),
            token("tres", start: 1.5, end: 1.8)
        ],
        totalDuration: 1.5,
        startGate: 0.0,
        endGate: 1.8
    )
    requireEqual(
        snapshot(
            TextPlayerTimeline.buildSettlingDisplay(
                sentences: [settlingSentence],
                activeIndex: 0,
                newPrimaryTrack: .translation,
                chunkTime: 0.6,
                audioDuration: 1.8
            )!
        ),
        "sentence-0#0#200#active#original:3/3@2{-}|transliteration:1/2@0{0.00,1.80}|translation:2/3@1{0.00,0.50,1.50}",
        "Settling display should combine the completed previous track with live translation reveal timing"
    )

    let translationSeekSentences = [
        sentence(
            id: 30,
            displayIndex: 300,
            originalTokens: ["first", "source"],
            transliterationTokens: ["eerste", "bron"],
            translationTokens: ["eerste", "nederlandse", "zin"],
            timingTokens: [
                token("eerste", start: 10.00, end: 10.20),
                token("nederlandse", start: 10.75, end: 11.10),
                token("zin", start: 11.50, end: 11.80)
            ],
            totalDuration: 1.80,
            startGate: 10.00,
            endGate: 11.90
        ),
        sentence(
            id: 31,
            displayIndex: 301,
            originalTokens: ["second", "source"],
            transliterationTokens: ["tweede", "bron"],
            translationTokens: ["tweede", "zin"],
            timingTokens: [
                token("tweede", start: 12.20, end: 12.50),
                token("zin", start: 12.90, end: 13.20)
            ],
            totalDuration: 1.20,
            startGate: 12.20,
            endGate: 13.40
        )
    ]

    requireEqual(
        snapshot(
            TextPlayerTimeline.buildActiveSentenceDisplay(
                sentences: translationSeekSentences,
                activeTimingTrack: .translation,
                chunkTime: 10.90,
                audioDuration: 13.40,
                useCombinedPhases: false
            )!
        ),
        "sentence-0#0#300#active#original:0/2@-{}|transliteration:1/2@0{10.00,11.90}|translation:2/3@1{10.00,10.75,11.50}",
        "Translation-only slider seeks should return live translated-word highlighting after the audio reaches the target sentence"
    )
    let translationStartOnlyGateSentences = [
        sentence(
            id: 40,
            displayIndex: 400,
            originalTokens: ["first", "source"],
            transliterationTokens: ["eerste", "bron"],
            translationTokens: ["eerste", "nederlandse", "zin"],
            timingTokens: [
                token("eerste", start: 10.00, end: 10.20),
                token("nederlandse", start: 10.75, end: 11.10),
                token("zin", start: 11.50, end: 11.80)
            ],
            totalDuration: 1.80,
            startGate: 10.00
        ),
        sentence(
            id: 41,
            displayIndex: 401,
            originalTokens: ["second", "source"],
            transliterationTokens: ["tweede", "bron"],
            translationTokens: ["tweede", "zin"],
            timingTokens: [
                token("tweede", start: 12.20, end: 12.50),
                token("zin", start: 12.90, end: 13.20)
            ],
            totalDuration: 1.20,
            startGate: 12.20
        )
    ]
    requireEqual(
        TextPlayerTimeline.resolveActiveIndex(
            sentences: translationStartOnlyGateSentences,
            activeTimingTrack: .translation,
            chunkTime: 10.90,
            audioDuration: 13.40,
            useCombinedPhases: false
        ),
        0,
        "Start-only translation gates should still resolve active rendering in audio time"
    )
    requireEqual(
        snapshot(
            TextPlayerTimeline.buildActiveSentenceDisplay(
                sentences: translationStartOnlyGateSentences,
                activeTimingTrack: .translation,
                chunkTime: 10.90,
                audioDuration: 13.40,
                useCombinedPhases: false
            )!
        ),
        "sentence-0#0#400#active#original:0/2@-{}|transliteration:1/2@0{10.00,12.20}|translation:2/3@1{10.00,10.75,11.50}",
        "Translation-only rendering should stay on the sought sentence when jobs provide start gates without end gates"
    )

    let stretchedTranslationSentences = [
        sentence(
            id: 50,
            displayIndex: 500,
            originalTokens: ["first", "source"],
            transliterationTokens: [],
            translationTokens: ["eerste", "zin"],
            timingTokens: [
                token("eerste", start: 0.00, end: 1.00),
                token("zin", start: 2.50, end: 5.00)
            ],
            totalDuration: 5.00,
            startGate: 0.00,
            endGate: 5.00
        ),
        sentence(
            id: 51,
            displayIndex: 501,
            originalTokens: ["second", "source"],
            transliterationTokens: [],
            translationTokens: ["tweede", "lange", "zin"],
            timingTokens: [
                token("tweede", start: 5.00, end: 6.00),
                token("lange", start: 7.50, end: 8.50),
                token("zin", start: 9.00, end: 10.00)
            ],
            totalDuration: 5.00,
            startGate: 5.00,
            endGate: 10.00
        )
    ]
    requireEqual(
        snapshot(
            TextPlayerTimeline.buildActiveSentenceDisplay(
                sentences: stretchedTranslationSentences,
                activeTimingTrack: .translation,
                chunkTime: 12.00,
                audioDuration: 20.00,
                useCombinedPhases: false
            )!
        ),
        "sentence-1#1#501#active#original:0/2@-{}|translation:1/3@0{5.00,7.50,9.00}",
        "Translation-only word highlighting should use the timeline runtime so stretched audio does not reveal the whole next sentence too early"
    )

    let selectedFallback = TextPlayerTimeline.selectActiveSentence(
        from: TextPlayerTimeline.buildStaticDisplay(sentences: sentences, activeIndex: nil)
    )
    requireEqual(
        snapshot(selectedFallback),
        "sentence-0#0#100#active#original:3/3@2{-}|transliteration:2/2@1{-}|translation:3/3@2{-}",
        "Active selection should return the active sentence from static display"
    )

    requireNil(
        TextPlayerTimeline.buildInitialDisplay(sentences: sentences, activeIndex: 9, primaryTrack: .original),
        "Out-of-range initial display should be nil"
    )
    requireEqual(
        snapshot(TextPlayerTimeline.buildStaticDisplay(sentences: [], activeIndex: 0)),
        "",
        "Empty static display should remain empty"
    )
}

@main
private struct TranscriptDisplaySnapshotCheck {
    static func main() {
        runChecks()
    }
}
