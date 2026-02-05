import SwiftUI

/// Shared ViewModel for MyLinguist bubble state and lookup logic.
/// Used by both InteractivePlayerView and VideoPlayerView to eliminate duplicated
/// lookup, pronunciation, and preference management code.
@Observable
final class MyLinguistBubbleViewModel {

    // MARK: - Bubble State

    var bubble: MyLinguistBubbleState?
    private(set) var lookupTask: Task<Void, Never>?
    private(set) var speechTask: Task<Void, Never>?
    var autoLookupTask: Task<Void, Never>?
    var availableLlmModels: [String] = []
    var didLoadLlmModels = false
    var voiceInventory: VoiceInventoryResponse?
    var didLoadVoiceInventory = false

    // MARK: - Dependencies

    let pronunciationSpeaker: PronunciationSpeaker
    private var apiConfigProvider: () -> APIClientConfiguration?
    private var jobIdProvider: () -> String?
    private var fetchCachedLookupProvider: ((String, String) async -> LookupCacheEntryResponse?)?

    // MARK: - Language context (set by the owning view)

    /// The original/source language of the content (e.g., "English")
    var inputLanguage: String = ""
    /// The translation/target language (e.g., "Arabic")
    var lookupLanguage: String = ""
    /// The language used for explanations in the bubble (e.g., "English")
    var explanationLanguage: String = ""

    // MARK: - Init

    init(
        pronunciationSpeaker: PronunciationSpeaker = PronunciationSpeaker(),
        apiConfigProvider: @escaping () -> APIClientConfiguration? = { nil },
        jobIdProvider: @escaping () -> String? = { nil },
        fetchCachedLookup: ((String, String) async -> LookupCacheEntryResponse?)? = nil
    ) {
        self.pronunciationSpeaker = pronunciationSpeaker
        self.apiConfigProvider = apiConfigProvider
        self.jobIdProvider = jobIdProvider
        self.fetchCachedLookupProvider = fetchCachedLookup
    }

    /// Configure API access after initialization.
    /// Call this when the view's dependencies are available (e.g., in .task or .onAppear).
    func configure(
        apiConfigProvider: @escaping () -> APIClientConfiguration?,
        jobIdProvider: @escaping () -> String? = { nil },
        fetchCachedLookup: ((String, String) async -> LookupCacheEntryResponse?)? = nil
    ) {
        self.apiConfigProvider = apiConfigProvider
        self.jobIdProvider = jobIdProvider
        self.fetchCachedLookupProvider = fetchCachedLookup
    }

    // MARK: - UserDefaults-backed preferences

    var storedLookupLanguage: String {
        get { UserDefaults.standard.string(forKey: MyLinguistPreferences.lookupLanguageKey) ?? "" }
        set { UserDefaults.standard.set(newValue, forKey: MyLinguistPreferences.lookupLanguageKey) }
    }

    var storedLlmModel: String {
        get { UserDefaults.standard.string(forKey: MyLinguistPreferences.llmModelKey) ?? MyLinguistPreferences.defaultLlmModel }
        set { UserDefaults.standard.set(newValue, forKey: MyLinguistPreferences.llmModelKey) }
    }

    var storedTtsVoice: String {
        get { UserDefaults.standard.string(forKey: MyLinguistPreferences.ttsVoiceKey) ?? "" }
        set { UserDefaults.standard.set(newValue, forKey: MyLinguistPreferences.ttsVoiceKey) }
    }

    // MARK: - Computed Language / Model Options

    var resolvedLookupLanguage: String {
        let trimmed = storedLookupLanguage.trimmingCharacters(in: .whitespacesAndNewlines)
        if !trimmed.isEmpty { return trimmed }
        let fallback = explanationLanguage.trimmingCharacters(in: .whitespacesAndNewlines)
        return fallback.isEmpty ? MyLinguistPreferences.defaultLookupLanguage : fallback
    }

    var resolvedLlmModel: String? {
        let trimmed = storedLlmModel.trimmingCharacters(in: .whitespacesAndNewlines)
        return trimmed.isEmpty ? MyLinguistPreferences.defaultLlmModel : trimmed
    }

    var lookupLanguageOptions: [String] {
        buildLookupLanguageOptions(
            resolvedLookupLanguage: resolvedLookupLanguage,
            explanationLanguage: explanationLanguage,
            lookupLanguage: lookupLanguage,
            inputLanguage: inputLanguage
        )
    }

    var llmModelOptions: [String] {
        buildLlmModelOptions(
            resolvedModel: resolvedLlmModel,
            availableModels: availableLlmModels
        )
    }

    // MARK: - Lookup

