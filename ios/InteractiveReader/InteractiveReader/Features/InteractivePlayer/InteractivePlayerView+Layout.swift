import SwiftUI
#if os(iOS) || os(tvOS)
import UIKit
#endif

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
            loadLlmModelsIfNeeded()
            loadVoiceInventoryIfNeeded()
            refreshBookmarks()
            guard let chunk = viewModel.selectedChunk else { return }
            applyDefaultTrackSelection(for: chunk)
            syncSelectedSentence(for: chunk)
            viewModel.prefetchAdjacentSentencesIfNeeded(isPlaying: audioCoordinator.isPlaying)
            configureReadingBed()
            // NOTE: We no longer freeze transcript during sequence transitions.
            // Instead, interactiveContent() handles stale detection and shows appropriate
            // display (static for track switches, fresh for sentence changes) in real-time.
            // The onSequenceWillTransition callback is now a no-op but kept for debugging.
            print("[TranscriptFreeze] Setting up onSequenceWillTransition callback (no-op)")
            viewModel.onSequenceWillTransition = {
                print("[TranscriptFreeze] onSequenceWillTransition callback invoked (no-op)")
            }
            // Set up shouldSkipTrack callback to skip hidden tracks during playback
            updateShouldSkipTrackCallback()
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
            clearLinguistState()
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
        view = AnyView(view.onChange(of: readingBedEnabled) { _, _ in
            updateReadingBedPlayback()
        })
        view = AnyView(view.onChange(of: audioCoordinator.isPlaying) { _, isPlaying in
            handleNarrationPlaybackChange(isPlaying: isPlaying)
            if isPlaying {
                clearLinguistState()
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
            clearLinguistState()
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
            print("[TranscriptFreeze] isSequenceTransitioning changed to \(isTransitioning)")
            guard viewModel.isSequenceModeActive else {
                print("[TranscriptFreeze] Not in sequence mode, skipping")
                return
            }
            // When transition ends, ensure frozen state is cleared (unless menu is visible)
            if !isTransitioning && !isMenuVisible {
                if frozenTranscriptSentences != nil || frozenPlaybackPrimaryKind != nil {
                    print("[TranscriptFreeze] Transition ended, clearing frozen state")
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
            readingBedPauseTask?.cancel()
            readingBedPauseTask = nil
            readingBedCoordinator.reset()
            clearLinguistState()
            // Clear the sequence transition callback to prevent dangling references
            viewModel.onSequenceWillTransition = nil
            // Clear the shouldSkipTrack callback
            viewModel.sequenceController.shouldSkipTrack = nil
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
        #if os(iOS)
        return UIDevice.current.userInterfaceIdiom == .pad
        #else
        return false
        #endif
    }

    var isPhone: Bool {
        #if os(iOS)
        return UIDevice.current.userInterfaceIdiom == .phone
        #else
        return false
        #endif
    }

    var isPhonePortrait: Bool {
        #if os(iOS)
        return isPhone && verticalSizeClass == .regular
        #else
        return false
        #endif
    }

    var isTV: Bool {
        #if os(tvOS)
        return true
        #else
        return false
        #endif
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

            // Log EVERY render in sequence mode to catch the blip
            if viewModel.sequenceController.isEnabled {
                print("[InteractiveContent] RENDER: trans=\(isTransitioning), dwell=\(isDwelling), sameSentence=\(isSameSentenceTrackSwitch), sameSentenceSettling=\(isInSameSentenceSettling), sentenceChangeSettling=\(isInSentenceChangeSettling), seqIdx=\(currentSentenceIdx ?? -1), preTransIdx=\(viewModel.preTransitionSentenceIndex ?? -1), stabilizedAt=\(viewModel.timeStabilizedAt != nil)")
            }

            // During transitions, always use the target sentence from sequence controller
            // Use sequenceTimingTrack directly instead of activeTimingTrack to avoid timing issues
            // where isSequenceModeActive check might fail due to SwiftUI state propagation delays
            if isTransitioning, let targetIdx = currentSentenceIdx {
                // Debug: check if chunk has sentences and if target index is valid
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

                if isSameSentenceTrackSwitch {
                    // Same-sentence switch: show previous track fully revealed, new track ready to animate
                    // e.g., when switching original→translation: original=full, translation=0
                    if let display = TextPlayerTimeline.buildTrackSwitchDisplay(
                        sentences: chunk.sentences,
                        activeIndex: targetIdx,
                        newPrimaryTrack: sequenceTimingTrack
                    ) {
                        print("[InteractiveContent] SAME-SENTENCE SWITCH: transitioning=\(isTransitioning), using track-switch sentence[\(targetIdx)] with variants: \(display.variants.map { "\($0.kind.rawValue): \($0.revealedCount)/\($0.tokens.count)" }.joined(separator: ", "))")
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
                            print("[InteractiveContent] SENTENCE-CHANGE: transitioning=\(isTransitioning), showing PREVIOUS sentence[\(prevIdx)] fully revealed (target=\(targetIdx))")
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
                        print("[InteractiveContent] SENTENCE-CHANGE (fallback): transitioning=\(isTransitioning), using initial sentence[\(targetIdx)] with variants: \(display.variants.map { "\($0.kind.rawValue): \($0.revealedCount)/\($0.tokens.count)" }.joined(separator: ", "))")
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
                    print("[InteractiveContent] SAME-SENTENCE SETTLING: sentence[\(targetIdx)] at t=\(String(format: "%.3f", playbackTime)) with variants: \(display.variants.map { "\($0.kind.rawValue): \($0.revealedCount)/\($0.tokens.count)" }.joined(separator: ", "))")
                    return [display]
                }
                // Fallback to static track-switch display
                if let display = TextPlayerTimeline.buildTrackSwitchDisplay(
                    sentences: chunk.sentences,
                    activeIndex: targetIdx,
                    newPrimaryTrack: sequenceTimingTrack
                ) {
                    print("[InteractiveContent] SAME-SENTENCE SETTLING (fallback): using sentence[\(targetIdx)]")
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
                        print("[InteractiveContent] SENTENCE-CHANGE SETTLING: showing PREVIOUS sentence[\(prevIdx)] fully revealed (target=\(currentSentenceIdx ?? -1))")
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
                        print("[InteractiveContent] SENTENCE-CHANGE SETTLING (fallback): using initial sentence[\(targetIdx)] with variants: \(display.variants.map { "\($0.kind.rawValue): \($0.revealedCount)/\($0.tokens.count)" }.joined(separator: ", "))")
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
                    print("[InteractiveContent] DWELL: sentence[\(targetIdx)] current=\(sequenceTimingTrack)")
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
                    print("[InteractiveContent] TRANSITION FALLBACK: using initial sentence[\(targetIdx)]")
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
                    print("[InteractiveContent] POST-STABILIZATION GUARD: sentence[\(targetIdx)] at t=\(String(format: "%.3f", playbackTime))")
                    return [display]
                }
            }

            // Normal case: build transcript based on current time
            // Log when falling through to normal case during sequence mode to detect blips
            if viewModel.sequenceController.isEnabled {
                let normalTranscript = self.transcriptSentences(for: chunk)
                let sentenceInfo = normalTranscript.first.map { "sentence[\($0.index)]" } ?? "none"
                print("[InteractiveContent] NORMAL CASE (sequence mode): \(sentenceInfo), sequenceIdx=\(currentSentenceIdx.map(String.init) ?? "nil"), t=\(String(format: "%.3f", viewModel.highlightingTime))")
                return normalTranscript
            }
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
        let _ = {
            // Reduced logging - only log during active transitions or settling
            let isInSameSentenceSettling = isSameSentenceTrackSwitch && expectedPosition != nil
            let isInSentenceChangeSettling = !isSameSentenceTrackSwitch && expectedPosition != nil
            if isTransitioning || isInSameSentenceSettling || isInSentenceChangeSettling {
                let highlightTime = viewModel.highlightingTime
                let sentenceInfo = transcriptSentences.first.map { sentence -> String in
                    let variants = sentence.variants.map { variant in
                        "\(variant.kind.rawValue):\(variant.revealedCount)/\(variant.tokens.count)"
                    }.joined(separator: ", ")
                    return "s[\(sentence.index)] \(variants)"
                } ?? "no sentence"
                let settlingType = isInSameSentenceSettling ? "sameSentence" : (isInSentenceChangeSettling ? "sentenceChange" : "none")
                print("[InteractiveContent] transitioning=\(isTransitioning), sameSentence=\(isSameSentenceTrackSwitch), settling=\(settlingType), idx=\(currentSentenceIdx.map(String.init) ?? "nil"), t=\(String(format: "%.2f", highlightTime)) | \(sentenceInfo)")
            }
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
            ttsVoice: storedTtsVoice.isEmpty ? nil : storedTtsVoice,
            ttsVoiceOptions: ttsVoiceOptions(for: ttsLanguageForCurrentSelection),
            onTtsVoiceChange: { storedTtsVoice = $0 ?? "" },
            playbackPrimaryKind: resolvedPlaybackPrimaryKind,
            visibleTracks: visibleTracks,
            isBubbleFocusEnabled: bubbleFocusEnabled,
            onToggleTrack: { kind in
                toggleTrackIfAvailable(kind)
            },
            isMenuVisible: isMenuVisible,
            isTranscriptLoading: viewModel.isTranscriptLoading,
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

    @ViewBuilder
    var keyboardShortcutLayer: some View {
        #if os(iOS)
        if isPad {
            KeyboardCommandHandler(
                onPlayPause: { audioCoordinator.togglePlayback() },
                onPrevious: {
                    if bubbleKeyboardNavigator.isKeyboardFocusActive {
                        bubbleKeyboardNavigator.navigateLeft()
                    } else if audioCoordinator.isPlaying {
                        viewModel.skipSentence(forward: false, preferredTrack: preferredSequenceTrack)
                    } else {
                        handleWordNavigation(-1, in: viewModel.selectedChunk)
                    }
                },
                onNext: {
                    if bubbleKeyboardNavigator.isKeyboardFocusActive {
                        bubbleKeyboardNavigator.navigateRight()
                    } else if audioCoordinator.isPlaying {
                        viewModel.skipSentence(forward: true, preferredTrack: preferredSequenceTrack)
                    } else {
                        handleWordNavigation(1, in: viewModel.selectedChunk)
                    }
                },
                onPreviousWord: { handleWordNavigation(-1, in: viewModel.selectedChunk) },
                onNextWord: { handleWordNavigation(1, in: viewModel.selectedChunk) },
                onExtendSelectionBackward: {
                    guard let chunk = viewModel.selectedChunk else { return }
                    handleWordRangeSelection(-1, in: chunk)
                },
                onExtendSelectionForward: {
                    guard let chunk = viewModel.selectedChunk else { return }
                    handleWordRangeSelection(1, in: chunk)
                },
                onLookup: {
                    // Handle Enter key when in bubble keyboard focus mode
                    if bubbleKeyboardNavigator.isKeyboardFocusActive {
                        handleBubbleKeyboardActivate()
                        return
                    }
                    guard !audioCoordinator.isPlaying else { return }
                    guard let chunk = viewModel.selectedChunk else { return }
                    handleLinguistLookup(in: chunk)
                },
                onIncreaseFont: { adjustTrackFontScale(by: trackFontScaleStep) },
                onDecreaseFont: { adjustTrackFontScale(by: -trackFontScaleStep) },
                onToggleOriginal: { toggleTrackIfAvailable(.original) },
                onToggleTransliteration: { toggleTrackIfAvailable(.transliteration) },
                onToggleTranslation: { toggleTrackIfAvailable(.translation) },
                onToggleOriginalAudio: { toggleAudioTrack(.original) },
                onToggleTranslationAudio: { toggleAudioTrack(.translation) },
                onToggleReadingBed: { toggleReadingBed() },
                onIncreaseLinguistFont: { handleKeyboardFontAdjust(increase: true) },
                onDecreaseLinguistFont: { handleKeyboardFontAdjust(increase: false) },
                onToggleShortcutHelp: { toggleShortcutHelp() },
                onToggleHeader: { toggleHeaderCollapsed() },
                onIncreaseHeaderScale: { adjustHeaderScale(by: headerScaleStep) },
                onDecreaseHeaderScale: { adjustHeaderScale(by: -headerScaleStep) },
                onOptionKeyDown: { showShortcutHelpModifier() },
                onOptionKeyUp: { hideShortcutHelpModifier() },
                onShowMenu: {
                    if audioCoordinator.isPlaying {
                        showMenu()
                    } else if bubbleKeyboardNavigator.isKeyboardFocusActive {
                        // Already in bubble focus mode, ignore down arrow
                        return
                    } else if linguistBubble != nil, let chunk = viewModel.selectedChunk {
                        // Bubble is open, try to navigate down to it
                        let moved = handleTrackNavigation(1, in: chunk)
                        if !moved {
                            // At bottom track, enter bubble keyboard focus
                            bubbleKeyboardNavigator.enterFocus()
                        }
                    } else if let chunk = viewModel.selectedChunk {
                        handleTrackNavigation(1, in: chunk)
                    }
                },
                onHideMenu: {
                    if audioCoordinator.isPlaying {
                        hideMenu()
                    } else if bubbleKeyboardNavigator.isKeyboardFocusActive {
                        // Exit bubble keyboard focus
                        bubbleKeyboardNavigator.exitFocus()
                    } else if let chunk = viewModel.selectedChunk {
                        handleTrackNavigation(-1, in: chunk)
                    }
                },
                onBubbleNavigateLeft: {
                    bubbleKeyboardNavigator.navigateLeft()
                },
                onBubbleNavigateRight: {
                    bubbleKeyboardNavigator.navigateRight()
                }
            )
            .frame(width: 0, height: 0)
            .accessibilityHidden(true)
        }
        #else
        EmptyView()
        #endif
    }

    @ViewBuilder
    var trackpadSwipeLayer: some View {
        #if os(iOS)
        if isPad {
            TrackpadSwipeHandler(
                onSwipeDown: { showMenu() },
                onSwipeUp: { hideMenu() }
            )
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .accessibilityHidden(true)
        }
        #else
        EmptyView()
        #endif
    }

    func handleKeyboardFontAdjust(increase: Bool) {
        if linguistBubble != nil {
            adjustLinguistFontScale(by: increase ? linguistFontScaleStep : -linguistFontScaleStep)
        } else {
            adjustTrackFontScale(by: increase ? trackFontScaleStep : -trackFontScaleStep)
        }
    }

    @ViewBuilder
    var shortcutHelpOverlay: some View {
        #if os(iOS)
        if isPad, isShortcutHelpVisible {
            ShortcutHelpOverlayView(onDismiss: { dismissShortcutHelp() })
                .transition(.opacity)
                .zIndex(4)
        }
        #else
        EmptyView()
        #endif
    }

    #if !os(tvOS)
    var menuToggleGesture: some Gesture {
        DragGesture(minimumDistance: 24, coordinateSpace: .local)
            .onEnded { value in
                let horizontal = value.translation.width
                let vertical = value.translation.height
                guard abs(vertical) > abs(horizontal) else { return }
                if vertical > 24 {
                    showMenu()
                } else if vertical < -24 {
                    hideMenu()
                }
            }
    }
    #endif

    func showMenu() {
        guard !isMenuVisible else { return }
        guard viewModel.selectedChunk != nil else { return }
        resumePlaybackAfterMenu = audioCoordinator.isPlaybackRequested || audioCoordinator.isPlaying
        if resumePlaybackAfterMenu {
            audioCoordinator.pause()
        }
        withAnimation(.easeOut(duration: 0.2)) {
            isMenuVisible = true
        }
        #if os(tvOS)
        focusedArea = .controls
        #endif
    }

    func hideMenu() {
        guard isMenuVisible else { return }
        withAnimation(.easeOut(duration: 0.2)) {
            isMenuVisible = false
        }
        if resumePlaybackAfterMenu {
            audioCoordinator.play()
        }
        resumePlaybackAfterMenu = false
        #if os(tvOS)
        focusedArea = .transcript
        #endif
    }

    func playerInfoOverlay(for chunk: InteractiveChunk) -> some View {
        let variant = resolveInfoVariant()
        let label = headerInfo?.itemTypeLabel.isEmpty == false ? headerInfo?.itemTypeLabel : "Job"
        let slideLabel = slideIndicatorLabel(for: chunk)
        let timelineLabel = audioTimelineLabel(for: chunk)
        let showHeaderContent = !isHeaderCollapsed
        let headerView = HStack(alignment: .top, spacing: 12) {
            if showHeaderContent {
                PlayerChannelBugView(variant: variant, label: label, sizeScale: infoHeaderScale)
                if let headerInfo {
                    infoBadgeView(info: headerInfo, chunk: chunk)
                }
            }
            Spacer(minLength: 12)
            if showHeaderContent || isTV {
                VStack(alignment: .trailing, spacing: 6) {
                    if showHeaderContent {
                        if let slideLabel {
                            slideIndicatorView(label: slideLabel)
                        }
                        if let timelineLabel {
                            audioTimelineView(label: timelineLabel, onTap: toggleHeaderCollapsed)
                        }
                    } else if let timelineLabel {
                        audioTimelineView(label: timelineLabel, onTap: toggleHeaderCollapsed)
                    }
                    #if os(tvOS)
                    tvHeaderTogglePill
                    #endif
                }
            }
        }
        .padding(.horizontal, isPhonePortrait ? 16 : (isPhone ? 12 : 6))
        .padding(.top, 6)
        .frame(maxWidth: .infinity, alignment: .topLeading)
        .allowsHitTesting(true)
        #if os(tvOS)
        .onLongPressGesture(minimumDuration: 0.6) {
            toggleHeaderCollapsed()
        }
        #endif
        .zIndex(1)
        return headerMagnifyWrapper(headerView)
    }

    func infoBadgeView(info: InteractivePlayerHeaderInfo, chunk: InteractiveChunk) -> some View {
        let availableRoles = availableAudioRoles(for: chunk)
        let activeRoles = activeAudioRoles(for: chunk, availableRoles: availableRoles)
        return VStack(alignment: .leading, spacing: isPhonePortrait ? 6 : 0) {
            HStack(alignment: .top, spacing: 8) {
                if info.coverURL != nil || info.secondaryCoverURL != nil {
                    PlayerCoverStackView(
                        primaryURL: info.coverURL,
                        secondaryURL: info.secondaryCoverURL,
                        width: infoCoverWidth,
                        height: infoCoverHeight,
                        isTV: isTV
                    )
                }
                VStack(alignment: .leading, spacing: 2) {
                    Text(info.title.isEmpty ? "Untitled" : info.title)
                        .font(infoTitleFont)
                        .lineLimit(1)
                        .minimumScaleFactor(0.85)
                    if !info.author.isEmpty {
                        Text(info.author)
                            .font(infoMetaFont)
                            .foregroundStyle(Color.white.opacity(0.75))
                            .lineLimit(1)
                            .minimumScaleFactor(0.85)
                    }
                    // On non-portrait layouts, show flags inline with title/author
                    if !isPhonePortrait, !info.languageFlags.isEmpty {
                        HStack(spacing: 8 * infoPillScale) {
                            PlayerLanguageFlagRow(
                                flags: info.languageFlags,
                                modelLabel: isPhone ? nil : info.translationModel,
                                isTV: isTV,
                                sizeScale: infoPillScale,
                                activeRoles: activeRoles,
                                availableRoles: availableRoles,
                                onToggleRole: { role in
                                    toggleHeaderAudioRole(role, for: chunk, availableRoles: availableRoles)
                                },
                                showConnector: !isPhone
                            )
                            searchPillView
                            bookmarkRibbonPillView
                        }
                    }
                }
            }
            // On iPhone portrait, show flags/search/bookmark on separate row, aligned right
            if isPhonePortrait, !info.languageFlags.isEmpty {
                HStack(spacing: 6) {
                    Spacer()
                    PlayerLanguageFlagRow(
                        flags: info.languageFlags,
                        modelLabel: nil,
                        isTV: isTV,
                        sizeScale: infoPillScale,
                        activeRoles: activeRoles,
                        availableRoles: availableRoles,
                        onToggleRole: { role in
                            toggleHeaderAudioRole(role, for: chunk, availableRoles: availableRoles)
                        },
                        showConnector: false
                    )
                    searchPillView
                    bookmarkRibbonPillView
                }
            }
        }
    }

    func slideIndicatorView(label: String) -> some View {
        Text(label)
            .font(infoIndicatorFont)
            .foregroundStyle(Color.white.opacity(0.85))
            .lineLimit(1)
            .truncationMode(.tail)
            .padding(.horizontal, 10)
            .padding(.vertical, 4)
            .background(
                Capsule()
                    .fill(Color.black.opacity(0.6))
                    .overlay(
                        Capsule().stroke(Color.white.opacity(0.2), lineWidth: 1)
                    )
            )
    }

    func audioTimelineView(label: String, onTap: (() -> Void)? = nil) -> some View {
        Text(label)
            .font(infoIndicatorFont)
            .foregroundStyle(Color.white.opacity(0.75))
            .lineLimit(1)
            .truncationMode(.tail)
            .padding(.horizontal, 10)
            .padding(.vertical, 4)
            .background(
                Capsule()
                    .fill(Color.black.opacity(0.5))
                    .overlay(
                        Capsule().stroke(Color.white.opacity(0.18), lineWidth: 1)
                    )
            )
            .contentShape(Capsule())
            .onTapGesture {
                onTap?()
            }
    }

    var infoCoverWidth: CGFloat {
        PlayerInfoMetrics.coverWidth(isTV: isTV) * infoHeaderScale
    }

    var infoCoverHeight: CGFloat {
        PlayerInfoMetrics.coverHeight(isTV: isTV) * infoHeaderScale
    }

    var infoTitleFont: Font {
        #if os(tvOS)
        return .headline
        #else
        if isPad {
            return scaledHeaderFont(style: .subheadline, weight: .semibold)
        }
        return .subheadline.weight(.semibold)
        #endif
    }

    var infoMetaFont: Font {
        #if os(tvOS)
        return .callout
        #else
        if isPad {
            return scaledHeaderFont(style: .caption1, weight: .regular)
        }
        return .caption
        #endif
    }

    var infoIndicatorFont: Font {
        #if os(tvOS)
        return .callout.weight(.semibold)
        #else
        if isPad {
            return scaledHeaderFont(style: .caption1, weight: .semibold)
        }
        return .caption.weight(.semibold)
        #endif
    }

    var infoHeaderScale: CGFloat {
        #if os(iOS)
        let base: CGFloat = isPad ? 2.0 : 1.0
        return base * headerScale
        #else
        return 1.0
        #endif
    }

    var infoPillScale: CGFloat {
        #if os(iOS)
        let base: CGFloat = isPad ? 2.0 : 1.0
        return base * headerScale
        #else
        return 1.0
        #endif
    }

    private func scaledHeaderFont(style: UIFont.TextStyle, weight: Font.Weight) -> Font {
        #if os(iOS) || os(tvOS)
        let baseSize = UIFont.preferredFont(forTextStyle: style).pointSize
        return .system(size: baseSize * infoHeaderScale, weight: weight)
        #else
        return .system(size: 16 * infoHeaderScale, weight: weight)
        #endif
    }

    var headerScale: CGFloat {
        get { CGFloat(headerScaleValue) }
        nonmutating set { headerScaleValue = Double(newValue) }
    }

    func adjustHeaderScale(by delta: CGFloat) {
        setHeaderScale(headerScale + delta)
    }

    func setHeaderScale(_ value: CGFloat) {
        let updated = min(max(value, headerScaleMin), headerScaleMax)
        if updated != headerScale {
            headerScale = updated
        }
    }

    @ViewBuilder
    private func headerMagnifyWrapper<Content: View>(_ content: Content) -> some View {
        #if os(iOS)
        if isPad {
            // Use .subviews to allow Menu and other interactive elements to work
            // while still supporting pinch-to-zoom on non-interactive areas
            content.simultaneousGesture(headerMagnifyGesture, including: .subviews)
        } else {
            content
        }
        #else
        content
        #endif
    }

    #if os(iOS)
    private var headerMagnifyGesture: some Gesture {
        MagnificationGesture()
            .onChanged { value in
                if headerMagnifyStartScale == nil {
                    headerMagnifyStartScale = headerScale
                }
                let startScale = headerMagnifyStartScale ?? headerScale
                setHeaderScale(startScale * value)
            }
            .onEnded { _ in
                headerMagnifyStartScale = nil
            }
    }
    #endif

    var infoHeaderReservedHeight: CGFloat {
        #if os(tvOS)
        return PlayerInfoMetrics.badgeHeight(isTV: true) + 24
        #else
        let baseHeight = PlayerInfoMetrics.badgeHeight(isTV: false) * infoHeaderScale
        let padding = isPad ? 20 * infoHeaderScale : 16
        return baseHeight + padding
        #endif
    }

    var transcriptTopPadding: CGFloat {
        #if os(iOS) || os(tvOS)
        // Reduce padding when bubble is shown (header is auto-hidden on iPhone and iPad)
        if (isPhone || isPad) && linguistBubble != nil {
            return 8
        }
        return isHeaderCollapsed ? 8 : infoHeaderReservedHeight
        #else
        return infoHeaderReservedHeight
        #endif
    }

    var shouldShowHeaderOverlay: Bool {
        // Hide header on iPhone and iPad when bubble is shown to maximize screen space
        if (isPhone || isPad) && linguistBubble != nil {
            return false
        }
        return !isHeaderCollapsed
    }

    @ViewBuilder
    var headerToggleButton: some View {
        #if os(iOS)
        // Show timeline pill when header is collapsed OR when bubble is shown (auto-minimized)
        let showButton = isHeaderCollapsed || ((isPhone || isPad) && linguistBubble != nil)
        if showButton, let chunk = viewModel.selectedChunk {
            let timelineLabel = audioTimelineLabel(for: chunk)
            if let timelineLabel {
                // Position pill in top-right corner using VStack/HStack with Spacers
                // The Spacers don't have content shape so touches pass through
                VStack(spacing: 0) {
                    HStack(spacing: 0) {
                        Spacer(minLength: 0)
                        audioTimelineView(label: timelineLabel, onTap: toggleHeaderCollapsed)
                            .padding(.top, 6)
                            .padding(.trailing, 6)
                    }
                    Spacer(minLength: 0)
                }
                .zIndex(2)
            }
        }
        #else
        EmptyView()
        #endif
    }

    #if os(tvOS)
    var tvHeaderTogglePill: some View {
        Button(action: toggleHeaderCollapsed) {
            Image(systemName: isHeaderCollapsed ? "chevron.down" : "chevron.up")
                .font(.caption.weight(.semibold))
                .padding(.horizontal, 8)
                .padding(.vertical, 4)
                .background(Color.black.opacity(0.6), in: Capsule())
                .foregroundStyle(.white)
        }
        .buttonStyle(.plain)
        .focusable(focusedArea == .controls)
        .allowsHitTesting(focusedArea == .controls)
        .focused($focusedArea, equals: .controls)
        .accessibilityLabel(isHeaderCollapsed ? "Show header" : "Hide header")
    }
    #endif

    func toggleHeaderCollapsed() {
        withAnimation(.easeInOut(duration: 0.2)) {
            isHeaderCollapsed.toggle()
        }
    }

    func playbackPrimaryKind(for chunk: InteractiveChunk) -> TextPlayerVariantKind? {
        // Return a valid kind if playback is active or requested.
        // Using isPlaybackRequested in addition to isPlaying handles the brief moments
        // during track switches where isPlaying might be false momentarily.
        guard audioCoordinator.isPlaying || audioCoordinator.isPlaybackRequested else { return nil }
        let activeTrack = viewModel.activeTimingTrack(for: chunk)
        switch activeTrack {
        case .original:
            if visibleTracks.contains(.original) {
                return .original
            }
            if visibleTracks.contains(.translation) {
                return .translation
            }
            if visibleTracks.contains(.transliteration) {
                return .transliteration
            }
        case .translation, .mix:
            if visibleTracks.contains(.translation) {
                return .translation
            }
            if visibleTracks.contains(.transliteration) {
                return .transliteration
            }
            if visibleTracks.contains(.original) {
                return .original
            }
        }
        return nil
    }

    func resolveInfoVariant() -> PlayerChannelVariant {
        let rawLabel = (headerInfo?.itemTypeLabel ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
        let lower = rawLabel.lowercased()
        if lower.contains("subtitle") {
            return .subtitles
        }
        if lower.contains("video") {
            return .video
        }
        if lower.contains("book") || headerInfo?.author.isEmpty == false || headerInfo?.title.isEmpty == false {
            return .book
        }
        return .job
    }

    func slideIndicatorLabel(for chunk: InteractiveChunk) -> String? {
        guard let currentSentence = currentSentenceNumber(for: chunk) else { return nil }
        let jobBounds = jobSentenceBounds
        let jobStart = jobBounds.start ?? 1
        let jobEnd = jobBounds.end
        let displayCurrent = jobEnd.map { min(currentSentence, $0) } ?? currentSentence

        // Unified compact format across all platforms
        var label = jobEnd != nil
            ? "S:\(displayCurrent)/\(jobEnd ?? displayCurrent)"
            : "S:\(displayCurrent)"

        var suffixParts: [String] = []
        if let jobEnd {
            let span = max(jobEnd - jobStart, 0)
            let ratio = span > 0 ? Double(displayCurrent - jobStart) / Double(span) : 1
            if ratio.isFinite {
                let percent = min(max(Int(round(ratio * 100)), 0), 100)
                suffixParts.append("J:\(percent)%")
            }
        }
        if let bookTotal = bookTotalSentences(jobEnd: jobEnd) {
            let ratio = bookTotal > 0 ? Double(displayCurrent) / Double(bookTotal) : 1
            if ratio.isFinite {
                let percent = min(max(Int(round(ratio * 100)), 0), 100)
                suffixParts.append("B:\(percent)%")
            }
        }
        if !suffixParts.isEmpty {
            label += " · " + suffixParts.joined(separator: " · ")
        }
        return label
    }

    func audioTimelineLabel(for chunk: InteractiveChunk) -> String? {
        guard let metrics = audioTimelineMetrics(for: chunk) else { return nil }
        let played = formatDurationLabel(metrics.played)
        let remaining = formatDurationLabel(metrics.remaining)
        return "\(played) / \(remaining)"
    }

    func audioTimelineMetrics(
        for chunk: InteractiveChunk
    ) -> (played: Double, remaining: Double, total: Double)? {
        guard let context = viewModel.jobContext else { return nil }
        let chunks = context.chunks
        guard let currentIndex = chunks.firstIndex(where: { $0.id == chunk.id }) else { return nil }
        let preferredKind = selectedAudioKind(for: chunk)
        let total = chunks.reduce(0.0) { partial, entry in
            partial + resolvedAudioDuration(for: entry, preferredKind: preferredKind, isCurrent: entry.id == chunk.id)
        }
        guard total > 0 else { return nil }
        let before = chunks.prefix(currentIndex).reduce(0.0) { partial, entry in
            partial + resolvedAudioDuration(for: entry, preferredKind: preferredKind, isCurrent: false)
        }
        let currentDuration = resolvedAudioDuration(for: chunk, preferredKind: preferredKind, isCurrent: true)
        let usesCombinedQueue = preferredKind == .combined && viewModel.usesCombinedQueue(for: chunk)
        let currentTime = max(
            usesCombinedQueue ? viewModel.combinedQueuePlaybackTime(for: chunk) : viewModel.playbackTime(for: chunk),
            0
        )
        let within = currentDuration > 0 ? min(currentTime, currentDuration) : currentTime
        let played = min(before + within, total)
        let remaining = max(total - played, 0)
        return (played, remaining, total)
    }

    func selectedAudioKind(for chunk: InteractiveChunk) -> InteractiveChunk.AudioOption.Kind? {
        if let selectedID = viewModel.selectedAudioTrackID,
           let option = chunk.audioOptions.first(where: { $0.id == selectedID }) {
            return option.kind
        }
        return chunk.audioOptions.first?.kind
    }

    func availableAudioRoles(for chunk: InteractiveChunk) -> Set<LanguageFlagRole> {
        let kinds = Set(chunk.audioOptions.map(\.kind))
        var roles: Set<LanguageFlagRole> = []
        if kinds.contains(.original) {
            roles.insert(.original)
        }
        if kinds.contains(.translation) {
            roles.insert(.translation)
        }
        if roles.isEmpty, kinds.contains(.combined) {
            roles = [.original, .translation]
        }
        return roles
    }

    func activeAudioRoles(
        for chunk: InteractiveChunk,
        availableRoles: Set<LanguageFlagRole>
    ) -> Set<LanguageFlagRole> {
        guard let kind = selectedAudioKind(for: chunk) else { return [] }
        switch kind {
        case .original:
            return availableRoles.contains(.original) ? [.original] : []
        case .translation:
            return availableRoles.contains(.translation) ? [.translation] : []
        case .combined, .other:
            return availableRoles.intersection([.original, .translation])
        }
    }

    func toggleHeaderAudioRole(
        _ role: LanguageFlagRole,
        for chunk: InteractiveChunk,
        availableRoles: Set<LanguageFlagRole>
    ) {
        guard !availableRoles.isEmpty else { return }
        var activeRoles = activeAudioRoles(for: chunk, availableRoles: availableRoles)
        if activeRoles.isEmpty {
            activeRoles = availableRoles
        }
        if activeRoles.contains(role) {
            if activeRoles.count > 1 {
                activeRoles.remove(role)
            } else {
                return
            }
        } else {
            activeRoles.insert(role)
        }
        selectAudioTrack(for: chunk, preferredRoles: activeRoles, availableRoles: availableRoles)
    }

    func selectAudioTrack(
        for chunk: InteractiveChunk,
        preferredRoles: Set<LanguageFlagRole>,
        availableRoles: Set<LanguageFlagRole>
    ) {
        let options = chunk.audioOptions
        guard !options.isEmpty else { return }
        let combinedOption = options.first(where: { $0.kind == .combined })
        let originalOption = options.first(where: { $0.kind == .original })
        let translationOption = options.first(where: { $0.kind == .translation })
        var desiredRoles = preferredRoles.intersection(availableRoles)
        if desiredRoles.isEmpty {
            desiredRoles = availableRoles
        }
        let targetOption: InteractiveChunk.AudioOption?
        if desiredRoles.contains(.original), desiredRoles.contains(.translation), let combinedOption {
            targetOption = combinedOption
        } else if desiredRoles.contains(.original), let originalOption {
            targetOption = originalOption
        } else if desiredRoles.contains(.translation), let translationOption {
            targetOption = translationOption
        } else if let combinedOption {
            targetOption = combinedOption
        } else {
            targetOption = translationOption ?? originalOption ?? options.first
        }
        if let targetOption, targetOption.id != viewModel.selectedAudioTrackID {
            viewModel.selectAudioTrack(id: targetOption.id)
        }
    }

    func resolvedAudioDuration(
        for chunk: InteractiveChunk,
        preferredKind: InteractiveChunk.AudioOption.Kind?,
        isCurrent: Bool
    ) -> Double {
        let usesCombinedQueue = preferredKind == .combined && viewModel.usesCombinedQueue(for: chunk)
        if isCurrent {
            if usesCombinedQueue,
               let duration = viewModel.combinedPlaybackDuration(for: chunk) {
                return max(duration, 0)
            }
            if let duration = viewModel.timelineDuration(for: chunk) ?? viewModel.playbackDuration(for: chunk) {
                return max(duration, 0)
            }
        }
        if usesCombinedQueue,
           let duration = viewModel.combinedPlaybackDuration(for: chunk) {
            return max(duration, 0)
        }
        let option = chunk.audioOptions.first(where: { $0.kind == preferredKind }) ?? chunk.audioOptions.first
        if let duration = option?.duration, duration > 0 {
            return duration
        }
        if preferredKind == .combined,
           let fallback = viewModel.fallbackDuration(for: chunk, kind: .combined),
           fallback > 0 {
            return fallback
        }
        if let option,
           let fallback = viewModel.fallbackDuration(for: chunk, kind: option.kind),
           fallback > 0 {
            return fallback
        }
        let sentenceSum = chunk.sentences.compactMap { $0.totalDuration }.reduce(0, +)
        if sentenceSum > 0 {
            return sentenceSum
        }
        return 0
    }

    func formatDurationLabel(_ value: Double) -> String {
        let total = max(0, Int(value.rounded()))
        let hours = total / 3600
        let minutes = (total % 3600) / 60
        let seconds = total % 60
        if hours > 0 {
            return String(format: "%02d:%02d:%02d", hours, minutes, seconds)
        }
        return String(format: "%02d:%02d", minutes, seconds)
    }

    func currentSentenceNumber(for chunk: InteractiveChunk) -> Int? {
        if let active = activeSentenceDisplay(for: chunk) {
            if let number = active.sentenceNumber {
                return number
            }
            if let start = chunk.startSentence {
                return start + max(active.index, 0)
            }
            return active.index + 1
        }
        return nil
    }

    func bookTotalSentences(jobEnd: Int?) -> Int? {
        if !viewModel.chapterEntries.isEmpty {
            var maxEnd: Int?
            for chapter in viewModel.chapterEntries {
                let candidate = chapter.endSentence ?? chapter.startSentence
                maxEnd = maxEnd.map { max($0, candidate) } ?? candidate
            }
            return maxEnd
        }
        return jobEnd
    }
}
