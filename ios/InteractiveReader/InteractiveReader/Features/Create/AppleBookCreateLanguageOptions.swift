import Foundation

extension AppleBookCreatePresentation {
    static func availableInputLanguages(
        from options: BookCreationOptionsResponse?
    ) -> [AppleBookCreateLanguage] {
        availableLanguages(options?.supportedInputLanguages ?? [])
    }

    static func availableTargetLanguages(
        from options: BookCreationOptionsResponse?
    ) -> [AppleBookCreateLanguage] {
        availableLanguages(options?.supportedOutputLanguages ?? [])
    }

    static func availableVoices(
        from options: BookCreationOptionsResponse?,
        selected: AppleBookCreateVoiceOption?
    ) -> [AppleBookCreateVoiceOption] {
        availableVoices(
            from: options,
            inventory: nil,
            language: "",
            selected: selected
        )
    }

    static func availableVoices(
        from options: BookCreationOptionsResponse?,
        inventory: AppleBookCreateVoiceInventory?,
        language: String,
        selected: AppleBookCreateVoiceOption?
    ) -> [AppleBookCreateVoiceOption] {
        let baseOptions = AppleBookCreateVoiceOption.options(
            from: options?.supportedVoices ?? [],
            selected: selected
        )
        let inventoryOptions = voiceInventoryOptions(from: inventory, language: language)
        return mergedVoiceOptions(baseOptions + inventoryOptions, selected: selected)
    }

    static func languageVoiceOptions(
        from options: BookCreationOptionsResponse?,
        inventory: AppleBookCreateVoiceInventory?,
        languages: [String],
        selectedOverrides: [String: String],
        fallbackVoice: AppleBookCreateVoiceOption
    ) -> [String: [AppleBookCreateVoiceOption]] {
        var result = [String: [AppleBookCreateVoiceOption]]()
        for language in languages {
            let selected = selectedOverrides[language].flatMap(AppleBookCreateVoiceOption.init(backendValue:))
            result[language] = availableVoices(
                from: options,
                inventory: inventory,
                language: language,
                selected: selected ?? fallbackVoice
            )
        }
        return result
    }

    static func targetLanguagesForVoiceOverrides(
        mode: AppleCreateMode,
        primary: String,
        additionalTargets: String
    ) -> [String] {
        switch mode {
        case .generatedBook, .narrateEbook:
            return normalizedTargetLanguages(primary: primary, additionalTargets: additionalTargets)
        case .subtitleJob, .youtubeDub:
            return []
        }
    }

    static func voiceInventoryOptions(
        from inventory: AppleBookCreateVoiceInventory?,
        language: String
    ) -> [AppleBookCreateVoiceOption] {
        guard let inventory else { return [] }
        let normalizedLanguage = normalizedVoiceLanguage(language)
        let baseLanguage = baseVoiceLanguage(normalizedLanguage)
        guard !baseLanguage.isEmpty else { return [] }

        var options = [AppleBookCreateVoiceOption]()
        var seen = Set<String>()

        for entry in inventory.gtts where voiceLanguageMatches(entry.code, normalizedLanguage: normalizedLanguage) {
            let identifier = "gTTS-\(baseVoiceLanguage(entry.code))"
            appendVoiceOption(identifier, to: &options, seen: &seen)
        }

        for voice in inventory.macos.sorted(by: { $0.name < $1.name })
            where voiceLanguageMatches(voice.lang, normalizedLanguage: normalizedLanguage) {
            appendVoiceOption(macOSVoiceIdentifier(voice), to: &options, seen: &seen)
        }

        for voice in inventory.piper.sorted(by: { $0.name < $1.name })
            where voiceLanguageMatches(voice.lang, normalizedLanguage: normalizedLanguage) {
            appendVoiceOption(voice.name, to: &options, seen: &seen)
        }

        return options
    }

    static func sampleSentence(language: String, fallbackLabel: String) -> String {
        let code = normalizedVoiceLanguage(language)
        if let sentence = AppleBookCreateVoicePreviewSamples.sentences[code] {
            return sentence
        }
        let base = baseVoiceLanguage(code)
        if let sentence = AppleBookCreateVoicePreviewSamples.sentences[base] {
            return sentence
        }
        let label = AppleLanguageCatalog.canonicalLanguageName(for: language)
            ?? normalizedCreateOptionText(fallbackLabel).nonEmptyValue
            ?? language
        return "Sample narration for \(label)."
    }

    static func voicePreviewKey(language: String) -> String {
        normalizedVoiceLanguage(language).lowercased()
    }

    private static func availableLanguages(_ supported: [String]) -> [AppleBookCreateLanguage] {
        AppleBookCreateLanguage.options(from: supported)
    }

    private static func mergedVoiceOptions(
        _ options: [AppleBookCreateVoiceOption],
        selected: AppleBookCreateVoiceOption?
    ) -> [AppleBookCreateVoiceOption] {
        var seen = Set<String>()
        var merged = [AppleBookCreateVoiceOption]()
        for option in options where seen.insert(option.backendValue.lowercased()).inserted {
            merged.append(option)
        }
        if let selected, !seen.contains(selected.backendValue.lowercased()) {
            merged.insert(selected, at: 0)
        }
        return merged.isEmpty ? AppleBookCreateVoiceOption.fallbackOptions : merged
    }

    private static func appendVoiceOption(
        _ value: String,
        to options: inout [AppleBookCreateVoiceOption],
        seen: inout Set<String>
    ) {
        guard let option = AppleBookCreateVoiceOption(backendValue: value),
              seen.insert(option.backendValue.lowercased()).inserted else {
            return
        }
        options.append(option)
    }

    private static func macOSVoiceIdentifier(_ voice: AppleBookCreateVoiceInventory.MacOSVoice) -> String {
        let quality = normalizedCreateOptionText(voice.quality ?? "").nonEmptyValue ?? "Default"
        let gender = normalizedCreateOptionText(voice.gender ?? "").nonEmptyValue.map { " - \(capitalizedFirst($0))" } ?? ""
        return "\(voice.name) - \(voice.lang) - (\(quality))\(gender)"
    }

    private static func capitalizedFirst(_ value: String) -> String {
        guard let first = value.first else { return value }
        return first.uppercased() + value.dropFirst()
    }

    private static func voiceLanguageMatches(
        _ candidate: String,
        normalizedLanguage: String
    ) -> Bool {
        let normalizedCandidate = normalizedVoiceLanguage(candidate)
        guard !normalizedCandidate.isEmpty, !normalizedLanguage.isEmpty else { return false }
        if normalizedCandidate == normalizedLanguage {
            return true
        }
        return baseVoiceLanguage(normalizedCandidate) == baseVoiceLanguage(normalizedLanguage)
    }

    private static func normalizedVoiceLanguage(_ value: String) -> String {
        let trimmed = normalizedCreateOptionText(value)
        if let code = AppleLanguageCatalog.languageCode(for: trimmed) {
            return code
                .replacingOccurrences(of: "_", with: "-")
                .lowercased()
        }
        return trimmed
            .replacingOccurrences(of: "_", with: "-")
            .lowercased()
    }

    private static func baseVoiceLanguage(_ value: String) -> String {
        normalizedVoiceLanguage(value)
            .split(separator: "-", omittingEmptySubsequences: true)
            .first
            .map(String.init) ?? ""
    }

    private static func normalizedCreateOptionText(_ value: String) -> String {
        value.trimmingCharacters(in: .whitespacesAndNewlines)
    }
}
