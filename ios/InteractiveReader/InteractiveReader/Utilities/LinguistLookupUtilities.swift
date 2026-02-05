import Foundation

// MARK: - Query Sanitization

/// Sanitize a lookup query string: strip surrounding punctuation/symbols and trim whitespace.
/// Returns nil if the result is empty.
func sanitizeLookupQuery(_ value: String) -> String? {
    let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
    let stripped = trimmed.trimmingCharacters(in: .punctuationCharacters.union(.symbols))
    let normalized = stripped.trimmingCharacters(in: .whitespacesAndNewlines)
    return normalized.isEmpty ? nil : normalized
}

// MARK: - Token Navigation

/// Find the nearest non-punctuation token index, searching outward from `startingAt`.
func nearestLookupTokenIndex(in tokens: [String], startingAt index: Int) -> Int? {
    guard !tokens.isEmpty else { return nil }
    let clamped = max(0, min(index, tokens.count - 1))
    if sanitizeLookupQuery(tokens[clamped]) != nil {
        return clamped
    }
    if tokens.count == 1 {
        return nil
    }
    for offset in 1..<tokens.count {
        let forward = clamped + offset
        if forward < tokens.count, sanitizeLookupQuery(tokens[forward]) != nil {
            return forward
        }
        let backward = clamped - offset
        if backward >= 0, sanitizeLookupQuery(tokens[backward]) != nil {
            return backward
        }
    }
    return nil
}

// MARK: - Language Utilities

/// Normalize a language name to its ISO 639-1 code (e.g., "English" → "en", "Turkish" → "tr").
/// If the input is already a code or not recognized, it is returned as-is.
func normalizeLanguageCode(_ language: String) -> String {
    let languageMap: [String: String] = [
        "english": "en", "arabic": "ar", "spanish": "es", "french": "fr",
        "german": "de", "italian": "it", "portuguese": "pt", "russian": "ru",
        "chinese": "zh", "japanese": "ja", "korean": "ko", "hindi": "hi",
        "turkish": "tr", "dutch": "nl", "polish": "pl", "swedish": "sv",
        "norwegian": "no", "danish": "da", "finnish": "fi", "greek": "el",
        "hebrew": "he", "hungarian": "hu", "czech": "cs", "romanian": "ro",
        "thai": "th", "vietnamese": "vi", "indonesian": "id", "malay": "ms",
        "filipino": "tl", "ukrainian": "uk", "bengali": "bn", "tamil": "ta",
        "telugu": "te", "marathi": "mr", "gujarati": "gu", "kannada": "kn",
        "malayalam": "ml", "punjabi": "pa", "urdu": "ur", "persian": "fa",
        "afrikaans": "af", "swahili": "sw", "catalan": "ca", "serbian": "sr",
        "croatian": "hr", "bosnian": "bs", "slovenian": "sl", "slovak": "sk",
        "bulgarian": "bg", "latvian": "lv", "lithuanian": "lt", "estonian": "et"
    ]
    let lower = language.lowercased().trimmingCharacters(in: .whitespacesAndNewlines)
    return languageMap[lower] ?? language
}

/// Build ordered, deduplicated lookup language options from preferred values + full list.
func buildLookupLanguageOptions(
    resolvedLookupLanguage: String,
    explanationLanguage: String,
    lookupLanguage: String,
    inputLanguage: String
) -> [String] {
    var seen: Set<String> = []
    var options: [String] = []
    let preferred = [
        resolvedLookupLanguage,
        explanationLanguage,
        lookupLanguage,
        inputLanguage,
        MyLinguistPreferences.defaultLookupLanguage
    ]
    for value in preferred {
        let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { continue }
        let label = LanguageFlagResolver.flagEntry(for: trimmed).label
        let key = label.lowercased()
        guard !seen.contains(key) else { continue }
        seen.insert(key)
        options.append(label)
    }
    for label in LanguageFlagResolver.availableLanguageLabels() {
        let key = label.lowercased()
        guard !seen.contains(key) else { continue }
        seen.insert(key)
        options.append(label)
    }
    return options
}

/// Build ordered, deduplicated LLM model options.
func buildLlmModelOptions(
    resolvedModel: String?,
    availableModels: [String]
) -> [String] {
    let candidates: [String?] = [resolvedModel, MyLinguistPreferences.defaultLlmModel] + availableModels.map { $0 as String? }
    var seen: Set<String> = []
    var models: [String] = []
    for candidate in candidates {
        guard let raw = candidate else { continue }
        let trimmed = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { continue }
        let key = trimmed.lowercased()
        guard !seen.contains(key) else { continue }
        seen.insert(key)
        models.append(trimmed)
    }
    if models.isEmpty {
        return [MyLinguistPreferences.defaultLlmModel]
    }
    return models
}

/// Resolve the input language for a lookup based on which variant track was tapped.
/// - Parameters:
///   - isTranslationTrack: true if the tapped variant is translation (or unknown/subtitle)
///   - originalLanguage: the original/source language
///   - translationLanguage: the translation/target language
func lookupInputLanguage(
    isTranslationTrack: Bool,
    originalLanguage: String,
    translationLanguage: String
) -> String {
    let resolvedOriginal = originalLanguage.trimmingCharacters(in: .whitespacesAndNewlines)
    let resolvedTranslation = translationLanguage.trimmingCharacters(in: .whitespacesAndNewlines)
    if isTranslationTrack {
        return resolvedTranslation.isEmpty ? resolvedOriginal : resolvedTranslation
    } else {
        return resolvedOriginal.isEmpty ? resolvedTranslation : resolvedOriginal
    }
}

/// Resolve the pronunciation language for TTS based on the variant track.
func pronunciationLanguage(
    isTranslationTrack: Bool,
    inputLanguage: String,
    lookupLanguage: String
) -> String? {
    let preferred = lookupInputLanguage(
        isTranslationTrack: isTranslationTrack,
        originalLanguage: inputLanguage,
        translationLanguage: lookupLanguage
    )
    let trimmed = preferred.trimmingCharacters(in: .whitespacesAndNewlines)
    return trimmed.isEmpty ? nil : trimmed
}
