import SwiftUI

struct VideoPlayerSpeedMenu: View {
    let playbackRate: Double
    let playbackRateOptions: [Double]
    let onPlaybackRateChange: (Double) -> Void
    let onUserInteraction: () -> Void

    #if os(tvOS)
    let isFocused: Bool
    let isDisabled: Bool
    #endif

    var body: some View {
        Menu {
            ForEach(playbackRateOptions, id: \.self) { rate in
                Button {
                    onPlaybackRateChange(rate)
                    onUserInteraction()
                } label: {
                    if isCurrentRate(rate) {
                        Label(rateLabel(rate), systemImage: "checkmark")
                    } else {
                        Text(rateLabel(rate))
                    }
                }
            }
        } label: {
            menuLabel
        }
        #if os(tvOS)
        .disabled(isDisabled)
        #endif
    }

    private var menuLabel: some View {
        #if os(tvOS)
        VideoPlayerControlLabel(
            systemName: "speedometer",
            label: "Speed",
            font: .callout.weight(.semibold),
            isFocused: isFocused
        )
        #else
        Label("Speed", systemImage: "speedometer")
            .labelStyle(.titleAndIcon)
            .font(.caption)
            .lineLimit(1)
            .truncationMode(.tail)
            .padding(.horizontal, 10)
            .padding(.vertical, 6)
            .background(.black.opacity(0.45), in: RoundedRectangle(cornerRadius: 8))
            .foregroundStyle(.white)
        #endif
    }

    private func rateLabel(_ rate: Double) -> String {
        let percent = (rate * 100).rounded()
        return "\(Int(percent))%"
    }

    private func isCurrentRate(_ rate: Double) -> Bool {
        abs(rate - playbackRate) < 0.01
    }
}
