import SwiftUI

extension InteractivePlayerView {
    #if os(iOS)
    /// Handle keyboard activation (Enter key) when bubble keyboard focus is active
    func handleBubbleKeyboardActivate() {
        guard let control = bubbleKeyboardNavigator.focusedControl else { return }
        switch control {
        case .language, .voice, .model:
            // Trigger activation in the bubble view via the navigator
            bubbleKeyboardNavigator.activateCurrentControl()
        case .close:
            closeLinguistBubble()
            bubbleKeyboardNavigator.exitFocus()
        }
    }
    #endif

    func handleLinguistLookup(
        sentenceIndex: Int,
        variantKind: TextPlayerVariantKind,
        tokenIndex: Int,
        token: String
    ) {
        if audioCoordinator.isPlaying {
            audioCoordinator.pause()
        }
        guard let query = sanitizeLookupQuery(token) else { return }
        linguistSelectionRange = nil
        linguistSelection = TextPlayerWordSelection(
            sentenceIndex: sentenceIndex,
            variantKind: variantKind,
            tokenIndex: tokenIndex
        )
        startLinguistLookup(query: query, variantKind: variantKind)
    }

    func handleLinguistLookup(in chunk: InteractiveChunk) {
        if audioCoordinator.isPlaying {
            audioCoordinator.pause()
        }
        guard let sentence = activeSentenceDisplay(for: chunk) else {
            return
        }
        // If we have an active selection range, use it directly (don't rely on resolvedSelection
        // which may fall back to a different variant)
        if let range = linguistSelectionRange,
           range.sentenceIndex == sentence.index,
           let variant = sentence.variants.first(where: { $0.kind == range.variantKind }),
           visibleTracks.contains(variant.kind),
           !variant.tokens.isEmpty {
            let maxIndex = variant.tokens.count - 1
            let startIndex = max(0, min(range.startIndex, maxIndex))
            let endIndex = max(0, min(range.endIndex, maxIndex))
            guard startIndex <= endIndex else { return }
            let queryText = variant.tokens[startIndex...endIndex]
                .joined(separator: " ")
                .trimmingCharacters(in: .whitespacesAndNewlines)
            guard let query = sanitizeLookupQuery(queryText) else { return }
            let focusIndex = max(0, min(range.focusIndex, maxIndex))
            linguistSelection = TextPlayerWordSelection(
                sentenceIndex: sentence.index,
                variantKind: range.variantKind,
                tokenIndex: focusIndex
            )
            startLinguistLookup(query: query, variantKind: range.variantKind)
            return
        }
        // Fallback to resolved selection for single-word lookup
        guard let selection = resolvedSelection(for: chunk),
              let variant = sentence.variants.first(where: { $0.kind == selection.variantKind }),
              variant.tokens.indices.contains(selection.tokenIndex) else {
            return
        }
        guard let lookupIndex = nearestLookupTokenIndex(
            in: variant.tokens,
            startingAt: selection.tokenIndex
        ) else {
            return
        }
        let rawToken = variant.tokens[lookupIndex]
        guard let query = sanitizeLookupQuery(rawToken) else { return }
        linguistSelection = TextPlayerWordSelection(
            sentenceIndex: sentence.index,
            variantKind: selection.variantKind,
            tokenIndex: lookupIndex
        )
        startLinguistLookup(query: query, variantKind: selection.variantKind)
    }

