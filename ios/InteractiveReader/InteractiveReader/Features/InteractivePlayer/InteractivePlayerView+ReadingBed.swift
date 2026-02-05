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

    // MARK: - Speed Pill (header shortcut)

    /// Pill button showing current narration speed. Tapping opens speed control.
    @ViewBuilder
    var speedPillView: some View {
        let currentRate = audioCoordinator.playbackRate
        let isNonDefault = abs(currentRate - 1.0) > 0.01
        let pill = Button {
            showSpeedOverlay.toggle()
        } label: {
            HStack(spacing: 4 * infoPillScale) {
                Image(systemName: "gauge.with.needle")
                    .font(speedPillIconFont)
                Text(playbackRateLabel(currentRate))
                    .font(speedPillLabelFont)
            }
            .foregroundStyle(Color.white.opacity(isNonDefault ? 1.0 : 0.85))
            .padding(.horizontal, (isTV ? 12 : 8) * infoPillScale)
            .padding(.vertical, (isTV ? 6 : 4) * infoPillScale)
            .background(
                Capsule()
                    .fill(Color.black.opacity(isNonDefault ? 0.7 : 0.55))
                    .overlay(
                        Capsule().stroke(Color.white.opacity(isNonDefault ? 0.35 : 0.22), lineWidth: 1)
                    )
            )
        }
        .buttonStyle(.plain)
        .accessibilityLabel("Narration speed: \(playbackRateLabel(currentRate))")

        #if os(tvOS)
        pill
            .buttonStyle(TVMusicPillButtonStyle())
            .focused($focusedArea, equals: .controls)
            .sheet(isPresented: $showSpeedOverlay) {
                speedControlOverlay
            }
        #elseif os(iOS)
        if isPhone {
            // iPhone: use sheet with small detent
            pill
                .sheet(isPresented: $showSpeedOverlay) {
                    speedControlOverlay
                        .presentationDetents([.height(280)])
                        .presentationDragIndicator(.visible)
                }
        } else {
            // iPad: native popover below the pill
            pill
                .popover(isPresented: $showSpeedOverlay, arrowEdge: .top) {
                    speedControlOverlay
                }
        }
        #else
        pill
        #endif
    }

    private var speedPillIconFont: Font {
        #if os(iOS) || os(tvOS)
        let style: UIFont.TextStyle = isTV ? .callout : .caption1
        let base = UIFont.preferredFont(forTextStyle: style).pointSize
        return .system(size: base * infoPillScale, weight: .semibold)
        #else
        return .system(size: 12 * infoPillScale, weight: .semibold)
        #endif
    }

    private var speedPillLabelFont: Font {
        #if os(iOS) || os(tvOS)
        let style: UIFont.TextStyle = isTV ? .caption1 : .caption2
        let base = UIFont.preferredFont(forTextStyle: style).pointSize
        return .system(size: base * infoPillScale, weight: .medium)
        #else
        return .system(size: 10 * infoPillScale, weight: .medium)
        #endif
    }

    private var speedControlOverlay: some View {
        SpeedControlOverlayView(
            currentRate: audioCoordinator.playbackRate,
            rates: playbackRates,
            onSelectRate: { rate in
                audioCoordinator.setPlaybackRate(rate)
            },
            rateLabel: playbackRateLabel
        )
    }
}

// MARK: - Speed Control Overlay View

/// Compact overlay for controlling narration playback speed.
struct SpeedControlOverlayView: View {
    let currentRate: Double
    let rates: [Double]
    let onSelectRate: (Double) -> Void
    let rateLabel: (Double) -> String

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Narration Speed")
                .font(.subheadline.weight(.medium))

