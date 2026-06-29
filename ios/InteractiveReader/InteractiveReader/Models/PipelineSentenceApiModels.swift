import Foundation

struct ChunkMetadataPayload: Decodable {
    let sentences: [ChunkSentenceMetadata]

    enum CodingKeys: String, CodingKey {
        case sentences
    }

    init(sentences: [ChunkSentenceMetadata] = []) {
        self.sentences = sentences
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        sentences = (try? container.decode([ChunkSentenceMetadata].self, forKey: .sentences)) ?? []
    }
}

struct ChunkSentenceMetadata: Decodable, Identifiable {
    var id: Int { sentenceNumber ?? UUID().hashValue }
    let sentenceNumber: Int?
    let original: ChunkSentenceVariant
    let translation: ChunkSentenceVariant?
    let transliteration: ChunkSentenceVariant?
    let imagePath: String?
    let timeline: [ChunkSentenceTimelineEvent]
    let totalDuration: Double?
    let highlightGranularity: String?
    let counts: [String: Int]
    let phaseDurations: ChunkSentencePhaseDurations?
    // Sentence gate fields for sequence playback
    let startGate: Double?
    let endGate: Double?
    let originalStartGate: Double?
    let originalEndGate: Double?

    enum CodingKeys: String, CodingKey {
        case sentenceNumber = "sentenceNumber"
        case original
        case translation
        case transliteration
        case imagePath = "imagePath"
        case timeline
        case totalDuration = "totalDuration"
        case highlightGranularity = "highlightGranularity"
        case counts
        case phaseDurations = "phaseDurations"
        case startGate = "startGate"
        case endGate = "endGate"
        case originalStartGate = "originalStartGate"
        case originalEndGate = "originalEndGate"
    }

    private enum SnakeCodingKeys: String, CodingKey {
        case sentenceNumber = "sentence_number"
    }

    init(sentenceNumber: Int?, original: ChunkSentenceVariant, translation: ChunkSentenceVariant?, transliteration: ChunkSentenceVariant?) {
        self.sentenceNumber = sentenceNumber
        self.original = original
        self.translation = translation
        self.transliteration = transliteration
        imagePath = nil
        timeline = []
        totalDuration = nil
        highlightGranularity = nil
        counts = [:]
        phaseDurations = nil
        startGate = nil
        endGate = nil
        originalStartGate = nil
        originalEndGate = nil
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        let snakeContainer = try? decoder.container(keyedBy: SnakeCodingKeys.self)
        sentenceNumber = (try? container.decode(Int.self, forKey: .sentenceNumber))
            ?? (try? snakeContainer?.decode(Int.self, forKey: .sentenceNumber))

        let originalValue = try? container.decode(ChunkSentenceVariant.self, forKey: .original)
        let translationValue = try? container.decode(ChunkSentenceVariant.self, forKey: .translation)
        let transliterationValue = try? container.decode(ChunkSentenceVariant.self, forKey: .transliteration)

        if let originalValue {
            original = originalValue
        } else if let translationValue {
            original = translationValue
        } else {
            original = ChunkSentenceVariant(text: "", tokens: nil)
        }

        translation = translationValue
        transliteration = transliterationValue

        imagePath = (try? container.decode(String.self, forKey: .imagePath))?.nonEmptyValue

        timeline = (try? container.decode([ChunkSentenceTimelineEvent].self, forKey: .timeline)) ?? []
        totalDuration = try? container.decode(Double.self, forKey: .totalDuration)
        highlightGranularity = try? container.decode(String.self, forKey: .highlightGranularity)
        counts = (try? container.decode([String: Int].self, forKey: .counts)) ?? [:]
        phaseDurations = try? container.decode(ChunkSentencePhaseDurations.self, forKey: .phaseDurations)
        startGate = try? container.decode(Double.self, forKey: .startGate)
        endGate = try? container.decode(Double.self, forKey: .endGate)
        originalStartGate = try? container.decode(Double.self, forKey: .originalStartGate)
        originalEndGate = try? container.decode(Double.self, forKey: .originalEndGate)
    }
}

struct ChunkSentenceVariant: Decodable {
    let text: String
    let tokens: [String]?

    enum CodingKeys: String, CodingKey {
        case text
        case tokens
    }

    init(text: String, tokens: [String]?) {
        self.text = text
        self.tokens = tokens
    }

    init(from decoder: Decoder) throws {
        if let singleContainer = try? decoder.singleValueContainer(),
           let textValue = try? singleContainer.decode(String.self) {
            text = textValue
            tokens = nil
            return
        }

        let container = try decoder.container(keyedBy: CodingKeys.self)
        text = (try? container.decode(String.self, forKey: .text)) ?? ""
        tokens = try? container.decode([String].self, forKey: .tokens)
    }
}

struct ChunkSentenceTimelineEvent: Decodable {
    let duration: Double
    let originalIndex: Int
    let translationIndex: Int
    let transliterationIndex: Int

    enum CodingKeys: String, CodingKey {
        case duration
        case originalIndex = "original_index"
        case translationIndex = "translation_index"
        case transliterationIndex = "transliteration_index"
        case originalIndexCamel = "originalIndex"
        case translationIndexCamel = "translationIndex"
        case transliterationIndexCamel = "transliterationIndex"
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        duration = (try? container.decode(Double.self, forKey: .duration)) ?? 0
        originalIndex = (try? container.decode(Int.self, forKey: .originalIndex))
            ?? (try? container.decode(Int.self, forKey: .originalIndexCamel))
            ?? 0
        translationIndex = (try? container.decode(Int.self, forKey: .translationIndex))
            ?? (try? container.decode(Int.self, forKey: .translationIndexCamel))
            ?? 0
        transliterationIndex = (try? container.decode(Int.self, forKey: .transliterationIndex))
            ?? (try? container.decode(Int.self, forKey: .transliterationIndexCamel))
            ?? 0
    }
}

struct ChunkSentencePhaseDurations: Decodable {
    let original: Double?
    let translation: Double?
    let gap: Double?
    let tail: Double?

    enum CodingKeys: String, CodingKey {
        case original
        case translation
        case gap
        case tail
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        original = try? container.decode(Double.self, forKey: .original)
        translation = try? container.decode(Double.self, forKey: .translation)
        gap = try? container.decode(Double.self, forKey: .gap)
        tail = try? container.decode(Double.self, forKey: .tail)
    }
}
