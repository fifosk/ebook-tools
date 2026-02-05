import SwiftUI

extension VideoPlayerView {

    // MARK: - ViewModel Configuration

    func configureLinguistVM() {
        linguistVM.configure(
            apiConfigProvider: { [weak appState] in appState?.configuration }
        )
        linguistVM.inputLanguage = linguistInputLanguage
        linguistVM.lookupLanguage = linguistLookupLanguage
        linguistVM.explanationLanguage = linguistExplanationLanguage
    }

    // MARK: - Lookup Entry Points

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

    // MARK: - Lookup Execution (delegates to ViewModel)

    func startSubtitleLookup(query: String, lineKind: VideoSubtitleLineKind) {
        let isTranslation = (lineKind == .translation || lineKind == .unknown)
        linguistVM.startLookup(
            query: query,
            isTranslationTrack: isTranslation
        )
    }

    // MARK: - Computed Language / Model Options (delegate to ViewModel)

    var resolvedLookupLanguage: String {
        linguistVM.resolvedLookupLanguage
    }

    var resolvedLlmModel: String? {
        linguistVM.resolvedLlmModel
    }

    var lookupLanguageOptions: [String] {
        linguistVM.lookupLanguageOptions
    }

    var llmModelOptions: [String] {
        linguistVM.llmModelOptions
    }

    func loadLlmModelsIfNeeded() {
        linguistVM.loadLlmModelsIfNeeded()
    }

    // MARK: - State Management

    func closeSubtitleBubble() {
        linguistVM.close()
    }

    func scheduleAutoSubtitleLookup() {
        guard subtitleBubble != nil else { return }
        guard !coordinator.isPlaying else { return }
        linguistVM.autoLookupTask?.cancel()
        linguistVM.autoLookupTask = Task { @MainActor in
            try? await Task.sleep(nanoseconds: subtitleAutoLookupDelayNanos)
            guard !Task.isCancelled else { return }
            guard subtitleBubble != nil else { return }
            guard !coordinator.isPlaying else { return }
            handleSubtitleLookup()
        }
    }

    // MARK: - Language Utilities

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

    // MARK: - Token Navigation (VideoPlayer-only)

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
