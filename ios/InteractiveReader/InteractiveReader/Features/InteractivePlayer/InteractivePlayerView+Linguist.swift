import SwiftUI

extension InteractivePlayerView {
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
        linguistBubble = MyLinguistBubbleState(query: query, status: .loading, answer: nil, model: nil)
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
        startPronunciation(text: query, apiLanguage: apiLanguage, fallbackLanguage: resolvedPronunciationLanguage)
        linguistLookupTask = Task { @MainActor in
            do {
                let response = try await viewModel.lookupAssistant(
                    query: query,
                    inputLanguage: inputLanguage,
                    lookupLanguage: explanationLanguage,
                    llmModel: selectedModel
                )
                linguistBubble = MyLinguistBubbleState(
                    query: query,
                    status: .ready,
                    answer: response.answer,
                    model: response.model
                )
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
        pronunciationSpeaker.stop()
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

    func startPronunciation(text: String, apiLanguage: String?, fallbackLanguage: String?) {
        linguistSpeechTask?.cancel()
        pronunciationSpeaker.stop()
        linguistSpeechTask = Task { @MainActor in
            do {
                let data = try await viewModel.synthesizePronunciation(text: text, language: apiLanguage)
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
