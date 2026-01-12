import SwiftUI

enum AppTheme {
    static let lightBackground = Color(red: 0.06, green: 0.09, blue: 0.16)
    static let darkBackground = Color.black

    static func background(for scheme: ColorScheme) -> Color {
        scheme == .dark ? darkBackground : lightBackground
    }
}
