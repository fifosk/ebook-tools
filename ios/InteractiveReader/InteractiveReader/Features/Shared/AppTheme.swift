import SwiftUI

enum AppTheme {
    static let lightBackground = Color(red: 0.06, green: 0.09, blue: 0.16)
    static let darkBackground = Color.black

    static func background(for scheme: ColorScheme) -> some View {
        #if os(tvOS)
        ZStack {
            Color(red: 0.03, green: 0.10, blue: 0.18)
            RadialGradient(
                gradient: Gradient(colors: [
                    Color(red: 56 / 255, green: 189 / 255, blue: 248 / 255).opacity(0.22),
                    .clear
                ]),
                center: UnitPoint(x: 0.18, y: 0.18),
                startRadius: 0,
                endRadius: 520
            )
            RadialGradient(
                gradient: Gradient(colors: [
                    Color(red: 59 / 255, green: 130 / 255, blue: 246 / 255).opacity(0.18),
                    .clear
                ]),
                center: UnitPoint(x: 0.82, y: 0.08),
                startRadius: 0,
                endRadius: 620
            )
        }
        #else
        scheme == .dark ? darkBackground : lightBackground
        #endif
    }
}
