import SwiftUI

// MARK: - Platform Colors
public enum PlatformColors {
    public static var secondaryBackground: Color {
        #if os(iOS)
        return Color(uiColor: .secondarySystemBackground)
        #elseif os(macOS)
        return Color(nsColor: .windowBackgroundColor)
        #elseif os(tvOS)
        // tvOS doesn't expose secondarySystemBackground; choose a neutral fallback
        return Color.black.opacity(0.2)
        #else
        return Color.secondary.opacity(0.2)
        #endif
    }
}

// MARK: - Platform Slider
// A slider-like control that compiles on tvOS. On tvOS, uses Stepper as a fallback.
public struct PlatformSlider<Value: BinaryFloatingPoint>: View where Value.Stride: BinaryFloatingPoint {
    @Binding private var value: Value
    private let range: ClosedRange<Value>
    private let step: Value
    private let label: String?

    public init(_ label: String? = nil, value: Binding<Value>, in range: ClosedRange<Value>, step: Value = 1) {
        self._value = value
        self.range = range
        self.step = step
        self.label = label
    }

    public var body: some View {
        #if os(tvOS)
        VStack(alignment: .leading, spacing: 8) {
            if let label {
                Text(label)
                    .font(.headline)
            }
            HStack(spacing: 12) {
                Text("\(range.lowerBound, specifier: \"%.0f\")")
                    .monospacedDigit()
                Stepper(value: $value, in: range, step: step) {
                    Text("\(value, specifier: \"%.0f\")")
                        .monospacedDigit()
                }
                Text("\(range.upperBound, specifier: \"%.0f\")")
                    .monospacedDigit()
            }
        }
        .padding(12)
        .background(PlatformColors.secondaryBackground)
        .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
        #else
        VStack(alignment: .leading, spacing: 8) {
            if let label {
                Text(label)
                    .font(.headline)
            }
            Slider(value: $value, in: range, step: step)
        }
        #endif
    }
}

// MARK: - Platform GroupBox
// A GroupBox-like wrapper that compiles on tvOS by using a styled container.
public struct PlatformGroupBox<Label: View, Content: View>: View {
    private let label: () -> Label
    private let content: () -> Content

    public init(@ViewBuilder label: @escaping () -> Label, @ViewBuilder content: @escaping () -> Content) {
        self.label = label
        self.content = content
    }

    public var body: some View {
        #if os(tvOS)
        VStack(alignment: .leading, spacing: 8) {
            label()
                .font(.headline)
            content()
        }
        .padding(12)
        .background(PlatformColors.secondaryBackground)
        .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
        #else
        GroupBox(label: label(), content: content)
        #endif
    }
}

// MARK: - Picker Style Helper
public enum PlatformPickerStyle {
    @ViewBuilder
    public static func applyWheelStyleIfAvailable<Content: View>(_ content: Content) -> some View {
        #if os(tvOS)
        // tvOS doesn't support wheel style; return as-is
        content
        #else
        content.pickerStyle(.wheel)
        #endif
    }
}
