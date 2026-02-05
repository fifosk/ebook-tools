import SwiftUI
#if canImport(UIKit)
import UIKit
#endif

// MARK: - Platform Detection

/// Centralized platform detection to avoid scattered #if os() checks
enum PlatformAdapter {
    /// Whether running on iPad
    static var isPad: Bool {
        #if os(iOS)
        return UIDevice.current.userInterfaceIdiom == .pad
        #else
        return false
        #endif
    }

    /// Whether running on iPhone
    static var isPhone: Bool {
        #if os(iOS)
        return UIDevice.current.userInterfaceIdiom == .phone
        #else
        return false
        #endif
    }

    /// Whether running on Apple TV
    static var isTV: Bool {
        #if os(tvOS)
        return true
        #else
        return false
        #endif
    }

    /// Whether running on macOS (Mac Catalyst or native)
    static var isMac: Bool {
        #if targetEnvironment(macCatalyst) || os(macOS)
        return true
        #else
        return false
        #endif
    }

    /// Whether the device supports touch input
    static var supportsTouch: Bool {
        #if os(iOS) || os(visionOS)
        return true
        #else
        return false
        #endif
    }

    /// Whether the device uses focus-based navigation (tvOS)
    static var usesFocusNavigation: Bool {
        #if os(tvOS)
        return true
        #else
        return false
        #endif
    }

    /// Whether keyboard shortcuts should be enabled
    static var supportsKeyboardShortcuts: Bool {
        #if os(iOS)
        return UIDevice.current.userInterfaceIdiom == .pad
        #elseif os(macOS) || targetEnvironment(macCatalyst)
        return true
        #else
        return false
        #endif
    }
}

// MARK: - Platform Metrics

/// Platform-specific size and spacing values
enum PlatformMetrics {
    /// Standard spacing between elements
    static var standardSpacing: CGFloat {
        #if os(tvOS)
        return 20
        #else
        return PlatformAdapter.isPad ? 16 : 12
        #endif
    }

    /// Compact spacing for tight layouts
    static var compactSpacing: CGFloat {
        #if os(tvOS)
        return 12
        #else
        return PlatformAdapter.isPad ? 10 : 8
        #endif
    }

    /// Standard corner radius
    static var cornerRadius: CGFloat {
        #if os(tvOS)
        return 16
        #else
        return PlatformAdapter.isPad ? 12 : 10
        #endif
    }

    /// Standard button size for playback controls
    static var playbackButtonSize: CGFloat {
        #if os(tvOS)
        return 60
        #else
        return PlatformAdapter.isPad ? 48 : 40
        #endif
    }

    /// Standard icon size for controls
    static var controlIconSize: CGFloat {
        #if os(tvOS)
        return 32
        #else
        return PlatformAdapter.isPad ? 24 : 20
        #endif
    }

    /// Icon size for list action rows (globe, iCloud, etc.)
    static var listIconSize: CGFloat {
        #if os(tvOS)
        return 20
        #else
        return 18
        #endif
    }

    /// Safe area inset for overlays
    static var overlayInset: CGFloat {
        #if os(tvOS)
        return 60
        #else
        return PlatformAdapter.isPad ? 24 : 16
        #endif
    }

    /// UI scale factor for adaptive layouts
    static var uiScale: CGFloat {
        #if os(tvOS)
        return 2.0
        #else
        return PlatformAdapter.isPad ? 1.5 : 1.0
        #endif
    }
}

// MARK: - Platform Typography

/// Platform-specific font styles
enum PlatformTypography {
    /// Title font for headers
    static var titleFont: Font {
        #if os(tvOS)
        return .title2
        #else
        return PlatformAdapter.isPad ? .title3 : .headline
        #endif
    }

    /// Subtitle font for secondary headers
    static var subtitleFont: Font {
        #if os(tvOS)
        return .headline
        #else
        return PlatformAdapter.isPad ? .subheadline : .footnote
        #endif
    }

    /// Body font for content
    static var bodyFont: Font {
        #if os(tvOS)
        return .body
        #else
        return .body
        #endif
    }

    /// Caption font for small labels
    static var captionFont: Font {
        #if os(tvOS)
        return .callout
        #else
        return .caption
        #endif
    }

