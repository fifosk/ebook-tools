import SwiftUI
#if os(iOS)
import UIKit
#endif

/// Compact overlay for controlling background music settings.
/// Displayed as a popover on iOS or sheet on tvOS, anchored to the music pill.
struct MusicControlOverlayView: View {
    @Binding var readingBedEnabled: Bool
    @Binding var useAppleMusicForBed: Bool
    @Binding var musicVolume: Double
    @ObservedObject var musicCoordinator: MusicKitCoordinator
    let builtInBedLabel: String
    let onChangeSong: () -> Void

    /// Local state for scrubbing timeline without affecting playback until release.
    @State private var isScrubbing = false
    @State private var scrubTime: TimeInterval = 0

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            // On/Off toggle
            Toggle("Background Music", isOn: $readingBedEnabled)
                .font(.subheadline.weight(.medium))

            if readingBedEnabled {
                Divider()

                // Source picker
                Picker("Source", selection: $useAppleMusicForBed) {
                    Text("Reading Bed").tag(false)
                    Text("Apple Music").tag(true)
                }
                .pickerStyle(.segmented)

                // Apple Music now-playing info
                if useAppleMusicForBed {
                    appleMusicInfo
                    transportControls
                    playbackTimeline
                } else {
                    Text(builtInBedLabel)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }

                Divider()

                // Volume mix slider
                #if os(iOS)
                VStack(alignment: .leading, spacing: 6) {
                    HStack {
                        Text("Mix")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                        Spacer()
                        Text("\(Int(musicVolume * 100))%")
                            .font(.caption.monospacedDigit())
                            .foregroundStyle(.secondary)
                    }
                    HStack(spacing: 10) {
                        Image(systemName: "waveform")
                            .font(.caption2)
                            .foregroundStyle(.secondary)
                        Slider(value: $musicVolume, in: 0...1)
                            .tint(.accentColor)
                        Image(systemName: "music.note")
                            .font(.caption2)
                            .foregroundStyle(.secondary)
                    }
                }
                #else
                // tvOS: Slider unavailable, use +/- buttons
                VStack(alignment: .leading, spacing: 4) {
                    Text("Mix")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    HStack(spacing: 16) {
                        Button(action: decreaseMusicVolume) {
                            Image(systemName: "speaker.wave.1")
                        }
                        Text("\(Int(musicVolume * 100))%")
                            .font(.body.monospacedDigit())
                            .frame(minWidth: 44)
                        Button(action: increaseMusicVolume) {
                            Image(systemName: "speaker.wave.3")
                        }
                    }
                }
                #endif
            }
        }
        .padding(16)
        #if os(iOS)
        .frame(width: isPad ? 340 : nil)
        // Ensure good visibility in both light and dark modes
        .background {
            RoundedRectangle(cornerRadius: 16)
                .fill(.regularMaterial)
        }
        .foregroundStyle(.primary)
        #endif
    }

    private var isPad: Bool {
        #if os(iOS)
        UIDevice.current.userInterfaceIdiom == .pad
        #else
        false
        #endif
    }

    @ViewBuilder
    private var transportControls: some View {
        HStack(spacing: 0) {
            // Shuffle
            Button(action: toggleShuffle) {
                Image(systemName: "shuffle")
                    .font(.caption)
                    .foregroundStyle(musicCoordinator.shuffleMode == .songs ? Color.accentColor : .secondary)
            }
            .buttonStyle(.plain)
            .frame(maxWidth: .infinity)

            // Skip back
            Button(action: skipToPrevious) {
                Image(systemName: "backward.fill")
                    .font(.subheadline)
            }
            .buttonStyle(.plain)
            .frame(maxWidth: .infinity)

            // Play/Pause
            Button(action: togglePlayback) {
                Image(systemName: musicCoordinator.isPlaying ? "pause.fill" : "play.fill")
                    .font(.title3)
            }
            .buttonStyle(.plain)
            .frame(maxWidth: .infinity)

            // Skip forward
            Button(action: skipToNext) {
                Image(systemName: "forward.fill")
                    .font(.subheadline)
            }
            .buttonStyle(.plain)
            .frame(maxWidth: .infinity)

            // Repeat
            Button(action: cycleRepeatMode) {
                Image(systemName: repeatIconName)
                    .font(.caption)
                    .foregroundStyle(musicCoordinator.repeatMode != .off ? Color.accentColor : .secondary)
            }
            .buttonStyle(.plain)
            .frame(maxWidth: .infinity)
        }
        .padding(.vertical, 6)
    }

    @ViewBuilder
    private var playbackTimeline: some View {
        let duration = musicCoordinator.playbackDuration
        let currentTime = isScrubbing ? scrubTime : musicCoordinator.playbackTime
        let hasValidDuration = duration > 0

        if hasValidDuration {
            VStack(spacing: 4) {
                #if os(iOS)
                Slider(
                    value: Binding(
                        get: { isScrubbing ? scrubTime : musicCoordinator.playbackTime },
                        set: updateScrubTime
                    ),
                    in: 0...duration,
                    onEditingChanged: handleScrubEditingChanged
                )
                .tint(.accentColor)
                #else
                // tvOS: progress bar with skip buttons
                HStack(spacing: 12) {
                    Button(action: seekBackward) {
                        Image(systemName: "gobackward.15")
                            .font(.caption)
                    }
                    .buttonStyle(.plain)

                    GeometryReader { geometry in
                        ZStack(alignment: .leading) {
                            Capsule()
                                .fill(Color.secondary.opacity(0.3))
                                .frame(height: 4)
                            Capsule()
                                .fill(Color.accentColor)
                                .frame(width: geometry.size.width * (currentTime / duration), height: 4)
                        }
                    }
                    .frame(height: 4)

                    Button(action: seekForward) {
                        Image(systemName: "goforward.15")
                            .font(.caption)
                    }
                    .buttonStyle(.plain)
                }
                #endif

                // Time labels
                HStack {
                    Text(formatTime(currentTime))
                        .font(.caption2.monospacedDigit())
                        .foregroundStyle(.secondary)
                    Spacer()
                    Text("-\(formatTime(duration - currentTime))")
                        .font(.caption2.monospacedDigit())
                        .foregroundStyle(.secondary)
                }
            }
        }
    }

    private func formatTime(_ time: TimeInterval) -> String {
        let totalSeconds = Int(time)
        let minutes = totalSeconds / 60
        let seconds = totalSeconds % 60
        return String(format: "%d:%02d", minutes, seconds)
    }

    private var repeatIconName: String {
        switch musicCoordinator.repeatMode {
        case .one: return "repeat.1"
        case .all, .off: return "repeat"
        }
    }

    @ViewBuilder
    private var appleMusicInfo: some View {
        if let title = musicCoordinator.currentSongTitle {
            HStack(spacing: 8) {
                if let url = musicCoordinator.currentArtworkURL {
                    AsyncImage(url: url) { phase in
                        if let image = phase.image {
                            image.resizable().scaledToFill()
                        } else {
                            Color.gray.opacity(0.3)
                        }
                    }
                    .frame(width: 36, height: 36)
                    .clipShape(RoundedRectangle(cornerRadius: 6))
                }
                VStack(alignment: .leading, spacing: 1) {
                    Text(title)
                        .font(.caption)
                        .lineLimit(1)
                    if let artist = musicCoordinator.currentArtist {
                        Text(artist)
                            .font(.caption2)
                            .foregroundStyle(.secondary)
                            .lineLimit(1)
                    }
                }
                Spacer()
                Button("Change", action: changeSong)
                    .font(.caption)
                    .buttonStyle(.bordered)
                    .controlSize(.mini)
            }
        } else {
            Button("Choose Music...", action: changeSong)
                .font(.subheadline)
        }
    }

    private func decreaseMusicVolume() {
        musicVolume = max(0, musicVolume - 0.1)
    }

    private func increaseMusicVolume() {
        musicVolume = min(1, musicVolume + 0.1)
    }

    private func toggleShuffle() {
        musicCoordinator.toggleShuffle()
    }

    private func skipToPrevious() {
        musicCoordinator.skipToPrevious()
    }

    private func togglePlayback() {
        if musicCoordinator.isPlaying {
            musicCoordinator.pause()
        } else {
            musicCoordinator.resume()
        }
    }

    private func skipToNext() {
        musicCoordinator.skipToNext()
    }

    private func cycleRepeatMode() {
        musicCoordinator.cycleRepeatMode()
    }

    private func updateScrubTime(_ newValue: TimeInterval) {
        scrubTime = newValue
        if !isScrubbing {
            isScrubbing = true
        }
    }

    private func handleScrubEditingChanged(_ editing: Bool) {
        guard !editing else { return }
        musicCoordinator.seek(to: scrubTime)
        isScrubbing = false
    }

    private func seekBackward() {
        let newTime = max(0, musicCoordinator.playbackTime - 15)
        musicCoordinator.seek(to: newTime)
    }

    private func seekForward() {
        let duration = musicCoordinator.playbackDuration
        let newTime = min(duration, musicCoordinator.playbackTime + 15)
        musicCoordinator.seek(to: newTime)
    }

    private func changeSong() {
        onChangeSong()
    }
}
