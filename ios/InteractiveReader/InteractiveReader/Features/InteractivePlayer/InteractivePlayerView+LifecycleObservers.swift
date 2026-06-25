import SwiftUI
import OSLog

private let playerLifecycleDebug = false
private let interactiveLifecycleLogger = Logger(subsystem: "InteractiveReader", category: "InteractiveLifecycle")

extension InteractivePlayerView {
    var playerContent: some View {
        playerContentWrapped()
    }

    private func playerContentWrapped() -> some View {
        playerPresentedContent
    }

    private var playerPresentedContent: some View {
        playerExternalObservedContent
            .sheet(isPresented: $showMusicPicker) {
                AppleMusicPickerView(
                    searchService: musicSearchService,
                    musicCoordinator: musicCoordinator,
                    onSelect: handleMusicPickerSelection,
                    onDismiss: handleMusicPickerDismiss
                )
                #if os(iOS)
                .presentationDetents([.medium, .large])
                #endif
            }
    }

    private var playerExternalObservedContent: some View {
        playerStateObservedContent
            .onReceive(
                NotificationCenter.default.publisher(for: PlaybackBookmarkStore.didChangeNotification),
                perform: handleBookmarkStoreChange
            )
            .onChange(of: readingBedCoordinator.isPlaying) { _, isPlaying in
                handleReadingBedPlaybackChange(isPlaying)
            }
            .onDisappear(perform: handlePlayerDisappear)
            .onChange(of: audioModeManager.currentMode) { _, newMode in
                handleAudioModeChange(newMode)
            }
            .onChange(of: useAppleMusicForBed) { _, usingAppleMusic in
                handleAppleMusicSourceChange(usingAppleMusic)
            }
            .onChange(of: musicVolume) { _, newVolume in
                handleMusicVolumeChange(newVolume)
            }
            .onChange(of: musicCoordinator.isPlaying) { _, isPlaying in
                handleAppleMusicPlaybackChange(isPlaying)
            }
    }

    private var playerStateObservedContent: some View {
        playerLifecycleContent
            .onChange(of: audioCoordinator.isPlaying) { _, isPlaying in
                handleAudioPlaybackChange(isPlaying)
            }
            .onChange(of: linguistBubble) { _, _ in
                handleLinguistBubbleChange()
            }
            .onChange(of: visibleTracks) { _, _ in
                handleVisibleTracksChange()
            }
            .onChange(of: isMenuVisible) { _, visible in
                handleMenuVisibilityChange(visible)
            }
            .onChange(of: viewModel.isSequenceTransitioning) { _, isTransitioning in
                handleSequenceTransitionChange(isTransitioning)
            }
            .onChange(of: bookmarkIdentityKey) { _, _ in
                handleBookmarkIdentityChange()
            }
    }

    private var playerLifecycleContent: some View {
        playerStackWithGestures
            .onAppear(perform: handlePlayerAppear)
            .onChange(of: viewModel.selectedChunk?.id) { _, _ in
                handleSelectedChunkChange()
            }
            .onChange(of: trackAvailabilitySignature) { _, _ in
                handleTrackAvailabilityChange()
            }
            .onChange(of: viewModel.highlightingTime) { _, _ in
                handleHighlightingTimeChange()
            }
            .onChange(of: viewModel.readingBedURL) { _, _ in
                handleReadingBedURLChange()
            }
            .onChange(of: readingBedEnabled) { _, newValue in
                handleReadingBedEnabledChange(newValue)
            }
    }

    @ViewBuilder
    private var playerStackWithGestures: some View {
        #if os(tvOS)
        playerStack
        #else
        playerStack.simultaneousGesture(menuToggleGesture, including: .subviews)
        #endif
    }

