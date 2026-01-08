import SwiftUI
#if os(iOS)
import UIKit

struct VideoShortcutHelpOverlayView: View {
    let onDismiss: () -> Void

    private let sections: [ShortcutHelpSection] = [
        ShortcutHelpSection(
            title: "Playback",
            items: [
                ShortcutHelpItem(keys: "Space", action: "Play or pause"),
                ShortcutHelpItem(keys: "Left Arrow (playing)", action: "Previous sentence"),
                ShortcutHelpItem(keys: "Right Arrow (playing)", action: "Next sentence")
            ]
        ),
        ShortcutHelpSection(
            title: "Subtitles",
            items: [
                ShortcutHelpItem(keys: "Left / Right Arrow (paused)", action: "Previous or next word"),
                ShortcutHelpItem(keys: "Up / Down Arrow (paused)", action: "Switch subtitle line"),
                ShortcutHelpItem(keys: "Enter", action: "Lookup word"),
                ShortcutHelpItem(keys: "O", action: "Toggle original line"),
                ShortcutHelpItem(keys: "I", action: "Toggle transliteration line"),
                ShortcutHelpItem(keys: "P", action: "Toggle translation line"),
                ShortcutHelpItem(keys: "+ / -", action: "Subtitle font size")
            ]
        ),
        ShortcutHelpSection(
            title: "Touch",
            items: [
                ShortcutHelpItem(keys: "Tap word", action: "Jump to word"),
                ShortcutHelpItem(keys: "Long press word", action: "System lookup"),
                ShortcutHelpItem(keys: "Drag subtitles", action: "Move subtitle position"),
                ShortcutHelpItem(keys: "Pinch subtitles", action: "Resize subtitle text"),
                ShortcutHelpItem(keys: "Pinch bubble", action: "Resize lookup bubble")
            ]
        ),
        ShortcutHelpSection(
            title: "Help",
            items: [
                ShortcutHelpItem(keys: "H", action: "Toggle this overlay"),
                ShortcutHelpItem(keys: "Option (hold)", action: "Show shortcuts overlay")
            ]
        )
    ]

