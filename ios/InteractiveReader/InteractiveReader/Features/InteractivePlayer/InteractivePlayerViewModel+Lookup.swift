import Foundation

extension InteractivePlayerViewModel {
    func lookupAssistant(
        query: String,
        inputLanguage: String,
        lookupLanguage: String,
        llmModel: String?
    ) async throws -> AssistantLookupResponse {
        guard let configuration = apiConfiguration else {
            throw AssistantLookupError.missingConfiguration
        }
        let client = APIClient(configuration: configuration)
        return try await client.assistantLookup(
            query: query,
            inputLanguage: inputLanguage,
            lookupLanguage: lookupLanguage,
            llmModel: llmModel
        )
    }

    func fetchLlmModels() async -> [String] {
        guard let configuration = apiConfiguration else {
            return []
        }
        let client = APIClient(configuration: configuration)
        do {
            let response = try await client.fetchLlmModels()
            return response.models
        } catch {
            return []
        }
    }

    func fetchVoiceInventory() async -> VoiceInventoryResponse? {
        guard let configuration = apiConfiguration else {
            return nil
        }
        let client = APIClient(configuration: configuration)
        do {
            return try await client.fetchVoiceInventory()
        } catch {
            return nil
        }
    }

    func synthesizePronunciation(text: String, language: String?, voice: String? = nil) async throws -> Data {
        guard let configuration = apiConfiguration else {
            throw PronunciationError.missingConfiguration
        }
        let client = APIClient(configuration: configuration)
        return try await client.synthesizeAudio(text: text, language: language, voice: voice)
    }

    // MARK: - Lookup Cache

    /// Attempt to fetch a cached lookup for a word from the job's lookup cache.
    /// Checks offline storage first, then falls back to API if not found locally.
    /// Returns nil if the cache doesn't exist or the word isn't cached.
    func fetchCachedLookup(jobId: String, word: String) async -> LookupCacheEntryResponse? {
        // Check offline cache first
        if let offlineCache = offlineLookupCache {
            let normalized = normalizeWordForLookup(word)
            if let entry = offlineCache.entries[normalized] {
                print("[LookupCache] OFFLINE HIT for '\(word)' (normalized: '\(normalized)')")
                return entry
            }
            print("[LookupCache] OFFLINE MISS for '\(word)' (normalized: '\(normalized)'), entries=\(offlineCache.entries.count)")
            // If we have offline cache but word not found, return a miss without API call
            // (the word simply doesn't exist in the cache)
            return LookupCacheEntryResponse(
                word: word,
                wordNormalized: normalized,
                cached: false,
                lookupResult: nil,
                audioReferences: []
            )
        }

        // Fallback to API (no offline cache available)
        print("[LookupCache] No offline cache, falling back to API for '\(word)'")
        guard let configuration = apiConfiguration else {
            print("[LookupCache] No API configuration and no offline cache")
            return nil
        }
        let client = APIClient(configuration: configuration)
        do {
            let result = try await client.fetchCachedLookup(jobId: jobId, word: word)
            if let result {
                print("[LookupCache] API \(result.cached ? "HIT" : "MISS") for '\(word)': hasResult=\(result.lookupResult != nil)")
            } else {
                print("[LookupCache] No API result for '\(word)'")
            }
            return result
        } catch {
            print("[LookupCache] Error fetching cache for '\(word)': \(error.localizedDescription)")
            return nil
        }
    }

    /// Normalize a word for lookup cache key matching.
    /// Mirrors the backend normalize_word() function: strips diacritics, lowercases, trims whitespace.
    private func normalizeWordForLookup(_ word: String) -> String {
        // Strip Arabic diacritics (tashkeel/harakat) - Unicode range U+064B to U+065F
        guard let startScalar = Unicode.Scalar(0x064B),
              let endScalar = Unicode.Scalar(0x065F) else {
            return word.lowercased().trimmingCharacters(in: .whitespacesAndNewlines)
        }
        let diacriticRange = startScalar...endScalar
        var result = ""
        for scalar in word.unicodeScalars {
            if !diacriticRange.contains(scalar) {
                result.append(Character(scalar))
            }
        }
        // Lowercase and trim
        return result.lowercased().trimmingCharacters(in: .whitespacesAndNewlines)
    }

    /// Fetch lookup cache summary for a job (total entries, languages, etc.)
    func fetchLookupCacheSummary(jobId: String) async -> LookupCacheSummaryResponse? {
        guard let configuration = apiConfiguration else {
            return nil
        }
        let client = APIClient(configuration: configuration)
        do {
            return try await client.fetchLookupCacheSummary(jobId: jobId)
        } catch {
            return nil
        }
    }
}
