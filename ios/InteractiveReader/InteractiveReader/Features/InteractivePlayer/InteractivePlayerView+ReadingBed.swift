import SwiftUI
#if os(iOS) || os(tvOS)
import UIKit
#endif

// MARK: - tvOS Button Style for Header Pills (Music, Speed, Jump)

#if os(tvOS)
/// Unified button style for all header pills on tvOS.
/// Matches TVLanguageFlagButtonStyle for consistent focus appearance.
struct TVHeaderPillButtonStyle: ButtonStyle {
    @Environment(\.isFocused) var isFocused

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .scaleEffect(configuration.isPressed ? 0.95 : (isFocused ? 1.1 : 1.0))
            .brightness(isFocused ? 0.15 : 0)
            .animation(.easeInOut(duration: 0.15), value: isFocused)
            .animation(.easeInOut(duration: 0.1), value: configuration.isPressed)
    }
}

// Keep TVMusicPillButtonStyle as an alias for backwards compatibility
typealias TVMusicPillButtonStyle = TVHeaderPillButtonStyle
#endif

extension InteractivePlayerView {
    func toggleReadingBed() {
        withAnimation(.none) {
            readingBedEnabled.toggle()
        }
    }

    var selectedReadingBedLabel: String {
        if useAppleMusicForBed, let title = musicCoordinator.currentSongTitle {
            return title
        }
        if let selectedID = viewModel.selectedReadingBedID,
           let beds = viewModel.readingBedCatalog?.beds,
           let match = beds.first(where: { $0.id == selectedID }) {
            return match.label.isEmpty ? match.id : match.label
        }
        return "Default"
    }

    func readingBedSummary(label: String) -> String {
        let state = readingBedEnabled ? "On" : "Off"
        if label.isEmpty {
            return state
        }
        return "\(state) / \(label)"
    }

    func configureReadingBed() {
        if useAppleMusicForBed && musicCoordinator.isAuthorized {
            readingBedCoordinator.pause()
            prepareAppleMusicMixDefaultIfNeeded()
            guard readingBedEnabled else {
                audioCoordinator.configureAudioSessionForMixing(false)
                audioCoordinator.setTargetVolume(1.0)
                return
            }
            // Apple Music mode: stop built-in reading bed and let narration mix with it.
            configureAppleMusicAudioSession(for: musicVolume)
            applyMixVolume(musicVolume)
            if !musicCoordinator.isBackgroundMode {
                Task {
                    await musicCoordinator.ensureLastSelectionLoadedForReadingBed()
                    await musicCoordinator.activateAsReadingBed()
                }
            }
            return
        }
        // Built-in mode: ensure no mixing
        audioCoordinator.configureAudioSessionForMixing(false)
        if musicCoordinator.ownershipState != .narration {
            Task { await musicCoordinator.deactivateAsReadingBed() }
        }
        readingBedCoordinator.setLooping(true)
        applyMixVolume(musicVolume)
        updateReadingBedPlayback()
    }

    func handleNarrationPlaybackChange(isPlaying: Bool) {
        readingBedPauseTask?.cancel()
        readingBedPauseTask = nil

        // Route to appropriate handler based on music source
        if useAppleMusicForBed && musicCoordinator.isAuthorized {
            handleAppleMusicPlaybackChange(isPlaying: isPlaying)
        } else {
            handleBuiltInReadingBedPlaybackChange(isPlaying: isPlaying)
        }
    }

    // MARK: - Apple Music Playback Control

    private var shouldAutoResumeAppleMusicReadingBed: Bool {
        readingBedEnabled &&
        audioCoordinator.isPlaybackRequested &&
        !musicCoordinator.isPausedByReaderTransport &&
        !musicCoordinator.isReaderTransportPauseGuardActive &&
        musicCoordinator.canAutoResumeReadingBed
    }

    private var appleMusicDuckingMixThreshold: Double { 0.35 }

    private func shouldDuckAppleMusic(for mix: Double) -> Bool {
        useAppleMusicForBed && mix < appleMusicDuckingMixThreshold
    }