    func startLinguistLookup(query: String, variantKind: TextPlayerVariantKind) {
        linguistLookupTask?.cancel()
        linguistAutoLookupTask?.cancel()
        // When bubble is already visible, use smooth animation to avoid visual flicker
        if linguistBubble != nil {
            withAnimation(.easeInOut(duration: 0.15)) {
                linguistBubble = MyLinguistBubbleState(query: query, status: .loading, answer: nil, model: nil)
            }
        } else {
            linguistBubble = MyLinguistBubbleState(query: query, status: .loading, answer: nil, model: nil)
        }
        let originalLanguage = linguistInputLanguage.trimmingCharacters(in: .whitespacesAndNewlines)
        let translationLanguage = linguistLookupLanguage.trimmingCharacters(in: .whitespacesAndNewlines)
        let explanationLanguage = resolvedLookupLanguage
        let inputLanguage = lookupInputLanguage(
            for: variantKind,
            originalLanguage: originalLanguage,
            translationLanguage: translationLanguage
        )
        let selectedModel = resolvedLlmModel
        let pronunciationLanguage = pronunciationLanguage(
            for: variantKind,
            inputLanguage: originalLanguage,
            lookupLanguage: translationLanguage
        )
        let resolvedPronunciationLanguage = SpeechLanguageResolver.resolveSpeechLanguage(pronunciationLanguage ?? "")
        let apiLanguage = resolvedPronunciationLanguage ?? pronunciationLanguage
        // Get per-language stored voice for the pronunciation language
        let langCode = normalizeLanguageCode(apiLanguage ?? "")
        let perLangVoice = TtsVoicePreferencesManager.shared.voice(for: langCode)
        // Use per-language voice if set, otherwise nil for auto-selection
        let selectedVoice = perLangVoice
        startPronunciation(text: query, apiLanguage: apiLanguage, fallbackLanguage: resolvedPronunciationLanguage, voice: selectedVoice)

        // Capture jobId for cache lookup
        let jobId = viewModel.jobId

        linguistLookupTask = Task { @MainActor in
            // Try cache first if we have a jobId
            if let jobId {
                print("[Linguist] Checking cache for '\(query)' in job \(jobId)")
                if let cached = await viewModel.fetchCachedLookup(jobId: jobId, word: query) {
                    print("[Linguist] Cache response: cached=\(cached.cached), hasResult=\(cached.lookupResult != nil), audioRefs=\(cached.audioReferences.count)")
                    if cached.cached, let result = cached.lookupResult {
                        guard !Task.isCancelled else { return }
                        // Encode lookupResult as JSON so it can be parsed by LinguistLookupResult.parse
                        // IMPORTANT: Use snake_case key encoding to match the decoding CodingKeys
                        // LinguistLookupResult expects keys like "part_of_speech", "related_languages", etc.
                        let encoder = JSONEncoder()
                        encoder.keyEncodingStrategy = .convertToSnakeCase
                        if let jsonData = try? encoder.encode(result),
                           let cachedAnswer = String(data: jsonData, encoding: .utf8) {
                            print("[Linguist] Using CACHED lookup for '\(query)', JSON: \(cachedAnswer.prefix(300))...")
                            var state = MyLinguistBubbleState(
                                query: query,
                                status: .ready,
                                answer: cachedAnswer,
                                model: nil
                            )
                            state.lookupSource = .cache
                            // Capture first audio reference for "play from narration" feature
                            state.cachedAudioRef = cached.audioReferences.first
                            linguistBubble = state
                            return
                        } else {
                            print("[Linguist] Failed to encode cached result as JSON")
                        }
                    }
                } else {
                    print("[Linguist] No cache response for '\(query)'")
                }
            } else {
                print("[Linguist] No jobId, skipping cache lookup")
            }

            // Cache miss or no cache - fallback to live LLM lookup
            do {
                let response = try await viewModel.lookupAssistant(
                    query: query,
                    inputLanguage: inputLanguage,
                    lookupLanguage: explanationLanguage,
                    llmModel: selectedModel
                )
                guard !Task.isCancelled else { return }
                var state = MyLinguistBubbleState(
                    query: query,
                    status: .ready,
                    answer: response.answer,
                    model: response.model
                )
                state.lookupSource = .live
                linguistBubble = state
            } catch {
                guard !Task.isCancelled else { return }
                linguistBubble = MyLinguistBubbleState(
                    query: query,
                    status: .error(error.localizedDescription),
                    answer: nil,
                    model: nil
                )
            }
        }
    }

    var resolvedLookupLanguage: String {
        let trimmed = storedLookupLanguage.trimmingCharacters(in: .whitespacesAndNewlines)
        if !trimmed.isEmpty {
            return trimmed
        }
        let fallback = linguistExplanationLanguage.trimmingCharacters(in: .whitespacesAndNewlines)
        return fallback.isEmpty ? MyLinguistPreferences.defaultLookupLanguage : fallback
    }

    var resolvedLlmModel: String? {
        let trimmed = storedLlmModel.trimmingCharacters(in: .whitespacesAndNewlines)
        if trimmed.isEmpty {
            return MyLinguistPreferences.defaultLlmModel
        }
        return trimmed
    }

