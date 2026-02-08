import SwiftUI
#if os(iOS) || os(tvOS)
import UIKit
#endif

/// Set to true to enable verbose transcript/content debug logging
private let transcriptDebug = false

extension InteractivePlayerView {
    var baseContent: some View {
        ZStack {
            Color.black.ignoresSafeArea()
            playerContent
        }
    }

    var playerContent: some View {
        playerContentWrapped()
    }

    private func playerContentWrapped() -> some View {
        let viewModel = self.viewModel
        let audioCoordinator = self.audioCoordinator
        var view = AnyView(playerStack)
        #if !os(tvOS)
        view = AnyView(view.simultaneousGesture(menuToggleGesture, including: .subviews))
        #endif
        view = AnyView(view.onAppear {
            configureLinguistVM()
            loadLlmModelsIfNeeded()
            loadVoiceInventoryIfNeeded()
            refreshBookmarks()
            if let jobId = viewModel.jobId, let config = viewModel.apiConfiguration {
                heartbeatManager.start(
                    jobId: jobId,
                    originalLanguage: linguistInputLanguage,
                    translationLanguage: linguistLookupLanguage,
                    configuration: config,
                    audioCoordinator: viewModel.audioCoordinator,
                    sequenceController: viewModel.sequenceController,
                    audioModeManager: audioModeManager
                )
            }
            guard let chunk = viewModel.selectedChunk else { return }
            applyDefaultTrackSelection(for: chunk)
            syncSelectedSentence(for: chunk)
            viewModel.prefetchAdjacentSentencesIfNeeded(isPlaying: audioCoordinator.isPlaying)
            configureReadingBed()
            // NOTE: We no longer freeze transcript during sequence transitions.
            // Instead, interactiveContent() handles stale detection and shows appropriate
            // display (static for track switches, fresh for sentence changes) in real-time.
            // The onSequenceWillTransition callback is now a no-op but kept for debugging.
            if transcriptDebug { print("[TranscriptFreeze] Setting up onSequenceWillTransition callback (no-op)") }
            viewModel.onSequenceWillTransition = {
                if transcriptDebug { print("[TranscriptFreeze] onSequenceWillTransition callback invoked (no-op)") }
            }
            // Text track visibility should not affect audio playback.
            // Audio track selection is controlled separately via the audio toggle pills.
            viewModel.sequenceController.shouldSkipTrack = nil
            // Sync audio mode manager and sequence controller from AudioModeManager
            viewModel.audioModeManager = audioModeManager
            viewModel.sequenceController.audioMode = audioModeManager.currentMode
            #if os(tvOS)
            if !didSetInitialFocus {
                didSetInitialFocus = true
                Task { @MainActor in
                    focusedArea = .transcript
                }
            }
            #endif
        })
        view = AnyView(view.onChange(of: viewModel.selectedChunk?.id) { _, _ in
            guard let chunk = viewModel.selectedChunk else { return }
            // Respect pin state - keep bubble visible across chunk/sentence changes if pinned
            #if os(iOS)
            let shouldKeepBubble = isPad && iPadBubblePinned
            #elseif os(tvOS)
            let shouldKeepBubble = tvSplitEnabled && tvBubblePinned
            #else
            let shouldKeepBubble = false
            #endif
            if !shouldKeepBubble {
                clearLinguistState()
            }
            applyDefaultTrackSelection(for: chunk)
            syncSelectedSentence(for: chunk)
            viewModel.prefetchAdjacentSentencesIfNeeded(isPlaying: audioCoordinator.isPlaying)
            if isMenuVisible && !audioCoordinator.isPlaying {
                frozenTranscriptSentences = transcriptSentences(for: chunk)
                frozenPlaybackPrimaryKind = playbackPrimaryKind(for: chunk)
            } else {
                frozenTranscriptSentences = nil
                frozenPlaybackPrimaryKind = nil
            }
        })
        view = AnyView(view.onChange(of: trackAvailabilitySignature) { _, _ in
            guard let chunk = viewModel.selectedChunk else { return }
            applyDefaultTrackSelection(for: chunk)
        })
        view = AnyView(view.onChange(of: viewModel.highlightingTime) { _, _ in
            guard !isMenuVisible else { return }
            guard focusedArea != .controls && focusedArea != .bubble else { return }
            guard let chunk = viewModel.selectedChunk else { return }
            if audioCoordinator.isPlaying {
                viewModel.prefetchAdjacentSentencesIfNeeded(isPlaying: true)
                return
            }
            syncSelectedSentence(for: chunk)
        })
        view = AnyView(view.onChange(of: viewModel.readingBedURL) { _, _ in
            configureReadingBed()
        })
        view = AnyView(view.onChange(of: readingBedEnabled) { _, newValue in
            if useAppleMusicForBed && musicCoordinator.isAuthorized {
                handleReadingBedToggleWithAppleMusic(enabled: newValue)
            } else {
                updateReadingBedPlayback()
            }
        })
        view = AnyView(view.onChange(of: audioCoordinator.isPlaying) { _, isPlaying in
            handleNarrationPlaybackChange(isPlaying: isPlaying)
            if isPlaying {
                // Respect pin state - keep bubble visible during playback if pinned
                #if os(iOS)
                let shouldKeepBubble = isPad && iPadBubblePinned
                #elseif os(tvOS)
                let shouldKeepBubble = tvSplitEnabled && tvBubblePinned
                #else
                let shouldKeepBubble = false
                #endif
                if !shouldKeepBubble {
                    clearLinguistState()
                }
            }
            if isPlaying {
                // Don't unfreeze during sequence transitions - let the transition handler manage it
                if !viewModel.isSequenceTransitioning {
                    frozenTranscriptSentences = nil
                    frozenPlaybackPrimaryKind = nil
                }
                viewModel.prefetchAdjacentSentencesIfNeeded(isPlaying: true)
            } else if let chunk = viewModel.selectedChunk {
                syncPausedSelection(for: chunk)
                if isMenuVisible {
                    frozenTranscriptSentences = transcriptSentences(for: chunk)
                    frozenPlaybackPrimaryKind = playbackPrimaryKind(for: chunk)
                }
            }
        })
        view = AnyView(view.onChange(of: visibleTracks) { _, _ in
            // Respect pin state - keep bubble visible when tracks change if pinned
            #if os(iOS)
            let shouldKeepBubble = isPad && iPadBubblePinned
            #elseif os(tvOS)
            let shouldKeepBubble = tvSplitEnabled && tvBubblePinned
            #else
            let shouldKeepBubble = false
            #endif
            if !shouldKeepBubble {
                clearLinguistState()
            }
            if isMenuVisible, !audioCoordinator.isPlaying, let chunk = viewModel.selectedChunk {
                frozenTranscriptSentences = transcriptSentences(for: chunk)
                frozenPlaybackPrimaryKind = playbackPrimaryKind(for: chunk)
            }
            // Note: Text track visibility no longer affects audio playback.
            // Audio track selection is controlled separately via the audio picker.
            // This prevents counterintuitive behavior where hiding a text track
            // would also skip its audio in combined/sequence mode.
        })
        view = AnyView(view.onChange(of: isMenuVisible) { _, visible in
            guard let chunk = viewModel.selectedChunk else { return }
            if visible && !audioCoordinator.isPlaying {
                frozenTranscriptSentences = transcriptSentences(for: chunk)
                frozenPlaybackPrimaryKind = playbackPrimaryKind(for: chunk)
            } else {
                frozenTranscriptSentences = nil
                frozenPlaybackPrimaryKind = nil
            }
            // Only update reading bed when menu closes, not when it opens
            // This avoids unnecessary state changes during menu interactions
            if !visible {
                updateReadingBedPlayback()
            }
        })
        // Clear frozen state when sequence transitions complete
        // NOTE: We no longer freeze during transitions - instead, interactiveContent() handles
        // stale detection and correction in real-time during renders. This avoids race conditions
        // between frozen state updates and render cycles.
        view = AnyView(view.onChange(of: viewModel.isSequenceTransitioning) { _, isTransitioning in
            if transcriptDebug { print("[TranscriptFreeze] isSequenceTransitioning changed to \(isTransitioning)") }
            guard viewModel.isSequenceModeActive else {
                if transcriptDebug { print("[TranscriptFreeze] Not in sequence mode, skipping") }
                return
            }
            // When transition ends, ensure frozen state is cleared (unless menu is visible)
            if !isTransitioning && !isMenuVisible {
                if frozenTranscriptSentences != nil || frozenPlaybackPrimaryKind != nil {
                    if transcriptDebug { print("[TranscriptFreeze] Transition ended, clearing frozen state") }
                    frozenTranscriptSentences = nil
                    frozenPlaybackPrimaryKind = nil
                }
            }
        })
        view = AnyView(view.onChange(of: bookmarkIdentityKey) { _, _ in
            refreshBookmarks()
        })
        view = AnyView(
            view.onReceive(NotificationCenter.default.publisher(for: PlaybackBookmarkStore.didChangeNotification)) { notification in
                guard let jobId = resolvedBookmarkJobId else { return }
                let userId = resolvedBookmarkUserId
                if let changedUser = notification.userInfo?["userId"] as? String, changedUser != userId {
                    return
                }
                bookmarks = PlaybackBookmarkStore.shared.bookmarks(for: jobId, userId: userId)
            }
        )
        view = AnyView(view.onChange(of: readingBedCoordinator.isPlaying) { _, isPlaying in
            guard !isPlaying else { return }
            guard readingBedEnabled else { return }
            guard audioCoordinator.isPlaybackRequested else { return }
            // Only restart reading bed if narration is actively playing
            // Avoid restarting during transitions
            guard audioCoordinator.isPlaying else { return }
            updateReadingBedPlayback()
        })
        view = AnyView(view.onDisappear {
            heartbeatManager.stop()
            readingBedPauseTask?.cancel()
            readingBedPauseTask = nil
            readingBedCoordinator.reset()
            // Clean up Apple Music if it was the active reading bed
            if useAppleMusicForBed {
                musicCoordinator.pause()
                Task { await musicCoordinator.deactivateAsReadingBed() }
                audioCoordinator.configureAudioSessionForMixing(false)
                audioCoordinator.setTargetVolume(1.0)
            }
            clearLinguistState()
            // Clear the sequence transition callback to prevent dangling references
            viewModel.onSequenceWillTransition = nil
            // Clear the shouldSkipTrack callback
            viewModel.sequenceController.shouldSkipTrack = nil
        })
        // Audio mode change handler - sync to sequence controller when mode changes
        view = AnyView(view.onChange(of: audioModeManager.currentMode) { _, newMode in
            viewModel.sequenceController.audioMode = newMode
            print("[AudioToggle] Mode changed: \(newMode.description)")
        })
        // Apple Music source change handler
        view = AnyView(view.onChange(of: useAppleMusicForBed) { _, usingAppleMusic in
            if usingAppleMusic {
                switchToAppleMusic()
            } else {
                switchToBuiltInBed()
            }
        })
        // Apple Music volume change handler
        view = AnyView(view.onChange(of: musicVolume) { _, newVolume in
            handleMusicVolumeChange(newVolume)
        })
        // When Apple Music starts/stops playing externally (e.g., from Control Centre)
        view = AnyView(view.onChange(of: musicCoordinator.isPlaying) { _, isPlaying in
            if isPlaying && useAppleMusicForBed {
                // Apple Music started playing - pause built-in reading bed
                readingBedCoordinator.pause()
            }
        })
        // Music picker sheet presentation
        view = AnyView(view.sheet(isPresented: $showMusicPicker) {
            AppleMusicPickerView(
                searchService: musicSearchService,
                musicCoordinator: musicCoordinator,
                onSelect: {
                    useAppleMusicForBed = true
                    showMusicPicker = false
                },
                onDismiss: { showMusicPicker = false }
            )
            #if os(iOS)
            .presentationDetents([.medium, .large])
            #endif
        })
        return view
    }