    private func configureAppleMusicAudioSession(for mix: Double) {
        audioCoordinator.configureAudioSessionForMixing(
            true,
            duckOthers: shouldDuckAppleMusic(for: mix)
        )
    }

    private func handleAppleMusicPlaybackChange(isPlaying: Bool) {
        guard readingBedEnabled else {
            musicCoordinator.pause(userInitiated: false)
            return
        }
        if musicCoordinator.isPausedByReaderTransport || musicCoordinator.isReaderTransportPauseGuardActive {
            if isPlaying {
                musicCoordinator.pauseReadingBedForReaderTransport()
            }
            return
        }
        if isPlaying || audioCoordinator.isPlaybackRequested {
            musicCoordinator.prepareForNarrationMix()
            if shouldAutoResumeAppleMusicReadingBed,
               musicCoordinator.settleAlreadyPlayingReadingBedForAutoResume(reason: "interactivePlaybackChangeAlreadyPlaying") {
                return
            }
            Task {
                await musicCoordinator.ensureLastSelectionLoadedForReadingBed()
                musicCoordinator.prepareForNarrationMix()
                if shouldAutoResumeAppleMusicReadingBed {
                    if musicCoordinator.settleAlreadyPlayingReadingBedForAutoResume(reason: "interactivePlaybackChangeTaskAlreadyPlaying") {
                        return
                    }
                    musicCoordinator.resume(userInitiated: false)
                }
            }
            return
        }
        if !audioCoordinator.isPlaybackRequested {
            musicCoordinator.pause(userInitiated: false)
            return
        }
        readingBedPauseTask = Task { @MainActor in
            try? await Task.sleep(nanoseconds: readingBedPauseDelayNanos)
            guard !Task.isCancelled else { return }
            if !audioCoordinator.isPlaybackRequested {
                musicCoordinator.pause(userInitiated: false)
            }
        }
    }

    // MARK: - Built-in Reading Bed Playback Control

    private func handleBuiltInReadingBedPlaybackChange(isPlaying: Bool) {
        if isPlaying {
            // Playback started/resumed - ensure reading bed is playing if enabled
            // Only call update if reading bed isn't already playing correctly
            if readingBedEnabled,
               let url = viewModel.readingBedURL,
               (!readingBedCoordinator.isPlaying || readingBedCoordinator.activeURL != url) {
                updateReadingBedPlayback()
            }
            return
        }
        // Playback stopped - check if this is a definitive pause or a brief transition
        if !audioCoordinator.isPlaybackRequested {
            // Definitive pause (user stopped playback) - pause reading bed immediately
            readingBedCoordinator.pause()
            return
        }
        // Playback requested but not currently playing = likely a transition between chunks
        // Let reading bed continue playing without interruption
        // Schedule a delayed check in case this is actually a stalled playback
        readingBedPauseTask = Task { @MainActor in
            try? await Task.sleep(nanoseconds: readingBedPauseDelayNanos)
            guard !Task.isCancelled else { return }
            // After delay, only pause if playback truly stopped (not requested anymore)
            if !audioCoordinator.isPlaybackRequested {
                readingBedCoordinator.pause()
            }
            // If isPlaybackRequested is still true, assume playback will resume
            // and let reading bed continue playing
        }
    }

    func updateReadingBedPlayback() {
        // If using Apple Music, don't control built-in reading bed
        guard !useAppleMusicForBed else { return }

        guard readingBedEnabled, let url = viewModel.readingBedURL else {
            readingBedCoordinator.pause()
            return
        }
        guard audioCoordinator.isPlaybackRequested else {
            readingBedCoordinator.pause()
            return
        }
        if readingBedCoordinator.activeURL == url && readingBedCoordinator.isPlaying {
            return
        }
        if readingBedCoordinator.activeURL != url || readingBedCoordinator.activeURL == nil {
            readingBedCoordinator.load(url: url, autoPlay: true)
        } else {
            readingBedCoordinator.play()
        }
    }

    // MARK: - Music Source Switching

