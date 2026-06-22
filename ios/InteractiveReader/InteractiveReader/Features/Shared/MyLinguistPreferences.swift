import Foundation

enum MyLinguistPreferences {
    static let lookupLanguageKey = "mylinguist.lookupLanguage"
    static let llmModelKey = "mylinguist.llmModel"
    static let ttsVoiceKey = "mylinguist.ttsVoice"
    static let ttsVoicesByLanguageKey = "mylinguist.ttsVoicesByLanguage"
    static let defaultLookupLanguage = "English"
    static let defaultLlmModel = "ollama_cloud:mistral-large-3:675b-cloud"
}

final class TtsVoicePreferencesManager {
    static let shared = TtsVoicePreferencesManager()

    private let userDefaults = UserDefaults.standard
    private let storageKey = MyLinguistPreferences.ttsVoicesByLanguageKey

    private init() {}

    func voice(for languageCode: String) -> String? {
        guard !languageCode.isEmpty else { return nil }
        let normalized = normalizedLanguageCode(languageCode)
        let voices = loadVoices()
        return voices[normalized]
    }

    func setVoice(_ voice: String?, for languageCode: String) {
        guard !languageCode.isEmpty else { return }
        let normalized = normalizedLanguageCode(languageCode)
        var voices = loadVoices()

        if let voice, !voice.isEmpty, !isAutoVoice(voice) {
            voices[normalized] = voice
        } else {
            voices.removeValue(forKey: normalized)
        }

        saveVoices(voices)
    }

    func clearAllVoices() {
        userDefaults.removeObject(forKey: storageKey)
    }

    func allVoices() -> [String: String] {
        loadVoices()
    }

    private func normalizedLanguageCode(_ languageCode: String) -> String {
        languageCode.lowercased().split(separator: "-").first.map(String.init) ?? languageCode.lowercased()
    }

    private func isAutoVoice(_ voice: String) -> Bool {
        let lower = voice.lowercased()
        return lower == "gtts" || lower == "piper-auto" || lower == "macos-auto"
    }

    private func loadVoices() -> [String: String] {
        guard let data = userDefaults.data(forKey: storageKey),
              let voices = try? JSONDecoder().decode([String: String].self, from: data) else {
            return [:]
        }
        return voices
    }

    private func saveVoices(_ voices: [String: String]) {
        guard let data = try? JSONEncoder().encode(voices) else { return }
        userDefaults.set(data, forKey: storageKey)
    }
}