    private var playerStack: some View {
        ZStack(alignment: .top) {
            playerMainLayer
                #if os(tvOS)
                .disabled(searchViewModel.isExpanded)
                #endif
            playerOverlayLayer
        }
    }

    @ViewBuilder
    private var playerMainLayer: some View {
        VStack(alignment: .leading, spacing: 12) {
            if let chunk = viewModel.selectedChunk {
                interactiveContent(for: chunk)
            } else {
                Text("No interactive chunks were returned for this job.")
                    .foregroundStyle(.secondary)
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
    }

    @ViewBuilder
    private var playerOverlayLayer: some View {
        // Background overlays - disabled when search is active on tvOS
        Group {
            if let chunk = viewModel.selectedChunk, (shouldShowHeaderOverlay || isTV) {
                playerInfoOverlay(for: chunk)
            }
            if let chunk = viewModel.selectedChunk {
                menuOverlay(for: chunk)
            }
            headerToggleButton
        }
        #if os(tvOS)
        .disabled(searchViewModel.isExpanded)
        #endif

        // Search overlay - on top and captures focus
        searchOverlayContainer

        // Other layers
        trackpadSwipeLayer
        shortcutHelpOverlay
        keyboardShortcutLayer
    }

    @ViewBuilder
    private var searchOverlayContainer: some View {
        if searchViewModel.isExpanded {
            ZStack {
                // Background dismissal area
                Color.black.opacity(0.3)
                    #if !os(tvOS)
                    .onTapGesture {
                        withAnimation(.easeOut(duration: 0.2)) {
                            searchViewModel.isExpanded = false
                        }
                    }
                    #endif

                // Search content
                VStack {
                    HStack {
                        Spacer()
                        searchOverlayView
                            .padding(.top, infoHeaderReservedHeight + 8)
                            .padding(.trailing, 8)
                    }
                    Spacer()
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            #if os(tvOS)
            .focusScope(searchFocusNamespace)
            .onExitCommand {
                withAnimation(.easeOut(duration: 0.2)) {
                    searchViewModel.isExpanded = false
                }
            }
            #endif
            .zIndex(3)
        }
    }

    var isPad: Bool {
        PlatformAdapter.isPad
    }

    var isPhone: Bool {
        PlatformAdapter.isPhone
    }

    var isPhonePortrait: Bool {
        #if os(iOS)
        return isPhone && verticalSizeClass == .regular
        #else
        return false
        #endif
    }

    var isTV: Bool {
        PlatformAdapter.isTV
    }

    var isShortcutHelpVisible: Bool {
        isShortcutHelpPinned || isShortcutHelpModifierActive
    }

    @ViewBuilder
    func interactiveContent(for chunk: InteractiveChunk) -> some View {
        // Simplified transcript handling:
        // 1. For same-sentence track switches: show static fully-revealed display
        // 2. For all other cases: build transcript normally based on current time
        //
        // The sequence controller's isSameSentenceTrackSwitch flag tells us when we're
        // switching tracks within the same sentence (e.g., original→translation).
        // During these transitions, we show all variants as fully revealed to avoid
        // the blip of showing partial reveal from the old track's perspective.
        let isTransitioning = viewModel.isSequenceTransitioning
        let isSameSentenceTrackSwitch = viewModel.sequenceController.isSameSentenceTrackSwitch
        let isDwelling = viewModel.sequenceController.isDwelling
        let currentSentenceIdx = viewModel.sequenceController.currentSentenceIndex
        let expectedPosition = viewModel.sequenceController.expectedPosition
        let currentPlaybackKind = playbackPrimaryKind(for: chunk)

        // Get timing track directly from sequence controller during transitions
        // This avoids timing issues where isSequenceModeActive might not be updated yet
        // due to SwiftUI's batched property updates
        let sequenceTimingTrack: TextPlayerTimingTrack = {
            switch viewModel.sequenceController.currentTrack {
            case .original:
                return .original
            case .translation:
                return .translation
            }
        }()

        let transcriptSentences: [TextPlayerSentenceDisplay] = {
            // During transitions, time-based sentence lookup can show the wrong sentence
            // because the time corresponds to a position in the NEW track that maps to a
            // different sentence in that track's timeline.
            //
            // Solution: During ANY transition, use the sequence controller's target sentence
            // index to show the correct sentence. For same-sentence switches, show all variants
            // fully revealed. For sentence changes, show the target sentence starting fresh.
            //
            // The settling window (right after transition ends) also needs protection for
            // same-sentence switches.
            let isInSameSentenceSettling = isSameSentenceTrackSwitch && expectedPosition != nil
            let isInSentenceChangeSettling = !isSameSentenceTrackSwitch && expectedPosition != nil

            // Only log state transitions, not every render (reduces log spam significantly)

            // During transitions, always use the target sentence from sequence controller
            // Use sequenceTimingTrack directly instead of activeTimingTrack to avoid timing issues
            // where isSequenceModeActive check might fail due to SwiftUI state propagation delays
            if isTransitioning, let targetIdx = currentSentenceIdx {
                // Debug: check if chunk has sentences and if target index is valid
                if transcriptDebug {
                    if chunk.sentences.isEmpty {
                        print("[InteractiveContent] WARNING: chunk.sentences is EMPTY during transition, targetIdx=\(targetIdx)")
                    } else if !chunk.sentences.indices.contains(targetIdx) {
                        print("[InteractiveContent] WARNING: targetIdx=\(targetIdx) out of bounds, chunk has \(chunk.sentences.count) sentences")
                    } else {
                        let sentence = chunk.sentences[targetIdx]
                        let hasTokens = !sentence.originalTokens.isEmpty || !sentence.translationTokens.isEmpty
                        if !hasTokens {
                            print("[InteractiveContent] WARNING: sentence[\(targetIdx)] has NO TOKENS - original=\(sentence.originalTokens.count), translation=\(sentence.translationTokens.count)")
                        }
                    }
                }

                if isSameSentenceTrackSwitch {
                    // Same-sentence switch: show previous track fully revealed, new track ready to animate
                    // e.g., when switching original→translation: original=full, translation=0
                    if let display = TextPlayerTimeline.buildTrackSwitchDisplay(
                        sentences: chunk.sentences,
                        activeIndex: targetIdx,
                        newPrimaryTrack: sequenceTimingTrack
                    ) {
                        if transcriptDebug { print("[InteractiveContent] SAME-SENTENCE SWITCH: transitioning=\(isTransitioning), using track-switch sentence[\(targetIdx)] with variants: \(display.variants.map { "\($0.kind.rawValue): \($0.revealedCount)/\($0.tokens.count)" }.joined(separator: ", "))") }
                        return [display]
                    }
                } else {
                    // Sentence change: show PREVIOUS sentence fully revealed during transition
                    // This prevents the blip where we briefly show the new sentence before it should appear
                    // The new sentence will be shown once the transition completes and time-based lookup takes over
                    if let prevIdx = viewModel.preTransitionSentenceIndex,
                       chunk.sentences.indices.contains(prevIdx) {
                        // Build a fully-revealed display for the previous sentence
                        if let display = TextPlayerTimeline.buildFullyRevealedDisplay(
                            sentences: chunk.sentences,
                            activeIndex: prevIdx
                        ) {
                            if transcriptDebug { print("[InteractiveContent] SENTENCE-CHANGE: transitioning=\(isTransitioning), showing PREVIOUS sentence[\(prevIdx)] fully revealed (target=\(targetIdx))") }
                            return [display]
                        }
                    }
                    // Fallback: show target sentence with first word revealed
                    // This happens if preTransitionSentenceIndex wasn't captured
                    if let display = TextPlayerTimeline.buildInitialDisplay(
                        sentences: chunk.sentences,
                        activeIndex: targetIdx,
                        primaryTrack: sequenceTimingTrack
                    ) {
                        if transcriptDebug { print("[InteractiveContent] SENTENCE-CHANGE (fallback): transitioning=\(isTransitioning), using initial sentence[\(targetIdx)] with variants: \(display.variants.map { "\($0.kind.rawValue): \($0.revealedCount)/\($0.tokens.count)" }.joined(separator: ", "))") }
                        return [display]
                    }
                }
            }

            // Settling window for same-sentence switches: build hybrid display
            // - Previous track (e.g., original): fully revealed (we just finished it)
            // - New track (e.g., translation): animated based on current time
            if isInSameSentenceSettling, let targetIdx = currentSentenceIdx {
                let playbackTime = viewModel.highlightingTime
                let playbackDuration = viewModel.playbackDuration(for: chunk) ?? audioCoordinator.duration
                let timelineDuration = viewModel.timelineDuration(for: chunk)
                let durationValue: Double? = timelineDuration ?? (playbackDuration > 0 ? playbackDuration : nil)

                if let display = TextPlayerTimeline.buildSettlingDisplay(
                    sentences: chunk.sentences,
                    activeIndex: targetIdx,
                    newPrimaryTrack: sequenceTimingTrack,
                    chunkTime: playbackTime,
                    audioDuration: durationValue,
                    timingVersion: chunk.timingVersion
                ) {
                    if transcriptDebug { print("[InteractiveContent] SAME-SENTENCE SETTLING: sentence[\(targetIdx)] at t=\(String(format: "%.3f", playbackTime)) with variants: \(display.variants.map { "\($0.kind.rawValue): \($0.revealedCount)/\($0.tokens.count)" }.joined(separator: ", "))") }
                    return [display]
                }
                // Fallback to static track-switch display
                if let display = TextPlayerTimeline.buildTrackSwitchDisplay(
                    sentences: chunk.sentences,
                    activeIndex: targetIdx,
                    newPrimaryTrack: sequenceTimingTrack
                ) {
                    if transcriptDebug { print("[InteractiveContent] SAME-SENTENCE SETTLING (fallback): using sentence[\(targetIdx)]") }
                    return [display]
                }
            }

            // Settling window for sentence changes: continue showing PREVIOUS sentence fully revealed
            // This prevents the blip where we briefly show the new sentence before time stabilizes
            if isInSentenceChangeSettling {
                // Use preTransitionSentenceIndex if available (captured at transition start)
                if let prevIdx = viewModel.preTransitionSentenceIndex,
                   chunk.sentences.indices.contains(prevIdx) {
                    if let display = TextPlayerTimeline.buildFullyRevealedDisplay(
                        sentences: chunk.sentences,
                        activeIndex: prevIdx
                    ) {
                        if transcriptDebug { print("[InteractiveContent] SENTENCE-CHANGE SETTLING: showing PREVIOUS sentence[\(prevIdx)] fully revealed (target=\(currentSentenceIdx ?? -1))") }
                        return [display]
                    }
                }
                // Fallback: show target sentence with initial display if preTransitionSentenceIndex not available
                if let targetIdx = currentSentenceIdx {
                    if let display = TextPlayerTimeline.buildInitialDisplay(
                        sentences: chunk.sentences,
                        activeIndex: targetIdx,
                        primaryTrack: sequenceTimingTrack
                    ) {
                        if transcriptDebug { print("[InteractiveContent] SENTENCE-CHANGE SETTLING (fallback): using initial sentence[\(targetIdx)] with variants: \(display.variants.map { "\($0.kind.rawValue): \($0.revealedCount)/\($0.tokens.count)" }.joined(separator: ", "))") }
                        return [display]
                    }
                }
            }

            // During dwell (paused at segment end to show last word), use sequence controller's
            // sentence index. Show current track fully revealed, other tracks at 0 (green).
            // The time has advanced past segment end so time-based lookup would return the WRONG sentence.
            if isDwelling, let targetIdx = currentSentenceIdx, chunk.sentences.indices.contains(targetIdx) {
                if let display = TextPlayerTimeline.buildDwellDisplay(
                    sentences: chunk.sentences,
                    activeIndex: targetIdx,
                    currentTrack: sequenceTimingTrack
                ) {
                    if transcriptDebug { print("[InteractiveContent] DWELL: sentence[\(targetIdx)] current=\(sequenceTimingTrack)") }
                    return [display]
                }
            }

            // For menu visible + paused, use frozen state if available
            if isMenuVisible, !audioCoordinator.isPlaying, let frozen = frozenTranscriptSentences {
                return frozen
            }

            // CRITICAL: During transitions, settling, or dwell, NEVER use time-based lookup as it can show wrong sentence.
            // The time value might be stale (from old track) and map to a different sentence on the new track.
            // During dwell, time has advanced past segment end and would map to the wrong sentence.
            // Always use the sequence controller's sentence index during these states.
            let isInAnyTransitionState = isTransitioning || isDwelling || isInSameSentenceSettling || (!isSameSentenceTrackSwitch && expectedPosition != nil)
            if isInAnyTransitionState, let targetIdx = currentSentenceIdx, chunk.sentences.indices.contains(targetIdx) {
                // Build initial display for the target sentence as a safe fallback
                // This ensures we never show the wrong sentence during transitions
                if let display = TextPlayerTimeline.buildInitialDisplay(
                    sentences: chunk.sentences,
                    activeIndex: targetIdx,
                    primaryTrack: sequenceTimingTrack
                ) {
                    if transcriptDebug { print("[InteractiveContent] TRANSITION FALLBACK: using initial sentence[\(targetIdx)]") }
                    return [display]
                }
            }

            // Post-stabilization guard: for a short period after time stabilizes, trust the sequence
            // controller's sentence index to prevent blips from timing jitter in the transcript lookup
            let stabilizationGuardDuration: TimeInterval = 0.25  // 250ms guard window
            if let stabilizedAt = viewModel.timeStabilizedAt,
               Date().timeIntervalSince(stabilizedAt) < stabilizationGuardDuration,
               let targetIdx = currentSentenceIdx,
               chunk.sentences.indices.contains(targetIdx) {
                // Build display based on sequence controller's current sentence, but with time-based reveal
                let playbackTime = viewModel.highlightingTime
                let playbackDuration = viewModel.playbackDuration(for: chunk) ?? audioCoordinator.duration
                let timelineDuration = viewModel.timelineDuration(for: chunk)
                let durationValue: Double? = timelineDuration ?? (playbackDuration > 0 ? playbackDuration : nil)

                if let display = TextPlayerTimeline.buildSettlingDisplay(
                    sentences: chunk.sentences,
                    activeIndex: targetIdx,
                    newPrimaryTrack: sequenceTimingTrack,
                    chunkTime: playbackTime,
                    audioDuration: durationValue,
                    timingVersion: chunk.timingVersion
                ) {
                    if transcriptDebug { print("[InteractiveContent] POST-STABILIZATION GUARD: sentence[\(targetIdx)] at t=\(String(format: "%.3f", playbackTime))") }
                    return [display]
                }
            }

            // Normal case: build transcript based on current time
            return self.transcriptSentences(for: chunk)
        }()

        // Determine playback primary kind for highlighting
        let resolvedPlaybackPrimaryKind: TextPlayerVariantKind? = {
            // For menu state, use frozen kind if available
            if isMenuVisible, !audioCoordinator.isPlaying, let frozen = frozenPlaybackPrimaryKind {
                return frozen
            }
            return playbackPrimaryKind(for: chunk)
        }()
        // Determine effective loading state: either explicit loading flag is set,
        // OR we have chunk sentences but no displayable tokens (placeholder state waiting for metadata)
        let effectiveIsLoading: Bool = {
            if viewModel.isTranscriptLoading {
                return true
            }
            // If transcriptSentences is empty but chunk has sentences, we're waiting for token data
            if transcriptSentences.isEmpty && !chunk.sentences.isEmpty {
                // Check if any chunk sentence has actual tokens
                let hasAnyTokens = chunk.sentences.contains { sentence in
                    !sentence.originalTokens.isEmpty || !sentence.translationTokens.isEmpty
                }
                // If no tokens exist yet, treat as loading
                return !hasAnyTokens
            }
            return false
        }()

        InteractiveTranscriptView(
            viewModel: viewModel,
            audioCoordinator: audioCoordinator,
            sentences: transcriptSentences,
            selection: linguistSelection,
            selectionRange: linguistSelectionRange,
            bubble: linguistBubble,
            lookupLanguage: resolvedLookupLanguage,
            lookupLanguageOptions: lookupLanguageOptions,
            onLookupLanguageChange: { storedLookupLanguage = $0 },
            llmModel: resolvedLlmModel ?? MyLinguistPreferences.defaultLlmModel,
            llmModelOptions: llmModelOptions,
            onLlmModelChange: { storedLlmModel = $0 },
            ttsVoice: voiceForCurrentLanguage,
            ttsVoiceOptions: ttsVoiceOptions(for: ttsLanguageForCurrentSelection),
            onTtsVoiceChange: { setVoiceForCurrentLanguage($0) },
            playbackPrimaryKind: resolvedPlaybackPrimaryKind,
            visibleTracks: visibleTracks,
            isBubbleFocusEnabled: bubbleFocusEnabled,
            onToggleTrack: { kind in
                toggleTrackIfAvailable(kind)
            },
            isMenuVisible: isMenuVisible,
            isTranscriptLoading: effectiveIsLoading,
            trackFontScale: trackFontScale,
            minTrackFontScale: trackFontScaleMin,
            maxTrackFontScale: trackFontScaleMax,
            autoScaleEnabled: autoScaleEnabled,
            linguistFontScale: linguistFontScale,
            canIncreaseLinguistFont: linguistFontScale < linguistFontScaleMax - 0.001,
            canDecreaseLinguistFont: linguistFontScale > linguistFontScaleMin + 0.001,
            focusedArea: $focusedArea,
            onSkipSentence: { delta in
                viewModel.skipSentence(forward: delta > 0, preferredTrack: preferredSequenceTrack)
            },
            onNavigateTrack: { delta in
                handleTrackNavigation(delta, in: chunk)
            },
            onShowMenu: {
                showMenu()
            },
            onHideMenu: {
                hideMenu()
            },
            onLookup: {
                handleLinguistLookup(in: chunk)
            },
            onLookupToken: { sentenceIndex, variantKind, tokenIndex, token in
                handleLinguistLookup(
                    sentenceIndex: sentenceIndex,
                    variantKind: variantKind,
                    tokenIndex: tokenIndex,
                    token: token
                )
            },
            onSeekToken: { sentenceIndex, sentenceNumber, variantKind, tokenIndex, seekTime in
                handleTokenSeek(
                    sentenceIndex: sentenceIndex,
                    sentenceNumber: sentenceNumber,
                    variantKind: variantKind,
                    tokenIndex: tokenIndex,
                    seekTime: seekTime,
                    in: chunk
                )
            },
            onUpdateSelectionRange: { range, selection in
                linguistSelection = selection
                linguistSelectionRange = range
            },
            onIncreaseLinguistFont: { handleKeyboardFontAdjust(increase: true) },
            onDecreaseLinguistFont: { handleKeyboardFontAdjust(increase: false) },
            onSetTrackFontScale: { setTrackFontScale($0) },
            onSetLinguistFontScale: { setLinguistFontScale($0) },
            onCloseBubble: {
                #if os(iOS)
                // On iPad, respect pinned state - only close if not pinned
                if isPad && iPadBubblePinned {
                    return
                }
                #elseif os(tvOS)
                // On tvOS, respect pinned state in split mode
                if tvSplitEnabled && tvBubblePinned {
                    return
                }
                #endif
                closeLinguistBubble()
            },
            onTogglePlayback: {
                audioCoordinator.togglePlayback()
            },
            onToggleHeader: {
                toggleHeaderCollapsed()
            },
            onBubblePreviousToken: {
                handleWordNavigation(-1, in: chunk)
                scheduleAutoLinguistLookup(in: chunk)
            },
            onBubbleNextToken: {
                handleWordNavigation(1, in: chunk)
                scheduleAutoLinguistLookup(in: chunk)
            },
            iPadSplitDirection: iPadSplitDirection,
            iPadSplitRatio: Binding(
                get: { iPadSplitRatio },
                set: { iPadSplitRatio = $0 }
            ),
            onToggleLayoutDirection: {
                toggleiPadLayoutDirection()
            },
            iPadBubblePinned: iPadBubblePinned,
            onToggleBubblePin: {
                toggleiPadBubblePin()
            },
            onPlayFromNarration: {
                handlePlayFromNarration()
            },
            bubbleKeyboardNavigator: bubbleKeyboardNavigator
        )
        .padding(.top, transcriptTopPadding)
    }

    @ViewBuilder
    func menuOverlay(for chunk: InteractiveChunk) -> some View {
        if isMenuVisible {
            VStack(alignment: .leading, spacing: 12) {
                menuDragHandle
                if let summary = viewModel.highlightingSummary {
                    Text(summary)
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }
                controlBar(chunk)
            }
            .padding(12)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(menuBackground)
            .clipShape(RoundedRectangle(cornerRadius: 16))
            .shadow(color: Color.black.opacity(0.25), radius: 12, x: 0, y: 6)
            .transition(.move(edge: .top).combined(with: .opacity))
            .accessibilityAddTraits(.isModal)
            .zIndex(2)
        }
    }

}