    var lookupLanguageOptions: [String] {
        var seen: Set<String> = []
        var options: [String] = []
        let preferred = [
            resolvedLookupLanguage,
            linguistExplanationLanguage,
            linguistLookupLanguage,
            linguistInputLanguage,
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

    /// Determines the TTS language based on current linguist selection's variant
    var ttsLanguageForCurrentSelection: String {
        guard let selection = linguistSelection else {
            // No selection, default to original language
            return linguistInputLanguage
        }
        switch selection.variantKind {
        case .translation, .transliteration:
            // For translation/transliteration tracks, use the lookup/translation language
            return linguistLookupLanguage.isEmpty ? linguistInputLanguage : linguistLookupLanguage
        case .original:
            // For original track, use the original language
            return linguistInputLanguage
        }
    }

    /// Get the stored voice for the current TTS language
    /// Returns the per-language stored voice, or nil if no custom voice is set
    var voiceForCurrentLanguage: String? {
        let language = ttsLanguageForCurrentSelection
        let langCode = normalizeLanguageCode(language)
        return TtsVoicePreferencesManager.shared.voice(for: langCode)
    }

    /// Set the voice for the current TTS language
    /// - Parameter voice: The voice to store, or nil to clear (reset to default)
    func setVoiceForCurrentLanguage(_ voice: String?) {
        let language = ttsLanguageForCurrentSelection
        let langCode = normalizeLanguageCode(language)
        TtsVoicePreferencesManager.shared.setVoice(voice, for: langCode)
        // Also update the legacy storage for compatibility
        storedTtsVoice = voice ?? ""
    }

    var llmModelOptions: [String] {
        let candidates = [resolvedLlmModel, MyLinguistPreferences.defaultLlmModel] + availableLlmModels
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

    func loadLlmModelsIfNeeded() {
        guard !didLoadLlmModels else { return }
        didLoadLlmModels = true
        Task { @MainActor in
            let models = await viewModel.fetchLlmModels()
            if !models.isEmpty {
                availableLlmModels = models
            }
        }
    }

    func loadVoiceInventoryIfNeeded() {
        guard !didLoadVoiceInventory else { return }
        didLoadVoiceInventory = true
        Task { @MainActor in
            let inventory = await viewModel.fetchVoiceInventory()
            voiceInventory = inventory
        }
    }

    /// Computed TTS voice options filtered by the current input language
    func ttsVoiceOptions(for inputLanguage: String?) -> [String] {
        guard let inventory = voiceInventory else { return [] }
        let langCode = normalizeLanguageCode(inputLanguage ?? "")
        let baseLang = langCode.lowercased().split(separator: "-").first.map(String.init) ?? langCode.lowercased()
        guard !baseLang.isEmpty else { return [] }

        var result: [String] = []
        var seen = Set<String>()

        // Add auto options at the top (priority order: gTTS -> Piper -> macOS)
        let autoOptions = ["gTTS", "piper-auto", "macOS-auto"]
        for opt in autoOptions {
            seen.insert(opt.lowercased())
            result.append(opt)
        }

        // Add per-language stored voice if it exists and matches the current language
        if let perLangVoice = TtsVoicePreferencesManager.shared.voice(for: baseLang),
           !perLangVoice.isEmpty,
           !seen.contains(perLangVoice.lowercased()),
           voiceMatchesLanguage(perLangVoice, language: baseLang, inventory: inventory) {
            seen.insert(perLangVoice.lowercased())
            result.append(perLangVoice)
        }

        // Add gTTS option for the language (specific language variant)
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

        // Add Piper voices matching the language
        for voice in inventory.piper {
            let voiceLang = voice.lang.lowercased().split(separator: "-").first
                .map(String.init)?.split(separator: "_").first.map(String.init) ?? ""
            if voiceLang == baseLang && !seen.contains(voice.name.lowercased()) {
                seen.insert(voice.name.lowercased())
                result.append(voice.name)
            }
        }

        // Add macOS voices matching the language
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

    /// Returns the voice if it matches the given language, otherwise nil (for auto-selection)
    /// Used when starting pronunciation to ensure the stored voice matches the token's language
    /// - Parameters:
    ///   - voice: Stored voice identifier
    ///   - language: Target language code or name (e.g., "en", "Turkish", "hi")
    /// - Returns: The voice if it matches, nil otherwise
    private func resolvedVoiceForLanguage(_ voice: String, language: String?) -> String? {
        guard !voice.isEmpty else { return nil }
        guard let language, !language.isEmpty else { return nil }

        // Normalize language to code
        let langCode = normalizeLanguageCode(language).lowercased()
        let baseLang = langCode.split(separator: "-").first.map(String.init) ?? langCode

        // Check if voice matches language using inventory if available
        if let inventory = voiceInventory {
            if voiceMatchesLanguage(voice, language: baseLang, inventory: inventory) {
                return voice
            }
            return nil
        }

        // Fallback: simple pattern matching without inventory
        let voiceLower = voice.lowercased()

        // gTTS format: "gTTS-<lang>"
        if voiceLower.hasPrefix("gtts-") {
            let voiceLang = String(voiceLower.dropFirst(5)).split(separator: "-").first.map(String.init) ?? ""
            return voiceLang == baseLang ? voice : nil
        }

        // macOS format: "Name - lang-region"
        if voice.contains(" - ") {
            let parts = voice.split(separator: " - ", maxSplits: 1)
            if parts.count == 2 {
                let voiceLang = String(parts[1]).lowercased().split(separator: "-").first.map(String.init) ?? ""
                return voiceLang == baseLang ? voice : nil
            }
        }

        // Unknown format without inventory - safer to return nil for auto-selection
        return nil
    }

    /// Check if a voice identifier matches the given language code
    /// - Parameters:
    ///   - voice: Voice identifier (e.g., "gTTS-hi", "Samantha - en-US", "piper-name")
    ///   - language: Normalized language code (e.g., "hi", "en", "tr")
    ///   - inventory: Voice inventory to look up piper voice languages
    /// - Returns: true if the voice is compatible with the language
    private func voiceMatchesLanguage(_ voice: String, language: String, inventory: VoiceInventoryResponse) -> Bool {
        let voiceLower = voice.lowercased()

        // gTTS format: "gTTS-<lang>" (e.g., "gTTS-hi", "gTTS-tr")
        if voiceLower.hasPrefix("gtts-") {
            let voiceLang = String(voiceLower.dropFirst(5)).split(separator: "-").first.map(String.init) ?? ""
            return voiceLang == language
        }

        // macOS format: "Name - lang-region" (e.g., "Samantha - en-US", "Lekha - hi-IN")
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

        // Unknown format - don't include (safer to exclude than show wrong language)
        return false
    }

    /// Normalize language name to code (e.g., "English" → "en")
    private func normalizeLanguageCode(_ language: String) -> String {
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

    func clearLinguistState() {
        linguistLookupTask?.cancel()
        linguistLookupTask = nil
        linguistSpeechTask?.cancel()
        linguistSpeechTask = nil
        linguistAutoLookupTask?.cancel()
        linguistAutoLookupTask = nil
        linguistBubble = nil
        bubbleFocusEnabled = false
        linguistSelection = nil
        linguistSelectionRange = nil
        pronunciationSpeaker.stop()
    }

    func closeLinguistBubble() {
        linguistLookupTask?.cancel()
        linguistLookupTask = nil
        linguistSpeechTask?.cancel()
        linguistSpeechTask = nil
        linguistAutoLookupTask?.cancel()
        linguistAutoLookupTask = nil
        linguistBubble = nil
        bubbleFocusEnabled = false
        #if os(iOS)
        bubbleKeyboardNavigator.exitFocus()
        #endif
        pronunciationSpeaker.stop()
    }

    /// Play word pronunciation from narration audio using cached timing reference
    func handlePlayFromNarration() {
        guard let audioRef = linguistBubble?.cachedAudioRef,
              let chunk = viewModel.selectedChunk else { return }
        // Seek to the word's start time in the audio
        let seekTime = audioRef.t0
        viewModel.seekPlayback(to: seekTime, in: chunk)
        // If not already playing, start playback
        if !audioCoordinator.isPlaying {
            audioCoordinator.play()
        }
    }

    func scheduleAutoLinguistLookup(in chunk: InteractiveChunk) {
        guard linguistBubble != nil else { return }
        guard !audioCoordinator.isPlaying else { return }
        linguistAutoLookupTask?.cancel()
        let chunkID = chunk.id
        linguistAutoLookupTask = Task { @MainActor in
            try? await Task.sleep(nanoseconds: linguistAutoLookupDelayNanos)
            guard !Task.isCancelled else { return }
            guard !audioCoordinator.isPlaying else { return }
            guard linguistBubble != nil else { return }
            guard viewModel.selectedChunk?.id == chunkID else { return }
            handleLinguistLookup(in: chunk)
        }
    }

    func adjustTrackFontScale(by delta: CGFloat) {
        setTrackFontScale(trackFontScale + delta)
    }

    func adjustLinguistFontScale(by delta: CGFloat) {
        setLinguistFontScale(linguistFontScale + delta)
    }

    func toggleShortcutHelp() {
        isShortcutHelpPinned.toggle()
    }

    func showShortcutHelpModifier() {
        isShortcutHelpModifierActive = true
    }

    func hideShortcutHelpModifier() {
        isShortcutHelpModifierActive = false
    }

    func dismissShortcutHelp() {
        isShortcutHelpPinned = false
    }

    func setTrackFontScale(_ value: CGFloat) {
        let updated = min(max(value, trackFontScaleMin), trackFontScaleMax)
        if updated != trackFontScale {
            trackFontScale = updated
        }
    }

    func setLinguistFontScale(_ value: CGFloat) {
        let updated = min(max(value, linguistFontScaleMin), linguistFontScaleMax)
        if updated != linguistFontScale {
            linguistFontScale = updated
        }
    }

    var trackFontScale: CGFloat {
        get { CGFloat(trackFontScaleValue) }
        nonmutating set { trackFontScaleValue = Double(newValue) }
    }

    var linguistFontScale: CGFloat {
        get { CGFloat(linguistFontScaleValue) }
        nonmutating set { linguistFontScaleValue = Double(newValue) }
    }

    #if os(iOS)
    var iPadSplitDirection: iPadBubbleSplitDirection {
        get {
            iPadSplitDirectionRaw == "horizontal" ? .horizontal : .vertical
        }
        nonmutating set {
            iPadSplitDirectionRaw = newValue == .horizontal ? "horizontal" : "vertical"
        }
    }

    var iPadSplitRatio: CGFloat {
        get { CGFloat(iPadSplitRatioValue) }
        nonmutating set { iPadSplitRatioValue = Double(newValue) }
    }

    func toggleiPadLayoutDirection() {
        iPadSplitDirection = iPadSplitDirection == .vertical ? .horizontal : .vertical
        // Reset ratio to 30% bubble / 70% track when toggling (matching tvOS)
        iPadSplitRatio = 0.4
    }

    func toggleiPadBubblePin() {
        iPadBubblePinned.toggle()
    }
    #else
    // tvOS uses horizontal split when enabled (30% bubble / 70% track)
    var iPadSplitDirection: iPadBubbleSplitDirection {
        get { tvSplitEnabled ? .horizontal : .vertical }
        nonmutating set { /* controlled via tvSplitEnabled */ }
    }
    var iPadSplitRatio: CGFloat {
        // tvOS fixed ratio: 30% for bubble, 70% for tracks
        get { 0.30 }
        nonmutating set { /* fixed on tvOS */ }
    }
    func toggleiPadLayoutDirection() {
        tvSplitEnabled.toggle()
    }
    // tvOS pin support - keeps bubble visible during playback in split mode
    var iPadBubblePinned: Bool {
        get { tvBubblePinned }
        nonmutating set { tvBubblePinned = newValue }
    }
    func toggleiPadBubblePin() {
        tvBubblePinned.toggle()
    }
    #endif

    func sanitizeLookupQuery(_ value: String) -> String? {
        let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
        let stripped = trimmed.trimmingCharacters(in: .punctuationCharacters.union(.symbols))
        let normalized = stripped.trimmingCharacters(in: .whitespacesAndNewlines)
        return normalized.isEmpty ? nil : normalized
    }

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

    func pronunciationLanguage(
        for variantKind: TextPlayerVariantKind,
        inputLanguage: String,
        lookupLanguage: String
    ) -> String? {
        let preferred = lookupInputLanguage(
            for: variantKind,
            originalLanguage: inputLanguage,
            translationLanguage: lookupLanguage
        )
        let trimmed = preferred.trimmingCharacters(in: .whitespacesAndNewlines)
        return trimmed.isEmpty ? nil : trimmed
    }

    func lookupInputLanguage(
        for variantKind: TextPlayerVariantKind,
        originalLanguage: String,
        translationLanguage: String
    ) -> String {
        let resolvedOriginal = originalLanguage.trimmingCharacters(in: .whitespacesAndNewlines)
        let resolvedTranslation = translationLanguage.trimmingCharacters(in: .whitespacesAndNewlines)
        switch variantKind {
        case .translation:
            return resolvedTranslation.isEmpty ? resolvedOriginal : resolvedTranslation
        case .original, .transliteration:
            return resolvedOriginal.isEmpty ? resolvedTranslation : resolvedOriginal
        }
    }

    func startPronunciation(text: String, apiLanguage: String?, fallbackLanguage: String?, voice: String? = nil) {
        linguistSpeechTask?.cancel()
        pronunciationSpeaker.stop()
        linguistSpeechTask = Task { @MainActor in
            do {
                let data = try await viewModel.synthesizePronunciation(text: text, language: apiLanguage, voice: voice)
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
