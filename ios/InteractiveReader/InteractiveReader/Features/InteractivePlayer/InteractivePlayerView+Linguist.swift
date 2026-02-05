import SwiftUI

extension InteractivePlayerView {

    // MARK: - ViewModel Configuration

    func configureLinguistVM() {
        linguistVM.configure(
            apiConfigProvider: { [weak viewModel] in viewModel?.apiConfiguration },
            jobIdProvider: { [weak viewModel] in viewModel?.jobId },
            fetchCachedLookup: { [weak viewModel] jobId, word in
                await viewModel?.fetchCachedLookup(jobId: jobId, word: word)
            }
        )
        linguistVM.inputLanguage = linguistInputLanguage
        linguistVM.lookupLanguage = linguistLookupLanguage
        linguistVM.explanationLanguage = linguistExplanationLanguage
    }

    // MARK: - Keyboard Focus (iOS)

    #if os(iOS)
    /// Handle keyboard activation (Enter key) when bubble keyboard focus is active
    func handleBubbleKeyboardActivate() {
        guard let control = bubbleKeyboardNavigator.focusedControl else { return }
        switch control {
        case .language, .voice, .model:
            bubbleKeyboardNavigator.activateCurrentControl()
        case .close:
            closeLinguistBubble()
            bubbleKeyboardNavigator.exitFocus()
        }
    }
    #endif

    // MARK: - Lookup Entry Points

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
        // If we have an active selection range, use it directly
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

    // MARK: - Lookup Execution (delegates to ViewModel)

    func startLinguistLookup(query: String, variantKind: TextPlayerVariantKind) {
        let isTranslation = variantKind == .translation
        let animateBubble = linguistBubble != nil
        linguistVM.startLookup(
            query: query,
            isTranslationTrack: isTranslation,
            animateBubble: animateBubble
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

    /// Determines the TTS language based on current linguist selection's variant
    var ttsLanguageForCurrentSelection: String {
        guard let selection = linguistSelection else {
            return linguistInputLanguage
        }
        switch selection.variantKind {
        case .translation, .transliteration:
            return linguistLookupLanguage.isEmpty ? linguistInputLanguage : linguistLookupLanguage
        case .original:
            return linguistInputLanguage
        }
    }

    /// Get the stored voice for the current TTS language
    var voiceForCurrentLanguage: String? {
        linguistVM.voiceForLanguage(ttsLanguageForCurrentSelection)
    }

    /// Set the voice for the current TTS language
    func setVoiceForCurrentLanguage(_ voice: String?) {
        linguistVM.setVoice(voice, forLanguage: ttsLanguageForCurrentSelection)
        storedTtsVoice = voice ?? ""
    }

    var llmModelOptions: [String] {
        linguistVM.llmModelOptions
    }

    func loadLlmModelsIfNeeded() {
        linguistVM.loadLlmModelsIfNeeded()
    }

    func loadVoiceInventoryIfNeeded() {
        linguistVM.loadVoiceInventoryIfNeeded()
    }

    func ttsVoiceOptions(for inputLanguage: String?) -> [String] {
        linguistVM.ttsVoiceOptions(for: inputLanguage)
    }

    // MARK: - State Management

    func clearLinguistState() {
        linguistVM.close()
        bubbleFocusEnabled = false
        linguistSelection = nil
        linguistSelectionRange = nil
    }

    func closeLinguistBubble() {
        linguistVM.close()
        bubbleFocusEnabled = false
        #if os(iOS)
        bubbleKeyboardNavigator.exitFocus()
        #endif
    }

    /// Play word pronunciation from narration audio using cached timing reference
    func handlePlayFromNarration() {
        guard let audioRef = linguistBubble?.cachedAudioRef,
              let chunk = viewModel.selectedChunk else { return }
        let seekTime = audioRef.t0
        viewModel.seekPlayback(to: seekTime, in: chunk)
        if !audioCoordinator.isPlaying {
            audioCoordinator.play()
        }
    }

    func scheduleAutoLinguistLookup(in chunk: InteractiveChunk) {
        guard linguistBubble != nil else { return }
        guard !audioCoordinator.isPlaying else { return }
        linguistVM.autoLookupTask?.cancel()
        let chunkID = chunk.id
        linguistVM.autoLookupTask = Task { @MainActor in
            try? await Task.sleep(nanoseconds: linguistAutoLookupDelayNanos)
            guard !Task.isCancelled else { return }
            guard !audioCoordinator.isPlaying else { return }
            guard linguistBubble != nil else { return }
            guard viewModel.selectedChunk?.id == chunkID else { return }
            handleLinguistLookup(in: chunk)
        }
    }

    // MARK: - Pronunciation

    func startPronunciation(text: String, apiLanguage: String?, fallbackLanguage: String?, voice: String? = nil) {
        linguistVM.startPronunciation(text: text, apiLanguage: apiLanguage, fallbackLanguage: fallbackLanguage, voice: voice)
    }

    // MARK: - Language Utilities

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

    func pronunciationLanguage(
        for variantKind: TextPlayerVariantKind,
        inputLanguage: String,
        lookupLanguage: String
    ) -> String? {
        let preferred = self.lookupInputLanguage(
            for: variantKind,
            originalLanguage: inputLanguage,
            translationLanguage: lookupLanguage
        )
        let trimmed = preferred.trimmingCharacters(in: .whitespacesAndNewlines)
        return trimmed.isEmpty ? nil : trimmed
    }

    // MARK: - Font Scale

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
        get { 0.30 }
        nonmutating set { /* fixed on tvOS */ }
    }
    func toggleiPadLayoutDirection() {
        tvSplitEnabled.toggle()
    }
    var iPadBubblePinned: Bool {
        get { tvBubblePinned }
        nonmutating set { tvBubblePinned = newValue }
    }
    func toggleiPadBubblePin() {
        tvBubblePinned.toggle()
    }
    #endif
}
