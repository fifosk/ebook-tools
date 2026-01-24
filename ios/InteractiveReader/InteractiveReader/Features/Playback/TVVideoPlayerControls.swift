import SwiftUI

#if os(tvOS)
import UIKit

// MARK: - TV Action Button

struct TVActionButton<Label: View>: View {
    let isFocusable: Bool
    let isFocused: Bool
    let onMoveUp: (() -> Void)?
    let onMoveDown: (() -> Void)?
    let action: () -> Void
    let label: () -> Label

    var body: some View {
        Button(action: action) {
            label()
        }
        .buttonStyle(.plain)
        .contentShape(Rectangle())
        .disabled(!isFocusable)
        .focusEffectDisabled()
        .onMoveCommand { direction in
            guard isFocused else { return }
            switch direction {
            case .up:
                onMoveUp?()
            case .down:
                onMoveDown?()
            default:
                break
            }
        }
    }
}

// MARK: - TV Scrubber

struct TVScrubber: View {
    @Binding var value: Double
    let range: ClosedRange<Double>
    let isFocusable: Bool
    let onEditingChanged: (Bool) -> Void
    let onCommit: (Double) -> Void
    let onUserInteraction: () -> Void

    @FocusState private var isFocused: Bool
    @State private var commitTask: Task<Void, Never>?
    @State private var isEditing = false

    var body: some View {
        GeometryReader { proxy in
            let progress = normalizedProgress
            let width = max(proxy.size.width, 1)
            let barHeight: CGFloat = 6
            let thumbSize: CGFloat = isFocused ? 18 : 14
            let xOffset = max(0, min(width - thumbSize, width * progress - thumbSize / 2))
            ZStack(alignment: .leading) {
                Capsule()
                    .fill(Color.white.opacity(0.25))
                    .frame(height: barHeight)
                Capsule()
                    .fill(Color.white)
                    .frame(width: max(thumbSize, width * progress), height: barHeight)
                Circle()
                    .fill(Color.white)
                    .frame(width: thumbSize, height: thumbSize)
                    .offset(x: xOffset)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
        .frame(height: 24)
        .focusable(isFocusable)
        .focused($isFocused)
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(isFocused ? Color.white.opacity(0.8) : .clear, lineWidth: 1)
        )
        .onChange(of: isFocused) { _, focused in
            onUserInteraction()
            if !focused {
                commitScrub()
            }
        }
        .onMoveCommand { direction in
            guard isFocused else { return }
            onUserInteraction()
            beginScrubbing()
            let step = stepSize
            switch direction {
            case .left:
                value = max(range.lowerBound, value - step)
            case .right:
                value = min(range.upperBound, value + step)
            default:
                break
            }
            scheduleCommit()
        }
        .onTapGesture {
            onUserInteraction()
            beginScrubbing()
            scheduleCommit()
        }
    }

    private var normalizedProgress: CGFloat {
        let span = max(range.upperBound - range.lowerBound, 1)
        let clamped = min(max(value, range.lowerBound), range.upperBound)
        return CGFloat((clamped - range.lowerBound) / span)
    }

    private var stepSize: Double {
        let span = max(range.upperBound - range.lowerBound, 1)
        return max(span / 300, 1)
    }

    private func scheduleCommit() {
        commitTask?.cancel()
        commitTask = Task {
            try? await Task.sleep(nanoseconds: 600_000_000)
            await MainActor.run {
                commitScrub()
            }
        }
    }

    private func commitScrub() {
        commitTask?.cancel()
        commitTask = nil
        if isEditing {
            onEditingChanged(false)
            isEditing = false
        }
        onCommit(value)
    }

    private func beginScrubbing() {
        guard !isEditing else { return }
        isEditing = true
        onEditingChanged(true)
    }
}

// MARK: - TV Control Label

struct VideoPlayerControlLabel: View {
    let systemName: String
    var label: String? = nil
    var font: Font? = nil
    var prominent: Bool = false
    var isFocused: Bool = false

