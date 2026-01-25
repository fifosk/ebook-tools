import SwiftUI

extension VideoPlayerView {
    func handleSubtitleLookup() {
        if coordinator.isPlaying {
            coordinator.pause()
        }
        guard let display = currentSubtitleDisplay() else { return }
        let selection = normalizedSelection(from: subtitleSelection, in: display)
            ?? defaultSubtitleSelection(in: display)
        guard let selection, let line = lineForSelection(selection, in: display) else { return }
        if let range = subtitleSelectionRange,
           range.lineKind == selection.lineKind,
           range.lineIndex == selection.lineIndex,
           !line.tokens.isEmpty {
            let maxIndex = line.tokens.count - 1
            let startIndex = max(0, min(range.startIndex, maxIndex))
            let endIndex = max(0, min(range.endIndex, maxIndex))
            guard startIndex <= endIndex else { return }
            let queryText = line.tokens[startIndex...endIndex]
                .joined(separator: " ")
                .trimmingCharacters(in: .whitespacesAndNewlines)
            guard let query = sanitizeLookupQuery(queryText) else { return }
            let focusIndex = max(0, min(range.focusIndex, maxIndex))
            isManualSubtitleNavigation = true
            subtitleSelection = VideoSubtitleWordSelection(
                lineKind: line.kind,
                lineIndex: line.index,
                tokenIndex: focusIndex
            )
            startSubtitleLookup(query: query, lineKind: line.kind)
            return
        }
        guard line.tokens.indices.contains(selection.tokenIndex) else { return }
        let rawToken = line.tokens[selection.tokenIndex]
        guard let query = sanitizeLookupQuery(rawToken) else { return }
        isManualSubtitleNavigation = true
        subtitleSelection = selection
        startSubtitleLookup(query: query, lineKind: line.kind)
    }

    func handleSubtitleTokenLookup(_ token: VideoSubtitleTokenReference) {
        if coordinator.isPlaying {
            coordinator.pause()
        }
        isManualSubtitleNavigation = true
        subtitleSelectionRange = nil
        subtitleSelection = VideoSubtitleWordSelection(
            lineKind: token.lineKind,
            lineIndex: token.lineIndex,
            tokenIndex: token.tokenIndex
        )
        guard let query = sanitizeLookupQuery(token.token) else { return }
        startSubtitleLookup(query: query, lineKind: token.lineKind)
    }

    func handleSubtitleTokenSeek(_ token: VideoSubtitleTokenReference) {
        isManualSubtitleNavigation = true
        subtitleSelectionRange = nil
        subtitleSelection = VideoSubtitleWordSelection(
            lineKind: token.lineKind,
            lineIndex: token.lineIndex,
            tokenIndex: token.tokenIndex
        )
        scheduleAutoSubtitleLookup()
        if let seekTime = token.seekTime, seekTime.isFinite {
            coordinator.seek(to: seekTime)
            return
        }
        guard let display = currentSubtitleDisplay() else { return }
        guard display.cue.start.isFinite else { return }
        coordinator.seek(to: display.cue.start)
    }

