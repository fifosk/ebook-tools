import SwiftUI

// MARK: - Platform Slider

/// A slider-like control that compiles on tvOS using Stepper as fallback
struct PlatformSlider<Value: BinaryFloatingPoint>: View where Value.Stride: BinaryFloatingPoint {
    @Binding private var value: Value
    private let range: ClosedRange<Value>
    private let step: Value.Stride
    private let label: String?

    init(_ label: String? = nil, value: Binding<Value>, in range: ClosedRange<Value>, step: Value.Stride = 1) {
        self._value = value
        self.range = range
        self.step = step
        self.label = label
    }

    private func formatValue(_ v: Value) -> String {
        String(format: "%.0f", Double(v))
    }

    var body: some View {
        #if os(tvOS)
        VStack(alignment: .leading, spacing: 8) {
            if let label {
                Text(label)
                    .font(.headline)
            }
            HStack(spacing: 16) {
                Button {
                    let newValue = value - Value(step)
                    if newValue >= range.lowerBound {
                        value = newValue
                    }
                } label: {
                    Image(systemName: "minus.circle.fill")
                        .font(.title2)
                }
                .disabled(value <= range.lowerBound)

                Text(formatValue(value))
                    .font(.title3)
                    .monospacedDigit()
                    .frame(minWidth: 60)

                Button {
                    let newValue = value + Value(step)
                    if newValue <= range.upperBound {
                        value = newValue
                    }
                } label: {
                    Image(systemName: "plus.circle.fill")
                        .font(.title2)
                }
                .disabled(value >= range.upperBound)
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

// MARK: - Picker Style Helper

enum PlatformPickerStyle {
    @ViewBuilder
    static func applyWheelStyleIfAvailable<Content: View>(_ content: Content) -> some View {
        #if os(tvOS)
        content
        #else
        content.pickerStyle(.wheel)
        #endif
    }
}

// MARK: - Platform Button Style

/// Adaptive button style for playback controls
struct PlatformPlaybackButtonStyle: ButtonStyle {
    let size: CGFloat
    let isHighlighted: Bool

    init(size: CGFloat = PlatformMetrics.playbackButtonSize, isHighlighted: Bool = false) {
        self.size = size
        self.isHighlighted = isHighlighted
    }

    func makeBody(configuration: Configuration) -> some View {
        #if os(tvOS)
        configuration.label
            .frame(width: size, height: size)
            .foregroundStyle(isHighlighted ? .primary : .secondary)
        #else
        configuration.label
            .frame(width: size, height: size)
            .background(
                Circle()
                    .fill(.thinMaterial)
                    .opacity(configuration.isPressed ? 0.8 : 1.0)
            )
            .foregroundStyle(isHighlighted ? .primary : .secondary)
        #endif
    }
}

// MARK: - Focus Support

/// View modifier for conditional focus management
struct PlatformFocusModifier: ViewModifier {
    let shouldFocus: Bool

    func body(content: Content) -> some View {
        #if os(tvOS)
        content
            .focusable(shouldFocus)
        #else
        content
        #endif
    }
}

extension View {
    /// Applies focus support only on tvOS
    func platformFocusable(_ shouldFocus: Bool = true) -> some View {
        modifier(PlatformFocusModifier(shouldFocus: shouldFocus))
    }
}

// MARK: - Gesture Support

/// Conditional gesture application
extension View {
    /// Applies a drag gesture only on iOS (not tvOS)
    @ViewBuilder
    func platformDragGesture<G: Gesture>(
        _ gesture: G,
        including mask: GestureMask = .all
    ) -> some View where G.Value: Equatable {
        #if os(iOS)
        self.gesture(gesture, including: mask)
        #else
        self
        #endif
    }

    /// Applies a tap gesture only on touch devices
    @ViewBuilder
    func platformTapGesture(count: Int = 1, perform action: @escaping () -> Void) -> some View {
        #if os(iOS)
        self.onTapGesture(count: count, perform: action)
        #else
        self
        #endif
    }
}

// MARK: - List Background Styling

extension View {
    /// Applies platform-appropriate list background styling.
    /// On tvOS: applies AppTheme gradient background.
    /// On iOS: conditionally applies dark background with hidden scroll content background.
    @ViewBuilder
    func platformListBackground(usesDark: Bool, colorScheme: ColorScheme) -> some View {
        #if os(tvOS)
        self.background(AppTheme.background(for: colorScheme))
        #elseif os(iOS)
        self
            .background(usesDark ? AppTheme.lightBackground : Color.clear)
            .scrollContentBackground(usesDark ? .hidden : .automatic)
            .environment(\.colorScheme, usesDark ? .dark : colorScheme)
        #else
        self
        #endif
    }
}