    /// Monospaced font for timing displays
    static var monospacedFont: Font {
        #if os(tvOS)
        return .body.monospacedDigit()
        #else
        return .caption.monospacedDigit()
        #endif
    }

    /// Scaled font from UIFont.TextStyle.
    /// On tvOS applies 0.5x scaling; on iOS returns matching SwiftUI Font.
    static func scaledFont(_ style: UIFont.TextStyle) -> Font {
        #if os(tvOS)
        let size = UIFont.preferredFont(forTextStyle: style).pointSize * 0.5
        return .system(size: size)
        #else
        switch style {
        case .headline: return .headline
        case .subheadline: return .subheadline
        case .caption1: return .caption
        case .caption2: return .caption2
        case .body: return .body
        case .callout: return .callout
        case .footnote: return .footnote
        default: return .body
        }
        #endif
    }

    /// Header font for list sections (used by JobsView, LibraryView, etc.)
    static var sectionHeaderFont: Font {
        scaledFont(.body)
    }
}

// MARK: - Platform Colors

/// Platform-specific color definitions
enum PlatformColors {
    /// Secondary background color
    static var secondaryBackground: Color {
        #if os(iOS)
        return Color(uiColor: .secondarySystemBackground)
        #elseif os(tvOS)
        return Color.black.opacity(0.2)
        #else
        return Color.secondary.opacity(0.2)
        #endif
    }

    /// Tertiary background color
    static var tertiaryBackground: Color {
        #if os(iOS)
        return Color(uiColor: .tertiarySystemBackground)
        #elseif os(tvOS)
        return Color.black.opacity(0.15)
        #else
        return Color.secondary.opacity(0.15)
        #endif
    }

    /// Overlay background for controls
    static var overlayBackground: Color {
        #if os(tvOS)
        return Color.black.opacity(0.6)
        #else
        return Color.black.opacity(0.4)
        #endif
    }

    // MARK: Status Colors

    /// Color for pending/pausing status indicators
    static var statusPendingColor: Color {
        #if os(tvOS)
        return .yellow
        #else
        return .orange
        #endif
    }

    /// Color for running/active status indicators
    static var statusActiveColor: Color {
        #if os(tvOS)
        return .cyan
        #else
        return .blue
        #endif
    }

    // MARK: Row Text Colors

    /// Primary text color for list rows.
    /// - Parameters:
    ///   - isFocused: tvOS focus state (pass `false` on iOS)
    ///   - usesDarkBackground: iOS dark background mode (pass `false` on tvOS)
    static func rowTitleColor(isFocused: Bool = false, usesDarkBackground: Bool = false) -> Color {
        #if os(tvOS)
        return isFocused ? .black : .white
        #elseif os(iOS)
        return usesDarkBackground ? .white : .primary
        #else
        return .primary
        #endif
    }

    /// Secondary text color for list rows.
    static func rowSecondaryColor(isFocused: Bool = false, usesDarkBackground: Bool = false) -> Color {
        #if os(tvOS)
        return isFocused ? .black.opacity(0.7) : .white.opacity(0.75)
        #elseif os(iOS)
        return usesDarkBackground ? .white.opacity(0.75) : .gray
        #else
        return .gray
        #endif
    }

    /// Tertiary text color for list rows.
    static func rowTertiaryColor(isFocused: Bool = false, usesDarkBackground: Bool = false) -> Color {
        #if os(tvOS)
        return isFocused ? .black.opacity(0.55) : .white.opacity(0.6)
        #elseif os(iOS)
        return usesDarkBackground ? .white.opacity(0.6) : .gray.opacity(0.8)
        #else
        return .gray.opacity(0.6)
        #endif
    }
}

// MARK: - Platform Control Styles

/// Platform-specific control styling helpers
enum PlatformControlStyle {
    /// Button corner radius
    static var buttonCornerRadius: CGFloat {
        #if os(tvOS)
        return 12
        #else
        return PlatformAdapter.isPad ? 10 : 8
        #endif
    }

    /// Whether to use circular button backgrounds
    static var useCircularButtons: Bool {
        #if os(tvOS)
        return false
        #else
        return true
        #endif
    }

    /// Control size for buttons
    #if os(tvOS)
    static let controlSize: ControlSize = .small
    #else
    static let controlSize: ControlSize = .regular
    #endif
}

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