    /// Switch to Apple Music as the reading bed source.
    func switchToAppleMusic() {
        readingBedCoordinator.pause()
        prepareAppleMusicMixDefaultIfNeeded()
        guard readingBedEnabled else {
            audioCoordinator.configureAudioSessionForMixing(false)
            audioCoordinator.setTargetVolume(1.0)
            return
        }
        configureAppleMusicAudioSession(for: musicVolume)
        applyMixVolume(musicVolume)
        // Resume Apple Music if playback is active unless the user paused it.
        Task {
            await musicCoordinator.ensureLastSelectionLoadedForReadingBed()
            musicCoordinator.prepareForNarrationMix()
            if shouldAutoResumeAppleMusicReadingBed {
                musicCoordinator.resume(userInitiated: false)
            }
            await musicCoordinator.activateAsReadingBed()
        }
    }

    /// Switch back to built-in reading bed.
    func switchToBuiltInBed() {
        Task {
            await musicCoordinator.deactivateAsReadingBed()
            audioCoordinator.configureAudioSessionForMixing(false)
            audioCoordinator.setTargetVolume(1.0)
            useAppleMusicForBed = false
            configureReadingBed()
        }
    }

    /// Called when music volume slider changes.
    func handleMusicVolumeChange(_ volume: Double) {
        applyMixVolume(volume)
    }

    /// Apple Music is system-owned audio; low mixes request ducking while higher mixes lower narration around it.
    func prepareAppleMusicMixDefaultIfNeeded() {
        guard !didInitializeAppleMusicMix else { return }
        didInitializeAppleMusicMix = true
        guard musicVolume <= MusicPreferences.defaultMusicVolume else { return }
        musicVolume = MusicPreferences.defaultAppleMusicMix
    }

    /// Apply unified volume mix. mix=0: full narration, no music. mix=1: max bed, reduced narration.
    /// Works identically for both Apple Music and built-in reading bed sources.
    func applyMixVolume(_ mix: Double) {
        // Narration: full at mix=0, reduced at mix=1 (min 0.3)
        let narrationVolume = 1.0 - (mix * 0.7)
        audioCoordinator.setTargetVolume(narrationVolume)

        if !useAppleMusicForBed {
            // Built-in bed: scale volume with gentle curve for natural feel
            let bedVolume = pow(mix, 1.5) * 0.3
            readingBedCoordinator.setVolume(bedVolume)
        } else {
            // Apple Music volume is not directly app-controlled; low mixes request system ducking.
            configureAppleMusicAudioSession(for: mix)
        }
    }

    /// Handle reading bed enable/disable toggle when Apple Music is active.
    func handleReadingBedToggleWithAppleMusic(enabled: Bool) {
        if enabled {
            // Only restart Apple Music from the toggle when narration is actively playing.
            if shouldAutoResumeAppleMusicReadingBed {
                Task {
                    await musicCoordinator.ensureLastSelectionLoadedForReadingBed()
                    musicCoordinator.resume(userInitiated: false)
                }
            }
        } else {
            musicCoordinator.pause()
        }
    }

    // MARK: - Music Pill (header shortcut)

