import SwiftUI

struct PlayerProgressFooterView: View {
    enum Style {
        case sentence
        case time
    }

    let style: Style
    let leadingLabel: String
    let trailingLabel: String?
    let accessibilityLabel: String
    let accessibilityValue: String
    @Binding var value: Double
    let range: ClosedRange<Double>
    let step: Double?
    let onEditingChanged: (Bool) -> Void

    var body: some View {
        VStack(spacing: 5) {
            HStack(spacing: 10) {
                Image(systemName: iconName)
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(Color.white.opacity(0.82))
                Text(leadingLabel)
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(Color.white.opacity(0.84))
                    .lineLimit(1)
                    .minimumScaleFactor(0.78)
                Spacer(minLength: 8)
                if let trailingLabel {
                    Text(trailingLabel)
                        .font(.caption.monospacedDigit().weight(.medium))
                        .foregroundStyle(Color.white.opacity(0.62))
                        .lineLimit(1)
                        .minimumScaleFactor(0.78)
                }
            }
            slider
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 9)
        .background(
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .fill(Color.black.opacity(0.68))
                .overlay(
                    RoundedRectangle(cornerRadius: 8, style: .continuous)
                        .stroke(Color.white.opacity(0.16), lineWidth: 1)
                )
        )
        .accessibilityElement(children: .combine)
        .accessibilityLabel(accessibilityLabel)
        .accessibilityValue(accessibilityValue)
        .accessibilityIdentifier(accessibilityIdentifier)
    }

    @ViewBuilder
    private var slider: some View {
        #if os(tvOS)
        TVScrubber(
            value: $value,
            range: range,
            isFocusable: true,
            onEditingChanged: onEditingChanged,
            onCommit: { _ in },
            onUserInteraction: {}
        )
        #else
        if let step {
            Slider(value: $value, in: range, step: step, onEditingChanged: onEditingChanged)
                .tint(tint)
        } else {
            Slider(value: $value, in: range, onEditingChanged: onEditingChanged)
                .tint(tint)
        }
        #endif
    }

    private var iconName: String {
        switch style {
        case .sentence:
            return "text.line.first.and.arrowtriangle.forward"
        case .time:
            return "playhead.forward"
        }
    }

    private var tint: Color {
        switch style {
        case .sentence:
            return Color.orange.opacity(0.92)
        case .time:
            return Color.white.opacity(0.92)
        }
    }

    private var accessibilityIdentifier: String {
        switch style {
        case .sentence:
            return "interactiveReaderProgressFooter"
        case .time:
            return "videoPlayerProgressFooter"
        }
    }
}
