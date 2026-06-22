import SwiftUI
#if os(iOS)
import UIKit
#endif

struct ShortcutHelpOverlayView: View {
    let onDismiss: () -> Void

    private let sections: [ShortcutHelpSection] = [
        ShortcutHelpSection(
            title: "Playback",
            items: [
                ShortcutHelpItem(keys: "Space", action: "Play or pause")
            ]
        ),
        ShortcutHelpSection(
            title: "Navigation",
            items: [
                ShortcutHelpItem(keys: "Left Arrow (playing)", action: "Previous sentence"),
                ShortcutHelpItem(keys: "Right Arrow (playing)", action: "Next sentence"),
                ShortcutHelpItem(keys: "Left / Right Arrow (paused)", action: "Previous or next word"),
                ShortcutHelpItem(keys: "Shift + Left / Right Arrow (paused)", action: "Extend selection"),
                ShortcutHelpItem(keys: "Ctrl + Left / Right (paused)", action: "Skip sentence"),
                ShortcutHelpItem(keys: "Ctrl + Left / Right (playing)", action: "Previous / next word"),
                ShortcutHelpItem(keys: "Enter", action: "Lookup word"),
                ShortcutHelpItem(keys: "Down Arrow (playing)", action: "Show menu"),
                ShortcutHelpItem(keys: "Up Arrow (playing)", action: "Hide menu"),
                ShortcutHelpItem(keys: "Up / Down Arrow (paused)", action: "Switch track"),
                ShortcutHelpItem(keys: "Down Arrow (bubble open)", action: "Focus bubble controls"),
                ShortcutHelpItem(keys: "Left / Right Arrow (bubble focus)", action: "Navigate controls"),
                ShortcutHelpItem(keys: "Up Arrow (bubble focus)", action: "Exit bubble focus")
            ]
        ),
        ShortcutHelpSection(
            title: "Touch",
            items: [
                ShortcutHelpItem(keys: "Tap word", action: "Jump to word"),
                ShortcutHelpItem(keys: "Tap background", action: "Play or pause"),
                ShortcutHelpItem(keys: "Swipe left", action: "Next sentence"),
                ShortcutHelpItem(keys: "Swipe right", action: "Previous sentence"),
                ShortcutHelpItem(keys: "Pinch text", action: "Resize tracks"),
                ShortcutHelpItem(keys: "Pinch bubble", action: "Resize MyLinguist"),
                ShortcutHelpItem(keys: "Pinch header (iPad)", action: "Resize header")
            ]
        ),
        ShortcutHelpSection(
            title: "Text Tracks",
            items: [
                ShortcutHelpItem(keys: "O", action: "Toggle original line"),
                ShortcutHelpItem(keys: "I", action: "Toggle transliteration line"),
                ShortcutHelpItem(keys: "P", action: "Toggle translation line")
            ]
        ),
        ShortcutHelpSection(
            title: "Audio Tracks",
            items: [
                ShortcutHelpItem(keys: "Shift + O", action: "Toggle original audio"),
                ShortcutHelpItem(keys: "Shift + P", action: "Toggle translation audio"),
                ShortcutHelpItem(keys: "Shift + I", action: "Toggle reading bed")
            ]
        ),
        ShortcutHelpSection(
            title: "Font Size",
            items: [
                ShortcutHelpItem(keys: "+ / -", action: "Track font size"),
                ShortcutHelpItem(keys: "Ctrl + +/-", action: "MyLinguist font size"),
                ShortcutHelpItem(keys: "Shift + +/-", action: "Header size")
            ]
        ),
        ShortcutHelpSection(
            title: "Help",
            items: [
                ShortcutHelpItem(keys: "H", action: "Toggle this overlay"),
                ShortcutHelpItem(keys: "Shift + H", action: "Toggle header"),
                ShortcutHelpItem(keys: "Option (hold)", action: "Show shortcuts overlay")
            ]
        )
    ]

