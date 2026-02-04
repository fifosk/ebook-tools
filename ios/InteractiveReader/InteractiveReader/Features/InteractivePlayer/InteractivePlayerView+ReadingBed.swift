import SwiftUI
#if os(iOS) || os(tvOS)
import UIKit
#endif

// MARK: - tvOS Button Style for Music Pill

#if os(tvOS)
struct TVMusicPillButtonStyle: ButtonStyle {
    @Environment(\.isFocused) var isFocused

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .scaleEffect(configuration.isPressed ? 0.95 : (isFocused ? 1.1 : 1.0))
            .brightness(isFocused ? 0.15 : 0)
            .animation(.easeInOut(duration: 0.15), value: isFocused)
            .animation(.easeInOut(duration: 0.1), value: configuration.isPressed)
    }
}
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
            // Apple Music mode: stop built-in reading bed, set mixing audio session
            readingBedCoordinator.pause()
            audioCoordinator.configureAudioSessionForMixing(true)
            applyMixVolume(musicVolume)
            if musicCoordinator.ownershipState != .appleMusic {
                Task { await musicCoordinator.activateAsReadingBed() }
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

    private func handleAppleMusicPlaybackChange(isPlaying: Bool) {
        if isPlaying {
            // Narration started - resume Apple Music if enabled and has a song queued
            if readingBedEnabled && musicCoordinator.currentSongTitle != nil {
                musicCoordinator.resume()
            }
            return
        }
        // Narration paused or stopped.
        // Unlike built-in reading bed, Apple Music continues as ambient background.
        // It only stops when user explicitly disables it or leaves the player.
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
        audioCoordinator.configureAudioSessionForMixing(true)
        applyMixVolume(musicVolume)
        // Resume Apple Music if playback is active and a song is queued
        if audioCoordinator.isPlaybackRequested && readingBedEnabled && musicCoordinator.currentSongTitle != nil {
            musicCoordinator.resume()
        }
        Task { await musicCoordinator.activateAsReadingBed() }
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

    /// Apply unified volume mix. mix=0: full narration, no music. mix=1: max music, reduced narration.
    /// Works identically for both Apple Music and built-in reading bed sources.
    func applyMixVolume(_ mix: Double) {
        // Narration: full at mix=0, reduced at mix=1 (min 0.3)
        let narrationVolume = 1.0 - (mix * 0.7)
        audioCoordinator.setTargetVolume(narrationVolume)

        if !useAppleMusicForBed {
            // Built-in bed: scale volume with gentle curve for natural feel
            let bedVolume = pow(mix, 1.5) * 0.3
            readingBedCoordinator.setVolume(bedVolume)
        }
        // Apple Music: uses system volume, narration reduction handles the mix
    }

    /// Handle reading bed enable/disable toggle when Apple Music is active.
    func handleReadingBedToggleWithAppleMusic(enabled: Bool) {
        if enabled {
            // Resume Apple Music if there's a song in the queue
            if musicCoordinator.currentSongTitle != nil {
                musicCoordinator.resume()
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
        let pill = Button {
            showMusicOverlay.toggle()
        } label: {
            Image(systemName: "music.note")
                .font(musicPillIconFont)
                .foregroundStyle(Color.white.opacity(isActive ? 1.0 : 0.85))
                .padding(.horizontal, (isTV ? 12 : 8) * infoPillScale)
                .padding(.vertical, (isTV ? 6 : 4) * infoPillScale)
                .background(
                    Capsule()
                        .fill(Color.black.opacity(isActive ? 0.7 : 0.55))
                        .overlay(
                            Capsule().stroke(Color.white.opacity(isActive ? 0.35 : 0.22), lineWidth: 1)
                        )
                )
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