    func startSubtitleLookup(query: String, lineKind: VideoSubtitleLineKind) {
        subtitleLookupTask?.cancel()
        subtitleAutoLookupTask?.cancel()
        subtitleBubble = VideoLinguistBubbleState(query: query, status: .loading, answer: nil, model: nil)
        let originalLanguage = linguistInputLanguage.trimmingCharacters(in: .whitespacesAndNewlines)
        let translationLanguage = linguistLookupLanguage.trimmingCharacters(in: .whitespacesAndNewlines)
        let explanationLanguage = resolvedLookupLanguage
        let inputLanguage = lookupInputLanguage(
            for: lineKind,
            originalLanguage: originalLanguage,
            translationLanguage: translationLanguage
        )
        let selectedModel = resolvedLlmModel
        let pronunciationLanguage = inputLanguage.trimmingCharacters(in: .whitespacesAndNewlines)
        let resolvedPronunciationLanguage = pronunciationLanguage.isEmpty ? nil : pronunciationLanguage
        let resolvedApiLanguage = SpeechLanguageResolver.resolveSpeechLanguage(resolvedPronunciationLanguage ?? "")
        let apiLanguage = resolvedApiLanguage ?? resolvedPronunciationLanguage
        let fallbackLanguage = resolvedApiLanguage
        startSubtitlePronunciation(
            text: query,
            apiLanguage: apiLanguage,
            fallbackLanguage: fallbackLanguage
        )
        subtitleLookupTask = Task { @MainActor in
            guard let configuration = appState.configuration else {
                subtitleBubble = VideoLinguistBubbleState(
                    query: query,
                    status: .error("Lookup is not configured."),
                    answer: nil,
                    model: nil
                )
                return
            }
            do {
                let client = APIClient(configuration: configuration)
                let response = try await client.assistantLookup(
                    query: query,
                    inputLanguage: inputLanguage,
                    lookupLanguage: explanationLanguage,
                    llmModel: selectedModel
                )
                subtitleBubble = VideoLinguistBubbleState(
                    query: query,
                    status: .ready,
                    answer: response.answer,
                    model: response.model
                )
            } catch {
                guard !Task.isCancelled else { return }
                subtitleBubble = VideoLinguistBubbleState(
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
            guard let configuration = appState.configuration else { return }
            let client = APIClient(configuration: configuration)
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

    func closeSubtitleBubble() {
        subtitleLookupTask?.cancel()
        subtitleLookupTask = nil
        subtitleSpeechTask?.cancel()
        subtitleSpeechTask = nil
        subtitleAutoLookupTask?.cancel()
        subtitleAutoLookupTask = nil
        subtitleBubble = nil
        pronunciationSpeaker.stop()
    }

    func scheduleAutoSubtitleLookup() {
        guard subtitleBubble != nil else { return }
        guard !coordinator.isPlaying else { return }
        subtitleAutoLookupTask?.cancel()
        subtitleAutoLookupTask = Task { @MainActor in
            try? await Task.sleep(nanoseconds: subtitleAutoLookupDelayNanos)
            guard !Task.isCancelled else { return }
            guard subtitleBubble != nil else { return }
            guard !coordinator.isPlaying else { return }
            handleSubtitleLookup()
        }
    }

    func startSubtitlePronunciation(text: String, apiLanguage: String?, fallbackLanguage: String?) {
        subtitleSpeechTask?.cancel()
        pronunciationSpeaker.stop()
        subtitleSpeechTask = Task { @MainActor in
            guard let configuration = appState.configuration else {
                if let fallbackLanguage {
                    pronunciationSpeaker.speakFallback(text, language: fallbackLanguage)
                }
                return
            }
            do {
                let client = APIClient(configuration: configuration)
                let data = try await client.synthesizeAudio(text: text, language: apiLanguage)
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

    func lookupInputLanguage(
        for lineKind: VideoSubtitleLineKind,
        originalLanguage: String,
        translationLanguage: String
    ) -> String {
        let resolvedOriginal = originalLanguage.trimmingCharacters(in: .whitespacesAndNewlines)
        let resolvedTranslation = translationLanguage.trimmingCharacters(in: .whitespacesAndNewlines)
        switch lineKind {
        case .translation, .unknown:
            return resolvedTranslation.isEmpty ? resolvedOriginal : resolvedTranslation
        case .original, .transliteration:
            return resolvedOriginal.isEmpty ? resolvedTranslation : resolvedOriginal
        }
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

    func nextLookupTokenIndex(
        in tokens: [String],
        startingAt index: Int,
        direction: Int
    ) -> Int? {
        guard !tokens.isEmpty else { return nil }
        let step = direction >= 0 ? 1 : -1
        var idx = index
        while idx >= 0 && idx < tokens.count {
            if sanitizeLookupQuery(tokens[idx]) != nil {
                return idx
            }
            idx += step
        }
        return nil
    }

    func wrappedLookupTokenIndex(
        in tokens: [String],
        startingAt index: Int,
        direction: Int
    ) -> Int? {
        guard !tokens.isEmpty else { return nil }
        let step = direction >= 0 ? 1 : -1
        let count = tokens.count
        var idx = index
        for _ in 0..<count {
            let wrapped = ((idx % count) + count) % count
            if sanitizeLookupQuery(tokens[wrapped]) != nil {
                return wrapped
            }
            idx += step
        }
        return nil
    }
}