    /// Pill button shown in the header next to search and bookmark pills.
    /// Tapping opens the music control popover.
    @ViewBuilder
    var musicPillView: some View {
        let isActive = readingBedEnabled && (useAppleMusicForBed ? musicCoordinator.isPlaying : true)
        let hasNowPlaying = useAppleMusicForBed && musicCoordinator.currentSongTitle != nil
        let pill = Button {
            showMusicOverlay.toggle()
        } label: {
            HStack(spacing: (isTV ? 6 : 4) * infoPillScale) {
                // Show cover art when Apple Music is active with artwork available
                if hasNowPlaying, let url = musicCoordinator.currentArtworkURL {
                    let artSize = (isPhone ? 18 : 22) * infoPillScale
                    AsyncImage(url: url) { image in
                        image.resizable().scaledToFill()
                    } placeholder: {
                        Image(systemName: "music.note")
                            .font(musicPillIconFont)
                    }
                    .frame(width: artSize, height: artSize)
                    .clipShape(RoundedRectangle(cornerRadius: 3 * infoPillScale))
                } else {
                    Image(systemName: "music.note")
                        .font(musicPillIconFont)
                }
                // Show now-playing text alongside cover art
                // iPhone portrait: use marquee (newsreel) effect for compact display
                // iPad, TV, iPhone landscape: static text
                if hasNowPlaying {
                    if isPhonePortrait {
                        // Compact marquee display: "Song - Artist"
                        let displayText = [musicCoordinator.currentSongTitle, musicCoordinator.currentArtist]
                            .compactMap { $0 }
                            .joined(separator: " — ")
                        MarqueeText(
                            text: displayText,
                            font: musicPillNowPlayingFont,
                            speed: 25,
                            gap: 24
                        )
                        .frame(maxWidth: 100 * infoPillScale)
                    } else {
                        VStack(alignment: .leading, spacing: 0) {
                            Text(musicCoordinator.currentSongTitle ?? "")
                                .font(musicPillNowPlayingFont)
                                .lineLimit(1)
                            if let artist = musicCoordinator.currentArtist {
                                Text(artist)
                                    .font(musicPillArtistFont)
                                    .foregroundStyle(Color.white.opacity(0.7))
                                    .lineLimit(1)
                            }
                        }
                    }
                }
            }
            .foregroundStyle(Color.white.opacity(isActive ? 1.0 : 0.85))
            .padding(.horizontal, (isTV ? 12 : 8) * infoPillScale)
            .padding(.vertical, (isTV ? 6 : 4) * infoPillScale)
            .background(PlayerHeaderPillBackground(isActive: isActive))
        }
        .buttonStyle(.plain)
        .accessibilityLabel(useAppleMusicForBed ? "Apple Music: \(musicCoordinator.currentSongTitle ?? "active")" : "Music")

        #if os(tvOS)
        pill
            .buttonStyle(TVMusicPillButtonStyle())
            .focused($focusedArea, equals: .controls)
            .sheet(isPresented: $showMusicOverlay) {
                musicControlOverlay
            }
        #elseif os(iOS)
        if isPhone {
            // iPhone: use sheet with detent for a clean bottom panel
            pill
                .sheet(isPresented: $showMusicOverlay) {
                    musicControlOverlay
                        .presentationDetents([.medium])
                        .presentationDragIndicator(.visible)
                }
        } else {
            // iPad: native popover below the pill
            pill
                .popover(isPresented: $showMusicOverlay, arrowEdge: .top) {
                    musicControlOverlay
                }
        }
        #else
        pill
        #endif
    }

    private var musicPillIconFont: Font {
        #if os(iOS) || os(tvOS)
        let style: UIFont.TextStyle = isTV ? .callout : .caption1
        let base = UIFont.preferredFont(forTextStyle: style).pointSize
        return .system(size: base * infoPillScale, weight: .semibold)
        #else
        return .system(size: 12 * infoPillScale, weight: .semibold)
        #endif
    }

    private var musicPillNowPlayingFont: Font {
        #if os(iOS) || os(tvOS)
        let style: UIFont.TextStyle = isTV ? .caption1 : .caption2
        let base = UIFont.preferredFont(forTextStyle: style).pointSize
        return .system(size: base * infoPillScale, weight: .medium)
        #else
        return .system(size: 10 * infoPillScale, weight: .medium)
        #endif
    }

    private var musicPillArtistFont: Font {
        #if os(iOS) || os(tvOS)
        let style: UIFont.TextStyle = isTV ? .caption2 : .caption2
        let base = UIFont.preferredFont(forTextStyle: style).pointSize
        return .system(size: (base - 1) * infoPillScale, weight: .regular)
        #else
        return .system(size: 9 * infoPillScale, weight: .regular)
        #endif
    }

    private var musicControlOverlay: some View {
        MusicControlOverlayView(
            readingBedEnabled: $readingBedEnabled,
            useAppleMusicForBed: $useAppleMusicForBed,
            musicVolume: $musicVolume,
            musicCoordinator: musicCoordinator,
            builtInBedLabel: selectedReadingBedLabel,
            onChangeSong: {
                showMusicOverlay = false
                showMusicPicker = true
            }
        )
    }

}