            #if os(iOS)
            // iOS: Slider with discrete steps
            VStack(spacing: 8) {
                HStack {
                    Text("Slower")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                    Spacer()
                    Text(rateLabel(currentRate))
                        .font(.body.weight(.semibold).monospacedDigit())
                    Spacer()
                    Text("Faster")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }

                Slider(
                    value: Binding(
                        get: { currentRate },
                        set: { newValue in
                            // Snap to nearest rate in the array
                            if let closest = rates.min(by: { abs($0 - newValue) < abs($1 - newValue) }) {
                                onSelectRate(closest)
                            }
                        }
                    ),
                    in: (rates.first ?? 0.5)...(rates.last ?? 1.5),
                    step: 0.1
                )
                .tint(.accentColor)

                // Quick presets row
                HStack(spacing: 8) {
                    ForEach([0.5, 0.8, 1.0, 1.2, 1.5], id: \.self) { rate in
                        Button {
                            onSelectRate(rate)
                        } label: {
                            Text(rateLabel(rate))
                                .font(.caption2.weight(isCurrentRate(rate) ? .bold : .regular))
                                .padding(.horizontal, 8)
                                .padding(.vertical, 4)
                                .background(
                                    Capsule()
                                        .fill(isCurrentRate(rate) ? Color.accentColor : Color.secondary.opacity(0.2))
                                )
                                .foregroundStyle(isCurrentRate(rate) ? .white : .primary)
                        }
                        .buttonStyle(.plain)
                    }
                }
            }
            #else
            // tvOS: Button grid for speed selection
            LazyVGrid(columns: [
                GridItem(.flexible()),
                GridItem(.flexible()),
                GridItem(.flexible())
            ], spacing: 12) {
                ForEach(rates, id: \.self) { rate in
                    Button {
                        onSelectRate(rate)
                    } label: {
                        Text(rateLabel(rate))
                            .font(.body.weight(isCurrentRate(rate) ? .bold : .regular))
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 10)
                            .background(
                                RoundedRectangle(cornerRadius: 8)
                                    .fill(isCurrentRate(rate) ? Color.accentColor : Color.secondary.opacity(0.2))
                            )
                            .foregroundStyle(isCurrentRate(rate) ? .white : .primary)
                    }
                    .buttonStyle(.plain)
                }
            }
            #endif
        }
        .padding(16)
        #if os(iOS)
        .frame(width: isPad ? 300 : nil)
        .background {
            RoundedRectangle(cornerRadius: 16)
                .fill(.regularMaterial)
        }
        .foregroundStyle(.primary)
        #endif
    }

    private func isCurrentRate(_ rate: Double) -> Bool {
        abs(rate - currentRate) < 0.01
    }

    private var isPad: Bool { PlatformAdapter.isPad }
}

// MARK: - Jump Pill Extension

extension InteractivePlayerView {
    // MARK: - Jump Pill (header shortcut)

    /// Pill button showing current sentence. Tapping opens jump-to navigation.
    @ViewBuilder
    var jumpPillView: some View {
        let currentSentence = selectedSentenceID ?? 1
        let pill = Button {
            showJumpOverlay.toggle()
        } label: {
            HStack(spacing: 4 * infoPillScale) {
                Image(systemName: "arrow.right.to.line")
                    .font(jumpPillIconFont)
                Text("#\(currentSentence)")
                    .font(jumpPillLabelFont)
            }
            .foregroundStyle(Color.white.opacity(0.85))
            .padding(.horizontal, (isTV ? 12 : 8) * infoPillScale)
            .padding(.vertical, (isTV ? 6 : 4) * infoPillScale)
            .background(
                Capsule()
                    .fill(Color.black.opacity(0.55))
                    .overlay(
                        Capsule().stroke(Color.white.opacity(0.22), lineWidth: 1)
                    )
            )
        }
        .buttonStyle(.plain)
        .accessibilityLabel("Jump to sentence \(currentSentence)")

        #if os(tvOS)
        pill
            .buttonStyle(TVMusicPillButtonStyle())
            .focused($focusedArea, equals: .controls)
            .sheet(isPresented: $showJumpOverlay) {
                jumpControlOverlay
            }
        #elseif os(iOS)
        if isPhone {
            // iPhone: use sheet with medium detent
            pill
                .sheet(isPresented: $showJumpOverlay) {
                    jumpControlOverlay
                        .presentationDetents([.medium])
                        .presentationDragIndicator(.visible)
                }
        } else {
            // iPad: native popover below the pill
            pill
                .popover(isPresented: $showJumpOverlay, arrowEdge: .top) {
                    jumpControlOverlay
                }
        }
        #else
        pill
        #endif
    }

    private var jumpPillIconFont: Font {
        #if os(iOS) || os(tvOS)
        let style: UIFont.TextStyle = isTV ? .callout : .caption1
        let base = UIFont.preferredFont(forTextStyle: style).pointSize
        return .system(size: base * infoPillScale, weight: .semibold)
        #else
        return .system(size: 12 * infoPillScale, weight: .semibold)
        #endif
    }

    private var jumpPillLabelFont: Font {
        #if os(iOS) || os(tvOS)
        let style: UIFont.TextStyle = isTV ? .caption1 : .caption2
        let base = UIFont.preferredFont(forTextStyle: style).pointSize
        return .system(size: base * infoPillScale, weight: .medium)
        #else
        return .system(size: 10 * infoPillScale, weight: .medium)
        #endif
    }