    var body: some View {
        Group {
            if let label {
                Label(label, systemImage: systemName)
                    .labelStyle(.titleAndIcon)
            } else {
                Image(systemName: systemName)
            }
        }
        .font(font ?? .title3.weight(.semibold))
        .foregroundStyle(.white)
        .padding(.horizontal, 14)
        .padding(.vertical, 8)
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(prominent ? Color.white.opacity(0.18) : Color.black.opacity(0.45))
        )
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(isFocused ? Color.white.opacity(0.85) : Color.clear, lineWidth: 1)
        )
        .scaleEffect(isFocused ? 1.06 : 1.0)
        .shadow(color: isFocused ? Color.white.opacity(0.25) : .clear, radius: 6, x: 0, y: 0)
        .animation(.easeInOut(duration: 0.12), value: isFocused)
    }
}

// MARK: - TV Control Button

struct TVControlButton: View {
    let systemName: String
    var label: String? = nil
    var font: Font? = nil
    var prominent: Bool = false
    var isFocused: Bool = false
    var isFocusable: Bool = true
    let onMoveUp: (() -> Void)?
    let onMoveDown: (() -> Void)?
    let action: () -> Void

    var body: some View {
        TVActionButton(
            isFocusable: isFocusable,
            isFocused: isFocused,
            onMoveUp: onMoveUp,
            onMoveDown: onMoveDown,
            action: action
        ) {
            VideoPlayerControlLabel(
                systemName: systemName,
                label: label,
                font: font,
                prominent: prominent,
                isFocused: isFocused
            )
        }
    }
}

// MARK: - TV Playback Controls Bar

struct TVPlaybackControlsBar: View {
    let isPlaying: Bool
    let showTVControls: Bool
    let showSubtitleSettings: Bool
    let suppressControlFocus: Bool
    let hasOptions: Bool
    let canShowBookmarks: Bool
    let duration: Double
    let displayTime: Double
    @Binding var scrubberValue: Double
    var focusTarget: FocusState<VideoPlayerFocusTarget?>.Binding

    // Callbacks
    let onPlayPause: () -> Void
    let onSkipBackward: () -> Void
    let onSkipForward: () -> Void
    let onSeek: (Double) -> Void
    let onEditingChanged: (Bool) -> Void
    let onUserInteraction: () -> Void
    let onShowSubtitleSettings: () -> Void

    // Menus
    let bookmarkMenu: AnyView?
    let speedMenu: AnyView

    var body: some View {
        VStack(spacing: 10) {
            HStack(alignment: .center, spacing: 18) {
                Spacer(minLength: 0)
                controlsRow
                Spacer(minLength: 0)
            }
            if duration > 0 {
                scrubberRow
            }
        }
        .padding(.horizontal, 18)
        .padding(.vertical, 14)
        .background(
            LinearGradient(
                colors: [Color.black.opacity(0.75), Color.black.opacity(0.35)],
                startPoint: .bottom,
                endPoint: .top
            ),
            in: RoundedRectangle(cornerRadius: 20)
        )
        .opacity(showTVControls ? 1 : 0)
        .allowsHitTesting(showTVControls)
        .animation(.easeInOut(duration: 0.2), value: showTVControls)
        .focusSection()
        .onMoveCommand { direction in
            guard !showSubtitleSettings else { return }
            if direction == .up {
                focusTarget.wrappedValue = .subtitles
            }
        }
    }

    private var controlsFocusEnabled: Bool {
        showTVControls && !showSubtitleSettings && !suppressControlFocus
    }

