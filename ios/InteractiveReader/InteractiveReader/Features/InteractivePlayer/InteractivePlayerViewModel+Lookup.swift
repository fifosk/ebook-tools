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

    func synthesizePronunciation(text: String, language: String?) async throws -> Data {
        guard let configuration = apiConfiguration else {
            throw PronunciationError.missingConfiguration
        }
        let client = APIClient(configuration: configuration)
        return try await client.synthesizeAudio(text: text, language: language)
    }
}