    var body: some View {
        ZStack {
            Color.black.opacity(0.35)
                .ignoresSafeArea()
                .onTapGesture(perform: handleBackdropTap)
            VStack(alignment: .leading, spacing: 12) {
                header
                Divider()
                    .overlay(Color.white.opacity(0.12))
                ScrollView {
                    LazyVGrid(columns: gridColumns, alignment: .leading, spacing: 16) {
                        ForEach(sections) { section in
                            ShortcutHelpSectionView(section: section, keycapWidth: keycapColumnWidth)
                        }
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                }
                .frame(maxHeight: isPad ? 380 : 320)
            }
            .padding(20)
            .frame(maxWidth: isPad ? 660 : 520)
            .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 20, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: 20, style: .continuous)
                    .stroke(Color.white.opacity(0.18), lineWidth: 1)
            )
            .shadow(color: Color.black.opacity(0.2), radius: 14, x: 0, y: 8)
        }
    }

    private var header: some View {
        HStack(spacing: 10) {
            Label("Keyboard Shortcuts", systemImage: "keyboard")
                .font(.headline.weight(.semibold))
            Spacer()
            Button(action: handleCloseButtonTap) {
                Image(systemName: "xmark")
                    .font(.caption.weight(.semibold))
                    .padding(8)
                    .background(.black.opacity(0.15), in: Circle())
            }
            .buttonStyle(.plain)
        }
    }

    private var gridColumns: [GridItem] {
        if isPad {
            return [GridItem(.flexible(), spacing: 16), GridItem(.flexible(), spacing: 16)]
        }
        return [GridItem(.flexible())]
    }

    private var keycapColumnWidth: CGFloat {
        isPad ? 150 : 170
    }

    private var isPad: Bool {
        #if os(iOS)
        return UIDevice.current.userInterfaceIdiom == .pad
        #else
        return false
        #endif
    }

    private func handleBackdropTap() {
        onDismiss()
    }

    private func handleCloseButtonTap() {
        onDismiss()
    }

    private struct ShortcutHelpSectionView: View {
        let section: ShortcutHelpSection
        let keycapWidth: CGFloat

        var body: some View {
            VStack(alignment: .leading, spacing: 8) {
                Text(section.title.uppercased())
                    .font(.caption2.weight(.semibold))
                    .foregroundStyle(.secondary)
                ForEach(section.items) { item in
                    ShortcutHelpRow(item: item, keycapWidth: keycapWidth)
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }

    private struct ShortcutHelpRow: View {
        let item: ShortcutHelpItem
        let keycapWidth: CGFloat

        var body: some View {
            HStack(alignment: .top, spacing: 12) {
                KeycapGroup(keys: item.keys)
                    .frame(width: keycapWidth, alignment: .leading)
                Text(item.action)
                    .font(.callout)
                    .foregroundStyle(.primary)
                Spacer(minLength: 0)
            }
        }
    }

    private struct KeycapGroup: View {
        let keys: String

        var body: some View {
            let (base, context) = splitContext(keys)
            HStack(spacing: 6) {
                keycapContent(base)
                if let context {
                    ContextPill(label: context)
                }
            }
        }

        @ViewBuilder
        private func keycapContent(_ value: String) -> some View {
            let alternatives = value.split(separator: "/").map { $0.trimmingCharacters(in: .whitespaces) }
            HStack(spacing: 4) {
                ForEach(Array(alternatives.enumerated()), id: \.offset) { index, alternative in
                    if index > 0 {
                        Text("/")
                            .font(.caption2.weight(.semibold))
                            .foregroundStyle(.secondary)
                    }
                    let combo = alternative.split(separator: "+").map { $0.trimmingCharacters(in: .whitespaces) }
                    HStack(spacing: 4) {
                        ForEach(Array(combo.enumerated()), id: \.offset) { comboIndex, token in
                            if comboIndex > 0 {
                                Text("+")
                                    .font(.caption2.weight(.semibold))
                                    .foregroundStyle(.secondary)
                            }
                            KeycapView(label: keyLabel(String(token)))
                        }
                    }
                }
            }
        }

        private func splitContext(_ value: String) -> (String, String?) {
            guard let openRange = value.range(of: " ("),
                  value.hasSuffix(")") else {
                return (value, nil)
            }
            let base = value[..<openRange.lowerBound]
            let contextStart = value.index(openRange.lowerBound, offsetBy: 2)
            let contextEnd = value.index(before: value.endIndex)
            let context = value[contextStart..<contextEnd]
            return (String(base), String(context))
        }

        private func keyLabel(_ raw: String) -> String {
            let trimmed = raw.trimmingCharacters(in: .whitespacesAndNewlines)
            let lower = trimmed.lowercased()
            switch lower {
            case "left arrow":
                return "←"
            case "right arrow":
                return "→"
            case "up arrow":
                return "↑"
            case "down arrow":
                return "↓"
            case "option":
                return "⌥"
            case "shift":
                return "⇧"
            case "ctrl", "control":
                return "⌃"
            case "command", "cmd":
                return "⌘"
            case "enter", "return":
                return "↩︎"
            case "backspace":
                return "⌫"
            case "delete":
                return "⌦"
            case "+/-":
                return "±"
            case "space":
                return "Space"
            default:
                return trimmed
            }
        }
    }

    private struct KeycapView: View {
        let label: String

        var body: some View {
            Text(label)
                .font(.system(size: 12, weight: .semibold, design: .rounded))
                .foregroundStyle(.primary)
                .padding(.horizontal, 8)
                .padding(.vertical, 5)
                .background(
                    RoundedRectangle(cornerRadius: 6, style: .continuous)
                        .fill(Color.primary.opacity(0.12))
                )
                .overlay(
                    RoundedRectangle(cornerRadius: 6, style: .continuous)
                        .stroke(Color.primary.opacity(0.22), lineWidth: 1)
                )
        }
    }

    private struct ContextPill: View {
        let label: String

        var body: some View {
            Text(label)
                .font(.caption2.weight(.semibold))
                .foregroundStyle(.secondary)
                .padding(.horizontal, 6)
                .padding(.vertical, 3)
                .background(
                    Capsule()
                        .fill(Color.primary.opacity(0.08))
                )
        }
    }

    private struct ShortcutHelpSection: Identifiable {
        let id = UUID()
        let title: String
        let items: [ShortcutHelpItem]
    }

    private struct ShortcutHelpItem: Identifiable {
        let id = UUID()
        let keys: String
        let action: String
    }
}