    private var jumpControlOverlay: some View {
        JumpControlOverlayView(
            chapters: scopedChapterEntries,
            currentSentence: selectedSentenceID ?? 1,
            sentenceBounds: jobSentenceBounds,
            chapterLabel: chapterLabel,
            onJumpToSentence: { sentence in
                viewModel.jumpToSentence(sentence, autoPlay: audioCoordinator.isPlaybackRequested)
                showJumpOverlay = false
            },
            onJumpToChapter: { chapter in
                selectedSentenceID = chapter.startSentence
                viewModel.jumpToSentence(chapter.startSentence, autoPlay: audioCoordinator.isPlaybackRequested)
                showJumpOverlay = false
            }
        )
    }
}

// MARK: - Jump Control Overlay View

/// Compact overlay for jumping to a specific chapter or sentence.
struct JumpControlOverlayView: View {
    let chapters: [ChapterNavigationEntry]
    let currentSentence: Int
    let sentenceBounds: (start: Int?, end: Int?)
    let chapterLabel: (ChapterNavigationEntry, Int) -> String
    let onJumpToSentence: (Int) -> Void
    let onJumpToChapter: (ChapterNavigationEntry) -> Void

    @State private var inputSentence: String = ""
    @FocusState private var isInputFocused: Bool

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("Jump To")
                .font(.subheadline.weight(.medium))

            // Sentence number input
            VStack(alignment: .leading, spacing: 8) {
                Text("Sentence")
                    .font(.caption)
                    .foregroundStyle(.secondary)

                HStack(spacing: 12) {
                    #if os(iOS)
                    TextField("Enter #", text: $inputSentence)
                        .keyboardType(.numberPad)
                        .textFieldStyle(.roundedBorder)
                        .frame(width: 100)
                        .focused($isInputFocused)
                        .onSubmit {
                            if let num = Int(inputSentence), num > 0 {
                                onJumpToSentence(num)
                            }
                        }
                    #else
                    TextField("Enter #", text: $inputSentence)
                        .frame(width: 100)
                    #endif

                    Button("Go") {
                        if let num = Int(inputSentence), num > 0 {
                            onJumpToSentence(num)
                        }
                    }
                    .buttonStyle(.borderedProminent)
                    .disabled(Int(inputSentence) == nil || Int(inputSentence)! <= 0)

                    Spacer()

                    if let start = sentenceBounds.start, let end = sentenceBounds.end {
                        Text("\(start)–\(end)")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }
            }

            // Chapter picker (if chapters exist)
            if !chapters.isEmpty {
                Divider()

                VStack(alignment: .leading, spacing: 8) {
                    Text("Chapter")
                        .font(.caption)
                        .foregroundStyle(.secondary)

                    #if os(iOS)
                    ScrollView {
                        LazyVStack(alignment: .leading, spacing: 4) {
                            ForEach(Array(chapters.enumerated()), id: \.element.id) { index, chapter in
                                chapterButton(chapter: chapter, index: index)
                            }
                        }
                    }
                    .frame(maxHeight: 200)
                    #else
                    // tvOS: Vertical list with focus
                    LazyVStack(alignment: .leading, spacing: 8) {
                        ForEach(Array(chapters.enumerated()), id: \.element.id) { index, chapter in
                            chapterButton(chapter: chapter, index: index)
                        }
                    }
                    #endif
                }
            }
        }
        .padding(16)
        .onAppear {
            inputSentence = "\(currentSentence)"
        }
        #if os(iOS)
        .frame(width: isPad ? 340 : nil)
        .background {
            RoundedRectangle(cornerRadius: 16)
                .fill(.regularMaterial)
        }
        .foregroundStyle(.primary)
        #endif
    }

    @ViewBuilder
    private func chapterButton(chapter: ChapterNavigationEntry, index: Int) -> some View {
        let isActive = currentSentence >= chapter.startSentence &&
            (chapter.endSentence == nil || currentSentence <= chapter.endSentence!)

        Button {
            onJumpToChapter(chapter)
        } label: {
            HStack {
                Text(chapterLabel(chapter, index))
                    .font(.subheadline)
                    .lineLimit(2)
                    .multilineTextAlignment(.leading)
                Spacer()
                if isActive {
                    Image(systemName: "checkmark")
                        .font(.caption)
                        .foregroundStyle(Color.accentColor)
                }
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 8)
            .background(
                RoundedRectangle(cornerRadius: 8)
                    .fill(isActive ? Color.accentColor.opacity(0.15) : Color.secondary.opacity(0.1))
            )
        }
        .buttonStyle(.plain)
    }

    private var isPad: Bool { PlatformAdapter.isPad }
}
