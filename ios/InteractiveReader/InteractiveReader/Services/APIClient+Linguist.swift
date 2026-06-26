import Foundation

extension APIClient {
    func assistantLookup(
        query: String,
        inputLanguage: String,
        lookupLanguage: String,
        llmModel: String? = nil
    ) async throws -> AssistantLookupResponse {
        let payload = AssistantLookupRequest(
            query: query,
            inputLanguage: inputLanguage,
            lookupLanguage: lookupLanguage,
            llmModel: llmModel
        )
        let data = try await sendJSONRequest(path: "/api/assistant/lookup", method: "POST", payload: payload)
        return try decode(AssistantLookupResponse.self, from: data)
    }

    func fetchCachedLookup(jobId: String, word: String) async throws -> LookupCacheEntryResponse? {
        let encodedJob = AppleAPIPathComponentEncoding.encode(jobId)
        // Use alphanumerics to force percent-encoding of non-ASCII characters (Arabic, etc.)
        // This ensures the URL is properly encoded for the server to decode.
        let encodedWord = word.addingPercentEncoding(withAllowedCharacters: .alphanumerics) ?? word
        let path = "/api/pipelines/jobs/\(encodedJob)/lookup-cache/\(encodedWord)"
        logger.debug("Lookup cache request job=\(encodedJob, privacy: .private) wordLength=\(word.count, privacy: .public)")
        guard let data = try await sendRequestAllowingNotFound(path: path) else {
            logger.debug("Lookup cache miss job=\(encodedJob, privacy: .private)")
            return nil
        }
        logger.debug("Lookup cache response bytes=\(data.count, privacy: .public)")
        return try decode(LookupCacheEntryResponse.self, from: data)
    }

    func fetchCachedLookupsBulk(jobId: String, words: [String]) async throws -> LookupCacheBulkResponse? {
        guard !words.isEmpty else { return nil }
        let encodedJob = AppleAPIPathComponentEncoding.encode(jobId)
        struct BulkRequest: Encodable { let words: [String] }
        let data = try await sendJSONRequest(
            path: "/api/pipelines/jobs/\(encodedJob)/lookup-cache/bulk",
            method: "POST",
            payload: BulkRequest(words: words)
        )
        return try decode(LookupCacheBulkResponse.self, from: data)
    }

    func fetchLookupCacheSummary(jobId: String) async throws -> LookupCacheSummaryResponse? {
        let encodedJob = AppleAPIPathComponentEncoding.encode(jobId)
        guard let data = try await sendRequestAllowingNotFound(
            path: "/api/pipelines/jobs/\(encodedJob)/lookup-cache/summary"
        ) else {
            return nil
        }
        return try decode(LookupCacheSummaryResponse.self, from: data)
    }

    /// Fetch the complete lookup cache JSON for offline storage.
    /// Returns raw Data to avoid decoding until needed.
    func fetchLookupCacheRaw(jobId: String) async throws -> Data? {
        let encodedJob = AppleAPIPathComponentEncoding.encode(jobId)
        return try await sendRequestAllowingNotFound(
            path: "/api/pipelines/jobs/\(encodedJob)/lookup-cache"
        )
    }

    func fetchLlmModels() async throws -> LLMModelListResponse {
        let data = try await sendRequest(path: AppleCreateRuntimeContract.pipelineLlmModelsPath)
        return try decode(LLMModelListResponse.self, from: data)
    }

    func fetchVoiceInventory() async throws -> VoiceInventoryResponse {
        let data = try await sendRequest(path: AppleCreateRuntimeContract.audioVoicesPath)
        return try decode(VoiceInventoryResponse.self, from: data)
    }

    func synthesizeAudio(text: String, language: String?, voice: String? = nil, speed: Int? = nil) async throws -> Data {
        let payload = AudioSynthesisRequest(text: text, voice: voice, speed: speed, language: language)
        let encoder = JSONEncoder()
        let body = try encoder.encode(payload)
        return try await sendRequest(
            path: "/api/audio",
            method: "POST",
            body: body,
            contentType: "application/json",
            accept: "audio/mpeg"
        )
    }

    func searchMedia(jobId: String, query: String, limit: Int = 25) async throws -> MediaSearchResponse {
        let trimmed = query.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else {
            return MediaSearchResponse(query: "", limit: limit, count: 0, results: [])
        }
        var components = URLComponents()
        components.queryItems = [
            URLQueryItem(name: "query", value: trimmed),
            URLQueryItem(name: "limit", value: "\(limit)"),
            URLQueryItem(name: "job_id", value: jobId),
        ]
        let suffix = components.percentEncodedQuery.map { "?\($0)" } ?? ""
        let data = try await sendRequest(path: "/api/pipelines/search\(suffix)")
        logger.debug("Media search response bytes=\(data.count, privacy: .public)")
        return try decode(MediaSearchResponse.self, from: data)
    }
}