    private func handlePlayerAppear() {
        appState.playerKeyboardShortcutsActive = true
        #if os(iOS)
        if isPad {
            focusedArea = .transcript
        }
        #endif
        requestKeyboardShortcutFocus()
        configureLinguistVM()
        loadLlmModelsIfNeeded()
        loadVoiceInventoryIfNeeded()
        refreshBookmarks()
        guard let chunk = viewModel.selectedChunk else { return }
        applyDefaultTrackSelection(for: chunk)
        syncSelectedSentence(for: chunk)
        viewModel.prefetchAdjacentSentencesIfNeeded(isPlaying: audioCoordinator.isPlaying)
        configureReadingBed()
        if playerLifecycleDebug {
            interactiveLifecycleLogger.debug("Setting up onSequenceWillTransition callback (no-op)")
        }
        viewModel.onSequenceWillTransition = {
            if playerLifecycleDebug {
                interactiveLifecycleLogger.debug("onSequenceWillTransition callback invoked (no-op)")
            }
        }
        viewModel.sequenceController.shouldSkipTrack = nil
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
    }

    private func handleMusicPickerSelection() {
        useAppleMusicForBed = true
        showMusicPicker = false
    }

    private func handleMusicPickerDismiss() {
        showMusicPicker = false
    }

    private func handleSelectedChunkChange() {
        guard let chunk = viewModel.selectedChunk else { return }
        if !shouldKeepBubbleVisibleForPinnedState {
            clearLinguistState()
        }
        applyDefaultTrackSelection(for: chunk)
        syncSelectedSentence(for: chunk)
        viewModel.prefetchAdjacentSentencesIfNeeded(isPlaying: audioCoordinator.isPlaying)
        updateFrozenTranscriptState(for: chunk, shouldFreeze: isMenuVisible && !audioCoordinator.isPlaying)
    }

    private func handleTrackAvailabilityChange() {
        guard let chunk = viewModel.selectedChunk else { return }
        applyDefaultTrackSelection(for: chunk)
    }

    private func handleHighlightingTimeChange() {
        guard !isMenuVisible else { return }
        guard focusedArea != .controls && focusedArea != .bubble else { return }
        guard let chunk = viewModel.selectedChunk else { return }
        if audioCoordinator.isPlaying {
            viewModel.prefetchAdjacentSentencesIfNeeded(isPlaying: true)
            return
        }
        syncSelectedSentence(for: chunk)
    }

    private func handleReadingBedEnabledChange(_ isEnabled: Bool) {
        if useAppleMusicForBed && musicCoordinator.isAuthorized {
            handleReadingBedToggleWithAppleMusic(enabled: isEnabled)
        } else {
            updateReadingBedPlayback()
        }
    }

    private func handleAudioPlaybackChange(_ isPlaying: Bool) {
        #if os(iOS)
        if isPad {
            focusedArea = .transcript
        }
        #endif
        requestKeyboardShortcutFocus()
        handleNarrationPlaybackChange(isPlaying: isPlaying)
        if isPlaying {
            if !shouldKeepBubbleVisibleForPinnedState {
                clearLinguistState()
            }
            requestKeyboardShortcutFocus()
        }
        if isPlaying {
            if !viewModel.isSequenceTransitioning {
                frozenTranscriptSentences = nil
                frozenPlaybackPrimaryKind = nil
            }
            viewModel.prefetchAdjacentSentencesIfNeeded(isPlaying: true)
        } else if let chunk = viewModel.selectedChunk {
            syncPausedSelection(for: chunk)
            if isMenuVisible {
                updateFrozenTranscriptState(for: chunk, shouldFreeze: true)
            }
        }
    }

    private func handleLinguistBubbleChange() {
        #if os(iOS)
        if isPad {
            focusedArea = .transcript
        }
        #endif
        requestKeyboardShortcutFocus()
    }

    private func handleVisibleTracksChange() {
        if !shouldKeepBubbleVisibleForPinnedState {
            clearLinguistState()
        }
        if isMenuVisible, !audioCoordinator.isPlaying, let chunk = viewModel.selectedChunk {
            updateFrozenTranscriptState(for: chunk, shouldFreeze: true)
        }
    }