    @ViewBuilder
    private var controlsRow: some View {
        HStack(spacing: 14) {
            TVControlButton(
                systemName: "gobackward.15",
                isFocused: focusTarget.wrappedValue == .control(.skipBackward),
                isFocusable: controlsFocusEnabled,
                onMoveUp: { focusTarget.wrappedValue = .control(.header) },
                onMoveDown: { focusTarget.wrappedValue = .subtitles },
                action: onSkipBackward
            )
            .focused(focusTarget, equals: .control(.skipBackward))

            TVControlButton(
                systemName: isPlaying ? "pause.fill" : "play.fill",
                prominent: true,
                isFocused: focusTarget.wrappedValue == .control(.playPause),
                isFocusable: controlsFocusEnabled,
                onMoveUp: { focusTarget.wrappedValue = .control(.header) },
                onMoveDown: { focusTarget.wrappedValue = .subtitles },
                action: onPlayPause
            )
            .focused(focusTarget, equals: .control(.playPause))

            TVControlButton(
                systemName: "goforward.15",
                isFocused: focusTarget.wrappedValue == .control(.skipForward),
                isFocusable: controlsFocusEnabled,
                onMoveUp: { focusTarget.wrappedValue = .control(.header) },
                onMoveDown: { focusTarget.wrappedValue = .subtitles },
                action: onSkipForward
            )
            .focused(focusTarget, equals: .control(.skipForward))

            if let bookmarkMenu, canShowBookmarks {
                bookmarkMenu
                    .focused(focusTarget, equals: .control(.bookmark))
            }

            speedMenu
                .focused(focusTarget, equals: .control(.speed))

            if hasOptions {
                TVControlButton(
                    systemName: "captions.bubble",
                    label: "Options",
                    font: .callout.weight(.semibold),
                    isFocused: focusTarget.wrappedValue == .control(.captions),
                    isFocusable: controlsFocusEnabled,
                    onMoveUp: { focusTarget.wrappedValue = .control(.header) },
                    onMoveDown: { focusTarget.wrappedValue = .subtitles },
                    action: onShowSubtitleSettings
                )
                .focused(focusTarget, equals: .control(.captions))
            }
        }
        .onMoveCommand { direction in
            guard !showSubtitleSettings else { return }
            if direction == .up {
                focusTarget.wrappedValue = .control(.header)
            } else if direction == .down {
                focusTarget.wrappedValue = .subtitles
            }
        }
    }

    @ViewBuilder
    private var scrubberRow: some View {
        HStack(spacing: 12) {
            Text(formattedTime(displayTime))
                .font(.caption2)
                .foregroundStyle(.white.opacity(0.8))
                .frame(width: 64, alignment: .leading)
            TVScrubber(
                value: $scrubberValue,
                range: 0...max(duration, 1),
                isFocusable: controlsFocusEnabled,
                onEditingChanged: onEditingChanged,
                onCommit: onSeek,
                onUserInteraction: onUserInteraction
            )
            .focused(focusTarget, equals: .control(.scrubber))
            Text(formattedTime(duration))
                .font(.caption2)
                .foregroundStyle(.white.opacity(0.8))
                .frame(width: 64, alignment: .trailing)
        }
    }

    private func formattedTime(_ seconds: Double) -> String {
        guard seconds.isFinite else { return "--:--" }
        let total = max(0, Int(seconds.rounded()))
        let hours = total / 3600
        let minutes = (total % 3600) / 60
        let remainingSeconds = total % 60
        if hours > 0 {
            return String(format: "%d:%02d:%02d", hours, minutes, remainingSeconds)
        }
        return String(format: "%02d:%02d", minutes, remainingSeconds)
    }
}

// MARK: - TV Header Toggle Pill

struct TVHeaderTogglePill: View {
    let isCollapsed: Bool
    let isFocusable: Bool
    let isFocused: Bool
    let onMoveDown: () -> Void
    let onToggle: () -> Void

    var body: some View {
        TVActionButton(
            isFocusable: isFocusable,
            isFocused: isFocused,
            onMoveUp: nil,
            onMoveDown: onMoveDown,
            action: onToggle
        ) {
            Image(systemName: isCollapsed ? "chevron.down" : "chevron.up")
                .font(.caption.weight(.semibold))
                .padding(.horizontal, 8)
                .padding(.vertical, 4)
                .background(Color.black.opacity(0.6), in: Capsule())
                .foregroundStyle(.white)
        }
        .accessibilityLabel(isCollapsed ? "Show info header" : "Hide info header")
    }
}
#endif
