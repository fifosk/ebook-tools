import SwiftUI

struct SleepTimerOption: Identifiable, Equatable {
    let id: String
    let label: String
    let seconds: Int

    static let presets: [SleepTimerOption] = [
        SleepTimerOption(id: "5m", label: "5 min", seconds: 5 * 60),
        SleepTimerOption(id: "15m", label: "15 min", seconds: 15 * 60),
        SleepTimerOption(id: "30m", label: "30 min", seconds: 30 * 60),
        SleepTimerOption(id: "45m", label: "45 min", seconds: 45 * 60)
    ]
}

@MainActor
final class SleepTimerController: ObservableObject {
    @Published private(set) var activeOption: SleepTimerOption?
    @Published private(set) var remainingSeconds: Int?

    private var timerTask: Task<Void, Never>?

    var isActive: Bool {
        remainingSeconds != nil
    }

    var remainingLabel: String {
        guard let remainingSeconds else { return "Sleep" }
        return Self.formatRemaining(seconds: remainingSeconds)
    }

    func start(option: SleepTimerOption, onExpire: @escaping @MainActor () -> Void) {
        cancel()
        activeOption = option
        remainingSeconds = option.seconds
        timerTask = Task { @MainActor [weak self] in
            guard let self else { return }
            var remaining = option.seconds
            while remaining > 0 {
                do {
                    try await Task.sleep(nanoseconds: 1_000_000_000)
                } catch {
                    return
                }
                guard !Task.isCancelled else { return }
                remaining -= 1
                self.remainingSeconds = remaining
            }
            self.activeOption = nil
            self.remainingSeconds = nil
            self.timerTask = nil
            onExpire()
        }
    }

    func cancel() {
        timerTask?.cancel()
        timerTask = nil
        activeOption = nil
        remainingSeconds = nil
    }

    static func formatRemaining(seconds: Int) -> String {
        let clamped = max(seconds, 0)
        let minutes = clamped / 60
        let remainingSeconds = clamped % 60
        if minutes >= 60 {
            let hours = minutes / 60
            let trailingMinutes = minutes % 60
            return "\(hours)h \(trailingMinutes)m"
        }
        if minutes > 0 {
            return "\(minutes)m"
        }
        return "\(remainingSeconds)s"
    }
}

struct SleepTimerMenu: View {
    @ObservedObject var timer: SleepTimerController
    let isTV: Bool
    let sizeScale: CGFloat
    let onStart: (SleepTimerOption) -> Void
    let onCancel: () -> Void

    var body: some View {
        Menu {
            if timer.isActive {
                Button("Cancel Timer", role: .destructive, action: onCancel)
            }
            Section("Sleep Timer") {
                ForEach(SleepTimerOption.presets) { option in
                    Button {
                        onStart(option)
                    } label: {
                        if timer.activeOption == option {
                            Label(option.label, systemImage: "checkmark")
                        } else {
                            Label(option.label, systemImage: "timer")
                        }
                    }
                }
            }
        } label: {
            pillLabel
        }
        .accessibilityIdentifier("sleepTimerPill")
        .accessibilityLabel(accessibilityLabel)
    }

    private var pillLabel: some View {
        HStack(spacing: 4 * sizeScale) {
            Image(systemName: timer.isActive ? "moon.zzz.fill" : "moon.zzz")
                .font(iconFont)
            Text(timer.remainingLabel)
                .font(labelFont)
                .monospacedDigit()
        }
        .foregroundStyle(Color.white.opacity(timer.isActive ? 1.0 : 0.85))
        .padding(.horizontal, (isTV ? 12 : 8) * sizeScale)
        .padding(.vertical, (isTV ? 6 : 4) * sizeScale)
        .background(
            Capsule()
                .fill(Color.black.opacity(timer.isActive ? 0.7 : 0.55))
                .overlay(
                    Capsule().stroke(Color.white.opacity(timer.isActive ? 0.35 : 0.22), lineWidth: 1)
                )
        )
    }

    private var accessibilityLabel: String {
        timer.isActive ? "Sleep timer: \(timer.remainingLabel) remaining" : "Sleep timer"
    }

    private var iconFont: Font {
        #if os(iOS) || os(tvOS)
        return .system(size: (isTV ? 17 : 12) * sizeScale, weight: .semibold)
        #else
        return .system(size: 12 * sizeScale, weight: .semibold)
        #endif
    }

    private var labelFont: Font {
        #if os(iOS) || os(tvOS)
        return .system(size: (isTV ? 13 : 11) * sizeScale, weight: .medium)
        #else
        return .system(size: 11 * sizeScale, weight: .medium)
        #endif
    }
}