    /// Start a linguist lookup for the given query.
    /// - Parameters:
    ///   - query: The sanitized word/phrase to look up
    ///   - isTranslationTrack: Whether the tapped variant is a translation track
    ///   - animateBubble: If true and bubble is already visible, animate the transition
    @MainActor
    func startLookup(
        query: String,
        isTranslationTrack: Bool,
        animateBubble: Bool = false
    ) {
        lookupTask?.cancel()
        autoLookupTask?.cancel()

        let newBubble = MyLinguistBubbleState(query: query, status: .loading, answer: nil, model: nil)
        if animateBubble && bubble != nil {
            withAnimation(.easeInOut(duration: 0.15)) {
                bubble = newBubble
            }
        } else {
            bubble = newBubble
        }

        let originalLang = inputLanguage.trimmingCharacters(in: .whitespacesAndNewlines)
        let translationLang = lookupLanguage.trimmingCharacters(in: .whitespacesAndNewlines)
        let explanationLang = resolvedLookupLanguage
        let resolvedInputLanguage = lookupInputLanguage(
            isTranslationTrack: isTranslationTrack,
            originalLanguage: originalLang,
            translationLanguage: translationLang
        )
        let selectedModel = resolvedLlmModel

        // Pronunciation
        let pronLang = pronunciationLanguage(
            isTranslationTrack: isTranslationTrack,
            inputLanguage: originalLang,
            lookupLanguage: translationLang
        )
        let resolvedPronLang = SpeechLanguageResolver.resolveSpeechLanguage(pronLang ?? "")
        let apiLanguage = resolvedPronLang ?? pronLang
        let langCode = normalizeLanguageCode(apiLanguage ?? "")
        let perLangVoice = TtsVoicePreferencesManager.shared.voice(for: langCode)
        startPronunciation(text: query, apiLanguage: apiLanguage, fallbackLanguage: resolvedPronLang, voice: perLangVoice)

        let jobId = jobIdProvider()
        let cachedLookupFn = fetchCachedLookupProvider

        lookupTask = Task { @MainActor in
            // Try cache first
            if let jobId, let cachedLookupFn {
                if let cached = await cachedLookupFn(jobId, query) {
                    if cached.cached, let result = cached.lookupResult {
                        guard !Task.isCancelled else { return }
                        let encoder = JSONEncoder()
                        encoder.keyEncodingStrategy = .convertToSnakeCase
                        if let jsonData = try? encoder.encode(result),
                           let cachedAnswer = String(data: jsonData, encoding: .utf8) {
                            bubble = MyLinguistBubbleState(
                                query: query,
                                status: .ready,
                                answer: cachedAnswer,
                                model: nil,
                                lookupSource: .cache,
                                cachedAudioRef: cached.audioReferences.first
                            )
                            return
                        }
                    }
                }
            }

            // Cache miss or no cache — live LLM lookup
            guard let config = apiConfigProvider() else {
                bubble = MyLinguistBubbleState(
                    query: query,
                    status: .error("Lookup is not configured."),
                    answer: nil,
                    model: nil
                )
                return
            }
            do {
                let client = APIClient(configuration: config)
                let response = try await client.assistantLookup(
                    query: query,
                    inputLanguage: resolvedInputLanguage,
                    lookupLanguage: explanationLang,
                    llmModel: selectedModel
                )
                guard !Task.isCancelled else { return }
                bubble = MyLinguistBubbleState(
                    query: query,
                    status: .ready,
                    answer: response.answer,
                    model: response.model,
                    lookupSource: .live
                )
            } catch {
                guard !Task.isCancelled else { return }
                bubble = MyLinguistBubbleState(
                    query: query,
                    status: .error(error.localizedDescription),
                    answer: nil,
                    model: nil
                )
            }
        }
    }

    // MARK: - Close / Cancel

    func close() {
        lookupTask?.cancel()
        lookupTask = nil
        speechTask?.cancel()
        speechTask = nil
        autoLookupTask?.cancel()
        autoLookupTask = nil
        bubble = nil
        pronunciationSpeaker.stop()
    }

    // MARK: - LLM Models

    func loadLlmModelsIfNeeded() {
        guard !didLoadLlmModels else { return }
        didLoadLlmModels = true
        Task { @MainActor in
            guard let config = apiConfigProvider() else { return }
            let client = APIClient(configuration: config)
            do {
                let response = try await client.fetchLlmModels()
                if !response.models.isEmpty {
                    availableLlmModels = response.models
                }
            } catch {
                return
            }
        }
    }

    // MARK: - Voice Inventory

    func loadVoiceInventoryIfNeeded() {
        guard !didLoadVoiceInventory else { return }
        didLoadVoiceInventory = true
        Task { @MainActor in
            guard let config = apiConfigProvider() else { return }
            let client = APIClient(configuration: config)
            do {
                let inventory = try await client.fetchVoiceInventory()
                voiceInventory = inventory
            } catch {
                return
            }
        }
    }

