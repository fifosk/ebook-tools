import Foundation

struct JobContext {
    let jobId: String
    let highlightingPolicy: String?
    let hasEstimatedSegments: Bool
    let chunks: [InteractiveChunk]

    private let chunkIndex: [String: Int]

    init(jobId: String, highlightingPolicy: String?, hasEstimatedSegments: Bool, chunks: [InteractiveChunk]) {
        self.jobId = jobId
        self.highlightingPolicy = highlightingPolicy
        self.hasEstimatedSegments = hasEstimatedSegments
        self.chunks = chunks
        self.chunkIndex = Dictionary(uniqueKeysWithValues: chunks.enumerated().map { ($0.element.id, $0.offset) })
    }

    func chunk(withID id: String) -> InteractiveChunk? {
        guard let index = chunkIndex[id], chunks.indices.contains(index) else {
            return nil
        }
        return chunks[index]
    }

    func nextChunk(after id: String) -> InteractiveChunk? {
        guard let index = chunkIndex[id] else { return nil }
        let nextIndex = index + 1
        guard chunks.indices.contains(nextIndex) else { return nil }
        return chunks[nextIndex]
    }

    func previousChunk(before id: String) -> InteractiveChunk? {
        guard let index = chunkIndex[id] else { return nil }
        let previousIndex = index - 1
        guard chunks.indices.contains(previousIndex) else { return nil }
        return chunks[previousIndex]
    }
}

struct InteractivePlayerHeaderInfo {
    let title: String
    let author: String
    let itemTypeLabel: String
    let coverURL: URL?
    let secondaryCoverURL: URL?
    let languageFlags: [LanguageFlagEntry]
    let translationModel: String?
}

struct TextPlayerWordSelection: Hashable {
    let sentenceIndex: Int
    let variantKind: TextPlayerVariantKind
    let tokenIndex: Int
}

struct SentenceOption: Identifiable, Hashable {
    let id: Int
    let label: String
    let startTime: Double?
}

struct SentenceRange: Hashable {
    let start: Int
    let end: Int
}

enum InteractivePlayerFocusArea: Hashable {
    case controls
    case transcript
    case bubble
}

struct ChapterNavigationEntry: Identifiable, Hashable {
    let id: String
    let title: String
    let startSentence: Int
    let endSentence: Int?
}

struct InteractiveChunk: Identifiable {
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
        let timeline: [ChunkSentenceTimelineEvent]
        let totalDuration: Double?
        let phaseDurations: ChunkSentencePhaseDurations?
    }

    struct AudioOption: Identifiable {
        enum Kind: String {
            case combined
            case translation
            case original
            case other
        }

        let id: String
        let label: String
        let kind: Kind
        let streamURLs: [URL]
        let timingURL: URL?
        let duration: Double?

        var primaryURL: URL {
            streamURLs[0]
        }
    }

    let id: String
    let label: String
    let rangeFragment: String?
    let rangeDescription: String?
    let startSentence: Int?
    let endSentence: Int?
    let sentences: [Sentence]
    let audioOptions: [AudioOption]
}

struct WordTimingToken: Identifiable {
    let id: String
    let text: String
    let sentenceIndex: Int?
    let startTime: Double
    let endTime: Double

    var displayText: String {
        text.isEmpty ? "" : text
    }

    func isActive(at time: Double, tolerance: Double = 0.02) -> Bool {
        guard time.isFinite else { return false }
        let start = startTime - tolerance
        let end = endTime + tolerance
        return time >= start && time <= end
    }
}

struct PendingSentenceJump {
    let chunkID: String
    let sentenceNumber: Int
}

extension WordTimingToken {
    init?(entry: JobTimingEntry) {
        guard let start = entry.t0 ?? entry.start ?? entry.begin ?? entry.time,
              let endValue = entry.t1 ?? entry.end ?? entry.stop ?? entry.time else {
            return nil
        }
        let textValue = entry.text?.nonEmptyValue ?? entry.token?.nonEmptyValue ?? ""
        let sentenceIndex = entry.sentenceIdx ?? entry.sentenceIdMixed ?? Int(entry.sentenceID ?? "")
        let identifier = entry.rawID ?? UUID().uuidString
        self.init(
            id: identifier,
            text: textValue,
            sentenceIndex: sentenceIndex,
            startTime: min(start, endValue),
            endTime: max(endValue, start)
        )
    }
}

extension InteractiveChunk.Sentence {
    var startTime: Double? {
        guard !timingTokens.isEmpty else { return nil }
        return timingTokens.map(\.startTime).min()
    }

    var endTime: Double? {
        guard !timingTokens.isEmpty else { return nil }
        return timingTokens.map(\.endTime).max()
    }

    func contains(time: Double) -> Bool {
        guard let start = startTime, let end = endTime else { return false }
        return time >= start && time <= end
    }
}
