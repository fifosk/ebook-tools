import SwiftUI

enum LoginServerStatus: String {
    case checking
    case online
    case offline

    var label: String {
        switch self {
        case .checking:
            return "Checking server"
        case .online:
            return "Server online"
        case .offline:
            return "Server offline"
        }
    }
}

struct LoginBackgroundView: View {
    @Environment(\.colorScheme) private var colorScheme

    var body: some View {
        ZStack {
            AppTheme.background(for: colorScheme)
            if colorScheme != .dark {
                RadialGradient(
                    gradient: Gradient(colors: [Color(red: 0.22, green: 0.74, blue: 0.97, opacity: 0.22), .clear]),
                    center: .topLeading,
                    startRadius: 20,
                    endRadius: 420
                )
                RadialGradient(
                    gradient: Gradient(colors: [Color(red: 0.23, green: 0.51, blue: 0.96, opacity: 0.18), .clear]),
                    center: .topTrailing,
                    startRadius: 20,
                    endRadius: 460
                )
            }
        }
        .ignoresSafeArea()
    }
}

struct LoginCard<Content: View>: View {
    let content: Content

    init(@ViewBuilder content: () -> Content) {
        self.content = content()
    }

    var body: some View {
        content
            .padding(.vertical, 24)
            .padding(.horizontal, 22)
            .frame(maxWidth: 420)
            .background(AppTheme.lightBackground.opacity(0.72))
            .clipShape(RoundedRectangle(cornerRadius: 24, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: 24, style: .continuous)
                    .stroke(Color(red: 0.58, green: 0.64, blue: 0.72).opacity(0.2), lineWidth: 1)
            )
            .shadow(color: Color.black.opacity(0.35), radius: 26, x: 0, y: 18)
    }
}

struct LoginHeaderView: View {
    var body: some View {
        HStack(spacing: 12) {
            ZStack {
                Circle()
                    .fill(Color(red: 0.23, green: 0.51, blue: 0.96).opacity(0.2))
                    .overlay(
                        Circle()
                            .stroke(Color(red: 0.38, green: 0.65, blue: 0.98).opacity(0.55), lineWidth: 1)
                    )
                Image(systemName: "globe")
                    .font(.system(size: 22, weight: .semibold))
                    .foregroundStyle(Color(red: 0.38, green: 0.65, blue: 0.98))
            }
            .frame(width: 46, height: 46)

            Text("Language tools")
                .font(.system(size: 24, weight: .semibold))
                .foregroundStyle(Color.white)
        }
        .frame(maxWidth: .infinity, alignment: .center)
    }
}

struct LoginServerStatusView: View {
    let status: LoginServerStatus

    var body: some View {
        HStack(spacing: 12) {
            LoginTrafficLightView(status: status)
            VStack(alignment: .leading, spacing: 2) {
                Text("Healthcheck")
                    .font(.caption)
                    .foregroundStyle(Color.white.opacity(0.6))
                Text(status.label)
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(Color.white)
            }
        }
        .frame(maxWidth: .infinity, alignment: .center)
        .padding(12)
        .background(Color(red: 0.06, green: 0.09, blue: 0.16).opacity(0.55))
        .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 14, style: .continuous)
                .stroke(Color(red: 0.58, green: 0.64, blue: 0.72).opacity(0.2), lineWidth: 1)
        )
    }
}

struct LoginTrafficLightView: View {
    let status: LoginServerStatus

    var body: some View {
        VStack(spacing: 6) {
            circle(for: .offline)
            circle(for: .checking)
            circle(for: .online)
        }
        .padding(6)
        .background(Color(red: 0.01, green: 0.02, blue: 0.09).opacity(0.6))
        .clipShape(Capsule())
    }

    private func circle(for lane: LoginServerStatus) -> some View {
        let isActive = status == lane
        let baseColor: Color
        switch lane {
        case .offline:
            baseColor = Color(red: 0.92, green: 0.26, blue: 0.29)
        case .checking:
            baseColor = Color(red: 0.96, green: 0.74, blue: 0.2)
        case .online:
            baseColor = Color(red: 0.2, green: 0.8, blue: 0.4)
        }
        return Circle()
            .fill(baseColor.opacity(isActive ? 1 : 0.25))
            .frame(width: 10, height: 10)
            .overlay(
                Circle()
                    .stroke(Color.white.opacity(isActive ? 0.5 : 0.15), lineWidth: 1)
            )
            .shadow(color: baseColor.opacity(isActive ? 0.45 : 0), radius: 6)
    }
}

struct LoginFieldStyle: ViewModifier {
    func body(content: Content) -> some View {
        content
            .textFieldStyle(.plain)
            .padding(.vertical, 10)
            .padding(.horizontal, 12)
            .background(Color(red: 0.06, green: 0.09, blue: 0.16).opacity(0.9))
            .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: 12, style: .continuous)
                    .stroke(Color(red: 0.58, green: 0.64, blue: 0.72).opacity(0.3), lineWidth: 1)
            )
            .foregroundStyle(Color.white)
            .tint(Color(red: 0.66, green: 0.88, blue: 1))
    }
}

extension View {
    func loginFieldStyle() -> some View {
        modifier(LoginFieldStyle())
    }

    func loginPrimaryButtonStyle() -> some View {
        buttonStyle(LoginPrimaryButtonStyle())
    }
}

struct LoginPrimaryButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.headline)
            .foregroundStyle(Color.white)
            .padding(.vertical, 12)
            .frame(maxWidth: .infinity)
            .background(
                LinearGradient(
                    colors: [
                        Color(red: 0.22, green: 0.74, blue: 0.97),
                        Color(red: 0.51, green: 0.55, blue: 0.97)
                    ],
                    startPoint: .topLeading,
                    endPoint: .bottomTrailing
                )
                .opacity(configuration.isPressed ? 0.85 : 1)
            )
            .clipShape(Capsule())
            .overlay(
                Capsule()
                    .stroke(Color.white.opacity(0.25), lineWidth: 1)
            )
            .shadow(color: Color(red: 0.22, green: 0.74, blue: 0.97).opacity(0.35), radius: 16, x: 0, y: 8)
            .scaleEffect(configuration.isPressed ? 0.98 : 1)
            .animation(.easeOut(duration: 0.15), value: configuration.isPressed)
    }
}