    private func handleMenuVisibilityChange(_ isVisible: Bool) {
        guard let chunk = viewModel.selectedChunk else { return }
        updateFrozenTranscriptState(for: chunk, shouldFreeze: isVisible && !audioCoordinator.isPlaying)
        if !isVisible {
            updateReadingBedPlayback()
        }
    }

    private func handleSequenceTransitionChange(_ isTransitioning: Bool) {
        if playerLifecycleDebug {
            interactiveLifecycleLogger.debug("isSequenceTransitioning changed to \(isTransitioning, privacy: .public)")
        }
        guard viewModel.isSequenceModeActive else {
            if playerLifecycleDebug {
                interactiveLifecycleLogger.debug("Not in sequence mode, skipping")
            }
            return
        }
        if !isTransitioning && !isMenuVisible {
            if frozenTranscriptSentences != nil || frozenPlaybackPrimaryKind != nil {
                if playerLifecycleDebug {
                    interactiveLifecycleLogger.debug("Transition ended, clearing frozen state")
                }
                frozenTranscriptSentences = nil
                frozenPlaybackPrimaryKind = nil
            }
        }
    }

    private func handleBookmarkIdentityChange() {
        refreshBookmarks()
    }

    private func handleReadingBedURLChange() {
        configureReadingBed()
    }

    private func handleBookmarkStoreChange(_ notification: Notification) {
        guard let jobId = resolvedBookmarkJobId else { return }
        let userId = resolvedBookmarkUserId
        if let changedUser = notification.userInfo?["userId"] as? String, changedUser != userId {
            return
        }
        bookmarks = PlaybackBookmarkStore.shared.bookmarks(for: jobId, userId: userId)
    }

    private func handleReadingBedPlaybackChange(_ isPlaying: Bool) {
        guard !isPlaying else { return }
        guard readingBedEnabled else { return }
        guard audioCoordinator.isPlaybackRequested else { return }
        guard audioCoordinator.isPlaying else { return }
        updateReadingBedPlayback()
    }

    private func handlePlayerDisappear() {
        appState.playerKeyboardShortcutsActive = false
        sleepTimer.cancel()
        readingBedPauseTask?.cancel()
        readingBedPauseTask = nil
        readingBedCoordinator.reset()
        if useAppleMusicForBed {
            musicCoordinator.pause()
            Task { await musicCoordinator.deactivateAsReadingBed() }
            audioCoordinator.configureAudioSessionForMixing(false)
            audioCoordinator.setTargetVolume(1.0)
        }
        clearLinguistState()
        viewModel.onSequenceWillTransition = nil
        viewModel.sequenceController.shouldSkipTrack = nil
    }

    private func handleAudioModeChange(_ newMode: AudioMode) {
        viewModel.sequenceController.audioMode = newMode
        interactiveLifecycleLogger.debug("Audio mode changed: \(newMode.description, privacy: .public)")
    }

    private func handleAppleMusicSourceChange(_ usingAppleMusic: Bool) {
        if usingAppleMusic {
            switchToAppleMusic()
        } else {
            switchToBuiltInBed()
        }
    }

    private func handleAppleMusicPlaybackChange(_ isPlaying: Bool) {
        if isPlaying && useAppleMusicForBed {
            readingBedCoordinator.pause()
        }
    }

    private var shouldKeepBubbleVisibleForPinnedState: Bool {
        #if os(iOS)
        return isPad && iPadBubblePinned
        #elseif os(tvOS)
        return tvSplitEnabled && tvBubblePinned
        #else
        return false
        #endif
    }

    private func updateFrozenTranscriptState(for chunk: InteractiveChunk, shouldFreeze: Bool) {
        if shouldFreeze {
            frozenTranscriptSentences = transcriptSentences(for: chunk)
            frozenPlaybackPrimaryKind = playbackPrimaryKind(for: chunk)
        } else {
            frozenTranscriptSentences = nil
            frozenPlaybackPrimaryKind = nil
        }
    }
}
