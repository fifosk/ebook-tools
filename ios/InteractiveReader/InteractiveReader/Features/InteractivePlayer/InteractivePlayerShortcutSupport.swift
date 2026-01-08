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
                ShortcutHelpItem(keys: "Ctrl + Left Arrow", action: "Previous word"),
                ShortcutHelpItem(keys: "Ctrl + Right Arrow", action: "Next word"),
                ShortcutHelpItem(keys: "Enter", action: "Lookup word"),
                ShortcutHelpItem(keys: "Down Arrow (playing)", action: "Show menu"),
                ShortcutHelpItem(keys: "Up Arrow (playing)", action: "Hide menu"),
                ShortcutHelpItem(keys: "Up / Down Arrow (paused)", action: "Switch track")
            ]
        ),
        ShortcutHelpSection(
            title: "Touch",
            items: [
                ShortcutHelpItem(keys: "Tap word", action: "Jump to word"),
                ShortcutHelpItem(keys: "Double tap background", action: "Play or pause"),
                ShortcutHelpItem(keys: "Swipe left", action: "Next sentence"),
                ShortcutHelpItem(keys: "Swipe right", action: "Previous sentence"),
                ShortcutHelpItem(keys: "Pinch text", action: "Resize tracks"),
                ShortcutHelpItem(keys: "Pinch bubble", action: "Resize MyLinguist")
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
                ShortcutHelpItem(keys: "Shift + P", action: "Toggle translation audio")
            ]
        ),
        ShortcutHelpSection(
            title: "Font Size",
            items: [
                ShortcutHelpItem(keys: "+ / -", action: "Track font size"),
                ShortcutHelpItem(keys: "Ctrl + +/-", action: "MyLinguist font size")
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
                .frame(maxHeight: 360)
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

#if os(iOS)
struct TrackpadSwipeHandler: UIViewRepresentable {
    let onSwipeDown: () -> Void
    let onSwipeUp: () -> Void

    func makeCoordinator() -> Coordinator {
        Coordinator(onSwipeDown: onSwipeDown, onSwipeUp: onSwipeUp)
    }

    func makeUIView(context: Context) -> UIView {
        let view = TrackpadSwipeView()
        view.backgroundColor = .clear
        let pan = UIPanGestureRecognizer(target: context.coordinator, action: #selector(Coordinator.handlePan(_:)))
        pan.cancelsTouchesInView = false
        if #available(iOS 13.4, *) {
            pan.allowedScrollTypesMask = [.continuous, .discrete]
            pan.allowedTouchTypes = [NSNumber(value: UITouch.TouchType.indirectPointer.rawValue)]
        }
        view.addGestureRecognizer(pan)
        return view
    }

    func updateUIView(_ uiView: UIView, context: Context) {}

    private final class TrackpadSwipeView: UIView {
        override func hitTest(_ point: CGPoint, with event: UIEvent?) -> UIView? {
            guard let event else { return nil }
            guard let touches = event.allTouches, !touches.isEmpty else { return nil }
            let hasPointer = touches.contains { touch in
                if #available(iOS 13.4, *) {
                    return touch.type == .indirectPointer || touch.type == .indirect
                }
                return false
            }
            return hasPointer ? self : nil
        }
    }

    final class Coordinator: NSObject {
        private let onSwipeDown: () -> Void
        private let onSwipeUp: () -> Void
        private let threshold: CGFloat = 24

        init(onSwipeDown: @escaping () -> Void, onSwipeUp: @escaping () -> Void) {
            self.onSwipeDown = onSwipeDown
            self.onSwipeUp = onSwipeUp
        }

        @objc func handlePan(_ gesture: UIPanGestureRecognizer) {
            guard gesture.state == .ended || gesture.state == .cancelled else { return }
            let translation = gesture.translation(in: gesture.view)
            let horizontal = translation.x
            let vertical = translation.y
            guard abs(vertical) > abs(horizontal) else { return }
            if vertical > threshold {
                onSwipeDown()
            } else if vertical < -threshold {
                onSwipeUp()
            }
        }
    }
}

struct KeyboardCommandHandler: UIViewControllerRepresentable {
    let onPlayPause: () -> Void
    let onPrevious: () -> Void
    let onNext: () -> Void
    let onPreviousWord: () -> Void
    let onNextWord: () -> Void
    let onLookup: () -> Void
    let onIncreaseFont: () -> Void
    let onDecreaseFont: () -> Void
    let onToggleOriginal: () -> Void
    let onToggleTransliteration: () -> Void
    let onToggleTranslation: () -> Void
    let onToggleOriginalAudio: () -> Void
    let onToggleTranslationAudio: () -> Void
    let onIncreaseLinguistFont: () -> Void
    let onDecreaseLinguistFont: () -> Void
    let onToggleShortcutHelp: () -> Void
    let onOptionKeyDown: () -> Void
    let onOptionKeyUp: () -> Void
    let onShowMenu: () -> Void
    let onHideMenu: () -> Void

    func makeUIViewController(context: Context) -> KeyCommandController {
        let controller = KeyCommandController()
        controller.onPlayPause = onPlayPause
        controller.onPrevious = onPrevious
        controller.onNext = onNext
        controller.onPreviousWord = onPreviousWord
        controller.onNextWord = onNextWord
        controller.onLookup = onLookup
        controller.onIncreaseFont = onIncreaseFont
        controller.onDecreaseFont = onDecreaseFont
        controller.onToggleOriginal = onToggleOriginal
        controller.onToggleTransliteration = onToggleTransliteration
        controller.onToggleTranslation = onToggleTranslation
        controller.onToggleOriginalAudio = onToggleOriginalAudio
        controller.onToggleTranslationAudio = onToggleTranslationAudio
        controller.onIncreaseLinguistFont = onIncreaseLinguistFont
        controller.onDecreaseLinguistFont = onDecreaseLinguistFont
        controller.onToggleShortcutHelp = onToggleShortcutHelp
        controller.onOptionKeyDown = onOptionKeyDown
        controller.onOptionKeyUp = onOptionKeyUp
        controller.onShowMenu = onShowMenu
        controller.onHideMenu = onHideMenu
        return controller
    }

    func updateUIViewController(_ uiViewController: KeyCommandController, context: Context) {
        uiViewController.onPlayPause = onPlayPause
        uiViewController.onPrevious = onPrevious
        uiViewController.onNext = onNext
        uiViewController.onPreviousWord = onPreviousWord
        uiViewController.onNextWord = onNextWord
        uiViewController.onLookup = onLookup
        uiViewController.onIncreaseFont = onIncreaseFont
        uiViewController.onDecreaseFont = onDecreaseFont
        uiViewController.onToggleOriginal = onToggleOriginal
        uiViewController.onToggleTransliteration = onToggleTransliteration
        uiViewController.onToggleTranslation = onToggleTranslation
        uiViewController.onToggleOriginalAudio = onToggleOriginalAudio
        uiViewController.onToggleTranslationAudio = onToggleTranslationAudio
        uiViewController.onIncreaseLinguistFont = onIncreaseLinguistFont
        uiViewController.onDecreaseLinguistFont = onDecreaseLinguistFont
        uiViewController.onToggleShortcutHelp = onToggleShortcutHelp
        uiViewController.onOptionKeyDown = onOptionKeyDown
        uiViewController.onOptionKeyUp = onOptionKeyUp
        uiViewController.onShowMenu = onShowMenu
        uiViewController.onHideMenu = onHideMenu
    }

    final class KeyCommandController: UIViewController {
        var onPlayPause: (() -> Void)?
        var onPrevious: (() -> Void)?
        var onNext: (() -> Void)?
        var onPreviousWord: (() -> Void)?
        var onNextWord: (() -> Void)?
        var onLookup: (() -> Void)?
        var onIncreaseFont: (() -> Void)?
        var onDecreaseFont: (() -> Void)?
        var onToggleOriginal: (() -> Void)?
        var onToggleTransliteration: (() -> Void)?
        var onToggleTranslation: (() -> Void)?
        var onToggleOriginalAudio: (() -> Void)?
        var onToggleTranslationAudio: (() -> Void)?
        var onIncreaseLinguistFont: (() -> Void)?
        var onDecreaseLinguistFont: (() -> Void)?
        var onToggleShortcutHelp: (() -> Void)?
        var onOptionKeyDown: (() -> Void)?
        var onOptionKeyUp: (() -> Void)?
        var onShowMenu: (() -> Void)?
        var onHideMenu: (() -> Void)?
        private var isOptionKeyDown = false

        override var canBecomeFirstResponder: Bool {
            true
        }

        override func viewDidAppear(_ animated: Bool) {
            super.viewDidAppear(animated)
            becomeFirstResponder()
        }

        override var keyCommands: [UIKeyCommand]? {
            let commands = [
                makeCommand(input: " ", action: #selector(handlePlayPause)),
                makeCommand(input: UIKeyCommand.inputLeftArrow, action: #selector(handlePrevious)),
                makeCommand(input: UIKeyCommand.inputRightArrow, action: #selector(handleNext)),
                makeCommand(input: UIKeyCommand.inputLeftArrow, modifiers: [.control], action: #selector(handlePreviousWord)),
                makeCommand(input: UIKeyCommand.inputRightArrow, modifiers: [.control], action: #selector(handleNextWord)),
                makeCommand(input: "\r", action: #selector(handleLookup)),
                makeCommand(input: "\n", action: #selector(handleLookup)),
                makeCommand(input: UIKeyCommand.inputDownArrow, action: #selector(handleShowMenu)),
                makeCommand(input: UIKeyCommand.inputUpArrow, action: #selector(handleHideMenu)),
                makeCommand(input: "h", action: #selector(handleToggleHelp)),
                makeCommand(input: "h", modifiers: [.shift], action: #selector(handleToggleHelp)),
                makeCommand(input: "o", action: #selector(handleToggleOriginal)),
                makeCommand(input: "o", modifiers: [.shift], action: #selector(handleToggleOriginalAudio)),
                makeCommand(input: "i", action: #selector(handleToggleTransliteration)),
                makeCommand(input: "i", modifiers: [.shift], action: #selector(handleToggleTransliteration)),
                makeCommand(input: "p", action: #selector(handleToggleTranslation)),
                makeCommand(input: "p", modifiers: [.shift], action: #selector(handleToggleTranslationAudio)),
                makeCommand(input: "=", modifiers: [.control], action: #selector(handleIncreaseLinguistFont)),
                makeCommand(input: "=", modifiers: [.control, .shift], action: #selector(handleIncreaseLinguistFont)),
                makeCommand(input: "+", modifiers: [.control], action: #selector(handleIncreaseLinguistFont)),
                makeCommand(input: "-", modifiers: [.control], action: #selector(handleDecreaseLinguistFont)),
                makeCommand(input: "=", modifiers: [], action: #selector(handleIncreaseFont)),
                makeCommand(input: "=", modifiers: [.shift], action: #selector(handleIncreaseFont)),
                makeCommand(input: "+", modifiers: [], action: #selector(handleIncreaseFont)),
                makeCommand(input: "-", modifiers: [], action: #selector(handleDecreaseFont)),
            ]
            return commands
        }

        @objc private func handlePlayPause() {
            onPlayPause?()
        }

        @objc private func handlePrevious() {
            onPrevious?()
        }

        @objc private func handleNext() {
            onNext?()
        }

        @objc private func handlePreviousWord() {
            onPreviousWord?()
        }

        @objc private func handleNextWord() {
            onNextWord?()
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

        @objc private func handleToggleOriginalAudio() {
            onToggleOriginalAudio?()
        }

        @objc private func handleToggleTranslationAudio() {
            onToggleTranslationAudio?()
        }

        @objc private func handleIncreaseLinguistFont() {
            onIncreaseLinguistFont?()
        }

        @objc private func handleDecreaseLinguistFont() {
            onDecreaseLinguistFont?()
        }

        @objc private func handleToggleHelp() {
            onToggleShortcutHelp?()
        }

        @objc private func handleShowMenu() {
            onShowMenu?()
        }

        @objc private func handleHideMenu() {
            onHideMenu?()
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
