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
        return UIDevice.current.userInterfaceIdiom == .pad || UIDevice.current.userInterfaceIdiom == .phone
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