    var body: some View {
        ZStack {
            Color.black.opacity(0.55)
                .ignoresSafeArea()
                .onTapGesture {
                    onDismiss()
                }
            VStack(alignment: .leading, spacing: 16) {
                HStack {
                    Text("Keyboard Shortcuts")
                        .font(.title3.weight(.semibold))
                    Spacer()
                    Button(action: onDismiss) {
                        Image(systemName: "xmark")
                            .font(.caption.weight(.semibold))
                            .padding(6)
                            .background(.black.opacity(0.3), in: Circle())
                    }
                    .buttonStyle(.plain)
                }
                ScrollView {
                    VStack(alignment: .leading, spacing: 12) {
                        ForEach(sections) { section in
                            VStack(alignment: .leading, spacing: 6) {
                                Text(section.title)
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                                ForEach(section.items) { item in
                                    HStack(alignment: .top, spacing: 12) {
                                        Text(item.keys)
                                            .font(.callout.monospaced())
                                            .frame(width: 170, alignment: .leading)
                                        Text(item.action)
                                            .font(.callout)
                                        Spacer(minLength: 0)
                                    }
                                }
                            }
                        }
                    }
                }
                .frame(maxHeight: 320)
            }
            .padding(20)
            .frame(maxWidth: 520)
            .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 18))
            .overlay(
                RoundedRectangle(cornerRadius: 18)
                    .stroke(Color.white.opacity(0.12), lineWidth: 1)
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

struct VideoKeyboardCommandHandler: UIViewControllerRepresentable {
    let onPlayPause: () -> Void
    let onSkipBackward: () -> Void
    let onSkipForward: () -> Void
    let onNavigateLineUp: () -> Void
    let onNavigateLineDown: () -> Void
    let onLookup: () -> Void
    let onIncreaseFont: () -> Void
    let onDecreaseFont: () -> Void
    let onToggleOriginal: () -> Void
    let onToggleTransliteration: () -> Void
    let onToggleTranslation: () -> Void
    let onToggleShortcutHelp: () -> Void
    let onOptionKeyDown: () -> Void
    let onOptionKeyUp: () -> Void

    func makeUIViewController(context: Context) -> KeyCommandController {
        let controller = KeyCommandController()
        controller.onPlayPause = onPlayPause
        controller.onSkipBackward = onSkipBackward
        controller.onSkipForward = onSkipForward
        controller.onNavigateLineUp = onNavigateLineUp
        controller.onNavigateLineDown = onNavigateLineDown
        controller.onLookup = onLookup
        controller.onIncreaseFont = onIncreaseFont
        controller.onDecreaseFont = onDecreaseFont
        controller.onToggleOriginal = onToggleOriginal
        controller.onToggleTransliteration = onToggleTransliteration
        controller.onToggleTranslation = onToggleTranslation
        controller.onToggleShortcutHelp = onToggleShortcutHelp
        controller.onOptionKeyDown = onOptionKeyDown
        controller.onOptionKeyUp = onOptionKeyUp
        return controller
    }

    func updateUIViewController(_ uiViewController: KeyCommandController, context: Context) {
        uiViewController.onPlayPause = onPlayPause
        uiViewController.onSkipBackward = onSkipBackward
        uiViewController.onSkipForward = onSkipForward
        uiViewController.onNavigateLineUp = onNavigateLineUp
        uiViewController.onNavigateLineDown = onNavigateLineDown
        uiViewController.onLookup = onLookup
        uiViewController.onIncreaseFont = onIncreaseFont
        uiViewController.onDecreaseFont = onDecreaseFont
        uiViewController.onToggleOriginal = onToggleOriginal
        uiViewController.onToggleTransliteration = onToggleTransliteration
        uiViewController.onToggleTranslation = onToggleTranslation
        uiViewController.onToggleShortcutHelp = onToggleShortcutHelp
        uiViewController.onOptionKeyDown = onOptionKeyDown
        uiViewController.onOptionKeyUp = onOptionKeyUp
    }

    final class KeyCommandController: UIViewController {
        var onPlayPause: (() -> Void)?
        var onSkipBackward: (() -> Void)?
        var onSkipForward: (() -> Void)?
        var onNavigateLineUp: (() -> Void)?
        var onNavigateLineDown: (() -> Void)?
        var onLookup: (() -> Void)?
        var onIncreaseFont: (() -> Void)?
        var onDecreaseFont: (() -> Void)?
        var onToggleOriginal: (() -> Void)?
        var onToggleTransliteration: (() -> Void)?
        var onToggleTranslation: (() -> Void)?
        var onToggleShortcutHelp: (() -> Void)?
        var onOptionKeyDown: (() -> Void)?
        var onOptionKeyUp: (() -> Void)?
        private var isOptionKeyDown = false

        override var canBecomeFirstResponder: Bool {
            true
        }

        override func viewDidAppear(_ animated: Bool) {
            super.viewDidAppear(animated)
            becomeFirstResponder()
        }

        override var keyCommands: [UIKeyCommand]? {
            [
                makeCommand(input: " ", action: #selector(handlePlayPause)),
                makeCommand(input: UIKeyCommand.inputLeftArrow, action: #selector(handleSkipBackward)),
                makeCommand(input: UIKeyCommand.inputRightArrow, action: #selector(handleSkipForward)),
                makeCommand(input: UIKeyCommand.inputUpArrow, action: #selector(handleLineUp)),
                makeCommand(input: UIKeyCommand.inputDownArrow, action: #selector(handleLineDown)),
                makeCommand(input: "\r", action: #selector(handleLookup)),
                makeCommand(input: "\n", action: #selector(handleLookup)),
                makeCommand(input: "o", action: #selector(handleToggleOriginal)),
                makeCommand(input: "o", modifiers: [.shift], action: #selector(handleToggleOriginal)),
                makeCommand(input: "i", action: #selector(handleToggleTransliteration)),
                makeCommand(input: "i", modifiers: [.shift], action: #selector(handleToggleTransliteration)),
                makeCommand(input: "p", action: #selector(handleToggleTranslation)),
                makeCommand(input: "p", modifiers: [.shift], action: #selector(handleToggleTranslation)),
                makeCommand(input: "=", action: #selector(handleIncreaseFont)),
                makeCommand(input: "=", modifiers: [.shift], action: #selector(handleIncreaseFont)),
                makeCommand(input: "+", action: #selector(handleIncreaseFont)),
                makeCommand(input: "-", action: #selector(handleDecreaseFont)),
                makeCommand(input: "h", action: #selector(handleToggleHelp)),
                makeCommand(input: "h", modifiers: [.shift], action: #selector(handleToggleHelp))
            ]
        }

        @objc private func handlePlayPause() {
            onPlayPause?()
        }

        @objc private func handleSkipBackward() {
            onSkipBackward?()
        }

        @objc private func handleSkipForward() {
            onSkipForward?()
        }

        @objc private func handleLineUp() {
            onNavigateLineUp?()
        }

        @objc private func handleLineDown() {
            onNavigateLineDown?()
        }

        @objc private func handleLookup() {
            onLookup?()
        }

        @objc private func handleIncreaseFont() {
            onIncreaseFont?()
        }

        @objc private func handleDecreaseFont() {
            onDecreaseFont?()
        }

        @objc private func handleToggleOriginal() {
            onToggleOriginal?()
        }

        @objc private func handleToggleTransliteration() {
            onToggleTransliteration?()
        }

        @objc private func handleToggleTranslation() {
            onToggleTranslation?()
        }

        @objc private func handleToggleHelp() {
            onToggleShortcutHelp?()
        }

        override func pressesBegan(_ presses: Set<UIPress>, with event: UIPressesEvent?) {
            if shouldHandleOptionKey(presses), !isOptionKeyDown {
                isOptionKeyDown = true
                onOptionKeyDown?()
            }
            super.pressesBegan(presses, with: event)
        }

        override func pressesEnded(_ presses: Set<UIPress>, with event: UIPressesEvent?) {
            if shouldHandleOptionKey(presses), isOptionKeyDown {
                isOptionKeyDown = false
                onOptionKeyUp?()
            }
            super.pressesEnded(presses, with: event)
        }

        override func pressesCancelled(_ presses: Set<UIPress>, with event: UIPressesEvent?) {
            if isOptionKeyDown {
                isOptionKeyDown = false
                onOptionKeyUp?()
            }
            super.pressesCancelled(presses, with: event)
        }

        private func makeCommand(
            input: String,
            modifiers: UIKeyModifierFlags = [],
            action: Selector
        ) -> UIKeyCommand {
            let command = UIKeyCommand(input: input, modifierFlags: modifiers, action: action)
            command.wantsPriorityOverSystemBehavior = true
            return command
        }

        private func shouldHandleOptionKey(_ presses: Set<UIPress>) -> Bool {
            for press in presses {
                guard let key = press.key else { continue }
                if key.keyCode == .keyboardLeftAlt || key.keyCode == .keyboardRightAlt {
                    return true
                }
                if key.characters.isEmpty,
                   key.charactersIgnoringModifiers.isEmpty,
                   key.modifierFlags.contains(.alternate) {
                    return true
                }
            }
            return false
        }
    }
}
#endif
