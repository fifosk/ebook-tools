import Foundation
import OSLog

private let lookupCacheLogger = Logger(subsystem: "InteractiveReader", category: "LookupCache")

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
                lookupCacheLogger.debug(
                    "Offline hit word=\(word, privacy: .private) normalized=\(normalized, privacy: .private)"
                )
                return entry
            }
            lookupCacheLogger.debug(
                "Offline miss word=\(word, privacy: .private) normalized=\(normalized, privacy: .private), entries=\(offlineCache.entries.count, privacy: .public)"
            )
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
        lookupCacheLogger.debug("No offline cache, falling back to API word=\(word, privacy: .private)")
        guard let configuration = apiConfiguration else {
            lookupCacheLogger.warning("No API configuration and no offline cache")
            return nil
        }
        let client = APIClient(configuration: configuration)
        do {
            let result = try await client.fetchCachedLookup(jobId: jobId, word: word)
            if let result {
                lookupCacheLogger.debug(
                    "API cache result cached=\(result.cached, privacy: .public), hasResult=\(result.lookupResult != nil, privacy: .public), word=\(word, privacy: .private)"
                )
            } else {
                lookupCacheLogger.debug("No API result word=\(word, privacy: .private)")
            }
            return result
        } catch {
            lookupCacheLogger.error(
                "Error fetching cache word=\(word, privacy: .private): \(error.localizedDescription, privacy: .private)"
            )
            return nil
        }
    }

    /// Normalize a word for lookup cache key matching.
    /// Mirrors the backend normalize_word() function: strips diacritics, lowercases, trims whitespace.
    private func normalizeWordForLookup(_ word: String) -> String {
        let markRanges: [(UInt32, UInt32)] = [
            (0x0591, 0x05BD), // Hebrew cantillation/niqqud
            (0x05BF, 0x05BF), // Hebrew rafe
            (0x05C1, 0x05C2), // Hebrew shin/sin dots
            (0x05C4, 0x05C5), // Hebrew upper/lower dots
            (0x05C7, 0x05C7), // Hebrew qamats qatan
            (0x064B, 0x065F), // Arabic tashkeel/harakat
        ]
        let boundaryPunctuation = CharacterSet(charactersIn:
            ".,;:!?\"'()[]{}«»" +
            "\u{201E}\u{201C}\u{201F}\u{2018}\u{201A}\u{2019}\u{201B}" +
            "\u{060C}\u{061B}\u{061F}\u{066A}\u{066B}\u{066C}\u{066D}" +
            "\u{05BE}\u{05C0}\u{05C3}\u{05C6}" +
            "\u{3001}\u{3002}\u{FF0C}\u{FF0E}\u{FF1B}\u{FF1F}\u{FF01}" +
            "\u{2013}\u{2014}\u{2015}"
        )
        let trimSet = CharacterSet.whitespacesAndNewlines.union(boundaryPunctuation)
        var result = String.UnicodeScalarView()

        let canonicalWord = word.precomposedStringWithCanonicalMapping
        for scalar in canonicalWord.unicodeScalars {
            let value = scalar.value
            if markRanges.contains(where: { value >= $0.0 && value <= $0.1 }) {
                continue
            }
            result.append(scalar)
        }

        return String(result).lowercased().trimmingCharacters(in: trimSet)
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