    /// Build TTS voice options filtered by the given language.
    func ttsVoiceOptions(for inputLanguage: String?) -> [String] {
        guard let inventory = voiceInventory else { return [] }
        let langCode = normalizeLanguageCode(inputLanguage ?? "")
        let baseLang = langCode.lowercased().split(separator: "-").first.map(String.init) ?? langCode.lowercased()
        guard !baseLang.isEmpty else { return [] }

        var result: [String] = []
        var seen = Set<String>()

        // Auto options at the top
        let autoOptions = ["gTTS", "piper-auto", "macOS-auto"]
        for opt in autoOptions {
            seen.insert(opt.lowercased())
            result.append(opt)
        }

        // Per-language stored voice
        if let perLangVoice = TtsVoicePreferencesManager.shared.voice(for: baseLang),
           !perLangVoice.isEmpty,
           !seen.contains(perLangVoice.lowercased()),
           voiceMatchesLanguage(perLangVoice, language: baseLang, inventory: inventory) {
            seen.insert(perLangVoice.lowercased())
            result.append(perLangVoice)
        }

        // gTTS option for the language
        for entry in inventory.gtts {
            let entryLang = entry.code.lowercased().split(separator: "-").first.map(String.init) ?? ""
            if entryLang == baseLang {
                let identifier = "gTTS-\(entryLang)"
                if !seen.contains(identifier.lowercased()) {
                    seen.insert(identifier.lowercased())
                    result.append(identifier)
                }
                break
            }
        }

        // Piper voices
        for voice in inventory.piper {
            let voiceLang = voice.lang.lowercased().split(separator: "-").first
                .map(String.init)?.split(separator: "_").first.map(String.init) ?? ""
            if voiceLang == baseLang && !seen.contains(voice.name.lowercased()) {
                seen.insert(voice.name.lowercased())
                result.append(voice.name)
            }
        }

        // macOS voices
        for voice in inventory.macos {
            let voiceLang = voice.lang.lowercased().split(separator: "-").first
                .map(String.init)?.split(separator: "_").first.map(String.init) ?? ""
            if voiceLang == baseLang {
                let identifier = "\(voice.name) - \(voice.lang)"
                if !seen.contains(identifier.lowercased()) {
                    seen.insert(identifier.lowercased())
                    result.append(identifier)
                }
            }
        }

        return result
    }

    // MARK: - Voice Preferences

    /// Get the stored voice for a given language code.
    func voiceForLanguage(_ language: String) -> String? {
        let langCode = normalizeLanguageCode(language)
        return TtsVoicePreferencesManager.shared.voice(for: langCode)
    }

    /// Store or clear a voice for a given language code.
    func setVoice(_ voice: String?, forLanguage language: String) {
        let langCode = normalizeLanguageCode(language)
        TtsVoicePreferencesManager.shared.setVoice(voice, for: langCode)
        storedTtsVoice = voice ?? ""
    }

    // MARK: - Voice Matching (private)

    private func voiceMatchesLanguage(_ voice: String, language: String, inventory: VoiceInventoryResponse) -> Bool {
        let voiceLower = voice.lowercased()

        // gTTS format: "gTTS-<lang>"
        if voiceLower.hasPrefix("gtts-") {
            let voiceLang = String(voiceLower.dropFirst(5)).split(separator: "-").first.map(String.init) ?? ""
            return voiceLang == language
        }

        // macOS format: "Name - lang-region"
        if voice.contains(" - ") {
            let parts = voice.split(separator: " - ", maxSplits: 1)
            if parts.count == 2 {
                let voiceLang = String(parts[1]).lowercased().split(separator: "-").first.map(String.init) ?? ""
                return voiceLang == language
            }
        }

        // Piper voices: look up in inventory by name
        if let piperVoice = inventory.piper.first(where: { $0.name.lowercased() == voiceLower }) {
            let voiceLang = piperVoice.lang.lowercased()
                .split(separator: "-").first.map(String.init)?
                .split(separator: "_").first.map(String.init) ?? ""
            return voiceLang == language
        }

        return false
    }

    // MARK: - Pronunciation

    @MainActor
    func startPronunciation(text: String, apiLanguage: String?, fallbackLanguage: String?, voice: String? = nil) {
        speechTask?.cancel()
        pronunciationSpeaker.stop()
        speechTask = Task { @MainActor in
            guard let config = apiConfigProvider() else {
                if let fallbackLanguage {
                    pronunciationSpeaker.speakFallback(text, language: fallbackLanguage)
                }
                return
            }
            do {
                let client = APIClient(configuration: config)
                let data = try await client.synthesizeAudio(text: text, language: apiLanguage, voice: voice)
                guard !Task.isCancelled else { return }
                pronunciationSpeaker.playAudio(data)
            } catch {
                guard !Task.isCancelled else { return }
                if let fallbackLanguage {
                    pronunciationSpeaker.speakFallback(text, language: fallbackLanguage)
                }
            }
        }
    }
}
