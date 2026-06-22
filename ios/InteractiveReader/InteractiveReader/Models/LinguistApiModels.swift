import Foundation
import OSLog

private let linguistApiModelsLogger = Logger(subsystem: "InteractiveReader", category: "LinguistApiModels")

struct AssistantLookupRequest: Encodable {
    let query: String
    let inputLanguage: String
    let lookupLanguage: String
    let llmModel: String?

    enum CodingKeys: String, CodingKey {
        case query
        case inputLanguage = "input_language"
        case lookupLanguage = "lookup_language"
        case llmModel = "llm_model"
    }
}

struct AssistantLookupResponse: Decodable {
    let answer: String
    let model: String
    let tokenUsage: [String: Int]?
    let source: String?
}

enum LinguistLookupType: String, Codable {
    case word
    case phrase
    case sentence
}

struct LinguistRelatedLanguage: Codable, Identifiable {
    let language: String
    let word: String
    let transliteration: String?

    var id: String { "\(language)-\(word)" }
}

struct LinguistLookupResult: Codable {
    let type: LinguistLookupType
    let definition: String
    let partOfSpeech: String?
    let pronunciation: String?
    let etymology: String?
    let example: String?
    let exampleTranslation: String?
    let exampleTransliteration: String?
    let idioms: [String]?
    let relatedLanguages: [LinguistRelatedLanguage]?

    // NOTE: No explicit CodingKeys here!
    // When decoded via APIClient (which uses .convertFromSnakeCase), the decoder
    // automatically maps snake_case JSON keys to camelCase Swift properties.
    // When decoded via parse() for live LLM responses, we use .convertFromSnakeCase too.

    /// Attempt to parse a JSON response from the LLM answer string.
    /// Returns nil if the answer is not valid JSON or doesn't match the expected structure.
    static func parse(from answer: String) -> LinguistLookupResult? {
        // Try to extract JSON from the answer (LLM might include extra text)
        let trimmed = answer.trimmingCharacters(in: .whitespacesAndNewlines)

        // Find JSON object bounds
        guard let startIndex = trimmed.firstIndex(of: "{"),
              let endIndex = trimmed.lastIndex(of: "}") else {
            return nil
        }

        let jsonString = String(trimmed[startIndex...endIndex])
        guard let data = jsonString.data(using: .utf8) else {
            return nil
        }

        do {
            let decoder = JSONDecoder()
            // Use snake_case decoding to match the JSON format from both:
            // - Live LLM responses (snake_case keys like part_of_speech)
            // - Re-encoded cached results (also snake_case via encoder.keyEncodingStrategy)
            decoder.keyDecodingStrategy = .convertFromSnakeCase
            return try decoder.decode(LinguistLookupResult.self, from: data)
        } catch {
            linguistApiModelsLogger.error("LinguistLookupResult parse error: \(String(describing: error), privacy: .private)")
            return nil
        }
    }
}

struct LLMModelListResponse: Decodable {
    let models: [String]
}

struct MacOSVoice: Decodable {
    let name: String
    let lang: String
    let quality: String?
    let gender: String?
}

struct GTTSLanguage: Decodable {
    let code: String
    let name: String
}

struct PiperVoice: Decodable {
    let name: String
    let lang: String
    let quality: String
}

struct VoiceInventoryResponse: Decodable {
    let macos: [MacOSVoice]
    let gtts: [GTTSLanguage]
    let piper: [PiperVoice]
}

struct AudioSynthesisRequest: Encodable {
    let text: String
    let voice: String?
    let speed: Int?
    let language: String?
}
