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
        wordNormalized = try container.decode(String.self, forKey: .wordNormalized)
        cached = try container.decode(Bool.self, forKey: .cached)
        audioReferences = try container.decode([LookupCacheAudioRef].self, forKey: .audioReferences)
        lookupResult = try container.decodeIfPresent(LinguistLookupResult.self, forKey: .lookupResult)
    }
}

struct LookupCacheBulkResponse: Decodable {
    let results: [String: LookupCacheEntryResponse?]
    let cacheHits: Int
    let cacheMisses: Int

    enum CodingKeys: String, CodingKey {
        case results
        case cacheHits
        case cacheMisses
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        results = try container.decode([String: LookupCacheEntryResponse?].self, forKey: .results)
        cacheHits = try container.decode(Int.self, forKey: .cacheHits)
        cacheMisses = try container.decode(Int.self, forKey: .cacheMisses)
    }
}

struct LookupCacheSummaryResponse: Decodable {
    let available: Bool
    let wordCount: Int
    let inputLanguage: String?
    let definitionLanguage: String?
    let llmCalls: Int
    let skippedStopwords: Int
    let buildTimeSeconds: Double

    enum CodingKeys: String, CodingKey {
        case available
        case wordCount
        case inputLanguage
        case definitionLanguage
        case llmCalls
        case skippedStopwords
        case buildTimeSeconds
    }
}
