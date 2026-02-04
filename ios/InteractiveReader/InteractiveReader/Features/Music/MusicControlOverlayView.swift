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
                        Button {
                            musicVolume = max(0, musicVolume - 0.1)
                        } label: {
                            Image(systemName: "speaker.wave.1")
                        }
                        Text("\(Int(musicVolume * 100))%")
                            .font(.body.monospacedDigit())
                            .frame(minWidth: 44)
                        Button {
                            musicVolume = min(1, musicVolume + 0.1)
                        } label: {
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
            Button { musicCoordinator.toggleShuffle() } label: {
                Image(systemName: "shuffle")
                    .font(.caption)
                    .foregroundStyle(musicCoordinator.shuffleMode == .songs ? Color.accentColor : .secondary)
            }
            .buttonStyle(.plain)
            .frame(maxWidth: .infinity)

            // Skip back
            Button { musicCoordinator.skipToPrevious() } label: {
                Image(systemName: "backward.fill")
                    .font(.subheadline)
            }
            .buttonStyle(.plain)
            .frame(maxWidth: .infinity)

            // Play/Pause
            Button {
                if musicCoordinator.isPlaying {
                    musicCoordinator.pause()
                } else {
                    musicCoordinator.resume()
                }
            } label: {
                Image(systemName: musicCoordinator.isPlaying ? "pause.fill" : "play.fill")
                    .font(.title3)
            }
            .buttonStyle(.plain)
            .frame(maxWidth: .infinity)

            // Skip forward
            Button { musicCoordinator.skipToNext() } label: {
                Image(systemName: "forward.fill")
                    .font(.subheadline)
            }
            .buttonStyle(.plain)
            .frame(maxWidth: .infinity)

            // Repeat
            Button { musicCoordinator.cycleRepeatMode() } label: {
                Image(systemName: repeatIconName)
                    .font(.caption)
                    .foregroundStyle(musicCoordinator.repeatMode != .off ? Color.accentColor : .secondary)
            }
            .buttonStyle(.plain)
            .frame(maxWidth: .infinity)
        }
        .padding(.vertical, 6)
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
                Button("Change") { onChangeSong() }
                    .font(.caption)
                    .buttonStyle(.bordered)
                    .controlSize(.mini)
            }
        } else {
            Button("Choose Music...") { onChangeSong() }
                .font(.subheadline)
        }
    }
}
