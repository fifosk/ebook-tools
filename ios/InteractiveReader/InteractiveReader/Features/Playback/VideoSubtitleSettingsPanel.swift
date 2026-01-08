import SwiftUI
#if canImport(UIKit)
import UIKit
#endif

struct SubtitleSettingsPanel: View {
    let tracks: [VideoSubtitleTrack]
    @Binding var selectedTrack: VideoSubtitleTrack?
    @Binding var visibility: SubtitleVisibility
    let segmentOptions: [VideoSegmentOption]
    let selectedSegmentID: String?
    let onSelectSegment: ((String) -> Void)?
    let onClose: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            headerRow
            Divider()
                .overlay(Color.white.opacity(0.25))
            scrollableOptions
            Divider()
                .overlay(Color.white.opacity(0.25))
            lineVisibilityOptions
        }
        .padding(16)
        .frame(maxWidth: panelMaxWidth)
        .background(.black.opacity(0.85), in: RoundedRectangle(cornerRadius: 16))
        .foregroundStyle(.white)
    }

    private var headerRow: some View {
        HStack {
            Text("Subtitles")
                .font(.headline)
            Spacer()
            Button("Done") {
                onClose()
            }
            .font(.subheadline.weight(.semibold))
        }
    }

    private var scrollableOptions: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 12) {
                if segmentOptions.count > 1 {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Chunks")
                            .font(.caption)
                            .foregroundStyle(.white.opacity(0.7))
                        ForEach(segmentOptions) { segment in
                            Button {
                                onSelectSegment?(segment.id)
                            } label: {
                                trackRow(label: segment.label, selected: segment.id == selectedSegmentID)
                            }
                        }
                    }

                    Divider()
                        .overlay(Color.white.opacity(0.25))
                }

                VStack(alignment: .leading, spacing: 8) {
                    Text("Tracks")
                        .font(.caption)
                        .foregroundStyle(.white.opacity(0.7))
                    Button {
                        selectedTrack = nil
                    } label: {
                        trackRow(label: "Subtitles Off", selected: selectedTrack == nil)
                    }
                    if tracks.isEmpty {
                        Text("No subtitle tracks available.")
                            .font(.caption)
                            .foregroundStyle(.white.opacity(0.7))
                            .padding(.vertical, 4)
                    } else {
                        ForEach(tracks) { track in
                            Button {
                                selectedTrack = track
                            } label: {
                                let label = "\(track.label) (\(track.format.label))"
                                trackRow(label: label, selected: selectedTrack?.id == track.id)
                            }
                        }
                    }
                }
            }
        }
        .frame(maxHeight: panelScrollMaxHeight)
    }

    private var lineVisibilityOptions: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Lines")
                .font(.caption)
                .foregroundStyle(.white.opacity(0.7))
            Toggle("Original", isOn: $visibility.showOriginal)
            Toggle("Translation", isOn: $visibility.showTranslation)
            Toggle("Transliteration", isOn: $visibility.showTransliteration)
        }
        .disabled(selectedTrack == nil)
    }

    private func trackRow(label: String, selected: Bool) -> some View {
        HStack {
            Text(label)
                .lineLimit(1)
            Spacer()
            if selected {
                Image(systemName: "checkmark")
            }
        }
        .padding(.vertical, 4)
    }

    private var panelMaxWidth: CGFloat {
        #if os(tvOS)
        return 640
        #else
        return 480
        #endif
    }

    private var panelScrollMaxHeight: CGFloat {
        let screenHeight = UIScreen.main.bounds.height
        #if os(tvOS)
        return max(260, screenHeight * 0.45)
        #else
        return max(220, screenHeight * 0.35)
        #endif
    }
}
