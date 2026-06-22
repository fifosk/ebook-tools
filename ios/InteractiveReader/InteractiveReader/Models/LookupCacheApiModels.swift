struct LookupCacheAudioRef: Decodable, Equatable {
    let chunkId: String
    let sentenceIdx: Int
    let tokenIdx: Int
    let track: String
    let t0: Double
    let t1: Double

    enum CodingKeys: String, CodingKey {
        case chunkId
        case sentenceIdx
        case tokenIdx
        case track
        case t0
        case t1
    }
}

struct LookupCacheEntryResponse: Decodable {
    let word: String
    let wordNormalized: String
    let cached: Bool
    let lookupResult: LinguistLookupResult?
    let audioReferences: [LookupCacheAudioRef]

    enum CodingKeys: String, CodingKey {
        case word
        case wordNormalized
        case cached
        case lookupResult
        case audioReferences
    }

    /// Convenience initializer for creating cache miss responses.
    init(word: String, wordNormalized: String, cached: Bool, lookupResult: LinguistLookupResult?, audioReferences: [LookupCacheAudioRef]) {
        self.word = word
        self.wordNormalized = wordNormalized
        self.cached = cached
        self.lookupResult = lookupResult
        self.audioReferences = audioReferences
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        word = try container.decode(String.self, forKey: .word)
        wordNormalized = (try? container.decode(String.self, forKey: .wordNormalized)) ?? word
        cached = (try? container.decode(Bool.self, forKey: .cached)) ?? false
        audioReferences = (try? container.decode([LookupCacheAudioRef].self, forKey: .audioReferences)) ?? []
        lookupResult = try? container.decode(LinguistLookupResult.self, forKey: .lookupResult)
    }
}

struct LookupCacheBulkResponse: Decodable {
    let jobId: String
    let words: [String]
    let entries: [LookupCacheEntryResponse]

    enum CodingKeys: String, CodingKey {
        case jobId
        case words
        case entries
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        jobId = try container.decode(String.self, forKey: .jobId)
        words = (try? container.decode([String].self, forKey: .words)) ?? []
        entries = (try? container.decode([LookupCacheEntryResponse].self, forKey: .entries)) ?? []
    }
}

struct LookupCacheSummaryResponse: Decodable {
    let jobId: String
    let totalEntries: Int
    let inputLanguage: String?
    let definitionLanguage: String?
    let cacheVersion: String?

    enum CodingKeys: String, CodingKey {
        case jobId
        case totalEntries
        case inputLanguage
        case definitionLanguage
        case cacheVersion
    }
}
