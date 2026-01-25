import Foundation

enum SpeechLanguageResolver {
    static func resolveSpeechLanguage(_ value: String) -> String? {
        let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return nil }
        let normalized = trimmed.replacingOccurrences(of: "_", with: "-")
        if normalized.contains("-") || normalized.count <= 3 {
            return normalized
        }
        switch normalized.lowercased() {
        case "english":
            return "en-US"
        case "japanese":
            return "ja-JP"
        case "spanish":
            return "es-ES"
        case "french":
            return "fr-FR"
        case "german":
            return "de-DE"
        case "italian":
            return "it-IT"
        case "portuguese":
            return "pt-PT"
        case "chinese (simplified)", "chinese simplified", "simplified chinese":
            return "zh-CN"
        case "chinese (traditional)", "chinese traditional", "traditional chinese":
            return "zh-TW"
        case "chinese":
            return "zh-CN"
        case "korean":
            return "ko-KR"
        case "russian":
            return "ru-RU"
        case "arabic":
            return "ar-SA"
        case "hindi":
            return "hi-IN"
        default:
            return nil
        }
    }
}
